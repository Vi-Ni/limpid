import json
from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext as _

from apps.education.models import LessonProgress
from apps.market_data.models import Asset

from .models import Holding, Portfolio, Transaction

# Allocation configs by risk profile tier
SANDBOX_ALLOCATIONS = {
    "conservative": [
        ("XBAL.TO", Decimal("0.60")),
        ("ZAG.TO", Decimal("0.30")),
        ("CASH.TO", Decimal("0.10")),
    ],
    "moderate": [
        ("XEQT.TO", Decimal("0.50")),
        ("XBAL.TO", Decimal("0.25")),
        ("ZAG.TO", Decimal("0.15")),
        ("RY.TO", Decimal("0.10")),
    ],
    "growth": [
        ("XEQT.TO", Decimal("0.60")),
        ("VFV.TO", Decimal("0.20")),
        ("SHOP.TO", Decimal("0.10")),
        ("RY.TO", Decimal("0.10")),
    ],
}

SANDBOX_TOTAL = Decimal("10000")

# Map asset types to lesson IDs that cover them
ASSET_TYPE_LESSON_MAP = {
    "etf": ["L1-02"],
    "stock": ["L1-01"],
    "bond": ["L1-03"],
    "gic": ["L1-03"],
    "cash": ["L0-01"],
}

CHART_COLORS = [
    "#4f46e5",  # indigo-600
    "#10b981",  # emerald-500
    "#f59e0b",  # amber-500
    "#ef4444",  # red-500
    "#8b5cf6",  # violet-500
    "#ec4899",  # pink-500
    "#06b6d4",  # cyan-500
    "#84cc16",  # lime-500
]


def _get_risk_tier(score):
    """Map risk profile score to allocation tier."""
    if score is None or score <= 3:
        return "conservative"
    if score <= 6:
        return "moderate"
    return "growth"


def create_sandbox_portfolio(user):
    """Create a sandbox portfolio with seed holdings based on risk profile.

    Idempotent: skips if user already has a sandbox portfolio.
    """
    if Portfolio.objects.filter(user=user, is_sandbox=True).exists():
        return Portfolio.objects.get(user=user, is_sandbox=True)

    profile = getattr(user, "profile", None)
    score = profile.risk_profile_score if profile else None
    tier = _get_risk_tier(score)
    allocations = SANDBOX_ALLOCATIONS[tier]

    portfolio = Portfolio.objects.create(
        user=user,
        name=_("My Sandbox Portfolio"),
        is_sandbox=True,
    )

    now = timezone.now()

    for ticker, weight in allocations:
        asset, _created = Asset.objects.get_or_create(
            ticker=ticker,
            defaults={"name": ticker, "asset_type": "cash", "current_price": Decimal("1.00")},
        )
        amount = SANDBOX_TOTAL * weight
        quantity = (amount / asset.current_price).quantize(Decimal("0.0001"))
        avg_cost = asset.current_price * Decimal("0.97")  # Simulate bought slightly lower

        Holding.objects.create(
            portfolio=portfolio,
            asset=asset,
            quantity=quantity,
            average_cost=avg_cost,
        )

        Transaction.objects.create(
            portfolio=portfolio,
            asset=asset,
            transaction_type="buy",
            quantity=quantity,
            price=avg_cost,
            fees=Decimal("0.00"),
            executed_at=now,
        )

    return portfolio


def get_portfolio_snapshot(portfolio):
    """Compute portfolio-level metrics from holdings."""
    holdings = portfolio.holdings.select_related("asset").all()

    total_value = Decimal("0")
    total_cost = Decimal("0")
    daily_change = Decimal("0")

    for h in holdings:
        mv = h.quantity * h.asset.current_price
        tc = h.quantity * h.average_cost
        dc = h.quantity * h.asset.daily_change
        total_value += mv
        total_cost += tc
        daily_change += dc

    gain_loss = total_value - total_cost
    gain_loss_pct = (gain_loss / total_cost * 100) if total_cost else Decimal("0")
    prev_value = total_value - daily_change
    daily_change_pct = (daily_change / prev_value * 100) if prev_value else Decimal("0")

    dc = daily_change.quantize(Decimal("0.01"))
    dc_pct = daily_change_pct.quantize(Decimal("0.01"))
    sign = "+" if dc >= 0 else ""
    daily_change_display = f"{sign}${dc} ({sign}{dc_pct}%)"

    gl = gain_loss.quantize(Decimal("0.01"))
    gl_pct = gain_loss_pct.quantize(Decimal("0.01"))
    gl_sign = "+" if gl >= 0 else ""
    gain_loss_display = f"{gl_sign}${gl} ({gl_sign}{gl_pct}%)"

    return {
        "total_value": total_value.quantize(Decimal("0.01")),
        "total_cost": total_cost.quantize(Decimal("0.01")),
        "gain_loss": gl,
        "gain_loss_pct": gl_pct,
        "gain_loss_display": gain_loss_display,
        "daily_change": dc,
        "daily_change_pct": dc_pct,
        "daily_change_display": daily_change_display,
    }


def get_allocation_breakdown(portfolio):
    """Break down portfolio by asset type with chart data."""
    holdings = portfolio.holdings.select_related("asset").all()

    by_type = {}
    total_value = Decimal("0")

    for h in holdings:
        mv = h.quantity * h.asset.current_price
        total_value += mv
        label = h.asset.get_asset_type_display()
        by_type[label] = by_type.get(label, Decimal("0")) + mv

    breakdown = []
    labels = []
    values = []

    for label, value in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        pct = (value / total_value * 100) if total_value else Decimal("0")
        pct_q = pct.quantize(Decimal("0.1"))
        val_q = value.quantize(Decimal("0.01"))
        breakdown.append(
            {
                "label": label,
                "value": val_q,
                "pct": pct_q,
                "display": f"{pct_q}% (${val_q})",
            }
        )
        labels.append(label)
        values.append(float(pct.quantize(Decimal("0.1"))))

    chart_data = json.dumps(
        {
            "labels": labels,
            "values": values,
            "colors": CHART_COLORS[: len(labels)],
        }
    )

    return {"breakdown": breakdown, "chart_data": chart_data}


def get_exposure_breakdown(portfolio):
    """Break down portfolio by geography and sector."""
    holdings = portfolio.holdings.select_related("asset").all()

    geo = {}
    sector = {}
    total_value = Decimal("0")

    for h in holdings:
        mv = h.quantity * h.asset.current_price
        total_value += mv
        if h.asset.geography:
            geo[h.asset.geography] = geo.get(h.asset.geography, Decimal("0")) + mv
        if h.asset.sector:
            sector[h.asset.sector] = sector.get(h.asset.sector, Decimal("0")) + mv

    def to_list(d):
        result = []
        for label, value in sorted(d.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total_value * 100) if total_value else Decimal("0")
            result.append({"label": label, "pct": float(pct.quantize(Decimal("0.1")))})
        return result

    return {"geography": to_list(geo), "sectors": to_list(sector)}


def get_clarity_score(user, portfolio):
    """Compute % of asset types in portfolio that user has learned about."""
    holdings = portfolio.holdings.select_related("asset").all()
    asset_types = {h.asset.asset_type for h in holdings}

    if not asset_types:
        return {"score": 0, "learned": 0, "total": 0}

    completed_ids = set(LessonProgress.objects.filter(user=user).values_list("lesson_id", flat=True))

    learned = 0
    for at in asset_types:
        required_lessons = ASSET_TYPE_LESSON_MAP.get(at, [])
        if required_lessons and all(lid in completed_ids for lid in required_lessons):
            learned += 1

    total = len(asset_types)
    score = round(learned / total * 100) if total else 0

    return {"score": score, "learned": learned, "total": total}


def get_holdings_table(portfolio):
    """Build a list of holding dicts for the detail table."""
    holdings = portfolio.holdings.select_related("asset").all()

    total_value = sum(h.quantity * h.asset.current_price for h in holdings)
    rows = []

    for h in holdings:
        mv = h.quantity * h.asset.current_price
        tc = h.quantity * h.average_cost
        gl = mv - tc
        gl_pct = (gl / tc * 100) if tc else Decimal("0")
        weight = (mv / total_value * 100) if total_value else Decimal("0")

        rows.append(
            {
                "ticker": h.asset.ticker,
                "name": h.asset.name,
                "quantity": h.quantity,
                "avg_cost": h.average_cost.quantize(Decimal("0.01")),
                "current_price": h.asset.current_price.quantize(Decimal("0.01")),
                "market_value": mv.quantize(Decimal("0.01")),
                "gain_loss": gl.quantize(Decimal("0.01")),
                "gain_loss_pct": gl_pct.quantize(Decimal("0.01")),
                "weight": weight.quantize(Decimal("0.1")),
            }
        )

    return sorted(rows, key=lambda r: r["market_value"], reverse=True)
