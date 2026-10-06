"""
fetch_data.py
=============
Download the real-network corpus into data/.

Run:  python fetch_data.py            # the pilot set
      python fetch_data.py --all      # pilot set + extras

Why this exists: the raw edge lists are not in the repo (they are other
people's data and some are large), but a clone with no data/ cannot
reproduce anything. This script makes the corpus one command away, and
records the source URL and a checksum for every file so the methods section
can state exactly which version of each network was used.

SNAP files are gzipped edge lists with '#' comment headers, which
preprocessing.load_edgelist already handles - no per-file parsing needed.
"""
import argparse
import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

# name -> (url, directed_in_source, note)
# 'directed_in_source' is recorded, not acted on: our protocol symmetrizes
# everything (decision 1). Keeping the flag means the writeup can state which
# networks were originally directed, which reviewers do ask about.
PILOT = {
    "ca-GrQc":         ("https://snap.stanford.edu/data/ca-GrQc.txt.gz",
                        False, "collaboration, GR-QC arXiv"),
    "ca-HepTh":        ("https://snap.stanford.edu/data/ca-HepTh.txt.gz",
                        False, "collaboration, HEP-TH arXiv"),
    "email-Eu-core":   ("https://snap.stanford.edu/data/email-Eu-core.txt.gz",
                        True,  "email, EU research institution"),
    "p2p-Gnutella08":  ("https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz",
                        True,  "peer-to-peer file sharing"),
    "facebook_combined": ("https://snap.stanford.edu/data/facebook_combined.txt.gz",
                        False, "ego-Facebook, combined ego networks"),
}

EXTRA = {
    "ca-HepPh":        ("https://snap.stanford.edu/data/ca-HepPh.txt.gz",
                        False, "collaboration, HEP-PH arXiv"),
    "ca-CondMat":      ("https://snap.stanford.edu/data/ca-CondMat.txt.gz",
                        False, "collaboration, cond-mat arXiv"),
    "p2p-Gnutella09":  ("https://snap.stanford.edu/data/p2p-Gnutella09.txt.gz",
                        True,  "peer-to-peer, second snapshot"),
    "as20000102":      ("https://snap.stanford.edu/data/as20000102.txt.gz",
                        False, "autonomous systems, internet topology"),
    "oregon1_010331":  ("https://snap.stanford.edu/data/oregon1_010331.txt.gz",
                        False, "AS peering, Oregon route view"),
}


# Pinned identities of the registered corpus (Task 6 audit finding P1-02,
# Claude Opus 5, 2026-09-11). Until this table existed, fetch() on an
# already-present file simply re-hashed whatever was on disk and wrote THAT
# into the manifest - so a corrupted or edited local copy was re-manifested
# rather than detected, and the manifest could never disagree with the disk.
# These are the values data/manifest.json has carried since the corpus was
# first fetched, and the values every cache_meta and Phase 6 provenance record
# is bound to (cache_provenance_audit_20260911.json). Verified, never
# re-recorded: a present file that hashes differently is an error.
# EXTRA networks are unpinned because no result depends on them.
EXPECTED_SHA256 = {
    "ca-GrQc":           "f8ce6e931e068b878044b783da99ef603f566c87bcbce7991cd53720879f1660",
    "ca-HepTh":          "8ce8a9aa75f0617d574a8109a6f8b189a9e38d214a6698ceaf25b2eecc873e90",
    "email-Eu-core":     "23e0ca0bce21a053025e78f7e9691ac9210ae806a0689bd5edff3c3bac572d4c",
    "p2p-Gnutella08":    "fecc14ef3c36ac13210bf9618cec773d7354ec9b033fe716a3af3fb815049499",
    "facebook_combined": "f41c026ed8af3cc3359f1ca5573d0605fb09ae0eefa34544b820fd8c6e2ef296",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pinned(name: str, path: Path, digest: str) -> None:
    """Raise if a pinned network's bytes are not the registered bytes."""
    expected = EXPECTED_SHA256.get(name)
    if expected is not None and digest != expected:
        raise ValueError(
            f"{path} hashes {digest[:16]}... but the registered corpus pins "
            f"{name} at {expected[:16]}.... The file is not the one every "
            f"cache and result was computed from; it was NOT re-manifested. "
            f"Delete it and re-fetch, or investigate the source.")


def fetch(name: str, url: str, out_dir: Path) -> dict:
    """Download, decompress, checksum. Skips anything already present."""
    final = out_dir / f"{name}.txt"
    if final.exists():
        digest = sha256(final)
        verify_pinned(name, final, digest)           # P1-02: verify, don't re-record
        pinned = "verified against pin" if name in EXPECTED_SHA256 else "unpinned"
        print(f"  [skip] {name} already present ({pinned})")
        return {"name": name, "url": url, "path": str(final),
                "sha256": digest, "bytes": final.stat().st_size}

    gz = out_dir / f"{name}.txt.gz"
    print(f"  [get ] {name} <- {url}")
    # SNAP rejects the default urllib agent on some mirrors.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(gz, "wb") as fh:
        shutil.copyfileobj(r, fh)

    with gzip.open(gz, "rb") as fin, open(final, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    gz.unlink()

    digest = sha256(final)
    # A fresh download that does not match the pin means the upstream file
    # changed; the run must stop rather than quietly manifest a new corpus.
    verify_pinned(name, final, digest)
    print(f"         -> {final.name}  {final.stat().st_size:,} bytes  sha256={digest[:16]}...")
    return {"name": name, "url": url, "path": str(final),
            "sha256": digest, "bytes": final.stat().st_size}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also fetch the extras")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    targets = dict(PILOT)
    if args.all:
        targets.update(EXTRA)

    manifest = []
    for name, (url, directed, note) in targets.items():
        try:
            rec = fetch(name, url, out)
            rec.update({"directed_in_source": directed, "note": note})
            manifest.append(rec)
        except Exception as e:
            # One dead mirror should not abort the whole corpus download.
            print(f"  [FAIL] {name}: {e}")

    mpath = out / "manifest.json"
    json.dump(manifest, open(mpath, "w"), indent=2)
    print(f"\nwrote {mpath} ({len(manifest)} networks)")
    print("\nNext:  python stage1_prepare.py data/ca-GrQc.txt 4000 1.5")


if __name__ == "__main__":
    main()
