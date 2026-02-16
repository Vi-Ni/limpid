from django.db import models
from django.utils.translation import gettext_lazy as _


class Asset(models.Model):
    ASSET_TYPE_CHOICES = [
        ("etf", _("ETF")),
        ("stock", _("Stock")),
        ("bond", _("Bond")),
        ("gic", _("GIC")),
        ("cash", _("Cash")),
    ]

    CURRENCY_CHOICES = [
        ("CAD", "CAD"),
        ("USD", "USD"),
    ]

    ticker = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPE_CHOICES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CAD")
    sector = models.CharField(max_length=100, blank=True, default="")
    geography = models.CharField(max_length=100, blank=True, default="")
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    previous_close = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = _("asset")
        verbose_name_plural = _("assets")
        ordering = ["ticker"]

    def __str__(self):
        return f"{self.ticker} — {self.name}"

    @property
    def daily_change(self):
        if self.previous_close:
            return self.current_price - self.previous_close
        return 0

    @property
    def daily_change_pct(self):
        if self.previous_close:
            return (self.daily_change / self.previous_close) * 100
        return 0
