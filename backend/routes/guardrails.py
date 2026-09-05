from flask import Blueprint, jsonify
from config import Config

bp = Blueprint("guardrails", __name__, url_prefix="/api/guardrails")


@bp.get("")
def get_guardrails():
    return jsonify({
        "max_retries": Config.MAX_RETRIES,
        "retry_cooldown_minutes": Config.RETRY_COOLDOWN_MINUTES,
        "high_value_threshold": Config.HIGH_VALUE_THRESHOLD,
        "max_notifications": Config.MAX_NOTIFICATIONS,
        "recovery_kill_switch": Config.RECOVERY_KILL_SWITCH,
        "allowed_actions": Config.ALLOWED_ACTIONS,
        "payment_mode": Config.PAYMENT_MODE,
        "rules": [
            "Stop automated retries once max_retries is reached; escalate instead.",
            "Any AI-recommended action outside the allowed list for that scenario is rejected and escalated.",
            "Transactions at/above the high-value threshold always require manual/merchant review.",
            "A customer will not be notified more than max_notifications times.",
            "AI recommendations below a confidence floor are downgraded to a low-risk action.",
            "A global kill switch can pause all automated recovery actions instantly.",
            "Every AI recommendation and every guardrail decision is written to the audit trail.",
        ],
    })
