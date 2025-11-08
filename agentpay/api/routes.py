"""HTTP routes for AgentPay API."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request

from agentpay.api.models import (
    RegisterAgentRequest,
    AgentResponse,
    UpdatePolicyRequest,
    FundRequest,
    WalletResponse,
    PaymentRequest,
    PaymentResponse,
    CreateEscrowRequest,
    EscrowResponse,
    LedgerEntryResponse,
)
from agentpay.sdk import AgentPaySDK
from agentpay.models import Policy


router = APIRouter()


def get_sdk(req: Request) -> AgentPaySDK:
    sdk = getattr(req.app.state, "sdk", None)
    if sdk is None:
        raise RuntimeError("SDK not initialized")
    return sdk


# ------- Agents -------

@router.post("/agents", response_model=AgentResponse)
def register_agent(payload: RegisterAgentRequest, sdk: AgentPaySDK = Depends(get_sdk)) -> AgentResponse:
    policy = Policy(
        max_per_transaction=payload.max_per_transaction,
        daily_spend_cap=payload.daily_spend_cap,
        require_human_approval_over=payload.require_human_approval_over,
        allowlist=set(payload.allowlist) if payload.allowlist else None,
    )
    try:
        agent = sdk.register_agent(payload.agent_id, policy=policy, metadata=payload.metadata or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AgentResponse(
        agent_id=agent.agent_id,
        metadata=agent.metadata,
        paused=agent.policy.paused,
        balance=agent.wallet.balance,
        hold=agent.wallet.hold,
    )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> AgentResponse:
    agent = sdk.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(
        agent_id=agent.agent_id,
        metadata=agent.metadata,
        paused=agent.policy.paused,
        balance=agent.wallet.balance,
        hold=agent.wallet.hold,
    )


@router.get("/agents", response_model=List[AgentResponse])
def list_agents(sdk: AgentPaySDK = Depends(get_sdk)) -> List[AgentResponse]:
    agents = sdk.list_agents()
    return [
        AgentResponse(
            agent_id=a.agent_id,
            metadata=a.metadata,
            paused=a.policy.paused,
            balance=a.wallet.balance,
            hold=a.wallet.hold,
        )
        for a in agents
    ]


@router.patch("/agents/{agent_id}/policy", response_model=AgentResponse)
def update_policy(agent_id: str, payload: UpdatePolicyRequest, sdk: AgentPaySDK = Depends(get_sdk)) -> AgentResponse:
    # Fetch existing to merge
    agent = sdk.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    new_policy = Policy(
        max_per_transaction=payload.max_per_transaction if payload.max_per_transaction is not None else agent.policy.max_per_transaction,
        daily_spend_cap=payload.daily_spend_cap if payload.daily_spend_cap is not None else agent.policy.daily_spend_cap,
        require_human_approval_over=(
            payload.require_human_approval_over if payload.require_human_approval_over is not None else agent.policy.require_human_approval_over
        ),
        allowlist=set(payload.allowlist) if payload.allowlist is not None else agent.policy.allowlist,
        paused=payload.paused if payload.paused is not None else agent.policy.paused,
    )
    updated = sdk.update_agent_policy(agent_id, new_policy)
    return AgentResponse(
        agent_id=updated.agent_id,
        metadata=updated.metadata,
        paused=updated.policy.paused,
        balance=updated.wallet.balance,
        hold=updated.wallet.hold,
    )


# ------- Wallet -------

@router.post("/agents/{agent_id}/fund", response_model=WalletResponse)
def fund_agent(agent_id: str, payload: FundRequest, sdk: AgentPaySDK = Depends(get_sdk)) -> WalletResponse:
    try:
        sdk.fund_agent(agent_id, payload.amount, memo=payload.memo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    wallet = sdk.get_wallet(agent_id)
    return WalletResponse(balance=wallet.balance, hold=wallet.hold, total=wallet.total)


@router.get("/agents/{agent_id}/wallet", response_model=WalletResponse)
def get_wallet(agent_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> WalletResponse:
    try:
        wallet = sdk.get_wallet(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return WalletResponse(balance=wallet.balance, hold=wallet.hold, total=wallet.total)


# ------- Payments -------

@router.post("/payments", response_model=PaymentResponse)
def make_payment(payload: PaymentRequest, sdk: AgentPaySDK = Depends(get_sdk)) -> PaymentResponse:
    res = sdk.pay(
        from_agent=payload.from_agent,
        to_agent=payload.to_agent,
        amount=payload.amount,
        memo=payload.memo,
        idempotency_key=payload.idempotency_key,
    )
    return PaymentResponse(
        success=res.success,
        intent_id=res.payment_intent.intent_id,
        status=res.payment_intent.status.value,
        error_code=res.error_code,
        error_message=res.error_message,
    )


@router.get("/payments/{intent_id}", response_model=PaymentResponse)
def get_payment_status(intent_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> PaymentResponse:
    intent = sdk.get_payment_status(intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    return PaymentResponse(
        success=intent.status.value == "completed",
        intent_id=intent.intent_id,
        status=intent.status.value,
        error_code=None,
        error_message=intent.failure_reason,
    )


# ------- Escrow -------

@router.post("/escrows", response_model=EscrowResponse)
def create_escrow(payload: CreateEscrowRequest, sdk: AgentPaySDK = Depends(get_sdk)) -> EscrowResponse:
    res = sdk.create_escrow(payload.from_agent, payload.to_agent, payload.amount, memo=payload.memo)
    if not res.success:
        return EscrowResponse(success=False, error_message=res.error_message)
    return EscrowResponse(success=True, escrow_id=res.escrow.escrow_id, status=res.escrow.status.value)


@router.post("/escrows/{escrow_id}/release", response_model=EscrowResponse)
def release_escrow(escrow_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> EscrowResponse:
    res = sdk.release_escrow(escrow_id)
    if not res.success:
        return EscrowResponse(success=False, error_message=res.error_message)
    return EscrowResponse(success=True, escrow_id=res.escrow.escrow_id, status=res.escrow.status.value)


@router.post("/escrows/{escrow_id}/cancel", response_model=EscrowResponse)
def cancel_escrow(escrow_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> EscrowResponse:
    res = sdk.cancel_escrow(escrow_id)
    if not res.success:
        return EscrowResponse(success=False, error_message=res.error_message)
    return EscrowResponse(success=True, escrow_id=res.escrow.escrow_id, status=res.escrow.status.value)


# ------- Ledger / History -------

@router.get("/agents/{agent_id}/ledger", response_model=List[LedgerEntryResponse])
def get_agent_ledger(agent_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> List[LedgerEntryResponse]:
    entries = sdk.get_transaction_history(agent_id)
    return [
        LedgerEntryResponse(
            reference_id=e.reference_id,
            entry_type=e.entry_type.value,
            delta_amount=e.delta_amount,
            balance_after=e.balance_after,
            memo=e.memo,
        )
        for e in entries
    ]


@router.get("/transactions/{reference_id}", response_model=List[LedgerEntryResponse])
def get_by_reference(reference_id: str, sdk: AgentPaySDK = Depends(get_sdk)) -> List[LedgerEntryResponse]:
    entries = sdk.get_transaction_by_reference(reference_id)
    return [
        LedgerEntryResponse(
            reference_id=e.reference_id,
            entry_type=e.entry_type.value,
            delta_amount=e.delta_amount,
            balance_after=e.balance_after,
            memo=e.memo,
        )
        for e in entries
    ]
