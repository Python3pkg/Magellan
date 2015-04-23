#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Playground for various ideas. Nothing to see here, move along...
"""

from analysis import write_dot_graph_to_disk, query_nodes_eges_in_venv


def scratchpad():
    """Playground for various ideas. Nothing to see here, move along..."""
    
    nodes, edges = query_nodes_eges_in_venv('D16/bin/')
    write_dot_graph_to_disk(nodes, edges, "DependencyGraph.gv")