"""Entry point so ``python -m csvpeek`` works without installing."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
