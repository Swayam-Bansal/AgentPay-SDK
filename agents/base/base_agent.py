"""Base agent class - foundation for all AgentPay agents.

This module provides the abstract base class that all agents inherit from,
whether they are orchestrators, specialized service providers, or general agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4
from datetime import datetime, UTC
from pydantic import BaseModel, Field

from agentpay import AgentPaySDK
from agents.base.capabilities import CapabilityProfile, AgentCapability


class TaskStatus(str, Enum):
    """Status of a task execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Represents a task to be executed by an agent.
    
    Tasks are the unit of work in the agent marketplace.
    They can be assigned to agents and tracked through completion.
    """
    task_id: str = Field(
        default_factory=lambda: f"task-{uuid4()}",
        description="Unique task identifier"
    )
    description: str = Field(
        description="What needs to be done"
    )
    required_capability: Optional[AgentCapability] = Field(
        default=None,
        description="The capability needed to complete this task"
    )
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for the task"
    )
    expected_output_format: Optional[str] = Field(
        default=None,
        description="Expected format of the result"
    )
    deadline: Optional[datetime] = Field(
        default=None,
        description="When task should be completed"
    )
    max_budget: Optional[int] = Field(
        default=None,
        description="Maximum budget for this task (in cents)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata"
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current status of the task"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When task was created"
    )


class TaskResult(BaseModel):
    """Result of a task execution.
    
    Contains the output, status, and metadata about task completion.
    """
    task_id: str = Field(
        description="ID of the task this result is for"
    )
    status: TaskStatus = Field(
        description="Final status of the task"
    )
    output_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="The result of the task"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if task failed"
    )
    execution_time: Optional[float] = Field(
        default=None,
        description="Time taken to execute (seconds)"
    )
    cost: Optional[int] = Field(
        default=None,
        description="Actual cost of execution (in cents)"
    )
    agent_id: str = Field(
        description="ID of agent that executed the task"
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When task completed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata"
    )


class BaseAgent(ABC):
    """Abstract base class for all agents in the AgentPay ecosystem.
    
    This class provides the common interface that all agents must implement,
    including payment capabilities, task execution, and SDK integration.
    
    All agents (orchestrators, specialized agents, etc.) inherit from this class.
    
    Attributes:
        agent_id: Unique identifier for this agent
        name: Human-readable name
        sdk: AgentPaySDK instance for payments
        capabilities: List of capabilities this agent has
        is_active: Whether agent is currently accepting tasks
        reputation_score: Agent's reputation (0-100)
    
    Example:
        ```python
        class MyAgent(BaseAgent):
            def __init__(self, sdk: AgentPaySDK, agent_id: str):
                super().__init__(sdk, agent_id, "My Custom Agent")
                self.add_capability(
                    AgentCapability.DATA_ANALYSIS,
                    CapabilityLevel.EXPERT
                )
            
            def execute_task(self, task: Task) -> TaskResult:
                # Custom task execution logic
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.COMPLETED,
                    output_data={"result": "Done!"},
                    agent_id=self.agent_id
                )
        ```
    """
    
    def __init__(
        self,
        sdk: AgentPaySDK,
        agent_id: str,
        name: str,
        description: str = ""
    ):
        """Initialize the base agent.
        
        Args:
            sdk: AgentPaySDK instance for payment operations
            agent_id: Unique identifier for this agent
            name: Human-readable name for the agent
            description: Optional description of what this agent does
        """
        self.sdk = sdk
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities: List[CapabilityProfile] = []
        self.is_active = True
        self.reputation_score = 50.0  # Start at neutral
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        # Register agent with SDK if not already registered
        if not sdk.agent_exists(agent_id):
            sdk.register_agent(
                agent_id=agent_id,
                metadata={
                    "name": name,
                    "description": description,
                    "type": self.__class__.__name__
                }
            )
    
    def add_capability(
        self,
        capability: AgentCapability,
        level: CapabilityLevel,
        specializations: Optional[List[str]] = None
    ) -> None:
        """Add a capability to this agent's profile.
        
        Args:
            capability: The capability to add
            level: Proficiency level at this capability
            specializations: Optional list of specializations
        
        Example:
            ```python
            agent.add_capability(
                AgentCapability.DATA_ANALYSIS,
                CapabilityLevel.EXPERT,
                specializations=["time series", "regression"]
            )
            ```
        """
        profile = CapabilityProfile(
            capability=capability,
            level=level,
            specializations=specializations or []
        )
        self.capabilities.append(profile)
    
    def has_capability(
        self,
        capability: AgentCapability,
        min_level: Optional[CapabilityLevel] = None
    ) -> bool:
        """Check if agent has a specific capability.
        
        Args:
            capability: The capability to check for
            min_level: Minimum proficiency level required
        
        Returns:
            True if agent has the capability at required level
        """
        for cap_profile in self.capabilities:
            if cap_profile.matches(capability, min_level):
                return True
        return False
    
    @abstractmethod
    def execute_task(self, task: Task) -> TaskResult:
        """Execute a task and return the result.
        
        This is the core method that each agent must implement.
        Defines how the agent processes and completes tasks.
        
        Args:
            task: The task to execute
        
        Returns:
            TaskResult with output and status
        
        Note:
            Implementations should:
            1. Validate task is compatible with agent's capabilities
            2. Perform the actual work
            3. Return TaskResult with appropriate status
            4. Update task completion stats
        """
        pass
    
    def request_payment(
        self,
        amount: int,
        purpose: str,
        justification: str = ""
    ) -> Dict[str, Any]:
        """Request payment approval for expenses.
        
        Used when agent needs funds to complete a task (e.g., API costs).
        In remote mode, triggers quorum voting.
        
        Args:
            amount: Amount needed in cents
            purpose: What the funds are for
            justification: Why this expense is needed
        
        Returns:
            Payment request result with approval status
        """
        if self.sdk.mode == 'remote':
            return self.sdk.request_payment_card(
                amount=amount,
                purpose=purpose,
                justification=justification,
                agent_id=self.agent_id
            )
        else:
            # In local mode, just check balance
            balance = self.sdk.get_balance(self.agent_id)
            if balance >= amount:
                return {
                    'approved': True,
                    'amount': amount,
                    'purpose': purpose
                }
            else:
                return {
                    'approved': False,
                    'amount': amount,
                    'reason': 'Insufficient balance'
                }
    
    def receive_payment(
        self,
        from_agent_id: str,
        amount: int,
        purpose: str
    ) -> Dict[str, Any]:
        """Receive payment from another agent.
        
        Called when this agent has completed a service for another agent.
        
        Args:
            from_agent_id: Agent paying for the service
            amount: Amount in cents
            purpose: What the payment is for
        
        Returns:
            Transfer result
        """
        result = self.sdk.transfer_to_agent(
            from_agent_id=from_agent_id,
            to_agent_id=self.agent_id,
            amount=amount,
            purpose=purpose
        )
        
        if result['status'] == 'completed':
            # Update reputation on successful payment
            self.reputation_score = min(100.0, self.reputation_score + 0.1)
        
        return result
    
    def pay_agent(
        self,
        to_agent_id: str,
        amount: int,
        purpose: str
    ) -> Dict[str, Any]:
        """Pay another agent for their services.
        
        Args:
            to_agent_id: Agent to pay
            amount: Amount in cents
            purpose: What the payment is for
        
        Returns:
            Transfer result
        """
        return self.sdk.transfer_to_agent(
            from_agent_id=self.agent_id,
            to_agent_id=to_agent_id,
            amount=amount,
            purpose=purpose
        )
    
    def get_balance(self) -> int:
        """Get current balance of this agent.
        
        Returns:
            Balance in cents
        """
        return self.sdk.get_balance(self.agent_id)
    
    def get_earnings_summary(self) -> Dict[str, Any]:
        """Get summary of this agent's earnings.
        
        Returns:
            Dict with total_earned, total_spent, net_profit
        """
        return self.sdk.get_agent_balance_summary(self.agent_id)
    
    def get_reputation(self) -> float:
        """Get agent's reputation score.
        
        Returns:
            Reputation score (0-100)
        """
        return self.reputation_score
    
    def update_reputation(self, delta: float) -> None:
        """Update agent's reputation score.
        
        Args:
            delta: Amount to change reputation (+/-)
        """
        self.reputation_score = max(0.0, min(100.0, self.reputation_score + delta))
    
    def get_success_rate(self) -> float:
        """Calculate task success rate.
        
        Returns:
            Success rate as percentage (0-100)
        """
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks == 0:
            return 0.0
        return (self.tasks_completed / total_tasks) * 100
    
    def to_profile(self) -> Dict[str, Any]:
        """Get agent's public profile.
        
        Returns:
            Dict with agent information for marketplace listing
        """
        earnings = self.get_earnings_summary()
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'description': self.description,
            'type': self.__class__.__name__,
            'capabilities': [
                {
                    'capability': cap.capability.value,
                    'level': cap.level.value,
                    'specializations': cap.specializations
                }
                for cap in self.capabilities
            ],
            'is_active': self.is_active,
            'reputation_score': self.reputation_score,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'success_rate': self.get_success_rate(),
            'total_earned': earnings['total_earned'],
            'total_spent': earnings['total_spent'],
            'net_profit': earnings['net_profit'],
            'current_balance': earnings['current_balance']
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.agent_id}: {self.name}>"
