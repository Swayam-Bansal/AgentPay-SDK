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
from agentpay.http_client import HTTPClient


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
        # Local Mode (in-memory, for testing)
        sdk = AgentPaySDK()

        # Remote Mode (connected to backend API)
        sdk = AgentPaySDK(
            api_key="sk_test_abc123...",
            base_url="http://localhost:5001"
        )

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
        mode (str): 'local' or 'remote' - determines if using in-memory or API backend
        http_client (HTTPClient): HTTP client for remote API calls (remote mode only)
        registry (AgentRegistry): Internal agent registry (local mode only)
        ledger (LedgerManager): Internal ledger manager (local mode only)
        payment_engine (PaymentEngine): Payment execution engine (local mode only)
        escrow_manager (EscrowManager): Escrow management (local mode only)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:5001"
    ):
        """Initialize the AgentPay SDK.

        Args:
            api_key: API key for authentication. If provided, SDK runs in remote mode.
                    If None, SDK runs in local (in-memory) mode for testing.
            base_url: Base URL of the AgentPay API (only used in remote mode)

        Examples:
            # Local mode (for testing)
            sdk = AgentPaySDK()

            # Remote mode (production)
            sdk = AgentPaySDK(api_key="sk_test_abc123...")
        """
        if api_key:
            # Remote mode - connect to backend API
            self.mode = 'remote'
            self.http_client = HTTPClient(api_key, base_url)

            # Test connection
            try:
                ping_result = self.http_client.ping()
                print(f"✓ Connected to AgentPay API as {ping_result.get('authenticated_as', {}).get('key_name', 'unknown')}")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to AgentPay API: {e}")

            # Remote mode doesn't use local components
            self.registry = None
            self.ledger = None
            self.payment_engine = None
            self.escrow_manager = None
        else:
            # Local mode - in-memory operations
            self.mode = 'local'
            self.http_client = None

            # Create all internal components
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
    
    # ========== Agent-to-Agent Transfers & Earnings ==========
    
    def transfer_to_agent(
        self,
        from_agent_id: str,
        to_agent_id: str,
        amount: int,
        purpose: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Transfer funds from one agent to another (agent earns money).
        
        This is used for agent-to-agent service payments where one agent
        pays another for work completed. The receiving agent earns income.
        
        Args:
            from_agent_id: Paying agent's ID (the one spending)
            to_agent_id: Receiving agent's ID (the earner)
            amount: Amount in cents to transfer
            purpose: Reason for payment
            metadata: Additional context
        
        Returns:
            Dict with:
                - transaction_id: str
                - from_agent: str
                - to_agent: str
                - amount: int
                - status: str ("completed" or "failed")
                - timestamp: str
                - purpose: str
                - error: Optional[str] (if failed)
        
        Raises:
            ValueError: If agents don't exist or validation fails
        
        Example:
            ```python
            # Agent A pays Agent B for data analysis service
            result = sdk.transfer_to_agent(
                from_agent_id="agent-a",
                to_agent_id="agent-b",
                amount=5000,  # $50
                purpose="Data analysis service payment"
            )
            
            if result['status'] == 'completed':
                print(f"Payment successful: {result['transaction_id']}")
            else:
                print(f"Payment failed: {result['error']}")
            ```
        """
        from datetime import datetime, UTC
        
        if self.mode == 'remote':
            raise NotImplementedError(
                "transfer_to_agent() is only available in local mode currently"
            )
        
        transaction_id = f"transfer-{uuid4()}"
        
        try:
            # Use the existing payment engine which now tracks earnings
            result = self.pay(
                from_agent=from_agent_id,
                to_agent=to_agent_id,
                amount=amount,
                memo=purpose,
                metadata=metadata
            )
            
            if result.success:
                return {
                    'transaction_id': transaction_id,
                    'from_agent': from_agent_id,
                    'to_agent': to_agent_id,
                    'amount': amount,
                    'status': 'completed',
                    'timestamp': datetime.now(UTC).isoformat(),
                    'purpose': purpose
                }
            else:
                return {
                    'transaction_id': transaction_id,
                    'from_agent': from_agent_id,
                    'to_agent': to_agent_id,
                    'amount': amount,
                    'status': 'failed',
                    'timestamp': datetime.now(UTC).isoformat(),
                    'purpose': purpose,
                    'error': result.error_message
                }
        except Exception as e:
            return {
                'transaction_id': transaction_id,
                'from_agent': from_agent_id,
                'to_agent': to_agent_id,
                'amount': amount,
                'status': 'failed',
                'timestamp': datetime.now(UTC).isoformat(),
                'purpose': purpose,
                'error': str(e)
            }
    
    def get_agent_earnings(
        self,
        agent_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all income transactions for an agent (money they've earned).
        
        Args:
            agent_id: Agent ID to query
            start_date: Optional ISO format date to filter from
            end_date: Optional ISO format date to filter to
        
        Returns:
            Dict with:
                - agent_id: str
                - total_earned: int (lifetime earnings in cents)
                - transaction_count: int
                - transactions: List of income transactions
        
        Example:
            ```python
            earnings = sdk.get_agent_earnings("agent-b")
            print(f"Total earned: ${earnings['total_earned'] / 100}")
            print(f"Transactions: {earnings['transaction_count']}")
            
            for txn in earnings['transactions']:
                print(f"  ${txn['amount'] / 100} from {txn['from_agent']}")
                print(f"  Purpose: {txn['purpose']}")
            ```
        """
        if self.mode == 'remote':
            raise NotImplementedError(
                "get_agent_earnings() is only available in local mode currently"
            )
        
        from agentpay.models import TransactionType
        from datetime import datetime
        
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Get all ledger entries for this agent
        all_entries = self.get_transaction_history(agent_id)
        
        # Filter to only income transactions
        income_entries = [
            e for e in all_entries 
            if e.transaction_type == TransactionType.INCOME
        ]
        
        # Apply date filters if provided
        if start_date:
            start = datetime.fromisoformat(start_date)
            income_entries = [e for e in income_entries if e.created_at >= start]
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            income_entries = [e for e in income_entries if e.created_at <= end]
        
        # Format transactions
        transactions = []
        for entry in income_entries:
            transactions.append({
                'transaction_id': entry.reference_id,
                'from_agent': entry.counterparty_id,
                'amount': entry.delta_amount,
                'purpose': entry.memo or "Payment received",
                'timestamp': entry.created_at.isoformat(),
                'balance_after': entry.balance_after
            })
        
        return {
            'agent_id': agent_id,
            'total_earned': agent.total_earned,
            'transaction_count': len(transactions),
            'transactions': transactions
        }
    
    def get_agent_expenses(
        self,
        agent_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all expense transactions for an agent (money they've spent).
        
        Args:
            agent_id: Agent ID to query
            start_date: Optional ISO format date to filter from
            end_date: Optional ISO format date to filter to
        
        Returns:
            Dict with:
                - agent_id: str
                - total_spent: int (lifetime spending in cents)
                - transaction_count: int
                - transactions: List of expense transactions
        
        Example:
            ```python
            expenses = sdk.get_agent_expenses("agent-a")
            print(f"Total spent: ${expenses['total_spent'] / 100}")
            
            for txn in expenses['transactions']:
                print(f"  ${abs(txn['amount']) / 100} to {txn['to_agent']}")
                print(f"  Purpose: {txn['purpose']}")
            ```
        """
        if self.mode == 'remote':
            raise NotImplementedError(
                "get_agent_expenses() is only available in local mode currently"
            )
        
        from agentpay.models import TransactionType
        from datetime import datetime
        
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Get all ledger entries for this agent
        all_entries = self.get_transaction_history(agent_id)
        
        # Filter to only expense transactions
        expense_entries = [
            e for e in all_entries 
            if e.transaction_type == TransactionType.EXPENSE
        ]
        
        # Apply date filters if provided
        if start_date:
            start = datetime.fromisoformat(start_date)
            expense_entries = [e for e in expense_entries if e.created_at >= start]
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            expense_entries = [e for e in expense_entries if e.created_at <= end]
        
        # Format transactions
        transactions = []
        for entry in expense_entries:
            transactions.append({
                'transaction_id': entry.reference_id,
                'to_agent': entry.counterparty_id,
                'amount': entry.delta_amount,  # Will be negative
                'purpose': entry.memo or "Payment made",
                'timestamp': entry.created_at.isoformat(),
                'balance_after': entry.balance_after
            })
        
        return {
            'agent_id': agent_id,
            'total_spent': agent.total_spent,
            'transaction_count': len(transactions),
            'transactions': transactions
        }
    
    def get_agent_balance_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get current balance and earning/spending summary for an agent.
        
        Args:
            agent_id: Agent ID to query
        
        Returns:
            Dict with:
                - agent_id: str
                - current_balance: int (available balance)
                - total_earned: int (lifetime earnings)
                - total_spent: int (lifetime spending)
                - net_profit: int (earned - spent)
                - hold: int (funds in escrow)
                - total_wallet: int (balance + hold)
        
        Example:
            ```python
            summary = sdk.get_agent_balance_summary("agent-b")
            print(f"Balance: ${summary['current_balance'] / 100}")
            print(f"Total Earned: ${summary['total_earned'] / 100}")
            print(f"Total Spent: ${summary['total_spent'] / 100}")
            print(f"Net Profit: ${summary['net_profit'] / 100}")
            ```
        """
        if self.mode == 'remote':
            raise NotImplementedError(
                "get_agent_balance_summary() is only available in local mode currently"
            )
        
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        return {
            'agent_id': agent_id,
            'current_balance': agent.wallet.balance,
            'total_earned': agent.total_earned,
            'total_spent': agent.total_spent,
            'net_profit': agent.net_profit,
            'hold': agent.wallet.hold,
            'total_wallet': agent.wallet.total
        }
    
    # ========== Utility Methods ==========
    
    def clear_all(self) -> None:
        """Clear all data from the SDK.
        
        Warning:
            This is for testing only. Removes all agents, ledger entries,
            payments, and escrows.
        """
        if self.mode == 'remote':
            raise NotImplementedError("clear_all() is not supported in remote mode")
        
        self.registry.clear()
        self.ledger.clear()
        self.payment_engine.clear_idempotency_cache()
        self.escrow_manager.clear()

    # ========== Virtual Card Methods (Remote Mode Only) ==========

    def request_payment_card(
        self,
        amount: int,
        purpose: str,
        justification: str,
        agent_id: str = "sdk-agent",
        expected_roi: Optional[str] = None,
        urgency: str = "Medium",
        budget_remaining: Optional[int] = None
    ) -> Dict[str, Any]:
        """Request a one-time virtual card with quorum approval.
        
        This triggers the full approval workflow:
        1. Submit payment request
        2. 5-agent quorum votes on approval
        3. If approved: virtual card generated (5-minute expiry)
        4. If denied: rejection with reasoning
        
        Args:
            amount: Card limit (in cents, e.g., 10000 = $100)
            purpose: What the card is for (e.g., "OpenAI API Credits")
            justification: Detailed explanation for the request
            agent_id: ID of requesting agent (default: "sdk-agent")
            expected_roi: Expected return on investment
            urgency: "Low", "Medium", or "High"
            budget_remaining: Optional budget context
        
        Returns:
            Dict with:
                - approved: bool
                - card: Dict with card details (if approved)
                - denial_reason: str (if denied)
                - consensus_result: Dict with voting details
                - transaction_id: str
        
        Raises:
            NotImplementedError: If called in local mode
            ConnectionError: If API request fails
        
        Example:
            ```python
            sdk = AgentPaySDK(api_key="sk_test_abc...")
            
            result = sdk.request_payment_card(
                amount=10000,  # $100
                purpose="OpenAI API Credits",
                justification="Need GPT-4 for Q4 ad campaign",
                expected_roi="$5K revenue from improved ads",
                urgency="High"
            )
            
            if result['approved']:
                card = result['card']
                print(f"💳 Card: {card['card_number']}")
                print(f"   CVV: {card['cvv']}")
                print(f"   Expires: {card['expires_at']}")
            else:
                print(f"❌ Denied: {result['denial_reason']}")
            ```
        """
        if self.mode != 'remote':
            raise NotImplementedError(
                "request_payment_card() is only available in remote mode. "
                "Initialize SDK with api_key to use this feature."
            )
        
        return self.http_client.request_payment_card(
            amount=amount,
            purpose=purpose,
            justification=justification,
            agent_id=agent_id,
            expected_roi=expected_roi,
            urgency=urgency,
            budget_remaining=budget_remaining
        )
    
    def get_card_details(self, card_id: str) -> Dict[str, Any]:
        """Get details of a virtual card.
        
        Args:
            card_id: ID of the card
        
        Returns:
            Dict with complete card details
        
        Raises:
            NotImplementedError: If called in local mode
        
        Example:
            ```python
            card = sdk.get_card_details("card-123")
            print(f"Status: {card['status']}")
            print(f"Limit: ${card['amount_limit'] / 100}")
            ```
        """
        if self.mode != 'remote':
            raise NotImplementedError(
                "get_card_details() is only available in remote mode"
            )
        
        return self.http_client.get_card_details(card_id)
    
    def cancel_card(self, card_id: str) -> bool:
        """Cancel a virtual card.
        
        Args:
            card_id: ID of the card to cancel
        
        Returns:
            True if successful
        
        Raises:
            NotImplementedError: If called in local mode
        
        Example:
            ```python
            success = sdk.cancel_card("card-123")
            if success:
                print("Card cancelled")
            ```
        """
        if self.mode != 'remote':
            raise NotImplementedError(
                "cancel_card() is only available in remote mode"
            )
        
        return self.http_client.cancel_card(card_id)
    
    def charge_card(
        self,
        card_number: str,
        cvv: str,
        expiry_date: str,
        amount: int,
        merchant_name: str
    ) -> Dict[str, Any]:
        """Charge a virtual card at a mock merchant.
        
        This simulates making a purchase with the virtual card.
        The card will be marked as "used" after a successful charge.
        
        Args:
            card_number: 16-digit card number
            cvv: 3-digit CVV
            expiry_date: Expiry in MM/YY format
            amount: Amount to charge (in cents)
            merchant_name: Name of merchant (e.g., "OpenAI API Credits")
        
        Returns:
            Dict with:
                - success: bool
                - transaction_id: str (if successful)
                - error: str (if failed)
        
        Raises:
            NotImplementedError: If called in local mode
        
        Example:
            ```python
            result = sdk.charge_card(
                card_number="4242424242424242",
                cvv="123",
                expiry_date="12/25",
                amount=10000,
                merchant_name="OpenAI API Credits"
            )
            
            if result['success']:
                print(f"✓ Charge successful: {result['transaction_id']}")
            else:
                print(f"✗ Charge failed: {result['error']}")
            ```
        """
        if self.mode != 'remote':
            raise NotImplementedError(
                "charge_card() is only available in remote mode"
            )
        
        return self.http_client.charge_card(
            card_number=card_number,
            cvv=cvv,
            expiry_date=expiry_date,
            amount=amount,
            merchant_name=merchant_name
        )
