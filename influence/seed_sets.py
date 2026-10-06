"""Exact component-union policies for symmetric IC (no fitting).

Labels have shape node x draw. Components are distinct between draws; summing
their sizes after deduplicating the selected labels gives exact set influence.
"""
import numpy as np


def validate_labels(labels):
    labels=np.asarray(labels)
    if labels.ndim != 2 or min(labels.shape)<1 or not np.issubdtype(labels.dtype,np.integer) or labels.min()<0 or labels.max()>=len(labels):
        raise ValueError('labels must be nonnegative integer node x draw component IDs')
    return labels


def validate_k(k,n):
    if isinstance(k,(bool,np.bool_)) or not isinstance(k,(int,np.integer)) or not 0<=k<=n:
        raise ValueError('k must be an integer between zero and n')


def top_k(values,k):
    values=np.asarray(values)
    if values.ndim!=1 or not np.isfinite(values).all():
        raise ValueError('ranking must be a finite vector')
    validate_k(k,len(values))
    # lexsort makes equal scores choose the smaller cache node index.
    return np.lexsort((np.arange(len(values)),-values))[:k]


def set_spread(labels,seeds):
    labels=validate_labels(labels)
    seeds=np.asarray(seeds)
    if seeds.ndim!=1 or (len(seeds) and (not np.issubdtype(seeds.dtype,np.integer) or seeds.min()<0 or seeds.max()>=len(labels))) or len(np.unique(seeds))!=len(seeds):
        raise ValueError('seeds must be distinct valid node indices')
    seeds=seeds.astype(int)
    return np.array([np.bincount(labels[:,d],minlength=len(labels))[np.unique(labels[seeds,d])].sum()
                     for d in range(labels.shape[1])],dtype=np.int64)


def greedy_seed_set(labels,k):
    labels=validate_labels(labels)
    n,draws=labels.shape
    validate_k(k,n)
    # Maintain each node's per-draw marginal. Selecting a component zeros that
    # whole component's contribution, avoiding a node x node x draw tensor.
    marginal=np.stack([np.bincount(labels[:,d],minlength=n)[labels[:,d]] for d in range(draws)],axis=1)
    selected=[]; gains=[]
    for _ in range(k):
        sums=marginal.sum(axis=1)
        sums[selected]=-1
        node=int(np.argmax(sums))
        selected.append(node); gains.append(float(sums[node]/draws))
        marginal[labels==labels[node,:]]=0
    return np.asarray(selected,dtype=int),np.asarray(gains)


def degree_discount(adj,k,p):
    """Chen, Wang & Yang (KDD 2009) small-p uniform IC approximation.

    Uses dd=d-2t-(d-t)t*p. Primary derivation:
    https://www.microsoft.com/en-us/research/wp-content/uploads/2016/06/kdd09_influence-1.pdf
    """
    n=adj.shape[0]; validate_k(k,n)
    if not np.isfinite(p) or not 0<=p<=1: raise ValueError('invalid p')
    degree=np.asarray(adj.sum(axis=1)).ravel().astype(float)
    t=np.zeros(n); score=degree.copy(); selected=[]
    for _ in range(k):
        score[selected]=-np.inf
        node=int(np.argmax(score)); selected.append(node)
        neighbors=adj.indices[adj.indptr[node]:adj.indptr[node+1]]
        t[neighbors]+=1
        score[neighbors]=degree[neighbors]-2*t[neighbors]-(degree[neighbors]-t[neighbors])*t[neighbors]*p
    return np.asarray(selected,dtype=int)
