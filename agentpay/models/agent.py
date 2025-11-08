"""Agent model - represents a logical identity that can own and spend money.

This module provides the Agent class, which is the core entity in the payment system.
An Agent combines identity, financial state (wallet), and spending rules (policy) into
a single cohesive unit that can participate in payments.
"""

from typing import Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field

from agentpay.models.wallet import Wallet
from agentpay.models.policy import Policy


class Agent(BaseModel):
    """Logical identity that can own money and make payments.
    
    An Agent represents any entity (AI agent, human, service, organization) that can:
    - Own funds (stored in a wallet)
    - Send payments to other agents
    - Receive payments from other agents
    - Be governed by spending policies
    
    Key Concepts:
    - **Identity**: Each agent has a unique ID (auto-generated UUID or custom)
    - **Financial State**: Managed via an embedded Wallet (balance + hold)
    - **Spending Rules**: Enforced via an embedded Policy
    - **Metadata**: Flexible key-value storage for application-specific data
    
    Agent Lifecycle:
    1. Create agent (ID auto-generated or provided)
    2. Fund wallet via top-up operations
    3. Configure policy to set spending limits/rules
    4. Execute payments (checked against policy)
    5. Track history via ledger entries
    
    Usage Example:
        ```python
        # Create an agent with custom settings
        agent = Agent(
            agent_id="agent-alice",
            metadata={"name": "Alice", "role": "assistant"},
        )
        agent.wallet.balance = 50000  # Fund with $500
        agent.policy.max_per_transaction = 10000  # $100 limit per tx
        
        # Check if agent can make a payment
        can_pay, reason = agent.can_pay(amount=7500, recipient_id="agent-bob")
        if can_pay:
            print("Payment authorized")
        else:
            print(f"Payment blocked: {reason}")
        ```
    
    Attributes:
        agent_id (str): Unique identifier for this agent. Auto-generated as UUID v4
            if not provided. Should be immutable after creation. Required for all
            payment operations.
        wallet (Wallet): The agent's financial state including available balance and
            held funds. Managed by the ledger system. Default: empty wallet (0 balance, 0 hold)
        policy (Policy): Spending rules and restrictions that govern this agent's
            payment behavior. Checked before every payment. Default: unrestricted policy
        metadata (Dict[str, Any]): Flexible key-value storage for application-specific
            data like display names, roles, external IDs, etc. Default: empty dict
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
        """Get a human-readable display name for this agent.
        
        Returns the 'name' field from metadata if present, otherwise falls back
        to the agent_id. Useful for UI display and logging.
        
        Returns:
            str: Display name (from metadata['name']) or agent_id as fallback
            
        Example:
            ```python
            agent = Agent(metadata={"name": "Alice"})
            print(agent.display_name)  # "Alice"
            
            agent2 = Agent(agent_id="agent-123")
            print(agent2.display_name)  # "agent-123" (fallback)
            ```
        """
        return self.metadata.get("name", self.agent_id)
    
    def can_pay(self, amount: int, recipient_id: str) -> tuple[bool, Optional[str]]:
        """Check if this agent can make a payment to another agent.
        
        Performs a comprehensive pre-flight check of all payment requirements:
        1. Agent is not paused (emergency stop)
        2. Recipient is in allowlist (if allowlist is configured)
        3. Amount is within per-transaction limit (if limit is set)
        4. Sufficient available balance exists in wallet
        
        Checks are performed in order and stop at the first failure. This ensures
        the most critical issues (like paused status) are reported first.
        
        Note: This is a read-only check. It does not modify state or reserve funds.
        The actual payment must be executed through the ledger system.
        
        Args:
            amount (int): Payment amount in smallest unit (e.g., cents)
            recipient_id (str): Agent ID of the intended recipient
            
        Returns:
            tuple[bool, Optional[str]]: A tuple of (can_pay, reason) where:
                - can_pay (bool): True if all checks pass, False if any check fails
                - reason (Optional[str]): None if allowed, or error code string if blocked:
                    - "AGENT_PAUSED": This agent is paused (emergency stop)
                    - "RECIPIENT_NOT_ALLOWED": Recipient not in allowlist
                    - "AMOUNT_EXCEEDS_LIMIT": Amount exceeds max_per_transaction
                    - "INSUFFICIENT_FUNDS": Not enough balance in wallet
        
        Example:
            ```python
            agent = Agent()
            agent.wallet.balance = 10000  # $100
            agent.policy.max_per_transaction = 5000  # $50 limit
            
            # Successful check
            can_pay, reason = agent.can_pay(3000, "recipient-123")
            assert can_pay is True
            assert reason is None
            
            # Failed check - amount too high
            can_pay, reason = agent.can_pay(7000, "recipient-123")
            assert can_pay is False
            assert reason == "AMOUNT_EXCEEDS_LIMIT"
            
            # Failed check - insufficient funds
            can_pay, reason = agent.can_pay(15000, "recipient-123")
            assert can_pay is False
            assert reason == "INSUFFICIENT_FUNDS"
            ```
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
