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
