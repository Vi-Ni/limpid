from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.market_data.models import Asset


class Portfolio(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    name = models.CharField(max_length=200)
    is_sandbox = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("portfolio")
        verbose_name_plural = _("portfolios")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"


class Holding(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    average_cost = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _("holding")
        verbose_name_plural = _("holdings")
        unique_together = [("portfolio", "asset")]

    def __str__(self):
        return f"{self.asset.ticker} x{self.quantity}"

    @property
    def market_value(self):
        return self.quantity * self.asset.current_price

    @property
    def total_cost(self):
        return self.quantity * self.average_cost

    @property
    def gain_loss(self):
        return self.market_value - self.total_cost

    @property
    def gain_loss_pct(self):
        if self.total_cost:
            return (self.gain_loss / self.total_cost) * 100
        return 0


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("buy", _("Buy")),
        ("sell", _("Sell")),
    ]

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    fees = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    executed_at = models.DateTimeField()

    class Meta:
        verbose_name = _("transaction")
        verbose_name_plural = _("transactions")
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.transaction_type} {self.asset.ticker} x{self.quantity}"
