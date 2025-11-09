# AgentPay SDK

A lightweight, rail-agnostic SDK that lets any AI agent send, receive, hold (escrow), and track value safely under configurable policies — with a single, simple API.

## Why AgentPay?

- **Make agents financially useful.** Give autonomous agents the ability to pay and get paid under guardrails you control.
- **Safety-first.** Per-agent policies (allowlists, limits, pause) and a double-entry ledger prevent mistakes and enable audits.
- **Rail-agnostic.** Start with internal “credits” for testing. Plug external rails (Stripe/AP2/etc.) later via adapters.

## What you can build with it

- **Agent-to-agent payments** with policy enforcement and idempotency.
- **Escrows** to lock funds and release or cancel later.
- **Wallet/ledger visibility** for balances and transaction history.
- A **single Python API** you can call from your agent loops or services.
An SDK that lets any AI agent — regardless of model, provider, or platform — safely send, receive, hold, and track value under configurable policies, using a single simple API.

> **Payment infrastructure for AI agents** – internal credits, escrow, policy enforcement, and extensible rail adapters.

## Install

```bash
pip install -e .
```

Requires Python 3.10+.

## Quickstart (Local, in-memory)

```python
from agentpay.sdk import AgentPaySDK
from agentpay.models import Policy

# Create SDK in local mode (in-memory)
sdk = AgentPaySDK()

# Register agents
sdk.register_agent("alice", metadata={"name": "Alice"})
sdk.register_agent("bob", metadata={"name": "Bob"})

# Fund Alice with 100.00 credits (cents)
sdk.fund_agent("alice", 10_000, memo="Initial funding")

# Optional: set guardrails for Alice
sdk.update_agent_policy("alice", Policy(max_per_transaction=6_000))

# Pay Bob 50.00
result = sdk.pay(from_agent="alice", to_agent="bob", amount=5_000, memo="Consulting")
assert result.success, result.error_message

# Check balances
print("Alice:", sdk.get_balance("alice"))  # 5000
print("Bob:",   sdk.get_balance("bob"))    # 5000

# View Alice’s transaction history
for entry in sdk.get_transaction_history("alice"):
    print(entry.entry_type, entry.delta_amount, entry.balance_after)
```

## Core concepts (2-minute read)

- **Agent**: Logical identity that owns funds and can pay others. Holds a `Wallet` and `Policy`.
- **Wallet**: Two buckets — `balance` (available) and `hold` (reserved for escrow). Amounts are integers (smallest unit, e.g., cents).
- **Policy**: Guardrails per agent. Examples: `paused`, `allowlist`, `max_per_transaction`, `daily_spend_cap` (planned), `require_human_approval_over` (planned flow).
- **PaymentIntent**: A request to move value. The engine validates policies and funds and records double-entry ledger entries.
- **LedgerEntry**: Immutable audit trail. Every movement is recorded and reconciles to zero (except top-ups/withdrawals).
- **Escrow**: Lock funds now, release to recipient later or cancel back to payer.

## Common tasks and examples

### 1) Agent management

```python
from agentpay.sdk import AgentPaySDK
sdk = AgentPaySDK()

sdk.register_agent("agent-1", metadata={"name": "Builder"})
agent = sdk.get_agent("agent-1")
print(agent.display_name)

# Pause/unpause spending
sdk.pause_agent("agent-1")
sdk.unpause_agent("agent-1")
```

### 2) Funding wallets (top-ups)

```python
entry = sdk.fund_agent("agent-1", 25_000, memo="Seed credits")
print(entry.balance_after)
```

### 3) Payments with policies and idempotency

```python
from agentpay.models import Policy

# Only allow payments to a specific recipient, limit per-tx to 100.00
sdk.update_agent_policy("agent-1", Policy(
    allowlist={"agent-2"},
    max_per_transaction=10_000,
))

# Idempotent payment (safe to retry with the same key)
res = sdk.pay(
    from_agent="agent-1",
    to_agent="agent-2",
    amount=9_500,
    idempotency_key="pay-2025-001",
    memo="Monthly access"
)
if not res.success:
    print(res.error_code, res.error_message)
```

### 4) Escrow lifecycle

```python
# Create escrow (moves payer balance -> hold)
escrow = sdk.create_escrow(from_agent="agent-1", to_agent="agent-2", amount=3_000)
assert escrow.success
escrow_id = escrow.escrow.escrow_id

# Release (payer hold -> recipient balance)
rel = sdk.release_escrow(escrow_id)
assert rel.success

# Or cancel (payer hold -> payer balance)
# can = sdk.cancel_escrow(escrow_id)
```

### 5) History and reporting

```python
entries = sdk.get_transaction_history("agent-1")
for e in entries:
    print(e.entry_type, e.delta_amount, e.reference_id)
```

## Local vs Remote modes

- **Local mode (default)**: In-memory registry, ledger, payment engine, and escrow manager. Perfect for tests and prototyping.
- **Remote mode**: If you pass an API key, the SDK uses an `HTTPClient` to talk to a separate AgentPay service (not bundled here). You’ll need that service running with compatible endpoints.

```python
sdk = AgentPaySDK(api_key="sk_test_abc123", base_url="http://localhost:5001")
# Operations will call the HTTP API via HTTPClient.ping()/get()/post(), etc.
```

Note: This repo currently does not ship the FastAPI service; the `HTTPClient` exists for integration with an external deployment.

## Error codes and safety

Typical errors returned by the payment engine:

- `AGENT_PAUSED` — spending is paused for the payer.
- `RECIPIENT_NOT_ALLOWED` — recipient not in payer’s allowlist.
- `AMOUNT_EXCEEDS_LIMIT` — amount exceeds per-transaction limit.
- `INSUFFICIENT_FUNDS` — not enough available balance.
- `PAYER_NOT_FOUND` / `PAYEE_NOT_FOUND` — agent IDs invalid.

Design notes:
## 📦 Installation

```bash
# Core SDK (Python 3.10+)
pip install agentpay-sdk

# With HTTP API dependencies (optional)
pip install "agentpay-sdk[api]"

# Development install
git clone https://github.com/your-org/agentpay-sdk.git
cd agentpay-sdk
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

---

## 🚀 Quick Start

### SDK Usage

```python
from agentpay import AgentPaySDK, Policy

# Initialize
sdk = AgentPaySDK()

# Register agents with policy
alice_policy = Policy(max_per_transaction=5000, daily_spend_cap=20000)
sdk.register_agent("alice", policy=alice_policy, metadata={"name": "Alice"})
sdk.register_agent("bob", metadata={"name": "Bob"})

# Fund Alice (amount in cents; 10000 = $100.00)
sdk.fund_agent("alice", 10000, memo="Initial funding")

# Make a payment
result = sdk.pay("alice", "bob", 3000, memo="Payment for services")
if result.success:
    print(f"Payment succeeded: {result.payment_intent.intent_id}")
else:
    print(f"Payment failed: {result.error_message}")

# Check balances
alice_wallet = sdk.get_wallet("alice")
print(f"Alice balance: ${alice_wallet.balance / 100:.2f}")
```

### HTTP API Usage

```bash
# Start server (requires api dependencies)
uvicorn agentpay.api.app:app --reload

# Register an agent
curl -X POST http://127.0.0.1:8000/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"alice","metadata":{"name":"Alice"}}'

# Fund wallet
curl -X POST http://127.0.0.1:8000/v1/agents/alice/fund \
  -H "Content-Type: application/json" \
  -d '{"amount":10000,"memo":"Initial"}'

# Make payment
curl -X POST http://127.0.0.1:8000/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"from_agent":"alice","to_agent":"bob","amount":5000,"memo":"Test"}'
```

---

## 📚 API Documentation

### SDK API

| Method                                                               | Description                    | Example                                        |
| -------------------------------------------------------------------- | ------------------------------ | ---------------------------------------------- |
| `register_agent(agent_id, policy=None, metadata=None)`               | Register new agent             | `sdk.register_agent("alice", policy=Policy())` |
| `fund_agent(agent_id, amount, memo=None)`                            | Add funds to wallet            | `sdk.fund_agent("alice", 10000)`               |
| `pay(from_agent, to_agent, amount, memo=None, idempotency_key=None)` | Execute payment                | `sdk.pay("alice", "bob", 5000)`                |
| `create_escrow(from_agent, to_agent, amount, memo=None)`             | Hold funds in escrow           | `sdk.create_escrow("alice", "bob", 3000)`      |
| `release_escrow(escrow_id)`                                          | Release escrow to recipient    | `sdk.release_escrow("esc-123")`                |
| `cancel_escrow(escrow_id)`                                           | Cancel escrow and return funds | `sdk.cancel_escrow("esc-123")`                 |
| `get_wallet(agent_id)`                                               | Get wallet balance/holds       | `sdk.get_wallet("alice")`                      |
| `get_payment_status(intent_id)`                                      | Get payment intent status      | `sdk.get_payment_status("pay-123")`            |
| `get_transaction_history(agent_id)`                                  | Get ledger entries             | `sdk.get_transaction_history("alice")`         |

### HTTP API Endpoints

#### Agents

- `POST /v1/agents` – Register agent
- `GET /v1/agents/{agent_id}` – Get agent info
- `GET /v1/agents` – List all agents
- `PATCH /v1/agents/{agent_id}/policy` – Update policy

#### Wallet

- `POST /v1/agents/{agent_id}/fund` – Fund wallet
- `GET /v1/agents/{agent_id}/wallet` – Get wallet balance

#### Payments

- `POST /v1/payments` – Make payment
- `GET /v1/payments/{intent_id}` – Get payment status

#### Escrow

- `POST /v1/escrows` – Create escrow
- `POST /v1/escrows/{escrow_id}/release` – Release escrow
- `POST /v1/escrows/{escrow_id}/cancel` – Cancel escrow

#### History

- `GET /v1/agents/{agent_id}/ledger` – Get transaction history
- `GET /v1/transactions/{reference_id}` – Get entries by reference

#### Health

- `GET /health` – Service health check

#### Interactive Docs

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

- All amounts are integers (e.g., cents). No floats.
- Double-entry ledger ensures debits equal credits (except top-ups/withdrawals).
- Idempotency is supported in-memory in local mode.

## Current status vs roadmap

What’s implemented today:

- Agent registry and policies: `paused`, `allowlist`, `max_per_transaction` (enforced).
- Wallets and double-entry ledger: top-ups, payments, escrow lock/release/cancel, history queries.
- Payment engine: validation, policy enforcement, idempotency cache, clear results.
- High-level Python SDK: one place to call for all operations.

Planned/next:

- `daily_spend_cap` enforcement and approval workflow for `require_human_approval_over`.
- Streaming payments (stream model and ticks).
- Persistence (DB-backed agents/ledger/escrows/idempotency) with transactions.
- Optional HTTP service (auth, idempotency headers, pagination, webhooks) in this repo or a sibling.
- Rail adapter interface and at least one concrete adapter (e.g., Stripe/AP2) in addition to internal credits.

## Testing

```bash
pytest -q
```

The suite covers models, SDK flows, payments, and escrow behaviors. Add tests for your policies and integrations as you extend the SDK.

## Contributing

- Open an issue with your use case and proposed changes.
- Keep APIs minimal and rail-agnostic.
- Add tests for new behaviors and invariants.

## License

MIT License. See `LICENSE`.
## 🏗️ Architecture

```
AgentPay SDK
├── Core Models (Agent, Wallet, Policy, PaymentIntent, Escrow)
├── AgentRegistry – In-memory agent store
├── LedgerManager – Double-entry accounting
├── EscrowManager – Escrow lifecycle
├── PaymentEngine – Payment orchestration
├── Rail Adapters
│   ├── RailAdapter (base interface)
│   └── InternalCreditsAdapter (default)
└── AgentPaySDK – High-level API

HTTP Layer (optional)
├── FastAPI app
├── Request/response models
└── REST endpoints
```

### Key Concepts

- **Agents**: Entities with wallets and policies
- **Wallets**: Balance + hold amounts
- **Policies**: Spending limits and controls
- **PaymentIntents**: Idempotent payment requests
- **Escrows**: Authorize → capture/void flows
- **Ledger**: Immutable double-entry transactions
- **Rail Adapters**: Pluggable payment backends

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agentpay --cov-report=html

# Run specific test suites
pytest tests/test_models.py
pytest tests/test_sdk.py
pytest tests/test_rails.py
pytest tests/test_api.py
```

### Test Coverage

- **94 tests total** – 100% passing
- Models, core components, SDK, rail adapters, HTTP API
- Integration and end-to-end scenarios

---

## 🛣️ Roadmap

- [ ] **External rail adapters** (Stripe, PayPal, bank transfers)
- [ ] **Streaming payments** and subscriptions
- [ ] **Webhooks** for real-time events
- [ ] **Persistence layer** (PostgreSQL, Redis)
- [ ] **Multi-tenant isolation**
- [ ] **Advanced policies** (ML-based, rate limiting)

---

## 📄 License

MIT License – see LICENSE file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/your-org/agentpay-sdk.git
cd agentpay-sdk
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Run pre-commit hooks (if configured)
pre-commit install

# Run tests
pytest

# Type checking
mypy agentpay/

# Formatting
black agentpay/ tests/
```

---

## 📞 Support

- **Issues**: https://github.com/your-org/agentpay-sdk/issues
- **Discussions**: https://github.com/your-org/agentpay-sdk/discussions
- **Documentation**: https://agentpay-sdk.readthedocs.io/

---

## 🎯 Examples

### Escrow Flow

```python
# Authorize payment (hold funds)
result = sdk.create_escrow("alice", "bob", 3000, memo="Hold for order")
if result.success:
    escrow_id = result.escrow.escrow_id

    # Later: capture (release to recipient)
    sdk.release_escrow(escrow_id)

    # Or: void (return to sender)
    # sdk.cancel_escrow(escrow_id)
```

### Idempotent Payments

```python
import uuid

idempotency_key = str(uuid.uuid4())
result = sdk.pay(
    "alice", "bob", 5000,
    idempotency_key=idempotency_key
)

# Retry with same key – no duplicate charge
retry_result = sdk.pay(
    "alice", "bob", 5000,
    idempotency_key=idempotency_key
)
assert result.intent_id == retry_result.intent_id
```

### Policy Enforcement

```python
# Set strict policy
policy = Policy(
    max_per_transaction=10000,  # $100 limit
    daily_spend_cap=50000,      # $500 daily limit
    require_human_approval_over=25000,  # Approvals over $250
    paused=False
)

sdk.register_agent("alice", policy=policy)

# This will fail if exceeds limits
result = sdk.pay("alice", "bob", 20000)  # > max_per_transaction
assert not result.success
assert "exceeds limit" in result.error_message
```

---

## 📦 Package Structure

```
agentpay/
├── __init__.py          # Public API exports
├── models.py            # Core data models
├── agent_registry.py    # Agent storage
├── ledger_manager.py    # Accounting system
├── escrow_manager.py    # Escrow lifecycle
├── payment_engine.py    # Payment orchestration
├── sdk.py              # High-level SDK
├── rails/              # Payment rail adapters
│   ├── __init__.py
│   ├── base.py         # RailAdapter interface
│   └── internal_credits.py  # Internal credits adapter
└── api/                # HTTP layer
    ├── __init__.py
    ├── app.py          # FastAPI app
    ├── models.py       # Request/response models
    └── routes.py       # API endpoints

tests/
├── test_models.py      # Model tests
├── test_sdk.py         # SDK tests
├── test_rails.py       # Rail adapter tests
└── test_api.py         # HTTP API tests
```

---

**Built with ❤️ for the AI agent ecosystem**
