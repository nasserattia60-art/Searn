from django import template

register = template.Library()


@register.filter
def dict_key(d, key):
    """Get a dictionary value by key. Usage: {{ my_dict|dict_key:key }}"""
    if d is None:
        return None
    return d.get(key, None)