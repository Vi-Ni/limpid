from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.real_estate.models import (
    Mortgage,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyExpense,
    PropertyNotification,
    PropertyOwnership,
)
from apps.real_estate.services import (
    _calculate_acb,
    calculate_monthly_payment,
    calculate_monthly_rate,
    estimate_sale_proceeds,
    generate_amortization_schedule,
    get_current_ownership_shares,
    get_owner_contributions,
    get_owner_snapshot,
    get_property_snapshot,
    get_remaining_balance,
    get_total_paid,
    notify_co_owners,
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
        assert contributions["expenses_paid"] == Decimal("0")
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
