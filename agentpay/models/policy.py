"""Policy model - defines spending rules and limits for agents."""

from typing import Optional, Set
from pydantic import BaseModel, Field


class Policy(BaseModel):
    """Per-agent spending rules and restrictions.
    
    Policies control how an agent can spend funds, including transaction limits,
    daily caps, approval requirements, and allowlists.
    
    Attributes:
        max_per_transaction: Maximum amount for a single payment (None = unlimited)
        daily_spend_cap: Maximum total outgoing spend per UTC day (None = unlimited)
        require_human_approval_over: Amount threshold requiring human approval (None = never)
        allowlist: Set of agent IDs this agent is allowed to pay (None = can pay anyone)
        paused: If True, agent cannot make any payments (emergency stop)
    """
    
    max_per_transaction: Optional[int] = Field(
        default=None,
        ge=0,
        description="Max amount per transaction in smallest unit"
    )
    daily_spend_cap: Optional[int] = Field(
        default=None,
        ge=0,
        description="Max daily spend in smallest unit"
    )
    require_human_approval_over: Optional[int] = Field(
        default=None,
        ge=0,
        description="Amount requiring human approval"
    )
    allowlist: Optional[Set[str]] = Field(
        default=None,
        description="Set of allowed recipient agent IDs (None = all allowed)"
    )
    paused: bool = Field(
        default=False,
        description="Emergency stop - blocks all spending if True"
    )
    
    def is_agent_allowed(self, agent_id: str) -> bool:
        """Check if payment to given agent is allowed."""
        if self.allowlist is None:
            return True
        return agent_id in self.allowlist
    
    def is_amount_allowed(self, amount: int) -> bool:
        """Check if amount is within per-transaction limit."""
        if self.max_per_transaction is None:
            return True
        return amount <= self.max_per_transaction
    
    def requires_approval(self, amount: int) -> bool:
        """Check if amount requires human approval."""
        if self.require_human_approval_over is None:
            return False
        return amount > self.require_human_approval_over
