# AgentPay SDK

Payment infrastructure for AI agents. A lightweight, rail-agnostic SDK that lets any AI agent send, receive, hold (escrow), and track value safely under configurable policies — with a single, simple API.

## Why AgentPay?

- **Make agents financially useful.** Give autonomous agents the ability to pay and get paid under guardrails you control.
- **Safety-first.** Per-agent policies (allowlists, limits, pause) and a double-entry ledger prevent mistakes and enable audits.
- **Rail-agnostic.** Start with internal “credits” for testing. Plug external rails (Stripe/AP2/etc.) later via adapters.

## What you can build with it

- **Agent-to-agent payments** with policy enforcement and idempotency.
- **Escrow**: lock funds now, release or cancel later.
- **Wallet + ledger**: balances, holds, immutable double-entry history.
- **Policies**: per-agent allowlists, per-transaction limits, and pause.
- **Local (in-memory) and HTTP API modes**.

---

## 📦 Installation

Requires Python 3.10+.

From source (recommended during development):

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

Optional API extras (FastAPI + Uvicorn):

```bash
pip install -e .
```

---

## 🚀 Quickstart (local, in-memory)

```python
from agentpay import AgentPaySDK, Policy

sdk = AgentPaySDK()  # local mode

# Register agents
sdk.register_agent("alice", metadata={"name": "Alice"})
sdk.register_agent("bob", metadata={"name": "Bob"})

# Fund Alice with $100.00 (cents)
sdk.fund_agent("alice", 10_000, memo="Initial funding")

# Optional: guardrails
sdk.update_agent_policy("alice", Policy(max_per_transaction=6_000))

# Pay Bob $50.00
res = sdk.pay(from_agent="alice", to_agent="bob", amount=5_000, memo="Consulting")
assert res.success, res.error_message

print("Alice:", sdk.get_balance("alice"))  # 5000
print("Bob:",   sdk.get_balance("bob"))    # 5000

# History
for e in sdk.get_transaction_history("alice"):
    print(e.entry_type, e.delta_amount, e.balance_after)
```

---

## 🧠 Core concepts

- **Agent**: Identity that owns funds and can pay others. Holds a `Wallet` and `Policy`.
- **Wallet**: `balance` (available) and `hold` (escrow). Amounts are integers (e.g., cents).
- **Policy**: Guardrails per agent — `paused`, `allowlist`, `max_per_transaction`. (`daily_spend_cap` and `require_human_approval_over` are designed but not enforced yet.)
- **PaymentIntent**: Idempotent request to move value; validated and recorded.
- **LedgerEntry**: Immutable double-entry accounting.
- **Escrow**: Authorize now, release or cancel later.

---

## 🔧 Common tasks

- **Register + manage agents**

```python
sdk = AgentPaySDK()
sdk.register_agent("agent-1", metadata={"name": "Builder"})
agent = sdk.get_agent("agent-1")

sdk.pause_agent("agent-1")
sdk.unpause_agent("agent-1")
```

- **Fund wallets**

```python
entry = sdk.fund_agent("agent-1", 25_000, memo="Seed credits")
print(entry.balance_after)
```

- **Payments with policies + idempotency**

```python
from agentpay import Policy

sdk.update_agent_policy("agent-1", Policy(allowlist={"agent-2"}, max_per_transaction=10_000))

res = sdk.pay(
    from_agent="agent-1", to_agent="agent-2", amount=9_500,
    idempotency_key="pay-2025-001", memo="Monthly access"
)
if not res.success:
    print(res.error_code, res.error_message)
```

- **Escrow lifecycle**

```python
esc = sdk.create_escrow("agent-1", "agent-2", 3_000)
escrow_id = esc.escrow.escrow_id
sdk.release_escrow(escrow_id)
# or: sdk.cancel_escrow(escrow_id)
```

- **History + queries**

```python
for e in sdk.get_transaction_history("agent-1"):
    print(e.entry_type, e.delta_amount, e.reference_id)
```

---

## 💼 Earnings helpers (local mode)

Agent-to-agent earning features build on the core payment engine and are available in local mode:

```python
# Service payment: Agent A pays Agent B for work
result = sdk.transfer_to_agent(
    from_agent_id="agent-a",
    to_agent_id="agent-b",
    amount=7_500,
    purpose="Data Analysis Report"
)

# Earnings and expenses reports
earnings = sdk.get_agent_earnings("agent-b")
expenses = sdk.get_agent_expenses("agent-b")
summary = sdk.get_agent_balance_summary("agent-b")
```

Notes:

- Helpers above are local-mode only today and rely on enhanced ledger metadata.
- All amounts are integers (smallest unit, e.g., cents).

For a runnable walkthrough, see `examples/test_earning.py`.

---

## 🌐 HTTP API (optional)

Start the local API (requires `[api]` extras):

```bash
uvicorn agentpay.api.app:app --reload
```

Endpoints (prefix `/v1`):

- `POST /agents` — register agent
- `GET /agents/{agent_id}` — get agent
- `GET /agents` — list agents
- `PATCH /agents/{agent_id}/policy` — update policy
- `POST /agents/{agent_id}/fund` — fund wallet
- `GET /agents/{agent_id}/wallet` — wallet balances
- `POST /payments` — make payment
- `GET /payments/{intent_id}` — payment status
- `POST /escrows` — create escrow
- `POST /escrows/{escrow_id}/release` — release escrow
- `POST /escrows/{escrow_id}/cancel` — cancel escrow
- `GET /agents/{agent_id}/ledger` — transaction history
- `GET /transactions/{reference_id}` — entries by reference
- `GET /health` — service health

Interactive docs:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## 🧪 Testing

```bash
pytest -q
```

The suite covers models, SDK flows, payments, escrow, and end-to-end scenarios. Add tests for new policies and integrations as you extend the SDK.

---

## 🛣️ Roadmap

- Enforce `daily_spend_cap` and add approval flow for `require_human_approval_over`.
- Streaming payments.
- Persistence (DB-backed agents/ledger/escrows/idempotency).
- HTTP service hardening (auth, idempotency headers, pagination, webhooks).
- Rail adapter interface and concrete adapters (e.g., Stripe/AP2) alongside internal credits.

---

## 🤝 Contributing

- Open an issue with your use case and proposal.
- Keep APIs minimal and rail-agnostic.
- Include tests for new behaviors and invariants.

---

## 📄 License

MIT License. See `LICENSE`.

---

## 📁 Repository structure

```
agentpay/
├── __init__.py
├── sdk.py               # High-level SDK
├── agent_registry.py    # Agent store
├── ledger_manager.py    # Double-entry ledger
├── escrow_manager.py    # Escrow lifecycle
├── payment_engine.py    # Payment orchestration
├── models/              # Core data models
└── api/                 # Optional FastAPI layer

examples/
└── test_earning.py      # Earnings demo (local mode)

tests/
├── test_models.py
├── test_sdk.py
└── test_step2_integration.py
```

---

Built for the AI agent ecosystem.
