"""Focused no-fit checks for the Phase 6 structural paired analysis."""
import copy
import unittest

import numpy as np
import pandas as pd

import analyse_structural_target_noise as mod


class StructuralPairedAnalysisTests(unittest.TestCase):
    def provenance(self):
        configuration = {"tier": mod.FULL, "reps": 200, "networks": list(mod.NETWORKS),
                         "targets": list(mod.MC_TARGETS), "radii": list(mod.RADII),
                         "fit_seed": 0, "resample_seed": 0, "outer_workers": 1}
        # The exact digest content is irrelevant here; validator only proves corpus agreement.
        return {"configuration": configuration, "configuration_sha256": "fixture-config",
                "resample_index_sha256": {network: [f"{network}-{rep}" for rep in range(200)]
                                            for network in mod.NETWORKS}}

    def corpus(self):
        provenance = self.provenance()
        return pd.DataFrame([(network, target, radius, mod.FULL, rep, .1,
                              "fixture-config", f"{network}-{rep}")
                             for network in mod.NETWORKS for target in mod.MC_TARGETS
                             for radius in mod.RADII for rep in range(200)],
                            columns=["network", "target", "radius", "tier", "rep", "tau_refit",
                                     "configuration_sha256", "resample_sha256"]), provenance

    def test_complete_fixture_passes_provenance_bound_validation(self):
        corpus, provenance = self.corpus()
        mod.validate_refit_corpus(corpus, provenance)

    def test_partial_wrong_identity_and_changed_tier_are_rejected(self):
        corpus, provenance = self.corpus()
        cases = [corpus.iloc[:-1], corpus.assign(resample_sha256="wrong"),
                 corpus.assign(tier="node+edge+subgraph+dynamic")]
        for broken in cases:
            with self.subTest(rows=len(broken)):
                with self.assertRaises(ValueError):
                    mod.validate_refit_corpus(broken, provenance)

    def test_shared_noise_variance_identity_is_preserved(self):
        summary = mod.pair_summary(np.array([0., 1., 2.]), np.array([1., 2., 3.]))
        self.assertEqual(summary["sd"], 0.)
        self.assertEqual(summary["covariance"], 1.)
        self.assertEqual(summary["variance_identity"], 0.)


if __name__ == "__main__":
    unittest.main(verbosity=2)
