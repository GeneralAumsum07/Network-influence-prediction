"""Pure contract helper for the Phase 6 radius-one structural ablation.

Created 2026-09-10 by Claude Opus 5 for Phase 6 Task 5 (r=1 ablation scope gap).
Specification: docs/phase6_r1_ablation_implementation_brief.md, as corrected by
docs/phase6_r1_ablation_readiness_addendum.md.

WHY THIS EXISTS
---------------
`results/RESULTS_r1_subgraph_ablation.txt` covers only three of the five
networks and was produced from an older feature table, yet the study's prose
generalises about structural expressive power across all five. That gap is the
whole point of this lane: the existing numbers cannot support the sentence they
are cited for.

The historical `cache_oof_<network>.npz` endpoints cannot close it either. They
hold 640 bare `target|radius|richness|seed` arrays with no embedded manifest,
no selected-column list or hash, no cache input hash, no target-objective id,
no fold digest and no estimator hash. Names and a matching column count are not
provenance. The root archive's `betweenness` endpoint also belongs to the RAW
objective, while this design reports `rf_log1p`. So every cell here is a fresh,
provenance-bound fit.

WHAT LIVES HERE, AND WHAT DELIBERATELY DOES NOT
-----------------------------------------------
This module is pure: feature-set construction, objective routing, fold
digesting, key construction and hashing. It performs no I/O and fits no model,
so `verify_r1_ablation.py` can exercise the entire scientific contract without
touching the five-network corpus. The runner and analyzer own all I/O.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

# --- The fixed experiment grid. Order matters: it fixes the sort order of the
# --- cell table and the contrast table, so results are diffable across runs.
TARGETS: tuple[str, ...] = ("spread_mean", "spread_cv", "spread_resid", "betweenness")
SET_IDS: tuple[str, ...] = ("node_edge", "plus_nonorbit_subgraph", "plus_orbit_lt15",
                            "full_r1_structural")
SEEDS: tuple[int, ...] = tuple(range(10))
NETWORKS: tuple[str, ...] = ("ca-GrQc", "ca-HepTh", "email-Eu-core", "facebook_combined",
                             "p2p-Gnutella08")

RADIUS = 1
N_SPLITS = 5

# The two subgraph-tier features that are not graphlet orbits. Set 2 isolates
# them so that "subgraph tier helps" cannot be silently credited to orbits.
NONORBIT_SUBGRAPH: tuple[str, ...] = ("ego_betweenness", "triangle_count")

# Node-orbit index below which an orbit joins Set 3 rather than Set 4. 15 is the
# first 5-node orbit index in ORCA's numbering, so this splits "4-node and
# smaller" from "genuinely 5-node" without hardcoding a name list.
ORBIT_INDEX_SPLIT = 15

# Only a NODE orbit is named `orbit_<digits>_...`. `eorbit_` names are EDGE-tier
# members of the common baseline; classifying one as a node orbit would move
# nine columns out of Set 1 and corrupt every contrast.
_NODE_ORBIT_RE = re.compile(r"^orbit_(\d+)_")

_VALID_TIERS = frozenset({"node", "edge", "subgraph", "dynamic"})


class R1ContractError(ValueError):
    """Raised when the R1 feature/objective contract cannot be satisfied exactly."""


# ---------------------------------------------------------------------------
# Feature-set construction
# ---------------------------------------------------------------------------

def select_r1_sets(features: pd.DataFrame, registry: pd.DataFrame) -> dict[str, list[str]]:
    """Build the four nested radius-one feature sets, in registry row order.

    Registry row order is preserved rather than sorted, because the column order
    handed to the forest is part of the run's identity: two orderings of the
    same columns are the same information but not the same fitted model, and the
    cell records hash the ordered list.

    Every failure mode below is raised rather than warned. A silently wrong set
    membership produces a plausible number credited to the wrong rung of the
    ladder, which is the exact failure this project has already been bitten by.
    """
    for column in ("feature", "hop", "tier"):
        if column not in registry.columns:
            raise R1ContractError(f"registry lacks required column {column!r}")

    available = set(features.columns)
    rows = registry[registry["hop"] <= RADIUS]

    node_edge: list[str] = []
    nonorbit_subgraph: list[str] = []
    orbit_low: list[str] = []
    orbit_high: list[str] = []
    seen: set[str] = set()

    for name, tier in zip(rows["feature"], rows["tier"]):
        if tier not in _VALID_TIERS:
            raise R1ContractError(f"unknown tier {tier!r} for feature {name!r}")
        if tier == "dynamic":
            # Dynamic features are simulation-derived, not structural; they are
            # outside this ablation's ladder entirely.
            continue
        if name in seen:
            raise R1ContractError(f"duplicate feature in registry: {name!r}")
        seen.add(name)
        if name not in available:
            raise R1ContractError(f"registry feature {name!r} is absent from the feature table")

        if tier in ("node", "edge"):
            node_edge.append(name)
            continue

        # tier == "subgraph": split into the three subgraph rungs.
        match = _NODE_ORBIT_RE.match(name)
        if match is None:
            if name.startswith("orbit"):
                # `orbit`-prefixed but unparseable: refuse rather than guess a rung.
                raise R1ContractError(f"malformed node-orbit name: {name!r}")
            nonorbit_subgraph.append(name)
        elif int(match.group(1)) < ORBIT_INDEX_SPLIT:
            orbit_low.append(name)
        else:
            orbit_high.append(name)

    sets = {
        "node_edge": list(node_edge),
        "plus_nonorbit_subgraph": node_edge + nonorbit_subgraph,
        "plus_orbit_lt15": node_edge + nonorbit_subgraph + orbit_low,
        "full_r1_structural": node_edge + nonorbit_subgraph + orbit_low + orbit_high,
    }

    # Nesting is the premise of a paired ladder: each contrast must add columns
    # and remove none, or "gain" does not mean what the report says it means.
    for lower, higher in zip(SET_IDS, SET_IDS[1:]):
        if sets[higher][:len(sets[lower])] != sets[lower]:
            raise R1ContractError(f"set {higher!r} is not a prefix-extension of {lower!r}")

    return sets


def assert_full_set_matches_select_features(sets: dict[str, list[str]],
                                            features: pd.DataFrame,
                                            registry: pd.DataFrame) -> None:
    """Cross-check Set 4 against the project's own selector.

    Set 4 is, by definition, every hop<=1 node/edge/subgraph feature. The
    pipeline already has a function that computes exactly that. Deriving the set
    twice by different routes and requiring agreement is what stops a private
    reimplementation from quietly drifting from the published one.
    """
    from influence.features import select_features

    expected = select_features(features, registry, max_hop=RADIUS,
                               tiers=("node", "edge", "subgraph"))
    if sorted(sets["full_r1_structural"]) != sorted(expected):
        raise R1ContractError(
            "full_r1_structural disagrees with select_features(max_hop=1, "
            f"tiers=(node,edge,subgraph)): {len(sets['full_r1_structural'])} vs {len(expected)}")


# ---------------------------------------------------------------------------
# Objective routing
# ---------------------------------------------------------------------------

def objective_for(target: str, rf_n_jobs: int) -> tuple[str, Callable[[int], object]]:
    """Return `(objective_id, factory)` for one target at a bounded worker count.

    Two constraints collide here, which is why this is an R1-only factory rather
    than a reuse of `influence.estimators`:

    - `make_rf` / `make_rf_log1p` hard-code `n_jobs=-1`, and
      `out_of_fold_predictions` has no `n_jobs` parameter, so neither can be
      asked for the bounded 1/4/8 pilot the readiness addendum requires.
    - Those factories must not be edited: 3,200 published cells came from that
      exact construction, and changing it invalidates them silently.

    So this rebuilds the SAME pinned model -- 120 trees, min_samples_leaf=2 --
    with an explicit inner worker count, and leaves the published path alone.

    betweenness gets `rf_log1p`: its skew runs 4.77-28.88, squared error spends
    its budget on the few enormous nodes, and Kendall tau is invariant to
    monotone transforms of the ground truth -- so training on log1p(y) while
    scoring against untransformed y is a better-conditioned objective, not an
    easier test.
    """
    if target not in TARGETS:
        raise R1ContractError(f"unknown target {target!r}")
    if not isinstance(rf_n_jobs, int) or isinstance(rf_n_jobs, bool) or rf_n_jobs < 1:
        raise R1ContractError(f"rf_n_jobs must be a positive int, got {rf_n_jobs!r}")

    def make_bounded_rf(seed: int) -> RandomForestRegressor:
        return RandomForestRegressor(n_estimators=120, n_jobs=rf_n_jobs,
                                     random_state=seed, min_samples_leaf=2)

    if target == "betweenness":
        def make_bounded_rf_log1p(seed: int) -> TransformedTargetRegressor:
            # expm1 on the way out is a no-op for tau (strictly increasing) but
            # keeps rmse in the target's own units.
            return TransformedTargetRegressor(regressor=make_bounded_rf(seed),
                                              func=np.log1p, inverse_func=np.expm1)
        return "rf_log1p", make_bounded_rf_log1p

    return "rf", make_bounded_rf


# ---------------------------------------------------------------------------
# Identity: folds, keys, hashing
# ---------------------------------------------------------------------------

def fold_digest(n_rows: int, seed: int, n_splits: int = N_SPLITS) -> str:
    """Hash the actual fold ALLOCATION, not merely the seed that produced it.

    Recording `seed=3` says nothing about which rows were held out; that depends
    on n_rows, n_splits, and the scikit-learn version's shuffling. Hashing the
    realised fold-owner vector means a changed split cannot masquerade as the
    same cell, which is what makes a paired within-seed contrast trustworthy.
    """
    if n_rows < n_splits:
        raise R1ContractError(f"n_rows={n_rows} is below n_splits={n_splits}")
    owner = np.empty(n_rows, dtype=np.int8)
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for index, (_, test_index) in enumerate(splitter.split(np.zeros((n_rows, 1)))):
        owner[test_index] = index
    digest = hashlib.sha256()
    digest.update(f"{n_rows}|{n_splits}|{seed}|".encode("ascii"))
    digest.update(owner.astype("<i1").tobytes())
    return digest.hexdigest()


def expected_keys(tags: tuple[str, ...] = NETWORKS) -> set[tuple[str, str, str, int]]:
    """The exact cell universe: 5 networks x 4 targets x 4 sets x 10 seeds = 800."""
    return {(tag, target, set_id, seed)
            for tag in tags for target in TARGETS for set_id in SET_IDS for seed in SEEDS}


def cell_name(tag: str, target: str, set_id: str, seed: int) -> str:
    """Canonical on-disk cell filename stem."""
    return f"{tag}__{target}__{set_id}__s{seed}"


def sort_key(tag: str, target: str, set_id: str, seed: int) -> tuple[int, int, int, int]:
    """Order cells by the declared grid order, never alphabetically."""
    return (NETWORKS.index(tag), TARGETS.index(target), SET_IDS.index(set_id), int(seed))


def canonical_sha256(value: dict | list) -> str:
    """SHA-256 over a canonical JSON rendering.

    `sort_keys` plus fixed separators means the digest depends on the content
    and not on dict insertion order or whitespace, so a record rewritten by a
    later Python version still hashes the same.
    """
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require_finite(name: str, values) -> None:
    """Reject nonfinite values explicitly.

    `experiment.evaluate` RETURNS NaN when a rank statistic is undefined; it does
    not refuse it. A NaN that reaches a cell record becomes a silently dropped
    pair in the analyzer, so it is rejected here at the boundary instead.
    """
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise R1ContractError(f"{name} contains nonfinite values")
