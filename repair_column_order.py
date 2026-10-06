"""
repair_column_order.py - evict sweep cells whose COLUMN ORDER changed.

WHY THIS EXISTS
---------------
On 2026-08-31 `ball2_density` and `local_conductance_2` were retagged
edge -> subgraph. The retag rewrote `cache_registry_<tag>.csv`, and rewriting
it MOVED those two rows: they sat at positions 65 and 90 in the old file and at
107 and 109 in the new one.

That matters more than a relabelling should, because of two facts that are
individually harmless and jointly a trap:

  * `select_features` returns column names in REGISTRY ROW ORDER.
  * `RandomForestRegressor` draws its per-split candidate features from its RNG
    BY INDEX. A fixed random_state fixes the index sequence, not the features.

So permuting the columns of X - same set, same seed - builds a different
forest. The audit refitted the 400 `node+edge` cells at r=2,3, where the two
columns actually LEFT the set. It checked set equality, found the richest tiers
unchanged, and left them. Their order had changed.

MEASURED, not assumed. On ca-GrQc betweenness, node+edge+subgraph:

    r=2 seed 0   published 0.92242850   new order 0.92203768   old order 0.92242850
    r=3 seed 3   published 0.92153910   new order 0.92228977   old order 0.92153910

The old order reproduces the stored value exactly (0.00e+00). The new order
differs by up to 1.08e-03 - the same size as the seed-to-seed spread that this
project reports its richness gains against, and larger than several of them.

WHY THIS IS NOT A SMALL BOOKKEEPING PROBLEM
-------------------------------------------
r*(eps) is read off the `node+edge+subgraph` curve. Its r=0 and r=1 points are
clean (the two columns are hop-2, so they are absent there), but its r=2 and
r=3 points are exactly the stale ones. The audit's reassurance that no locality
horizon moved was therefore computed on numbers that had not been refitted, and
"2,804 cells bit-identical" was true only because those cells were never re-run.
An identity you obtain by not recomputing is not evidence.

WHAT THIS SCRIPT DOES
---------------------
It does NOT refit anything. It removes the stale rows from `sweep_<tag>.csv`
and the matching vectors from `cache_oof_<tag>.npz`, so that re-running
`stage2_sweep.py` - whose resume logic already requires BOTH artefacts to be
present before it skips a cell - refills exactly those cells and nothing else.
Splitting eviction from refitting keeps the expensive step restartable and
keeps this script auditable: it only ever deletes what it can name.

Originals are copied to `*.prereorder` first. Nothing is overwritten in place
until the replacement has been built in memory.

Run:  python repair_column_order.py [--apply]
Without --apply it reports what it would evict and changes nothing.
"""
import glob
import json
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd

from influence.experiment import TIER_LADDER
from influence.features import select_features

MAX_HOP = 3


def stale_cells(tag: str) -> list[tuple[int, str]]:
    """
    (radius, richness) pairs whose column LIST changed by order alone.

    Set changes are excluded deliberately: those cells were correctly refitted
    on 2026-08-31, and re-evicting them would throw away good work. The
    reference for "before" is the `.pretier` registry backup, which is the only
    record of the order that produced the stored numbers.
    """
    old_path = f"cache_registry_{tag}.csv.pretier"
    if not os.path.exists(old_path):
        raise SystemExit(
            f"{old_path} missing - without it there is no record of the column "
            f"order that produced sweep_{tag}.csv, and staleness cannot be "
            f"determined. Do not guess; the whole point of this script is that "
            f"the difference is invisible in the data.")

    # nrows=1 is enough: select_features only needs the column NAMES to
    # intersect against, and the feature tables are large.
    X = pd.read_csv(f"cache_features_{tag}.csv", nrows=1)
    new = pd.read_csv(f"cache_registry_{tag}.csv")
    old = pd.read_csv(old_path)

    out = []
    for r in range(0, MAX_HOP + 1):
        for tier_name, tiers in TIER_LADDER.items():
            cn = select_features(X, new, max_hop=r, tiers=tiers)
            co = select_features(X, old, max_hop=r, tiers=tiers)
            if cn != co and set(cn) == set(co):
                out.append((r, tier_name))
    return out


def write_column_fingerprint(tag: str) -> str:
    """
    Record the exact ordered column list behind every cell of this sweep.

    This is the durable half of the fix. The bug was undetectable because
    nothing on disk remembered WHICH columns, in WHICH order, produced a stored
    tau - so a registry edit could invalidate results with no diff to show for
    it. With this sidecar, `verify_pipeline.py` can compare what the registry
    yields today against what it yielded when the numbers were made, and a
    future retag fails loudly instead of silently.
    """
    X = pd.read_csv(f"cache_features_{tag}.csv", nrows=1)
    reg = pd.read_csv(f"cache_registry_{tag}.csv")
    fp = {}
    for r in range(0, MAX_HOP + 1):
        for tier_name, tiers in TIER_LADDER.items():
            cols = select_features(X, reg, max_hop=r, tiers=tiers)
            if cols:
                fp[f"{r}|{tier_name}"] = cols
    path = f"sweep_{tag}.columns.json"
    with open(path, "w") as fh:
        json.dump(fp, fh, indent=1)
    return path


def evict(tag: str, cells: list[tuple[int, str]], apply: bool) -> int:
    """Drop the named cells from the metrics CSV and the prediction store."""
    sweep_path, oof_path = f"sweep_{tag}.csv", f"cache_oof_{tag}.npz"
    d = pd.read_csv(sweep_path)

    keep = pd.Series(True, index=d.index)
    for r, tier in cells:
        keep &= ~((d.radius == r) & (d.richness == tier))
    n_dropped = int((~keep).sum())

    if not apply:
        return n_dropped

    # Back up BOTH artefacts before touching either. They are only meaningful
    # together - a CSV that lost rows beside an npz that kept its vectors would
    # make the resume logic skip cells it should refit.
    shutil.copy2(sweep_path, sweep_path + ".prereorder")
    if os.path.exists(oof_path):
        shutil.copy2(oof_path, oof_path + ".prereorder")

    d[keep].to_csv(sweep_path, index=False)

    if os.path.exists(oof_path):
        with np.load(oof_path) as z:
            store = {k: z[k] for k in z.files}
        # Keys are `target|radius|richness|seed`. Match on the middle two
        # fields only - the target and seed are irrelevant to whether the
        # column order moved, and every one of them is affected.
        stale_keys = {(str(r), tier) for r, tier in cells}
        drop = [k for k in store
                if len(k.split("|")) == 4
                and tuple(k.split("|")[1:3]) in stale_keys]
        for k in drop:
            del store[k]
        np.savez_compressed(oof_path, **store)
        print(f"  dropped {len(drop)} prediction vectors")

    return n_dropped


def main() -> None:
    apply = "--apply" in sys.argv
    tags = sorted(
        m.group(1) for m in
        (re.match(r"sweep_(.+)\.csv$", os.path.basename(p))
         for p in glob.glob("sweep_*.csv"))
        if m and not m.group(1).endswith(".columns"))

    if not tags:
        raise SystemExit("no sweep_*.csv found")

    print("MODE:", "APPLY (files will be rewritten)" if apply
          else "DRY RUN (nothing changes; pass --apply to act)")

    total = 0
    for tag in tags:
        cells = stale_cells(tag)
        print(f"\n{tag}")
        if not cells:
            print("  no order-only changes - nothing to evict")
        for r, tier in cells:
            print(f"  stale: r={r} {tier}")
        n = evict(tag, cells, apply) if cells else 0
        total += n
        print(f"  {'evicted' if apply else 'would evict'} {n} rows")
        if apply:
            print(f"  wrote {write_column_fingerprint(tag)}")

    print(f"\ntotal {'evicted' if apply else 'to evict'}: {total} cells")
    if apply:
        print("\nNow refill them - stage2_sweep.py will fit only what is "
              "missing:\n"
              "    python stage2_sweep.py <tag> "
              "spread_mean,spread_cv,betweenness,spread_resid 3 10")


if __name__ == "__main__":
    main()
