"""Pydantic models for AgentPay HTTP API."""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field


# -------- Common --------

class ErrorResponse(BaseModel):
    detail: str


# -------- Agents --------

class RegisterAgentRequest(BaseModel):
    agent_id: str
    metadata: Optional[Dict[str, Any]] = None
    # Simple policy fields; more can be added as needed
    max_per_transaction: Optional[int] = None
    daily_spend_cap: Optional[int] = None
    require_human_approval_over: Optional[int] = None
    allowlist: Optional[List[str]] = None


class AgentResponse(BaseModel):
    agent_id: str
    metadata: Dict[str, Any]
    paused: bool
    balance: int
    hold: int


class UpdatePolicyRequest(BaseModel):
    paused: Optional[bool] = None
    max_per_transaction: Optional[int] = None
    daily_spend_cap: Optional[int] = None
    require_human_approval_over: Optional[int] = None
    allowlist: Optional[List[str]] = None


# -------- Funding / Wallet --------

class FundRequest(BaseModel):
    amount: int = Field(gt=0)
    memo: Optional[str] = None


class WalletResponse(BaseModel):
    balance: int
    hold: int
    total: int


# -------- Payments --------

class PaymentRequest(BaseModel):
    from_agent: str
    to_agent: str
    amount: int = Field(gt=0)
    memo: Optional[str] = None
    idempotency_key: Optional[str] = None


class PaymentResponse(BaseModel):
    success: bool
    intent_id: str
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# -------- Escrow --------

class CreateEscrowRequest(BaseModel):
    from_agent: str
    to_agent: str
    amount: int = Field(gt=0)
    memo: Optional[str] = None


class EscrowResponse(BaseModel):
    success: bool
    escrow_id: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


# -------- Queries --------

class LedgerEntryResponse(BaseModel):
    reference_id: str
    entry_type: str
    delta_amount: int
    balance_after: int
    memo: Optional[str] = None

