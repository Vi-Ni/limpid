from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.real_estate.models import (
    Mortgage,
    MortgageRateChange,
    OwnerMonthlyPayment,
    Property,
    PropertyExpense,
    PropertyOwnership,
    RentalIncome,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", email="alice@test.com", password="testpass123")


@pytest.fixture
def prop(user):
    return Property.objects.create(
        name="Test House",
        property_type="house",
        usage="primary",
        address="123 Main St",
        city="Montreal",
        purchase_price=Decimal("500000"),
        purchase_date=date(2020, 1, 1),
        current_valuation=Decimal("600000"),
        valuation_date=date(2024, 1, 1),
    )


class TestProperty:
    def test_str(self, prop):
        assert str(prop) == "Test House"

    def test_total_appreciation(self, prop):
        assert prop.total_appreciation == Decimal("100000")

    def test_total_appreciation_pct(self, prop):
        assert prop.total_appreciation_pct == Decimal("20")

    def test_total_invested_no_expenses(self, prop):
        assert prop.total_invested == Decimal("500000")

    def test_total_invested_with_expenses(self, prop, user):
        ownership = PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="Kitchen",
            amount=Decimal("20000"),
            date=date(2022, 1, 1),
            paid_by=ownership,
        )
        assert prop.total_invested == Decimal("520000")


class TestPropertyOwnership:
    def test_str(self, prop, user):
        ownership = PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        assert str(ownership) == f"{user} — {prop}"

    def test_unique_together(self, prop, user):
        PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        with pytest.raises(IntegrityError):
            PropertyOwnership.objects.create(user=user, property=prop)


class TestMortgage:
    def test_effective_principal(self, prop):
        m = Mortgage.objects.create(
            real_estate=prop,
            lender="Bank",
            principal=Decimal("400000"),
            annual_rate=Decimal("5.000"),
            start_date=date(2020, 1, 1),
            insurance_premium=Decimal("12000"),
        )
        assert m.effective_principal == Decimal("412000")

    def test_monthly_rate_fixed(self, prop):
        m = Mortgage.objects.create(
            real_estate=prop,
            lender="Bank",
            principal=Decimal("400000"),
            annual_rate=Decimal("5.000"),
            rate_type="fixed",
            start_date=date(2020, 1, 1),
        )
        expected = (1 + Decimal("0.05") / 2) ** (Decimal("1") / 6) - 1
        assert abs(m.monthly_rate - expected) < Decimal("0.0000001")

    def test_monthly_rate_variable(self, prop):
        m = Mortgage.objects.create(
            real_estate=prop,
            lender="Bank",
            principal=Decimal("400000"),
            annual_rate=Decimal("5.000"),
            rate_type="variable",
            start_date=date(2020, 1, 1),
        )
        assert abs(m.monthly_rate - Decimal("0.05") / 12) < Decimal("0.0000001")

    def test_monthly_payment(self, prop):
        m = Mortgage.objects.create(
            real_estate=prop,
            lender="Bank",
            principal=Decimal("400000"),
            annual_rate=Decimal("5.000"),
            rate_type="fixed",
            amortization_years=25,
            start_date=date(2020, 1, 1),
        )
        assert Decimal("2300") < m.monthly_payment < Decimal("2400")

    def test_zero_rate_payment(self, prop):
        m = Mortgage.objects.create(
            real_estate=prop,
            lender="Bank",
            principal=Decimal("300000"),
            annual_rate=Decimal("0"),
            rate_type="fixed",
            amortization_years=25,
            start_date=date(2020, 1, 1),
        )
        assert m.monthly_payment == Decimal("1000")


@pytest.fixture
def mortgage(prop):
    return Mortgage.objects.create(
        real_estate=prop,
        lender="Bank",
        principal=Decimal("400000"),
        annual_rate=Decimal("5.000"),
        rate_type="fixed",
        amortization_years=25,
        start_date=date(2020, 1, 1),
    )


class TestMortgageRateChange:
    @pytest.fixture
    def rate_change(self, mortgage):
        return MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.500"),
            new_rate_type="fixed",
            effective_date=date(2025, 1, 1),
            note="Term renewal",
        )

    def test_str(self, rate_change):
        assert "4.500" in str(rate_change)
        assert "2025-01-01" in str(rate_change)

    def test_ordering(self, mortgage):
        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.000"),
            effective_date=date(2026, 1, 1),
        )
        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("5.500"),
            effective_date=date(2025, 1, 1),
        )
        changes = list(MortgageRateChange.objects.filter(mortgage=mortgage))
        assert changes[0].effective_date < changes[1].effective_date


class TestRentalIncome:
    @pytest.fixture
    def rental_prop(self, user):
        p = Property.objects.create(
            name="Rental Unit",
            property_type="condo",
            usage="rental",
            address="456 Rent St",
            city="Montreal",
            purchase_price=Decimal("400000"),
            purchase_date=date(2020, 1, 1),
            current_valuation=Decimal("420000"),
            valuation_date=date(2024, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True)
        return p

    @pytest.fixture
    def rental_income(self, rental_prop):
        return RentalIncome.objects.create(
            real_estate=rental_prop,
            monthly_rent=Decimal("1800"),
            agency_fee_pct=Decimal("8.0"),
            start_date=date(2021, 1, 1),
        )

    def test_str(self, rental_income):
        assert "1800" in str(rental_income)

    def test_net_monthly_rent(self, rental_income):
        assert rental_income.net_monthly_rent == Decimal("1656.00")

    def test_net_monthly_rent_no_agency(self, rental_prop):
        ri = RentalIncome.objects.create(
            real_estate=rental_prop,
            monthly_rent=Decimal("1800"),
            agency_fee_pct=Decimal("0"),
            start_date=date(2021, 1, 1),
        )
        assert ri.net_monthly_rent == Decimal("1800.00")


class TestOwnerMonthlyPayment:
    @pytest.fixture
    def owner_payment(self, prop, user, mortgage):
        ownership = PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        return OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=ownership,
            monthly_amount=Decimal("1500"),
            effective_date=date(2020, 1, 1),
        )

    def test_str(self, owner_payment):
        assert "1500" in str(owner_payment)

    def test_unique_effective_date(self, prop, user, mortgage):
        ownership = PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=ownership,
            monthly_amount=Decimal("1500"),
            effective_date=date(2020, 1, 1),
        )
        with pytest.raises(IntegrityError):
            OwnerMonthlyPayment.objects.create(
                mortgage=mortgage,
                owner=ownership,
                monthly_amount=Decimal("1600"),
                effective_date=date(2020, 1, 1),
            )


class TestExpenseProofLink:
    def test_proof_link_optional(self, prop, user):
        ownership = PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        expense = PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="New roof",
            amount=Decimal("15000"),
            date=date(2024, 6, 1),
            paid_by=ownership,
        )
        assert expense.proof_link == ""

    def test_proof_link_stores_url(self, prop, user):
        ownership = PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        expense = PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="New roof",
            amount=Decimal("15000"),
            date=date(2024, 6, 1),
            paid_by=ownership,
            proof_link="https://drive.google.com/file/d/abc123",
        )
        assert expense.proof_link == "https://drive.google.com/file/d/abc123"
