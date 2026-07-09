from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.real_estate.models import (
    Mortgage,
    MortgageRateChange,
    OwnerMonthlyPayment,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyExpense,
    PropertyInvitation,
    PropertyNotification,
    PropertyOwnership,
    PropertyTax,
    PropertyValuation,
    RentalIncome,
)
from apps.real_estate.services import get_current_ownership_shares

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", email="alice@test.com", password="testpass123")


@pytest.fixture
def user2(db):
    return User.objects.create_user(username="bob", email="bob@test.com", password="testpass123")


@pytest.fixture
def client(user):
    c = Client()
    c.login(username="alice", password="testpass123")
    return c


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
        current_valuation=Decimal("600000"),
        valuation_date=date(2024, 1, 1),
    )
    ownership = PropertyOwnership.objects.create(user=user, property=p, is_admin=True, down_payment=Decimal("100000"))
    period = OwnershipPeriod.objects.create(property=p, start_date=date(2020, 1, 1))
    OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
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
        start_date=date(2020, 1, 1),
    )


class TestPropertyList:
    def test_requires_login(self, db):
        c = Client()
        response = c.get("/real-estate/")
        assert response.status_code == 302

    def test_shows_user_properties(self, client, prop):
        response = client.get("/real-estate/")
        assert response.status_code == 200
        assert b"Test House" in response.content

    def test_does_not_show_other_users_properties(self, client, user2):
        other_prop = Property.objects.create(
            name="Other House",
            property_type="house",
            usage="primary",
            address="456 Other St",
            city="Quebec",
            purchase_price=Decimal("300000"),
            purchase_date=date(2021, 1, 1),
            current_valuation=Decimal("350000"),
            valuation_date=date(2024, 1, 1),
        )
        PropertyOwnership.objects.create(user=user2, property=other_prop, is_admin=True)
        response = client.get("/real-estate/")
        assert b"Other House" not in response.content


class TestPropertyDetail:
    def test_shows_property(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/")
        assert response.status_code == 200
        assert b"Test House" in response.content

    def test_non_owner_gets_404(self, user2, prop):
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/{prop.pk}/")
        assert response.status_code == 404


class TestPropertyCreate:
    def test_create_property(self, client):
        response = client.post(
            "/real-estate/create/",
            {
                "name": "New Property",
                "country": "CA",
                "property_type": "condo",
                "usage": "primary",
                "currency": "CAD",
                "address": "789 New St",
                "city": "Laval",
                "province": "QC",
                "purchase_price": "400000",
                "purchase_date": "2023-01-01",
                "welcome_tax_paid": "5000",
                "notary_fees_purchase": "1800",
                "current_valuation": "420000",
                "valuation_date": "2024-01-01",
                "municipal_assessment": "380000",
                "down_payment": "80000",
                "mortgage-lender": "Bank",
                "mortgage-principal": "320000",
                "mortgage-annual_rate": "4.500",
                "mortgage-rate_type": "fixed",
                "mortgage-amortization_years": "25",
                "mortgage-term_years": "5",
                "mortgage-payment_frequency": "monthly",
                "mortgage-start_date": "2023-01-01",
                "mortgage-insurance_premium": "0",
            },
        )
        assert response.status_code == 302
        assert Property.objects.filter(name="New Property").exists()
        prop = Property.objects.get(name="New Property")
        assert prop.ownerships.count() == 1
        assert prop.mortgages.count() == 1
        assert prop.ownership_periods.count() == 1


class TestAddExpense:
    def test_add_expense(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/expense/",
            {
                "expense_type": "renovation",
                "description": "Bathroom reno",
                "amount": "15000",
                "date": "2023-06-01",
                "increases_acb": "on",
            },
        )
        assert response.status_code == 200
        assert prop.expenses.count() == 1


class TestAmortization:
    def test_amortization_view(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/amortization/")
        assert response.status_code == 200


class TestSaleSimulator:
    def test_sale_simulator(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/sale-simulator/?sale_price=650000&commission=5")
        assert response.status_code == 200


class TestInvitation:
    def test_invite_co_owner(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/invite/",
            {"email": "bob@test.com", "down_payment": "50000"},
        )
        assert response.status_code == 302
        assert PropertyInvitation.objects.filter(email="bob@test.com").exists()

    def test_accept_invitation(self, prop, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=prop.ownerships.first().user,
            email="bob@test.com",
            down_payment=Decimal("50000"),
            token="test-token-123",
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/invite/{invitation.token}/accept/")
        assert response.status_code == 302
        assert PropertyOwnership.objects.filter(user=user2, property=prop).exists()
        invitation.refresh_from_db()
        assert invitation.accepted

    def test_wrong_email_rejected(self, prop, user, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="different@test.com",
            token="test-token-456",
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/invite/{invitation.token}/accept/")
        assert response.status_code == 302
        assert not PropertyOwnership.objects.filter(user=user2, property=prop).exists()

    def test_already_accepted(self, prop, user, user2):
        PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="bob@test.com",
            token="test-token-789",
            accepted=True,
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get("/real-estate/invite/test-token-789/accept/")
        assert response.status_code == 404

    def test_non_admin_cannot_invite(self, prop, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, is_admin=False)
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/{prop.pk}/invite/")
        assert response.status_code == 404


class TestCreateWithCoOwner:
    def test_create_with_co_owner(self, client):
        response = client.post(
            "/real-estate/create/",
            {
                "name": "Shared Condo",
                "country": "CA",
                "property_type": "condo",
                "usage": "primary",
                "currency": "CAD",
                "address": "100 Shared Ave",
                "city": "Montreal",
                "province": "QC",
                "purchase_price": "400000",
                "purchase_date": "2024-01-01",
                "welcome_tax_paid": "4000",
                "notary_fees_purchase": "1500",
                "current_valuation": "420000",
                "valuation_date": "2024-06-01",
                "municipal_assessment": "380000",
                "down_payment": "50000",
                "co_owner_email": "bob@test.com",
                "co_owner_down_payment": "30000",
                "co_owner_share": "40",
                "mortgage-lender": "Bank",
                "mortgage-principal": "320000",
                "mortgage-annual_rate": "5.000",
                "mortgage-rate_type": "fixed",
                "mortgage-amortization_years": "25",
                "mortgage-term_years": "5",
                "mortgage-payment_frequency": "monthly",
                "mortgage-start_date": "2024-01-01",
                "mortgage-insurance_premium": "0",
            },
        )
        assert response.status_code == 302
        prop = Property.objects.get(name="Shared Condo")
        # Invitation created with correct share
        invitation = PropertyInvitation.objects.get(property=prop)
        assert invitation.email == "bob@test.com"
        assert invitation.down_payment == Decimal("30000")
        assert invitation.share_pct == Decimal("40")
        # Creator's share is 60%
        period = prop.ownership_periods.first()
        creator_share = period.shares.get(owner__is_admin=True)
        assert creator_share.share_pct == Decimal("60")

    def test_create_without_co_owner(self, client):
        response = client.post(
            "/real-estate/create/",
            {
                "name": "Solo House",
                "country": "CA",
                "property_type": "house",
                "usage": "primary",
                "currency": "CAD",
                "address": "200 Solo St",
                "city": "Laval",
                "province": "QC",
                "purchase_price": "500000",
                "purchase_date": "2024-01-01",
                "welcome_tax_paid": "5000",
                "notary_fees_purchase": "2000",
                "current_valuation": "520000",
                "valuation_date": "2024-06-01",
                "municipal_assessment": "480000",
                "down_payment": "100000",
            },
        )
        assert response.status_code == 302
        prop = Property.objects.get(name="Solo House")
        assert not PropertyInvitation.objects.filter(property=prop).exists()
        period = prop.ownership_periods.first()
        assert period.shares.first().share_pct == Decimal("100")


class TestAddTax:
    def test_add_tax(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/tax/",
            {
                "tax_type": "municipal",
                "year": "2025",
                "amount": "3500",
            },
        )
        assert response.status_code == 200
        assert prop.taxes.count() == 1
        tax = prop.taxes.first()
        assert tax.tax_type == "municipal"
        assert tax.year == 2025
        assert tax.amount == Decimal("3500")

    def test_get_tax_form(self, client, prop):
        response = client.get(f"/real-estate/{prop.pk}/tax/")
        assert response.status_code == 200

    def test_unique_constraint(self, client, prop):
        PropertyTax.objects.create(property=prop, tax_type="municipal", year=2025, amount=Decimal("3000"))
        response = client.post(
            f"/real-estate/{prop.pk}/tax/",
            {
                "tax_type": "municipal",
                "year": "2025",
                "amount": "3500",
            },
        )
        # Should return the form with errors (not crash), and not create a duplicate
        assert response.status_code == 200
        assert prop.taxes.count() == 1


class TestPropertyDetailCharts:
    def test_charts_in_context(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/")
        assert response.status_code == 200
        assert b"data-chart" in response.content


class TestAmortizationAutoScroll:
    def test_current_payment_marked(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/amortization/")
        assert response.status_code == 200
        assert b"current-payment" in response.content


class TestAcceptInvitationShareUpdate:
    def test_accept_updates_ownership_shares(self, prop, user, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="bob@test.com",
            down_payment=Decimal("50000"),
            share_pct=Decimal("40"),
            token="share-test-token",
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/invite/{invitation.token}/accept/")
        assert response.status_code == 302

        # Verify ownership period shares were updated
        period = prop.ownership_periods.filter(end_date__isnull=True).order_by("-start_date").first()
        shares = {s.owner.user.username: s.share_pct for s in period.shares.all()}
        assert shares["alice"] == Decimal("60")
        assert shares["bob"] == Decimal("40")


# ── Expense CRUD ─────────────────────────────────────────────


@pytest.fixture
def expense(prop):
    ownership = prop.ownerships.first()
    return PropertyExpense.objects.create(
        property=prop,
        expense_type="renovation",
        description="Paint",
        amount=Decimal("500"),
        date=date(2024, 6, 1),
        paid_by=ownership,
    )


class TestExpenseCRUD:
    def test_edit_expense_get(self, client, prop, expense):
        response = client.get(f"/real-estate/{prop.pk}/expense/{expense.pk}/edit/")
        assert response.status_code == 200
        assert b"Paint" in response.content

    def test_edit_expense_post(self, client, prop, expense):
        response = client.post(
            f"/real-estate/{prop.pk}/expense/{expense.pk}/edit/",
            {
                "expense_type": "renovation",
                "description": "New paint",
                "amount": "600",
                "date": "2024-06-01",
            },
        )
        assert response.status_code == 200
        expense.refresh_from_db()
        assert expense.description == "New paint"
        assert expense.amount == Decimal("600")

    def test_delete_expense(self, client, prop, expense):
        response = client.delete(f"/real-estate/{prop.pk}/expense/{expense.pk}/delete/")
        assert response.status_code == 200
        assert not PropertyExpense.objects.filter(pk=expense.pk).exists()

    def test_edit_expense_creates_notification(self, client, prop, expense, user2):
        PropertyOwnership.objects.create(user=user2, property=prop)
        client.post(
            f"/real-estate/{prop.pk}/expense/{expense.pk}/edit/",
            {
                "expense_type": "renovation",
                "description": "Updated paint",
                "amount": "700",
                "date": "2024-06-01",
            },
        )
        assert PropertyNotification.objects.filter(recipient=user2, verb="expense_updated").exists()


# ── Tax CRUD ─────────────────────────────────────────────────


@pytest.fixture
def tax(prop):
    return PropertyTax.objects.create(
        property=prop,
        tax_type="municipal",
        year=2025,
        amount=Decimal("3500"),
    )


class TestTaxCRUD:
    def test_edit_tax_post(self, client, prop, tax):
        response = client.post(
            f"/real-estate/{prop.pk}/tax/{tax.pk}/edit/",
            {
                "tax_type": "municipal",
                "year": "2025",
                "amount": "3800",
            },
        )
        assert response.status_code == 200
        tax.refresh_from_db()
        assert tax.amount == Decimal("3800")

    def test_edit_tax_unique_constraint(self, client, prop, tax):
        PropertyTax.objects.create(property=prop, tax_type="school", year=2025, amount=Decimal("1000"))
        response = client.post(
            f"/real-estate/{prop.pk}/tax/{tax.pk}/edit/",
            {
                "tax_type": "school",
                "year": "2025",
                "amount": "3800",
            },
        )
        assert response.status_code == 200
        tax.refresh_from_db()
        assert tax.tax_type == "municipal"

    def test_delete_tax(self, client, prop, tax):
        response = client.delete(f"/real-estate/{prop.pk}/tax/{tax.pk}/delete/")
        assert response.status_code == 200
        assert not PropertyTax.objects.filter(pk=tax.pk).exists()


# ── Valuation CRUD ───────────────────────────────────────────


@pytest.fixture
def valuation(prop):
    return PropertyValuation.objects.create(
        property=prop,
        value=Decimal("650000"),
        date=date(2025, 1, 1),
        source="manual",
    )


class TestValuationCRUD:
    def test_edit_valuation_post(self, client, prop, valuation):
        response = client.post(
            f"/real-estate/{prop.pk}/valuation/{valuation.pk}/edit/",
            {
                "value": "670000",
                "date": "2025-01-01",
                "source": "manual",
            },
        )
        assert response.status_code == 200
        valuation.refresh_from_db()
        assert valuation.value == Decimal("670000")

    def test_edit_valuation_updates_current(self, client, prop, valuation):
        client.post(
            f"/real-estate/{prop.pk}/valuation/{valuation.pk}/edit/",
            {
                "value": "680000",
                "date": "2025-06-01",
                "source": "manual",
            },
        )
        prop.refresh_from_db()
        assert prop.current_valuation == Decimal("680000")

    def test_delete_valuation(self, client, prop, valuation):
        response = client.delete(f"/real-estate/{prop.pk}/valuation/{valuation.pk}/delete/")
        assert response.status_code == 200
        assert not PropertyValuation.objects.filter(pk=valuation.pk).exists()
        prop.refresh_from_db()
        assert prop.current_valuation == prop.purchase_price

    def test_delete_valuation_keeps_latest(self, client, prop, valuation):
        older = PropertyValuation.objects.create(
            property=prop, value=Decimal("620000"), date=date(2024, 6, 1), source="manual"
        )
        client.delete(f"/real-estate/{prop.pk}/valuation/{valuation.pk}/delete/")
        prop.refresh_from_db()
        assert prop.current_valuation == older.value


# ── Remove Co-owner ──────────────────────────────────────────


@pytest.fixture
def co_owned_prop(user, user2):
    p = Property.objects.create(
        name="Shared House",
        property_type="house",
        usage="primary",
        address="100 Shared St",
        city="Montreal",
        purchase_price=Decimal("500000"),
        purchase_date=date(2020, 1, 1),
        current_valuation=Decimal("600000"),
        valuation_date=date(2024, 1, 1),
    )
    admin_own = PropertyOwnership.objects.create(user=user, property=p, is_admin=True, down_payment=Decimal("75000"))
    co_own = PropertyOwnership.objects.create(user=user2, property=p, down_payment=Decimal("25000"))
    period = OwnershipPeriod.objects.create(property=p, start_date=date(2020, 1, 1))
    OwnershipPeriodShare.objects.create(period=period, owner=admin_own, share_pct=Decimal("60"))
    OwnershipPeriodShare.objects.create(period=period, owner=co_own, share_pct=Decimal("40"))
    return p


class TestRemoveCoOwner:
    def test_remove_co_owner(self, client, co_owned_prop, user2):
        co_own = PropertyOwnership.objects.get(property=co_owned_prop, user=user2)
        response = client.post(f"/real-estate/{co_owned_prop.pk}/remove-owner/{co_own.pk}/")
        assert response.status_code == 302
        assert not PropertyOwnership.objects.filter(pk=co_own.pk).exists()
        shares = get_current_ownership_shares(co_owned_prop)
        assert list(shares.values()) == [Decimal("100")]

    def test_cannot_remove_self(self, client, co_owned_prop, user):
        admin_own = PropertyOwnership.objects.get(property=co_owned_prop, user=user)
        response = client.post(f"/real-estate/{co_owned_prop.pk}/remove-owner/{admin_own.pk}/")
        assert response.status_code == 302
        assert PropertyOwnership.objects.filter(pk=admin_own.pk).exists()

    def test_non_admin_cannot_remove(self, co_owned_prop, user, user2):
        admin_own = PropertyOwnership.objects.get(property=co_owned_prop, user=user)
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.post(f"/real-estate/{co_owned_prop.pk}/remove-owner/{admin_own.pk}/")
        assert response.status_code == 404

    def test_removed_user_gets_notification(self, client, co_owned_prop, user2):
        co_own = PropertyOwnership.objects.get(property=co_owned_prop, user=user2)
        client.post(f"/real-estate/{co_owned_prop.pk}/remove-owner/{co_own.pk}/")
        assert PropertyNotification.objects.filter(recipient=user2, verb="co_owner_removed").exists()

    def test_confirmation_page_renders(self, client, co_owned_prop, user2):
        co_own = PropertyOwnership.objects.get(property=co_owned_prop, user=user2)
        response = client.get(f"/real-estate/{co_owned_prop.pk}/remove-owner/{co_own.pk}/")
        assert response.status_code == 200
        assert b"Retirer" in response.content


# ── Notification Views ───────────────────────────────────────


class TestNotificationViews:
    def test_notification_list(self, client, prop, user, user2):
        PropertyNotification.objects.create(
            recipient=user, property=prop, actor=user2, verb="expense_added", description="added expense"
        )
        response = client.get("/real-estate/notifications/")
        assert response.status_code == 200
        assert b"added expense" in response.content

    def test_mark_all_read(self, client, prop, user, user2):
        PropertyNotification.objects.create(
            recipient=user, property=prop, actor=user2, verb="expense_added", description="test"
        )
        response = client.post("/real-estate/notifications/mark-read/")
        assert response.status_code == 200
        assert PropertyNotification.objects.filter(recipient=user, is_read=False).count() == 0

    def test_notification_list_empty(self, client):
        response = client.get("/real-estate/notifications/")
        assert response.status_code == 200
        assert b"Aucune notification" in response.content


class TestToggleCurrency:
    def test_toggle_cycles(self, client):
        response = client.get("/real-estate/currency/toggle/?target=EUR")
        assert response.status_code == 302
        assert client.session.get("display_currency") == "EUR"

        response = client.get("/real-estate/currency/toggle/?target=EUR")
        assert client.session.get("display_currency") is None

    def test_requires_login(self, db):
        c = Client()
        response = c.get("/real-estate/currency/toggle/")
        assert response.status_code == 302
        assert "/accounts/login" in response.url


class TestCreateWithEurCurrency:
    def test_create_eur_property(self, client):
        response = client.post(
            "/real-estate/create/",
            {
                "name": "Paris Flat",
                "country": "FR",
                "property_type": "condo",
                "usage": "primary",
                "currency": "EUR",
                "address": "10 Rue de Rivoli",
                "city": "Paris",
                "province": "75",
                "purchase_price": "300000",
                "purchase_date": "2023-01-01",
                "welcome_tax_paid": "0",
                "notary_fees_purchase": "0",
                "current_valuation": "320000",
                "valuation_date": "2024-01-01",
                "municipal_assessment": "0",
                "down_payment": "60000",
            },
        )
        assert response.status_code == 302
        prop = Property.objects.get(name="Paris Flat")
        assert prop.currency == "EUR"


# ── French property tests ───────────────────────────────────


@pytest.fixture
def french_prop(user):
    p = Property.objects.create(
        name="Paris Apartment",
        property_type="condo",
        usage="primary",
        country="FR",
        currency="EUR",
        address="10 Rue de Rivoli",
        city="Paris",
        province="75",
        purchase_price=Decimal("300000"),
        purchase_date=date(2023, 1, 1),
        welcome_tax_paid=Decimal("24000"),
        current_valuation=Decimal("320000"),
        valuation_date=date(2024, 1, 1),
    )
    ownership = PropertyOwnership.objects.create(user=user, property=p, is_admin=True, down_payment=Decimal("60000"))
    period = OwnershipPeriod.objects.create(property=p, start_date=date(2023, 1, 1))
    OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=Decimal("100"))
    return p


@pytest.fixture
def french_mortgage(french_prop):
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


class TestCreateFrenchProperty:
    def test_create_french_property(self, client):
        response = client.post(
            "/real-estate/create/",
            {
                "name": "Appartement Paris",
                "country": "FR",
                "property_type": "condo",
                "usage": "primary",
                "currency": "EUR",
                "address": "10 Rue de Rivoli",
                "city": "Paris",
                "province": "75",
                "purchase_price": "300000",
                "purchase_date": "2024-01-15",
                "welcome_tax_paid": "24000",
                "notary_fees_purchase": "0",
                "current_valuation": "320000",
                "valuation_date": "2026-01-01",
                "municipal_assessment": "0",
                "down_payment": "60000",
            },
        )
        assert response.status_code == 302
        prop = Property.objects.get(name="Appartement Paris")
        assert prop.country == "FR"
        assert prop.currency == "EUR"

    def test_french_property_with_mortgage(self, client):
        response = client.post(
            "/real-estate/create/",
            {
                "name": "Maison Lyon",
                "country": "FR",
                "property_type": "house",
                "usage": "primary",
                "currency": "EUR",
                "address": "5 Place Bellecour",
                "city": "Lyon",
                "province": "69",
                "purchase_price": "400000",
                "purchase_date": "2024-06-01",
                "welcome_tax_paid": "32000",
                "notary_fees_purchase": "0",
                "current_valuation": "420000",
                "valuation_date": "2026-01-01",
                "municipal_assessment": "0",
                "down_payment": "80000",
                "mortgage-lender": "BNP Paribas",
                "mortgage-principal": "320000",
                "mortgage-annual_rate": "3.500",
                "mortgage-rate_type": "fixed",
                "mortgage-amortization_years": "20",
                "mortgage-start_date": "2024-07-01",
                "mortgage-borrower_insurance_rate": "0.300",
            },
        )
        assert response.status_code == 302
        prop = Property.objects.get(name="Maison Lyon")
        mortgage = prop.mortgages.first()
        assert mortgage.borrower_insurance_rate == Decimal("0.300")
        assert mortgage.insurance_premium == 0


class TestFrenchTaxTypes:
    def test_add_taxe_fonciere(self, client, french_prop):
        response = client.post(
            f"/real-estate/{french_prop.pk}/tax/",
            {
                "tax_type": "taxe_fonciere",
                "year": "2025",
                "amount": "1500",
            },
        )
        assert response.status_code == 200
        assert PropertyTax.objects.filter(property=french_prop, tax_type="taxe_fonciere").exists()


class TestFrenchPropertyDetail:
    def test_detail_page_renders(self, client, french_prop, french_mortgage):
        response = client.get(f"/real-estate/{french_prop.pk}/")
        assert response.status_code == 200
        assert b"Paris Apartment" in response.content


class TestFrenchAmortizationView:
    def test_amortization_page_renders(self, client, french_prop, french_mortgage):
        response = client.get(f"/real-estate/{french_prop.pk}/mortgage/{french_mortgage.pk}/amortization/")
        assert response.status_code == 200
        # "Insurance" is translated to "Assurance" in FR locale
        assert b"Assurance" in response.content or b"Insurance" in response.content

    def test_insurance_column_in_schedule(self, client, french_prop, french_mortgage):
        response = client.get(f"/real-estate/{french_prop.pk}/mortgage/{french_mortgage.pk}/amortization/")
        assert response.status_code == 200
        assert b"BNP Paribas" in response.content


class TestFrenchSaleSimulatorView:
    def test_sale_simulator_renders(self, client, french_prop, french_mortgage):
        response = client.get(f"/real-estate/{french_prop.pk}/sale-simulator/?sale_price=350000&commission=5")
        assert response.status_code == 200


# ── Delete Property ─────────────────────────────────────────


class TestDeleteProperty:
    def test_confirmation_page(self, client, prop):
        response = client.get(f"/real-estate/{prop.pk}/delete/")
        assert response.status_code == 200
        assert b"Delete" in response.content or b"Supprimer" in response.content

    def test_admin_can_delete(self, client, prop):
        response = client.post(f"/real-estate/{prop.pk}/delete/")
        assert response.status_code == 302
        assert not Property.objects.filter(pk=prop.pk).exists()

    def test_non_admin_forbidden(self, prop, user2):
        PropertyOwnership.objects.create(user=user2, property=prop, is_admin=False)
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.post(f"/real-estate/{prop.pk}/delete/")
        assert response.status_code == 403
        assert Property.objects.filter(pk=prop.pk).exists()

    def test_non_owner_404(self, user2, prop):
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/{prop.pk}/delete/")
        assert response.status_code == 404


# ── Rate Change Views ───────────────────────────────────────


class TestRateChangeViews:
    def test_add_rate_change(self, client, prop, mortgage):
        response = client.post(
            f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/rate-change/",
            {
                "new_annual_rate": "4.500",
                "new_rate_type": "fixed",
                "effective_date": "2026-01-01",
            },
        )
        assert response.status_code == 200
        assert MortgageRateChange.objects.filter(mortgage=mortgage).count() == 1

    def test_get_rate_change_form(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/rate-change/")
        assert response.status_code == 200

    def test_delete_rate_change(self, client, prop, mortgage):
        rc = MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("4.500"), effective_date=date(2026, 1, 1)
        )
        response = client.delete(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/rate-change/{rc.pk}/delete/")
        assert response.status_code == 200
        assert not MortgageRateChange.objects.filter(pk=rc.pk).exists()


# ── Rental Income Views ─────────────────────────────────────


class TestRentalIncomeViews:
    def test_add_rental_income(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/rental-income/",
            {
                "monthly_rent": "1500",
                "agency_fee_pct": "0",
                "start_date": "2025-01-01",
            },
        )
        assert response.status_code == 200
        assert RentalIncome.objects.filter(real_estate=prop).count() == 1

    def test_get_rental_income_form(self, client, prop):
        response = client.get(f"/real-estate/{prop.pk}/rental-income/")
        assert response.status_code == 200

    def test_delete_rental_income(self, client, prop):
        ri = RentalIncome.objects.create(real_estate=prop, monthly_rent=Decimal("1500"), start_date=date(2025, 1, 1))
        response = client.delete(f"/real-estate/{prop.pk}/rental-income/{ri.pk}/delete/")
        assert response.status_code == 200
        assert not RentalIncome.objects.filter(pk=ri.pk).exists()


# ── Monthly Cost Views ──────────────────────────────────────


class TestMonthlyCostViews:
    def test_monthly_cost_partial(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/monthly-cost/")
        assert response.status_code == 200

    def test_monthly_cost_mine(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/monthly-cost/?mine=1")
        assert response.status_code == 200


# ── Charts Partial View ──────────────────────────────────────


class TestChartsPartialView:
    def test_charts_partial(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/charts/")
        assert response.status_code == 200
        assert b"data-chart" in response.content

    def test_charts_partial_no_mortgage(self, client, prop):
        response = client.get(f"/real-estate/{prop.pk}/charts/")
        assert response.status_code == 200

    def test_charts_partial_non_owner_404(self, user2, prop):
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.get(f"/real-estate/{prop.pk}/charts/")
        assert response.status_code == 404


# ── HX-Trigger Headers ──────────────────────────────────────


class TestHXTriggerHeaders:
    def test_add_expense_triggers(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/expense/",
            {"expense_type": "renovation", "description": "Test", "amount": "100", "date": "2024-01-01"},
        )
        assert response.status_code == 200
        assert response["HX-Trigger"] == "expenses-changed"

    def test_delete_expense_triggers(self, client, prop, expense):
        response = client.delete(f"/real-estate/{prop.pk}/expense/{expense.pk}/delete/")
        assert response["HX-Trigger"] == "expenses-changed"

    def test_edit_expense_triggers(self, client, prop, expense):
        response = client.post(
            f"/real-estate/{prop.pk}/expense/{expense.pk}/edit/",
            {"expense_type": "renovation", "description": "Updated", "amount": "200", "date": "2024-06-01"},
        )
        assert response["HX-Trigger"] == "expenses-changed"

    def test_add_tax_triggers(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/tax/",
            {"tax_type": "municipal", "year": "2025", "amount": "3000"},
        )
        assert response["HX-Trigger"] == "taxes-changed"

    def test_edit_tax_triggers(self, client, prop, tax):
        response = client.post(
            f"/real-estate/{prop.pk}/tax/{tax.pk}/edit/",
            {"tax_type": "municipal", "year": "2025", "amount": "3800"},
        )
        assert response["HX-Trigger"] == "taxes-changed"

    def test_delete_tax_triggers(self, client, prop, tax):
        response = client.delete(f"/real-estate/{prop.pk}/tax/{tax.pk}/delete/")
        assert response["HX-Trigger"] == "taxes-changed"

    def test_add_rate_change_triggers(self, client, prop, mortgage):
        response = client.post(
            f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/rate-change/",
            {"new_annual_rate": "4.500", "new_rate_type": "fixed", "effective_date": "2026-01-01"},
        )
        assert response["HX-Trigger"] == "mortgage-changed"

    def test_delete_rate_change_triggers(self, client, prop, mortgage):
        rc = MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("4.500"), effective_date=date(2026, 1, 1)
        )
        response = client.delete(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/rate-change/{rc.pk}/delete/")
        assert response["HX-Trigger"] == "mortgage-changed"

    def test_add_rental_income_triggers(self, client, prop):
        response = client.post(
            f"/real-estate/{prop.pk}/rental-income/",
            {"monthly_rent": "1500", "agency_fee_pct": "0", "start_date": "2025-01-01"},
        )
        assert response["HX-Trigger"] == "rental-changed"

    def test_delete_rental_income_triggers(self, client, prop):
        ri = RentalIncome.objects.create(real_estate=prop, monthly_rent=Decimal("1500"), start_date=date(2025, 1, 1))
        response = client.delete(f"/real-estate/{prop.pk}/rental-income/{ri.pk}/delete/")
        assert response["HX-Trigger"] == "rental-changed"


# ── Invitation Notifications ────────────────────────────────


class TestInvitationNotifications:
    def test_invite_creates_notification_for_existing_user(self, client, prop, user2):
        client.post(
            f"/real-estate/{prop.pk}/invite/",
            {"email": "bob@test.com", "down_payment": "50000"},
        )
        assert PropertyNotification.objects.filter(recipient=user2, verb="invitation_received").exists()

    def test_invite_no_notification_for_unknown_email(self, client, prop):
        client.post(
            f"/real-estate/{prop.pk}/invite/",
            {"email": "unknown@test.com", "down_payment": "0"},
        )
        assert not PropertyNotification.objects.filter(verb="invitation_received").exists()

    def test_notification_links_to_invitation(self, client, prop, user2):
        client.post(
            f"/real-estate/{prop.pk}/invite/",
            {"email": "bob@test.com", "down_payment": "50000"},
        )
        notif = PropertyNotification.objects.get(recipient=user2, verb="invitation_received")
        assert notif.invitation is not None
        assert notif.invitation.email == "bob@test.com"

    def test_accept_invitation_htmx(self, prop, user, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="bob@test.com",
            down_payment=Decimal("50000"),
            share_pct=Decimal("40"),
            token="htmx-accept-token",
        )
        PropertyNotification.objects.create(
            recipient=user2,
            property=prop,
            actor=user,
            verb="invitation_received",
            description="test",
            invitation=invitation,
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.post(f"/real-estate/invitation/{invitation.pk}/accept/")
        assert response.status_code == 200
        invitation.refresh_from_db()
        assert invitation.accepted
        assert PropertyOwnership.objects.filter(user=user2, property=prop).exists()
        notif = PropertyNotification.objects.get(recipient=user2, invitation=invitation)
        assert notif.is_read

    def test_decline_invitation_htmx(self, prop, user, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="bob@test.com",
            down_payment=Decimal("0"),
            share_pct=Decimal("50"),
            token="htmx-decline-token",
        )
        PropertyNotification.objects.create(
            recipient=user2,
            property=prop,
            actor=user,
            verb="invitation_received",
            description="test",
            invitation=invitation,
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.post(f"/real-estate/invitation/{invitation.pk}/decline/")
        assert response.status_code == 200
        assert not PropertyInvitation.objects.filter(pk=invitation.pk).exists()

    def test_wrong_user_cannot_accept(self, prop, user, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="someone@else.com",
            token="wrong-user-token",
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        response = c.post(f"/real-estate/invitation/{invitation.pk}/accept/")
        assert response.status_code == 403

    def test_login_signal_creates_notifications(self, prop, user, user2):
        PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="bob@test.com",
            share_pct=Decimal("40"),
            token="signal-test-token",
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        assert PropertyNotification.objects.filter(recipient=user2, verb="invitation_received").exists()

    def test_login_signal_no_duplicate(self, prop, user, user2):
        invitation = PropertyInvitation.objects.create(
            property=prop,
            invited_by=user,
            email="bob@test.com",
            share_pct=Decimal("40"),
            token="no-dup-token",
        )
        PropertyNotification.objects.create(
            recipient=user2,
            property=prop,
            actor=user,
            verb="invitation_received",
            description="already exists",
            invitation=invitation,
        )
        c = Client()
        c.login(username="bob", password="testpass123")
        assert (
            PropertyNotification.objects.filter(
                recipient=user2, verb="invitation_received", invitation=invitation
            ).count()
            == 1
        )


# ── Payment split auto-calc ──────────────────────────────────


class TestPaymentSplitAutoCalc:
    @pytest.fixture
    def two_owner_prop(self, user, user2, prop, mortgage):
        o2 = PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = prop.ownership_periods.first()
        period.shares.all().delete()
        o1 = prop.ownerships.get(user=user)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        return prop, mortgage, o1, o2

    def test_auto_creates_other_owner_payment(self, client, two_owner_prop):
        prop, mortgage, o1, o2 = two_owner_prop
        response = client.post(
            f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payments/",
            {
                "owner": o1.pk,
                "monthly_amount": "1000",
                "effective_date": "2020-01-01",
            },
        )
        assert response.status_code == 200
        # Auto-created payment for other owner
        other_payment = OwnerMonthlyPayment.objects.filter(mortgage=mortgage, owner=o2).first()
        assert other_payment is not None
        expected = mortgage.monthly_payment - Decimal("1000")
        assert abs(other_payment.monthly_amount - expected) < Decimal("0.01")

    def test_auto_updates_existing_payment(self, client, two_owner_prop):
        prop, mortgage, o1, o2 = two_owner_prop
        # First submission
        client.post(
            f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payments/",
            {
                "owner": o1.pk,
                "monthly_amount": "1000",
                "effective_date": "2020-01-01",
            },
        )
        # Second submission with different amount
        client.post(
            f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payments/",
            {
                "owner": o1.pk,
                "monthly_amount": "1200",
                "effective_date": "2020-01-01",
            },
        )
        # Should update, not duplicate
        payments = OwnerMonthlyPayment.objects.filter(mortgage=mortgage, owner=o2, effective_date=date(2020, 1, 1))
        assert payments.count() == 1
        expected = mortgage.monthly_payment - Decimal("1200")
        assert abs(payments.first().monthly_amount - expected) < Decimal("0.01")


# ── Payment split edit/delete ──────────────────────────────


class TestPaymentSplitEditDelete:
    @pytest.fixture
    def two_owner_prop(self, user, user2, prop, mortgage):
        o2 = PropertyOwnership.objects.create(user=user2, property=prop, down_payment=Decimal("50000"))
        period = prop.ownership_periods.first()
        period.shares.all().delete()
        o1 = prop.ownerships.get(user=user)
        OwnershipPeriodShare.objects.create(period=period, owner=o1, share_pct=Decimal("60"))
        OwnershipPeriodShare.objects.create(period=period, owner=o2, share_pct=Decimal("40"))
        return prop, mortgage, o1, o2

    def test_edit_owner_payment_get(self, client, two_owner_prop):
        prop, mortgage, o1, o2 = two_owner_prop
        payment = OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o1, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        response = client.get(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payment/{payment.pk}/edit/")
        assert response.status_code == 200

    def test_edit_owner_payment_post(self, client, two_owner_prop):
        prop, mortgage, o1, o2 = two_owner_prop
        payment = OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o1, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        response = client.post(
            f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payment/{payment.pk}/edit/",
            {
                "owner": o1.pk,
                "monthly_amount": "1300",
                "effective_date": "2020-01-01",
            },
        )
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.monthly_amount == Decimal("1300")
        # Auto-calc for other owner
        other_payment = OwnerMonthlyPayment.objects.filter(mortgage=mortgage, owner=o2).first()
        assert other_payment is not None
        expected = mortgage.monthly_payment - Decimal("1300")
        assert abs(other_payment.monthly_amount - expected) < Decimal("0.01")

    def test_delete_owner_payment(self, client, two_owner_prop):
        prop, mortgage, o1, o2 = two_owner_prop
        payment = OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o1, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        response = client.delete(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payment/{payment.pk}/delete/")
        assert response.status_code == 200
        assert not OwnerMonthlyPayment.objects.filter(pk=payment.pk).exists()

    def test_delete_owner_payment_wrong_method(self, client, two_owner_prop):
        prop, mortgage, o1, o2 = two_owner_prop
        payment = OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=o1, monthly_amount=Decimal("1000"), effective_date=date(2020, 1, 1)
        )
        response = client.get(f"/real-estate/{prop.pk}/mortgage/{mortgage.pk}/owner-payment/{payment.pk}/delete/")
        assert response.status_code == 405


class TestPropertyCreateWizard:
    def test_create_page_renders_wizard(self, client):
        response = client.get("/real-estate/create/")
        assert response.status_code == 200
        assert b"wizardForm" in response.content
        assert b"data-step" in response.content

    def test_wizard_form_still_submits(self, client):
        data = {
            "name": "Wizard Property",
            "country": "CA",
            "property_type": "house",
            "usage": "primary",
            "currency": "CAD",
            "address": "456 Wizard St",
            "city": "Montreal",
            "province": "QC",
            "postal_code": "H1A 1A1",
            "purchase_price": "500000",
            "purchase_date": "2024-01-01",
            "welcome_tax_paid": "5000",
            "notary_fees_purchase": "1800",
            "current_valuation": "550000",
            "valuation_date": "2024-06-01",
            "down_payment": "100000",
            "mortgage-lender": "Test Bank",
            "mortgage-principal": "400000",
            "mortgage-annual_rate": "5.5",
            "mortgage-rate_type": "fixed",
            "mortgage-amortization_years": "25",
            "mortgage-term_years": "5",
            "mortgage-payment_frequency": "monthly",
            "mortgage-start_date": "2024-01-01",
            "mortgage-insurance_premium": "0",
        }
        response = client.post("/real-estate/create/", data)
        assert response.status_code == 302

    def test_wizard_form_submits_without_valuation(self, client):
        data = {
            "name": "No Valuation Property",
            "country": "CA",
            "property_type": "condo",
            "usage": "primary",
            "currency": "CAD",
            "address": "789 Skip St",
            "city": "Toronto",
            "province": "ON",
            "postal_code": "M1A 1A1",
            "purchase_price": "300000",
            "purchase_date": "2024-06-01",
            "down_payment": "60000",
            "mortgage-principal": "",
        }
        response = client.post("/real-estate/create/", data)
        assert response.status_code == 302
        p = Property.objects.get(name="No Valuation Property")
        assert p.current_valuation is None
        assert p.valuation_date is None


@pytest.mark.django_db
class TestMonthlyCostStatCard:
    def test_detail_page_shows_monthly_cost_card(self, client, prop, mortgage):
        response = client.get(f"/real-estate/{prop.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "monthly_cost" in content
