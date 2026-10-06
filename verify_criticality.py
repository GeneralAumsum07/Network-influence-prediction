"""Independent analytical regression checks for epidemic-threshold estimates.

Run with the project interpreter:
    C:/Users/Rachit/miniconda3/envs/influence/python.exe verify_criticality.py

Every expected threshold below is derived from the graph definition, not from
the implementation under test.  In particular, changing the non-backtracking
path to accept the Ihara--Bass matrix's spurious tree roots must make the path
and tree checks fail.
"""

from __future__ import annotations

import math
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import scipy.sparse as sp

from influence.criticality import (
    build_ihara_bass,
    build_nonbacktracking_direct,
    epidemic_threshold,
    leading_eigenvalue,
    transmission_from_threshold,
)
from influence.preprocessing import Network, build_network


RTOL = 1e-7
ATOL = 1e-9
CACHE_RTOL = 1e-7


def assert_close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=RTOL, abs_tol=ATOL):
        raise AssertionError(f"{label}: expected {expected:.15g}, got {actual:.15g}")


def graph(edges: list[tuple[int, int]], name: str) -> Network:
    return build_network(edges, name=name)


def disconnected_graph(edges: list[tuple[int, int]], n: int, name: str) -> Network:
    """Construct a sparse test graph without preprocessing away components."""
    endpoints = np.asarray(edges, dtype=np.int64)
    rows = np.concatenate([endpoints[:, 0], endpoints[:, 1]])
    cols = np.concatenate([endpoints[:, 1], endpoints[:, 0]])
    adj = sp.csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)),
                        shape=(n, n))
    adj.sort_indices()
    return Network(
        name=name,
        adj=adj,
        nbrs=[adj.indices[adj.indptr[i]:adj.indptr[i + 1]] for i in range(n)],
        degree=np.diff(adj.indptr).astype(np.int64),
        original_ids=np.arange(n, dtype=np.int64),
    )


def edgeless_network(n: int) -> Network:
    """Construct a valid empty adjacency because preprocessing needs an edge list."""
    adj = sp.csr_matrix((n, n), dtype=np.int8)
    return Network(
        name=f"edgeless-{n}",
        adj=adj,
        nbrs=[np.empty(0, dtype=np.int64) for _ in range(n)],
        degree=np.zeros(n, dtype=np.int64),
        original_ids=np.arange(n, dtype=np.int64),
    )


def assert_raises_value_error(action, contains: str, label: str) -> None:
    try:
        action()
    except ValueError as exc:
        if contains not in str(exc):
            raise AssertionError(f"{label}: expected {contains!r} in {exc!r}") from exc
    else:
        raise AssertionError(f"{label}: expected ValueError")


def check_analytical_thresholds() -> None:
    # P4 has adjacency spectral radius phi=(1+sqrt(5))/2.  The direct B is
    # nilpotent, so the NB process has no repeating non-backtracking walk.
    path4 = graph([(0, 1), (1, 2), (2, 3)], "path4")
    assert_close(
        epidemic_threshold(path4, "adjacency"),
        2.0 / (1.0 + math.sqrt(5.0)),
        "P4 adjacency threshold",
    )
    if not math.isinf(epidemic_threshold(path4, "nonbacktracking")):
        raise AssertionError("P4 non-backtracking threshold must be infinite")

    # C4 is bipartite, so it also exercises sign ambiguity.  Its directed
    # non-backtracking operator consists of two directed 4-cycles: rho(B)=1.
    cycle4 = graph([(0, 1), (1, 2), (2, 3), (3, 0)], "cycle4")
    assert_close(epidemic_threshold(cycle4, "nonbacktracking"), 1.0,
                 "C4 non-backtracking threshold")

    # Every directed arc in K4 has two legal next arcs, hence rho(B)=2.
    complete4 = graph(
        [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], "complete4"
    )
    assert_close(epidemic_threshold(complete4, "nonbacktracking"), 0.5,
                 "K4 non-backtracking threshold")

    # Added 2026-09-11 by Claude Opus 5 (Task 6 audit findings P1-05, P1-10).
    #
    # K_{3,3}: bipartite AND multicyclic AND 3-regular, so it is the one
    # fixture that reaches the reduced sparse solve with a +/- extremal pair
    # present - the code path where a sign could leak. C4 is bipartite but
    # unicyclic and never gets there. rho(B) = d - 1 = 2, beta_c = 0.5.
    k33 = graph([(i, j) for i in range(3) for j in range(3, 6)], "K33")
    for trial in range(8):
        assert_close(epidemic_threshold(k33, "nonbacktracking"), 0.5,
                     f"K_3,3 non-backtracking threshold (trial {trial})")

    # Theta graphs: two hubs joined by three internally disjoint paths of
    # L+1 edges. Uniform subdivision of the 3-edge dipole (rho(B) = 2) gives
    # rho(B) = 2^(1/(L+1)) exactly. From L = 10 the spectrum crowds the unit
    # circle and Arnoldi raised ArpackNoConvergence before the dense fallback;
    # L = 6 converges and pins the closed form on the sparse path too.
    for L in (6, 10, 24):
        edges, nxt = [], 2
        for _ in range(3):
            prev = 0
            for _k in range(L):
                edges.append((prev, nxt))
                prev, nxt = nxt, nxt + 1
            edges.append((prev, 1))
        th = graph(edges, f"theta{L}")
        assert_close(epidemic_threshold(th, "nonbacktracking"),
                     2.0 ** (-1.0 / (L + 1)),
                     f"theta(L={L}) non-backtracking threshold")
        assert_close(
            leading_eigenvalue(build_nonbacktracking_direct(th)),
            2.0 ** (1.0 / (L + 1)),
            f"theta(L={L}) direct non-backtracking spectral radius",
        )


def check_direct_and_reduced_agree_when_cyclic() -> None:
    # These cyclic fixtures have no tree-only Ihara--Bass root ambiguity.
    for net in (
        graph([(0, 1), (1, 2), (2, 3), (3, 0)], "cycle4"),
        graph([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], "complete4"),
    ):
        direct = leading_eigenvalue(build_nonbacktracking_direct(net))
        reduced = leading_eigenvalue(build_ihara_bass(net))
        assert_close(reduced, direct, f"{net.name} direct/reduced spectral radius")


def check_unicyclic_and_disconnected_boundaries() -> None:
    # C8 plus a 64-edge pendant tail has one recurrent NB class: the cycle.
    # The tail only supplies transient walks, so rho(B)=1 exactly.
    tail_end = 8 + 64
    long_tail = [(i, i + 1) for i in range(7)] + [(7, 0)]
    long_tail += [(0, 8)] + [(i, i + 1) for i in range(8, tail_end - 1)]
    unicyclic = graph(long_tail, "cycle8-tail64")
    if (unicyclic.n, unicyclic.m) != (72, 72):
        raise AssertionError(f"unexpected C8+64-edge-tail shape: {(unicyclic.n, unicyclic.m)}")
    values = [epidemic_threshold(unicyclic, "nonbacktracking") for _ in range(5)]
    if values != [1.0] * 5:
        raise AssertionError(f"unicyclic threshold must be exact and deterministic: {values}")
    assert_close(
        leading_eigenvalue(build_nonbacktracking_direct(unicyclic)), 1.0,
        "C8+tail direct non-backtracking spectral radius",
    )

    # Component-wise excess must keep a cyclic component when another component
    # is a forest; overall m<n alone would incorrectly label this a forest.
    cycle_plus_tree = disconnected_graph(
        [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6)],
        n=7,
        name="cycle-plus-tree",
    )
    if epidemic_threshold(cycle_plus_tree, "nonbacktracking") != 1.0:
        raise AssertionError("cycle-plus-tree non-backtracking threshold must be 1")


def check_determinism_and_boundaries() -> None:
    path4 = graph([(0, 1), (1, 2), (2, 3)], "path4")
    values = [epidemic_threshold(path4, "adjacency") for _ in range(5)]
    if any(value < 0 or not math.isfinite(value) for value in values):
        raise AssertionError(f"adjacency thresholds must be finite and nonnegative: {values}")
    if max(values) - min(values) > RTOL * max(values):
        raise AssertionError(f"adjacency thresholds exceed eigensolver tolerance: {values}")

    cycle4 = graph([(0, 1), (1, 2), (2, 3), (3, 0)], "cycle4")
    nb_values = [epidemic_threshold(cycle4, "nonbacktracking") for _ in range(5)]
    if any(value < 0 or not math.isfinite(value) for value in nb_values):
        raise AssertionError(f"NB thresholds must be finite and nonnegative: {nb_values}")
    if max(nb_values) - min(nb_values) > RTOL * max(nb_values):
        raise AssertionError(f"NB thresholds exceed eigensolver tolerance: {nb_values}")

    for net in (edgeless_network(0), edgeless_network(1)):
        for method in ("adjacency", "nonbacktracking"):
            if not math.isinf(epidemic_threshold(net, method)):
                raise AssertionError(f"{net.name} {method} threshold must be infinite")

    # A forest has no NB transition cycle, so a finite transmission probability
    # cannot be derived from its critical threshold.  K4 at 3x has p=1.5,
    # outside the IC probability range.
    assert_raises_value_error(
        lambda: transmission_from_threshold(path4, 1.5),
        "no finite non-backtracking critical point",
        "forest transmission boundary",
    )
    complete4 = graph(
        [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], "complete4"
    )
    assert_raises_value_error(
        lambda: transmission_from_threshold(complete4, 3.0),
        "outside [0, 1]",
        "probability-range boundary",
    )
    assert_raises_value_error(
        lambda: transmission_from_threshold(complete4, 0.0),
        "finite and positive",
        "zero regime multiplier boundary",
    )


def check_registered_cache_thresholds() -> None:
    """Compare current code to the preserved cache lineage without rewriting it."""
    from pathlib import Path
    import json

    from influence.preprocessing import load_edgelist

    metadata = sorted(Path(".").glob("cache_meta_*.json"))
    if len(metadata) != 5:
        raise AssertionError(f"expected five current cache metadata files, found {metadata}")
    for meta_path in metadata:
        metadata_row = json.loads(meta_path.read_text(encoding="utf-8"))
        tag = meta_path.stem.removeprefix("cache_meta_")
        current = epidemic_threshold(load_edgelist(Path("data") / f"{tag}.txt"))
        cached = float(metadata_row["beta_c"])
        if not math.isclose(current, cached, rel_tol=CACHE_RTOL, abs_tol=ATOL):
            raise AssertionError(
                f"{tag} cache beta_c moved: cached={cached:.15g}, current={current:.15g}"
            )


def check_stage1_rejects_tree_before_cache_writes() -> None:
    """The production CLI must fail before a tree can create a cache lineage."""
    tag = "criticality-tree-input"
    outputs = [
        Path(f"cache_{kind}_{tag}{suffix}")
        for kind, suffix in (
            ("features", ".csv"), ("targets", ".csv"),
            ("registry", ".csv"), ("cascades", ".npy"), ("meta", ".json"),
        )
    ]
    if any(path.exists() for path in outputs):
        raise AssertionError(f"refusing to overwrite existing verifier output: {outputs}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / f"{tag}.txt"
        input_path.write_text("0 1\n1 2\n2 3\n", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "stage1_prepare.py", str(input_path), "1", "1.5"],
            text=True,
            capture_output=True,
            check=False,
        )
    if completed.returncode == 0:
        raise AssertionError("stage1 accepted a tree with no finite NB critical point")
    if "no finite non-backtracking critical point" not in (completed.stdout + completed.stderr):
        raise AssertionError(
            "stage1 did not explain the missing finite NB critical point:\n"
            + completed.stdout + completed.stderr
        )
    created = [path for path in outputs if path.exists()]
    if created:
        raise AssertionError(f"stage1 wrote cache outputs after rejecting tree: {created}")


def main() -> None:
    check_analytical_thresholds()
    check_direct_and_reduced_agree_when_cyclic()
    check_unicyclic_and_disconnected_boundaries()
    check_determinism_and_boundaries()
    check_stage1_rejects_tree_before_cache_writes()
    check_registered_cache_thresholds()
    print("criticality analytical regression checks: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
