"""Non-backtracking spectral gap: the certificate descriptor registered 2026-11-02 19:53 (part E).

    gap = 1 - |lambda_2| / lambda_1

over the spectrum of the Ihara-Bass matrix M = [[A, I - D], [I, 0]], the
2n x 2n form criticality.py already uses for the threshold. M's spectrum is the
non-backtracking matrix B's spectrum minus B's (m - n)-fold +/-1 roots, so the
two agree on lambda_2 whenever |lambda_2| > 1. When |lambda_2| <= 1 they need
not: B may have a +/-1 root that M lacks. The result says which case held
instead of pretending the distinction away.

Why the gap at all: the lane text asks whether the NB gap carries anything the
localisation duel ratio does not. On a sparse random graph the bulk of B's
spectrum sits near the circle of radius sqrt(lambda_1), so the gap is expected
to be close to a function of lambda_1 alone (inference; that is the point of
reporting it beside the duel ratio rather than scoring it).

A separate module so criticality.py, which stage 1 imports and the certificate
controller pins, is not edited.
"""
import numpy as np
import scipy.sparse.linalg as spla

from influence.criticality import build_ihara_bass

# Arnoldi settings. The second eigenvalue sits at the edge of a crowded bulk,
# which is where Arnoldi converges slowest, so ask for several eigenvalues
# with a wide Krylov space and keep the top two by modulus. The verifier checks
# these settings against the dense spectrum rather than trusting them.
N_EIGS = 8
NCV = 64
DENSE_MAX_DIM = 2000          # below this the dense solve is cheap and exact


def top_two_moduli(M, tol: float = 1e-10) -> tuple[float, float, str]:
    """(|lambda_1|, |lambda_2|, method) of a square sparse matrix."""
    dim = M.shape[0]
    if dim < 3:
        raise ValueError("need at least a 3 x 3 operator for two eigenvalues")
    if dim <= DENSE_MAX_DIM:
        vals = np.linalg.eigvals(M.toarray())
        method = "dense"
    else:
        vals = spla.eigs(M, k=N_EIGS, which="LM", ncv=min(NCV, dim - 1),
                         tol=tol, maxiter=20 * dim, return_eigenvectors=False)
        method = "arnoldi"
    mods = np.sort(np.abs(vals))[::-1]
    return float(mods[0]), float(mods[1]), method


def nb_spectral_gap(net, tol: float = 1e-10) -> dict:
    """The registered descriptor for one loaded network (its LCC, as stage 1 sees it)."""
    l1, l2, method = top_two_moduli(build_ihara_bass(net), tol=tol)
    return {"nb_lambda1": l1, "nb_lambda2_abs": l2,
            "nb_spectral_gap": 1.0 - l2 / l1,
            # True means |lambda_2| <= 1, where B's own lambda_2 could be a
            # +/-1 root that M does not carry (see the module docstring).
            "nb_lambda2_at_or_below_1": bool(l2 <= 1.0),
            "nb_method": method}
