"""Core profiling logic: read a CSV and describe every column."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["ColumnProfile", "profile_csv", "profile_rows", "render_table", "to_json"]

_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S")
_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0"}


@dataclass
class ColumnProfile:
    name: str
    kind: str                      # int | float | bool | date | text | empty
    total: int = 0
    nulls: int = 0
    unique: int = 0
    minimum: Any = None
    maximum: Any = None
    mean: float | None = None
    top: list[tuple[str, int]] = field(default_factory=list)

    @property
    def null_ratio(self) -> float:
        return self.nulls / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.kind,
            "rows": self.total,
            "nulls": self.nulls,
            "null_ratio": round(self.null_ratio, 4),
            "unique": self.unique,
            "min": self.minimum,
            "max": self.maximum,
            "mean": None if self.mean is None else round(self.mean, 6),
            "top": [{"value": v, "count": c} for v, c in self.top],
        }


def _classify(values: Sequence[str]) -> str:
    """Pick the narrowest type that every non-empty value satisfies."""
    if not values:
        return "empty"
    if all(v.lower() in _TRUE | _FALSE for v in values):
        # "0"/"1" alone is ambiguous; only call it bool if a word form appears.
        if any(v.lower() in {"true", "false", "yes", "no", "y", "n"} for v in values):
            return "bool"
    try:
        for v in values:
            int(v)
        return "int"
    except ValueError:
        pass
    try:
        for v in values:
            float(v)
        return "float"
    except ValueError:
        pass
    for v in values:
        if not any(_try_date(v, fmt) for fmt in _DATE_FORMATS):
            break
    else:
        return "date"
    return "text"


def _try_date(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
        return True
    except ValueError:
        return False


def _top_values(values: Iterable[str], limit: int) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:limit]


def profile_rows(header: Sequence[str], rows: Iterable[Sequence[str]], top: int = 5) -> list[ColumnProfile]:
    """Build one :class:`ColumnProfile` per column."""
    columns: list[list[str]] = [[] for _ in header]
    nulls = [0] * len(header)

    for row in rows:
        for i in range(len(header)):
            cell = row[i].strip() if i < len(row) else ""
            if cell == "":
                nulls[i] += 1
            else:
                columns[i].append(cell)

    profiles: list[ColumnProfile] = []
    for i, name in enumerate(header):
        values = columns[i]
        kind = _classify(values)
        prof = ColumnProfile(name=name, kind=kind, total=len(values) + nulls[i], nulls=nulls[i])
        prof.unique = len(set(values))

        if kind in ("int", "float") and values:
            nums = [float(v) for v in values]
            prof.minimum = min(nums)
            prof.maximum = max(nums)
            prof.mean = sum(nums) / len(nums)
            if kind == "int":
                prof.minimum = int(prof.minimum)
                prof.maximum = int(prof.maximum)
        elif kind == "date" and values:
            parsed = sorted(v for v in values)
            prof.minimum, prof.maximum = parsed[0], parsed[-1]
        elif kind == "bool" and values:
            trues = sum(1 for v in values if v.lower() in _TRUE)
            prof.minimum, prof.maximum = False, True
            prof.mean = trues / len(values)

        if kind in ("text", "bool") or (kind == "int" and prof.unique <= max(top, 1)):
            prof.top = _top_values(values, top)

        profiles.append(prof)
    return profiles


def profile_csv(path: str | Path, top: int = 5, encoding: str = "utf-8-sig") -> list[ColumnProfile]:
    """Profile a CSV file on disk."""
    with open(path, "r", encoding=encoding, errors="replace", newline="") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        delimiter = _sniff(sample)
        reader = csv.reader(fh, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            return []
        return profile_rows(header, reader, top=top)


def _sniff(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def render_table(profiles: Sequence[ColumnProfile]) -> str:
    """Render profiles as a fixed-width text table."""
    head = ("COLUMN", "TYPE", "NULLS", "UNIQUE", "MIN", "MAX", "MEAN")
    body = [
        (
            p.name,
            p.kind,
            f"{p.nulls}/{p.total} ({p.null_ratio:.0%})" if p.total else "0/0",
            str(p.unique),
            _fmt(p.minimum),
            _fmt(p.maximum),
            _fmt(p.mean),
        )
        for p in profiles
    ]
    widths = [max(len(str(r[i])) for r in (head, *body)) for i in range(len(head))]
    line = "  ".join(str(h).ljust(w) for h, w in zip(head, widths))
    sep = "  ".join("-" * w for w in widths)
    rows = ["  ".join(str(c).ljust(w) for c, w in zip(r, widths)) for r in body]
    return "\n".join([line, sep, *rows])


def to_json(profiles: Sequence[ColumnProfile]) -> dict[str, Any]:
    return {
        "columns": [p.as_dict() for p in profiles],
        "column_count": len(profiles),
        "row_count": profiles[0].total if profiles else 0,
    }


def load_from_text(text: str, top: int = 5) -> list[ColumnProfile]:
    """Profile CSV content already held in memory (useful for tests)."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return []
    return profile_rows(header, reader, top=top)
