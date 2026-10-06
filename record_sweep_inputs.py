"""
record_sweep_inputs.py - retroactively bind every existing sweep to the
stage-1 files it currently sits beside.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (P2-04).

WHAT THIS DOES AND DOES NOT ESTABLISH
-------------------------------------
For each sweep_<tag>.csv at the root and each estimators/sweep_<tag>__<est>.csv
this writes `<sweep>.inputs.json` with the SHA-256 of the four stage-1 files,
flagged `bound_from = "retroactive_20260911"`, and refuses to overwrite a
sidecar that already exists with different hashes.

It establishes that FROM NOW ON any change to the caches is detected before
a resume appends to these files. It does NOT establish that every row already
in them was fitted on the current caches - that evidence is (a) the column
fingerprint sidecars regenerated after the 2026-09-11 P1-01 refit, (b) the
reproduction checks in analyse_sample_efficiency.py / probe_objective_horizon.py
(FULL-tier rows reproduce to <= 5e-08), and (c) the 2026-09-11 refit itself,
which fitted the 1,700 r=1 subgraph-tier cells on exactly these caches. The
sidecar says so in its `note` field rather than implying more.

Run:  python record_sweep_inputs.py
"""
from __future__ import annotations

import glob
import os
import re

from influence.sweep_inputs import bind_inputs


def main() -> None:
    sweeps = sorted(glob.glob("sweep_*.csv")) + sorted(glob.glob(os.path.join("estimators", "sweep_*.csv")))
    for path in sweeps:
        tag = re.match(r"sweep_(.+?)(?:__.+)?\.csv$", os.path.basename(path)).group(1)
        print(f"{path:45s} tag={tag:20s} {bind_inputs(path, tag, bound_from='retroactive_20260911')}")
    print(f"{len(sweeps)} sweeps")


if __name__ == "__main__":
    main()
