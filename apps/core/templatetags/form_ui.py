from django import template

register = template.Library()

WIDGET_CLASSES = {
    "select": "select w-full",
    "selectmultiple": "select w-full h-auto",
    "nullbooleanselect": "select w-full",
    "textarea": "textarea",
    "checkbox": "input",
    # O Django repete a classe no <div> que envolve as opções; o estilo vem de .choice-list
    "radioselect": "",
    "checkboxselectmultiple": "",
}


@register.filter
def ui_widget(field):
    """{{ field|ui_widget }} -> o widget com as classes do Basecoat (sem as do Bootstrap)."""
    widget = field.field.widget
    kept = [
        name
        for name in widget.attrs.get("class", "").split()
        if not name.startswith(("form-", "btn"))
    ]
    kept.insert(0, WIDGET_CLASSES.get(field.widget_type, "input"))
    classes = " ".join(kept).strip()
    widget_attrs = {k: v for k, v in widget.attrs.items() if k != "class"}
    if classes:
        widget_attrs["class"] = classes
    original, widget.attrs = widget.attrs, widget_attrs
    try:
        return field.as_widget()
    finally:
        widget.attrs = original


@register.filter
def is_choice_list(field):
    return field.widget_type in ("radioselect", "checkboxselectmultiple")
