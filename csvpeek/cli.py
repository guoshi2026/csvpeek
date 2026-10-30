"""Command line entry point: ``python -m csvpeek path/to/file.csv``."""

from __future__ import annotations

import argparse
import json
import sys

from .core import profile_csv, render_table, to_json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="csvpeek",
        description="Profile a CSV file: column types, nulls, cardinality, ranges.",
    )
    p.add_argument("path", help="CSV file to inspect")
    p.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    p.add_argument("--top", type=int, default=5, metavar="N",
                   help="keep the N most frequent values per column (default: 5)")
    p.add_argument("--encoding", default="utf-8-sig", help="file encoding (default: utf-8-sig)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profiles = profile_csv(args.path, top=args.top, encoding=args.encoding)
    except FileNotFoundError:
        print(f"csvpeek: no such file: {args.path}", file=sys.stderr)
        return 2

    if not profiles:
        print("csvpeek: file is empty or has no header row", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(to_json(profiles), ensure_ascii=False, indent=2))
    else:
        print(render_table(profiles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
