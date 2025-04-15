# core/models.py
from django.db import models

class User(models.Model):
    """
    Stores Amina’s details: phone number, PIN, Celo wallet, and cUSD balance.
    - phone: Unique identifier (e.g., "+254123456789").
    - pin: 4-digit security code (stored as string for simplicity).
    - celo_address: Mock blockchain address for test mode (e.g., "0x123...").
    - balance: cUSD saved in MamaJamii Fund (default 0).
    """
    phone = models.CharField(max_length=15, unique=True, help_text="E.g., +254123456789")
    pin = models.CharField(max_length=4, help_text="4-digit PIN, e.g., 1234")
    celo_address = models.CharField(max_length=42, unique=True, help_text="Mock Celo address")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="cUSD balance")

    def __str__(self):
        return self.phone

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

class Transaction(models.Model):
    """
    Logs deposits/withdrawals for Amina’s savings.
    - user: Links to User (Amina).
    - tx_hash: Mock blockchain tx (e.g., "0x123...").
    - amount: cUSD value (e.g., 1.00 for deposit, 10.00 for withdrawal).
    - type: "deposit" or "withdraw".
    - timestamp: When it happened.
    """
    TYPE_CHOICES = (
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    tx_hash = models.CharField(max_length=66, help_text="Mock tx hash")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="cUSD amount")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone} - {self.type} ${self.amount}"

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"