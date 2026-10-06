"""Independent shortest-path fixtures for exact local IC dynamics."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import scipy.sparse as sp
from influence.preprocessing import Network
from influence.dynamics import simulate_ic_percolation, symmetric_edge_probabilities
from influence.local_dynamics import percolation_labels, truncated_cascade_sizes


def fixture(n, edges):
    a = np.zeros((n, n), dtype=bool)
    for u, v in edges:
        a[u, v] = a[v, u] = True
    return Network('fixture', sp.csr_matrix(a), [np.flatnonzero(r) for r in a],
                   a.sum(1), np.arange(n))


class ExactLocalTests(unittest.TestCase):
    def test_analysis_rejects_misfiled_and_changed_configuration(self):
        from analyse_local_predictors import validate_configuration
        meta = {'p':.1,'convention':'uniform','n_sims':4000,'simulation_seed':0}
        identity = {'tag':'ca-GrQc','p':.1,'convention':'uniform','simulation_seed':0,
                    'pilot_draws':0,'threads':1,'radii':[0,1,2,3],
                    'split':{'predictor':[0,2000],'target':[2000,4000]}}
        validate_configuration('ca-GrQc',identity,meta)
        for key,value in [('tag','ca-HepTh'),('radii',[1,2,3]),('simulation_seed',1),
                          ('split',{'predictor':[0,4000],'target':[0,4000]}),('p',.2),
                          ('convention','trivalency'),('pilot_draws',20),('threads',2)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_configuration('ca-GrQc',{**identity,key:value},meta)

    def test_analysis_rejects_other_original_ids(self):
        import pandas as pd
        from analyse_local_predictors import validate_saved_nodes
        cache = pd.DataFrame({'node':[0,1],'original_id':[11,22]})
        data = {'node':np.array([0,1]),'original_id':np.array([11,22]),
                'E':np.ones((2,4)),'target':np.ones(2)}
        validate_saved_nodes(data,cache)
        data['original_id'] = np.array([33,44])
        with self.assertRaises(ValueError):
            validate_saved_nodes(data,cache)

    def test_rf_ties_are_unscored_and_invalid_numeric_rejected(self):
        import pandas as pd
        from analyse_local_predictors import load_rf_reference, rf_cell_tau
        frame = pd.DataFrame({'target':['spread_mean']*10,'radius':[1]*10,
                              'richness':['node']*10,'seed':range(10),'network':['ca-GrQc']*10,
                              'kendall_tau':[float('nan')]*10,'spearman':[float('nan')]*10,
                              'fit_seconds':[1.]*10})
        with tempfile.TemporaryDirectory() as tmp, patch('analyse_local_predictors.ROOT',Path(tmp)):
            path = Path(tmp)/'sweep_ca-GrQc.csv'
            frame.to_csv(path,index=False)
            with patch('analyse_local_predictors.analyse.load',return_value=frame):
                rf,_ = load_rf_reference('ca-GrQc')
            self.assertIsNone(rf_cell_tau(rf,'node',1,'ca-GrQc'))
            for bad in [float('inf'),'garbage']:
                changed = frame.copy()
                changed['kendall_tau'] = bad
                changed.to_csv(path,index=False)
                with self.subTest(bad=bad),self.assertRaises(ValueError):
                    load_rf_reference('ca-GrQc')

    def test_rf_detects_change_during_load(self):
        import pandas as pd
        from analyse_local_predictors import load_rf_reference
        frame = pd.DataFrame({'target':['spread_mean'],'radius':[1],'richness':['node'],
                              'seed':[0],'network':['ca-GrQc'],'kendall_tau':[.5]})
        with tempfile.TemporaryDirectory() as tmp, patch('analyse_local_predictors.ROOT',Path(tmp)):
            path = Path(tmp)/'sweep_ca-GrQc.csv'
            frame.to_csv(path,index=False)
            def mutate(_tag):
                with path.open('a') as f:
                    f.write('\n')
                return frame
            with patch('analyse_local_predictors.analyse.load',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed'):
                load_rf_reference('ca-GrQc')

    def test_verdict_missing_and_ties(self):
        from analyse_local_predictors import verdicts
        report = verdicts({})
        self.assertEqual(report['counter']['verdict'],'unscored')
        self.assertEqual(report['monotonic']['ca-GrQc'],'unscored')
        rows = {tag:{'E1':.3,'E2':.4,'E3':.5,'node1':.2,'full2':.6,'full3':.55}
                for tag in ['ca-GrQc','ca-HepTh','p2p-Gnutella08','email-Eu-core','facebook_combined']}
        report = verdicts(rows)
        self.assertEqual(report['counter']['verdict'],'not_supported')
        self.assertEqual(report['RF_margin']['ca-GrQc'],'supported')
        for tag in rows:
            rows[tag]['full3'] = .5
        self.assertEqual(verdicts(rows)['counter']['verdict'],'supported')
        rows['ca-GrQc']['E1'] = None
        self.assertEqual(verdicts(rows)['monotonic']['ca-GrQc'],'unscored')

    def test_shortest_paths_and_production_rng(self):
        for net in [fixture(5, [(0,1),(1,2),(2,3),(3,4)]),
                    fixture(4, [(0,1),(1,2),(2,3),(3,0)]),
                    fixture(5, [(0,1),(0,2),(0,3),(0,4)]),
                    fixture(5, [(0,1),(2,3)]), fixture(1, [])]:
            for convention in ['uniform', 'trivalency']:
                for p in [0., .37, 1.]:
                    with self.subTest(n=net.n, convention=convention, p=p):
                        kw = dict(p=p, n_sims=8, convention=convention, seed=7)
                        labels = percolation_labels(net, **kw)
                        sizes = truncated_cascade_sizes(net, radii=range(6), **kw)
                        full = simulate_ic_percolation(net, verbose=False, **kw).sizes
                        np.testing.assert_array_equal(sizes[:, :, -1], full)
                        for m in range(8):
                            np.testing.assert_array_equal(np.bincount(labels[:,m])[labels[:,m]], full[:,m])
                        rng = np.random.default_rng(7)
                        u,v,probs = symmetric_edge_probabilities(net, convention,p,rng)
                        for m in range(8):
                            adj = [set() for _ in range(net.n)]
                            for x,y in zip(u[rng_live := rng.random(len(u)) < probs], v[rng_live]):
                                adj[x].add(y); adj[y].add(x)
                            for seed in range(net.n):
                                reached = {seed}
                                for r in range(6):
                                    self.assertEqual(sizes[seed,m,r],len(reached))
                                    reached |= {v for x in reached for v in adj[x]}
                        self.assertTrue((np.diff(sizes, axis=2) >= 0).all())
                        self.assertTrue((sizes[:,:,0] == 1).all())

    def test_invalid(self):
        net = fixture(3, [(0,1)])
        for kw in [dict(p=-.1),dict(p=float('nan')),dict(p=1.1),dict(n_sims=0),dict(n_sims=1.5),dict(convention='weighted'),dict(radii=[-1]),dict(radii=[1,1]),dict(radii=[.5])]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                truncated_cascade_sizes(net, **kw)


if __name__ == '__main__':
    unittest.main()
