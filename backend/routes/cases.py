from flask import Blueprint, jsonify, request
import database as db
from agent import recovery_engine
from config import Config

bp = Blueprint("cases", __name__, url_prefix="/api/cases")

SCENARIO_ALIASES = {
    "failed_payment": "failed_payment",
    "checkout_dropoff": "checkout_dropoff",
    "failed_subscription": "failed_subscription",
}


def _enrich(case):
    """Attach scenario-specific detail fields the frontend tables need."""
    detail = {}
    if case["scenario_type"] == "failed_payment":
        t = db.query_one("SELECT * FROM transactions WHERE id = %s", [case["source_id"]])
        if t:
            detail = {"failure_reason": t["failure_reason"], "attempt_number": t["attempt_number"],
                       "payment_method": t["payment_method"]}
    elif case["scenario_type"] == "checkout_dropoff":
        s = db.query_one("SELECT * FROM checkout_sessions WHERE id = %s", [case["source_id"]])
        if s:
            detail = {"started_at": s["started_at"], "abandoned_at": s["abandoned_at"]}
    else:
        sub = db.query_one("SELECT * FROM subscriptions WHERE id = %s", [case["source_id"]])
        if sub:
            detail = {"plan_name": sub["plan_name"], "failure_reason": sub["failure_reason"],
                       "billing_cycle": sub["billing_cycle"], "renewal_date": sub["renewal_date"]}

    customer = db.query_one("SELECT name, email FROM customers WHERE id = %s", [case["customer_id"]])
    latest_action = db.query_one(
        "SELECT * FROM recovery_actions WHERE recovery_case_id = %s ORDER BY id DESC LIMIT 1",
        [case["id"]],
    )
    case = dict(case)
    case["customer_name"] = customer["name"] if customer else "Unknown"
    case["customer_email"] = customer["email"] if customer else ""
    case["detail"] = detail
    case["latest_ai_recommendation"] = latest_action["ai_recommended_action"] if latest_action else None
    case["latest_final_action"] = latest_action["final_action"] if latest_action else None
    return case


@bp.get("")
def list_cases():
    scenario_type = request.args.get("type")
    status = request.args.get("status")
    q = "SELECT * FROM recovery_cases WHERE 1=1"
    params = []
    if scenario_type:
        q += " AND scenario_type = %s"
        params.append(scenario_type)
    if status:
        q += " AND status = %s"
        params.append(status)
    q += " ORDER BY created_at DESC LIMIT 500"
    cases = db.query(q, params)
    return jsonify([_enrich(c) for c in cases])


@bp.get("/<int:case_id>")
def get_case(case_id):
    case = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [case_id])
    if not case:
        return jsonify({"error": "Case not found"}), 404
    return jsonify(_enrich(case))


@bp.post("/<int:case_id>/execute-recovery")
def execute_recovery(case_id):
    case = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [case_id])
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if case["status"] in ("RECOVERED", "ESCALATED", "STOPPED"):
        return jsonify({"error": f"Case is already terminal ({case['status']}); no action taken."}), 409
    try:
        result = recovery_engine.process_case(case_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Recovery execution failed: {e}"}), 500


@bp.get("/<int:case_id>/actions")
def get_actions(case_id):
    actions = db.query(
        "SELECT * FROM recovery_actions WHERE recovery_case_id = %s ORDER BY id ASC", [case_id]
    )
    return jsonify(actions)


@bp.get("/<int:case_id>/audit")
def get_case_audit(case_id):
    logs = db.query(
        "SELECT * FROM audit_logs WHERE recovery_case_id = %s ORDER BY created_at ASC, id ASC",
        [case_id],
    )
    return jsonify(logs)
