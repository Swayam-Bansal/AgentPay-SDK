"""Tests for payment rail adapters."""

import pytest
from agentpay.models import Agent
from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager
from agentpay.escrow_manager import EscrowManager
from agentpay.rails import InternalCreditsAdapter, TransactionStatus


@pytest.fixture
def registry():
    """Create a fresh agent registry."""
    return AgentRegistry()


@pytest.fixture
def ledger(registry):
    """Create a ledger manager."""
    return LedgerManager(registry)


@pytest.fixture
def escrow_manager(registry, ledger):
    """Create an escrow manager."""
    return EscrowManager(registry, ledger)


@pytest.fixture
def adapter(registry, ledger, escrow_manager):
    """Create an internal credits adapter."""
    return InternalCreditsAdapter(registry, ledger, escrow_manager)


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


class TestInternalCreditsAdapter:
    """Tests for InternalCreditsAdapter."""
    
    def test_get_name(self, adapter):
        """Test adapter name."""
        assert adapter.get_name() == "internal_credits"
    
    def test_transfer_success(self, adapter, funded_agents, registry):
        """Test successful direct transfer."""
        alice, bob = funded_agents
        
        txn = adapter.transfer(
            from_account="alice",
            to_account="bob",
            amount=5000,
            metadata={"memo": "Test transfer"}
        )
        
        assert txn.status == TransactionStatus.COMPLETED
        assert txn.rail_name == "internal_credits"
        assert txn.from_account == "alice"
        assert txn.to_account == "bob"
        assert txn.amount == 5000
        
        # Verify balances
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 5000
        assert bob.wallet.balance == 5000
    
    def test_transfer_insufficient_funds(self, adapter, funded_agents):
        """Test transfer with insufficient funds."""
        alice, bob = funded_agents
        
        txn = adapter.transfer(
            from_account="alice",
            to_account="bob",
            amount=20000  # More than Alice has
        )
        
        assert txn.status == TransactionStatus.FAILED
        assert txn.error_message is not None
    
    def test_transfer_nonexistent_account(self, adapter, funded_agents):
        """Test transfer with non-existent account."""
        alice, bob = funded_agents
        
        # Non-existent sender
        txn1 = adapter.transfer(
            from_account="nonexistent",
            to_account="bob",
            amount=1000
        )
        assert txn1.status == TransactionStatus.FAILED
        
        # Non-existent recipient
        txn2 = adapter.transfer(
            from_account="alice",
            to_account="nonexistent",
            amount=1000
        )
        assert txn2.status == TransactionStatus.FAILED
    
    def test_authorize_success(self, adapter, funded_agents, registry):
        """Test successful authorization (escrow lock)."""
        alice, bob = funded_agents
        
        txn = adapter.authorize(
            from_account="alice",
            to_account="bob",
            amount=3000,
            metadata={"memo": "Hold for payment"}
        )
        
        assert txn.status == TransactionStatus.AUTHORIZED
        assert txn.external_id is not None  # Escrow ID
        
        # Verify Alice's wallet
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 7000
        assert alice.wallet.hold == 3000
    
    def test_authorize_insufficient_funds(self, adapter, funded_agents):
        """Test authorization with insufficient funds."""
        alice, bob = funded_agents
        
        txn = adapter.authorize(
            from_account="alice",
            to_account="bob",
            amount=20000
        )
        
        assert txn.status == TransactionStatus.FAILED
    
    def test_capture_success(self, adapter, funded_agents, registry):
        """Test successful capture of authorized transaction."""
        alice, bob = funded_agents
        
        # Authorize
        auth_txn = adapter.authorize("alice", "bob", 3000)
        assert auth_txn.status == TransactionStatus.AUTHORIZED
        
        # Capture
        capture_txn = adapter.capture(auth_txn.transaction_id)
        
        assert capture_txn.status == TransactionStatus.CAPTURED
        assert capture_txn.transaction_id == auth_txn.transaction_id
        
        # Verify balances
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 7000
        assert alice.wallet.hold == 0
        assert bob.wallet.balance == 3000
    
    def test_capture_nonexistent_transaction(self, adapter):
        """Test capturing non-existent transaction."""
        with pytest.raises(ValueError, match="not found"):
            adapter.capture("nonexistent-txn-id")
    
    def test_capture_not_authorized(self, adapter, funded_agents):
        """Test capturing transaction that's not in AUTHORIZED state."""
        alice, bob = funded_agents
        
        # Create a completed transfer
        txn = adapter.transfer("alice", "bob", 1000)
        
        # Try to capture it
        with pytest.raises(ValueError, match="cannot capture"):
            adapter.capture(txn.transaction_id)
    
    def test_void_success(self, adapter, funded_agents, registry):
        """Test successful void of authorized transaction."""
        alice, bob = funded_agents
        
        # Authorize
        auth_txn = adapter.authorize("alice", "bob", 3000)
        assert auth_txn.status == TransactionStatus.AUTHORIZED
        
        # Void
        void_txn = adapter.void(auth_txn.transaction_id)
        
        assert void_txn.status == TransactionStatus.CANCELLED
        
        # Verify Alice's wallet - funds returned
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 10000
        assert alice.wallet.hold == 0
    
    def test_void_nonexistent_transaction(self, adapter):
        """Test voiding non-existent transaction."""
        with pytest.raises(ValueError, match="not found"):
            adapter.void("nonexistent-txn-id")
    
    def test_void_not_authorized(self, adapter, funded_agents):
        """Test voiding transaction that's not in AUTHORIZED state."""
        alice, bob = funded_agents
        
        # Create a completed transfer
        txn = adapter.transfer("alice", "bob", 1000)
        
        # Try to void it
        with pytest.raises(ValueError, match="cannot void"):
            adapter.void(txn.transaction_id)
    
    def test_refund_success(self, adapter, funded_agents, registry):
        """Test successful refund of completed transaction."""
        alice, bob = funded_agents
        
        # Transfer
        txn = adapter.transfer("alice", "bob", 3000)
        assert txn.status == TransactionStatus.COMPLETED
        
        # Refund
        refund_txn = adapter.refund(
            txn.transaction_id,
            reason="Customer requested refund"
        )
        
        assert refund_txn.status == TransactionStatus.COMPLETED
        assert refund_txn.from_account == "bob"  # Reversed
        assert refund_txn.to_account == "alice"  # Reversed
        assert refund_txn.amount == 3000
        
        # Original transaction should be marked as refunded
        assert txn.status == TransactionStatus.REFUNDED
        
        # Verify balances - should be back to original
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 10000
        assert bob.wallet.balance == 0
    
    def test_refund_nonexistent_transaction(self, adapter):
        """Test refunding non-existent transaction."""
        with pytest.raises(ValueError, match="not found"):
            adapter.refund("nonexistent-txn-id")
    
    def test_refund_not_completed(self, adapter, funded_agents):
        """Test refunding transaction that's not COMPLETED."""
        alice, bob = funded_agents
        
        # Authorize (not completed)
        txn = adapter.authorize("alice", "bob", 1000)
        
        # Try to refund
        with pytest.raises(ValueError, match="cannot refund"):
            adapter.refund(txn.transaction_id)
    
    def test_refund_partial_not_supported(self, adapter, funded_agents):
        """Test that partial refunds are not supported."""
        alice, bob = funded_agents
        
        # Transfer
        txn = adapter.transfer("alice", "bob", 3000)
        
        # Try partial refund
        with pytest.raises(ValueError, match="Partial refunds not supported"):
            adapter.refund(txn.transaction_id, amount=1000)
    
    def test_get_transaction(self, adapter, funded_agents):
        """Test retrieving a transaction by ID."""
        alice, bob = funded_agents
        
        # Create transaction
        txn = adapter.transfer("alice", "bob", 1000)
        
        # Retrieve it
        retrieved = adapter.get_transaction(txn.transaction_id)
        
        assert retrieved is not None
        assert retrieved.transaction_id == txn.transaction_id
        assert retrieved.amount == 1000
        
        # Non-existent transaction
        assert adapter.get_transaction("nonexistent") is None
    
    def test_validate_accounts(self, adapter, funded_agents):
        """Test account validation."""
        alice, bob = funded_agents
        
        # Both exist
        assert adapter.validate_accounts("alice", "bob") is True
        
        # Sender doesn't exist
        assert adapter.validate_accounts("nonexistent", "bob") is False
        
        # Recipient doesn't exist
        assert adapter.validate_accounts("alice", "nonexistent") is False
        
        # Neither exist
        assert adapter.validate_accounts("fake1", "fake2") is False
    
    def test_clear(self, adapter, funded_agents):
        """Test clearing adapter state."""
        alice, bob = funded_agents
        
        # Create some transactions
        txn1 = adapter.transfer("alice", "bob", 1000)
        txn2 = adapter.authorize("alice", "bob", 2000)
        
        assert adapter.get_transaction(txn1.transaction_id) is not None
        assert adapter.get_transaction(txn2.transaction_id) is not None
        
        # Clear
        adapter.clear()
        
        # Transactions should be gone
        assert adapter.get_transaction(txn1.transaction_id) is None
        assert adapter.get_transaction(txn2.transaction_id) is None


class TestAuthorizeCaptureFlow:
    """Test the full authorize-capture flow."""
    
    def test_authorize_capture_flow(self, adapter, funded_agents, registry):
        """Test complete authorize -> capture flow."""
        alice, bob = funded_agents
        
        # Step 1: Authorize
        auth_txn = adapter.authorize(
            from_account="alice",
            to_account="bob",
            amount=5000,
            metadata={"memo": "Hold for order"}
        )
        
        assert auth_txn.status == TransactionStatus.AUTHORIZED
        
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 5000
        assert alice.wallet.hold == 5000
        
        # Step 2: Capture
        capture_txn = adapter.capture(auth_txn.transaction_id)
        
        assert capture_txn.status == TransactionStatus.CAPTURED
        
        # Verify final state
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 5000
        assert alice.wallet.hold == 0
        assert bob.wallet.balance == 5000
    
    def test_authorize_void_flow(self, adapter, funded_agents, registry):
        """Test complete authorize -> void flow."""
        alice, bob = funded_agents
        
        # Step 1: Authorize
        auth_txn = adapter.authorize(
            from_account="alice",
            to_account="bob",
            amount=5000
        )
        
        assert auth_txn.status == TransactionStatus.AUTHORIZED
        
        # Step 2: Void
        void_txn = adapter.void(auth_txn.transaction_id)
        
        assert void_txn.status == TransactionStatus.CANCELLED
        
        # Verify final state - funds returned
        alice = registry.get_agent("alice")
        assert alice.wallet.balance == 10000
        assert alice.wallet.hold == 0


class TestTransferRefundFlow:
    """Test the transfer-refund flow."""
    
    def test_transfer_refund_flow(self, adapter, funded_agents, registry):
        """Test complete transfer -> refund flow."""
        alice, bob = funded_agents
        
        # Step 1: Transfer
        transfer_txn = adapter.transfer(
            from_account="alice",
            to_account="bob",
            amount=6000
        )
        
        assert transfer_txn.status == TransactionStatus.COMPLETED
        
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 4000
        assert bob.wallet.balance == 6000
        
        # Step 2: Refund
        refund_txn = adapter.refund(
            transfer_txn.transaction_id,
            reason="Cancelled order"
        )
        
        assert refund_txn.status == TransactionStatus.COMPLETED
        assert transfer_txn.status == TransactionStatus.REFUNDED
        
        # Verify final state - back to original
        alice = registry.get_agent("alice")
        bob = registry.get_agent("bob")
        assert alice.wallet.balance == 10000
        assert bob.wallet.balance == 0
