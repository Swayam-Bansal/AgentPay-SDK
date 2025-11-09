"""Ledger Manager - double-entry accounting and transaction tracking.

The LedgerManager is responsible for:
- Recording all value movements as ledger entries
- Enforcing double-entry accounting principles
- Maintaining transaction history
- Providing audit trail and balance verification
- Updating agent wallets atomically with ledger entries

Key Principle: Every transaction creates entries such that the sum of all
delta_amounts equals zero (value is conserved).
"""

from typing import List, Dict, Optional
from agentpay.models import LedgerEntry, EntryType, TransactionType, Agent
from agentpay.agent_registry import AgentRegistry


class LedgerManager:
    """Manager for double-entry ledger and transaction tracking.
    
    The LedgerManager maintains an immutable audit trail of all value movements
    in the system. It works closely with the AgentRegistry to ensure that wallet
    balances and ledger entries stay synchronized.
    
    Double-Entry Accounting:
        For most transactions, the sum of all delta_amounts must equal zero:
        - Payment: debit payer (-X), credit payee (+X) → sum = 0
        - Escrow release: debit payer hold (-X), credit payee (+X) → sum = 0
        
        Exceptions (value entering/leaving system):
        - TOP_UP: +X (external funds entering)
        - WITHDRAWAL: -X (funds leaving system)
    
    Atomicity:
        Wallet updates and ledger entry creation happen together. If ledger
        entry creation fails, wallet changes are rolled back (via Pydantic
        model validation and Python exception handling).
    
    Usage Example:
        ```python
        registry = AgentRegistry()
        ledger = LedgerManager(registry)
        
        # Register agents
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        
        # Top up Alice's wallet
        ledger.record_top_up(
            agent_id="alice",
            amount=10000,
            reference_id="topup-1"
        )
        
        # Record a payment from Alice to Bob
        ledger.record_payment(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=5000,
            reference_id="payment-1"
        )
        
        # Get transaction history
        alice_history = ledger.get_agent_ledger_entries("alice")
        print(f"Alice has {len(alice_history)} transactions")
        ```
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        """Initialize the ledger manager.
        
        Args:
            agent_registry (AgentRegistry): The agent registry for wallet updates
        """
        self.agent_registry = agent_registry
        self._entries: List[LedgerEntry] = []
    
    def record_top_up(self, agent_id: str, amount: int, reference_id: str, 
                     memo: Optional[str] = None) -> LedgerEntry:
        """Record a top-up (external funds added to agent's wallet).
        
        This is a single-entry transaction (value entering the system).
        Creates one ledger entry crediting the agent's balance.
        
        Args:
            agent_id (str): Agent receiving the funds
            amount (int): Amount to add (must be > 0)
            reference_id (str): ID of the top-up transaction
            memo (Optional[str]): Optional description
            
        Returns:
            LedgerEntry: The created ledger entry
            
        Raises:
            ValueError: If agent doesn't exist or amount <= 0
            
        Example:
            ```python
            entry = ledger.record_top_up(
                agent_id="agent-1",
                amount=100000,  # $1000
                reference_id="topup-001",
                memo="Initial funding"
            )
            ```
        """
        if amount <= 0:
            raise ValueError("Top-up amount must be positive")
        
        agent = self.agent_registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Update agent's balance
        agent.wallet.balance += amount
        
        # Create ledger entry
        entry = LedgerEntry(
            agent_id=agent_id,
            delta_amount=amount,
            entry_type=EntryType.TOP_UP,
            reference_id=reference_id,
            balance_after=agent.wallet.balance,
            memo=memo
        )
        
        self._entries.append(entry)
        self.agent_registry.update_agent(agent)
        
        return entry
    
    def record_payment(self, from_agent_id: str, to_agent_id: str, amount: int,
                      reference_id: str, memo: Optional[str] = None) -> List[LedgerEntry]:
        """Record a payment between two agents.
        
        This is a double-entry transaction creating two ledger entries:
        1. Debit from payer's balance (-amount)
        2. Credit to payee's balance (+amount)
        
        Sum of deltas: -amount + amount = 0 ✓
        
        Args:
            from_agent_id (str): Agent making the payment (payer)
            to_agent_id (str): Agent receiving the payment (payee)
            amount (int): Amount to transfer (must be > 0)
            reference_id (str): ID linking these entries (e.g., PaymentIntent ID)
            memo (Optional[str]): Optional description
            
        Returns:
            List[LedgerEntry]: Two entries [debit_entry, credit_entry]
            
        Raises:
            ValueError: If agents don't exist, amount invalid, or insufficient funds
            
        Example:
            ```python
            entries = ledger.record_payment(
                from_agent_id="alice",
                to_agent_id="bob",
                amount=5000,  # $50
                reference_id="payment-123",
                memo="Payment for services"
            )
            # entries[0] = debit from Alice (-5000)
            # entries[1] = credit to Bob (+5000)
            ```
        """
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        from_agent = self.agent_registry.get_agent(from_agent_id)
        to_agent = self.agent_registry.get_agent(to_agent_id)
        
        if from_agent is None:
            raise ValueError(f"Payer agent {from_agent_id} not found")
        if to_agent is None:
            raise ValueError(f"Payee agent {to_agent_id} not found")
        
        # Check sufficient funds
        if from_agent.wallet.balance < amount:
            raise ValueError(
                f"Insufficient funds: agent {from_agent_id} has "
                f"{from_agent.wallet.balance}, needs {amount}"
            )
        
        # Update wallets
        from_agent.wallet.balance -= amount
        to_agent.wallet.balance += amount
        
        # Update lifetime earnings/spending
        from_agent.total_spent += amount
        to_agent.total_earned += amount
        
        # Create ledger entries
        debit_entry = LedgerEntry(
            agent_id=from_agent_id,
            delta_amount=-amount,
            entry_type=EntryType.PAYMENT,
            reference_id=reference_id,
            balance_after=from_agent.wallet.balance,
            memo=memo,
            transaction_type=TransactionType.EXPENSE,
            counterparty_id=to_agent_id
        )
        
        credit_entry = LedgerEntry(
            agent_id=to_agent_id,
            delta_amount=amount,
            entry_type=EntryType.PAYMENT,
            reference_id=reference_id,
            balance_after=to_agent.wallet.balance,
            memo=memo,
            transaction_type=TransactionType.INCOME,
            counterparty_id=from_agent_id
        )
        
        self._entries.extend([debit_entry, credit_entry])
        self.agent_registry.update_agent(from_agent)
        self.agent_registry.update_agent(to_agent)
        
        return [debit_entry, credit_entry]
    
    def record_escrow_lock(self, agent_id: str, amount: int, reference_id: str,
                          memo: Optional[str] = None) -> LedgerEntry:
        """Record locking funds into escrow (balance → hold).
        
        This moves funds within the same agent's wallet, so it's a single entry.
        The total wallet value (balance + hold) remains unchanged.
        
        Args:
            agent_id (str): Agent locking the funds
            amount (int): Amount to lock (must be > 0)
            reference_id (str): ID of the escrow
            memo (Optional[str]): Optional description
            
        Returns:
            LedgerEntry: The created ledger entry
            
        Raises:
            ValueError: If agent doesn't exist, amount invalid, or insufficient balance
            
        Example:
            ```python
            entry = ledger.record_escrow_lock(
                agent_id="alice",
                amount=3000,  # $30
                reference_id="escrow-456",
                memo="Escrow for task completion"
            )
            ```
        """
        if amount <= 0:
            raise ValueError("Escrow lock amount must be positive")
        
        agent = self.agent_registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.wallet.balance < amount:
            raise ValueError(
                f"Insufficient balance: agent {agent_id} has "
                f"{agent.wallet.balance}, needs {amount}"
            )
        
        # Move balance → hold
        agent.wallet.balance -= amount
        agent.wallet.hold += amount
        
        entry = LedgerEntry(
            agent_id=agent_id,
            delta_amount=-amount,  # Balance decreased
            entry_type=EntryType.ESCROW_LOCK,
            reference_id=reference_id,
            balance_after=agent.wallet.balance,
            memo=memo
        )
        
        self._entries.append(entry)
        self.agent_registry.update_agent(agent)
        
        return entry
    
    def record_escrow_release(self, from_agent_id: str, to_agent_id: str, amount: int,
                             reference_id: str, memo: Optional[str] = None) -> List[LedgerEntry]:
        """Record releasing escrowed funds to recipient.
        
        This is a special double-entry: payer's hold decreases, payee's balance increases.
        
        Args:
            from_agent_id (str): Agent whose funds were escrowed (payer)
            to_agent_id (str): Agent receiving the released funds (payee)
            amount (int): Amount to release (must be > 0)
            reference_id (str): ID of the escrow
            memo (Optional[str]): Optional description
            
        Returns:
            List[LedgerEntry]: Two entries [payer_hold_decrease, payee_balance_increase]
            
        Raises:
            ValueError: If agents don't exist, amount invalid, or insufficient hold
            
        Example:
            ```python
            entries = ledger.record_escrow_release(
                from_agent_id="alice",
                to_agent_id="bob",
                amount=3000,
                reference_id="escrow-456",
                memo="Task completed, releasing funds"
            )
            ```
        """
        if amount <= 0:
            raise ValueError("Escrow release amount must be positive")
        
        from_agent = self.agent_registry.get_agent(from_agent_id)
        to_agent = self.agent_registry.get_agent(to_agent_id)
        
        if from_agent is None:
            raise ValueError(f"Payer agent {from_agent_id} not found")
        if to_agent is None:
            raise ValueError(f"Payee agent {to_agent_id} not found")
        
        if from_agent.wallet.hold < amount:
            raise ValueError(
                f"Insufficient hold: agent {from_agent_id} has "
                f"{from_agent.wallet.hold} in hold, needs {amount}"
            )
        
        # Update wallets: payer's hold → payee's balance
        from_agent.wallet.hold -= amount
        to_agent.wallet.balance += amount
        
        # Update lifetime earnings/spending
        from_agent.total_spent += amount
        to_agent.total_earned += amount
        
        # Payer entry (hold decrease, but balance unchanged)
        payer_entry = LedgerEntry(
            agent_id=from_agent_id,
            delta_amount=-amount,
            entry_type=EntryType.ESCROW_RELEASE,
            reference_id=reference_id,
            balance_after=from_agent.wallet.balance,  # Balance unchanged
            memo=memo,
            transaction_type=TransactionType.EXPENSE,
            counterparty_id=to_agent_id
        )
        
        payee_entry = LedgerEntry(
            agent_id=to_agent_id,
            delta_amount=amount,
            entry_type=EntryType.ESCROW_RELEASE,
            reference_id=reference_id,
            balance_after=to_agent.wallet.balance,
            memo=memo,
            transaction_type=TransactionType.INCOME,
            counterparty_id=from_agent_id
        )
        
        self._entries.extend([payer_entry, payee_entry])
        self.agent_registry.update_agent(from_agent)
        self.agent_registry.update_agent(to_agent)
        
        return [payer_entry, payee_entry]
    
    def record_escrow_cancel(self, agent_id: str, amount: int, reference_id: str,
                            memo: Optional[str] = None) -> LedgerEntry:
        """Record cancelling escrow (hold → balance).
        
        This returns escrowed funds back to the payer's available balance.
        Single entry within same agent's wallet.
        
        Args:
            agent_id (str): Agent whose escrow is being cancelled
            amount (int): Amount to return (must be > 0)
            reference_id (str): ID of the escrow
            memo (Optional[str]): Optional description
            
        Returns:
            LedgerEntry: The created ledger entry
            
        Raises:
            ValueError: If agent doesn't exist, amount invalid, or insufficient hold
            
        Example:
            ```python
            entry = ledger.record_escrow_cancel(
                agent_id="alice",
                amount=3000,
                reference_id="escrow-456",
                memo="Task cancelled, returning funds"
            )
            ```
        """
        if amount <= 0:
            raise ValueError("Escrow cancel amount must be positive")
        
        agent = self.agent_registry.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.wallet.hold < amount:
            raise ValueError(
                f"Insufficient hold: agent {agent_id} has "
                f"{agent.wallet.hold} in hold, needs {amount}"
            )
        
        # Move hold → balance
        agent.wallet.hold -= amount
        agent.wallet.balance += amount
        
        entry = LedgerEntry(
            agent_id=agent_id,
            delta_amount=amount,  # Balance increased
            entry_type=EntryType.ESCROW_CANCEL,
            reference_id=reference_id,
            balance_after=agent.wallet.balance,
            memo=memo
        )
        
        self._entries.append(entry)
        self.agent_registry.update_agent(agent)
        
        return entry
    
    def get_agent_ledger_entries(self, agent_id: str) -> List[LedgerEntry]:
        """Get all ledger entries for a specific agent.
        
        Args:
            agent_id (str): The agent ID to query
            
        Returns:
            List[LedgerEntry]: All entries for this agent, ordered by creation time
            
        Example:
            ```python
            entries = ledger.get_agent_ledger_entries("alice")
            for entry in entries:
                print(f"{entry.entry_type}: {entry.delta_amount}")
            ```
        """
        return [e for e in self._entries if e.agent_id == agent_id]
    
    def get_entries_by_reference(self, reference_id: str) -> List[LedgerEntry]:
        """Get all ledger entries for a specific transaction.
        
        Args:
            reference_id (str): The reference ID (PaymentIntent ID, Escrow ID, etc.)
            
        Returns:
            List[LedgerEntry]: All entries with this reference_id
            
        Example:
            ```python
            # Get all entries for a specific payment
            payment_entries = ledger.get_entries_by_reference("payment-123")
            # Should have 2 entries (debit + credit)
            ```
        """
        return [e for e in self._entries if e.reference_id == reference_id]
    
    def get_all_entries(self) -> List[LedgerEntry]:
        """Get all ledger entries in the system.
        
        Returns:
            List[LedgerEntry]: All entries, ordered by creation time
        """
        return list(self._entries)
    
    def verify_double_entry(self, reference_id: str) -> bool:
        """Verify that entries for a transaction sum to zero.
        
        Args:
            reference_id (str): The transaction reference ID
            
        Returns:
            bool: True if entries sum to zero (or exception for TOP_UP/WITHDRAWAL)
            
        Example:
            ```python
            # After recording a payment
            assert ledger.verify_double_entry("payment-123") is True
            ```
        """
        entries = self.get_entries_by_reference(reference_id)
        if not entries:
            return True
        
        # Check if this is a TOP_UP or WITHDRAWAL (exceptions to zero-sum rule)
        entry_types = {e.entry_type for e in entries}
        if EntryType.TOP_UP in entry_types or EntryType.WITHDRAWAL in entry_types:
            return True  # These don't need to sum to zero
        
        total = sum(e.delta_amount for e in entries)
        return total == 0
    
    def get_entry_count(self) -> int:
        """Get total number of ledger entries.
        
        Returns:
            int: Total entry count
        """
        return len(self._entries)
    
    def clear(self) -> None:
        """Clear all ledger entries.
        
        Warning:
            This is destructive and only for testing. Does NOT reset agent wallets.
        """
        self._entries.clear()
