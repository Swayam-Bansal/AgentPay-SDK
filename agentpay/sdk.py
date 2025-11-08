"""AgentPay SDK - High-level API for AI agent payments.

This module provides the main SDK interface that wraps all internal components
into a simple, easy-to-use API for agent payment operations.
"""

from typing import Optional, List, Dict, Any
from uuid import uuid4

from agentpay.models import Agent, Wallet, Policy, PaymentIntent, PaymentStatus, LedgerEntry
from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager
from agentpay.payment_engine import PaymentEngine, PaymentResult
from agentpay.escrow_manager import EscrowManager, Escrow, EscrowResult, EscrowStatus


class AgentPaySDK:
    """High-level SDK for agent payment operations.
    
    The AgentPaySDK provides a simple, unified interface for all payment operations.
    It manages agents, wallets, payments, and escrows with an intuitive API.
    
    Key Features:
    - **Agent Management**: Register and manage agents
    - **Wallet Operations**: Fund agents and check balances
    - **Payments**: Simple payment execution with policy enforcement
    - **Escrows**: Create and manage escrow transactions
    - **Transaction History**: Query ledger entries
    
    Usage Example:
        ```python
        # Initialize SDK
        sdk = AgentPaySDK()
        
        # Register agents
        alice = sdk.register_agent("alice", metadata={"name": "Alice"})
        bob = sdk.register_agent("bob", metadata={"name": "Bob"})
        
        # Fund Alice
        sdk.fund_agent("alice", 10000)  # $100.00 in cents
        
        # Make a payment
        result = sdk.pay(
            from_agent="alice",
            to_agent="bob",
            amount=5000,
            memo="Payment for services"
        )
        
        if result.success:
            print(f"Payment complete! Bob received ${result.payment_intent.amount / 100}")
        
        # Create an escrow
        escrow_result = sdk.create_escrow(
            from_agent="alice",
            to_agent="bob",
            amount=3000,
            memo="Milestone payment"
        )
        
        # Later, release the escrow
        if escrow_result.success:
            sdk.release_escrow(escrow_result.escrow.escrow_id)
        
        # Check balances
        alice_balance = sdk.get_balance("alice")
        print(f"Alice balance: ${alice_balance / 100}")
        
        # View transaction history
        history = sdk.get_transaction_history("alice")
        for entry in history:
            print(f"{entry.entry_type}: {entry.delta_amount}")
        ```
    
    Attributes:
        registry (AgentRegistry): Internal agent registry
        ledger (LedgerManager): Internal ledger manager
        payment_engine (PaymentEngine): Payment execution engine
        escrow_manager (EscrowManager): Escrow management
    """
    
    def __init__(self):
        """Initialize the AgentPay SDK with default configuration.
        
        Creates all internal components (registry, ledger, payment engine, escrow manager)
        and wires them together.
        """
        self.registry = AgentRegistry()
        self.ledger = LedgerManager(self.registry)
        self.payment_engine = PaymentEngine(self.registry, self.ledger)
        self.escrow_manager = EscrowManager(self.registry, self.ledger)
    
    # ========== Agent Management ==========
    
    def register_agent(
        self,
        agent_id: str,
        policy: Optional[Policy] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """Register a new agent in the system.
        
        Args:
            agent_id (str): Unique identifier for the agent
            policy (Optional[Policy]): Payment policy (defaults to unrestricted)
            metadata (Optional[Dict]): Additional agent metadata
            
        Returns:
            Agent: The registered agent
            
        Raises:
            ValueError: If agent_id already exists
            
        Example:
            ```python
            # Simple registration
            agent = sdk.register_agent("agent-1")
            
            # With metadata
            alice = sdk.register_agent(
                "alice",
                metadata={"name": "Alice", "email": "alice@example.com"}
            )
            
            # With custom policy
            from agentpay.models import Policy
            policy = Policy(
                max_per_transaction=5000,
                allowlist={"bob", "charlie"}
            )
            agent = sdk.register_agent("restricted-agent", policy=policy)
            ```
        """
        agent = Agent(
            agent_id=agent_id,
            policy=policy or Policy(),
            metadata=metadata or {}
        )
        return self.registry.register_agent(agent)
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID.
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            Optional[Agent]: The agent if found, None otherwise
            
        Example:
            ```python
            agent = sdk.get_agent("alice")
            if agent:
                print(f"Agent: {agent.display_name}")
                print(f"Balance: {agent.wallet.balance}")
            ```
        """
        return self.registry.get_agent(agent_id)
    
    def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent exists.
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            bool: True if agent exists, False otherwise
        """
        return self.registry.agent_exists(agent_id)
    
    def list_agents(self) -> List[Agent]:
        """List all registered agents.
        
        Returns:
            List[Agent]: All agents in the system
        """
        return self.registry.list_agents()
    
    def update_agent_policy(
        self,
        agent_id: str,
        policy: Policy
    ) -> Agent:
        """Update an agent's payment policy.
        
        Args:
            agent_id (str): The agent ID
            policy (Policy): New policy to apply
            
        Returns:
            Agent: Updated agent
            
        Raises:
            ValueError: If agent not found
            
        Example:
            ```python
            from agentpay.models import Policy
            
            # Create new policy
            new_policy = Policy(
                max_per_transaction=10000,
                paused=False
            )
            
            # Update agent
            agent = sdk.update_agent_policy("alice", new_policy)
            ```
        """
        agent = self.registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent.policy = policy
        return self.registry.update_agent(agent)
    
    def pause_agent(self, agent_id: str) -> Agent:
        """Pause an agent (prevents all payments).
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            Agent: Updated agent
            
        Raises:
            ValueError: If agent not found
        """
        agent = self.registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent.policy.paused = True
        return self.registry.update_agent(agent)
    
    def unpause_agent(self, agent_id: str) -> Agent:
        """Unpause an agent (allows payments again).
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            Agent: Updated agent
            
        Raises:
            ValueError: If agent not found
        """
        agent = self.registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent.policy.paused = False
        return self.registry.update_agent(agent)
    
    # ========== Wallet Operations ==========
    
    def fund_agent(
        self,
        agent_id: str,
        amount: int,
        reference_id: Optional[str] = None,
        memo: Optional[str] = None
    ) -> LedgerEntry:
        """Add funds to an agent's wallet (top-up).
        
        Args:
            agent_id (str): The agent to fund
            amount (int): Amount to add (in smallest currency unit)
            reference_id (Optional[str]): External reference ID
            memo (Optional[str]): Description
            
        Returns:
            LedgerEntry: The ledger entry for this top-up
            
        Raises:
            ValueError: If agent not found or amount invalid
            
        Example:
            ```python
            # Fund agent with $100.00 (10000 cents)
            entry = sdk.fund_agent("alice", 10000, memo="Initial funding")
            print(f"New balance: ${entry.balance_after / 100}")
            ```
        """
        ref_id = reference_id or f"topup-{uuid4()}"
        return self.ledger.record_top_up(agent_id, amount, ref_id, memo)
    
    def get_balance(self, agent_id: str) -> int:
        """Get an agent's available balance.
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            int: Available balance (excluding holds)
            
        Raises:
            ValueError: If agent not found
            
        Example:
            ```python
            balance = sdk.get_balance("alice")
            print(f"Available: ${balance / 100:.2f}")
            ```
        """
        agent = self.registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        return agent.wallet.balance
    
    def get_wallet(self, agent_id: str) -> Wallet:
        """Get an agent's complete wallet (balance + hold).
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            Wallet: The agent's wallet
            
        Raises:
            ValueError: If agent not found
            
        Example:
            ```python
            wallet = sdk.get_wallet("alice")
            print(f"Balance: {wallet.balance}")
            print(f"Hold: {wallet.hold}")
            print(f"Total: {wallet.total}")
            ```
        """
        agent = self.registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        return agent.wallet
    
    # ========== Payment Operations ==========
    
    def pay(
        self,
        from_agent: str,
        to_agent: str,
        amount: int,
        memo: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """Execute a payment from one agent to another.
        
        Args:
            from_agent (str): Payer agent ID
            to_agent (str): Recipient agent ID
            amount (int): Amount to transfer
            memo (Optional[str]): Payment description
            idempotency_key (Optional[str]): Key for idempotent execution
            metadata (Optional[Dict]): Additional payment metadata
            
        Returns:
            PaymentResult: Result with success status and details
            
        Example:
            ```python
            result = sdk.pay(
                from_agent="alice",
                to_agent="bob",
                amount=5000,
                memo="Payment for consulting services"
            )
            
            if result.success:
                print("Payment successful!")
                print(f"Status: {result.payment_intent.status}")
            else:
                print(f"Payment failed: {result.error_message}")
            ```
        """
        intent = PaymentIntent(
            from_agent_id=from_agent,
            to_agent_id=to_agent,
            amount=amount,
            memo=memo,
            idempotency_key=idempotency_key,
            metadata=metadata or {}
        )
        return self.payment_engine.execute_payment(intent)
    
    def get_payment_status(self, intent_id: str) -> Optional[PaymentIntent]:
        """Get the status of a payment by intent ID.
        
        Args:
            intent_id (str): The payment intent ID
            
        Returns:
            Optional[PaymentIntent]: The payment intent if found
            
        Example:
            ```python
            result = sdk.pay("alice", "bob", 1000)
            intent_id = result.payment_intent.intent_id
            
            # Later, check status
            intent = sdk.get_payment_status(intent_id)
            print(f"Status: {intent.status}")
            ```
        """
        return self.payment_engine.get_payment_status(intent_id)
    
    # ========== Escrow Operations ==========
    
    def create_escrow(
        self,
        from_agent: str,
        to_agent: str,
        amount: int,
        memo: Optional[str] = None
    ) -> EscrowResult:
        """Create an escrow, locking funds from payer.
        
        Args:
            from_agent (str): Payer agent ID (funds will be locked)
            to_agent (str): Recipient agent ID (will receive if released)
            amount (int): Amount to lock
            memo (Optional[str]): Escrow description
            
        Returns:
            EscrowResult: Result with escrow details
            
        Example:
            ```python
            result = sdk.create_escrow(
                from_agent="alice",
                to_agent="bob",
                amount=5000,
                memo="Milestone 1 payment"
            )
            
            if result.success:
                escrow_id = result.escrow.escrow_id
                print(f"Escrow created: {escrow_id}")
            ```
        """
        return self.escrow_manager.create_escrow(from_agent, to_agent, amount, memo)
    
    def release_escrow(self, escrow_id: str) -> EscrowResult:
        """Release an escrow, transferring funds to recipient.
        
        Args:
            escrow_id (str): The escrow ID to release
            
        Returns:
            EscrowResult: Result with updated escrow
            
        Example:
            ```python
            result = sdk.release_escrow("escrow-123")
            if result.success:
                print("Funds released to recipient!")
            ```
        """
        return self.escrow_manager.release_escrow(escrow_id)
    
    def cancel_escrow(self, escrow_id: str) -> EscrowResult:
        """Cancel an escrow, returning funds to payer.
        
        Args:
            escrow_id (str): The escrow ID to cancel
            
        Returns:
            EscrowResult: Result with updated escrow
            
        Example:
            ```python
            result = sdk.cancel_escrow("escrow-123")
            if result.success:
                print("Escrow cancelled, funds returned!")
            ```
        """
        return self.escrow_manager.cancel_escrow(escrow_id)
    
    def get_escrow(self, escrow_id: str) -> Optional[Escrow]:
        """Get an escrow by ID.
        
        Args:
            escrow_id (str): The escrow ID
            
        Returns:
            Optional[Escrow]: The escrow if found
        """
        return self.escrow_manager.get_escrow(escrow_id)
    
    def list_agent_escrows(
        self,
        agent_id: str,
        role: str = "all"
    ) -> List[Escrow]:
        """List escrows for an agent.
        
        Args:
            agent_id (str): The agent ID
            role (str): Filter by role - "payer", "recipient", or "all"
            
        Returns:
            List[Escrow]: Escrows matching the criteria
            
        Example:
            ```python
            # Get all escrows where Alice is paying
            payer_escrows = sdk.list_agent_escrows("alice", role="payer")
            
            # Get all escrows where Alice is receiving
            recipient_escrows = sdk.list_agent_escrows("alice", role="recipient")
            
            # Get all escrows involving Alice
            all_escrows = sdk.list_agent_escrows("alice", role="all")
            ```
        """
        if role == "payer":
            return self.escrow_manager.list_escrows_by_payer(agent_id)
        elif role == "recipient":
            return self.escrow_manager.list_escrows_by_recipient(agent_id)
        else:
            payer = self.escrow_manager.list_escrows_by_payer(agent_id)
            recipient = self.escrow_manager.list_escrows_by_recipient(agent_id)
            # Combine and deduplicate
            all_escrows = {e.escrow_id: e for e in payer + recipient}
            return list(all_escrows.values())
    
    # ========== Transaction History ==========
    
    def get_transaction_history(self, agent_id: str) -> List[LedgerEntry]:
        """Get an agent's complete transaction history.
        
        Args:
            agent_id (str): The agent ID
            
        Returns:
            List[LedgerEntry]: All ledger entries for this agent
            
        Example:
            ```python
            history = sdk.get_transaction_history("alice")
            
            for entry in history:
                print(f"{entry.timestamp}: {entry.entry_type}")
                print(f"  Amount: {entry.delta_amount}")
                print(f"  Balance after: {entry.balance_after}")
            ```
        """
        return self.ledger.get_agent_ledger_entries(agent_id)
    
    def get_transaction_by_reference(self, reference_id: str) -> List[LedgerEntry]:
        """Get all ledger entries for a specific transaction.
        
        Args:
            reference_id (str): The transaction reference ID
            
        Returns:
            List[LedgerEntry]: All entries for this transaction
            
        Example:
            ```python
            # For a payment, this returns both debit and credit entries
            entries = sdk.get_transaction_by_reference("payment-123")
            for entry in entries:
                print(f"{entry.agent_id}: {entry.delta_amount}")
            ```
        """
        return self.ledger.get_entries_by_reference(reference_id)
    
    # ========== Utility Methods ==========
    
    def clear_all(self) -> None:
        """Clear all data from the SDK.
        
        Warning:
            This is for testing only. Removes all agents, ledger entries,
            payments, and escrows.
        """
        self.registry.clear()
        self.ledger.clear()
        self.payment_engine.clear_idempotency_cache()
        self.escrow_manager.clear()
