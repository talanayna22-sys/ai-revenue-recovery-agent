# Recoup — AI Revenue Recovery Agent

Built for **Razorpay AI Builder Buildathon — Track 03: AI Revenue Recovery**.

A merchant-facing platform where an AI agent detects revenue at risk across three
leak points — **failed payments**, **checkout drop-offs**, and **failed subscriptions**
— and runs a closed, auditable loop to win it back:

```
DETECT → ANALYZE → DECIDE → GUARDRAILS → ACT → CHECK RESULT → RECOVER / STOP / ESCALATE
```

This is not a dashboard that lists failed payments. Every case is actually pushed
through the recovery loop, and every dashboard number is computed live from real
case data — nothing is hardcoded.

---

## 1. What's AI, what's deterministic, what's synthetic

| Layer | What it is |
|---|---|
| **AI Reasoning Module** (`backend/agent/ai_reasoning.py`) | Advisory only. Returns `{analysis, recommended_action, confidence, reasoning}`. Calls the Anthropic API if `ANTHROPIC_API_KEY` is set; otherwise (or on any API failure) automatically falls back to a deterministic heuristic advisor — the system never crashes or stalls waiting on a third party. |
| **Guardrails Engine** (`backend/agent/guardrails.py`) | 100% deterministic. The *only* component with authority to approve a financial action. Can override the AI's recommendation (retry-limit reached, high-value transaction, unsupported action, repeated contact, low confidence, global kill switch). Every override is logged. |
| **Recovery Engine** (`backend/agent/recovery_engine.py`) | Orchestrates the full loop and is the only place that calls a payment adapter. |
| **Mock Adapter** (Synthetic Mode) | Simulates payment outcomes with a seeded RNG so demos are reproducible. Never touches a real payment gateway. Labeled "Synthetic Mode" everywhere in the UI. |
| **Razorpay Test Mode Adapter** | Real calls to Razorpay's sandbox API (Payment Links) + webhook verification. No real money moves. Labeled "Razorpay Test Mode" in the UI. |
| **Synthetic data** | 50+ generated customers/transactions/checkouts/subscriptions with a fixed random seed, so every demo run starts from a realistic, reproducible batch. |

The customer always pays through a real payment method (UPI/card/etc.) via
Razorpay — this application is the merchant's **recovery/control layer**, not a
replacement payment gateway.

---

## 2. Architecture

```
React (Vite)  ──REST/JSON──▶  Flask API  ──▶  Recovery Engine (deterministic orchestrator)
                                              │
                                 ┌────────────┼─────────────┐
                                 ▼            ▼             ▼
                         AI Reasoning   Guardrails    Payment Adapter
                         (advisory)     (final say)   (Mock | Razorpay Test)
                                 │            │             │
                                 └─────────┬──┴─────────────┘
                                           ▼
                                    MySQL / SQLite
                              (recovery_cases is the single
                               source of truth for all metrics)
```

Database engine is switchable via `DB_ENGINE` (`mysql` for production,
`sqlite` for zero-setup local dev/testing) — the rest of the code never
touches a driver directly, only `backend/database.py`.

---

## 3. Folder structure

```
ai-revenue-recovery-agent/
├── backend/
│   ├── app.py                     # Flask entrypoint
│   ├── config.py                  # env-driven configuration
│   ├── database.py                # DB abstraction (MySQL / SQLite)
│   ├── requirements.txt
│   ├── .env.example
│   ├── db/
│   │   ├── schema.sql              # canonical MySQL schema
│   │   └── seed_synthetic_data.py  # generates 50+ synthetic cases
│   ├── agent/
│   │   ├── context_builder.py
│   │   ├── ai_reasoning.py
│   │   ├── guardrails.py
│   │   └── recovery_engine.py
│   ├── adapters/
│   │   ├── base_adapter.py
│   │   ├── mock_adapter.py
│   │   └── razorpay_adapter.py
│   ├── routes/
│   │   ├── dashboard.py, cases.py, ai_agent.py, audit.py,
│   │   └── guardrails.py, demo.py, razorpay_webhook.py
│   ├── utils/audit_logger.py
│   └── tests/test_backend.py       # 15 automated tests, stdlib unittest
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── api/client.js
        ├── components/{layout,dashboard,cases,agent,audit,common}/
        └── pages/ (Dashboard, FailedPayments, CheckoutDropoffs,
                     FailedSubscriptions, AiAgent, AuditTrail, Guardrails)
```

---

## 4. Database setup

### Option A — MySQL (required for the actual submission)

```bash
mysql -u root -p < backend/db/schema.sql
```

Then in `backend/.env`:
```
DB_ENGINE=mysql
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=revenue_recovery
```

### Option B — SQLite (zero setup, great for quick local testing)

```
DB_ENGINE=sqlite
SQLITE_PATH=db/revenue_recovery.sqlite3
```

Tables are created automatically on first run — no migration step needed
for SQLite.

---

## 5. Installation & running

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt --break-system-packages   # or drop the flag inside a venv
cp .env.example .env        # then edit values as needed
python db/seed_synthetic_data.py --reset       # generates 55 synthetic cases
python app.py                                  # runs on http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev              # runs on http://localhost:5173, proxies /api to :5000
```

Open **http://localhost:5173**.

---

## 6. Generating synthetic data & running batch recovery

- **CLI:** `python db/seed_synthetic_data.py --reset --failed-payments 22 --checkout-dropoffs 18 --failed-subscriptions 15`
- **UI:** click **"Run Batch Recovery"** on the Dashboard — this calls
  `POST /api/demo/run-batch`, which processes every non-terminal
  `recovery_case` through the full DETECT→...→RECOVER/ESCALATE loop and
  refreshes every KPI live.
- Because of the **retry cooldown** guardrail, some cases will legitimately
  stay in `PENDING_RETRY` until the cooldown window elapses — this is
  intentional (it's one of the required stopping rules), not a bug. Run the
  batch again after a few minutes (or lower `RETRY_COOLDOWN_MINUTES` in
  `.env` for a faster demo) to watch more cases resolve.

---

## 7. Enabling Razorpay Test Mode

1. Get Test Mode API keys from your Razorpay Dashboard (Settings → API Keys, Test Mode).
2. In `backend/.env`:
   ```
   PAYMENT_MODE=razorpay_test
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
   RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxx
   ```
3. Configure a webhook in the Razorpay Dashboard pointing to
   `POST /api/razorpay/webhook`, subscribed to the `payment_link.paid` event,
   using the same secret as `RAZORPAY_WEBHOOK_SECRET`.
4. Restart the backend. The UI's mode pill will now read **"Razorpay Test Mode"**.
5. Trigger recovery on a case as usual — `controlled_retry` / `send_payment_link`
   now create a real Razorpay Test Mode payment link. Pay it with
   [Razorpay's documented test card/UPI credentials](https://razorpay.com/docs/payments/payments/test-card-upi-details/)
   to see the case flip to `RECOVERED` once the webhook fires.

**Honesty note:** Razorpay's API does not support silently re-charging an
already-failed payment. So "controlled retry" in Test Mode creates a **new**
Test Mode payment link representing the retry attempt — this is disclosed in
`adapters/razorpay_adapter.py` and in the audit trail, never presented as a
seamless server-side re-charge.

---

## 8. Testing

```bash
cd backend
python -m unittest discover -s tests -v
```

15 tests cover: DB health, synthetic data generation, all 6 guardrail rules
(retry limit, high-value threshold, unsupported action, low-confidence
downgrade, approved pass-through, kill switch), AI fallback behavior, full
batch-recovery integration, audit trail completeness, dashboard metric
consistency, and a regression test for a bug caught during development where
a customer notification was briefly (incorrectly) treated as a full recovery.

Manual end-to-end test:
1. `python db/seed_synthetic_data.py --reset`
2. `python app.py`
3. `curl -X POST http://localhost:5000/api/demo/run-batch`
4. `curl http://localhost:5000/api/dashboard/summary` — confirm recovered/escalated/pending counts and revenue figures are internally consistent (`revenue_recovered <= revenue_at_risk`).

---

## 9. Demo flow

1. Open the **Dashboard** — Revenue at Risk, Recovered, Recovery Rate, Unrecovered are all zero/empty until data exists.
2. Click **Run Batch Recovery** — watch the summary banner and KPIs update live as ~55 synthetic cases are processed.
3. Open **Failed Payments / Checkout Drop-offs / Failed Subscriptions** — click any row to open the case detail drawer: AI recommendation vs. guardrail-approved final action, full timeline, and (for non-terminal cases) an **Execute Recovery** button with a confirmation step.
4. Open **AI Agent** — see the DETECT→...→ESCALATE pipeline visualized, and every case's INPUT → ANALYSIS → DECISION → RESULT, including guardrail overrides highlighted separately from the AI's raw suggestion.
5. Open **Audit Trail** — filter by case ID, **Export CSV**.
6. Open **Guardrails** — see the live configuration (max retries, cooldown, high-value threshold, notification cap, kill switch) and the allowed-action list per scenario.
7. *(Optional)* Switch `PAYMENT_MODE=razorpay_test`, trigger recovery on one case, and complete the generated Test Mode payment link to show the loop closing with a real (test) payment.

---

## 10. Limitations & future improvements

- **Notification delivery** (SMS/email) is stubbed/logged, not actually sent — out of scope for the buildathon demo; the interface (`adapters/base_adapter.py::notify_customer`) is ready to wire into a real provider (Twilio/SendGrid) later.
- **Razorpay Test Mode `controlled_retry`** creates a new payment link rather than re-charging in place, for the reasons noted in §7 — this is a platform constraint, not a shortcut.
- **Auth** was intentionally skipped (single-merchant demo) per the buildathon brief's own guidance not to spend time on it.
- **Retry cooldowns** mean a single batch run may leave some cases in `PENDING_RETRY` — by design, but worth calling out to a judge running the demo quickly; `RETRY_COOLDOWN_MINUTES` is configurable for a faster walkthrough.
- Future: real notification channels, per-merchant multi-tenancy, a configurable-from-the-UI guardrails editor (currently read-only in the UI, but every value is env-configurable), and a live WebSocket feed instead of polling for the "recent activity" panel.
