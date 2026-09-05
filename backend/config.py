"""
Central configuration for the AI Revenue Recovery Agent backend.
All values are read from environment variables so no secrets are hardcoded.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- Database ----
    # DB_ENGINE can be "mysql" (production / real deployment) or "sqlite"
    # (zero-setup local development & automated testing). The rest of the
    # app talks to db.py only, never to a specific driver, so switching
    # engines never touches business logic.
    DB_ENGINE = os.getenv("DB_ENGINE", "mysql")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "revenue_recovery")

    SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(
        os.path.dirname(__file__), "db", "revenue_recovery.sqlite3"))

    # ---- AI ----
    # If ANTHROPIC_API_KEY is not set, the AI Reasoning Module automatically
    # falls back to a deterministic heuristic "advisor" so the whole agent
    # loop still runs end-to-end without any external API dependency.
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # ---- Payments ----
    # PAYMENT_MODE: "mock" (Synthetic Mode) or "razorpay_test" (Razorpay Test Mode)
    PAYMENT_MODE = os.getenv("PAYMENT_MODE", "mock")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # ---- Guardrails / stopping rules (defaults, can be overridden per env) ----
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
    RETRY_COOLDOWN_MINUTES = int(os.getenv("RETRY_COOLDOWN_MINUTES", "15"))
    HIGH_VALUE_THRESHOLD = float(os.getenv("HIGH_VALUE_THRESHOLD", "50000"))
    MAX_NOTIFICATIONS = int(os.getenv("MAX_NOTIFICATIONS", "3"))
    RECOVERY_KILL_SWITCH = os.getenv("RECOVERY_KILL_SWITCH", "false").lower() == "true"

    ALLOWED_ACTIONS = {
        "failed_payment": ["controlled_retry", "send_payment_link", "notify_customer", "escalate"],
        "checkout_dropoff": ["send_payment_link", "notify_customer", "wait", "escalate"],
        "failed_subscription": ["controlled_retry", "send_payment_link", "notify_customer", "escalate"],
    }

    # ---- Flask ----
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
