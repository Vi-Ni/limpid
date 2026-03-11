from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.forms import TAILWIND_SELECT_CLASS

from .models import Mortgage, Property, PropertyExpense, PropertyInvitation, PropertyTax, PropertyValuation

TAILWIND_INPUT_CLASS = "input"

DEPARTEMENT_CHOICES = [
    ("", "---------"),
    ("01", "01 - Ain"),
    ("02", "02 - Aisne"),
    ("03", "03 - Allier"),
    ("04", "04 - Alpes-de-Haute-Provence"),
    ("05", "05 - Hautes-Alpes"),
    ("06", "06 - Alpes-Maritimes"),
    ("07", "07 - Ardèche"),
    ("08", "08 - Ardennes"),
    ("09", "09 - Ariège"),
    ("10", "10 - Aube"),
    ("11", "11 - Aude"),
    ("12", "12 - Aveyron"),
    ("13", "13 - Bouches-du-Rhône"),
    ("14", "14 - Calvados"),
    ("15", "15 - Cantal"),
    ("16", "16 - Charente"),
    ("17", "17 - Charente-Maritime"),
    ("18", "18 - Cher"),
    ("19", "19 - Corrèze"),
    ("2A", "2A - Corse-du-Sud"),
    ("2B", "2B - Haute-Corse"),
    ("21", "21 - Côte-d'Or"),
    ("22", "22 - Côtes-d'Armor"),
    ("23", "23 - Creuse"),
    ("24", "24 - Dordogne"),
    ("25", "25 - Doubs"),
    ("26", "26 - Drôme"),
    ("27", "27 - Eure"),
    ("28", "28 - Eure-et-Loir"),
    ("29", "29 - Finistère"),
    ("30", "30 - Gard"),
    ("31", "31 - Haute-Garonne"),
    ("32", "32 - Gers"),
    ("33", "33 - Gironde"),
    ("34", "34 - Hérault"),
    ("35", "35 - Ille-et-Vilaine"),
    ("36", "36 - Indre"),
    ("37", "37 - Indre-et-Loire"),
    ("38", "38 - Isère"),
    ("39", "39 - Jura"),
    ("40", "40 - Landes"),
    ("41", "41 - Loir-et-Cher"),
    ("42", "42 - Loire"),
    ("43", "43 - Haute-Loire"),
    ("44", "44 - Loire-Atlantique"),
    ("45", "45 - Loiret"),
    ("46", "46 - Lot"),
    ("47", "47 - Lot-et-Garonne"),
    ("48", "48 - Lozère"),
    ("49", "49 - Maine-et-Loire"),
    ("50", "50 - Manche"),
    ("51", "51 - Marne"),
    ("52", "52 - Haute-Marne"),
    ("53", "53 - Mayenne"),
    ("54", "54 - Meurthe-et-Moselle"),
    ("55", "55 - Meuse"),
    ("56", "56 - Morbihan"),
    ("57", "57 - Moselle"),
    ("58", "58 - Nièvre"),
    ("59", "59 - Nord"),
    ("60", "60 - Oise"),
    ("61", "61 - Orne"),
    ("62", "62 - Pas-de-Calais"),
    ("63", "63 - Puy-de-Dôme"),
    ("64", "64 - Pyrénées-Atlantiques"),
    ("65", "65 - Hautes-Pyrénées"),
    ("66", "66 - Pyrénées-Orientales"),
    ("67", "67 - Bas-Rhin"),
    ("68", "68 - Haut-Rhin"),
    ("69", "69 - Rhône"),
    ("70", "70 - Haute-Saône"),
    ("71", "71 - Saône-et-Loire"),
    ("72", "72 - Sarthe"),
    ("73", "73 - Savoie"),
    ("74", "74 - Haute-Savoie"),
    ("75", "75 - Paris"),
    ("76", "76 - Seine-Maritime"),
    ("77", "77 - Seine-et-Marne"),
    ("78", "78 - Yvelines"),
    ("79", "79 - Deux-Sèvres"),
    ("80", "80 - Somme"),
    ("81", "81 - Tarn"),
    ("82", "82 - Tarn-et-Garonne"),
    ("83", "83 - Var"),
    ("84", "84 - Vaucluse"),
    ("85", "85 - Vendée"),
    ("86", "86 - Vienne"),
    ("87", "87 - Haute-Vienne"),
    ("88", "88 - Vosges"),
    ("89", "89 - Yonne"),
    ("90", "90 - Territoire de Belfort"),
    ("91", "91 - Essonne"),
    ("92", "92 - Hauts-de-Seine"),
    ("93", "93 - Seine-Saint-Denis"),
    ("94", "94 - Val-de-Marne"),
    ("95", "95 - Val-d'Oise"),
    ("971", "971 - Guadeloupe"),
    ("972", "972 - Martinique"),
    ("973", "973 - Guyane"),
    ("974", "974 - La Réunion"),
    ("976", "976 - Mayotte"),
]

TAILWIND_CHECKBOX_CLASS = "rounded border-border text-primary-600 focus:ring-primary-500"

FIELD_TOOLTIPS = {
    "purchase_price": _("The total price you paid for the property, before taxes and fees."),
    "purchase_date": _("The date the sale was finalized at the notary."),
    "current_valuation": _("Your best estimate of what the property is worth today."),
    "valuation_date": _("The date this valuation estimate was made."),
    "down_payment": _(
        "The cash amount you contributed toward the purchase. "
        "Used to calculate your ownership share if there are co-owners."
    ),
    "principal": _("The total amount borrowed from the lender. Usually the purchase price minus your down payment."),
    "annual_rate": _("The yearly interest rate on your mortgage, as stated in your contract (e.g. 5.5)."),
    "rate_type": _("Fixed: rate stays the same for the term. Variable: rate can change with the market."),
    "payment_frequency": _("How often you make mortgage payments."),
    "start_date": _("The date your first mortgage payment was due."),
    "co_owner_email": _("The email address your co-owner uses to log in to Limpid."),
    "co_owner_down_payment": _("The cash amount your co-owner contributed toward the purchase."),
    "co_owner_share": _("The percentage of the property your co-owner will own. Your share will be the remainder."),
}

FIELD_TOOLTIPS_CA = {
    "welcome_tax_paid": _(
        "Also called 'mutation tax'. A one-time tax paid to the municipality "
        "when you buy a property. Your notary should have the exact amount."
    ),
    "notary_fees_purchase": _("Legal fees paid to the notary for the purchase transaction."),
    "municipal_assessment": _(
        "The value assigned by your municipality for property tax purposes. Found on your municipal tax bill."
    ),
    "amortization_years": _("Total number of years to fully pay off the mortgage. Most common in Canada: 25 years."),
    "term_years": _("The length of your current mortgage contract before renewal. Most common in Canada: 5 years."),
    "insurance_premium": _(
        "If your down payment was less than 20%, you likely paid CMHC/Sagen/Canada Guaranty "
        "insurance. This premium is usually added to the mortgage principal."
    ),
}

FIELD_TOOLTIPS_FR = {
    "welcome_tax_paid": _(
        "Total 'frais de notaire' paid at purchase. Includes transfer taxes (droits de mutation), "
        "notary fees, and administrative costs. Typically 7-8.5% for existing properties, "
        "2-3% for new builds."
    ),
    "notary_fees_purchase": _("Real estate agent fees paid at purchase, if any."),
    "municipal_assessment": _(
        "The cadastral rental value (valeur locative cadastrale) used to calculate taxe foncière. "
        "Found on your taxe foncière notice."
    ),
    "amortization_years": _(
        "Total mortgage duration in years. Most common in France: 20 or 25 years. "
        "Maximum allowed by regulation: 25 years."
    ),
    "borrower_insurance_rate": _(
        "Annual rate for assurance emprunteur (e.g. 0.30 for 0.30%). "
        "Required by all French banks. Typical rates: 0.15-0.50% depending on age."
    ),
}


def _apply_tooltips(form, country="CA"):
    for field_name, tooltip in FIELD_TOOLTIPS.items():
        if field_name in form.fields:
            form.fields[field_name].help_text = tooltip
    overrides = FIELD_TOOLTIPS_FR if country == "FR" else FIELD_TOOLTIPS_CA
    for field_name, tooltip in overrides.items():
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
            "country",
            "property_type",
            "usage",
            "currency",
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
            "country": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "property_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "usage": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "currency": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "address": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "city": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "province": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "postal_code": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "purchase_price": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "purchase_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}),
            "welcome_tax_paid": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "notary_fees_purchase": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "current_valuation": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "valuation_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}),
            "municipal_assessment": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("purchase_date", "valuation_date"):
            self.fields[field_name].localize = False

        country = self._get_country()
        if country == "FR":
            self.fields["province"].label = _("Département")
            self.fields["province"].widget = forms.Select(
                attrs={"class": TAILWIND_SELECT_CLASS}, choices=DEPARTEMENT_CHOICES
            )
            self.fields["welcome_tax_paid"].label = _("Frais de notaire (achat)")
            self.fields["notary_fees_purchase"].label = _("Frais d'agence (achat)")
            self.fields["municipal_assessment"].label = _("Valeur cadastrale")

        _apply_tooltips(self, country)

    def _get_country(self):
        if self.instance and self.instance.pk:
            return self.instance.country
        if self.data:
            return self.data.get("country", "CA")
        return self.initial.get("country", "CA")


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
            "borrower_insurance_rate",
        ]
        widgets = {
            "lender": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "principal": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "annual_rate": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.001"}),
            "rate_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "amortization_years": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "term_years": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "payment_frequency": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}),
            "insurance_premium": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "borrower_insurance_rate": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.001"}),
        }

    def __init__(self, *args, country="CA", **kwargs):
        super().__init__(*args, **kwargs)
        self.country = country
        for field in self.fields.values():
            field.required = False
        self.fields["start_date"].localize = False

        if country == "FR":
            self.fields["amortization_years"].label = _("Loan duration (years)")

        _apply_tooltips(self, country)


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = PropertyExpense
        fields = ["expense_type", "description", "amount", "date", "increases_acb"]
        widgets = {
            "expense_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "description": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "amount": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}),
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
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}),
            "source": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "note": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].localize = False


class PropertyTaxForm(forms.ModelForm):
    CA_TAX_TYPES = [("municipal", _("Municipal tax")), ("school", _("School tax"))]
    FR_TAX_TYPES = [
        ("taxe_fonciere", _("Taxe foncière")),
        ("taxe_habitation", _("Taxe d'habitation")),
        ("ifi", _("IFI (wealth tax)")),
    ]

    class Meta:
        model = PropertyTax
        fields = ["tax_type", "year", "amount"]
        widgets = {
            "tax_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "year": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "amount": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
        }

    def __init__(self, *args, country="CA", **kwargs):
        super().__init__(*args, **kwargs)
        if country == "FR":
            self.fields["tax_type"].choices = self.FR_TAX_TYPES
        else:
            self.fields["tax_type"].choices = self.CA_TAX_TYPES


class InviteCoOwnerForm(forms.ModelForm):
    class Meta:
        model = PropertyInvitation
        fields = ["email", "down_payment"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": TAILWIND_INPUT_CLASS}),
            "down_payment": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
        }
