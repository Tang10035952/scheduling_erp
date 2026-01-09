from django import template
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    attrs = field.field.widget.attrs.copy()
    existing = attrs.get("class", "")
    attrs["class"] = f"{existing} {css}".strip()
    return field.as_widget(attrs=attrs)


@register.filter(name="getattr")
def get_attribute(obj, name):
    if obj is None:
        return None
    return getattr(obj, name, None)


@register.filter(name="int_display")
def int_display(value):
    if value is None or value == "":
        return ""
    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return str(decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
