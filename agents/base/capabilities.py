"""Agent capabilities and skill definitions.

This module defines the types of capabilities agents can have
and the system for matching agents to tasks.
"""

from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class AgentCapability(str, Enum):
    """Types of capabilities agents can offer.
    
    Each capability represents a category of services that agents
    can provide in the marketplace.
    """
    # Data & Analytics
    DATA_ANALYSIS = "data_analysis"
    DATA_CLEANING = "data_cleaning"
    DATA_VISUALIZATION = "data_visualization"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    
    # Research
    MARKET_RESEARCH = "market_research"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    FACT_CHECKING = "fact_checking"
    LITERATURE_REVIEW = "literature_review"
    WEB_SCRAPING = "web_scraping"
    
    # Content Creation
    CONTENT_WRITING = "content_writing"
    COPYWRITING = "copywriting"
    TECHNICAL_WRITING = "technical_writing"
    BLOG_WRITING = "blog_writing"
    EMAIL_WRITING = "email_writing"
    
    # Code & Development
    CODE_REVIEW = "code_review"
    CODE_GENERATION = "code_generation"
    BUG_FIXING = "bug_fixing"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    
    # Creative
    IMAGE_GENERATION = "image_generation"
    GRAPHIC_DESIGN = "graphic_design"
    VIDEO_EDITING = "video_editing"
    AUDIO_PROCESSING = "audio_processing"
    
    # Business
    FINANCIAL_ANALYSIS = "financial_analysis"
    BUSINESS_PLANNING = "business_planning"
    STRATEGY_CONSULTING = "strategy_consulting"
    
    # General
    TASK_PLANNING = "task_planning"
    PROJECT_MANAGEMENT = "project_management"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


class CapabilityLevel(str, Enum):
    """Proficiency level for a capability.
    
    Indicates how skilled an agent is at a particular capability.
    Can be used for:
    - Filtering agents by skill level
    - Pricing differentiation (expert > intermediate > beginner)
    - Quality expectations
    """
    BEGINNER = "beginner"      # Learning, may need oversight
    INTERMEDIATE = "intermediate"  # Competent, reliable
    ADVANCED = "advanced"      # Highly skilled
    EXPERT = "expert"          # Master level, premium service


class CapabilityProfile(BaseModel):
    """Profile describing an agent's capabilities.
    
    Used to advertise what an agent can do and at what level.
    Enables capability-based agent discovery and matching.
    """
    capability: AgentCapability = Field(
        description="The type of capability"
    )
    level: CapabilityLevel = Field(
        description="Proficiency level at this capability"
    )
    years_experience: Optional[float] = Field(
        default=None,
        description="Years of experience (for reputation)"
    )
    specializations: List[str] = Field(
        default_factory=list,
        description="Specific areas of expertise within this capability"
    )
    
    def matches(self, required_capability: AgentCapability, min_level: Optional[CapabilityLevel] = None) -> bool:
        """Check if this capability matches requirements.
        
        Args:
            required_capability: The capability needed
            min_level: Minimum proficiency level required (optional)
        
        Returns:
            True if this capability matches the requirements
        
        Example:
            ```python
            profile = CapabilityProfile(
                capability=AgentCapability.DATA_ANALYSIS,
                level=CapabilityLevel.EXPERT
            )
            
            # Matches exact capability
            assert profile.matches(AgentCapability.DATA_ANALYSIS) is True
            
            # Matches with level requirement
            assert profile.matches(
                AgentCapability.DATA_ANALYSIS,
                min_level=CapabilityLevel.INTERMEDIATE
            ) is True
            
            # Doesn't match - level too low
            assert profile.matches(
                AgentCapability.DATA_ANALYSIS,
                min_level=CapabilityLevel.EXPERT
            ) is True  # This passes because level is EXPERT
            ```
        """
        # Must match capability
        if self.capability != required_capability:
            return False
        
        # If no level requirement, it matches
        if min_level is None:
            return True
        
        # Check if agent's level meets minimum requirement
        level_hierarchy = {
            CapabilityLevel.BEGINNER: 1,
            CapabilityLevel.INTERMEDIATE: 2,
            CapabilityLevel.ADVANCED: 3,
            CapabilityLevel.EXPERT: 4
        }
        
        return level_hierarchy[self.level] >= level_hierarchy[min_level]


class CapabilityMatcher:
    """Utility for matching agents to tasks based on capabilities.
    
    Provides intelligent capability matching including:
    - Exact capability matching
    - Level-based filtering
    - Multi-capability requirements
    - Capability recommendations
    """
    
    @staticmethod
    def find_best_match(
        agent_capabilities: List[CapabilityProfile],
        required_capability: AgentCapability,
        min_level: Optional[CapabilityLevel] = None
    ) -> Optional[CapabilityProfile]:
        """Find the best matching capability from an agent's profile.
        
        Returns the highest-level matching capability.
        
        Args:
            agent_capabilities: List of agent's capabilities
            required_capability: Required capability type
            min_level: Minimum level required
        
        Returns:
            Best matching CapabilityProfile or None if no match
        """
        matches = [
            cap for cap in agent_capabilities
            if cap.matches(required_capability, min_level)
        ]
        
        if not matches:
            return None
        
        # Return highest level match
        level_hierarchy = {
            CapabilityLevel.BEGINNER: 1,
            CapabilityLevel.INTERMEDIATE: 2,
            CapabilityLevel.ADVANCED: 3,
            CapabilityLevel.EXPERT: 4
        }
        
        return max(matches, key=lambda c: level_hierarchy[c.level])
    
    @staticmethod
    def get_capability_category(capability: AgentCapability) -> str:
        """Get the category for a capability.
        
        Groups related capabilities together.
        
        Returns:
            Category name (e.g., "data", "content", "code")
        """
        category_map = {
            # Data
            AgentCapability.DATA_ANALYSIS: "data",
            AgentCapability.DATA_CLEANING: "data",
            AgentCapability.DATA_VISUALIZATION: "data",
            AgentCapability.STATISTICAL_ANALYSIS: "data",
            
            # Research
            AgentCapability.MARKET_RESEARCH: "research",
            AgentCapability.COMPETITIVE_ANALYSIS: "research",
            AgentCapability.FACT_CHECKING: "research",
            AgentCapability.LITERATURE_REVIEW: "research",
            AgentCapability.WEB_SCRAPING: "research",
            
            # Content
            AgentCapability.CONTENT_WRITING: "content",
            AgentCapability.COPYWRITING: "content",
            AgentCapability.TECHNICAL_WRITING: "content",
            AgentCapability.BLOG_WRITING: "content",
            AgentCapability.EMAIL_WRITING: "content",
            
            # Code
            AgentCapability.CODE_REVIEW: "code",
            AgentCapability.CODE_GENERATION: "code",
            AgentCapability.BUG_FIXING: "code",
            AgentCapability.TESTING: "code",
            AgentCapability.DOCUMENTATION: "code",
            
            # Creative
            AgentCapability.IMAGE_GENERATION: "creative",
            AgentCapability.GRAPHIC_DESIGN: "creative",
            AgentCapability.VIDEO_EDITING: "creative",
            AgentCapability.AUDIO_PROCESSING: "creative",
            
            # Business
            AgentCapability.FINANCIAL_ANALYSIS: "business",
            AgentCapability.BUSINESS_PLANNING: "business",
            AgentCapability.STRATEGY_CONSULTING: "business",
            
            # General
            AgentCapability.TASK_PLANNING: "general",
            AgentCapability.PROJECT_MANAGEMENT: "general",
            AgentCapability.TRANSLATION: "general",
            AgentCapability.SUMMARIZATION: "general",
        }
        
        return category_map.get(capability, "other")
    
    @staticmethod
    def suggest_related_capabilities(capability: AgentCapability) -> List[AgentCapability]:
        """Suggest related capabilities that often go together.
        
        Useful for:
        - Recommending additional services
        - Finding complementary agents
        - Building agent teams
        
        Args:
            capability: The capability to find related ones for
        
        Returns:
            List of related capabilities
        """
        relations = {
            AgentCapability.DATA_ANALYSIS: [
                AgentCapability.DATA_CLEANING,
                AgentCapability.DATA_VISUALIZATION,
                AgentCapability.STATISTICAL_ANALYSIS
            ],
            AgentCapability.CONTENT_WRITING: [
                AgentCapability.COPYWRITING,
                AgentCapability.BLOG_WRITING,
                AgentCapability.EMAIL_WRITING
            ],
            AgentCapability.CODE_REVIEW: [
                AgentCapability.TESTING,
                AgentCapability.BUG_FIXING,
                AgentCapability.DOCUMENTATION
            ],
            AgentCapability.MARKET_RESEARCH: [
                AgentCapability.COMPETITIVE_ANALYSIS,
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.WEB_SCRAPING
            ],
        }
        
        return relations.get(capability, [])
