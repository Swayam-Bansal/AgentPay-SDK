"""Ledger models - double-entry accounting records."""

from enum import Enum
from typing import Optional
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class EntryType(str, Enum):
    """Type of ledger entry."""
    PAYMENT = "payment"  # Regular payment between agents
    ESCROW_LOCK = "escrow_lock"  # Funds moved to hold for escrow
    ESCROW_RELEASE = "escrow_release"  # Escrow funds released to recipient
    ESCROW_CANCEL = "escrow_cancel"  # Escrow funds returned to payer
    STREAM_TICK = "stream_tick"  # Streaming payment tick
    TOP_UP = "top_up"  # External funds added to agent wallet
    WITHDRAWAL = "withdrawal"  # Funds withdrawn from system
    ADJUSTMENT = "adjustment"  # Manual balance adjustment


class LedgerEntry(BaseModel):
    """A single ledger entry representing value movement.
    
    Ledger entries form a double-entry accounting system. Every transaction
    creates at least two entries: one negative (debit) and one positive (credit).
    The sum of all delta_amounts for a transaction must equal zero.
    
    Attributes:
        entry_id: Unique identifier for this entry
        agent_id: Agent this entry belongs to
        delta_amount: Change in balance (positive = credit, negative = debit)
        entry_type: Type of transaction
        reference_id: ID of the related object (PaymentIntent, Escrow, etc.)
        balance_after: Agent's balance after this entry
        memo: Optional description
        created_at: When this entry was created
    """
    
    entry_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique ledger entry ID"
    )
    agent_id: str = Field(
        description="Agent this entry belongs to"
    )
    delta_amount: int = Field(
        description="Change in balance (+ or -) in smallest unit"
    )
    entry_type: EntryType = Field(
        description="Type of transaction"
    )
    reference_id: str = Field(
        description="ID of related PaymentIntent, Escrow, Stream, etc."
    )
    balance_after: int = Field(
        ge=0,
        description="Agent's balance after this entry"
    )
    memo: Optional[str] = Field(
        default=None,
        description="Optional description"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Entry timestamp"
    )
    
    @property
    def is_debit(self) -> bool:
        """Check if this is a debit (negative amount)."""
        return self.delta_amount < 0
    
    @property
    def is_credit(self) -> bool:
        """Check if this is a credit (positive amount)."""
        return self.delta_amount > 0
