"""AgentPay SDK - Payment infrastructure for AI agents."""

__version__ = "0.1.0"

# Main SDK interface
from agentpay.sdk import AgentPaySDK

# Core models (for advanced usage)
from agentpay.models import (
    Agent,
    Wallet,
    Policy,
    PaymentIntent,
    PaymentStatus,
    LedgerEntry,
    EntryType,
)

# Components (for advanced usage)
from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager
from agentpay.payment_engine import PaymentEngine, PaymentResult
from agentpay.escrow_manager import EscrowManager, Escrow, EscrowResult, EscrowStatus

__all__ = [
    # Main SDK
    "AgentPaySDK",
    # Models
    "Agent",
    "Wallet",
    "Policy",
    "PaymentIntent",
    "PaymentStatus",
    "LedgerEntry",
    "EntryType",
    # Components
    "AgentRegistry",
    "LedgerManager",
    "PaymentEngine",
    "PaymentResult",
    "EscrowManager",
    "Escrow",
    "EscrowResult",
    "EscrowStatus",
]

# Core models will be imported here for easy access once implemented
# from agentpay.models.agent import Agent
# from agentpay.models.wallet import Wallet
# from agentpay.models.policy import Policy
# from agentpay.models.payment import PaymentIntent, PaymentStatus
# from agentpay.models.ledger import LedgerEntry, EntryType
