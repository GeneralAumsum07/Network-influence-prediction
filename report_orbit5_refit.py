"""
report_orbit5_refit.py - old-vs-new for the r=1 cells refitted after the
5-node orbit radius retag.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (finding P1-01).

WHAT IT COMPARES
----------------
`repair_orbit5_radius.py --apply` backed up every sweep file to `.preorbit5`
before evicting the radius-1 rows of the two subgraph-inclusive tiers, and
`run_orbit5_refit.sh` refilled them with the corrected column set (six 5-node
orbits fewer). This script pairs each old row with its new row on
(target, radius, richness, seed) and reports, per (file, target, tier):

  old mean tau, new mean tau, mean paired difference, paired sd, and a
  descriptive flag when |mean diff| > 2 x paired sd over the 10 shared seeds -
  the same 2-sd rule used everywhere else in the project, with the same
  caveat: descriptive, not a hypothesis test (see Task 6 finding P3-01).

It also checks that the refit is COMPLETE: every evicted key is back in the
CSV and in the npz, no key is duplicated, and n_features dropped by exactly
six on every refitted row.

Rachit asked for the old and new numbers side by side rather than a silent
replacement, and the old rows are preserved unchanged in the .preorbit5
backups (root copies under cache_archive/pre_orbit5_20260911/ since
2026-09-13); this report is the reading of those two files.

Writes results/RESULTS_orbit5_refit_20260911.txt and
results/orbit5_refit_paired_20260911.csv.
"""
from __future__ import annotations

import glob
import os
import re

import numpy as np
import pandas as pd

from repair_orbit5_radius import BACKUP_SUFFIX, STALE_RADIUS, STALE_TIERS, tags

KEY = ["target", "radius", "richness", "seed"]
OUT_TXT = "results/RESULTS_orbit5_refit_20260911.txt"
OUT_CSV = "results/orbit5_refit_paired_20260911.csv"


def backup_path(sweep_path: str) -> str:
    """Where the `.preorbit5` copy of a sweep file lives.

    2026-09-13 (Claude Opus 5): the root-level backups moved to
    cache_archive/pre_orbit5_20260911/ in the root tidy-up (see
    cache_archive/README.md); estimator backups stayed beside their files
    under estimators/. Look in the archive first, then beside the file, so the
    report reads the same bytes it read on 2026-09-11 either way.
    """
    archived = os.path.join("cache_archive", "pre_orbit5_20260911",
                            os.path.basename(sweep_path) + BACKUP_SUFFIX)
    return archived if os.path.exists(archived) else sweep_path + BACKUP_SUFFIX


def pair(sweep_path: str, oof_path: str, label: str, lines: list[str]) -> pd.DataFrame:
    old = pd.read_csv(backup_path(sweep_path))
    new = pd.read_csv(sweep_path)
    stale = lambda d: (d.radius == STALE_RADIUS) & d.richness.isin(STALE_TIERS)
    o, n = old[stale(old)], new[stale(new)]

    # Completeness. The resume rule refits a cell only when BOTH its row and
    # its prediction vector are missing, so a partial refill would show here
    # as a key absent from one store or the other.
    ok_rows = len(n) == len(o) and not n.duplicated(KEY).any()
    ok_keys = set(map(tuple, o[KEY].values)) == set(map(tuple, n[KEY].values))
    with np.load(oof_path) as z:
        keys = set(z.files)
    ok_oof = all(f"{r.target}|{r.radius}|{r.richness}|{r.seed}" in keys for r in n.itertuples())
    unchanged = pd.merge(old[~stale(old)], new[~stale(new)], on=KEY, suffixes=("_o", "_n"))
    ok_rest = (len(unchanged) == (~stale(old)).sum()
               and np.allclose(unchanged.kendall_tau_o, unchanged.kendall_tau_n))
    m = pd.merge(o, n, on=KEY, suffixes=("_old", "_new"))
    ok_feat = bool(((m.n_features_old - m.n_features_new) == 6).all())
    lines.append(f"{label}: refitted rows {len(n)}/{len(o)}  keys match={ok_keys}  "
                 f"no duplicates={not n.duplicated(KEY).any()}  oof complete={ok_oof}  "
                 f"non-r1 rows byte-stable={ok_rest}  n_features -6 everywhere={ok_feat}")
    if not (ok_rows and ok_keys and ok_oof and ok_rest and ok_feat):
        lines.append("  *** INCOMPLETE OR INCONSISTENT REFIT - do not fingerprint ***")

    m["d_tau"] = m.kendall_tau_new - m.kendall_tau_old
    m["file"] = label
    return m


def main() -> None:
    lines = ["RESULTS: r=1 subgraph-tier refit after the 5-node orbit radius retag",
             "Written 2026-09-11 by report_orbit5_refit.py (Claude Opus 5); see the module docstring.",
             "Old = .preorbit5 backup (six orbits 56,57,65,66,68,70 at hop 1); new = refit with them at hop 2.",
             "star: |mean d_tau| > 2 x paired sd over the shared seeds (descriptive rule, not a test).",
             ""]
    frames = []
    for tag in tags():
        frames.append(pair(f"sweep_{tag}.csv", f"cache_oof_{tag}.npz", f"{tag} rf", lines))
        for est_csv in sorted(glob.glob(os.path.join("estimators", f"sweep_{tag}__*.csv"))):
            est = re.match(r".*__(.+)\.csv$", os.path.basename(est_csv)).group(1)
            oof = os.path.join("estimators", f"cache_oof_{tag}__{est}.npz")
            frames.append(pair(est_csv, oof, f"{tag} {est}", lines))
    m = pd.concat(frames, ignore_index=True)
    m.to_csv(OUT_CSV, index=False)

    g = (m.groupby(["file", "target", "richness"])
          .agg(n=("d_tau", "size"), tau_old=("kendall_tau_old", "mean"),
               tau_new=("kendall_tau_new", "mean"), d_mean=("d_tau", "mean"),
               d_sd=("d_tau", lambda s: s.std(ddof=1)))
          .reset_index())
    g["star"] = np.where(g.d_mean.abs() > 2 * g.d_sd, "*", "")
    lines += ["", f"{'file':30s} {'target':13s} {'tier':28s} {'n':>2s} {'tau_old':>9s} {'tau_new':>9s} "
              f"{'d_mean':>9s} {'d_sd':>8s}"]
    for r in g.itertuples():
        lines.append(f"{r.file:30s} {r.target:13s} {r.richness:28s} {r.n:2d} {r.tau_old:9.4f} "
                     f"{r.tau_new:9.4f} {r.d_mean:+9.4f} {r.d_sd:8.4f} {r.star}")
    lines += ["", "SUMMARY",
              f"  refitted cells: {len(m)}",
              f"  (file, target, tier) groups: {len(g)}; starred: {int((g.star == '*').sum())}",
              f"  mean d_tau over all cells: {m.d_tau.mean():+.5f}; "
              f"largest |d_mean| group: {g.loc[g.d_mean.abs().idxmax(), ['file', 'target', 'richness']].tolist()} "
              f"{g.d_mean.abs().max():+.4f}",
              f"  groups where new < old (the shallow tag inflated r=1): {int((g.d_mean < 0).sum())}; "
              f"new > old: {int((g.d_mean > 0).sum())}"]
    txt = "\n".join(lines) + "\n"
    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print(txt)
    print("wrote", OUT_TXT, "and", OUT_CSV)


if __name__ == "__main__":
    main()
