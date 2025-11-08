"""Unit tests for core data models."""

import pytest
from datetime import datetime

from agentpay.models import (
    Wallet,
    Policy,
    Agent,
    PaymentIntent,
    PaymentStatus,
    LedgerEntry,
    EntryType,
)


class TestWallet:
    """Tests for Wallet model."""
    
    def test_wallet_creation_defaults(self):
        """Test wallet is created with zero balance and hold."""
        wallet = Wallet()
        assert wallet.balance == 0
        assert wallet.hold == 0
        assert wallet.total == 0
    
    def test_wallet_with_initial_balance(self):
        """Test wallet can be created with initial balance."""
        wallet = Wallet(balance=10000, hold=2000)
        assert wallet.balance == 10000
        assert wallet.hold == 2000
        assert wallet.total == 12000
    
    def test_wallet_negative_balance_rejected(self):
        """Test that negative balance is rejected by validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            Wallet(balance=-100)
    
    def test_wallet_can_spend(self):
        """Test can_spend method."""
        wallet = Wallet(balance=1000)
        assert wallet.can_spend(500) is True
        assert wallet.can_spend(1000) is True
        assert wallet.can_spend(1001) is False
    
    def test_wallet_can_hold(self):
        """Test can_hold method."""
        wallet = Wallet(balance=1000)
        assert wallet.can_hold(500) is True
        assert wallet.can_hold(1000) is True
        assert wallet.can_hold(1001) is False


class TestPolicy:
    """Tests for Policy model."""
    
    def test_policy_defaults(self):
        """Test default policy has no restrictions."""
        policy = Policy()
        assert policy.max_per_transaction is None
        assert policy.daily_spend_cap is None
        assert policy.require_human_approval_over is None
        assert policy.allowlist is None
        assert policy.paused is False
    
    def test_policy_with_limits(self):
        """Test policy with spending limits."""
        policy = Policy(
            max_per_transaction=5000,
            daily_spend_cap=20000,
            require_human_approval_over=10000
        )
        assert policy.max_per_transaction == 5000
        assert policy.daily_spend_cap == 20000
        assert policy.require_human_approval_over == 10000
    
    def test_policy_is_agent_allowed_no_allowlist(self):
        """Test allowlist check with no allowlist (all allowed)."""
        policy = Policy()
        assert policy.is_agent_allowed("any-agent-id") is True
    
    def test_policy_is_agent_allowed_with_allowlist(self):
        """Test allowlist enforcement."""
        policy = Policy(allowlist={"agent-1", "agent-2"})
        assert policy.is_agent_allowed("agent-1") is True
        assert policy.is_agent_allowed("agent-2") is True
        assert policy.is_agent_allowed("agent-3") is False
    
    def test_policy_is_amount_allowed(self):
        """Test per-transaction limit check."""
        policy = Policy(max_per_transaction=1000)
        assert policy.is_amount_allowed(500) is True
        assert policy.is_amount_allowed(1000) is True
        assert policy.is_amount_allowed(1001) is False
    
    def test_policy_is_amount_allowed_no_limit(self):
        """Test amount check with no limit."""
        policy = Policy()
        assert policy.is_amount_allowed(999999999) is True
    
    def test_policy_requires_approval(self):
        """Test approval requirement check."""
        policy = Policy(require_human_approval_over=5000)
        assert policy.requires_approval(4999) is False
        assert policy.requires_approval(5000) is False
        assert policy.requires_approval(5001) is True


class TestAgent:
    """Tests for Agent model."""
    
    def test_agent_creation_with_defaults(self):
        """Test agent is created with auto-generated ID and default wallet/policy."""
        agent = Agent()
        assert agent.agent_id is not None
        assert len(agent.agent_id) > 0
        assert agent.wallet.balance == 0
        assert agent.policy.paused is False
        assert agent.metadata == {}
    
    def test_agent_with_custom_id(self):
        """Test agent can be created with custom ID."""
        agent = Agent(agent_id="custom-agent-123")
        assert agent.agent_id == "custom-agent-123"
    
    def test_agent_with_metadata(self):
        """Test agent with metadata."""
        agent = Agent(metadata={"name": "Alice", "role": "assistant"})
        assert agent.metadata["name"] == "Alice"
        assert agent.display_name == "Alice"
    
    def test_agent_display_name_fallback(self):
        """Test display_name falls back to agent_id if no name in metadata."""
        agent = Agent(agent_id="agent-123")
        assert agent.display_name == "agent-123"
    
    def test_agent_can_pay_success(self):
        """Test can_pay returns True when all checks pass."""
        agent = Agent()
        agent.wallet.balance = 10000
        
        can_pay, reason = agent.can_pay(5000, "recipient-123")
        assert can_pay is True
        assert reason is None
    
    def test_agent_can_pay_paused(self):
        """Test can_pay fails when agent is paused."""
        agent = Agent()
        agent.policy.paused = True
        agent.wallet.balance = 10000
        
        can_pay, reason = agent.can_pay(5000, "recipient-123")
        assert can_pay is False
        assert reason == "AGENT_PAUSED"
    
    def test_agent_can_pay_not_in_allowlist(self):
        """Test can_pay fails when recipient not in allowlist."""
        agent = Agent()
        agent.policy.allowlist = {"allowed-agent"}
        agent.wallet.balance = 10000
        
        can_pay, reason = agent.can_pay(5000, "not-allowed")
        assert can_pay is False
        assert reason == "RECIPIENT_NOT_ALLOWED"
    
    def test_agent_can_pay_exceeds_limit(self):
        """Test can_pay fails when amount exceeds limit."""
        agent = Agent()
        agent.policy.max_per_transaction = 1000
        agent.wallet.balance = 10000
        
        can_pay, reason = agent.can_pay(2000, "recipient-123")
        assert can_pay is False
        assert reason == "AMOUNT_EXCEEDS_LIMIT"
    
    def test_agent_can_pay_insufficient_funds(self):
        """Test can_pay fails with insufficient funds."""
        agent = Agent()
        agent.wallet.balance = 100
        
        can_pay, reason = agent.can_pay(500, "recipient-123")
        assert can_pay is False
        assert reason == "INSUFFICIENT_FUNDS"


class TestPaymentIntent:
    """Tests for PaymentIntent model."""
    
    def test_payment_intent_creation(self):
        """Test payment intent is created with correct defaults."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000
        )
        assert intent.intent_id is not None
        assert intent.from_agent_id == "agent-1"
        assert intent.to_agent_id == "agent-2"
        assert intent.amount == 1000
        assert intent.status == PaymentStatus.REQUIRES_CONFIRMATION
        assert intent.completed_at is None
        assert intent.failure_reason is None
    
    def test_payment_intent_with_idempotency_key(self):
        """Test payment intent with idempotency key."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000,
            idempotency_key="unique-key-123"
        )
        assert intent.idempotency_key == "unique-key-123"
    
    def test_payment_intent_with_memo(self):
        """Test payment intent with memo."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000,
            memo="Payment for services"
        )
        assert intent.memo == "Payment for services"
    
    def test_payment_intent_mark_completed(self):
        """Test marking payment as completed."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000
        )
        intent.mark_completed()
        
        assert intent.status == PaymentStatus.COMPLETED
        assert intent.completed_at is not None
        assert isinstance(intent.completed_at, datetime)
    
    def test_payment_intent_mark_failed_policy(self):
        """Test marking payment as failed due to policy."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000
        )
        intent.mark_failed("AGENT_PAUSED")
        
        assert intent.status == PaymentStatus.FAILED_POLICY
        assert intent.failure_reason == "AGENT_PAUSED"
        assert intent.completed_at is not None
    
    def test_payment_intent_mark_failed_funds(self):
        """Test marking payment as failed due to insufficient funds."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000
        )
        intent.mark_failed("INSUFFICIENT_FUNDS")
        
        assert intent.status == PaymentStatus.FAILED_FUNDS
        assert intent.failure_reason == "INSUFFICIENT_FUNDS"
    
    def test_payment_intent_mark_cancelled(self):
        """Test marking payment as cancelled."""
        intent = PaymentIntent(
            from_agent_id="agent-1",
            to_agent_id="agent-2",
            amount=1000
        )
        intent.mark_cancelled()
        
        assert intent.status == PaymentStatus.CANCELLED
        assert intent.completed_at is not None
    
    def test_payment_intent_zero_amount_rejected(self):
        """Test that zero or negative amounts are rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PaymentIntent(
                from_agent_id="agent-1",
                to_agent_id="agent-2",
                amount=0
            )


class TestLedgerEntry:
    """Tests for LedgerEntry model."""
    
    def test_ledger_entry_creation(self):
        """Test ledger entry is created correctly."""
        entry = LedgerEntry(
            agent_id="agent-1",
            delta_amount=-1000,
            entry_type=EntryType.PAYMENT,
            reference_id="payment-123",
            balance_after=9000
        )
        assert entry.entry_id is not None
        assert entry.agent_id == "agent-1"
        assert entry.delta_amount == -1000
        assert entry.entry_type == EntryType.PAYMENT
        assert entry.reference_id == "payment-123"
        assert entry.balance_after == 9000
        assert entry.created_at is not None
    
    def test_ledger_entry_is_debit(self):
        """Test is_debit property for negative amounts."""
        entry = LedgerEntry(
            agent_id="agent-1",
            delta_amount=-500,
            entry_type=EntryType.PAYMENT,
            reference_id="payment-123",
            balance_after=500
        )
        assert entry.is_debit is True
        assert entry.is_credit is False
    
    def test_ledger_entry_is_credit(self):
        """Test is_credit property for positive amounts."""
        entry = LedgerEntry(
            agent_id="agent-2",
            delta_amount=500,
            entry_type=EntryType.PAYMENT,
            reference_id="payment-123",
            balance_after=1500
        )
        assert entry.is_credit is True
        assert entry.is_debit is False
    
    def test_ledger_entry_with_memo(self):
        """Test ledger entry with memo."""
        entry = LedgerEntry(
            agent_id="agent-1",
            delta_amount=1000,
            entry_type=EntryType.TOP_UP,
            reference_id="topup-123",
            balance_after=1000,
            memo="Initial funding"
        )
        assert entry.memo == "Initial funding"
    
    def test_ledger_entry_negative_balance_after_rejected(self):
        """Test that negative balance_after is rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            LedgerEntry(
                agent_id="agent-1",
                delta_amount=-1000,
                entry_type=EntryType.PAYMENT,
                reference_id="payment-123",
                balance_after=-100  # Invalid
            )
    
    def test_ledger_entry_types(self):
        """Test all entry types are available."""
        assert EntryType.PAYMENT == "payment"
        assert EntryType.ESCROW_LOCK == "escrow_lock"
        assert EntryType.ESCROW_RELEASE == "escrow_release"
        assert EntryType.ESCROW_CANCEL == "escrow_cancel"
        assert EntryType.STREAM_TICK == "stream_tick"
        assert EntryType.TOP_UP == "top_up"
        assert EntryType.WITHDRAWAL == "withdrawal"
        assert EntryType.ADJUSTMENT == "adjustment"
