from django.utils.translation import gettext_lazy as _

TERM_TOOLTIPS = {
    "value": _(
        "The estimated current market value of the entire property. This is what you'd expect to sell it for today."
    ),
    "equity": _(
        "The portion of the property you truly own — the value minus what you still owe on the mortgage. "
        "Think of it as your 'net worth' in this property."
    ),
    "mortgage": _(
        "The remaining amount you owe to the bank. This decreases with each payment as you pay down the principal."
    ),
    "your_share": _(
        "Your personal portion of the equity, based on your ownership percentage. "
        "If you own 50% of a property with $200k equity, your share is $100k."
    ),
    "purchase_price": _(
        "The total price you paid for the property when you bought it, before taxes and closing costs."
    ),
    "appreciation": _(
        "How much the property value has increased (or decreased) since you bought it. "
        "Calculated as: current value minus purchase price."
    ),
    "your_valuation_share": _("Your portion of the total property value, based on your ownership percentage."),
    "your_mortgage_share": _("Your portion of the remaining mortgage debt, based on your ownership percentage."),
    "down_payment": _(
        "The cash you contributed upfront when purchasing the property. "
        "A larger down payment means less mortgage debt and lower insurance costs."
    ),
    "principal_paid": _(
        "The total amount of mortgage principal you've paid off so far. "
        "This is the portion of your payments that actually reduces your debt."
    ),
    "monthly_payment": _(
        "Your regular mortgage payment amount, including both principal and interest. "
        "Principal reduces your debt; interest is the cost of borrowing."
    ),
    "remaining_balance": _(
        "How much you still owe on the mortgage. This decreases with each payment as you chip away at the principal."
    ),
    "sale_price": _(
        "The assumed selling price. By default, this is your current property valuation. "
        "Adjust it to simulate different scenarios."
    ),
    "mortgage_balance": _("The remaining amount owed on your mortgage at the time of sale."),
    "gross_equity": _("Sale price minus the remaining mortgage. This is what you'd have before paying selling costs."),
    "notary_fees": _("Legal fees for the sale transaction, paid to the notary who handles the paperwork."),
    "total_costs": _("All costs associated with selling: agent fees, notary fees, and taxes."),
    "net_proceeds": _(
        "What you actually take home after selling — the sale price minus the mortgage and all selling costs. "
        "This is your real profit from the sale."
    ),
    "equity_breakdown": _(
        "A visual split of how much of the property value is yours (equity) vs. still owed to the bank."
    ),
    "payment_breakdown": _(
        "How your mortgage payments are split between principal (paying down debt) and interest (cost of borrowing)."
    ),
    "expenses_by_type": _(
        "A breakdown of all expenses you've recorded by category — renovations, maintenance, insurance, etc."
    ),
    "ownership": _(
        "Who owns this property and their respective share percentages. "
        "Shares can change when co-owners are added or removed."
    ),
    "lender": _("The bank or financial institution that provided your mortgage."),
    "your_equity": _(
        "Your personal equity — how much of the property's net value belongs to you. "
        "Calculated as: total equity multiplied by your ownership percentage."
    ),
    "total_interest_paid": _(
        "The total amount of interest you've paid since the start of your mortgage. "
        "This is the cost of borrowing — it doesn't reduce your debt."
    ),
    "total_paid": _("The total amount you've paid to date, combining both principal and interest portions."),
    "original_principal": _(
        "The total amount originally borrowed, including any mortgage insurance premium added to the loan."
    ),
    "annual_rate": _("The yearly interest rate on your mortgage, as stated in your contract."),
    "rate": _(
        "The annual interest rate on your mortgage. "
        "Fixed means it stays the same for your term; variable means it can change with the market."
    ),
}

TERM_TOOLTIPS_CA = {
    "amortization": _(
        "The total number of years to fully pay off the mortgage. "
        "In Canada, 25 years is the most common amortization period."
    ),
    "agent_commission": _(
        "The real estate agent's fee, typically 4-6% of the sale price in Canada. "
        "This includes applicable sales taxes (GST/QST)."
    ),
    "capital_gains_tax": _(
        "If this isn't your primary residence, you may owe tax on the profit. "
        "In Canada, 50% of the capital gain is taxable at your marginal rate."
    ),
    "insurance_premium": _(
        "If your down payment was less than 20%, you likely paid CMHC/Sagen/Canada Guaranty "
        "insurance. This premium is usually added to the mortgage principal."
    ),
}

TERM_TOOLTIPS_FR = {
    "amortization": _(
        "The total duration of your mortgage in years. "
        "In France, 20 or 25 years is most common. Maximum allowed: 25 years."
    ),
    "agent_commission": _(
        "The real estate agent's fee, typically 3-6% of the sale price in France. This includes 20% TVA."
    ),
    "capital_gains_tax": _(
        "If this isn't your primary residence, you owe plus-value tax on the profit: "
        "19% income tax + 17.2% social contributions. Abatements apply based on how long "
        "you've owned the property — full IR exemption after 22 years, full social exemption after 30."
    ),
    "borrower_insurance_rate": _(
        "Assurance emprunteur — mandatory insurance covering death, disability, and job loss. "
        "Paid monthly on top of your mortgage payment. Typical rate: 0.15-0.50% per year of the loan amount."
    ),
    "frais_notaire": _(
        "The 'frais de notaire' include transfer taxes (droits de mutation), notary fees, "
        "and administrative costs. For existing properties: 7-8.5% of the price. "
        "For new builds: 2-3% (VAT is included in the purchase price instead)."
    ),
    "taxe_fonciere": _(
        "Annual property tax paid to the municipality. Based on the cadastral value "
        "and local tax rates. Varies widely by location."
    ),
    "taxe_habitation": _(
        "Abolished for all primary residences since 2023. Still applies to "
        "secondary residences, with possible surcharges in high-demand areas."
    ),
    "ifi": _(
        "Wealth tax on real estate (Impot sur la Fortune Immobiliere). "
        "Applies if your total net real estate exceeds 1,300,000 EUR. "
        "Primary residence benefits from a 30% valuation abatement."
    ),
}


def get_tooltips(country="CA"):
    tips = dict(TERM_TOOLTIPS)
    if country == "FR":
        tips.update(TERM_TOOLTIPS_FR)
    else:
        tips.update(TERM_TOOLTIPS_CA)
    return tips
