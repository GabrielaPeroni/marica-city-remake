from django import template

from apps.core.content_translation import is_machine_translated, translated

register = template.Library()


@register.filter
def tr(obj, field):
    """{{ place|tr:"description" }}: campo no idioma ativo, ou o original."""
    return translated(obj, field)


@register.filter
def machine_translated(obj):
    return is_machine_translated(obj)
