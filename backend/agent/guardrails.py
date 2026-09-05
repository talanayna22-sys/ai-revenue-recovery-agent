"""
Deterministic Guardrails Engine.

This is the ONLY component with authority to approve a financial action.
It takes the AI's recommendation as input but can override it based on
fixed, auditable business rules. Every override is recorded so the
difference between "what the AI suggested" and "what actually happened"
is always visible (see recovery_actions.guardrail_overridden).
"""
from config import Config


def evaluate(context, ai_recommendation):
    """
    Returns:
        {
            "final_action": str,
            "overridden": bool,
            "note": str
        }
    """
    scenario = context["scenario_type"]
    amount = context["amount_at_risk"]
    retry_count = context.get("retry_count", 0)
    notif_count = context.get("notification_count", 0)
    max_retries = context.get("max_retries", Config.MAX_RETRIES)
    recommended = ai_recommendation["recommended_action"]
    allowed = Config.ALLOWED_ACTIONS.get(scenario, [])

    # Rule 0 — global kill switch
    if Config.RECOVERY_KILL_SWITCH:
        return _result("escalate", True, "Global recovery kill switch is enabled; all automated actions are paused.")

    # Rule 1 — unsupported/unrecognised action must be rejected
    if recommended not in allowed:
        return _result("escalate", True,
                        f"AI recommended an action ('{recommended}') that is not permitted for this scenario type.")

    # Rule 2 — retry limit reached => force escalate, regardless of AI opinion
    if recommended == "controlled_retry" and retry_count >= max_retries:
        return _result("escalate", True,
                        f"Retry limit reached ({retry_count}/{max_retries}); automated retries are not allowed to continue.")

    # Rule 3 — high value transactions require manual review
    if amount >= Config.HIGH_VALUE_THRESHOLD and recommended != "escalate":
        return _result("escalate", True,
                        f"Amount ₹{amount:,.0f} is at/above the manual-review threshold "
                        f"(₹{Config.HIGH_VALUE_THRESHOLD:,.0f}); routed to merchant.")

    # Rule 4 — do not repeatedly contact the same customer
    if recommended == "notify_customer" and notif_count >= Config.MAX_NOTIFICATIONS:
        return _result("escalate", True,
                        f"Customer has already been notified {notif_count} times; further contact is blocked.")

    # Rule 5 — confidence floor: very low-confidence AI suggestions get a safer fallback
    if ai_recommendation.get("confidence", 1.0) < 0.4 and recommended not in ("wait", "escalate"):
        return _result("notify_customer" if "notify_customer" in allowed else "escalate", True,
                        "AI confidence below safety threshold; downgraded to a low-risk action.")

    # No override needed — approve the AI's recommendation as-is
    return _result(recommended, False, "AI recommendation approved without modification.")


def _result(action, overridden, note):
    return {"final_action": action, "overridden": overridden, "note": note}


def check_cooldown_elapsed(case_row):
    """Rule: minimum time between retries. Returns True if a new action is allowed now."""
    from datetime import datetime
    next_retry_after = case_row.get("next_retry_after")
    if not next_retry_after:
        return True
    if isinstance(next_retry_after, str):
        try:
            next_retry_after = datetime.strptime(next_retry_after[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return True
    return datetime.now() >= next_retry_after
