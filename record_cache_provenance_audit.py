"""
record_cache_provenance_audit.py - write a dated provenance audit SIDECAR for
the existing cache_meta_<tag>.json files.

Created 2026-09-11 by Claude Opus 5 for Task 6 root integration (findings
P1-02, P1-03, P1-04).

WHY A SIDECAR, AND NOT A REWRITE
--------------------------------
The five cache_meta files were written by stage1_prepare.py on the dates the
caches were built. Their `provenance` blocks are the audit trail of THOSE
runs, and two of their fields are now known to be wrong or missing:

  * `multi_edges_collapsed` holds the pre-2026-09-11 sum of genuine
    multi-edges AND reciprocated arc pairs (P1-03) - 14,484 on ca-GrQc for a
    file that has no multi-edges at all;
  * there is no content hash of the edge list at all (P1-02), so nothing
    binds the cache to the bytes it was computed from.

Rewriting the old keys would make the record say something the 2026-08 run
did not record. And the cache_meta files are themselves bound by SHA-256 in
results/phase6_buffered_cv_provenance.json and
results/provenance_target_noise_refit_structural.json, so even ADDING a key
to them would break a recorded binding. They are therefore not touched.

Instead this script re-reads each network's source file with the CORRECTED
loader and writes one sidecar, cache_provenance_audit_20260911.json, keyed by
tag:

    "<tag>": {
        "source_sha256": ..., "source_bytes": ..., "rows_unparsed": ...,
        "multi_edges_collapsed": ...,  "reciprocated_pairs_folded": ...,
        "duplicate_rows_folded_total": ...,
        "matches_manifest_sha256": true/false,
        "reconciles_legacy_multi_edge_count": true/false,
        "reconciles_graph_size": true/false,
        "cache_meta_sha256": ...   # the cache_meta this audit describes
    }

`reconciles_legacy_multi_edge_count` is the check that matters: the legacy
`multi_edges_collapsed` must equal the new `duplicate_rows_folded_total`, and
the graph size (n, m) re-derived from the file must equal what the cache
recorded. If either fails the file on disk is NOT the file the cache was
built from, and no entry is written for that tag.

stage2_sweep.py reads `source_sha256` from the live `provenance` block for
caches built after 2026-09-11 and falls back to this sidecar for older ones
(matching on `cache_meta_sha256`, so a rebuilt cache_meta never inherits a
stale audit entry).

Idempotent. Nothing here fits a model or touches a sweep.

Run:  python record_cache_provenance_audit.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from influence.preprocessing import file_sha256, load_edgelist

SIDECAR = "cache_provenance_audit_20260911.json"
ROOT = Path(__file__).resolve().parent


def manifest_sha256() -> dict[str, str]:
    """name -> sha256 from data/manifest.json (written by fetch_data.py)."""
    with open(ROOT / "data" / "manifest.json", encoding="utf-8") as fh:
        return {row["name"]: row["sha256"] for row in json.load(fh)}


def audit_one(meta_path: Path, manifest: dict[str, str]) -> tuple[str, dict]:
    tag = re.match(r"cache_meta_(.+)\.json$", meta_path.name).group(1)
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    legacy = meta["provenance"]
    # The recorded source is whatever path stage 1 was invoked with; resolve
    # it against the project root so the audit works from any cwd.
    source = Path(legacy["source"].replace("\\", "/"))
    if not source.is_absolute():
        source = ROOT / source
    if not source.is_file():
        raise FileNotFoundError(f"{tag}: recorded source {source} not on disk")

    net = load_edgelist(source, name=tag)
    p = net.provenance
    block = {
        "cache_meta_sha256": file_sha256(meta_path),
        "source_sha256": p["source_sha256"],
        "source_bytes": p["source_bytes"],
        "rows_unparsed": p["rows_unparsed"],
        "raw_edge_rows": p["raw_edge_rows"],
        "multi_edges_collapsed": p["multi_edges_collapsed"],
        "reciprocated_pairs_folded": p["reciprocated_pairs_folded"],
        "duplicate_rows_folded_total": p["duplicate_rows_folded_total"],
        "multi_edge_semantics": p["multi_edge_semantics"],
        "matches_manifest_sha256": manifest.get(tag) == p["source_sha256"],
        # Legacy key = old semantics = multi + reciprocated.
        "reconciles_legacy_multi_edge_count":
            legacy["multi_edges_collapsed"] == p["duplicate_rows_folded_total"],
        "reconciles_graph_size": (meta["n"] == net.n and meta["m"] == net.m),
        "legacy_multi_edges_collapsed_meaning":
            "pre-2026-09-11 sum of same-orientation duplicates and reciprocated pairs (P1-03)",
    }
    return tag, block


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    manifest = manifest_sha256()
    out = {"recorded_by": "record_cache_provenance_audit.py (Claude Opus 5)",
           "recorded_on": "2026-09-11",
           "note": "sidecar to cache_meta_<tag>.json; those files are hash-bound "
                   "by Phase 6 provenance records and are deliberately not modified",
           "networks": {}}
    for meta_path in sorted(ROOT.glob("cache_meta_*.json")):
        tag, block = audit_one(meta_path, manifest)
        ok = (block["reconciles_legacy_multi_edge_count"]
              and block["reconciles_graph_size"])
        print(f"{tag:20s} sha={block['source_sha256'][:16]}... manifest="
              f"{block['matches_manifest_sha256']} multi={block['multi_edges_collapsed']} "
              f"recip={block['reciprocated_pairs_folded']} unparsed={block['rows_unparsed']} "
              f"legacy_reconciles={block['reconciles_legacy_multi_edge_count']} "
              f"size_reconciles={block['reconciles_graph_size']}")
        if not ok:
            print(f"  *** {tag}: file on disk does not reconcile with the cache - NOT written")
            continue
        out["networks"][tag] = block
    if a.dry_run:
        return
    with open(ROOT / SIDECAR, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {SIDECAR} ({len(out['networks'])} networks)")


if __name__ == "__main__":
    main()
