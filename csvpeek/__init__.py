"""csvpeek — a zero-dependency CSV profiler."""

from .core import ColumnProfile, profile_csv, profile_rows, render_table, to_json

__version__ = "0.1.0"
__all__ = ["ColumnProfile", "profile_csv", "profile_rows", "render_table", "to_json", "__version__"]
