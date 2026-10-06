"""Exact symmetric live-edge IC, preserving production random draw order.

Only node-by-draw labels/counts persist. Reachability uses one sparse boolean
matrix per draw, bounded further by seed batches; no node-by-node-by-draw cube.
"""
import numpy as np
import scipy.sparse as sp
from .dynamics import symmetric_edge_probabilities


def live_edge_draws(net, p=.05, n_sims=200, convention='uniform', seed=0):
    """Yield (symmetric CSR boolean adjacency, component labels) in draw order."""
    if not isinstance(n_sims, (int, np.integer)) or n_sims < 1:
        raise ValueError('n_sims must be a positive integer')
    if not np.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('p must be finite in [0,1]')
    a = net.adj
    if a.shape != (net.n, net.n) or net.n < 1 or (a != a.T).nnz or a.diagonal().any():
        raise ValueError('requires a nonempty symmetric loop-free graph')
    rng = np.random.default_rng(seed)
    # Trivalency consumes RNG here once, exactly as production does.
    u,v,probs = symmetric_edge_probabilities(net, convention,p,rng)
    for _ in range(n_sims):
        keep = rng.random(len(u)) < probs
        g = sp.csr_matrix((np.ones(keep.sum(),dtype=bool),(u[keep],v[keep])),shape=a.shape)
        _, labels = sp.csgraph.connected_components(g,directed=False)
        yield g + g.T, labels


def percolation_labels(net, p=.05, n_sims=200, convention='uniform', seed=0):
    """Return int32 labels [node, draw]; labels are local to each draw.

    This sufficient representation supports later seed-set union queries by
    summing sizes of unique component labels occupied by the chosen seeds.
    """
    return np.stack([labels for _,labels in live_edge_draws(net,p,n_sims,convention,seed)],axis=1)


def validate_radii(radii):
    radii = tuple(radii)
    if not radii or any(not isinstance(r,(int,np.integer)) or r < 0 for r in radii) or tuple(sorted(set(radii))) != radii:
        raise ValueError('radii must be strictly increasing nonnegative integers')
    return radii


def truncated_draw_sizes(g, radii=(0,1,2,3), batch_size=256):
    """Return counts [node, radius] for one symmetric live graph.

    Boolean multiplication records existence, avoiding integer walk overflow;
    retaining all previously reached nodes makes these shortest-path balls.
    """
    radii = validate_radii(radii)
    if not isinstance(batch_size,int) or batch_size < 1:
        raise ValueError('batch_size must be positive integer')
    n = g.shape[0]
    result = np.empty((n,len(radii)),dtype=np.int32)
    for start in range(0,n,batch_size):
        stop = min(n,start+batch_size)
        reach = sp.csr_matrix((np.ones(stop-start,dtype=bool),(np.arange(stop-start),np.arange(start,stop))),shape=(stop-start,n))
        for r in range(radii[-1]+1):
            if r in radii:
                result[start:stop,radii.index(r)] = reach.getnnz(axis=1)
            if r < radii[-1]:
                reach = reach + reach @ g
    return result


def truncated_cascade_sizes(net, radii=(0,1,2,3), p=.05, n_sims=200, convention='uniform', seed=0, batch_size=256):
    """Return int32 counts [node, draw, radius], seed included at r=0."""
    radii = validate_radii(radii)
    return np.stack([truncated_draw_sizes(g,radii,batch_size) for g,_ in live_edge_draws(net,p,n_sims,convention,seed)],axis=1)
