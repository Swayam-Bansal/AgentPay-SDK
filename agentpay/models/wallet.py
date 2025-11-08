"""Wallet model - manages agent's balance and held funds."""

from pydantic import BaseModel, Field


class Wallet(BaseModel):
    """Represents an agent's wallet with available and held funds.
    
    All amounts are stored as integers in the smallest unit (e.g., cents).
    This avoids floating-point precision issues.
    
    Attributes:
        balance: Available funds that can be spent
        hold: Funds reserved for escrow, pending payouts, etc.
    """
    
    balance: int = Field(
        default=0,
        ge=0,
        description="Available funds in smallest unit (e.g., cents)"
    )
    hold: int = Field(
        default=0,
        ge=0,
        description="Reserved funds not available for spending"
    )
    
    @property
    def total(self) -> int:
        """Total funds in wallet (balance + hold)."""
        return self.balance + self.hold
    
    def can_spend(self, amount: int) -> bool:
        """Check if wallet has sufficient available balance."""
        return self.balance >= amount
    
    def can_hold(self, amount: int) -> bool:
        """Check if wallet has sufficient balance to move to hold."""
        return self.balance >= amount
