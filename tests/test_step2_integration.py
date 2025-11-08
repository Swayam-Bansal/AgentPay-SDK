"""Integration tests for Step 2 components.

Tests the interaction between:
- AgentRegistry
- LedgerManager  
- PaymentEngine
- EscrowManager
"""

import pytest
from agentpay.models import Agent, PaymentIntent, PaymentStatus
from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager
from agentpay.payment_engine import PaymentEngine, PaymentResult
from agentpay.escrow_manager import EscrowManager, EscrowStatus


@pytest.fixture
def registry():
    """Create a fresh agent registry."""
    return AgentRegistry()


@pytest.fixture
def ledger(registry):
    """Create a ledger manager."""
    return LedgerManager(registry)


@pytest.fixture
def payment_engine(registry, ledger):
    """Create a payment engine."""
    return PaymentEngine(registry, ledger)


@pytest.fixture
def escrow_manager(registry, ledger):
    """Create an escrow manager."""
    return EscrowManager(registry, ledger)


@pytest.fixture
def funded_agents(registry, ledger):
    """Create and fund two test agents."""
    alice = Agent(agent_id="alice", metadata={"name": "Alice"})
    bob = Agent(agent_id="bob", metadata={"name": "Bob"})
    
    registry.register_agent(alice)
    registry.register_agent(bob)
    
    # Fund Alice with $100
    ledger.record_top_up("alice", 10000, "topup-alice")
    
    return alice, bob


class TestAgentRegistry:
    """Tests for AgentRegistry."""
    
    def test_register_and_retrieve_agent(self, registry):
        """Test registering and retrieving an agent."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        retrieved = registry.get_agent("test-agent")
        assert retrieved is not None
        assert retrieved.agent_id == "test-agent"
    
    def test_duplicate_registration_fails(self, registry):
        """Test that duplicate agent IDs are rejected."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        with pytest.raises(ValueError, match="already exists"):
            registry.register_agent(agent)
    
    def test_agent_exists(self, registry):
        """Test agent_exists method."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        assert registry.agent_exists("test-agent") is True
        assert registry.agent_exists("nonexistent") is False
    
    def test_update_agent(self, registry):
        """Test updating an agent."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        # Update wallet
        agent.wallet.balance = 5000
        registry.update_agent(agent)
        
        retrieved = registry.get_agent("test-agent")
        assert retrieved.wallet.balance == 5000
    
    def test_list_and_count_agents(self, registry):
        """Test listing and counting agents."""
        for i in range(3):
            registry.register_agent(Agent(agent_id=f"agent-{i}"))
        
        assert registry.count_agents() == 3
        assert len(registry.list_agents()) == 3
    
    def test_delete_agent(self, registry):
        """Test deleting an agent."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        deleted = registry.delete_agent("test-agent")
        assert deleted is True
        assert registry.agent_exists("test-agent") is False
        
        # Deleting again returns False
        deleted_again = registry.delete_agent("test-agent")
        assert deleted_again is False


class TestLedgerManager:
    """Tests for LedgerManager."""
    
    def test_record_top_up(self, registry, ledger):
        """Test recording a top-up."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        entry = ledger.record_top_up("test-agent", 10000, "topup-1")
        
        assert entry.agent_id == "test-agent"
        assert entry.delta_amount == 10000
        assert entry.balance_after == 10000
        
        # Verify wallet was updated
        updated_agent = registry.get_agent("test-agent")
        assert updated_agent.wallet.balance == 10000
    
    def test_record_payment(self, registry, ledger):
        """Test recording a payment."""
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        
        # Fund Alice
        ledger.record_top_up("alice", 10000, "topup-1")
        
        # Payment Alice -> Bob
        entries = ledger.record_payment("alice", "bob", 5000, "payment-1")
        
        assert len(entries) == 2
        assert entries[0].delta_amount == -5000  # Alice debit
        assert entries[1].delta_amount == 5000   # Bob credit
        
        # Verify wallets
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 5000
        assert bob.wallet.balance == 5000
    
    def test_payment_insufficient_funds(self, registry, ledger):
        """Test payment fails with insufficient funds."""
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        
        ledger.record_top_up("alice", 1000, "topup-1")
        
        with pytest.raises(ValueError, match="Insufficient funds"):
            ledger.record_payment("alice", "bob", 2000, "payment-1")
    
    def test_escrow_lock(self, registry, ledger):
        """Test locking funds in escrow."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        ledger.record_top_up("test-agent", 10000, "topup-1")
        
        entry = ledger.record_escrow_lock("test-agent", 3000, "escrow-1")
        
        assert entry.delta_amount == -3000
        
        # Verify wallet
        agent = registry.get_agent("test-agent")
        assert agent.wallet.balance == 7000
        assert agent.wallet.hold == 3000
    
    def test_escrow_release(self, registry, ledger):
        """Test releasing escrow to recipient."""
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        
        ledger.record_top_up("alice", 10000, "topup-1")
        ledger.record_escrow_lock("alice", 3000, "escrow-1")
        
        entries = ledger.record_escrow_release("alice", "bob", 3000, "escrow-1")
        
        assert len(entries) == 2
        
        # Verify wallets
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 7000
        assert alice.wallet.hold == 0
        assert bob.wallet.balance == 3000
    
    def test_escrow_cancel(self, registry, ledger):
        """Test cancelling escrow."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        ledger.record_top_up("test-agent", 10000, "topup-1")
        ledger.record_escrow_lock("test-agent", 3000, "escrow-1")
        
        entry = ledger.record_escrow_cancel("test-agent", 3000, "escrow-1")
        
        assert entry.delta_amount == 3000
        
        # Verify wallet
        agent = registry.get_agent("test-agent")
        assert agent.wallet.balance == 10000
        assert agent.wallet.hold == 0
    
    def test_get_agent_ledger_entries(self, registry, ledger):
        """Test retrieving agent's transaction history."""
        agent = Agent(agent_id="test-agent")
        registry.register_agent(agent)
        
        ledger.record_top_up("test-agent", 10000, "topup-1")
        ledger.record_top_up("test-agent", 5000, "topup-2")
        
        entries = ledger.get_agent_ledger_entries("test-agent")
        assert len(entries) == 2
    
    def test_verify_double_entry(self, registry, ledger):
        """Test double-entry verification."""
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        
        ledger.record_top_up("alice", 10000, "topup-1")
        ledger.record_payment("alice", "bob", 5000, "payment-1")
        
        # Payment should sum to zero
        assert ledger.verify_double_entry("payment-1") is True
        
        # Top-up is exempt from zero-sum
        assert ledger.verify_double_entry("topup-1") is True


class TestPaymentEngine:
    """Tests for PaymentEngine."""
    
    def test_successful_payment(self, funded_agents, payment_engine, registry):
        """Test successful payment execution."""
        alice, bob = funded_agents
        
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=5000,
            memo="Test payment"
        )
        
        result = payment_engine.execute_payment(intent)
        
        assert result.success is True
        assert result.payment_intent.status == PaymentStatus.COMPLETED
        
        # Verify balances
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 5000
        assert bob.wallet.balance == 5000
    
    def test_payment_insufficient_funds(self, funded_agents, payment_engine):
        """Test payment fails with insufficient funds."""
        alice, bob = funded_agents
        
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=20000  # More than Alice has
        )
        
        result = payment_engine.execute_payment(intent)
        
        assert result.success is False
        assert result.error_code == "INSUFFICIENT_FUNDS"
        assert result.payment_intent.status == PaymentStatus.FAILED_FUNDS
    
    def test_payment_agent_paused(self, funded_agents, payment_engine, registry):
        """Test payment fails when agent is paused."""
        alice, bob = funded_agents
        
        # Pause Alice
        alice.policy.paused = True
        registry.update_agent(alice)
        
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=1000
        )
        
        result = payment_engine.execute_payment(intent)
        
        assert result.success is False
        assert result.error_code == "AGENT_PAUSED"
    
    def test_payment_recipient_not_allowed(self, funded_agents, payment_engine, registry):
        """Test payment fails when recipient not in allowlist."""
        alice, bob = funded_agents
        
        # Set allowlist that doesn't include Bob
        alice.policy.allowlist = {"charlie"}
        registry.update_agent(alice)
        
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=1000
        )
        
        result = payment_engine.execute_payment(intent)
        
        assert result.success is False
        assert result.error_code == "RECIPIENT_NOT_ALLOWED"
    
    def test_payment_exceeds_limit(self, funded_agents, payment_engine, registry):
        """Test payment fails when amount exceeds limit."""
        alice, bob = funded_agents
        
        # Set transaction limit
        alice.policy.max_per_transaction = 1000
        registry.update_agent(alice)
        
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=2000
        )
        
        result = payment_engine.execute_payment(intent)
        
        assert result.success is False
        assert result.error_code == "AMOUNT_EXCEEDS_LIMIT"
    
    def test_payment_idempotency(self, funded_agents, payment_engine):
        """Test idempotent payment execution."""
        alice, bob = funded_agents
        
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=1000,
            idempotency_key="unique-key-123"
        )
        
        # First execution
        result1 = payment_engine.execute_payment(intent)
        assert result1.success is True
        
        # Second execution with same key should return cached result
        result2 = payment_engine.execute_payment(intent)
        assert result2.success is True
        assert result2.payment_intent.intent_id == result1.payment_intent.intent_id
    
    def test_payment_payer_not_found(self, payment_engine):
        """Test payment fails when payer doesn't exist."""
        intent = PaymentIntent(
            from_agent_id="nonexistent",
            to_agent_id="bob",
            amount=1000
        )
        
        result = payment_engine.execute_payment(intent)
        
        assert result.success is False
        assert result.error_code == "PAYER_NOT_FOUND"


class TestEscrowManager:
    """Tests for EscrowManager."""
    
    def test_create_escrow(self, funded_agents, escrow_manager, registry):
        """Test creating an escrow."""
        alice, bob = funded_agents
        
        result = escrow_manager.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=3000,
            memo="Test escrow"
        )
        
        assert result.success is True
        assert result.escrow.status == EscrowStatus.LOCKED
        assert result.escrow.amount == 3000
        
        # Verify Alice's wallet
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 7000
        assert alice.wallet.hold == 3000
    
    def test_release_escrow(self, funded_agents, escrow_manager, registry):
        """Test releasing an escrow."""
        alice, bob = funded_agents
        
        # Create escrow
        create_result = escrow_manager.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=3000
        )
        escrow_id = create_result.escrow.escrow_id
        
        # Release it
        release_result = escrow_manager.release_escrow(escrow_id)
        
        assert release_result.success is True
        assert release_result.escrow.status == EscrowStatus.RELEASED
        
        # Verify wallets
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 7000
        assert alice.wallet.hold == 0
        assert bob.wallet.balance == 3000
    
    def test_cancel_escrow(self, funded_agents, escrow_manager, registry):
        """Test cancelling an escrow."""
        alice, bob = funded_agents
        
        # Create escrow
        create_result = escrow_manager.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=3000
        )
        escrow_id = create_result.escrow.escrow_id
        
        # Cancel it
        cancel_result = escrow_manager.cancel_escrow(escrow_id)
        
        assert cancel_result.success is True
        assert cancel_result.escrow.status == EscrowStatus.CANCELLED
        
        # Verify Alice's wallet - funds returned
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 10000
        assert alice.wallet.hold == 0
    
    def test_escrow_insufficient_funds(self, funded_agents, escrow_manager):
        """Test escrow creation fails with insufficient funds."""
        alice, bob = funded_agents
        
        result = escrow_manager.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=20000  # More than Alice has
        )
        
        assert result.success is False
        assert result.error_code == "INSUFFICIENT_FUNDS"
    
    def test_release_nonexistent_escrow(self, escrow_manager):
        """Test releasing non-existent escrow fails."""
        result = escrow_manager.release_escrow("nonexistent")
        
        assert result.success is False
        assert result.error_code == "ESCROW_NOT_FOUND"
    
    def test_release_already_completed_escrow(self, funded_agents, escrow_manager):
        """Test releasing already-completed escrow fails."""
        alice, bob = funded_agents
        
        create_result = escrow_manager.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=1000
        )
        escrow_id = create_result.escrow.escrow_id
        
        # Release once
        escrow_manager.release_escrow(escrow_id)
        
        # Try to release again
        result = escrow_manager.release_escrow(escrow_id)
        assert result.success is False
        assert result.error_code == "ESCROW_NOT_LOCKED"
    
    def test_list_escrows(self, funded_agents, escrow_manager):
        """Test listing escrows."""
        alice, bob = funded_agents
        
        # Create multiple escrows
        escrow_manager.create_escrow("alice", "bob", 1000)
        escrow_manager.create_escrow("alice", "bob", 2000)
        
        # List by payer
        alice_escrows = escrow_manager.list_escrows_by_payer("alice")
        assert len(alice_escrows) == 2
        
        # List by recipient
        bob_escrows = escrow_manager.list_escrows_by_recipient("bob")
        assert len(bob_escrows) == 2
        
        # List by status
        locked = escrow_manager.list_escrows_by_status(EscrowStatus.LOCKED)
        assert len(locked) == 2


class TestEndToEndScenarios:
    """End-to-end integration tests."""
    
    def test_complete_payment_flow(self, registry, ledger, payment_engine):
        """Test complete payment flow from registration to payment."""
        # Setup
        alice = Agent(agent_id="alice", metadata={"name": "Alice"})
        bob = Agent(agent_id="bob", metadata={"name": "Bob"})
        registry.register_agent(alice)
        registry.register_agent(bob)
        
        # Fund Alice
        ledger.record_top_up("alice", 10000, "topup-1", "Initial funding")
        
        # Create and execute payment
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=3000,
            memo="Payment for services"
        )
        
        result = payment_engine.execute_payment(intent)
        assert result.success is True
        
        # Verify ledger entries
        alice_entries = ledger.get_agent_ledger_entries("alice")
        bob_entries = ledger.get_agent_ledger_entries("bob")
        assert len(alice_entries) == 2  # Top-up + payment
        assert len(bob_entries) == 1    # Payment received
        
        # Verify final balances
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 7000
        assert bob.wallet.balance == 3000
    
    def test_complete_escrow_flow(self, registry, ledger, escrow_manager):
        """Test complete escrow flow from creation to release."""
        # Setup
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        ledger.record_top_up("alice", 10000, "topup-1")
        
        # Create escrow
        create_result = escrow_manager.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=5000,
            memo="Escrow for milestone payment"
        )
        assert create_result.success is True
        escrow_id = create_result.escrow.escrow_id
        
        # Verify Alice's wallet after lock
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 5000
        assert alice.wallet.hold == 5000
        
        # Release escrow
        release_result = escrow_manager.release_escrow(escrow_id)
        assert release_result.success is True
        
        # Verify final wallets
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 5000
        assert alice.wallet.hold == 0
        assert bob.wallet.balance == 5000
        
        # Verify ledger
        entries = ledger.get_entries_by_reference(escrow_id)
        assert len(entries) == 3  # Lock + 2 for release
    
    def test_mixed_payment_and_escrow(self, registry, ledger, payment_engine, escrow_manager):
        """Test mixing regular payments and escrow operations."""
        # Setup
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        ledger.record_top_up("alice", 10000, "topup-1")
        
        # Regular payment
        intent = PaymentIntent(from_agent_id="alice", to_agent_id="bob", amount=2000)
        result = payment_engine.execute_payment(intent)
        assert result.success is True
        
        # Create escrow
        escrow_result = escrow_manager.create_escrow("alice", "bob", 3000)
        assert escrow_result.success is True
        
        # Verify Alice's state
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 5000  # 10000 - 2000 (paid) - 3000 (locked)
        assert alice.wallet.hold == 3000
        
        # Bob should have received the payment but not escrow yet
        bob = registry.get_agent("bob")
        assert bob.wallet.balance == 2000
        
        # Release escrow
        escrow_manager.release_escrow(escrow_result.escrow.escrow_id)
        
        # Final balances
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 5000
        assert alice.wallet.hold == 0
        assert bob.wallet.balance == 5000
