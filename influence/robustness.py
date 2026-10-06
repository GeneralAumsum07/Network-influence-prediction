"""
robustness.py
=============
Damaged views of a network, for Angle 4.

THE QUESTION
------------
Real networks are observed, not given. Edges are missed, links go unreported,
crawls terminate early. So: if you only get to see a damaged version of the
graph, are you better off

    (a) computing LOCAL features on the damaged graph and feeding them to a
        model learned from good data, or
    (b) recomputing the GLOBAL score directly on the damaged graph?

(b) is what anyone would do by default. It is also the honest rival, because it
is not obviously worse - it uses the same broken data, just differently. The
claim worth testing is that a local model degrades more gracefully, because a
bounded neighbourhood is less sensitive to a missing edge on the far side of
the graph than a shortest-path computation that routes through it.

WHY THIS MODULE SKIPS THE LCC STEP, DELIBERATELY
------------------------------------------------
The preprocessing protocol (decision 2) restricts every network to its largest
connected component. That is right for constructing a corpus and wrong here.

Deleting edges fragments the graph. If we then took the LCC, the damaged graph
would have FEWER NODES than the clean one, and there would be no way to compare
a node's predicted rank against its true rank - the two vectors would not even
be the same length. Worse, the nodes dropped would be exactly the ones the
damage hurt most, so the comparison would silently exclude its own hardest
cases and flatter every method equally.

So `delete_edges` keeps all n nodes, indices unchanged, isolated vertices and
all. Every feature in features.py already handles a degree-0 node by returning
zeros, and that is the correct answer for a node whose every edge was removed:
a local observer there genuinely sees nothing.

This is a deliberate, documented departure from the protocol, confined to this
module, and it is the only place in the project where a Network is built
without the LCC restriction.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .preprocessing import Network


def delete_edges(net: Network, rho: float, seed: int = 0) -> Network:
    """
    Uniformly delete a fraction `rho` of edges, keeping every node and index.

    Uniform deletion models MISSING OBSERVATION - each link independently fails
    to be recorded. That is the right null for an incompletely observed
    network, and it is deliberately not adversarial: removing the highest-
    betweenness edges would damage a shortest-path score far more than a local
    one and would rig the comparison in our favour. A targeted variant is worth
    running later as a separate, clearly-labelled experiment.

    Returns a Network with identical node indexing, so its features line up
    row-for-row with the clean graph's targets.
    """
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must be in [0, 1)")

    coo = sp.triu(net.adj, k=1).tocoo()
    eu, ev = coo.row, coo.col
    rng = np.random.default_rng(seed)
    keep = rng.random(len(eu)) >= rho
    eu, ev = eu[keep], ev[keep]

    n = net.n
    rows = np.concatenate([eu, ev])
    cols = np.concatenate([ev, eu])
    adj = sp.csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)),
                        shape=(n, n))
    adj.sort_indices()
    degree = np.diff(adj.indptr).astype(np.int64)
    nbrs = [adj.indices[adj.indptr[i]:adj.indptr[i + 1]] for i in range(n)]

    prov = dict(net.provenance)
    prov.update({"damaged_from": net.name, "rho": float(rho),
                 "damage_seed": int(seed),
                 "edges_before": int(net.m), "edges_after": int(len(eu)),
                 "lcc_restriction_skipped": True,
                 "isolated_nodes": int((degree == 0).sum())})

    return Network(name=f"{net.name}_rho{rho:g}_s{seed}", adj=adj, nbrs=nbrs,
                   degree=degree, original_ids=net.original_ids.copy(),
                   provenance=prov)


def align_features(damaged_X, clean_columns: list[str]):
    """
    Force a damaged graph's feature table onto the clean graph's columns.

    Necessary because feature extraction drops any orbit that is identically
    zero across the graph - and which orbits vanish depends on the graph. A
    damaged network can therefore produce a table with different columns, and
    a model trained on the clean columns would silently receive the wrong
    matrix. Missing columns are filled with zero, which is the honest value:
    that structure was not observed.
    """
    import pandas as pd
    out = damaged_X.reindex(columns=clean_columns)
    return out.fillna(0.0)
