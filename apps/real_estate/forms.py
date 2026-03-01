from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.forms import TAILWIND_SELECT_CLASS

from .models import Mortgage, Property, PropertyExpense, PropertyInvitation, PropertyValuation

TAILWIND_INPUT_CLASS = (
    "w-full rounded-lg border border-border px-3 py-2 text-sm"
    " shadow-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
)

TAILWIND_CHECKBOX_CLASS = "rounded border-border text-primary-600 focus:ring-primary-500"

FIELD_TOOLTIPS = {
    "purchase_price": _("The total price you paid for the property, before taxes and fees."),
    "purchase_date": _("The date the sale was finalized at the notary."),
    "welcome_tax_paid": _(
        "Also called 'mutation tax'. A one-time tax paid to the municipality "
        "when you buy a property. Your notary should have the exact amount."
    ),
    "notary_fees_purchase": _("Legal fees paid to the notary for the purchase transaction."),
    "current_valuation": _("Your best estimate of what the property is worth today."),
    "valuation_date": _("The date this valuation estimate was made."),
    "municipal_assessment": _(
        "The value assigned by your municipality for property tax purposes. "
        "Found on your municipal tax bill."
    ),
    "down_payment": _(
        "The cash amount you contributed toward the purchase. "
        "Used to calculate your ownership share if there are co-owners."
    ),
    "principal": _(
        "The total amount borrowed from the lender. "
        "Usually the purchase price minus your down payment."
    ),
    "annual_rate": _(
        "The yearly interest rate on your mortgage, as stated in your contract (e.g. 5.5)."
    ),
    "rate_type": _(
        "Fixed: rate stays the same for the term. "
        "Variable: rate can change with the market."
    ),
    "amortization_years": _(
        "Total number of years to fully pay off the mortgage. "
        "Most common in Canada: 25 years."
    ),
    "term_years": _(
        "The length of your current mortgage contract before renewal. "
        "Most common in Canada: 5 years."
    ),
    "payment_frequency": _("How often you make mortgage payments."),
    "start_date": _("The date your first mortgage payment was due."),
    "insurance_premium": _(
        "If your down payment was less than 20%, you likely paid CMHC/Sagen/Canada Guaranty "
        "insurance. This premium is usually added to the mortgage principal."
    ),
    "co_owner_email": _("The email address your co-owner uses to log in to Limpid."),
    "co_owner_down_payment": _(
        "The cash amount your co-owner contributed toward the purchase."
    ),
    "co_owner_share": _(
        "The percentage of the property your co-owner will own. Your share will be the remainder."
    ),
}


def _apply_tooltips(form):
    """Set help_text on form fields from FIELD_TOOLTIPS."""
    for field_name, tooltip in FIELD_TOOLTIPS.items():
        if field_name in form.fields:
            form.fields[field_name].help_text = tooltip


class PropertyForm(forms.ModelForm):
    down_payment = forms.DecimalField(
        label=_("Your down payment"),
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
    )
    co_owner_email = forms.EmailField(
        label=_("Co-owner email"),
        required=False,
        widget=forms.EmailInput(attrs={"class": TAILWIND_INPUT_CLASS}),
    )
    co_owner_down_payment = forms.DecimalField(
        label=_("Co-owner down payment"),
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
    )
    co_owner_share = forms.DecimalField(
        label=_("Co-owner ownership share (%)"),
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=1,
        max_value=99,
        widget=forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
    )

    class Meta:
        model = Property
        fields = [
            "name",
            "property_type",
            "usage",
            "address",
            "city",
            "province",
            "postal_code",
            "purchase_price",
            "purchase_date",
            "welcome_tax_paid",
            "notary_fees_purchase",
            "current_valuation",
            "valuation_date",
            "municipal_assessment",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "property_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "usage": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "address": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "city": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "province": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "postal_code": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "purchase_price": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "purchase_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}
            ),
            "welcome_tax_paid": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "notary_fees_purchase": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "current_valuation": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "valuation_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}
            ),
            "municipal_assessment": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("purchase_date", "valuation_date"):
            self.fields[field_name].localize = False
        _apply_tooltips(self)


class MortgageForm(forms.ModelForm):
    class Meta:
        model = Mortgage
        fields = [
            "lender",
            "principal",
            "annual_rate",
            "rate_type",
            "amortization_years",
            "term_years",
            "payment_frequency",
            "start_date",
            "insurance_premium",
        ]
        widgets = {
            "lender": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "principal": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "annual_rate": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.001"}),
            "rate_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "amortization_years": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "term_years": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "payment_frequency": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "start_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}
            ),
            "insurance_premium": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.fields["start_date"].localize = False
        _apply_tooltips(self)


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = PropertyExpense
        fields = ["expense_type", "description", "amount", "date", "increases_acb"]
        widgets = {
            "expense_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "description": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "amount": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}
            ),
            "increases_acb": forms.CheckboxInput(attrs={"class": TAILWIND_CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].localize = False


class ValuationForm(forms.ModelForm):
    class Meta:
        model = PropertyValuation
        fields = ["value", "date", "source", "note"]
        widgets = {
            "value": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}
            ),
            "source": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "note": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].localize = False


class InviteCoOwnerForm(forms.ModelForm):
    class Meta:
        model = PropertyInvitation
        fields = ["email", "down_payment"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "down_payment": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
        }
