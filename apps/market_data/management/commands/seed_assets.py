from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.market_data.models import Asset

ASSETS = [
    {
        "ticker": "XEQT.TO",
        "name": "iShares Core Equity ETF Portfolio",
        "asset_type": "etf",
        "currency": "CAD",
        "sector": "Multi-sector",
        "geography": "Global",
        "current_price": Decimal("28.50"),
        "previous_close": Decimal("28.35"),
        "description": "All-in-one global equity ETF with broad diversification.",
    },
    {
        "ticker": "XBAL.TO",
        "name": "iShares Core Balanced ETF Portfolio",
        "asset_type": "etf",
        "currency": "CAD",
        "sector": "Multi-sector",
        "geography": "Global",
        "current_price": Decimal("27.10"),
        "previous_close": Decimal("27.00"),
        "description": "Balanced mix of stocks and bonds for moderate investors.",
    },
    {
        "ticker": "ZAG.TO",
        "name": "BMO Aggregate Bond Index ETF",
        "asset_type": "etf",
        "currency": "CAD",
        "sector": "Fixed income",
        "geography": "Canada",
        "current_price": Decimal("14.20"),
        "previous_close": Decimal("14.18"),
        "description": "Broad Canadian bond market exposure.",
    },
    {
        "ticker": "VFV.TO",
        "name": "Vanguard S&P 500 Index ETF",
        "asset_type": "etf",
        "currency": "CAD",
        "sector": "Multi-sector",
        "geography": "United States",
        "current_price": Decimal("118.75"),
        "previous_close": Decimal("118.10"),
        "description": "Tracks the S&P 500 index in Canadian dollars.",
    },
    {
        "ticker": "RY.TO",
        "name": "Royal Bank of Canada",
        "asset_type": "stock",
        "currency": "CAD",
        "sector": "Financials",
        "geography": "Canada",
        "current_price": Decimal("145.30"),
        "previous_close": Decimal("144.80"),
        "description": "Canada's largest bank by market capitalization.",
    },
    {
        "ticker": "SHOP.TO",
        "name": "Shopify Inc.",
        "asset_type": "stock",
        "currency": "CAD",
        "sector": "Technology",
        "geography": "Canada",
        "current_price": Decimal("105.60"),
        "previous_close": Decimal("106.20"),
        "description": "E-commerce platform headquartered in Ottawa.",
    },
    {
        "ticker": "CASH.TO",
        "name": "Cash Reserve",
        "asset_type": "cash",
        "currency": "CAD",
        "sector": "",
        "geography": "Canada",
        "current_price": Decimal("1.00"),
        "previous_close": Decimal("1.00"),
        "description": "Cash or cash-equivalent position.",
    },
]


class Command(BaseCommand):
    help = "Seed the database with Canadian assets for the sandbox portfolio."

    def handle(self, *args, **options):
        for data in ASSETS:
            asset, created = Asset.objects.update_or_create(
                ticker=data["ticker"],
                defaults=data,
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {asset}")

        self.stdout.write(self.style.SUCCESS(f"Done — {len(ASSETS)} assets seeded."))
