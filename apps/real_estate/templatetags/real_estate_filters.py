from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _format_with_commas(n):
    """Format an integer with comma thousands separators."""
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
    """Format a Decimal as Canadian dollars: $1,234 or $1,234.56."""
    if value is None:
        return ""
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    if value == value.to_integral_value():
        return f"${_format_with_commas(int(value))}"
    formatted = f"{value:.2f}"
    parts = formatted.split(".")
    return f"${_format_with_commas(int(parts[0]))}.{parts[1]}"
