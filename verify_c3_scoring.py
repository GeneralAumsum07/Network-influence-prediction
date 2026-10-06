"""Independent regression checks for C3 support and source-row provenance."""
import numpy as np
import pandas as pd
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def main():
    from analyse_c3_benchmarks import gate_project_table
    # A standalone gate must not certify an empty/partial corpus merely because
    # the broader pipeline also runs another, stricter fallback check.
    with patch('pathlib.Path.exists', return_value=False):
        ok, message = gate_project_table()
        assert not ok and message.count('FAIL') == 5, 'Missing project graphs must fail'
    # Import inside the check so the missing implementation is an explicit red test.
    from score_c3_results import attach_source_identity, structural_errors
    cells = pd.DataFrame(dict(graph=['g'], algorithm=['a'], occurrence=[0],
                              tau_all=[.7], tau_filtered=[.2], err=[999.]))
    support = pd.DataFrame(dict(graph=['g'], n=[5], n_zero=[2], n_zero_shipped=[3])).set_index('graph')
    # Two zeros leave six boundary pairs and three positive pairs. The registered
    # geometric predictor is (6 + .2*3)/sqrt(9*10), independently of cached errors.
    expected = 6.6/np.sqrt(90) - .7
    np.testing.assert_allclose(structural_errors(cells, support), [expected], rtol=0, atol=1e-14)
    cells.err = -999.
    np.testing.assert_allclose(structural_errors(cells, support), [expected], rtol=0, atol=1e-14)

    # Occurrence zero is absent on this graph. Finite occurrence 0 must still map
    # to SOURCE occurrence 1, preserving the original rows instead of relabelling it.
    raw = pd.DataFrame(dict(Algorithm=['a', 'a', 'a_filtered', 'a_filtered'],
                            g=[np.nan, .7, .1, .2]))
    got = attach_source_identity(cells, raw)
    assert got.source_occurrence.tolist() == [1]
    assert got.plain_source_row.tolist() == [1]
    assert got.filtered_source_row.tolist() == [3]
    assert got.occurrence.tolist() == [0]
    bad = cells.copy()
    bad.tau_filtered = .9
    try:
        attach_source_identity(bad, raw)
    except AssertionError:
        pass
    else:
        raise AssertionError('Mispaired source values must fail')
    from analyse_c3_benchmarks import ABCDE_GRAPHS, gate_undirected_abcde
    # Tiny path fixture exercises the interface used by main(), not the real
    # corpus or its registered precision conditional. Centre is the sole positive.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        data = root / 'datasets' / 'abcde'
        data.mkdir(parents=True)
        for name in ABCDE_GRAPHS:
            (data / (name + '.txt')).write_text('0 1\n1 2\n')
            (data / (name + '-score.txt')).write_text('0\n1\n0\n')
        ok, _, details = gate_undirected_abcde(root)
        assert ok and all(d['n_zero_shipped'] == 2 for d in details.values())
        assert details['cit-Patents']['clamped'] and not details['amazon']['clamped']
        (data / 'amazon-score.txt').unlink()
        ok, _, _ = gate_undirected_abcde(root)
        assert not ok, 'Missing required reference must fail, not silently skip'

    # Task 6 finding P3-04 (Claude Opus 5, 2026-09-12): a failed P4 gate must
    # not overwrite the transcript score_c3_results.py asserts against, and
    # nothing must be promoted over the previous CSVs. Force the directed gate
    # to fail with the real corpus untouched, run main() into a temp root that
    # already holds a "previous traversal", and check nothing of it changed.
    import analyse_c3_benchmarks as c3
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'results').mkdir()
        previous = {root / 'results' / c3.RESULTS_TXT.name: 'previous transcript',
                    root / c3.STRUCTURE_CSV.name: 'previous structure',
                    root / c3.CELLS_CSV.name: 'previous cells'}
        for path, text in previous.items():
            path.write_text(text, encoding='utf-8')
        with patch.object(c3, 'gate_directed_rule', return_value=(False, 'forced failure')), \
                patch('builtins.print'):
            rc = c3.main(argv=[str(root)], out_root=root)
        assert rc == 1, 'a failed gate must return 1'
        for path, text in previous.items():
            assert path.read_text(encoding='utf-8') == text, f'{path.name} was overwritten on GATE FAILED'
        failed = root / 'results' / c3.GATE_FAILED_TXT.name
        assert failed.is_file() and 'GATE FAILED' in failed.read_text(encoding='utf-8'), \
            'the failed-gate transcript must land in the sidecar'
        assert not list(root.rglob('*.staging')), 'no staging file may survive a failed gate'
    # And the shares() floor must be the pipeline's, at 1e-9 (P3-02).
    for n, n_z in ((4158, 2288), (10, 3), (100, 0)):
        c3.assert_floor_matches_pipeline(c3.shares(n, n_z))
    s = c3.shares(4158, 2288)
    assert s['tau_floor'] > s['tau_floor_wz_approx'], 'exact floor exceeds the large-n form at finite n'
    assert abs(s['tau_floor'] - s['tau_floor_wz_approx']) < 5e-5
    print('C3 structural-support errors and pre-filter source identities: ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
