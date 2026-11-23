"""Command line: `python -m crink validate` and `python -m crink build`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .build import VERIFICATION_WEIGHTS, build
from .schema import validate

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crink", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="check data/raw/events.csv against the codebook")
    v.add_argument("--events", default=ROOT / "data/raw/events.csv", type=Path)

    b = sub.add_parser("build", help="validate, then write processed tables, graphs and figures")
    b.add_argument("--raw", default=ROOT / "data/raw", type=Path)
    b.add_argument("--out", default=ROOT / "data/processed", type=Path)
    b.add_argument("--figures", default=ROOT / "figures", type=Path)
    b.add_argument("--min-verification", choices=["A", "B", "C"], default="C",
                   help="robustness check: drop events below this grade (A strictest)")
    b.add_argument("--no-figures", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        events = pd.read_csv(args.events, dtype=str, keep_default_na=False)
        problems = validate(events)
        for p in problems:
            print(p)
        print(f"{len(events)} events, {len(problems)} problem(s)")
        return 1 if problems else 0

    tables = build(args.raw, args.out, VERIFICATION_WEIGHTS, args.min_verification)
    if not args.no_figures:
        from .plots import make_all

        for path in make_all(tables["dyad_year"], args.figures):
            print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    print(f"built {len(tables['events'])} events -> {len(tables['dyad_events'])} dyad rows, "
          f"{len(tables['directed_flows'])} directed flows")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
