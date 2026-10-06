"""Score L4 registered ratios; only complete, hash-validated full runs qualify."""
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import json
import numpy as np
import pandas as pd
from probe_seed_sets import BASE,ROOT,TAGS,TIERS,sha,atomic_json,stamp,validate_manifest


def radius_rule(curve):
    curve=np.asarray(curve,dtype=float)
    if curve.shape!=(4,) or not np.isfinite(curve).all() or curve[3]<=0: return None
    return int(np.flatnonzero(curve>=.98*curve[3])[0])


def verdicts(rows):
    def ratio(tag,test):
        value=rows.get(tag,{}).get('oracle_ratio')
        return 'unscored' if value is None else ('supported' if test(value) else 'not_supported')
    complete=set(rows)==set(TAGS)
    return {'facebook_oracle':ratio('facebook_combined',lambda x:x<.95),
            'p2p_oracle':ratio('p2p-Gnutella08',lambda x:x>.98),
            'stop':('supported' if all(rows[t]['oracle_ratio']>=.98 for t in TAGS) else 'not_supported') if complete else 'unscored',
            'RF_radius':{tier:('supported' if all(rows[t]['rf_radius'][tier]<=1 for t in TAGS) else 'not_supported') if complete else 'unscored' for tier in TIERS}}


def load_result(tag,out):
    path=out/f'{tag}.json'; data_path=out/f'{tag}.npz'
    status=json.loads(path.read_text())
    ident=status['identity']
    if status.get('status')!='complete' or status.get('pilot') or status.get('verified_draws')!=4000:
        raise ValueError('only completed full runs can score')
    if ident.get('tag')!=tag or ident.get('k')!=50 or ident.get('pilot_draws')!=0 or ident.get('threads')!=1 or ident.get('split')!={'train':[0,2000],'evaluation':[2000,4000]}:
        raise ValueError('incompatible L4 configuration')
    if sha(data_path)!=status['output_sha256']: raise ValueError('L4 output hash mismatch')
    required={k:f'cache_{k}_{tag}.{ext}' for k,ext in [('meta','json'),('features','csv'),('targets','csv'),('cascades','npy'),('oof','npz')]}
    validate_manifest(tag,ident['inputs'])
    features=pd.read_csv(ROOT/required['features'])
    with np.load(data_path,allow_pickle=False) as data:
        names=data['policy'].tolist(); seeds=data['seeds']; spread=data['spread']
        expected={'greedy','oracle_top_sigma','degree','degree_discount'}|{f'E|{r}' for r in range(4)}|{f'RF|spread_mean|{r}|{tier}|{s}' for tier in TIERS for r in range(4) for s in range(10)}
        if len(names)!=len(set(names)) or set(names)!=expected or seeds.shape!=(88,50) or spread.shape!=(88,2000): raise ValueError('policy grid/shape mismatch')
        if not np.array_equal(data['node'],features.node) or not np.array_equal(data['original_id'],features.original_id) or not np.array_equal(data['evaluation_draw'],np.arange(2000,4000)): raise ValueError('node/draw identity mismatch')
        n=len(features)
        if not np.issubdtype(seeds.dtype,np.integer) or seeds.min()<0 or seeds.max()>=n or any(len(set(row))!=50 for row in seeds): raise ValueError('invalid seed vectors')
        if not np.issubdtype(spread.dtype,np.integer) or spread.min()<50 or spread.max()>n: raise ValueError('invalid set spreads')
        return names,spread.copy(),status


def run(out=BASE):
    rows={}; tables=[]; hashes={}; states={}
    for tag in TAGS:
        path=out/f'{tag}.json'
        if not path.exists(): states[tag]='missing'; continue
        raw=json.loads(path.read_text())
        if raw['status']!='complete': states[tag]=raw['status']; continue
        names,spreads,status=load_result(tag,out)
        means={name:float(spreads[i].mean()) for i,name in enumerate(names)}
        row={'oracle_ratio':means['oracle_top_sigma']/means['greedy'],'rf_radius':{},'rf_seed_details':{}}
        for tier in TIERS:
            curves=np.array([[means[f'RF|spread_mean|{r}|{tier}|{s}'] for r in range(4)] for s in range(10)])
            radius=radius_rule(curves.mean(axis=0)); row['rf_radius'][tier]=radius
            per_seed=[radius_rule(curve) for curve in curves]
            row['rf_seed_details'][tier]={'mean_curve':curves.mean(axis=0).tolist(),'mean_curve_ratios':(curves.mean(axis=0)/curves[:,3].mean()).tolist(),'radii':per_seed,'ratios':(curves/curves[:,3,None]).tolist(),'disagreements_with_mean_radius':sum(r!=radius for r in per_seed)}
        rows[tag]=row; states[tag]='complete'
        hashes[tag]={'sidecar':sha(path),'npz':sha(path.with_suffix('.npz'))}
        for i,name in enumerate(names):
            paired=spreads[i]-spreads[names.index('greedy')]
            tables.append({'network':tag,'policy':name,'mean_spread':means[name],'ratio_to_greedy':means[name]/means['greedy'],'mean_paired_difference':float(paired.mean()),'sd_paired_difference':float(paired.std(ddof=1))})
    report={'created_utc':stamp(),'network_status':states,'network_results':rows,'verdicts':verdicts(rows),'input_hashes':hashes,'analysis_source_sha256':sha(__file__),
            'caveat':'RF OOF models trained on full-draw labels, including evaluation draws: descriptive policy comparison with target-noise reuse. Oracle means are train-half Monte Carlo. Greedy is not an exact optimum. RF seeds are summarized descriptively; no claim of independent replications.'}
    out.mkdir(parents=True,exist_ok=True)
    if tables:
        tmp=out/'scores.csv.tmp'; pd.DataFrame(tables).to_csv(tmp,index=False); os.replace(tmp,out/'scores.csv')
        report['scores_sha256']=sha(out/'scores.csv')
    atomic_json(out/'analysis.json',report)
    print(json.dumps(report['verdicts'],indent=2))
    return report


if __name__=='__main__': run()
