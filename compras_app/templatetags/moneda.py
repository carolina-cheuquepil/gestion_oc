from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

register = template.Library()


def _codigo_moneda(moneda):
    if moneda is None:
        return "CLP"
    codigo = getattr(moneda, "codigo", moneda)
    return str(codigo or "CLP").upper()


def _to_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _format_number(value, decimals):
    quant = Decimal("1") if decimals == 0 else Decimal("0.01")
    number = _to_decimal(value).quantize(quant, rounding=ROUND_HALF_UP)
    formatted = f"{number:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


@register.filter(name="moneda")
def moneda(value, currency="CLP"):
    codigo = _codigo_moneda(currency)

    if codigo == "USD":
        return f"US$ {_format_number(value, 2)}"

    if codigo == "CLP":
        return f"$ {_format_number(value, 0)}"

    return f"{codigo} {_format_number(value, 2)}"
