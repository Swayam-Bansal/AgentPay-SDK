"""Payment models - PaymentIntent and related types.

This module provides the PaymentIntent class and PaymentStatus enum that represent
payment requests and their lifecycle states in the agent payment system.
"""

from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, UTC
from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Status values for payment intent lifecycle.
    
    A PaymentIntent moves through various states from creation to completion.
    Terminal states (completed, failed_*, cancelled) are final and cannot transition.
    
    Status Flow:
        REQUIRES_CONFIRMATION → COMPLETED (normal flow)
                            → FAILED_POLICY (policy check failed)
                            → FAILED_FUNDS (insufficient balance)
                            → CANCELLED (manually cancelled)
                            → REQUIRES_APPROVAL (needs human approval)
    
    Attributes:
        REQUIRES_CONFIRMATION (str): Initial state. Payment created but not yet confirmed.
            Next: confirm → COMPLETED, or cancel → CANCELLED
        COMPLETED (str): Terminal state. Payment successfully processed, funds transferred.
            This is a final state - no further transitions.
        FAILED_POLICY (str): Terminal state. Payment blocked by policy violation
            (e.g., agent paused, recipient not allowed, amount exceeds limit).
        FAILED_FUNDS (str): Terminal state. Payment failed due to insufficient balance.
        CANCELLED (str): Terminal state. Payment explicitly cancelled before confirmation.
        REQUIRES_APPROVAL (str): Payment needs human approval before proceeding.
            Next: approve → COMPLETED, or deny → CANCELLED
    """
    REQUIRES_CONFIRMATION = "requires_confirmation"
    COMPLETED = "completed"
    FAILED_POLICY = "failed_policy"
    FAILED_FUNDS = "failed_funds"
    CANCELLED = "cancelled"
    REQUIRES_APPROVAL = "requires_approval"


class PaymentIntent(BaseModel):
    """A request to move value from one agent to another.
    
    PaymentIntent implements a two-phase payment protocol:
    1. **Creation**: Intent is created with all payment details (immutable)
    2. **Confirmation**: Intent is confirmed, triggering policy checks and fund transfer
    
    This design enables:
    - **Validation before execution**: Check all constraints before touching funds
    - **Approval workflows**: Human can review before funds move
    - **Idempotency**: Same request can be safely retried using idempotency_key
    - **Audit trail**: Complete history of payment attempts and outcomes
    
    Payment Intent Lifecycle:
    ```
    1. Create PaymentIntent → status = REQUIRES_CONFIRMATION
    2. Confirm payment:
       a. Check policies (paused, allowlist, limits)
       b. Check funds (sufficient balance)
       c. Execute transfer (update wallets + ledger)
       d. Mark completed → status = COMPLETED
    3. If any check fails → status = FAILED_POLICY or FAILED_FUNDS
    4. Can be cancelled before confirmation → status = CANCELLED
    ```
    
    Usage Example:
        ```python
        # Create a payment intent
        intent = PaymentIntent(
            from_agent_id="agent-alice",
            to_agent_id="agent-bob",
            amount=5000,  # $50.00
            memo="Payment for services",
            idempotency_key="payment-2024-001"
        )
        print(intent.status)  # REQUIRES_CONFIRMATION
        
        # Later, confirm the payment (done by ledger system)
        # If successful:
        intent.mark_completed()
        print(intent.status)  # COMPLETED
        
        # If failed:
        intent.mark_failed("INSUFFICIENT_FUNDS")
        print(intent.status)  # FAILED_FUNDS
        print(intent.failure_reason)  # "INSUFFICIENT_FUNDS"
        ```
    
    Attributes:
        intent_id (str): Unique identifier for this payment intent. Auto-generated UUID
            if not provided. Used to track and reference this payment.
        from_agent_id (str): Agent ID making the payment (payer). Required.
        to_agent_id (str): Agent ID receiving the payment (payee). Required.
        amount (int): Amount to transfer in smallest unit (e.g., cents). Must be > 0.
        status (PaymentStatus): Current lifecycle status. Default: REQUIRES_CONFIRMATION
        idempotency_key (Optional[str]): Optional key for idempotent processing. If provided,
            duplicate requests with same key should return the same result without
            creating duplicate payments. Default: None
        memo (Optional[str]): Optional human-readable description of the payment purpose.
            Stored for record-keeping and display. Default: None
        metadata (Dict[str, Any]): Flexible key-value storage for application-specific
            data (e.g., invoice_id, order_id). Default: empty dict
        created_at (datetime): UTC timestamp when this intent was created. Auto-set.
        completed_at (Optional[datetime]): UTC timestamp when payment reached terminal
            state (completed, failed, or cancelled). None until terminal. Auto-set.
        failure_reason (Optional[str]): Error code explaining why payment failed.
            None unless status is FAILED_POLICY or FAILED_FUNDS.
    """
    
    intent_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique payment intent ID"
    )
    from_agent_id: str = Field(
        description="Agent making the payment"
    )
    to_agent_id: str = Field(
        description="Agent receiving the payment"
    )
    amount: int = Field(
        gt=0,
        description="Amount to transfer in smallest unit"
    )
    status: PaymentStatus = Field(
        default=PaymentStatus.REQUIRES_CONFIRMATION,
        description="Current status"
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Key to ensure idempotent processing"
    )
    memo: Optional[str] = Field(
        default=None,
        description="Optional payment description"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Completion timestamp"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Reason for failure if status is failed"
    )
    
    def mark_completed(self) -> None:
        """Mark payment as successfully completed.
        
        Sets status to COMPLETED and records the completion timestamp.
        Should only be called after funds have been successfully transferred
        and ledger entries created.
        
        Side effects:
            - Sets self.status = PaymentStatus.COMPLETED
            - Sets self.completed_at = current UTC time
            
        Example:
            ```python
            intent = PaymentIntent(from_agent_id="a", to_agent_id="b", amount=1000)
            # ... perform transfer ...
            intent.mark_completed()
            assert intent.status == PaymentStatus.COMPLETED
            assert intent.completed_at is not None
            ```
        """
        self.status = PaymentStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
    
    def mark_failed(self, reason: str) -> None:
        """Mark payment as failed with a specific reason.
        
        Automatically categorizes the failure as either FAILED_POLICY or FAILED_FUNDS
        based on the reason string content. Records the failure reason and timestamp.
        
        Args:
            reason (str): Error code describing why payment failed. Common values:
                - "AGENT_PAUSED": Payer agent is paused
                - "RECIPIENT_NOT_ALLOWED": Recipient not in allowlist
                - "AMOUNT_EXCEEDS_LIMIT": Amount exceeds per-transaction limit
                - "INSUFFICIENT_FUNDS": Not enough balance
                - Custom application-specific error codes
                
        Side effects:
            - Sets self.status = FAILED_POLICY (if policy violation) or
                               FAILED_FUNDS (if insufficient funds)
            - Sets self.failure_reason = reason
            - Sets self.completed_at = current UTC time
            
        Logic:
            - Checks if reason contains "FUNDS" → FAILED_FUNDS
            - Checks if reason contains policy keywords → FAILED_POLICY
            - Default: FAILED_POLICY
            
        Example:
            ```python
            intent = PaymentIntent(from_agent_id="a", to_agent_id="b", amount=1000)
            
            intent.mark_failed("INSUFFICIENT_FUNDS")
            assert intent.status == PaymentStatus.FAILED_FUNDS
            
            intent2 = PaymentIntent(from_agent_id="a", to_agent_id="b", amount=1000)
            intent2.mark_failed("AGENT_PAUSED")
            assert intent2.status == PaymentStatus.FAILED_POLICY
            ```
        """
        if "POLICY" in reason or "ALLOWED" in reason or "PAUSED" in reason:
            self.status = PaymentStatus.FAILED_POLICY
        elif "FUNDS" in reason:
            self.status = PaymentStatus.FAILED_FUNDS
        else:
            self.status = PaymentStatus.FAILED_POLICY
        self.failure_reason = reason
        self.completed_at = datetime.now(UTC)
    
    def mark_cancelled(self) -> None:
        """Mark payment as explicitly cancelled.
        
        Used when a payment is manually cancelled before confirmation.
        Sets status to CANCELLED and records the cancellation timestamp.
        
        Side effects:
            - Sets self.status = PaymentStatus.CANCELLED
            - Sets self.completed_at = current UTC time
            
        Note:
            Should only be called on payments in REQUIRES_CONFIRMATION or
            REQUIRES_APPROVAL status. Completed or failed payments cannot be cancelled.
            
        Example:
            ```python
            intent = PaymentIntent(from_agent_id="a", to_agent_id="b", amount=1000)
            assert intent.status == PaymentStatus.REQUIRES_CONFIRMATION
            
            intent.mark_cancelled()
            assert intent.status == PaymentStatus.CANCELLED
            assert intent.completed_at is not None
            ```
        """
        self.status = PaymentStatus.CANCELLED
        self.completed_at = datetime.now(UTC)
