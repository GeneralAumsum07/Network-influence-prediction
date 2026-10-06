"""Fixture, determinism, and fail-closed checks for Phase 6.5 L7."""
from __future__ import annotations
import tempfile
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from influence.preprocessing import Network
from influence.branch_anisotropy import branch_anisotropy
from probe_branch_anisotropy import tails, contrast, run_network
def graph(n,edges,order=False):
    e=list(reversed(edges)) if order else edges; r=[a for a,b in e]+[b for a,b in e]; c=[b for a,b in e]+[a for a,b in e]; a=sp.csr_matrix((np.ones(len(r)),(r,c)),shape=(n,n)); a.sort_indices(); return Network('x',a,[a.indices[a.indptr[i]:a.indptr[i+1]] for i in range(n)],np.diff(a.indptr),np.arange(n))
def close(a,b):
    if not np.allclose(a,b): raise AssertionError((a,b))
def features():
    # diamond root 0: nodes 3 and 4 share (.5,.5); asymmetric root 0: three
    # shell nodes, one through parent1 and two through parent2 (.75,.25).
    d=graph(5,[(0,1),(0,2),(1,3),(2,3),(1,4),(2,4)]); m,h,e=branch_anisotropy(d); close([m[0],h[0]],[.5,np.log(2)]); assert not e[0]
    a=graph(7,[(0,1),(0,2),(1,3),(1,4),(1,5),(2,6)]); m,h,e=branch_anisotropy(a); close([m[0],h[0]],[.75,-.75*np.log(.75)-.25*np.log(.25)])
    for x in (graph(4,[(0,1),(0,2),(0,3)]),graph(3,[(0,1),(1,2),(2,0)]),graph(3,[])):
        m,h,e=branch_anisotropy(x); assert m[0]==0 and h[0]==0 and e[0]
    p=graph(6,[(0,1),(0,2),(1,3),(2,3),(1,4),(1,5)]); q=graph(6,[(0,1),(0,2),(1,5),(1,4),(2,3),(1,3)],True)
    for x,y in zip(branch_anisotropy(p),branch_anisotropy(q)): assert np.array_equal(x,y)
def logic():
    over,under,k=tails(np.array([0.,0.,1.,1.,2.,2.,3.,3.,4.,4.,5.,5.,6.,6.,7.,7.,8.,8.,9.,9.])); assert k==10 and not set(over)&set(under)
    effects,_,_=contrast({'x':np.arange(20.)},np.arange(20.)); assert effects['x']['cliffs_delta_under_minus_over']>0
def guards():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); (p/'ca-GrQc.json').write_text('{"status":"complete","identity":{"bad":true}}')
        try: run_network('ca-GrQc',p)
        except ValueError as e:
            if 'resume identity mismatch' not in str(e): raise
        else: raise AssertionError('corrupt resume accepted')
def main(): features(); logic(); guards(); print('branch anisotropy checks: ALL CHECKS PASSED')
if __name__=='__main__': main()
