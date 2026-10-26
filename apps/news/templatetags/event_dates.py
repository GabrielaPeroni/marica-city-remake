from django import template
from django.utils import timezone
from django.utils.formats import date_format, get_format
from django.utils.translation import get_language
from django.utils.translation import gettext as _

register = template.Library()


def _cased(text):
    # Português e espanhol escrevem meses e dias da semana em minúsculas
    return text if (get_language() or "").startswith("en") else text.lower()


@register.filter
def event_when(event):
    """Data do evento por extenso no idioma ativo, com intervalo se houver."""
    if not event.event_date:
        return ""
    start = timezone.localtime(event.event_date)
    end = event.event_end_date and timezone.localtime(event.event_end_date)
    month_day = get_format("MONTH_DAY_FORMAT")

    if end and end.date() != start.date():
        if (end.year, end.month) == (start.year, start.month):
            return _cased(
                _("%(start_day)s a %(end_day)s de %(month)s")
                % {
                    "start_day": start.day,
                    "end_day": end.day,
                    "month": date_format(start, "F"),
                }
            )
        return _cased(
            _("%(start)s a %(end)s")
            % {
                "start": date_format(start, month_day),
                "end": date_format(end, month_day),
            }
        )

    text = _cased(date_format(start, f"l, {month_day}"))
    if (start.hour, start.minute) != (0, 0):
        text = f"{text}, {date_format(start, 'TIME_FORMAT')}"
    return text
