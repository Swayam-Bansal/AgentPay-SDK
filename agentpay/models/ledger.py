"""Ledger models - double-entry accounting records.

This module provides the LedgerEntry class and EntryType enum for tracking all
value movements in the agent payment system using double-entry bookkeeping.
"""

from enum import Enum
from typing import Optional
from uuid import uuid4
from datetime import datetime, UTC
from pydantic import BaseModel, Field


class EntryType(str, Enum):
    """Types of ledger entries representing different value movement operations.
    
    Each EntryType corresponds to a specific kind of financial operation in the system.
    Every operation creates one or more ledger entries to maintain double-entry accounting.
    
    Double-Entry Principle:
    For every transaction, total debits (negative deltas) must equal total credits
    (positive deltas), ensuring the system's total value remains constant.
    
    Entry Type Categories:
    - **Payment Operations**: PAYMENT - direct transfers between agents
    - **Escrow Operations**: ESCROW_LOCK, ESCROW_RELEASE, ESCROW_CANCEL
    - **Streaming Operations**: STREAM_TICK - incremental payments over time
    - **External Operations**: TOP_UP, WITHDRAWAL - value entering/leaving system
    - **Administrative**: ADJUSTMENT - manual corrections
    
    Attributes:
        PAYMENT (str): Regular one-off payment between two agents.
            Creates 2 entries: debit from payer, credit to payee.
            Example: Agent A pays Agent B $50
            
        ESCROW_LOCK (str): Funds moved from agent's balance to hold (locked for escrow).
            Creates 1 entry: moves balance→hold for payer (no value movement between agents).
            Example: Lock $100 for future payment
            
        ESCROW_RELEASE (str): Escrow funds released from payer's hold to recipient's balance.
            Creates 2 entries: debit from payer's hold, credit to payee's balance.
            Example: Release locked $100 to recipient
            
        ESCROW_CANCEL (str): Escrow funds returned from hold back to payer's balance.
            Creates 1 entry: moves hold→balance for payer (no value movement).
            Example: Cancel escrow, return $100 to payer
            
        STREAM_TICK (str): Single increment of a streaming payment.
            Creates 2 entries: debit from payer, credit to payee.
            Example: $1/minute stream ticks, transferring $1
            
        TOP_UP (str): External funds added to an agent's wallet (value entering system).
            Creates 1 entry: credit to recipient. No corresponding debit (external source).
            Example: Fund agent with $1000 from credit card
            
        WITHDRAWAL (str): Funds withdrawn from agent's wallet (value leaving system).
            Creates 1 entry: debit from payer. No corresponding credit (external destination).
            Example: Cash out $500 to bank account
            
        ADJUSTMENT (str): Manual balance correction (administrative action).
            Creates entries as needed for corrections. Should be rare and audited.
            Example: Fix accounting error
    """
    PAYMENT = "payment"
    ESCROW_LOCK = "escrow_lock"
    ESCROW_RELEASE = "escrow_release"
    ESCROW_CANCEL = "escrow_cancel"
    STREAM_TICK = "stream_tick"
    TOP_UP = "top_up"
    WITHDRAWAL = "withdrawal"
    ADJUSTMENT = "adjustment"


class LedgerEntry(BaseModel):
    """A single ledger entry representing value movement.
    
    LedgerEntry is the fundamental building block of the payment system's accounting.
    It records every change to every agent's balance, forming an immutable audit trail.
    
    Double-Entry Accounting:
    The system enforces double-entry bookkeeping principles:
    - Every transaction involves at least 2 entries (typically payer debit + payee credit)
    - Sum of all delta_amounts for a transaction reference_id must equal zero
    - This ensures value is conserved: money doesn't appear or disappear
    - Exception: TOP_UP and WITHDRAWAL (value entering/leaving the system)
    
    Entry Anatomy:
    Each entry records:
    1. **Which agent** (agent_id)
    2. **How much changed** (delta_amount: negative=debit, positive=credit)
    3. **What type of operation** (entry_type)
    4. **What transaction** (reference_id: links to PaymentIntent/Escrow/etc.)
    5. **Resulting balance** (balance_after: snapshot for verification)
    6. **When it happened** (created_at: immutable timestamp)
    
    Invariants (must always hold):
    - balance_after >= 0 (no negative balances)
    - balance_after = previous_balance + delta_amount
    - For same reference_id: Σ delta_amount = 0 (except TOP_UP/WITHDRAWAL)
    - Entries are immutable once created (never modified, only appended)
    
    Usage Example:
        ```python
        # Example: Payment of $50 from Alice to Bob
        # Creates 2 ledger entries:
        
        # Entry 1: Debit Alice
        entry_alice = LedgerEntry(
            agent_id="agent-alice",
            delta_amount=-5000,  # -$50 (negative = debit)
            entry_type=EntryType.PAYMENT,
            reference_id="payment-intent-123",
            balance_after=45000,  # $450 remaining (was $500)
            memo="Payment to Bob for services"
        )
        
        # Entry 2: Credit Bob
        entry_bob = LedgerEntry(
            agent_id="agent-bob",
            delta_amount=5000,  # +$50 (positive = credit)
            entry_type=EntryType.PAYMENT,
            reference_id="payment-intent-123",  # Same reference!
            balance_after=15000,  # $150 total (was $100)
            memo="Payment from Alice for services"
        )
        
        # Verify double-entry: -5000 + 5000 = 0 ✓
        ```
    
    Attributes:
        entry_id (str): Unique identifier for this ledger entry. Auto-generated UUID.
            Used to reference and retrieve this specific entry.
        agent_id (str): Agent ID this entry belongs to. Links entry to specific agent.
        delta_amount (int): Change in balance in smallest unit (e.g., cents).
            Negative = debit (outgoing), Positive = credit (incoming), Zero = neutral.
        entry_type (EntryType): Type of operation that created this entry.
            Determines the semantic meaning (payment, escrow, stream, etc.).
        reference_id (str): ID of the related transaction object (PaymentIntent ID,
            Escrow ID, Stream ID, etc.). Used to group entries belonging to same transaction.
        balance_after (int): Agent's balance immediately after this entry was applied.
            Must be >= 0. Provides snapshot for verification and debugging.
        memo (Optional[str]): Optional human-readable description of this entry.
            Useful for auditing, debugging, and displaying transaction history.
        created_at (datetime): UTC timestamp when this entry was created.
            Immutable. Provides chronological ordering of all entries.
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
        default_factory=lambda: datetime.now(UTC),
        description="Entry timestamp"
    )
    
    @property
    def is_debit(self) -> bool:
        """Check if this entry is a debit (outgoing funds).
        
        A debit represents funds leaving the agent's balance (negative delta_amount).
        In accounting terms: assets decrease, expense recorded.
        
        Returns:
            bool: True if delta_amount < 0 (debit), False otherwise
            
        Example:
            ```python
            entry = LedgerEntry(
                agent_id="agent-1",
                delta_amount=-5000,  # -$50
                entry_type=EntryType.PAYMENT,
                reference_id="pay-123",
                balance_after=10000
            )
            assert entry.is_debit is True
            assert entry.is_credit is False
            ```
        """
        return self.delta_amount < 0
    
    @property
    def is_credit(self) -> bool:
        """Check if this entry is a credit (incoming funds).
        
        A credit represents funds entering the agent's balance (positive delta_amount).
        In accounting terms: assets increase, revenue recorded.
        
        Returns:
            bool: True if delta_amount > 0 (credit), False otherwise
            
        Example:
            ```python
            entry = LedgerEntry(
                agent_id="agent-2",
                delta_amount=5000,  # +$50
                entry_type=EntryType.PAYMENT,
                reference_id="pay-123",
                balance_after=15000
            )
            assert entry.is_credit is True
            assert entry.is_debit is False
            ```
        """
        return self.delta_amount > 0
