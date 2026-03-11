from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

CURRENCY_SYMBOLS = {
    "CAD": "$",
    "EUR": "\u20ac",
}


def _format_with_commas(n):
    negative = n < 0
    s = str(abs(n))
    groups = []
    while s:
        groups.append(s[-3:])
        s = s[:-3]
    result = ",".join(reversed(groups))
    return f"-{result}" if negative else result


@register.filter
def cad(value):
    return money(value, "CAD")


@register.filter
def money(value, currency="CAD"):
    if value is None:
        return ""
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    if value == value.to_integral_value():
        return f"{symbol}{_format_with_commas(int(value))}"
    formatted = f"{value:.2f}"
    parts = formatted.split(".")
    return f"{symbol}{_format_with_commas(int(parts[0]))}.{parts[1]}"


@register.simple_tag(takes_context=True)
def show_money(context, value, native_currency):
    if value is None:
        return ""
    display = context.get("display_currency")
    target = display if display and display != native_currency else native_currency
    if target != native_currency:
        from apps.real_estate.exchange_rates import convert

        try:
            converted = convert(Decimal(str(value)), native_currency, target)
            if converted is not None:
                return money(converted, target)
        except (InvalidOperation, TypeError, ValueError):
            pass
    return money(value, native_currency)


OTHER_CURRENCY = {"CAD": "EUR", "EUR": "CAD"}


@register.simple_tag
def other_currency(currency):
    return OTHER_CURRENCY.get(currency, "EUR")


@register.filter
def signed_pct(value):
    if value is None:
        return ""
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    formatted = f"{value:.1f}%"
    if value > 0:
        return f"+{formatted}"
    return formatted


@register.filter
def convert_to(value, args):
    if value is None:
        return ""
    try:
        from_currency, to_currency = args.split(",")
    except ValueError:
        return ""
    from apps.real_estate.exchange_rates import convert

    try:
        result = convert(Decimal(str(value)), from_currency.strip(), to_currency.strip())
    except (InvalidOperation, TypeError, ValueError):
        return ""
    if result is None:
        return ""
    return money(result, to_currency.strip())
