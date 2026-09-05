import sys
import os
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db"))
from db import seed_synthetic_data  # noqa: E402
from agent import recovery_engine  # noqa: E402

bp = Blueprint("demo", __name__, url_prefix="/api/demo")


@bp.post("/generate-batch")
def generate_batch():
    body = request.get_json(silent=True) or {}
    reset = bool(body.get("reset", False))
    fp = int(body.get("failed_payments", 22))
    cd = int(body.get("checkout_dropoffs", 18))
    fs = int(body.get("failed_subscriptions", 15))

    if reset:
        seed_synthetic_data.reset_tables()
    seed_synthetic_data.seed_failed_payments(fp)
    seed_synthetic_data.seed_checkout_dropoffs(cd)
    seed_synthetic_data.seed_failed_subscriptions(fs)

    total = fp + cd + fs
    return jsonify({"generated": total, "failed_payments": fp,
                     "checkout_dropoffs": cd, "failed_subscriptions": fs})


@bp.post("/run-batch")
def run_batch():
    body = request.get_json(silent=True) or {}
    limit = int(body.get("limit", 500))
    try:
        results = recovery_engine.run_batch(limit=limit)
    except Exception as e:
        return jsonify({"error": f"Batch recovery failed: {e}"}), 500

    summary = {"processed": len(results), "recovered": 0, "escalated": 0,
               "pending": 0, "waiting": 0, "skipped": 0}
    for r in results:
        if r.get("skipped"):
            summary["skipped"] += 1
        elif r.get("outcome") == "recovered":
            summary["recovered"] += 1
        elif r.get("outcome") == "escalated":
            summary["escalated"] += 1
        elif r.get("outcome") == "waiting":
            summary["waiting"] += 1
        else:
            summary["pending"] += 1
    return jsonify({"summary": summary, "results": results})
