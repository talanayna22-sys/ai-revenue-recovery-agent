"""
Generates realistic synthetic data across all three scenarios and creates
the corresponding unified recovery_cases rows. Run this once after the
schema is created:

    python db/seed_synthetic_data.py [--reset]

Uses a fixed random seed so demo runs are reproducible.
"""
import argparse
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db  # noqa: E402
from config import Config  # noqa: E402

RNG = random.Random(42)

FIRST_NAMES = ["Rahul", "Sneha", "Amit", "Priya", "Vikram", "Anjali", "Karan", "Neha",
               "Arjun", "Divya", "Rohit", "Pooja", "Sanjay", "Kavya", "Manish", "Ritu",
               "Aditya", "Meera", "Suresh", "Isha"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Iyer", "Nair", "Reddy", "Patel", "Singh",
              "Das", "Kapoor", "Menon", "Rao", "Chatterjee", "Bose", "Malhotra"]

FAILURE_REASONS = ["temporary_failure", "insufficient_funds", "bank_declined",
                    "network_timeout", "card_expired", "issuer_unavailable"]
PAYMENT_METHODS = ["UPI", "Card", "NetBanking", "Wallet"]
PLANS = [("Starter Monthly", 499), ("Pro Monthly", 1499), ("Business Monthly", 4999),
         ("Starter Annual", 4990), ("Pro Annual", 14990)]


def reset_tables():
    tables = ["audit_logs", "recovery_actions", "recovery_cases", "subscriptions",
              "checkout_sessions", "transactions", "customers"]
    for t in tables:
        db.execute(f"DELETE FROM {t}")


def make_customer():
    name = f"{RNG.choice(FIRST_NAMES)} {RNG.choice(LAST_NAMES)}"
    email = name.lower().replace(" ", ".") + f"{RNG.randint(1,999)}@example.com"
    past_success = RNG.choices([0, 1, 2, 3, 4, 5, 6], weights=[15, 15, 15, 15, 15, 15, 10])[0]
    cid = db.execute(
        "INSERT INTO customers (name, email, phone, past_successful_payments) VALUES (%s,%s,%s,%s)",
        [name, email, f"+91{RNG.randint(6000000000,9999999999)}", past_success],
    )
    return cid, past_success


def create_recovery_case(scenario_type, source_id, customer_id, amount):
    return db.execute(
        """INSERT INTO recovery_cases
           (scenario_type, source_id, customer_id, amount_at_risk, status, max_retries)
           VALUES (%s,%s,%s,%s,'DETECTED',%s)""",
        [scenario_type, source_id, customer_id, amount, Config.MAX_RETRIES],
    )


def seed_failed_payments(n):
    for _ in range(n):
        cid, _ = make_customer()
        amount = RNG.choice([499, 999, 1999, 2999, 5000, 7500, 12000, 25000, 60000])
        reason = RNG.choice(FAILURE_REASONS)
        method = RNG.choice(PAYMENT_METHODS)
        attempt = RNG.choice([1, 1, 1, 2])
        txn_id = db.execute(
            """INSERT INTO transactions (customer_id, amount, payment_method, status,
               failure_reason, attempt_number) VALUES (%s,%s,%s,'failed',%s,%s)""",
            [cid, amount, method, reason, attempt],
        )
        create_recovery_case("failed_payment", txn_id, cid, amount)


def seed_checkout_dropoffs(n):
    for _ in range(n):
        cid, _ = make_customer()
        cart_value = RNG.choice([799, 1499, 2999, 4999, 8000, 15000, 30000, 55000])
        started = datetime.now() - timedelta(minutes=RNG.randint(5, 300))
        abandoned = started + timedelta(minutes=RNG.randint(2, 20))
        session_id = db.execute(
            """INSERT INTO checkout_sessions (customer_id, cart_value, status, started_at, abandoned_at)
               VALUES (%s,%s,'abandoned',%s,%s)""",
            [cid, cart_value, started.isoformat(sep=" "), abandoned.isoformat(sep=" ")],
        )
        create_recovery_case("checkout_dropoff", session_id, cid, cart_value)


def seed_failed_subscriptions(n):
    for _ in range(n):
        cid, _ = make_customer()
        plan_name, amount = RNG.choice(PLANS)
        reason = RNG.choice(FAILURE_REASONS)
        retry_count = RNG.choices([0, 1, 2], weights=[60, 25, 15])[0]
        renewal_date = (datetime.now() - timedelta(days=RNG.randint(0, 5))).date().isoformat()
        sub_id = db.execute(
            """INSERT INTO subscriptions (customer_id, plan_name, amount, billing_cycle,
               renewal_date, status, failure_reason, retry_count)
               VALUES (%s,%s,%s,'monthly',%s,'failed',%s,%s)""",
            [cid, plan_name, amount, renewal_date, reason, retry_count],
        )
        case_id = create_recovery_case("failed_subscription", sub_id, cid, amount)
        if retry_count:
            db.execute("UPDATE recovery_cases SET retry_count = %s WHERE id = %s", [retry_count, case_id])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="wipe existing data first")
    parser.add_argument("--failed-payments", type=int, default=22)
    parser.add_argument("--checkout-dropoffs", type=int, default=18)
    parser.add_argument("--failed-subscriptions", type=int, default=15)
    args = parser.parse_args()

    db.init_db()
    if args.reset:
        reset_tables()

    seed_failed_payments(args.failed_payments)
    seed_checkout_dropoffs(args.checkout_dropoffs)
    seed_failed_subscriptions(args.failed_subscriptions)

    total = args.failed_payments + args.checkout_dropoffs + args.failed_subscriptions
    print(f"Seeded {total} synthetic recovery cases "
          f"({args.failed_payments} failed payments, {args.checkout_dropoffs} checkout drop-offs, "
          f"{args.failed_subscriptions} failed subscriptions).")


if __name__ == "__main__":
    main()
