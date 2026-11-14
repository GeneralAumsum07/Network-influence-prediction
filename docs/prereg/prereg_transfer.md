# Pre-registration: leave-one-graph-out transfer

**Registered:** 2026-11-14, before any cell of `probes/probe_transfer.py` was fitted.
**Code:** `probes/probe_transfer.py` (fits), `analysis/analyse_transfer.py` (scoring).
**Outputs:** `results/transfer/`, `results/RESULTS_transfer.txt`.

## Why

Every P(r) in this project is measured inside one graph: 5-fold out-of-fold predictions,
with the training labels taken from 80% of the same network's nodes. The study names the
clean version - train on some networks, test on an entirely separate one - and never runs
it ("Single-graph CV is not true transfer: still open", study doc, risks table). It is
also the version the partial-observability motivation needs: an observer who cannot see
the graph cannot compute ground-truth influence for 80% of its nodes, so whatever model it
uses must have been trained elsewhere.

Within-graph CV is known to be optimistic. Buffered CV (study doc 26k.2) costs about 0.09
tau at buffer 1 when training nodes near the test nodes are removed. Transfer is the
limiting case of that: no training node is in the test graph at all.

**Disclosure.** A single-seed pairwise check made on 2026-11-08 from the committed caches
(not part of this repository) informed the predictions below. That check found transfer
gaps at r=3 of -0.03 (ca-GrQc <-> ca-HepTh) to -0.08 (ca-GrQc -> p2p) on spread_mean,
and -0.23 on facebook_combined -> email-Eu-core betweenness. The registered protocol
differs (pooled training on four networks, three seeds), so it is not a re-run.

## Protocol

- **Corpus:** the five prepared networks. Registries are identical across networks (171
  columns), checked at run time.
- **Folds:** each network is held out once. The model trains on the other four.
- **Training rows:** up to 2,000 nodes drawn uniformly from each training network, so no
  network dominates by size. The draw depends on the seed.
- **Features:** the richest structural tier, `node+edge+subgraph`, at hop <= r, for
  r = 0..3. Column order is the registry's. The leakage guard runs on every cell.
- **Target encoding:** each network's target is replaced by its within-network percentile
  rank before training. This is a monotone transform per graph, so it changes no
  within-graph ordering. It removes the scale differences between networks, whose
  cascades are not in the same absolute range.
- **Model:** `influence.estimators.make_rf(seed)`, the project's frozen forest.
- **Score:** Kendall tau-b, and precision at 1% and 5%, on all nodes of the held-out
  network, against its original target.
- **Targets:** `spread_mean` and `betweenness`.
- **Seeds:** 0, 1, 2. A seed fixes both the training subsample and the forest.
- **References:**
    - within-graph out-of-fold P(r) at the same tier: `analysis/analyse.py::load`, with
      the log1p betweenness arm spliced in;
    - tau_b(y, degree);
    - the best single closed-form rule at radius r, from `analysis/analyse_closed_form.py`.

## Predictions

**P1 (level).** At r=3, transfer tau is below within-graph tau on all five networks for
`spread_mean`, and the mean gap over the five is at least 0.02.

**P2 (the radius gain survives).** For each target, transfer tau at r=3 exceeds transfer
tau at r=0 by more than twice the seed sd on at least four of five networks.

**P3 (betweenness on the dense pair).** For `betweenness` at r=3, the transfer gap is at
least 0.05 on email-Eu-core or on facebook_combined: the two dense networks are each
other's only dense training example.

**P4 (learned versus closed form, deployable setting).** At r=3, transfer tau beats the
best single closed-form rule at r=3 on at least three of five networks for
`spread_mean`.

**Counter to P4.** The best closed-form rule matches or beats transfer on at least three
of five networks. The learned combiner would then add nothing a single formula does not,
once its labels must come from other graphs. Note that the closed form's best rule is
chosen in-sample from about six rules, which favours the counter.

## Scoring

- "Beats" and "exceeds" mean the difference in seed-mean tau is positive. Where a
  prediction names twice the seed sd, the sd is over the three transfer seeds.
- Each prediction is scored as SUPPORTED or NOT SUPPORTED, with the per-network values
  printed beside it.
- No rule is changed after the first cell is fitted. Any deviation is recorded in a dated
  addendum below, never by editing the text above.

## Addendum, 2026-11-14 - a post-hoc arm without the graph-size column

Written after the first 10 primary cells (ca-GrQc, `spread_mean`, r = 0..3) were printed,
and before any other cell was seen. Nothing above changes, and the primary arm runs to
completion as registered.

Those cells put transfer tau at r=0 between 0.53 and 0.70 on ca-GrQc. The r=0 features
are `degree` and `degree_normalized` = k/(n-1), and tau_b(y, degree) is 0.82 there. The
likely cause is `degree_normalized`. It is the one column defined with a global constant,
n, and it maps the same degree to different values in graphs of different size. A forest
trained on four graphs can split on it and turn a monotone degree signal into a
non-monotone one on the fifth graph.

A secondary arm, labelled POST-HOC everywhere it is reported, repeats the registered grid
with `degree_normalized` excluded. Its output goes to `results/transfer_nosize/`. It is
reported beside the primary and is not used to score P1-P4.

## Addendum 2, 2026-11-14 - a post-hoc arm with per-graph percentile features

Written after 35 of the 120 primary cells (ca-GrQc, ca-HepTh, and email-Eu-core up to
r=3) were printed, and after two single-seed exploratory fits described below. Nothing
above changes.

What was seen. Held out, email-Eu-core collapses as the radius grows: spread_mean
transfer tau is 0.87 at r=0, 0.49 at r=1 and about 0.33 at r=3, against within-graph
P(r) above 0.95. ca-GrQc at r=1 and r=2 has precision at 1% of zero.

What the exploratory fits showed (seed 0, spread_mean):

| holdout, r | registered | without `degree_normalized` | node tier only | per-graph percentile features |
|---|---|---|---|---|
| email-Eu-core, r=1 | 0.47 | 0.40 | 0.55 | 0.91 |
| ca-GrQc, r=1 | 0.70 | 0.74 | 0.72 | 0.85 |

Removing `degree_normalized` does not explain the collapse; on email-Eu-core it makes it
worse. The candidate cause is covariate shift in raw feature scale. email-Eu-core is
dense (mean degree about 33), so its count features (`nbr_degree_sum`, `ego_net_edges`,
orbit counts) lie far outside the range of the four sparser training graphs. A forest
cannot extrapolate: every such node lands in the training graphs' extreme leaves, and the
ordering among them is lost.

Arm 2. Repeat the registered grid with every feature column replaced, per graph, by its
within-graph percentile rank, the same transform the target already gets. Output:
`results/transfer_featrank/`. Labelled POST-HOC, reported beside the primary, not used to
score P1-P4.

What arm 2 changes about the information budget. A percentile rank needs that column's
distribution over the graph's nodes, a global summary, in the same way that
`degree_normalized` needs n. It uses no labels, and no node's rank depends on structure
outside its own r-ball except through that one-dimensional distribution. An observer who
collects the r-balls of a sample of nodes can estimate it from the sample. Arm 2 is
therefore not a strictly local predictor, and its results must not be read as P(r) of
one. Arm 1 runs as stated in addendum 1.
