"""L3 zero-fit runner. Full draws are verified before a network is accepted.

Run from any cwd. Production output is results/phase6_5_local; --pilot-draws
uses an explicitly separate pilot directory and never supports scientific claims.
"""
import os
for _key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from influence.preprocessing import load_edgelist
from influence.local_dynamics import live_edge_draws, truncated_draw_sizes

ROOT = Path(__file__).resolve().parent
TAGS = ('ca-GrQc','ca-HepTh','p2p-Gnutella08','email-Eu-core','facebook_combined')


def sha(path):
    with open(path,'rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8')
    os.replace(tmp,path)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def peak_memory_bytes():
    """Process lifetime peak working set (includes native sparse allocations)."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('faults',wintypes.DWORD)] + [
                (name,ctypes.c_size_t) for name in ('peak','working','qpp','qp','qpnp','qnp','page','peakpage')]
        value = Counters()
        value.cb = ctypes.sizeof(value)
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        query = ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if not query(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return value.peak
    import resource
    import sys
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == 'darwin' else value*1024


def run_network(tag, out, pilot_draws=0):
    paths = {k:ROOT/f'cache_{k}_{tag}.{ext}' for k,ext in
             [('meta','json'),('features','csv'),('targets','csv'),('cascades','npy')]}
    meta = json.loads(paths['meta'].read_text())
    source = Path(meta['provenance']['source'])
    if not source.is_absolute():
        source = ROOT/source
    paths['edgelist'] = source
    for name in ('influence/local_dynamics.py','influence/dynamics.py','influence/preprocessing.py','probe_local_predictors.py'):
        paths[name] = ROOT/name
    identity = {'tag':tag,'inputs':{k:{'path':str(p.resolve()),'sha256':sha(p)} for k,p in paths.items()},
                'radii':[0,1,2,3], 'simulation_seed':meta['simulation_seed'],
                'p':meta['p'],'convention':meta['convention'], 'pilot_draws':pilot_draws,
                'split':{'predictor':[0, pilot_draws//2 if pilot_draws else 2000],
                         'target':[pilot_draws//2 if pilot_draws else 2000,pilot_draws or 4000]},
                'threads':1}
    status_path, data_path = out/f'{tag}.json', out/f'{tag}.npz'
    if status_path.exists():
        old = json.loads(status_path.read_text())
        if old['identity'] != identity:
            raise ValueError(f'{tag}: resume identity mismatch')
        if old['status'] == 'complete':
            if not data_path.exists() or sha(data_path) != old['output_sha256']:
                raise ValueError(f'{tag}: completed output corrupted/missing')
            return old
    status = {'identity':identity,'status':'running','started_utc':stamp(),'pilot':bool(pilot_draws)}
    atomic_json(status_path,status)
    t0 = time.perf_counter()
    try:
        if meta['n_sims'] != 4000 or meta['simulation_seed'] != 0:
            raise ValueError('L3 requires the registered 4000-draw seed-0 caches')
        net = load_edgelist(source)
        x,y = pd.read_csv(paths['features']),pd.read_csv(paths['targets'])
        for frame in (x,y):
            if len(frame) != net.n or frame.node.duplicated().any() or not np.array_equal(frame.node,np.arange(net.n)) or not np.isfinite(frame.to_numpy(dtype=float)).all():
                raise ValueError(f'{tag}: invalid/duplicate/nonfinite cache records')
        if not np.array_equal(x.original_id,net.original_ids) or meta['n'] != net.n or meta['m'] != net.m:
            raise ValueError(f'{tag}: source/cache node identity mismatch')
        cached = np.load(paths['cascades'],mmap_mode='r',allow_pickle=False)
        if cached.shape != (net.n,4000) or not np.issubdtype(cached.dtype,np.integer):
            raise ValueError('invalid cascade cache shape/dtype')
        draws = pilot_draws or 4000
        split = draws//2
        sums = np.zeros((net.n,4),dtype=np.float64)
        target = np.zeros(net.n,dtype=np.float64)
        for m,(g,labels) in enumerate(live_edge_draws(net,p=meta['p'],n_sims=draws,convention=meta['convention'],seed=meta['simulation_seed'])):
            full = np.bincount(labels)[labels]
            if not np.array_equal(full,cached[:,m]):
                raise ValueError(f'{tag}: cascade mismatch draw {m}')
            if m < split:
                sums += truncated_draw_sizes(g)
            else:
                target += full
            if (m+1)%200 == 0:
                print(f'{tag}: {m+1}/{draws} verified',flush=True)
        arrays = {'node':np.arange(net.n),'original_id':net.original_ids,
                  'E':sums/split,'target':target/(draws-split)}
        for column in ('perc_reach_2','perc_reach_3'):
            if column in x:
                arrays[column] = x[column].to_numpy()
        # Detect edits while running before publishing results under old hashes.
        if any(sha(paths[k]) != value['sha256'] for k,value in identity['inputs'].items()):
            raise ValueError('inputs changed during run')
        tmp = data_path.with_suffix('.npz.tmp')
        with open(tmp,'wb') as f:
            np.savez_compressed(f,**arrays)
        os.replace(tmp,data_path)
        elapsed = time.perf_counter()-t0
        status.update(status='complete',completed_utc=stamp(),seconds=elapsed,
                      verified_draws=draws,output_sha256=sha(data_path),
                      process_lifetime_peak_memory_bytes=peak_memory_bytes(),
                      estimated_full_seconds=elapsed*4000/draws,
                      memory_bound='256 x n sparse boolean reachability per draw; n x 4 accumulator; mmap full cache')
        atomic_json(status_path,status)
        print(f'{tag}: {elapsed:.3f}s ({draws} draws)',flush=True)
        return status
    except Exception as exc:
        status.update(status='failed',error=str(exc),completed_utc=stamp())
        atomic_json(status_path,status)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pilot-draws',type=int,default=0)
    ap.add_argument('--networks',nargs='+',choices=TAGS,default=list(TAGS))
    args = ap.parse_args()
    if args.pilot_draws and not 2 <= args.pilot_draws <= 20:
        ap.error('pilot draws must be 2..20')
    if len(set(args.networks)) != len(args.networks):
        ap.error('duplicate networks')
    out = ROOT/'results/phase6_5_local'
    if args.pilot_draws:
        out = out/f'pilot_{args.pilot_draws}'
    out.mkdir(parents=True,exist_ok=True)
    for tag in args.networks:
        run_network(tag,out,args.pilot_draws)


if __name__ == '__main__':
    main()
