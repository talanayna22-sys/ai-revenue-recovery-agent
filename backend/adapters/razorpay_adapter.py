"""
Razorpay Test Mode Adapter — REAL sandbox API calls, no real money.

Honesty note (per project requirements): Razorpay's API does not let a
merchant silently "re-charge" an already-failed payment behind the
customer's back. So "controlled_retry" in Test Mode is implemented as
creating a NEW Razorpay Test Mode Payment Link representing the retry
attempt, which the customer completes themselves (with Razorpay's
documented test card/UPI credentials in a sandbox demo). This is the
same underlying mechanism as send_payment_link — we label it separately
only so the audit trail still reflects the AI's original intent
(retry vs. fresh link).

Requires RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in the environment.
Never hardcode credentials; never expose the secret to the frontend.
"""
import requests
from requests.auth import HTTPBasicAuth
from adapters.base_adapter import BaseAdapter
from config import Config


class RazorpayTestAdapter(BaseAdapter):
    mode_label = "Razorpay Test Mode"
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self):
        if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
            raise RuntimeError(
                "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set. "
                "Set PAYMENT_MODE=mock or provide Test Mode credentials."
            )
        self.auth = HTTPBasicAuth(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET)

    def _create_payment_link(self, case_context, purpose):
        amount_paise = int(round(case_context["amount_at_risk"] * 100))
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "description": f"Revenue recovery ({purpose}) — case #{case_context.get('case_id')}",
            "customer": {
                "name": case_context["customer"]["name"],
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {
                "recovery_case_id": str(case_context.get("case_id")),
                "purpose": purpose,
            },
        }
        resp = requests.post(f"{self.BASE_URL}/payment_links", json=payload, auth=self.auth, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": "pending",
            "reference": data["id"],
            "link": data["short_url"],
            "detail": f"Razorpay Test Mode payment link created for {purpose}. Awaiting customer payment.",
        }

    def controlled_retry(self, case_context):
        return self._create_payment_link(case_context, "controlled_retry")

    def send_payment_link(self, case_context):
        return self._create_payment_link(case_context, "payment_link")

    def notify_customer(self, case_context):
        # Real SMS/email dispatch is out of scope for the buildathon demo;
        # we log the intent to the audit trail via the recovery engine instead.
        return {"status": "success", "detail": "Notification intent recorded (delivery channel not wired in demo)."}

    def check_status(self, reference):
        resp = requests.get(f"{self.BASE_URL}/payment_links/{reference}", auth=self.auth, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        status_map = {"paid": "success", "expired": "failed", "cancelled": "failed"}
        return {"status": status_map.get(data.get("status"), "pending"), "detail": data.get("status")}


def verify_webhook_signature(payload_body, signature_header):
    """Validate X-Razorpay-Signature using HMAC-SHA256 with the webhook secret."""
    import hmac
    import hashlib

    if not Config.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        Config.RAZORPAY_WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")
