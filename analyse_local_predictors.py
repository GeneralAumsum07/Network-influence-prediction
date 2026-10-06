"""Score registered L3 hypotheses; missing/tied evidence remains unscored.

RF scores use the existing full-4000-draw target and are descriptive references,
not a matched independent-half target experiment. No model is fitted here.
"""
import os
for _key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import kendalltau
import analyse
from probe_local_predictors import ROOT,TAGS,sha,atomic_json,stamp


def verdicts(networks):
    """Score network-level conjunctions without treating absent data as failures."""
    result = {'monotonic':{},'E1_beats_node':{},'RF_margin':{},'counter':{}}
    def check(row,keys,test):
        values = [row.get(k) for k in keys]
        if any(v is None or not np.isfinite(v) for v in values):
            return 'unscored'
        return 'supported' if test(*values) else 'not_supported'
    for tag in TAGS:
        row = networks.get(tag,{})
        result['monotonic'][tag] = check(row,['E1','E2','E3'],lambda a,b,c: b >= a-1e-12 and c >= b-1e-12)
        if tag in ('ca-GrQc','ca-HepTh','p2p-Gnutella08'):
            result['E1_beats_node'][tag] = check(row,['E1','node1'],lambda a,b:a>b)
        result['RF_margin'][tag] = check(row,['E2','E3','full2','full3'],lambda a,b,c,d:c-a >= .03 and d-b >= .03)
    comparisons = {tag:check(networks.get(tag,{}),['E3','full3'],lambda a,b:a>=b) for tag in TAGS}
    hits = sum(v=='supported' for v in comparisons.values())
    missing = sum(v=='unscored' for v in comparisons.values())
    counter = 'supported' if hits >= 4 else ('not_supported' if hits+missing < 4 else 'unscored')
    result['counter'] = {'verdict':counter,'networks_at_or_above':hits,'missing':missing,'network_verdicts':comparisons}
    return result


def tau(x,y):
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('nonfinite prediction/target')
    value = float(kendalltau(x,y).statistic)
    return value if np.isfinite(value) else None


def validate_configuration(tag, identity, meta):
    """Require the registered experiment, independently of a sidecar's hash."""
    expected = {'tag':tag, 'radii':[0,1,2,3], 'simulation_seed':0,
                'pilot_draws':0, 'threads':1,
                'split':{'predictor':[0,2000], 'target':[2000,4000]}}
    if meta.get('n_sims') != 4000 or meta.get('simulation_seed') != 0:
        raise ValueError(f'{tag}: incompatible simulation metadata')
    expected.update(p=meta.get('p'), convention=meta.get('convention'))
    if (not isinstance(expected['p'], (int,float)) or
            not np.isfinite(expected['p']) or not 0 <= expected['p'] <= 1 or
            expected['convention'] not in ('uniform','trivalency')):
        raise ValueError(f'{tag}: invalid transmission metadata')
    if any(identity.get(key) != value for key,value in expected.items()):
        raise ValueError(f'{tag}: incompatible L3 configuration')


def validate_saved_nodes(data, cache):
    """Bind row order to the expected network cache, including external IDs."""
    n = len(cache)
    if (not {'node','original_id'}.issubset(cache.columns) or
            not {'node','original_id','E','target'}.issubset(data.keys()) or
            not np.array_equal(cache['node'],np.arange(n)) or
            cache['original_id'].isna().any() or cache['original_id'].duplicated().any() or
            not np.array_equal(data['node'],cache['node']) or
            not np.array_equal(data['original_id'],cache['original_id']) or
            data['E'].shape != (n,4) or data['target'].shape != (n,)):
        raise ValueError('invalid predictor dimensions/node identity')
    for key in ('E','target','perc_reach_2','perc_reach_3'):
        if key in data:
            values = data[key]
            if (not np.issubdtype(values.dtype,np.number) or
                    not np.isfinite(values).all() or
                    (key.startswith('perc_reach_') and values.shape != (n,))):
                raise ValueError(f'invalid predictor array {key}')


def load_rf_reference(tag):
    """Validate raw rows before the historical loader can discard duplicates."""
    path = ROOT/f'sweep_{tag}.csv'
    before = sha(path)
    raw = pd.read_csv(path)
    required = {'target','radius','richness','seed','network','kendall_tau'}
    if not required.issubset(raw.columns):
        raise ValueError(f'{tag}: missing RF columns')
    raw = raw.loc[raw.target == 'spread_mean'].copy()
    if not raw.network.eq(tag).all() or raw.duplicated(['target','radius','richness','seed']).any():
        raise ValueError(f'{tag}: misfiled/duplicate RF spread records')
    # Tied predictions legitimately produce NaN rank correlations. Other missing
    # numbers, infinities and text are corruption, not permission to drop a seed.
    for column in raw.columns.difference(['target','richness','network']):
        try:
            values = pd.to_numeric(raw[column],errors='raise').to_numpy(dtype=float)
        except (ValueError,TypeError) as exc:
            raise ValueError(f'{tag}: malformed RF numeric {column}') from exc
        if np.isinf(values).any() or (column not in ('kendall_tau','spearman') and np.isnan(values).any()):
            raise ValueError(f'{tag}: nonfinite RF numeric {column}')
        if column in ('kendall_tau','spearman') and (np.abs(values[np.isfinite(values)]) > 1).any():
            raise ValueError(f'{tag}: invalid RF correlation {column}')
    rf = analyse.load(tag)
    # The digest brackets BOTH reads so a concurrent replacement cannot attach
    # one file's provenance to another file's scores.
    if sha(path) != before:
        raise ValueError(f'{tag}: RF reference changed during load')
    return rf.loc[rf.target == 'spread_mean'], before


def rf_cell_tau(rf, tier, radius, tag):
    cell = rf.loc[(rf.richness == tier)&(rf.radius == radius)]
    if cell.empty:
        return None
    if len(cell) != 10 or set(cell.seed) != set(range(10)):
        raise ValueError(f'{tag}: incomplete RF cell {tier}, radius {radius}')
    values = pd.to_numeric(cell.kendall_tau,errors='raise').to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError(f'{tag}: infinite RF tau')
    # Do not let pandas' skipna mean silently change the registered ten seeds.
    return None if np.isnan(values).any() else float(values.mean())


def run(out):
    coverage_path = ROOT/'results/coverage.csv'
    coverage = pd.read_csv(coverage_path)
    if coverage.duplicated(['network','radius']).any() or not np.isfinite(coverage.select_dtypes('number')).all().all():
        raise ValueError('invalid coverage records')
    all_rows, summary, statuses, hashes = [],{},{},{'coverage':sha(coverage_path)}
    for tag in TAGS:
        status_path = out/f'{tag}.json'
        if not status_path.exists():
            statuses[tag] = 'missing'
            continue
        status = json.loads(status_path.read_text())
        if status['status'] != 'complete':
            statuses[tag] = status['status']
            continue
        if status['pilot'] or status['verified_draws'] != 4000:
            raise ValueError('pilot/partial outputs cannot score preregistered claims')
        meta_path = ROOT/f'cache_meta_{tag}.json'
        meta = json.loads(meta_path.read_text())
        validate_configuration(tag,status['identity'],meta)
        expected_paths = {k:ROOT/f'cache_{k}_{tag}.{ext}' for k,ext in
                          [('meta','json'),('features','csv'),('targets','csv'),('cascades','npy')]}
        source = Path(meta['provenance']['source'])
        expected_paths['edgelist'] = source if source.is_absolute() else ROOT/source
        for name in ('influence/local_dynamics.py','influence/dynamics.py','influence/preprocessing.py','probe_local_predictors.py'):
            expected_paths[name] = ROOT/name
        inputs = status['identity']['inputs']
        if set(inputs) != set(expected_paths) or any(
                Path(inputs[k]['path']).resolve() != path.resolve() for k,path in expected_paths.items()):
            raise ValueError(f'{tag}: L3 inputs do not name the expected network caches')
        data_path = out/f'{tag}.npz'
        if sha(data_path) != status['output_sha256']:
            raise ValueError('prediction output hash mismatch')
        for item in status['identity']['inputs'].values():
            if sha(item['path']) != item['sha256']:
                raise ValueError('L3 input changed since prediction')
        hashes[tag] = {'predictions':sha(data_path),'status':sha(status_path)}
        rf, hashes[tag]['sweep'] = load_rf_reference(tag)
        row = {}
        for key,tier,r in [('node1','node',1),('full2',analyse.FULL,2),('full3',analyse.FULL,3)]:
            row[key] = rf_cell_tau(rf,tier,r,tag)
        with np.load(data_path,allow_pickle=False) as data:
            validate_saved_nodes(data,pd.read_csv(expected_paths['features']))
            for r in range(4):
                value = tau(data['E'][:,r],data['target'])
                row[f'E{r}'] = value
                all_rows.append({'network':tag,'radius':r,'predictor':f'E({r})','kendall_tau':value,'tau_status':'scored' if value is not None else 'unscored_tied',
                                 'rf_node_tau':row.get('node1') if r==1 else None,'rf_full_tau':row.get(f'full{r}')})
            for r in (2,3):
                key = f'perc_reach_{r}'
                if key in data:
                    value = tau(data[key],data['target'])
                    all_rows.append({'network':tag,'radius':r,'predictor':key,'kendall_tau':value,'tau_status':'scored' if value is not None else 'unscored_tied'})
        summary[tag] = row
        statuses[tag] = 'complete'
    report = {'created_utc':stamp(),'network_status':statuses,'network_results':summary,'verdicts':verdicts(summary),'hashes':hashes,
              'protocol_note':'E(r) draws 0..1999 vs target 2000..3999. RF uses historical full-draw targets; comparisons are descriptive. Radius 0 tied/unscored.'}
    if all_rows:
        frame = pd.DataFrame(all_rows)
        merged = frame.merge(coverage,on=['network','radius'],how='left',validate='many_to_one',indicator=True)
        if (merged['_merge'] != 'both').any():
            raise ValueError('missing network-radius coverage')
        merged = merged.drop(columns='_merge')
        tmp = out/'scores.csv.tmp'
        merged.to_csv(tmp,index=False)
        os.replace(tmp,out/'scores.csv')
    atomic_json(out/'analysis.json',report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    os.chdir(ROOT)  # analyse.load resolves the historical corpus from cwd.
    output = ROOT/'results/phase6_5_local'
    output.mkdir(parents=True,exist_ok=True)
    print(json.dumps(run(output),indent=2,allow_nan=False))
