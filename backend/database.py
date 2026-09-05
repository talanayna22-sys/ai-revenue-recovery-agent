"""
Database access layer.

Design goal: every route/agent module calls the functions in this file
(get_conn, query, execute) and never imports a driver directly. This lets
the whole application run on MySQL (the required production database) or
on SQLite (zero-setup local dev / automated testing) purely by changing
DB_ENGINE in the environment.

Both engines are initialised from the SAME logical schema. schema.sql
(db/schema.sql) is the canonical MySQL schema. init_sqlite() below creates
an equivalent structure for SQLite so the exact same application code and
tests can run without a MySQL server installed.
"""
import os
import sqlite3
import datetime
import threading
from contextlib import contextmanager

from config import Config

_local = threading.local()


class DBError(Exception):
    pass


def _mysql_conn():
    import pymysql
    import pymysql.cursors
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _sqlite_conn():
    os.makedirs(os.path.dirname(Config.SQLITE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn():
    """Return a thread-local connection, opening one if needed."""
    if not hasattr(_local, "conn") or _local.conn is None:
        try:
            if Config.DB_ENGINE == "mysql":
                _local.conn = _mysql_conn()
            else:
                _local.conn = _sqlite_conn()
        except Exception as e:
            raise DBError(f"Could not connect to database ({Config.DB_ENGINE}): {e}")
    return _local.conn


def _qmark(sql):
    """Convert '%s' placeholders (MySQL style, used everywhere in our code)
    to '?' placeholders for sqlite."""
    if Config.DB_ENGINE == "sqlite":
        return sql.replace("%s", "?")
    return sql


def _normalize_row(row):
    """
    Make MySQL and SQLite return identical, JSON/frontend-friendly types.

    Root cause this fixes: PyMySQL returns native Python datetime.datetime /
    datetime.date objects for TIMESTAMP/DATE columns (SQLite returns plain
    strings for the same columns). Flask's jsonify() then serializes those
    datetime objects as HTTP-date strings (e.g. "Sat, 05 Sep 2026 01:49:00 GMT"),
    which the frontend's simple date parser cannot read, producing
    "Invalid Date" in the UI. Converting to the same "YYYY-MM-DD HH:MM:SS"
    string format SQLite already produces fixes this at the source, for
    every table and every route, without touching the frontend.
    """
    for key, value in row.items():
        if isinstance(value, datetime.datetime):
            row[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, datetime.date):
            row[key] = value.strftime("%Y-%m-%d")
    return row


def query(sql, params=None):
    """Run a SELECT and return a list of dict rows with consistent types."""
    conn = get_conn()
    sql = _qmark(sql)
    params = params or []
    if Config.DB_ENGINE == "mysql":
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [_normalize_row(r) for r in rows]
    else:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return [_normalize_row(dict(r)) for r in rows]


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid where applicable."""
    conn = get_conn()
    sql = _qmark(sql)
    params = params or []
    if Config.DB_ENGINE == "mysql":
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid
    else:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def executemany(sql, seq_of_params):
    conn = get_conn()
    sql = _qmark(sql)
    if Config.DB_ENGINE == "mysql":
        with conn.cursor() as cur:
            cur.executemany(sql, seq_of_params)
    else:
        conn.executemany(sql, seq_of_params)
        conn.commit()


def health_check():
    try:
        query("SELECT 1 AS ok")
        return True, Config.DB_ENGINE
    except Exception as e:
        return False, str(e)


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL,
    phone VARCHAR(20),
    past_successful_payments INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(30),
    status VARCHAR(20) NOT NULL DEFAULT 'failed',
    failure_reason VARCHAR(60),
    attempt_number INTEGER DEFAULT 1,
    razorpay_reference VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checkout_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    cart_value DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'abandoned',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    abandoned_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    plan_name VARCHAR(60),
    amount DECIMAL(10,2) NOT NULL,
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    renewal_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'failed',
    failure_reason VARCHAR(60),
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recovery_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_type VARCHAR(30) NOT NULL,
    source_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    amount_at_risk DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DETECTED',
    retry_count INTEGER DEFAULT 0,
    notification_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 2,
    recovered_amount DECIMAL(10,2) DEFAULT 0,
    last_action_at TIMESTAMP,
    next_retry_after TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recovery_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recovery_case_id INTEGER NOT NULL REFERENCES recovery_cases(id),
    ai_recommended_action VARCHAR(30),
    ai_confidence DECIMAL(4,3),
    ai_reasoning TEXT,
    ai_source VARCHAR(20),
    final_action VARCHAR(30) NOT NULL,
    guardrail_overridden INTEGER DEFAULT 0,
    guardrail_note TEXT,
    result VARCHAR(20) DEFAULT 'pending',
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recovery_case_id INTEGER REFERENCES recovery_cases(id),
    event VARCHAR(80) NOT NULL,
    actor VARCHAR(20) NOT NULL DEFAULT 'system',
    detail TEXT,
    amount DECIMAL(10,2),
    status_at_event VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cases_status ON recovery_cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_type ON recovery_cases(scenario_type);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_logs(recovery_case_id, created_at);
"""


def init_db():
    """Create all tables if they do not exist. Safe to call on every startup."""
    if Config.DB_ENGINE == "sqlite":
        conn = get_conn()
        conn.executescript(SQLITE_SCHEMA)
        conn.commit()
    else:
        # For MySQL, the operator is expected to run db/schema.sql once
        # (see README). We still sanity-check connectivity here.
        query("SELECT 1")
