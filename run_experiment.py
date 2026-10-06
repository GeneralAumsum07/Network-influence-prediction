"""
Convenience wrapper: prepare + sweep one network in a single command.

WHAT THIS USED TO BE, AND WHY IT CHANGED
----------------------------------------
This file previously reimplemented the whole pipeline inline - load, threshold,
cascades, features, targets, sweep - and wrote its outputs under a DIFFERENT
naming scheme (`results_<tag>.csv`, `features_<tag>.csv`, ...) from the one
everything downstream reads (`cache_*`, `sweep_*`). Nothing consumed those
files. Worse, it was a second copy of the pipeline that could silently drift
from stage1/stage2 and produce numbers that disagreed with the real ones for
reasons nobody would think to look for.

It is now a thin wrapper that shells out to the same two stages you would run
by hand. There is exactly one implementation of the pipeline, and this file
cannot disagree with it.

Usage:
    python run_experiment.py data/ca-GrQc.txt [n_sims] [multiple] [n_seeds]
"""
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGETS = "spread_mean,spread_cv,spread_resid,betweenness"
MAX_HOP = 3


def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"step failed with exit code {result.returncode}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)

    path = sys.argv[1]
    n_sims = sys.argv[2] if len(sys.argv) > 2 else "4000"
    multiple = sys.argv[3] if len(sys.argv) > 3 else "1.5"
    n_seeds = sys.argv[4] if len(sys.argv) > 4 else "10"

    tag = Path(path).stem
    py = sys.executable   # same interpreter, so the env cannot differ

    # Input-identity guards (Task 6 audit P1-02/P2-04, 2026-09-11) are NOT
    # duplicated here on purpose: stage 1 records the edge list's sha256 in
    # cache_meta and stage 2 refuses a mismatched cache or a sweep whose
    # inputs changed. This wrapper inherits both by shelling out - a second
    # copy here is exactly the drift the docstring above warns about.
    run([py, "stage1_prepare.py", path, n_sims, multiple])
    run([py, "stage2_sweep.py", tag, DEFAULT_TARGETS, str(MAX_HOP), n_seeds])

    print(f"\ndone: {tag}")
    print("  next:  python analyse.py")
    print("         python make_fig1.py")


if __name__ == "__main__":
    main()
