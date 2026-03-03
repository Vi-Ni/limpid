import json
import logging
import urllib.request
from decimal import Decimal

from django.core.cache import cache

logger = logging.getLogger(__name__)

FALLBACK_RATES = {
    ("CAD", "EUR"): Decimal("0.67"),
    ("EUR", "CAD"): Decimal("1.49"),
    ("CAD", "CAD"): Decimal("1"),
    ("EUR", "EUR"): Decimal("1"),
}

CACHE_KEY = "exchange_rates"
CACHE_TTL = 3600


def get_exchange_rates():
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    rates = _fetch_rates()
    if rates:
        cache.set(CACHE_KEY, rates, CACHE_TTL)
    return rates or FALLBACK_RATES


def _fetch_rates():
    try:
        url = "https://open.er-api.com/v6/latest/CAD"
        req = urllib.request.Request(url, headers={"User-Agent": "Limpid/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        if data.get("result") == "success":
            eur_rate = Decimal(str(data["rates"]["EUR"]))
            return {
                ("CAD", "EUR"): eur_rate,
                ("EUR", "CAD"): (Decimal("1") / eur_rate).quantize(Decimal("0.0001")),
                ("CAD", "CAD"): Decimal("1"),
                ("EUR", "EUR"): Decimal("1"),
            }
    except Exception:
        logger.warning("Failed to fetch exchange rates, using fallback")

    return None


def convert(amount, from_currency, to_currency):
    if from_currency == to_currency:
        return amount
    rates = get_exchange_rates()
    rate = rates.get((from_currency, to_currency))
    if rate is None:
        return None
    return (amount * rate).quantize(Decimal("0.01"))
