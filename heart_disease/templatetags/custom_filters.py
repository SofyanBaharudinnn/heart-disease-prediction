from django import template

register = template.Library()

@register.filter
def getitem(dictionary, key):
    """Ambil nilai dari dict dengan key dinamis."""
    return dictionary.get(str(key), '')

@register.filter
def mul(value, arg):
    return float(value) * float(arg)

@register.filter
def percentage(value):
    return f"{float(value)*100:.1f}"
