from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css):
    """Return field rendered with added CSS class.

    Usage: {{ form.field|add_class:'form-control' }}
    Works with BoundField.
    """
    try:
        # If it's a BoundField, render with new attrs
        existing = field.field.widget.attrs.get('class', '')
        classes = (existing + ' ' + css).strip() if existing else css
        return mark_safe(field.as_widget(attrs={'class': classes}))
    except Exception:
        return field
