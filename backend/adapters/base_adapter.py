"""
Common interface both payment adapters must implement. The Recovery Engine
only ever talks to this interface, so it works identically whether the
active adapter is MockAdapter (Synthetic Mode) or RazorpayTestAdapter
(Razorpay Test Mode).
"""
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    mode_label = "unknown"

    @abstractmethod
    def controlled_retry(self, case_context):
        """Attempt to re-charge / reopen a retry window for a failed transaction.
        Returns {"status": "success"|"failed"|"pending", "reference": str, "detail": str}"""
        raise NotImplementedError

    @abstractmethod
    def send_payment_link(self, case_context):
        """Generate (and 'send') a payment link for the customer to complete payment.
        Returns {"status": "success"|"failed"|"pending", "reference": str, "link": str, "detail": str}"""
        raise NotImplementedError

    @abstractmethod
    def notify_customer(self, case_context):
        """Send a reminder notification (SMS/email stub).
        Returns {"status": "success", "detail": str}"""
        raise NotImplementedError

    @abstractmethod
    def check_status(self, reference):
        """Poll the status of a previously created reference (link/retry)."""
        raise NotImplementedError
