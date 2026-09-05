"""
Recovery Engine — the deterministic orchestrator.

This is the ONLY module that is allowed to call an adapter action. It runs:

    DETECT (case already exists in recovery_cases, status=DETECTED)
      -> ANALYZE (context_builder)
      -> DECIDE  (ai_reasoning — advisory)
      -> GUARDRAILS (guardrails — final authority)
      -> ACT (adapter.<action>)
      -> CHECK RESULT
      -> RECOVER / STOP / ESCALATE

Every step writes to audit_logs. recovery_actions stores the AI's raw
recommendation next to the guardrail's final decision so the two can
always be compared in the UI.
"""
from datetime import datetime, timedelta

import database as db
from agent import context_builder, ai_reasoning, guardrails
from utils import audit_logger
from config import Config


def get_adapter():
    """Chooses the active adapter based on PAYMENT_MODE. Imported lazily so
    the mock adapter (no external deps) is usable even if razorpay libs
    are unavailable in this environment."""
    if Config.PAYMENT_MODE == "razorpay_test":
        from adapters.razorpay_adapter import RazorpayTestAdapter
        return RazorpayTestAdapter()
    from adapters.mock_adapter import MockAdapter
    return MockAdapter()


def _update_case(case_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k} = %s" for k in fields)
    params = list(fields.values()) + [case_id]
    db.execute(f"UPDATE recovery_cases SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = %s", params)


def process_case(case_id):
    """
    Runs one full pass of the recovery loop for a single case.
    Safe to call repeatedly — cases that are already terminal
    (RECOVERED / ESCALATED / STOPPED) are skipped.
    Returns a summary dict describing what happened.
    """
    case = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [case_id])
    if not case:
        return {"case_id": case_id, "skipped": True, "reason": "not found"}

    if case["status"] in ("RECOVERED", "ESCALATED", "STOPPED"):
        return {"case_id": case_id, "skipped": True, "reason": f"case already terminal ({case['status']})"}

    if not guardrails.check_cooldown_elapsed(case):
        return {"case_id": case_id, "skipped": True, "reason": "cooldown not yet elapsed"}

    audit_logger.log(case_id, "Case detected", "system",
                      f"{case['scenario_type']} case flagged as revenue at risk.",
                      amount=case["amount_at_risk"], status_at_event="DETECTED")

    # ---- ANALYZE ----
    context = context_builder.build_context(case)
    _update_case(case_id, status="ANALYZING")
    audit_logger.log(case_id, "AI analysis started", "system", "Context built for AI reasoning module.",
                      status_at_event="ANALYZING")

    # ---- DECIDE (advisory) ----
    recommendation = ai_reasoning.get_recommendation(context)
    audit_logger.log(
        case_id, "AI recommendation generated", "ai",
        f"{recommendation['analysis']} => recommended '{recommendation['recommended_action']}' "
        f"(confidence {recommendation['confidence']:.2f}, source={recommendation['source']}). "
        f"Reasoning: {recommendation['reasoning']}",
        status_at_event="ANALYZING",
    )

    # ---- GUARDRAILS (final authority) ----
    decision = guardrails.evaluate(context, recommendation)
    audit_logger.log(
        case_id, "Guardrail evaluated", "system",
        f"Final action = '{decision['final_action']}'. {decision['note']}",
        status_at_event="ANALYZING",
    )
    if decision["overridden"]:
        audit_logger.log(case_id, "Guardrail override", "system",
                          f"AI recommended '{recommendation['recommended_action']}' but guardrails "
                          f"selected '{decision['final_action']}' instead. Reason: {decision['note']}",
                          status_at_event="ANALYZING")

    final_action = decision["final_action"]

    # ---- ACT ----
    if final_action == "escalate":
        return _escalate(case, context, recommendation, decision)
    if final_action == "wait":
        return _wait(case, recommendation, decision)

    return _execute_action(case, context, recommendation, decision, final_action)


def _execute_action(case, context, recommendation, decision, final_action):
    case_id = case["id"]
    adapter = get_adapter()
    _update_case(case_id, status="ACTION_TAKEN", last_action_at=datetime.now().isoformat(sep=" "))

    is_money_action = final_action in ("controlled_retry", "send_payment_link")

    if final_action == "controlled_retry":
        outcome = adapter.controlled_retry(context)
    elif final_action == "send_payment_link":
        outcome = adapter.send_payment_link(context)
    elif final_action == "notify_customer":
        outcome = adapter.notify_customer(context)
        _update_case(case_id, notification_count=case["notification_count"] + 1)
    else:
        outcome = {"status": "failed", "detail": f"Unsupported action '{final_action}' rejected."}

    action_id = db.execute(
        """INSERT INTO recovery_actions
           (recovery_case_id, ai_recommended_action, ai_confidence, ai_reasoning, ai_source,
            final_action, guardrail_overridden, guardrail_note, result)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [case_id, recommendation["recommended_action"], recommendation["confidence"],
         recommendation["reasoning"], recommendation["source"], final_action,
         1 if decision["overridden"] else 0, decision["note"],
         outcome.get("status", "pending")],
    )

    audit_logger.log(case_id, f"Recovery action executed: {final_action}", "system",
                      outcome.get("detail", ""), status_at_event="ACTION_TAKEN")

    # ---- CHECK RESULT ----
    if not is_money_action:
        # notify_customer (or any non-financial action) never itself recovers money.
        # It just moves the case into an "awaiting customer response" holding state,
        # with a cooldown so the same customer isn't re-notified immediately.
        db.execute("UPDATE recovery_actions SET result = 'success' WHERE id = %s", [action_id])
        next_retry_after = (datetime.now() + timedelta(minutes=Config.RETRY_COOLDOWN_MINUTES)).isoformat(sep=" ")
        _update_case(case_id, status="PENDING_RETRY", next_retry_after=next_retry_after)
        audit_logger.log(case_id, "Awaiting customer response", "system",
                          "Notification delivered; case will be re-evaluated after the cooldown "
                          "to see whether the customer has since paid.",
                          status_at_event="PENDING_RETRY")
        return {"case_id": case_id, "outcome": "notified_awaiting_customer", "action": final_action}

    if outcome.get("status") == "success":
        return _recover(case, action_id, outcome)
    elif outcome.get("status") == "failed":
        return _handle_failure(case, final_action, outcome)
    else:
        # pending (e.g. real Razorpay link awaiting customer) — leave case open
        _update_case(case_id, status="PENDING_RETRY")
        audit_logger.log(case_id, "Awaiting customer action", "system",
                          "Action executed; outcome will be confirmed via webhook/status check.",
                          status_at_event="PENDING_RETRY")
        return {"case_id": case_id, "outcome": "pending", "action": final_action}


def _recover(case, action_id, outcome):
    case_id = case["id"]
    amount = float(case["amount_at_risk"])
    _update_case(case_id, status="RECOVERED", recovered_amount=amount)
    db.execute("UPDATE recovery_actions SET result = 'success' WHERE id = %s", [action_id])
    audit_logger.log(case_id, "Recovery successful", "system", outcome.get("detail", ""),
                      amount=amount, status_at_event="RECOVERED")
    return {"case_id": case_id, "outcome": "recovered", "amount": amount}


def _handle_failure(case, final_action, outcome):
    case_id = case["id"]
    retry_count = case["retry_count"]
    max_retries = case["max_retries"]

    if final_action == "controlled_retry":
        retry_count += 1

    if retry_count >= max_retries and final_action in ("controlled_retry", "send_payment_link"):
        _update_case(case_id, status="ESCALATED", retry_count=retry_count)
        audit_logger.log(case_id, "Case escalated", "system",
                          f"Recovery attempt failed and retry limit reached ({retry_count}/{max_retries}).",
                          status_at_event="ESCALATED")
        return {"case_id": case_id, "outcome": "escalated", "retry_count": retry_count}

    next_retry_after = (datetime.now() + timedelta(minutes=Config.RETRY_COOLDOWN_MINUTES)).isoformat(sep=" ")
    _update_case(case_id, status="PENDING_RETRY", retry_count=retry_count, next_retry_after=next_retry_after)
    audit_logger.log(case_id, "Recovery attempt failed", "system",
                      f"{outcome.get('detail', '')} Will allow another attempt after cooldown.",
                      status_at_event="PENDING_RETRY")
    return {"case_id": case_id, "outcome": "failed_will_retry", "retry_count": retry_count}


def _escalate(case, context, recommendation, decision):
    case_id = case["id"]
    db.execute(
        """INSERT INTO recovery_actions
           (recovery_case_id, ai_recommended_action, ai_confidence, ai_reasoning, ai_source,
            final_action, guardrail_overridden, guardrail_note, result)
           VALUES (%s,%s,%s,%s,%s,'escalate',%s,%s,'success')""",
        [case_id, recommendation["recommended_action"], recommendation["confidence"],
         recommendation["reasoning"], recommendation["source"],
         1 if decision["overridden"] else 0, decision["note"]],
    )
    _update_case(case_id, status="ESCALATED")
    audit_logger.log(case_id, "Case escalated", "system", decision["note"], status_at_event="ESCALATED")
    return {"case_id": case_id, "outcome": "escalated"}


def _wait(case, recommendation, decision):
    case_id = case["id"]
    db.execute(
        """INSERT INTO recovery_actions
           (recovery_case_id, ai_recommended_action, ai_confidence, ai_reasoning, ai_source,
            final_action, guardrail_overridden, guardrail_note, result)
           VALUES (%s,%s,%s,%s,%s,'wait',%s,%s,'pending')""",
        [case_id, recommendation["recommended_action"], recommendation["confidence"],
         recommendation["reasoning"], recommendation["source"],
         1 if decision["overridden"] else 0, decision["note"]],
    )
    _update_case(case_id, status="DETECTED")  # remains open, revisited on next batch run
    audit_logger.log(case_id, "Recovery deferred (wait)", "system", decision["note"], status_at_event="DETECTED")
    return {"case_id": case_id, "outcome": "waiting"}


def run_batch(limit=200):
    """Process every non-terminal recovery case. Used by 'Run Batch Recovery'."""
    cases = db.query(
        "SELECT id FROM recovery_cases WHERE status NOT IN ('RECOVERED','ESCALATED','STOPPED') LIMIT %s",
        [limit],
    )
    results = [process_case(c["id"]) for c in cases]
    return results
