"""Phase 6.5 L4: cached policies evaluated on paired held-out IC draws.

RF targets used all 4000 draws; their policy evaluation has target-noise reuse.
Greedy is a training-draw heuristic, not an optimal-set oracle.
"""
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import argparse
import hashlib
import json
import time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from influence.preprocessing import load_edgelist
from influence.local_dynamics import percolation_labels
from influence.seed_sets import greedy_seed_set,set_spread,top_k,degree_discount

ROOT=Path(__file__).resolve().parent
TAGS=('ca-GrQc','ca-HepTh','p2p-Gnutella08','email-Eu-core','facebook_combined')
TIERS=('node','node+edge+subgraph')
BASE=ROOT/'results/phase6_5_seed_sets'


def sha(path):
    with open(path,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def atomic_json(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8')
    os.replace(tmp,path)


def stamp(): return datetime.now(timezone.utc).isoformat()


def expected_paths(tag,pilot=False):
    paths={k:ROOT/f'cache_{k}_{tag}.{ext}' for k,ext in [('meta','json'),('features','csv'),('targets','csv'),('cascades','npy'),('oof','npz')]}
    meta=json.loads(paths['meta'].read_text())
    source=Path(meta['provenance']['source'])
    paths['edgelist']=(source if source.is_absolute() else ROOT/source).resolve()
    for name in ('influence/seed_sets.py','influence/local_dynamics.py','influence/dynamics.py','influence/preprocessing.py','probe_seed_sets.py','analyse_local_predictors.py'):
        paths[name]=ROOT/name
    if not pilot:
        for ext in ('json','npz'): paths['L3_'+ext]=ROOT/'results/phase6_5_local'/f'{tag}.{ext}'
    return paths


def validate_manifest(tag,manifest,pilot=False,check_hashes=True):
    paths=expected_paths(tag,pilot)
    if set(manifest)!=set(paths): raise ValueError('missing/unexpected provenance inputs')
    for key,path in paths.items():
        if manifest[key].get('path')!=path.relative_to(ROOT).as_posix(): raise ValueError('wrong provenance path')
        if check_hashes and sha(path)!=manifest[key].get('sha256'): raise ValueError('input hash mismatch')


def validate_oof(data,keys,n):
    """Check ZIP key multiplicity before numpy's mapping hides duplicates."""
    if len(keys)!=len(set(keys)): raise ValueError('duplicate OOF keys')
    expected={f'spread_mean|{r}|{tier}|{s}' for tier in TIERS for r in range(4) for s in range(10)}
    relevant=[key for key in keys if key.startswith('spread_mean|')]
    for key in relevant:
        parts=key.split('|')
        if len(parts)!=4 or parts[1] not in ('0','1','2','3') or parts[3] not in tuple(map(str,range(10))):
            raise ValueError('malformed spread OOF key')
    if not expected.issubset(keys): raise ValueError('missing required OOF cells')
    result={}
    for key in sorted(expected):
        value=np.asarray(data[key])
        if value.shape!=(n,) or not np.issubdtype(value.dtype,np.number) or not np.isfinite(value).all():
            raise ValueError('invalid OOF vector')
        result[key]=value
    return result


def load_local(tag,features,meta):
    from analyse_local_predictors import validate_configuration,validate_saved_nodes
    path=ROOT/'results/phase6_5_local'/f'{tag}.json'
    data_path=path.with_suffix('.npz')
    status=json.loads(path.read_text())
    if status.get('status')!='complete' or status.get('pilot') or status.get('verified_draws')!=4000 or sha(data_path)!=status.get('output_sha256'):
        raise ValueError('L3 incomplete or output corrupted')
    validate_configuration(tag,status['identity'],meta)
    # Scientific caches must still match. Source hashes remain historical: an
    # unrelated subsequent helper edit must not relabel an already valid run.
    expected=expected_paths(tag)
    for key in ('meta','features','targets','cascades','edgelist'):
        item=status['identity']['inputs'][key]
        if Path(item['path']).resolve()!=expected[key].resolve() or sha(expected[key])!=item['sha256']:
            raise ValueError('L3 scientific input changed/misidentified')
    with np.load(data_path,allow_pickle=False) as data:
        validate_saved_nodes(data,features)
        return data['E'].copy(),status['identity']


def run_network(tag,out,pilot_draws=0):
    if pilot_draws and (not isinstance(pilot_draws,int) or not 2<=pilot_draws<=20 or pilot_draws%2):
        raise ValueError('pilot must be even, 2..20')
    paths=expected_paths(tag,bool(pilot_draws))
    meta=json.loads(paths['meta'].read_text())
    source=Path(meta['provenance']['source']); source=source if source.is_absolute() else ROOT/source
    paths['edgelist']=source
    identity={'tag':tag,'k':50,'pilot_draws':pilot_draws,'split':{'train':[0,pilot_draws//2 if pilot_draws else 2000], 'evaluation':[pilot_draws//2 if pilot_draws else 2000,pilot_draws or 4000]},'threads':1,
              'inputs':{key:{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for key,p in paths.items()}}
    status_path=out/f'{tag}.json'; data_path=out/f'{tag}.npz'
    if status_path.exists():
        old=json.loads(status_path.read_text())
        if old['identity']!=identity: raise ValueError('resume identity mismatch')
        if old['status']=='complete':
            if sha(data_path)!=old['output_sha256']: raise ValueError('completed output corrupted')
            return old
    elif data_path.exists(): raise ValueError('orphan output without provenance')
    status={'identity':identity,'status':'running','started_utc':stamp(),'pilot':bool(pilot_draws)}
    atomic_json(status_path,status); started=time.perf_counter()
    try:
        if meta['n_sims']!=4000 or meta['simulation_seed']!=0 or meta['convention']!='uniform':
            raise ValueError('requires registered uniform seed-0 4000-draw experiment')
        net=load_edgelist(source); features=pd.read_csv(paths['features']); targets=pd.read_csv(paths['targets'])
        for frame in (features,targets):
            if len(frame)!=net.n or not np.array_equal(frame.node,np.arange(net.n)) or not np.isfinite(frame.to_numpy(dtype=float)).all():
                raise ValueError('cache nodes/numeric values invalid')
        if not np.array_equal(features.original_id,net.original_ids) or meta['n']!=net.n or meta['m']!=net.m:
            raise ValueError('graph/cache identity mismatch')
        draws=pilot_draws or 4000; split=draws//2
        labels=percolation_labels(net,p=meta['p'],n_sims=draws,convention=meta['convention'],seed=0)
        cached=np.load(paths['cascades'],mmap_mode='r',allow_pickle=False)
        if cached.shape!=(net.n,4000) or not np.issubdtype(cached.dtype,np.integer): raise ValueError('invalid cascade cache')
        for d in range(draws):
            if not np.array_equal(np.bincount(labels[:,d])[labels[:,d]],cached[:,d]):
                raise ValueError(f'cascade mismatch draw {d}')
        with np.load(paths['oof'],allow_pickle=False) as data: predictions=validate_oof(data,data.files,net.n)
        train=labels[:,:split]; evaluation=labels[:,split:]
        greedy,gains=greedy_seed_set(train,50)
        sigma=np.mean(cached[:,:split],axis=1)
        policies={'greedy':greedy,'oracle_top_sigma':top_k(sigma,50),'degree':top_k(np.diff(net.adj.indptr),50),'degree_discount':degree_discount(net.adj,50,meta['p'])}
        for key,values in predictions.items(): policies['RF|'+key]=top_k(values,50)
        if not pilot_draws:
            E,history=load_local(tag,features,meta)
            # Local run identity contains legacy absolute paths. Preserve hashes
            # and configuration only in this new repository output.
            status['L3_historical_identity']={k:v for k,v in history.items() if k!='inputs'}
            status['L3_historical_input_hashes']={k:v['sha256'] for k,v in history['inputs'].items()}
            for r in range(4): policies[f'E|{r}']=top_k(E[:,r],50)
        names=list(policies)
        seeds=np.stack([policies[name] for name in names])
        spread=np.stack([set_spread(evaluation,policy) for policy in seeds])
        if any(sha(paths[k])!=item['sha256'] for k,item in identity['inputs'].items()): raise ValueError('inputs changed during run')
        tmp=data_path.with_suffix('.npz.tmp')
        with open(tmp,'wb') as f:
            np.savez_compressed(f,node=np.arange(net.n),original_id=net.original_ids,policy=np.asarray(names),seeds=seeds,spread=spread,greedy_gains=gains,evaluation_draw=np.arange(split,draws))
        os.replace(tmp,data_path)
        status.update(status='complete',completed_utc=stamp(),seconds=time.perf_counter()-started,verified_draws=draws,output_sha256=sha(data_path),
                      caveat='RF cached training targets use both draw halves; oracle-top-sigma uses training-half Monte Carlo means; greedy is not an exact optimum. Pilot omits E and cannot score claims.')
        atomic_json(status_path,status)
        print(f'{tag}: {status["seconds"]:.3f}s; {draws} exact draws; {len(names)} policies',flush=True)
        return status
    except Exception as exc:
        status.update(status='failed',error=str(exc),completed_utc=stamp()); atomic_json(status_path,status); raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-draws',type=int,default=0)
    parser.add_argument('--networks',nargs='+',choices=TAGS,default=list(TAGS))
    args=parser.parse_args()
    if args.pilot_draws and (not 2<=args.pilot_draws<=20 or args.pilot_draws%2): parser.error('pilot must be even, 2..20')
    if len(set(args.networks))!=len(args.networks): parser.error('duplicate networks')
    # Keep earlier pilots immutable when implementation changes: new pilot output
    # gets a source-hash suffix; normal full-run resume remains fail-closed.
    suffix=sha(__file__)[:12]
    out=BASE/f'pilot_{args.pilot_draws}_{suffix}' if args.pilot_draws else BASE
    out.mkdir(parents=True,exist_ok=True)
    for tag in args.networks: run_network(tag,out,args.pilot_draws)


if __name__=='__main__': main()
