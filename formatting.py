"""Общие функции форматирования значений для интерфейса."""

from .i18n import tr


def format_size(size: int) -> str:
    """Преобразовать размер в байтах в читаемую строку."""

    byte_unit = tr("Б")
    units = (byte_unit, tr("КБ"), tr("МБ"), tr("ГБ"), tr("ТБ"))
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == byte_unit:
                return "{} {}".format(int(value), unit)
            if value >= 100:
                return "{:.0f} {}".format(value, unit)
            return "{:.1f} {}".format(value, unit).replace(".0 ", " ")
        value /= 1024

    return "{} {}".format(size, byte_unit)


def format_number(value) -> str:
    """Форматировать число с разделителями тысяч."""
    if value is None:
        return "—"
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value)
