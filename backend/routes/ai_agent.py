from flask import Blueprint, jsonify, request
import database as db

bp = Blueprint("ai_agent", __name__, url_prefix="/api/ai")


@bp.get("/decisions")
def decisions():
    outcome = request.args.get("outcome")  # recovered | escalated | stopped | pending
    q = """
        SELECT ra.*, rc.scenario_type, rc.amount_at_risk, rc.status AS case_status,
               c.name AS customer_name
        FROM recovery_actions ra
        JOIN recovery_cases rc ON rc.id = ra.recovery_case_id
        JOIN customers c ON c.id = rc.customer_id
        WHERE 1=1
    """
    params = []
    if outcome == "recovered":
        q += " AND rc.status = 'RECOVERED'"
    elif outcome == "escalated":
        q += " AND rc.status = 'ESCALATED'"
    elif outcome == "pending":
        q += " AND rc.status IN ('DETECTED','ANALYZING','ACTION_TAKEN','PENDING_RETRY')"
    q += " ORDER BY ra.executed_at DESC LIMIT 200"
    rows = db.query(q, params)
    return jsonify(rows)
