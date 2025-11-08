"""Policy model - defines spending rules and limits for agents.

This module provides the Policy class that enforces spending restrictions,
allowlists, approval workflows, and emergency controls for agent payments.
"""

from typing import Optional, Set
from pydantic import BaseModel, Field


class Policy(BaseModel):
    """Per-agent spending rules and restrictions.
    
    A Policy defines the rules that govern an agent's spending behavior. It provides
    multiple layers of control including per-transaction limits, daily spending caps,
    recipient allowlists, approval thresholds, and emergency pause functionality.
    
    All policy checks are enforced before a payment is confirmed. If any check fails,
    the payment will be rejected with a specific error code.
    
    Policy Design Philosophy:
    - **Defense in depth**: Multiple independent controls can be combined
    - **Fail-safe defaults**: Missing limits (None) mean no restriction, except paused
    - **Clear error codes**: Each violation returns a specific, actionable error
    - **Zero-trust by default**: Agents can be restricted to specific recipients via allowlist
    
    Usage Example:
        ```python
        # Create a restrictive policy for a new agent
        policy = Policy(
            max_per_transaction=5000,      # Max $50 per payment
            daily_spend_cap=20000,         # Max $200 per day
            require_human_approval_over=10000,  # Approval needed above $100
            allowlist={"agent-1", "agent-2"},   # Can only pay these agents
            paused=False                   # Not paused
        )
        
        # Check if a payment is allowed
        if policy.is_agent_allowed("agent-1") and policy.is_amount_allowed(3000):
            print("Payment pre-checks passed")
        ```
    
    Attributes:
        max_per_transaction (Optional[int]): Maximum amount for a single payment in
            smallest unit (e.g., cents). None means no limit. Default: None
        daily_spend_cap (Optional[int]): Maximum total outgoing spend per UTC day in
            smallest unit. None means no daily limit. Default: None
            Note: Daily cap enforcement requires tracking (implemented in ledger)
        require_human_approval_over (Optional[int]): Amount threshold above which human
            approval is required. None means never require approval. Default: None
        allowlist (Optional[Set[str]]): Set of agent IDs this agent is permitted to pay.
            None means can pay any agent (no restrictions). Default: None
        paused (bool): Emergency stop flag. If True, agent cannot make ANY payments
            regardless of other settings. Default: False
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
        """Check if payment to a specific recipient agent is allowed.
        
        If an allowlist is configured, only agents in that list can receive payments.
        If no allowlist is set (None), all agents are allowed.
        
        Args:
            agent_id (str): The agent ID of the intended recipient
            
        Returns:
            bool: True if payment to this agent is allowed, False if blocked by allowlist
            
        Example:
            ```python
            policy = Policy(allowlist={"agent-1", "agent-2"})
            policy.is_agent_allowed("agent-1")  # True
            policy.is_agent_allowed("agent-3")  # False
            
            open_policy = Policy()  # No allowlist
            open_policy.is_agent_allowed("any-agent")  # True
            ```
        """
        if self.allowlist is None:
            return True
        return agent_id in self.allowlist
    
    def is_amount_allowed(self, amount: int) -> bool:
        """Check if a payment amount is within the per-transaction limit.
        
        This enforces the maximum amount that can be sent in a single transaction.
        If no limit is set (None), any amount is allowed.
        
        Args:
            amount (int): Payment amount in smallest unit (e.g., cents)
            
        Returns:
            bool: True if amount <= max_per_transaction (or no limit set), False otherwise
            
        Example:
            ```python
            policy = Policy(max_per_transaction=10000)  # $100 max
            policy.is_amount_allowed(5000)   # True - $50 is under limit
            policy.is_amount_allowed(10000)  # True - exactly at limit
            policy.is_amount_allowed(15000)  # False - over limit
            ```
        """
        if self.max_per_transaction is None:
            return True
        return amount <= self.max_per_transaction
    
    def requires_approval(self, amount: int) -> bool:
        """Check if a payment amount requires human approval.
        
        Amounts strictly greater than the threshold require approval. The threshold
        amount itself does not require approval (> not >=).
        
        If no approval threshold is set (None), approval is never required.
        
        Args:
            amount (int): Payment amount in smallest unit (e.g., cents)
            
        Returns:
            bool: True if amount > threshold (needs approval), False otherwise
            
        Note:
            This method only checks if approval is needed. The actual approval
            workflow is handled by the application layer, not the SDK.
            
        Example:
            ```python
            policy = Policy(require_human_approval_over=10000)  # Approval above $100
            policy.requires_approval(9999)   # False - under threshold
            policy.requires_approval(10000)  # False - at threshold (not over)
            policy.requires_approval(10001)  # True - over threshold
            ```
        """
        if self.require_human_approval_over is None:
            return False
        return amount > self.require_human_approval_over
