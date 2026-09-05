"""
Builds the structured context object passed to the AI Reasoning Module and
to the Guardrails engine for a given recovery_case. Keeping this in one
place means both components always reason over exactly the same facts.
"""
from datetime import datetime
import database as db


def _minutes_since(dt_str):
    if not dt_str:
        return None
    if isinstance(dt_str, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(dt_str[:19], fmt)
                break
            except ValueError:
                continue
        else:
            return None
    else:
        dt = dt_str
    return (datetime.now() - dt).total_seconds() / 60.0


def build_context(case_row):
    """case_row: a dict from recovery_cases (already fetched by caller)."""
    customer = db.query_one("SELECT * FROM customers WHERE id = %s", [case_row["customer_id"]])

    scenario = case_row["scenario_type"]
    source = None
    extra = {}

    if scenario == "failed_payment":
        source = db.query_one("SELECT * FROM transactions WHERE id = %s", [case_row["source_id"]])
        extra = {
            "failure_reason": source["failure_reason"] if source else None,
            "attempt_number": source["attempt_number"] if source else 1,
            "payment_method": source["payment_method"] if source else None,
        }
    elif scenario == "checkout_dropoff":
        source = db.query_one("SELECT * FROM checkout_sessions WHERE id = %s", [case_row["source_id"]])
        extra = {
            "minutes_since_abandonment": _minutes_since(source["abandoned_at"]) if source else None,
        }
    elif scenario == "failed_subscription":
        source = db.query_one("SELECT * FROM subscriptions WHERE id = %s", [case_row["source_id"]])
        extra = {
            "failure_reason": source["failure_reason"] if source else None,
            "retry_count": source["retry_count"] if source else 0,
            "plan_name": source["plan_name"] if source else None,
            "billing_cycle": source["billing_cycle"] if source else None,
        }

    prior_cases = db.query(
        "SELECT status FROM recovery_cases WHERE customer_id = %s AND id != %s",
        [case_row["customer_id"], case_row["id"]],
    )

    context = {
        "case_id": case_row["id"],
        "scenario_type": scenario,
        "amount_at_risk": float(case_row["amount_at_risk"]),
        "case_status": case_row["status"],
        "retry_count": case_row["retry_count"],
        "notification_count": case_row["notification_count"],
        "max_retries": case_row["max_retries"],
        "customer": {
            "name": customer["name"] if customer else "Unknown",
            "past_successful_payments": customer["past_successful_payments"] if customer else 0,
        },
        "prior_recovery_cases_count": len(prior_cases),
        "prior_recovery_success_count": sum(1 for c in prior_cases if c["status"] == "RECOVERED"),
        **extra,
    }
    return context
