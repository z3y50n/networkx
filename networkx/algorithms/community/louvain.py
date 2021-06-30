"""Function for detecting communities base on Louvain Community Detection
Algorithm"""

from collections import deque
from copy import deepcopy
import random

import networkx as nx
from networkx.algorithms.community import modularity
from networkx.utils import py_random_state

__all__ = ["louvain_communities", "generate_dendrogram"]


@py_random_state("seed")
def louvain_communities(G, weight="weight", threshold=0.0000001, seed=None):
    """Find the best partition of G using the Louvain Community Detection
     Algorithm.

     Parameters
     ----------
     G : NetworkX graph
     weight : string or None, optional (default="weight")
         The name of an edge attribute that holds the numerical value
         used as a weight. If None then each edge has weight 1.
     threshold : float, optional (default=0.0000001)
         Modularity gain threshold for each level. If the gain of modularity
         between 2 levels of the algorithm is less than the given threshold
         then the algorithm stops and returns the resulting communities.
    seed : integer, random_state, or None (default)
         Indicator of random number generation state.
         See :ref:`Randomness<randomness>`.

     Returns
     -------
     list
         A list of sets. Each set represents one community and contains
         all the nodes that constitute it.

     References
     ----------
     .. [1] Blondel, V.D. et al. Fast unfolding of communities in
        large networks. J. Stat. Mech 10008, 1-12(2008)
    """

    d = generate_dendrogram(G, weight, threshold, seed)
    q = deque(d, maxlen=1)
    return q.pop()


@py_random_state("seed")
def generate_dendrogram(G, weight="weight", threshold=0.0000001, seed=None):
    """Compute the communities in G and generate the associated dendrogram

    A dendrogram is a diagram representing a tree and each level represents
    a partition of the G graph. The top level contains the smallest communities
    and as you traverse to the bottom of the tree the communities get bigger
    and the overal modularity increases making the partition better.
    """

    partition = [{u} for u in G.nodes()]
    mod = modularity(G, partition)
    graph = G.copy()
    m = G.size(weight=weight)

    while True:
        partition, improvement = _one_level(graph, m, deepcopy(partition), weight, seed)
        if not improvement:
            break
        new_mod = modularity(G, partition)
        if new_mod - mod <= threshold:
            break
        graph = _gen_graph(G, partition)
        yield partition


def _one_level(G, m, partition, weight="weight", seed=None):
    """Calculate one level of the tree"""
    node2com = {u: i for i, u in enumerate(G.nodes())}
    degrees = dict(G.degree(weight=weight))
    total_weights = {i: deg for i, deg in enumerate(degrees.values())}
    nbrs = {u: dict(G[u]) for u in G.nodes()}
    rand_nodes = list(G.nodes)
    seed.shuffle(rand_nodes)
    nb_moves = 1
    improvement = False
    while nb_moves > 0:
        nb_moves = 0
        for u in rand_nodes:
            best_mod = 0
            best_com = node2com[u]
            partition[best_com].difference_update(G.nodes[u].get("nodes", {u}))
            weights2com = _neighbor_weights(u, nbrs[u], node2com, weight)
            degree = degrees[u]
            total_weights[best_com] -= degree
            for nbr_com, wt in weights2com.items():
                gain = wt - (total_weights[nbr_com] * degree) / m
                if gain > best_mod:
                    best_mod = gain
                    best_com = nbr_com
            partition[best_com].update(G.nodes[u].get("nodes", {u}))
            total_weights[best_com] += degree
            if best_com != node2com[u]:
                improvement = True
                nb_moves += 1
                node2com[u] = best_com
    partition = list(filter(len, partition))
    return partition, improvement


def _neighbor_weights(node, nbrs, node2com, weight="weight"):
    """Calculate node's neighbor communities and weights"""
    weights = {}
    for nbr, data in nbrs.items():
        if nbr != node:
            weights[node2com[nbr]] = weights.get(node2com[nbr], 0) + 2 * data.get(
                weight, 1
            )
    return weights


def _gen_graph(G, partition, weight="weight"):
    """Generate a new graph based on the partitions of a given graph"""
    H = nx.Graph()
    node2com = {}
    for i, part in enumerate(partition):
        H.add_node(i, nodes=part)
        for node in part:
            node2com[node] = i

    for node1, node2, wt in G.edges(data=True):
        wt = wt.get(weight, 1)
        com1 = node2com[node1]
        com2 = node2com[node2]
        temp = H.get_edge_data(com1, com2, {weight: 0}).get(weight, 1)
        H.add_edge(com1, com2, **{weight: wt + temp})
    return H
