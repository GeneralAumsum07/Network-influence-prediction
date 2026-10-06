# Pre-registration — C3: zero-set inflation on the external betweenness benchmarks

**Written 2026-09-06, before any value in `results/betweenness/all_results.csv` was read
beyond the four paired drops already recorded in the vault (see "Prior exposure" below).**

Registered by: Rachit Samal. Phase 6, D2 track.

---

## 0. Prior exposure — stated up front, because it limits what this document can claim

This is **not** a clean-room pre-registration and must not be cited as one. Before writing it,
the following was already known from the 2026-09-05 code-reading session (vault log
`Logs/2026-09-05-brava-gnn-computes-d2s-metric-but-never-reports-it-a7-target.md`):

- `utils.py::ranking_correlation` in BRAVA-GNN takes a `compute_filtered` flag that computes a
  second Kendall τ over `keep = true_arr > 0` — exactly D2's nonzero-subset metric —
  and `betweenness.py:196` passes it unconditionally at test time.
- The shipped `results/betweenness/all_results.csv` has 395 configurations with both plain and
  `_filtered` rows across 14 graphs; **5,309 of 5,482 algorithm × graph cells drop**.
- Four specific paired values: web-Google 0.7928 → 0.2651, email-EuAll 0.9911 → 0.5535,
  wiki-Talk 0.9927 → 0.6526, wiki-topcats ≈ 5% relative drop.
- Within BRAVA's hyperparameter family the configuration *ordering* largely survives filtering
  (τ 0.87–0.999 between the two rankings; winner changes on 4/14 graphs). **C3 was therefore
  reframed on 2026-09-05 away from "show where the method ranking flips" — that claim is not
  supported by their own data — and toward the level claim: τ is inflated, by a graph-specific
  amount, and is therefore not comparable across graphs.**

What was **not** known and is genuinely predicted below: the zero fraction `z` of any of the 14
graphs, the boundary share `w`, the τ floor, and — critically — whether the size of the observed
drop is *quantitatively explained* by `z` alone. The four drops above were read as bare pairs; no
structural quantity was computed for any graph in the corpus, and the closed form of §24.4 has
never been evaluated outside this project's own five networks.

P1 and P3 below are therefore the load-bearing registrations. P2 is weakened by the exposure
above (four of fourteen drops are known, though their `z` values are not) and is labelled
accordingly.

---

## 1. What is being tested

§24.4 of `docs/study_doc_v2.md` derives, for a graph with zero fraction `z` and `m = 1 − z`:

```math
w_{\text{exact}} = \frac{2 n_z n_m}{n(n-1) - n_z(n_z-1)}, \qquad
w \to \frac{2z}{1+z}, \qquad
\tau_{\text{floor}} = w\sqrt{1-z^2} \to 2z\sqrt{\frac{1-z}{1+z}}
```

and §24.1 proves the zero set is decidable exactly from the radius-1 ego graph (`b(v) = 0` iff
`v` is simplicial). Together these say a published all-node τ-b is a **mixture** of a solved
radius-1 binary question and the open ranking problem, mixed at a ratio fixed by `z`.

BRAVA-GNN ships both halves of that mixture for 14 benchmark graphs and 395 configurations.
That makes the decomposition **externally falsifiable for the first time**: `z` is computed here
from graph structure alone, with no model and no reference to their numbers, and then used to
predict one of their published columns from the other.

---

## 2. Corpus and construction — fixed before running

The 14 graphs BRAVA-GNN reports on, obtained via **their own** `datasets/download.py`
(9 from SNAP, 5 from the ABCDE v1.0.0 release), and loaded under **their own** regime
declarations in `graph_regimes.py`, which are adopted verbatim rather than re-derived:

- **Genuinely directed (8):** wiki-Talk, wiki-topcats, email-EuAll, web-Google, soc-Epinions1,
  soc-Pokec, soc-LiveJournal1, soc-Slashdot0902.
- **Undirected (5):** cit-Patents, amazon, com-youtube, dblp, com-lj.
- **Undirected stored as digraph, symmetrised at load (1):** p2p-Gnutella31.

Deviating from their regime table would compute `z` for a different graph than the one their τ
was measured on, which is the single easiest way to make this analysis meaningless.

**Directed extension of the Proposition (new, and registered as a claim to be verified, not
assumed).** For a digraph, `b(v) = 0` iff for every in-neighbour `u` and out-neighbour `w` with
`u ≠ w` there is an arc `u → w`. Proof sketch, same shape as §24.1: if `v` is interior to a
geodesic then its predecessor `u` and successor `w` on that path satisfy `d(u,w) = 2`, so no arc
`u → w` exists; conversely if every such pair is joined directly, any path through `v` shortcuts.
This is stated as a proposition **and verified against `networkx.betweenness_centrality` on the
small graphs** (P4) before any `z` computed under it is used.

---

## 3. Registered predictions

Thresholds are fixed here and will not be moved after seeing the results.

### P1 — the mixture identity reproduces the published all-node τ (primary)

For each (algorithm, graph) cell with both a plain and a `_filtered` value, predict the plain
value from the filtered value and `z` alone, assuming perfect zero-set classification:

```math
\hat\tau_{\text{all}} = \frac{n_z n_m + \tau_{\text{filt}} \cdot \binom{n_m}{2}}
                             {\sqrt{\text{scoreable} \cdot \text{total}}}, \qquad
\text{total} = \binom{n}{2}, \quad \text{scoreable} = \text{total} - \binom{n_z}{2}
```

**Prediction:** median over all cells of `|τ̂_all − τ_all|` is **≤ 0.05**, and the median signed
error is **≥ 0** (the identity assumes *perfect* zero-set classification, so it should
over-predict, not under-predict, wherever a method misclassifies zeros).

**Falsified if** the median absolute error exceeds 0.05, or the median signed error is negative.
A negative signed error would mean methods score the boundary pairs *better than perfectly*,
which is impossible and would instead indicate the decomposition or the regime handling is wrong.

### P2 — the drop is graph-structural, not method-specific (secondary; weakened by prior exposure)

**Prediction:** across the 14 graphs, the median-over-algorithms drop `τ_all − τ_filt` is
positively rank-correlated with `z`, Spearman **ρ ≥ 0.5**.

**Falsified if** ρ < 0.5. Labelled secondary because four of the fourteen drops were already
seen (§0), though none of their `z` values were.

### P3 — published numbers sit near a floor a zero-set-only method reaches for free (headline)

Compute `τ_floor = w√(1−z²)` per graph.

**Prediction:** on **≥ 7 of the 14 graphs**, at least one shipped configuration's published
all-node τ is at or below `τ_floor + 0.05` — i.e. a published, peer-reviewed number that a method
doing nothing but the radius-1 simplicial test would match.

**Falsified if** this holds on ≤ 6 graphs. Note this is a claim about the *level* being
uninformative, not about any method being bad; the framing in the write-up must say so.

### P4 — the local certificate is exact on real benchmark graphs (verification gate)

**Prediction:** the zero set computed by the simplicial rule matches the zero set of exact
betweenness with **zero mismatches**, in both regimes, on:

- **Undirected:** the five ABCDE graphs, against the ground-truth betweenness scores shipped in
  the ABCDE v1.0.0 release (`<graph>-score.txt`) — millions of nodes, no computation needed.
  Conditional on those scores being exact rather than sampled; if the release states or shows
  they are approximate, this arm is reported as *consistency*, not verification, and the
  undirected gate falls back to the project's own five networks (already zero mismatches on
  24,120 nodes, §24.2).
- **Directed:** 30 random digraphs (`n` ≤ 300, densities spanning sparse to dense) against
  `networkx.betweenness_centrality`, exhaustively.

> **Amended 2026-09-06, before any graph was loaded and before any result was computed.** The
> original wording promised exact betweenness on "every graph with `n ≤ 100,000`", which is not
> achievable: Brandes is O(nm), so p2p-Gnutella31 alone (62k nodes, 147k edges) is ~10¹⁰
> operations in networkx — days, not minutes. The amendment does not weaken the gate; it
> strengthens the undirected arm (millions of real nodes instead of 62k) and makes the directed
> arm exhaustive rather than incidental, since the directed rule is the new claim and random
> digraphs sample its failure modes far better than one real graph would.

> **Second amendment, 2026-09-06, written _after_ seeing the ABCDE mismatch counts — read this as
> an invoked conditional, not a moved threshold, and judge it on that basis.** The first run of
> the undirected arm returned 0 mismatches on amazon (2,146,057 nodes), com-youtube (1,134,890)
> and dblp (4,000,148), but 662 on cit-Patents (3,764,117) and 1,086 on com-lj (3,997,962). Under
> the letter of "falsified by a single mismatch" the gate failed and P1–P3 were not reported.
>
> Two facts about the release, both checkable from the shipped files alone, trigger the
> "conditional on those scores being exact rather than sampled" clause above:
>
> 1. **The two failing files are clamped and the three passing ones are not.** The smallest
>    printed nonzero score in cit-Patents and com-lj is exactly `1.0e-14`, with **1,679** and
>    **3,802** nodes sitting on that value. amazon, dblp and com-youtube have **no mass at
>    1e-14 at all**, and only 3, 1 and 1 nodes respectively at their own minima
>    (4.3e-13, 2.2e-10, 1.1e-13). *Corrected 2026-09-07 after review: an earlier version of
>    this line said those three files have no node at their own minimum, which is false —
>    every file attains its minimum somewhere. The real contrast is a pile-up of thousands
>    versus a handful, and the detector keys on that mass, not on mere attainment.* A file that prints a
>    hard floor and piles mass on it is quantised, so for those two graphs the shipped column is
>    an approximation of betweenness, not betweenness.
> 2. **Every single mismatch is in the direction the clamp produces.** Across both graphs,
>    `rule = 0 & truth > 0` occurs **0 times in 7,762,079 nodes**; all 1,748 discrepancies are
>    `rule > 0 & truth = 0` — non-simplicial nodes of degree 3–18 whose true betweenness is below
>    the printing floor.
>
> The revised criterion is therefore **directional, and only on a file shown to be clamped**:
> clamping can push a true nonzero down to a printed zero, but it can never lift a true zero up to
> a printed nonzero. So `rule = 0 & truth > 0` remains a valid falsification test on quantised
> data and stays the gate; `rule > 0 & truth = 0` is counted and printed but cannot fail a clamped
> graph. On an unclamped file both directions must still match exactly, as originally registered.
> Clamp detection is in code (`gate_undirected_abcde`), not in prose, so the classification is
> reproducible rather than asserted.
>
> **Third amendment, 2026-09-07 — the mechanism named in the sentence above was unsound and
> has been replaced.** This amendment is required rather than optional: P4's verdict depended
> on that detector *programmatically* (`analyse_c3_benchmarks.py` gates whether P1–P3 are
> reported on its boolean), and the paragraph above cites the detector **by name** as part of
> the justification. So this is not the outcome-only case that could be corrected as a plain
> factual note; the registered conditional's stated mechanism changed and the registration has
> to say so.
>
> *What was wrong.* The detector inferred "clamped" from a mass of ≥ 100 nodes on a file's
> smallest positive value. Adversarial review produced a working false pass: on 100
> disconnected three-node paths with **exact** ground truth, a deliberately broken rule
> calling every node nonzero made the gate return `True`, relabel the exact minimum as
> "clamped at 1.0e+00", and excuse 200 genuine errors. Legitimate graph symmetry produces
> repeated minima, and 100 is an absolute count unrelated to corpus size, so the test
> false-passes and false-negatives. "Reproducible rather than asserted" was true and beside
> the point: it was reproducibly wrong.
>
> *What replaces it.* The quantised files are now a hard-coded set of two, `cit-Patents` and
> `com-lj`, verified independently of the heuristic they replace: **every one of the
> 15,043,174 values across all five shipped ABCDE score files is an exact integer multiple of
> 1e-14**, checked on the printed decimal text with `Decimal` rather than on floats, with zero
> exceptions — the release is rounded to 14 decimal places. Rounding to that grid only reaches
> zero where a graph has true positives below half a step, and cit-Patents and com-lj are the
> two files that show it. A 14-graph corpus is small enough to verify directly; a statistical
> proxy was the wrong tool. The old heuristic survives as a **non-blocking diagnostic** for a
> human inspecting a new file, labelled unsound for auto-gating in code, and nothing branches
> on it.
>
> *Count corrected 2026-09-07 (category (a), factual).* This amendment as first written gave
> the total as **14,943,174**. That is 100,000 too small: an independent streaming recount by
> `audit_c4_support.py` totals **15,043,174**, and the per-file counts already recorded
> elsewhere (3,764,117 + 3,997,962 + 2,146,057 + 4,000,148 + 1,134,890) sum to that. The error
> was a mistyped sum, not a mismeasurement - "every value, zero exceptions" is unaffected, the
> P4 subset denominators (7,281,095 + 7,762,079) were always computed from the per-file counts
> rather than this total, and no threshold, conditional or scored verdict moves. Corrected in
> place above and recorded here so the original figure is not silently overwritten.
>
> *Framing narrowed 2026-09-07 (category (a)).* Earlier wording called the smallest positive
> grid point a **clamp**. That is stronger than the evidence: grid membership establishes a
> quantisation grid, not a hard floor imposed by the generator, and it does not by itself
> establish the rounding mode or recover the pre-rounding magnitudes. The identifier
> `CLAMPED_ABCDE` is retained in code for continuity, and its comment now says so.
>
> *What did not change.* No measured quantity moves. The 662 and 1,086 sub-grid zeros, the
> zero rule failures over 7,762,079 nodes, and the three exact files were all produced by a
> direct read of the score files and reproduce identically under the replacement. The recorded
> verdict stands as before: consistency on those two files, verification on the rest.
>
> **What this costs.** cit-Patents and com-lj are downgraded from verification to **consistency**,
> exactly as the original wording provided for. The verification claim now rests on: 7,281,095
> real nodes across three unclamped ABCDE graphs at 0 mismatches, the project's own five networks
> at 0 mismatches over 24,120 nodes (§24.2, and the `w` table reproduced to four decimals), and
> 4,752 nodes across 30 random digraphs against `networkx` for the directed rule.
>
> **The honest weakness, stated rather than buried:** this reasoning was not written before the
> numbers were seen, and a reader is entitled to discount it accordingly. The defence is that the
> clause it invokes *was* pre-registered, and its trigger is an objective property of someone else's files.
>
> **Corrected 2026-09-07 after adversarial review.** An earlier version of this paragraph
> claimed the replacement test is "strictly harder to pass by luck" than the one it replaces,
> and described the 1,748 discrepancies as falsification opportunities taken and survived.
> **That was wrong, and it was the load-bearing sentence of the defence.** Testing one
> direction is mathematically *weaker* than requiring both mismatch counts to be zero, and
> the 1,748 discrepancies are precisely the ones the revised criterion *excuses* — they are
> not survived tests. The honest statement is narrower: the surviving direction
> (`rule = 0 & shipped > 0`) is a real test that a clamp cannot fake, it was applied to
> 7,762,079 nodes, and it recorded zero failures. That supports the recorded consistency
> downgrade. It does not establish exactness, and the amendment is a genuine weakening of
> the gate on those two files, disclosed as such.

**Falsified by a single mismatch.** P4 is a **gate**: if it fails, P1–P3 are not reported at all,
because every `z` in them would be computed by a rule that does not hold.

---

## 4. What this does NOT establish, registered in advance

- **Nothing about method quality or ranking.** The 2026-09-05 reframing stands: BRAVA's own data
  shows configuration ordering largely survives filtering. Any sentence in the write-up implying
  the ranking flips is out of scope and wrong.
- **Nothing about BRAVA-GNN as a paper.** They *compute* the nonzero τ and ship it; the finding
  is about a field-wide reporting convention, and their repo is the evidence that the metric is
  cheap to produce. This must be credited prominently, not framed as a gotcha.
- **No claim that τ_floor is what any method actually scores.** It is a lower bound reachable
  without learning; P3 tests proximity to it, not equality with it.
- **No re-running of anyone's model.** Nothing is trained. Every number on the BRAVA side is
  theirs as shipped; every number on this side is computed from graph structure.

---

## 5. Execution constraints

- **No model fitting** (Decision 9, 2026-08-27: nothing gets fit on the Windows env until
  WSL + cuML is up). C3 fits nothing — it is graph statistics plus arithmetic on a shipped CSV,
  which is outside that directive.
- Zero-set computation must use **early-exit** neighbourhood checking rather than materialising
  `deg²` pairs, or the hub-heavy graphs (wiki-Talk, soc-LiveJournal1) will not terminate.
- Exact betweenness for P4 uses `networkx`/Brandes on the small graphs only, never on the corpus.

---

## SCORED — (to be appended after the run, with the verdict table)

### 2026-09-06 — complete 14-graph corpus

The completed background run is preserved in `results/RESULTS_c3_benchmarks.txt`,
`results_c3_structure.csv` and `results_c3_cells.csv`. `score_c3_results.py` checks its
pairing against the shipped CSV, applies the support correction below, and writes
`results_c3_scored_cells.csv`, `results_c3_scored_graphs.csv`, `results_c3_controls.csv`
and `results/c3_scored_summary.json`. Input hashes are in
`results/c3_scored_provenance.json`. The scoring check reports **ALL CHECKS PASSED**.
No model was fitted. A fresh corpus traversal encountered a scratchpad read-permission
error at the time of first scoring; these results used the completed run, not an asserted
successful second traversal.

> **Superseded 2026-09-07.** The independent traversal has since been run. `analyse_c3_benchmarks.py` was re-executed from the raw edge lists, rebuilding every zero set from scratch, and `results_c3_structure.csv` / `results_c3_cells.csv` reproduced the originals except on the two cells the support correction is designed to move (cit-Patents geometric median signed error −0.0130 → −0.0129, com-lj tied +0.0003 → +0.0004, both from the shipped-zeros switch committed between the two runs). `score_c3_results.py` and `verify_docs.py` were then re-run against the regenerated cells and both report ALL CHECKS PASSED, so every figure quoted in this block and in §26i is true of the data currently on disk. The verdicts are unchanged. This paragraph is retained rather than deleted so the original limitation stays on the record.

**Population clarification:** 395 distinct algorithm names have paired rows, but six
names recur with distinct values, giving 404 paired row occurrences and **5,608 finite
paired observations** across 14 graphs. Occurrences are retained and paired in source
order; no deduplication or many-to-many join is performed. The earlier 5,482 figure in
§0 describes the prior reading, not this complete occurrence-level population.

| Prediction | Registered criterion | Measured result | Verdict |
|---|---|---|---|
| P1 | Median absolute error ≤ 0.05 AND median signed error ≥ 0 | **0.078564**, **−0.076970** using the shipped target support | **FALSIFIED**, on both clauses |
| P2 | Spearman ρ ≥ 0.5 across 14 graphs | **0.890110**; identical using structural or shipped z | **SUPPORTED**, secondary and weakened by prior exposure |
| P3 | ≥ 7/14 graphs with at least one τ ≤ registered geometric floor + 0.05 | **12/14**; exceptions p2p-Gnutella31 and wiki-topcats | **SUPPORTED as registered** |
| P4 | Zero mismatches, with the previously invoked clamped-score conditional | Directed: 0/4,752; unclamped ABCDE: 0/7,281,095; clamped files: 0 falsifying-direction discrepancies over 7,762,079 nodes | **PASSED under the registered conditional**; two files provide consistency only |

#### Support correction — structural zeros are not the shipped filter

BRAVA's `keep = true_arr > 0` filters its shipped target. The correction below changes
which support predicts that column; it changes **no registered threshold**. P2 and the
registered P3 retain structural z and the registered geometric floor. The original
structural-support P1 median absolute error also rounds to 0.078564; no verdict changes.

| Graph | Structural zeros | Shipped zeros | Structural z | Shipped z | Structural w | Shipped w |
|---|---:|---:|---:|---:|---:|---:|
| cit-Patents | 709,062 | 709,724 | 0.188374 | 0.188550 | 0.317028 | 0.317277 |
| com-lj | 1,150,616 | 1,151,702 | 0.287801 | 0.288072 | 0.446965 | 0.447292 |

For P4 on these two files, `rule = 0 & shipped > 0` remains falsifying and occurs
zero times. The opposite discrepancies, **662 + 1,086 = 1,748**, are retained and
reported as consistent with clamping, not counted as exact verification. The clamp
masses are 1,679 and 3,802 at 1e-14. The explanation that every discrepant value is
below the printing floor is an inference; exact positive magnitudes were not computed.
The five-project-network fallback is the existing exact-zero check on 24,120 nodes;
the completed C3 gate independently reproduces all five boundary shares to four decimals.
The post-observation timing and limitations of the second amendment remain binding.

#### All fourteen graph scores

Here z and the geometric floor are structural. The final column counts observations
meeting **the registered** test, including external controls, without changing its
one-sided inequality to absolute distance. A value below the floor also qualifies.

| Graph | z | Geometric floor | Median τ drop | Minimum shipped τ | Hits / paired observations |
|---|---:|---:|---:|---:|---:|
| amazon | 0.326893 | 0.465651 | 0.16450 | 0.1890 | 12/404 |
| cit-Patents | 0.188374 | 0.311353 | 0.12500 | 0.1535 | 12/404 |
| com-lj | 0.287801 | 0.428054 | 0.16090 | 0.1671 | 9/401 |
| com-youtube | 0.573210 | 0.597115 | 0.23145 | 0.3224 | 18/404 |
| dblp | 0.419574 | 0.536578 | 0.21970 | 0.1639 | 9/401 |
| email-EuAll | 0.960877 | 0.271450 | 0.43280 | −0.1176 | 26/401 |
| p2p-Gnutella31 | 0.460630 | 0.559835 | 0.16440 | 0.6544 | 0/404 |
| soc-Epinions1 | 0.634497 | 0.600090 | 0.26250 | 0.3230 | 15/401 |
| soc-LiveJournal1 | 0.355146 | 0.489976 | 0.19290 | 0.1465 | 12/398 |
| soc-Pokec | 0.219042 | 0.350640 | 0.09920 | 0.2197 | 9/398 |
| soc-Slashdot0902 | 0.411523 | 0.531433 | 0.14800 | 0.5184 | 9/398 |
| web-Google | 0.561119 | 0.595032 | 0.52570 | 0.1835 | 13/398 |
| wiki-Talk | 0.958774 | 0.278188 | 0.33440 | 0.0550 | 27/398 |
| wiki-topcats | 0.040070 | 0.076991 | 0.03220 | 0.2146 | 0/398 |

#### P1 diagnosis and P3 sensitivity — POST-HOC, not replacement registrations

If predictions tie on the zero set, τ-b's denominator becomes `scoreable` rather
than `sqrt(scoreable * total)` (assuming no additional ties in the positive block).
The corresponding mixture is `w + (1−w)τ_filtered` and its zero-skill reference is
**w**. For continuous predictions the geometric expression and its discounted floor
apply. Both also assume perfect separation of zeros and positives. Neither expression
is a universal identity for arbitrary scores, nor is the reference a deterministic
lower bound under arbitrary negative ordering of the nonzero block.

BRAVA's `utils.py::graph_to_adj_bet` masks adjacency rows, providing the mechanism for
shared zero-set embeddings/scores. Across **5,278 `baseline_*` observations**, the tied
formula has median absolute error **0.000039** (0.0000 to four decimals), versus
**0.078296** for the registered formula. **This is a median fit, not exact reproduction
of every configuration:** the tied maximum is **0.715413**, on an email-EuAll
`baseline_random_*` row. Prediction arrays and tie metadata are not shipped in this
table; a row prefix alone cannot prove all mixture assumptions. These exceptions
remain in the analysis and are not removed to improve the diagnosis.

Using w indiscriminately gives 13/14 graphs, but that applies a tied-prediction
assumption to external methods too. The illustration using shipped w for `baseline_*`
and the geometric comparator for other rows gives **12/14**; its tie assignment is
conditional, not independently measured per row. **The registered P3 verdict is the
12/14 result above**, not either post-hoc substitution.

The external-method control fits neither expression well (median absolute errors):

| Family | Observations | Geometric | Tied |
|---|---:|---:|---:|
| DrBC | 42 | 0.184297 | 0.271664 |
| KADABRA | 42 | 0.261604 | 0.392771 |
| SILVAN | 126 | 0.190562 | 0.261353 |
| Bavarian | 18 | 0.152104 | 0.339543 |
| ABCDE | 18 | 0.112762 | 0.189548 |

The sampling approximators and the learned DrBC baseline are controls for the
perfect-separation/masking assumptions; DrBC is not itself a sampling approximator.
The contrast supports the mask diagnosis, without proving the cause of every residual.
BRAVA-GNN deserves prominent credit: it **computes and ships the nonzero-subset τ**,
making this inexpensive re-analysis possible. Configuration ordering largely surviving
filtering (the prior τ 0.87–0.999 result) stays the framing. No method-ranking flip,
method-quality judgement, or claim that this work invented the filtered metric follows.
