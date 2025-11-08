"""Internal Credits Rail Adapter.

Implements the RailAdapter interface using AgentPay's internal ledger system.
This is the default rail for pure internal credit transfers.
"""

from typing import Optional, Dict, Any

from agentpay.rails.base import RailAdapter, RailTransaction, TransactionStatus
from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager
from agentpay.escrow_manager import EscrowManager


class InternalCreditsAdapter(RailAdapter):
    """Rail adapter for internal credit transfers.
    
    This adapter uses AgentPay's internal ledger and escrow systems to
    implement the rail interface. It provides:
    
    - **transfer**: Direct payment via LedgerManager
    - **authorize**: Escrow lock via EscrowManager
    - **capture**: Escrow release
    - **void**: Escrow cancel
    - **refund**: Reverse payment
    
    This is the default rail and requires no external API keys or integrations.
    
    Usage Example:
        ```python
        from agentpay import AgentPaySDK
        from agentpay.rails import InternalCreditsAdapter
        
        sdk = AgentPaySDK()
        adapter = InternalCreditsAdapter(sdk.registry, sdk.ledger, sdk.escrow_manager)
        
        # Direct transfer
        txn = adapter.transfer("alice", "bob", 5000)
        print(f"Transfer: {txn.status}")
        
        # Two-phase transfer
        auth_txn = adapter.authorize("alice", "bob", 3000)
        capture_txn = adapter.capture(auth_txn.transaction_id)
        print(f"Captured: {capture_txn.status}")
        ```
    
    Attributes:
        agent_registry (AgentRegistry): Registry for agent lookup
        ledger_manager (LedgerManager): Ledger for recording transactions
        escrow_manager (EscrowManager): Escrow for authorize/capture flows
    """
    
    def __init__(
        self,
        agent_registry: AgentRegistry,
        ledger_manager: LedgerManager,
        escrow_manager: EscrowManager
    ):
        """Initialize the internal credits adapter.
        
        Args:
            agent_registry (AgentRegistry): Agent registry instance
            ledger_manager (LedgerManager): Ledger manager instance
            escrow_manager (EscrowManager): Escrow manager instance
        """
        self.agent_registry = agent_registry
        self.ledger_manager = ledger_manager
        self.escrow_manager = escrow_manager
        
        # Track transactions for lookup
        self._transactions: Dict[str, RailTransaction] = {}
        
        # Map transaction IDs to internal references (escrow IDs, etc.)
        self._internal_refs: Dict[str, str] = {}
    
    def get_name(self) -> str:
        """Get the name of this rail adapter.
        
        Returns:
            str: "internal_credits"
        """
        return "internal_credits"
    
    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: int,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RailTransaction:
        """Execute a direct transfer using the internal ledger.
        
        Args:
            from_account (str): Source agent ID
            to_account (str): Destination agent ID
            amount (int): Amount to transfer
            currency (str): Currency (ignored for internal credits)
            metadata (Optional[Dict]): Additional metadata
            
        Returns:
            RailTransaction: The completed transaction
            
        Raises:
            ValueError: If agents don't exist or insufficient funds
        """
        # Create transaction record
        txn = RailTransaction(
            rail_name=self.get_name(),
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            currency=currency,
            metadata=metadata or {}
        )
        
        try:
            # Validate accounts exist
            if not self.agent_registry.agent_exists(from_account):
                raise ValueError(f"Source account {from_account} not found")
            if not self.agent_registry.agent_exists(to_account):
                raise ValueError(f"Destination account {to_account} not found")
            
            # Execute payment via ledger
            entries = self.ledger_manager.record_payment(
                from_agent_id=from_account,
                to_agent_id=to_account,
                amount=amount,
                reference_id=txn.transaction_id,
                memo=metadata.get("memo") if metadata else None
            )
            
            # Mark as completed
            txn.mark_completed()
            
        except Exception as e:
            txn.mark_failed(str(e))
        
        # Store transaction
        self._transactions[txn.transaction_id] = txn
        
        return txn
    
    def authorize(
        self,
        from_account: str,
        to_account: str,
        amount: int,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RailTransaction:
        """Authorize (lock) funds using escrow.
        
        Args:
            from_account (str): Source agent ID
            to_account (str): Destination agent ID
            amount (int): Amount to authorize
            currency (str): Currency (ignored for internal credits)
            metadata (Optional[Dict]): Additional metadata
            
        Returns:
            RailTransaction: The authorized transaction
            
        Raises:
            ValueError: If agents don't exist or insufficient funds
        """
        # Create transaction record
        txn = RailTransaction(
            rail_name=self.get_name(),
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            currency=currency,
            metadata=metadata or {}
        )
        
        try:
            # Create escrow to lock funds
            result = self.escrow_manager.create_escrow(
                from_agent_id=from_account,
                to_agent_id=to_account,
                amount=amount,
                memo=metadata.get("memo") if metadata else None
            )
            
            if not result.success:
                raise ValueError(result.error_message)
            
            # Store escrow ID for later capture/void
            escrow_id = result.escrow.escrow_id
            self._internal_refs[txn.transaction_id] = escrow_id
            
            # Mark as authorized
            txn.mark_authorized(external_id=escrow_id)
            
        except Exception as e:
            txn.mark_failed(str(e))
        
        # Store transaction
        self._transactions[txn.transaction_id] = txn
        
        return txn
    
    def capture(
        self,
        transaction_id: str,
        amount: Optional[int] = None
    ) -> RailTransaction:
        """Capture (release) a previously authorized escrow.
        
        Args:
            transaction_id (str): ID of the authorized transaction
            amount (Optional[int]): Amount to capture (must match authorization)
            
        Returns:
            RailTransaction: The captured transaction
            
        Raises:
            ValueError: If transaction not found or not in AUTHORIZED status
        """
        # Get original transaction
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if txn.status != TransactionStatus.AUTHORIZED:
            raise ValueError(f"Transaction is {txn.status.value}, cannot capture")
        
        # Partial capture not supported for internal credits
        if amount is not None and amount != txn.amount:
            raise ValueError("Partial capture not supported for internal credits")
        
        try:
            # Get escrow ID
            escrow_id = self._internal_refs.get(transaction_id)
            if not escrow_id:
                raise ValueError("Escrow ID not found for transaction")
            
            # Release escrow
            result = self.escrow_manager.release_escrow(escrow_id)
            
            if not result.success:
                raise ValueError(result.error_message)
            
            # Mark as captured
            txn.mark_captured()
            
        except Exception as e:
            txn.mark_failed(str(e))
        
        return txn
    
    def void(
        self,
        transaction_id: str
    ) -> RailTransaction:
        """Void (cancel) a previously authorized escrow.
        
        Args:
            transaction_id (str): ID of the authorized transaction
            
        Returns:
            RailTransaction: The cancelled transaction
            
        Raises:
            ValueError: If transaction not found or not in AUTHORIZED status
        """
        # Get original transaction
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if txn.status != TransactionStatus.AUTHORIZED:
            raise ValueError(f"Transaction is {txn.status.value}, cannot void")
        
        try:
            # Get escrow ID
            escrow_id = self._internal_refs.get(transaction_id)
            if not escrow_id:
                raise ValueError("Escrow ID not found for transaction")
            
            # Cancel escrow
            result = self.escrow_manager.cancel_escrow(escrow_id)
            
            if not result.success:
                raise ValueError(result.error_message)
            
            # Mark as cancelled
            txn.status = TransactionStatus.CANCELLED
            txn.updated_at = txn.updated_at  # Update timestamp
            
        except Exception as e:
            txn.mark_failed(str(e))
        
        return txn
    
    def refund(
        self,
        transaction_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> RailTransaction:
        """Refund a completed transaction.
        
        Creates a reverse payment from recipient back to original sender.
        
        Args:
            transaction_id (str): ID of the completed transaction
            amount (Optional[int]): Amount to refund (must match original)
            reason (Optional[str]): Reason for refund
            
        Returns:
            RailTransaction: The refund transaction
            
        Raises:
            ValueError: If transaction not found or not in COMPLETED status
        """
        # Get original transaction
        original_txn = self._transactions.get(transaction_id)
        if original_txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if original_txn.status != TransactionStatus.COMPLETED:
            raise ValueError(f"Transaction is {original_txn.status.value}, cannot refund")
        
        # Partial refund not supported for internal credits
        refund_amount = amount if amount is not None else original_txn.amount
        if refund_amount != original_txn.amount:
            raise ValueError("Partial refunds not supported for internal credits")
        
        # Create refund transaction (reverse the accounts)
        refund_txn = RailTransaction(
            rail_name=self.get_name(),
            from_account=original_txn.to_account,  # Reversed
            to_account=original_txn.from_account,  # Reversed
            amount=refund_amount,
            currency=original_txn.currency,
            metadata={
                "refund_for": transaction_id,
                "reason": reason or "Refund"
            }
        )
        
        try:
            # Execute reverse payment
            entries = self.ledger_manager.record_payment(
                from_agent_id=refund_txn.from_account,
                to_agent_id=refund_txn.to_account,
                amount=refund_amount,
                reference_id=refund_txn.transaction_id,
                memo=f"Refund for {transaction_id}: {reason or 'N/A'}"
            )
            
            # Mark refund as completed
            refund_txn.mark_completed()
            
            # Mark original as refunded
            original_txn.mark_refunded()
            
        except Exception as e:
            refund_txn.mark_failed(str(e))
        
        # Store refund transaction
        self._transactions[refund_txn.transaction_id] = refund_txn
        
        return refund_txn
    
    def get_transaction(self, transaction_id: str) -> Optional[RailTransaction]:
        """Get a transaction by ID.
        
        Args:
            transaction_id (str): The transaction ID
            
        Returns:
            Optional[RailTransaction]: The transaction if found
        """
        return self._transactions.get(transaction_id)
    
    def validate_accounts(self, from_account: str, to_account: str) -> bool:
        """Validate that both accounts exist in the registry.
        
        Args:
            from_account (str): Source account
            to_account (str): Destination account
            
        Returns:
            bool: True if both accounts exist
        """
        return (
            self.agent_registry.agent_exists(from_account) and
            self.agent_registry.agent_exists(to_account)
        )
    
    def clear(self) -> None:
        """Clear all transaction records.
        
        Warning:
            This is for testing only. Does NOT affect the underlying ledger.
        """
        self._transactions.clear()
        self._internal_refs.clear()
