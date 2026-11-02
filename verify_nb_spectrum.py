"""Checks for influence/nb_spectrum.py, registered 2026-11-02 19:53 (L6 part E).

1. Arnoldi against the dense spectrum of the Ihara-Bass matrix on random
   graphs large enough to take the Arnoldi branch.
2. Dense M against the explicit 2m x 2m non-backtracking matrix B on small
   graphs: the same top two moduli whenever |lambda_2| > 1, which is the case
   the module docstring claims they agree on.
3. lambda_1 against 1 / beta_c from criticality.epidemic_threshold.
Run with an optional edge list to add the same Arnoldi-vs-dense check on a
real L6 graph (part E's "one L6 graph"):
    python verify_nb_spectrum.py [edgelist]
"""
import sys
import unittest

import numpy as np

from influence import generators as gen
from influence.criticality import (build_ihara_bass, build_nonbacktracking_direct,
                                   epidemic_threshold)
from influence import nb_spectrum
from influence.nb_spectrum import nb_spectral_gap, top_two_moduli

REL = 1e-8


def lcc_net(n, k, seed):
    # Erdos-Renyi through the project's own generator and loader path, so the
    # matrix is built exactly as stage 1 would build it.
    return gen.erdos_renyi(n, k, seed=seed)


class NBSpectrumTests(unittest.TestCase):
    def test_arnoldi_matches_dense(self):
        old = nb_spectrum.DENSE_MAX_DIM
        nb_spectrum.DENSE_MAX_DIM = 10          # force the Arnoldi branch
        try:
            for seed in range(20):
                n = 300 + 20 * seed
                net = gen.chung_lu(n, 2.2 + 0.09 * seed, mean_degree=5.0, seed=seed) \
                    if seed % 2 else lcc_net(n, 5.0, seed)
                M = build_ihara_bass(net)
                dense = np.sort(np.abs(np.linalg.eigvals(M.toarray())))[::-1]
                l1, l2, method = top_two_moduli(M)
                self.assertEqual(method, "arnoldi")
                self.assertAlmostEqual(l1 / dense[0], 1.0, delta=REL, msg=f"seed {seed}")
                self.assertAlmostEqual(l2 / dense[1], 1.0, delta=REL, msg=f"seed {seed}")
        finally:
            nb_spectrum.DENSE_MAX_DIM = old

    def test_matches_explicit_B_above_one(self):
        checked = 0
        for seed in range(30):
            net = lcc_net(40 + seed, 4.0, seed)
            B = build_nonbacktracking_direct(net).toarray()
            mb = np.sort(np.abs(np.linalg.eigvals(B)))[::-1]
            res = nb_spectral_gap(net)
            self.assertAlmostEqual(res["nb_lambda1"] / mb[0], 1.0, delta=1e-7)
            if res["nb_lambda2_abs"] > 1.0 + 1e-6:
                self.assertAlmostEqual(res["nb_lambda2_abs"] / mb[1], 1.0, delta=1e-7)
                checked += 1
        self.assertGreater(checked, 10)   # the claim must be exercised, not vacuous

    def test_lambda1_is_inverse_threshold(self):
        for seed in range(5):
            net = gen.chung_lu(800, 2.5, mean_degree=6.0, seed=seed)
            res = nb_spectral_gap(net)
            self.assertAlmostEqual(res["nb_lambda1"] * epidemic_threshold(net), 1.0, delta=REL)


def check_edgelist(path: str) -> None:
    from influence.preprocessing import load_edgelist
    net = load_edgelist(path)
    M = build_ihara_bass(net)
    res = nb_spectral_gap(net)
    dense = np.sort(np.abs(np.linalg.eigvals(M.toarray())))[::-1]
    ok = (abs(res["nb_lambda1"] / dense[0] - 1) <= REL
          and abs(res["nb_lambda2_abs"] / dense[1] - 1) <= REL
          and abs(res["nb_lambda1"] * epidemic_threshold(net) - 1) <= REL)
    print(f"{net.name}: n={net.n} dim={M.shape[0]} {res['nb_method']} "
          f"l1={res['nb_lambda1']:.10f} (dense {dense[0]:.10f}) "
          f"l2={res['nb_lambda2_abs']:.10f} (dense {dense[1]:.10f}) "
          f"gap={res['nb_spectral_gap']:.6f} -> {'OK' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_edgelist(sys.argv[1])
    else:
        unittest.main(verbosity=2)
