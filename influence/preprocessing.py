"""
preprocessing.py
================
Graph loading + the preprocessing protocol.

WHY THIS MODULE EXISTS
----------------------
Most irreproducibility in this literature comes from preprocessing, not from
algorithms. Two people run "the same" experiment on "the same" network and get
different numbers because one symmetrized the edges and the other didn't, or
one kept the disconnected fragments and the other didn't.

So we fix every one of those decisions ONCE, here, apply them identically to
every network, and log exactly what happened. The log goes in the methods
section of the writeup.

THE SIX DECISIONS (all applied by load_graph):
  1. Directedness    -> symmetrize (undirected). Stated, not silent.
  2. Largest component -> restrict to LCC.
  3. Self-loops      -> removed (they break the non-backtracking construction).
  4. Multi-edges     -> collapsed to simple edges (same reason).
  5. Weights         -> discarded entirely (we do not half-use weights).
  6. Node IDs        -> reindexed to 0..n-1, with the mapping KEPT so we can
                        always get back to the original file's IDs.

Decision 6 matters more than it looks. igraph and numpy both want contiguous
integer indices, but the raw files have arbitrary IDs with gaps. If you lose
that mapping you cannot join your results back to anything else.
"""

from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.sparse as sp


# ----------------------------------------------------------------------------
# The container we pass around everywhere else
# ----------------------------------------------------------------------------

@dataclass
class Network:
    """
    A preprocessed, undirected, simple, connected graph.

    We deliberately store the graph in TWO redundant forms because different
    operations want different shapes:

      adj  : scipy CSR sparse matrix. Fast for matrix-style work and for
             getting a node's neighbours as a contiguous slice.
      nbrs : list of numpy arrays, one per node. Fastest for the tight
             per-node loops in feature extraction and BFS.

    Both describe the same graph. Building nbrs once up front saves an enormous
    amount of time later, because the cascade simulator hits it millions of
    times.
    """
    name: str
    adj: sp.csr_matrix
    nbrs: list[np.ndarray]
    degree: np.ndarray
    # Mapping back to the source file's node labels: index i in our arrays
    # corresponds to original label original_ids[i].
    original_ids: np.ndarray
    provenance: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        """Number of nodes."""
        return self.adj.shape[0]

    @property
    def m(self) -> int:
        """Number of undirected edges."""
        return int(self.adj.nnz // 2)

    @property
    def mean_degree(self) -> float:
        return float(self.degree.mean())

    def __repr__(self) -> str:
        return (f"<Network {self.name}: n={self.n:,} m={self.m:,} "
                f"<k>={self.mean_degree:.2f}>")


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------

def load_edgelist(path: str | Path,
                  comment_chars: tuple[str, ...] = ("#", "%"),
                  name: str | None = None) -> Network:
    """
    Read a whitespace/comma separated edge list and apply the full protocol.

    Handles the usual real-world messiness: comment headers (SNAP uses '#',
    Netzschleuder uses '%'), tabs vs spaces vs commas, Windows line endings,
    and trailing weight columns (which we discard, per decision 5).
    """
    path = Path(path)
    name = name or path.stem

    raw_edges = []
    # P1-04 (Task 6 audit, Claude Opus 5, 2026-09-11): rows that fail to parse
    # used to vanish without trace, so a truncated or partly corrupted file
    # loaded as a smaller graph with a clean provenance record. They are now
    # counted, recorded as `rows_unparsed`, and warned about. Not raised on:
    # a Netzschleuder-style header line is a legitimate reason for one or two.
    n_unparsed = 0
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            # Skip blanks and comment headers.
            if not line or line[0] in comment_chars:
                continue
            # Normalise separators, then take only the FIRST TWO fields.
            # Anything beyond that is a weight or timestamp -> discarded.
            parts = line.replace(",", " ").replace("\t", " ").split()
            if len(parts) < 2:
                n_unparsed += 1
                continue
            try:
                u, v = int(parts[0]), int(parts[1])
            except ValueError:
                # Usually a header row that slipped past the comment check;
                # a corrupted region of the file takes this branch too, which
                # is why it is counted rather than ignored.
                n_unparsed += 1
                continue
            raw_edges.append((u, v))

    if not raw_edges:
        raise ValueError(f"No edges parsed from {path}")
    if n_unparsed:
        warnings.warn(f"{path}: {n_unparsed} non-comment row(s) could not be "
                      f"parsed as an edge and were skipped", stacklevel=2)

    net = build_network(raw_edges, name=name, source=str(path))
    # P1-02 (2026-09-11): bind the loaded graph to the BYTES of its source.
    # `tag` is path.stem, so before this any file with the same stem addressed
    # the same cache namespace and nothing downstream could tell. stage 2 and
    # the sweep input sidecar compare against these.
    net.provenance.update({
        "source_sha256": file_sha256(path),
        "source_bytes": path.stat().st_size,
        "rows_unparsed": n_unparsed,
    })
    return net


def file_sha256(path: str | Path) -> str:
    """SHA-256 of a file's bytes, streamed; the identity every cache binds to."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_network(raw_edges: list[tuple[int, int]],
                  name: str = "graph",
                  source: str = "in-memory") -> Network:
    """
    Apply decisions 1-6 to a raw edge list and return a Network.

    Every step records what it removed, so the provenance dict is a complete
    audit trail of what we did to the input.
    """
    edges = np.asarray(raw_edges, dtype=np.int64)
    n_raw_edges = len(edges)

    # --- Decision 3: drop self-loops -----------------------------------
    # A self-loop makes the non-backtracking operator ill-defined and inflates
    # degree without adding a spreading path.
    keep = edges[:, 0] != edges[:, 1]
    n_self_loops = int((~keep).sum())
    edges = edges[keep]

    # --- Decision 4 (part 1): genuine multi-edges ------------------------
    # P1-03 (Task 6 audit, Claude Opus 5, 2026-09-11). The old code counted
    # duplicates AFTER the orientation sort below, so every reciprocated arc
    # pair (u,v)+(v,u) in a bidirectional SNAP file was booked as a collapsed
    # multi-edge: ca-GrQc reported 14,484 = (28,980-12)/2 "multi-edges" for a
    # file with none. The graph was always right; the audit label was wrong.
    # A genuine multi-edge is a repeated row in the SAME orientation, so count
    # those first, then count the reciprocated pairs the symmetrisation folds.
    edges_oriented_unique = np.unique(edges, axis=0)
    n_multi = len(edges) - len(edges_oriented_unique)

    # --- Decision 1: symmetrize ----------------------------------------
    # We treat every edge as undirected. Sorting each pair so (u,v) and (v,u)
    # become identical is what lets the dedup step below also handle
    # decision 4.
    edges = np.sort(edges_oriented_unique, axis=1)

    # --- Decision 4 (part 2): fold reciprocated pairs --------------------
    edges_unique = np.unique(edges, axis=0)
    n_reciprocated = len(edges) - len(edges_unique)
    edges = edges_unique

    # --- Decision 6 (part 1): reindex to contiguous 0..n-1 --------------
    # np.unique gives us the sorted distinct labels; np.searchsorted then maps
    # every original label to its position. This is the mapping we keep.
    original_ids = np.unique(edges)
    remapped = np.searchsorted(original_ids, edges)

    n_nodes_all = len(original_ids)

    # --- Build a symmetric adjacency matrix ------------------------------
    # We add each edge in both directions so the matrix is symmetric.
    rows = np.concatenate([remapped[:, 0], remapped[:, 1]])
    cols = np.concatenate([remapped[:, 1], remapped[:, 0]])
    data = np.ones(len(rows), dtype=np.int8)
    adj = sp.csr_matrix((data, (rows, cols)),
                        shape=(n_nodes_all, n_nodes_all))
    # Any residual duplicates would show as data>1; force back to binary.
    adj.data[:] = 1

    # --- Decision 2: restrict to the largest connected component ---------
    # Influence on a small disconnected fragment is capped by the fragment's
    # size, which would contaminate the ground-truth distribution with a
    # cluster of artificially tiny values.
    n_comp, labels = sp.csgraph.connected_components(adj, directed=False)
    if n_comp > 1:
        sizes = np.bincount(labels)
        giant = int(sizes.argmax())
        keep_nodes = np.flatnonzero(labels == giant)
        adj = adj[keep_nodes][:, keep_nodes]
        original_ids = original_ids[keep_nodes]
    else:
        keep_nodes = np.arange(n_nodes_all)

    adj = sp.csr_matrix(adj)
    adj.sort_indices()

    degree = np.diff(adj.indptr).astype(np.int64)

    # Precompute neighbour arrays. adj.indices[indptr[i]:indptr[i+1]] IS the
    # neighbour list of i already, so this is a view-slice, not a rebuild.
    nbrs = [adj.indices[adj.indptr[i]:adj.indptr[i + 1]]
            for i in range(adj.shape[0])]

    provenance = {
        "source": source,
        "raw_edge_rows": n_raw_edges,
        "self_loops_removed": n_self_loops,
        # Since 2026-09-11 `multi_edges_collapsed` counts genuine same-
        # orientation duplicates only (P1-03). cache_meta files written before
        # that date hold the old sum (multi + reciprocated) under this key; the
        # dated `provenance_audit_20260911` block that
        # record_cache_provenance_audit.py adds to them carries the split.
        "multi_edges_collapsed": int(n_multi),
        "reciprocated_pairs_folded": int(n_reciprocated),
        "duplicate_rows_folded_total": int(n_multi + n_reciprocated),
        "multi_edge_semantics": "same-orientation duplicates (since 2026-09-11)",
        "nodes_before_lcc": int(n_nodes_all),
        "nodes_after_lcc": int(adj.shape[0]),
        "nodes_dropped_by_lcc": int(n_nodes_all - adj.shape[0]),
        "components_found": int(n_comp),
        "symmetrized": True,
        "weights_discarded": True,
    }

    return Network(name=name, adj=adj, nbrs=nbrs, degree=degree,
                   original_ids=original_ids, provenance=provenance)


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------

def describe(net: Network) -> str:
    """
    Human-readable summary. Print this for every network you use and paste it
    into the methods section - it is the audit trail for decisions 1-6.
    """
    p = net.provenance
    lines = [
        f"Network: {net.name}",
        f"  source                 : {p['source']}",
        f"  nodes (after LCC)      : {net.n:,}",
        f"  edges (simple, undir.) : {net.m:,}",
        f"  mean degree            : {net.mean_degree:.3f}",
        f"  max degree             : {int(net.degree.max()):,}",
        "  -- preprocessing applied --",
        f"  symmetrized            : {p['symmetrized']}",
        f"  self-loops removed     : {p['self_loops_removed']:,}",
        f"  multi-edges collapsed  : {p['multi_edges_collapsed']:,}"
        f"  (same-orientation duplicates)",
        f"  reciprocated pairs     : {p.get('reciprocated_pairs_folded', 'n/a')}"
        f"  (folded by symmetrisation)",
        f"  rows unparsed          : {p.get('rows_unparsed', 'n/a')}",
        f"  components found       : {p['components_found']:,}",
        f"  nodes dropped by LCC   : {p['nodes_dropped_by_lcc']:,}",
        f"  weights                : discarded",
    ]
    return "\n".join(lines)
