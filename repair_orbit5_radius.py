"""
repair_orbit5_radius.py - retag six 5-node orbit columns hop 1 -> 2 and evict
every sweep cell that was fitted with them at radius 1.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (finding P1-01).

WHY THIS EXISTS
---------------
`influence/graphlets.py` said ORBIT5_RADIUS was the maximum over graph families
of the measured radius. `_calib.calibrate` was not computing a maximum: the
first family to touch an orbit fixed its radius, and a family that did not
contain the orbit at all still voted "1". Six orbits - 56, 57, 65, 66, 68, 70 -
shipped at radius 1 when two of three families measure 2 and the exact
eccentricity reference (_calib.derive_node_radius) is 2. So every r=1 cell of
a subgraph-inclusive tier was fitted with six columns a radius-1 observer
cannot compute. That can only inflate the r=1 rung; by how much is unmeasured
until the cells are refitted, which is what this script prepares.

A retag is a refit, not a relabel - see repair_column_order.py: the random
forest draws split candidates by column INDEX, so any change to the column
list changes the fitted model, and a cell whose feature SET shrank by six is
simply a different experiment. The stored r=1 numbers are therefore evicted so
that `stage2_sweep.py`'s resume logic (metrics row AND prediction vector both
present, else refit) refills exactly those cells.

WHAT IT TOUCHES
---------------
  cache_registry_<tag>.csv        hop 1 -> 2 on the six rows, row order kept
                                  (so r=2 and r=3 column ORDER is unchanged and
                                  those cells stay valid). Backup: .preorbit5
  sweep_<tag>.csv                 drop radius==1 rows of the two subgraph tiers
  cache_oof_<tag>.npz             drop the matching prediction vectors
  estimators/sweep_<tag>__<est>.csv and cache_oof_<tag>__<est>.npz
                                  same, for every quarantined estimator
                                  (hgb, hgb_matched, ridge, rf_log1p): the M4
                                  estimator-invariance claim was made on the
                                  same mis-tagged columns.

It does NOT write `sweep_<tag>.columns.json`. verify_pipeline.py check [8]
must FAIL on the r=1 cells between this eviction and the refit; regenerate the
fingerprint only after `stage2_sweep.py` has refilled them, with
`--fingerprint`, which delegates to repair_column_order.write_column_fingerprint.

Run:  python repair_orbit5_radius.py            dry run, reports only
      python repair_orbit5_radius.py --apply    retag registries and evict
      python repair_orbit5_radius.py --fingerprint   after the refit
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd

from influence.graphlets import ORBIT5_RADIUS

# The six columns, named as stage1 registers them. Derived from the table so a
# future change to ORBIT5_RADIUS cannot leave this list stale: these are the
# 5-node orbits currently at radius 2 that a registry still lists at hop 1.
RETAGGED_ORBITS = (56, 57, 65, 66, 68, 70)
STALE_TIERS = ("node+edge+subgraph", "node+edge+subgraph+dynamic")
STALE_RADIUS = 1
BACKUP_SUFFIX = ".preorbit5"


def registry_columns() -> list[str]:
    for k in RETAGGED_ORBITS:
        assert ORBIT5_RADIUS[k] == 2, (
            f"orbit {k} is at radius {ORBIT5_RADIUS[k]} in graphlets.py; this "
            f"script encodes the 2026-09-11 retag to 2 and must not run otherwise")
    return [f"orbit_{k}_g5" for k in RETAGGED_ORBITS]


def assert_column_invariants(tag: str, old: pd.DataFrame, new: pd.DataFrame) -> None:
    """
    Prove the blast radius is exactly the r=1 subgraph-inclusive cells.

    The retag must (a) leave every r=0, r>=2 column list byte-identical, in
    ORDER - a reordered list is the repair_column_order.py bug all over again -
    (b) leave r=1 node and node+edge untouched, and (c) shrink r=1 subgraph
    tiers by precisely the six orbits, with the survivors in their old order.
    Anything else means the registry is not the one this script was written
    against, and nothing is evicted.
    """
    from influence.experiment import TIER_LADDER
    from influence.features import select_features
    X = pd.read_csv(f"cache_features_{tag}.csv", nrows=1)  # names only
    six = set(registry_columns())
    for r in range(0, 4):
        for tier_name, tiers in TIER_LADDER.items():
            a = select_features(X, old, max_hop=r, tiers=tiers)
            b = select_features(X, new, max_hop=r, tiers=tiers)
            if r == STALE_RADIUS and tier_name in STALE_TIERS:
                assert set(a) - set(b) == six and [c for c in a if c not in six] == b, \
                    f"{tag} r={r} {tier_name}: expected exactly the six orbits to leave"
            else:
                assert a == b, f"{tag} r={r} {tier_name}: column list changed - refusing"


def retag_registry(tag: str, apply: bool) -> int:
    path = f"cache_registry_{tag}.csv"
    reg = pd.read_csv(path)
    cols = registry_columns()
    mask = reg.feature.isin(cols)
    if int(mask.sum()) != len(cols):
        raise SystemExit(f"{path}: expected {len(cols)} orbit rows, found {int(mask.sum())}")
    stale = reg[mask & (reg.hop == 1)]
    if stale.empty:
        print(f"  registry already at hop 2 for all six")
        return 0
    new = reg.copy()
    new.loc[mask, "hop"] = 2
    assert_column_invariants(tag, reg, new)
    print("  column invariants hold: only r=1 subgraph tiers change, by exactly the six orbits")
    if apply:
        if not os.path.exists(path + BACKUP_SUFFIX):
            shutil.copy2(path, path + BACKUP_SUFFIX)
        new.to_csv(path, index=False)
        print(f"  retagged {len(stale)} registry rows hop 1 -> 2 (backup {path + BACKUP_SUFFIX})")
    else:
        print(f"  would retag {len(stale)} registry rows: {stale.feature.tolist()}")
    return len(stale)


def evict(sweep_path: str, oof_path: str, apply: bool) -> int:
    d = pd.read_csv(sweep_path)
    stale = (d.radius == STALE_RADIUS) & d.richness.isin(STALE_TIERS)
    n = int(stale.sum())
    if n == 0 or not apply:
        return n
    for p in (sweep_path, oof_path):
        if os.path.exists(p) and not os.path.exists(p + BACKUP_SUFFIX):
            shutil.copy2(p, p + BACKUP_SUFFIX)
    d[~stale].to_csv(sweep_path, index=False)
    if os.path.exists(oof_path):
        with np.load(oof_path) as z:
            store = {k: z[k] for k in z.files}
        drop = [k for k in store
                if len(k.split("|")) == 4
                and k.split("|")[1] == str(STALE_RADIUS)
                and k.split("|")[2] in STALE_TIERS]
        for k in drop:
            del store[k]
        np.savez_compressed(oof_path, **store)
        print(f"    {oof_path}: dropped {len(drop)} prediction vectors")
    return n


def main() -> None:
    apply = "--apply" in sys.argv
    if "--fingerprint" in sys.argv:
        from repair_column_order import write_column_fingerprint
        for tag in tags():
            print("wrote", write_column_fingerprint(tag))
        return
    print("MODE:", "APPLY" if apply else "DRY RUN (pass --apply to act)")
    total = 0
    for tag in tags():
        print(f"\n{tag}")
        retag_registry(tag, apply)
        n = evict(f"sweep_{tag}.csv", f"cache_oof_{tag}.npz", apply)
        print(f"  sweep_{tag}.csv: {'evicted' if apply else 'would evict'} {n} rows")
        total += n
        for est_csv in sorted(glob.glob(os.path.join("estimators", f"sweep_{tag}__*.csv"))):
            est = re.match(r".*__(.+)\.csv$", os.path.basename(est_csv)).group(1)
            oof = os.path.join("estimators", f"cache_oof_{tag}__{est}.npz")
            n = evict(est_csv, oof, apply)
            print(f"  {est_csv}: {'evicted' if apply else 'would evict'} {n} rows")
            total += n
    print(f"\ntotal {'evicted' if apply else 'to evict'}: {total} cells")
    if apply:
        print("Refill with stage2_sweep.py (raw, then each estimator), then run "
              "`repair_orbit5_radius.py --fingerprint` and verify_pipeline.py.")


def tags() -> list[str]:
    return sorted(m.group(1) for m in
                  (re.match(r"sweep_(.+)\.csv$", os.path.basename(p)) for p in glob.glob("sweep_*.csv"))
                  if m and not m.group(1).endswith(".columns"))


if __name__ == "__main__":
    main()
