"""
sweep_inputs.py - bind a stage-2 sweep to the exact inputs it was fitted on.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (findings
P1-02 and P2-04).

THE GAP THIS CLOSES
-------------------
stage2_sweep.py resumes on cell PRESENCE: a (target, radius, richness, seed)
row in sweep_<tag>.csv plus a matching key in cache_oof_<tag>.npz means the
cell is done. Nothing checked that the cache_features / cache_registry /
cache_targets files a resumed run reads are the ones the existing rows were
fitted on. Re-run stage 1 with a changed registry (the 2026-08-31 retag was
exactly that) and resume instead of deleting, and rows from two different
feature tables sit in one CSV indistinguishably. The Phase 6 runners written
after 2026-09-08 all bind their inputs by hash; the sweep predates that
standard. This module brings it up to it.

Two checks, both cheap:

  1. SOURCE IDENTITY (P1-02). cache_meta_<tag>.json now records the SHA-256
     of the edge list it was built from (`provenance.source_sha256`, written
     by influence.preprocessing.load_edgelist since 2026-09-11). For the five
     caches built before that date the hash lives in the sidecar
     cache_provenance_audit_20260911.json, matched on the cache_meta file's
     own hash so a rebuilt cache never inherits a stale entry. If the data
     file on disk hashes differently, the sweep refuses to run - the cache is
     not what its name claims.

  2. INPUT BINDING (P2-04). On its first write a sweep records the SHA-256 of
     its four input files in `<sweep>.inputs.json`. Every later run compares
     before touching the CSV and refuses on any difference. A legacy sweep
     with no sidecar gets one recorded at the first resume, flagged
     `bound_from = "resume"` so a reader knows rows before that timestamp are
     bound only by the column fingerprint (sweep_<tag>.columns.json) and the
     reproduction checks, not by this file.

Nothing here modifies a sweep, a cache or a recorded hash. A mismatch is an
error message and a non-zero exit; the fix is to delete the sweep and refit,
never to edit the sidecar.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from influence.preprocessing import file_sha256

INPUT_FILES = ("cache_features_{tag}.csv", "cache_registry_{tag}.csv",
               "cache_targets_{tag}.csv", "cache_meta_{tag}.json")
PROVENANCE_AUDIT_SIDECAR = "cache_provenance_audit_20260911.json"


def sidecar_path(sweep_csv: str | Path) -> str:
    """sweep_x.csv -> sweep_x.inputs.json (same directory, so the estimators/
    quarantine is preserved - see stage2_sweep's module docstring)."""
    sweep_csv = str(sweep_csv)
    assert sweep_csv.endswith(".csv"), sweep_csv
    return sweep_csv[:-4] + ".inputs.json"


def input_hashes(tag: str, root: str | Path = ".") -> dict[str, str]:
    """Root-relative posix name -> sha256 for the four stage-1 outputs."""
    root = Path(root)
    out = {}
    for pattern in INPUT_FILES:
        name = pattern.format(tag=tag)
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"stage-1 output missing: {name}")
        out[name] = file_sha256(path)
    return out


def recorded_source_sha256(tag: str, meta: dict, root: str | Path = ".") -> tuple[str | None, str]:
    """
    The edge-list hash the cache claims, and where the claim comes from.

    Returns (sha256 or None, origin). Live provenance wins; the dated audit
    sidecar is consulted only when its entry describes THIS cache_meta file
    byte-for-byte, so a cache rebuilt after 2026-09-11 without the key (which
    cannot happen with the current loader, but could with an old checkout)
    is reported as unbound rather than matched to a stale audit.
    """
    live = meta.get("provenance", {}).get("source_sha256")
    if live:
        return live, "cache_meta provenance"
    root = Path(root)
    sidecar = root / PROVENANCE_AUDIT_SIDECAR
    if sidecar.is_file():
        with open(sidecar, encoding="utf-8") as fh:
            audit = json.load(fh).get("networks", {}).get(tag)
        meta_path = root / f"cache_meta_{tag}.json"
        if audit and meta_path.is_file() and audit.get("cache_meta_sha256") == file_sha256(meta_path):
            return audit["source_sha256"], PROVENANCE_AUDIT_SIDECAR
    return None, "unbound"


def check_source_identity(tag: str, meta: dict, root: str | Path = ".") -> str:
    """
    Refuse if the edge list on disk is not the one the cache was built from.

    Returns a one-line status for the log. A missing data file is reported,
    not fatal: stage 2 reads the cache, not the edge list, and a clone that
    has caches but no data/ should still be able to sweep. A PRESENT file
    that hashes differently is fatal - that is the swapped-input case P1-02
    describes, and no number fitted on top of it could be explained later.
    """
    expected, origin = recorded_source_sha256(tag, meta, root)
    if expected is None:
        return "source identity: cache carries no edge-list hash (unbound; pre-2026-09-11 cache without audit sidecar)"
    source = meta.get("provenance", {}).get("source", "")
    path = Path(str(source).replace("\\", "/"))
    if not path.is_absolute():
        path = Path(root) / path
    if not path.is_file():
        return f"source identity: {expected[:16]}... ({origin}); data file not on disk, not re-verified"
    actual = file_sha256(path)
    if actual != expected:
        raise SystemExit(
            f"REFUSING: {path} hashes {actual[:16]}... but cache_meta_{tag}.json "
            f"was built from {expected[:16]}... ({origin}). The cache and the "
            f"data file disagree; rebuild the cache with stage1_prepare.py or "
            f"restore the original file. Do not edit the recorded hash.")
    return f"source identity: {expected[:16]}... verified against {path.name} ({origin})"


def bind_inputs(sweep_csv: str | Path, tag: str, root: str | Path = ".",
                bound_from: str | None = None) -> str:
    """
    Record or verify the sweep's input hashes. Returns a one-line status.

    `bound_from` names how the sidecar came to exist when it is first written:
    "first_write" (fresh sweep), "resume" (legacy sweep, first resume after
    2026-09-11) or "retroactive_20260911" (record_sweep_inputs.py). It is
    stored, not interpreted - the reader decides what it implies for rows
    that predate the timestamp.
    """
    current = input_hashes(tag, root)
    sc = Path(root) / sidecar_path(sweep_csv)
    if sc.is_file():
        with open(sc, encoding="utf-8") as fh:
            recorded = json.load(fh)
        diffs = sorted(k for k in set(current) | set(recorded.get("inputs", {}))
                       if current.get(k) != recorded.get("inputs", {}).get(k))
        if diffs:
            raise SystemExit(
                f"REFUSING to append to {sweep_csv}: its inputs changed since it "
                f"was recorded ({recorded.get('recorded')}). Differing: {diffs}. "
                f"Rows already in the file were fitted on different inputs; "
                f"delete the sweep, its oof store and {sc.name} and refit, or "
                f"restore the original inputs. Do not edit the sidecar.")
        return f"inputs bound: {sc.name} matches ({len(current)} files)"
    resuming = Path(root, sweep_csv).is_file()
    payload = {
        "tag": tag,
        "sweep": str(sweep_csv).replace("\\", "/"),
        "inputs": current,
        "recorded": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bound_from": bound_from or ("resume" if resuming else "first_write"),
        "note": ("rows fitted before `recorded` are bound only by the column "
                 "fingerprint sidecar and the reproduction checks, not by this file"
                 if resuming else "every row in this sweep was fitted on these inputs"),
        "recorded_by": "influence/sweep_inputs.py (Claude Opus 5, 2026-09-11, P2-04)",
    }
    os.makedirs(sc.parent, exist_ok=True)
    with open(sc, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return f"inputs bound: wrote {sc.name} ({payload['bound_from']})"
