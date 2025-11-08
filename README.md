# AgentPay SDK

> **Payment infrastructure for AI agents** – internal credits, escrow, policy enforcement, and extensible rail adapters.

---

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

---

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
