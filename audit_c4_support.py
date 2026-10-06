"""C4 support and zero-count reconciliation audit of the external BRAVA corpus.

This is not a two-number pilot: aggregate tables cannot recover a method's zero
decision or prediction ties. Reuse C3 counts; read only released decimal targets
and aggregate scores. Nothing is fitted and no graph traversal is repeated.
"""
from pathlib import Path
from decimal import Decimal, localcontext
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analyse_c3_benchmarks import (DEFAULT_BRAVA, ABCDE_GRAPHS, REGIME, shares,
                                   predict_tau_all, predict_tau_all_tied)


def scan_decimal(path):
    """Check the printed decimals exactly, avoiding binary-float grid tolerances.

    Hash bytes during the same streaming read so the result identifies precisely
    the released input. Grid membership alone does not prove rounding mode or
    the unavailable pre-rounding magnitudes.
    """
    count = zeros = off_grid = at_step = 0
    minimum, at_minimum = None, 0
    digest = hashlib.sha256()
    with localcontext() as context, path.open('rb') as stream:
        context.prec = 80
        for line in stream:
            digest.update(line)
            if not line.strip():
                continue
            value = Decimal(line.decode('ascii').strip())
            assert value.is_finite() and value >= 0, path
            scaled = value * Decimal('1e14')
            off_grid += scaled != scaled.to_integral_value()
            count += 1
            zeros += value == 0
            at_step += value == Decimal('1e-14')
            if value > 0:
                if minimum is None or value < minimum:
                    minimum, at_minimum = value, 1
                elif value == minimum:
                    at_minimum += 1
    return dict(values=count, zeros=zeros, off_grid=off_grid,
                at_grid_step=at_step, minimum_positive=str(minimum),
                at_minimum=at_minimum, sha256=digest.hexdigest())


def source_pairs(raw):
    """Pair nth plain and nth filtered label in source order before finite filtering.

    The occurrence index is assigned before graph-specific NA filtering; otherwise
    an absent occurrence could silently relabel the remaining observations.
    """
    raw = raw.copy()
    raw['source_row'] = np.arange(len(raw))
    mask = raw.Algorithm.str.endswith('_filtered')
    plain, filtered = raw[~mask].copy(), raw[mask].copy()
    filtered['Algorithm'] = filtered.Algorithm.str.removesuffix('_filtered')
    for frame in (plain, filtered):
        frame['source_occurrence'] = frame.groupby('Algorithm', sort=False).cumcount()
    names = set(plain.Algorithm) & set(filtered.Algorithm)
    plain, filtered = plain[plain.Algorithm.isin(names)], filtered[filtered.Algorithm.isin(names)]
    assert plain.groupby('Algorithm').size().equals(filtered.groupby('Algorithm').size())
    paired = plain.merge(filtered, on=['Algorithm', 'source_occurrence'],
                         suffixes=('_all', '_filtered'), validate='one_to_one')
    rows = []
    for g in REGIME:
        for _, row in paired.iterrows():
            a = pd.to_numeric(row[g + '_all'], errors='coerce')
            f = pd.to_numeric(row[g + '_filtered'], errors='coerce')
            if np.isfinite(a) and np.isfinite(f):
                rows.append(dict(graph=g, algorithm=row.Algorithm,
                                 source_occurrence=row.source_occurrence,
                                 plain_source_row=row.source_row_all,
                                 filtered_source_row=row.source_row_filtered,
                                 tau_all=a, tau_filtered=f, drop=a-f))
    return paired, pd.DataFrame(rows)


def main():
    structural = pd.read_csv('results_c3_structure.csv').set_index('graph')
    cached = pd.read_csv('results_c3_scored_cells.csv')
    raw_path = DEFAULT_BRAVA / 'results/betweenness/all_results.csv'
    paired, cells = source_pairs(pd.read_csv(raw_path))
    # Verify reuse against the existing C3 population without modifying its files.
    for (g, alg), block in cells.groupby(['graph', 'algorithm'], sort=False):
        old = cached[(cached.graph == g) & (cached.algorithm == alg)]
        np.testing.assert_allclose(block[['tau_all', 'tau_filtered']],
                                   old[['tau_all', 'tau_filtered']], rtol=0, atol=1e-14)
    assert len(cells) == len(cached) == 5608
    assert len(paired) == 404 and paired.Algorithm.nunique() == 395
    records = []
    lines = ['C4 SUPPORT AND ZERO-COUNT RECONCILIATION AUDIT',
             'External support/identifier audit; NOT a two-number pilot.',
             'No per-node method predictions, classification accuracy or ties inferred.',
             'Structural counts reused from C3; no corpus traversal or model fitting.', '']
    grids = {}
    for g in sorted(ABCDE_GRAPHS):
        grids[g] = scan_decimal(DEFAULT_BRAVA / 'datasets/abcde' / (g + '-score.txt'))
        d = grids[g]
        assert d['values'] == int(structural.loc[g, 'n']) and d['off_grid'] == 0
        records.append(dict(audit='decimal_grid', graph=g, **d))
        lines.append(f'{g}: {json.dumps(d, sort_keys=True)}')
    total_values = sum(d['values'] for d in grids.values())
    assert total_values == int(structural.loc[sorted(ABCDE_GRAPHS), 'n'].sum())
    lines += [f'All {total_values:,} printed values lie exactly on the 1e-14 grid; zero exceptions.',
              'CONTRADICTION: brief and C3 third amendment say 14,943,174; actual total is',
              '15,043,174 (100,000 more). The existing P4 subset denominators sum correctly.',
              'Defect: quantised targets described as exact support. Metadata remedy: target',
              'precision/rounding convention, checksum and both support counts.',
              'Inference only: under nearest rounding, positives strictly below 5e-15 round',
              'to zero; the half-step outcome depends on the rounding tie rule. Printed',
              'files do not establish rounding mode or exact discrepant positive magnitudes.', '']
    errors = {'structural': [], 'shipped': []}
    for g in sorted(REGIME):
        row = structural.loc[g]
        block = cells[cells.graph == g]
        a = shares(int(row.n), int(row.n_zero))
        b = shares(int(row.n), grids[g]['zeros'] if g in grids else int(row.n_zero))
        pa, pb = predict_tau_all(block.tau_filtered, a), predict_tau_all(block.tau_filtered, b)
        ta, tb = predict_tau_all_tied(block.tau_filtered, a), predict_tau_all_tied(block.tau_filtered, b)
        errors['structural'].extend(pa - block.tau_all)
        errors['shipped'].extend(pb - block.tau_all)
        if g in ('cit-Patents', 'com-lj'):
            d = dict(audit='support', graph=g, n=int(row.n),
                     structural_zeros=a['n_zero'], shipped_zeros=b['n_zero'])
            for metric, key in [('z', 'z'), ('w', 'w_exact'), ('geometric_floor', 'tau_floor')]:
                d.update({metric+'_structural': a[key], metric+'_shipped': b[key],
                          metric+'_delta': b[key]-a[key]})
            d.update(geometric_prediction_max_delta=float(np.max(np.abs(pb-pa))),
                     tied_prediction_max_delta=float(np.max(np.abs(tb-ta))),
                     geometric_signed_median_structural=float(np.median(pa-block.tau_all)),
                     geometric_signed_median_shipped=float(np.median(pb-block.tau_all)),
                     tied_signed_median_structural=float(np.median(ta-block.tau_all)),
                     tied_signed_median_shipped=float(np.median(tb-block.tau_all)),
                     registered_hits_structural=int((block.tau_all <= a['tau_floor']+.05).sum()),
                     sensitivity_hits_shipped=int((block.tau_all <= b['tau_floor']+.05).sum()))
            records.append(d)
            lines.append(json.dumps(d, sort_keys=True))
    for policy, err in errors.items():
        d = dict(audit='support_global', graph='ALL', policy=policy,
                 p1_absolute_median=float(np.median(np.abs(err))),
                 p1_signed_median=float(np.median(err)))
        records.append(d)
        lines.append(json.dumps(d, sort_keys=True))
    lines += ['Defect: structural support substituted for the shipped positive filter.',
              'Metadata remedy: preserve both support counts and identify the scored target.',
              'Published tau columns and their observed drops are unchanged (delta 0).',
              'A tau filtered on structural positives cannot be reconstructed from aggregates.',
              'Only conditional mixture predictions/reference values above can be quantified.', '']
    multiplicity = paired.groupby('Algorithm').size()
    lines.append('Repeated names and paired occurrences: ' + json.dumps(
        multiplicity[multiplicity > 1].to_dict(), sort_keys=True))
    for _, row in paired[paired.Algorithm.isin(multiplicity[multiplicity > 1].index)].iterrows():
        records.append(dict(audit='repeated_identifier', graph='ALL',
                            algorithm=row.Algorithm, source_occurrence=int(row.source_occurrence),
                            plain_source_row=int(row.source_row_all),
                            filtered_source_row=int(row.source_row_filtered)))
    for path in (raw_path, Path('results_c3_structure.csv'), Path('results_c3_scored_cells.csv')):
        records.append(dict(audit='input_provenance', graph='ALL', source=path.name,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    # First/last are explicitly sensitivity policies, not repairs. Keep source
    # occurrence 0 / final occurrence before finite filtering, not first finite.
    for policy in ('retain_occurrences', 'keep_first', 'keep_last'):
        if policy == 'retain_occurrences':
            selected = cells
        else:
            selected_pairs = paired.drop_duplicates('Algorithm', keep=policy.split('_')[1])
            selected = cells.merge(selected_pairs[['Algorithm', 'source_occurrence']],
                                   left_on=['algorithm', 'source_occurrence'],
                                   right_on=['Algorithm', 'source_occurrence'], validate='many_to_one')
        medians = selected.groupby('graph')['drop'].median().reindex(sorted(REGIME))
        rho = float(spearmanr(structural.loc[medians.index, 'z'], medians).statistic)
        for g, block in selected.groupby('graph'):
            original = cells[cells.graph == g]
            d = dict(audit='identifier_sensitivity', graph=g, policy=policy,
                     cells=len(block), cell_delta=len(block)-len(original),
                     median_drop=float(block['drop'].median()),
                     median_drop_delta=float(block['drop'].median()-original['drop'].median()),
                     median_all=float(block.tau_all.median()),
                     median_all_delta=float(block.tau_all.median()-original.tau_all.median()),
                     median_filtered=float(block.tau_filtered.median()),
                     median_filtered_delta=float(block.tau_filtered.median()-original.tau_filtered.median()),
                     registered_hits=int((block.tau_all <= structural.loc[g, 'tau_floor']+.05).sum()))
            records.append(d)
            lines.append(json.dumps(d, sort_keys=True))
        lines.append(f'{policy}: finite cells={len(selected)}; graph-level Spearman rho={rho:.12f}')
    lines += ['', 'Defect: ambiguous repeated labels (six names, nine additional occurrences).',
              'Metadata remedy: source row and occurrence IDs, graph identity, explicit pairing',
              'and aggregation population. Name-only many-to-many joins invent observations;',
              'name-only deduplication removes observations. Neither is an authorised C3 policy.',
              'Finite-pair source rows use zero-based data-row indices (header excluded).',
              'C3 registered verdicts unchanged; support/dedup sensitivities are not rescoring.',
              'ALL CHECKS PASSED']
    pd.DataFrame(records).to_csv('results_c4_support_audit.csv', index=False)
    Path('results/RESULTS_c4_support_audit.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
