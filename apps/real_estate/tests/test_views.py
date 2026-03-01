from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.real_estate.models import (
    Mortgage,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyInvitation,
    PropertyOwnership,
)

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
                "property_type": "condo",
                "usage": "primary",
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
                "property_type": "condo",
                "usage": "primary",
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
                "property_type": "house",
                "usage": "primary",
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
