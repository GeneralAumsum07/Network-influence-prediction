"""
checkpoint.py - append-only resume log for the long analysis scripts.

WHY THIS EXISTS
---------------
analyse_edge5.py, analyse_edge_tier.py and analyse_robustness.py each fit for
one to three hours and wrote nothing until the end. The laptop has self-reset
under sustained all-core load several times (most recently 2026-10-10 19:34),
and every reset threw the whole step away. The probes were made resumable on
2026-10-07 by keying their CSV rows; these scripts print a report rather than
write rows, so they need a different mechanism. This is it.

THE IDEA
--------
Each script splits its work into deterministic UNITS (one fold-seed's tau, one
damage level's rows). A unit's result AND everything it printed are appended
to a JSON-lines file as one record the moment the unit finishes. On a rerun,
a unit already in the file is replayed - its printed text is written to stdout
again and its value is returned - instead of being refitted. Because every unit
is deterministic (fixed seeds, fixed folds), a resumed run prints the same
bytes an uninterrupted run would have printed. That is what makes the RESULTS
files trustworthy after a resume, and the tests check exactly that.

WHAT IT REFUSES
---------------
The first line of the file is a header naming the script's arguments and the
SHA-256 of every project source file the script has loaded and of every input
it declared. A rerun whose arguments, code or inputs differ refuses to start:
replaying units computed by different code would splice two versions of the
answer into one report. The refusal says to move the file aside; nothing here
ever deletes or rewrites a recorded record to make a resume pass.

DURABILITY
----------
Each record is flushed and fsync'd before the script moves on, because the
failure being guarded against is a hard reset, which loses whatever the OS was
still buffering. A reset mid-append leaves at most one torn final line (no
trailing newline); that line is dropped on load, so the unit is simply redone.
A malformed line anywhere ELSE is not a torn append and is refused.

With no path the checkpoint is inert: nothing is read, nothing is written, and
the caller's code path is otherwise identical to the original script.
(Added 2026-10-11.)
"""
import contextlib
import hashlib
import io
import json
import os
import sys
from pathlib import Path

FORMAT = 1


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def loaded_project_sources() -> dict[str, str]:
    """SHA-256 of every already-imported module that lives in the project.

    Computed from sys.modules rather than from a hand-written list, so a new
    import cannot be forgotten. "Project" means under the working directory,
    which is also what every caller's relative cache paths assume; the conda
    environment lives elsewhere and is pinned by environment.yml, not here.
    The running script is always included, by file name only - recording an
    absolute path would put a local path into a file under results/.
    """
    root = Path.cwd().resolve()
    out = {}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f or not f.endswith(".py"):
            continue
        p = Path(f).resolve()
        if root in p.parents:
            out[p.relative_to(root).as_posix()] = _sha256(p)
    main = Path(sys.modules["__main__"].__file__).resolve()
    out["__main__:" + main.name] = _sha256(main)
    return dict(sorted(out.items()))


class _Tee(io.TextIOBase):
    """Write-through to the real stdout while keeping a copy of the unit's text.

    Write-through rather than capture-then-print so a stage log still shows
    progress live; if the unit dies part-way the partial text is in the
    RESULTS file, but the stage redirects with '>' so a rerun truncates it.
    """

    def __init__(self, real):
        self.real, self.buf = real, io.StringIO()

    def write(self, s):
        self.buf.write(s)
        return self.real.write(s)

    def flush(self):
        self.real.flush()


class Checkpoint:
    def __init__(self, path, script: str, args: dict, inputs: dict[str, Path]):
        """`args` are the arguments that change the answer; `inputs` maps a
        stable label (never an absolute path) to each data file read."""
        self.path = Path(path) if path else None
        self.records: dict[str, dict] = {}
        self.replayed = 0
        if self.path is None:
            return
        header = {"kind": "header", "format": FORMAT, "script": script,
                  "args": args,
                  "inputs": {k: _sha256(v) for k, v in sorted(inputs.items())},
                  "sources": loaded_project_sources()}
        if self.path.exists():
            self._load(header)
        else:
            # Header written atomically, so a reset during creation leaves
            # either no file or a whole header - never half of one.
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(header) + "\n", encoding="utf-8")
            os.replace(tmp, self.path)
        print(f"[checkpoint] {self.path.name}: {len(self.records)} units "
              f"recorded", file=sys.stderr, flush=True)

    def _load(self, header: dict) -> None:
        raw = self.path.read_bytes()
        lines = raw.split(b"\n")
        tail = lines.pop()          # b"" when the file ends with a newline
        if not lines:
            raise SystemExit(f"{self.path}: no header line; move it aside "
                             "to start fresh")
        found = json.loads(lines[0])
        diff = [k for k in ("format", "script", "args", "inputs", "sources")
                if found.get(k) != header[k]]
        if diff:
            detail = []
            for k in ("inputs", "sources"):
                if k in diff:
                    a, b = found.get(k) or {}, header[k]
                    detail += [f"{k}:{n}" for n in sorted(set(a) | set(b))
                               if a.get(n) != b.get(n)]
            raise SystemExit(
                f"{self.path}: recorded with different {', '.join(diff)} "
                f"({'; '.join(detail) or 'see header'}). Replaying it would "
                "mix two versions of the answer. Move the file aside to start "
                "fresh; do not edit it.")
        for n, line in enumerate(lines[1:], start=2):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                raise SystemExit(f"{self.path}: line {n} is malformed and is "
                                 "not the final line, so it is not a torn "
                                 "append; refusing")
            if rec["key"] in self.records:
                raise SystemExit(f"{self.path}: duplicate unit {rec['key']!r} "
                                 f"at line {n}; two writers? refusing")
            self.records[rec["key"]] = rec
        if tail:
            # A torn final append from a hard reset. Drop it so the unit is
            # recomputed; truncate the file so the next append starts clean.
            # Done only after every check above has passed, so a refused
            # resume leaves the file exactly as it found it.
            with open(self.path, "r+b") as fh:
                fh.truncate(len(raw) - len(tail))
            print(f"[checkpoint] dropped a torn final line "
                  f"({len(tail)} bytes)", file=sys.stderr, flush=True)

    def _append(self, rec: dict) -> None:
        line = (json.dumps(rec) + "\n").encode("utf-8")
        with open(self.path, "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self.records[rec["key"]] = rec

    def unit(self, key: str, compute):
        """Return compute()'s value, replaying it if `key` is recorded.

        `compute` must be deterministic and its value JSON-serialisable with
        exact round-trip (Python floats, ints, str, lists, dicts; NaN is
        fine). Whatever it prints is recorded with it and replayed verbatim.
        """
        if self.path is None:
            return compute()
        rec = self.records.get(key)
        if rec is not None:
            sys.stdout.write(rec["stdout"])
            self.replayed += 1
            return rec["value"]
        tee = _Tee(sys.stdout)
        with contextlib.redirect_stdout(tee):
            value = compute()
        self._append({"key": key, "value": value, "stdout": tee.buf.getvalue()})
        return value

    def __contains__(self, key: str) -> bool:
        return key in self.records
