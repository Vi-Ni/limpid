from django.contrib import admin

from .models import Holding, Portfolio, Transaction


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_sandbox", "created_at"]
    list_filter = ["is_sandbox"]
    search_fields = ["name", "user__email"]


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ["portfolio", "asset", "quantity", "average_cost"]
    list_filter = ["asset__asset_type"]
    search_fields = ["asset__ticker", "portfolio__name"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["portfolio", "asset", "transaction_type", "quantity", "price", "executed_at"]
    list_filter = ["transaction_type", "asset__asset_type"]
    search_fields = ["asset__ticker", "portfolio__name"]
