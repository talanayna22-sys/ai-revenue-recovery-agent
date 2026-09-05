"""
Mock Payment Adapter — SYNTHETIC MODE.

Simulates payment outcomes so the entire recovery loop can be demoed
end-to-end without any real payment gateway. Outcomes are seeded off the
case id + action type so a given case behaves reproducibly across runs,
which makes the demo debuggable and stable.

This is clearly a simulation — it is never presented to the user as a
real Razorpay integration (see PAYMENT_MODE / mode_label).
"""
import random
import uuid
from adapters.base_adapter import BaseAdapter


class MockAdapter(BaseAdapter):
    mode_label = "Synthetic Mode"

    def _seeded_rng(self, case_context, salt):
        seed = f"{case_context.get('case_id')}-{salt}"
        return random.Random(seed)

    def _success_probability(self, case_context, base):
        """Better customer history / lower amount => nudges probability up."""
        past_success = case_context["customer"]["past_successful_payments"]
        bump = min(0.15, past_success * 0.03)
        return min(0.95, base + bump)

    def controlled_retry(self, case_context):
        rng = self._seeded_rng(case_context, f"retry-{case_context.get('retry_count', 0)}")
        prob = self._success_probability(case_context, 0.55)
        success = rng.random() < prob
        ref = f"MOCK-RETRY-{uuid.uuid4().hex[:10]}"
        return {
            "status": "success" if success else "failed",
            "reference": ref,
            "detail": "Synthetic retry attempted against mock processor." if success
                       else "Synthetic retry declined by mock processor (simulated).",
        }

    def send_payment_link(self, case_context):
        rng = self._seeded_rng(case_context, "link")
        prob = self._success_probability(case_context, 0.5)
        success = rng.random() < prob
        ref = f"MOCK-LINK-{uuid.uuid4().hex[:10]}"
        return {
            "status": "success" if success else "failed",
            "reference": ref,
            "link": f"https://mock-pay.example/link/{ref}",
            "detail": "Customer completed the synthetic payment link." if success
                       else "Synthetic payment link was not completed (simulated timeout).",
        }

    def notify_customer(self, case_context):
        return {
            "status": "success",
            "detail": "Synthetic notification (SMS/email) queued to customer.",
        }

    def check_status(self, reference):
        # In synthetic mode the outcome is decided immediately in the action call above.
        return {"status": "unknown", "detail": "Synthetic mode resolves status immediately on action."}
