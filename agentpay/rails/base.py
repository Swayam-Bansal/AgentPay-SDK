"""Base Rail Adapter Interface.

Defines the interface for payment rail adapters. Rails can be internal (ledger-based)
or external (Stripe, PayPal, crypto, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from uuid import uuid4


class TransactionStatus(str, Enum):
    """Status of a rail transaction."""
    PENDING = "pending"              # Transaction initiated
    AUTHORIZED = "authorized"        # Funds authorized (held)
    CAPTURED = "captured"            # Funds captured (settled)
    COMPLETED = "completed"          # Transaction completed
    FAILED = "failed"                # Transaction failed
    CANCELLED = "cancelled"          # Transaction cancelled
    REFUNDED = "refunded"            # Transaction refunded


class RailTransaction(BaseModel):
    """Represents a transaction on a payment rail.
    
    This is the standardized format for all rail transactions,
    regardless of the underlying rail implementation.
    
    Attributes:
        transaction_id (str): Unique transaction ID
        rail_name (str): Name of the rail (e.g., "internal_credits", "stripe")
        external_id (Optional[str]): External transaction ID from the rail
        from_account (str): Source account/agent ID
        to_account (str): Destination account/agent ID
        amount (int): Amount in smallest currency unit
        currency (str): Currency code (default: "USD")
        status (TransactionStatus): Current transaction status
        created_at (datetime): When transaction was created
        updated_at (datetime): When transaction was last updated
        metadata (Dict[str, Any]): Additional transaction metadata
        error_message (Optional[str]): Error message if failed
    """
    
    transaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique transaction ID"
    )
    rail_name: str = Field(description="Name of the payment rail")
    external_id: Optional[str] = Field(
        default=None,
        description="External ID from the rail provider"
    )
    from_account: str = Field(description="Source account")
    to_account: str = Field(description="Destination account")
    amount: int = Field(gt=0, description="Amount in smallest unit")
    currency: str = Field(default="USD", description="Currency code")
    status: TransactionStatus = Field(
        default=TransactionStatus.PENDING,
        description="Transaction status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    
    def mark_completed(self) -> None:
        """Mark transaction as completed."""
        self.status = TransactionStatus.COMPLETED
        self.updated_at = datetime.now(UTC)
    
    def mark_failed(self, error: str) -> None:
        """Mark transaction as failed."""
        self.status = TransactionStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(UTC)
    
    def mark_authorized(self, external_id: Optional[str] = None) -> None:
        """Mark transaction as authorized."""
        self.status = TransactionStatus.AUTHORIZED
        if external_id:
            self.external_id = external_id
        self.updated_at = datetime.now(UTC)
    
    def mark_captured(self) -> None:
        """Mark transaction as captured."""
        self.status = TransactionStatus.CAPTURED
        self.updated_at = datetime.now(UTC)
    
    def mark_refunded(self) -> None:
        """Mark transaction as refunded."""
        self.status = TransactionStatus.REFUNDED
        self.updated_at = datetime.now(UTC)


class RailAdapter(ABC):
    """Abstract base class for payment rail adapters.
    
    A rail adapter handles the integration with a specific payment system.
    It translates AgentPay operations into rail-specific actions.
    
    All adapters must implement these core methods:
    - **transfer**: Direct fund transfer
    - **authorize**: Reserve funds (two-phase commit part 1)
    - **capture**: Complete reserved transfer (two-phase commit part 2)
    - **void**: Cancel authorization
    - **refund**: Reverse a completed transaction
    
    Usage Example:
        ```python
        class MyRailAdapter(RailAdapter):
            def get_name(self) -> str:
                return "my_rail"
            
            def transfer(self, from_account, to_account, amount, **kwargs):
                # Implement transfer logic
                txn = RailTransaction(
                    rail_name=self.get_name(),
                    from_account=from_account,
                    to_account=to_account,
                    amount=amount
                )
                # ... execute transfer ...
                txn.mark_completed()
                return txn
        ```
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this rail adapter.
        
        Returns:
            str: Rail name (e.g., "internal_credits", "stripe", "paypal")
        """
        pass
    
    @abstractmethod
    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: int,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RailTransaction:
        """Execute a direct transfer between accounts.
        
        This is a single-phase operation that immediately moves funds.
        
        Args:
            from_account (str): Source account identifier
            to_account (str): Destination account identifier
            amount (int): Amount to transfer (smallest currency unit)
            currency (str): Currency code (default: "USD")
            metadata (Optional[Dict]): Additional transaction metadata
            
        Returns:
            RailTransaction: The completed transaction
            
        Raises:
            Exception: If transfer fails
        """
        pass
    
    @abstractmethod
    def authorize(
        self,
        from_account: str,
        to_account: str,
        amount: int,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RailTransaction:
        """Authorize (reserve) funds for a future capture.
        
        This is phase 1 of a two-phase commit. Funds are reserved but not transferred.
        Must be followed by either capture() or void().
        
        Args:
            from_account (str): Source account identifier
            to_account (str): Destination account identifier
            amount (int): Amount to authorize
            currency (str): Currency code
            metadata (Optional[Dict]): Additional metadata
            
        Returns:
            RailTransaction: The authorized transaction
            
        Raises:
            Exception: If authorization fails
        """
        pass
    
    @abstractmethod
    def capture(
        self,
        transaction_id: str,
        amount: Optional[int] = None
    ) -> RailTransaction:
        """Capture (settle) a previously authorized transaction.
        
        This is phase 2 of a two-phase commit. Completes the transfer.
        
        Args:
            transaction_id (str): ID of the authorized transaction
            amount (Optional[int]): Amount to capture (None = full amount)
            
        Returns:
            RailTransaction: The captured transaction
            
        Raises:
            Exception: If capture fails or transaction not found
        """
        pass
    
    @abstractmethod
    def void(
        self,
        transaction_id: str
    ) -> RailTransaction:
        """Void (cancel) a previously authorized transaction.
        
        Releases the reserved funds back to the source account.
        
        Args:
            transaction_id (str): ID of the authorized transaction
            
        Returns:
            RailTransaction: The cancelled transaction
            
        Raises:
            Exception: If void fails or transaction not found
        """
        pass
    
    @abstractmethod
    def refund(
        self,
        transaction_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> RailTransaction:
        """Refund a completed transaction.
        
        Reverses a previously completed transfer.
        
        Args:
            transaction_id (str): ID of the completed transaction
            amount (Optional[int]): Amount to refund (None = full refund)
            reason (Optional[str]): Reason for refund
            
        Returns:
            RailTransaction: The refund transaction
            
        Raises:
            Exception: If refund fails or transaction not found
        """
        pass
    
    @abstractmethod
    def get_transaction(self, transaction_id: str) -> Optional[RailTransaction]:
        """Get a transaction by ID.
        
        Args:
            transaction_id (str): The transaction ID
            
        Returns:
            Optional[RailTransaction]: The transaction if found
        """
        pass
    
    def validate_accounts(self, from_account: str, to_account: str) -> bool:
        """Validate that accounts exist and are valid.
        
        Default implementation always returns True. Override for custom validation.
        
        Args:
            from_account (str): Source account
            to_account (str): Destination account
            
        Returns:
            bool: True if accounts are valid
        """
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(rail={self.get_name()})>"
