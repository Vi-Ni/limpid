from django.contrib import admin

from .models import (
    Mortgage,
    MortgagePayment,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyExpense,
    PropertyInvitation,
    PropertyOwnership,
    PropertyValuation,
)


class PropertyOwnershipInline(admin.TabularInline):
    model = PropertyOwnership
    extra = 0


class MortgageInline(admin.TabularInline):
    model = Mortgage
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["name", "property_type", "usage", "city", "purchase_price", "current_valuation"]
    list_filter = ["property_type", "usage", "province"]
    search_fields = ["name", "address", "city"]
    inlines = [PropertyOwnershipInline, MortgageInline]


@admin.register(PropertyOwnership)
class PropertyOwnershipAdmin(admin.ModelAdmin):
    list_display = ["user", "property", "is_admin", "down_payment"]
    list_filter = ["is_admin"]


@admin.register(Mortgage)
class MortgageAdmin(admin.ModelAdmin):
    list_display = ["real_estate", "lender", "principal", "annual_rate", "rate_type", "is_active"]
    list_filter = ["rate_type", "is_active"]


@admin.register(MortgagePayment)
class MortgagePaymentAdmin(admin.ModelAdmin):
    list_display = ["mortgage", "payment_number", "date", "total_payment", "principal_portion", "interest_portion"]
    list_filter = ["mortgage"]


@admin.register(OwnershipPeriod)
class OwnershipPeriodAdmin(admin.ModelAdmin):
    list_display = ["property", "start_date", "end_date"]


@admin.register(OwnershipPeriodShare)
class OwnershipPeriodShareAdmin(admin.ModelAdmin):
    list_display = ["period", "owner", "share_pct"]


@admin.register(PropertyExpense)
class PropertyExpenseAdmin(admin.ModelAdmin):
    list_display = ["property", "expense_type", "description", "amount", "date", "increases_acb"]
    list_filter = ["expense_type", "increases_acb"]


@admin.register(PropertyValuation)
class PropertyValuationAdmin(admin.ModelAdmin):
    list_display = ["property", "value", "date", "source"]
    list_filter = ["source"]


@admin.register(PropertyInvitation)
class PropertyInvitationAdmin(admin.ModelAdmin):
    list_display = ["property", "email", "invited_by", "accepted", "created_at"]
    list_filter = ["accepted"]
