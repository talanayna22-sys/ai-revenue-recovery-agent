import csv
import io
from flask import Blueprint, jsonify, request, Response
import database as db

bp = Blueprint("audit", __name__, url_prefix="/api/audit")


def _build_query(args):
    q = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if args.get("case_id"):
        q += " AND recovery_case_id = %s"
        params.append(args.get("case_id"))
    if args.get("from"):
        q += " AND created_at >= %s"
        params.append(args.get("from"))
    if args.get("to"):
        q += " AND created_at <= %s"
        params.append(args.get("to"))
    q += " ORDER BY created_at DESC LIMIT 2000"
    return q, params


@bp.get("")
def list_audit():
    q, params = _build_query(request.args)
    return jsonify(db.query(q, params))


@bp.get("/export.csv")
def export_csv():
    q, params = _build_query(request.args)
    rows = db.query(q, params)
    buf = io.StringIO()
    fieldnames = ["id", "recovery_case_id", "event", "actor", "detail", "amount", "status_at_event", "created_at"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_trail.csv"},
    )
