"""C4 reusable reporting and internal code-correctness check, NOT pilot evidence.

The caller must supply the zero decision explicitly; None means unavailable.
The cache runner declares score == 0 retrospectively for code correctness only.
It does not attach a perfect auxiliary certificate to a learned estimator, fit
anything, or calibrate a threshold. Forest outputs have real ties.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse_c3_benchmarks import shares, predict_tau_all, predict_tau_all_tied


def tied_pairs(values):
    """Count exact floating-point equality, without introducing a rounding grid."""
    _, counts = np.unique(values, return_counts=True)
    return sum(int(k) * (int(k) - 1) // 2 for k in counts)


def tau_with_reason(y, s, prefix):
    if len(y) < 2:
        return float('nan'), 'fewer_than_two_' + prefix
    if np.unique(y).size == 1:
        return float('nan'), 'constant_' + prefix.rstrip('s') + '_reference'
    if np.unique(s).size == 1:
        return float('nan'), 'constant_' + prefix.rstrip('s') + '_prediction'
    return float(kendalltau(s, y, variant='b').statistic), ''


def report(y, scores, *, predicted_zero, decision_provenance):
    """Report aligned held-out vectors, with the zero class explicitly labelled.

    Negative/nonfinite truth and nonfinite scores are errors, not silently dropped
    observations. Undefined metrics stay NaN with reasons. Confusion terminology:
    false_zero is a reference-positive node declared zero; missed_zero is the
    converse. Fractions condition on reference positives and zeros respectively.
    Simplified mixture labels require ALL their assumptions, not just one tie count.
    """
    y, s = np.asarray(y, dtype=float), np.asarray(scores, dtype=float)
    if y.ndim != 1 or s.shape != y.shape or not np.isfinite(y).all() or not np.isfinite(s).all() or (y < 0).any():
        raise ValueError('Expected aligned finite 1D scores and nonnegative reference')
    if not isinstance(decision_provenance, str) or not decision_provenance.strip():
        raise ValueError('Declare decision provenance, including when unavailable')
    z = y == 0
    n, nz, nm = len(y), int(z.sum()), int((~z).sum())
    nan = float('nan')
    out = dict(n=n, n_zero=nz, n_positive=nm, z=nz/n if n else nan,
               decision_provenance=decision_provenance)
    for key in ['zero_accuracy', 'true_zero', 'missed_zero', 'false_zero', 'true_positive',
                'false_zero_rate', 'missed_zero_rate']:
        out[key] = nan
    out['zero_accuracy_na_reason'] = 'no_declared_zero_decision'
    if predicted_zero is not None:
        d = np.asarray(predicted_zero)
        if d.dtype != np.bool_ or d.shape != y.shape:
            raise ValueError('predicted_zero must be an aligned Boolean vector')
        out.update(true_zero=int((d & z).sum()), missed_zero=int((~d & z).sum()),
                   false_zero=int((d & ~z).sum()), true_positive=int((~d & ~z).sum()),
                   zero_accuracy=float(np.mean(d == z)) if n else nan,
                   zero_accuracy_na_reason='' if n else 'empty_evaluation')
        out['false_zero_rate'] = out['false_zero']/nm if nm else nan
        out['missed_zero_rate'] = out['missed_zero']/nz if nz else nan
    out['false_zero_rate_na_reason'] = ('no_declared_zero_decision' if predicted_zero is None
                                        else 'no_reference_positives' if not nm else '')
    out['missed_zero_rate_na_reason'] = ('no_declared_zero_decision' if predicted_zero is None
                                         else 'no_reference_zeros' if not nz else '')
    # Filter only by truth: predicted zeros among positives remain evaluated.
    out['tau_positive'], out['tau_positive_na_reason'] = tau_with_reason(y[~z], s[~z], 'positives')
    out['tau_all'], out['tau_all_na_reason'] = tau_with_reason(y, s, 'nodes')
    out['tau_drop'] = out['tau_all'] - out['tau_positive']
    tz, tp, tall = tied_pairs(s[z]), tied_pairs(s[~z]), tied_pairs(s)
    ry = tied_pairs(y[~z])
    total, zero_pairs = n*(n-1)//2, nz*(nz-1)//2
    out.update(distinct_predictions=int(np.unique(s).size),
               distinct_predictions_zero=int(np.unique(s[z]).size),
               distinct_predictions_positive=int(np.unique(s[~z]).size),
               prediction_ties_zero=tz, prediction_ties_positive=tp,
               prediction_ties_cross=tall-tz-tp, reference_ties_positive=ry,
               total_pairs=total, reference_ties=zero_pairs+ry, prediction_ties=tall,
               # Python integers keep pair counts exact, but NumPy sqrt dispatches
               # huge integers as objects. Convert only at the final square root.
               tau_b_denominator=float(np.sqrt(float((total-zero_pairs-ry)*(total-tall)))))
    # Zero-block ties alone do not justify the arithmetic mixture. In particular,
    # forests also tie positives and can tie or reverse pairs across the boundary.
    separated = bool(nz and nm and s[z].max() < s[~z].min())
    out['perfect_score_separation'] = separated
    out['zero_tie_regime'] = ('no_zero_pairs' if nz < 2 else 'all_tied' if tz == zero_pairs
                              else 'untied' if tz == 0 else 'partially_tied')
    out.update(mixture_regime='general_pair_accounting', mixture_prediction=nan,
               zero_skill_reference=nan)
    if nz >= 2 and nm >= 2 and separated and ry == 0 and tp == 0:
        support = shares(n, nz)
        if tz == zero_pairs:
            out.update(mixture_regime='zero_block_tied',
                       mixture_prediction=float(predict_tau_all_tied(out['tau_positive'], support)),
                       zero_skill_reference=support['w_exact'])
        elif tall == 0:
            out.update(mixture_regime='untied',
                       mixture_prediction=float(predict_tau_all(out['tau_positive'], support)),
                       zero_skill_reference=support['w_exact'] * np.sqrt(support['scoreable_pairs']/total))
    out['mixture_na_reason'] = ('simplified_mixture_assumptions_not_met'
                                 if out['mixture_regime'] == 'general_pair_accounting' else '')
    return out


def main():
    networks = ['ca-GrQc', 'ca-HepTh', 'email-Eu-core', 'facebook_combined', 'p2p-Gnutella08']
    rows, hashes = [], {}
    rule = 'Retrospective code-correctness check only: predicted_zero = (cached score == 0); no calibration or auxiliary mask'
    for net in networks:
        target_path, cache_path = Path(f'cache_targets_{net}.csv'), Path(f'cache_oof_{net}.npz')
        target = pd.read_csv(target_path).set_index('node')
        sweep_path = Path(f'sweep_{net}.csv')
        sweep = pd.read_csv(sweep_path).set_index(['target', 'radius', 'richness', 'seed'])
        assert sweep.index.is_unique
        # The writer persists vectors in target CSV order, without node IDs inside
        # NPZ. Hashes document this alignment assumption; they cannot prove history.
        assert target.index.is_unique and np.array_equal(target.index, np.arange(len(target)))
        y = target.betweenness.to_numpy()
        for path in [target_path, cache_path, sweep_path, Path('stage2_sweep.py'), Path('influence/experiment.py')]:
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(cache_path, allow_pickle=False) as cache:
            keys = [k for k in cache.files if k.startswith('betweenness|')]
            assert len(keys) == 160, (net, len(keys))
            for key in sorted(keys):
                _, radius, richness, seed = key.split('|')
                s = cache[key]
                row = report(y, s, predicted_zero=(s == 0), decision_provenance=rule)
                # A permutation or wrong cache-key interpretation can preserve all
                # dimensions. Agreement with the independently stored sweep metric
                # adds a numerical alignment check without refitting a single model.
                stored_tau = float(sweep.loc[('betweenness', int(radius), richness, int(seed)), 'kendall_tau'])
                row['sweep_tau_difference'] = row['tau_all'] - stored_tau
                assert abs(row['sweep_tau_difference']) < 1e-12, (net, key, 'sweep mismatch')
                rows.append(dict(network=net, cache_key=key, radius=int(radius), richness=richness,
                                 seed=int(seed), evidence='code-correctness check, not pilot evidence', **row))
    result = pd.DataFrame(rows)
    out = Path('results')
    out.mkdir(exist_ok=True)
    with (out/'results_c4_internal_smoke.csv').open('w', encoding='utf-8', newline='') as stream:
        stream.write('# Internal code-correctness check, not pilot evidence; retrospective score == 0 rule\n')
        result.to_csv(stream, index=False, na_rep='NA')
    summary = result.groupby('network').agg(rows=('cache_key', 'size'),
        finite_accuracy=('zero_accuracy', 'count'), finite_positive_tau=('tau_positive', 'count'),
        accuracy_min=('zero_accuracy', 'min'), accuracy_median=('zero_accuracy', 'median'),
        accuracy_max=('zero_accuracy', 'max'), tau_positive_min=('tau_positive', 'min'),
        tau_positive_median=('tau_positive', 'median'), tau_positive_max=('tau_positive', 'max'))
    text = ('C4 INTERNAL CODE-CORRECTNESS CHECK, NOT PILOT EVIDENCE\n' + rule + '\n'
            'Target: cached exact unnormalised betweenness; simple unweighted undirected LCC, endpoints excluded.\n'
            'Each row is one full 5-fold OOF vector: target|radius|richness|seed, not a fold.\n'
            'Medians below pool all 160 radius/richness/seed configurations per graph; no uncertainty claim.\n'
            + summary.to_string() + '\nMixture regimes:\n' + result.mixture_regime.value_counts().to_string()
            + f'\nMax absolute cached all-node tau minus sweep tau: {result.sweep_tau_difference.abs().max():.3e}\n')
    (out/'RESULTS_c4_internal_smoke.txt').write_text(text, encoding='utf-8')
    (out/'c4_internal_provenance.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
