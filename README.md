# Local Network-Based Influence Prediction

How much of a node's influence over a whole network can be predicted from what is
visible in its local neighbourhood alone?

This repository measures that. A model sees only the ball of radius *r* around each
node (r = 0 to 3 hops) and tries to rank nodes by their whole-network influence. The
radius is treated as a quantity to measure, not as a hyperparameter to tune: the
question is how quickly predictability rises with r, and which kinds of local
structure carry it. The motivation is partial observability (crawlers, decentralised
peers, privacy-limited platforms, sampled subgraphs), not compute cost.

## What is measured

- **Networks.** Five real networks: ca-GrQc, ca-HepTh, email-Eu-core,
  facebook_combined and p2p-Gnutella08. Each is cleaned to its largest connected
  component. A synthetic corpus is available as a control.
- **Targets.** Three from independent-cascade simulation: mean cascade size, its
  coefficient of variation (volatility), and volatility with the mean's contribution
  regressed out. The fourth is betweenness centrality.
- **Dynamics.** Every network runs at the same multiple (1.5×) of its own epidemic
  threshold β_c, computed from the non-backtracking operator, with 4,000 percolation
  runs. Using the same multiple everywhere is what makes networks comparable.
- **Features.** 171 registered features in four tiers: node, edge, subgraph (graphlet
  orbits from ORCA) and dynamic. Each feature is tagged with the radius at which it
  becomes observable, and a leakage guard rejects anything that needs more of the
  graph than its radius allows.
- **Scoring.** Kendall τ and precision@k on held-out nodes, over a radius × feature
  richness grid with 10 seeds per cell.

The findings, with their evidence and every revision, are in
[`docs/study_doc_v2.md`](docs/study_doc_v2.md).

Everything runs on a CPU. A GPU arm was measured and came out slower, because the
work is thousands of small independent fits rather than a few large ones.

## Repository layout

| Path | Contents |
|---|---|
| `influence/` | The package: graph cleaning, features, graphlets, dynamics, targets and the leakage guard, the sweep, estimators. |
| `pipeline/` | Data fetch, `stage0_generate`, `stage1_prepare`, `stage2_sweep`, `run_experiment`, and one-off repair and record scripts. |
| `analysis/` | Scripts that turn sweeps into result tables (`analyse_*`, scoring, reporting). |
| `figures/` | Figure scripts (`make_fig*`). |
| `probes/` | Self-contained experiments (`probe_*`). |
| `checks/` | Verification gates (`verify_*`). |
| `data/` | The corpus manifest. Edge lists are downloaded here; `data/cache/` holds the per-network stage-1 caches and sweeps. |
| `estimators/` | Sweeps with alternative estimators, kept apart because every `data/cache/sweep_*.csv` is read as a network. |
| `results/` | Result tables (`RESULTS_*.txt`, `results_*.csv`), figures and per-experiment output folders. |
| `docs/` | The study document, preregistrations (`docs/prereg/`) and reference guides (`docs/reference/`). |
| `vendor/` | Source of the ORCA graphlet-orbit counter. |

Further reading:

- [`docs/reference/running_guide.md`](docs/reference/running_guide.md): every
  argument, the model choices, how to read the metrics, known pitfalls, and a worked
  example with measured timings.
- [`docs/reference/phase6_reproduction.md`](docs/reference/phase6_reproduction.md):
  how the published results were produced, script by script.

## Setup

```bash
conda env create -f environment.yml
conda activate influence
```

`environment.yml` pins every version, including an OpenBLAS build of the BLAS
(`environment.lock.yml` is the exact solved environment). **Do not `pip install`
numpy, scipy or scikit-learn into this environment.** A pip wheel brings its own
BLAS, and the clash aborts natively, with exit code 127 and no traceback, at the
first matrix multiply. After any change to the environment, check:

```bash
python -c "import numpy as np; A=np.random.rand(300,300); print((A@A).sum())"
```

**Optional: build ORCA.** It is needed for the subgraph-tier (graphlet-orbit)
features. Without it those columns are skipped and the experiment is reduced.

```bash
g++ -O2 -std=c++11 -static -static-libgcc -static-libstdc++ -o vendor/orca.exe vendor/orca.cpp
```

## Running the pipeline

Run every script from the repository root (`python analysis/analyse.py`, not from
inside `analysis/`), because data paths are relative to the root.

```bash
# 1. Data
python pipeline/fetch_data.py                 # the five pilot networks (--all for more)
python pipeline/stage0_generate.py --n 5000   # synthetic control corpus (optional)

# 2. Per network: features and ground truth, then the radius x richness sweep
#    stage1 arguments: edge list, number of simulations, multiple of beta_c
#    stage2 arguments: tag, targets, max radius, number of seeds (never 1)
python pipeline/stage1_prepare.py data/ca-GrQc.txt 4000 1.5
python pipeline/stage2_sweep.py ca-GrQc spread_mean,spread_cv,spread_resid,betweenness 3 10
#    or both steps at once:
#    python pipeline/run_experiment.py data/p2p-Gnutella08.txt 4000 1.5 10

# 3. Results and figures
python analysis/analyse.py && python figures/make_fig1.py
python analysis/analyse_betweenness.py        # if betweenness was a target
python analysis/analyse_failures.py && python figures/make_fig2.py
python analysis/analyse_features.py
python analysis/analyse_robustness.py && python figures/make_fig3.py
```

Things to keep in mind:

- **Use the same β_c multiple for every network you compare.**
- `stage1_prepare.py` overwrites that network's cache. `stage2_sweep.py` resumes
  from `data/cache/sweep_<tag>.csv`.
- To add a network, put a plain-text edge list (two integer columns, one edge per
  line) in `data/`. Its tag is the file name without the extension.
- If a run dies with no error message, test the BLAS (see Setup) before anything else.
- A hash mismatch on resume means an input changed and needs investigating. Never
  edit a recorded hash to force a resume.

### Zero-fit analyses

These read the prepared caches, check their identity hashes, and write under
`results/phase6_5_*`. `probe_seed_sets.py` needs the outputs of
`probe_local_predictors.py`.

```bash
python checks/verify_local_dynamics.py
python probes/probe_local_predictors.py && python analysis/analyse_local_predictors.py
python checks/verify_seed_sets.py
python probes/probe_seed_sets.py && python analysis/analyse_seed_sets.py
python checks/verify_nonbacktracking_local.py && python probes/probe_nonbacktracking_local.py
```

## Verification

Each `checks/verify_*.py` is a standalone gate that prints `ALL CHECKS PASSED` or
exits non-zero. Run these three before trusting any result:

```bash
python checks/verify_pipeline.py data/email-Eu-core.txt   # features, cost model, dynamics, leakage guard
python checks/verify_generators.py                        # synthetic generators and structural measurements
python checks/verify_docs.py                              # document claims against artefacts; paths and links
```

One gate fails at present: `checks/verify_robustness_rerun.py` reports that the raw
robustness re-run differs from the archived file. The difference is explained in
[`docs/reference/phase6_reproduction.md`](docs/reference/phase6_reproduction.md).

## Contributing a change

- A new feature must pass the leakage guard in `influence/targets.py` and be
  registered with a hop, a tier and a cost group.
- Report Kendall τ and precision@k first. The training objective is not the scoring
  metric; the running guide explains why that matters.
- The running guide's "Things that will bite you" section lists the pitfalls this
  project has already hit, with the reason for each.

## License

MIT. See [`LICENSE`](LICENSE).
