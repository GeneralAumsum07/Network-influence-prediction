"""Phase 6.5 L2 zero-fit, full-draw non-backtracking baseline.

This runner only reads registered cache inputs and historical RF scores; it
performs no model fitting.  ``--pilot`` writes a separately labelled,
unscored single-network smoke output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

# This probe runs beside a fitted controller; set the process limit before
# importing NumPy/SciPy, when their native thread pools may be initialised.
for _key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from analyse_local_predictors import load_rf_reference, rf_cell_tau
from influence.nonbacktracking_local import nb_walk_counts
from influence.preprocessing import load_edgelist
from influence.sweep_inputs import check_source_identity

ROOT = Path(__file__).resolve().parent
TAGS = ('ca-GrQc', 'ca-HepTh', 'p2p-Gnutella08', 'email-Eu-core', 'facebook_combined')
OUT = ROOT / 'results' / 'phase6_5_nonbacktracking'


def sha(path: Path) -> str:
    with open(path, 'rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf8')
    os.replace(tmp, path)


def kendall_tau_b(predictor: np.ndarray, target: np.ndarray) -> float | None:
    """Return None for tied/undefined rankings; never silently drop rows."""
    if predictor.ndim != 1 or target.ndim != 1 or predictor.shape != target.shape:
        raise ValueError('predictor and target must be equally sized vectors')
    if not np.isfinite(predictor).all() or not np.isfinite(target).all():
        raise ValueError('nonfinite predictor or target')
    value = float(kendalltau(predictor, target).statistic)
    return value if np.isfinite(value) else None


def input_paths(tag: str, meta: dict) -> dict[str, Path]:
    source = Path(meta.get('provenance', {}).get('source', ''))
    source = source if source.is_absolute() else ROOT / source
    return {
        'meta': ROOT / f'cache_meta_{tag}.json',
        'features': ROOT / f'cache_features_{tag}.csv',
        'targets': ROOT / f'cache_targets_{tag}.csv',
        'registry': ROOT / f'cache_registry_{tag}.csv',
        'edgelist': source,
        'nonbacktracking_local': ROOT / 'influence' / 'nonbacktracking_local.py',
        'preprocessing': ROOT / 'influence' / 'preprocessing.py',
        'sweep_inputs': ROOT / 'influence' / 'sweep_inputs.py',
        'probe_nonbacktracking_local': ROOT / 'probe_nonbacktracking_local.py',
        'rf_helpers': ROOT / 'analyse_local_predictors.py',
        'analyse': ROOT / 'analyse.py',
        'sweep': ROOT / f'sweep_{tag}.csv',
        'provenance_audit': ROOT / 'cache_provenance_audit_20260911.json',
    }


def build_identity(tag: str, meta: dict) -> dict:
    paths = input_paths(tag, meta)
    if any(not path.is_file() for path in paths.values()):
        raise ValueError(f'{tag}: required input is missing')
    return {
        'tag': tag, 'configuration': {'target': 'spread_mean', 'draws': 4000, 'simulation_seed': 0,
                                      'convention': 'uniform', 'threads': 1, 'lengths': [1, 2, 3],
                                      'h_index_order': 3, 'rf_tier': 'node', 'rf_radius': 2},
        'inputs': {name: {'path': relative(path), 'sha256': sha(path)} for name, path in paths.items()},
        'imported_helpers': ['analyse_local_predictors.load_rf_reference', 'analyse_local_predictors.rf_cell_tau'],
    }


def validate_inputs(tag: str, meta: dict, net, features: pd.DataFrame,
                    targets: pd.DataFrame, registry: pd.DataFrame) -> None:
    """Bind all cache rows to the reloaded source graph before scoring it."""
    if (meta.get('n_sims') != 4000 or meta.get('simulation_seed') != 0 or
            meta.get('convention') != 'uniform' or not isinstance(meta.get('p'), (int, float)) or
            not np.isfinite(meta['p']) or not 0 <= meta['p'] <= 1):
        raise ValueError(f'{tag}: requires uniform seed-0 4000-draw metadata')
    if tag in TAGS:
        # Legacy cache metadata predates source hashes.  The read-only audit
        # sidecar binds its hash to this exact meta-file digest, so dimensions
        # and node IDs cannot accidentally bless a rewired same-size source.
        check_source_identity(tag, meta, root=ROOT)
    if meta.get('n') != net.n or meta.get('m') != net.m:
        raise ValueError(f'{tag}: source graph does not match cached dimensions')
    required_features = {'node', 'original_id', 'h_index_3'}
    if not required_features.issubset(features.columns) or not {'node', 'spread_mean'}.issubset(targets.columns):
        raise ValueError(f'{tag}: missing canonical feature or target columns')
    if 'feature' not in registry.columns or (registry.feature == 'h_index_3').sum() != 1:
        raise ValueError(f'{tag}: registry does not uniquely register h_index_3')
    expected_nodes = np.arange(net.n)
    for frame, label in ((features, 'features'), (targets, 'targets')):
        if (len(frame) != net.n or frame.node.duplicated().any() or
                not np.array_equal(frame.node.to_numpy(), expected_nodes) or
                not np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy()).all()):
            raise ValueError(f'{tag}: invalid canonical {label} rows')
    if (features.original_id.isna().any() or features.original_id.duplicated().any() or
            not np.array_equal(features.original_id.to_numpy(), net.original_ids)):
        raise ValueError(f'{tag}: feature original IDs do not match source graph')


def run_network(tag: str, out: Path, pilot: bool = False) -> dict:
    meta_path = ROOT / f'cache_meta_{tag}.json'
    meta = json.loads(meta_path.read_text(encoding='utf8'))
    paths = input_paths(tag, meta)
    identity = build_identity(tag, meta)
    status_path, data_path = out / f'{tag}.json', out / f'{tag}.npz'
    if status_path.exists():
        old = json.loads(status_path.read_text(encoding='utf8'))
        if old.get('identity') != identity:
            raise ValueError(f'{tag}: resume identity mismatch')
        if old.get('status') == 'complete':
            if not data_path.is_file() or sha(data_path) != old.get('output_sha256'):
                raise ValueError(f'{tag}: completed output is missing or corrupted')
            return old
    status = {'status': 'running', 'pilot': pilot, 'started_utc': stamp(), 'identity': identity}
    atomic_json(status_path, status)
    try:
        net = load_edgelist(paths['edgelist'], name=tag)
        features, targets, registry = (pd.read_csv(paths['features']), pd.read_csv(paths['targets']), pd.read_csv(paths['registry']))
        validate_inputs(tag, meta, net, features, targets, registry)
        counts = [nb_walk_counts(net, length) for length in (1, 2, 3)]
        target = targets.spread_mean.to_numpy(dtype=np.float64)
        h3 = features.h_index_3.to_numpy(dtype=np.float64)
        scores = {f'NB{length}': kendall_tau_b(value, target) for length, value in enumerate(counts, start=1)}
        scores['Hindex3'] = kendall_tau_b(h3, target)
        rf, _ = load_rf_reference(tag)
        scores['RFnode_r2_mean10'] = rf_cell_tau(rf, 'node', 2, tag)
        arrays = {'node': np.arange(net.n), 'original_id': net.original_ids, 'target': target, 'h_index_3': h3,
                  'nb_walks_1': counts[0], 'nb_walks_2': counts[1], 'nb_walks_3': counts[2]}
        if any(sha(paths[name]) != record['sha256'] for name, record in identity['inputs'].items()):
            raise ValueError(f'{tag}: input changed during run')
        tmp = data_path.with_suffix('.npz.tmp')
        with open(tmp, 'wb') as handle:
            np.savez_compressed(handle, **arrays)
        os.replace(tmp, data_path)
        status.update(status='complete', completed_utc=stamp(), output_sha256=sha(data_path), scores=scores,
                      radius_note='NB3 has information radius 2; cached H-index order 3 has radius 3.',
                      scoring_status='unscored_pilot' if pilot else 'ready_for_scoring')
        atomic_json(status_path, status)
        return status
    except Exception as exc:
        status.update(status='failed', completed_utc=stamp(), error=str(exc))
        atomic_json(status_path, status)
        raise


def score_verdict(scores: dict) -> dict:
    """Apply the registered comparisons without converting missing evidence to a no."""
    def check(keys, predicate):
        values = [scores.get(key) for key in keys]
        if any(value is None or not np.isfinite(value) for value in values):
            return 'unscored'
        return 'supported' if predicate(*values) else 'not_supported'
    return {
        'NB3_within_0_02_of_Hindex3': check(['NB3', 'Hindex3'], lambda nb, h3: abs(nb - h3) <= .02),
        'NB3_below_RFnode_r2_mean10': check(['NB3', 'RFnode_r2_mean10'], lambda nb, rf: nb < rf),
    }


def write_summary(out: Path) -> None:
    """Create the five-network scorecard only from complete, non-pilot records."""
    rows, statuses, hashes = {}, {}, {}
    for tag in TAGS:
        status_path = out / f'{tag}.json'
        if not status_path.is_file():
            statuses[tag] = 'missing'
            continue
        status = json.loads(status_path.read_text(encoding='utf8'))
        statuses[tag] = status.get('status', 'invalid')
        if status.get('status') != 'complete' or status.get('pilot'):
            continue
        meta = json.loads((ROOT / f'cache_meta_{tag}.json').read_text(encoding='utf8'))
        if status.get('identity') != build_identity(tag, meta):
            raise ValueError(f'{tag}: completed status identity no longer matches current inputs')
        data_path = out / f'{tag}.npz'
        if not data_path.is_file() or sha(data_path) != status.get('output_sha256'):
            raise ValueError(f'{tag}: summary found a corrupt completed output')
        paths = input_paths(tag, meta)
        net = load_edgelist(paths['edgelist'], name=tag)
        features, targets, registry = (pd.read_csv(paths['features']), pd.read_csv(paths['targets']),
                                       pd.read_csv(paths['registry']))
        validate_inputs(tag, meta, net, features, targets, registry)
        with np.load(data_path, allow_pickle=False) as data:
            expected_keys = {'node', 'original_id', 'target', 'h_index_3', 'nb_walks_1', 'nb_walks_2', 'nb_walks_3'}
            if set(data.files) != expected_keys or not np.array_equal(data['node'], np.arange(net.n)) or \
                    not np.array_equal(data['original_id'], net.original_ids) or \
                    not np.array_equal(data['target'], targets.spread_mean.to_numpy(dtype=np.float64)) or \
                    not np.array_equal(data['h_index_3'], features.h_index_3.to_numpy(dtype=np.float64)):
                raise ValueError(f'{tag}: saved arrays do not match canonical nodes or cache columns')
            counts = [nb_walk_counts(net, length) for length in (1, 2, 3)]
            if any(not np.array_equal(data[f'nb_walks_{length}'], counts[length - 1]) for length in (1, 2, 3)):
                raise ValueError(f'{tag}: saved non-backtracking counts do not recompute exactly')
            scores = {f'NB{length}': kendall_tau_b(counts[length - 1], data['target']) for length in (1, 2, 3)}
            scores['Hindex3'] = kendall_tau_b(data['h_index_3'], data['target'])
        rf, _ = load_rf_reference(tag)
        scores['RFnode_r2_mean10'] = rf_cell_tau(rf, 'node', 2, tag)
        if status.get('scores') != scores:
            raise ValueError(f'{tag}: saved score record does not recompute from validated inputs')
        rows[tag] = {'scores': scores, 'verdicts': score_verdict(scores)}
        hashes[tag] = {'status_sha256': sha(status_path), 'output_sha256': sha(data_path)}
    required = [rows.get(tag, {}).get('verdicts', {}) for tag in TAGS]
    universal_values = [item.get('NB3_within_0_02_of_Hindex3') for item in required]
    universal = ('supported' if universal_values and all(value == 'supported' for value in universal_values)
                 else 'not_supported' if all(value in ('supported', 'not_supported') for value in universal_values)
                 else 'unscored')
    below_values = [item.get('NB3_below_RFnode_r2_mean10') for item in required]
    universal_below = ('supported' if below_values and all(value == 'supported' for value in below_values)
                       else 'not_supported' if all(value in ('supported', 'not_supported') for value in below_values)
                       else 'unscored')
    counter_values = [rows.get(tag, {}).get('scores', {}) for tag in ('ca-GrQc', 'p2p-Gnutella08')]
    if any(not values for values in counter_values) or any(
            values.get('NB3') is None or values.get('RFnode_r2_mean10') is None for values in counter_values):
        counter = 'unscored'
    else:
        counter = ('supported' if all(values['NB3'] > values['RFnode_r2_mean10'] for values in counter_values)
                   else 'not_supported')
    report = {
        'created_utc': stamp(), 'network_status': statuses, 'network_results': rows, 'hashes': hashes,
        'verdicts': {'universal_NB3_within_0_02_of_Hindex3': universal,
                     'universal_NB3_below_RFnode_r2_mean10': universal_below,
                     'counter_NB3_strictly_beats_RFnode_r2_on_caGrQc_and_p2p': counter},
        'radius_note': 'NB3 information radius is 2; cached H-index order 3 radius is 3. This is a descriptive benchmark.',
        'reconstruction_gate': 'deferred; DERIVED_R2=0.999 requires the later registered HGB protocol after Stage 4.',
    }
    atomic_json(out / 'analysis.json', report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--networks', nargs='+', choices=TAGS, default=list(TAGS))
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    if len(set(args.networks)) != len(args.networks):
        parser.error('duplicate networks')
    if args.pilot and len(args.networks) != 1:
        parser.error('--pilot requires exactly one network')
    out = OUT / 'pilot' if args.pilot else OUT
    out.mkdir(parents=True, exist_ok=True)
    for tag in args.networks:
        print(json.dumps(run_network(tag, out, args.pilot), indent=2, allow_nan=False))
    if not args.pilot:
        write_summary(out)


if __name__ == '__main__':
    main()
