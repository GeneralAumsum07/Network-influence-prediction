"""Bounded local witnesses for C3's external zero-printing precision question.

This module deliberately reimplements only C3's sorted-label, simple
undirected topology semantics.  It never computes exact betweenness: each
selected node receives a local lower-bound certificate from nonadjacent
neighbour pairs.  Raw ABCDE inputs are streamed into bounded external-sort
runs because the existing C3 loader intentionally materialises arrays that are
too large for this workstation's available memory envelope.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import heapq
import json
import os
import shutil
import struct
import tempfile
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

import numpy as np


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "results" / "phase6_precision_witness"
PREFLIGHT_PATH = ROOT / "results" / "phase6_precision_input_preflight.json"
VERSION_TAG = b"phase6-c3-bounded-csr-v1\0"
MIB = 1024 * 1024
SORT_PAYLOAD_CAP = 192 * MIB
TEXT_BUFFER_BYTES = 8 * MIB
PARSER_MAPPING_CAP = 40 * MIB
MERGE_BUFFER_CAP = 8 * MIB
RESERVE_BYTES = 512 * MIB


class PrecisionWitnessError(ValueError):
    """Raised for an identity, topology, resource, or witness invariant failure."""


@dataclass
class GraphSpec:
    """Pinned public-input identity and C3 whole-graph topology expectations."""

    graph: str
    edge_sha256: str
    score_sha256: str
    nodes: int
    arcs: int
    selected_targets: int
    raw_rows: int
    edge_bytes: int
    score_rows: int
    score_bytes: int


SPECS = {
    "cit-Patents": GraphSpec(
        "cit-Patents", "f8797f004315acf99faaee62b08ce093109968ba82bb52d55c7bc8b92e4918b9",
        "48f352137529955aed7faf1fd06be1ded7fe77708ca0989683ef984733ab71a6",
        3_764_117, 33_023_480, 662, 16_511_741, 256_154_375, 3_764_117, 71_518_223,
    ),
    "com-lj": GraphSpec(
        "com-lj", "835d5175a7309fedd782fc505407a5d140587540b27d4eab64df9f3f3eba2add",
        # CORRECTED 2026-09-10 by Claude Opus 5. The value recorded here (and the
        # identical one in results/phase6_precision_input_preflight.json) was 61
        # characters, not 64: three characters, "74c", had been dropped after
        # "...f3ef34c" in transcription. Because BOTH records carried the same
        # truncated string they agreed with each other, so validate_preflight_spec
        # and the verifier passed -- but _score_rows (below) hashes the real file,
        # so a com-lj run would have failed AFTER building its whole topology.
        #
        # This is a correction to a defective RECORD, not a file that changed. The
        # score file's content is unchanged, established by two independent
        # quantities the same preflight recorded and which both still match
        # exactly: 75,961,278 bytes and 3,997,962 non-blank rows. The truncated
        # string is also a subsequence of the true digest, which is what a dropped
        # -character transcription looks like and what a different file does not.
        # Evidence: results/phase6_brava_corpus_identity_20260910.json.
        "78a77750ac83057a6c62e5cef3ef34c74c50a8c6fc7603d0b460eb91a0d480d4",
        3_997_962, 69_362_378, 1_086, 34_681_189, 502_171_107, 3_997_962, 75_961_278,
    ),
    # ------------------------------------------------------------------------
    # The three UNCLAMPED reference graphs, added 2026-09-11 by Claude Opus 5 on
    # Rachit's instruction to run the witness on all five ABCDE graphs rather
    # than only the two whose ground truth is clamped at 1.0e-14.
    #
    # HOW THESE NUMBERS DIFFER FROM THE TWO ABOVE, and it matters:
    #
    # cit-Patents and com-lj were pinned from the 2026-09-09 read-only preflight
    # and the C3 analysis, i.e. from records that predate the witness. Nothing of
    # the kind exists for these three, so every field here was MEASURED in order
    # to be pinned (scratchpad discovery pass, 2026-09-11; provenance in
    # results/phase6_precision_witness_discovery_20260911.json).
    #
    # A pin derived that way CANNOT falsify the run that produced it. It buys
    # reproducibility and detection of later corpus drift, and nothing more. It is
    # labelled here rather than left implicit precisely because the [3,18] degree
    # range was an inherited claim presented as a prediction, and that cost a run.
    #
    # `selected_targets=0` on all three is not a placeholder. It is the measured
    # outcome and the control result: no printed zero on any of these graphs has a
    # nonadjacent neighbour pair, so none of them is structurally positive. Two
    # independent per-graph consistency checks hold on all three -- score rows
    # equal node count, and raw rows minus self-loop rows equal canonical edges --
    # so the topology is not silently wrong in a way that would suppress targets.
    "amazon": GraphSpec(
        "amazon", "43f7a104f3ec6c2c2d7bcd947a71fe5ceb2f16db3060200e907e9f9dc0dca00f",
        "3a89a0714033591105d0070b9228cfe0763e8a0b2ca8487ca54e800a27c040c4",
        2_146_057, 11_486_264, 0, 5_743_146, 76_719_716, 2_146_057, 40_775_083,
    ),
    "dblp": GraphSpec(
        "dblp", "5641215f2373210340309553a26c2517a8379f81b8a93490bab80b05eeaff52b",
        "4236b420a8ef0303120735eca6dfe787a8a4526e94a8d285e24af23789cb7c47",
        4_000_148, 17_298_002, 0, 8_649_011, 124_933_350, 4_000_148, 76_002_812,
    ),
    "com-youtube": GraphSpec(
        "com-youtube", "b9dad0cdd621f9b0c8f9a333a9783776b6af1624ca0f908158d6af3e0a5acaec",
        "b9f3aa834eb638ca7db74b61f5515298eb41cfcf9efdf0ce95f81e3dd8d675b3",
        1_134_890, 5_975_248, 0, 2_987_624, 38_210_288, 1_134_890, 21_562_910,
    ),
}


def assert_pinned_hashes_wellformed() -> None:
    """Fail loudly if any pinned digest is not exactly 64 lowercase hex characters.

    Added 2026-09-10 by Claude Opus 5 after a 61-character com-lj score hash
    survived every existing check. The gap it closes: the identity guard compares
    the spec against the preflight, so a defect transcribed into BOTH records is
    invisible to it. A well-formedness check needs no second copy to compare
    against, which is exactly why it catches this class of error.
    """
    for name, spec in sorted(SPECS.items()):
        for field, digest in (("edge_sha256", spec.edge_sha256),
                              ("score_sha256", spec.score_sha256)):
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise PrecisionWitnessError(
                    f"pinned {field} for {name} is not a well-formed SHA-256 "
                    f"({len(digest)} chars): {digest!r}")


@dataclass
class Topology:
    """Memmapped C3-compatible topology plus the temporary files that own it."""

    spec: GraphSpec
    temp_dir: Path
    original_ids_path: Path
    indptr_path: Path
    indices_path: Path
    data_path: Path
    original_ids: np.memmap
    indptr: np.memmap
    indices: np.memmap
    data: np.memmap
    raw_rows: int
    edge_bytes: int
    canonical_edges: int
    topology_sha256: str
    resource: dict[str, int]

    def close(self) -> None:
        """Flush mappings before a caller removes a successful run's scratch tree."""
        for mapped in (self.original_ids, self.indptr, self.indices, self.data):
            _close_memmap(mapped)


def _close_memmap(mapped: np.memmap) -> None:
    mapped.flush()
    backing = getattr(mapped, "_mmap", None)
    if backing is not None:
        backing.close()


def _paths(spec: GraphSpec, brava: Path) -> tuple[Path, Path]:
    root = Path(brava) / "datasets" / "abcde"
    return root / f"{spec.graph}.txt", root / f"{spec.graph}-score.txt"


def _parse_edge_line(raw: bytes, path: Path, line_number: int) -> tuple[int, int] | None:
    """Accept precisely the documented ABCDE two-integer data-line grammar."""
    stripped = raw.strip()
    if not stripped or stripped.startswith((b"#", b"%")):
        return None
    fields = stripped.split()
    if len(fields) != 2 or any(not _is_signed_decimal(field) for field in fields):
        raise PrecisionWitnessError(f"malformed edge line {line_number} in {path.name}")
    return int(fields[0]), int(fields[1])


def _is_signed_decimal(value: bytes) -> bool:
    if value.startswith((b"+", b"-")):
        value = value[1:]
    return bool(value) and value.isdigit()


def inspect_edge_file(spec: GraphSpec, edge_path: Path) -> tuple[int, int]:
    """Hash and parse before creating derived files, so bad inputs publish nothing."""
    if not edge_path.is_file():
        raise PrecisionWitnessError(f"edge input missing: {edge_path}")
    digest = hashlib.sha256()
    rows = 0
    with edge_path.open("rb", buffering=TEXT_BUFFER_BYTES) as stream:
        for line_number, raw in enumerate(stream, start=1):
            digest.update(raw)
            if _parse_edge_line(raw, edge_path, line_number) is not None:
                rows += 1
    actual_hash = digest.hexdigest()
    size = edge_path.stat().st_size
    if actual_hash != spec.edge_sha256:
        raise PrecisionWitnessError(f"edge SHA-256 mismatch for {spec.graph}")
    if size != spec.edge_bytes:
        raise PrecisionWitnessError(f"edge byte count mismatch for {spec.graph}: {size}")
    if rows != spec.raw_rows:
        raise PrecisionWitnessError(f"raw edge-row count mismatch for {spec.graph}: {rows}")
    return rows, size


def _resource_contract(spec: GraphSpec, raw_rows: int) -> dict[str, int]:
    """Compute the documented derived-file peak; raw BRAVA bytes are pre-existing."""
    n, arcs = spec.nodes, spec.arcs
    edges = arcs // 2
    if arcs % 2:
        raise PrecisionWitnessError("pinned CSR arc count must be even")
    label = 16 * raw_rows + 8 * n
    canonical = 8 * raw_rows + 8 * edges + 8 * n
    arc = 8 * arcs + 8 * edges + 4 * arcs + arcs + 4 * (n + 1) + 8 * n
    peak = max(label, canonical, arc)
    return {
        "label_phase": label, "canonical_phase": canonical,
        "direct_arc_merge_phase": arc, "peak": peak,
        "reserve": RESERVE_BYTES, "required_free": peak + RESERVE_BYTES,
    }


def _require_scratch_capacity(output_root: Path, resource: dict[str, int]) -> None:
    free = shutil.disk_usage(output_root).free
    if free < resource["required_free"]:
        raise PrecisionWitnessError(
            f"scratch volume has {free} free bytes; requires {resource['required_free']}"
        )


def _new_temp_dir(output_root: Path, graph: str) -> Path:
    # Interrupted work is retained for inspection.  A fresh UUID prevents a
    # resume from trusting potentially half-written sort runs.
    return Path(tempfile.mkdtemp(prefix=f".{graph}-tmp-", dir=output_root))


def _write_run(values: np.ndarray, count: int, path: Path) -> None:
    values[:count].sort()
    with path.open("wb") as stream:
        values[:count].tofile(stream)


def _label_runs(edge_path: Path, temp_dir: Path, payload_bytes: int) -> list[Path]:
    capacity = max(2, payload_bytes // np.dtype("<i8").itemsize)
    values = np.empty(capacity, dtype="<i8")
    count, sequence = 0, 0
    runs: list[Path] = []
    with edge_path.open("rb", buffering=TEXT_BUFFER_BYTES) as stream:
        for line_number, raw in enumerate(stream, start=1):
            pair = _parse_edge_line(raw, edge_path, line_number)
            if pair is None:
                continue
            if count + 2 > capacity:
                run = temp_dir / f"labels-{sequence:06d}.i64"
                _write_run(values, count, run)
                runs.append(run)
                count, sequence = 0, sequence + 1
            values[count], values[count + 1] = pair
            count += 2
    if count:
        run = temp_dir / f"labels-{sequence:06d}.i64"
        _write_run(values, count, run)
        runs.append(run)
    if not runs:
        raise PrecisionWitnessError("edge input has no parsed rows")
    return runs


def _merge_unique_runs(runs: list[Path], dtype: str, output_path: Path,
                       *, buffer_bytes: int) -> int:
    """K-way merge directly to its final file; no merged intermediary is allowed."""
    if not runs:
        raise PrecisionWitnessError("cannot merge an empty run set")
    maps = [np.memmap(path, mode="r", dtype=dtype) for path in runs]
    positions = [0] * len(maps)
    heap = [(int(values[0]), index) for index, values in enumerate(maps) if len(values)]
    heapq.heapify(heap)
    itemsize = np.dtype(dtype).itemsize
    out = np.empty(max(1, buffer_bytes // itemsize), dtype=dtype)
    out_count, total, prior = 0, 0, None
    try:
        with output_path.open("wb") as stream:
            while heap:
                value, source = heapq.heappop(heap)
                if prior is None or value != prior:
                    out[out_count] = value
                    out_count += 1
                    total += 1
                    prior = value
                    if out_count == len(out):
                        out.tofile(stream)
                        out_count = 0
                positions[source] += 1
                if positions[source] < len(maps[source]):
                    heapq.heappush(heap, (int(maps[source][positions[source]]), source))
            if out_count:
                out[:out_count].tofile(stream)
    finally:
        for mapped in maps:
            _close_memmap(mapped)
    return total


def _delete_runs(runs: list[Path]) -> None:
    for path in runs:
        path.unlink()


def _canonical_runs(edge_path: Path, original_ids: np.memmap, n: int,
                    temp_dir: Path, payload_bytes: int) -> list[Path]:
    # Endpoint arrays plus one searchsorted result and one key buffer are kept
    # below the 40 MiB parser/mapping allocation cap.
    capacity = max(1, min(payload_bytes // 8, PARSER_MAPPING_CAP // 32))
    raw_u = np.empty(capacity, dtype="<i8")
    raw_v = np.empty(capacity, dtype="<i8")
    keys = np.empty(capacity, dtype="<u8")
    count, sequence = 0, 0
    runs: list[Path] = []

    def map_and_canonicalise(length: int) -> int:
        """Relabel in place without vector temporaries that would breach the cap."""
        positions = np.searchsorted(original_ids, raw_u[:length])
        if np.any(positions >= n) or not np.array_equal(original_ids[positions], raw_u[:length]):
            raise PrecisionWitnessError("sorted original-id map rejected a raw endpoint")
        raw_u[:length] = positions
        positions = np.searchsorted(original_ids, raw_v[:length])
        if np.any(positions >= n) or not np.array_equal(original_ids[positions], raw_v[:length]):
            raise PrecisionWitnessError("sorted original-id map rejected a raw endpoint")
        raw_v[:length] = positions
        # Scalar conversion is intentional.  Vector masks/minimum/advanced
        # indexing create several full chunk temporaries, defeating the fixed
        # numeric allocation bound for the real graphs.
        kept = 0
        for index in range(length):
            u, v = int(raw_u[index]), int(raw_v[index])
            if u != v:
                if u > v:
                    u, v = v, u
                keys[kept] = np.uint64(u * n + v)
                kept += 1
        return kept

    def flush() -> None:
        nonlocal count, sequence
        if not count:
            return
        run = temp_dir / f"canonical-{sequence:06d}.u64"
        _write_run(keys, count, run)
        runs.append(run)
        count, sequence = 0, sequence + 1

    with edge_path.open("rb", buffering=TEXT_BUFFER_BYTES) as stream:
        for line_number, raw in enumerate(stream, start=1):
            pair = _parse_edge_line(raw, edge_path, line_number)
            if pair is None:
                continue
            raw_u[count], raw_v[count] = pair
            count += 1
            if count == capacity:
                count = map_and_canonicalise(count)
                flush()
    if count:
        count = map_and_canonicalise(count)
        flush()
    if not runs:
        raise PrecisionWitnessError("all parsed raw edges were loops")
    return runs


def _arc_runs(canonical_path: Path, n: int, temp_dir: Path,
              payload_bytes: int) -> list[Path]:
    canonical = np.memmap(canonical_path, mode="r", dtype="<u8")
    capacity = max(2, payload_bytes // np.dtype("<u8").itemsize)
    values = np.empty(capacity, dtype="<u8")
    count, sequence = 0, 0
    runs: list[Path] = []
    try:
        for encoded in canonical:
            u, v = divmod(int(encoded), n)
            if count + 2 > capacity:
                run = temp_dir / f"arcs-{sequence:06d}.u64"
                _write_run(values, count, run)
                runs.append(run)
                count, sequence = 0, sequence + 1
            values[count] = np.uint64(u * n + v)
            values[count + 1] = np.uint64(v * n + u)
            count += 2
        if count:
            run = temp_dir / f"arcs-{sequence:06d}.u64"
            _write_run(values, count, run)
            runs.append(run)
    finally:
        _close_memmap(canonical)
    return runs


def _merge_arcs_to_csr(runs: list[Path], n: int, expected_arcs: int,
                       indptr_path: Path, indices_path: Path, data_path: Path,
                       *, buffer_bytes: int) -> tuple[np.memmap, np.memmap, np.memmap]:
    """Decode merged arc keys straight into CSR arrays, never an arc merge file."""
    if not runs:
        raise PrecisionWitnessError("canonical graph produced no arcs")
    maps = [np.memmap(path, mode="r", dtype="<u8") for path in runs]
    positions = [0] * len(maps)
    heap = [(int(values[0]), index) for index, values in enumerate(maps) if len(values)]
    heapq.heapify(heap)
    indptr = np.memmap(indptr_path, mode="w+", dtype="<u4", shape=n + 1)
    indices = np.memmap(indices_path, mode="w+", dtype="<u4", shape=expected_arcs)
    data = np.memmap(data_path, mode="w+", dtype="u1", shape=expected_arcs)
    row, previous_column, previous_key, written = 0, -1, None, 0
    indptr[0] = 0
    try:
        while heap:
            key, source = heapq.heappop(heap)
            if previous_key is not None and key == previous_key:
                raise PrecisionWitnessError("duplicate arc survived canonical edge merge")
            source_row, column = divmod(key, n)
            if source_row < row:
                raise PrecisionWitnessError("arc merge order is not row-major")
            while row < source_row:
                indptr[row + 1] = written
                row += 1
                previous_column = -1
            if column <= previous_column:
                raise PrecisionWitnessError("CSR row is not strictly ascending")
            if written >= expected_arcs:
                raise PrecisionWitnessError("CSR arc count exceeds pinned topology")
            indices[written] = column
            data[written] = 1
            written += 1
            previous_column, previous_key = column, key
            positions[source] += 1
            if positions[source] < len(maps[source]):
                heapq.heappush(heap, (int(maps[source][positions[source]]), source))
        while row < n:
            indptr[row + 1] = written
            row += 1
    finally:
        for mapped in maps:
            _close_memmap(mapped)
    if written != expected_arcs:
        raise PrecisionWitnessError(f"CSR arc count {written}, expected {expected_arcs}")
    indptr.flush()
    indices.flush()
    data.flush()
    return indptr, indices, data


def _topology_digest(n: int, arcs: int, indptr: np.memmap, indices: np.memmap) -> str:
    digest = hashlib.sha256()
    digest.update(VERSION_TAG)
    digest.update(struct.pack("<QQ", n, arcs))
    # Hash in bounded chunks so the fingerprint does not materialise a CSR copy.
    for mapped in (indptr, indices):
        step = max(1, MERGE_BUFFER_CAP // mapped.dtype.itemsize)
        for start in range(0, len(mapped), step):
            digest.update(mapped[start:start + step].tobytes())
    return digest.hexdigest()


def build_topology(spec: GraphSpec, brava: Path, output_root: Path = OUTPUT_ROOT,
                   *, payload_bytes: int = SORT_PAYLOAD_CAP) -> Topology:
    """Construct the whole sorted-label C3 topology within the documented envelope."""
    if payload_bytes < 8 or payload_bytes > SORT_PAYLOAD_CAP:
        raise PrecisionWitnessError(f"payload_bytes must be in [8, {SORT_PAYLOAD_CAP}]")
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    edge_path, _score_path = _paths(spec, Path(brava))
    raw_rows, edge_bytes = inspect_edge_file(spec, edge_path)
    resource = _resource_contract(spec, raw_rows)
    _require_scratch_capacity(output_root, resource)
    temp_dir = _new_temp_dir(output_root, spec.graph)
    try:
        label_runs = _label_runs(edge_path, temp_dir, payload_bytes)
        original_ids_path = temp_dir / "original_ids.i64"
        n = _merge_unique_runs(label_runs, "<i8", original_ids_path,
                               buffer_bytes=min(MERGE_BUFFER_CAP, payload_bytes))
        _delete_runs(label_runs)
        if n != spec.nodes:
            raise PrecisionWitnessError(f"sorted original-id count {n}, expected {spec.nodes}")
        original_ids = np.memmap(original_ids_path, mode="r", dtype="<i8", shape=n)
        if n > 1 and np.any(original_ids[1:] <= original_ids[:-1]):
            raise PrecisionWitnessError("original IDs are not strictly increasing")
        canonical_runs = _canonical_runs(edge_path, original_ids, n, temp_dir, payload_bytes)
        canonical_path = temp_dir / "canonical_edges.u64"
        edges = _merge_unique_runs(canonical_runs, "<u8", canonical_path,
                                   buffer_bytes=min(MERGE_BUFFER_CAP, payload_bytes))
        _delete_runs(canonical_runs)
        if edges * 2 != spec.arcs:
            raise PrecisionWitnessError(f"canonical edge count {edges}, expected {spec.arcs // 2}")
        arc_runs = _arc_runs(canonical_path, n, temp_dir, payload_bytes)
        indptr_path, indices_path, data_path = (temp_dir / "indptr.u32", temp_dir / "indices.u32",
                                                 temp_dir / "data.u8")
        indptr, indices, data = _merge_arcs_to_csr(
            arc_runs, n, spec.arcs, indptr_path, indices_path, data_path,
            buffer_bytes=min(MERGE_BUFFER_CAP, payload_bytes),
        )
        _delete_runs(arc_runs)
        # Canonical edges are retained only until arc merge succeeds; the CSR is
        # now the sole topology needed by selector and witness code.
        canonical_path.unlink()
        digest = _topology_digest(n, spec.arcs, indptr, indices)
        return Topology(spec, temp_dir, original_ids_path, indptr_path, indices_path,
                        data_path, original_ids, indptr, indices, data, raw_rows,
                        edge_bytes, edges, digest, resource)
    except Exception:
        # Preserve the incomplete temp directory exactly as the resource design
        # requires; it contains no published result and is useful for inspection.
        raise


def _row(topology: Topology, node: int) -> np.ndarray:
    return topology.indices[int(topology.indptr[node]):int(topology.indptr[node + 1])]


def _contains(sorted_row: np.ndarray, target: int) -> bool:
    index = int(np.searchsorted(sorted_row, target))
    return index < len(sorted_row) and int(sorted_row[index]) == target


def _common_neighbours(first: np.ndarray, second: np.ndarray) -> int:
    """Count exactly with two cursors instead of allocating an intersection array."""
    left = right = count = 0
    while left < len(first) and right < len(second):
        a, b = int(first[left]), int(second[right])
        if a == b:
            count += 1
            left += 1
            right += 1
        elif a < b:
            left += 1
        else:
            right += 1
    return count


def _first_nonadjacent_pair(topology: Topology, node: int) -> tuple[int, int] | None:
    neighbours = _row(topology, node)
    for left in range(len(neighbours) - 1):
        a = int(neighbours[left])
        a_row = _row(topology, a)
        for right in range(left + 1, len(neighbours)):
            b = int(neighbours[right])
            if not _contains(a_row, b):
                return a, b
    return None


def threshold_decision(n: int, common_neighbour_count: int) -> dict[str, int | bool]:
    """Use strict integer cross-products for the two conditional normalised claims."""
    if n < 3 or common_neighbour_count < 1:
        raise PrecisionWitnessError("threshold requires n >= 3 and a positive common-neighbour count")
    denominator = (n - 1) * (n - 2) * common_neighbour_count
    five_left, five_right = 2 * 10**15, 5 * denominator
    one_left, one_right = 2 * 10**14, denominator
    return {
        "numerator": 2, "denominator": denominator,
        "gt_5e15": five_left > five_right,
        "gt_1e14": one_left > one_right,
        "gt_5e15_left_cross_product": five_left,
        "gt_5e15_right_cross_product": five_right,
        "gt_1e14_left_cross_product": one_left,
        "gt_1e14_right_cross_product": one_right,
    }


def _score_rows(score_path: Path, spec: GraphSpec) -> Iterator[tuple[int, str, Decimal]]:
    if not score_path.is_file():
        raise PrecisionWitnessError(f"score input missing: {score_path}")
    digest = hashlib.sha256()
    row = 0
    with score_path.open("rb", buffering=TEXT_BUFFER_BYTES) as stream:
        for line_number, raw in enumerate(stream, start=1):
            digest.update(raw)
            try:
                literal = raw.decode("utf-8").strip()
            except UnicodeDecodeError as exc:
                raise PrecisionWitnessError(f"score text is not UTF-8 at line {line_number}") from exc
            if not literal:
                continue
            try:
                value = Decimal(literal)
            except InvalidOperation as exc:
                raise PrecisionWitnessError(f"invalid Decimal score at line {line_number}") from exc
            if not value.is_finite():
                raise PrecisionWitnessError(f"non-finite Decimal score at line {line_number}")
            yield row, literal, value
            row += 1
    if digest.hexdigest() != spec.score_sha256:
        raise PrecisionWitnessError(f"score SHA-256 mismatch for {spec.graph}")
    if score_path.stat().st_size != spec.score_bytes:
        raise PrecisionWitnessError(f"score byte count mismatch for {spec.graph}")
    if row != spec.score_rows:
        raise PrecisionWitnessError(f"score-row count {row}, expected {spec.score_rows}")


TARGET_COLUMNS = (
    "graph", "score_row", "compact_id", "original_node_id", "printed_score_text", "degree",
    "edge_sha256", "score_sha256",
)
WITNESS_COLUMNS = (
    "graph", "score_row", "compact_id", "original_node_id", "degree",
    "a_compact_id", "b_compact_id", "a_original_node_id", "b_original_node_id",
    "common_neighbor_count", "rational_numerator", "rational_denominator",
    "gt_5e15", "gt_1e14", "gt_5e15_left_cross_product", "gt_5e15_right_cross_product",
    "gt_1e14_left_cross_product", "gt_1e14_right_cross_product", "usable_pair_count",
    "gt_5e15_qualifying_pair_count", "gt_1e14_qualifying_pair_count",
    "edge_sha256", "score_sha256",
)


# Degree guards on a selected target.
#
# Corrected 2026-09-10 by Claude Opus 5. The lower bound was 3, inherited from
# the design's sentence "affected nodes were previously reported as degree
# 3--18". Nothing in this repository records that measurement, and because the
# witness had never completed a run, the range had never been tested. Its first
# real execution rejected the majority of its own targets on BOTH pinned graphs
# with "selected target degree 2 outside [3,18]".
#
# Two is the structural MINIMUM, not an anomaly. The selector admits a row when
# its printed score is zero and some pair of its neighbours is nonadjacent. A
# degree-two node with two nonadjacent neighbours satisfies that, and is
# positive for the same reason every other selected node is: a-v-b is a
# length-two shortest path, so BC(v) >= 1/c > 0. A floor of 3 is therefore not
# a data guard -- it is unsatisfiable in principle for a legitimate class of
# targets, and it discards them.
#
# The graph was never in doubt. The same run reproduced two other pinned
# quantities on cit-Patents exactly -- 709,724 printed zeros and 662 selected
# rows -- so only the degree prediction was wrong. Measured range there is
# [2,6]: 424 of the 662 targets have degree two.
#
# The upper bound of 18 was ALSO wrong, and is replaced rather than raised.
#
# cit-Patents passed with a measured maximum degree of 6, so 18 looked like a
# safe envelope. com-lj then failed with "degree 34 outside [2,18]": its
# measured range is [2,111], and 412 of its 1,086 targets exceed 18. So the
# inherited range is wrong at BOTH ends, on BOTH graphs -- while both pinned
# COUNTS (662 and 1,086) and both printed-zero counts reproduced exactly.
#
# 18 was never a resource guard in its own right. It was a second consequence
# of the same wrong degree claim, used to state a pair budget of
# 1,748 * C(18,2) = 267,444. The real total is the sum of C(degree,2) over
# selected targets: 1,459 for cit-Patents and 293,013 for com-lj, i.e.
# 294,472 -- about 10% above the quoted figure. The design states these
# intersection scans are constant-extra-memory streaming work, so this count
# bounds TIME, not memory, and a 10% overrun of a few hundred thousand
# two-pointer intersections is not an envelope breach.
#
# Capping per-node degree is therefore the wrong instrument: it rejects lawful
# targets while only indirectly limiting the quantity at issue. This guards the
# actual quantity -- the cumulative pair scan -- and leaves per-node degree
# bounded only by the graph. The cap is set far above the measured 294,472 so
# it binds on a runaway, not on real data, and it is a declared budget rather
# than an inherited measurement.
MIN_TARGET_DEGREE = 2
MAX_TOTAL_PAIR_SCAN = 5_000_000


def _select_targets(topology: Topology, score_path: Path,
                    staging_path: Path) -> tuple[int, int, int, int]:
    """Stream Decimal scores and inspect only zero rows; no global zero-set mask exists.

    Returns `(selected, min_degree, max_degree, pair_scan)`. The observed range is
    reported rather than assumed, so the run records a MEASURED fact where the
    design carried an inherited prediction.
    """
    selected, max_degree = 0, 0
    min_degree: int | None = None
    pair_scan = 0
    with staging_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=TARGET_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for score_row, literal, score in _score_rows(score_path, topology.spec):
            if score_row >= topology.spec.nodes:
                raise PrecisionWitnessError("score row exceeds compact-node range")
            if not score.is_zero():
                continue
            pair = _first_nonadjacent_pair(topology, score_row)
            if pair is None:
                continue
            degree = int(topology.indptr[score_row + 1] - topology.indptr[score_row])
            if degree < MIN_TARGET_DEGREE:
                raise PrecisionWitnessError(
                    f"selected target degree {degree} below the structural "
                    f"minimum {MIN_TARGET_DEGREE}"
                )
            # Guard the cumulative scan, which is the quantity the design's
            # budget was actually about.
            pair_scan += degree * (degree - 1) // 2
            if pair_scan > MAX_TOTAL_PAIR_SCAN:
                raise PrecisionWitnessError(
                    f"cumulative witness pair scan {pair_scan} exceeds the "
                    f"declared budget {MAX_TOTAL_PAIR_SCAN}"
                )
            selected += 1
            max_degree = max(max_degree, degree)
            min_degree = degree if min_degree is None else min(min_degree, degree)
            writer.writerow({
                "graph": topology.spec.graph, "score_row": score_row, "compact_id": score_row,
                "original_node_id": int(topology.original_ids[score_row]),
                "printed_score_text": literal, "degree": degree,
                "edge_sha256": topology.spec.edge_sha256,
                "score_sha256": topology.spec.score_sha256,
            })
    if selected != topology.spec.selected_targets:
        raise PrecisionWitnessError(
            f"selected target count {selected}, expected {topology.spec.selected_targets}"
        )
    # Corrected 2026-09-11 by Claude Opus 5. The comment that stood here said
    # "`selected == 0` cannot reach here: the count check above would have fired
    # first, since no pinned spec declares zero targets." That was true only
    # while the two clamped graphs were the entire pinned corpus. Extending the
    # witness to the three UNCLAMPED reference graphs made zero the expected
    # outcome, not an impossible one: amazon, dblp and com-youtube select no
    # targets at all among 3,030,420 printed zeros between them, because every
    # printed-zero node's neighbourhood is a clique and so no nonadjacent
    # neighbour pair exists to certify a positive bound.
    #
    # That is the control result the design asks for, so the run must PUBLISH it
    # rather than crash on `int(None)`. Degrees are reported as 0 in that case;
    # `target_count` is what distinguishes "no targets selected" from "targets
    # selected with degree 0", and a degree-0 target is impossible anyway, since
    # MIN_TARGET_DEGREE is 2 and a smaller degree raises above.
    return selected, 0 if min_degree is None else int(min_degree), max_degree, pair_scan


def _witness_for_target(topology: Topology, node: int) -> dict[str, int | bool]:
    neighbours = _row(topology, node)
    usable = qualified_five = qualified_one = 0
    best: tuple[int, int, int] | None = None
    for left in range(len(neighbours) - 1):
        a = int(neighbours[left])
        a_row = _row(topology, a)
        for right in range(left + 1, len(neighbours)):
            b = int(neighbours[right])
            if _contains(a_row, b):
                continue
            common = _common_neighbours(a_row, _row(topology, b))
            if common < 1:
                raise PrecisionWitnessError("length-two witness has no common neighbour")
            usable += 1
            decision = threshold_decision(topology.spec.nodes, common)
            qualified_five += int(bool(decision["gt_5e15"]))
            qualified_one += int(bool(decision["gt_1e14"]))
            candidate = (common, a, b)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        raise PrecisionWitnessError("selected structurally positive node has no usable pair")
    common, a, b = best
    decision = threshold_decision(topology.spec.nodes, common)
    return {
        "a_compact_id": a, "b_compact_id": b,
        "a_original_node_id": int(topology.original_ids[a]),
        "b_original_node_id": int(topology.original_ids[b]),
        "common_neighbor_count": common,
        "usable_pair_count": usable,
        "gt_5e15_qualifying_pair_count": qualified_five,
        "gt_1e14_qualifying_pair_count": qualified_one,
        "rational_numerator": decision.pop("numerator"),
        "rational_denominator": decision.pop("denominator"),
        **decision,
    }


def _write_witnesses(topology: Topology, targets_path: Path, staging_path: Path) -> dict[str, int]:
    totals = {"usable_pair_count": 0, "gt_5e15_qualifying_pair_count": 0,
              "gt_1e14_qualifying_pair_count": 0}
    with targets_path.open(encoding="utf-8", newline="") as input_stream, \
            staging_path.open("w", encoding="utf-8", newline="") as output_stream:
        reader = csv.DictReader(input_stream)
        writer = csv.DictWriter(output_stream, fieldnames=WITNESS_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for target in reader:
            witness = _witness_for_target(topology, int(target["compact_id"]))
            row = {
                "graph": target["graph"], "score_row": target["score_row"],
                "compact_id": target["compact_id"], "original_node_id": target["original_node_id"],
                "degree": target["degree"], "edge_sha256": target["edge_sha256"],
                "score_sha256": target["score_sha256"], **witness,
            }
            writer.writerow(row)
            for name in totals:
                totals[name] += int(witness[name])
    return totals


def _source_hashes() -> dict[str, str]:
    paths = [ROOT / "precision_witness.py", ROOT / "probe_c3_precision_witness.py",
             ROOT / "verify_c3_precision_witness.py"]
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
            for path in paths}


def validate_preflight_spec(spec: GraphSpec, path: Path = PREFLIGHT_PATH) -> None:
    """Bind a production run to the accepted read-only raw-input preflight."""
    try:
        contents = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrecisionWitnessError(f"precision input preflight is unreadable: {path}") from exc
    found = next((item for item in contents.get("graphs", []) if item.get("graph") == spec.graph), None)
    if found is None:
        raise PrecisionWitnessError(f"preflight lacks {spec.graph}")
    edge, score, topology = found.get("edge", {}), found.get("score", {}), found.get("topology", {})
    actual = (edge.get("sha256"), score.get("sha256"), edge.get("parsed_rows"), edge.get("bytes"),
              score.get("nonblank_rows"), score.get("bytes"), topology.get("nodes"),
              topology.get("final_csr_arcs"))
    expected = (spec.edge_sha256, spec.score_sha256, spec.raw_rows, spec.edge_bytes,
                spec.score_rows, spec.score_bytes, spec.nodes, spec.arcs)
    if actual != expected:
        raise PrecisionWitnessError(f"preflight identity disagrees with pinned {spec.graph} specification")


def _memory_snapshot() -> dict[str, int | None]:
    """Report observed process/machine state without making free RAM a correctness gate."""
    if os.name != "nt":
        return {"working_set": None, "available_physical": None}
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    memory = MEMORYSTATUSEX()
    memory.dwLength = ctypes.sizeof(memory)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    process = ctypes.windll.kernel32.GetCurrentProcess()

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]

    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
    return {"working_set": int(counters.WorkingSetSize), "available_physical": int(memory.ullAvailPhys)}


def run_precision_witness(spec: GraphSpec, brava: Path, output_root: Path = OUTPUT_ROOT,
                          *, payload_bytes: int = SORT_PAYLOAD_CAP, workers: int = 1,
                          require_preflight: bool = False) -> dict[str, object]:
    """Publish one graph's target and witness artifacts only after all checks pass."""
    if workers != 1:
        raise PrecisionWitnessError("workers must be 1; witness construction is deliberately serial")
    if require_preflight:
        validate_preflight_spec(spec)
    output_root = Path(output_root)
    final_paths = {
        "targets": output_root / f"{spec.graph}_targets.csv",
        "witnesses": output_root / f"{spec.graph}_witnesses.csv",
        "summary": output_root / f"{spec.graph}_summary.json",
    }
    if any(path.exists() for path in final_paths.values()):
        raise PrecisionWitnessError(f"refusing to overwrite existing precision witness artifact for {spec.graph}")
    topology = build_topology(spec, brava, output_root, payload_bytes=payload_bytes)
    success = False
    try:
        _edge_path, score_path = _paths(spec, Path(brava))
        targets_stage = topology.temp_dir / "targets.csv"
        witnesses_stage = topology.temp_dir / "witnesses.csv"
        target_count, min_degree, max_degree, pair_scan = _select_targets(
            topology, score_path, targets_stage)
        totals = _write_witnesses(topology, targets_stage, witnesses_stage)
        result: dict[str, object] = {
            "status": "conditional_precision_witness_complete",
            # Both ends of the range are recorded 2026-09-10 by Claude Opus 5.
            # Only the maximum was persisted before, so a run could not report
            # the quantity whose inherited prediction it had just falsified.
            "graph": spec.graph, "target_count": target_count,
            "minimum_degree": min_degree, "maximum_degree": max_degree,
            # The measured cumulative pair scan, against the declared budget.
            # Recorded so the design's resource claim is checkable from the
            # artifact instead of resting on a predicted degree range.
            "total_pair_scan": pair_scan,
            "total_pair_scan_budget": MAX_TOTAL_PAIR_SCAN,
            "usable_pair_count": totals["usable_pair_count"],
            "gt_5e15_qualifying_pair_count": totals["gt_5e15_qualifying_pair_count"],
            "gt_1e14_qualifying_pair_count": totals["gt_1e14_qualifying_pair_count"],
            "edge_sha256": spec.edge_sha256, "score_sha256": spec.score_sha256,
            "raw_rows": topology.raw_rows, "edge_bytes": topology.edge_bytes,
            "nodes": spec.nodes, "arcs": spec.arcs, "canonical_edges": topology.canonical_edges,
            "topology_sha256": topology.topology_sha256, "resource_contract": topology.resource,
            "configuration": {"workers": workers, "payload_bytes": payload_bytes,
                              "text_buffer_bytes": TEXT_BUFFER_BYTES,
                              "parser_mapping_cap": PARSER_MAPPING_CAP,
                              "merge_buffer_cap": MERGE_BUFFER_CAP},
            "memory_before_publication": _memory_snapshot(), "source_sha256": _source_hashes(),
            "normalization_condition": (
                "Bounds use endpoint-excluding normalized undirected betweenness only; "
                "they do not establish release graph identity, producer provenance, or exact centrality."
            ),
        }
        summary_stage = topology.temp_dir / "summary.json"
        summary_stage.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Every preflight and witness condition is complete before the first
        # final-path replacement.  The staging tree remains the only output on
        # failure before this point.
        output_root.mkdir(parents=True, exist_ok=True)
        os.replace(targets_stage, final_paths["targets"])
        os.replace(witnesses_stage, final_paths["witnesses"])
        os.replace(summary_stage, final_paths["summary"])
        success = True
        return result
    finally:
        topology.close()
        if success:
            shutil.rmtree(topology.temp_dir)
        else:
            # Close mappings before preserving an incomplete tree for inspection.
            gc.collect()
