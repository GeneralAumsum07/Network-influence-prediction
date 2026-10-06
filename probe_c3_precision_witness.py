"""Run one pinned, bounded C3 local-precision witness graph at a time.

This command neither loads the legacy C3 raw graph path nor computes exact
centrality.  It streams only the supplied BRAVA ABCDE text, builds a bounded
whole-graph CSR, and publishes conditional local witness evidence.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from precision_witness import OUTPUT_ROOT, SORT_PAYLOAD_CAP, SPECS, PrecisionWitnessError, run_precision_witness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, choices=sorted(SPECS),
                        help="one pinned ABCDE graph; concurrent graphs are prohibited")
    parser.add_argument("--brava", required=True, type=Path,
                        help="existing BRAVA checkout containing datasets/abcde")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT,
                        help="new Phase 6 artifact directory (default: results/phase6_precision_witness)")
    parser.add_argument("--workers", type=int, default=1,
                        help="must remain one: construction is serial by design")
    parser.add_argument("--payload-mib", type=int, default=SORT_PAYLOAD_CAP // (1024 * 1024),
                        help="external-sort payload cap, at most 192 MiB")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_precision_witness(
            SPECS[args.graph], args.brava, args.output_root,
            payload_bytes=args.payload_mib * 1024 * 1024, workers=args.workers,
            require_preflight=True,
        )
    except PrecisionWitnessError as exc:
        parser.error(str(exc))
    print(
        f"{result['graph']}: conditional witness complete; "
        f"targets={result['target_count']}, usable_pairs={result['usable_pair_count']}, "
        f">5e-15_pairs={result['gt_5e15_qualifying_pair_count']}, "
        f">1e-14_pairs={result['gt_1e14_qualifying_pair_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
