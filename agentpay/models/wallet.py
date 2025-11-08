"""Wallet model - manages agent's balance and held funds.

This module provides the Wallet class that tracks an agent's financial state,
including available funds and funds held in reserve (e.g., for escrow).
"""

from pydantic import BaseModel, Field


class Wallet(BaseModel):
    """Represents an agent's wallet with available and held funds.
    
    A Wallet maintains two separate balances:
    1. **balance**: Funds available for immediate spending
    2. **hold**: Funds reserved (locked) for escrow, pending transactions, etc.
    
    Important Design Decisions:
    - All amounts are stored as **integers** in the smallest currency unit (e.g., cents for USD)
    - This avoids floating-point precision issues common in financial calculations
    - Balance and hold must always be non-negative (enforced by validation)
    - The total funds in a wallet = balance + hold
    
    Usage Example:
        ```python
        # Create a wallet with some initial balance
        wallet = Wallet(balance=10000, hold=0)  # $100.00 available, $0.00 held
        
        # Check if agent can spend an amount
        if wallet.can_spend(5000):  # Can spend $50.00?
            print("Sufficient funds")
        
        # Check total funds
        print(f"Total: ${wallet.total / 100:.2f}")
        ```
    
    Attributes:
        balance (int): Available funds that can be spent immediately. Must be >= 0.
                      Stored in smallest unit (e.g., cents). Default: 0
        hold (int): Funds reserved for escrow, pending payouts, or other holds.
                   These funds are owned by the agent but cannot be spent until released.
                   Must be >= 0. Stored in smallest unit. Default: 0
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
        """Calculate total funds in wallet (available + held).
        
        This is the sum of all funds the agent owns, whether they are
        available for spending (balance) or temporarily held (hold).
        
        Returns:
            int: Total funds in smallest unit (balance + hold)
            
        Example:
            ```python
            wallet = Wallet(balance=7500, hold=2500)
            print(wallet.total)  # 10000 (representing $100.00)
            ```
        """
        return self.balance + self.hold
    
    def can_spend(self, amount: int) -> bool:
        """Check if wallet has sufficient available balance for a transaction.
        
        This method checks only the **available balance**, not held funds.
        Held funds cannot be spent until they are released back to the balance.
        
        Args:
            amount (int): Amount to check, in smallest unit (e.g., cents)
            
        Returns:
            bool: True if balance >= amount, False otherwise
            
        Example:
            ```python
            wallet = Wallet(balance=10000, hold=5000)
            wallet.can_spend(8000)   # False - only 10000 available, not 15000
            wallet.can_spend(10000)  # True - exact amount available
            wallet.can_spend(5000)   # True - less than available
            ```
        """
        return self.balance >= amount
    
    def can_hold(self, amount: int) -> bool:
        """Check if wallet has sufficient balance to move funds to hold.
        
        This checks if there is enough available balance to lock into hold
        (e.g., for creating an escrow). The funds must come from the available
        balance, not from already-held funds.
        
        Args:
            amount (int): Amount to potentially move to hold, in smallest unit
            
        Returns:
            bool: True if balance >= amount (can lock this amount), False otherwise
            
        Note:
            This is a check only - it does not actually move funds. The actual
            movement happens in the ledger operations during escrow creation.
            
        Example:
            ```python
            wallet = Wallet(balance=10000, hold=0)
            if wallet.can_hold(3000):
                # Proceed with escrow creation that will lock 3000
                pass
            ```
        """
        return self.balance >= amount
