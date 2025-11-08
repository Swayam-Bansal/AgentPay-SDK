"""Payment Engine - high-level payment orchestration.

The PaymentEngine provides the main API for executing payments. It:
- Validates PaymentIntents
- Enforces policies before execution
- Handles idempotency
- Orchestrates ledger and wallet updates
- Provides clear success/failure responses

This is the primary interface that applications use to process payments.
"""

from typing import Dict, Optional
from agentpay.models import PaymentIntent, PaymentStatus
from agentpay.agent_registry import AgentRegistry
from agentpay.ledger_manager import LedgerManager


class PaymentResult:
    """Result of a payment operation.
    
    Encapsulates the outcome of a payment attempt, including success/failure
    status, the updated payment intent, and any error information.
    
    Attributes:
        success (bool): True if payment succeeded, False otherwise
        payment_intent (PaymentIntent): The payment intent with updated status
        error_code (Optional[str]): Error code if failed (e.g., "INSUFFICIENT_FUNDS")
        error_message (Optional[str]): Human-readable error description
    """
    
    def __init__(self, success: bool, payment_intent: PaymentIntent,
                 error_code: Optional[str] = None, error_message: Optional[str] = None):
        self.success = success
        self.payment_intent = payment_intent
        self.error_code = error_code
        self.error_message = error_message
    
    def __repr__(self) -> str:
        if self.success:
            return f"PaymentResult(success=True, intent_id={self.payment_intent.intent_id})"
        return f"PaymentResult(success=False, error={self.error_code})"


class PaymentEngine:
    """Engine for executing payments with policy enforcement and idempotency.
    
    The PaymentEngine is the main entry point for processing payments. It provides
    a high-level API that handles the complete payment workflow:
    
    1. Create PaymentIntent (request)
    2. Validate agents exist
    3. Check payer's policy (paused, allowlist, limits)
    4. Verify sufficient funds
    5. Execute transfer via LedgerManager
    6. Update PaymentIntent status
    7. Return structured result
    
    Idempotency:
        If a PaymentIntent with the same idempotency_key has already been processed,
        returns the existing result instead of reprocessing.
    
    Usage Example:
        ```python
        registry = AgentRegistry()
        ledger = LedgerManager(registry)
        engine = PaymentEngine(registry, ledger)
        
        # Register and fund agents
        alice = Agent(agent_id="alice")
        bob = Agent(agent_id="bob")
        registry.register_agent(alice)
        registry.register_agent(bob)
        ledger.record_top_up("alice", 10000, "topup-1")
        
        # Create and execute payment
        intent = PaymentIntent(
            from_agent_id="alice",
            to_agent_id="bob",
            amount=5000,
            memo="Payment for services"
        )
        
        result = engine.execute_payment(intent)
        if result.success:
            print(f"Payment completed! Intent ID: {intent.intent_id}")
        else:
            print(f"Payment failed: {result.error_message}")
        ```
    """
    
    def __init__(self, agent_registry: AgentRegistry, ledger_manager: LedgerManager):
        """Initialize the payment engine.
        
        Args:
            agent_registry (AgentRegistry): Registry for accessing agents
            ledger_manager (LedgerManager): Ledger for recording transactions
        """
        self.agent_registry = agent_registry
        self.ledger_manager = ledger_manager
        self._processed_intents: Dict[str, PaymentIntent] = {}  # For idempotency
    
    def execute_payment(self, payment_intent: PaymentIntent) -> PaymentResult:
        """Execute a payment with full validation and error handling.
        
        This is the main payment execution method. It performs all necessary checks,
        executes the transfer if valid, and returns a structured result.
        
        Workflow:
        1. Check idempotency (if key provided)
        2. Validate both agents exist
        3. Check payer can pay (policy + funds)
        4. Execute transfer via ledger
        5. Mark intent as completed
        6. Store for idempotency
        7. Return success result
        
        If any step fails, the intent is marked failed and an error result is returned.
        
        Args:
            payment_intent (PaymentIntent): The payment to execute
            
        Returns:
            PaymentResult: Result with success status and updated intent
            
        Example:
            ```python
            intent = PaymentIntent(
                from_agent_id="alice",
                to_agent_id="bob",
                amount=1000,
                idempotency_key="payment-2024-001"
            )
            
            result = engine.execute_payment(intent)
            
            if result.success:
                print("Payment successful!")
                print(f"Intent status: {result.payment_intent.status}")
            else:
                print(f"Failed: {result.error_code}")
                print(f"Reason: {result.error_message}")
            ```
        """
        # Check idempotency
        if payment_intent.idempotency_key:
            existing = self._processed_intents.get(payment_intent.idempotency_key)
            if existing:
                return PaymentResult(
                    success=existing.status == PaymentStatus.COMPLETED,
                    payment_intent=existing,
                    error_code=existing.failure_reason if existing.failure_reason else None,
                    error_message=f"Already processed: {existing.status.value}"
                )
        
        # Validate agents exist
        from_agent = self.agent_registry.get_agent(payment_intent.from_agent_id)
        to_agent = self.agent_registry.get_agent(payment_intent.to_agent_id)
        
        if from_agent is None:
            payment_intent.mark_failed("PAYER_NOT_FOUND")
            return self._failed_result(
                payment_intent,
                "PAYER_NOT_FOUND",
                f"Payer agent {payment_intent.from_agent_id} not found"
            )
        
        if to_agent is None:
            payment_intent.mark_failed("PAYEE_NOT_FOUND")
            return self._failed_result(
                payment_intent,
                "PAYEE_NOT_FOUND",
                f"Payee agent {payment_intent.to_agent_id} not found"
            )
        
        # Check if payer can make this payment (policy + funds)
        can_pay, reason = from_agent.can_pay(payment_intent.amount, payment_intent.to_agent_id)
        
        if not can_pay:
            payment_intent.mark_failed(reason)
            return self._failed_result(
                payment_intent,
                reason,
                self._get_error_message(reason)
            )
        
        # Execute the payment via ledger
        try:
            self.ledger_manager.record_payment(
                from_agent_id=payment_intent.from_agent_id,
                to_agent_id=payment_intent.to_agent_id,
                amount=payment_intent.amount,
                reference_id=payment_intent.intent_id,
                memo=payment_intent.memo
            )
            
            # Mark as completed
            payment_intent.mark_completed()
            
            # Store for idempotency
            if payment_intent.idempotency_key:
                self._processed_intents[payment_intent.idempotency_key] = payment_intent
            
            return PaymentResult(
                success=True,
                payment_intent=payment_intent
            )
            
        except Exception as e:
            # Unexpected error during execution
            payment_intent.mark_failed("EXECUTION_ERROR")
            return self._failed_result(
                payment_intent,
                "EXECUTION_ERROR",
                f"Payment execution failed: {str(e)}"
            )
    
    def _failed_result(self, payment_intent: PaymentIntent, 
                      error_code: str, error_message: str) -> PaymentResult:
        """Create a failed PaymentResult.
        
        Helper method to construct error results consistently.
        
        Args:
            payment_intent (PaymentIntent): The failed payment intent
            error_code (str): Error code constant
            error_message (str): Human-readable error description
            
        Returns:
            PaymentResult: Failed result
        """
        # Store for idempotency even if failed
        if payment_intent.idempotency_key:
            self._processed_intents[payment_intent.idempotency_key] = payment_intent
        
        return PaymentResult(
            success=False,
            payment_intent=payment_intent,
            error_code=error_code,
            error_message=error_message
        )
    
    def _get_error_message(self, error_code: str) -> str:
        """Get human-readable error message for error code.
        
        Args:
            error_code (str): The error code constant
            
        Returns:
            str: Human-readable message
        """
        messages = {
            "AGENT_PAUSED": "Payment blocked: agent is paused",
            "RECIPIENT_NOT_ALLOWED": "Payment blocked: recipient not in allowlist",
            "AMOUNT_EXCEEDS_LIMIT": "Payment blocked: amount exceeds per-transaction limit",
            "INSUFFICIENT_FUNDS": "Payment failed: insufficient balance",
            "PAYER_NOT_FOUND": "Payment failed: payer agent does not exist",
            "PAYEE_NOT_FOUND": "Payment failed: payee agent does not exist",
        }
        return messages.get(error_code, f"Payment failed: {error_code}")
    
    def get_payment_status(self, intent_id: str) -> Optional[PaymentIntent]:
        """Get the status of a payment by intent ID.
        
        Args:
            intent_id (str): The payment intent ID
            
        Returns:
            Optional[PaymentIntent]: The intent if found, None otherwise
            
        Note:
            This only finds intents that have been processed through this engine.
            For a complete view, check the ledger entries.
        """
        # Search through processed intents by idempotency key
        for intent in self._processed_intents.values():
            if intent.intent_id == intent_id:
                return intent
        return None
    
    def clear_idempotency_cache(self) -> None:
        """Clear the idempotency cache.
        
        Warning:
            This is for testing only. In production, idempotency records should
            persist (e.g., in a database) to handle restarts.
        """
        self._processed_intents.clear()
