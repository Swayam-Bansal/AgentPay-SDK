"""Payment models - PaymentIntent and related types."""

from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Status of a payment intent."""
    REQUIRES_CONFIRMATION = "requires_confirmation"  # Created but not yet confirmed
    COMPLETED = "completed"  # Successfully processed
    FAILED_POLICY = "failed_policy"  # Blocked by policy violation
    FAILED_FUNDS = "failed_funds"  # Insufficient funds
    CANCELLED = "cancelled"  # Explicitly cancelled
    REQUIRES_APPROVAL = "requires_approval"  # Needs human approval


class PaymentIntent(BaseModel):
    """A request to move value from one agent to another.
    
    PaymentIntents are created first, then confirmed. This two-step process
    allows for validation, approval workflows, and idempotency.
    
    Attributes:
        intent_id: Unique identifier for this payment intent
        from_agent_id: Paying agent ID
        to_agent_id: Receiving agent ID
        amount: Amount to transfer (smallest unit)
        status: Current status of the payment
        idempotency_key: Optional key to prevent duplicate processing
        memo: Optional description/note
        metadata: Additional data
        created_at: When the intent was created
        completed_at: When the payment was completed (if applicable)
        failure_reason: Reason for failure (if failed)
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
        default_factory=datetime.utcnow,
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
        """Mark payment as completed."""
        self.status = PaymentStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self, reason: str) -> None:
        """Mark payment as failed with reason."""
        if "POLICY" in reason or "ALLOWED" in reason or "PAUSED" in reason:
            self.status = PaymentStatus.FAILED_POLICY
        elif "FUNDS" in reason:
            self.status = PaymentStatus.FAILED_FUNDS
        else:
            self.status = PaymentStatus.FAILED_POLICY
        self.failure_reason = reason
        self.completed_at = datetime.utcnow()
    
    def mark_cancelled(self) -> None:
        """Mark payment as cancelled."""
        self.status = PaymentStatus.CANCELLED
        self.completed_at = datetime.utcnow()
