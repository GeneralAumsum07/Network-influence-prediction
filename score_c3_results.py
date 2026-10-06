"""Score the completed C3 run without repeating corpus traversal or fitting.

The background run's structural counts and P4 transcript are retained as evidence.
The two shipped zero counts below are from the dated handoff/P4 amendment, not a
claim that this scoring pass recomputed the large graphs. Source CSV pairing is
checked independently, including repeated labels (paired in source order).
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analyse_c3_benchmarks import DEFAULT_BRAVA, REGIME, shares, predict_tau_all


def structural_errors(cells, support):
    """Recompute the structural contrast from counts, never a cached error label."""
    result = pd.Series(index=cells.index, dtype=float)
    for graph, block in cells.groupby('graph', sort=False):
        row = support.loc[graph]
        s = shares(int(row.n), int(row.n_zero))
        result.loc[block.index] = predict_tau_all(block.tau_filtered, s) - block.tau_all
    return result


def attach_source_identity(cells, raw):
    """Retain original row identities before graph-specific finite filtering.

    The legacy occurrence column enumerates finite rows. It remains for backwards
    compatibility, but cannot identify a source run when an earlier row is missing.
    Source occurrence and zero-based CSV data-row indices supply that distinction.
    """
    result = cells.copy()
    for graph, algorithm in cells[['graph', 'algorithm']].drop_duplicates().itertuples(index=False, name=None):
        block = cells[(cells.graph == graph) & (cells.algorithm == algorithm)]
        a = raw.loc[raw.Algorithm == algorithm, graph]
        f = raw.loc[raw.Algorithm == algorithm + '_filtered', graph]
        assert len(a) == len(f), (graph, algorithm, 'unbalanced pairing')
        av = pd.to_numeric(a, errors='coerce').to_numpy()
        fv = pd.to_numeric(f, errors='coerce').to_numpy()
        keep = np.isfinite(av) & np.isfinite(fv)
        np.testing.assert_allclose(block.tau_all, av[keep], atol=1e-14, rtol=0)
        np.testing.assert_allclose(block.tau_filtered, fv[keep], atol=1e-14, rtol=0)
        result.loc[block.index, 'source_occurrence'] = np.flatnonzero(keep)
        result.loc[block.index, 'plain_source_row'] = a.index.to_numpy()[keep]
        result.loc[block.index, 'filtered_source_row'] = f.index.to_numpy()[keep]
    for column in ['source_occurrence', 'plain_source_row', 'filtered_source_row']:
        result[column] = result[column].astype('int64')
    assert not result.duplicated(['graph', 'algorithm', 'source_occurrence']).any()
    return result


def main():
    s = pd.read_csv('results_c3_structure.csv').set_index('graph')
    c = pd.read_csv('results_c3_cells.csv')
    transcript = Path('results/RESULTS_c3_benchmarks.txt').read_text(encoding='utf-8')
    assert 'GATE PASSED' in transcript and 'P4 PASS (gate)' in transcript
    assert set(s.index) == set(c.graph) == set(REGIME)
    assert c[['tau_all', 'tau_filtered']].notna().all().all()

    # The repeated labels are distinct observations, not identical duplicates.
    # Assert source-order pairing instead of silently deduplicating or doing a
    # many-to-many merge, either of which would change the scoring population.
    raw = pd.read_csv(DEFAULT_BRAVA / 'results/betweenness/all_results.csv')
    plain = raw[~raw.Algorithm.str.endswith('_filtered')].copy()
    filt = raw[raw.Algorithm.str.endswith('_filtered')].copy()
    filt['Algorithm'] = filt.Algorithm.str.removesuffix('_filtered')
    for g in REGIME:
        for alg, block in c[c.graph == g].groupby('algorithm', sort=False):
            a = pd.to_numeric(plain.loc[plain.Algorithm == alg, g], errors='coerce').to_numpy()
            f = pd.to_numeric(filt.loc[filt.Algorithm == alg, g], errors='coerce').to_numpy()
            assert len(a) == len(f), (g, alg, 'unbalanced pairing')
            keep = np.isfinite(a) & np.isfinite(f)
            np.testing.assert_allclose(block.tau_all, a[keep], atol=1e-14, rtol=0)
            np.testing.assert_allclose(block.tau_filtered, f[keep], atol=1e-14, rtol=0)
    c['occurrence'] = c.groupby(['graph', 'algorithm']).cumcount()
    assert not c.duplicated(['graph', 'algorithm', 'occurrence']).any()
    c = attach_source_identity(c, raw)

    clamped = {'cit-Patents': (709062, 709724, 662),
               'com-lj': (1150616, 1151702, 1086)}
    s['n_zero_shipped'] = s.n_zero
    for g, (structural, shipped, under) in clamped.items():
        assert int(s.loc[g, 'n_zero']) == structural
        assert shipped - structural == under
        assert f'{under} sub-grid zeros' in transcript
        s.loc[g, 'n_zero_shipped'] = shipped
    for g, row in s.iterrows():
        support = shares(int(row.n), int(row.n_zero_shipped))
        s.loc[g, 'z_shipped'] = support['z']
        s.loc[g, 'w_shipped'] = support['w_exact']
        s.loc[g, 'floor_shipped_geometric'] = support['tau_floor']
    c['z_shipped'] = c.graph.map(s.z_shipped)
    c['w_shipped'] = c.graph.map(s.w_shipped)
    c['masked_family'] = c.algorithm.str.startswith('baseline_')

    # RENAMED 2026-09-07 after review. This column was called
    # 'err_structural_geometric' and described as preserving the STRUCTURAL-support
    # error for sensitivity reporting. That stopped being true once the regenerated
    # input adopted shipped support: c.err is then the shipped-support error, so the
    # column was carrying shipped values under a structural name. Max divergence from
    # an independently recomputed structural error is 1.92e-4 (cit-Patents) and
    # 2.13e-4 (com-lj); headline medians and every verdict are unaffected, but the
    # claimed sensitivity contrast was not actually being preserved. Named for what
    # it holds rather than what it was intended to hold. Phase 6 closure now also
    # recomputes a genuinely structural column independently from source counts.
    c['err_as_scored_geometric'] = c.err
    c['err_structural_geometric'] = structural_errors(c, s)
    for g, block in c.groupby('graph'):
        row = s.loc[g]
        n, nz = int(row.n), int(row.n_zero_shipped)
        nm = n - nz
        total = n * (n - 1) / 2
        scoreable = total - nz * (nz - 1) / 2
        c.loc[block.index, 'tau_all_pred'] = (
            nz * nm + block.tau_filtered * nm * (nm - 1) / 2
        ) / np.sqrt(total * scoreable)
        c.loc[block.index, 'tau_all_pred_tied'] = (
            nz * nm + block.tau_filtered * nm * (nm - 1) / 2
        ) / scoreable
    c['err'] = c.tau_all_pred - c.tau_all
    c['err_tied'] = c.tau_all_pred_tied - c.tau_all
    c['registered_hit'] = c.tau_all <= c.tau_floor + 0.05
    # This is a post-hoc regime illustration. External methods' prediction ties
    # are not available: their geometric comparator is conditional on continuity.
    c['floor_regime'] = np.where(c.masked_family, c.w_shipped,
                               c.graph.map(s.floor_shipped_geometric))
    c['regime_hit'] = c.tau_all <= c.floor_regime + 0.05
    graph = c.groupby('graph').agg(
        cells=('tau_all', 'size'), median_drop=('drop', 'median'),
        min_tau=('tau_all', 'min'), registered_hits=('registered_hit', 'sum'),
        regime_hits=('regime_hit', 'sum'))
    graph = s.join(graph)
    rho = float(spearmanr(graph.z, graph.median_drop).statistic)
    rho_shipped = float(spearmanr(graph.z_shipped, graph.median_drop).statistic)
    p1_mae, p1_signed = float(c.err.abs().median()), float(c.err.median())
    p3_graphs = int((graph.registered_hits > 0).sum())
    regimes = int((graph.regime_hits > 0).sum())
    masked = c[c.masked_family]
    summary = dict(cells=len(c), names=c.algorithm.nunique(), graphs=len(graph),
                   p1_mae=p1_mae, p1_signed=p1_signed,
                   P1='SUPPORTED' if p1_mae <= .05 and p1_signed >= 0 else 'FALSIFIED',
                   rho=rho, rho_shipped=rho_shipped,
                   P2='SUPPORTED' if rho >= .5 else 'FALSIFIED',
                   p3_graphs=p3_graphs, P3='SUPPORTED' if p3_graphs >= 7 else 'FALSIFIED',
                   regime_graphs=regimes, P4='PASSED UNDER REGISTERED CONDITIONAL',
                   masked_cells=len(masked), masked_mae=float(masked.err_tied.abs().median()),
                   masked_max=float(masked.err_tied.abs().max()),
                   structural_mae=float(c.err_structural_geometric.abs().median()))
    controls = c.assign(family=c.algorithm.str.split('_').str[0]).groupby('family').agg(
        cells=('err', 'size'), geometric_mae=('err', lambda x: x.abs().median()),
        tied_mae=('err_tied', lambda x: x.abs().median()))
    c.to_csv('results_c3_scored_cells.csv', index=False)
    graph.to_csv('results_c3_scored_graphs.csv')
    controls.to_csv('results_c3_controls.csv')
    Path('results/c3_scored_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    # Keys are POSIX-style so the provenance file reads the same on every
    # platform; until 2026-09-12 str(Path(...)) wrote the transcript key with a
    # backslash on Windows (Task 6 finding P3-06, Claude Opus 5). The recorded
    # file keeps its old key until the next traversal regenerates it.
    provenance = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        Path('results_c3_structure.csv'), Path('results_c3_cells.csv'),
        Path('results/RESULTS_c3_benchmarks.txt'),
        DEFAULT_BRAVA / 'results/betweenness/all_results.csv']}
    # Record a portable source name, not the temporary machine-specific location.
    provenance['BRAVA-GNN/results/betweenness/all_results.csv'] = provenance.pop((DEFAULT_BRAVA / 'results/betweenness/all_results.csv').as_posix())
    Path('results/c3_scored_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    print(graph[['n', 'n_zero', 'n_zero_shipped', 'z', 'w_shipped', 'tau_floor', 'median_drop', 'registered_hits', 'regime_hits']].to_string())
    print(controls.to_string())
    print('ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
