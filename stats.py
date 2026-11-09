"""Агрегация пространственных таблиц для вкладки статистики."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .catalog import SpatialTable, geometry_rank, normalize_geometry_type
from .i18n import tr

MIB = 1024 * 1024
GIB = 1024 * MIB

SIZE_BUCKETS: Tuple[Tuple[str, int, Optional[int]], ...] = (
    ("До 1 МБ", 0, MIB),
    ("1–10 МБ", MIB, 10 * MIB),
    ("10–100 МБ", 10 * MIB, 100 * MIB),
    ("100 МБ–1 ГБ", 100 * MIB, GIB),
    ("1 ГБ и более", GIB, None),
)


@dataclass(frozen=True)
class SizeBucketStat:
    label: str
    count: int
    total_size: int


@dataclass(frozen=True)
class TypeStat:
    name: str
    count: int
    total_size: int


def _table_size(table: SpatialTable) -> int:
    return table.total_size if table.total_size is not None else 0


def build_size_distribution(tables: Iterable[SpatialTable]) -> List[SizeBucketStat]:
    """Распределить таблицы по диапазонам размера."""

    counts = [0] * len(SIZE_BUCKETS)
    sizes = [0] * len(SIZE_BUCKETS)

    for table in tables:
        size = _table_size(table)
        bucket_index = len(SIZE_BUCKETS) - 1
        for index, (_label, minimum, maximum) in enumerate(SIZE_BUCKETS):
            if size >= minimum and (maximum is None or size < maximum):
                bucket_index = index
                break
        counts[bucket_index] += 1
        sizes[bucket_index] += size

    return [
        SizeBucketStat(
            label=tr(label),
            count=counts[index],
            total_size=sizes[index],
        )
        for index, (label, _minimum, _maximum) in enumerate(SIZE_BUCKETS)
    ]


def build_type_distribution(
    tables: Iterable[SpatialTable],
    group_of,
    other_label: str,
    limit: Optional[int] = None,
    sort_key=None,
) -> List[TypeStat]:
    """Сгруппировать таблицы по функции ``group_of``.

    ``group_of`` возвращает имя группы для таблицы. Порядок по умолчанию —
    по убыванию количества, затем по размеру и имени; ``sort_key`` позволяет
    задать собственный ключ сортировки для группы.
    """

    grouped: Dict[str, Dict[str, object]] = {}
    for table in tables:
        name = group_of(table)
        entry = grouped.get(name)
        if entry is None:
            entry = {"name": name, "count": 0, "total_size": 0}
            grouped[name] = entry
        entry["count"] = int(entry["count"]) + 1
        entry["total_size"] = int(entry["total_size"]) + _table_size(table)

    stats = [
        TypeStat(
            name=str(entry["name"]),
            count=int(entry["count"]),
            total_size=int(entry["total_size"]),
        )
        for entry in grouped.values()
    ]
    if sort_key is not None:
        stats.sort(key=sort_key)
    else:
        stats.sort(
            key=lambda item: (-item.count, -item.total_size, item.name.casefold())
        )

    if limit is not None and limit > 0 and len(stats) > limit:
        top_count = max(0, limit - 1)
        top = stats[:top_count]
        rest = stats[top_count:]
        other = TypeStat(
            name=other_label,
            count=sum(item.count for item in rest),
            total_size=sum(item.total_size for item in rest),
        )
        stats = top + [other]

    return stats


def build_geometry_type_distribution(
    tables: Iterable[SpatialTable], limit: Optional[int] = None
) -> List[TypeStat]:
    """Распределение по типу геометрии, упорядоченное по типу."""
    return build_type_distribution(
        tables,
        group_of=lambda t: normalize_geometry_type(t.geom_type),
        other_label=tr("Другие типы"),
        limit=limit,
        sort_key=lambda item: (
            geometry_rank(item.name),
            -item.count,
            item.name.casefold(),
        ),
    )


def build_schema_distribution(
    tables: Iterable[SpatialTable], limit: Optional[int] = None
) -> List[TypeStat]:
    """Распределение по схеме, упорядоченное по количеству."""
    return build_type_distribution(
        tables,
        group_of=lambda t: t.schema,
        other_label=tr("Другие схемы"),
        limit=limit,
    )


def totals(tables: Iterable[SpatialTable]) -> Tuple[int, int, int]:
    """Итоги: число таблиц, сумма строк и суммарный размер."""
    count = 0
    features = 0
    size = 0
    for table in tables:
        count += 1
        if table.feature_count is not None:
            features += table.feature_count
        size += _table_size(table)
    return count, features, size