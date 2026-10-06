"""Independent checks for bounded non-backtracking walk counts.

Run with the project interpreter:
    C:/Users/Rachit/miniconda3/envs/influence/python.exe verify_nonbacktracking_local.py
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import tempfile
from pathlib import Path

from influence.criticality import build_nonbacktracking_direct
from influence.preprocessing import Network
from influence.nonbacktracking_local import nb_walk_counts
from probe_nonbacktracking_local import (
    kendall_tau_b, run_network, validate_inputs, write_summary,
)


def fixture(name: str, n: int, edges: list[tuple[int, int]]) -> Network:
    rows = [u for u, v in edges] + [v for u, v in edges]
    cols = [v for u, v in edges] + [u for u, v in edges]
    adj = sp.csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(n, n))
    adj.sort_indices()
    return Network(name, adj, [adj.indices[adj.indptr[i]:adj.indptr[i + 1]] for i in range(n)],
                   np.diff(adj.indptr).astype(np.int64), np.arange(n))


def explicit_counts(net: Network, length: int) -> np.ndarray:
    """Enumerate legal walks directly, independently of the recurrence."""
    out = np.zeros(net.n, dtype=np.int64)
    def visit(root: int, previous: int, current: int, remaining: int) -> None:
        if remaining == 0:
            out[root] += 1
            return
        for nxt in net.nbrs[current]:
            if int(nxt) != previous:
                visit(root, current, int(nxt), remaining - 1)
    for root in range(net.n):
        for nxt in net.nbrs[root]:
            visit(root, root, int(nxt), length - 1)
    return out


def direct_matrix_counts(net: Network, length: int) -> np.ndarray:
    """Use B only in this small-fixture verifier, never in the production API."""
    arcs = [(u, int(v)) for u in range(net.n) for v in net.nbrs[u]]
    if not arcs:
        return np.zeros(net.n, dtype=np.int64)
    B = build_nonbacktracking_direct(net)
    continuations = np.ones(len(arcs), dtype=np.int64)
    for _ in range(length - 1):
        continuations = B @ continuations
    out = np.zeros(net.n, dtype=np.int64)
    for (root, _), value in zip(arcs, continuations):
        out[root] += value
    return out


def assert_equal(actual, expected, label: str) -> None:
    if not np.array_equal(actual, np.asarray(expected, dtype=np.int64)):
        raise AssertionError(f"{label}: expected {expected}, got {actual.tolist()}")


def check_named_fixtures() -> None:
    cases = [
        (fixture('path4', 4, [(0, 1), (1, 2), (2, 3)]), ([1, 2, 2, 1], [1, 1, 1, 1], [1, 0, 0, 1])),
        (fixture('cycle4', 4, [(0, 1), (1, 2), (2, 3), (3, 0)]), ([2, 2, 2, 2], [2, 2, 2, 2], [2, 2, 2, 2])),
        (fixture('star4', 4, [(0, 1), (0, 2), (0, 3)]), ([3, 1, 1, 1], [0, 2, 2, 2], [0, 0, 0, 0])),
        (fixture('triangle', 3, [(0, 1), (1, 2), (2, 0)]), ([2, 2, 2], [2, 2, 2], [2, 2, 2])),
        (fixture('isolates', 3, []), ([0, 0, 0], [0, 0, 0], [0, 0, 0])),
    ]
    for net, expected in cases:
        for length, wanted in enumerate(expected, start=1):
            actual = nb_walk_counts(net, length)
            assert_equal(actual, wanted, f'{net.name} length {length}')
            assert_equal(actual, explicit_counts(net, length), f'{net.name} explicit length {length}')
            assert_equal(actual, direct_matrix_counts(net, length), f'{net.name} direct-B length {length}')


def check_contract() -> None:
    net = fixture('edge', 2, [(0, 1)])
    if nb_walk_counts(net, 1).dtype != np.dtype(np.int64):
        raise AssertionError('counts must be exact int64 values')
    for bad in (0, -1, 4, 1.5, True, '3'):
        try:
            nb_walk_counts(net, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f'length {bad!r} must be rejected')


def check_ties_and_overflow_guard() -> None:
    if kendall_tau_b(np.array([1, 1, 1]), np.array([2, 3, 4])) is not None:
        raise AssertionError('a tied predictor must remain unscored')
    if kendall_tau_b(np.array([1, 2, 3]), np.array([3, 2, 1])) != -1.0:
        raise AssertionError('Kendall tau-b must preserve an exact anti-ranking')
    from influence.nonbacktracking_local import _checked_int64
    try:
        _checked_int64([np.iinfo(np.int64).max + 1], 3)
    except OverflowError:
        pass
    else:
        raise AssertionError('out-of-range exact counts must not wrap')


def check_input_and_resume_guards() -> None:
    """Corruption must fail before any output can be accepted or resumed."""
    net = fixture('edge', 2, [(0, 1)])
    features = __import__('pandas').DataFrame({
        'node': [0, 1], 'original_id': [0, 1], 'h_index_3': [1.0, 1.0],
    })
    targets = __import__('pandas').DataFrame({'node': [0, 1], 'spread_mean': [1.0, 2.0]})
    registry = __import__('pandas').DataFrame({'feature': ['h_index_3']})
    meta = {'n_sims': 4000, 'simulation_seed': 0, 'convention': 'uniform', 'p': .1, 'n': 2, 'm': 1}
    validate_inputs('fixture', meta, net, features, targets, registry)
    bad_meta = dict(meta, convention='trivalency')
    try:
        validate_inputs('fixture', bad_meta, net, features, targets, registry)
    except ValueError as exc:
        if 'uniform seed-0 4000-draw' not in str(exc):
            raise AssertionError(f'unexpected metadata error: {exc}') from exc
    else:
        raise AssertionError('non-uniform metadata must be rejected')
    bad_features = features.copy()
    bad_features.loc[1, 'original_id'] = 0
    try:
        validate_inputs('fixture', meta, net, bad_features, targets, registry)
    except ValueError as exc:
        if 'original IDs' not in str(exc):
            raise AssertionError(f'unexpected ID error: {exc}') from exc
    else:
        raise AssertionError('duplicate original IDs must be rejected')

    # A deliberately incompatible checkpoint must fail before reading or
    # publishing a production result.  The temporary directory is isolated.
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory)
        (out / 'ca-GrQc.json').write_text('{"status":"complete","identity":{"wrong":true}}', encoding='utf8')
        try:
            run_network('ca-GrQc', out, pilot=False)
        except ValueError as exc:
            if 'resume identity mismatch' not in str(exc):
                raise AssertionError(f'unexpected resume error: {exc}') from exc
        else:
            raise AssertionError('mismatched checkpoint must not resume')
        try:
            write_summary(out)
        except ValueError as exc:
            if 'identity no longer matches current inputs' not in str(exc):
                raise AssertionError(f'unexpected summary identity error: {exc}') from exc
        else:
            raise AssertionError('summary must reject a completed record with wrong identity')


def main() -> None:
    check_named_fixtures()
    check_contract()
    check_ties_and_overflow_guard()
    check_input_and_resume_guards()
    print('bounded non-backtracking local checks: ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
