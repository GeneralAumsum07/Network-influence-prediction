# Local Network-Based Influence Prediction
## Study Document — Pipeline, Results, and Glossary

---

## 0. How to use this document

**Current scope, 2026-09-09:** Phase 6 is reopened under the authorised training
extension. The structural target-bootstrap pilot has completed 120 cells and the
12,000-cell full run is in progress. Buffered CV, targeted external precision
witnesses, the matched five-network radius-one ablation, and the final codebase
audit remain pending. See [the live extension ledger](archive/phase6_record.md#rec-phase6_extension_20260908).
The dated September 7 no-fit completion statements describe that earlier scope;
they do not certify this extension. Phase 7 remains deferred.

This is the working reference for the project. It explains **what we are doing, why each step exists, what tool does each job, and what we have measured so far.**

**Part VIII is a complete glossary.** Every technical term and every mathematical expression used anywhere in this document is defined there in one or two plain sentences. If a word or symbol is unfamiliar, look it up there first — nothing is assumed.

Three conventions used throughout:

- **Inputs** are always *local* — computed from a bounded neighbourhood around a node.
- **Targets** are always *global* — computed from the whole network, and are what we try to predict.
- **Baselines** are rival methods we must beat, or honestly report losing to.

The single rule that protects the entire project: **a global measurement may never appear as an input feature.** Breaking it invalidates every result downstream. This rule is enforced in code (`assert_no_leakage`), not just by discipline.

**Nothing in this project is inherited.** We take no published result, no reported number, and no claim about which radius works as given. Algorithm *definitions* are specifications we implement ourselves and then verify against an independent reference. Every number in Part VII is one we measured.

---

# PART I — THE PROBLEM

## 1. The research question

Can we predict how influential a person is in an **entire** network, using only information visible in their **local neighbourhood** — their friends, friends-of-friends, and perhaps one hop further?

### 1.1 Why the constraint matters

*(Rewritten 2026-08-28. The previous version of this subsection argued from compute cost. That argument does not survive contact with the algorithms literature, and it is replaced rather than patched.)*

Influence is defined globally. The question is what happens to an observer who cannot see globally — and the reason such an observer exists is **not** that the global computation is too expensive.

It usually is not expensive. PageRank, eigenvector, Katz and coreness are near-linear in the number of edges and run routinely on graphs of 10⁹ edges and beyond. Betweenness has Brandes' algorithm exactly, and both VC-dimension sampling (Riondato–Kornaropoulos) and adaptive sampling (KADABRA) approximately, with guarantees. Influence spread under Independent Cascade — #P-hard to compute exactly — has reverse-reachable-set sketches (Borgs et al.; TIM, IMM, SSA) that reach (1 − 1/e − ε) at billion-edge scale. A referee at KDD or WWW knows this, and any motivation resting on "too large to process" is refuted in a sentence.

**The constraint that does not dissolve is observational, not computational.** Consider:

- a crawler behind an API rate limit, permitted a few thousand requests a day against a graph of millions;
- a node inside a decentralised protocol, which by construction knows its own peers and nothing beyond them;
- a platform barred by privacy regulation from joining data across users, even though it physically holds all of it;
- an analyst working from a sampled subgraph, with no mechanism to obtain the remainder.

**None of these can see the whole network at any compute budget.** Buying a larger machine does not help a crawler that is rate-limited, or a protocol node that is not permitted to ask. For such an observer, "how far must I look?" is not a tuning decision — it is the whole problem.

This reframing does real work, and it changes what the rest of this document is claiming:

1. **The small, exactly-solvable corpus is the correct instrument.** We work at a scale where the true global influence is still exactly computable *because that exact value is the ground truth our local predictions are graded against*. Scaling the corpus up would remove the grader. This is a design choice, not a limitation we are apologising for.
2. **Radius-as-measurement is the centrepiece**, not a defensive move.
3. **Angle 4 becomes the same question under a noisy observation channel**, rather than a separate robustness study — which situates it inside the measurement-error literature on centrality (Costenbader–Valente 2003; Borgatti–Carley–Krackhardt 2006; Martin–Niemeyer 2019) instead of leaving it unanchored.

### 1.2 Our data: real network corpora

We train and test on **real networks already used in this literature**, rather than generating our own. The reason is comparability: this subfield shares a benchmark convention — spreading-process ground truth, Kendall τ and top-k overlap, roughly ten to twelve real networks. Adopting that convention exactly makes our numbers directly comparable to published ones instead of only internally consistent.

**Networks used so far** (all from the SNAP pilot set, all processed by our own pipeline). β_c is this network's own epidemic threshold from the non-backtracking operator; every value below is read from that network's `cache_meta_<tag>.json`, not remembered:

| Network | Nodes (after cleaning) | Edges | Mean degree | β_c | Character |
|---|---|---|---|---|---|
| ca-GrQc | 4,158 | 13,422 | 6.46 | 0.02250 | Sparse collaboration network |
| ca-HepTh | 8,638 | 24,806 | 5.74 | 0.03333 | Sparse collaboration — same-family replicate of ca-GrQc |
| email-Eu-core | 986 | 16,064 | 32.58 | 0.01338 | Dense communication network |
| facebook_combined | 4,039 | 88,234 | 43.69 | 0.00620 | Dense social — union of 10 ego networks |
| p2p-Gnutella08 | 6,299 | 20,776 | 6.60 | 0.03772 | Sparse peer-to-peer network |

The first two of the original three were chosen deliberately as a contrast: one sparse, one dense. As Part VII shows, that contrast turned out to matter a great deal. Gnutella was added as a second sparse network and behaves differently again from ca-GrQc.

**The 2026-08-27 expansion added a matched pair, one on each arm**, rather than simply more data. ca-HepTh is the same generative process as ca-GrQc at near-identical density, so it tests *replication*. facebook_combined is a second dense network to set against email-Eu-core, so it tests whether "dense" was ever the operative variable. Both returned informative answers — and both revised existing findings. See Findings 4, 6 and 10.

**All five run at identical dynamical settings:** p = 1.5 × β_c, 4,000 percolation runs, uniform convention. This matters more than it looks. An earlier version of the corpus ran email-Eu-core at 1.2 × β_c while the other two ran at 1.5 ×, which silently reintroduced the exact confound the β_c normalisation exists to remove — and Finding 4 is a *cross-network* claim. The mismatched cache is retained under `cache_archive/` because the two runs together are the start of a p-multiple sweep worth doing properly.

**Corpus to expand into:** the remaining SNAP pilot set (ca-HepTh and ego-Facebook are already downloaded), the Erkol network list, the Banerjee village networks, Netzschleuder, and ICON — plus the generated corpus described in §14, which supplies the structural control real networks cannot.

**Scale rationale.** We work at a scale where the true global influence remains exactly computable. That computability is essential: it is the ground truth our local predictions are graded against.

### 1.3 The core vocabulary

Full definitions are in Part VIII. The four terms you cannot read further without:

| Term | Meaning |
|---|---|
| **Hop** | One step along an edge. 1-hop = direct friends; 2-hop = friends-of-friends. |
| **r-ball** | Everything within r hops of a node. |
| **Ego-network** | A node (the *ego*), its direct friends (*alters*), and all edges among them. |
| **Local feature** | A number computable from a bounded neighbourhood only. |

---

## 2. Defining influence: three targets

"Influence" is vague, so we pin it to three measurable quantities. A node can score high on one and low on another — that disagreement is itself a finding.

### 2.1 Target A — Bridge influence (betweenness centrality)

```math
b(v) = Σ_{s≠v≠t}  σ_st(v) / σ_st
```

**Plain meaning:** the fraction of everyone's shortest paths that route through you. High betweenness means you are a broker between otherwise-separate groups; remove you and the network fragments.

**Why it is global:** to know which shortest paths pass through v, you must know shortest paths between *every pair* in the network. No local patch contains this.

**Why it is not just popularity:** a node with two friends can have high betweenness if those two friends belong to different regions of the network.

### 2.2 Target B — Spread influence (expected cascade size)

```math
σ(i) = E[ |R(i)| ]
```

**Plain meaning:** start a rumour at node i, let it spread at random, and count how many people eventually hear it. Average that over many runs.

Because it is stochastic, we estimate by **Monte Carlo**:

```math
σ̂(i) = (1/M) Σ_{m=1..M} |R_m(i)|          SE = s / √M
```

M is the number of runs and s the sample standard deviation. We choose M so that each node's standard error is far below the spread *between* nodes — otherwise we would be ranking simulation noise rather than real differences. Our runs report a ratio of 0.0036, comfortably safe.

### 2.3 Target C — Spread volatility

```math
CV(i) = sd(|R(i)|) / σ(i)
```

**Plain meaning:** two seeds can have the same average reach but behave completely differently — one reaches ~200 people almost every time, another usually reaches 5 but occasionally 800. CV measures that unreliability on a scale-free basis.

**Why it matters:** the averaged number erases the difference between a *reliable broadcaster* and a *lottery ticket*, which is exactly the distinction a practitioner cares about.

**The trap, and the control.** Variance is mechanically coupled to the mean — a seed reaching 500 has more room to vary than one reaching 3. Predicting raw variance would largely re-predict the mean in disguise. Two controls, both implemented:

1. Predict **CV** rather than raw variance (scale-free).
2. Predict the **variance residual**: fit the expected spread-versus-mean relationship non-parametrically, then predict only what is left over.

```math
Var(i) = f(σ(i)) + ε_i     →  predict ε_i from local features
```

### 2.4 The Independent Cascade mechanism

The spreading rule we simulate:

1. The seed node starts active; all others inactive.
2. When a node *first* becomes active, it gets **one** attempt to activate each inactive neighbour, succeeding independently with probability **p**.
3. Success or failure, that attempt is never repeated.
4. Newly activated nodes act in the next round.
5. Repeat until a round produces no new activations. Count the total activated.

**Edge probability conventions.** The convention silently changes results, so it is an explicit parameter, never a buried default:

| Convention | Rule | Note |
|---|---|---|
| uniform | p on every edge | Simplest; inflates hub influence |
| weighted cascade | p_uv = 1/degree(v) | Normalises each node's incoming pressure |
| trivalency | p drawn per edge from {0.001, 0.01, 0.1} | Standard in benchmarking |

We report under at least two. A spreading process with a rate parameter is a fourth convention that does not map exactly onto any of them.

---

## 3. Choosing p: the epidemic threshold

This was a real problem and it has a principled solution.

**Why the obvious approaches fail.** Fixing p = 0.05 everywhere is meaningless: on a dense network that is far above the tipping point (everything reaches everyone) and on a sparse one far below (nothing spreads). Comparing networks at fixed p compares different dynamical regimes. Alternatively, picking the p that maximises the spread of influence scores is confounded with scale — larger p means larger cascades means larger raw variance, so the criterion just chases the top of whatever range you searched. **We confirmed this failure empirically before discarding the method.**

**The solution.** Compute each network's own critical threshold and work at a fixed *multiple* of it. Then "p = 1.5 × β_c" means the same dynamical regime on every network, and cross-network comparison is finally valid.

### 3.1 The non-backtracking operator

The naive estimate β_c = 1/λ₁(A) using the adjacency matrix is poor on networks with hubs, because the leading eigenvector localises on a hub and drags the estimate around. The better operator tracks walks that never immediately step back where they came from:

```math
B[(i→j), (k→l)] = 1  if j = k and i ≠ l,  else 0
```
```math
β_c = 1 / λ₁(B)
```

B is 2m × 2m, which is large. The **Ihara-Bass identity** gives the same leading eigenvalue from a 2n × 2n matrix:

```math
M = [[ A,  I − D ], [ I,  0 ]]
```

where A is adjacency, D the degree diagonal, and I the identity. We implemented both, and verified they agree to 1e-9.

### 3.2 What we measured

| Network | β_c (non-backtracking) | β_c (adjacency) | β_c (mean-field) |
|---|---|---|---|
| ca-GrQc | 0.02250 | 0.02192 | 0.05889 |
| email-Eu-core | 0.01338 | 0.01311 | 0.01358 |

**Finding.** On the dense network all three agree. On the sparse network the mean-field estimate is wrong by a factor of 2.6. This is concrete evidence that the non-backtracking operator is a necessity rather than a refinement — and it is our own measurement, not an inherited claim.

**Finding.** Sweeping p as a multiple of each network's own β_c, the between-node coefficient of variation *peaks near criticality* (roughly 1.0–1.5 × β_c) and falls away on both sides. Discriminability between nodes is highest near the tipping point, which is where we therefore run.

---

# PART II — THE FEATURES

## 4. What makes a feature "local"

A feature is local if computing it for node v requires only the r-ball around v, for small r. Degree is local (count your own edges). Betweenness is not (requires all-pairs shortest paths).

Two further quality criteria: a feature must **vary across nodes** (a constant teaches nothing), and must not be a **trivial duplicate** of another.

## 5. The two tagging axes

Every feature carries two tags, and this is what makes the experiments cheap.

**Hop tag** — the smallest radius that can compute it:

- hop 0: the node's own edges only
- hop 1: the node + its neighbours + edges among them (the ego network)
- hop 2: adds friends-of-friends
- hop 3: adds one ring further

**What "radius r" grants, precisely.** At radius r an observer knows which nodes lie within r hops, the edges among them, and the degrees of the nodes on the boundary. The boundary-degree allowance is what makes `h_index_1`, `collective_influence_1` and `edges_leaving_ego` hop-1 features — each needs neighbours' degrees and nothing more.

This convention has to be applied consistently, and originally it was not. Ten features — `nbr_clustering_*` and `nbr_triangles_*` — were tagged hop 1, but a neighbour's clustering coefficient is decided by the edges *among that neighbour's neighbours*, which sit at distance 2. Edges between two distance-2 nodes are not inside a 1-ball, so those features are hop 2 and are now tagged as such.

The looser reading — "a neighbour can simply tell you its clustering coefficient" — is one this project already rejects elsewhere: under it `shell_2_degree_mean` would also be hop 1, and it has always been tagged hop 2. Under that reading a neighbour could equally report its betweenness, and the whole locality framing collapses.

The mis-tagging mattered. It put 2-hop information into the r=1 column, which inflated P(1), depressed the measured r1→r2 gain, and therefore biased r\* **downward** — on exactly the column the saturation claims are read from. Correcting it moves real numbers: ca-GrQc spread volatility at r=1 fell from 0.7179 to 0.6706, and the gain it had been absorbing reappeared at r=2.

**Tier tag** — what object the feature describes:

- `node`: properties of the node itself
- `edge`: properties of its incident edges, aggregated
- `subgraph`: counts of small structures it participates in
- `dynamic`: a local estimate of the spreading process itself

Radius and tier are independent axes. That is deliberate: it lets us ask whether it is better to look **further** (more hops) or look **richer** (more tiers) for the same compute budget.

### The tier axis has to actually vary information, and once it did not

A feature audit (`analyse_features.py`) found that **five of the six original edge- and subgraph-tier features were exact algebraic functions of node-tier features**, verified to machine precision on all three networks in the corpus at the time (ca-GrQc, email-Eu-core, p2p-Gnutella08):

```math
\begin{aligned}
\text{triangle\_count} &= C(i)\cdot k(k-1)/2 \\
\text{ego\_net\_edges} &= \text{triangle\_count} + k \\
\text{edges\_leaving\_ego} &= \text{nbr\_degree\_sum} - 2\,\text{triangle\_count} - k \\
\text{ego\_net\_density} &= \text{ego\_net\_edges}\,/\,[(k+1)k/2] \\
\text{ego\_net\_size} &= k + 1
\end{aligned}
```

So `node → node+edge` added **exactly zero** information, and `+subgraph` added only `ego_betweenness` — the single genuinely independent non-node feature in the original table. The richness ladder was not varying richness.

That is not a small bookkeeping point. It is the explanation for Finding 3 (§20): "richness does not help" was really "adding ego-betweenness does not help, except for betweenness itself, where §24 shows exactly why it must."

The table now contains genuinely independent edge and subgraph structure (§6.4, §6.8), and `verify_pipeline.py` carries a standing guard so that a derived column cannot be reintroduced unnoticed.

**A derived column is not useless, and the distinction matters.** A tree cannot compute `C(i)·k(k-1)/2`; it approximates products with axis-aligned splits, so handing it the transform can help. What a derived column cannot do is add *information* — and the measured gain of ≈0 says the forest did not need the help.

Because of the tagging, the radius sweep is a one-line filter (`select_features`) rather than a rewrite.

## 6. The implemented feature set (171 features)

Counts by radius are cumulative: a radius-r observer may use **2** features at r=0, **62** at r=1, **145** at r=2 and **170** at r=3.

By tier: 45 node, 48 edge, 76 subgraph, 2 dynamic.

Two details that trip people up when they reconcile these numbers against a run:

- **171 registered, 170 reachable.** One subgraph column — `orbit_15_g5`, the endpoint of an induced **5**-path — is tagged hop 4, because that is the radius at which it is actually measurable: the far end of a P5 sits four steps away. (The induced-*P4* endpoint is a different orbit, number 4, and it is hop 3.) See §5 on measuring rather than deriving the radius tag. `MAX_HOP` is 3, so the sweep never selects it. It is registered anyway rather than deleted, because deleting it would quietly turn "we measured this orbit's radius and it was out of range" into "this orbit does not exist". The full ORCA accounting chain — 73 emitted → 71 registered → 70 selectable — is tabulated in `HANDOFF.md` §7.3, and `verify_docs.py` asserts every step of it.
- A sweep cell at r=3, richest **structural** tier, reports **168** features, not 170: the two `dynamic` columns are excluded from every headline claim because they assume the observer knows *p*.

The earlier 64-feature table is what you get today if `vendor/orca.exe` is absent — the 107 orbit columns (71 node-orbit, 36 edge-orbit) drop out together and the rest is unchanged. The node tier is untouched at 45 either way; the growth is entirely edge (14 → 48) and subgraph (3 → 76).

**Tier correction, 2026-08-31.** The edge/subgraph split read 50/74 until a project-wide code audit moved `ball2_density` and `local_conductance_2` from the edge tier to the subgraph tier. Both aggregate the edges *among* 2-ball members rather than the node's own incident edges, which is what §6.4 defines the edge tier to be; `ball2_edges`, computed from the identical array, was already subgraph. Because the richness ladder is nested, the mis-tag let the `node+edge` rung at r ≥ 2 reconstruct `ball2_edges` exactly, so the rung meant to be structure-blind was reading 2-ball structure. 400 of 3,200 sweep cells were refitted; §26a is the finding it rewrites.

### 6.1 Hop 0 — the node itself

| Feature | Meaning |
|---|---|
| `degree` | Number of direct neighbours |
| `degree_normalized` | degree / (n−1); a rescaling for cross-network comparability |

**A note on `degree_normalized`, since a reviewer will ask.** It divides by n, and a strictly local observer does not know n. We keep it, and describe it precisely as *degree rescaled by a known global constant* rather than as a local measurement. The distinction is real but narrow: n carries no information about anyone's connections, and within a single network the feature is rank-identical to `degree`, so it cannot affect any within-network result. It earns its place only in cross-network transfer, where the two networks differ in size — which is exactly the experiment it is there for.

### 6.2 Hop 1 — ego-network structure

| Feature | Meaning |
|---|---|
| `clustering_coefficient` | Fraction of your neighbour pairs that are themselves connected |
| `triangle_count` | Triangles through the node **(derived: = C·k(k−1)/2)** |
| `ego_net_size` | Nodes in the ego network **(derived: = k+1)** |
| `ego_net_edges` | Edges inside the ego network **(derived)** |
| `ego_net_density` | Ego-net edges / possible edges **(derived)** |
| `edges_leaving_ego` | Edges from your neighbours to nodes outside your ego net **(derived)** |
| `effective_size` | Burt's measure: count of non-redundant contacts |
| `boundary_porosity` | Outward edges / all ego-net edge endpoints — how "leaky" your boundary is |

`boundary_porosity` was included deliberately: a node cannot see past its own boundary, but it *can* observe how porous that boundary is. This is the key signal for the self-assessment question in Angle 5.

The five marked **derived** are kept because they are conventional and because a transform can help a tree even when it adds no information — but they must not be counted as evidence that the edge or subgraph tiers carry anything of their own.

### 6.3 Hop 1 — local heterogeneity

| Feature | Meaning |
|---|---|
| `local_entropy` | Shannon entropy of the neighbour-degree distribution |
| `local_entropy_norm` | The same, divided by log k — heterogeneity *shape* with the degree scale removed |

Standard deviation captures spread; entropy captures shape. One dominant neighbour among many small ones reads very differently from an even spread at equal variance, and `nbr_degree_std` cannot tell them apart.

### 6.4 Hop 1 — a real edge tier

| Feature group | Meaning |
|---|---|
| `edge_embeddedness_{mean,max,min,std}` | Common neighbours on each incident edge, summarised over edges |
| `edge_overlap_{mean,max,min,std}` | Onnela neighbourhood overlap of each incident edge: nᵢⱼ / ((kᵢ−1)+(kⱼ−1)−nᵢⱼ) |

These are the answer to the tier problem in §5. Every earlier edge feature was one aggregate over the whole ego net, and each turned out to be a closed-form function of node-tier columns. These describe the **distribution** of structure across a node's incident edges, and no combination of node-level columns recovers a distribution's shape from its total. Low overlap marks a bridge, high marks an embedded tie — the strong/weak tie distinction, per edge.

The `sum` statistic is deliberately omitted from embeddedness: it equals exactly 2·`triangle_count`, so emitting it would add a column and no information.

### 6.5 Hop 1 — brokerage

| Feature | Meaning |
|---|---|
| `ego_betweenness` | Betweenness of the ego computed *inside its own ego network only* |

**Our derivation.** Within an ego network, two neighbours j,k of the ego are either directly connected (shortest path length 1, cannot pass through the ego) or not (every shortest path has length 2 and runs through a common neighbour; the ego is always one such). So for each non-adjacent pair, the contribution is 1/(number of their common neighbours inside the ego net, plus the ego itself). Summing gives exact ego-betweenness without running full betweenness on each ego network. Verified against brute force to 2e-11.

This was the **only** genuinely independent non-node feature in the original table, which is why §20 and §24 both turn on it.

### 6.6 Hop 1 — literature baselines, honestly labelled

| Feature | Meaning |
|---|---|
| `cluster_rank` | Chen's ClusterRank: 10^−C(i) · Σ(kⱼ+1) over neighbours |
| `local_gravity_ℓ` | Local gravity model truncated at radius ℓ: kᵢ · Σ kⱼ/d² over the ℓ-ball |

Both are standard in the influential-node literature and both are **recombinations of columns already present** — nonlinear ones a tree would struggle to form, but not new information. They are included so the claim can be tested rather than assumed; `analyse_features.py` reports where each sits on the derived-to-independent continuum.

`local_gravity_ℓ` is radius-parameterised by construction, so it slots into the hop ladder exactly as `collective_influence_ℓ` does.

### 6.7 The H-index ladder, Collective Influence, and shells

Unchanged from earlier versions: `h_index_1..3`, `collective_influence_1..3`, `shell_{2,3}_{count,degree_mean,degree_max}`, `growth_ratio_{2,3}`, `reach_within_{2,3}`. Each is tagged with the radius it genuinely needs.

The H-index ladder approaches coreness **from above** — degree = h⁽⁰⁾ ≥ h⁽¹⁾ ≥ … ≥ coreness — and the gap h⁽³⁾ − coreness is how far a bounded local view *over-reads* a node's embedding. That gap is a profiling axis in the failure atlas (§25).

### 6.8 Hop 2 — ball-internal structure

| Feature | Meaning |
|---|---|
| `ball2_edges` | Edges with both endpoints inside the 2-ball |
| `ball2_density` | Those edges divided by the possible number |
| `local_conductance_2` | 2-ball cut size / 2-ball degree volume |

**This closes the largest structural gap in the feature set.** Every other multi-hop feature is a count or a degree summary of a *shell*; none of them ever looked at the edges **among** those nodes. The table could say how many friends-of-friends a node had and how well connected they were, and nothing whatever about how they were wired to one another.

Only the 2-ball is measured, deliberately. On a dense network the 3-ball is most of the graph — on email-Eu-core the 2-ball already covers about 93% of nodes — so a 3-ball density would stop being a local quantity in any useful sense while costing far more. That the 2-ball can swallow a dense network is not a defect of the measurement; it is a large part of *why* locality saturates there.

### 6.9 Hop 3 — neighbour-aggregated reach

| Feature | Meaning |
|---|---|
| `semilocal_centrality` | Chen's semi-local centrality: Σ over neighbours of their 2-ball size |
| `nbr_reach2_mean` | The same, averaged |

Genuinely hop 3: the 2-ball of a node one step away reaches distance 3. Nothing else in the table aggregates *reach* over neighbours — the neighbour aggregates only ever summarised degree, clustering and triangles.

### 6.10 The `dynamic` tier — a local estimate of the cascade itself

| Feature | Meaning |
|---|---|
| `perc_reach_ℓ` | Expected cascade size within ℓ hops, independent-path approximation at transmission probability p |

Every other feature is a structural *proxy* for spreading. This one estimates the spreading directly, propagating a reach probability outward along the BFS layers:

```math
q(i) = 1, \qquad q(j) = 1 - \prod_{u \in \text{parents}(j)} \bigl(1 - p\,q(u)\bigr)
```

summed over the r-ball. It treats the paths arriving at j as independent, which they are not when the neighbourhood contains cycles, so it over-estimates in clustered regions. The point is not exactness but that it is **mechanistic** — derived from the dynamics rather than from generic structure.

**It sits on its own tier because it makes an assumption none of the others make: that the observer knows p.** That is a modelling assumption, not leakage — no global structure enters, and p is a known constant in the same sense n is — but no general claim about "richness" should be allowed to depend on it silently. Passing no `p_transmission` to `extract_features` omits the tier entirely, and dropping one line from `TIER_LADDER` removes it from every sweep.

Radius 1 is excluded: there the estimate is 1 + p·k, a linear function of degree and therefore a rank-identical duplicate of it.

### 6.11 Graphlet orbits — and the observation that they are not all the same radius

| Feature group | Meaning |
|---|---|
| `orbit_NN_<name>` | Count of times the node occupies orbit NN of a graphlet on ≤4 nodes |

A **graphlet** is a small connected induced subgraph; an **orbit** is a position within one, up to automorphism. There are 15 orbits for graphlets on up to 4 nodes and 73 for up to 5. Counts come from ORCA, which recovers most orbits from a system of linear equations relating them rather than enumerating every subgraph.

Orbits 0 and 3 are dropped: they are exactly `degree` and `triangle_count`. That leaves **13 usable orbits**, taking the subgraph tier from 3 features to 16 — and one of the previous three, `triangle_count`, was algebraically derived anyway. This is the fair test that Finding 3's caveat has always demanded.

**The part that is ours: orbits do not all cost the same radius.** Every treatment of graphlet features we found adds all 15 as a single block. For this project that would be wrong. The radius an orbit needs is the **eccentricity of the node within its graphlet** — the furthest any other member sits from it along the graphlet's own edges. To recognise an induced subgraph you must see all its members *and every edge among them*, since an absent edge is as much a part of the pattern as a present one, and the r-ball gives exactly that.

Worked through orbit by orbit:

| radius | orbits | shape |
|---|---|---|
| **1** | 2, 7, 11, 13, 14 | the node is adjacent to every other member |
| **2** | 1, 5, 6, 8, 9, 10, 12 | one member sits two steps away |
| **3** | 4 | the node is an endpoint of an induced 4-path |

**Only one of the fifteen genuinely needs three hops.** Graphlets are not an expensive block bolted onto the deepest radius; they are mostly a radius-1 and radius-2 enrichment. That is a substantive point for the depth-versus-richness comparison, and it falls straight out of taking the radius axis seriously.

The tagging is deliberately **conservative**. Graphlet distance upper-bounds distance in the host graph — two members three steps apart inside an induced 4-path may be two steps apart through some node outside it — so an orbit may be tagged deeper than strictly necessary, never shallower. A radius-r observer is never credited with something it could not have computed.

**Cost does not decompose by radius here, unlike everything else.** The BFS shells can be charged per level because each level is produced by a separate expansion. ORCA solves for all fifteen orbits at once, so there is no cheaper run returning only the hop-1 ones. Any cell using any orbit pays for all of them, and they share a single cost group. In practice the bill is small: about 0.1 s per pilot network.

**A convention that had to be measured rather than assumed.** ORCA numbers the paw graphlet (a triangle with a pendant edge) the opposite way round from the obvious guess: the degree-2 triangle nodes are orbit 10 and the degree-3 hub is orbit 11. Our brute-force check disagreed on exactly those two orbits and no others across five graph families, which is what made it findable; running ORCA on a hand-built paw settled it. The radius tags follow the correction — the hub touches every member (hop 1) while a degree-2 triangle node is two steps from the tail (hop 2). Had we shipped the guess, two orbits would have carried the wrong radius and the ladder would have been quietly wrong.

### 6.12 What is NOT a feature

| Quantity | Role |
|---|---|
| `betweenness` | **Target** (bridge influence) |
| `spread_mean`, `spread_cv`, `spread_resid` | **Targets** (spreading influence) |
| `closeness`, `pagerank`, `eigenvector`, `katz`, `harmonic`, `coreness` | **Rival baselines only** — never inputs |

**Why these are global.** Betweenness and closeness depend on shortest paths across the whole network. PageRank and Katz are recursive — your score depends on your neighbours' scores, which depend on theirs, unravelling across the entire graph. None can be computed from a bounded local patch.

---

# PART III — EVALUATION

## 7. Metrics

Influence is heavily skewed: a few enormous nodes, thousands near zero. Raw error is dominated by the large ones and hides whether the *ranking* is right, which is what actually matters for finding influencers.

### 7.1 Primary

**Kendall's τ**

```math
τ = (n_c − n_d) / (½ n(n−1))
```

Over all pairs of nodes, n_c is the count ranked in the same order as truth (concordant) and n_d the count reversed (discordant). τ = +1 is a perfect ranking, 0 is random, −1 is exactly reversed.

**Precision@k**

```math
P@k = |top-k predicted ∩ top-k true| / k
```

Of the truly top-k influencers, how many did we catch? This is what a practitioner actually asks.

### 7.2 Secondary

Spearman correlation; RMSE reported but never headlined.

### 7.3 Honest error estimation

**k-fold cross-validation with out-of-fold prediction.** Nodes are split into k groups; we train on k−1 and predict the held-out group, rotating until every node has a prediction from a model that never trained on it. Without this, a flexible model partly memorises its training nodes and its errors look artificially small — which would wreck the failure analysis, since we would be studying memorisation artefacts rather than genuine structural blind spots.

**Known limitation, stated openly.** On a *single* graph, held-out nodes' features are still computed on a graph containing the training nodes. This is not fully independent transfer. The clean version is training on some networks and testing on entirely separate ones; the pipeline supports this and it is the next step as the corpus grows.

## 8. The baseline ladder

Every result is reported against this ladder:

1. **Degree only** — the naive "popularity = influence" rule. *This is the r=0 row of every sweep.*
2. **Classical local scores** — H-index ladder, CI_ℓ, ego-betweenness.
3. **Our full feature set** — node + edge + subgraph tiers across hops.
4. **Published baselines** — *reimplemented by us, or run from released code.*

**On rung 4 — the replication rule.** Do not accept a published number as a baseline until you can reproduce it. Authors may cherry-pick; results may not replicate. Check for released code first; if unavailable, implement it yourself. Replication is itself respected work.

---

# PART IV — THE IMPLEMENTED PIPELINE

## 9. Module structure

The codebase is a Python package, `influence/`, of eight modules.

| Module | Responsibility |
|---|---|
| `preprocessing.py` | Loading and the cleaning protocol; the `Network` container |
| `features.py` | All 43 local features, with hop/tier/cost-group tagging and per-hop timing |
| `dynamics.py` | IC and SIR simulators, edge-probability conventions, full distributions |
| `criticality.py` | Non-backtracking operator, Ihara-Bass form, β_c |
| `targets.py` | Ground truth, variance residual, and the leakage guard |
| `experiment.py` | Metrics, out-of-fold prediction, the radius × richness sweep, the cost model |
| `generators.py` | Synthetic networks — the structural control arm |
| `structure.py` | Whole-network descriptors, **and** the per-node global quantities the failure atlas profiles against |
| `graphlets.py` | Graphlet orbit counts via ORCA, their measured radius tags, and the brute-force reference that checks them |
| `robustness.py` | Damaged views of a network for Angle 4 - the one place a Network is built without the LCC restriction, deliberately |

**The one module that needs watching is `structure.py`.** Nothing in it may ever enter the feature matrix. Its first half is per-network descriptors, which are safe because they never have the shape of a feature column. Its second half — `core_numbers`, `distance_to_hubs` — is per-node and global, so it looks exactly like a feature and is the genuinely dangerous part. Those exist because the failure atlas can only describe what locality is blind to using information the model was denied. The leakage guard is the backstop: `coreness` and `k_shell` are both forbidden substrings, so such a column reaching the feature matrix aborts the run.

Runner scripts, in order:

| Script | Role |
|---|---|
| `fetch_data.py` | Download the real corpus, with checksums |
| `stage0_generate.py` | Build the synthetic corpus |
| `stage1_prepare.py` | Checkpoint the expensive deterministic work (β_c, cascades, features, targets) |
| `stage2_sweep.py` | Run the grid at several seeds, saving metrics **and out-of-fold predictions** as each cell completes |
| `analyse.py` / `make_fig1.py` | The locality budget tables and figure |
| `analyse_failures.py` / `make_fig2.py` | The failure atlas and its figure |
| `analyse_features.py` | Feature-table audit: exact identities, effective dimensionality, and the tier test |
| `analyse_robustness.py` / `make_fig3.py` | Angle 4: local prediction against recomputation on damaged graphs |
| `analyse_betweenness.py` | The betweenness tie-block analysis |
| `verify_pipeline.py` / `verify_generators.py` | The two verification suites |

**Predictions are kept, not recomputed.** Every sweep cell predicts every node out-of-fold and used to discard the result, which meant the failure analysis could not be done without re-running the entire grid. They are now written to `cache_oof_<tag>.npz` keyed `target|radius|richness|seed` — one float per node per cell, about 5 MB per network, against the fifteen minutes of fitting that produced them.

## 10. The cleaning protocol

Six decisions, applied identically to every network and logged into a provenance record that goes straight into the methods section:

1. **Directedness** → symmetrize. Stated, not silent.
2. **Largest connected component** → restrict to it. Influence on a small fragment is capped by fragment size, which would contaminate the ground-truth distribution.
3. **Self-loops** → removed; they make the non-backtracking construction ill-defined.
4. **Multi-edges** → collapsed to simple edges.
5. **Weights** → discarded entirely. Half-using weights is the most common silent error in this literature.
6. **Node IDs** → reindexed to 0..n−1, with the mapping **kept**, so results can always be joined back to the source file's labels.

## 11. The percolation shortcut

The single most important performance decision in the pipeline.

**The problem.** Naively, M simulations from each of n seeds is O(n·M) cascades — millions of runs.

**The insight.** Independent Cascade with a fixed per-edge probability is exactly **bond percolation**. Each edge either transmits or does not, independently, and that draw does not depend on who is seeding. So we can sample one live-edge subgraph, find its connected components, and every node's reached set for that sample *is* its component.

One run therefore yields a sample for **all n seeds simultaneously** — M percolation runs instead of n·M cascades, a speedup of roughly n.

**Measured:** 1.6s for all 986 seeds, versus 36s for just 25 seeds by direct simulation — about 900×.

**Scope.** Exact for symmetric conventions (uniform, trivalency). It does *not* hold for weighted cascade, where the probability depends on the receiving node's degree and the edge is asymmetric. Both paths are implemented, and we verified they agree where both are valid.

## 12. Verification

Nothing is assumed. Each implementation was checked against an independent reference:

| Implementation | Checked against | Result |
|---|---|---|
| degree, clustering, triangles | networkx | exact match |
| H-operator | hand-computed unit tests | correct |
| ego-betweenness | brute-force betweenness on explicit ego subgraphs | 2e-11 |
| Ihara-Bass eigenvalue | direct 2m × 2m non-backtracking matrix | 1e-9, three graph families |
| Brandes betweenness | networkx | 1e-14 |
| igraph fast betweenness | our own Brandes | 1e-14 |
| percolation shortcut | direct per-seed IC simulation | r = 0.9993 |
| SIR with μ=1 | Independent Cascade (they should coincide) | 0.4% difference |
| leakage guard | deliberate injection of forbidden names | all caught, no false positives |
| structural measures (assortativity, transitivity, clustering, triangles) | networkx, four graph families | 1e-14 or better |
| power-law MLE | synthetic data with a known exponent, at known `xmin` | error < 0.007 |
| power-law reliability flag | the steep-tail / small-n failure mode | caught |
| Chung-Lu, Holme-Kim, degree-swap, assortativity rewiring | each knob moves its own parameter, degrees preserved exactly | verified |
| merged shell + CI traversal | the separate `bfs_shells` and `collective_influence` reference implementations, and the pre-merge production cache | bit-identical on the three networks that predate the merge; a pre-merge cache cannot exist for ca-HepTh or facebook_combined, which instead pass `verify_pipeline.py` from scratch |
| trivalency edge probabilities | percolation path against direct path, same seed | identical, symmetric |
| graphlet orbit counts (ORCA) | our own enumeration of every connected induced subgraph, classified from first principles, on four graph families | all 15 orbits exactly identical |
| 5-node graphlet orbit counts (ORCA) — *row added 2026-09-12, Claude Opus 5* | first-principles enumeration of the 21 connected 5-node graphs / 58 orbits on four generated fixtures (`verify_pipeline.py` 2c-5) | all 58 columns match under one bijection; three labels pinned by structure; the remaining numbering and the recovery equations are inherited from ORCA — see §26k.3 |

**On the merged traversal.** Shell statistics and Collective Influence used to walk every node's neighbourhood four separate times — once for the shells and once per CI radius — which was 78–94% of feature-extraction time across the corpus. They now share one traversal. The reference implementations are kept precisely so the fast path can be checked against them, the same discipline applied to Brandes betweenness and the Ihara-Bass eigenvalue. The check is bit-for-bit equality, not approximate agreement.

**On the igraph fast path.** We wrote Brandes' algorithm ourselves first and confirmed it matches. Using the C implementation afterwards for large graphs is a speed decision, not an inherited result — the algorithm is a specification and we have verified our reading of it.

---

# PART V — THE PHASES

| Phase | Status |
|---|---|
| 0 — Reproduce the supervisor's baseline plot | **Done** — the P(r) curve exists |
| 1 — Cleaning protocol and loader | **Done** |
| 2 — Four-tier feature engine | **Done** (171 features, hop tags measured not derived) |
| 3 — Ground truth: β_c, cascades, betweenness | **Done** |
| 4 — Locality budget sweep | **Done** on five networks, 10 seeds per cell (3,200 cells) |
| 4b — Structural control arm (generators) | **Done** — built and verified; sweep not yet run |
| 5 — The analysis angles | Angles 1, 2, 3, 4 and 6 done; 5 partly answered by the atlas |
| 6 — Corpus expansion | Controlled synthetic confirmation first, then real-corpus scale-out; both remain to be run. C3 aggregate audit and C4 reporting are complete (§26i–§26j), not fitted corpus expansion. |
| 7 — Neural comparison | Last, per supervision |

**Post-review programme status, checked 2026-09-07.** The phase numbers above describe
the original pipeline; the separate work plan's A/B/C labels describe later research.
Completed analysis does not mean a positive prediction or a resolved limitation.

| Work | Delivered evidence | Remaining qualification |
|---|---|---|
| A1–A6: framing, coverage, top-k, multiplicity, documentation and zero-set formalisation | Revised study text; `results/RESULTS_coverage.txt`, `RESULTS_topk.txt`, `RESULTS_multiplicity.txt`; C1/C2 checks | Formalisation is not a claim to have invented the prior-art zero-set rule; paper positioning remains necessary. |
| B2 estimator invariance | `docs/prereg/prereg_B2_estimator.md`; `results/estimator_shape.csv`, `estimator_horizons.csv`; §26c | Preserve the scored verdicts and design caveats; not an unrestricted invariance claim. |
| B1 sample efficiency | `docs/prereg/prereg_B1_sample_efficiency.md`; `results/sample_efficiency.csv`; §26e | Completed; the direction prediction was falsified and effects differ by target. |
| A7 target noise | `docs/prereg/prereg_A7_target_noise.md`; `results_target_noise_scored.csv`; §26h | Scored refit arm complete. Phase 6 dynamic-tier paired follow-through complete (38 retained / 3 lost flags); headline structural-tier comparisons remain unmeasured. |
| C5 matched-radius closed form and C6 residual autocorrelation | `results_betweenness_k.csv`, `results_moran_correlogram.csv`, `results_moran_zeroset.csv`; §26f–§26g | Closed-form comparison and diagnostic complete; they do not supply learned baselines or blocked CV. |
| C3 external benchmark analysis and C4 reporting | §26i–§26j, scored C3 tables, C4 audit/reporter and verification logs | Bounded implementation complete; prospective external validation and later confirmation remain separate. |

**Every swept cell carries seed variability, not total uncertainty.** Each grid cell is run at ten seeds, varying both the cross-validation split and the forest's own randomness. This is not cosmetic: the conclusions rest on tau differences of 0.001 to 0.02, and at a single seed none of them could be distinguished from run-to-run noise. Marginal gains are computed *paired* — differencing within a seed before averaging — which cancels the shared fold noise and makes the test far sharper.

## 13. Angles

**Angle 1 — Locality budget.** How far out must you look? **Delivered.** P(r) curves with seed spread, r\*(ε) across tolerances *and* its stability across seeds, paired marginal gain per hop tested against the noise floor. Five networks, all at p = 1.5 × β_c. See Part VII.

**Angle 2 — Multi-target contrast.** Same features, four targets. **Delivered.** The striking result is that the targets have genuinely *different* horizons, and with error bars the claim is now testable rather than eyeballed: on ca-GrQc betweenness stops gaining after r=1 while spread mean is still gaining a small but significant amount at r=3.

**Angle 3 — Failure atlas.** Which nodes does local prediction fail on, and why? **Delivered** — see §25. Out-of-fold predictions are now persisted by `stage2_sweep.py`, and `analyse_failures.py` profiles the misranked tails against global quantities the model was denied.

The headline is that the **directional** blind spot appears exactly where the locality horizon has not been reached: null on ca-GrQc, large on p2p-Gnutella08, and driven there by how much of a node's cascade escapes its visible 3-ball. Two mechanical artefacts had to be removed before that was visible — shrinkage and, less obviously, the heteroscedasticity that made both tails profile identically.

§24 supplies the useful contrast case: an entire class of node whose global betweenness is exactly determined by a local feature, which is the opposite of a blind spot.

```math
Δ(v) = rank_true(v) − rank_pred(v)
```

Large positive Δ = under-predicted "hidden influencer."

**Angle 4 — Robustness under noise.** **Delivered** — see §26. The answer is target-dependent: local prediction reaches parity with recomputation for spreading influence once ~5% of edges are missing, and loses to it for betweenness. The skew control matters and cuts against the naive reading, and degree on the damaged graph is a humbling baseline at high noise.

```math
τ_local(ρ)  >  τ_recompute(ρ)  ?
```

**Angle 5 — The locality gap.** How much of a node's importance physically lies beyond r hops? **Partly answered as a by-product of Angle 3**: the ratio of mean cascade size to the size of the visible 3-ball is the top directional separator on p2p-Gnutella08 (δ = 0.51), which is the gap measured directly. What remains is the second half of the question — whether a node can predict its *own* gap from local features alone.

The original formulation:

```math
g_r(v) = 1 − b_r(v) / b(v)     ∈ [0, 1]
```

where b_r(v) counts only pairs with both endpoints inside the r-ball. Then: can a node predict its *own* gap from local features? It cannot see past its boundary, but `boundary_porosity` and the growth ratios describe how leaky that boundary is. Already implemented as features, so the experiment is ready to run.

**Angle 6 — Spread volatility.** **Delivered.** `spread_cv` and the variance residual `spread_resid` are both swept on all five networks; see §23. The result is a genuine cross-network contrast rather than a single number: on the dense network the raw volatility signal is essentially the mean in disguise, and on the two sparse ones a large residual signal survives with the longest horizon of any target measured. Remaining: the archetype map.

## 14. The structural control arm (built)

No longer deferred — `influence/generators.py`, `influence/structure.py` and `stage0_generate.py` are implemented and verified, and `verify_generators.py` must print `ALL CHECKS PASSED` before the corpus is used.

Real networks cannot isolate a variable: ca-GrQc differs from email-Eu-core in density *and* degree tail *and* clustering *and* assortativity at once, so when r\* differs between them nothing can be attributed. Generated families move one knob at a time.

| Family | Generator | Knob | Holds fixed |
|---|---|---|---|
| `gamma` | Chung–Lu | degree tail exponent | mean degree |
| `clustering` | Holme–Kim | triangle density | tail, m |
| `assortativity` | Xulvi-Brunet–Sokolov | degree correlation | degree sequence **exactly** |
| `community` | LFR | mixing parameter μ | tail, mean degree |
| `controls` | ER / BA / WS | — | the three corner cases |

Generated graphs are written out as plain edge lists and go through `stage1_prepare.py` with no special case, which is the only reason their r\* values are comparable to the real ones.

**Read before plotting anything against gamma.** `gamma_uncertainty.py` measures how precisely the tail exponent can be estimated at our network sizes. The answer is: not very. The MLE is essentially exact at a *known* `xmin` (error < 0.007), but `xmin` is chosen by minimising a KS distance and that selection dominates the uncertainty — bootstrap standard deviation of 0.10 to 0.38 at n = 6,300. At n = 1,000 with a steep tail the estimator fails outright, fitting the bulk instead of the tail and returning 1.81 for a graph built at 3.4. `fit_power_law_tail` therefore returns a `reliable` flag and a `tail_fraction`, and the gamma family is plotted against the generator's **target** gamma, which has no measurement error. Any figure showing gamma for a *real* network needs an error bar on it.

What remains is running the sweep across the generated corpus, and the criticality sweep: measuring r\* as p moves through β_c to test whether the required radius peaks at the tipping point.

---

# PART VI — TECHNOLOGY STACK

| Tool | Role | Notes |
|---|---|---|
| **NumPy / SciPy** | Arrays, sparse matrices, eigenvalues, connected components | `scipy.sparse` is the backbone; `sparse.linalg.eigs` powers β_c |
| **pandas** | Feature and result tables | |
| **python-igraph** | Fast exact betweenness on large graphs | C-backed; used only after verifying against our own implementation |
| **networkx** | Verification reference, graph generators | Pure Python and slower; ideal as an independent check |
| **scikit-learn** | Random forest regressor, k-fold CV, metrics | |
| **matplotlib** | Figures | |
| **ORCA** | Graphlet orbit counts for the subgraph tier | Single C++ file, vendored and built locally; verified against our own enumeration |
| **PyTorch Geometric** (Phase 7) | GraphSAGE for the neural comparison | Respects locality by construction |

## 15. Performance notes

- **Python threading does not parallelise CPU-bound work** (the GIL). Use processes, or C-backed libraries that release it.
- **`n_jobs=-1`.** It was set to 1 because the original development machine had one core, which made the sweep roughly an order of magnitude slower than it needed to be. See §16 for the one price this charges: predictions become reproducible only to the last bits.
- **Algorithmic wins dominate hardware ones.** Two examples from this project. The percolation shortcut replaced n·M cascade simulations with M runs, about 900×. Merging the shell, Collective-Influence and gravity traversals into a single BFS gave a further 4–8× on feature extraction, verified bit-identical against the separate reference implementations. Neither required a faster machine.
- **Reuse the traversal, not the result.** Feature extraction was four walks of every neighbourhood — one for shells, one per CI radius — because each family was written independently. Every radius-parameterised quantity is now a different reading of one walk. The reference implementations are kept precisely so the merged version can be checked against them.
- **Checkpoint everything.** `stage1_prepare.py` saves features, targets, cascades and metadata; `stage2_sweep.py` appends each grid cell *and its out-of-fold predictions* as it finishes. A run that dies loses nothing. This was learned the hard way, twice: the second time, a cell counted as done if its metrics row existed even though its predictions had not yet been flushed, so an interruption left a handful of cells scored but unusable for the failure atlas.
- **Cache aggressively.** Features and simulation results are deterministic given a seed.
- **Log wall-clock cost per feature group** during extraction — the cost-versus-quality analysis depends on it and it cannot be reconstructed afterwards. Charge each BFS expansion *forward* to the level it produces, or the deepest hop looks free and the cumulative cost of radius r includes a shell no radius-r observer needs.

## 16. Reproducibility practices

- Fix and record random seeds for every stochastic component. The sweep seed is a column in `sweep_<tag>.csv`; the simulation seed is in `cache_meta_<tag>.json`.
- Store **full cascade distributions**, not summary statistics — volatility work needs them and re-running is expensive.
- Store **out-of-fold predictions** for the same reason. They cost one float per node per cell and are the sole input to the failure atlas; discarding them meant the atlas could not be built without re-running the whole grid.
- Keep the feature registry in sync with the feature table; it carries the hop, tier and cost-group tags that the sweep and the cost model depend on.
- Record the provenance dict for every network, plus the exact package versions the result was produced under.
- **Pin the environment, including the BLAS implementation.** See the note in `environment.yml`: an unpinned solve produced a numpy/scipy pair with two different BLAS libraries in one process, which aborted natively with no Python traceback.

### Evidence, not intention — and one honest caveat

These are claims, so they get checked like everything else. The full three-network sweep was run twice, on separate days, from the pinned environment. All 1,440 cells matched:

| Network | max \|Δτ\| across two independent runs |
|---|---|
| ca-GrQc | 0.00e+00 |
| email-Eu-core | 0.00e+00 |
| p2p-Gnutella08 | **5.08e-08** |

Two of the three are bit-identical and the third is not. The cause is worth stating rather than rounding away, because it is a trade we deliberately made.

`n_jobs=-1` parallelises the forest across cores, and sklearn accumulates predictions across trees in whatever order the workers finish. Floating-point addition is not associative, so the prediction vector is reproducible only to the last bits. Measured directly, two identical runs on p2p-Gnutella08:

| setting | max \|Δ prediction\| |
|---|---|
| `n_jobs=1` | 0.00e+00 — bit-identical |
| `n_jobs=-1` | 5.68e-14 |

A 5.68e-14 wobble in a prediction becomes 5.08e-08 in τ because τ is a *rank* statistic: a difference in the last bits can flip a near-tie, and a flipped pair moves τ by a discrete step.

**Is that acceptable?** Yes, and the numbers say why. We report τ to four decimals, and the seed-to-seed spread — the uncertainty we actually quote — is of order 1e-3. The reproducibility wobble is five orders of magnitude below the noise we already report, and it is averaged over ten seeds besides. Against that, `n_jobs=-1` is roughly a tenfold speedup and is what makes ten seeds per cell affordable at all.

So the honest claim is not "bit-identical" but: **reproducible to 5e-08 in τ, which is far below the reported precision, and exactly reproducible if you set `n_jobs=1`.** Anyone needing bit-exactness for an audit can have it for a tenfold slowdown; nobody needs it for a conclusion in this project.

What the seed discipline does still buy is the important part: any future change to a reported number at the precision we quote is a real change in the code or the data, never drift.

---

# PART VII — RESULTS SO FAR

## 17. The locality budget curve

Kendall τ, out-of-fold, richest **structural** tier, **mean ± sd over ten seeds**. All five networks at p = 1.5 × β_c, 4,000 percolation runs, uniform convention. 171 features (§6). The `dynamic` tier is excluded from these curves — it assumes the observer knows p, and the headline result must not depend on that.

**ca-GrQc** (n = 4,158, ⟨k⟩ = 6.5):

| radius | spread (mean) | betweenness | spread volatility | volatility residual |
|---|---|---|---|---|
| 0 | 0.7807 ± 0.0019 | 0.5422 ± 0.0015 | 0.4598 ± 0.0019 | 0.2240 ± 0.0028 |
| 1 | 0.9207 ± 0.0007 | 0.9181 ± 0.0008 | 0.7074 ± 0.0023 | 0.5300 ± 0.0025 |
| 2 | 0.9416 ± 0.0004 | 0.9215 ± 0.0012 | 0.8046 ± 0.0017 | 0.6522 ± 0.0014 |
| 3 | 0.9441 ± 0.0004 | 0.9216 ± 0.0012 | 0.8206 ± 0.0016 | 0.6715 ± 0.0019 |

**ca-HepTh** (n = 8,638, ⟨k⟩ = 5.7) — *added 2026-08-28; this table was missing while the
section header already claimed five networks:*

| radius | spread (mean) | betweenness | spread volatility | volatility residual |
|---|---|---|---|---|
| 0 | 0.7228 ± 0.0007 | 0.6611 ± 0.0007 | 0.3282 ± 0.0008 | 0.2870 ± 0.0005 |
| 1 | 0.9012 ± 0.0003 | 0.8990 ± 0.0005 | 0.6708 ± 0.0007 | 0.5463 ± 0.0013 |
| 2 | 0.9461 ± 0.0002 | 0.9153 ± 0.0004 | 0.8001 ± 0.0007 | 0.6931 ± 0.0013 |
| 3 | 0.9508 ± 0.0002 | 0.9162 ± 0.0005 | 0.8220 ± 0.0004 | 0.7191 ± 0.0005 |

**facebook_combined** (n = 4,039, ⟨k⟩ = 43.7) — *added 2026-08-28, same reason:*

| radius | spread (mean) | betweenness | spread volatility | volatility residual |
|---|---|---|---|---|
| 0 | 0.6705 ± 0.0013 | 0.3038 ± 0.0047 | 0.1438 ± 0.0045 | 0.3000 ± 0.0026 |
| 1 | 0.9558 ± 0.0003 | 0.6269 ± 0.0047 | 0.8335 ± 0.0015 | 0.7295 ± 0.0030 |
| 2 | 0.9574 ± 0.0004 | 0.8239 ± 0.0054 | 0.8364 ± 0.0015 | 0.7364 ± 0.0019 |
| 3 | 0.9586 ± 0.0004 | 0.8514 ± 0.0033 | 0.8360 ± 0.0012 | 0.7378 ± 0.0017 |

**email-Eu-core** (n = 986, ⟨k⟩ = 32.6):

| radius | spread (mean) | betweenness | spread volatility | volatility residual |
|---|---|---|---|---|
| 0 | 0.8619 ± 0.0012 | 0.7429 ± 0.0035 | 0.8563 ± 0.0012 | 0.0312 ± 0.0120 |
| 1 | 0.9595 ± 0.0003 | 0.8984 ± 0.0023 | 0.9537 ± 0.0010 | 0.0659 ± 0.0134 |
| 2 | 0.9638 ± 0.0006 | 0.9041 ± 0.0024 | 0.9575 ± 0.0008 | 0.0980 ± 0.0114 |
| 3 | 0.9687 ± 0.0003 | 0.9030 ± 0.0024 | 0.9629 ± 0.0005 | 0.0802 ± 0.0137 |

**p2p-Gnutella08** (n = 6,299, ⟨k⟩ = 6.6):

| radius | spread (mean) | betweenness | spread volatility | volatility residual |
|---|---|---|---|---|
| 0 | 0.6705 ± 0.0012 | 0.8853 ± 0.0005 | 0.4560 ± 0.0011 | 0.1393 ± 0.0030 |
| 1 | 0.8021 ± 0.0010 | 0.9233 ± 0.0003 | 0.5923 ± 0.0018 | 0.2558 ± 0.0040 |
| 2 | 0.8867 ± 0.0007 | 0.9337 ± 0.0004 | 0.7182 ± 0.0024 | 0.3728 ± 0.0026 |
| 3 | 0.9159 ± 0.0003 | 0.9367 ± 0.0003 | 0.7793 ± 0.0010 | 0.4375 ± 0.0032 |

## 17a. The coverage control — how much of the graph does a radius-r observer see?

*Added 2026-08-28 (`analyse_coverage.py`, `results/RESULTS_coverage.txt`). Answers
referee objection M3. Predictions were written first, in `docs/prereg/prereg_A2_coverage.md`,
before any number here was computed; the scoring is at the end of this section and
**three of the five predictions were falsified**.*

### The objection

Every result in this document is indexed by radius. The objection is that radius is a
proxy for a much duller quantity — **the fraction of the graph you are allowed to see** —
and that r\*(ε) is just the radius at which you have seen enough of it. SNAP reports a
90th-percentile effective diameter of 2.9 for email-Eu-core, which would make its r=3
"local" view the entire graph.

The ball sizes needed to check this have been cached columns since the pipeline was
built (`degree`, `reach_within_2`, `reach_within_3`). Nobody had plotted them.

### Median coverage |B_r(v)| / n

| network | n | ⟨k⟩ | r=1 | r=2 | r=3 | nodes seeing >50% at r=3 |
|---|---|---|---|---|---|---|
| email-Eu-core | 986 | 32.6 | 2.33% | 49.4% | **97.3%** | **98.4%** |
| facebook_combined | 4,039 | 43.7 | 0.64% | 19.0% | **45.3%** | 31.5% |
| p2p-Gnutella08 | 6,299 | 6.6 | 0.06% | 0.75% | 6.83% | 0.3% |
| ca-GrQc | 4,158 | 6.5 | 0.10% | 0.55% | 2.55% | 0.0% |
| ca-HepTh | 8,638 | 5.7 | 0.05% | 0.30% | 1.86% | 0.0% |

**The objection is correct about email and it is worse than the referee assumed.** A
median email node's 3-ball is 959 of 986 nodes. Ninety-eight percent of its nodes see
more than half the graph. email's r=3 column is not a local measurement in any useful
sense, and it should never again be described as one.

The corpus spans **fifty-two-fold** in r=3 coverage, from 1.86% to 97.3%. That range is
invisible on every P(r) figure in this project, all of which put r on the x-axis and
thereby imply the five networks are being compared at the same thing. They are not.

### But the confound runs the *opposite* way from the one assumed

This is the part that was not predicted and is the reason the section is worth reading.

The worry was that good local results are bought with high coverage. Put the τ column
next to the coverage column and it is the reverse:

| network | cov at r=1 | τ at r=1 | cov at r=3 | τ at r=3 | what the extra 95% of the graph bought |
|---|---|---|---|---|---|
| email-Eu-core | 2.33% | 0.9595 | 97.3% | 0.9687 | **+0.0092** |
| facebook_combined | 0.64% | 0.9558 | 45.3% | 0.9586 | +0.0028 |

*(`spread_mean`, richest structural tier.)*

**On email, going from seeing 2.3% of the graph to seeing 97.3% of it buys nine
thousandths of a tau.** That is the single strongest locality result in the project and
it was sitting inside the objection meant to destroy it. The same holds on facebook: a
seventy-fold increase in what the observer sees is worth +0.003.

There is a second consequence, and it is favourable in a way that needs stating because
it will not be obvious to a referee either. r\*(ε) is defined against the **best observed**
value, which is the r=3 cell. On email that reference point is computed at 97% coverage —
so email's r\*(ε) is measured against what is, to numerical accuracy, **the global
answer**. Email's horizon claim is therefore the best-grounded in the corpus, not the
most suspect: it is the one network where "you need only r=1" is being asserted against a
near-exact global ceiling rather than against another local measurement.

### Where the confound does bite

Three claims in this document are stated at r=3 on email, i.e. at 97% coverage, and are
**not** local measurements:

1. **§20** — email is the only network whose r=3 subgraph gain exceeds its r=1 gain
   (+0.0062 vs +0.0026). At r=3 those "subgraph" features are being computed on
   essentially the whole graph. The anomaly is a comparison between a local measurement
   on four networks and a near-global one on the fifth.
2. **§23** — email's null volatility-residual signal (τ = 0.080) is also an r=3 number.
   Whatever it means, it does not mean "locality fails here", because locality is not
   what was being tested in that cell.
3. **§21** — email's r\*(ε) = 1 for betweenness against facebook's 3 was read as evidence
   that density does not set the horizon. Coverage at r=3 is 97.3% vs 45.3%, so the two
   networks' *ceilings* are not comparable objects. The finding is not overturned — see
   the scoring below — but this is the comparison a referee will press on.

**The recommendation that follows is unconditional: every P(r) figure in the paper gets a
coverage twin.** That was pre-registered as the outcome regardless of which way the
predictions fell, and it is what the section delivers.

### Scoring the pre-registration

| # | Prediction | Outcome |
|---|---|---|
| P1 | email has highest r=3 coverage, median > 0.90 | **CONFIRMED** (0.9726, rank 1) |
| P2 | coverage driven by n, not density | **FALSIFIED** — exact tie |
| P3 | collaboration pair within 2× at every r | **FALSIFIED** — 2.08× at r=1 |
| P4 | email's anomalies sit at unreachable coverage | **UNTESTABLE**, as pre-registered |
| P5 | blind spot is partly a coverage effect (\|ρ\| ≥ 0.7) | **FALSIFIED** — ρ = +0.30 |

Each falsification is more informative than the prediction would have been.

**P2 — n and density are collinear in this corpus and cannot be separated.**
Spearman(n, coverage) = **−0.900** and Spearman(⟨k⟩, coverage) = **+0.900**. Not "density
wins" — an exact tie, because email is the smallest graph *and* one of the two densest,
while ca-HepTh is the largest *and* the sparsest. Five observational networks cannot tell
these apart, and the prediction was wrong to assume they could. This is the same
limitation §21 records for the horizon itself, arriving independently on a different
quantity, and it is a second argument for the generated corpus.

**P3 — falsified on a badly chosen criterion, and the underlying claim survives.**
ca-GrQc and ca-HepTh differ by 2.08× at r=1, just past the pre-registered 2.0. But their
**median 1-ball is 4 nodes on both** — identical — and the coverage ratio 2.08 is exactly
the ratio of their sizes (8,638 / 4,158 = 2.077). The two graphs see the same
neighbourhood and differ only in what it is a fraction *of*. A ratio test on quantities
near zero is hypersensitive and the threshold should have been stated on ball size, not
on coverage. **The criterion was poor; it is reported as failed anyway.** Rewriting a
pre-registered threshold after seeing the data is the practice this section exists to
argue against, and the project does not get an exemption from its own argument.

**P5 — the prediction was wrong in sign, and Finding 8 survives cleanly.**
Coverage does *not* explain the directional blind spot: ρ = **+0.300** against
final-hop-gain's ρ = 0.900, and even the sign is opposite to the prediction. Finding 8
is not a restatement of how much of the graph is visible. *(This number was wrong once:
the first parser read past the directional block into the rescue table and returned
ρ = −0.600. Caught by cross-checking all ten parsed δ values against §25's table — four
of five disagreed — and the corrected parser now reproduces all ten exactly. The blank-line
terminator that fixed it is documented in `analyse_coverage.py`.)*

### The honest summary

The coverage axis was a real gap and the objection was worth raising. Having plotted it:
email's r=3 column is disqualified as a local measurement and three claims that rest on it
are now scoped accordingly; the *headline* locality claim is strengthened rather than
weakened, because the networks with the most coverage gain the least from it; and the two
findings that could have been coverage artefacts (8, and the density argument in 4) are
not. What the corpus still cannot do is separate n from density, and that is now failing
in two independent places.

## 18. Finding 1 — different targets have different horizons

Marginal gain in τ per extra hop, **paired within seed**. A starred row exceeds twice the standard deviation of the paired per-seed difference.

**ca-GrQc:**

| Target | base (r=0) | r0→r1 | r1→r2 | r2→r3 |
|---|---|---|---|---|
| betweenness | 0.5422 | +0.3759 ± 0.0019 ✱ | +0.0034 ± 0.0011 ✱ | +0.0000 ± 0.0012 |
| spread mean | 0.7807 | +0.1400 ± 0.0019 ✱ | +0.0209 ± 0.0006 ✱ | +0.0025 ± 0.0002 ✱ |
| spread volatility | 0.4598 | +0.2475 ± 0.0039 ✱ | +0.0972 ± 0.0016 ✱ | +0.0160 ± 0.0011 ✱ |
| volatility residual | 0.2240 | +0.3060 ± 0.0049 ✱ | +0.1223 ± 0.0020 ✱ | +0.0193 ± 0.0011 ✱ |

**p2p-Gnutella08** — every gain at every radius is significant, including the last:

| Target | base (r=0) | r0→r1 | r1→r2 | r2→r3 |
|---|---|---|---|---|
| betweenness | 0.8853 | +0.0380 ± 0.0004 ✱ | +0.0104 ± 0.0006 ✱ | +0.0030 ± 0.0002 ✱ |
| spread mean | 0.6705 | +0.1316 ± 0.0015 ✱ | +0.0846 ± 0.0012 ✱ | +0.0292 ± 0.0008 ✱ |
| spread volatility | 0.4560 | +0.1363 ± 0.0017 ✱ | +0.1260 ± 0.0027 ✱ | +0.0611 ± 0.0024 ✱ |
| volatility residual | 0.1393 | +0.1165 ± 0.0044 ✱ | +0.1170 ± 0.0059 ✱ | +0.0647 ± 0.0043 ✱ |

**ca-HepTh** *(added 2026-08-28 — this network was in the corpus but had no gain table here):*

| Target | base (r=0) | r0→r1 | r1→r2 | r2→r3 |
|---|---|---|---|---|
| betweenness | 0.6611 | +0.2378 ± 0.0007 ✱ | +0.0163 ± 0.0006 ✱ | +0.0009 ± 0.0005 |
| spread mean | 0.7228 | +0.1785 ± 0.0008 ✱ | +0.0448 ± 0.0003 ✱ | +0.0047 ± 0.0002 ✱ |
| spread volatility | 0.3282 | +0.3427 ± 0.0008 ✱ | +0.1292 ± 0.0008 ✱ | +0.0219 ± 0.0005 ✱ |
| volatility residual | 0.2870 | +0.2594 ± 0.0013 ✱ | +0.1467 ± 0.0019 ✱ | +0.0260 ± 0.0012 ✱ |

**facebook_combined** *(added 2026-08-28, same reason):*

| Target | base (r=0) | r0→r1 | r1→r2 | r2→r3 |
|---|---|---|---|---|
| betweenness | 0.3038 | +0.3231 ± 0.0057 ✱ | +0.1970 ± 0.0083 ✱ | +0.0275 ± 0.0039 ✱ |
| spread mean | 0.6705 | +0.2853 ± 0.0013 ✱ | +0.0016 ± 0.0003 ✱ | +0.0012 ± 0.0002 ✱ |
| spread volatility | 0.1438 | +0.6897 ± 0.0050 ✱ | +0.0029 ± 0.0009 ✱ | −0.0004 ± 0.0008 |
| volatility residual | 0.3000 | +0.4295 ± 0.0047 ✱ | +0.0069 ± 0.0019 ✱ | +0.0015 ± 0.0008 |

**email-Eu-core** saturates fastest: betweenness r2→r3 = −0.0010 ± 0.0017, not significant.

Betweenness on ca-GrQc is the only target whose final hop buys nothing measurable. **This is the headline, and the error bars sharpen rather than soften it** — at a single seed, "+0.0025" and "+0.0000" would be indistinguishable claims.

Two corpus-wide facts are only visible now that all five tables sit together, and both
were stated wrongly while two of them were missing:

- **The largest single-hop gain in the project is not a betweenness gain.** It is
  facebook_combined's `spread volatility` at r0→r1, **+0.6897 ± 0.0050** — degree alone
  reaches τ = 0.14 on that target and one hop takes it to 0.83. ca-GrQc betweenness's
  +0.3759 is the largest gain *for betweenness*, which is a narrower claim than the one
  §24 used to make (corrected there).
- **facebook is the corpus's clearest split between targets.** Its three non-betweenness
  targets are finished after one hop (r1→r2 gains of +0.0016, +0.0029, +0.0069); its
  betweenness is still buying +0.197 at that same step. One network, one radius, a
  hundredfold difference in what the hop is worth depending only on the target. This is
  Finding 1 in its strongest available form and it needed facebook to see.

## 19. Finding 2 — r\* depends on the tolerance, and sometimes on the seed

r\*(ε), modal radius across ten seeds with the number that agreed:

| Network | Target | ε=0.20 | ε=0.10 | ε=0.05 | ε=0.02 | ε=0.01 |
|---|---|---|---|---|---|---|
| ca-GrQc | betweenness | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) |
| ca-GrQc | spread mean | 0 (10/10) | 1 (10/10) | 1 (10/10) | 2 (10/10) | 2 (10/10) |
| ca-GrQc | spread volatility | 1 (10/10) | 2 (10/10) | 2 (10/10) | 2 (7/10) | 3 (10/10) |
| ca-GrQc | volatility residual | 2 (10/10) | 2 (10/10) | 2 (10/10) | 3 (10/10) | 3 (10/10) |
| ca-HepTh | betweenness | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 2 (10/10) |
| ca-HepTh | spread mean | 1 (10/10) | 1 (10/10) | 2 (10/10) | 2 (10/10) | 2 (10/10) |
| ca-HepTh | spread volatility | 1 (10/10) | 2 (10/10) | 2 (10/10) | 3 (10/10) | 3 (10/10) |
| ca-HepTh | volatility residual | 2 (10/10) | 2 (10/10) | 2 (10/10) | 3 (10/10) | 3 (10/10) |
| facebook_combined | betweenness | 2 (10/10) | 2 (10/10) | 2 (10/10) | 3 (10/10) | 3 (10/10) |
| facebook_combined | spread mean | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) |
| facebook_combined | spread volatility | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) |
| facebook_combined | volatility residual | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | **2 (5/10)** |
| email-Eu-core | betweenness | 0 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) |
| email-Eu-core | spread mean | 0 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) |
| email-Eu-core | spread volatility | 0 (10/10) | 1 (10/10) | 1 (10/10) | 1 (10/10) | 1 (7/10) |
| email-Eu-core | volatility residual | 2 (9/10) | 2 (10/10) | 2 (10/10) | 2 (10/10) | 2 (10/10) |
| p2p-Gnutella08 | betweenness | 0 (10/10) | 0 (10/10) | 1 (10/10) | 1 (10/10) | 2 (10/10) |
| p2p-Gnutella08 | spread mean | 1 (10/10) | 2 (10/10) | 2 (10/10) | 3 (10/10) | 3 (10/10) |
| p2p-Gnutella08 | spread volatility | 2 (10/10) | 2 (10/10) | 3 (10/10) | 3 (10/10) | 3 (10/10) |
| p2p-Gnutella08 | volatility residual | 2 (10/10) | 3 (10/10) | 3 (10/10) | 3 (10/10) | 3 (10/10) |

*(ca-HepTh and facebook_combined added 2026-08-28. The table had covered three networks
since before the corpus expanded; the twelve original rows were re-derived from the current
171-feature sweeps at the same time and are unchanged.)*

A single r\* is an artefact of an arbitrary tolerance — ca-GrQc spread mean moves 0 → 2 across the ε range, Gnutella betweenness 0 → 2. Where the signal is strong r\* is stable at 10/10; where it is weak the reported radius is closer to a coin flip. **A radius reported without that check cannot be distinguished from one of these.**

The two additions supply the corpus's **worst** stability cell and its most stable network
at once, which is the useful part:

- `facebook_combined` volatility residual at ε = 0.01 is **5/10** — the modal radius is
  literally a coin flip between 1 and 2, worse than the 7/10 cells that motivated this
  finding. Its own r\* is unquotable at that tolerance and must be reported as a split.
- Everything else on facebook is 10/10 at radius 1 across every tolerance. So the network
  with the least stable cell in the corpus is also the one with the flattest, most
  decisively-r=1 profile on three of four targets. Instability is a property of the
  (network, target, ε) cell, not of the network.

## 19a. The top-k arm — does the horizon move when the metric is precision@k?

*Added 2026-08-28 (`analyse_topk.py`, `results/RESULTS_topk.txt`, `results/topk_rstar.csv`).
Answers referee objection M7. No fits: `precision_at_1pct` and `precision_at_5pct` have
been columns in every sweep row since the sweep was written, and `locality_horizon`
(`influence/experiment.py:278`) has always taken a `metric=` argument. This needed a
caller, not an experiment.*

### The objection

Every r\*(ε) above is defined on Kendall τ over **all pairs**. τ is a bulk metric: on
ca-HepTh it scores about 37 million pairs, and almost all of them are two peripheral
authors whose relative order nobody will ever act on. The applied question is not "rank
all 8,638 nodes" — it is "who are the top 50 to seed, monitor or immunise". If the
horizon under precision@k differs from the horizon under τ, every r\* in this document
answers a question no practitioner asked.

### The result: it does not move

> **Regenerated 2026-09-12 by Claude Opus 5 (Task 6 runs C6; findings P1-01, P2-03).**
> The numbers in this subsection were produced on 2026-09-01. `analyse_topk.py` was re-run
> on the refit sweep (r=1 subgraph-tier cells refit after the orbit-5 retag) with
> betweenness on the reported log1p arm; the previous report is kept as
> `results/RESULTS_topk_pre_orbit5_refit_20260901.txt`. What moved, with the 2026-09-01
> value in brackets: shift distribution 2 / 10 / **72** / 14 / 2 cells (1 / 8 / 74 / 15 / 2),
> agreement **72%** (74%), mean shift +0.04 hops (+0.09); the 28 disagreeing cells split 16
> up / 12 down, exact sign test **p = 0.572** (17/9, p = 0.169) — still symmetric. By target:
> betweenness 76% (84), spread_resid 80% (76), spread_cv 72% (68), spread_mean 60% (68). By
> network: facebook 80% (90), ca-HepTh 75% (80), ca-GrQc 70% (70), email 70% (65), Gnutella
> 65% (65). By tolerance ε = 0.20 / 0.10 / 0.05 / 0.02 / 0.01: 70 / 90 / 75 / 65 / 60%
> (70 / 85 / 85 / 65 / 65). p@1% agrees with τ on 51% (47%) and with p@5% on 56% (54%);
> its disagreement is 29 down / 20 up, p = 0.253 (29/24, p = 0.583). The noise filter is
> still vacuous; the worst p@5% noise ratio is now email betweenness at 0.162 (was email
> spread_resid at 0.130). None of the conclusions drawn below changes: the horizon is
> metric-invariant to within threshold-crossing noise, p@1% is a blunter ruler, and the
> caveat about τ's zero-pair floor stands. The prose and tables below are left as the
> 2026-09-01 record; `results/RESULTS_topk.txt` is authoritative.

r\*(ε) computed under `precision_at_5pct` instead of `kendall_tau`, over all
**100 cells** (5 networks × 4 targets × 5 tolerances):

| shift in r\* | cells | |
|---|---|---|
| −2 hops | 1 | 1% |
| −1 hop | 8 | 8% |
| **0 — identical** | **74** | **74%** |
| +1 hop | 15 | 15% |
| +2 hops | 2 | 2% |

**Three quarters of cells give exactly the same horizon under both metrics**, and the
mean shift is +0.09 hops. More importantly the 26 disagreeing cells are **not
directional**: 17 up against 9 down, exact two-sided sign test **p = 0.169**. There is no
evidence that top-k needs systematically more or fewer hops than bulk τ.

This is the outcome that most favours the existing results, and it was not the expected
one — the plan's own framing anticipated a shift in one direction or the other, with
"either is a result". The actual answer is that r\*(ε) is **substantially
metric-invariant**, which is a stronger licence for the reported horizons than a
directional shift would have been.

Where the residual disagreement concentrates:

| by network | agree | | by target | agree |
|---|---|---|---|---|
| facebook_combined | 90% | | betweenness | 84% |
| ca-HepTh | 80% | | spread_resid | 76% |
| ca-GrQc | 70% | | spread_cv | 68% |
| email-Eu-core | 65% | | spread_mean | 68% |
| p2p-Gnutella08 | 65% | | | |

And by tolerance — the agreement is worst exactly where §19 already said r\* is least
stable, at the tightest tolerances:

| ε | 0.20 | 0.10 | 0.05 | 0.02 | 0.01 |
|---|---|---|---|---|---|
| agreement | 70% | 85% | 85% | 65% | 65% |

That pattern is consistent with the disagreement being **threshold-crossing noise**
rather than a metric effect: at tight ε the threshold sits on the flat part of both
curves, where a thousandth of movement changes which radius crosses first.

### precision@1% is not a second opinion — it is a blunter ruler

This is the part worth carrying into D2.

`precision_at_1pct` agrees with τ on only **47%** of cells and with `precision_at_5pct`
on **54%**. It agrees with nothing, including the other top-k metric. Its disagreement
with τ is even more symmetric than p@5%'s — 29 down, 24 up, sign test **p = 0.583**.

The reason is visible in the noise column. Seed sd as a fraction of each metric's own
r=0→3 range, averaged over the corpus:

| metric | noise ratio |
|---|---|
| `kendall_tau` | **0.014** |
| `precision_at_5pct` | 0.040 |
| `precision_at_1pct` | **0.113** |

p@1% is roughly **eight times noisier than τ** relative to the signal it is trying to
resolve, and on email-Eu-core's betweenness the ratio reaches **0.444** — the seed
spread is nearly half the entire radius-to-radius range. And the arithmetic reason is
not subtle:

| network | n | top 1% | top 5% |
|---|---|---|---|
| email-Eu-core | 986 | **10 nodes** | 49 nodes |
| facebook_combined | 4,039 | 40 | 202 |
| ca-GrQc | 4,158 | 42 | 208 |
| p2p-Gnutella08 | 6,299 | 63 | 315 |
| ca-HepTh | 8,638 | 86 | 432 |

**On email, precision@1% is measured on ten nodes.** One node is worth ten percentage
points. A metric with that granularity cannot support a threshold rule at ε = 0.01,
and its disagreement with τ carries no information about the horizon.

`precision@k` on graphs of a few thousand nodes is standard in the learned-centrality
literature, frequently at k = 1%, and usually reported without a seed spread. **A
single-seed p@1% on a 1,000-node graph is a ten-node measurement quoted to three
decimal places.** That belongs in D2 (§24.3) next to the zero-inflation argument: it is
the same class of finding — a headline metric whose reported precision vastly exceeds
what the evaluation can resolve.

### A caveat on the comparison itself, stated because it cuts against the result

r\*(ε) is "the smallest r reaching (1−ε) of the best observed value", and that definition
is metric-relative. τ-b on a zero-inflated target carries a large floor from boundary
pairs alone (§24) — on ca-GrQc roughly 0.71 of τ is the zero/nonzero question — whereas
p@5% has a floor near 0.05 from random guessing. So "90% of the ceiling" is a
substantially weaker bar on τ than on p@5%, and some of the 74% agreement is the two
definitions happening to bite at similar radii rather than the horizon being the same
object. **The invariance result is real but it is not as clean as a single agreement
percentage makes it look**, and a referee is entitled to press on exactly this.

A noise-based restriction was tried first and **dropped nothing** — no (network, target)
pair has a p@5% noise ratio above 0.20, the worst being email `spread_resid` at 0.130.
That is reported as a vacuous filter rather than tightened until it excluded something.

## 19b. Multiplicity — how many of this project's stars survive correction?

*Added 2026-08-28 (`analyse_multiplicity.py`, `results/RESULTS_multiplicity.txt`,
`results/multiplicity.csv`). Answers referee objection M5b. No fits.*

> **Revised 2026-09-12 by Claude Opus 5 (Task 6 findings P3-01 and P3-07; refit P1-01).**
> Two things changed in this section. (1) The stated per-comparison level of the star
> rule was wrong: "roughly α = 0.046" is P(|z| > 2), which is neither the rule's statistic
> nor its distribution. On ten seeds the rule is |t₉| > 2√10 = 6.32, two-sided
> α = 1.37 × 10⁻⁴, so a 60-comparison family expects **0.008** false stars under a global
> null, not "about three", and the whole 3,204-cell corpus expects 0.44, not 147. The
> consequence — a star can never fail BH here, because the smallest BH threshold a family
> of 60 can set at q = 0.05 is 8.3 × 10⁻⁴ — makes "withdrawn = 0" a property of the rule,
> not a finding of the correction. (2) The table was regenerated from the current sweep
> corpus, which since 2026-09-11 carries the r=1 subgraph-tier refit after the 5-node
> orbit radius retag (§26k.3); the previous table was computed on the pre-refit corpus and
> is kept below it, superseded, so the change is visible. `results/RESULTS_multiplicity.txt`
> is now the script's captured stdout; the 2026-09-01 version is archived as
> `results/RESULTS_multiplicity_pre_orbit5_refit_20260901.txt`. Betweenness rows come from
> the reported log1p arm (P2-03).

### The objection

Throughout this document a claim earns a ✱ when its paired per-seed gain beats **twice
the standard deviation** of that paired difference. On ten seeds that is |t₉| > 6.32,
a two-sided α of 1.37 × 10⁻⁴ per comparison, applied across a corpus of **3,204 swept
cells** with no correction anywhere. *(Superseded wording, 2026-08-28: "roughly
α = 0.046 two-sided … about 147 stars regardless … one 60-comparison family expects about
three." Wrong by the arithmetic in the note above.)* The referee's objection stands on
its own terms — the rule was never stated as a significance level and no correction was
applied — even though the level turns out to be far stricter than the wording implied.

### The result: nothing is withdrawn

Four families, 60 comparisons each, p-values from a paired t-test on the ten seed
differences, Benjamini–Hochberg within family. Current corpus (post-refit, 2026-09-12):

| family | comparisons | ✱ by the 2-sd rule | expected false ✱ under null | survive BH q<0.05 | survive BY q<0.05 | **withdrawn** |
|---|---|---|---|---|---|---|
| hop gain (r→r+1) | 60 | 54 | 0.008 | 57 | 56 | **0** |
| edge tier | 60 | 29 | 0.008 | 44 | 39 | **0** |
| subgraph tier | 60 | 25 | 0.008 | 43 | 34 | **0** |
| dynamic tier | 60 | 5 | 0.008 | 5 | 5 | **0** |

Superseded table (pre-refit corpus, as written 2026-08-28; kept for the old-vs-new
comparison required by §26k.3):

| family | comparisons | ✱ by the 2-sd rule | survive BH q<0.05 | survive BY q<0.05 | **withdrawn** |
|---|---|---|---|---|---|
| hop gain (r→r+1) | 60 | 53 | 57 | 57 | **0** |
| edge tier | 60 | 29 | 44 | 43 | **0** |
| subgraph tier | 60 | 37 | 53 | 48 | **0** |
| dynamic tier | 60 | 4 | 6 | 4 | **0** |

The subgraph-tier row is where the refit bites. A controlled comparison — the
`.preorbit5` backups of the same sweep files (under `cache_archive/pre_orbit5_20260911/` since 2026-09-13), with the same log1p betweenness arm spliced
in, so the r=1 refit is the *only* difference
(`results/multiplicity_refit_delta_20260912.txt`) — gives pre-refit family star counts of
54 / 29 / **41** / 5 against the post-refit 54 / 29 / **25** / 5. All sixteen lost stars
and all eleven lost BH-significant comparisons are subgraph-tier **r=1** rows; no
comparison gained a star or BH significance. Fourteen of the sixteen are `spread_*` rows
whose gains collapse from +0.003…+0.035 to within ±0.0005 (the shallow-tag inflation,
§26k.3); the other two are ca-HepTh and p2p-Gnutella08 betweenness at r=1, whose gains
fall from +0.0014 / +0.0007 to +0.0002 / +0.0001. Betweenness moved by at most 0.0043 τ
anywhere. Hop-gain rows moved only at r0→r1 and r1→r2, as they must — the retag changed
which hop six 5-node orbits belong to and nothing else. *(The superseded table's 37 for the
subgraph tier, and the 42 in the archived 2026-09-01 `RESULTS_multiplicity.txt`, are
snapshots of the corpus as it stood on those dates; neither is reproducible from the
2026-09-11 backups, which give 41 on either betweenness arm. Why the corpus moved between
2026-08-28 and 2026-09-11 is not established here — inferred, not verified: later sweep
appends de-duplicated by `analyse._read_dedup`'s keep-last rule. The 41 is the
like-for-like baseline for the refit.)*

*(BY = Benjamini–Yekutieli, which controls FDR under **arbitrary** dependence rather than
positive dependence. These cells are positively dependent — radii share seeds and
therefore fold splits, which is the entire point of pairing — so BH is the appropriate
procedure and BY is quoted as the conservative bound. The two barely differ.)*

**Not one starred claim in the project fails multiplicity correction.** The reason is
arithmetic and it should be stated because it was never the stated bar:

> The star rule is |mean| > 2·sd. The paired t-statistic is mean/(sd/√10) = √10·(mean/sd).
> So "beats 2 sd" is **|t| > 6.3**, not |t| > 2 — roughly **three times stricter** than a
> t-test at the same nominal α.

The project has been applying a bar far higher than "p < 0.05" while describing it in
language a referee reads as ordinary significance. The stars were safe by accident of a
conservative rule, not by design. **Every ✱ in this document should now be read as
"survives BH within its family", because it does.**

### The uncomfortable half: the document systematically *under*-claims

The correction runs the other way. In three of four families, substantially more
comparisons are significant than are starred — 44 against 29 on the edge tier, 43 against
25 on the subgraph tier *(post-refit counts, 2026-09-12; the 2026-08-28 text read "53
against 37")*. Fifteen edge-tier comparisons and eighteen subgraph-tier comparisons are
reliably nonzero and currently written up as nulls; 36 across the four families.

**This does not mean sixteen findings are being missed**, and the distinction is the
whole point of the exercise. Significance is not magnitude. Fifteen starred comparisons
across the corpus *(post-refit; twelve on 2026-08-28)* have |gain| < 0.001 — below the third decimal place this document
reports to. A gain of +0.0003 measured on ten seeds with sd 0.00006 is *real*, *reliably
reproducible*, and *worth nothing to anybody*.

The correct reporting discipline that follows, and which this document has not been
observing: **a claim needs both a q-value and an effect size, and "not significant" must
never be used where "negligible" is meant.** They came apart in exactly one place, below.

### One claim that has to change wording: the dynamic tier

§20 states "**the dynamic tier still adds nothing**". Under correction that is the wrong
sentence for two independent reasons.

**First, it is measured on 40 comparisons, not 60.** The `dynamic` tier contains exactly
two features, `perc_reach_2` (hop 2) and `perc_reach_3` (hop 3). There is *no dynamic
feature at hop 1*. So all twenty r=1 comparisons compare a feature set with itself:
**eighteen of them are bit-identical across all ten seeds**, and the other two
(ca-GrQc and ca-HepTh betweenness, now read from the log1p arm) differ by mean
2 × 10⁻⁸ and 2 × 10⁻⁷ with sd 7 × 10⁻⁸ and 1.5 × 10⁻⁶ — run-to-run floating-point
noise, not a feature effect *(post-refit, log1p-arm reading of 2026-09-12; the 2026-08-28
text, on the raw arm, read "nineteen … and the twentieth (facebook betweenness) differs by
3.9 × 10⁻⁹, consistent with the documented 5.08 × 10⁻⁸ floating-point tolerance")*. The r=1 third of that family is vacuous **by
construction**, not by measurement, and quoting it as evidence of a null is quoting the
absence of an input.

*(This also caught a bug in the audit script itself: its first version scored
zero-variance cells as maximally significant, fabricating 20 "significant" results from
cells whose differences were identically zero. The `+0.0000 ± 0.0000, q=0.0000` rows made
it obvious. Fixed by splitting the two zero-variance cases — all-differences-zero is
p = 1, a constant nonzero difference is p = 0.)*

**Second, on the 40 comparisons that are real, five survive BH at q < 0.05** *(six on
2026-08-28; the post-refit set is ca-GrQc `spread_mean` r=2 and r=3, ca-HepTh `spread_mean`
r=2 and r=3, facebook `spread_mean` r=2 — all `spread_mean`, all positive)*. The largest
is ca-GrQc `spread_mean` at r=3: **+0.00082 ± 0.00016**, q = 4 × 10⁻⁶. That is not
nothing; it is a reliably positive gain of eight ten-thousandths of a tau.

So the accurate statement is:

> The dynamic tier has no features below hop 2. Where it has features at all, its
> contribution is **reliably positive and negligibly small** — the largest gain anywhere
> is +0.0008, against +0.376 for one extra hop (largest hop gain in the corpus: +0.68,
> facebook `spread_cv` r0→r1). Giving the model a direct local
> approximation of the very process being predicted is worth about a five-hundredth of
> what one more hop is worth.

That is a **stronger** version of the original claim, not a retraction: "measurably
positive and still worthless" is harder to argue with than "adds nothing", which invites
the reply that the test was underpowered. §20 is corrected accordingly.

### Two assumptions, flagged rather than buried

- The paired t-test assumes the ten seed differences are approximately normal. At n = 10
  that is not seriously checkable. A distribution-free sign test is computed alongside in
  `results/multiplicity.csv`; it is much less powerful — its smallest attainable
  two-sided p at n = 10 is 0.002 — so it cannot support q < 0.001 claims at all, and it
  is reported as a floor rather than as the primary test.
- The four families are the sets a reader scans together looking for stars. Correcting
  across all 3,204 cells would correct across questions nobody asks jointly; correcting
  within a single table row would not be correcting at all. The choice of family is a
  judgement and it is recorded here so it can be disputed.

### Not done: the hierarchical model

The plan's stronger option — fit `tau ~ target * radius + (1 | network)` with seed as the
residual level, so partial pooling replaces per-cell testing — has **not** been run. BH is
the cheap correct answer; partial pooling would be the better one, and it would also give
a principled shrinkage estimate for the many tiny-but-significant gains above. Open item.

## 20. Finding 3 — depth beats richness, but richness is not nothing, and the reason is specific

### The claim has been revised twice, both times because the ladder improved

The original result was that adding edge and subgraph tiers changed τ by less than ±0.001. That was **vacuous**: five of the six edge/subgraph features were exact algebraic functions of node-tier features (§5), so `node → node+edge` could not have shown a gain. The measured zero was a property of the ladder.

With genuinely independent edge structure it became a real measurement, and richness helped the structural target only. With graphlet orbits added it changed again — and the second change is the interesting one.

### Where richness helps now

Subgraph-tier gain over node+edge, starred where it beats twice the seed sd:

| Network | Target | r=1 | r=2 | r=3 |
|---|---|---|---|---|
| ca-GrQc | **spread volatility** | **+0.0354** ✱ | +0.0008 | +0.0015 |
| ca-GrQc | **volatility residual** | **+0.0315** ✱ | +0.0008 | +0.0006 |
| ca-GrQc | **spread mean** | **+0.0134** ✱ | −0.0002 | +0.0006 |
| ca-GrQc | betweenness | +0.0006 | +0.0014 | **+0.0037** ✱ |
| email-Eu-core | spread mean | **+0.0026** ✱ | **+0.0036** ✱ | **+0.0062** ✱ |
| email-Eu-core | spread volatility | **+0.0044** ✱ | **+0.0028** ✱ | **+0.0059** ✱ |
| p2p-Gnutella08 | spread mean | **+0.0093** ✱ | +0.0012 | **+0.0027** ✱ |
| p2p-Gnutella08 | spread volatility | **+0.0074** ✱ | +0.0013 | **+0.0034** ✱ |

**Subgraph structure does help the dynamical targets, on all three networks — and mostly at radius 1.** That is the opposite of where anyone would look for it. (That was the three-network statement; it is re-tested at five immediately below, where the first half strengthens and the second acquires an exception.)

### Replication at five networks (2026-08-27)

The claim above was made on three. Re-measured on all five, paired within seed, `node+edge` → `node+edge+subgraph`, ✱ = |gain| > 2 sd:

| Network | target | r=1 | r=2 | r=3 |
|---|---|---|---|---|
| ca-GrQc | spread mean | **+0.0134** ✱ | −0.0002 | +0.0006 ✱ |
| ca-GrQc | spread volatility | **+0.0354** ✱ | +0.0008 | +0.0015 ✱ |
| ca-HepTh | spread mean | **+0.0046** ✱ | +0.0001 | +0.0008 ✱ |
| ca-HepTh | spread volatility | **+0.0141** ✱ | +0.0004 | +0.0028 ✱ |
| facebook_combined | spread mean | **+0.0103** ✱ | +0.0016 ✱ | +0.0015 ✱ |
| facebook_combined | spread volatility | **+0.0060** ✱ | +0.0000 | +0.0008 |
| p2p-Gnutella08 | spread mean | **+0.0093** ✱ | +0.0012 ✱ | +0.0027 ✱ |
| p2p-Gnutella08 | spread volatility | **+0.0074** ✱ | +0.0013 ✱ | +0.0034 ✱ |
| email-Eu-core | spread mean | +0.0026 ✱ | +0.0036 ✱ | **+0.0062** ✱ |
| email-Eu-core | spread volatility | +0.0044 ✱ | +0.0028 ✱ | **+0.0059** ✱ |

**The first half of the claim strengthens: all ten (network, target) pairs show a significant positive r=1 subgraph gain.** Ten for ten, on two networks that did not exist when the claim was made.

**The second half acquires an exception.** The r=1 gain is the largest of the three radii on eight of ten pairs — and the two that break it are both email-Eu-core, where r=3 is largest on both targets (+0.0062 and +0.0059, against +0.0026 and +0.0044 at r=1). So "mostly at radius 1" holds on four of five networks and is reversed on the fifth.

This is the **second** place email-Eu-core is the odd one out: it is also the only network with no volatility-residual signal (§23), where its `spread_resid` ceiling is 0.098 against 0.44-0.74 everywhere else. One network, two independent anomalies, one obvious shared cause — it is by far the smallest (n=986) and by far the densest (⟨k⟩=32.6). Which of those two is responsible is not separable with five observational networks, and it should not be asserted either way. It is the sharpest reason in this document to run the generated corpus (§14), where n and ⟨k⟩ move independently.

### Both tables above are pre-retag; at r=1 the subgraph tier now contributes nothing (2026-09-12)

> **Superseded 2026-09-12 by Claude Opus 5 (Task 6 finding P1-01, runs C2/C6).** The two
> tables above were measured when six 5-node orbits (56, 57, 65, 66, 68, 70) were tagged
> hop 1; the exact eccentricity derivation (`_calib.derive_node_radius`, gated by
> `verify_pipeline.py` 2c-5) puts them at hop 2, and every r=1 subgraph-tier cell was refit
> without them on 2026-09-11. The same paired construction on the refit sweep
> (`results/subgraph_gain_pre_post_retag_20260912.txt`; the pre-refit half of that file
> reproduces every number in the tables above to four decimals):

| Network | target | r=1 | r=2 | r=3 |
|---|---|---|---|---|
| ca-GrQc | spread mean | +0.0000 | −0.0003 ✱ | +0.0005 ✱ |
| ca-GrQc | spread volatility | +0.0001 | +0.0009 | +0.0013 ✱ |
| ca-GrQc | volatility residual | +0.0001 | +0.0015 | +0.0016 |
| ca-GrQc | betweenness | +0.0004 | +0.0023 | +0.0033 ✱ |
| ca-HepTh | spread mean | −0.0000 | +0.0002 ✱ | +0.0008 ✱ |
| ca-HepTh | spread volatility | −0.0002 | +0.0012 | +0.0026 ✱ |
| ca-HepTh | volatility residual | −0.0003 | −0.0001 | −0.0003 |
| ca-HepTh | betweenness | +0.0002 | +0.0055 ✱ | +0.0066 ✱ |
| email-Eu-core | spread mean | +0.0001 | +0.0036 ✱ | +0.0062 ✱ |
| email-Eu-core | spread volatility | +0.0002 | +0.0028 ✱ | +0.0058 ✱ |
| email-Eu-core | volatility residual | −0.0008 | +0.0103 | +0.0027 |
| email-Eu-core | betweenness | +0.0023 | +0.0002 | −0.0001 |
| facebook_combined | spread mean | −0.0002 | +0.0018 ✱ | +0.0015 ✱ |
| facebook_combined | spread volatility | −0.0003 | +0.0000 | +0.0013 |
| facebook_combined | volatility residual | −0.0001 | +0.0013 | +0.0000 |
| facebook_combined | betweenness | +0.0031 ✱ | **+0.0436** ✱ | +0.0256 ✱ |
| p2p-Gnutella08 | spread mean | −0.0000 | +0.0013 ✱ | +0.0027 ✱ |
| p2p-Gnutella08 | spread volatility | +0.0000 | +0.0027 ✱ | +0.0035 ✱ |
| p2p-Gnutella08 | volatility residual | −0.0005 | +0.0028 | +0.0042 ✱ |
| p2p-Gnutella08 | betweenness | +0.0001 | +0.0019 ✱ | +0.0020 ✱ |

> Betweenness rows here are on the reported log1p arm (§26b); the pre-retag tables above
> carried the raw arm, which is why facebook r=2 reads +0.0436 rather than +0.1291 (§26a/§26k).
>
> **What this reverses.** "All ten (network, target) pairs show a significant positive r=1
> subgraph gain" — ten for ten — becomes **zero for ten**: every r=1 spread-target gain is
> within ±0.0008 of zero and none clears twice its paired sd. The r=2 and r=3 columns are
> unchanged to the last digit for the spread targets (those cells were never refit; the
> cumulative sets contain both hops either way). So "richness helps the dynamical targets
> mostly at radius 1" was a radius-tagging artefact: the six orbits carried the whole r=1
> signal, and they are hop-2 quantities. What survives of Finding 3's richness half is
> smaller and lives one hop further out: subgraph gains of +0.001 to +0.006 at r≥2 on the
> spread targets, and the facebook betweenness rung at r=2 (§26a). The step-decomposition
> table that follows and its "It is the step from 4-node to 5-node graphlets" heading are
> the three-network, pre-retag record; §26k.3 carries the five-network reversal
> (17/20 → 0/20 flagged cells for the 5-node step).

### It is the step from 4-node to 5-node graphlets, and nothing else

Decomposing the r=1 subgraph tier, ten seeds, paired.

> **Scope: three networks, not five.** `results/RESULTS_r1_subgraph_ablation.txt` contains
> three blocks — ca-GrQc, p2p-Gnutella08, email-Eu-core. The ablation has **never been run
> on ca-HepTh or facebook_combined**, so the attribution below is not known to hold on the
> two networks added in the corpus expansion. The claim it supports — that 5-node orbits
> earn their cost — is therefore a three-network claim, and the r=1 subgraph *gain* it
> explains is five-for-five (table above) while its *explanation* is three-for-three. Open
> item as of 2026-08-28.

*spread volatility:*

| step | ca-GrQc | p2p-Gnutella08 | email-Eu-core |
|---|---|---|---|
| + pre-ORCA subgraph (ego-betweenness, triangles) | −0.0000 ± 0.0003 | +0.0000 ± 0.0001 | −0.0001 ± 0.0001 |
| + the five **4-node** hop-1 orbits | +0.0001 ± 0.0003 | −0.0000 ± 0.0001 | +0.0001 ± 0.0002 |
| **+ the seventeen extra 5-node hop-1 orbits** | **+0.0353 ± 0.0014** ✱ | **+0.0074 ± 0.0004** ✱ | **+0.0044 ± 0.0006** ✱ |

*spread mean:*

| step | ca-GrQc | p2p-Gnutella08 | email-Eu-core |
|---|---|---|---|
| + pre-ORCA subgraph | +0.0000 ± 0.0001 | −0.0000 ± 0.0001 | −0.0001 ± 0.0001 |
| + the five **4-node** hop-1 orbits | +0.0000 ± 0.0001 | −0.0001 ± 0.0001 | +0.0000 ± 0.0001 |
| **+ the seventeen extra 5-node hop-1 orbits** | **+0.0134 ± 0.0005** ✱ | **+0.0094 ± 0.0004** ✱ | **+0.0026 ± 0.0003** ✱ |

*volatility residual:* ca-GrQc **+0.0317 ± 0.0036** ✱, Gnutella **+0.0060 ± 0.0009** ✱, email +0.0115 ± 0.0065 (positive, not significant).

**Neither the old subgraph features nor the 4-node orbits contribute anything at radius 1, on any network, for any target.** Every increment in those two rows is within noise of zero. The attribution replicates exactly even though the magnitude does not — ca-GrQc gains five times what email does. **Four-node graphlets are simply not expressive enough to describe an ego network; five-node ones are.** That is a clean answer to an open decision the project had been carrying (§ open decisions): *5-node orbits justify their cost, and specifically at radius 1.*

> **Reconciled against the five-network measurement, 2026-09-11 by Claude Opus 5 (see §26k.3).**
> The paragraph above is retained as written; the tables above it are three-network,
> three-target, older-feature-table numbers and remain so. The 800-cell matched run
> (5 networks × 4 targets × 4 nested sets × 10 seeds) now bears on all three of its claims,
> and it does not support them equally.
>
> - **"The 4-node orbits contribute nothing at radius 1, on any network, for any target" —
>   upheld, and now on five networks and four targets.** `add_orbit_lt15` flags **0 of 20**
>   cells; its absolute mean gain never exceeds 2.5 × 10⁻⁴ anywhere.
> - **"Neither the old subgraph features … contribute anything" — narrowed.** The non-orbit
>   subgraph step flags on **2 of 20** cells, and both are `betweenness`: email-Eu-core
>   +0.00254 (sd 0.00108) and facebook_combined +0.00349 (sd 0.00138). The original claim
>   was made from tables that contained no betweenness column at all, which is exactly where
>   the exception lives. It is a target-specific effect, not a tier-wide one, but "nothing …
>   for any target" is too strong.
> - **"Four-node graphlets are not expressive enough … five-node ones are" — upheld in
>   direction, not as a universal.** The 5-node step flags on 17 of 20 cells with gains to
>   +0.035, but it does not flag on ca-GrQc/`betweenness` (+0.00045, sd 0.00081) or
>   email-Eu-core/`spread_resid`, and on **email-Eu-core/`betweenness` the mean gain is
>   negative** (−0.00049, sd 0.00037, nine of ten seeds worse). That is a small consistent harm
>   pointing opposite to every other network, and it is retained rather than absorbed.
>
> The three magnitudes above that the new run can compare directly reproduce closely on a newer
> feature table (ca-GrQc: spread_cv +0.0353 → +0.03515, spread_mean +0.0134 → +0.01340,
> volatility residual +0.0317 → +0.03191). Radius one only.
>
> **Reversed 2026-09-12 by Claude Opus 5 (see the superseding block at the top of §26k.3).**
> Both the tables above and the 2026-09-11 run were fitted with six 5-node orbits tagged hop 1
> that reach two hops. Rerun on the corrected registries, `add_remaining_g5_orbits` flags
> **0 of 20** cells (largest |mean| 0.00054 τ), so the third bullet — "four-node graphlets are
> not expressive enough … five-node ones are" — is **not upheld at radius one in any form**.
> The close reproduction noted in the previous paragraph is now evidence that the three-network
> tables rested on the same shallow tag (inferred, not separately measured). The first two
> bullets stand: the 4-node orbit step still flags nothing, and the non-orbit subgraph step
> still flags exactly the two `betweenness` cells, with unchanged magnitudes.

### Depth still wins, by roughly an order of magnitude

The largest richness gain anywhere is +0.035. One extra hop buys up to +0.376. The original conclusion stands — depth dominates — but "richness is worthless" was an artefact of asking with too poor a vocabulary, twice.

> **Superseded in its general form (see §26a).** Both numbers in that paragraph are
> three-network numbers. On facebook_combined's betweenness the subgraph tier alone is worth
> **+0.129** at fixed radius (and the whole ladder above `node` +0.160), against +0.197 for
> the r1→r2 hop on the same cell — the same
> order of magnitude, not an order apart. Depth still wins on average and wins outright on
> the sparse networks; the *ratio* is a property of the network, not a constant. The
> paragraph is kept because the three-network measurement it reports is correct and the
> revision is easier to read against it.

### The dynamic tier is measurably positive and still negligible

*Reworded 2026-08-28 after the multiplicity audit (§19b). It previously read "the dynamic
tier still adds nothing", which was wrong in two ways: it counted twenty comparisons that
are vacuous by construction, and it called a reliably nonzero effect a null.*

`perc_reach_ℓ` — a mechanistic local estimate of the cascade, assuming knowledge of p —
exists only at hops 2 and 3, so **there is no dynamic tier at r=1** and the twenty r=1
comparisons are a feature set against itself (eighteen bit-identical, two differing at the
10⁻⁷ level on the log1p betweenness arm). On the forty comparisons that are real, **five
survive Benjamini–Hochberg at q < 0.05** *(figures updated 2026-09-12 by Claude Opus 5 to
the post-refit corpus, §19b; previously "six", "nineteen … one differing by 4 × 10⁻⁹",
"+0.00083 ± 0.00021, q = 1.4 × 10⁻⁶")*, the largest being ca-GrQc `spread_mean` at r=3:
**+0.00082 ± 0.00016**, q = 4 × 10⁻⁶.

So the tier is not a null — it is **reliably positive and negligibly small**. Its largest
gain anywhere is +0.0008 against +0.376 for one extra hop, a ratio of about 1:450.
Giving the model a direct local approximation of the very process being predicted buys
something real and worth essentially nothing next to looking one hop further.

That is a stronger claim than the original, not a weaker one: "measurably positive and
still worthless" cannot be answered with "your test was underpowered."

### A caution about how "redundant" was measured

`orbit_04` is 0.99 rank-correlated with existing columns and still produced a ten-sigma gain in the 4-node-only table. **High correlation is not redundancy.** The effective-dimensionality figure in §5 measures *monotone* redundancy — the right instrument for exact algebraic duplicates, a poor one for "adds nothing predictive". The algebraic identities remain exact; a 0.99 correlation is a weaker and different claim.

### The edge axis, and where the expansion stops paying

ORCA's 4-node **edge** orbits are in (12, aggregated three ways). The edge tier's own gain is now significant for betweenness on ca-GrQc (+0.0097, +0.0082, +0.0060 across radii) and for Gnutella betweenness at r≥2, so the edge axis is no longer inert either.

**5-node edge orbits were implemented, radius-calibrated and then declined on evidence.** `analyse_edge5.py` compares the full structural tier with 4-node against 5-node edge orbits, paired over ten seeds — on **two networks**, chosen as the sparse/dense extremes of the three-network corpus. That was a decision to *not add* features, so the evidence bar is lower than for a positive claim; but note it was taken before facebook_combined existed, and facebook is the one network where the edge axis turned out to carry a large effect (§26a). The decision is not re-opened here, and it is flagged as resting on a corpus that excludes its most edge-sensitive member:

> **Table below is pre-retag and raw-arm — re-run scheduled, 2026-09-12 by Claude Opus 5
> (Task 6 findings P1-01/P2-11, run C8).** On 2026-09-11 nine 5-node *edge* orbits (49, 50,
> 51, 59, 60, 61, 63, 64, 65) and six 5-node *node* orbits were found to sit at hop 2, not
> hop 1, so the r=1 column of this table compared column sets a radius-1 observer cannot
> compute; the r=2/r=3 columns are unaffected (cumulative sets contain both hops). The
> betweenness rows are raw squared-error fits, not the log1p arm §26b reports. The lane is
> being re-run on all five networks with the corrected tables
> (`results/phase6_root_integration_stage3_20260912.ps1` → `results/RESULTS_edge5.txt`,
> plus a betweenness-only log1p run); until that lands, this table is the 2026-08-26
> historical record, kept at `results/c8_historical_pre_20260912/RESULTS_edge5.txt`. See
> `results/HISTORICAL_LANES_NOTE_20260912.md`.

| Network | Target | r=1 (+39 cols) | r=2 (+132 cols) | r=3 (+165 cols) |
|---|---|---|---|---|
| ca-GrQc | spread mean | +0.0004 ✱ | −0.0002 | −0.0002 ✱ |
| ca-GrQc | volatility | +0.0020 ✱ | +0.0002 | +0.0001 |
| ca-GrQc | betweenness | +0.0000 | +0.0015 | +0.0016 |
| email-Eu-core | spread mean | +0.0004 | **−0.0007** ✱ | **−0.0006** ✱ |
| email-Eu-core | volatility | +0.0004 ✱ | **−0.0007** ✱ | −0.0002 |
| email-Eu-core | betweenness | −0.0007 | −0.0002 | −0.0021 |

The largest gain anywhere is +0.0020, and several entries are *significantly negative* — past roughly forty extra columns the additions dilute rather than help. They are off by default; `edge_graphlet_size=5` turns them on.

**The asymmetry with node orbits is the interesting part.** Widening the *node* orbit vocabulary from 4-node to 5-node was a decisive win at radius 1 (+0.035 on ca-GrQc volatility). Widening the *edge* vocabulary the same way buys nothing anywhere. Whatever five-node ego structure encodes about spreading, it is a property of the node's position within it rather than of the individual edges.
## 21. Finding 4 — the horizon is a property of the network, and specifically not of its density

**Revised on the five-network corpus (2026-08-27).** The three-network version of this finding argued that density does not determine the horizon, resting on a single coincidence: ca-GrQc and Gnutella have almost the same mean degree and behave differently. That is one data point and it could have been luck. Adding ca-HepTh and facebook_combined was designed to break the argument if it was wrong, and it did not break it — it made it much stronger, because the two additions form a matched pair on each side.

All five networks at the same dynamical regime (p = 1.5 × β_c, 4,000 sims, uniform), spread mean:

| Network | ⟨k⟩ | family | τ at r=0 (degree alone) | τ at r=3 | still gaining at r=3? |
|---|---|---|---|---|---|
| facebook_combined | 43.7 | social ego-nets | 0.6705 | 0.9586 | marginally (+0.0012) |
| email-Eu-core | 32.6 | communication | 0.8619 | 0.9687 | marginally (+0.0049) |
| p2p-Gnutella08 | 6.6 | peer-to-peer | 0.6705 | 0.9159 | **yes (+0.0292)** |
| ca-GrQc | 6.5 | collaboration | 0.7807 | 0.9441 | barely (+0.0025) |
| ca-HepTh | 5.7 | collaboration | 0.7228 | 0.9508 | barely (+0.0047) |

### The same-family replicate

ca-HepTh and ca-GrQc are both arXiv collaboration graphs, with mean degree 5.7 against 6.5 — same generative process, near-identical density. If the horizon is a property of the network's *kind*, they should agree. Their r\*(ε) profiles, at ε = 0.02, ten seeds:

| target | ca-GrQc | ca-HepTh |
|---|---|---|
| betweenness | 1 (10/10) | 1 (10/10) |
| spread mean | 2 (10/10) | 2 (10/10) |
| spread volatility | 2 (7/10) | 3 (10/10) |
| volatility residual | 3 (10/10) | 3 (10/10) |

Three of four agree exactly, and the fourth differs by one hop on the one cell where ca-GrQc's own seed stability was weakest (7/10 — a near coin-flip, flagged as such in §19). The whole shape of the curve replicates: both start near 0.72–0.78 on degree alone, both finish near 0.945–0.951, both have the volatility residual as their longest-horizon target. This is the first genuine replication in the project — two independent graphs of the same kind, measured end to end, agreeing.

### The matched dense pair, which is where the density hypothesis dies

facebook_combined (⟨k⟩ = 43.7) is *denser* than email-Eu-core (32.6). If density set the horizon, it should saturate at least as fast. On spreading it does. On **betweenness** it does the opposite:

| | email-Eu-core | facebook_combined |
|---|---|---|
| ⟨k⟩ | 32.6 | 43.7 |
| betweenness τ at r=0 | 0.7429 | **0.3038** |
| betweenness τ at r=3 | 0.9030 | 0.8514 |
| r1→r2 marginal gain | +0.0056 | **+0.1970** |
| r\*(ε=0.02) | 1 | **3** |

Degree alone predicts betweenness on email at τ = 0.74; on the denser facebook it manages 0.30. Email is finished at one hop; facebook is still gaining +0.197 at the second and +0.028 at the third. Two networks, the denser one with the **longer** horizon and the weaker degree baseline — density cannot be the explanatory variable.

The structural reason is visible in what the graphs are. facebook_combined is a union of ego networks: dense friend groups joined by a small number of bridges. Degree measures how big your friend group is, which says almost nothing about whether you are one of the bridges — and betweenness is almost entirely about the bridges. Email-Eu-core is one institution where the high-degree people genuinely are the hubs everything routes through. Same density, opposite relationship between degree and brokerage.

### What can now be claimed, and what cannot

**Can:** the horizon is a property of the network, it is not a function of mean degree, and it replicates within a family. Two collaboration graphs agree to within one hop on every target; two dense graphs disagree by two hops on betweenness.

**Cannot:** that *family* is the causal variable. Five observational networks cannot separate family from the things that co-vary with it (modularity, clustering, degree-tail shape, assortativity). The correspondence is now a five-point one with a matched pair on each arm rather than a three-point one, which is a real strengthening — but it is still observational. The generated corpus in §14 remains the instrument that would move one structural parameter at a time, and it is still unswept.

## 22. Finding 5 — discriminability peaks near criticality

Degree-versus-spread rank correlation on email-Eu-core, as p sweeps through multiples of β_c:

| multiple of β_c | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 | 5.0 |
|---|---|---|---|---|---|---|
| τ(degree, spread) | 0.916 | 0.860 | 0.880 | 0.906 | 0.938 | 0.960 |

The correlation dips to a **minimum near criticality**. That is exactly the regime where looking beyond degree pays most — and therefore the regime where our question is most interesting. It also justifies running at a small multiple of β_c rather than at an arbitrary p.

## 23. Finding 6 — volatility beyond the mean is predictable on some networks and not others

`spread_resid` is spread volatility with the mean's mechanical contribution regressed out (§2.3). It is the control against the objection that a good volatility result is just the mean predicted twice. It had been implemented and never run. Run, it says:

| Network | ⟨k⟩ | τ at r=3 | reading |
|---|---|---|---|
| facebook_combined | 43.7 | 0.7378 ± 0.0017 | **strongest residual signal in the corpus** |
| ca-HepTh | 5.7 | 0.7191 ± 0.0005 | substantial genuine signal |
| ca-GrQc | 6.5 | 0.6715 ± 0.0019 | substantial genuine signal |
| p2p-Gnutella08 | 6.6 | 0.4375 ± 0.0032 | real, and still climbing steeply |
| email-Eu-core | 32.6 | 0.0802 ± 0.0137 | essentially nothing |

On email-Eu-core the raw volatility result (τ = 0.963) **was** the mean in disguise — once the mean is removed almost no predictable signal remains, and r\* becomes unstable across seeds (7/10 at ε=0.01, §19). Everywhere else a large residual signal survives, and on Gnutella it has the **longest horizon of any target measured**, still gaining +0.065 between r=2 and r=3.

### Revision: this was read as a density effect, and it is not (2026-08-27)

The three-network version of this finding said "the objection is correct for the dense network and wrong for the sparse ones," and generalised from a single dense network to density as such. facebook_combined falsifies that generalisation directly. It is the **densest** graph in the corpus at ⟨k⟩ = 43.7 — a third denser than email — and it has the **largest** residual signal of all five, τ = 0.7378 against email's 0.0802. An order of magnitude apart, in the direction opposite to the one density predicts.

So the correct statement is the narrow one: **email-Eu-core is the network where volatility is the mean in disguise**, and nothing about its density explains that. Four of five networks retain a large predictable residual; email is the exception, not the representative of a class.

What plausibly distinguishes it is left explicitly open. Email is by far the smallest graph (n = 986 against 4,039–8,638), which alone makes its residual the noisiest quantity measured here — its seed spread, ±0.0137, is the largest in the table and roughly eight times ca-HepTh's. A residual that is mostly noise cannot be predicted by anything, and a near-zero τ is exactly what that looks like. Whether email's null is a structural fact about institutional email or an artefact of having 986 nodes is **not resolved by this corpus**, and it should not be asserted either way until a second communication network of comparable size is run.

This is the second finding in the project revised by adding networks rather than by finding a bug, and both revisions ran the same way: a claim indexed to a *property* (density) turned out to be indexed to a *single network*. Three points are enough to notice a pattern and not enough to name its cause.

## 24. Finding 7 — the betweenness result is real, and needs a stated caveat

Betweenness has the largest r0→r1 jump *of any betweenness measurement* (+0.3759 on ca-GrQc) and is the clearest case of early saturation. *(Corrected 2026-08-28 on two counts: the figure was written as +0.3750, and the claim was "largest in the project" — which was true of the three-network corpus and is not true now. facebook_combined's `spread volatility` gains +0.6897 at the same step, §18.)* Both facts have the same cause, and it must be stated before a reader finds it.

A large share of nodes have betweenness **exactly zero**. Kendall τ-b drops pairs tied in the truth, but still scores every zero-versus-nonzero pair:

| Network | betweenness = 0 | share of τ-b's scored pairs that are zero-vs-nonzero |
|---|---|---|
| ca-GrQc | 55.0% | 71.0% |
| ca-HepTh | 48.5% | 65.4% |
| p2p-Gnutella08 | 27.8% | 43.5% |
| email-Eu-core | 15.1% | 26.3% |
| **facebook_combined** | **8.5%** | **15.6%** |

So on ca-GrQc most of the "prediction problem" is one binary question.

**The five-network corpus sharpens this caveat considerably (2026-08-27).** The zero-inflation is not a fixed nuisance — it varies from 71% of scored pairs down to 16%, and it varies *inversely* with how hard the betweenness problem actually is. The two collaboration graphs, where τ looks best (0.92 at r=3), are the two where the score is most inflated: roughly two thirds of what τ rewards there is the zero/nonzero question, which §24 shows has an **exact** local answer. facebook_combined, where only 16% of scored pairs are that question, is the cleanest betweenness measurement in the corpus — and it is also where locality does worst: degree alone reaches τ = 0.30, and even at r = 3 the full structural model reaches only 0.85.

Put the two together and the ordering reverses. On the inflated networks locality looks near-perfect at betweenness; on the network where the metric is not doing the work for us, betweenness is the hardest target measured and has the longest horizon (r\* = 3 at ε = 0.02, §21). The saturation conclusion survives on the collaboration graphs, but **the corpus-wide impression that "betweenness saturates early" is substantially an artefact of which networks happened to be in the corpus**. It does not hold on the one graph where the target is nearly zero-free. And that question has an **exact local answer**:

### 24.1 The zero set, stated as a theorem *(formalised 2026-08-28)*

This was previously carried as an empirical check with an informal argument beside it. It is a theorem, and stating it as one is worth doing: it converts a 24,000-node verification into three sentences, it makes the *radius* at which the zero set is decidable explicit, and — see §24.3 — it is the engine of a much larger claim about how the whole learned-betweenness literature is scored.

> **Proposition.** Let G be a finite connected simple graph, v a vertex, and let betweenness exclude endpoints. Then
>
> ```math
> betweenness(v) = 0 \iff ego\_betweenness(v) = 0 \iff N(v) \text{ induces a clique}
> ```
>
> — that is, if and only if v is **simplicial**.
>
> *Proof.* (⇐) Suppose every two neighbours of v are adjacent. Any path `s … a v b … t` passing through v enters via some `a ∈ N(v)` and leaves via some `b ∈ N(v)`; since `ab ∈ E`, the path can be shortcut by replacing `a v b` with `a b`, strictly reducing its length. So no geodesic has v as an interior vertex, giving `betweenness(v) = 0`; the identical argument inside the ego graph gives `ego_betweenness(v) = 0`.
>
> (⇒) Suppose some `u, w ∈ N(v)` are non-adjacent. Then `d(u,w) = 2` and `u–v–w` is a geodesic, so `σ_uw(v) ≥ 1` and `betweenness(v) ≥ σ_uw(v)/σ_uw > 0`. The same pair witnesses `ego_betweenness(v) > 0`, since u, w and all their common neighbours lie inside the ego graph. ∎
>
> Nodes of degree < 2 are simplicial vacuously and are zero on both sides.

**Attribution — this proposition is NOT new, and the priority search found who has it (2026-09-05).** The mathematical content is known and is already in production use in exactly this literature. Maurya et al.'s GNN-Bet (CIKM 2019; ACM TKDD 15(5), 2021) prunes from the adjacency matrix "those nodes that lie on no shortest path"; BRAVA-GNN (arXiv:2602.09716, CIKM '26) restates the rule explicitly as its preprocessing step — *isolated or leaf nodes* have zero centrality, and for *clique neighborhoods*, "any shortest path between them will favor the direct edge (length 1) over a path through the node (length 2)". That is the (⇐) direction, verbatim, in someone else's paper.

What is written above therefore stands as a **statement and proof of a known fact** — kept because the project needs it stated precisely, and because the ⇔ with `ego_betweenness` is the form the pipeline actually checks — and **not** as a novel result. Any write-up must cite Maurya et al. here.

**Positioning corrected 2026-09-07.** Zero-set preprocessing is prior art, and BRAVA-GNN computes and ships the nonzero-subset tau. The earlier claim that nobody removes zeros from the score was false. The remaining proposal concerns explicit joint reporting, support reconciliation and reconstructible decision/tie metadata (§26i–§26j), not invention of zero filtering. The precise novelty claim still requires paper-stage positioning; see `docs/archive/phase6_record.md#rec-priority_search_D2`.

**The consequence that matters, and it is a statement about radius.** Membership in the zero set is **decidable exactly from the radius-1 ego graph** — no approximation, no model, no training. A global property vanishing has a strictly local, O(k²) certificate.

This is not a footnote to the thesis; it is an instance of it. The project's claim is that different targets have different locality horizons. Here is a component of one target whose horizon is provably **exactly 1**, and it happens to be the component that dominates τ on the sparse networks. It also explains Finding 3's exception cleanly: `ego_betweenness` is a subgraph-tier feature, which is why structural richness helps betweenness and almost nothing else.

### 24.2 The empirical check is now a canary, not the evidence

The pipeline check is **kept**, with its role relabelled: it no longer supplies the truth of the proposition (mathematics does that) but guards the *implementation*. If `exact_betweenness` or `ego_betweenness` is ever broken by a refactor, the two will disagree and the check will catch it — which is exactly the class of error this project has been bitten by twice.

Measured: **zero mismatches on all 24,120 nodes of the five-network corpus** (`results/RESULTS_betweenness.txt`). `clustering_coefficient = 1` is *not* equivalent — it misses degree-1 nodes, disagreeing on 675 / 1,462 / 95 / 75 / 1,744 nodes across ca-GrQc / ca-HepTh / email / facebook / Gnutella, which is precisely the vacuous-simpliciality case the proposition handles explicitly.

> **Scope gap found and closed, 2026-08-28.** Until this date the zero-inflation table above covered five networks while the verification underneath it covered three (11,443 = 4,158 + 986 + 6,299) — `analyse_betweenness.py` had not been re-run since the corpus expanded, so ca-HepTh and facebook_combined had never had this check applied at all. Two of the five rows of the table above were being read against a guard that had never been pointed at them. Both now pass with zero mismatches.
>
> The re-run also made the script **read the sweep's stored out-of-fold predictions instead of refitting**, which removed 200 redundant forest fits and — the more important half — guarantees that the nonzero-subset column below describes the *same models* as the full-τ column beside it, rather than an independent refit that could silently drift from it.

### 24.3 τ restricted to the nodes where betweenness actually varies

**All five networks, 171 features, ten seeds, read from the sweep's own stored predictions (2026-08-28).** The previous version of this table covered three networks and predated the 64 → 171 feature expansion; both the numbers and the conclusion drawn from them have changed.

| radius | ca-GrQc all / nonzero | ca-HepTh all / nonzero | email all / nonzero | facebook all / nonzero | Gnutella all / nonzero |
|---|---|---|---|---|---|
| 0 | 0.5422 / 0.4264 | 0.6611 / 0.5354 | 0.7429 / 0.6699 | 0.3038 / 0.2783 | 0.8853 / 0.7973 |
| 1 | 0.9181 / 0.7266 | 0.8990 / 0.7119 | 0.8984 / 0.8731 | 0.6269 / 0.6156 | 0.9233 / 0.8652 |
| 2 | 0.9215 / 0.7526 | 0.9153 / 0.7596 | 0.9041 / 0.8862 | 0.8239 / **0.8463** | 0.9337 / 0.8834 |
| 3 | 0.9216 / 0.7532 | 0.9162 / 0.7652 | 0.9030 / 0.8858 | 0.8514 / **0.8743** | 0.9367 / 0.8888 |

**The gap tracks the zero fraction, as the decomposition says it must.** At r=3 the drop from full τ to nonzero τ is 0.168 on ca-GrQc (55.0% zeros), 0.151 on ca-HepTh (48.5%), 0.048 on Gnutella (27.8%), 0.017 on email (15.1%). Four networks, monotone in z, exactly as predicted.

**And then facebook_combined inverts the sign — the only network in the corpus that does.** At r=2 and r=3 its nonzero τ is *higher* than its full τ (+0.022 and +0.023, against paired seed sds of 0.003-0.005, so this is not noise). Restricting to the nodes where betweenness actually varies makes the model look **better**, not worse.

This is not an anomaly to be explained away; it is what the zero-inflation account predicts at the small-z end, and it is worth stating precisely. On a network with 55% zeros, τ is largely rewarding a binary question with an exact radius-1 answer (§24.1), so removing those pairs takes away easy credit and τ falls. On facebook only 8.5% of nodes are zero and only 15.6% of scored pairs are boundary pairs — there is almost no easy credit to remove. What is left is that facebook's few zero nodes are ones the model ranks *badly*, so excluding them removes a source of error rather than a source of inflation.

**The practical consequence, and it is the one that matters for reading anyone's results:** the full-τ column and the nonzero column do not differ by a fixed correction factor, and they do not even differ in a fixed *direction*. On four of five networks full τ flatters the model; on the fifth it understates it. A single reported τ cannot be adjusted into the other by any rule of thumb — the two must both be reported, per network. §24.4 makes this quantitative and turns it into a scoring protocol.

**The saturation conclusion survives the restriction where it was claimed.** ca-GrQc still flattens after r=1 on the nonzero subset (0.7266 → 0.7526 → 0.7532), so Finding 7 is not an artefact of zero-inflation — it is just smaller than the headline number suggests. But note that facebook does *not* flatten on either column, which is consistent with the rest of Finding 7: it is the network where betweenness is genuinely hard and the horizon genuinely long.

### 24.3a The same table on the reported objective: facebook no longer inverts (2026-09-12)

> **Regenerated 2026-09-12 by Claude Opus 5 (Task 6 finding P2-03, run C6).** The table in
> §24.3 was read from `cache_oof_<tag>.npz`, which is the **raw squared-error** arm — the
> arm §26b showed was mis-specified and §26d replaced (adopted 2026-09-04). `analyse_betweenness.py` now reads the
> reported `rf_log1p` archive by default (`--arm=raw` reproduces the old table; kept as
> `results/RESULTS_betweenness_pre_orbit5_refit_20260828.txt`), and the r=1 rows also carry
> the 2026-09-11 orbit-5 refit. Same models as §26d's ladder, same seeds, same nodes:

| radius | ca-GrQc all / nonzero | ca-HepTh all / nonzero | email all / nonzero | facebook all / nonzero | Gnutella all / nonzero |
|---|---|---|---|---|---|
| 0 | 0.5560 / 0.3665 | 0.6611 / 0.5020 | 0.7831 / 0.7219 | 0.5944 / 0.5290 | 0.8848 / 0.7966 |
| 1 | 0.9197 / 0.7365 | 0.9024 / 0.7194 | 0.9078 / 0.8774 | 0.8095 / 0.7747 | 0.9235 / 0.8646 |
| 2 | 0.9288 / 0.7754 | 0.9193 / 0.7711 | 0.9131 / 0.8857 | 0.9233 / 0.9096 | 0.9357 / 0.8862 |
| 3 | 0.9283 / 0.7765 | 0.9199 / 0.7759 | 0.9134 / 0.8862 | 0.9303 / 0.9187 | 0.9387 / 0.8916 |

> **What changes.** The facebook inversion does not survive the objective. On the reported
> arm its nonzero τ sits *below* its full τ at every radius (r=2: 0.9096 vs 0.9233; r=3:
> 0.9187 vs 0.9303, gaps of 0.012-0.014 against seed sds of 0.001), the same direction as the
> other four. The r=3 full-minus-nonzero gap is now monotone in the zero fraction on **all
> five** networks: 0.152 (ca-GrQc, 55.0%), 0.144 (ca-HepTh, 48.5%), 0.047 (Gnutella,
> 27.8%), 0.027 (email, 15.1%), 0.012 (facebook, 8.5%). So the paragraph above that reads
> the inversion as "what the zero-inflation account predicts at the small-z end" was
> explaining a property of the mis-specified model: the raw-objective forest on facebook
> was so poor at the zero/nonzero question (full τ 0.30 at r=0) that removing the boundary
> pairs *helped* it; the log1p forest gets that question right and the ordinary decomposition
> takes over.
>
> **What does not change.** The direction argument in §24.4 needs only that boundary pairs
> carry a share `w` of the scored pairs and that a radius-1 rule answers them exactly; it
> never depended on facebook inverting, and the recommendation to report both columns per
> network stands — the gap still ranges from 0.012 to 0.152 across the corpus. ca-GrQc still
> saturates on the nonzero subset (0.7365 → 0.7754 → 0.7765), so Finding 7 survives on the
> reported arm as it did on the raw one; facebook still does not flatten on either column.
> "On four of five networks full τ flatters the model; on the fifth it understates it"
> should now be read as: **on all five, full τ flatters the model, by an amount that tracks
> z.** Finding 8's failure atlas (§25) and fig2 were regenerated on the same arm
> (`docs/archive/phase6_record.md#rec-REGENERATION_NOTE_20260912`).

### 24.4 The zero-inflation decomposition, in closed form

Everything above is a statement about *this* corpus. It generalises, and the generalisation is the more useful object — because it applies to every published paper that scores learned betweenness with Kendall τ, and it can be evaluated for any benchmark graph **without running anyone's model**.

Let `z = |{v : b(v) = 0}| / n` be the zero fraction and `m = 1 − z`. Partition the `n(n−1)/2` node pairs:

- **zero–zero pairs** (∝ z²/2) — tied in the truth. τ-b excludes these from its concordant/discordant count entirely; they enter only the tie correction.
- **zero–nonzero "boundary" pairs** (∝ z·m) — their true order is determined *solely* by membership in the zero set.
- **nonzero–nonzero pairs** (∝ m²/2) — the actual ranking problem.

So the share of τ-b's **scored** pairs that are boundary pairs is, writing `n_z = |Z|` and `n_m = n − n_z`:

```math
w_{\text{exact}} = \frac{2\,n_z n_m}{n(n-1) - n_z(n_z-1)}
```

and, treating z as continuous and dropping the `−1` terms, this simplifies to a strikingly clean limit:

```math
w = \frac{zm}{zm + m^2/2} = \frac{z}{z + m/2} = \boxed{\frac{2z}{1+z}}
```

— a function of **z alone**. The m's cancel entirely, which is the point worth carrying away: *the boundary share depends on nothing about the graph except its zero fraction.* Not its size, not its density, not its degree distribution.

**Keep the two forms distinct.** `w_exact` is an identity with the pair counts and holds to machine precision; `2z/(1+z)` is its large-n limit and carries an O(1/n) error. Both are checked in `analyse_betweenness.py::boundary_share`, and the exact form is the one asserted — it *raises*, it does not print a warning. `verify_pipeline.py` N10 calls the same function (never a second copy of the formula) and additionally pins the table below to three decimals, so a re-cached target column with a different endpoint convention cannot satisfy the identity and silently invalidate these numbers:

| network | z | w exact | counted | asymptotic 2z/(1+z) | error of the limit |
|---|---|---|---|---|---|
| ca-GrQc | 0.5503 | 71.0008% | 71.0008% ✓ | 70.9898% | −0.0110 pp |
| ca-HepTh | 0.4853 | 65.3519% | 65.3519% ✓ | 65.3468% | −0.0051 pp |
| p2p-Gnutella08 | 0.2781 | 43.5280% | 43.5280% ✓ | 43.5225% | −0.0054 pp |
| email-Eu-core | 0.1511 | 26.2787% | 26.2787% ✓ | 26.2555% | −0.0232 pp |
| facebook_combined | 0.0847 | 15.6164% | 15.6164% ✓ | 15.6129% | −0.0036 pp |

The exact form reproduces the pipeline's independently-computed count on all five networks to machine precision. The asymptotic form is accurate to ~0.02 percentage points and is the version worth quoting in prose — it is largest in error on email-Eu-core, which is exactly what an O(1/n) correction predicts, since email is the smallest graph in the corpus at n = 986.

*(This distinction was found by writing the check: asserting `2z/(1+z)` against the counted value at a 1e-9 tolerance failed on all five networks while agreeing to every printed decimal. A looser tolerance would have hidden a real approximation behind an apparent identity.)*

### 24.5 The zero-skill reference depends on prediction ties

**Reconciled 2026-09-07 after completed C3 and C4.** On 2026-09-05 this section replaced
the arithmetic reference w with a geometric reference, but incorrectly justified it by
calling forest predictions untied. The 2026-09-06 six-graph diagnosis then overclaimed
exact reproduction. Those interim interpretations are superseded by the complete
14-graph results in §26i and the measured forest ties in §26j. The arithmetic form was
not wrong in general; neither form is a universal identity for actual predictions.

Write T = C(n,2), S = T − C(n_z,2), Q = C(n_m,2), and w = n_z n_m / S.
Assume perfect score separation of reference zeros below positives, no reference ties
among positives and no prediction ties among positives or across the boundary:

| Prediction regime | All-node tau-b | Zero-positive separation with zero within-positive ranking skill |
|---|---|---|
| No prediction ties anywhere | `(n_z*n_m + Q*tau_positive)/sqrt(S*T)` | `w*sqrt(S/T)` |
| One tied score on the zero block | `w + (1-w)*tau_positive` | `w` |

The exact finite-n geometric factor is **sqrt(S/T)**, approximately sqrt(1−z²) for large n.
C3's registered geometric reference uses that large-n expression; its thresholds are
unchanged. Both regimes are pinned by the existing C3 N11 synthetic check. C4 N12 also
tests independent hand-computable cases, extra ties and undefined metrics.

A zero-skill reference is not a universal lower bound: a method can reverse the positive
ordering and fall below it. Partial zero-block ties, positive-block ties or boundary
errors require the actual tau-b denominator and pair accounting. The internal C4 cache
check finds **all 800 forest rows** in this general case. Emitting floating-point scores
does not imply continuity or absence of ties.

The earlier hypothetical continuous-score reference table is retained as a conditional
comparison, not a decomposition of the actual forests' scores:

| network | hypothetical geometric reference, approximately w·sqrt(1−z²) | our τ at r=3 | margin above that reference |
|---|---|---|---|
| ca-GrQc | 0.5929 | 0.9216 | +0.329 |
| ca-HepTh | 0.5714 | 0.9162 | +0.345 |
| p2p-Gnutella08 | 0.4181 | 0.9367 | +0.519 |
| email-Eu-core | 0.2598 | 0.9030 | +0.643 |
| facebook_combined | 0.1556 | 0.8514 | +0.696 |

Subtracting this hypothetical comparator changes the cross-graph margin ordering:
facebook has the largest margin and ca-GrQc the smallest. It does **not** establish how
much of any actual forest tau came from zero separation, nor a cross-method ranking
reversal. In particular, “0.59 of the observed 0.92 is the binary question” is not licensed
by a comparator whose tie assumptions the actual forest violates. The earlier 200-draw
continuous-score simulation supported that hypothetical construction, not a measured
tie regime for the forest.

C3's completed post-hoc tied-mixture fit covers **5,278 baseline_* observations**:
median absolute error **0.000039**, maximum **0.715413**, including the retained
baseline_random exceptions. BRAVA-GNN **computes and ships** the positive-only metric.
The previous description of it as unpublished and the six-graph exact-identity claim
are withdrawn. Aggregate fit cannot prove each row's tie regime. Registered P1 remains
falsified; registered P3 remains **12/14 against the geometric reference**.

The implemented reporting proposal now has two explicit measurements:

1. Accuracy of the method's **declared zero decision**, with confusion counts and
   prevalence. If no decision exists, report NA; do not substitute an auxiliary exact
   certificate. The radius-1 certificate is available under its stated graph conventions,
   but adding it changes the evaluated method.
2. Kendall tau-b on **reference-positive nodes only**, retaining positive nodes assigned
   zero scores. Report NA with a reason when this ranking is undefined.

Support, ties and provenance are necessary to interpret both. Matching zero fractions
alone is not sufficient to make all-node tau comparable across graphs. The complete
contract and its implementation are in §26j and
[C4 reporting protocol](reference/C4_two_number_reporting_protocol.md).

### 24.6 Prior art on zero-inflated rank correlation — direct-source correction

**Updated 2026-09-07.** The earlier “not scooped” verdict and categorical claim that the
literature lacks a tau-b counterpart are withdrawn. The direct publisher version of
Perrone, van den Heuvel and Zhan (2023), *Kendall's tau estimator for bivariate
zero-inflated count data*, was obtained and read. The previous “not on arXiv/not obtained”
description is superseded; the article also has preprint arXiv:2208.03155.

Perrone et al. distinguish population association from its sample estimators. Their
proposed estimator substitutes sample frequencies into the zero/nonzero decomposition
and explicitly uses tie-corrected tau-b for its positive-positive component. The article
does not state the project's one-sided p2=0 specialization or the finite-vector pair
share w and denominator decomposition used in §24.5. Those distinctions define scope;
they do not establish priority. The historical C0 calculation through Arends et al.
(arXiv:2503.13148v3, on Spearman correlation) exposed our floor error, but cannot support
an absence claim about a different paper.

The defensible D2 argument is now the released-benchmark support audit and executable
reporting contract. Zero-inflated concordance decompositions, the graph zero-set
certificate, and positive-only Kendall evaluation are antecedents to cite. BRAVA-GNN
already computes and ships filtered aggregate results; the inspected release lacks the
aligned per-node method arrays needed to reconstruct the proposed two-task evaluation.
This is a bounded release finding, not a claim about all benchmark practice.

Primary-source locations, reading levels, code snapshots and hashes are in
[the Phase 6 literature review](reference/prior_work.md), including the
[direct Perrone paper](https://doi.org/10.1016/j.spl.2023.109858). The Phase 6 paper draft
and reproduction guide develop this narrower argument. Venue fit is a recommendation;
no venue has been selected and no submission has been made.

## 25. Finding 8 — locality's blind spot appears exactly where the horizon has not been reached

### How the residual is built

For each node, a rank residual at the reference configuration (r = 3, richest structural tier):

```math
\Delta(v) = \text{pct}_\text{true}(v) - \text{pct}_\text{pred}(v)
```

positive meaning the node is genuinely more important than predicted — an under-predicted "hidden influencer". Δ is computed inside each seed and averaged over the ten, so a node reaches a tail by being *consistently* misplaced.

**Two mechanical effects have to come out first, and the second nearly produced a spurious result.**

*Shrinkage.* Every regression pulls predictions toward the middle, so high-influence nodes get positive Δ and low-influence nodes negative Δ as an artefact of fitting. Raw tails would report that the under-predicted nodes are the influential ones — true, mechanical, not a finding.

*Heteroscedasticity.* Residual variance is far from constant. Thousands of near-tied peripheral nodes are ranked much more loosely than well-connected ones, so the tails fill with the periphery regardless of structure. The symptom was unmistakable once looked for: **both tails profiled identically** — on ca-GrQc, under- and over-predicted groups both came out low-degree, low-coreness, high-porosity. That is one population appearing at both ends, not two blind spots.

Both are removed by standardising Δ within bins of true influence — subtract the median, divide by the median absolute deviation — the same non-parametric construction `variance_residual` uses in §2.3.

### The profiling axes are deliberately global

A blind spot can only be explained with information the model was **denied**: coreness, hop distance to the nearest hub, the fraction of the network inside the 3-ball, and the ratio of mean cascade size to that visible ball. These live in `structure.py` and would abort the sweep if they ever reached the feature matrix. Local features are profiled as context. Comparisons are ranked by **Cliff's δ**, a rank-based effect size, not by p-value: at several thousand nodes almost everything is "significant".

### The result

Comparing each tail against the well-ranked middle answers "what makes a node hard to rank". Comparing the two tails **against each other** cancels everything they share and isolates what decides the *sign* of the error. That second question is the sharp one, and its answer differs strikingly across the corpus:

Measured on all five networks, at the 171-feature table, target `spread_mean`. "Final hop" is the paired r=2 → r=3 gain from §17; the seed sd on every one of those gains is ≤ 0.0008, so the ordering of the column is not noise.

| Network | final hop still buys | max \|δ\| directional | verdict |
|---|---|---|---|
| facebook_combined | +0.0012 | **0.146** | none |
| ca-GrQc | +0.0025 | **0.122** | none |
| ca-HepTh | +0.0047 | **0.185** | weak |
| email-Eu-core | +0.0049 | **0.319** | medium |
| p2p-Gnutella08 | +0.0292 | **0.403** | medium |

**The directional blind spot tracks how much the last hop is still buying.** Spearman ρ between the two numeric columns is **0.900 (p = 0.037, n = 5)**. Where P(r) has flattened the residual is symmetric imprecision — the model is imprecise about an identifiable population but not *biased* about it. Where the curve is still climbing at r=3, the errors acquire a direction.

And the variable driving it is the right one: on Gnutella the top directional separator is **spread / visible ball** at δ = 0.40 — the under-predicted nodes are precisely those whose average cascade escapes everything they can see. The same variable leads on ca-HepTh (+0.19) and facebook (+0.15) and comes third on email (+0.25). That is the locality gap of Angle 5, measured directly, falling out of the failure analysis rather than being assumed.

Note that expanding the feature set 64 → 171 (§6) **shrank** Gnutella's directional δ from 0.51 to 0.40. The new features ate into the blind spot where one existed, which is the behaviour a real blind spot should show and an artefact should not.

### How much of this is an actual test (2026-08-27)

Less than the ρ suggests, and the distinction matters.

This hypothesis was **formed** on ca-GrQc, email-Eu-core and p2p-Gnutella08. Those three points cannot also test it. Only ca-HepTh and facebook_combined are out-of-sample, so the honest question is what the three-network model predicted for them before they were run, and whether it was right:

- **ca-HepTh** — mid-sized final-hop gain (+0.0047), so a mid-sized δ was predicted. Measured 0.185, third of five. **Hit.**
- **facebook_combined** — the *smallest* final-hop gain in the corpus (+0.0012), so the smallest δ was predicted. Measured 0.146, which is second-smallest; ca-GrQc's 0.122 is lower. **Near miss** — right regime, wrong rank.

So the out-of-sample record is one clean hit and one near miss, and the single inversion in the table is exactly that facebook/ca-GrQc pair. Their final-hop gains differ by 0.0013 and their δ by 0.023; nothing rests on which way round they fall.

Two further reasons not to over-read ρ = 0.900:

- **n = 5.** One swap anywhere in the ordering drops ρ to 0.7 and p above 0.1. The coefficient is a description of five points, not an estimate of a population quantity.
- **ca-HepTh and email are tied on the x-axis** at +0.0047 and +0.0049, a difference of one seed sd. Their relative order is arbitrary. That they happen to be ordered correctly on δ as well is luck, and it is inflating ρ.

The correspondence is real and it replicated on new data. It is not yet a measured relationship, and the thing that would make it one is unchanged: the generated corpus (§14), where the structural parameters move one at a time and r\* can be dialled rather than observed.

### What the extra hops rescue

Profiling the nodes whose ranking improves most between r=1 and r=3 gives the mechanism from the other side:

| Network | mean \|Δ\| r=1 → r=3 | what gets rescued |
|---|---|---|
| p2p-Gnutella08 | 0.0679 → 0.0292 (−57%) | 2-ball conductance δ=+0.56, growth ratio r3 δ=+0.54 (both large) |
| ca-HepTh | 0.0330 → 0.0166 (−50%) | boundary porosity δ=+0.50, 2-ball conductance δ=+0.33 |
| ca-GrQc | 0.0259 → 0.0187 (−28%) | boundary porosity δ=+0.50, hops to nearest hub δ=−0.46 |
| email-Eu-core | 0.0141 → 0.0108 (−23%) | little left to rescue; effect sizes collapse with the improvement |
| facebook_combined | 0.0146 → 0.0138 (−5%) | nothing meaningful — see below |

Two things to read off that table. First, **ca-HepTh replicates ca-GrQc's mechanism exactly**: same family, same leading rescued variable (boundary porosity, δ = +0.50 on both to two decimals). Same-family replication of a mechanism, not just of a number.

Second, **facebook rescues almost nothing on `spread_mean` (−5%)**, and that is consistent rather than anomalous: its r\*(ε) is 1 on this target at every tolerance tested, so by r=1 there is nothing left for hops 2 and 3 to fix. The one network where the extra hops are nearly worthless is the one the locality budget already said would not need them.

### Why this matters for the project's claim

The locality budget says *how far* you must look. The atlas says *what you lose* by stopping early, and the two agree: where P(r) has flattened the errors are directionless, and where it has not, the errors point at the unseen mass. That is a considerably stronger statement than either result alone, because neither was constructed to produce it.

**Caveat.** Five networks, and see the out-of-sample accounting above. The generated corpus (§14) is what turns a suggestive correspondence into a measured relationship, by sweeping structural parameters one at a time and asking whether the directional δ tracks r\*.

### A note on betweenness

On betweenness the picture is not the same one, and the difference is systematic. Directional δ, both targets, all five networks:

| Network | `spread_mean` | `betweenness` | leading directional variable (betweenness) |
|---|---|---|---|
| ca-GrQc | 0.122 | **0.334** | ego betweenness −0.33 |
| ca-HepTh | 0.185 | **0.421** | 2-ball density −0.42 |
| email-Eu-core | 0.319 | **0.911** | ego betweenness +0.91 |
| facebook_combined | 0.146 | **0.735** | ego betweenness +0.73 |
| p2p-Gnutella08 | 0.403 | 0.286 | spread / visible ball −0.29 |

**Betweenness carries a much larger directional blind spot than `spread_mean` on four of five networks**, and the exception is Gnutella — the same network that is the exception in §17 for never saturating. Where the spread target's errors are directionless, the betweenness errors on the same nodes are not.

The leading variable is usually **`ego_betweenness`**, which is a local feature the model *had*. That is the uncomfortable part: on the spreading targets the directional blind spot is explained by a global quantity the model was denied (`spread / visible ball`), which is a satisfying story. On betweenness it is explained by something sitting in the feature matrix the whole time. The model is not short of the information; it is failing to use it at the tails.

**The sign is not stable, and no portable rule survives it.** `ego_betweenness` leads on four networks, but which tail is the bridge-like one flips:

| Network | median ego-btw, under-pred | median, over-pred | δ | which tail is bridge-like |
|---|---|---|---|---|
| ca-GrQc | 5.83 | 12.5 | −0.334 | **over**-predicted |
| ca-HepTh | 7 | 2 | +0.385 | under-predicted |
| email-Eu-core | 69.85 | 0 | +0.911 | under-predicted |
| facebook_combined | 33.86 | 0.31 | +0.735 | under-predicted |
| p2p-Gnutella08 | 42.5 | 35.5 | +0.081 | negligible |

On ca-GrQc the locally-bridge-like nodes are the ones the model *over*-rates; on the other three with real signal they are the ones it *under*-rates. So "high local bridging ⇒ systematically under-ranked" is a statement about three networks, not a law, and it must not be written as one. Whether ca-GrQc's reversal is a property of sparse collaboration graphs is not answerable here — ca-HepTh is the same family and goes the other way, which rules out the easiest explanation and leaves no tested one.

What can be said without qualification is the facebook panel, which is the most informative in the corpus: mean |Δ| falls 0.1206 → 0.0502 from r=1 to r=3 (−58%, the largest rescue anywhere), and the over-predicted tail separates at δ ≈ −0.63 to −0.68 on coreness, h_index_3, degree, edge embeddedness and ego betweenness simultaneously. Those are low-degree, shallow-core nodes sitting in a dense local patch that the model reads as a bridge and the global graph routes around. That is exactly the failure mode Finding 10 predicts for an ego-network union, arrived at from the opposite direction.

### A bug that was hiding all of this (fixed 2026-08-27)

The betweenness table above could not be seen until today, and the reason is worth recording because it is a general trap.

`make_fig2.py` drew its bottom row — "what decides the direction of the error" — using the variable set selected by the row above it, which ranks by the *under-predicted vs middle* contrast. The two rows are different contrasts over different node sets. A variable that separates the two tails from each other can be flat against the middle, because it pushes the two tails in opposite directions and they cancel. Selecting the directional row by the other row's ranking therefore **systematically hides precisely the strongest directional effects** — the failure mode is not random, it is targeted at the quantity the panel exists to show.

The panel's headline `max |δ|` was computed over that borrowed subset too. Consequences at the five-network corpus:

| Panel | printed | true | printed verdict | true verdict |
|---|---|---|---|---|
| ca-HepTh `spread_mean` | 0.14 | 0.185 | *no directional blind spot* | signal present |
| p2p-Gnutella08 `betweenness` | 0.12 | 0.286 | *no directional blind spot* | signal present |
| facebook `betweenness` | 0.54 | 0.735 | signal present | signal present |

Two panels **announced a null that their own data contradicted**. The text dump in `results/RESULTS_failures.txt` was correct throughout — it ranks each table on its own terms — so the error lived only in the figure, which is the artefact most likely to be read and least likely to be checked against the file it came from.

Fixed by giving each row its own top-7 from its own table, and by computing the verdict over the whole directional table rather than the drawn bars. The cost is that the two bar rows no longer share a y-axis and cannot be scanned down a column; that alignment is what caused the bug and it was buying a false headline.

---

## 26. Finding 9 — Angle 4: what survives damage depends on what you are predicting

### The experiment

Delete a fraction ρ of edges uniformly, then rank nodes by their **clean-graph** influence given only the damaged graph, three ways:

- **local** — local features on the damaged graph, through a model trained on clean data
- **recompute** — the global score computed directly on the damaged graph
- **degree** — degree on the damaged graph, as a floor

Uniform deletion models *missing observation*, deliberately not adversarial: removing the highest-betweenness edges would wreck a shortest-path score far more than a local one and rig the comparison in our favour.

The model is trained once per network and target on clean features and clean targets, five-fold, and then shown each node's *damaged* features by the fold that never trained on it. That is the realistic deployment: you learn the mapping from good data and then meet a graph you can only observe imperfectly. Fitting the folds once and reusing them across every noise level also means differences between levels are the damage and nothing else.

At ρ = 0 the recompute line is **1.0 by construction** — it *is* the truth. So local starts behind by whatever the model's clean-data error is, and the question is not who starts ahead but **who falls faster**.

### The answer differs by target, and that is the finding

**Spreading influence — local wins, from very little damage onward.**

τ against the clean truth, `spread_mean`, local minus recompute *(original three-network measurement; the five-network table is below)*:

| ρ | ca-GrQc | email-Eu-core | p2p-Gnutella08 |
|---|---|---|---|
| 0.00 | −0.056 | −0.032 | −0.084 |
| 0.05 | **+0.008** | −0.000 | **+0.019** |
| 0.10 | **+0.007** | **+0.002** | **+0.014** |
| 0.20 | **+0.007** | **+0.001** | **+0.005** |
| 0.30 | **+0.006** | −0.001 | **+0.002** |
| 0.50 | −0.011 | −0.007 | **+0.003** |

The crossover happens at ρ = 0.05–0.10 on all three of the networks this was first measured on, and the local line stays level with or above recomputation across most of the range. **This does not hold on all five** - see the replication subsection below, where `facebook_combined` never crosses. The margins are small — a few thousandths — so the honest statement is **parity, reached almost immediately, not a rout**. Recomputing the cascade on a damaged graph loses the very pathways the cascade would have used; the local model at least maps damaged structure onto a learned influence scale.

**Bridging influence — recomputation wins, and the gap widens.**

`betweenness`, local minus recompute *(original three-network measurement)*:

| ρ | ca-GrQc | email-Eu-core | p2p-Gnutella08 |
|---|---|---|---|
| 0.05 | −0.065 | −0.087 | −0.083 |
| 0.20 | −0.101 | −0.111 | −0.211 |
| 0.50 | −0.273 | −0.241 | −0.502 |

Not a marginal loss and not a stable one: the local model degrades *faster*. **The Angle 4 hypothesis is rejected for betweenness.** Shortest paths reroute around a missing edge; a randomly thinned graph is still structurally close, so recomputed betweenness stays informative.

### The skew control cuts against the naive reading

Section 24 showed 8.5–55% of nodes have betweenness exactly zero, and that a single local feature identifies that set perfectly. *(Range corrected 2026-08-28: "15–55%" was the three-network span and predates facebook_combined's 8.5%.)* Restricting to the nonzero subset — the nodes where the ranking actually matters — the picture changes:

local minus recompute on the **nonzero** subset, `betweenness` — **two networks only**;
this table was never extended past the original pair, and the five-network version of the
same comparison (damage-trained) is in the replication subsection below:

| ρ | ca-GrQc | email-Eu-core |
|---|---|---|
| 0.00 | −0.244 | −0.110 |
| 0.10 | −0.140 | −0.074 |
| 0.30 | −0.101 | −0.056 |
| 0.50 | −0.085 | −0.083 |

The gap **narrows** as damage increases, by roughly a factor of three on ca-GrQc, where on the full τ it tripled in the other direction. So a large part of recomputation's apparent advantage is that it keeps the zero/nonzero split intact, not that it ranks the important nodes better. Both statements are true and they point opposite ways; reporting only the first would have been misleading.

### The most uncomfortable line on the figure is the grey one

Plain **degree on the damaged graph** beats the whole 171-feature local model for betweenness at high damage:

| ρ = 0.5 | local | degree |
|---|---|---|
| facebook_combined | **−0.111** | **0.591** |
| p2p-Gnutella08 | 0.239 | **0.735** |
| ca-HepTh | 0.278 | **0.582** |
| ca-GrQc | 0.306 | **0.460** |
| email-Eu-core | 0.593 | **0.780** |

*(ca-HepTh and facebook_combined added 2026-08-27. facebook's local τ is negative:
the model is anti-correlated with true betweenness at that damage level.)*

That is worth sitting with rather than explaining away. The likely cause is **distribution shift**, not locality: the model learned a mapping from clean feature distributions, and heavy edge deletion moves the 171-dimensional input far outside the region it was fitted on. Degree has no such problem — it is a single monotone quantity that shrinks smoothly.

If that reading is right, the binding constraint is the *protocol* rather than the *principle*. That was run as a separate line, and it confirms the reading.

### Training on damaged data recovers most of the collapse

`analyse_robustness.py --train-on clean,damaged` fits the folds on a *different* damage draw at the same ρ — a different realisation, so the model learns the regime rather than that particular set of missing edges — and predicts the held-out draw. τ against the clean truth, `betweenness`:

| ρ = 0.5 | clean-trained | damaged-trained | recovered |
|---|---|---|---|
| facebook_combined | −0.111 | **0.398** | **+0.509** |
| p2p-Gnutella08 | 0.239 | **0.693** | +0.454 |
| ca-HepTh | 0.278 | **0.569** | +0.291 |
| ca-GrQc | 0.306 | **0.509** | +0.203 |
| email-Eu-core | 0.593 | **0.770** | +0.177 |

*(five networks as of 2026-08-27. The recovery is largest exactly where the collapse
was largest, which is what a distribution-shift explanation predicts and a
fragility-of-locality explanation does not.)*

**The collapse was distribution shift, not fragility of locality.** A model that has seen the noise regime it is deployed in loses most of the disadvantage; on Gnutella it recovers nearly half a tau point.

Three qualifications, all of which matter:

- **Recomputation still wins for betweenness.** Damaged-trained minus recompute is −0.05 to −0.09 across the range — a modest, *stable* margin rather than a widening collapse. The Angle 4 conclusion for betweenness does not change; only the size and shape of the loss do.
- **It buys nothing for spreading** *(on four of five networks)*. Damaged-trained minus clean-trained is within ±0.010 for `spread_mean` on ca-GrQc, ca-HepTh, email and Gnutella (the original ±0.01 bound, unchanged by the two new networks). On `facebook_combined` it is worth up to **+0.240**, which is the exception the replication subsection is about. There was no shift to fix, because the clean-trained model was already at parity. The asymmetry is itself informative: betweenness prediction leans on features that move sharply under edge deletion, spreading prediction on degree-like quantities that shrink smoothly.
- **Degree is still not beaten** on email (0.780 vs 0.770), Gnutella (0.735 vs 0.693), ca-HepTh (0.582 vs 0.569) or facebook (0.591 vs 0.398) at ρ = 0.5. Damaged training overtakes it on ca-GrQc alone (0.509 vs 0.460) - one network in five. A single monotone quantity remains startlingly hard to beat under heavy damage.

The honest framing: **the Angle 4 comparison as originally posed conflates two things** — how much information a bounded neighbourhood carries, and whether the model has seen the regime it is tested in. Separating them shows the second was doing most of the damage, and that the first still loses to recomputation for a shortest-path target.

### Replication at five networks (2026-08-27)

Everything above was measured on three networks. `ca-HepTh` and `facebook_combined`
were added and the whole arm re-run: 5 networks x 2 targets x rho in {0, 0.05, 0.1,
0.2, 0.3, 0.5} x 3 damage draws x 4 methods. Error bars below are the sd of the
**paired within-draw** difference across the three draws. Every method ranks the
*same* damaged graph, so the draw-to-draw spread of each method taken separately is
the wrong bar; the paired difference is.

**Spreading: parity replicates on four of five. facebook is the exception.**

`spread_mean`, local minus recompute (mean over 3 draws; all entries marked * differ
from zero by more than 2 sd of the paired difference):

| rho | ca-GrQc | ca-HepTh | email-Eu-core | facebook_combined | p2p-Gnutella08 |
|---|---|---|---|---|---|
| 0.00 | −0.056* | −0.050* | −0.032* | −0.041* | −0.084* |
| 0.05 | **+0.008\*** | **+0.008\*** | −0.000 | −0.013* | **+0.019\*** |
| 0.10 | **+0.007\*** | **+0.008\*** | **+0.002\*** | −0.037* | **+0.014\*** |
| 0.20 | **+0.007\*** | **+0.008\*** | +0.001 | −0.063* | **+0.005\*** |
| 0.30 | **+0.006\*** | **+0.010\*** | −0.001 | −0.073* | +0.002 |
| 0.50 | −0.011* | **+0.001\*** | −0.007* | −0.086* | +0.003 |

The three-network statement — crossover at rho = 0.05-0.10, then parity or a hair
better — survives on ca-GrQc, ca-HepTh, email and Gnutella. On
`facebook_combined` it fails outright: local never reaches recomputation, and
unlike every other network the gap **widens monotonically**, from −0.013 at 5%
damage to −0.086 at 50%.

**But the facebook failure is distribution shift, not a failure of locality.**

Retraining on a *different draw at the same rho* (`local_trained_damaged`) does
essentially nothing on the other four networks — damaged-trained minus recompute
stays inside ±0.016 everywhere, because there was no shift to fix. On facebook it
does this:

| rho | facebook: clean-trained − recompute | facebook: damaged-trained − recompute |
|---|---|---|
| 0.05 | −0.013 | **+0.014** |
| 0.10 | −0.037 | **+0.024** |
| 0.20 | −0.063 | **+0.058** |
| 0.30 | −0.073 | **+0.104** |
| 0.50 | −0.086 | **+0.154** |

That is the single largest margin any method achieves over recomputation anywhere in
this table, on the network where the clean-trained model looked worst. So facebook
does not show that a bounded neighbourhood carries too little information about
spreading under damage. It shows that facebook's clean-to-damaged **transfer** is
uniquely bad — plausibly because it is the one corpus network built from overlapping
dense ego-nets, where uniform edge deletion shreds exactly the triangle- and
conductance-based features the model leans on, moving the inputs far outside the
region they were fitted on. The other four networks are sparse enough that deletion
mostly rescales features it does not restructure.

**Bridging: the loss to recomputation replicates without exception.**

`betweenness`, local minus recompute — every cell significant at 2 sd:

| rho | ca-GrQc | ca-HepTh | email-Eu-core | facebook_combined | p2p-Gnutella08 |
|---|---|---|---|---|---|
| 0.05 | −0.065 | −0.085 | −0.087 | −0.292 | −0.083 |
| 0.20 | −0.101 | −0.150 | −0.111 | −0.360 | −0.211 |
| 0.50 | −0.273 | −0.372 | −0.241 | −0.554 | −0.502 |

Five for five, widening in every case. **The Angle 4 hypothesis stays rejected for
betweenness**, now on a corpus that includes both a same-family replicate and a
structurally unlike dense network.

facebook is the extreme case and worth stating plainly: its clean-trained local model
goes from tau = 0.851 undamaged to tau = **−0.111** at rho = 0.5. Not degraded —
*anti-correlated* with true betweenness. A model that has learned "dense, cliquey
ego-net implies high betweenness" on the clean graph reads a thinned graph's
surviving dense pockets as bridges when the actual bridges are elsewhere.

**The grey line is universal, not a facebook pathology.**

Plain degree on the damaged graph overtakes the full 171-feature clean-trained model
for betweenness on **every** network; only the damage level at which it happens
differs:

| network | first rho where degree ≥ local |
|---|---|
| facebook_combined | 0.05 |
| p2p-Gnutella08 | 0.05 |
| ca-HepTh | 0.30 |
| email-Eu-core | 0.30 |
| ca-GrQc | 0.50 |

The three-network write-up presented this as a high-damage embarrassment. At five
networks it is better read as a **rule with a network-dependent onset**: a single
monotone quantity that shrinks smoothly under deletion beats a high-dimensional
learned mapping as soon as the mapping's inputs leave their training regime.

**On the nodes that matter, the damage-trained model reaches recomputation.**

This is the strongest result in the arm and it did not exist at three networks.
Restricting to the nonzero-betweenness subset (Section 24) *and* training on the
damage regime, damaged-trained minus recompute:

| rho | ca-GrQc | ca-HepTh | email-Eu-core | facebook_combined | p2p-Gnutella08 |
|---|---|---|---|---|---|
| 0.00 | −0.244 | −0.235 | −0.110 | −0.126 | −0.112 |
| 0.10 | −0.125 | −0.140 | −0.085 | −0.022 | −0.047 |
| 0.30 | −0.044 | −0.059 | −0.058 | **+0.026** | −0.011 |
| 0.50 | **+0.002** | −0.015 | −0.056 | **+0.020** | **+0.001** |

On four of five networks the gap closes to parity or better by rho = 0.5. Only
email-Eu-core holds a stable −0.056. So the honest form of the betweenness result is
narrower than "recomputation wins": recomputation wins **on the full ranking, with a
clean-trained model**. Remove both of those qualifiers — score only the nodes whose
ranking is meaningful, and let the model see the noise regime — and local prediction
is level with recomputing the global score on most of the corpus.

Two cautions on that. First, the nonzero-subset numbers are not the headline metric
and were not pre-registered as one; they are a diagnostic that happens to point the
other way from the headline, which is why both are reported. Second, facebook's
*full-tau* damaged-trained numbers carry paired sds of 0.10-0.18 and are **not**
significant at 2 sd — the point estimates (−0.16 to −0.03) should not be quoted as if
they were. The nonzero-subset column above is the stable one there.

### What to claim

*Rewritten 2026-08-27 on the five-network corpus. Two of the three bullets below
changed; the middle one changed the most.*

- For **spreading** targets, a clean-trained local model reaches parity with
  recomputation once even 5% of edges are missing and holds it - **on four of five
  networks**. `facebook_combined` is the exception and never crosses. Retraining on
  the damage regime removes the exception and makes local the best method there by a
  wide margin (+0.154 tau over recompute at rho = 0.5), so the failure is transfer,
  not locality. The defensible claim is therefore: *local prediction of spreading
  influence is at least as good as recomputation on a damaged graph, provided the
  model has seen the damage regime.* Without that proviso it is a four-of-five claim.

- For **betweenness**, recomputation wins on the **full ranking with a clean-trained
  model** - five networks out of five, widening with damage, no exceptions. Drop
  either qualifier and the result changes: on the nonzero subset with a
  damage-trained model, local is at parity or ahead on four of five by rho = 0.5.
  Both statements are measured and they point opposite ways. Neither may be reported
  alone.

- Plain **degree** on the damaged graph beats the 171-feature clean-trained model for
  betweenness on **every** network - at rho = 0.05 on facebook and Gnutella, at 0.30
  on ca-HepTh and email, at 0.50 on ca-GrQc. This is a rule with a network-dependent
  onset, not a high-damage curiosity, and it is the cheapest available evidence that
  the binding constraint is distribution shift rather than information content.

- The comparison is **not** evidence that local features are intrinsically fragile.
  Training on the noise regime recovers up to +0.45 tau on betweenness and turns
  facebook's spreading result from worst to best, which settles that.

- **Open, and not answered by this arm:** whether the facebook transfer failure is
  specifically a dense-overlapping-ego-net effect is a hypothesis fitted to one
  network. It predicts that a synthetic corpus with tunable clustering would show the
  clean-to-damaged gap growing with clustering coefficient. That is a real test and
  it has not been run. (TBC)

---

## 26a. Finding 10 — one rung of the ladder is not a null; it is network-dependent, and one feature carries it

*Added 2026-08-27, on the five-network corpus. This finding did not exist before facebook_combined was run, and it revises the headline of Finding 3.*

*Rewritten 2026-08-31. The first version of this section attributed the effect to the **edge** tier. That attribution was wrong — not because the measurement was wrong, but because the two columns carrying it were mis-tagged `edge` when they belong to `subgraph` (see §6, "Tier correction"). The finding survives the correction; its subject changes. This section states the corrected version, and then states what the correction cost, because a reader who saw the earlier claim is entitled to know how it failed.*

### What the three-network corpus said

Supervisor directive 4 asked for edge-level and subgraph-level features. Finding 3 reported that once the ladder was repaired, subgraph structure helped the dynamical targets by up to +0.035, and that the **edge** tier contributed essentially nothing anywhere. The write-up treated the edge tier as a built-and-measured null: worth having so the claim could be made honestly, not worth anything predictively.

That reading was correct for the edge tier, and it is still correct. What was wrong was the conclusion drawn next.

### The measurement that broke it

On facebook_combined, predicting betweenness at radius 2, ten seeds, from `sweep_facebook_combined.csv` after the 2026-08-31 refit:

| feature set | features | τ |
|---|---|---|
| node only | 35 | 0.6641 ± 0.0048 |
| node + edge | 80 | 0.6959 ± 0.0036 |
| node + edge + subgraph | 144 | **0.8239 ± 0.0054** |

Paired within seed (`analyse_edge_tier.py`, which now takes `--tier`):

| rung | gain | sd of paired difference |
|---|---|---|
| node → node + edge | +0.0318 | ± 0.0064 * |
| node + edge → + subgraph | **+0.1291** | ± 0.0043 * |

The **subgraph** tier is worth +0.129 at fixed radius, roughly 30 sd. For scale, the largest richness effect previously recorded anywhere in this project was +0.035, and the largest single depth step — one whole extra hop of information on ca-GrQc betweenness — is +0.376. A single tier, at fixed radius, is delivering roughly a third of what an entire extra hop delivers.

The edge tier does contribute here (+0.032, and beyond 2 sd), which is itself larger than it is anywhere else in the corpus. But it is a fifth of the effect, not the effect.

### Which part of the tier, isolated

The number is large enough and singular enough that it was isolated rather than reported off the sweep table. Adding each subgraph cost-group to the **node + edge** baseline separately, so the groups cannot mask one another:

| added group | features | τ | gain vs node + edge |
|---|---|---|---|
| `shells_ci_hop_2` | **3** | 0.8193 | **+0.1234 ± 0.0042** * |
| `graphlet_orbits` | 59 | 0.7093 | +0.0134 ± 0.0051 * |
| `hop1_ego_betweenness` | 1 | 0.6983 | +0.0024 ± 0.0035 |
| `hop1_ego` | 1 | 0.6955 | −0.0004 ± 0.0018 |

Three features out of 64 carry 96% of the effect. Splitting those three, against the same baseline:

| added feature(s) | τ | gain vs node + edge |
|---|---|---|
| `local_conductance_2` | 0.8130 | **+0.1171 ± 0.0044** * |
| `ball2_density` | 0.7428 | +0.0469 ± 0.0028 * |
| `ball2_edges` | 0.7001 | +0.0042 ± 0.0027 |
| `ball2_density` + `local_conductance_2` | 0.8130 | +0.1171 ± 0.0044 * |
| all three | 0.8191 | +0.1232 ± 0.0040 * |

**One feature — the conductance of the 2-ball — is worth +0.117 τ.** And `ball2_density`, which is worth +0.047 on its own, is worth nothing once conductance is present: the two-feature gain equals the conductance-only gain to five decimal places. They are two readings of the same quantity, and only one of them is needed.

The cost side is the sharpest part of the result. `shells_ci_hop_2` takes **1.55 s** on this 4,039-node graph and buys +0.123. `graphlet_orbits` takes **231.6 s** — 150× longer — and buys +0.013.

### Why that feature, on that network

`local_conductance_2` is the fraction of the 2-ball's edge volume that leaves the 2-ball. It is a bridge detector by construction: a node whose neighbourhood is a closed community has low conductance, a node whose neighbourhood leaks into the rest of the graph has high conductance.

facebook_combined is a union of ego networks — dense friend groups joined by a few bridges — and betweenness there is almost entirely about which nodes are the bridges. That is invisible to every node-tier feature: a bridging node need not have unusual degree, clustering, H-index or coreness. It is exactly what a boundary measurement sees.

### The feature is *not* orthogonal to the tiers below it — and that is the interesting part

An earlier version of this section certified `local_conductance_2` as new information, reporting a held-out R² of **−0.88** predicting it from the node tier at r ≤ 2, and reading the negative sign as "the node tier predicts it worse than its own mean does."

**That number does not reproduce and should not be cited.** Measured on the current feature table by two independent routes — the project's own probe in `analyse_features.py` (HistGradientBoosting, single 70/30 split, 4,000-row subsample) and a RandomForest under 5-fold cross-validation — the held-out R² is about **+0.99**, from the node tier and from the node + edge tier alike:

| column | from node (f=35) | from node + edge (f=80) |
|---|---|---|
| `ball2_edges` | +0.999 | +0.999 |
| `ball2_density` | +0.992 | +0.991 |
| `local_conductance_2` | +0.992 | +0.992 |

This is not a retraction of the finding; it changes what the finding means. `local_conductance_2` is very nearly a deterministic function of columns the model already had — which is unsurprising once written down, since the shell counts and shell degree sums at r ≤ 2 contain the ingredients of cut and volume. It is nonetheless worth +0.117 τ.

**Reconstructible is not the same as accessible.** A forest fitting *betweenness* under a finite sample does not spontaneously discover that it should form the ratio cut/vol from a dozen shell columns; it has no gradient pointing at that construction and no budget of splits to spend approximating a ratio. Handing it the ratio directly is worth a third of a hop. That is a statement about feature engineering under a fixed estimator, and it is a better result than the orthogonality claim it replaces — but it is a different claim, and the two must not be confused. Anything that depended on "orthogonal information, not a correlated restatement" is now unsupported.

### The replication, which is what makes this a finding and not an anecdote

The same ablation across all five networks, betweenness at r=2, paired within seed:

| network | edge rung | subgraph rung | `shells_ci_hop_2` | `graphlet_orbits` |
|---|---|---|---|---|
| facebook_combined | +0.0318 * | **+0.1291 \*** | **+0.1234 \*** | +0.0134 * |
| ca-HepTh | +0.0105 * | +0.0050 * | +0.0004 | **+0.0043 \*** |
| ca-GrQc | +0.0082 * | +0.0014 | +0.0005 | +0.0006 |
| email-Eu-core | +0.0023 | +0.0045 | +0.0003 | +0.0017 |
| p2p-Gnutella08 | +0.0009 * | +0.0014 * | +0.0010 * | +0.0006 * |

`*` = |gain| > 2 × sd of the paired per-seed difference.

Three distinct regimes, and the *composition* differs, not just the magnitude:

- **facebook_combined** — boundary geometry dominates. Conductance is worth 250× what it is worth on ca-GrQc.
- **the two collaboration graphs** — what little there is comes from **orbits**, on both rungs, and conductance is worth nothing (+0.0004, +0.0005). Note that these two agree with each other again, as they did in Finding 4.
- **email and Gnutella** — both rungs are nulls, as originally reported. p2p's starred gains are +0.001, statistically clean and practically nil, which is what a tiny sd buys you.

### What this changes

**Finding 3's headline needs qualifying, and for the same reason as before.** "Depth beats richness by roughly an order of magnitude" was measured as +0.376 for a hop against +0.035 for richness. On facebook betweenness the comparison is **+0.197** for the r1→r2 hop (0.6269 → 0.8239 at the richest structural tier) against **+0.160** for richness at fixed r=2 (0.6641 → 0.8239) — the same order of magnitude. Both of those numbers are untouched by the retag, because the node tier and the richest tier are the same sets of columns as before; only the rung *between* them moved. Depth still wins on average and still wins outright on the sparse networks; it does not win everywhere, and the ratio is a property of the network rather than a constant.

**Supervisor directive 4 is answered, but not the way the first version said.** The honest three-network answer was "we built the edge tier and it bought nothing." The five-network answer is that the **edge** tier buys between nothing and +0.032, so the original null reading of it stands almost everywhere; and that the **subgraph** tier buys nothing on four networks and +0.129 on the fifth, where almost all of the payment comes from three columns costing 1.55 s.

**A practical rule falls out.** Feature-group value is not a property of the feature group. Reporting "the subgraph tier is worth +0.003" as a corpus average would have hidden a +0.129 effect inside a mean, and a practitioner following that average would have dropped the one feature that mattered most on the one network where anything mattered at all. Per-network ablation is not optional.

**And a second rule, from the correction itself.** A tier label is not documentation; it is an input to every richness comparison the project makes. Because the ladder is nested, a column tagged one rung too low is handed to every model at that rung and above, so a mis-tag does not produce a missing number — it produces a *plausible* number attributed to the wrong cause. This one survived the leakage guard, the pipeline checks and two document audits, and was caught only by reading the tier definitions against the code. The invariant that would have caught it — the three columns computed from one array must share one tier — is now enforced in `verify_pipeline.py`.

### Limits

- One network drives the effect. The mechanism proposed (union of ego networks ⇒ brokerage invisible to node features) is a **post-hoc structural reading**, consistent with what facebook_combined is, but it was not predicted in advance and one graph cannot confirm it. The test is a second modular graph with a comparable community structure, and it has not been run.
- The effect is measured on betweenness. On facebook's spreading targets the subgraph tier is worth at most +0.012 (at r=1; at r=2 it is between −0.000 and +0.002) — the finding is specific to the brokerage target, which is also the target where facebook's degree baseline collapses to 0.30.
- All three 2-ball columns are hop-2 features, so the effect is unavailable to a radius-1 observer. ~~At r=1 the facebook edge tier is *negative* (0.6366 → 0.6268) and the subgraph tier then adds +0.0001 — the columns dilute before they help.~~

  **CORRECTED 2026-09-04 — the second half of that sentence was an artefact of the training objective, not a property of the features.** The betweenness re-sweep under a `log1p` objective (§26d) puts the same two rungs at:

  | facebook r=1 rung | squared-error objective | `log1p` objective |
  |---|---|---|
  | node → node+edge | **−0.0097** \* | **+0.0158** \* |
  | node+edge → +subgraph | +0.0000 | **+0.0074** \* |

  Both starred under both objectives, and the edge rung *changes sign*. So "the columns dilute before they help" is **withdrawn**: under a correctly-conditioned objective the r=1 edge tier significantly helps. The part of the bullet that survives is the first clause — the three driving columns are still hop-2 and still unavailable at radius 1, which is what the limit was actually about.
- ~~The +0.117 is measured under one estimator... the estimator-invariance sweep (M4, plan Part B2) has not been run.~~ **RESOLVED 2026-09-01 — the sweep was run, and the caution above was justified twice over.** See §26b and §26c. In short: the rung *does* survive on a second, capacity-matched non-linear learner (+0.0555 ± 0.0128), so it is not a random-forest artefact. But its **size was inflated roughly threefold** by a mis-specified training objective, and the honest figure for the rung is ≈ **+0.05, not +0.129**. The revised table:

  | how the rung is measured | gain | sd |
  |---|---|---|
  | as published (rf, squared error on raw betweenness) | +0.1291 | 0.0043 \* |
  | rf, trained on `log1p(y)`, τ scored against original y | **+0.0436** | 0.0011 \* |
  | `hgb_matched`, a capacity-matched second non-linear learner | **+0.0555** | 0.0128 \* |

  Two corrections made for entirely unrelated reasons — fixing the objective, and matching a leaf-floor hyperparameter — landing within 0.012 of each other is what makes ≈ +0.05 a conclusion rather than one number replacing another. The rung is **real and starred under all three**; only its magnitude moves.

---

## 26b. Finding 11 — the training objective was mis-specified, and it cost more than any feature ever added *(2026-09-01)*

This is the largest correction the project has made since the tier mis-tag, and unlike that one **it is not a bug**. Nothing was implemented incorrectly. A default was wrong, and the default was invisible because it is the same default everyone uses.

### The mismatch

Every model in this project minimises **squared error**. Every model is scored by **Kendall τ**. Those are different objectives, and on a heavy-tailed target they are barely related:

- **Squared error** is dominated by the largest residuals. On `facebook_combined` betweenness, whose skew is **28.88**, a handful of nodes carry enormous values, and the fit spends its capacity getting those approximately right.
- **Kendall τ** counts concordant and discordant *pairs*. It does not care how large the top node's value is — only that it is ranked above the next one. Almost all of τ's pairs live in the bulk, which squared error has been ignoring.

So the model is being trained to do one thing and graded on another, and the grading has never been what the training optimised.

### The fix, and why it is legitimate rather than a relaxation

Kendall τ is invariant to any strictly monotone transform of the **ground truth**. If `g` is increasing, the ordering of `g(y)` is the ordering of `y`, so every concordant pair stays concordant. That licenses a clean intervention:

> Train the model on `log1p(y)`. Score τ against the **original** `y`.

Only what the model optimises changes. What it is judged against does not move at all. This is the point that has to be made loudly, because the intervention *looks* like the kind of thing that inflates a metric by changing the task, and it is the opposite — the task is fixed and the objective is brought closer to it.

In code, the honesty of the comparison is visible on two adjacent lines:

```python
model.fit(X[train], np.log1p(y[train]))        # what it optimises
tau = kendalltau(y, predictions).statistic      # what it is judged against — original y
```

### What it is worth

`facebook_combined`, betweenness, r=2, `node+edge`, 10 seeds, 5-fold out-of-fold:

| what the model trains on | τ (always scored against the original y) |
|---|---|
| `y` — as every published number in this project was produced | 0.6959 |
| `log1p(y)` | **0.8797** |

**+0.1838 τ, for free.** To put that in the project's own units: it is larger than the entire subgraph tier was worth under the raw objective (+0.1291); larger than any single hop on this cell; and it costs no additional traversal, no additional hop, and no additional column. The single most valuable intervention discovered anywhere in this project is not a feature.

### Why it contaminates the richness ladder specifically

This is the part that changes a result rather than just improving a number.

The handicap is **not constant across the richness ladder**, which means it is confounded with exactly the axis §26a is measuring. Measured across the corpus (`probe_objective_horizon.py`, 800 cells), the correction is **largest where the feature set is poorest** and shrinks as features are added — on facebook betweenness: **+0.2906** at r=0, **+0.1870** at r=1, **+0.0983** at r=2, **+0.0793** at r=3.

The reading: **richer features partially substitute for a correct objective.** A model handed a badly-posed objective and a thin feature set is doubly handicapped; extra columns give it other routes to recover ranking information. So a rung measured under the bad objective flatters the richer arm — not because the richer arm gained more, but because the poorer arm was penalised harder.

> **Correction, made the same day this section was written.** The first draft asserted the opposite — that the handicap *grows* with feature count, because more features let the model chase the tail harder. That reasoning was generalised from a single cell and the corpus probe falsifies it for `rf`. The **conclusion** below is unaffected, because it was always measured directly rather than derived from the mechanism. The direction is also **learner-specific**: `ridge` on facebook betweenness genuinely does decay with radius (0.5445 → 0.1866 → 0.0956 → 0.1107), which is what made the wrong reading plausible in the first place. The claim that survives both learners is the weaker and sufficient one: **the handicap varies along the richness ladder**, so it confounds richness comparisons.

Correcting the objective and re-measuring the rung:

| objective | node+edge | +subgraph | rung gain | sd |
|---|---|---|---|---|
| raw `y` | 0.6959 | 0.8250 | +0.1291 | 0.0043 \* |
| `log1p(y)` | 0.8797 | 0.9233 | **+0.0436** | 0.0011 \* |

**66% of the published effect was the forest compensating for a badly-posed objective**, not gaining access to a ratio it could not otherwise form. The rung survives — it is starred under both, and with *tighter* error bars under the corrected objective — but at roughly a third of its published size.

Note also the second row's left-hand column. Fixing the objective at the *lower* rung (0.6959 → 0.8797) beats the published number at the *higher* rung (0.8250). The project spent 64 subgraph columns and a hop of extra traversal to buy less than a `log1p` would have bought for nothing.

### How it was found, and the two hypotheses that were killed first

This did not come from suspecting the objective. It came from asking why `ridge` and `hgb` both collapsed on the one cell where `rf` thrives — an ~0.50 τ gap at the `node+edge` rung, before the subgraph tier even enters. Two mechanisms were proposed and **both were falsified and discarded**:

1. **Feature skew.** Hypothesis: the collapse is caused by the feature table mixing raw counts with bounded ratios. Test: `log1p` the *features*. Result: it rescued nobody and made ridge substantially **worse** (0.0932 → 0.0208). The control that makes this conclusive is that a random forest is invariant to monotone transforms of *individual features* — splits are thresholds — so rf should not move, and it did not (+0.0014).
2. **Discretisation.** Hypothesis: `hgb`'s histogram binning is destroying the signal. Test: `max_bins=32`. Result: it hurt (0.2076 → 0.1413), but it was not the cause.

The objective was the third hypothesis, and unlike the first two it predicted the *pattern* as well as the fact: ridge should be hit hardest, trees partially protected, and the damage should grow with feature count. All three held.

### Who it hits, and how hard

| learner | exposure |
|---|---|
| `ridge` | **Worst — it cannot escape the loss, it *is* the loss.** Its collapse on facebook betweenness is this artefact, not inductive bias. This matters for §26c, because a pre-registered prediction was scored on ridge's behaviour. |
| `hgb` | Badly, and compounded by an unrelated leaf-floor confound (§26c). |
| `rf` | **Partially protected, not fully.** Split *selection* is order-based, but the split criterion and the leaf values are means, which are not. It still gains +0.18. |

The general form of the lesson: order-based *structure* does not make a learner immune to a scale-based *objective*.

### What this does and does not invalidate

**It does not invalidate any comparison made at a fixed objective.** Every rung gain, hop gain and horizon in Part VII was computed with both arms under the same handicap, so the comparisons are internally consistent and the *signs* are unaffected.

**What moves is magnitude** — for anything involving betweenness — **and the ranking of feature groups wherever the handicap grows along the axis being compared.** That is precisely the richness ladder, and precisely §26a.

### Does the horizon move? — measured, and it moves *down*

`probe_objective_horizon.py` recomputes r\*(ε) under both objectives on all five networks, `betweenness` and `spread_mean`, four radii × ten seeds, at the richest structural tier — using the project's own `r_star_per_seed` rather than a reimplementation, so the numbers are directly comparable to the published horizons. The raw arm reproduces the published sweep to **1e-16**, well inside the documented `n_jobs=-1` tolerance, so the only thing that differs between arms is the transform applied to the training target.

**3 of 50 (network × target × ε) horizon cells moved. All three are betweenness; all three are facebook_combined. 0 of 25 spreading cells moved.**

| network | target | ε | raw r\* | log1p r\* |
|---|---|---|---|---|
| facebook_combined | betweenness | 0.20 | 2 | **1** |
| facebook_combined | betweenness | 0.02 | 3 | **2** |
| facebook_combined | betweenness | 0.01 | 3 | **2** |

**Every movement shortens the horizon, and that is the substantive result.** Part of the apparent need for a third hop on facebook betweenness was the model **buying with features what a correct objective would have supplied for free**. Under a properly-conditioned objective r\*=2 suffices where r\*=3 was published.

This cuts *for* the thesis rather than against it. The project's claim is that the horizon is a measured property of the (network, target) pair; the corrected measurement says locality is **more** sufficient on facebook betweenness than the published figure admits. It is still a correction to a published number, and it is reported as one.

**The control did its job.** Mean correction gain is **+0.0385 on betweenness** (mean skew 11.29) against **+0.0005 on spread_mean** (mean skew 4.12) — a 77× separation tracking skew, with spread_mean's largest single movement anywhere being +0.0047. Had both targets moved, this would have been a fact about the transform perturbing r\* rather than about the objective mismatch. They did not.

**One wrinkle, reported rather than smoothed.** ca-GrQc betweenness at ε=0.01 keeps its modal r\* but loses seed stability under the corrected objective — modal support falls from 10/10 to 5/10. Every other cell in the probe holds at 9/10 or 10/10 under both objectives. That is one cell out of fifty and it is not a claim; it is a thing a careful reader would find and should not have to find alone.

**What remains open.** This probe covers the richest structural tier and two targets. `spread_cv` and `spread_resid` were not probed, and the full corpus has not been re-swept — so the decision recorded in §14 of `HANDOFF.md` (whether to re-base the published betweenness numbers) is informed by this, not settled by it.

### Where this belongs in the argument

For **D2** (the evaluation-pitfalls direction) this is not a footnote — it is a second pitfall of the same species as the zero-inflation floor in §24. Both are cases where a number that looks like model quality is substantially an artefact of the evaluation setup, and both are checkable by anyone in one line without re-running a single model. The zero-set floor says *part of your τ was free*; the objective mismatch says *part of your feature gain was never about features*.

---

## 26c. B2 — estimator invariance, and what the sweep actually established *(2026-09-01)*

### Why it was run

Everything in Part VII is measured with one instrument: `RandomForestRegressor(n_estimators=120, min_samples_leaf=2)` over 171 features. The project's central claim is that r\*(ε) is a **property of the (network, target) pair**, not of the model. A measurement must be instrument-independent within a stated tolerance, and nothing established that.

The 2026-08-31 audit turned that from a completeness gap into a live risk. §26a's carrying feature turned out to be ~99% *reconstructible* from columns already present and still worth +0.117 τ — so what it buys is **accessibility, not information**. An accessibility gain is exactly the kind of effect a different inductive bias erases, which makes estimator-dependence a threat to a headline finding rather than a box to tick.

`docs/prereg/prereg_B2_estimator.md` was written and dated **before** the sweeps, with six predictions and their thresholds fixed in advance.

### What was run

Two full corpus sweeps — `ridge` and `hgb` — plus one **declared post-hoc** arm, `hgb_matched` (`docs/archive/phase6_record.md#rec-posthoc_B2_hgb_capacity`, also written before it ran). All five networks, four targets, four radii, four richness rungs, ten seeds. Output under `estimators/`, **640 rows and 640 out-of-fold vectors per network per arm, with 0 duplicates and 0 NaNs across all fifteen files.**

### The verdicts

| | verdict | note |
|---|---|---|
| **P1** — the subgraph rung largely disappears under ridge | CONFIRMED | but for the wrong reason — see caveat 2 |
| **P2** — the rung does not go to zero, may go negative | CONFIRMED | −0.0016 ± 0.0066 |
| **P3** — `hgb` sides with `rf`, not ridge | **FALSIFIED** | and the test was confounded — see caveat 1 |
| **P4** — r\*(ε) agrees across estimators on the spreading targets | CONFIRMED | lands *exactly* on the threshold bar |
| **P5** — betweenness is where invariance is most at risk | CONFIRMED | |
| **P6** — the *shape* of P(r) is more invariant than its *level* | CONFIRMED | median ρ masks a sign flip on betweenness under ridge |

### Three caveats, each of which weakens a verdict

**1. P3 was falsified on a confound — and it is the same class of error the pre-registration congratulated itself for avoiding.**

The pre-registration was explicit that ridge must be scaled, because *"an unscaled ridge would be crippled by feature scaling rather than by inductive bias, and would produce a false 'invariance fails' verdict."* That reasoning was correct and it was applied to ridge. It was not applied to `hgb`.

The sweep compared `rf` at `min_samples_leaf=2` — pinned deliberately by this project — against `hgb` at **20**, which is scikit-learn's default and was chosen by nobody. Isolating one hyperparameter at a time on the facebook betweenness r=2 cell:

| configuration | τ |
|---|---|
| `hgb` as swept (`min_samples_leaf=20`) | 0.2076 |
| **only** `min_samples_leaf=2` | **0.6286** |
| only `max_iter=1000` | 0.1303 (worse) |
| only `max_leaf_nodes=255` | 0.2024 (flat) |
| only `max_bins=32` | 0.1413 (worse) |
| `rf` as swept | 0.8231 |

One parameter, changed alone, accounts for **68% of the entire gap**. The two obvious "capacity" knobs account for none of it. That is a comparison of leaf floors, not of inductive biases.

**P3 stays falsified.** A post-hoc rerun does not un-falsify a pre-registered prediction, and saying so plainly is the only thing that keeps pre-registration meaningful. What the rerun establishes is a different, separately-declared claim.

The `hgb_matched` arm changed `min_samples_leaf` and **nothing else** — deliberately, since changing three parameters at once is what created the problem. Its three declared expectations, and how they resolved:

| declared before the run | outcome |
|---|---|
| **E1** — τ of 0.60–0.75 at `node+edge+subgraph` | **0.6300 — met.** The single-seed isolation (0.6286) generalised across ten seeds almost exactly. |
| **E2** — rung gain, with *both* extremes pre-interpreted | **+0.0555 ± 0.0128**, starred. Neither "near rf's +0.1291" nor "near zero" — 43% of rf's. |
| **E3** — nothing outside betweenness moves | **Met.** Spreading targets moved ≤ 0.0034 (max 0.0096 on any single network); betweenness was the only target that moved (+0.0741). |

E2 landing between its two pre-read extremes is the honest outcome and both readings are reported rather than one being picked. But there is a genuinely informative convergence here, and it was **not** anticipated by the declaration, so it is flagged as a post-hoc observation: `hgb_matched`'s +0.0555 and the objective-corrected rf's +0.0436 (§26b) agree to within 0.012, from two corrections with nothing in common. That is triangulation, and it is why §26a's revised figure is ≈ +0.05 rather than either number alone.

**2. P1 is confirmed in outcome and wrong in mechanism.**

The pre-registration reasoned that ridge would lose the rung *because a linear model computes ratios for free in the space where they matter* — so the accessibility gain would have nothing to offer it. Ridge does lose the rung. But it loses it while scoring **0.0971**, which is to say while not functioning at all, and §26b explains why. A prediction can be right about what happens and wrong about why, and this one is. The stated mechanism for P1 is **not established** and should not be repeated.

**3. P4 and P5 both land exactly on their threshold bars.** Neither has a comfortable margin; either would flip on a single cell. They should be reported as "consistent with", not as established.

### What survives cleanly

r\*(ε) agreement between `hgb` and `rf` is **17 of 20 cells**, and the horizon claim on the **spreading targets** is estimator-stable within the pre-registered tolerance. That is the licence the sweep was run to obtain, and for the spreading targets it was obtained.

For **betweenness** it was not — and §26b now supplies most of the explanation, since the estimator most damaged by the objective mismatch is precisely the one whose disagreement drove P5.

### The methodological lesson

The pre-registration protected the project exactly where it looked: it forced the ridge scaler question to be asked in advance, and that saved a false verdict. It did not protect where nobody was looking, and the same error walked in through a different hyperparameter.

> **Equalise capacity hyperparameters before claiming a comparison measures inductive bias.** A default that neither party chose is not a property of the learner. The general form: when comparing two implementations, enumerate every parameter where their defaults *differ*, and either match them or state why the difference is part of the thing being measured.

### A verification claim that was re-established rather than assumed

Separately, the 2026-08-31 audit's stability claims — "every locality horizon is unchanged" and "eight richness-gain cells flipped significance" — were computed **before** the 800-cell column-order repair, i.e. on data that was subsequently fixed. They were re-run against the repaired sweeps:

- **r\*(ε): 0 of 100 (network × target × ε) horizon cells moved.**
- **Significance stars: 2 borderline flips**, both below 0.004 in magnitude.
- **Quoted richest-tier τ at r=2 and r=3: maximum delta +0.0011**, nothing above the 0.002 reporting threshold.

The claim was true. It is now *checked*, which it previously was not. A project that publishes a leakage critique does not get to leave a verification claim resting on data it later repaired.

---

### Re-read on the refit registries (2026-09-12)

> **Added 2026-09-12 by Claude Opus 5 (Task 6 findings P1-01, P2-01; run C6).** The
> `ridge`, `hgb` and `hgb_matched` arms had their r=1 subgraph-inclusive cells refit on
> 2026-09-11 alongside the primary sweep (same orbit-5 retag, same seeds), and
> `analyse_estimators.py` was re-run. **The licence above is unchanged: r\*(ε) agrees
> with `rf` in 17 of 20 cells under `hgb` and 17 of 20 under `hgb_matched`** (11 of 20
> under ridge, as before). One row is gone from `estimator_horizons.csv`: `rf_log1p` was
> listed there as if it were a fourth learner, with 15 cells per network that do not
> exist — it is an objective arm of the same forest (§26d), and it is now excluded from
> the estimator comparison rather than scored against itself. Files:
> `results/estimator_horizons.csv`, `results/estimator_shape.csv`, log
> `results/estimators_analyse_20260912.log`; the 2026-09-04 versions are under
> `results/pre_orbit5_refit_20260911/`.

---

## 26d. The betweenness re-sweep — what a corrected objective does to the whole ladder *(2026-09-04)*

§26b established that the training objective was mis-specified and measured the cost on
one cell. §26c triangulated the consequence for Finding 10. This section reports the
**corpus re-sweep** that was then authorised: 800 cells, betweenness only, the pinned
forest trained on `log1p(y)` and scored against the untransformed `y`, written to
`estimators/sweep_<tag>__rf_log1p.csv`. Declaration and scored addendum:
`docs/reference/decl_objective_resweep.md`, written before the run.

### Why only betweenness

Not a scoping convenience — the other three targets are ineligible, and the reason is
arithmetic:

| target | obstacle | measured |
|---|---|---|
| `spread_resid` | **negative on all five networks** — `log1p` undefined or wrong | min −0.9364 (facebook) |
| `spread_cv` | **left**-skewed on p2p — `log1p` worsens the conditioning | skew −0.96 |
| `spread_mean` | low skew; the probe's control measured no effect | mean gain +0.0005 |

Applying a variance-stabilising transform to a target that is not right-skewed is an
intervention, not a correction. This also cut the run from the ~6 h estimated in
`HANDOFF.md` to ~1.5 h, since only a quarter of the grid was eligible.

### The headline reproduces from a second code path

| facebook betweenness r=2, subgraph rung | gain |
|---|---|
| published (squared-error objective) | +0.1291 |
| corrected (`log1p`), single-cell probe §26b | +0.0436 |
| corrected (`log1p`), **full re-sweep** | **+0.0436** |

The re-sweep and the probe agree to four decimals despite running through different
code (a registry estimator inside `stage2_sweep.py` versus a bespoke probe loop). With
`hgb_matched`'s +0.0555 from an unrelated correction, **three routes now put the honest
rung near +0.05, not +0.13.**

### The declared prediction was falsified, and the failure is the informative part

The declaration predicted that *every* facebook rung would shrink, reasoning that the
objective handicap is largest where features are poorest. Six of eight shrank. Two grew:

| facebook r=1 rung | squared error | `log1p` |
|---|---|---|
| node → node+edge | **−0.0097** \* | **+0.0158** \* |
| node+edge → +subgraph | +0.0000 | **+0.0074** \* |

The first is substantive. Under the published objective the r=1 edge tier
*significantly hurt*; under a correct one it significantly helps. **A published negative
rung was an artefact of the loss function**, and §26a's "the columns dilute before they
help" is withdrawn accordingly.

This is the correct general statement, and it is not the one the declaration made:
correcting a mis-specified objective does not uniformly *shrink* gains. It removes a
distortion whose sign varies by rung. Where the distortion had made a tier look harmful,
correcting it makes the tier look helpful — the gain goes **up**.

### The scope limit that must travel with the headline

| | rungs moving > 0.02 |
|---|---|
| facebook_combined | 4 of 8 |
| **the other four networks combined** | **0 of 32** |

**The objective correction is essentially a facebook effect.** It tracks skew, and
facebook's betweenness skew is 28.88 against 4.77–9.73 elsewhere — but the *magnitude*
behind "+0.18 τ, larger than any feature tier" rests on **n = 1**. This project has
already been burned by a facebook-only mechanism (Finding 9's ego-network reading) and
by an n=5 correlation (Finding 8), and the same caution applies here with the same
force. State it wherever the headline is quoted.

### Top-k: a suspected harm that is not there

The declaration flagged, and deliberately declined to predict, a specific risk: squared
error over-weights exactly the huge-betweenness nodes that `precision_at_1pct` rewards,
so the "correction" might improve bulk τ while degrading the applied top-k question.
Measured, paired within seed at the richest tier, against the project's |mean| > 2·sd bar:

| | count |
|---|---|
| significant τ changes | 18 / 20 |
| significant `precision_at_1pct` changes | **1 / 20** (positive) |
| cells with τ significantly **up** and p@1 significantly **down** | **0 / 20** |

Five cells show the pattern in the raw means and none survives its error bars: p@1's
seed-to-seed sd runs 0.01–0.07, an order of magnitude above the shifts.

**Stated with its power caveat**, because the null is only as good as its resolution:
`precision_at_1pct` is coarse by construction — 1% of ca-GrQc's ~4,158 nodes is ~41
nodes, so a single node is ~0.024, larger than every apparent decline observed. This
rules out an effect of the size the means suggested. It does not rule out a small one.

### ~~What this does not do~~ → ADOPTED 2026-09-04

The paragraph that stood here said the corpus was *not* re-based and that adoption was
an open decision. **It was taken on 2026-09-04: `rf_log1p` is the reported objective
for betweenness.** The original text is superseded rather than deleted, per the
project's convention of showing corrections:

> ~~**The published corpus was not re-based.** `sweep_*.csv` is untouched and every
> betweenness τ quoted from it remains a squared-error-objective number carrying that
> qualifier. The re-sweep produced the *evidence* for adopting `rf_log1p` as the
> reported default; the adoption itself is a separate open decision.~~

**What is true now.** `sweep_*.csv` is *still* untouched on disk — the raw record of
what the project used to believe stays inspectable — but `analyse.load()` substitutes
the log1p betweenness rows at read time, so every betweenness number in this document
and in the figures is a corrected-objective number and carries no qualifier.

Three properties of the substitution, each asserted on every run by `verify_pipeline.py`
section N9 rather than assumed:

1. **It is confined to betweenness.** The three spreading targets pass through
   bit-identically (`worst |dτ| = 0.000e+00` across 5 networks × 3 targets). They were
   never eligible: `spread_resid` is negative everywhere, `spread_cv` is left-skewed on
   p2p, and `spread_mean` showed a control gain of +0.0005.
2. **It is not a no-op.** All five networks' betweenness means move, so a missing or
   truncated log1p file cannot silently revert the correction — `load()` raises rather
   than falling back.
3. **It does not leak into the estimator comparison.** `analyse_estimators.py` is pinned
   to the raw arm, because `ridge` and `hgb` were fitted under squared error; taking the
   corrected corpus there would report Finding 11's objective effect under an
   estimator's name.

**The horizon is largely unaffected**, which is the point worth carrying: 3 of 25
betweenness r\*(ε) cells moved, all on `facebook_combined`, all downward. The adoption
sharpens the *richness attribution* (Finding 10's rung, the r=1 edge sign flip); it does
not rewrite the locality thesis.

**Still on the superseded objective, and not re-based:** B2's estimator-invariance sweep
and B1's betweenness arm (Finding 12) were both fitted with `make_rf`. Re-basing either
requires re-running it.

---

## 26e. Finding 12 — the sample-efficiency effect changes SIGN by target *(2026-09-04)*

Supervisor directive 5, requested July 2026 and outstanding for two months, is
discharged. It asked a simple question — the lab believes ~20% of labelled nodes
may suffice — and the answer turned out to depend on something nobody had asked
about.

### The design, and the one choice that makes it interpretable

5,600 cells: 5 networks × 4 targets × 4 radii × 7 training fractions
{5, 10, 20, 40, 60, 80, 100}% × 10 seeds, at the FULL structural tier.

**Only the training portion of each fold is subsampled. The test fold always stays
whole.** This is the choice the whole experiment rests on. Had the test fold shrunk
too, τ at 5% and τ at 100% would be computed over different node sets, and the curve
would confound "less training data" with "noisier measurement" — two effects with the
same sign, permanently entangled. Holding the test fold fixed makes every fraction an
estimate of the *same* quantity, so the fractions pair within seed and their
differences mean something.

### Validity before interpretation

`probe_sample_efficiency.py` re-implements the out-of-fold loop rather than calling
`out_of_fold_predictions`, because that function has no way to subsample a training
fold and adding one would edit the code path that produced 3,200 published cells. A
duplicated loop that silently differs from the pipeline would push the difference
straight into the measured effect.

So the duplication was checked, not trusted. All **800** fraction=1.0 cells were
compared against the published `sweep_<tag>.csv` at FULL:

    worst |dtau| = 0.000e+00      (declared tolerance 5e-08)

Bit-identical on all five networks. The pre-registration said the run was **void**
otherwise, and this gate runs before any prediction is scored.

### Result 1 — the ~20% claim is target-dependent

τ at 20% labels against τ at 100%, paired within seed, radius ≥ 1:

| target | cells within 0.02 | mean cost |
|---|---|---|
| `spread_mean` | **15/15** | −0.0097 |
| `spread_cv` | 11/15 | −0.0157 |
| `spread_resid` | **3/15** | −0.0285 |

The lab's rule is **right for the easy target and wrong for the hard one**. It is not
a rule about label counts at all; it is a rule about how much signal the target has to
spare. `spread_mean` is predicted at τ ≈ 0.90–0.96 and can afford to lose four fifths
of its labels; `spread_resid` on email-Eu-core is predicted at τ ≈ 0.07 and cannot.

### Result 2 — the headline: r\*(ε) moves in opposite directions by target

The sharper, on-thesis question was whether the measured locality horizon shifts when
labels are scarce. The plan predicted it would move **down**. Scored under the
pre-registered rule — a shift counts only if the modal r\* differs *and* its per-seed
support is ≥ 6/10 under both arms — with email-Eu-core excluded as underdetermined:

| target | DOWN | UP | unchanged |
|---|---|---|---|
| `betweenness` | **9** | **0** | 30 |
| `spread_mean` | 1 | 0 | 38 |
| `spread_cv` | 0 | **9** | 31 |
| `spread_resid` | 0 | **6** | 32 |

**Zero counterexamples in either direction.** Two mechanisms, each owning a set of
targets:

- **On `betweenness`, the plan's mechanism holds.** Its deep-radius advantage is
  carried by a few high-variance columns — Finding 10's `local_conductance_2` rung —
  whose estimates degrade fastest as rows are removed. The deep advantage goes first,
  so r\* falls.
- **On the hard targets, the opposite mechanism holds.** Scarcity lowers τ everywhere,
  but it lowers the *shallow* radii proportionally more: they have fewer, cruder
  features and less redundancy to average over. The relative ranking tips deeper and
  r\* rises.

Overall, 20 cells moved up against 15 down, so **the plan's standing prediction is
falsified as stated.** That is reported rather than reframed because the
pre-registration declared the competing mechanism, with its opposite sign, before the
run — precisely so this outcome would be scoreable. The general statement that
survives is not about scarcity at all:

> **The direction of the sample-efficiency effect is a property of the target, not of
> the scarcity.**

### The limit on the 5% arm, and why the falsification survives it

The pre-registration warned that 5% of a 4/5 training split is an underdetermined fit.
Measured, at r=3:

| network | train rows | features | rows/feature |
|---|---|---|---|
| ca-HepTh | 346 | 168 | 2.06 |
| p2p-Gnutella08 | 252 | 168 | 1.50 |
| ca-GrQc | 166 | 168 | **0.99** |
| facebook_combined | 162 | 168 | **0.96** |
| email-Eu-core | **39** | 168 | **0.23** |

Three of five networks have no more rows than columns; email-Eu-core has four times as
many columns as rows. Such a fit prefers a shallow radius for reasons unrelated to any
information horizon — which would *manufacture* exactly the DOWN moves the plan
predicted. The robustness pass therefore drops email, the network most able to
fabricate the original hypothesis. Removing it **strengthens** the UP verdict
(10 down / 15 up becomes the tally on the remaining four), and both fractions agree
independently. The falsification does not rest on the weakest data.

Label starvation is *not* the driver either: nonzero betweenness labels survive uniform
subsampling roughly in proportion (32.9 of 39 rows on email-Eu-core, 74.5 of 166 on
ca-GrQc). The non-stratified-sampling confound was real enough to log per cell, and it
did not bite.

### What this does not license

The 5% arm is not a locality result on its own and must carry the underdetermination
caveat wherever it appears. The 10% and 20% arms carry the weight of Result 2.

---

## 26f. Finding 13 — the first external comparison point: a zero-training closed form at matched radius *(2026-09-05, C5)*

Every "the model needs radius r" statement in this document has, until now, been a statement about *our* model with nothing beside it. M2 of the technical review named that directly: zero published methods have been run, in a field with at least six comparable systems since 2019.

`betweenness_k` closes part of that gap, and it is a better answer than its cost suggests.

### What it is, and why it belongs to *this* project

Ordinary betweenness restricted to source–target pairs at graph distance ≤ k, defined in Appendix A.4 of arXiv 2601.16236 (Exarchakos, van der Hofstad, Nagy, Pandey, Jan 2026), which demonstrates `betweenness6` / `betweenness10` against full betweenness on a 3,774,768-vertex citation network.

**It is a radius-k local rule by construction**, which is what makes it drop into this project's protocol at *matched* r with no training, no features, no seeds and no hyperparameters. The proof matters, because the loose version of it is easy to get wrong:

> Take a pair (i, j) contributing a nonzero term, so `d(i,j) ≤ k` and v lies on some shortest i–j path; hence `d(v,i) + d(v,j) = d(i,j)`. Let u be a node on **any** shortest i–j path — including the paths avoiding v, which matter because `σ_ij` counts them. Then `d(v,u) ≤ d(v,i) + d(i,u)` and `d(v,u) ≤ d(v,j) + d(j,u)`, and those two bounds sum to `d(i,j) + d(i,j) ≤ 2k`. A minimum is at most the mean of the two, so **`d(v,u) ≤ k`**. Every geodesic entering `b_k(v)` — numerator *and* denominator — lies inside the k-ball around v. ∎

The naive argument ("`d(i,j) ≤ k` and v on the path implies `d(i,v) ≤ k`") establishes only which *pairs* matter, not that `σ_ij` is locally computable — and `σ_ij` is exactly the part that could have reached outside. It does not, but that needed showing.

**`b_1 ≡ 0` identically**, and that is the definition rather than a bug: a geodesic between adjacent nodes is the edge itself and has no interior vertex. The k=1 row is kept in every table below to make that visible rather than quietly starting at k=2.

### The result: matched radius, richest tier, betweenness

| network | r | model τ | seed sd | `b_r` τ | model − `b_r` | |
|---|---|---|---|---|---|---|
| ca-GrQc | 1 | 0.9200 | 0.0011 | 0.0000 | +0.9200 | model |
| | 2 | 0.9287 | 0.0014 | 0.9033 | +0.0254 | model |
| | 3 | 0.9281 | 0.0015 | 0.9122 | +0.0159 | model |
| ca-HepTh | 2 | 0.9192 | 0.0005 | 0.8909 | +0.0282 | model |
| | 3 | 0.9199 | 0.0003 | 0.8825 | +0.0374 | model |
| email-Eu-core | 2 | 0.9131 | 0.0017 | 0.8917 | +0.0214 | model |
| | 3 | 0.9134 | 0.0017 | **0.9736** | **−0.0603** | **`b_k`** |
| facebook_combined | 2 | 0.9233 | 0.0009 | 0.8312 | +0.0921 | model |
| | 3 | 0.9303 | 0.0008 | 0.9285 | **+0.0018** | model, but see below |
| p2p-Gnutella08 | 2 | 0.9357 | 0.0003 | 0.9196 | +0.0161 | model |
| | 3 | 0.9386 | 0.0003 | 0.9056 | +0.0331 | model |

Verdicts use the sweep's own 2 × seed-sd rule. Seed sd is the right yardstick here and unusually so: A7 has just established that target noise exceeds seed noise on 55 of 60 cells, but `betweenness` is the one target that is **exact** (Brandes, no Monte Carlo) and was excluded from A7 for that reason. There is no target-noise channel to add.

**Three things follow, and only the first is comfortable.**

**1. The model wins at matched radius on 14 of 15 cells — but the margins are small.** At r=2 and r=3 the 171-feature random forest beats a closed form seeing the same ball by **+0.016 to +0.092 τ**. That is a real gain and it is starred, but it is roughly the size of Finding 10's single-feature rung, not the size of a hop.

**2. `facebook_combined` at r=3 is a statistical win and a practical tie.** +0.0018 τ clears 2 seed sd (0.0015) because the seed sd is tiny, not because the gap is meaningful. **This is reported as a tie in prose**, and the r=3 facebook cell must not be cited as evidence that learning beats truncation.

**3. `email-Eu-core` at r=3 goes to the closed form, by −0.060 τ.** This is the **third independent finding** in which email is the corpus outlier (the others: Finding 6, and the subgraph tier peaking at r=3). It is also exactly what A2's coverage work predicts: SNAP's 90th-percentile effective diameter for email is 2.9, so `b_3` on email is capturing almost every pair in the graph and is converging on exact betweenness (`b_4` = 0.9967, `b_6` = 1.0000). The "locality horizon" at r=3 on email is nominal, and here it costs the model a head-to-head.

### On D2's own metric, which this project demands of everyone else

§24.5 argues that all-node τ on a zero-inflated target conflates a solved radius-1 subproblem with an open one, and C4 proposes that every learned-betweenness paper report τ on the nonzero–nonzero pairs. Judging our own baseline comparison on the all-node number while demanding the subset number of others would be indefensible, so both are computed. The zero set is taken from the **truth**, not from either method's prediction.

| network | r | model τ (nz) | `b_r` τ (nz) | model − `b_r` |
|---|---|---|---|---|
| ca-GrQc | 3 | 0.7764 | 0.6966 | **+0.0797** |
| ca-HepTh | 3 | 0.7759 | 0.6605 | **+0.1154** |
| email-Eu-core | 3 | 0.8863 | 0.9643 | **−0.0780** |
| facebook_combined | 3 | 0.9187 | 0.9152 | +0.0035 |
| p2p-Gnutella08 | 3 | 0.8915 | 0.8327 | **+0.0588** |

**The model's margin grows on the honest metric, on four of five networks.** On the sparse collaboration graphs it roughly triples (ca-GrQc +0.016 → +0.080; ca-HepTh +0.037 → +0.115). The reading: much of `b_k`'s all-node score is the same free floor §24.5 describes — it separates the zero set perfectly (see below) and is then weaker than the model on the part that is actually a ranking problem. **Removing the free part makes the learned model look better, not worse**, which is the opposite of what a sceptical reader would assume and is worth stating plainly.

email remains the exception in both metrics, and facebook remains a tie in both.

### The unexpected result: `b_2` *is* the §24.1 Proposition, arithmetised

`b_2(v)` counts precisely the pairs of **non-adjacent neighbours** of v — those are the only pairs at distance 2 with v interior. So

```math
b_2(v) > 0 \iff N(v) \text{ is not a clique} \iff v \text{ is not simplicial} \iff b(v) > 0
```

by the Proposition of §24.1. **Checked on all five networks: `support(b_2)` equals the nonzero betweenness set exactly** — 1,870 / 4,446 / 837 / 3,697 / 4,547 nodes, no discrepancies.

That gives §24.1 a **second, independent computational witness**. The existing canary in `analyse_betweenness.py` tests it through `ego_betweenness`; this route never touches that code and arrives at the same set. It also gives C4's two-number protocol a concrete answer to "what should a method's zero-set classifier be?" — `b_2`, which is a closed form, exact, and needs no model at all. Pinned as `verify_pipeline.py` **N11**, alongside the check that `b_k` at k = diameter reproduces full betweenness (max |diff| 2.2e-11 on email-Eu-core).

### How much reach is learning worth?

The comparison this project's axis actually invites: at what k does the untrained formula match the trained model's **r=3** score?

| network | model τ at r=3 | smallest k with `b_k` ≥ that |
|---|---|---|
| ca-GrQc | 0.9281 | **6** |
| ca-HepTh | 0.9199 | **6** |
| p2p-Gnutella08 | 0.9386 | **5** |
| facebook_combined | 0.9303 | 4 |
| email-Eu-core | 0.9134 | 3 |

**On the sparse collaboration graphs, learning at radius 3 buys roughly a doubling of effective reach.** That is the cleanest statement of the value of learning this corpus can produce, and it is stated on the reach axis rather than as a bare τ delta — which is the axis the whole project is organised around.

### The k=2 → k=3 dip: examined, partially explained *(2026-09-05)*

τ(b_k, b) is non-monotone in k on two networks — ca-HepTh 0.8909 → 0.8825, p2p-Gnutella08 0.9196 → 0.9056 — recovering by k=4. `probe_betweenness_k_dip.py`.

**First, the fact that reframes the question, and it is a proof rather than a measurement.** Raw `b_k(v)` is monotone **non-decreasing** in k for every node, by construction: each pair (s,t) either has `d(s,t) ≤ k`, contributing a fixed non-negative share that does not depend on k, or it does not and contributes zero. Raising k can only move pairs from the second category into the first; no term can shrink. **So no node's score goes down, and an implementation bug is excluded by the definition rather than by re-auditing the code.** The dip is a **rank reversal**: nodes approach their ceilings at different *rates*, so agreement with the true ranking can move non-monotonically while every underlying value climbs. (Asserted against the arrays as well — 0 violations on all five networks — because the proof says what must be true of `truncated_betweenness` and the assertion says the code implements the thing the proof is about.)

**The hypothesis tested:** local hubs are dominated by short-range pairs and saturate early; genuine long-range bridges only accrue importance once k is large enough to count far-apart pairs. Hubs would then hold the ranking at k=2 and be partially displaced at k=3, mid-resort.

Node-level attribution uses the exact decomposition `c_p(v) = Σ_u sign(b(v)−b(u))·sign(p(v)−p(u))`, whose sum over v is `2(C−D)`, so it partitions the statistic rather than proxying it. `Δ(v) = c_3(v) − c_2(v)`.

> **A confound that had to be removed first, and it reversed a conclusion.** Roughly half of every network here is simplicial (`b = 0`, §24.1) and has `b_k = 0` at every k, so those nodes can never move. Comparing movers' degree against the *whole graph's* median compares "nodes that can move" against "nodes that mostly cannot" — and simplicial nodes are overwhelmingly low-degree, so that test comes out significant regardless of the mechanism. Against the whole graph, ca-HepTh's losers looked like hubs (median degree 5.0 vs 3.0, p = 6e-25). Against the **nonzero set**, they are *below* median (5.0 vs 6.0). The same correction applies to the atlas base rates below, where it roughly halves every enrichment figure.

| check | result |
|---|---|
| **1. Do the drivers skew to high degree?** | **p2p: yes, both directions.** Losers median degree 11.0 vs 7.0 (p = 4e-25); gainers 2.0 vs 7.0 (p = 7e-47). Textbook hub displacement. **ca-HepTh: no.** Losers 5.0 and gainers 5.0, both *below* the nonzero median of 6.0. The resort there is among below-median-degree nodes. |
| **1b. The mechanism, measured directly** — τ(degree, `b_2/b`) on nonzero nodes | **Confirmed on the sparse graphs**: +0.380 ca-GrQc, +0.293 ca-HepTh, +0.207 p2p (vs +0.062 email, −0.118 facebook). Higher degree ⟹ more of the true value already captured at k=2. **But ca-GrQc shows it most strongly and does not dip**, so differential saturation is **necessary, not sufficient**. |
| **2. Failure-atlas cross-reference** | **Lands, and lands corpus-wide.** See below. |
| **3. Is the hub/bridge split sharper on the dip networks?** λ_NB/κ, where λ_NB = 1/β_c and κ = ⟨k²⟩/⟨k⟩−1 | **Ruled out.** 2.617 (ca-GrQc, no dip) > 2.503 (ca-HepTh, dip) > 1.592 (p2p, dip) > 1.528 (facebook) > 1.015 (email). The highest ratio belongs to a network that does not dip. No separation. |

**Check 2 is the result worth keeping, and it is bigger than the dip.** The nodes that `b_k` only begins to credit at k=3 are significantly enriched in the nodes the *learned model at r=3* **under-predicts** (Finding 8's atlas, true ≫ predicted), on **all five networks**:

| network | gainers in under-predicted tail | enrichment | hypergeom p | gainers in over-predicted tail |
|---|---|---|---|---|
| facebook_combined | 140 / 730 | **3.51×** | 2e-56 | 0.90× (ns) |
| ca-HepTh | 79 / 266 | **3.06×** | 1e-21 | 4.05× |
| ca-GrQc | 49 / 189 | **2.33×** | 1e-09 | 1.38× |
| p2p-Gnutella08 | 77 / 521 | **2.13×** | 1e-11 | 1.35× |
| email-Eu-core | 21 / 223 | **1.61×** | 8e-03 | 0.94× (ns) |

Two entirely unrelated methods — a closed-form truncation with no parameters, and a 171-feature random forest — **under-credit the same nodes**. That is Finding 8's locality blind spot arriving from the opposite direction, and it is independent of whether the network dips. On four of five the enrichment is specific to the *under*-predicted tail; **ca-HepTh is the exception**, where gainers are enriched in both tails (4.05× over-predicted), so there it reads as "extreme-residual nodes" rather than "under-predicted nodes" and the directional claim does not hold.

**Verdict, stated as the evidence supports and no further.** The dip is a rank reversal, not a value decrease — that much is proved. Differential saturation by degree is real on the sparse graphs and is the plausible driver, but it is present at full strength on a network that does not dip, so it is not the whole story. The specific hub-displacement account holds cleanly on **p2p only**. Branching heterogeneity as measured by λ_NB/κ is **ruled out**. **What remains unexplained is why ca-HepTh and p2p dip while ca-GrQc — same regime, same saturation signature, stronger degree–saturation coupling — does not.** That is a sharper open question than the one this started with, and it is the one to carry.

### What this does NOT establish

**`b_k` is not a published *learned* method, and running it does not discharge M2.** DrBC, ABCDE, BRAVA-GNN and 1D-CGS remain unrun and are Part D1 work. This closes the "no external comparison point of any kind" gap — it does not close the baselines gap, and the write-up must not let one stand for the other.

Cost, for the record: 14.4 s to 52.6 s per network for k = 1…6, single-threaded, on cached graphs.

---

## 26g. O1 — residual network autocorrelation: a hop-lag correlogram *(2026-09-06, C6)*

Every uncertainty figure in this project up to here measures one of two things: **model-fitting** variability (the seed sd behind every error bar) or, since A7, **Monte Carlo noise in the target**. Neither touches a third possibility. Neighbouring nodes have overlapping neighbourhoods, therefore overlapping features, therefore potentially correlated *errors* — and that effect would exist under noise-free ground truth. It is the standard reason random k-fold CV is optimistically biased in the spatial-statistics literature, and this project has never checked for it.

Code: `analyse_moran_correlogram.py` (measurement), `probe_moran_zeroset.py` (the confound check below). Output: `results_moran_correlogram.csv` (5,600 rows), `results_moran_zeroset.csv` (1,400 rows). Three minutes for the corpus; no refits — the OOF prediction stores already on disk carry everything needed.

### The weighting decision: a correlogram, not a matrix *(Rachit, 2026-09-05)*

The obvious implementations are plain adjacency, or a single fixed k-hop decay. **Both are refused, for a reason specific to this project rather than a generic methodological preference:** the premise under examination is that *reach-of-structure changes with r*. Any single fixed weights matrix chosen up front assumes an answer to the question this measurement exists to settle.

So Moran's I is computed **separately at each hop-lag**, each lag using the **exact-distance-d "hollow" indicator matrix** — weight 1 for pairs at distance exactly *d*, 0 otherwise — **row-normalised**. Not cumulative and not continuously decayed: either of those smears the lags together and destroys the only thing a correlogram is for. This is the standard spatial-statistics construction (Legendre & Legendre, *Numerical Ecology*; reference implementations `spdep::sp.correlogram` and `ncf::correlog`).

Two protocol choices follow, and both are stated rather than defaulted:

- **The null is permutation-based, not the classical analytic variance.** The closed-form variance of Moran's I is derived for near-regular spatial contiguity. These degree distributions are heavy-tailed enough that it misbehaves. 199 permutations per (target, radius, lag). *Validation:* the empirical null mean lands on the theoretical −1/(n−1) — −0.0009 measured against −0.0010 expected on email-Eu-core — which is a check on the whole machinery, not just the null.
- **Multiplicity correction is progressive (sequential) Bonferroni: lag *d* is tested at α/*d*, α = 0.05.** Not BH. BH is for exchangeable hypotheses; these are ordered, lag 1 is tested first and interest decays outward. The method is written into every row of the output CSV so no reader has to infer it.

Two guards, both of which change results rather than merely tidying them:

> **The graph-exhaustion guard.** At large *d* most nodes have no shell left — on email-Eu-core, lag 7 has 984 of 986 sources empty, so I is computed from **two nodes**, and `spread_cv` at r=3 returns I = −2.14, outside the interpretable range entirely. Both statistic and null then have enormous variance, p approaches 1, and the lag looks "indistinguishable from the null". Reading a buffer radius off that would report **the point where the network ran out**, dressed up as the point where correlation died. A lag is testable only when ≥30 sources contribute. Untestable lags are still written to the CSV — suppressing them would hide exactly the coverage story email exists to tell — but they are excluded from the read-off.
>
> **The r=0 degeneracy.** The spec's range *d* = 1…2*r*+1 admits exactly **one** lag at r=0, so a cell still significant at lag 1 has no lag left at which to become insignificant, and its buffer is undefined by construction. Read-off (a) obeys the spec range; read-off (b), which compares *across* r, uses a **common lag ceiling** instead, because otherwise it would be comparing unequal probe ranges — precisely the confound (b) exists to avoid. Every row carries `in_spec_range` so the two are never conflated.

### (a) Buffer radius, per cell — the block-CV number

The smallest lag at which I is indistinguishable from the permutation null. Reported **per (network, target, radius) cell, not as one global number for the project** — a single number would assume the uniformity the correlogram was built to test. At the reported radius r=3, median over ten seeds:

| network | betweenness | spread_mean | spread_cv | spread_resid |
|---|---|---|---|---|
| ca-GrQc | **4** | 1 | 1 | 1 |
| ca-HepTh | **3** | 5 | 4 | 4 |
| email-Eu-core | **4** | 4 | 1 | 1 |
| facebook_combined | **2** | 1 | 7 | 1 |
| p2p-Gnutella08 | **6** | 2 | 1 | 2 |

Every r=3 cell resolves to a finite buffer; none is left "still significant everywhere". Across-seed ranges are mostly tight (p2p betweenness 6–6, ca-GrQc betweenness 3–4) but not always — facebook betweenness spans 2–6 and facebook `spread_cv` spans 3–7, so those two cells' buffers are themselves unstable and any block-CV built on them should take the upper end.

**The operational consequence:** a graph-distance-blocked CV robustness check now has a *measured* buffer per cell rather than a guessed global one. The numbers are inconvenient — a buffer of 6 on p2p betweenness excludes a large fraction of the graph from every fold — which is itself worth knowing before the check is designed.

### (b) Does correlation length scale with r? — the discriminating question

If cells built at deeper r show correlation reaching further, the mechanism is **feature overlap** (overlapping r-balls → correlated residuals): expected, clean, a CV footnote. If correlation is flat and long-range regardless of r, the **target itself** is network-autocorrelated independently of feature construction — a claim about the phenomenon, not the protocol.

The buffer radius answers this weakly (it is ordinal, thresholded, and moves by whole hops): on the common ceiling, 7 of the 10 cells with a finite delta *shrink* from r=0 to r=3, 2 are flat, 1 grows. Nothing grows systematically, so **feature overlap is not the story** — but "buffer shrinks" is not yet an interpretation.

**The magnitude of lag-1 I is the sharper instrument, and it splits the corpus by target, not by network.** Median over seeds:

| network | target | r=0 | r=1 | r=2 | r=3 |
|---|---|---|---|---|---|
| ca-GrQc | spread_mean | 0.2518 | 0.0927 | 0.0451 | **0.0201** |
| ca-GrQc | spread_resid | 0.4172 | 0.1362 | 0.0457 | **0.0120** |
| facebook_combined | spread_mean | 0.5336 | 0.0317 | 0.0168 | **0.0111** |
| facebook_combined | spread_cv | 0.5266 | −0.0029 | −0.0104 | **−0.0189** |
| … | … | | | | |
| ca-GrQc | **betweenness** | 0.4115 | 0.1325 | 0.1594 | **0.1748** |
| ca-HepTh | **betweenness** | 0.3712 | 0.1862 | 0.1682 | **0.1624** |
| email-Eu-core | **betweenness** | 0.2301 | 0.1150 | 0.1434 | **0.1403** |
| p2p-Gnutella08 | **betweenness** | 0.1443 | 0.1471 | 0.1547 | **0.1625** |
| facebook_combined | **betweenness** | 0.3496 | 0.1174 | 0.0721 | **0.0673** |

**All three spreading targets collapse toward zero as r deepens, on all five networks. Betweenness does not.** On four of five it is flat or *rising* — p2p rises monotonically across every radius (0.1443 → 0.1471 → 0.1547 → 0.1625), ca-GrQc dips at r=1 and then climbs back above its r=1 value. Only facebook decays, and even there it plateaus at 0.067 rather than reaching the ~0.01 the spreading targets reach.

That is read-off (b)'s second branch, and it is the headline: **for betweenness, residual network autocorrelation is not removed by deepening the feature radius.** Deeper features absorb the spreading targets' spatial structure into the predictions, which is what feature overlap looks like when it is the whole story. They do not absorb betweenness's.

### The confound, checked before the headline was written

There is an alternative that produces the identical signature with no target-level autocorrelation whatsoever, and it is the confound this project has already been caught by twice:

> Roughly half of every corpus network is **simplicial**, with b(v) = 0 exactly (§24.1's proposition, §26f's `b_2` witness). *If* simplicial nodes were spatially clustered, and the model had systematically signed residuals on them — which it must, since ranking a mass of exact ties against a continuous prediction cannot be done well — then that component of the residual field would be both spatially clustered **and immune to r**, because the zero set is already decidable at radius 1. Flat and long-range regardless of r, from zero-inflation alone.
>
> §26f's dip investigation was reversed on ca-HepTh by exactly this correction. Writing this section without the check would have been the third occurrence, on the largest claim.

`probe_moran_zeroset.py` recomputes the betweenness correlogram on **{v : b(v) > 0}** only — sources, shell membership, denominator and permutation null all restricted to the subset, with hop distances still taken on the **full** graph, since the question concerns positions in the network and not the induced subgraph's own geometry. Residuals are re-ranked *within* the subset; slicing an all-node ranking would carry the zero block's rank mass in and defeat the point.

**Both halves of the confound fail.**

*The zero set is not clustered.* Lag-1 Moran's I of the nonzero **indicator** itself: −0.0538 (ca-GrQc), −0.0677 (ca-HepTh), −0.0074 (email), −0.0334 (p2p), **+0.0777** (facebook). Negative on four of five — simplicial nodes are mildly *dispersed*, not clumped, which is what leaf-and-hub adjacency predicts. The mechanism has no substrate to run on except possibly on facebook, and facebook is the one network where betweenness's I *does* decay.

*Removing the zero set does not weaken the signal — it strengthens it.* Lag-1 I on betweenness residuals, nonzero subset, against the all-node figure:

| network | r=3, all nodes | r=3, b>0 only | change |
|---|---|---|---|
| ca-GrQc | 0.1748 | **0.2262** | +0.051 |
| ca-HepTh | 0.1624 | **0.2079** | +0.046 |
| email-Eu-core | 0.1403 | **0.1699** | +0.030 |
| p2p-Gnutella08 | 0.1625 | **0.1766** | +0.014 |
| facebook_combined | 0.0673 | 0.0678 | +0.000 |

The flat-or-rising-with-r pattern survives on all five (ca-GrQc 0.296 → 0.180 → 0.223 → 0.226; p2p 0.172 → 0.156 → 0.166 → 0.177). The autocorrelation is carried by exactly the nodes that have a real ranking problem, which is the opposite of what the confound predicts.

### What this changes, and what it does not

**Primary result.** Betweenness residuals are network-autocorrelated at a magnitude (lag-1 I ≈ 0.07–0.23 at r=3, 0.07–0.23 on the nonzero subset) that **deepening the feature radius does not reduce**, and that is not an artefact of the zero set. For the three spreading targets the same measurement shows the expected feature-overlap picture and shows it cleanly: I collapses by one to two orders of magnitude from r=0 to r=3.

**Secondary result, and the actionable one.** Random 5-fold CV is optimistically biased for every cell with a buffer above 1, which is most of them. The per-cell buffer radii in (a) are the block sizes a graph-distance-blocked re-sweep would need. That re-sweep has **not** been run; it is a robustness check, not a correction, and no number in this document has been adjusted for it.

**What is NOT established, stated explicitly.**

- **No effect size on τ is claimed.** That residuals are autocorrelated does not by itself say how much τ would move under blocked CV. Only the re-sweep answers that, and it has not been done.
- **The mechanism behind betweenness's flatness is not identified.** A natural hypothesis — that it is the long-range-bridge population §26f's dip investigation left open, whose true importance accrues from pairs beyond any feasible r — is *plausible and unexamined*. It is recorded here as a question, **not as a finding**, and the two open items are now visibly related: §26f asks which nodes converge late in k, and O1 asks which nodes carry residual structure that r cannot remove. Whether they are the same nodes is a one-script check that has not been run.
- **The raw-residual arm is reported and disagrees in places.** The rank residual is primary — the targets span six orders of magnitude, so a raw residual would make Moran's I a statement about a handful of hubs rather than about the field, and the rank convention matches Finding 8's atlas. On raw residuals lag-1 I is *negative* for betweenness on email (−0.013) and facebook (−0.028) where the rank arm is strongly positive. The scale choice is a real modelling decision; both arms are in the CSV and neither is hidden.
- **A single approximation is taken in the null and is checkable rather than asserted.** One permutation null per (target, radius) is built from the seed-0 residual and reused across the ten seeds. Moran's I is invariant to affine rescaling of the residual vector, so the null depends on distribution *shape*, not scale; the across-seed spread of excess kurtosis is printed per network so the assumption can be inspected. A separate null per seed would cost ten times as much for a null that would agree to within its own Monte Carlo error.

---

## 26h. A7 — target noise, and why every error bar in this document is the smaller of two *(2026-09-06)*

Appendix-grade by intent, but the result inverted the expectation that motivated it, so it is stated in the body rather than buried.

The percolation shortcut evaluates all seeds against the **same** 4,000 live-edge samples. Node-level spread estimates therefore have strongly positive covariance, and the effective sample size behind each target column is far below 4,000. Every error bar in this project is a **seed sd** — model-fitting variability. The plan predicted that quoting target-noise CIs once would show seed noise dominates. It does not.

**Two arms, both bootstrapping the target over live-edge sample indices, 200 replicates, 60 cells** (5 networks × 3 Monte Carlo targets × 4 radii, richest tier). Full detail and the dated pre-registration are in `docs/prereg/prereg_A7_target_noise.md`; scoring in `score_a7_arm2.py`, per-cell output `results_target_noise_scored.csv`.

- **Arm 1 (frozen)** re-scores the cached OOF predictions against each resampled target. Cheap, but it charges τ for realisation mismatch while omitting the training channel entirely — so **it cannot sign its own bias**, which is why arm 2 was run.
- **Arm 2 (refit)** performs a full out-of-fold refit per replicate: 12,000 refits, paired to arm 1 by construction (same RNG seed and call sequence, with a runtime pairing anchor rather than an assumption).

**`betweenness` is excluded from both arms** and this is not an omission: it is computed exactly by Brandes, carries no Monte Carlo noise, and a bootstrap over cascade samples cannot move it. A row of zeros would read as a bug rather than as a fact about the estimator. Everything §26f and §26g say about betweenness is therefore untouched by this section.

**The result: target noise exceeds seed noise, and freezing the model *understated* the gap.** Median seed-sd ÷ target-noise-sd:

| target | arm 1 (frozen) | arm 2 (refit) |
|---|---|---|
| `spread_cv` | 0.401 | **0.307** |
| `spread_resid` | 0.463 | **0.344** |
| `spread_mean` | 0.554 | **0.441** |

Seed noise is smaller than target noise on **55 of 60** cells frozen and **56 of 60** refit — and once the model is free to adapt it is typically a **quarter to a half** of the target noise, not a half. The ratio of refit to frozen target-noise sd has median **1.220** and falls below 1 on only 2 of 60 cells.

The pre-registration predicted the opposite direction (P1) and **named the competing mechanism in advance (P2)** precisely so that an increase would be reportable rather than explained after the fact. P2 is what happened: a random forest fitted to a noisier target realisation makes genuinely worse splits, and that degradation is invisible to a frozen design. The realisation-mismatch channel is real but smaller.

**Phase 6 paired follow-through (2026-09-07).** The saved dynamic-tier corpus now supplies 45 adjacent-radius contrasts with 200 paired target-bootstrap replicates and ten paired seeds. Under the descriptive |mean gain| > 2·sample SD rule, 38 flags are retained, 3 lost and none new (4 neither). All 45 target-radius covariances are positive; paired SD is median 0.529 of covariance-ignored SD. The target/seed paired-SD ratio is median 1.733. Lost flags are email spread_resid r1→r2 and facebook spread_cv/spread_resid r1→r2. See [design and limits](archive/phase6_record.md#rec-phase6_paired_noise_analysis). This is post-hoc and conditional, not total uncertainty or an updated significance test. The saved corpus uses the richest dynamic tier; headline radius tables use the richest structural tier. Therefore this measurement does not resolve or downgrade those headline stars. Structural-tier paired refits and blocked CV remain unrun.

---

## 26i. C3 — external benchmark levels and the two tie regimes *(2026-09-06)*

**BRAVA-GNN makes this test possible by computing and shipping the nonzero-subset
Kendall τ alongside all-node τ.** The contribution here is verification and interpretation
of that existing metric, and a reporting protocol, not discovery of the metric or a
criticism of the method. The binding registration and full graph/verdict tables are in
`docs/prereg/prereg_C3_benchmark_inflation.md`, under SCORED. Nothing was trained.

The complete corpus comprises eight directed graphs, five undirected ABCDE graphs and
p2p-Gnutella31 symmetrised according to BRAVA's regime declaration. The shipped table has
395 distinct paired algorithm names; six labels recur with distinct observations, so
source-order pairing gives 404 paired row occurrences and **5,608 finite graph/row
observations**. Repeated labels are retained, not silently discarded. Counts and drops
below include the external methods as required by the registration.

| Graph | Structural z | Median all-node minus nonzero τ | Registered P3 hits / observations |
|---|---:|---:|---:|
| amazon | 0.326893 | 0.16450 | 12/404 |
| cit-Patents | 0.188374 | 0.12500 | 12/404 |
| com-lj | 0.287801 | 0.16090 | 9/401 |
| com-youtube | 0.573210 | 0.23145 | 18/404 |
| dblp | 0.419574 | 0.21970 | 9/401 |
| email-EuAll | 0.960877 | 0.43280 | 26/401 |
| p2p-Gnutella31 | 0.460630 | 0.16440 | 0/404 |
| soc-Epinions1 | 0.634497 | 0.26250 | 15/401 |
| soc-LiveJournal1 | 0.355146 | 0.19290 | 12/398 |
| soc-Pokec | 0.219042 | 0.09920 | 9/398 |
| soc-Slashdot0902 | 0.411523 | 0.14800 | 9/398 |
| web-Google | 0.561119 | 0.52570 | 13/398 |
| wiki-Talk | 0.958774 | 0.33440 | 27/398 |
| wiki-topcats | 0.040070 | 0.03220 | 0/398 |

**Registered verdicts.** P1 is **FALSIFIED**: median absolute error **0.078564** exceeds
0.05 and median signed error **−0.076970** violates the nonnegative-sign clause. P2 is
**SUPPORTED**, Spearman **ρ = 0.890110** across all 14 graphs against the registered
0.5 threshold, and remains secondary because four drops were already seen. P3 is
**SUPPORTED as registered, 12/14 graphs**, against the unchanged geometric-floor + 0.05
criterion and ≥7 threshold; p2p-Gnutella31 and wiki-topcats do not qualify. This criterion
is one-sided: it includes values below the reference, not just values within absolute
distance 0.05. It does not establish a method-ranking reversal.

**Why P1 failed — a post-hoc diagnosis, not a replacement prediction.** Write
`T = C(n,2)`, `S = T − C(n_z,2)` and `Q = C(n_m,2)`. With perfect separation of zeros
from positives and no additional positive-block ties, the two expressions are:

| Prediction tie regime | All-node mixture | Zero-skill reference (τ_nonzero = 0) |
|---|---|---|
| Continuous predictions, including among true zeros | `(n_z n_m + Q τ_nonzero) / sqrt(S T)` | `n_z n_m / sqrt(S T)`, asymptotically `w sqrt(1−z²)` |
| Predictions tied on the true-zero block | `(n_z n_m + Q τ_nonzero) / S = w + (1−w)τ_nonzero` | **w** |

The exact finite-n geometric factor is `sqrt(S/T)`; the registered `sqrt(1−z²)` is its
large-n approximation. Neither formula applies universally to arbitrary tied scores or
imperfect boundary classification. The reference called a “floor” is a zero-within-block-
skill benchmark, not a lower bound for a method that reverses the positive ranking.

BRAVA's `utils.py::graph_to_adj_bet` multiplies adjacency rows by its clique mask.
Masking supplies a mechanism for identical zero-set embeddings and scores, collapsing
τ-b's denominator from `sqrt(S T)` to `S`. The synthetic check in
`analyse_c3_benchmarks.py::check_tie_denominator` verifies both regimes against scipy to
at most **1.11e-16** on its test arrays; `verify_pipeline.py` pins both forms so neither
becomes “the formula” again. Across the **5,278 `baseline_*` observations**, the tied
formula's median absolute error is **0.000039**, against **0.078296** geometric.

That strong median fit must not be described as exact reproduction throughout the
family. The tied error reaches **0.715413** on an email-EuAll `baseline_random_*` row.
The shipped aggregate table does not establish every row's ties, separation or
positive-block tie corrections. Those exceptions remain included; resolving their
individual causes requires prediction or configuration evidence. A prefix is not
proof that the assumptions hold.

**External controls.** The median absolute errors (geometric / tied) are DrBC
**0.184297 / 0.271664** (42 observations), KADABRA **0.261604 / 0.392771** (42),
SILVAN **0.190562 / 0.261353** (126), Bavarian **0.152104 / 0.339543** (18), and
ABCDE **0.112762 / 0.189548** (18). The sampling approximators and learned DrBC
baseline fit neither form well. This contrast supports the masking/perfect-separation
diagnosis; it does not prove every residual comes from that mechanism, nor does it
make DrBC a sampling approximator.

**The quantised-support caveat.** cit-Patents has **709,062 structural zeros versus
709,724 shipped zeros**; com-lj has **1,150,616 versus 1,151,702**. BRAVA's
`keep = true_arr > 0` uses the shipped support. Predicting its column therefore uses
shipped z (**0.188550 / 0.288072**) and w (**0.317277 / 0.447292**), not the
structural quantities (**z 0.188374 / 0.287801; w 0.317028 / 0.446965**).
The w changes are **0.000249 / 0.000328**, too small to change these verdicts;
P2's ρ is identical under either support. P2 and registered P3 retain structural z.

**P4 passes under its previously invoked conditional.** The completed gate reports
0 mismatches on 4,752 nodes in 30 random digraphs and 0 on 7,281,095 nodes in the
three ABCDE graphs without support loss. The two files with support loss supply
**consistency only**: zero `rule = 0 & shipped > 0` discrepancies over 7,762,079 nodes,
while all **1,748** opposite-direction discrepancies (662 and 1,086) remain reported.
The repeated-minimum detector was removed after a counterexample; the third amendment
uses the named two-file set, not a mass threshold. C4's exact Decimal recount finds
**15,043,174 values** across all five score files, all on the 1e-14 grid. This corrects
the third amendment's 14,943,174 total; its existing P4 denominators already sum correctly.

All five files are quantised, including those without support loss. Under nearest
rounding, positives strictly below 5e-15 reach zero; grid membership alone establishes
neither the rounding mode nor the unavailable exact magnitudes. The first-grid-point
masses 1,679 and 3,802 are descriptive evidence, not an automatic gate. The directional
conditional is weaker than a two-direction exactness test and does not turn the 1,748
excused discrepancies into survived falsification opportunities. The five-project-network
fallback now has an independent C3 loader/CSR nodewise gate: all five required graphs,
24,120 aligned nodes, zero mismatches in either direction. It fails on absent inputs or
ID/order disagreement. This strengthens implementation evidence for zero support only;
positive magnitudes and the post-observation amendment timing remain limitations.

> **Witness executed on all five ABCDE graphs, 2026-09-11 by Claude Opus 5 (see the
> [precision follow-up](archive/phase6_record.md#rec-phase6_external_precision_followup)).** The exact rational local
> witness now has measured outcomes, and they bear directly on the paragraphs above.
>
> On the **two graphs with support loss**, the 662 and 1,086 structurally-positive printed
> zeros are confirmed as selected targets, and **no pair qualifies at either threshold**
> (`gt_5e15` 0, `gt_1e14` 0) — the certified bounds are real but too weak to contradict the
> shipped zeros. That is a null, and it does not strengthen the directional conditional.
>
> On the **three graphs without support loss** the witness selects **zero** structurally-positive
> printed zeros among 3,030,420 printed zeros (amazon 701,532; dblp 1,678,358; com-youtube
> 650,530). Every printed-zero node there has a clique neighbourhood, so no printed zero is
> structurally impossible. The selector's predicate is not a clamping detector — it asks only
> whether a node has two nonadjacent neighbours — so the separation is informative: the two
> graphs with support loss are exactly the two carrying structurally impossible zeros.
>
> This is a **control result and remains a null**. It does not prove the three graphs are
> unclamped; "all five files are quantised" above is unchanged, and grid membership still
> establishes neither the rounding mode nor the unavailable exact magnitudes. The directional
> test still cannot catch false-**nonzero** rule errors among shipped zeros, and the 1,748
> excused discrepancies remain excused, not survived. Two defects found while executing —
> a 61-character pinned SHA-256 and a degree range wrong at both ends — are recorded in the
> [witness design](archive/phase6_record.md#rec-phase6_precision_witness_design).

**P3's diagnosis stays separate from its score.** A masked scorer's relevant reference
is w, while a continuous scorer's is geometric. The original transcript's blanket-w
sensitivity gives 13/14, but assigns that tie regime to external methods too. Assigning
shipped w to `baseline_*` rows and geometric references to the others gives 12/14;
this is a conditional illustration because per-row tie regimes are not measured.
Neither replaces the registered **12/14** geometric-floor verdict.

**What follows.** Median drops range from **0.03220 to 0.52570** and track graph
structure strongly. This is evidence about the reported **level**, not a claim that
methods are bad or their rankings flip. The prior BRAVA configuration-ordering result
(τ 0.87–0.999) remains the framing and was not recomputed here. BRAVA already shows
the nonzero metric is cheap to produce; C4 should make explicit reporting of the
zero-set task and positive-only ranking routine, with support and tie metadata.

C4 was started on 2026-09-07 in `docs/reference/C4_two_number_reporting_protocol.md`, which
defines those measurements and their support, tie and provenance metadata. Its three
bounded steps were delivered the same day: an external support and zero-count
reconciliation audit (`audit_c4_support.py`), a reusable reporting implementation
(`c4_two_numbers.py`, pinned by `verify_pipeline.py` N12) exercised as a
code-correctness check against this project's own cached predictions, and a cutoff
predeclaration contract. Nothing was fitted. **No two-number pilot was run on any
published method, and none can be** — Finding C4-1 in that document records that no
method in this corpus, BRAVA-GNN included, ships the per-node arrays such a pilot needs.

Reproduction: `score_c3_results.py` verifies the saved run against the shipped CSV
and records input hashes, corrected cell/graph tables and control summaries. The
large-graph P4 evidence comes from the completed background run.

**Independent traversal completed 2026-09-07.** An earlier version of this paragraph
recorded that a second traversal had been attempted and abandoned on a scratchpad
read-permission error, and therefore did not count as a fresh verification. That is
superseded: `analyse_c3_benchmarks.py` has since been re-executed from the raw edge
lists, rebuilding every zero set from scratch, and `results_c3_structure.csv` and
`results_c3_cells.csv` reproduced the originals apart from the support-sensitive
changes summarised for two graphs — cit-Patents geometric median signed error −0.0130 →
−0.0129 and com-lj tied +0.0003 → +0.0004, both from the shipped-zeros switch committed
between the two runs. `score_c3_results.py` and `verify_docs.py` were then re-run against
the regenerated cells and both report ALL CHECKS PASSED. Every figure quoted in this
section is therefore true of the data currently on disk, and the verdicts are unchanged.
This historical execution account comes from the dated supersession in
`docs/prereg/prereg_C3_benchmark_inflation.md` under SCORED, which retains the earlier limitation.
The present documentation pass checked the saved artefacts, not that traversal's historical
execution. No threshold was moved and no model was fitted.

### Regenerated after the Task 6 fixes: verdicts unchanged to the digit (2026-09-12)

> **Added 2026-09-12 by Claude Opus 5 (Task 6 findings P3-02, P3-03, P3-04; run C7).**
> `analyse_c3_benchmarks.py` was re-executed from the raw edge lists after three audit
> fixes to the scorer (an exact `tau_floor` beside the `2z/(1+z)` approximation, the
> ABCDE shipped-zero gate detail carried into the structure rows, and a registered
> `tau_floor` column on every cell), and `score_c3_results.py`, `c4_two_numbers.py` and
> `audit_c4_support.py` were re-run on the result. **P1 FALSIFIED at MAE
> 0.07856417907755398, P2 ρ = 0.8901098901098902, P3 12/14, P4 PASSED UNDER REGISTERED
> CONDITIONAL — every scored number in `c3_scored_summary.json` is byte-identical to the
> 2026-09-07 file.** What did change is bookkeeping, not evidence: the exact floor differs
> from the approximation by at most 1.5 × 10⁻⁶; the two clamped graphs now record their
> ABCDE-gated zero counts (cit-Patents 709,062 → 709,724; com-lj 1,150,616 → 1,151,702)
> with `clamped = True` where the 2026-09-07 file had left the flag false; and the
> per-cell registered floor is at most 2.7 × 10⁻⁴ on tied predictions. The full table of
> differences, with hashes, is `docs/archive/phase6_record.md#rec-C3_C4_REGENERATION_NOTE_20260912`;
> `verify_c3_scoring.py` and `verify_docs.py` pass on the regenerated files
> (`results/VERIFY_phase6_claude_c3_scoring_20260912.txt`).

---

## 26j. C4 — delivered reporting machinery and remaining work *(2026-09-07)*

The three bounded C4 pieces are complete and have different evidential weight.
[The protocol](reference/C4_two_number_reporting_protocol.md) is the detailed specification;
this section records implementation status and the evidence available on disk.

| Delivered piece | Reproducible artefacts | Result and scope |
|---|---|---|
| External support and zero-count reconciliation audit | `audit_c4_support.py`; `results_c4_support_audit.csv`; `results/RESULTS_c4_support_audit.txt` | 15,043,174 decimal values checked, zero grid exceptions; structural/shipped support and source occurrence sensitivities. **Not a two-number pilot.** |
| Two-number implementation | `c4_two_numbers.py::report`; `verify_pipeline.py` N12 | Explicit zero decision/provenance, zero-labelled confusion counts/rates, reference-positive tau-b, actual ties/denominator, NA reasons and invalid-input rejection. |
| Internal code-correctness check | `results/results_c4_internal_smoke.csv`; `results/RESULTS_c4_internal_smoke.txt`; `results/c4_internal_provenance.json` | 800 cached betweenness vectors, 160 per graph; no fitting; all require general pair accounting. **Not pilot evidence.** |
| Cutoff predeclaration contract | Protocol's “Cutoff predeclaration contract” | Fixed, top-k and adaptive rules: what to freeze before graph/label access, realised decisions to release and what cannot be audited. |

**External audit results.** Switching from structural to shipped support increases the
geometric references by **0.000233865** on cit-Patents and **0.000277127** on com-lj.
Maximum geometric mixture-prediction shifts are **0.000192224 / 0.000213260**.
Global P1 medians and the two graphs' P3 hit counts remain unchanged. Keeping only the
first or last repeated name loses **126** observations (5,608 to 5,482), changes a graph's
median drop by at most **0.0009**, and changes rho from **0.890110 to 0.907692**.
These are sensitivity calculations, not replacements for the registered occurrence-level
analysis. An actual structural-support filtered method tau cannot be reconstructed from
the available aggregates.

**Internal code-correctness check.** Each vector is a full 5-fold OOF vector with key
`target|radius|richness|seed`; the final field is not a fold. The runner explicitly
supplies `score == 0` **retrospectively for this check**, because the cache contains no
historical declared zero mask. The numbers below cannot validate prospective cutoff
selection or an external method's reporting behaviour.

| Graph | Rows / finite positive taus | Median zero accuracy | Median positive tau-b |
|---|---:|---:|---:|
| ca-GrQc | 160 / 160 | 0.991101 | 0.723900 |
| ca-HepTh | 160 / 160 | 0.995948 | 0.714781 |
| email-Eu-core | 160 / 160 | 0.965517 | 0.876114 |
| facebook_combined | 160 / 160 | 0.963605 | 0.645960 |
| p2p-Gnutella08 | 160 / 160 | 0.998412 | 0.872212 |

Medians pool all radius/richness/seed configurations per graph; they are not selected
operating points or uncertainty intervals. All-node taus match the stored sweep cells
within **2.220e-16**. NPZ lacks node and fold IDs: agreement with target ordering and
sweep metrics is consistency evidence, not proof of historical alignment or held-outness.

**Verified implementation, bounded conclusions.** The support audit, `verify_pipeline.py`,
`verify_generators.py`, `verify_docs.py` and `score_c3_results.py` report **ALL CHECKS
PASSED**; C4 verification transcripts are under `results/VERIFY_c4_*.txt`. N12 checks
hand-computable accuracy 3/5, positive tau 1/3, tied/untied all-node taus 7/9 and
7/sqrt(90), degenerate cases and pair-count products exceeding int64. No model was fitted
and the C3 verdicts in §26i did not change.

### What remains after C4

| Remaining item | Current evidence / next bounded action |
|---|---|
| D2 paper argument and positioning | Phase 6 manuscript, source review and reproduction guide delivered; §24.6 corrects the direct Perrone finding. Venue fit is conditional; submission/publication remains outside this handoff. |
| Prospective external two-number evaluation | Finding C4-1 remains: inspected releases lack per-node method arrays and declared decisions. No such pilot was run. An author-supplied release could enable it; no checkpoint execution or author contact is authorised here. |
| Stronger C3 verification | Nodewise C3 fallback enforcement now passes all five required graphs: 0 mismatches over 24,120 aligned nodes, both directions retained. Exact positive magnitudes and rounding mode remain unestablished; P4 stays conditional. |
| D3 controlled synthetic confirmation | Generators and `stage0_generate.py` exist and are verified; the confirmatory sweep remains unrun. No D3 registration is present among the checked preregistration files. Fix predictions and scoring rules before executing a new experiment. |
| Real-corpus scale-out and cross-network transfer | Five-network fitted evidence and the 14-graph aggregate audit answer different questions. No broader fitted confirmation or cross-network generalisation result is established by C4; these follow the controlled arm in the current plan. |
| Published learned baselines inside the radius protocol | Still deferred; C3 re-analysis is not execution of a baseline. Requires its own scope and environment. |
| A7 paired target-noise impact and blocked CV | Saved dynamic-tier paired analysis delivered: 38 retained, 3 lost, 0 new heuristic flags across 45 contrasts. These are not headline structural-tier stars. The authorised September 8 extension now runs structural-tier paired refits; buffered-CV implementation is active. Results remain pending; see §26k. |

The implementation dependency in the work plan is discharged. Later empirical work still
needs its own predeclaration and execution scope; documentation completion is not permission
to fit models, install dependencies, contact authors or execute external checkpoints.

## 26k. Expanded Phase 6 follow-up *(status 2026-09-10)*

The subsequent authorisation permits the CPU sweeps needed to close Phase 6 evidence
gaps. It supersedes the earlier no-fit boundary. Designs were written before the new
follow-up results; historical C3/A7/B1/B2 verdicts remain unchanged. Phase 7 is deferred.

| Work | Built and checked | Still required |
|---|---|---|
| Structural paired target uncertainty | Separate resumable structural-tier runner and paired analyzer; 11 scoped tests; complete 120-cell pilot with interruption/resume validation. | Full 12,000-cell corpus, all 45 paired contrasts and interpretation against matching structural seed results. |
| Buffered CV | Producer/harness/analyzer passed scoped review and all 25 fixtures. Structural Moran: 5,600 rows, 51 resolved and 29 unresolved buffer decisions. Preflight: 20,000 logical fold rows, 13,972 canonical fits and 1,500 aliases; the four-worker pilot and controlled stop/resume passed. Full execution is active. | Complete feasible fits, validate final logical-cell accounting and analyze paired outcomes. Exhausted and unresolved buffers remain explicit results. |
| External precision | Public-source investigation and exact rational local-witness design for the 662/1,086 structural-positive printed zeros. | Execute bounded-memory witnesses and report conditional bounds. Producer normalisation and rounding provenance remain unknown. No external per-node predictions have been established. |
| Radius-one attribution | Matched five-network, four-target, four-nested-set, ten-seed design. | Current-feature ablation fits and all 60 paired step contrasts; replace broad attribution language only using measured outcomes. |
| Numerical criticality | Repaired bipartite spectral sign, tree/unit-root boundary, exact unicyclic components and invalid transmission probabilities. Scoped review and analytical/cached-network checks pass. | Include the repaired module and callers in the final full audit. Existing caches were not regenerated. |
| Full audit and reconciliation | Requirements inventory and final audit protocol are written. The four missing threshold-comparison values have been measured and added to HANDOFF. | Review every source file after implementation, resolve defects, run affected checks and reconcile plan/study/paper with complete outputs. |

The [extension ledger](archive/phase6_record.md#rec-phase6_extension_20260908) records execution state and
artifact paths. The [final audit protocol](reference/phase6_final_audit_protocol.md) defines
closure evidence. Neither a successful pilot nor a launched process is a completed
research result. These additions measure conditional robustness; they do not establish
total uncertainty, independent graph generalisation or an external two-number pilot.

The [buffered execution record](archive/phase6_record.md#rec-phase6_buffered_cv_execution_status) contains
the authenticated prerequisite counts and pilot. Forty-five of 80 buffer decisions
have a later significant lag after the first testable non-significant lag. This
predeclared read-off therefore does not establish that all more distant residuals
are uncorrelated. The shared seed-0 permutation reference and remaining transductive
and simulation dependence also limit an independence interpretation.

> Added 2026-09-10 by Claude Opus 5. The table above describes what was *planned*, and is kept
> as the record of that. The three subsections below report what the completed runs actually
> measured. Where a "Still required" cell is now answered, the answer is here, not there.

### 26k.1 Structural paired target uncertainty — measured

The full corpus completed: 12,000 cells, all 45 predeclared adjacent-radius contrasts scored
with the predeclared descriptive paired-SD heuristic. The outcome is **38 flags retained, 3
lost, 4 neither, and none new**.

The three lost flags all sit at the radius 1→2 step: email-Eu-core/`spread_resid`
(mean gain −0.005752, paired SD 0.021810), facebook_combined/`spread_cv` (+0.002007, 0.001674)
and facebook_combined/`spread_resid` (+0.004565, 0.002437). No headline structural-tier flag
failed that A7 had retained.

This reproduces A7's saved dynamic-tier analysis exactly — the same counts *and* the same three
contrasts. **That agreement is weaker evidence than it looks, and is qualified here rather than
reported as replication.** The two tiers share their target-noise resamples by design (asserted
by `verify_structural_target_noise.py`), so they see identical perturbed targets. What it
establishes is that the fragility of those three flags is driven by **target noise**, not by the
feature tier.

The quantitative statement the corpus does support: the ratio of target-noise paired SD to
seed-only paired SD has median **1.700** and exceeds 1 in **41 of 45** contrasts (range
0.700–3.984). Ten-seed intervals therefore understate total uncertainty on most contrasts, which
is the mechanism behind the three losses. Detail in
[the structural task report](archive/phase6_record.md#rec-phase6_structural_task_report).

### 26k.2 Buffered CV — measured

`verify_buffered_cv.py` passes 25/25 against the completed corpus and all 20,000 logical fold
rows are accounted for (15,472 ready, 814 `infeasible_lt30`, 814 `source_infeasible`, 2,900
`unresolved_seedwise_buffer`); the infeasible and unresolved cases are reported, not dropped.

The interpretable comparison is **buffer vs size-matched control**, both sharing one geometry.
At b=1, removing the same number of training rows *without* regard to geometry costs −0.005 tau;
removing them *by proximity* costs −0.092, leaving −0.087 for geometry alone. **About 94% of the
buffered drop is geometric rather than a training-set-size effect.** At the measured radii the
same decomposition gives −0.027 versus −0.182, leaving −0.155 (~85%), on 30 of 80 decisions and
correspondingly weaker.

The random-KFold file is a distinct geometry and is deliberately **not** used as a comparator.
These remain descriptive within-seed contrasts with no null distribution and no multiplicity
correction; a measured buffer is a diagnostic label-exclusion radius, **not** a proof of
independence. The 45-of-80 `later_testable_sig` warning stands and does not license departing
from the predeclared read-off. Detail in
[the buffered execution record](archive/phase6_record.md#rec-phase6_buffered_cv_execution_status).

> *Added 2026-09-12 by Claude Opus 5 (Task 6 finding P3-08).* The analysis table has 480
> rows — one per (cell, predeclared pair) — of which 330 are scored, but in 15 of the 80
> cells the measured buffer resolved to 1, so the `*_measured` arms there are aliases of the
> `*_b1` arms and their three contrast rows repeat the b1 rows exactly. **45 of the 330
> scored rows are repeats; the scored table holds 285 distinct measurements.** This
> matters for the "measured radii" sentence above: its 30 decisions are the 30 cells whose
> `buffer_measured` arm is complete, and **15 of those 30 are the alias cells**, so the
> −0.027 / −0.182 pair averages 15 genuine measured-buffer cells with 15 copies of b=1
> numbers. Over the 15 cells whose measured buffer is genuinely > 1 the same decomposition
> is −0.046 (size-matched control) versus −0.231 (buffer), leaving −0.185, about 80%
> geometric; over the 15 alias cells it is −0.007 versus −0.133, which is just their b=1
> result restated. The direction of the finding does not change; the "30 of 80" count and
> the ~85% figure should be read as 15 of 80 and ~80%. Computed from
> `results/phase6_buffered_cv_cells.csv` through `analyse_buffered_cv.descriptive_contrasts`
> on 2026-09-12; the rows are flagged (`is_alias`, `alias_of_pair`) from the table's next
> regeneration.

### 26k.3 Radius-one attribution — measured

> **SUPERSEDED 2026-09-12 by Claude Opus 5 (Task 6 findings P1-01 → run C2). Read this
> block first; the section beneath it is the 2026-09-11 write-up, retained verbatim.**
>
> The 800-cell run reported below (`run_id afadc675…4441`) was fitted against feature
> registries in which six 5-node orbits — 56, 57, 65, 66, 68, 70 — were tagged hop 1 although
> a node in each of them can be two hops from the centre (P1-01; the retag and the sweep
> refit are described in §19b and §26k.2). Its `full_r1_structural` set therefore had 62
> columns, six of which were hop-2 columns, and "the seventeen extra 5-node hop-1 orbits"
> were in fact eleven hop-1 orbits plus those six. The pre-retag artefacts are archived at
> `results/phase6_r1_ablation_pre_orbit5_retag_20260910/` and were not edited.
>
> The design was rerun unchanged on the corrected registries on 2026-09-12 — same five
> networks, same feature and target caches (hashes unchanged), same ten seeds, same folds,
> same `rf_log1p` objective; only the top rung changed, 62 → 56 columns. Artefacts:
> `results/phase6_r1_ablation/`, `run_id c66485a6…299f`; the pre/post comparison is in
> `results/phase6_r1_ablation_retag_delta_20260912.txt`.
>
> | Contrast (nested step) | pre-retag (62-col) | **post-retag (56-col)** |
> | --- | ---: | ---: |
> | `add_nonorbit_subgraph` | 2 of 20 | **2 of 20** (same two cells, means equal to 2 × 10⁻⁷) |
> | `add_orbit_lt15` | 0 of 20 | **0 of 20** (means equal to 3 × 10⁻⁷) |
> | `add_remaining_g5_orbits` | 17 of 20 | **0 of 20** |
>
> **Every one of the seventeen stars on the 5-node rung disappears.** The largest post-retag
> |mean| on that rung is 0.00054 τ (email-Eu-core/`betweenness`, still negative, sd 0.00049),
> against pre-retag gains up to +0.03515; the sum of the twenty means falls from +0.187 to
> +0.0004. The two lower rungs, whose columns did not move, reproduce to floating-point
> round-off, which is the control that the rerun changed nothing but the six columns.
>
> **What this means.** At radius one, the 5-node orbits contribute nothing that the 4-node
> orbits do not already carry, on any of the five networks, for any of the four targets. The
> "5-node graphlets beat 4-node at r=1" result — here, in §16's three-network tables, in
> HANDOFF Finding 3 and in the open-decisions list — was a *radius* effect mislabelled as a
> *graphlet-size* effect: the whole gain was carried by six orbits that reach two hops. It is
> the same failure class as Finding 10's "+0.148 edge tier" (tier tags are inputs, not
> labels; a mis-tagged column yields a plausible number credited to the wrong rung). The
> three-network tables in §16 are *inferred* to rest on the same tag, because the pre-retag
> five-network run reproduced their magnitudes to three decimals (+0.0353 → +0.03515).
>
> **What it does not say.** Nothing about r ≥ 2, where the six orbits now live. Whether they
> earn their place at hop 2 is a question for the main radius ladder (§19b's regenerated
> table shows hop-gain rows moved only at r0→r1 and r1→r2, as the retag requires), not for
> this ablation. The non-orbit-subgraph result — two `betweenness` cells and only those —
> stands exactly as written below. Stars remain the descriptive |mean| > 2·sd heuristic.

The full matched design ran: **800 fresh out-of-fold cells** (5 networks × 4 targets × 4 nested
feature sets × 10 paired seeds), 60 paired contrasts, **19 flagged**. No historical `cache_oof`
endpoint was reused — those archives carry no manifest, column list, fold digest or objective id,
and the root betweenness endpoint belongs to the *raw* objective while this report uses
`rf_log1p`. Artifacts: `results/phase6_r1_ablation/`, `run_id afadc675…4441`.

**The rung that carries the effect is the 5-node orbits, and only that rung.**

| Contrast (nested step) | Flagged cells |
| --- | ---: |
| `add_nonorbit_subgraph` (node+edge → +non-orbit subgraph) | **2 of 20** |
| `add_orbit_lt15` (→ + node orbits index < 15) | **0 of 20** |
| `add_remaining_g5_orbits` (→ + remaining 5-node orbits) | **17 of 20** |

Adding the 4-node-and-smaller node orbits moves nothing anywhere: zero of twenty cells, with
mean gains at or below 2.5 × 10⁻⁴ in absolute value on every network and target. The remaining
5-node orbits then produce gains up to **+0.035 tau** (ca-GrQc/`spread_cv`), typically with all
ten seeds agreeing in sign. This is consistent with the earlier r=1 finding that 5-node graphlets
beat 4-node ones, and it now rests on all five networks rather than three.

**Qualified by graph, as required.** The 5-node step is *not* universal. It fails to flag on
three cells: ca-GrQc/`betweenness` (+0.00045, sd 0.00081), email-Eu-core/`spread_resid`
(+0.01163 but sd 0.00855 — a large mean swamped by seed variance) and email-Eu-core/`betweenness`,
where the mean gain is **negative** (−0.00049, sd 0.00037, nine of ten seeds worse). That last
cell is a small consistent *harm*, below the flag threshold but pointed in the opposite direction
from every other network; it is retained here rather than absorbed into a positive summary.
Symmetrically, the non-orbit subgraph step flags on exactly two cells and both are `betweenness`
(email-Eu-core +0.00254, facebook_combined +0.00349) — a target-specific effect, not a tier-wide
one.

The stars are the descriptive `|mean| > 2·sd` heuristic over ten seeds: no null distribution, no
multiplicity correction across 60 contrasts, and ten seeds on one graph are not ten graphs. **This
covers radius one only** and says nothing about any other radius. It does not alter Finding 3 or
any registered outcome; reconciliation of the broad expressive-power language elsewhere in this
document is a separate step against these artifacts. Detail in
[the ablation brief](archive/phase6_record.md#rec-phase6_r1_ablation_implementation_brief).

#### What is and is not independently established about the 5-node orbit counts

*Scope statement added 2026-09-12 by Claude Opus 5 (Task 6 finding P1-08).* The rung that
carries this section's effect is the 5-node orbits, so it has to be said exactly what this
project has verified about them and what it inherits.

- **Inherited from ORCA (Hočevar & Demšar, 2014), not re-derived here:** the system of
  linear equations by which `vendor/orca.cpp` recovers most 5-node orbit counts from a
  smaller set of enumerated ones, and the Pržulj (2007) orbit numbering it follows. Until
  2026-09-11 the only in-project reference was the 4-node enumeration in §16 ("all 15
  orbits exactly identical"); nothing checked columns 15–72.
- **Established by this project since 2026-09-11** (`verify_pipeline.py` step 2c-5, on
  every run): a first-principles enumeration of the connected 5-node graphs gives 21
  isomorphism classes and 58 automorphism orbits; on four generated fixtures (sparse and
  dense Erdős–Rényi, Holme–Kim, Watts–Strogatz; every one of the 58 reference orbits
  realised on at least one) ORCA's 58 columns equal the enumerated per-node counts **under a
  single column bijection shared by every node of every fixture**, with total orbit
  memberships equal; three labels are pinned by structure (K5 → orbit 72; K5 minus an edge
  → 70/71; the induced 5-path → 15/16/17) and agree with ORCA's convention; and the
  radius tag of all 73 node orbits equals an exact eccentricity derivation
  (`_calib.derive_node_radius`). Independently, `vendor/orca.exe` reproduces a fresh build
  of `vendor/orca.cpp` byte-for-byte (`vendor/BUILD_20260911.md`), and the binary now
  fails loudly rather than emitting an empty file.
- **Still inherited after that gate:** the identity of the other 55 columns *by label*. The
  bijection proves each ORCA column is *some* orbit's exact count on the fixtures, and the
  three pins fix the convention at its anchors, but which of two orbits with similar
  fixture profiles carries which index is taken from Pržulj's table. For this study that
  distinction is immaterial — the model consumes the 58 columns as an unlabelled block and
  the radius tags are derived from the orbit *structure*, which the bijection does pin —
  but any sentence naming an individual 5-node orbit by number rests on the inherited
  numbering. Also inherited: correctness on graphs larger than the 16–30-node fixtures,
  which the gate does not exercise.

---

## Phase 6.5 L2 — local iterative metrics and the comparison being tested

Zhang, Hanjalic and Wang (2024) already study nodal influence through iterative
local metrics, vary infection-rate multiples and compare random forests with
ridge regression. Those choices are prior work, not new contributions of this
project. Their NWC counts ordinary walks; L2's non-backtracking counts exclude
immediate edge reversals and are a related baseline rather than a reproduction.
Their H-index order1 is degree, whereas this repository calls degree order0:
the existing `h_index_r` recursion corresponds to their order r+1. See the
[primary-source comparison](reference/prior_work.md#zhang-correction-to-the-attached-plan).

The relevant earlier work includes Lü et al. (2016) on the iterative H-operator
linking degree and coreness, Kitsak et al. (2010) on k-shell influence and seed
separation, and Guilbeault–Centola (2021) on reinforcement in complex contagion;
their primary sources are linked in the [reference note](reference/prior_work.md#other-required-citations).
The project evaluates explicit radius conventions, tolerance and seed stability,
multiple targets, estimator sensitivity, buffered validation and target noise.
That combination describes this protocol; the targeted literature check does
not establish global novelty or a population information ceiling.

L2 compares length3 non-backtracking walks with H-index3 and the RF node tier
at radius2 on the same full-draw spread_mean target. Under the ball-plus-boundary-
degrees convention, NB length3 uses radius2 and H-index3 uses radius3. Their
standalone comparison is consequently descriptive across unequal observation
radii. The reconstruction gate requires model fitting and remains separate
from these zero-fit scores. Predictions and scoring definitions are in the
[preregistration](prereg/prereg_phase6_5_lanes.md).

### L2 standalone results, 2026-09-14

| Network | NB length3 tau | H-index3 tau | RF node radius2 mean tau |
|---|---:|---:|---:|
| ca-GrQc | 0.747899 | 0.770837 | 0.942144 |
| ca-HepTh | 0.820623 | 0.760281 | 0.945688 |
| p2p-Gnutella08 | 0.876171 | 0.763015 | 0.885393 |
| email-Eu-core | 0.959704 | 0.902486 | 0.959346 |
| facebook_combined | 0.862449 | 0.726746 | 0.955370 |

The predicted ±0.02 H-index band failed on all five networks. The prediction
that NB3 stays below RF everywhere also failed: four networks satisfy it, but
email has a tiny NB advantage of 0.0003584. This is a strict-sign verdict,
not evidence of statistical superiority. NB3 beat RF on neither ca-GrQc nor
p2p, so the registered two-network counter did not fire. The later reconstruction
gate and any incremental fitting experiment remain unscored. Complete arrays,
NB1/NB2 scores and source/input provenance are under
`results/phase6_5_nonbacktracking/`; the scored addendum preserves the original
predictions and explicitly discloses the unequal H-index observation radius.

## Phase 6.5 L3 — truncated local IC, scored 2026-09-13

The zero-training predictor E(r) averages cascade sizes truncated at r live steps
on simulation draws 0–1999; its target averages full sizes on draws 2000–3999.
All 4,000 full-size draws reproduce the existing cache exactly on each of the five
networks. E(r)'s Kendall tau increases from radius 1 to 3 on all five. Its r=3 tau
is 0.878247 (ca-GrQc), 0.875394 (ca-HepTh), 0.792533 (p2p), 0.948937 (email), and
0.793972 (facebook). E(1) beats the RF node-tier r=1 score on none of the three
registered sparse networks, falsifying that prediction.

The registered counter, E(3) at least matching the structural RF on four networks,
does not fire (zero of five). The prediction of an RF advantage of at least 0.03
at both r=2 and r=3 on every network is also falsified: email's r=3 gap is only
0.019719. The other four networks satisfy both margins. Cached RF scores use
full-draw targets, so this is a descriptive comparison with different target-noise
protocols, not an isolated measurement of learner advantage. Radius-zero E is tied
and its tau is unscored. Complete scores, feature-coverage columns and provenance
are in `results/phase6_5_local/`; the registered predictions and scored addendum
are in [the Phase 6.5 preregistration](prereg/prereg_phase6_5_lanes.md).

### Phase 6.5 L4: individually strong seeds can overlap heavily (2026-09-13)

Selecting 50 nodes by training-half Monte Carlo individual spread achieved only
49.8%, 53.9%, 79.6%, 89.9% and 49.4% of greedy's held-out set spread on ca-GrQc,
ca-HepTh, p2p-Gnutella08, email-Eu-core and facebook_combined respectively.
The Facebook prediction (<95%) held; the p2p prediction (>98%) failed. Greedy
selected by exact component-union marginal gains on 2,000 training draws; all
policies used the same separate 2,000 evaluation draws. All 4,000 component-size
columns reproduced the cached simulation exactly on each network.

For both RF node and structural tiers, radius zero already reached 98% of that
tier's radius-three set spread on every network, with agreement across all ten
fit seeds. This is saturation relative to the RF policy's own reference, not
near-optimal set selection. Greedy is itself a sampled-objective heuristic,
not a certified optimum. RF labels include evaluation draws and therefore
retain target-noise reuse; individual-top-sigma means use the training half.
Degree-discount reached 86.8%–99.2% of greedy, reported descriptively.

The registered stop condition (individual-top-sigma/greedy >=98% everywhere)
did not fire on any network. Full policy curves, selected nodes, paired-draw
spreads and hash provenance are in `results/phase6_5_seed_sets/`; the complete
table and verdicts are in the [scored preregistration](prereg/prereg_phase6_5_lanes.md).

# PART VIII — GLOSSARY

> **Positioning addendum, 2026-09-12:** the new lane plan is registered in
> `prereg/prereg_phase6_5_lanes.md`. The source-checked comparison with Zhang (2024), missing
> H-index/k-shell/complex-contagion citations and estimator-family caveats are in
> [the prior-work note](reference/prior_work.md). In particular, infection-rate
> variation and qualitative learner comparison are already prior work. Our empirical
> P(r) measures performance of fitted estimators under the declared observation
> convention (ball plus boundary degrees), not the true information ceiling. The
> connection to predictive V-information is conceptual; no V-information estimate
> has been computed. The L3/L4 results added on 2026-09-13 appear immediately above;
> other lane predictions remain unscored until their validated runs complete.

Every technical term and mathematical expression used in this document, in plain language.

## 27. Network structure

| Term | Plain meaning |
|---|---|
| **Node** (vertex) | One entity in the network — a person, author, or account. |
| **Edge** (link, tie) | A connection between two nodes, such as a friendship. |
| **Undirected** | Edges have no direction: if A knows B, then B knows A. |
| **Directed** | Edges point one way, like a follow. We symmetrize these into undirected. |
| **Degree**, k | How many direct connections a node has. |
| **Neighbour** | A node directly connected to you. |
| **Hop** | One step along an edge. Two hops = a friend of a friend. |
| **r-ball** | Everything within r hops of a node. |
| **Shell at distance r** | Nodes at *exactly* r hops — the ring, not the filled circle. |
| **Ego-network** | A node plus its neighbours plus all edges among them. |
| **Ego / alter** | The ego is the node at the centre; alters are its neighbours. |
| **Adjacency matrix**, A | A table where entry (i,j) is 1 if i and j are connected, 0 otherwise. |
| **Sparse matrix** | A storage format that records only the non-zero entries; essential when most pairs are unconnected. |
| **Path** | A route from one node to another along edges. |
| **Shortest path** | The route using the fewest edges. |
| **Connected component** | A group of nodes all reachable from one another. |
| **Largest connected component (LCC)** | The biggest such group; we restrict analysis to it. |
| **Self-loop** | An edge from a node to itself. Removed. |
| **Multi-edge** | The same pair connected more than once. Collapsed to one. |
| **Triangle** | Three nodes all mutually connected. |
| **Clustering coefficient**, C | Of all pairs of your neighbours who *could* know each other, the fraction who do. |
| **Density** | Actual edges divided by possible edges in a group. |
| **Assortativity** | Whether nodes tend to connect to others of similar degree. |
| **Structural hole** | A gap between two of your contacts who do not know each other — a brokerage opportunity. |
| **Effective size** (Burt) | Your number of *non-redundant* contacts: neighbours who bring genuinely new reach. |
| **Boundary porosity** | How many edges lead out of your ego network — how "leaky" your local view is. |
| **Growth ratio** | How much bigger each successive shell is than the last; how fast your reach expands. |
| **Hub** | A node with unusually high degree. |
| **k-core / coreness** | The deepest densely-connected layer a node survives in when you repeatedly peel off low-degree nodes. |
| **Graphlet** | A small connected subgraph (3–5 nodes) — a structural motif. |
| **Orbit** | A distinct structural position within a graphlet. |

## 28. Centrality measures

| Term | Plain meaning | Local or global? |
|---|---|---|
| **Degree centrality** | How many connections you have. | Local |
| **Betweenness centrality**, b(v) | The fraction of all shortest paths that run through you. Measures brokerage. | **Global** |
| **Closeness centrality** | How close you are on average to everyone else. | **Global** |
| **PageRank** | You matter if people who matter link to you; defined recursively. | **Global** |
| **Eigenvector centrality** | Same recursive idea as PageRank, different formulation. | **Global** |
| **Katz centrality** | Importance from all paths reaching you, with longer paths counting less. | **Global** |
| **Harmonic centrality** | A closeness variant that copes with disconnected graphs. | **Global** |
| **Ego-betweenness** | Betweenness computed *only inside* your own ego network. | **Local** |
| **H-index of a node** | Apply the h-index idea to your neighbours' degrees instead of citation counts. | Local (per order) |
| **Collective Influence**, CI_ℓ | Your degree minus one, times the same quantity summed over the shell at distance ℓ. | Local |

## 29. Spreading processes

| Term | Plain meaning |
|---|---|
| **Cascade** | One run of something spreading through the network. |
| **Seed** | The node where the spread starts. |
| **Independent Cascade (IC)** | Each newly activated node gets one attempt to activate each neighbour, succeeding with probability p. |
| **SIR** | Susceptible–Infected–Recovered: an epidemic model where infected nodes eventually recover and stop spreading. |
| **Linear Threshold (LT)** | An alternative model where a node activates once *enough* of its neighbours have. |
| **Transmission probability**, p or β | The chance that one contact passes the infection along. |
| **Reached set**, R(i) | The set of nodes eventually activated when i is the seed. |
| **Expected spread**, σ(i) | The average size of R(i) over many runs. |
| **Epidemic threshold**, β_c | The tipping point: below it outbreaks die out, above it they can engulf a large fraction of the network. |
| **Criticality** | Being at or near the tipping point, where behaviour is most variable and hardest to predict. |
| **Percolation** | Randomly keeping or deleting edges and asking what stays connected. |
| **Bond percolation** | The edge-deletion version; mathematically identical to IC with fixed p. |
| **Live-edge graph** | One sample of which edges successfully transmit. |
| **Mean-field estimate** | A simplified threshold formula that ignores network correlations; inaccurate on sparse graphs. |
| **Ignition probability** | The chance a cascade exceeds some large size instead of fizzling. |

## 30. Linear algebra and spectra

| Term | Plain meaning |
|---|---|
| **Eigenvalue** | A number describing how much a matrix stretches a particular direction. |
| **Leading eigenvalue**, λ₁ | The largest one; it governs the long-run behaviour of repeated application. |
| **Eigenvector** | The direction associated with an eigenvalue. |
| **Spectral radius** | The magnitude of the leading eigenvalue. |
| **Localisation** | When the leading eigenvector concentrates on a few nodes (usually hubs), making estimates unreliable. |
| **Non-backtracking walk** | A walk that never immediately steps back where it came from. |
| **Hashimoto / non-backtracking matrix**, B | The matrix encoding those non-reversing steps, defined on directed edges. |
| **Ihara-Bass identity** | A result letting you get B's leading eigenvalue from a smaller 2n × 2n matrix. |
| **Power iteration / Arnoldi** | Numerical methods for finding the leading eigenvalue of a large sparse matrix. |
| **Identity matrix**, I | Ones on the diagonal, zeros elsewhere; the "do nothing" matrix. |
| **Degree diagonal**, D | A matrix with each node's degree on the diagonal. |

## 31. Machine learning

| Term | Plain meaning |
|---|---|
| **Feature** | One input number describing a node. |
| **Target** | The value we are trying to predict. |
| **Regression** | Predicting a number (rather than a category). |
| **Random forest** | A model that averages many decision trees; a strong, cheap general-purpose regressor. |
| **Training / test set** | Data the model learns from, versus data used to judge it. |
| **k-fold cross-validation** | Split into k groups; train on k−1 and predict the rest, rotating so every node is predicted once. |
| **Out-of-fold prediction** | A node's prediction made by a model that never saw it during training. |
| **Overfitting** | Memorising the training data instead of learning a general pattern. |
| **Leakage** | Accidentally letting the answer into the inputs; produces excellent, meaningless results. |
| **Permutation importance** | Shuffle one feature column and see how much performance drops; measures that feature's contribution. |
| **Baseline** | A simple rival method your approach must beat to be worth anything. |
| **Heteroscedastic** | Spread that changes with the size of the value — big means have big variance. |
| **Residual** | What is left over after subtracting the expected part. |
| **Monte Carlo** | Estimating a quantity by random simulation repeated many times. |
| **Standard error**, SE | How uncertain an average is, given how many samples produced it. |

## 32. Evaluation metrics

| Term | Plain meaning |
|---|---|
| **Kendall's τ** | Over all pairs, did we put them in the same order as the truth? +1 perfect, 0 random. |
| **Concordant / discordant pair** | A pair ranked the same way as truth / the opposite way. |
| **Spearman correlation** | Rank correlation; similar spirit to τ, computed differently. |
| **Precision@k** | Of the true top k, how many did our top k catch? |
| **RMSE / MAE** | Average size of numerical error; misleading on skewed targets, so kept secondary. |
| **R²** | Fraction of variance explained. Secondary here. |
| **Coefficient of variation (CV)** | Standard deviation divided by mean — relative variability, comparable across scales. |
| **Skew** | Asymmetry of a distribution; influence is heavily right-skewed. |

## 33. Project-specific terms

| Term | Plain meaning |
|---|---|
| **Local feature** | Computable from a bounded neighbourhood only — the only thing allowed as model input. |
| **Global measure** | Requires the whole graph; may be a target or a rival baseline, never an input. |
| **Locality horizon**, r\*(ε) | The smallest radius whose performance reaches (1−ε) of the best we measured. |
| **Locality budget** | The general question of how much neighbourhood you can afford to look at. |
| **Locality gap**, g_r(v) | The fraction of a node's influence that comes from structure beyond r hops. |
| **Depth vs richness** | Looking further out (more hops) versus describing the same view more elaborately (more tiers). |
| **Tier** | Whether a feature describes a node, its edges, or small subgraphs it sits in. |
| **Hop tag** | The smallest radius at which a feature can be computed. |
| **Depth = radius** | An r-layer graph neural network sees exactly the r-ball, so "how far to look" and "how deep a network" are the same question. |
| **Failure atlas** | The profile of nodes local prediction gets most wrong, and what they have structurally in common. |
| **Hidden influencer** | A node whose true influence is high but which local features under-predict. |
| **Archetype node** | A node scoring very differently on two influence definitions — e.g. strong bridge, weak spreader. |
| **Provenance record** | The log of exactly what preprocessing was applied to a network. |

## 34. Mathematical notation

| Symbol | Meaning |
|---|---|
| n | Number of nodes |
| m | Number of edges |
| k_i | Degree of node i |
| ⟨k⟩ | Mean degree across all nodes |
| ⟨k²⟩ | Mean of squared degree; large when hubs are present |
| A | Adjacency matrix |
| B | Non-backtracking (Hashimoto) matrix |
| D | Degree diagonal matrix |
| I | Identity matrix |
| λ₁ | Leading (largest) eigenvalue |
| σ_st | Number of shortest paths between s and t |
| σ_st(v) | How many of those pass through v |
| b(v) | Betweenness centrality of v |
| σ(i) | Expected spread when i is the seed |
| σ̂(i) | Our Monte Carlo estimate of it |
| R(i) | The set of nodes reached from seed i |
| \|R(i)\| | The size of that set |
| E[ · ] | Expected value — the long-run average |
| p, β | Transmission probability |
| β_c | Critical threshold |
| μ | Recovery probability in SIR |
| M | Number of simulation runs |
| s | Sample standard deviation |
| SE | Standard error |
| r | Radius, in hops |
| r\*(ε) | Locality horizon at tolerance ε |
| ε | Tolerance — how far below the ceiling we accept |
| P(r) | Best performance achievable using only the r-ball |
| τ | Kendall's tau |
| ρ | Fraction of edges deleted (robustness experiments) |
| g_r(v) | Locality gap of node v at radius r |
| Δ(v) | Rank difference — used for both archetypes and failures |
| CI_ℓ(i) | Collective Influence of i at radius ℓ |
| h⁽ⁿ⁾(i) | Order-n H-index of node i |
| H( · ) | The H-operator |
| Σ | Sum over the indicated range |
| ∈ | "is a member of" |
| ⊆ | "is a subset of" |
| ∩ | Set intersection — elements in both |
| ≠ | "not equal to" |
| ≥, ≤ | "greater/less than or equal to" |
| → | "maps to" or "step to" |

---

# PART IX — RISKS AND OPEN QUESTIONS

| Risk | Status / mitigation |
|---|---|
| Three networks is a small corpus | **Partly addressed (2026-08-27).** Now five: ca-HepTh and facebook_combined added as a matched pair, one per arm. Three findings were revised and one reversed outright, so the concern was well founded. Five is still small; the synthetic corpus (§14) remains unswept |
| Single-graph CV is not true transfer | Still open. Train and test on separate networks as the corpus grows |
| Depth-beats-richness may reflect a thin subgraph tier | **Resolved, and it amended the finding twice.** With genuinely independent edge structure AND graphlet orbits, the subgraph tier helps the dynamical targets on **all five** networks, significantly, at r=1 on ten of ten (network, target) pairs — traced by ablation to the 4-node to 5-node step. Depth still dominates by roughly 9:1 on Gnutella `spread_mean` at r=1. Both remaining sub-questions are now answered: 5-node NODE orbits are a decisive win, 5-node EDGE orbits are not (`analyse_edge5.py`, largest gain anywhere +0.0020, several significantly negative) |
| High correlation mistaken for redundancy | **Caught.** `orbit_04` is 0.99 rank-correlated with existing columns and still gives a ten-sigma gain. The effective-dimensionality figure measures monotone redundancy only; it is not a test of predictive redundancy, and §20 says so |
| Feature count mistaken for information | **Fixed.** `analyse_features.py` checks closed-form identities to machine precision, reports effective dimensionality, and tests each tier against the tiers below it. `verify_pipeline.py` §6c carries a standing guard |
| A mechanistic feature might beat structural proxies | **Tested, and it does not.** The `dynamic` tier (a truncated local percolation estimate, assuming knowledge of p) adds at most +0.0006 over the full structural tier on any network or target — within noise everywhere |
| The `dynamic` tier assumes the observer knows p | Isolated on its own rung of the ladder and excluded from every headline curve, so no general claim can depend on it silently |
| r\* is sensitive to ε | Report the whole curve and marginal gains, not a single number. r\*(ε) is now also reported with its **seed stability** — how many of the ten seeds agreed |
| Volatility result may be the mean in disguise | **Resolved by running the control.** `spread_resid` is swept, and the answer differs by network: predictable on ca-GrQc, essentially not on email-Eu-core |
| Results indistinguishable from noise | **Partly addressed.** Ten seeds quantify seed variability; A7 quantifies conditional target noise. Phase 6 measures dynamic-tier paired gains, but headline structural-tier stars and total uncertainty remain unresolved (§26h, §26j). |
| Cross-network comparison confounded by p | **Fixed.** All five networks run at p = 1.5 × β_c and 4,000 sims. email-Eu-core previously ran at 1.2 × |
| Hop tags misdescribe what a radius grants | **Fixed.** Ten neighbour-structure features moved from hop 1 to hop 2; see §5 |
| Betweenness result is a tie-breaking artefact | **Disclosed and quantified.** See §22 |
| Cost/quality frontier built on a broken cost model | **Fixed.** `feature_cost` sums the timed extraction groups a cell actually used |
| Cascade estimates too noisy | Standard-error report built into every run; all five networks pass |
| Feature leakage | `assert_no_leakage` runs on every grid cell, not once |
| Angle 4 conflates locality with distribution shift | **Resolved.** Run as a separate line: training on a different damage draw at the same rho recovers up to +0.45 tau (Gnutella, rho=0.5). The collapse was shift, not fragility. Recomputation still wins for betweenness by a modest stable margin; spreading is unaffected because there was no shift to fix |
| Angle 4 damage model is too gentle | Uniform edge deletion is *missing observation*, chosen deliberately over adversarial removal because targeted deletion would rig the comparison in our favour. A targeted variant is worth running, clearly labelled as a different question |
| Angle 4 result read off the full tau only | **Controlled.** Every comparison is reported over all nodes and over the nonzero subset. For betweenness the two point opposite ways, and the doc says so |
| Results not reproducible across rebuilds | **Fixed, with a stated limit.** `environment.yml` pins versions and the BLAS implementation; `cache_meta_<tag>.json` records the versions each result was produced under. Reproducible to 5e-08 in τ at `n_jobs=-1`, bit-exact at `n_jobs=1` — see §16 |
| Failure atlas could rediscover regression to the mean | **Fixed.** The residual is standardised within bins of true influence, removing both the shrinkage level and the non-constant scale. The report prints the median true percentile of each tail as the check |
| Atlas tails might just be "the noisy periphery" | **Caught and fixed.** They were, before standardising — both tails profiled identically. The directional under-vs-over contrast is now reported alongside, and it is the table that carries the finding |
| Directional-blind-spot / saturation correspondence rests on three points | Open. The generated corpus (§14) is what turns it into a measured relationship |

**Open decisions:**

- Which edge-probability convention to headline (weighted cascade is the most defensible default for social networks; uniform is what the percolation shortcut supports).
- Whether to add a threshold model (Linear Threshold) as a second dynamics arm.
- When to bring synthetic generation back in for the criticality sweep.
- ~~Whether 5-node graphlets justify their cost over 4-node.~~ ~~**Answered: yes.**~~
  **Re-opened 2026-09-12 by Claude Opus 5.** The "yes" below rested on six 5-node orbits
  tagged hop 1 that reach two hops (P1-01). On the corrected registries the 5-node step at
  radius one flags **0 of 20** cells across five networks and four targets (§26k.3,
  superseding block); at r=1 the 5-node orbits add nothing to the 4-node ones. Whether they
  justify their cost at r ≥ 2, where those six orbits now sit, has not been ablated and is the
  open question. The original text follows, retained as written:
  **Answered: yes.** At radius 1 the five 4-node hop-1 orbits contribute nothing to any target, while the seventeen extra 5-node hop-1 orbits contribute +0.035 on ca-GrQc spread volatility and +0.013 on spread mean. Four-node graphlets are not expressive enough to describe an ego network. Cost is 0.7 s on the sparse networks and 15 s on the dense one — negligible against the model fits. 5-node EDGE orbits (204 columns) remain untested and are off by default. **Confirmed on five networks and four targets, 2026-09-11 by Claude Opus 5 (§26k.3):** the 4-node step flags 0 of 20 cells, the 5-node step 17 of 20. The answer stands, with two qualifications the three-network run could not see — the non-orbit subgraph step is *not* uniformly worthless (it flags on both networks' `betweenness`), and the 5-node step is negative on email-Eu-core/`betweenness`.

---

*End of study document.*
