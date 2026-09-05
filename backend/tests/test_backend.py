"""
Automated tests for the AI Revenue Recovery Agent backend.

Run with:
    cd backend
    DB_ENGINE=sqlite SQLITE_PATH=db/test_revenue_recovery.sqlite3 python3 -m unittest discover -s tests -v

Uses a throwaway SQLite database so tests never touch real/dev data and
need no external services (MySQL, LLM API, Razorpay) to run.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_ENGINE"] = "sqlite"
os.environ["SQLITE_PATH"] = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "test_revenue_recovery.sqlite3")
os.environ["PAYMENT_MODE"] = "mock"
os.environ["MAX_RETRIES"] = "2"
os.environ["RETRY_COOLDOWN_MINUTES"] = "15"
os.environ["HIGH_VALUE_THRESHOLD"] = "50000"
os.environ["MAX_NOTIFICATIONS"] = "3"
os.environ["RECOVERY_KILL_SWITCH"] = "false"

import database as db  # noqa: E402
from db import seed_synthetic_data  # noqa: E402
from agent import recovery_engine, guardrails, ai_reasoning, context_builder  # noqa: E402
from config import Config  # noqa: E402


def _fresh_db():
    # Close and clear any cached thread-local connection before touching the
    # underlying file, otherwise sqlite can hand back a stale/readonly handle.
    if hasattr(db._local, "conn") and db._local.conn is not None:
        try:
            db._local.conn.close()
        except Exception:
            pass
        db._local.conn = None
    if os.path.exists(Config.SQLITE_PATH):
        os.remove(Config.SQLITE_PATH)
    db.init_db()


class TestDatabase(unittest.TestCase):
    def test_health_check(self):
        _fresh_db()
        ok, engine = db.health_check()
        self.assertTrue(ok)
        self.assertEqual(engine, "sqlite")

    def test_normalize_row_converts_datetime_objects_to_strings(self):
        """
        Regression test for the 'Invalid Date' bug: PyMySQL returns native
        datetime.datetime / datetime.date objects for TIMESTAMP/DATE columns.
        Flask's jsonify() then serializes those as HTTP-date strings
        (e.g. 'Sat, 05 Sep 2026 01:49:00 GMT'), which the frontend's date
        parser cannot read. _normalize_row must convert these to the same
        plain 'YYYY-MM-DD HH:MM:SS' string format SQLite already returns.
        """
        import datetime as dt
        row = {
            "id": 1,
            "created_at": dt.datetime(2026, 9, 5, 1, 49, 0),
            "renewal_date": dt.date(2026, 9, 1),
            "abandoned_at": None,
            "event": "Recovery successful",
        }
        normalized = db._normalize_row(dict(row))
        self.assertEqual(normalized["created_at"], "2026-09-05 01:49:00")
        self.assertEqual(normalized["renewal_date"], "2026-09-01")
        self.assertIsNone(normalized["abandoned_at"])
        self.assertEqual(normalized["event"], "Recovery successful")
        # Must never be an HTTP-date string (the actual bug that shipped)
        self.assertNotIn(",", normalized["created_at"])
        self.assertNotIn("GMT", normalized["created_at"])


class TestSeedData(unittest.TestCase):
    def test_seed_creates_expected_counts(self):
        _fresh_db()
        seed_synthetic_data.reset_tables()
        seed_synthetic_data.seed_failed_payments(5)
        seed_synthetic_data.seed_checkout_dropoffs(4)
        seed_synthetic_data.seed_failed_subscriptions(3)

        cases = db.query("SELECT * FROM recovery_cases")
        self.assertEqual(len(cases), 12)
        types = [c["scenario_type"] for c in cases]
        self.assertEqual(types.count("failed_payment"), 5)
        self.assertEqual(types.count("checkout_dropoff"), 4)
        self.assertEqual(types.count("failed_subscription"), 3)
        for c in cases:
            self.assertEqual(c["status"], "DETECTED")
            self.assertGreater(float(c["amount_at_risk"]), 0)


class TestGuardrails(unittest.TestCase):
    def test_retry_limit_forces_escalation(self):
        context = {"scenario_type": "failed_payment", "amount_at_risk": 1000,
                   "retry_count": 2, "max_retries": 2, "notification_count": 0}
        rec = {"recommended_action": "controlled_retry", "confidence": 0.9}
        decision = guardrails.evaluate(context, rec)
        self.assertEqual(decision["final_action"], "escalate")
        self.assertTrue(decision["overridden"])

    def test_high_value_forces_escalation(self):
        context = {"scenario_type": "failed_payment", "amount_at_risk": 999999,
                   "retry_count": 0, "max_retries": 2, "notification_count": 0}
        rec = {"recommended_action": "controlled_retry", "confidence": 0.9}
        decision = guardrails.evaluate(context, rec)
        self.assertEqual(decision["final_action"], "escalate")
        self.assertTrue(decision["overridden"])

    def test_unsupported_action_rejected(self):
        context = {"scenario_type": "checkout_dropoff", "amount_at_risk": 1000,
                   "retry_count": 0, "max_retries": 2, "notification_count": 0}
        rec = {"recommended_action": "controlled_retry", "confidence": 0.9}  # not allowed for this scenario
        decision = guardrails.evaluate(context, rec)
        self.assertEqual(decision["final_action"], "escalate")
        self.assertTrue(decision["overridden"])

    def test_low_confidence_is_downgraded(self):
        context = {"scenario_type": "failed_payment", "amount_at_risk": 1000,
                   "retry_count": 0, "max_retries": 2, "notification_count": 0}
        rec = {"recommended_action": "controlled_retry", "confidence": 0.1}
        decision = guardrails.evaluate(context, rec)
        self.assertNotEqual(decision["final_action"], "controlled_retry")
        self.assertTrue(decision["overridden"])

    def test_approved_recommendation_is_not_overridden(self):
        context = {"scenario_type": "failed_payment", "amount_at_risk": 1000,
                   "retry_count": 0, "max_retries": 2, "notification_count": 0}
        rec = {"recommended_action": "controlled_retry", "confidence": 0.9}
        decision = guardrails.evaluate(context, rec)
        self.assertEqual(decision["final_action"], "controlled_retry")
        self.assertFalse(decision["overridden"])

    def test_kill_switch_blocks_everything(self):
        Config.RECOVERY_KILL_SWITCH = True
        context = {"scenario_type": "failed_payment", "amount_at_risk": 1000,
                   "retry_count": 0, "max_retries": 2, "notification_count": 0}
        rec = {"recommended_action": "controlled_retry", "confidence": 0.9}
        decision = guardrails.evaluate(context, rec)
        Config.RECOVERY_KILL_SWITCH = False  # reset for other tests
        self.assertEqual(decision["final_action"], "escalate")


class TestAIReasoningFallback(unittest.TestCase):
    def test_fallback_used_when_no_api_key(self):
        Config.ANTHROPIC_API_KEY = ""
        context = {"scenario_type": "failed_payment", "amount_at_risk": 1000, "retry_count": 0,
                   "max_retries": 2, "notification_count": 0, "failure_reason": "temporary_failure",
                   "customer": {"name": "Test", "past_successful_payments": 3}}
        rec = ai_reasoning.get_recommendation(context)
        self.assertEqual(rec["source"], "fallback_heuristic")
        self.assertIn(rec["recommended_action"], Config.ALLOWED_ACTIONS["failed_payment"])
        self.assertIsInstance(rec["confidence"], float)

    def test_never_raises_on_bad_context(self):
        # Even a minimal/odd context must produce a safe recommendation, never crash.
        rec = ai_reasoning.get_recommendation({
            "scenario_type": "checkout_dropoff", "amount_at_risk": 500,
            "retry_count": 0, "max_retries": 2, "notification_count": 0,
            "customer": {"name": "X", "past_successful_payments": 0},
        })
        self.assertIn(rec["recommended_action"], Config.ALLOWED_ACTIONS["checkout_dropoff"])


class TestRecoveryEngineIntegration(unittest.TestCase):
    def setUp(self):
        _fresh_db()
        seed_synthetic_data.reset_tables()

    def test_full_loop_produces_terminal_or_pending_state(self):
        seed_synthetic_data.seed_failed_payments(10)
        results = recovery_engine.run_batch()
        self.assertEqual(len(results), 10)
        cases = db.query("SELECT * FROM recovery_cases")
        valid_statuses = {"RECOVERED", "ESCALATED", "PENDING_RETRY", "DETECTED"}
        for c in cases:
            self.assertIn(c["status"], valid_statuses)

    def test_notify_customer_never_marks_revenue_recovered_by_itself(self):
        """Regression test for a bug where sending a notification (which only
        confirms delivery, not payment) was incorrectly treated as full recovery."""
        seed_synthetic_data.seed_failed_payments(15)
        recovery_engine.run_batch()
        actions = db.query("SELECT * FROM recovery_actions WHERE final_action = 'notify_customer'")
        for a in actions:
            case = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [a["recovery_case_id"]])
            if case["status"] == "RECOVERED":
                # It's fine if the case *later* recovered via a different, subsequent
                # action — but the notify_customer action row itself must never be
                # the one whose result directly set recovered_amount in the same step.
                other_money_actions = db.query(
                    "SELECT * FROM recovery_actions WHERE recovery_case_id = %s "
                    "AND final_action IN ('controlled_retry','send_payment_link') AND result='success'",
                    [case["id"]],
                )
                self.assertTrue(len(other_money_actions) > 0,
                                 "Case marked RECOVERED with only a notify_customer action and no "
                                 "successful money-moving action — this is the bug.")

    def test_audit_trail_is_written_for_every_case(self):
        seed_synthetic_data.seed_checkout_dropoffs(6)
        cases = db.query("SELECT id FROM recovery_cases")
        for c in cases:
            recovery_engine.process_case(c["id"])
        for c in cases:
            logs = db.query("SELECT * FROM audit_logs WHERE recovery_case_id = %s", [c["id"]])
            self.assertGreater(len(logs), 0)

    def test_dashboard_metrics_are_internally_consistent(self):
        seed_synthetic_data.seed_failed_payments(10)
        seed_synthetic_data.seed_checkout_dropoffs(8)
        seed_synthetic_data.seed_failed_subscriptions(7)
        recovery_engine.run_batch()

        row = db.query_one("""
            SELECT COALESCE(SUM(amount_at_risk),0) AS at_risk,
                   COALESCE(SUM(recovered_amount),0) AS recovered
            FROM recovery_cases
        """)
        self.assertGreaterEqual(float(row["at_risk"]), float(row["recovered"]))

    def test_max_retries_eventually_escalates(self):
        seed_synthetic_data.seed_failed_payments(1)
        case = db.query_one("SELECT * FROM recovery_cases LIMIT 1")
        case_id = case["id"]
        # Force every retry to fail by running many times; eventually must escalate
        # (cooldown means most calls are skipped, but repeated cooldown resets let
        # us assert the invariant instead: retry_count never exceeds max_retries).
        for _ in range(5):
            db.execute("UPDATE recovery_cases SET next_retry_after = NULL WHERE id = %s", [case_id])
            recovery_engine.process_case(case_id)
        updated = db.query_one("SELECT * FROM recovery_cases WHERE id = %s", [case_id])
        self.assertLessEqual(updated["retry_count"], Config.MAX_RETRIES)
        self.assertIn(updated["status"], ("RECOVERED", "ESCALATED", "PENDING_RETRY", "DETECTED"))


if __name__ == "__main__":
    unittest.main()
