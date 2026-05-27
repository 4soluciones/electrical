from django import template
from django.template.loader import get_template


register = template.Library()


@register.filter(name='zfill')
def zfill(d, k):
    res = str(d).zfill(int(k))
    return res


@register.filter(name='stock_near_min')
def stock_near_min(stock, stock_min):
    """True si el stock está en o cerca del mínimo (hasta 15% por encima)."""
    try:
        s = float(stock)
        m = float(stock_min)
        if m <= 0:
            return False
        return s <= m * 1.15
    except (TypeError, ValueError):
        return False


@register.filter(name='stock_near_max')
def stock_near_max(stock, stock_max):
    """True si el stock está en o cerca del máximo (desde 85% del límite)."""
    try:
        s = float(stock)
        m = float(stock_max)
        if m <= 0:
            return False
        return s >= m * 0.85
    except (TypeError, ValueError):
        return False
