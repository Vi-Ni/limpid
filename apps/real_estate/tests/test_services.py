from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.real_estate.models import (
    Mortgage,
    MortgageRateChange,
    OwnerMonthlyPayment,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyExpense,
    PropertyNotification,
    PropertyOwnership,
    PropertyTax,
    RentalIncome,
)
from apps.real_estate.services import (
    _calculate_acb,
    _calculate_french_capital_gains_tax,
    _calculate_french_surtax,
    calculate_monthly_cost,
    calculate_monthly_payment,
    calculate_monthly_rate,
    compute_miz,
    estimate_sale_proceeds,
    generate_amortization_schedule,
    generate_evolution_chart_data,
    generate_per_owner_amortization,
    get_current_ownership_shares,
    get_monthly_payment,
    get_owner_contributions,
    get_owner_principal_paid,
    get_owner_snapshot,
    get_ownership_comparison,
    get_property_snapshot,
    get_remaining_balance,
    get_total_paid,
    notify_co_owners,
    split_sale_by_miz,
)

User = get_user_model()

TWO_PLACES = Decimal("0.01")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", email="alice@test.com", password="testpass123")


@pytest.fixture
def user2(db):
    return User.objects.create_user(username="bob", email="bob@test.com", password="testpass123")


@pytest.fixture
def prop(user):
    p = Property.objects.create(
        name="Test House",
        property_type="house",
        usage="primary",
        address="123 Main St",
        city="Montreal",
        purchase_price=Decimal("500000"),
        purchase_date=date(2020, 1, 1),
        welcome_tax_paid=Decimal("7500"),
        notary_fees_purchase=Decimal("2000"),
        current_valuation=Decimal("600000"),
        valuation_date=date(2024, 1, 1),
    )
    PropertyOwnership.objects.create(user=user, property=p, is_admin=True, down_payment=Decimal("100000"))
    return p


@pytest.fixture
def mortgage(prop):
    return Mortgage.objects.create(
        real_estate=prop,
        lender="Test Bank",
        principal=Decimal("400000"),
        annual_rate=Decimal("5.000"),
        rate_type="fixed",
        amortization_years=25,
        term_years=5,
        start_date=date(2020, 1, 1),
    )


# ── Amortization math ────────────────────────────────────────


class TestMonthlyRate:
    def test_fixed_rate_semi_annual_compounding(self):
        rate = calculate_monthly_rate(Decimal("5.000"), "fixed")
        expected = (1 + Decimal("0.05") / 2) ** (Decimal("1") / 6) - 1
        assert abs(rate - expected) < Decimal("0.0000001")

    def test_variable_rate_monthly_compounding(self):
        rate = calculate_monthly_rate(Decimal("5.000"), "variable")
        expected = Decimal("0.05") / 12
        assert abs(rate - expected) < Decimal("0.0000001")

    def test_zero_rate(self):
        rate = calculate_monthly_rate(Decimal("0"), "fixed")
        assert rate == Decimal("0")


class TestMonthlyPayment:
    def test_standard_mortgage(self):
        pmt = calculate_monthly_payment(Decimal("400000"), Decimal("5.000"), 25, "fixed")
        assert Decimal("2300") < pmt < Decimal("2400")

    def test_zero_rate(self):
        pmt = calculate_monthly_payment(Decimal("300000"), Decimal("0"), 25, "fixed")
        assert pmt == Decimal("1000.00")


class TestAmortizationSchedule:
    def test_first_payment_mostly_interest(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        first = schedule[0]
        assert first["interest"] > first["principal"]

    def test_last_payment_balance_zero(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        last = schedule[-1]
        assert last["balance"] == Decimal("0")

    def test_total_matches(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        total_principal = sum(e["principal"] for e in schedule)
        total_interest = sum(e["interest"] for e in schedule)
        assert abs(total_principal - mortgage.effective_principal) < Decimal("0.10")
        assert total_interest > 0

    def test_schedule_length(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        assert len(schedule) == 300  # 25 years * 12

    def test_payment_dates_monthly(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        assert schedule[0]["date"] == date(2020, 2, 1)
        assert schedule[1]["date"] == date(2020, 3, 1)
        assert schedule[11]["date"] == date(2021, 1, 1)


class TestRemainingBalance:
    def test_at_start(self, mortgage):
        balance = get_remaining_balance(mortgage, as_of_date=date(2020, 1, 15))
        assert balance > Decimal("399000")

    def test_at_year_10(self, mortgage):
        balance = get_remaining_balance(mortgage, as_of_date=date(2030, 1, 1))
        assert Decimal("250000") < balance < Decimal("320000")

    def test_after_full_amortization(self, mortgage):
        balance = get_remaining_balance(mortgage, as_of_date=date(2050, 1, 1))
        assert balance == Decimal("0")


class TestTotalPaid:
    def test_total_paid_at_year_5(self, mortgage):
        paid = get_total_paid(mortgage, as_of_date=date(2025, 1, 1))
        assert paid["total_principal_paid"] > 0
        assert paid["total_interest_paid"] > 0
        assert paid["total_paid"] == paid["total_principal_paid"] + paid["total_interest_paid"]


class TestMonthlyPaymentAsOf:
    @pytest.fixture
    def renewed_mortgage(self, mortgage):
        MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("3.000"), effective_date=date(2025, 1, 1)
        )
        return mortgage

    def test_without_rate_change_matches_original_payment(self, mortgage):
        expected = calculate_monthly_payment(Decimal("400000"), Decimal("5"), 25)
        assert get_monthly_payment(mortgage, as_of_date=date(2022, 6, 1)) == expected

    def test_before_rate_change_uses_original_payment(self, renewed_mortgage):
        expected = calculate_monthly_payment(Decimal("400000"), Decimal("5"), 25)
        assert get_monthly_payment(renewed_mortgage, as_of_date=date(2024, 12, 1)) == expected

    def test_after_rate_change_uses_recalculated_payment(self, renewed_mortgage):
        # Payment #60 (2025-01-01) is the first at the new rate, with 241 payments left
        balance = get_remaining_balance(renewed_mortgage, as_of_date=date(2024, 12, 1))
        r = calculate_monthly_rate(Decimal("3"))
        expected = ((r * balance) / (1 - (1 + r) ** -241)).quantize(TWO_PLACES)
        payment = get_monthly_payment(renewed_mortgage, as_of_date=date(2025, 1, 1))
        assert payment == expected
        assert payment < calculate_monthly_payment(Decimal("400000"), Decimal("5"), 25)

    def test_after_full_amortization_is_zero(self, mortgage):
        assert get_monthly_payment(mortgage, as_of_date=date(2050, 1, 1)) == Decimal("0")


# ── Ownership ─────────────────────────────────────────────────


class TestOwnershipShares:
    def test_single_owner_with_period(self, prop, user):
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        ownership = prop.ownerships.get(user=user)
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        shares = get_current_ownership_shares(prop)
        assert list(shares.values()) == [Decimal("100")]

    def test_two_owners_60_40(self, prop, user, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        shares = get_current_ownership_shares(prop)
        assert set(shares.values()) == {Decimal("60"), Decimal("40")}

    def test_period_change(self, prop, user, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        period1 = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1), end_date=date(2023, 6, 30))
        OwnershipPeriodShare.objects.create(period=period1, owner=o1, share_pct=Decimal("50"))
        OwnershipPeriodShare.objects.create(period=period1, owner=o2, share_pct=Decimal("50"))
        period2 = OwnershipPeriod.objects.create(property=prop, start_date=date(2023, 7, 1))
        OwnershipPeriodShare.objects.create(period=period2, owner=o1, share_pct=Decimal("75"))
        OwnershipPeriodShare.objects.create(period=period2, owner=o2, share_pct=Decimal("25"))

        shares_before = get_current_ownership_shares(prop, as_of_date=date(2022, 6, 1))
        assert set(shares_before.values()) == {Decimal("50"), Decimal("50")}

        shares_after = get_current_ownership_shares(prop, as_of_date=date(2024, 1, 1))
        assert set(shares_after.values()) == {Decimal("75"), Decimal("25")}

    def test_no_periods_fallback_equal(self, prop, user, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        shares = get_current_ownership_shares(prop)
        assert all(v == Decimal("50.00") for v in shares.values())


class TestOwnerContributions:
    def test_down_payment_only(self, prop, user):
        ownership = prop.ownerships.get(user=user)
        contributions = get_owner_contributions(ownership)
        assert contributions["down_payment"] == Decimal("100000")
        assert contributions["principal_paid"] == Decimal("0")
        assert contributions["capital_improvements_paid"] == Decimal("0")
        assert contributions["other_expenses_paid"] == Decimal("0")
        assert contributions["total"] == Decimal("100000")


# ── Property Snapshot ─────────────────────────────────────────


class TestPropertySnapshot:
    def test_snapshot_with_mortgage(self, prop, mortgage):
        snapshot = get_property_snapshot(prop)
        assert snapshot["current_valuation"] == Decimal("600000")
        assert snapshot["purchase_price"] == Decimal("500000")
        assert snapshot["appreciation"] == Decimal("100000")
        assert snapshot["mortgage_balance"] > 0
        assert snapshot["equity"] == snapshot["current_valuation"] - snapshot["mortgage_balance"]
        assert snapshot["monthly_payment"] > 0

    def test_snapshot_uses_payment_after_rate_change(self, prop, mortgage):
        MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("3.000"), effective_date=date(2025, 1, 1)
        )
        snapshot = get_property_snapshot(prop)
        assert snapshot["monthly_payment"] == get_monthly_payment(mortgage)
        assert snapshot["monthly_payment"] < mortgage.monthly_payment

    def test_snapshot_no_mortgage(self, prop):
        snapshot = get_property_snapshot(prop)
        assert snapshot["mortgage_balance"] == Decimal("0")
        assert snapshot["equity"] == Decimal("600000")
        assert snapshot["monthly_payment"] == Decimal("0.00")


class TestOwnerSnapshot:
    def test_single_owner(self, prop, user, mortgage):
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        ownership = prop.ownerships.get(user=user)
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        snap = get_owner_snapshot(prop, user)
        assert snap["share_pct"] == Decimal("100")
        assert snap["your_equity"] == snap["equity"].quantize(TWO_PLACES)

    def test_principal_paid_from_schedule(self, prop, user, mortgage):
        """Principal paid should come from amortization schedule, not MortgagePayment records."""
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        ownership = prop.ownerships.get(user=user)
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        snap = get_owner_snapshot(prop, user)
        assert snap["your_contributions"]["principal_paid"] > Decimal("0")


# ── Sale Simulation ───────────────────────────────────────────


class TestSaleSimulation:
    def test_primary_residence_no_capital_gains(self, prop, mortgage):
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        ownership = prop.ownerships.get()
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        result = estimate_sale_proceeds(prop, sale_price=Decimal("600000"))
        assert result["capital_gains_tax"] == Decimal("0.00")
        assert result["net_proceeds"] > 0

    def test_rental_property_has_capital_gains(self, user):
        rental = Property.objects.create(
            name="Rental",
            property_type="duplex",
            usage="rental",
            address="456 Rental St",
            city="Quebec",
            purchase_price=Decimal("300000"),
            purchase_date=date(2020, 1, 1),
            welcome_tax_paid=Decimal("4000"),
            notary_fees_purchase=Decimal("1500"),
            current_valuation=Decimal("400000"),
            valuation_date=date(2024, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=rental, is_admin=True)
        period = OwnershipPeriod.objects.create(property=rental, start_date=date(2020, 1, 1))
        ownership = rental.ownerships.get()
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        result = estimate_sale_proceeds(rental, sale_price=Decimal("400000"))
        assert result["capital_gains_tax"] > Decimal("0")

    def test_commission_with_taxes(self, prop, mortgage):
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        ownership = prop.ownerships.get()
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        result = estimate_sale_proceeds(prop, sale_price=Decimal("500000"), agent_commission_pct=Decimal("5"))
        expected_commission = (Decimal("500000") * Decimal("0.05") * Decimal("1.14975")).quantize(TWO_PLACES)
        assert result["agent_commission"] == expected_commission

    def test_per_owner_split(self, prop, user, user2, mortgage):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        result = estimate_sale_proceeds(prop, sale_price=Decimal("600000"))
        assert len(result["per_owner"]) == 2
        total_owner_proceeds = sum(o["net_proceeds"] for o in result["per_owner"])
        assert abs(total_owner_proceeds - result["net_proceeds"]) < Decimal("0.05")


class TestACB:
    def test_acb_with_improvements(self, prop, user):
        ownership = prop.ownerships.get(user=user)
        PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="Kitchen reno",
            amount=Decimal("30000"),
            date=date(2022, 6, 1),
            increases_acb=True,
            paid_by=ownership,
        )
        acb = _calculate_acb(prop)
        assert acb == Decimal("500000") + Decimal("7500") + Decimal("2000") + Decimal("30000")

    def test_acb_without_improvements(self, prop):
        acb = _calculate_acb(prop)
        assert acb == Decimal("500000") + Decimal("7500") + Decimal("2000")


# ── Notification service ─────────────────────────────────────


class TestNotifyCoOwners:
    def test_excludes_actor(self, prop, user, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        notify_co_owners(prop, user, "expense_added", "added expense")
        assert PropertyNotification.objects.filter(recipient=user2).count() == 1
        assert PropertyNotification.objects.filter(recipient=user).count() == 0

    def test_notification_created_unread(self, prop, user, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        notify_co_owners(prop, user, "tax_added", "added tax")
        notif = PropertyNotification.objects.first()
        assert notif.is_read is False
        assert notif.actor == user
        assert notif.recipient == user2
        assert notif.verb == "tax_added"

    def test_no_co_owners(self, prop, user):
        notify_co_owners(prop, user, "expense_added", "added expense")
        assert PropertyNotification.objects.count() == 0


# ── Currency filters & exchange rates ────────────────────────


class TestMoneyFilter:
    def test_cad_format(self):
        from apps.real_estate.templatetags.real_estate_filters import money

        assert money(Decimal("1234"), "CAD") == "$1,234"
        assert money(Decimal("1234.56"), "CAD") == "$1,234.56"

    def test_eur_format(self):
        from apps.real_estate.templatetags.real_estate_filters import money

        assert money(Decimal("1234"), "EUR") == "\u20ac1,234"
        assert money(Decimal("1234.56"), "EUR") == "\u20ac1,234.56"

    def test_none_value(self):
        from apps.real_estate.templatetags.real_estate_filters import money

        assert money(None) == ""

    def test_cad_backward_compat(self):
        from apps.real_estate.templatetags.real_estate_filters import cad

        assert cad(Decimal("500000")) == "$500,000"


class TestExchangeRates:
    def test_convert_same_currency(self):
        from apps.real_estate.exchange_rates import convert

        assert convert(Decimal("100"), "CAD", "CAD") == Decimal("100")

    def test_convert_uses_fallback(self):
        from unittest.mock import patch

        from apps.real_estate.exchange_rates import convert

        with patch("apps.real_estate.exchange_rates._fetch_rates", return_value=None):
            result = convert(Decimal("100"), "CAD", "EUR")
            assert result is not None
            assert result == Decimal("67.00")

    def test_convert_to_filter(self):
        from apps.real_estate.templatetags.real_estate_filters import convert_to

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "apps.real_estate.exchange_rates.get_exchange_rates",
            return_value={
                ("CAD", "EUR"): Decimal("0.67"),
                ("EUR", "CAD"): Decimal("1.49"),
                ("CAD", "CAD"): Decimal("1"),
                ("EUR", "EUR"): Decimal("1"),
            },
        ):
            result = convert_to(Decimal("100"), "CAD,EUR")
            assert "\u20ac" in result


class TestPropertyCurrency:
    def test_property_default_cad(self, prop):
        assert prop.currency == "CAD"

    def test_create_eur_property(self, user):
        p = Property.objects.create(
            name="Paris Flat",
            property_type="condo",
            usage="primary",
            currency="EUR",
            address="10 Rue de Rivoli",
            city="Paris",
            purchase_price=Decimal("300000"),
            purchase_date=date(2023, 1, 1),
            current_valuation=Decimal("320000"),
            valuation_date=date(2024, 1, 1),
        )
        assert p.currency == "EUR"


# ── French mortgage math ────────────────────────────────────


class TestFrenchMonthlyRate:
    def test_fixed_rate_uses_simple_division(self):
        rate = calculate_monthly_rate(Decimal("3.5"), rate_type="fixed", country="FR")
        expected = Decimal("3.5") / 100 / 12
        assert abs(rate - expected) < Decimal("0.000001")

    def test_variable_rate_same_as_fixed(self):
        fixed = calculate_monthly_rate(Decimal("3.5"), rate_type="fixed", country="FR")
        variable = calculate_monthly_rate(Decimal("3.5"), rate_type="variable", country="FR")
        assert fixed == variable

    def test_french_rate_higher_than_canadian(self):
        fr_rate = calculate_monthly_rate(Decimal("5.0"), rate_type="fixed", country="FR")
        ca_rate = calculate_monthly_rate(Decimal("5.0"), rate_type="fixed", country="CA")
        assert fr_rate > ca_rate


class TestFrenchMonthlyPayment:
    def test_standard_french_mortgage(self):
        pmt = calculate_monthly_payment(
            Decimal("200000"),
            Decimal("3.5"),
            20,
            rate_type="fixed",
            country="FR",
        )
        assert Decimal("1155") < pmt < Decimal("1165")

    def test_french_with_borrower_insurance(self):
        base_pmt = calculate_monthly_payment(
            Decimal("200000"),
            Decimal("3.5"),
            20,
            rate_type="fixed",
            country="FR",
        )
        insurance_monthly = Decimal("200000") * Decimal("0.30") / 100 / 12
        total = base_pmt + insurance_monthly
        assert total > base_pmt
        assert insurance_monthly == Decimal("50.00")


class TestFrenchAmortizationSchedule:
    @pytest.fixture
    def french_prop(self, user):
        p = Property.objects.create(
            name="Paris Flat",
            property_type="condo",
            usage="primary",
            country="FR",
            currency="EUR",
            address="10 Rue de Rivoli",
            city="Paris",
            province="75",
            purchase_price=Decimal("300000"),
            purchase_date=date(2023, 1, 1),
            current_valuation=Decimal("320000"),
            valuation_date=date(2024, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True, down_payment=Decimal("60000"))
        return p

    @pytest.fixture
    def french_mortgage(self, french_prop):
        return Mortgage.objects.create(
            real_estate=french_prop,
            lender="BNP Paribas",
            principal=Decimal("240000"),
            annual_rate=Decimal("3.500"),
            rate_type="fixed",
            amortization_years=20,
            start_date=date(2023, 1, 1),
            borrower_insurance_rate=Decimal("0.300"),
        )

    def test_uses_proportional_rate(self, french_mortgage):
        schedule = generate_amortization_schedule(french_mortgage)
        first = schedule[0]
        expected_interest = (Decimal("240000") * Decimal("3.5") / 100 / 12).quantize(TWO_PLACES)
        assert first["interest"] == expected_interest

    def test_insurance_in_each_entry(self, french_mortgage):
        schedule = generate_amortization_schedule(french_mortgage)
        expected_insurance = (Decimal("240000") * Decimal("0.300") / 100 / 12).quantize(TWO_PLACES)
        assert schedule[0]["insurance"] == expected_insurance
        assert schedule[10]["insurance"] == expected_insurance

    def test_total_payment_includes_insurance(self, french_mortgage):
        schedule = generate_amortization_schedule(french_mortgage)
        first = schedule[0]
        base_payment = first["principal"] + first["interest"]
        assert first["total_payment"] == base_payment + first["insurance"]


# ── French capital gains tax ─────────────────────────────────


class TestFrenchCapitalGainsTax:
    @pytest.fixture
    def french_rental(self, user):
        p = Property.objects.create(
            name="Paris Apartment",
            property_type="condo",
            usage="rental",
            address="10 Rue de Rivoli",
            city="Paris",
            province="75",
            country="FR",
            currency="EUR",
            purchase_price=Decimal("300000"),
            purchase_date=date(2015, 1, 1),
            welcome_tax_paid=Decimal("24000"),
            notary_fees_purchase=Decimal("0"),
            current_valuation=Decimal("400000"),
            valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True)
        return p

    def test_primary_residence_exempt(self, user):
        p = Property.objects.create(
            name="Paris Home",
            property_type="condo",
            usage="primary",
            address="5 Av Montaigne",
            city="Paris",
            province="75",
            country="FR",
            currency="EUR",
            purchase_price=Decimal("500000"),
            purchase_date=date(2010, 1, 1),
            current_valuation=Decimal("800000"),
            valuation_date=date(2026, 1, 1),
        )
        tax, details = _calculate_french_capital_gains_tax(p, Decimal("800000"))
        assert tax == Decimal("0")

    def test_rental_under_5_years_no_abatement(self, french_rental):
        french_rental.purchase_date = date(2024, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        # Gain: 400k - (300k + 24k) = 76k
        assert details["ir_abatement_pct"] == Decimal("0")
        assert details["ps_abatement_pct"] == Decimal("0")

    def test_rental_10_years_partial_abatement(self, french_rental):
        french_rental.purchase_date = date(2016, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        assert details["holding_years"] == 10
        assert details["ir_abatement_pct"] == Decimal("30")

    def test_rental_22_years_ir_exempt(self, french_rental):
        french_rental.purchase_date = date(2004, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        assert details["ir_abatement_pct"] == Decimal("100")
        assert details["ir_tax"] == Decimal("0")
        assert details["ps_tax"] > 0

    def test_rental_30_years_fully_exempt(self, french_rental):
        french_rental.purchase_date = date(1995, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        assert tax == Decimal("0")

    def test_no_gain_no_tax(self, french_rental):
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("250000"))
        assert tax == Decimal("0")


class TestFrenchSurtax:
    def test_no_surtax_under_50k(self):
        assert _calculate_french_surtax(Decimal("49000")) == Decimal("0")

    def test_surtax_at_100k(self):
        result = _calculate_french_surtax(Decimal("100000"))
        assert result == Decimal("2000.00")

    def test_surtax_at_260k_plus(self):
        result = _calculate_french_surtax(Decimal("300000"))
        assert result == Decimal("18000.00")

    def test_surtax_boundary_60k(self):
        result = _calculate_french_surtax(Decimal("55000"))
        expected = (Decimal("55000") * Decimal("0.02") - (60000 - 55000) * Decimal("0.05")).quantize(TWO_PLACES)
        assert result == expected


# ── French sale simulation ───────────────────────────────────


class TestFrenchSaleSimulation:
    def test_french_commission_includes_tva(self, user):
        p = Property.objects.create(
            name="Lyon House",
            property_type="house",
            usage="primary",
            address="1 Place Bellecour",
            city="Lyon",
            province="69",
            country="FR",
            currency="EUR",
            purchase_price=Decimal("400000"),
            purchase_date=date(2020, 1, 1),
            current_valuation=Decimal("500000"),
            valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True)
        period = OwnershipPeriod.objects.create(property=p, start_date=date(2020, 1, 1))
        ownership = p.ownerships.get()
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        estimate = estimate_sale_proceeds(p, sale_price=Decimal("500000"))
        # 5% * 500k = 25k * 1.20 TVA = 30k
        assert estimate["agent_commission"] == Decimal("30000.00")

    def test_french_primary_no_cgt(self, user):
        p = Property.objects.create(
            name="Paris Home",
            property_type="condo",
            usage="primary",
            address="5 Rue de Passy",
            city="Paris",
            province="75",
            country="FR",
            currency="EUR",
            purchase_price=Decimal("500000"),
            purchase_date=date(2015, 1, 1),
            current_valuation=Decimal("700000"),
            valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True)
        period = OwnershipPeriod.objects.create(property=p, start_date=date(2015, 1, 1))
        ownership = p.ownerships.get()
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        estimate = estimate_sale_proceeds(p, sale_price=Decimal("700000"))
        assert estimate["capital_gains_tax"] == Decimal("0.00")

    def test_french_rental_has_cgt(self, user):
        p = Property.objects.create(
            name="Nice Studio",
            property_type="condo",
            usage="rental",
            address="10 Prom. des Anglais",
            city="Nice",
            province="06",
            country="FR",
            currency="EUR",
            purchase_price=Decimal("200000"),
            purchase_date=date(2022, 1, 1),
            current_valuation=Decimal("250000"),
            valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True)
        period = OwnershipPeriod.objects.create(property=p, start_date=date(2022, 1, 1))
        ownership = p.ownerships.get()
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        estimate = estimate_sale_proceeds(p, sale_price=Decimal("250000"))
        assert estimate["capital_gains_tax"] > Decimal("0")
        assert "capital_gains_details" in estimate


# ── Rate changes in amortization ─────────────────────────────


class TestAmortizationWithRateChanges:
    @pytest.fixture
    def rate_change(self, mortgage):
        return MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.000"),
            new_rate_type="fixed",
            effective_date=date(2025, 1, 1),
        )

    def test_schedule_uses_original_rate_before_change(self, mortgage, rate_change):
        schedule = generate_amortization_schedule(mortgage)
        jan_2020 = next(e for e in schedule if e["date"].year == 2020 and e["date"].month == 2)
        feb_2025 = next(e for e in schedule if e["date"].year == 2025 and e["date"].month == 2)
        assert feb_2025["interest"] < jan_2020["interest"]

    def test_schedule_recalculates_payment_after_change(self, mortgage, rate_change):
        schedule = generate_amortization_schedule(mortgage)
        before = next(e for e in schedule if e["date"] == date(2024, 12, 1))
        after = next(e for e in schedule if e["date"] == date(2025, 2, 1))
        assert after["total_payment"] < before["total_payment"]

    def test_schedule_ends_at_zero_balance(self, mortgage, rate_change):
        schedule = generate_amortization_schedule(mortgage)
        assert schedule[-1]["balance"] == Decimal("0")

    def test_no_rate_changes_same_as_original(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        assert schedule[0]["interest"] > schedule[0]["principal"]

    def test_simulation_flag_included(self, mortgage):
        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("6.000"),
            effective_date=date(2025, 6, 1),
            is_simulation=True,
        )
        schedule = generate_amortization_schedule(mortgage)
        assert schedule[-1]["balance"] == Decimal("0")


# ── Monthly cost ─────────────────────────────────────────────


class TestMonthlyCost:
    @pytest.fixture
    def prop_with_taxes(self, prop, mortgage):
        PropertyTax.objects.create(property=prop, tax_type="municipal", year=2025, amount=Decimal("4200"))
        PropertyTax.objects.create(property=prop, tax_type="school", year=2025, amount=Decimal("600"))
        return prop

    def test_monthly_cost_basic(self, prop_with_taxes, mortgage):
        result = calculate_monthly_cost(prop_with_taxes)
        assert "mortgage_payment" in result
        assert "taxes_monthly" in result
        assert "total_monthly" in result
        assert result["taxes_monthly"] == Decimal("400.00")

    def test_monthly_cost_uses_payment_after_rate_change(self, prop, mortgage):
        MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("3.000"), effective_date=date(2025, 1, 1)
        )
        result = calculate_monthly_cost(prop, for_user=prop.ownerships.first().user)
        assert result["mortgage_payment"] < mortgage.monthly_payment
        assert result["mortgage_payment"] == get_monthly_payment(mortgage)
        assert result["your_mortgage_payment"] == get_monthly_payment(mortgage)

    def test_monthly_cost_with_rental_income(self, prop, mortgage):
        prop.usage = "rental"
        prop.save()
        RentalIncome.objects.create(
            real_estate=prop,
            monthly_rent=Decimal("2000"),
            agency_fee_pct=Decimal("10"),
            start_date=date(2020, 1, 1),
        )
        result = calculate_monthly_cost(prop)
        assert result["rental_income"] == Decimal("2000.00")
        assert result["rental_net"] == Decimal("1800.00")
        assert result["total_monthly"] < result["mortgage_payment"] + result["taxes_monthly"]

    def test_monthly_cost_no_mortgage(self, prop):
        prop.mortgages.all().delete()
        result = calculate_monthly_cost(prop)
        assert result["mortgage_payment"] == Decimal("0")

    def test_monthly_cost_owner_share(self, prop_with_taxes, mortgage, user):
        result = calculate_monthly_cost(prop_with_taxes, for_user=user)
        assert "your_total_monthly" in result


# ── Evolution chart data ─────────────────────────────────────


class TestEvolutionChartData:
    def test_generates_monthly_series(self, mortgage):
        data = generate_evolution_chart_data(mortgage)
        assert "labels" in data
        assert "principal_series" in data
        assert "interest_series" in data
        assert "balance_series" in data
        assert len(data["labels"]) > 0
        assert len(data["principal_series"]) == len(data["labels"])

    def test_principal_eventually_exceeds_interest(self, mortgage):
        data = generate_evolution_chart_data(mortgage)
        crossover_found = False
        for p, i in zip(data["principal_series"], data["interest_series"], strict=True):
            if p > i:
                crossover_found = True
                break
        assert crossover_found

    def test_balance_decreases(self, mortgage):
        data = generate_evolution_chart_data(mortgage)
        assert data["balance_series"][0] > data["balance_series"][-1]
        assert data["balance_series"][-1] == 0


# ── Ownership comparison ─────────────────────────────────────


class TestOwnershipComparison:
    def test_single_owner(self, prop, user, mortgage):
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        ownership = prop.ownerships.get(user=user)
        OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
        result = get_ownership_comparison(prop)
        assert len(result) == 1
        assert result[0]["purchase_share"] == Decimal("100.00")
        assert result[0]["contribution_share"] == Decimal("100.00")
        assert result[0]["admin_share"] == Decimal("100")

    def test_two_owners_different_down_payments(self, prop, user, user2, mortgage):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        result = get_ownership_comparison(prop)
        assert len(result) == 2
        # user put 100k, user2 put 50k -> 66.67% vs 33.33%
        alice = next(r for r in result if r["user"] == user)
        bob = next(r for r in result if r["user"] == user2)
        assert alice["purchase_share"] == Decimal("66.67")
        assert bob["purchase_share"] == Decimal("33.33")
        assert alice["admin_share"] == Decimal("60")
        assert bob["admin_share"] == Decimal("40")

    def test_shares_sum_to_100(self, prop, user, user2, mortgage):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        result = get_ownership_comparison(prop)
        purchase_total = sum(r["purchase_share"] for r in result)
        contribution_total = sum(r["contribution_share"] for r in result)
        assert abs(purchase_total - Decimal("100")) < Decimal("0.02")
        assert abs(contribution_total - Decimal("100")) < Decimal("0.02")


# ── Monthly cost with custom payments ──────────────────────


class TestMonthlyCostCustomPayments:
    @pytest.fixture
    def two_owners(self, prop, user, user2, mortgage):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        return o1, o2

    def test_custom_payment_remainder_logic(self, prop, mortgage, user, user2, two_owners):
        """When owner A has custom $1000, owner B gets remainder, not share_pct * total."""
        o1, o2 = two_owners
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=o1,
            monthly_amount=Decimal("1000"),
            effective_date=date(2020, 1, 1),
        )
        result = calculate_monthly_cost(prop, for_user=user)
        assert result["your_mortgage_payment"] == Decimal("1000")

        result_b = calculate_monthly_cost(prop, for_user=user2)
        expected_b = mortgage.monthly_payment - Decimal("1000")
        assert abs(result_b["your_mortgage_payment"] - expected_b) < Decimal("0.01")

    def test_custom_payment_both_owners(self, prop, mortgage, user, user2, two_owners):
        """When both owners have custom payments, use those directly."""
        o1, o2 = two_owners
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=o1,
            monthly_amount=Decimal("1500"),
            effective_date=date(2020, 1, 1),
        )
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=o2,
            monthly_amount=Decimal("800"),
            effective_date=date(2020, 1, 1),
        )
        result_a = calculate_monthly_cost(prop, for_user=user)
        assert result_a["your_mortgage_payment"] == Decimal("1500")
        result_b = calculate_monthly_cost(prop, for_user=user2)
        assert result_b["your_mortgage_payment"] == Decimal("800")

    def test_returns_recurring_and_rental_fields(self, prop, mortgage, user):
        """Verify your_recurring_monthly and your_rental_offset are returned."""
        result = calculate_monthly_cost(prop, for_user=user)
        assert "your_recurring_monthly" in result
        assert "your_rental_offset" in result


# ── Per-owner amortization ─────────────────────────────────


class TestPerOwnerAmortization:
    @pytest.fixture
    def two_owners(self, prop, user, user2, mortgage):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
        o1 = prop.ownerships.get(user=user)
        o2 = prop.ownerships.get(user=user2)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        return o1, o2

    def test_returns_schedule_and_summaries(self, prop, mortgage, two_owners):
        schedule, summaries = generate_per_owner_amortization(mortgage)
        assert len(schedule) > 0
        assert len(summaries) == 2

    def test_owner_payments_in_entries(self, prop, mortgage, two_owners):
        schedule, _ = generate_per_owner_amortization(mortgage)
        first = schedule[0]
        assert "owner_payments" in first
        assert len(first["owner_payments"]) == 2

    def test_summaries_sum_to_total(self, prop, mortgage, two_owners):
        schedule, summaries = generate_per_owner_amortization(mortgage)
        total_from_schedule = sum(e["principal"] + e["interest"] for e in schedule)
        total_from_summaries = sum(s["total_paid"] for s in summaries)
        assert abs(total_from_schedule - total_from_summaries) < Decimal("1")

    def test_contribution_pcts_sum_to_100(self, prop, mortgage, two_owners):
        _, summaries = generate_per_owner_amortization(mortgage)
        total_pct = sum(s["contribution_pct"] for s in summaries)
        assert abs(total_pct - Decimal("100")) < Decimal("0.1")

    def test_custom_payment_affects_split(self, prop, mortgage, user, user2, two_owners):
        o1, o2 = two_owners
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=o1,
            monthly_amount=Decimal("1500"),
            effective_date=date(2020, 1, 1),
        )
        schedule, summaries = generate_per_owner_amortization(mortgage)
        alice_summary = next(s for s in summaries if s["owner"] == o1)
        bob_summary = next(s for s in summaries if s["owner"] == o2)
        # Alice pays more, so her contribution % should be higher
        assert alice_summary["contribution_pct"] > bob_summary["contribution_pct"]

    def test_single_owner_returns_empty_summaries(self, prop, mortgage):
        """Single owner should return basic schedule with no summaries."""
        schedule, summaries = generate_per_owner_amortization(mortgage)
        assert len(summaries) == 0
        assert len(schedule) > 0

    def test_per_owner_includes_insurance(self, user, user2):
        """Per-owner total_payment should include insurance (French mortgage)."""
        p = Property.objects.create(
            name="Paris Flat",
            property_type="condo",
            usage="primary",
            country="FR",
            currency="EUR",
            address="10 Rue de Rivoli",
            city="Paris",
            province="75",
            purchase_price=Decimal("300000"),
            purchase_date=date(2023, 1, 1),
            current_valuation=Decimal("320000"),
            valuation_date=date(2024, 1, 1),
        )
        o1 = PropertyOwnership.objects.create(user=user, property=p, is_admin=True, down_payment=Decimal("30000"))
        o2 = PropertyOwnership.objects.create(user=user2, property=p, down_payment=Decimal("30000"))
        period = OwnershipPeriod.objects.create(property=p, start_date=date(2023, 1, 1))
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("50"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("50"))
        m = Mortgage.objects.create(
            real_estate=p,
            lender="BNP",
            principal=Decimal("240000"),
            annual_rate=Decimal("3.500"),
            rate_type="fixed",
            amortization_years=20,
            start_date=date(2023, 1, 1),
            borrower_insurance_rate=Decimal("0.300"),
        )
        schedule, summaries = generate_per_owner_amortization(m)
        first = schedule[0]
        # Sum of owner payments should equal total_payment (which includes insurance)
        owner_payment_sum = sum(op["payment"] for op in first["owner_payments"].values())
        assert abs(owner_payment_sum - first["total_payment"]) < Decimal("0.02")
        # Total paid by all owners across the full schedule should include insurance
        total_from_summaries = sum(s["total_paid"] for s in summaries)
        total_from_schedule = sum(e["total_payment"] for e in schedule)
        assert abs(total_from_summaries - total_from_schedule) < Decimal("1")


class TestAmortizationScheduleAnnualRate:
    def test_annual_rate_in_entries(self, mortgage):
        schedule = generate_amortization_schedule(mortgage)
        assert "annual_rate" in schedule[0]
        assert schedule[0]["annual_rate"] == Decimal("5.000")

    def test_annual_rate_changes_after_rate_change(self, mortgage):
        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.000"),
            new_rate_type="fixed",
            effective_date=date(2025, 1, 1),
        )
        schedule = generate_amortization_schedule(mortgage)
        before = next(e for e in schedule if e["date"] == date(2024, 12, 1))
        after = next(e for e in schedule if e["date"] == date(2025, 2, 1))
        assert before["annual_rate"] == Decimal("5.000")
        assert after["annual_rate"] == Decimal("4.000")


class TestEvolutionChartCurrentMonth:
    def test_current_month_index_present(self, mortgage):
        data = generate_evolution_chart_data(mortgage)
        assert "current_month_index" in data

    def test_current_month_index_within_schedule(self, mortgage):
        data = generate_evolution_chart_data(mortgage)
        if data["current_month_index"] is not None:
            assert 0 <= data["current_month_index"] < len(data["labels"])


# ── Payment splits drive principal attribution ─────────────


@pytest.fixture
def co_owned(prop, user, user2, mortgage):
    """Two owners with equal down payments and a 50/50 ownership period."""
    o1 = prop.ownerships.get(user=user)
    o2 = PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("100000"))
    period = OwnershipPeriod.objects.create(property=prop, start_date=date(2020, 1, 1))
    OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("50"))
    OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("50"))
    return o1, o2


class TestOwnerPrincipalPaid:
    def test_without_split_follows_ownership_shares(self, mortgage, co_owned):
        o1, o2 = co_owned
        as_of = date(2025, 1, 1)
        total = get_total_paid(mortgage, as_of)["total_principal_paid"]
        p1 = get_owner_principal_paid(mortgage, o1, as_of)
        p2 = get_owner_principal_paid(mortgage, o2, as_of)
        assert p1 + p2 == total
        # Odd cents of each instalment go to the same owner: a few cents over the years
        assert abs(p1 - p2) < Decimal("0.50")

    def test_fixed_split_attributes_principal_to_actual_payer(self, mortgage, co_owned):
        o1, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        as_of = date(2025, 1, 1)
        total = get_total_paid(mortgage, as_of)["total_principal_paid"]
        payment = get_monthly_payment(mortgage, as_of)
        p1 = get_owner_principal_paid(mortgage, o1, as_of)
        p2 = get_owner_principal_paid(mortgage, o2, as_of)
        assert p1 + p2 == total
        # o1 pays the remainder of each payment, so gets that share of the principal, not 50 %
        assert abs(p1 - total * (payment - 1000) / payment) < Decimal("0.50")

    def test_stops_at_as_of_date(self, mortgage, co_owned):
        o1, _ = co_owned
        early = get_owner_principal_paid(mortgage, o1, date(2021, 1, 1))
        late = get_owner_principal_paid(mortgage, o1, date(2025, 1, 1))
        assert Decimal("0") < early < late

    def test_single_owner_gets_all_principal(self, mortgage, user, prop):
        as_of = date(2025, 1, 1)
        o1 = prop.ownerships.get(user=user)
        total = get_total_paid(mortgage, as_of)["total_principal_paid"]
        assert get_owner_principal_paid(mortgage, o1, as_of) == total


class TestSplitConsistency:
    def test_equal_shares_sum_exactly_to_payment(self, mortgage, co_owned):
        schedule, _ = generate_per_owner_amortization(mortgage)
        for entry in schedule[:24]:
            assert sum(op["payment"] for op in entry["owner_payments"].values()) == entry["total_payment"]
            assert sum(op["principal"] for op in entry["owner_payments"].values()) == entry["principal"]

    def test_one_fixed_entry_sums_to_payment(self, mortgage, co_owned):
        _, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        schedule, _ = generate_per_owner_amortization(mortgage)
        for entry in schedule[:24]:
            assert entry["owner_payments"][o2.pk]["payment"] == Decimal("1000.00")
            assert sum(op["payment"] for op in entry["owner_payments"].values()) == entry["total_payment"]

    def test_fixed_amount_above_payment_is_capped(self, mortgage, co_owned):
        o1, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("9000"), effective_date=date(2020, 1, 1)
        )
        schedule, _ = generate_per_owner_amortization(mortgage)
        first = schedule[0]
        assert first["owner_payments"][o2.pk]["payment"] == first["total_payment"]
        assert first["owner_payments"][o1.pk]["payment"] == Decimal("0.00")

    def test_percentage_split_follows_rate_change(self, mortgage, co_owned):
        _, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, share_pct=Decimal("25.00"), effective_date=date(2020, 1, 1)
        )
        MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("3.000"), effective_date=date(2025, 1, 1)
        )
        schedule, _ = generate_per_owner_amortization(mortgage)
        before = next(e for e in schedule if e["date"] == date(2024, 12, 1))
        after = next(e for e in schedule if e["date"] == date(2025, 2, 1))
        assert before["owner_payments"][o2.pk]["payment"] == (before["total_payment"] / 4).quantize(TWO_PLACES)
        assert after["owner_payments"][o2.pk]["payment"] == (after["total_payment"] / 4).quantize(TWO_PLACES)
        assert after["owner_payments"][o2.pk]["payment"] < before["owner_payments"][o2.pk]["payment"]


class TestMonthlyCostSplitTiming:
    def test_uses_split_in_effect_on_next_payment(self, prop, mortgage, user, user2, co_owned):
        _, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("900"), effective_date=date(2025, 2, 1)
        )
        as_of = date(2025, 1, 15)  # next payment is 2025-02-01
        payment = get_monthly_payment(mortgage, as_of)
        cost_o2 = calculate_monthly_cost(prop, for_user=user2, as_of_date=as_of)
        cost_o1 = calculate_monthly_cost(prop, for_user=user, as_of_date=as_of)
        assert cost_o2["your_mortgage_payment"] == Decimal("900.00")
        assert cost_o1["your_mortgage_payment"] == payment - Decimal("900")

    def test_percentage_split_in_monthly_cost(self, prop, mortgage, user2, co_owned):
        _, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, share_pct=Decimal("25.00"), effective_date=date(2020, 1, 1)
        )
        as_of = date(2025, 1, 15)
        cost = calculate_monthly_cost(prop, for_user=user2, as_of_date=as_of)
        assert cost["your_mortgage_payment"] == (get_monthly_payment(mortgage, as_of) / 4).quantize(TWO_PLACES)


class TestContributionsUseActualPayments:
    def test_only_capital_improvements_count(self, prop, co_owned):
        o1, _ = co_owned
        PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="Kitchen",
            amount=Decimal("20000"),
            date=date(2022, 5, 1),
            increases_acb=True,
            paid_by=o1,
        )
        PropertyExpense.objects.create(
            property=prop,
            expense_type="repair",
            description="Plumber",
            amount=Decimal("800"),
            date=date(2022, 6, 1),
            paid_by=o1,
        )
        c = get_owner_contributions(o1, as_of_date=date(2023, 1, 1))
        assert c["capital_improvements_paid"] == Decimal("20000")
        assert c["other_expenses_paid"] == Decimal("800")
        assert c["total"] == c["down_payment"] + c["principal_paid"] + Decimal("20000")

    def test_principal_paid_follows_split(self, mortgage, co_owned):
        o1, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        as_of = date(2025, 1, 1)
        assert get_owner_contributions(o1, as_of)["principal_paid"] == get_owner_principal_paid(mortgage, o1, as_of)

    def test_snapshot_principal_follows_split(self, prop, mortgage, user, co_owned):
        o1, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        snapshot = get_owner_snapshot(prop, user)
        assert snapshot["your_contributions"]["principal_paid"] == get_owner_principal_paid(mortgage, o1)

    def test_comparison_reflects_who_pays(self, prop, mortgage, user, co_owned):
        _, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        alice = next(r for r in get_ownership_comparison(prop) if r["user"] == user)
        assert alice["purchase_share"] == Decimal("50.00")
        assert alice["contribution_share"] > Decimal("50.00")

    def test_end_share_projects_current_splits_to_end_of_amortization(self, prop, mortgage, user, co_owned):
        _, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        result = get_ownership_comparison(prop)
        alice = next(r for r in result if r["user"] == user)
        # Alice pays the remainder (~57 % of each payment) until the loan is repaid
        assert alice["end_share"] > alice["contribution_share"] > Decimal("50.00")
        assert abs(sum(r["end_share"] for r in result) - Decimal("100")) < Decimal("0.02")

    def test_end_share_equals_today_without_mortgage(self, prop, user, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        for r in get_ownership_comparison(prop):
            assert r["end_share"] == r["contribution_share"]


# ── Sale split by contributions (MIZ) ──────────────────────


class TestSplitSaleByMiz:
    def test_gain_shared_by_miz_without_floor(self):
        result = split_sale_by_miz(Decimal("300000"), {"a": Decimal("120000"), "b": Decimal("40000")})
        # Each takes back their MIZ, the 140k gain is split 75/25
        assert result["a"]["total"] == Decimal("225000.00")
        assert result["b"]["total"] == Decimal("75000.00")
        assert result["b"]["gain"] == Decimal("35000.00")
        assert result["b"]["gain_share_pct"] == Decimal("25.00")

    def test_floor_applies_to_gain(self):
        result = split_sale_by_miz(
            Decimal("300000"), {"a": Decimal("120000"), "b": Decimal("40000")}, floor_pct=Decimal("30")
        )
        assert result["b"]["gain_share_pct"] == Decimal("30.00")
        assert result["b"]["total"] == Decimal("82000.00")
        assert result["a"]["total"] == Decimal("218000.00")

    def test_floor_not_binding(self):
        result = split_sale_by_miz(
            Decimal("300000"), {"a": Decimal("100000"), "b": Decimal("80000")}, floor_pct=Decimal("30")
        )
        assert result["b"]["total"] == Decimal("80000") + (Decimal("120000") * 80 / 180).quantize(TWO_PLACES)

    def test_loss_is_prorated_without_floor(self):
        result = split_sale_by_miz(
            Decimal("100000"), {"a": Decimal("120000"), "b": Decimal("40000")}, floor_pct=Decimal("30")
        )
        assert result["a"]["total"] == Decimal("75000.00")
        assert result["b"]["total"] == Decimal("25000.00")
        assert result["b"]["gain"] == Decimal("0")

    def test_parts_add_up_to_net(self):
        result = split_sale_by_miz(Decimal("300000.01"), {"a": Decimal("100000"), "b": Decimal("200000")})
        assert sum(r["total"] for r in result.values()) == Decimal("300000.01")

    def test_floor_with_more_than_two_owners_rejected(self):
        with pytest.raises(ValueError):
            split_sale_by_miz(
                Decimal("300000"),
                {"a": Decimal("1"), "b": Decimal("1"), "c": Decimal("1")},
                floor_pct=Decimal("30"),
            )


class TestSaleEstimateByMiz:
    @pytest.fixture
    def miz_prop(self, prop, mortgage, co_owned):
        o1, o2 = co_owned
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o2, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        prop.sale_split_method = "miz"
        prop.miz_floor_pct = Decimal("30")
        prop.save()
        return prop, o1, o2

    def test_compute_miz_matches_contributions(self, miz_prop):
        prop, o1, o2 = miz_prop
        miz = compute_miz(prop)
        assert miz[o1]["miz"] == get_owner_contributions(o1)["total"]
        assert miz[o1]["miz_share"] + miz[o2]["miz_share"] == Decimal("100.00")

    def test_per_owner_uses_miz_split(self, miz_prop):
        prop, o1, o2 = miz_prop
        result = estimate_sale_proceeds(prop)
        by_owner = {r["ownership"]: r for r in result["per_owner"]}
        assert sum(r["net_proceeds"] for r in result["per_owner"]) == result["net_proceeds"]
        expected = split_sale_by_miz(
            result["net_proceeds"],
            {o: m["miz"] for o, m in compute_miz(prop).items()},
            floor_pct=Decimal("30"),
        )
        assert by_owner[o1]["net_proceeds"] == expected[o1]["total"]
        assert by_owner[o1]["net_proceeds"] > by_owner[o2]["net_proceeds"]

    def test_default_method_keeps_ownership_share(self, prop, mortgage, co_owned):
        result = estimate_sale_proceeds(prop)
        shares = {r["share_pct"] for r in result["per_owner"]}
        assert shares == {Decimal("50")}
