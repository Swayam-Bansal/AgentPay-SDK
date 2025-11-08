"""Agent model - represents a logical identity that can own and spend money."""

from typing import Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field

from agentpay.models.wallet import Wallet
from agentpay.models.policy import Policy


class Agent(BaseModel):
    """Logical identity that can own money and make payments.
    
    Each agent has:
    - A unique ID
    - A wallet (balance + hold)
    - A policy controlling spending
    - Optional metadata for display/tracking
    
    Attributes:
        agent_id: Unique identifier (auto-generated UUID if not provided)
        wallet: The agent's wallet with balance and held funds
        policy: Spending rules and restrictions
        metadata: Optional data (display name, role, external refs, etc.)
    """
    
    agent_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique agent identifier"
    )
    wallet: Wallet = Field(
        default_factory=Wallet,
        description="Agent's wallet"
    )
    policy: Policy = Field(
        default_factory=Policy,
        description="Spending policy and restrictions"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (name, role, etc.)"
    )
    
    @property
    def display_name(self) -> str:
        """Get display name from metadata or use agent_id."""
        return self.metadata.get("name", self.agent_id)
    
    def can_pay(self, amount: int, recipient_id: str) -> tuple[bool, Optional[str]]:
        """Check if agent can make a payment.
        
        Returns:
            (can_pay, reason): True if allowed, False with reason if blocked
        """
        # Check if agent is paused
        if self.policy.paused:
            return False, "AGENT_PAUSED"
        
        # Check if recipient is in allowlist
        if not self.policy.is_agent_allowed(recipient_id):
            return False, "RECIPIENT_NOT_ALLOWED"
        
        # Check per-transaction limit
        if not self.policy.is_amount_allowed(amount):
            return False, "AMOUNT_EXCEEDS_LIMIT"
        
        # Check if sufficient funds
        if not self.wallet.can_spend(amount):
            return False, "INSUFFICIENT_FUNDS"
        
        return True, None
