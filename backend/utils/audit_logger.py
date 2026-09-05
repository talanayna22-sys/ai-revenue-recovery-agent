"""Single place that writes to audit_logs so every event has a consistent shape."""
import database as db


def log(case_id, event, actor="system", detail="", amount=None, status_at_event=""):
    db.execute(
        """INSERT INTO audit_logs (recovery_case_id, event, actor, detail, amount, status_at_event)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        [case_id, event, actor, detail, amount, status_at_event],
    )
