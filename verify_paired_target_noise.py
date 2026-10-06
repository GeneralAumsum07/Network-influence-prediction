"""Focused arithmetic/integrity tests; no models, targets, or simulations run."""
import importlib.util
import math
import unittest

import numpy as np
import pandas as pd


class PairedNoiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A missing implementation is deliberately represented as a failed
        # assertion so the first red run identifies the absent functionality.
        cls.available = importlib.util.find_spec('analyse_paired_target_noise') is not None
        if cls.available:
            import analyse_paired_target_noise
            cls.mod = analyse_paired_target_noise

    def setUp(self):
        self.assertTrue(self.available, 'paired-noise analysis implementation is absent')

    def test_key_alignment_survives_scrambled_row_order(self):
        # Positional subtraction would turn these into different gains.
        d = pd.DataFrame([(i, r, i / 10 + r / 100) for i in range(3)
                          for r in range(4)], columns=['rep', 'radius', 'tau'])
        mat = self.mod.paired_matrix(d.sample(frac=1, random_state=7), 'rep', 'tau', 3)
        np.testing.assert_allclose(mat[1] - mat[0], [.01, .01, .01])

    def test_missing_duplicate_extra_and_nonfinite_pairs_are_rejected(self):
        d = pd.DataFrame([(i, r, .1) for i in range(3) for r in range(4)],
                         columns=['rep', 'radius', 'tau'])
        bad_frames = [d.iloc[:-1], pd.concat([d, d.iloc[:1]]),
                      pd.concat([d, pd.DataFrame([(3, 0, .1)], columns=d.columns)])]
        bad = d.copy()
        bad.loc[0, 'tau'] = np.nan
        bad_frames.append(bad)
        for bad in bad_frames:
            with self.subTest(rows=len(bad)):
                with self.assertRaises(ValueError):
                    self.mod.paired_matrix(bad, 'rep', 'tau', 3)

    def test_shared_noise_cancels_exactly(self):
        # An unpaired variance sum would be 2, but paired variance is zero.
        s = self.mod.pair_summary(np.array([0., 1., 2.]), np.array([1., 2., 3.]))
        self.assertEqual(s['sd'], 0.)
        self.assertEqual(s['mean'], 1.)
        self.assertEqual(s['covariance'], 1.)
        self.assertEqual(s['variance_identity'], 0.)
        self.assertTrue(s['heuristic_star'])

    def test_statistics_match_hand_calculated_gain_vector(self):
        # Gain [-2, 0, 2] has SD 2 and linear percentile span [-1.9, 1.9].
        s = self.mod.pair_summary(np.zeros(3), np.array([-2., 0., 2.]))
        self.assertEqual((s['positive'], s['zero'], s['negative']), (1, 1, 1))
        self.assertEqual(s['sd'], 2.)
        self.assertAlmostEqual(s['p025'], -1.9)
        self.assertAlmostEqual(s['p975'], 1.9)
        self.assertFalse(s['heuristic_star'])

    def test_heuristic_strict_boundary_and_negative_effect(self):
        # [1,2,3]: mean 2 = 2*SD, so the strict rule must not award a star.
        self.assertFalse(self.mod.pair_summary(np.zeros(3), np.array([1., 2., 3.]))['heuristic_star'])
        self.assertTrue(self.mod.pair_summary(np.zeros(3), np.array([-2., -3., -4.]))['heuristic_star'])

    def test_corpus_rejects_wrong_tier_target_or_network(self):
        d = pd.DataFrame([(n, t, r, self.mod.TIER, rep, .1)
                          for n in self.mod.NETWORKS for t in self.mod.TARGETS
                          for r in range(4) for rep in range(200)],
                         columns=['network', 'target', 'radius', 'tier', 'rep', 'tau_refit'])
        self.mod.validate_corpus(d)
        for col in ['network', 'target', 'tier']:
            bad = d.copy()
            bad.loc[0, col] = 'wrong'
            with self.subTest(column=col):
                with self.assertRaises(ValueError):
                    self.mod.validate_corpus(bad)


if __name__ == '__main__':
    unittest.main()
