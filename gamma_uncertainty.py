"""
How precisely can we even measure gamma at OUR network sizes?

This determines whether an r*(gamma) sweep is a curve or a smear. Run before
committing to the sweep design.
"""
import numpy as np
from influence import generators as gen
from influence import structure as st

print("Chung-Lu graphs at a KNOWN target gamma, fitted with bootstrap CIs.")
print("Sizes chosen to bracket the real corpus (email=986, ca-GrQc=4158, Gnutella=6299).\n")
print(f"{'n':>7} {'target':>7} {'fitted':>8} {'+/- std':>8} {'95% CI':>18} {'n_tail':>7}")
print("-" * 62)
for n in [1000, 4000, 6300, 20000]:
    for target in [2.2, 2.8, 3.4]:
        net = gen.chung_lu(n, target, mean_degree=6.0, seed=11)
        f = st.fit_power_law_tail(net.degree, n_bootstrap=200, seed=11)
        ci = f"[{f.get('alpha_ci_lo', np.nan):.2f}, {f.get('alpha_ci_hi', np.nan):.2f}]"
        print(f"{n:>7} {target:>7.1f} {f['alpha']:>8.3f} "
              f"{f.get('alpha_std', np.nan):>8.3f} {ci:>18} {f['n_tail']:>7}")
