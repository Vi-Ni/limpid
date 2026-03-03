from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Property(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ("house", _("House")),
        ("condo", _("Condo (divided co-ownership)")),
        ("condo_undivided", _("Condo (undivided co-ownership)")),
        ("duplex", _("Duplex")),
        ("triplex", _("Triplex")),
        ("land", _("Vacant land")),
        ("cottage", _("Cottage / Secondary residence")),
        ("commercial", _("Commercial property")),
    ]

    USAGE_CHOICES = [
        ("primary", _("Primary residence")),
        ("secondary", _("Secondary residence")),
        ("rental", _("Rental property")),
        ("commercial", _("Commercial")),
    ]

    name = models.CharField(_("name"), max_length=200)
    property_type = models.CharField(_("property type"), max_length=20, choices=PROPERTY_TYPE_CHOICES)
    usage = models.CharField(_("usage"), max_length=20, choices=USAGE_CHOICES)
    address = models.CharField(_("address"), max_length=500)
    city = models.CharField(_("city"), max_length=100)
    province = models.CharField(_("province"), max_length=50, default="QC")
    postal_code = models.CharField(_("postal code"), max_length=10, blank=True)

    purchase_price = models.DecimalField(_("purchase price"), max_digits=12, decimal_places=2)
    purchase_date = models.DateField(_("purchase date"))
    welcome_tax_paid = models.DecimalField(_("welcome tax paid"), max_digits=10, decimal_places=2, default=0)
    notary_fees_purchase = models.DecimalField(_("notary fees at purchase"), max_digits=10, decimal_places=2, default=0)

    current_valuation = models.DecimalField(_("current valuation"), max_digits=12, decimal_places=2)
    valuation_date = models.DateField(_("valuation date"))
    municipal_assessment = models.DecimalField(_("municipal assessment"), max_digits=12, decimal_places=2, default=0)

    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="PropertyOwnership",
        related_name="properties",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("property")
        verbose_name_plural = _("properties")
        ordering = ["-purchase_date"]

    def __str__(self):
        return self.name

    @property
    def total_invested(self):
        expenses_total = self.expenses.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
        return self.purchase_price + self.welcome_tax_paid + self.notary_fees_purchase + expenses_total

    @property
    def total_appreciation(self):
        return self.current_valuation - self.purchase_price

    @property
    def total_appreciation_pct(self):
        if self.purchase_price:
            return (self.total_appreciation / self.purchase_price) * 100
        return Decimal("0")


class PropertyOwnership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="property_ownerships")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="ownerships")
    is_admin = models.BooleanField(
        _("can edit property"),
        default=False,
        help_text=_("Can this owner edit property details?"),
    )
    down_payment = models.DecimalField(_("down payment contributed"), max_digits=12, decimal_places=2, default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "property")]
        verbose_name = _("property ownership")

    def __str__(self):
        return f"{self.user} — {self.property}"


class OwnershipPeriod(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="ownership_periods")
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"), null=True, blank=True)
    note = models.CharField(_("note"), max_length=200, blank=True)

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        end = self.end_date or "ongoing"
        return f"{self.property.name}: {self.start_date} → {end}"


class OwnershipPeriodShare(models.Model):
    period = models.ForeignKey(OwnershipPeriod, on_delete=models.CASCADE, related_name="shares")
    owner = models.ForeignKey(PropertyOwnership, on_delete=models.CASCADE, related_name="period_shares")
    share_pct = models.DecimalField(_("ownership share (%)"), max_digits=5, decimal_places=2)

    class Meta:
        unique_together = [("period", "owner")]

    def __str__(self):
        return f"{self.owner.user}: {self.share_pct}%"


class Mortgage(models.Model):
    RATE_TYPE_CHOICES = [
        ("fixed", _("Fixed")),
        ("variable", _("Variable")),
    ]

    PAYMENT_FREQUENCY_CHOICES = [
        ("monthly", _("Monthly")),
        ("biweekly", _("Bi-weekly")),
        ("accelerated_biweekly", _("Accelerated bi-weekly")),
    ]

    real_estate = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="mortgages")
    lender = models.CharField(_("lender"), max_length=200)
    principal = models.DecimalField(_("original principal"), max_digits=12, decimal_places=2)
    annual_rate = models.DecimalField(_("annual interest rate (%)"), max_digits=5, decimal_places=3)
    rate_type = models.CharField(_("rate type"), max_length=20, choices=RATE_TYPE_CHOICES, default="fixed")
    amortization_years = models.PositiveSmallIntegerField(_("amortization (years)"), default=25)
    term_years = models.PositiveSmallIntegerField(_("term (years)"), default=5)
    payment_frequency = models.CharField(
        _("payment frequency"), max_length=30, choices=PAYMENT_FREQUENCY_CHOICES, default="monthly"
    )
    start_date = models.DateField(_("start date"))
    is_active = models.BooleanField(_("active"), default=True)
    insurance_premium = models.DecimalField(_("mortgage insurance premium"), max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.lender} — {self.real_estate.name}"

    @property
    def effective_principal(self):
        return self.principal + self.insurance_premium

    @property
    def monthly_rate(self):
        r = self.annual_rate / 100
        if self.rate_type == "fixed":
            return (1 + r / 2) ** (Decimal("1") / 6) - 1
        return r / 12

    @property
    def monthly_payment(self):
        r = self.monthly_rate
        n = self.amortization_years * 12
        p = self.effective_principal
        if r == 0:
            return p / n
        return (r * p) / (1 - (1 + r) ** (-n))


class MortgagePayment(models.Model):
    mortgage = models.ForeignKey(Mortgage, on_delete=models.CASCADE, related_name="payments")
    payment_number = models.PositiveIntegerField(_("payment number"))
    date = models.DateField(_("payment date"))
    total_payment = models.DecimalField(_("total payment"), max_digits=10, decimal_places=2)
    principal_portion = models.DecimalField(_("principal portion"), max_digits=10, decimal_places=2)
    interest_portion = models.DecimalField(_("interest portion"), max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(_("balance after payment"), max_digits=12, decimal_places=2)
    paid_by = models.ForeignKey(
        PropertyOwnership, on_delete=models.SET_NULL, null=True, blank=True, related_name="mortgage_payments"
    )

    class Meta:
        ordering = ["payment_number"]
        unique_together = [("mortgage", "payment_number")]

    def __str__(self):
        return f"Payment #{self.payment_number} — {self.mortgage}"


class PropertyExpense(models.Model):
    EXPENSE_TYPE_CHOICES = [
        ("renovation", _("Renovation / Improvement")),
        ("repair", _("Repair / Maintenance")),
        ("property_tax", _("Property tax")),
        ("insurance", _("Insurance")),
        ("condo_fees", _("Condo fees")),
        ("other", _("Other")),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="expenses")
    expense_type = models.CharField(_("type"), max_length=20, choices=EXPENSE_TYPE_CHOICES)
    description = models.CharField(_("description"), max_length=300)
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    date = models.DateField(_("date"))
    increases_acb = models.BooleanField(
        _("increases cost base"),
        default=False,
        help_text=_("Capital improvements increase the adjusted cost base for tax purposes."),
    )
    paid_by = models.ForeignKey(
        PropertyOwnership, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses_paid"
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.description} — ${self.amount}"


class PropertyValuation(models.Model):
    SOURCE_CHOICES = [
        ("manual", _("Manual estimate")),
        ("appraisal", _("Professional appraisal")),
        ("municipal", _("Municipal assessment")),
        ("comparable", _("Comparable sales")),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="valuations")
    value = models.DecimalField(_("value"), max_digits=12, decimal_places=2)
    date = models.DateField(_("date"))
    source = models.CharField(_("source"), max_length=20, choices=SOURCE_CHOICES, default="manual")
    note = models.CharField(_("note"), max_length=300, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.property.name}: ${self.value} ({self.date})"


class PropertyTax(models.Model):
    TAX_TYPE_CHOICES = [
        ("municipal", _("Municipal tax")),
        ("school", _("School tax")),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="taxes")
    tax_type = models.CharField(_("tax type"), max_length=20, choices=TAX_TYPE_CHOICES)
    year = models.PositiveIntegerField(_("year"))
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)

    class Meta:
        unique_together = [("property", "tax_type", "year")]
        ordering = ["-year", "tax_type"]
        verbose_name = _("property tax")
        verbose_name_plural = _("property taxes")

    def __str__(self):
        return f"{self.get_tax_type_display()} {self.year} — ${self.amount}"


class PropertyInvitation(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField(_("invitee email"))
    down_payment = models.DecimalField(_("down payment"), max_digits=12, decimal_places=2, default=0)
    share_pct = models.DecimalField(_("ownership share (%)"), max_digits=5, decimal_places=2, default=50)
    token = models.CharField(max_length=64, unique=True)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation for {self.email} → {self.property}"


class PropertyNotification(models.Model):
    VERB_CHOICES = [
        ("invitation_sent", _("Invitation sent")),
        ("invitation_accepted", _("Invitation accepted")),
        ("co_owner_removed", _("Co-owner removed")),
        ("expense_added", _("Expense added")),
        ("expense_updated", _("Expense updated")),
        ("expense_deleted", _("Expense deleted")),
        ("tax_added", _("Tax added")),
        ("tax_updated", _("Tax updated")),
        ("tax_deleted", _("Tax deleted")),
        ("valuation_added", _("Valuation added")),
        ("valuation_updated", _("Valuation updated")),
        ("valuation_deleted", _("Valuation deleted")),
        ("property_updated", _("Property updated")),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_notifications",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    verb = models.CharField(_("action"), max_length=30, choices=VERB_CHOICES)
    description = models.CharField(_("description"), max_length=300)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.actor} → {self.recipient}: {self.verb}"
