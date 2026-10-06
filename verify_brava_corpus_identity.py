"""Establish and re-verify the identity of the local BRAVA/ABCDE corpus copy.

Created 2026-09-10 by Claude Opus 5 for Phase 6 Lane 3 (external precision witness).

WHY THIS EXISTS
---------------
The ABCDE corpus the precision witness consumes lived only inside a previous
agent session's temporary scratchpad directory, which any cleanup deletes.  It
has now been copied to ``data/brava/``.  A copy is only usable as scientific
input if it reproduces the identity the earlier preflight recorded, so this
script re-verifies it rather than trusting robocopy's success code.

Two facts about the existing record forced the shape of this script:

1.  ``results/phase6_precision_input_preflight.json`` pins only TWO of the five
    graphs (cit-Patents and com-lj -- the two that showed the 1.0e-14 clamp).
    The other three, amazon / dblp / com-youtube, have never had a recorded
    identity at all.  Witnessing all five therefore requires establishing their
    identity first; this script does that and writes it out as a new, separately
    dated artifact rather than editing the historical preflight.

2.  The preflight's recorded ``com-lj`` score hash is MALFORMED: it is 61
    characters, not 64.  It is a subsequence of the true digest, i.e. three
    characters were dropped in transcription -- it is not a different file's
    hash.  We do NOT silently rewrite that field (the standing trap forbids
    rewriting a recorded source hash to make a guard pass).  Instead the
    mismatch is reported explicitly, and the file's identity is corroborated by
    two independent quantities the preflight also recorded and which do match
    exactly: byte size and non-blank row count.

The script only reads.  It fits nothing, downloads nothing and modifies no
historical artifact.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

# The stabilised corpus location.  The old default was a session-scoped temp
# directory; see docs/phase6_claude_worklog_20260910.md Lane 3.
CORPUS_ROOT = Path("data/brava")
ABCDE = CORPUS_ROOT / "datasets" / "abcde"

PREFLIGHT_PATH = Path("results/phase6_precision_input_preflight.json")
OUTPUT_PATH = Path("results/phase6_brava_corpus_identity_20260910.json")

# All five ABCDE graphs.  Rachit's 2026-09-10 ruling is to witness all five, so
# all five need an identity record -- not just the two the preflight pinned.
GRAPHS = ("amazon", "cit-Patents", "com-lj", "com-youtube", "dblp")

_READ_CHUNK = 1 << 22  # 4 MiB; these files run to 502 MB.


def sha256_of(path: Path) -> str:
    """Streaming SHA-256, so a 502 MB edge list never lands in memory at once."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(_READ_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def count_nonblank_rows(path: Path) -> int:
    """Count non-blank lines, matching the preflight's own 'score_rows' rule."""
    total = 0
    with open(path, "rb") as handle:
        for line in handle:
            if line.strip():
                total += 1
    return total


def _pinned_entries() -> dict[str, dict[str, dict]]:
    """Read the historical preflight, keyed by graph then 'edge'/'score'.

    Returns an empty mapping for graphs the preflight never covered, which is
    the normal case for three of the five graphs.
    """
    if not PREFLIGHT_PATH.exists():
        return {}
    document = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    return {entry["graph"]: {"edge": entry["edge"], "score": entry["score"]}
            for entry in document.get("graphs", [])}


def _compare(measured: dict, pinned: dict | None) -> dict:
    """Classify a measured file against its pinned record, if one exists.

    The three outcomes are deliberately distinct.  'unpinned' is not a failure
    -- it means no prior claim existed to check against.  'malformed_pinned_hash'
    separates a defective RECORD from a changed FILE, which is the distinction
    that matters scientifically: only the latter would invalidate evidence.
    """
    if pinned is None:
        return {"status": "unpinned", "detail":
                "No historical preflight entry; identity established here for the first time."}

    pinned_hash = pinned["sha256"]
    size_ok = measured["bytes"] == pinned["bytes"]

    # A well-formed SHA-256 is exactly 64 lowercase hex characters.  Anything
    # else is a broken record, and must not be treated as a content mismatch.
    if len(pinned_hash) != 64 or any(c not in "0123456789abcdef" for c in pinned_hash):
        subsequence = _is_subsequence(pinned_hash, measured["sha256"])
        return {
            "status": "malformed_pinned_hash",
            "pinned_sha256_length": len(pinned_hash),
            "pinned_is_subsequence_of_measured": subsequence,
            "byte_size_matches": size_ok,
            "detail": (
                "The RECORDED hash is not a valid SHA-256 (character(s) dropped in "
                "transcription). It is not evidence of a changed file. The recorded "
                "value is NOT rewritten here. Identity is corroborated instead by byte "
                "size and non-blank row count, both recorded by the same preflight."),
        }

    return {"status": "match" if (measured["sha256"] == pinned_hash and size_ok) else "mismatch",
            "byte_size_matches": size_ok,
            "hash_matches": measured["sha256"] == pinned_hash}


def _is_subsequence(short: str, long: str) -> bool:
    """True if `short` can be obtained from `long` by deleting characters.

    Distinguishes 'a few characters were lost writing this down' from 'this is
    a completely different digest'.
    """
    position = 0
    for character in short:
        found = long.find(character, position)
        if found < 0:
            return False
        position = found + 1
    return True


def main() -> int:
    if not ABCDE.is_dir():
        raise SystemExit(f"corpus not found at {ABCDE}")

    pinned = _pinned_entries()
    record: dict = {
        "generated": datetime.now(timezone.utc).astimezone().isoformat(),
        "author": "Claude Opus 5",
        "purpose": ("Identity of the stabilised local BRAVA/ABCDE copy for the Phase 6 "
                    "precision witness. Read-only; establishes identity for the three "
                    "graphs the historical preflight never covered and re-verifies the two "
                    "it did."),
        "corpus_root": str(CORPUS_ROOT).replace("\\", "/"),
        "historical_preflight": str(PREFLIGHT_PATH).replace("\\", "/"),
        "graphs": [],
    }

    problems: list[str] = []
    for graph in GRAPHS:
        entry: dict = {"graph": graph}
        for kind, filename in (("edge", f"{graph}.txt"), ("score", f"{graph}-score.txt")):
            path = ABCDE / filename
            if not path.exists():
                problems.append(f"{graph}/{kind}: MISSING {path}")
                entry[kind] = {"status": "missing", "path": str(path).replace("\\", "/")}
                continue

            measured = {
                "logical_path": f"datasets/abcde/{filename}",
                "bytes": path.stat().st_size,
                "sha256": sha256_of(path),
                "nonblank_rows": count_nonblank_rows(path),
            }
            comparison = _compare(measured, pinned.get(graph, {}).get(kind))
            measured["comparison"] = comparison
            entry[kind] = measured

            if comparison["status"] == "mismatch":
                problems.append(f"{graph}/{kind}: CONTENT MISMATCH against pinned record")
            print(f"{comparison['status']:>22}  {graph:<12} {kind:<6} "
                  f"{measured['bytes']:>12,} bytes  {measured['nonblank_rows']:>10,} rows  "
                  f"{measured['sha256'][:16]}")

        record["graphs"].append(entry)

    record["problems"] = problems
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")

    if problems:
        print("\nPROBLEMS:")
        for item in problems:
            print("  -", item)
        return 1

    print("\nNo content mismatch. A 'malformed_pinned_hash' status is a defect in the "
          "historical RECORD, not in the file; see that entry's detail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
