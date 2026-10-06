# Pre-registration — A2, ball-coverage curves

**Written 2026-08-28, before any coverage number was computed.**
**Author:** Rachit (with Claude)
**Answers review objection:** M3 (ball-coverage confound)
**Script that will test it:** `analyse_coverage.py` (not yet written at time of writing)

---

## Why this is pre-registered

This is the one analysis in the current backlog that can **undermine the project's
central claim**, and it costs nothing to run because the data is already cached. That
combination — cheap to run, dangerous to the thesis — is exactly the situation where
writing the prediction down afterwards is worthless.

The thesis is that r\*(ε) is a *locality horizon*: a property of the (network, target)
pair describing how far information about influence extends. The competing explanation
is much more boring: **r indexes how much of the graph you are allowed to see**, and
r\*(ε) is just the radius at which you have seen enough of it. On a graph with a small
effective diameter those are the same number, and the interesting reading is unearned.

SNAP reports a 90th-percentile effective diameter of **2.9** for email-Eu-core. If that
carries over to our symmetrised largest connected component, email's r=3 "local" view is
numerically the whole graph, and email is precisely the network that is anomalous in two
independent findings. That is not a comfortable coincidence and it is the reason for
this analysis.

---

## What will be computed

Per network, per r ∈ {0,1,2,3}, over every node v in the LCC:

```
|B_r(v)| / n     with   |B_0| = 1
                        |B_1| = 1 + degree
                        |B_2| = 1 + reach_within_2
                        |B_3| = 1 + reach_within_3
```

all four already columns in `cache_features_*.csv`. No fits, no traversal, no new cache.

Reported: median, IQR, and the fraction of nodes with coverage > 0.5. Then the existing
P(r) curves are re-plotted against **median coverage** and against **mean edges examined**
instead of against hop index.

---

## Predictions

Numbered so they can be scored individually. Each states what would falsify it.

**P1 — email has the highest 3-ball coverage in the corpus, and it is near-total.**
Median |B_3|/n on email-Eu-core > 0.90, and email ranks 1 of 5.
*Falsified by:* email not ranking first, or median below 0.90.

**P2 — coverage is driven by n, not by density.**
Rank order of median 3-ball coverage will track 1/n more closely than ⟨k⟩. Concretely:
email (n=986) above facebook (n=4,039) **despite facebook being the denser graph**
(⟨k⟩ 43.7 vs 32.6), and p2p-Gnutella08 (n=6,299, ⟨k⟩=6.6) lowest or second-lowest.
*Falsified by:* facebook above email, or the ordering matching ⟨k⟩ better than n.
*Why it matters:* if true, Finding 4's "the horizon is not a function of density"
survives contact with the coverage axis — coverage and density are not the same variable.

**P3 — the collaboration replication survives.**
ca-GrQc and ca-HepTh have median coverage curves within a factor of 2 of each other at
every r. Their r\*(ε) agreement (3 of 4 targets exact, §21) is therefore a replication of
mechanism and not an artefact of the two graphs happening to see the same fraction.
*Falsified by:* a factor > 2 gap at any r, which would mean the "same family, same
horizon" result is confounded by them simply seeing different amounts.

**P4 — email's two anomalies shrink or vanish on the coverage axis.**
The two are: (a) it is the only network where the r=3 subgraph gain exceeds the r=1 gain
(§20), and (b) it is the only network with no volatility-residual signal (§23).
Prediction: both of email's anomalous measurements sit at a coverage no other network
reaches at any radius, so they are **comparisons at non-comparable coverage** rather than
network-level anomalies.
*Falsified by:* another network reaching email's r=3 coverage (within 0.10) at some
radius and *not* showing the same behaviour there.
*Caveat, stated in advance:* if no other network gets near email's coverage, P4 is
**untestable on this corpus** rather than confirmed. That outcome must be reported as
"cannot be separated", not as support. This is the most likely outcome and it is the
argument for the synthetic corpus (§14).

**P5 — the blind-spot correspondence (Finding 8) partially survives.**
Finding 8 says the directional blind spot tracks how much the final hop still buys
(ρ = 0.900, n = 5). Prediction: p2p-Gnutella08 has the **lowest** 3-ball coverage and
also the largest directional δ, so coverage is a *partial* alternative explanation.
Specifically, Spearman ρ between median 3-ball coverage and directional δ will be
negative and |ρ| ≥ 0.7 — meaning the finding is at least partly a coverage effect.
*Falsified by:* |ρ| < 0.7, which would mean the blind spot is not reducible to how much
of the graph is visible.

---

## What each global outcome means

This is written now so that neither result can be spun later.

- **If coverage explains the anomalies (P4, P5 confirmed):** the honest conclusion is
  that a substantial part of what this project has been calling a *locality horizon* is a
  **sampling-fraction** effect, and the paper must be reframed around that. This would be
  a significant negative result about the project's own framing. It is still publishable
  and it is still the D2-shaped contribution — "the radius axis is confounded with the
  coverage axis and nobody controls for it" is a genuine evaluation-pitfalls finding, and
  it would apply to the whole literature, not just to us.

- **If coverage does not explain them (P4, P5 falsified):** r\*(ε) survives as a claim
  about information rather than about sampling fraction, and the coverage plot becomes the
  control that licenses the word "locality". This is the better outcome for the current
  framing and it is the weaker prior.

- **If it is untestable (the likely P4 outcome):** say so plainly and treat it as the
  single strongest argument in the document for running the generated corpus, where n and
  coverage can be moved independently.

**No outcome licenses dropping the coverage axis from the paper.** Whichever way it
falls, every P(r) figure gets a coverage twin from here on.

---

## Recorded constraints

- Coverage is computed on the **symmetrised largest connected component**, which is what
  the pipeline actually runs on. It will be *more* compact than the raw SNAP graph, so
  our coverage should come out **at or above** SNAP's published effective diameters would
  imply. The correction runs against us — i.e. it makes the confound worse, not better,
  which is the right direction for a check we want to be conservative.
- `reach_within_r` excludes the node itself; the `1 +` is not optional.
- These predictions are about **median** coverage. The distributions are expected to be
  heavily skewed and the IQR is reported for that reason; a median-based prediction
  scored against a mean would be a different claim.

---

# OUTCOME — scored 2026-08-28

Run: `analyse_coverage.py` → `results/RESULTS_coverage.txt`, `results/coverage.csv`.
Write-up: `docs/study_doc_v2.md` §17a.

| # | Outcome | Key number |
|---|---|---|
| P1 | **CONFIRMED** | email median r=3 coverage 0.9726, rank 1 of 5 |
| P2 | **FALSIFIED** | ρ(n)=−0.900 vs ρ(⟨k⟩)=+0.900 — an exact tie, not a win for density |
| P3 | **FALSIFIED** | 2.08× at r=1, just past the 2.0 threshold |
| P4 | **UNTESTABLE**, as pre-registered | nothing within 0.10 of email's 0.9726 |
| P5 | **FALSIFIED** | ρ = +0.300 — wrong sign, well under the 0.7 bar |

Three of five falsified. Two notes on how that was handled, recorded here rather than
only in the write-up:

- **P3's threshold was badly chosen** and this was obvious only after seeing the data.
  The two collaboration graphs have an *identical* median 1-ball (4 nodes); the 2.08×
  is exactly their size ratio. A ratio test on near-zero quantities is hypersensitive
  and the bound should have been stated on ball size. It is scored as **failed anyway**.
  The whole point of writing predictions down first is lost if the threshold moves after
  the fact, and the D2 paper this project is aiming at is an argument against exactly
  that practice.
- **P5 was scored wrong once.** The first parser of `RESULTS_failures.txt` ran past the
  directional block into the rescue table and gave ρ = −0.600, which would have been
  read as partial support. Caught by cross-checking all ten parsed Cliff's δ against
  §25's published table — four of five disagreed. Corrected parser reproduces all ten
  exactly. **The originally-reported −0.600 is void**; the number is +0.300.

**The headline outcome was not predicted by any of the five.** Coverage is a real and
severe confound *for email specifically* (97.3% of the graph at r=3), but it runs
opposite to the assumed direction: on email, going from 2.3% coverage to 97.3% buys
+0.0092 τ. The networks that gain the most coverage gain the least performance from it.
That strengthens the locality claim rather than weakening it, and it was not on the list.

Standing commitment from the "what each global outcome means" section above, now in
force: **every P(r) figure gets a coverage twin.**
