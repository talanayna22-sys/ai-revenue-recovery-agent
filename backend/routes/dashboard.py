from flask import Blueprint, jsonify
import database as db

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/summary")
def summary():
    row = db.query_one("""
        SELECT
            COALESCE(SUM(amount_at_risk), 0) AS revenue_at_risk,
            COALESCE(SUM(recovered_amount), 0) AS revenue_recovered,
            COUNT(*) AS total_cases,
            SUM(CASE WHEN status = 'RECOVERED' THEN 1 ELSE 0 END) AS recovered_cases,
            SUM(CASE WHEN status = 'ESCALATED' THEN 1 ELSE 0 END) AS escalated_cases,
            SUM(CASE WHEN status IN ('DETECTED','ANALYZING','ACTION_TAKEN','PENDING_RETRY') THEN 1 ELSE 0 END) AS pending_cases,
            SUM(CASE WHEN scenario_type = 'failed_payment' THEN 1 ELSE 0 END) AS failed_payment_cases,
            SUM(CASE WHEN scenario_type = 'checkout_dropoff' THEN 1 ELSE 0 END) AS checkout_dropoff_cases,
            SUM(CASE WHEN scenario_type = 'failed_subscription' THEN 1 ELSE 0 END) AS failed_subscription_cases
        FROM recovery_cases
    """)
    at_risk = float(row["revenue_at_risk"] or 0)
    recovered = float(row["revenue_recovered"] or 0)
    unrecovered = max(at_risk - recovered, 0)
    recovery_rate = round((recovered / at_risk) * 100, 2) if at_risk > 0 else 0.0

    overrides = db.query_one(
        "SELECT COUNT(*) AS c FROM recovery_actions WHERE guardrail_overridden = 1"
    )
    failed_recoveries = db.query_one(
        "SELECT COUNT(*) AS c FROM recovery_actions WHERE result = 'failed'"
    )

    return jsonify({
        "revenue_at_risk": at_risk,
        "revenue_recovered": recovered,
        "unrecovered_revenue": unrecovered,
        "recovery_rate": recovery_rate,
        "total_cases": row["total_cases"] or 0,
        "recovered_cases": row["recovered_cases"] or 0,
        "escalated_cases": row["escalated_cases"] or 0,
        "pending_cases": row["pending_cases"] or 0,
        "failed_payment_cases": row["failed_payment_cases"] or 0,
        "checkout_dropoff_cases": row["checkout_dropoff_cases"] or 0,
        "failed_subscription_cases": row["failed_subscription_cases"] or 0,
        "guardrail_overrides": overrides["c"] or 0,
        "failed_recovery_attempts": failed_recoveries["c"] or 0,
    })


@bp.get("/charts")
def charts():
    by_scenario = db.query("""
        SELECT scenario_type,
               COALESCE(SUM(amount_at_risk),0) AS at_risk,
               COALESCE(SUM(recovered_amount),0) AS recovered
        FROM recovery_cases GROUP BY scenario_type
    """)
    by_status = db.query("""
        SELECT status, COUNT(*) AS count FROM recovery_cases GROUP BY status
    """)
    recent_activity = db.query("""
        SELECT al.created_at, al.event, al.detail, al.amount, al.status_at_event, al.recovery_case_id
        FROM audit_logs al ORDER BY al.created_at DESC LIMIT 25
    """)
    return jsonify({
        "recovery_by_scenario": [
            {"scenario_type": r["scenario_type"], "at_risk": float(r["at_risk"]), "recovered": float(r["recovered"])}
            for r in by_scenario
        ],
        "case_status_distribution": [{"status": r["status"], "count": r["count"]} for r in by_status],
        "recent_activity": recent_activity,
    })
