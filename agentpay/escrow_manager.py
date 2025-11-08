"""Escrow Manager - manages escrow lifecycle and state.

The EscrowManager provides high-level escrow operations:
- Creating escrows (locking funds)
- Releasing escrows (paying recipient)
- Cancelling escrows (returning funds)
- Tracking escrow state and history

Escrows allow agents to lock funds for future payment, with the ability
to either release to a recipient or cancel and return the funds.
"""

from typing import Dict, Optional, List
from enum import Enum
from uuid import uuid4
from datetime import datetime, UTC
from pydantic import BaseModel, Field

from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager


class EscrowStatus(str, Enum):
    """Status of an escrow."""
    LOCKED = "locked"  # Funds locked, pending release or cancel
    RELEASED = "released"  # Funds released to recipient
    CANCELLED = "cancelled"  # Funds returned to payer


class Escrow(BaseModel):
    """Represents an escrow holding locked funds.
    
    An Escrow locks funds from a payer's wallet (balance → hold) with the
    intent to later release them to a recipient or cancel and return them.
    
    Lifecycle:
    1. Create: Funds moved from payer's balance to hold (LOCKED)
    2a. Release: Funds moved from payer's hold to recipient's balance (RELEASED)
    2b. Cancel: Funds moved from payer's hold back to balance (CANCELLED)
    
    Attributes:
        escrow_id (str): Unique identifier for this escrow
        from_agent_id (str): Agent whose funds are locked (payer)
        to_agent_id (str): Agent who will receive funds if released (recipient)
        amount (int): Amount locked in smallest unit
        status (EscrowStatus): Current status
        created_at (datetime): When escrow was created
        completed_at (Optional[datetime]): When escrow was released/cancelled
        memo (Optional[str]): Optional description
    """
    
    escrow_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique escrow identifier"
    )
    from_agent_id: str = Field(description="Payer agent ID")
    to_agent_id: str = Field(description="Recipient agent ID")
    amount: int = Field(gt=0, description="Locked amount")
    status: EscrowStatus = Field(
        default=EscrowStatus.LOCKED,
        description="Current escrow status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Completion timestamp"
    )
    memo: Optional[str] = Field(
        default=None,
        description="Optional description"
    )
    
    def mark_released(self) -> None:
        """Mark escrow as released."""
        self.status = EscrowStatus.RELEASED
        self.completed_at = datetime.now(UTC)
    
    def mark_cancelled(self) -> None:
        """Mark escrow as cancelled."""
        self.status = EscrowStatus.CANCELLED
        self.completed_at = datetime.now(UTC)


class EscrowResult:
    """Result of an escrow operation.
    
    Attributes:
        success (bool): True if operation succeeded
        escrow (Escrow): The escrow object
        error_code (Optional[str]): Error code if failed
        error_message (Optional[str]): Human-readable error
    """
    
    def __init__(self, success: bool, escrow: Escrow,
                 error_code: Optional[str] = None, error_message: Optional[str] = None):
        self.success = success
        self.escrow = escrow
        self.error_code = error_code
        self.error_message = error_message
    
    def __repr__(self) -> str:
        if self.success:
            return f"EscrowResult(success=True, escrow_id={self.escrow.escrow_id})"
        return f"EscrowResult(success=False, error={self.error_code})"


class EscrowManager:
    """Manager for escrow operations and lifecycle.
    
    The EscrowManager provides a high-level API for working with escrows.
    It handles the full escrow lifecycle from creation through completion.
    
    Key Operations:
    - **create_escrow**: Lock funds from payer (balance → hold)
    - **release_escrow**: Transfer to recipient (hold → recipient's balance)
    - **cancel_escrow**: Return to payer (hold → payer's balance)
    - **get_escrow**: Retrieve escrow by ID
    - **list_escrows**: Query escrows by agent or status
    
    Usage Example:
        ```python
        registry = AgentRegistry()
        ledger = LedgerManager(registry)
        escrow_mgr = EscrowManager(registry, ledger)
        
        # Register and fund agents
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        ledger.record_top_up("alice", 10000, "topup-1")
        
        # Create escrow
        result = escrow_mgr.create_escrow(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=5000,
            memo="Escrow for task completion"
        )
        
        if result.success:
            escrow_id = result.escrow.escrow_id
            
            # Later, release the escrow
            release_result = escrow_mgr.release_escrow(escrow_id)
            if release_result.success:
                print("Escrow released to Bob!")
        ```
    """
    
    def __init__(self, agent_registry: AgentRegistry, ledger_manager: LedgerManager):
        """Initialize the escrow manager.
        
        Args:
            agent_registry (AgentRegistry): Registry for accessing agents
            ledger_manager (LedgerManager): Ledger for recording transactions
        """
        self.agent_registry = agent_registry
        self.ledger_manager = ledger_manager
        self._escrows: Dict[str, Escrow] = {}
    
    def create_escrow(self, from_agent_id: str, to_agent_id: str, amount: int,
                     memo: Optional[str] = None) -> EscrowResult:
        """Create a new escrow, locking funds from payer.
        
        This locks funds from the payer's balance into hold. The funds are
        reserved but not yet transferred to the recipient.
        
        Args:
            from_agent_id (str): Agent locking the funds (payer)
            to_agent_id (str): Agent who will receive if released (recipient)
            amount (int): Amount to lock (must be > 0)
            memo (Optional[str]): Optional description
            
        Returns:
            EscrowResult: Result with success status and escrow object
            
        Example:
            ```python
            result = escrow_mgr.create_escrow(
                from_agent_id="alice",
                to_agent_id="bob",
                amount=3000,
                memo="Payment for milestone 1"
            )
            
            if result.success:
                print(f"Escrow created: {result.escrow.escrow_id}")
                print(f"Status: {result.escrow.status}")
            else:
                print(f"Failed: {result.error_message}")
            ```
        """
        # Validate agents exist
        from_agent = self.agent_registry.get_agent(from_agent_id)
        to_agent = self.agent_registry.get_agent(to_agent_id)
        
        if from_agent is None:
            escrow = Escrow(from_agent_id=from_agent_id, to_agent_id=to_agent_id, amount=amount)
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="PAYER_NOT_FOUND",
                error_message=f"Payer agent {from_agent_id} not found"
            )
        
        if to_agent is None:
            escrow = Escrow(from_agent_id=from_agent_id, to_agent_id=to_agent_id, amount=amount)
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="RECIPIENT_NOT_FOUND",
                error_message=f"Recipient agent {to_agent_id} not found"
            )
        
        # Check sufficient balance
        if not from_agent.wallet.can_hold(amount):
            escrow = Escrow(from_agent_id=from_agent_id, to_agent_id=to_agent_id, amount=amount)
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="INSUFFICIENT_FUNDS",
                error_message=f"Insufficient balance: {from_agent.wallet.balance} < {amount}"
            )
        
        # Create escrow object
        escrow = Escrow(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            amount=amount,
            memo=memo
        )
        
        # Lock funds via ledger
        try:
            self.ledger_manager.record_escrow_lock(
                agent_id=from_agent_id,
                amount=amount,
                reference_id=escrow.escrow_id,
                memo=memo
            )
            
            # Store escrow
            self._escrows[escrow.escrow_id] = escrow
            
            return EscrowResult(success=True, escrow=escrow)
            
        except Exception as e:
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="EXECUTION_ERROR",
                error_message=f"Escrow creation failed: {str(e)}"
            )
    
    def release_escrow(self, escrow_id: str) -> EscrowResult:
        """Release an escrow, transferring funds to recipient.
        
        This moves funds from the payer's hold to the recipient's balance.
        The escrow is marked as RELEASED and cannot be modified further.
        
        Args:
            escrow_id (str): The escrow ID to release
            
        Returns:
            EscrowResult: Result with success status
            
        Example:
            ```python
            result = escrow_mgr.release_escrow("escrow-123")
            
            if result.success:
                print("Escrow released!")
                print(f"Status: {result.escrow.status}")  # RELEASED
            else:
                print(f"Failed: {result.error_message}")
            ```
        """
        escrow = self._escrows.get(escrow_id)
        
        if escrow is None:
            # Create dummy escrow for error result
            dummy = Escrow(from_agent_id="", to_agent_id="", amount=0, escrow_id=escrow_id)
            return EscrowResult(
                success=False,
                escrow=dummy,
                error_code="ESCROW_NOT_FOUND",
                error_message=f"Escrow {escrow_id} not found"
            )
        
        if escrow.status != EscrowStatus.LOCKED:
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="ESCROW_NOT_LOCKED",
                error_message=f"Escrow is {escrow.status.value}, cannot release"
            )
        
        # Release funds via ledger
        try:
            self.ledger_manager.record_escrow_release(
                from_agent_id=escrow.from_agent_id,
                to_agent_id=escrow.to_agent_id,
                amount=escrow.amount,
                reference_id=escrow.escrow_id,
                memo=escrow.memo
            )
            
            # Mark as released
            escrow.mark_released()
            
            return EscrowResult(success=True, escrow=escrow)
            
        except Exception as e:
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="EXECUTION_ERROR",
                error_message=f"Escrow release failed: {str(e)}"
            )
    
    def cancel_escrow(self, escrow_id: str) -> EscrowResult:
        """Cancel an escrow, returning funds to payer.
        
        This moves funds from the payer's hold back to their available balance.
        The escrow is marked as CANCELLED and cannot be modified further.
        
        Args:
            escrow_id (str): The escrow ID to cancel
            
        Returns:
            EscrowResult: Result with success status
            
        Example:
            ```python
            result = escrow_mgr.cancel_escrow("escrow-123")
            
            if result.success:
                print("Escrow cancelled, funds returned!")
                print(f"Status: {result.escrow.status}")  # CANCELLED
            else:
                print(f"Failed: {result.error_message}")
            ```
        """
        escrow = self._escrows.get(escrow_id)
        
        if escrow is None:
            # Create dummy escrow for error result
            dummy = Escrow(from_agent_id="", to_agent_id="", amount=0, escrow_id=escrow_id)
            return EscrowResult(
                success=False,
                escrow=dummy,
                error_code="ESCROW_NOT_FOUND",
                error_message=f"Escrow {escrow_id} not found"
            )
        
        if escrow.status != EscrowStatus.LOCKED:
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="ESCROW_NOT_LOCKED",
                error_message=f"Escrow is {escrow.status.value}, cannot cancel"
            )
        
        # Cancel escrow via ledger
        try:
            self.ledger_manager.record_escrow_cancel(
                agent_id=escrow.from_agent_id,
                amount=escrow.amount,
                reference_id=escrow.escrow_id,
                memo=escrow.memo
            )
            
            # Mark as cancelled
            escrow.mark_cancelled()
            
            return EscrowResult(success=True, escrow=escrow)
            
        except Exception as e:
            return EscrowResult(
                success=False,
                escrow=escrow,
                error_code="EXECUTION_ERROR",
                error_message=f"Escrow cancellation failed: {str(e)}"
            )
    
    def get_escrow(self, escrow_id: str) -> Optional[Escrow]:
        """Get an escrow by ID.
        
        Args:
            escrow_id (str): The escrow ID
            
        Returns:
            Optional[Escrow]: The escrow if found, None otherwise
        """
        return self._escrows.get(escrow_id)
    
    def list_escrows_by_payer(self, agent_id: str) -> List[Escrow]:
        """Get all escrows where agent is the payer.
        
        Args:
            agent_id (str): The payer agent ID
            
        Returns:
            List[Escrow]: All escrows from this agent
        """
        return [e for e in self._escrows.values() if e.from_agent_id == agent_id]
    
    def list_escrows_by_recipient(self, agent_id: str) -> List[Escrow]:
        """Get all escrows where agent is the recipient.
        
        Args:
            agent_id (str): The recipient agent ID
            
        Returns:
            List[Escrow]: All escrows to this agent
        """
        return [e for e in self._escrows.values() if e.to_agent_id == agent_id]
    
    def list_escrows_by_status(self, status: EscrowStatus) -> List[Escrow]:
        """Get all escrows with a specific status.
        
        Args:
            status (EscrowStatus): The status to filter by
            
        Returns:
            List[Escrow]: All escrows with this status
        """
        return [e for e in self._escrows.values() if e.status == status]
    
    def get_all_escrows(self) -> List[Escrow]:
        """Get all escrows in the system.
        
        Returns:
            List[Escrow]: All escrows
        """
        return list(self._escrows.values())
    
    def clear(self) -> None:
        """Clear all escrows.
        
        Warning:
            This is for testing only. Does NOT affect ledger or wallets.
        """
        self._escrows.clear()
