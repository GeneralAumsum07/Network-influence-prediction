# Local Network-Based Influence Prediction - How to Run It

**Where to read the results:** [`docs/study_doc_v2.md`](docs/study_doc_v2.md) is the
scientific record, finding by finding, and [`HANDOFF.md`](HANDOFF.md) summarises the
findings, binding rules and known gotchas. This file is operational only: setup, how
to run, verification.

**Research continuation, 2026-09-12:** the seven new lanes (Phase 6.5, the deck
lanes L1–L7; the name was settled on 2026-09-12) are registered in
[the Phase 6.5 protocol](docs/prereg/prereg_phase6_5_lanes.md). See
[prior-work positioning](docs/reference/prior_work.md) for the corrected
comparison with Zhang (2024) and the H-index, k-shell and complex-contagion sources.
The existing long Phase 6 rerun is still incomplete.

Everything here runs on a laptop. No GPU, no PyTorch. Preparing one real network
of a few thousand nodes takes seconds; the full 640-cell sweep over it takes
roughly 45-70 minutes on 16 cores. Measured numbers are in section 11 - do not
trust a timing claim in this project that you have not measured yourself.

**"No GPU" is now a measurement, not a preference (2026-09-01).** The sweep was
timed against a CUDA arm on an RTX 5060 and the GPU came out **1.54x slower** than
correctly-scheduled CPU. The reason is structural and worth knowing before you
reach for a GPU on anything shaped like this: the workload is **6,400 small
independent fits** per network, so its parallelism is *across* fits, not *within*
one. A GPU only accelerates the within-fit axis. Handing 16 CPU cores the outer
axis beat the GPU outright. See `HANDOFF.md` section 11 for the three-arm table.

The research question: **can we predict how influential a node is in an entire
network using only information visible in its local neighbourhood?** And the
framing that matters - we treat the neighbourhood radius as a *measured
quantity* rather than a hyperparameter.

### Why the local constraint is the interesting one

The motivation is **partial observability, not compute cost.**

This is worth stating precisely, because the obvious version of the argument is
wrong and a referee will know it is wrong. "Real networks are too large to
compute influence on globally" does not survive contact with the algorithms
literature: PageRank, eigenvector, Katz and coreness are all near-linear in the
number of edges and run routinely at 10^9 edges or more; betweenness has
Brandes exactly and both VC-dimension sampling (Riondato-Kornaropoulos) and
adaptive sampling (KADABRA) approximately; influence spread has reverse-
reachable-set sketches (RIS, TIM, IMM) with approximation guarantees at
billion-edge scale. If compute were the only obstacle, the honest answer would
be to go and compute it.

The obstacle that does not dissolve is **not being able to see the graph at
all**:

- a crawler behind an API rate limit,
- a node inside a decentralised protocol, which knows its own peers and nothing
  else,
- a platform constrained by privacy rules from joining data across users,
- an analyst holding a sampled subgraph, with no way to obtain the rest.

None of these can see the whole network **at any compute budget.** For them
"how far must I look?" is not an optimisation, it is the entire question - and
it is one nobody can answer by buying a bigger machine.

Three things follow, and they are why this framing is load-bearing rather than
cosmetic:

1. **The small corpus is the right instrument, not an apology.** We work at a
   scale where the true global influence is still exactly computable, because
   that exact value is the ground truth our local predictions are graded
   against. A larger corpus would remove the grader.
2. **Radius-as-measurement becomes the centrepiece** rather than a defence.
3. **Angle 4 (damage) stops being a bolted-on robustness study** and becomes the
   same question asked through a noisy observation channel - which connects it
   to the twenty-year measurement-error literature on centrality rather than
   leaving it free-floating.

---

## 1. Setup (once)

### Use a dedicated conda environment

There is an `environment.yml` in the repo. Use it. Do **not** `pip install` into
your conda `base` environment - that is how base environments get broken, and
untangling one afterwards is genuinely unpleasant.

```bash
conda env create -f environment.yml
conda activate influence
```

That gives you Python 3.12 with numpy, scipy, pandas, scikit-learn,
python-igraph, networkx, matplotlib and tqdm. Python is pinned to 3.12
deliberately: it is mature enough that every package above has a solid prebuilt
Windows binary on conda-forge, and newer releases often lag by months on
scientific packages.

### Everything is pinned, including the BLAS - do not unpin it

`environment.yml` pins exact versions and, importantly, the line

```
- libblas=*=*openblas
```

That line is not stylistic. An unpinned solve produced numpy linked against
MKL 2026.1.0 alongside a **pip-installed** scipy carrying its own bundled
OpenBLAS, and the result was a hard native abort - exit code 127, no Python
traceback - on any dense matrix multiply. That kills `beta_c` at the first
eigenvalue call and therefore kills the whole pipeline, with an error message
that tells you nothing.

Two rules follow:

- **Install everything from conda-forge.** Never `pip install` numpy, scipy or
  scikit-learn into this environment; a pip wheel brings its own BLAS and
  reintroduces the conflict.
- **Check the BLAS after any environment change:**

```bash
python -c "import numpy as np; A=np.random.rand(300,300); print((A@A).sum())"
```

If that aborts instead of printing a number, the BLAS is broken - fix it before
anything else, because every downstream failure will be mysterious.

`environment.lock.yml` records the exact solved environment. Results are only
comparable across rebuilds if the versions match, which is why
`cache_meta_<tag>.json` now stores the versions each result was produced
under.

### Build ORCA (optional, for the graphlet orbit features)

Graphlet orbits are the subgraph tier. They come from ORCA, a single C++ file
vendored in `vendor/orca.cpp`. Build it once:

```bash
g++ -O2 -std=c++11 -static -static-libgcc -static-libstdc++ -o vendor/orca.exe vendor/orca.cpp
```

`-static` matters on Windows: without it a MinGW-built binary needs MSYS2's
runtime DLLs on PATH and will fail confusingly when run from a conda
environment.

**This step is optional.** If `vendor/orca.exe` is absent, `extract_features`
prints one line saying the orbits were skipped and the rest of the pipeline
runs normally - you simply get 64 features instead of 171. Both orbit groups
skip together, so what you lose is exactly `graphlet_orbits` (71 columns) and
`edge_orbits` (36). Nothing else depends on it.

Be aware that this is not a free downgrade any more. The 107 orbit columns are
where finding 3 lives (5-node hop-1 orbits) and they carry a small but real
gain on most targets, so a 64-feature run is a reduced experiment rather than
an equivalent one.

> Updated 2026-09-12 by Claude Opus 5 (Task 6 finding P1-01): the "5-node hop-1
> orbits" attribution above is withdrawn. Six of those orbits sit at hop 2; refit
> without them, the r=1 subgraph tier's gain is zero on every spread target
> (study §20, §26k.3). The orbit columns still matter - the subgraph tier's
> surviving gains are at r>=2 and on facebook betweenness - so a 64-feature run
> remains a reduced experiment, just not for the reason this paragraph gave.

The vendored source is upstream `thocevar/orca` unmodified, sha256
`01c580febfd3653a632a04d6b466f7c6f2bf2f9baf3a75a2e553be30ac7ee778`. It is
checked against our own enumeration on every `verify_pipeline.py` run - see
section 9.

**Every command in this README assumes `influence` is the active environment.**
Check with:

```bash
conda activate influence
python -c "import numpy, scipy, sklearn, igraph, networkx; print('environment ok')"
```

If you have several Python installs (the `py` launcher on Windows will happily
show you 3.12, 3.13 and 3.14 alongside conda), that check is worth running -
it confirms which interpreter you are actually about to use.

To update the environment later after editing `environment.yml`:

```bash
conda env update -f environment.yml --prune
```

### What each dependency is for

| Package | Role | Required? |
|---|---|---|
| numpy, scipy | arrays, sparse matrices, eigenvalues, connected components | yes |
| pandas | feature and result tables | yes |
| scikit-learn | RandomForestRegressor, k-fold CV | yes |
| networkx | synthetic generators, and the independent reference for verification | yes |
| python-igraph | fast exact betweenness on larger graphs | recommended |
| matplotlib | figures | for step 6 only |

`networkx` used to be verification-only. It is now a hard dependency, because
`influence/generators.py` builds the synthetic corpus on top of it.

### Folder layout

```
Network_influence_prediction/
  influence/                 <- the package (10 modules)
    preprocessing.py           loading + the six-decision cleaning protocol
    features.py                171 local features, hop and tier tagged
    graphlets.py               ORCA orbit counts, node and edge (the subgraph tier)
    dynamics.py                IC and SIR simulators, percolation shortcut
    criticality.py             non-backtracking operator, beta_c
    targets.py                 ground truth + THE LEAKAGE GUARD
    experiment.py              metrics, out-of-fold prediction, the sweep
    estimators.py              the estimator registry (rf / ridge / hgb / hgb_matched)
    robustness.py              damaged views of a network (Angle 4)
    generators.py              synthetic networks (structural control arm)
    structure.py               whole-network descriptors (gamma, assortativity, ...)

  data/                      <- real edge lists land here
  data/synthetic/            <- generated edge lists land here
  results/                   <- figures and result dumps
  estimators/                <- alternative-estimator sweeps. NOT the repo root:
                                `sweep_*.csv` there would be read as a network
  docs/                      <- pre-registrations, post-hoc declarations, study doc
  cache_archive/             <- superseded caches, kept for comparison only

  fetch_data.py              step 1a: download the real corpus
  stage0_generate.py         step 1b: build the synthetic corpus
  stage1_prepare.py          step 2:  features + ground truth  (per network)
  stage2_sweep.py            step 3:  train and evaluate       (per network)
  analyse.py                 step 4:  result tables
  make_fig1.py               step 5:  the locality budget figure
  analyse_failures.py        step 6:  the failure atlas (Angle 3)
  make_fig2.py               step 7:  the failure atlas figure
  analyse_features.py        audit the feature table itself
  analyse_robustness.py      step 9:  Angle 4, robustness under damage
  make_fig3.py               step 10: the robustness figure
  analyse_betweenness.py     the betweenness tie-block analysis
  analyse_edge_tier.py       what inside the edge tier rescues betweenness
  analyse_edge5.py           do 5-node EDGE orbits earn their 204 columns?
  analyse_estimators.py      B2: does r*(eps) agree across estimators?
  probe_objective_horizon.py does r*(eps) move under a corrected objective?
  analyse_objective_horizon.py   reads that probe's output
  probe_sample_efficiency.py B1: how much performance survives fewer labels?
  analyse_sample_efficiency.py   scores that probe against its pre-registration
  run_experiment.py          convenience wrapper: stage1 + stage2 in one call

  _calib.py                  measures the radius each NODE orbit needs
  _calib_edge.py             measures the radius each EDGE orbit needs

  verify_pipeline.py         verification suite for features/cost/dynamics
  verify_generators.py       verification suite for generators + structure
  gamma_uncertainty.py       how precisely gamma can be measured at our sizes

  vendor/orca.cpp            ORCA graphlet orbit counter (vendored source)
  vendor/orca.exe            built locally - see section 1
  environment.yml            pinned environment spec (do not unpin the BLAS)
  environment.lock.yml       exact solved environment

  HANDOFF.md                 read this first if you are new to the project
  docs/study_doc_v2.md       the long-form results document, finding by finding
```

`HANDOFF.md` moved into the repo on 2026-08-27; it used to live outside it, which
meant the code could drift from its description with nothing to show the drift.

---

## 2. The full run, in order

If you are starting from a clean clone, this is the whole sequence. Each step is
explained in detail further down.

```bash
conda activate influence

# --- 1a. get the real networks ---------------------------------------
python fetch_data.py                       # the pilot five
# python fetch_data.py --all               # plus five more

# --- 1b. build the synthetic control corpus (optional but recommended) -
python stage0_generate.py --n 5000

# --- 2 & 3. per network: prepare, then sweep -------------------------
# The last argument to stage2 is the number of SEEDS. Do not set it to 1.
python stage1_prepare.py data/ca-GrQc.txt 4000 1.5
python stage2_sweep.py ca-GrQc spread_mean,spread_cv,spread_resid,betweenness 3 10

python stage1_prepare.py data/email-Eu-core.txt 4000 1.5
python stage2_sweep.py email-Eu-core spread_mean,spread_cv,spread_resid,betweenness 3 10

# ... repeat for each network in data/ and data/synthetic/
# or, for one network in a single command:
#     python run_experiment.py data/p2p-Gnutella08.txt 4000 1.5 10

# --- 4 & 5. results --------------------------------------------------
python analyse.py
python make_fig1.py
python analyse_betweenness.py        # only if betweenness is among your targets

# --- 6 & 7. the failure atlas ----------------------------------------
python analyse_failures.py
python make_fig2.py

# --- 8. audit the feature table itself --------------------------------
python analyse_features.py

# --- 9 & 10. robustness under damage (Angle 4) ------------------------
python analyse_robustness.py
python make_fig3.py
```

**Use the same beta_c multiple for every network you intend to compare.** The
whole point of expressing p as a multiple of each network's own threshold is
that a fixed multiple puts every network in the same dynamical regime. An
earlier version of this corpus ran email-Eu-core at 1.2x while the others ran
at 1.5x, which quietly reintroduced exactly the confound the normalisation
exists to remove.

**Before a big run, verify the machinery.** Two suites, both must print
`ALL CHECKS PASSED`:

```bash
python verify_pipeline.py data/email-Eu-core.txt
```

```bash
python verify_generators.py
```

`verify_pipeline.py` covers feature extraction, the cost model, the dynamics
helpers and the leakage guard. `verify_generators.py` covers the synthetic
corpus and the structural measurements and takes about three minutes.

**`n_jobs` is now `-1`** in `out_of_fold_predictions` - it uses every core.
It used to be `1` because the original build machine had one, which made the
sweep roughly an order of magnitude slower than it needed to be. Trees are
independent so the speedup is close to linear, and the result is unchanged:
`random_state` still fixes which trees get built. This is what makes running
ten seeds per cell affordable.

---

## 3. Step 1a - getting the real networks

```bash
python fetch_data.py
```

Downloads, decompresses and checksums the pilot five into `data/`:
`ca-GrQc`, `ca-HepTh`, `email-Eu-core`, `p2p-Gnutella08`, `facebook_combined`
(ego-Facebook). Add `--all` for ca-HepPh, ca-CondMat, p2p-Gnutella09 and two
autonomous-system topologies.

It is idempotent - anything already in `data/` is skipped - and a single dead
mirror does not abort the rest.

It writes `data/manifest.json` recording, per network, the source URL, byte
count, SHA-256 and whether the source file was directed. **Keep that file.**
It is the same discipline as the provenance dict in `preprocessing.py`: if your
numbers ever drift between runs months apart, the checksum tells you whether the
data changed or your code did. SNAP has silently re-uploaded files before.

### Why not just curl

You can, on Linux or macOS:

```bash
cd data
curl -sLO https://snap.stanford.edu/data/ca-GrQc.txt.gz
gunzip ca-GrQc.txt.gz
```

For one file that is functionally identical and `fetch_data.py` adds nothing
magical. But **on Windows PowerShell it does not work**: `curl` there is an
alias for `Invoke-WebRequest`, which rejects `-sLO`, and `gunzip` does not exist
at all. Use `curl.exe` if you insist on the manual route. `fetch_data.py` is
pure Python stdlib and behaves the same everywhere - plus it records the
checksums, which the manual route does not.

### Adding your own network

A plain text edge list, two integer columns, one edge per line:

```
# comment lines starting with # or % are ignored
3466	937
3466	5233
795	937
```

Separators can be tabs, spaces or commas. Extra columns (weights, timestamps)
are ignored - we discard weights deliberately and consistently, because
half-using weights is the most common silent error in this literature. Node IDs
can be any integers with gaps; they are reindexed internally and the mapping
back to the original labels is preserved in `Network.original_ids`.

Drop the file in `data/`. The network's **tag** - used in every later command
and output filename - is the filename without its extension.

```
data/ca-GrQc.txt      ->  tag is  ca-GrQc
data/my-network.txt   ->  tag is  my-network
```

---

## 4. Step 1b - building the synthetic corpus

```bash
python stage0_generate.py --n 5000
```

Real networks cannot isolate a variable. ca-GrQc differs from email-Eu-core in
density *and* degree tail *and* clustering *and* assortativity simultaneously,
so when r\* differs between them you cannot say which property caused it.
Generated networks fix exactly one knob at a time.

Writes edge lists to `data/synthetic/` plus a `manifest.json` with each graph's
generator settings and measured structural profile. They are plain edge lists,
so `stage1_prepare.py` runs on them with no code change and no special case -
which is the only reason their r\* values are comparable to the real ones.

Four families plus controls:

| Family | Generator | Knob | Holds fixed |
|---|---|---|---|
| `gamma` | Chung-Lu | degree tail exponent | mean degree |
| `clustering` | Holme-Kim | triangle density | tail, m |
| `assortativity` | Xulvi-Brunet-Sokolov | degree correlation | degree sequence **exactly** |
| `community` | LFR | mixing parameter mu | tail, mean degree |
| `controls` | ER / BA / WS | - | the three corner cases |

Useful flags: `--families gamma,clustering` to build a subset, `--bootstrap 0`
to skip the gamma error bars (much faster), `--seed` for a different draw.

### Read this before plotting anything against gamma

Run `python gamma_uncertainty.py` once and look at the output.

The Clauset-Shalizi-Newman estimator is essentially exact when `xmin` is known -
error under 0.007. But `xmin` is not known; it is chosen by minimising a KS
distance, and that selection is the dominant source of uncertainty. At n = 6,300
the bootstrap standard deviation on gamma is 0.10 to 0.38. At n = 1,000 with a
steep tail the estimator fails outright: a Chung-Lu graph built at gamma = 3.4
fitted as **1.81**, because there were not 50 points above any genuinely
tail-like `xmin`, so the fit fell back to a low `xmin` and fitted the bulk of
the distribution instead.

Two consequences:

- `fit_power_law_tail` now returns a `reliable` flag and a `tail_fraction`. A
  fit that retains most of the data is not a tail fit, and it says so rather
  than returning a confident-looking wrong number.
- `stage0_generate.py` plots the gamma family against the generator's **target**
  gamma, which is known by construction and has no measurement error - not
  against the fitted value. The fitted value is still recorded, with its error
  bar, because the real networks have no target gamma and the honest version of
  this result has to show how noisy that measurement is.

**Any figure showing gamma for a real network needs an error bar on it.**

---

## 5. Step 2 - features and ground truth

```bash
python stage1_prepare.py data/ca-GrQc.txt 4000 1.5
```

| Position | Meaning | Default |
|---|---|---|
| 1 | Path to the edge list | required |
| 2 | Number of cascade simulations | 4000 |
| 3 | Transmission probability, as a multiple of this network's own beta_c | 1.5 |
| 4 | Edge-probability convention (`uniform` or `trivalency`) | `uniform` |

The third argument is the important one. We do **not** fix p at an absolute
number - that would put different networks in different dynamical regimes and
make any cross-network comparison meaningless. Instead we compute each network's
own epidemic threshold beta_c from the non-backtracking operator, and work at a
fixed multiple of it, so `1.5` means the same regime everywhere. Values between
1.0 and 2.0 sit near criticality, which is where nodes are most distinguishable
and therefore where the research question is most interesting.

The feature table is **171 columns registered, 170 reachable** with ORCA built:
45 node, 48 edge, 76 subgraph, 2 dynamic. The gap is one orbit, not an
accounting slip - see the radius ladder below. What each column is, and which
are derived rather than independent, is in section 6 of `docs/study_doc_v2.md`.

*(The edge/subgraph split was 50/74 until 2026-08-31, when a project-wide audit
moved `ball2_density` and `local_conductance_2` from the edge tier to the
subgraph tier. They describe edges **among** 2-ball members, not the node's own
incident edges, which is what this project defines the edge tier to be - and
`ball2_edges`, computed from the identical array, was already tagged subgraph.
See §26a of the study doc for what that changes and what it does not.)*

Cumulative by radius: **2** at r=0, **56** at r=1, **145** at r=2, **170** at
r=3. One subgraph feature sits at hop 4 and is therefore never selectable at
the default `max_hop=3`.

*(Updated 2026-09-12 by Claude Opus 5: r=1 was 62 until the 2026-09-11 radius
retag moved six 5-node orbits - 56, 57, 65, 66, 68, 70 - from hop 1 to hop 2,
where their measured eccentricity puts them (Task 6 finding P1-01, study
§26k.3). The r=1 subgraph-tier cells were refitted on the corrected 56.)*

*(These counts are verifiable rather than remembered - they are exactly what
`cache_registry_<tag>.csv` contains, and `verify_docs.py` checks this paragraph
against it. An earlier version of this section claimed 77 columns / 45-14-16-2,
which described the pre-ORCA-5 era and had silently gone stale.)*

**Graphlet orbits are not all the same radius**, which is worth knowing before
reading any cost table. The radius an orbit needs is the eccentricity of the
node within its graphlet. Measured - not derived by hand - by `_calib.py` and
`_calib_edge.py`:

| | hop 1 | hop 2 | hop 3 | hop 4 | total |
|---|---|---|---|---|---|
| **node orbits** (5-node ORCA) | 22 | 37 | 11 | 1 | **71** |
| **edge orbit columns** (12 orbits x 3 statistics) | 9 | 24 | 3 | - | **36** |

Graphlets are mostly a radius-1 and radius-2 enrichment, not an expensive block
attached to the deepest radius.

**Why 71 node orbits and not 73.** ORCA emits 73 orbits for graphlets on up to
5 nodes (0-72). Two are dropped because they are *exactly* columns the table
already has - **orbit 0 is degree** and **orbit 3 is triangle_count** - so
including them would duplicate features and inflate the subgraph tier with
nothing. This is enforced by `REDUNDANT_ORBITS = (0, 3)` in
`influence/graphlets.py`, and any orbit that is identically zero on a given
graph is skipped as well, since a constant column carries no information.

Their *cost*, unlike everything else in the table, does not decompose by
radius: ORCA solves for all orbits in one pass, so a cell using any orbit pays
for all of them. **This is the one place graphlet cost really bites, and it is
density-driven:** 0.65 s on ca-GrQc, but **231.6 s on facebook_combined** -
232 of that network's 242 s stage-1 total. Do not generalise the sparse-network
figure.

This step prints a **noise report**. Check it:

```
ratio (want << 1) : 0.0036  [OK]
```

If it says `TOO NOISY`, raise the simulation count.

Outputs, cached so you never repeat the expensive work:
`cache_features_<tag>.csv`, `cache_targets_<tag>.csv`, `cache_registry_<tag>.csv`,
`cache_cascades_<tag>.npy`, `cache_meta_<tag>.json`.

`cache_meta_<tag>.json` records everything a result might later need to be
explained by: beta_c and the multiple used, the simulation count, **the
convention, the max hop and the simulation seed**, per-group feature timings,
per-stage wall clock, the full preprocessing provenance, and **the exact
package versions**. The first three of those were previously not recorded,
which meant a cache built under different simulation settings was
indistinguishable from one built under the current ones.

---

## 6. Step 3 - train and evaluate

```bash
python stage2_sweep.py ca-GrQc spread_mean,spread_cv,betweenness 3
```

| Position | Meaning | Default |
|---|---|---|
| 1 | Network tag | required |
| 2 | Comma-separated targets to predict | `spread_mean` |
| 3 | Maximum radius to test | 3 |
| 4 | Number of seeds per cell | 10 |

Available targets: `spread_mean`, `spread_cv`, `spread_std`, `spread_resid`,
`spread_ignition`, `betweenness`.

The richness ladder has **four** rungs: `node`, `node+edge`,
`node+edge+subgraph`, and `node+edge+subgraph+dynamic`. The fourth holds the
truncated percolation estimate - the only feature family that assumes the
observer knows the transmission probability p. Keeping it on its own rung means
no general claim about richness can quietly depend on that assumption, and
deleting one line from `TIER_LADDER` in `influence/experiment.py` removes it
from every sweep. Passing no `p_transmission` to `extract_features` omits the
columns entirely.

Trains one model per cell of the radius x richness grid **at each seed**, and
appends each result to `sweep_<tag>.csv` as it finishes. If the run is
interrupted, run the same command again - it resumes at the exact cell it
stopped on, seed included. Delete the CSV to force a clean re-run.

### Why several seeds, and not one

This is the change that matters most for the credibility of everything else.

The project's claim is that the neighbourhood radius is a **measured**
quantity rather than a hyperparameter. A measurement without an uncertainty is
not a measurement, and the numbers the conclusions rest on are small - some of
the marginal gains are 0.001 to 0.02 in Kendall tau. At one seed there is
simply no way to tell any of them from run-to-run noise, and `r*(eps)` is an
integer that can flip on a different fold split.

Varying the seed varies two things at once, which is what we want: which nodes
land in which cross-validation fold, and the forest's own tree construction.
Together they are the full sampling variability of one result.

`analyse.py` then differences **paired** - the same seed's r and r+1 curves are
subtracted before averaging. Radii sharing a seed share their fold split, so
the paired difference cancels most of the shared noise and is a much sharper
test than comparing two independent means.

### Which model, and how it is trained

`RandomForestRegressor`, configured in `influence/experiment.py`:

| Setting | Value | Why |
|---|---|---|
| `n_estimators` | 120 | More trees is slightly better and slower |
| `min_samples_leaf` | 2 | Mild smoothing; prevents single-node leaves |
| `n_jobs` | **-1** | Uses every core. Set to `1` only for a bit-exact audit (~10x slower) |
| `random_state` | seed | Fixes which trees get built - but see below, this is *not* bit-exact at `n_jobs=-1` |

**`random_state` does not buy bit-exact reproducibility at `n_jobs=-1`, and the
table used to claim it did.** sklearn accumulates tree predictions in whatever
order the workers finish, and floating-point addition is not associative. Two
identical runs on p2p-Gnutella08 differ by 5.7e-14 in predictions and by exactly
0 at `n_jobs=1`. Because Kendall tau is a rank statistic, that amplifies to
about **5.08e-08** in tau - a last-bit difference can flip a near-tie, which
moves tau by a discrete step. That is five orders of magnitude below the
seed-to-seed spread we report (~1e-3), so it cannot affect a conclusion, but it
is a measured tolerance and not an exact identity. State it that way.

It is a regression model - it predicts a number, not a category - and it is
refit for every grid cell, so one sweep fits many models.

Training uses **5-fold cross-validation with out-of-fold prediction**: nodes are
split into 5 groups, the model trains on 4 and predicts the 5th, rotating until
every node has a prediction from a model that never saw it. Without this a
random forest partly memorises its training nodes, errors look artificially
small, and the failure analysis would be studying memorisation rather than real
structural blind spots.

Known limitation, stated openly: on a single graph the held-out nodes' features
are still computed on a graph that contains the training nodes. This is not
fully independent transfer. Training on some networks and testing on entirely
separate ones is the clean version, and the pipeline supports it.

### Swapping the model

*(Rewritten 2026-09-01. This section used to say the swap was "a hack, not an
interface" and that a real refactor was planned work. The refactor landed - the
description below is the interface that now exists.)*

Estimators live in `influence/estimators.py` as a registry of **factories**. A
factory is `(seed: int) -> unfitted regressor`, and the model class is a CLI
argument to `stage2_sweep.py`:

```bash
python stage2_sweep.py ca-GrQc spread_mean,spread_cv,betweenness,spread_resid 3 10 ridge
```

Four are registered: `rf` (the default that produced every published number),
`ridge`, `hgb`, and `hgb_matched`. To add one, write a factory and register it in
`ESTIMATORS`; anything with scikit-learn's `.fit()` / `.predict()` contract works.

**The factory takes the seed** rather than being nullary, so that model
construction and fold assignment are seeded from the *same* draw - that is what
makes one "seed" in this project a single coherent sample of variability.

**Alternative-estimator output goes to `estimators/`, and this is load-bearing.**
`analyse.py::discover_networks` globs `sweep_*.csv` and regexes `sweep_(.+)\.csv`,
so a file named `sweep_ca-GrQc__ridge.csv` in the repo root would be silently
discovered as a **network** and would corrupt five consumers of that glob. The
globs are non-recursive, which is what makes the subdirectory safe.

**Two traps that cost real time here, both worth knowing outside this project:**

1. **Match capacity hyperparameters, or you are comparing defaults rather than
   inductive biases.** `RandomForestRegressor` defaults to `min_samples_leaf=1`
   and this project pins **2**; `HistGradientBoostingRegressor` defaults to **20**.
   Comparing those directly produced a 0.5 τ gap that was read as inductive bias
   and was **68% that one parameter**.
2. **Scale the features for any penalised linear model, inside the fold.** The
   table mixes raw counts, degrees and bounded ratios across four orders of
   magnitude, so an unscaled ridge measures feature scaling. `make_ridge` uses
   `make_pipeline(StandardScaler(), RidgeCV(...))` so the scaler is fitted on the
   training fold only - scaling before the split leaks.

**Why this exists.** The project's central claim is that r\*(ε) is a *measured
property of the (network, target) pair*. A measurement must be
instrument-independent within a stated tolerance. As of 2026-09-01 that has been
tested: the horizon **is** estimator-stable on the spreading targets (17/20 cells
agree between `rf` and `hgb`) and is **not** established on betweenness. See
`HANDOFF.md` section 10 and `docs/prereg/prereg_B2_estimator.md`.

### The training objective is not the scoring metric - read this before quoting τ

**Every estimator above minimises squared error. Everything is scored by Kendall
τ.** On a heavy-tailed target those are barely related: squared loss spends the
model on the few nodes with enormous values, while τ only rewards ordering the
bulk. On facebook_combined betweenness (skew **28.88**) that mismatch costs
**+0.18 τ** - more than any feature tier in the project is worth.

The fix is one line, and it is legitimate rather than a metric relaxation: τ is
invariant to monotone transforms of the *ground truth*, so you can train on
`log1p(y)` while still scoring τ against the **original** `y`.

```python
model.fit(X[train], np.log1p(y[train]))       # what it optimises
tau = kendalltau(y, predictions).statistic     # what it is judged against
```

**It is not applied in the sweep**, and that is a pending decision rather than an
oversight (`HANDOFF.md` section 14). Two consequences you must respect meanwhile:

- **Every betweenness τ in this repository is measured under a squared-error
  objective** and is understated. Quote it with that qualifier.
- **The handicap varies along the richness ladder**, so it contaminates *richness*
  comparisons specifically. For the random forest it is **largest where the feature
  set is poorest** (+0.291 at r=0 down to +0.079 at r=3 on facebook betweenness) -
  richer features partially substitute for a correct objective, so the poorer rung
  is penalised harder and the comparison flatters the richer one. Correcting it cuts
  the project's largest richness effect from +0.129 to +0.044. The *direction* is
  learner-specific (ridge decays with radius instead), so the claim to rely on is
  that it varies, not which way. Before comparing feature groups on a rank metric,
  check the target's skew and refit once on a transformed target.
- **It can move the reported horizon.** Measured across the corpus, 3 of 50
  r\*(ε) cells moved under a corrected objective - all on betweenness, all on
  facebook_combined, and all **downward** (r\*=3 → 2 at the tight tolerances). None
  of the 25 spreading-target cells moved. Run `probe_objective_horizon.py` and
  `analyse_objective_horizon.py` to reproduce.
- **It can flip a rung's SIGN, not just shrink it.** The corpus re-sweep
  (2026-09-04) found the facebook r=1 edge rung goes from a significant
  **−0.0097** to a significant **+0.0158**. A tier that looked *harmful* was an
  artefact of the loss function. So "correcting the objective shrinks gains" is
  wrong as a general rule - it removes a distortion whose sign varies by rung.
- **But it is essentially a `facebook_combined` effect, and that is n=1.**
  0 of 32 rungs on the other four networks moved by more than 0.02. The effect
  tracks target skew (facebook betweenness is 28.88 against 4.77-9.73 elsewhere),
  but the magnitude behind the headline rests on a single network. Say so
  whenever you quote it.
- **It does not measurably hurt top-k.** This was a live concern - squared error
  over-weights exactly the huge-betweenness nodes `precision_at_1pct` rewards - so
  it was measured rather than assumed: 1 of 20 p@1 changes clears 2·sd and it is
  *positive*, and no cell shows τ significantly up with p@1 significantly down.
  Caveat on the null: p@1 is coarse (1% of ca-GrQc is ~41 nodes, so one node is
  ~0.024), so this rules out a large effect, not a small one.

To reproduce the re-sweep arm: `python stage2_sweep.py <tag> betweenness 3 10 rf_log1p`,
then `python analyse_objective_resweep.py`. Output lands in `estimators/`, never the
repo root - see the folder-layout note on why that matters.

### How many labels do you actually need? *(B1, 2026-09-04)*

Measured over 5,600 cells: only the *training* portion of each fold is subsampled,
the test fold always stays whole, so every fraction estimates the same quantity.

- **"~20% of labels is enough" is true only for the easy target.** τ at 20% vs 100%,
  radius ≥ 1: `spread_mean` is within 0.02 in **15/15** cells (mean cost −0.0097),
  `spread_cv` in 11/15, and `spread_resid` in only **3/15** (worst −0.0441). Quote
  the rule with the target attached or do not quote it.
- **Label scarcity moves the reported horizon in OPPOSITE directions depending on
  the target.** With email-Eu-core excluded as underdetermined, r\*(ε) moved down on
  `betweenness` (9 down, **0 up**) and up on `spread_cv` and `spread_resid`
  (**0 down**, 15 up). Zero counterexamples either way. If you are label-limited,
  the radius you should buy depends on which target you are predicting - shallower
  for betweenness, deeper for the residual targets.
- **Do not quote the 5% arm alone.** At 5% and r=3, three of five networks have no
  more training rows than feature columns (email-Eu-core: 39 rows, 168 columns).
  Those fits prefer a shallow radius for reasons that have nothing to do with an
  information horizon. The 10% and 20% arms carry the weight.

To reproduce: `python probe_sample_efficiency.py --check` (must PASS - it verifies the
probe's own OOF loop against the published sweep), then `python
probe_sample_efficiency.py`, then `python analyse_sample_efficiency.py`.

---

## 7. Steps 4 and 5 - results and figure

```bash
python analyse.py       # tables
python make_fig1.py     # fig1_locality_budget.png
```

`analyse.py` prints the locality budget curves P(r), r\*(eps) across a range of
tolerances, the marginal gain per hop, the depth-versus-richness comparison and
the cost/quality frontier.

Neither script takes a network list. Both discover their inputs by globbing
`sweep_*.csv` in the working directory, so a network joins the analysis the
moment its sweep finishes and there is no hand-maintained list to forget to
update. `analyse_failures.py` and `analyse_robustness.py` do the same over
`cache_oof_*.npz` and `cache_features_*.csv` respectively.

**Always report the full P(r) curve and the marginal-gain table, with r\*(eps)
across a range of eps as a summary.** A single r\* number is an artefact of an
arbitrary tolerance - on ca-GrQc spread mean, r\* is 0 at eps=0.20, 1 at
eps=0.10 and 2 at eps=0.02. Reporting one of those alone would be exactly the
ad hoc choice this project exists to criticise.

### Reading the metrics

| Metric | Meaning | Good value |
|---|---|---|
| `kendall_tau` | Did we rank every pair in the right order? | 1.0 perfect, 0 random |
| `precision_at_5pct` | Of the true top 5%, how many did we catch? | closer to 1 is better |
| `n_features` | How many features that cell was allowed | - |
| `fit_seconds` | Model training cost for that cell | - |
| `feature_seconds` | Feature extraction cost for that cell | see caveat below |

Lead with tau and precision@k, never RMSE. Influence is heavily skewed - a few
enormous nodes and thousands near zero - so raw error is dominated by the big
ones and hides whether the ranking is right.

**`feature_seconds` used to be wrong and is now correct.** The old `_cost_for`
inferred a feature's cost group from its hop and tier, and got it wrong in both
directions: it charged the whole collective-influence and H-ladder cost at r=1
(including the CI_2 and CI_3 work r=1 cannot use), and charged *zero* extra for
r=2 to r=3, so those rows carried identical costs on every network. Any Pareto
frontier built on it was ranking noise.

Each feature now records the timed extraction group that produced it, in the
registry, and `feature_cost()` simply sums the distinct groups a cell touches.
There is no mapping to keep in sync, and a feature that forgets its group shows
up as a missing cost rather than a silently mis-attributed one. Timings are
recorded per hop for the shell/CI traversal and per order for the H-ladder, so
the step from r=2 to r=3 costs what it actually costs.

One subtlety is worth knowing, because getting it wrong is easy: expanding the
BFS frontier at level h is what *produces* level h+1, so its cost is charged
forward to h+1. Charging it to the level that triggered it makes the deepest
hop look nearly free and makes the cumulative cost of radius r include building
the shell at r+1, which a radius-r observer never needs.

---

## 8. Steps 6 and 7 - the failure atlas

```bash
python analyse_failures.py
python make_fig2.py
```

Every other analysis asks *how accurate* local prediction is. This one asks
what locality is **blind to** - which nodes the model consistently misranks,
and what those nodes have in common.

### What it computes

For each node, a rank residual at the reference configuration (deepest radius,
full richness):

```
delta(v) = true percentile rank - predicted percentile rank
```

positive meaning the node is genuinely more important than the model said - an
under-predicted "hidden influencer". It is computed inside each seed and then
averaged, so a node lands in a tail because the model *consistently* misplaces
it rather than because one fold split happened to.

### The two things that make it a result rather than an artefact

**Shrinkage is removed first.** Every regression pulls predictions toward the
middle, so in rank space the high-influence nodes get positive delta and the
low-influence ones negative delta as a pure artefact of fitting. Taken raw, the
atlas would announce that the under-predicted nodes are the influential ones -
true, mechanical, and worthless. So the expected residual at each level of true
influence is subtracted first, exactly as `variance_residual` does in
`targets.py`. The report prints the median true percentile of each tail as the
check: near 0.5 means shrinkage is not driving the split.

**The profiling axes are deliberately global.** The atlas can only explain a
blind spot using information the model was *denied* - coreness, hop distance to
the nearest hub, the gap between coreness and its local H-index proxy. Those
come from `structure.py` and would abort the sweep if they ever reached the
feature matrix. Local features are profiled too, but as context: they say what
a failing node looks like from the inside, which is all a practitioner would
actually have.

### Reading the tables

Comparisons are ranked by **Cliff's delta**, a rank-based effect size in
[-1, 1], not by p-value. At several thousand nodes almost any difference is
"significant", so a p-value would rank everything as important. Conventional
reading: below 0.15 negligible, 0.33 small, 0.47 medium, above that large.

The last block, `WHAT HOPS 2-3 RESCUE`, is usually the sharpest signal. It
profiles the nodes whose ranking improves most between r=1 and the deepest
radius - that is, it names what the extra hops actually supply.

**It needs `cache_oof_<tag>.npz`**, written by stage 2. A sweep older than
prediction storage will not have one, and there is no way to recover the
predictions without refitting.

### Phase 6.5 zero-fit analyses

Run these from the repository root in the `influence` environment. They set
native numerical libraries to one thread, validate their cache identities and
write under `results/phase6_5_*`. A hash mismatch requires investigation; do not
edit a sidecar to force a resume. L4 requires the completed L3 outputs.

```powershell
python verify_local_dynamics.py
python probe_local_predictors.py
python analyse_local_predictors.py
python verify_seed_sets.py
python probe_seed_sets.py
python analyse_seed_sets.py
python verify_nonbacktracking_local.py
python probe_nonbacktracking_local.py
```

The preregistration defines the comparisons and their limitations, including the
conditions that must hold before any additional fitted lane is started.

## 9. Verification

The project standard is that nothing is asserted, only checked against an
independent reference. Two suites:

```bash
python verify_generators.py    # generators + structural measurements
python gamma_uncertainty.py    # how precisely gamma can be measured
```

Verification added since: the merged shell/CI traversal was checked against the
separate `bfs_shells` and `collective_influence` reference implementations *and*
against the pre-merge production cache, and agrees **bit for bit**; the
trivalency edge probabilities now come from one shared helper, so the
percolation and direct paths draw the same graph from the same seed;
`betweenness == 0` was checked to be exactly equivalent to `ego_betweenness == 0`
with zero mismatches.

The pre-merge-cache comparison and the 11,443-node betweenness equivalence check
were both run on the three networks that made up the corpus at the time
(ca-GrQc, email-Eu-core, p2p-Gnutella08) - a pre-merge cache cannot exist for a
network first prepared after the merge. `verify_pipeline.py` itself needs no
such cache and was re-run from scratch on the two networks added later,
`ca-HepTh` and `facebook_combined`; both print `ALL CHECKS PASSED`, including
the leakage guard.

`verify_generators.py` runs six checks and must print `ALL CHECKS PASSED`:

1. Assortativity, transitivity, average clustering and triangle counts against
   networkx, on four graph families - agreement to 1e-14 or better.
2. The power-law MLE against synthetic data with a known exponent, tested
   separately at known `xmin` and through the full KS selection procedure.
3. That the reliability flag catches the bulk-fit fallback failure mode.
4. That Chung-Lu's fitted gamma tracks its target monotonically.
5. That Holme-Kim's `p_triad` actually raises clustering.
6. That double-edge-swap preserves the degree sequence exactly, and that
   assortativity rewiring moves toward its target while holding degrees fixed.

Earlier verification, from the core pipeline: ego-betweenness against
brute-force betweenness on explicit ego subgraphs (2e-11), the Ihara-Bass
eigenvalue against the direct 2m x 2m non-backtracking matrix (1e-9), our
Brandes implementation against networkx (1e-14), igraph's betweenness against
our Brandes (1e-14), the percolation shortcut against direct per-seed IC
simulation (r = 0.9993), SIR with mu=1 against Independent Cascade (0.4%), and
deliberate injection of forbidden feature names into the leakage guard (all
caught, no false positives).

Documentation gate, `python verify_docs.py` (must print `ALL CHECKS PASSED`).
Besides the study/README consistency checks it has always run, since 2026-09-12
it also checks:

- **Record-block integrity** — every `<!-- BEGIN … sha256=… -->` block in
  `docs/archive/phase6_record.md` is extracted and re-hashed; the hash must equal
  the marker and the sidecar `results/phase6_doc_moves_20260912.json`, and the set
  of blocks must equal the sidecar's archive entries. An edited or missing archive
  block fails the gate.
- **Path and link resolution** — every `docs/…md` / `results/…md` token and every
  markdown link in the root `*.md` files, `docs/**`, `results/*.md`, the root
  `*.py` files, `influence/*.py` and `results/*.ps1` must resolve to a file, and
  every `#rec-…` anchor must exist in the record. Stale paths inside code
  comments that cannot be edited while the root-integration queue runs are
  allow-listed from the sidecar's `deferred_code_rewrites` and counted in the
  output; that count must reach zero once the queue drains.

---

## 10. Things that will bite you

**The leakage guard will stop you, on purpose.** If a feature name contains
`betweenness`, `pagerank`, `closeness`, `coreness`, `spread_` and so on, the run
aborts with `LEAKAGE DETECTED`. Those are global quantities and using them as
inputs would hand the model the answer key. If you genuinely have a local
feature that trips it, add it to `ALLOWED_EXCEPTIONS` in `influence/targets.py`
**with a written justification**. Never disable the guard. It runs on every grid
cell, not once at startup.

**Any new feature must be registered with a hop tag, a tier tag and a cost
group**, or it will silently vanish from the sweeps. `select_features` filters
on hop and tier; an untagged feature is invisible rather than loudly broken.

**And check it is not derived before you count it.** Run:

```bash
python analyse_features.py
```

The feature table reached 43 columns before anyone measured how many
*dimensions* it held. The answer was about five - and five of the six edge- and
subgraph-tier features turned out to be exact algebraic functions of node-tier
columns:

```
triangle_count     = clustering x k(k-1)/2
ego_net_edges      = triangle_count + k
edges_leaving_ego  = nbr_degree_sum - 2*triangle_count - k
ego_net_density    = ego_net_edges / [(k+1)k/2]
ego_net_size       = k + 1
```

That mattered because the depth-versus-richness experiment *compares tiers*. If
the tiers do not differ in information, the comparison is not measuring what it
claims to. `analyse_features.py` now checks this automatically - closed-form
identities to machine precision, effective dimensionality, and a per-tier test
of whether each rung can be predicted from the rungs below it.

A derived column is not useless: a tree cannot compute `clustering x k(k-1)/2`
and handing it the transform may help. What it cannot do is add information -
so it must never be counted as evidence that a tier carries anything of its
own.

**The BLAS can break silently and catastrophically.** A mismatched numpy/scipy
BLAS aborts the process with exit code 127 and no Python traceback, and the
first thing it kills is the `beta_c` eigenvalue call. If a run dies with no
error message, test the BLAS before anything else:

```bash
python -c "import numpy as np; A=np.random.rand(300,300); print((A@A).sum())"
```

**The leakage guard's exception list matches exact names only.** A legitimate
variant such as `ego_betweenness_normalized` or `collective_influence_4` will
trip the guard even though it is local. That is deliberate - fail loud, force a
deliberate decision - but it will surprise you if you extend `max_hop` past 3,
because `collective_influence_4` is not in `ALLOWED_EXCEPTIONS`.

**Re-running stage 1 overwrites the cache** for that tag, including the
cascades. Cascades are the expensive part - avoid unless you are deliberately
changing simulation settings.

**`sweep_<tag>.csv` resumes.** Delete it to force a clean re-run. The
out-of-fold predictions in `cache_oof_<tag>.npz` resume with it - the two are
written together and a resumed run extends both.

**The failure atlas needs `cache_oof_<tag>.npz`.** If `analyse_failures.py`
says it cannot find one, the sweep that produced your CSV predates prediction
storage. Delete `sweep_<tag>.csv` and re-run stage 2; there is no way to
recover the predictions without refitting.

**Cascade arrays are large** (~50-75 MB per network) and are excluded from
version control. They regenerate in seconds.

**igraph reindexes node IDs on load.** The mapping is preserved in
`Network.original_ids` - use it when joining back to anything external.

**Memory on big graphs.** Beyond ~50k nodes, 3-hop shells get expensive. Reduce
`max_hop` to 2, or sample nodes.

**If you sample seeds, `CascadeResults.n_nodes` is what you want**, not
`sizes.shape[0]`. With subsampled seeds `sizes` has one row per sampled seed,
not one per node, and `ignition_probability` needs the network size to turn a
fraction into a node count. It used to read the row count and silently rescale
the threshold to the sample.

**Windows specifics.** Paths use backslashes. `curl` in PowerShell is an alias
for `Invoke-WebRequest` and will not accept `-sLO` - use `curl.exe`, or just use
`fetch_data.py`.

**`structure.py` is not a feature module.** Everything in it is a whole-network
descriptor used to organise results across networks. Nothing in it may ever
enter the feature matrix. The leakage guard will *not* catch this mistake,
because those quantities never become columns in the feature table - keeping
them in a separate module from `features.py` is the only defence.

---

## 11. A complete worked example

From a clean clone to results on one network:

```bash
conda env create -f environment.yml
conda activate influence

python fetch_data.py
python stage1_prepare.py data/p2p-Gnutella08.txt 4000 1.5
python stage2_sweep.py p2p-Gnutella08 spread_mean 3 10
```

Stage 2 prints **one line per (radius, richness) cell** - sixteen lines for one
target on the current four-tier ladder, not four. The result of that run, on
6,299 nodes after cleaning, read back out of `sweep_p2p-Gnutella08.csv`:

```
  r=0 node                       f=   2 tau=0.6705 +/- 0.0012
  r=0 node+edge                  f=   2 tau=0.6705 +/- 0.0012
  r=0 node+edge+subgraph         f=   2 tau=0.6705 +/- 0.0012
  r=0 node+edge+subgraph+dynamic f=   2 tau=0.6705 +/- 0.0012
  r=1 node                       f=  17 tau=0.7927 +/- 0.0010
  r=1 node+edge                  f=  38 tau=0.7928 +/- 0.0009
  r=1 node+edge+subgraph         f=  62 tau=0.8021 +/- 0.0010
  r=1 node+edge+subgraph+dynamic f=  62 tau=0.8021 +/- 0.0010
  r=2 node                       f=  35 tau=0.8854 +/- 0.0006
  r=2 node+edge                  f=  80 tau=0.8854 +/- 0.0007
  r=2 node+edge+subgraph         f= 144 tau=0.8867 +/- 0.0007
  r=2 node+edge+subgraph+dynamic f= 145 tau=0.8867 +/- 0.0006
  r=3 node                       f=  45 tau=0.9124 +/- 0.0003
  r=3 node+edge                  f=  93 tau=0.9133 +/- 0.0003
  r=3 node+edge+subgraph         f= 168 tau=0.9159 +/- 0.0003
  r=3 node+edge+subgraph+dynamic f= 170 tau=0.9159 +/- 0.0003
```

It is read out of the CSV rather than pasted from a console because the second
run of a completed sweep takes the resume path and prints no per-cell lines -
it reloads all 640 stored cells and rewrites the CSV. Reproduce the table with:

```bash
python -c "import pandas as pd; d=pd.read_csv('sweep_p2p-Gnutella08.csv'); print(d[d.target=='spread_mean'].groupby(['radius','richness']).kendall_tau.agg(['mean','std','count']))"
```

**An earlier version of this README printed this block from the 43-feature
table**, before the ORCA orbit features existed, and the numbers there were
0.6705 / 0.7927 / 0.8852 / 0.9114 at full richness. The node-tier column is
still almost exactly that; what changed is that there is now a subgraph tier
above it worth having. That is the whole reason the stale numbers are called
out rather than quietly overwritten.

### Timings, measured rather than remembered

Stage 1 on this network is about 6 seconds total: 1.1s of cascades (4,000
percolation runs for all 6,299 seeds), 1.2s of feature extraction, 3.2s of
exact betweenness.

The sweep is the expensive part, and how expensive depends entirely on how much
you ask for. All four targets at ten seeds - 480 model fits - took **931
seconds** on 16 cores. One target at ten seeds is roughly a quarter of that.

An earlier version of this README claimed "about 90 seconds" for this example.
That was wrong by a wide margin even at one seed: the recorded `fit_seconds`
for the old twelve-cell single-seed run summed to 255 seconds. If you see a
timing claim in this project that you have not measured yourself, distrust it -
`cache_meta_<tag>.json` now records per-stage wall clock precisely so this
stops being guesswork.

### Reading the result

With only degree (r=0) the model ranks nodes at tau=0.6705. One hop lifts it to
0.8021, two to 0.8867, three to 0.9159. Paired within seed those hops are worth
+0.1316, +0.0846 and +0.0292, against a seed sd of about 0.001 - every one of
them is real by a wide margin.

Gnutella is the **only network in the five-network corpus that has not saturated
by r=3 on any target**: it is the only one where the r=2 -> r=3 gain clears twice
the paired seed sd on all four targets at once. Everywhere else at least one
target has gone flat by r=3 - betweenness on ca-GrQc (+0.0000), on ca-HepTh
(+0.0009) and on email (-0.0010), spread_cv and spread_resid on facebook. That
is the point. The locality horizon is not a constant, and measuring it is
therefore worth doing.

Notice also how little the richness ladder buys compared with a hop. At r=1 the
whole ladder from node-only to full richness is worth +0.0094; the next hop is
worth +0.0846, nine times more. The `node` and `node+edge` columns are identical
to three decimal places at r=1 and r=2 - **the edge tier buys essentially nothing
on this network** - and almost all of what small gain there is comes from the
subgraph tier, i.e. from the graphlet orbits. The one exception is r=3, where the
edge tier does clear the noise band, at +0.0009 +/- 0.0001.

Two caveats on that, both of which cost this project time to learn:

- An earlier version of this section claimed the richness columns were
  *identical to four decimal places* and that looking richer buys nothing. That
  was true on the 43-feature table and is no longer true: with orbits present
  the richness gain beats the seed noise at r=1, r=2 and r=3. It is small
  (+0.0094 / +0.0013 / +0.0035 for the WHOLE ladder, node -> full richness), but
  it is not zero, and "small but real" is a different claim from "zero". Those
  three are the whole-ladder gains, not the subgraph rung alone: the two
  coincide at r=1 and r=2 because the edge tier contributes ~0 there, but at
  r=3 the ladder splits +0.0009 edge and +0.0026 subgraph. The distinction was
  glossed here until 2026-08-31.
- None of this generalises off Gnutella. A tier being worthless here is a fact
  about Gnutella, not about the tier: on `facebook_combined` the subgraph tier is
  the largest richness effect anywhere in the corpus on betweenness at r=2. See
  finding 10 in `docs/study_doc_v2.md`, and section 20 there for betweenness
  generally.

  **The reported figure is +0.0436**, under the log1p objective adopted as the
  default on 2026-09-04. The superseded squared-error figure was ~~+0.1291~~ —
  roughly 3x larger, and inflated because minimising squared error on a target
  with skew 28.88 is dominated by a handful of huge-betweenness nodes. Three
  independent routes agree on +0.0436. See sections 26b and 26d.
