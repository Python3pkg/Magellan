#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package contains numerous analysis routines and links to third party libraries
in order to analyse and explore packages for Magellan.
"""

from pprint import pprint


def calc_connected_nodes(nodes, edges, include_root=False):
    """ Returns dictionary of how many nodes all nodes are connected to.

    If including root then everything is connected to everything.
    Root is env root.

    :param nodes:
    :param edges:
    :return: dictionary of how many nodes any other is connected to.
    """
    conn_nodes = {}

    for n in nodes:
        n_key = n[0].lower()
        dist_dict = calc_node_distances(
            n_key, nodes, edges, include_root, list_or_dict='dict')
        conn_nodes[n] = len(dist_dict)

    return conn_nodes


def calc_weighted_connections(nodes, edges, include_root=False):
    """ Returns measures of connectedness as a fn. of number of nodes and
    distance to those nodes.

    :param nodes:
    :param edges:
    :param include_root: bool if including env root.
    :return: dict weighted_conn, dict sq_weighted_conn: connection measures.
    """
    weighted_conn = {}
    sq_weighted_conn = {}
    for n in nodes:
        n_key = n[0].lower()
        dist_dict = calc_node_distances(
            n_key, nodes, edges, include_root, list_or_dict='dict')
        weighted_conn[n] = sum(map(lambda x: 1.0/(1+x), dist_dict.values()))
        sq_weighted_conn[n] = sum(map(lambda x: 1.0/(1 + x*(2+x)),
                                      dist_dict.values()))

    return weighted_conn, sq_weighted_conn


def write_dot_graph_to_disk(nodes, edges, filename):
    """Write dot graph to disk."""

    node_template = 'n{}'
    node_index = {(nodes[x][0].lower(), nodes[x][1]): node_template.format(x+1)
                  for x in range(len(nodes))}
    node_index[('root', '0.0.0')] = node_template.format(0)

    pprint(node_index)

    # Fill in nodes
    node_template = '    {0} [label="{1}"];\n'

    with open(filename, 'wb') as f:

        f.write('digraph magout {\n')

        # Nodes
        f.write(node_template.format("n0", "root"))
        for n in node_index:
            f.write(node_template.format(node_index[n], n))

        # Fill in edge
        for e in edges:
            from_e = (e[0][0].lower(), e[0][1])
            to_e = (e[1][0].lower(), e[1][1])
            print(from_e, to_e)
            f.write("    {0} -> {1};\n"
                    .format(node_index[from_e], node_index[to_e]))

        f.write('}')


def write_dot_graph_to_disk_with_distance_colour(
        nodes, edges, filename, distances, inc_dist_labels=True):

    """ Create dot graph with colours.

    :param list nodes: list of nodes for graph
    :param list edges: list of connections between nodes
    :param str filename: output filename
    :param dict distances: (nodes:values) giving values to be used in colouring
    :param bool inc_dist_labels=True: include value of distances on node-label
    """
    node_template = 'n{}'
    node_index = {(nodes[x][0].lower(), nodes[x][1]): node_template.format(x+1)
                  for x in range(len(nodes))}
    node_index[('root', '0.0.0')] = node_template.format(0)

    # Fill in nodes
    node_template = '    {0} [label="{1}{2}];\n'
    colour_bit_template = '", style=filled, color="{0} {1} {2}"'

    dist_lookup = {k[0].lower(): distances[k] for k in distances}

    with open(filename, 'wb') as f:

        f.write('digraph magout {\n')

        # NODES
        orig_col_bit = colour_bit_template.format(0.25, 0.25, 0.25)
        f.write(node_template.format("n0", "root", orig_col_bit))
        max_col = max(distances.values())
        for n in node_index:
            n_key = n[0].lower()
            if n_key in dist_lookup:
                colour_bit = colour_bit_template.format(
                    str(1-0.5*dist_lookup[n_key]/max_col)[0:5], 1.0, 1.0)
                if inc_dist_labels:
                    colour_bit = ('\n dist: ' + str(dist_lookup[n_key])[0:5]
                                  + colour_bit)
            else:
                colour_bit = orig_col_bit

            f.write(node_template.format(node_index[n], n, colour_bit))

        # EDGES
        for e in edges:
            from_e = (e[0][0].lower(), e[0][1])
            to_e = (e[1][0].lower(), e[1][1])
            # print(from_e, to_e, node_index[from_e], node_index[to_e])
            f.write("    {0} -> {1};\n"
                    .format(node_index[from_e], node_index[to_e]))

        f.write('}')


def write_dot_graph_subset(
        nodes, edges, filename, distances, inc_dist_labels=True):

    """ Create dot graph with colours; truncated to only include those nodes
    in "distances"

    :param list nodes: list of nodes for graph
    :param list edges: list of connections between nodes
    :param str filename: output filename
    :param dict distances: (nodes:values) giving values used in colouring
    :param bool inc_dist_labels=True: include value of distances on node-label
    """

    dist_lookup = {k[0].lower(): distances[k] for k in distances}

    # reduce nodes and edges to only include distances:
    node_template = 'n{}'
    node_index = {(nodes[x][0].lower(), nodes[x][1]): node_template.format(x+1)
                  for x in range(len(nodes))
                  if nodes[x][0].lower() in dist_lookup}
    node_index[('root', '0.0.0')] = node_template.format(0)

    edge_index = [e for e in edges if e[0][0].lower() in dist_lookup
                  and e[1][0].lower() in dist_lookup]

    # Templates:
    node_template = '    {0} [label="{1}{2}];\n'
    colour_bit_template = '", style=filled, color="{0} {1} {2}"'

    with open(filename, 'wb') as f:

        f.write('digraph magout {\n')

        # NODES
        orig_col_bit = colour_bit_template.format(0.25, 0.25, 0.25)
        f.write(node_template.format("n0", "root", orig_col_bit))
        max_col = max(distances.values())
        for n in node_index:
            n_key = n[0]
            if n_key in dist_lookup:
                colour_bit = colour_bit_template.format(
                    str(1-0.5*dist_lookup[n_key]/max_col)[0:5], 1.0, 1.0)
                if inc_dist_labels:
                    colour_bit = ('\n dist: ' + str(dist_lookup[n_key])[0:5]
                                  + colour_bit)
            else:
                colour_bit = orig_col_bit

            f.write(node_template.format(node_index[n], n, colour_bit))

        # EDGES
        for e in edge_index:
            from_e = (e[0][0].lower(), e[0][1])
            to_e = (e[1][0].lower(), e[1][1])
            f.write("    {0} -> {1};\n"
                    .format(node_index[from_e], node_index[to_e]))

        f.write('}')


def print_pdp_tree_parsed(pdp_tree_parsed):
    print("pipdeptree nodes:")
    for n in pdp_tree_parsed['nodes']:
        print(n)
    print("pipdeptree deps:")
    for n in pdp_tree_parsed['dependencies']:
        print('-'*72)
        print(n)
        for d in pdp_tree_parsed['dependencies'][n]:
            print(d)


