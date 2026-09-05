import json
from flask import Blueprint, request, jsonify
import database as db
from config import Config
from utils import audit_logger

bp = Blueprint("razorpay", __name__, url_prefix="/api/razorpay")


@bp.post("/create-payment-link")
def create_payment_link():
    """Manual/demo trigger to create a real Razorpay Test Mode link for a case."""
    if Config.PAYMENT_MODE != "razorpay_test":
        return jsonify({"error": "PAYMENT_MODE is not 'razorpay_test'. Enable Razorpay Test Mode in .env first."}), 400

    body = request.get_json(silent=True) or {}
    case_id = body.get("case_id")
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400

    from agent import context_builder, recovery_engine
    case = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [case_id])
    if not case:
        return jsonify({"error": "Case not found"}), 404

    try:
        adapter = recovery_engine.get_adapter()
        context = context_builder.build_context(case)
        outcome = adapter.send_payment_link(context)
        return jsonify(outcome)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.post("/webhook")
def webhook():
    from adapters.razorpay_adapter import verify_webhook_signature

    signature = request.headers.get("X-Razorpay-Signature", "")
    raw_body = request.get_data()

    if not verify_webhook_signature(raw_body, signature):
        return jsonify({"error": "Invalid webhook signature"}), 400

    payload = json.loads(raw_body)
    event = payload.get("event", "")
    reference = (
        payload.get("payload", {}).get("payment_link", {}).get("entity", {}).get("id")
    )

    if not reference:
        return jsonify({"status": "ignored", "reason": "no payment_link reference in payload"})

    action = db.query_one(
        "SELECT * FROM recovery_actions WHERE ai_reasoning LIKE %s OR final_action IS NOT NULL "
        "AND recovery_case_id IN (SELECT id FROM recovery_cases) ORDER BY id DESC LIMIT 1",
        [f"%{reference}%"],
    )
    # In production this lookup would key off a stored reference column;
    # kept simple here since this endpoint requires live Razorpay credentials to exercise.

    if event == "payment_link.paid" and action:
        case_id = action["recovery_case_id"]
        case = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [case_id])
        if case and case["status"] not in ("RECOVERED", "ESCALATED"):
            db.execute(
                "UPDATE recovery_cases SET status='RECOVERED', recovered_amount=amount_at_risk WHERE id=%s",
                [case_id],
            )
            audit_logger.log(case_id, "Recovery successful (Razorpay webhook)", "system",
                              "Razorpay Test Mode payment_link.paid received.",
                              status_at_event="RECOVERED")

    return jsonify({"status": "ok"})
