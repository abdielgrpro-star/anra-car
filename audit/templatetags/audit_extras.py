import json

from django import template

register = template.Library()


@register.filter
def pretty_json(value):
    if value is None:
        return "{}"

    try:
        return json.dumps(
            value,
            indent=4,
            ensure_ascii=False,
            sort_keys=True,
        )
    except TypeError:
        return str(value)