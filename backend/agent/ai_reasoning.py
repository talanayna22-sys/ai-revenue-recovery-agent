"""
AI Reasoning Module — ADVISORY ONLY.

This module NEVER executes a financial action. It returns a structured
recommendation:

    {
        "analysis": str,
        "recommended_action": str,
        "confidence": float,
        "reasoning": str,
        "source": "llm" | "fallback_heuristic"
    }

The Guardrails engine (agent/guardrails.py) is the only component with
authority to turn this into a real action. If the LLM API is unavailable,
unconfigured, or errors out, this module transparently falls back to a
deterministic heuristic "advisor" so the agent loop never crashes and
never stalls waiting on a third party.
"""
import json
import re
from config import Config

ALLOWED_ACTIONS_BY_SCENARIO = Config.ALLOWED_ACTIONS


def _heuristic_recommendation(context):
    """
    Deterministic, explainable stand-in for the LLM. Used automatically
    when no ANTHROPIC_API_KEY is configured, or when the live call fails.
    This is NOT a guardrail — it is just a simpler advisor. Guardrails
    still run afterward regardless of which advisor produced the input.
    """
    scenario = context["scenario_type"]
    amount = context["amount_at_risk"]
    retry_count = context.get("retry_count", 0)
    past_success = context["customer"]["past_successful_payments"]

    if scenario == "failed_payment":
        reason = (context.get("failure_reason") or "").lower()
        if retry_count >= context.get("max_retries", 2):
            action, conf = "escalate", 0.95
            analysis = f"Retry limit already reached ({retry_count}) for this customer."
            reasoning = "Further automated retries are not permitted; escalate to merchant."
        elif "temporary" in reason or "network" in reason or "timeout" in reason:
            action, conf = "controlled_retry", 0.86
            analysis = f"Failure reason '{reason or 'unknown'}' looks transient."
            reasoning = (f"Customer has {past_success} prior successful payments, "
                         f"a controlled retry is likely to succeed.")
        elif "insufficient" in reason or "declined" in reason:
            action, conf = "send_payment_link", 0.75
            analysis = f"Failure reason '{reason or 'unknown'}' suggests the same card/method may fail again."
            reasoning = "Offering an alternate payment method via a link is safer than retrying the same instrument."
        else:
            action, conf = "notify_customer", 0.6
            analysis = "Failure reason is unclear or unrecognised."
            reasoning = "Defaulting to a low-risk notification before attempting any charge."

    elif scenario == "checkout_dropoff":
        minutes = context.get("minutes_since_abandonment") or 0
        if minutes < 10:
            action, conf = "wait", 0.7
            analysis = f"Checkout abandoned only {minutes:.0f} minutes ago."
            reasoning = "Too early to contact; customer may still return organically."
        elif amount >= Config.HIGH_VALUE_THRESHOLD:
            action, conf = "escalate", 0.8
            analysis = f"High cart value (₹{amount:,.0f}) abandoned for {minutes:.0f} minutes."
            reasoning = "High-value drop-offs are routed to the merchant for a manual/human touch."
        else:
            action, conf = "send_payment_link", 0.82
            analysis = f"Checkout abandoned for {minutes:.0f} minutes, moderate value."
            reasoning = "A direct payment link recovers drop-offs more reliably than a generic reminder."

    else:  # failed_subscription
        reason = (context.get("failure_reason") or "").lower()
        if retry_count >= context.get("max_retries", 2):
            action, conf = "escalate", 0.95
            analysis = f"Subscription retry limit reached ({retry_count})."
            reasoning = "No further automated retries allowed; escalate for manual dunning."
        elif past_success >= 3:
            action, conf = "controlled_retry", 0.88
            analysis = "Customer has a strong history of successful renewals."
            reasoning = "A controlled retry is appropriate given the reliable payment history."
        else:
            action, conf = "send_payment_link", 0.7
            analysis = f"Renewal failed due to '{reason or 'unknown reason'}', limited payment history."
            reasoning = "Sending an update-payment-method link avoids repeating a possibly bad instrument."

    action = _clamp_to_allowed(scenario, action)
    return {
        "analysis": analysis,
        "recommended_action": action,
        "confidence": conf,
        "reasoning": reasoning,
        "source": "fallback_heuristic",
    }


def _clamp_to_allowed(scenario, action):
    allowed = ALLOWED_ACTIONS_BY_SCENARIO.get(scenario, [])
    return action if action in allowed else "escalate"


def _call_llm(context):
    """Attempt a real LLM call. Raises on any failure; caller catches it."""
    if not Config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    import requests

    allowed = ALLOWED_ACTIONS_BY_SCENARIO.get(context["scenario_type"], [])
    system_prompt = (
        "You are a revenue-recovery advisor for a payments merchant. "
        "You NEVER execute actions yourself, you only recommend one. "
        f"You MUST pick recommended_action from exactly this list: {allowed}. "
        "Respond with ONLY a JSON object, no prose, no markdown fences, matching this schema: "
        '{"analysis": string, "recommended_action": string, "confidence": number between 0 and 1, "reasoning": string}'
    )
    user_prompt = json.dumps(context)

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": Config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": Config.ANTHROPIC_MODEL,
            "max_tokens": 400,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    text = re.sub(r"^```json|```$", "", text.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(text)

    parsed["recommended_action"] = _clamp_to_allowed(context["scenario_type"], parsed.get("recommended_action", ""))
    parsed["confidence"] = float(parsed.get("confidence", 0.5))
    parsed["source"] = "llm"
    return parsed


def get_recommendation(context):
    """
    Public entry point. Always returns a valid recommendation dict —
    never raises — so the recovery engine can call this unconditionally.
    """
    try:
        return _call_llm(context)
    except Exception as e:
        fallback = _heuristic_recommendation(context)
        fallback["fallback_reason"] = str(e)
        return fallback
