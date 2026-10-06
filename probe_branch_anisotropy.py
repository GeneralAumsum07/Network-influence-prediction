"""Phase 6.5 L7 zero-fit branch anisotropy and residual-tail probe."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
for _k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[_k] = '1'
import numpy as np
import pandas as pd
from analyse_failures import pct_rank, mean_delta, standardise_residual, cliffs_delta
from influence.branch_anisotropy import branch_anisotropy
from influence.preprocessing import load_edgelist
from influence.sweep_inputs import check_source_identity, recorded_source_sha256

ROOT=Path(__file__).resolve().parent
TAGS=('ca-GrQc','ca-HepTh','p2p-Gnutella08','email-Eu-core','facebook_combined')
OUT=ROOT/'results'/'phase6_5_anisotropy'
FULL='node+edge+subgraph'
def sha(p):
    with open(p,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def rel(p): return p.resolve().relative_to(ROOT.resolve()).as_posix()
def stamp(): return datetime.now(timezone.utc).isoformat()
def atomic_json(p,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf8'); os.replace(t,p)
def atomic_npz(p,**x):
    t=p.with_suffix(p.suffix+'.tmp')
    with open(t,'wb') as f: np.savez_compressed(f,**x)
    os.replace(t,p)
def paths(tag,meta):
    source=Path(meta.get('provenance',{}).get('source','')); source=source if source.is_absolute() else ROOT/source
    return {'meta':ROOT/f'cache_meta_{tag}.json','features':ROOT/f'cache_features_{tag}.csv','targets':ROOT/f'cache_targets_{tag}.csv','reported_oof':ROOT/'estimators'/f'cache_oof_{tag}__rf_log1p.npz','raw_oof':ROOT/f'cache_oof_{tag}.npz','edgelist':source,'source_audit':ROOT/'cache_provenance_audit_20260911.json','branch_anisotropy':ROOT/'influence'/'branch_anisotropy.py','probe':ROOT/'probe_branch_anisotropy.py','analyse_failures':ROOT/'analyse_failures.py','sweep_inputs':ROOT/'influence'/'sweep_inputs.py'}
def identity(tag,meta):
    ps=paths(tag,meta)
    if any(not p.is_file() for p in ps.values()): raise ValueError(f'{tag}: required input missing')
    h,origin=recorded_source_sha256(tag,meta,ROOT)
    if not h: raise ValueError(f'{tag}: absent recorded source hash; refusing unbound cache')
    return {'tag':tag,'configuration':{'threads':1,'radius':3,'richness':FULL,'seeds':list(range(10)),'primary':'reported_rf_log1p_betweenness','sensitivities':['raw_betweenness','spread_mean'],'tail_fraction':.05,'tie_rule':'ascending np.lexsort((node, adjusted_delta))'},'recorded_source_sha256':h,'source_hash_origin':origin,'inputs':{k:{'path':rel(v),'sha256':sha(v)} for k,v in ps.items()}}
def validate(tag,meta,net,features,targets):
    if meta.get('n')!=net.n or meta.get('m')!=net.m: raise ValueError(f'{tag}: graph/cache dimensions mismatch')
    check_source_identity(tag,meta,ROOT)
    needed={'node','original_id'}
    if not needed<=set(features) or not {'node','betweenness','spread_mean'}<=set(targets): raise ValueError(f'{tag}: required cache columns missing')
    for x,name in ((features,'features'),(targets,'targets')):
        if len(x)!=net.n or x.node.duplicated().any() or not np.array_equal(x.node.to_numpy(),np.arange(net.n)): raise ValueError(f'{tag}: invalid {name} nodes')
    if features.original_id.duplicated().any() or not np.array_equal(features.original_id.to_numpy(),net.original_ids): raise ValueError(f'{tag}: original ids mismatch')
    if not np.isfinite(targets[['betweenness','spread_mean']].to_numpy(float)).all(): raise ValueError(f'{tag}: nonfinite targets')
def residual(oof_path,target,y):
    with np.load(oof_path,allow_pickle=False) as d:
        keys=[f'{target}|3|{FULL}|{s}' for s in range(10)]
        if set(keys)-set(d.files): raise ValueError(f'{oof_path.name}: incomplete distinct ten-seed OOF keys')
        oof={k:np.asarray(d[k],dtype=float) for k in keys}
    n=len(y)
    if any(v.shape!=(n,) or not np.isfinite(v).all() for v in oof.values()): raise ValueError('invalid OOF vector')
    delta,per=mean_delta(oof,target,3,y)
    if delta is None or per.shape!=(10,n): raise ValueError('invalid residual aggregation')
    return standardise_residual(delta,pct_rank(y)), delta
def tails(adjusted):
    n=len(adjusted); k=max(10,round(.05*n))
    if 2*k>n: raise ValueError('tails would overlap')
    idx=np.lexsort((np.arange(n),adjusted))
    return idx[:k],idx[-k:],k
def contrast(features,adjusted):
    over,under,k=tails(adjusted); rows={}
    for name,values in features.items():
        d,p=cliffs_delta(values[under],values[over])
        rows[name]={'cliffs_delta_under_minus_over':None if not np.isfinite(d) else float(d),'p_value':None if not np.isfinite(p) else float(p),'under_n':k,'over_n':k}
    return rows,over,under
def run_network(tag,out,pilot=False):
    meta=json.loads((ROOT/f'cache_meta_{tag}.json').read_text()); ident=identity(tag,meta); statusp=out/f'{tag}.json'; datap=out/f'{tag}.npz'
    if statusp.exists():
        old=json.loads(statusp.read_text())
        if old.get('identity')!=ident: raise ValueError(f'{tag}: resume identity mismatch')
        if old.get('status')=='complete':
            if not datap.is_file() or sha(datap)!=old.get('output_sha256'): raise ValueError(f'{tag}: corrupt completed output')
            return old
    status={'status':'running','pilot':pilot,'started_utc':stamp(),'identity':ident}; atomic_json(statusp,status)
    try:
        ps=paths(tag,meta); net=load_edgelist(ps['edgelist'],name=tag); f=pd.read_csv(ps['features']); y=pd.read_csv(ps['targets']); validate(tag,meta,net,f,y)
        maximum,entropy,empty=branch_anisotropy(net); feat={'max_branch_share':maximum,'branch_entropy_nats':entropy}
        output={'node':np.arange(net.n),'original_id':net.original_ids,'max_branch_share':maximum,'branch_entropy_nats':entropy,'empty_shell2':empty.astype(np.uint8)}; results={}; alltails={}
        arms=[('primary_reported_betweenness',ps['reported_oof'],'betweenness'),('sensitivity_raw_betweenness',ps['raw_oof'],'betweenness'),('sensitivity_spread_mean',ps['raw_oof'],'spread_mean')]
        for arm,path,target in arms:
            adj,raw=residual(path,target,y[target].to_numpy(float)); effects,over,under=contrast(feat,adj); results[arm]={'status':'scored','target':target,'objective_arm':'rf_log1p' if arm.startswith('primary') else 'raw','effects':effects}; output[f'adjusted_delta_{arm}']=adj; output[f'raw_delta_{arm}']=raw; output[f'over_indices_{arm}']=over; output[f'under_indices_{arm}']=under
        if any(sha(ps[k])!=r['sha256'] for k,r in ident['inputs'].items()): raise ValueError(f'{tag}: input changed during run')
        atomic_npz(datap,**output); status.update(status='complete',completed_utc=stamp(),output_sha256=sha(datap),arms=results,empty_shell2_count=int(empty.sum()),scoring_status='unscored_pilot' if pilot else 'ready_for_scoring'); atomic_json(statusp,status); return status
    except Exception as e:
        status.update(status='failed',completed_utc=stamp(),error=str(e)); atomic_json(statusp,status); raise
def summary(out):
    networks={}; hashes={}; eligible=[]
    for tag in TAGS:
        sp=out/f'{tag}.json'
        if not sp.is_file(): networks[tag]={'status':'missing'}; continue
        s=json.loads(sp.read_text()); networks[tag]=s
        if s.get('status')!='complete' or s.get('pilot'): continue
        meta=json.loads((ROOT/f'cache_meta_{tag}.json').read_text()); ident=identity(tag,meta)
        if s.get('identity')!=ident: raise ValueError(f'{tag}: summary identity mismatch')
        dp=out/f'{tag}.npz'
        if not dp.is_file() or sha(dp)!=s.get('output_sha256'): raise ValueError(f'{tag}: summary output corruption')
        primary=s['arms'].get('primary_reported_betweenness')
        if not primary or primary.get('status')!='scored': continue
        vals=[x['cliffs_delta_under_minus_over'] for x in primary['effects'].values()]
        if any(v is None for v in vals): continue
        eligible.append(tag); hashes[tag]={'status_sha256':sha(sp),'output_sha256':sha(dp)}
    hits=sum(max(abs(v) for v in networks[t]['arms']['primary_reported_betweenness']['effects'].values() if v['cliffs_delta_under_minus_over'] is not None)>.2 for t in eligible)
    verdict='supported' if hits>=3 else ('not_supported' if hits+(5-len(eligible))<3 else 'unscored')
    atomic_json(out/'analysis.json',{'created_utc':stamp(),'network_results':networks,'hashes':hashes,'primary_prediction':{'status':verdict,'qualified_networks':hits,'scored_primary_networks':len(eligible),'rule':'max(abs(d)) across max_branch_share and branch_entropy_nats > 0.2; support >=3/5'},'reconstruction_gate':'DEFERRED: no model fitting; R2 gate awaits Stage4.'})
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--networks',nargs='+',choices=TAGS,default=list(TAGS)); ap.add_argument('--pilot',action='store_true'); a=ap.parse_args()
    if len(set(a.networks))!=len(a.networks): ap.error('duplicate networks')
    if a.pilot and len(a.networks)!=1: ap.error('--pilot requires exactly one network')
    out=OUT/'pilot' if a.pilot else OUT; out.mkdir(parents=True,exist_ok=True)
    for tag in a.networks: print(json.dumps(run_network(tag,out,a.pilot),indent=2,allow_nan=False))
    if not a.pilot: summary(out)
if __name__=='__main__': main()
