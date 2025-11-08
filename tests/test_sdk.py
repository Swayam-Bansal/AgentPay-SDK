"""Tests for the high-level AgentPaySDK."""

import pytest
from agentpay import AgentPaySDK, Policy, PaymentStatus, EscrowStatus


@pytest.fixture
def sdk():
    """Create a fresh SDK instance."""
    return AgentPaySDK()


class TestAgentManagement:
    """Tests for agent management operations."""
    
    def test_register_agent_simple(self, sdk):
        """Test simple agent registration."""
        agent = sdk.register_agent("test-agent")
        
        assert agent.agent_id == "test-agent"
        assert agent.wallet.balance == 0
        assert agent.policy.paused is False
    
    def test_register_agent_with_metadata(self, sdk):
        """Test agent registration with metadata."""
        agent = sdk.register_agent(
            "alice",
            metadata={"name": "Alice", "email": "alice@example.com"}
        )
        
        assert agent.agent_id == "alice"
        assert agent.metadata["name"] == "Alice"
        assert agent.display_name == "Alice"
    
    def test_register_agent_with_policy(self, sdk):
        """Test agent registration with custom policy."""
        policy = Policy(
            max_per_transaction=5000,
            allowlist={"bob", "charlie"}
        )
        agent = sdk.register_agent("restricted", policy=policy)
        
        assert agent.policy.max_per_transaction == 5000
        assert "bob" in agent.policy.allowlist
    
    def test_duplicate_registration_fails(self, sdk):
        """Test that duplicate agent IDs are rejected."""
        sdk.register_agent("test-agent")
        
        with pytest.raises(ValueError, match="already exists"):
            sdk.register_agent("test-agent")
    
    def test_get_agent(self, sdk):
        """Test getting an agent by ID."""
        sdk.register_agent("test-agent")
        
        agent = sdk.get_agent("test-agent")
        assert agent is not None
        assert agent.agent_id == "test-agent"
        
        # Non-existent agent
        assert sdk.get_agent("nonexistent") is None
    
    def test_agent_exists(self, sdk):
        """Test checking agent existence."""
        sdk.register_agent("test-agent")
        
        assert sdk.agent_exists("test-agent") is True
        assert sdk.agent_exists("nonexistent") is False
    
    def test_list_agents(self, sdk):
        """Test listing all agents."""
        sdk.register_agent("agent-1")
        sdk.register_agent("agent-2")
        sdk.register_agent("agent-3")
        
        agents = sdk.list_agents()
        assert len(agents) == 3
        agent_ids = {a.agent_id for a in agents}
        assert agent_ids == {"agent-1", "agent-2", "agent-3"}
    
    def test_update_agent_policy(self, sdk):
        """Test updating an agent's policy."""
        sdk.register_agent("test-agent")
        
        new_policy = Policy(max_per_transaction=10000)
        updated = sdk.update_agent_policy("test-agent", new_policy)
        
        assert updated.policy.max_per_transaction == 10000
    
    def test_pause_unpause_agent(self, sdk):
        """Test pausing and unpausing an agent."""
        sdk.register_agent("test-agent")
        
        # Pause
        paused = sdk.pause_agent("test-agent")
        assert paused.policy.paused is True
        
        # Unpause
        unpaused = sdk.unpause_agent("test-agent")
        assert unpaused.policy.paused is False


class TestWalletOperations:
    """Tests for wallet operations."""
    
    def test_fund_agent(self, sdk):
        """Test funding an agent."""
        sdk.register_agent("alice")
        
        entry = sdk.fund_agent("alice", 10000, memo="Initial funding")
        
        assert entry.agent_id == "alice"
        assert entry.delta_amount == 10000
        assert entry.balance_after == 10000
    
    def test_get_balance(self, sdk):
        """Test getting agent balance."""
        sdk.register_agent("alice")
        sdk.fund_agent("alice", 10000)
        
        balance = sdk.get_balance("alice")
        assert balance == 10000
    
    def test_get_balance_nonexistent_agent(self, sdk):
        """Test getting balance for non-existent agent."""
        with pytest.raises(ValueError, match="not found"):
            sdk.get_balance("nonexistent")
    
    def test_get_wallet(self, sdk):
        """Test getting complete wallet info."""
        sdk.register_agent("alice")
        sdk.fund_agent("alice", 10000)
        
        wallet = sdk.get_wallet("alice")
        assert wallet.balance == 10000
        assert wallet.hold == 0
        assert wallet.total == 10000


class TestPaymentOperations:
    """Tests for payment operations."""
    
    def test_simple_payment(self, sdk):
        """Test simple payment between agents."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        result = sdk.pay(
            from_agent="alice",
            to_agent="bob",
            amount=5000,
            memo="Test payment"
        )
        
        assert result.success is True
        assert result.payment_intent.status == PaymentStatus.COMPLETED
        assert result.payment_intent.amount == 5000
        
        # Check balances
        assert sdk.get_balance("alice") == 5000
        assert sdk.get_balance("bob") == 5000
    
    def test_payment_insufficient_funds(self, sdk):
        """Test payment with insufficient funds."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 1000)
        
        result = sdk.pay("alice", "bob", 5000)
        
        assert result.success is False
        assert result.error_code == "INSUFFICIENT_FUNDS"
    
    def test_payment_with_idempotency(self, sdk):
        """Test idempotent payments."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        # First payment
        result1 = sdk.pay(
            from_agent="alice",
            to_agent="bob",
            amount=1000,
            idempotency_key="unique-key-123"
        )
        assert result1.success is True
        
        # Second payment with same key
        result2 = sdk.pay(
            from_agent="alice",
            to_agent="bob",
            amount=1000,
            idempotency_key="unique-key-123"
        )
        assert result2.success is True
        assert result2.payment_intent.intent_id == result1.payment_intent.intent_id
        
        # Balance should only be deducted once
        assert sdk.get_balance("alice") == 9000
    
    def test_get_payment_status(self, sdk):
        """Test getting payment status."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        result = sdk.pay("alice", "bob", 1000)
        intent_id = result.payment_intent.intent_id
        
        # Retrieve status
        intent = sdk.get_payment_status(intent_id)
        assert intent is not None
        assert intent.status == PaymentStatus.COMPLETED


class TestEscrowOperations:
    """Tests for escrow operations."""
    
    def test_create_escrow(self, sdk):
        """Test creating an escrow."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        result = sdk.create_escrow(
            from_agent="alice",
            to_agent="bob",
            amount=5000,
            memo="Milestone payment"
        )
        
        assert result.success is True
        assert result.escrow.status == EscrowStatus.LOCKED
        assert result.escrow.amount == 5000
        
        # Check Alice's wallet
        wallet = sdk.get_wallet("alice")
        assert wallet.balance == 5000
        assert wallet.hold == 5000
    
    def test_release_escrow(self, sdk):
        """Test releasing an escrow."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        # Create escrow
        create_result = sdk.create_escrow("alice", "bob", 5000)
        escrow_id = create_result.escrow.escrow_id
        
        # Release it
        release_result = sdk.release_escrow(escrow_id)
        
        assert release_result.success is True
        assert release_result.escrow.status == EscrowStatus.RELEASED
        
        # Check balances
        assert sdk.get_balance("alice") == 5000
        assert sdk.get_balance("bob") == 5000
        assert sdk.get_wallet("alice").hold == 0
    
    def test_cancel_escrow(self, sdk):
        """Test cancelling an escrow."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        # Create escrow
        create_result = sdk.create_escrow("alice", "bob", 5000)
        escrow_id = create_result.escrow.escrow_id
        
        # Cancel it
        cancel_result = sdk.cancel_escrow(escrow_id)
        
        assert cancel_result.success is True
        assert cancel_result.escrow.status == EscrowStatus.CANCELLED
        
        # Funds returned to Alice
        assert sdk.get_balance("alice") == 10000
        assert sdk.get_wallet("alice").hold == 0
    
    def test_get_escrow(self, sdk):
        """Test getting an escrow by ID."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        create_result = sdk.create_escrow("alice", "bob", 5000)
        escrow_id = create_result.escrow.escrow_id
        
        escrow = sdk.get_escrow(escrow_id)
        assert escrow is not None
        assert escrow.amount == 5000
        assert escrow.from_agent_id == "alice"
    
    def test_list_agent_escrows(self, sdk):
        """Test listing escrows for an agent."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.register_agent("charlie")
        sdk.fund_agent("alice", 10000)
        
        # Create escrows
        sdk.create_escrow("alice", "bob", 2000)
        sdk.create_escrow("alice", "charlie", 3000)
        
        # List by payer
        payer_escrows = sdk.list_agent_escrows("alice", role="payer")
        assert len(payer_escrows) == 2
        
        # List by recipient
        recipient_escrows = sdk.list_agent_escrows("bob", role="recipient")
        assert len(recipient_escrows) == 1
        
        # List all
        all_escrows = sdk.list_agent_escrows("alice", role="all")
        assert len(all_escrows) == 2


class TestTransactionHistory:
    """Tests for transaction history."""
    
    def test_get_transaction_history(self, sdk):
        """Test getting agent transaction history."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        
        # Create transactions
        sdk.fund_agent("alice", 10000)
        sdk.pay("alice", "bob", 3000)
        
        # Check Alice's history
        alice_history = sdk.get_transaction_history("alice")
        assert len(alice_history) == 2  # Top-up + payment
        
        # Check Bob's history
        bob_history = sdk.get_transaction_history("bob")
        assert len(bob_history) == 1  # Payment received
    
    def test_get_transaction_by_reference(self, sdk):
        """Test getting transaction by reference ID."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        # Make payment
        result = sdk.pay("alice", "bob", 5000)
        payment_id = result.payment_intent.intent_id
        
        # Get transaction entries
        entries = sdk.get_transaction_by_reference(payment_id)
        assert len(entries) == 2  # Debit + Credit
        
        # Verify double-entry
        total = sum(e.delta_amount for e in entries)
        assert total == 0


class TestEndToEndScenarios:
    """End-to-end usage scenarios."""
    
    def test_complete_workflow(self, sdk):
        """Test complete agent payment workflow."""
        # 1. Register agents
        alice = sdk.register_agent("alice", metadata={"name": "Alice"})
        bob = sdk.register_agent("bob", metadata={"name": "Bob"})
        
        assert alice.display_name == "Alice"
        assert bob.agent_id == "bob"
        
        # 2. Fund Alice
        entry = sdk.fund_agent("alice", 10000, memo="Initial funding")
        assert entry.balance_after == 10000
        
        # 3. Make a payment
        payment_result = sdk.pay(
            from_agent="alice",
            to_agent="bob",
            amount=3000,
            memo="Consulting services"
        )
        assert payment_result.success is True
        
        # 4. Check balances
        assert sdk.get_balance("alice") == 7000
        assert sdk.get_balance("bob") == 3000
        
        # 5. Create escrow
        escrow_result = sdk.create_escrow("alice", "bob", 2000, memo="Milestone 1")
        assert escrow_result.success is True
        escrow_id = escrow_result.escrow.escrow_id
        
        # 6. Check Alice's wallet state
        wallet = sdk.get_wallet("alice")
        assert wallet.balance == 5000
        assert wallet.hold == 2000
        
        # 7. Release escrow
        release_result = sdk.release_escrow(escrow_id)
        assert release_result.success is True
        
        # 8. Final balances
        assert sdk.get_balance("alice") == 5000
        assert sdk.get_balance("bob") == 5000
        
        # 9. Check transaction history
        alice_history = sdk.get_transaction_history("alice")
        assert len(alice_history) == 4  # topup, payment, escrow_lock, escrow_release
    
    def test_policy_enforcement(self, sdk):
        """Test that policies are enforced."""
        # Create agent with restrictive policy
        policy = Policy(
            max_per_transaction=1000,
            allowlist={"bob"}
        )
        sdk.register_agent("alice", policy=policy)
        sdk.register_agent("bob")
        sdk.register_agent("charlie")
        sdk.fund_agent("alice", 10000)
        
        # Payment within limit to allowed recipient - succeeds
        result1 = sdk.pay("alice", "bob", 500)
        assert result1.success is True
        
        # Payment exceeds limit - fails
        result2 = sdk.pay("alice", "bob", 2000)
        assert result2.success is False
        assert result2.error_code == "AMOUNT_EXCEEDS_LIMIT"
        
        # Payment to non-allowed recipient - fails
        result3 = sdk.pay("alice", "charlie", 500)
        assert result3.success is False
        assert result3.error_code == "RECIPIENT_NOT_ALLOWED"
        
        # Pause agent
        sdk.pause_agent("alice")
        result4 = sdk.pay("alice", "bob", 100)
        assert result4.success is False
        assert result4.error_code == "AGENT_PAUSED"
    
    def test_mixed_operations(self, sdk):
        """Test mixing different operation types."""
        sdk.register_agent("alice")
        sdk.register_agent("bob")
        sdk.fund_agent("alice", 10000)
        
        # Regular payment
        sdk.pay("alice", "bob", 2000)
        
        # Create multiple escrows
        escrow1 = sdk.create_escrow("alice", "bob", 1000)
        escrow2 = sdk.create_escrow("alice", "bob", 1500)
        
        # Release one, cancel another
        sdk.release_escrow(escrow1.escrow.escrow_id)
        sdk.cancel_escrow(escrow2.escrow.escrow_id)
        
        # Another payment
        sdk.pay("alice", "bob", 500)
        
        # Check final state
        alice_balance = sdk.get_balance("alice")
        bob_balance = sdk.get_balance("bob")
        
        # Alice: 10000 - 2000 (pay) - 1000 (escrow released) - 500 (pay) = 6500
        # (escrow2 was cancelled, so funds returned)
        assert alice_balance == 6500
        
        # Bob: 2000 + 1000 + 500 = 3500
        assert bob_balance == 3500


class TestUtilities:
    """Tests for utility methods."""
    
    def test_clear_all(self, sdk):
        """Test clearing all data."""
        sdk.register_agent("alice")
        sdk.fund_agent("alice", 10000)
        
        sdk.clear_all()
        
        # Everything should be gone
        assert len(sdk.list_agents()) == 0
        assert len(sdk.ledger.get_all_entries()) == 0
