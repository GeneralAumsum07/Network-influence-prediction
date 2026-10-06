"""Independent tiny-graph oracles for Phase 6.5 L4; never fits a model."""
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import unittest
import numpy as np
from influence.seed_sets import set_spread, greedy_seed_set, top_k


def oracle(labels, seeds):
    return np.array([sum(any(labels[i,d] == labels[s,d] for s in seeds)
                         for i in range(len(labels))) for d in range(labels.shape[1])])


class SeedSets(unittest.TestCase):
    def test_resume_and_corruption(self):
        import tempfile
        import json
        from pathlib import Path
        from probe_seed_sets import run_network
        from analyse_seed_sets import load_result
        # Two draws are an execution fixture, never a scientific result. Its
        # exact output must resume, reject altered configuration, reject bytes,
        # and remain ineligible for the full-corpus scorer.
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            first=run_network('ca-GrQc',out,2)
            self.assertEqual(run_network('ca-GrQc',out,2),first)
            with self.assertRaises(ValueError): load_result('ca-GrQc',out)
            # Build an explicitly synthetic full-shaped serialization fixture.
            # It exercises the real scorer validation without running 4000 draws.
            from probe_seed_sets import expected_paths,ROOT,sha
            with np.load(out/'ca-GrQc.npz') as saved:
                arrays={key:saved[key] for key in saved.files}
            arrays['policy']=np.concatenate([arrays['policy'],[f'E|{r}' for r in range(4)]])
            arrays['seeds']=np.concatenate([arrays['seeds'],arrays['seeds'][:4]])
            arrays['spread']=np.repeat(np.concatenate([arrays['spread'],arrays['spread'][:4]]),2000,axis=1)
            arrays['evaluation_draw']=np.arange(2000,4000)
            fixture=json.loads(json.dumps(first))
            fixture.update(pilot=False,verified_draws=4000)
            fixture['identity'].update(pilot_draws=0,split={'train':[0,2000],'evaluation':[2000,4000]})
            fixture['identity']['inputs']={k:{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for k,p in expected_paths('ca-GrQc').items()}
            fixture_out=out/'fixture'; fixture_out.mkdir()
            fixture_path=fixture_out/'ca-GrQc.npz'
            def publish():
                np.savez(fixture_path,**arrays)
                fixture['output_sha256']=sha(fixture_path)
                (fixture_out/'ca-GrQc.json').write_text(json.dumps(fixture))
            publish()
            self.assertEqual(len(load_result('ca-GrQc',fixture_out)[0]),88)
            arrays['node']=arrays['node'][::-1]; publish()
            with self.assertRaises(ValueError): load_result('ca-GrQc',fixture_out)
            arrays['node']=arrays['node'][::-1]
            arrays['seeds'][0,1]=arrays['seeds'][0,0]; publish()
            with self.assertRaises(ValueError): load_result('ca-GrQc',fixture_out)
            with open(fixture_path,'ab') as stream: stream.write(b'corruption')
            with self.assertRaises(ValueError): load_result('ca-GrQc',fixture_out)
            path=out/'ca-GrQc.json'
            bad=json.loads(path.read_text()); bad['identity']['k']=49
            path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): run_network('ca-GrQc',out,2)
            path.write_text(json.dumps(first))
            with open(out/'ca-GrQc.npz','ab') as stream: stream.write(b'corruption')
            with self.assertRaises(ValueError): run_network('ca-GrQc',out,2)

    def test_manifest_fail_closed(self):
        from probe_seed_sets import expected_paths,validate_manifest,ROOT
        paths=expected_paths('ca-GrQc',False)
        manifest={k:{'path':p.relative_to(ROOT).as_posix(),'sha256':'x'} for k,p in paths.items()}
        validate_manifest('ca-GrQc',manifest,False,check_hashes=False)
        for key in ('edgelist','L3_json','influence/seed_sets.py'):
            bad=dict(manifest); bad.pop(key)
            with self.assertRaises(ValueError): validate_manifest('ca-GrQc',bad,False,check_hashes=False)
        bad=dict(manifest); bad['oof']={'path':'cache_oof_other.npz','sha256':'x'}
        with self.assertRaises(ValueError): validate_manifest('ca-GrQc',bad,False,check_hashes=False)

    def test_degree_discount_oracle(self):
        from influence.seed_sets import degree_discount
        import scipy.sparse as sp
        a=np.array([[0,1,1,1,0],[1,0,1,0,0],[1,1,0,0,1],[1,0,0,0,0],[0,0,1,0,0]])
        for p in (0,.03,1):
            selected=[]
            for k in range(1,6):
                def score(i):
                    d=int(a[i].sum()); t=sum(a[i,j] for j in selected)
                    return d-2*t-(d-t)*t*p
                selected.append(min((i for i in range(5) if i not in selected),key=lambda i:(-score(i),i)))
                self.assertEqual(degree_discount(sp.csr_matrix(a),k,p).tolist(),selected)

    def test_oof_validation(self):
        from probe_seed_sets import validate_oof
        keys=[f'spread_mean|{r}|{tier}|{s}' for tier in ('node','node+edge+subgraph') for r in range(4) for s in range(10)]
        data={key:np.arange(4,dtype=float) for key in keys}
        self.assertEqual(len(validate_oof(data,keys,4)),80)
        for bad in (keys+keys[:1],keys[:-1],keys+['spread_mean|oops']):
            with self.assertRaises(ValueError): validate_oof(data,bad,4)
        data[keys[0]]=np.array([np.nan]*4)
        with self.assertRaises(ValueError): validate_oof(data,keys,4)

    def test_scoring_boundaries(self):
        from analyse_seed_sets import verdicts, radius_rule
        self.assertEqual(radius_rule([98,99,99,100]),0)
        self.assertEqual(radius_rule([97,98,99,100]),1)
        self.assertEqual(verdicts({})['stop'],'unscored')
        rows={t:{'oracle_ratio':.98,'rf_radius':{'node':1,'node+edge+subgraph':1}} for t in ('ca-GrQc','ca-HepTh','p2p-Gnutella08','email-Eu-core','facebook_combined')}
        self.assertEqual(verdicts(rows)['stop'],'supported')
        self.assertEqual(verdicts(rows)['p2p_oracle'],'not_supported')
        rows['facebook_combined']['oracle_ratio']=.95
        self.assertEqual(verdicts(rows)['facebook_oracle'],'not_supported')

    def test_union(self):
        labels = np.array([[0,0],[0,1],[1,1],[2,2]])
        for seeds in ([],[0],[0,1],[1,3],list(range(4))):
            np.testing.assert_array_equal(set_spread(labels,seeds),oracle(labels,seeds))

    def test_exhaustive_greedy(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            labels = rng.integers(0,4,size=(7,5))
            selected=[]
            for k in range(1,8):
                values=[(-oracle(labels,selected+[i]).sum(),i) for i in range(7) if i not in selected]
                selected.append(min(values)[1])
                got,gains=greedy_seed_set(labels,k)
                self.assertEqual(list(got),selected)
                self.assertTrue(np.all(np.diff(gains)<=0))

    def test_edges_and_ties(self):
        labels=np.arange(4)[:,None]
        self.assertEqual(list(top_k(np.ones(4),3)),[0,1,2])
        self.assertEqual(list(greedy_seed_set(labels,0)[0]),[])
        for k in (-1,5,1.5,True):
            with self.assertRaises(ValueError): greedy_seed_set(labels,k)
        with self.assertRaises(ValueError): set_spread(labels,[1,1])
        with self.assertRaises(ValueError): top_k([1,np.nan],1)

    def test_split_independence(self):
        train=np.array([[0,0],[0,1],[2,1],[3,3]])
        chosen=greedy_seed_set(train,2)[0]
        evaluation=np.zeros((4,2),dtype=int)
        np.testing.assert_array_equal(set_spread(evaluation,chosen),[4,4])
        np.testing.assert_array_equal(chosen,greedy_seed_set(train.copy(),2)[0])


if __name__ == '__main__': unittest.main(verbosity=2)
