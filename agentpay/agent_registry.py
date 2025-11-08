"""Agent Registry - storage and management system for agents.

The AgentRegistry is responsible for:
- Storing and retrieving agents
- Ensuring agent uniqueness (no duplicate IDs)
- Providing agent lookup and listing capabilities
- Managing agent lifecycle (create, update, delete)

This implementation uses in-memory storage (dictionary). In production,
this could be backed by a database, Redis, or other persistent storage.
"""

from typing import Dict, List, Optional
from agentpay.models import Agent


class AgentRegistry:
    """Registry for storing and managing agents.
    
    The AgentRegistry acts as the central storage system for all agents in the
    payment system. It ensures that each agent has a unique ID and provides
    methods to create, retrieve, update, and list agents.
    
    Storage:
        Uses an in-memory dictionary keyed by agent_id. For production use,
        this could be replaced with a database backend while keeping the same API.
    
    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access, add
        locking mechanisms or use a thread-safe storage backend.
    
    Usage Example:
        ```python
        registry = AgentRegistry()
        
        # Register a new agent
        agent = Agent(metadata={"name": "Alice"})
        registry.register_agent(agent)
        
        # Retrieve an agent
        retrieved = registry.get_agent(agent.agent_id)
        print(retrieved.display_name)  # "Alice"
        
        # List all agents
        all_agents = registry.list_agents()
        print(f"Total agents: {len(all_agents)}")
        ```
    """
    
    def __init__(self):
        """Initialize the agent registry with empty storage."""
        self._agents: Dict[str, Agent] = {}
    
    def register_agent(self, agent: Agent) -> Agent:
        """Register a new agent in the registry.
        
        Adds the agent to storage. If an agent with the same ID already exists,
        raises a ValueError.
        
        Args:
            agent (Agent): The agent to register
            
        Returns:
            Agent: The registered agent (same instance)
            
        Raises:
            ValueError: If an agent with this ID is already registered
            
        Example:
            ```python
            registry = AgentRegistry()
            agent = Agent(agent_id="agent-1")
            registry.register_agent(agent)
            
            # Attempting to register again raises error
            try:
                registry.register_agent(agent)
            except ValueError as e:
                print(e)  # "Agent with ID agent-1 already exists"
            ```
        """
        if agent.agent_id in self._agents:
            raise ValueError(f"Agent with ID {agent.agent_id} already exists")
        
        self._agents[agent.agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Retrieve an agent by ID.
        
        Args:
            agent_id (str): The unique ID of the agent to retrieve
            
        Returns:
            Optional[Agent]: The agent if found, None otherwise
            
        Example:
            ```python
            registry = AgentRegistry()
            agent = Agent(agent_id="agent-1")
            registry.register_agent(agent)
            
            # Retrieve existing agent
            found = registry.get_agent("agent-1")
            assert found is not None
            
            # Try to get non-existent agent
            not_found = registry.get_agent("agent-999")
            assert not_found is None
            ```
        """
        return self._agents.get(agent_id)
    
    def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent with the given ID exists.
        
        Args:
            agent_id (str): The agent ID to check
            
        Returns:
            bool: True if agent exists, False otherwise
            
        Example:
            ```python
            registry = AgentRegistry()
            agent = Agent(agent_id="agent-1")
            registry.register_agent(agent)
            
            assert registry.agent_exists("agent-1") is True
            assert registry.agent_exists("agent-999") is False
            ```
        """
        return agent_id in self._agents
    
    def update_agent(self, agent: Agent) -> Agent:
        """Update an existing agent in the registry.
        
        Replaces the stored agent with the provided agent instance.
        The agent_id must match an existing agent.
        
        Args:
            agent (Agent): The agent with updated data
            
        Returns:
            Agent: The updated agent (same instance)
            
        Raises:
            ValueError: If no agent with this ID exists
            
        Note:
            This replaces the entire agent object. For updating just the wallet
            or policy, retrieve the agent, modify it, then call update_agent.
            
        Example:
            ```python
            registry = AgentRegistry()
            agent = Agent(agent_id="agent-1")
            registry.register_agent(agent)
            
            # Update agent's wallet
            agent.wallet.balance = 10000
            registry.update_agent(agent)
            
            # Verify update
            updated = registry.get_agent("agent-1")
            assert updated.wallet.balance == 10000
            ```
        """
        if agent.agent_id not in self._agents:
            raise ValueError(f"Agent with ID {agent.agent_id} does not exist")
        
        self._agents[agent.agent_id] = agent
        return agent
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent from the registry.
        
        Args:
            agent_id (str): The ID of the agent to delete
            
        Returns:
            bool: True if agent was deleted, False if agent didn't exist
            
        Warning:
            Deleting an agent does NOT clean up their transaction history or
            ledger entries. This should only be used in test/dev scenarios.
            
        Example:
            ```python
            registry = AgentRegistry()
            agent = Agent(agent_id="agent-1")
            registry.register_agent(agent)
            
            # Delete the agent
            deleted = registry.delete_agent("agent-1")
            assert deleted is True
            
            # Verify it's gone
            assert registry.agent_exists("agent-1") is False
            
            # Deleting again returns False
            deleted_again = registry.delete_agent("agent-1")
            assert deleted_again is False
            ```
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
    
    def list_agents(self) -> List[Agent]:
        """Get a list of all registered agents.
        
        Returns:
            List[Agent]: List of all agents in the registry
            
        Note:
            Returns a new list, not a view. Modifying the returned list
            does not affect the registry.
            
        Example:
            ```python
            registry = AgentRegistry()
            registry.register_agent(Agent(agent_id="agent-1"))
            registry.register_agent(Agent(agent_id="agent-2"))
            
            agents = registry.list_agents()
            print(f"Total agents: {len(agents)}")  # 2
            
            for agent in agents:
                print(agent.agent_id)
            ```
        """
        return list(self._agents.values())
    
    def count_agents(self) -> int:
        """Get the total number of registered agents.
        
        Returns:
            int: Number of agents in the registry
            
        Example:
            ```python
            registry = AgentRegistry()
            assert registry.count_agents() == 0
            
            registry.register_agent(Agent())
            assert registry.count_agents() == 1
            ```
        """
        return len(self._agents)
    
    def clear(self) -> None:
        """Remove all agents from the registry.
        
        Warning:
            This is a destructive operation typically only used in tests.
            Use with caution in production scenarios.
            
        Example:
            ```python
            registry = AgentRegistry()
            registry.register_agent(Agent())
            registry.register_agent(Agent())
            assert registry.count_agents() == 2
            
            registry.clear()
            assert registry.count_agents() == 0
            ```
        """
        self._agents.clear()
