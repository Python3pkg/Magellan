#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package contains numerous analysis routines and links to third party libraries
in order to analyse and explore packages for Magellan.
"""

from pprint import pprint
import subprocess
import shlex
import sys
import re
import pickle
import os
from utils import run_in_subprocess


def direct_links_to_package(package_name, edges):
    """Returns direct dependency links from a given package.

    :param str package_name: package name
    :param list edges: edges
    :rtype list
    :return: ancestors, descendants
    """

    descendants = [x for x in edges if package_name.lower() == x[0][0].lower()]
    ancestors = [x for x in edges if package_name.lower() == x[1][0].lower()]
    return ancestors, descendants


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


def ancestor_trace(
        package, nodes, edges, include_root=True, keep_untouched_nodes=False):
    """ Returns dict indicating ancestor trace of package.

    If X depends on Y, then if Y changes it may affect X; not vice versa.
    So if X changes it will not affect Y. Therefore it is the ancestors that
    are affected by their descendants. With this in mind, this routine traces
    the connections of a directed graph, returning only a direct ancestral
    lineage.

    This should indicate what packages are at risk should a package change.

    Implementation, breadth first search but focusing only on upstream links.

    :param package: str name of package
    :param nodes: list of nodes
    :param edges: list of edges
    :return: dict indicating ancestor trace of package
    """

    # Define recursive function in _scope_ of calc_node_distance_to fn.
    def rec_fun(search_set, cur_level):
        """ Recursive function to determine distance of connected nodes"""
        to_search_next = []

        for p in search_set:
            if abs(dist_dict[p]) > cur_level:
                dist_dict[p] = cur_level
            node_touched[p] = True

            anc, _ = direct_links_to_package(p, edges)
            if not include_root:
                anc = [nx for nx in anc if 'root' not in str(nx)]

            anc_search = [nx[0][0].lower() for nx in anc
                          if not node_touched[nx[0][0].lower()]]
            to_search_next += anc_search

        to_search_next = list(set(to_search_next))  # uniques

        if to_search_next:
            rec_fun(to_search_next, cur_level + 1)

            # END OF RECURSIVE FUNCTION #
            # ------------------------- #

    start_dist = -999
    # set up distance dictionary:
    dist_dict = {x[0].lower(): start_dist for x in nodes}
    if include_root:
        dist_dict['root'] = start_dist

    # set up search dictionary:
    node_touched = {x[0].lower(): False for x in nodes}
    if include_root:
        node_touched['root'] = False

    rec_fun([package.lower()], 0)

    if keep_untouched_nodes:
        anc_trace = {(x[0], x[1]): dist_dict[x[0].lower()] for x in nodes}
    else:
        anc_trace = {(x[0], x[1]): dist_dict[x[0].lower()]
                     for x in nodes if dist_dict[x[0].lower()] > start_dist}
    if include_root:
        anc_trace[('root', '0.0.0')] = dist_dict['root']

    # Return type dict:
    return anc_trace


def calc_node_distances(
        package, nodes, edges, include_root=False,
        keep_untouched_nodes=False, list_or_dict="list"):

    """ Calculates the distance to a node on an acyclic directed graph.

    :param package: package_name
    :param nodes: list of nodes
    :param edges: list of edges (node links)
    :param include_root=False: whether to include the environment root
    :param keep_untouched_nodes=False: whether to return untouched nodes
    :param list_or_dict="dict": return type
    :rtype: list | dict
    :return: list or dict of nodes and distance

    NB: package name will be a string of just the name, we are ignoring version
    and assuming package name is unique!

    NB: 'root' connects everything, so can skip that node optionally

    Other details:
        Selected package root node (not env 'root') has distance of zero
        Everything begins at -999

    """

    # Define recursive function in _scope_ of calc_node_distance_to fn.
    def rec_fun(search_set, cur_level):
        """ Recursive function to determine distance of connected nodes"""
        to_search_next = []

        for p in search_set:
            if abs(dist_dict[p]) > cur_level:
                dist_dict[p] = cur_level
            node_touched[p] = True

            anc, dec = direct_links_to_package(p, edges)
            if not include_root:
                anc = [nx for nx in anc if 'root' not in str(nx)]
                dec = [nx for nx in dec if 'root' not in str(nx)]

            dec_search = [nx[1][0].lower() for nx in dec
                          if not node_touched[nx[1][0].lower()]]
            anc_search = [nx[0][0].lower() for nx in anc
                          if not node_touched[nx[0][0].lower()]]
            to_search_next += dec_search + anc_search

        to_search_next = list(set(to_search_next))  # uniques

        if to_search_next:
            rec_fun(to_search_next, cur_level+1)

        # END OF RECURSIVE FUNCTION #
        # ------------------------- #

    start_distance = -999
    # set up distance dictionary:
    dist_dict = {x[0].lower(): start_distance for x in nodes}
    if include_root:
        dist_dict['root'] = start_distance

    # set up search dictionary:
    node_touched = {x[0].lower(): False for x in nodes}
    if include_root:
        node_touched['root'] = False

    rec_fun([package.lower()], 0)

    if list_or_dict == "list":
        if keep_untouched_nodes:
            node_distances = [(x[0], x[1], dist_dict[x[0].lower()])
                              for x in nodes]
        else:
            node_distances = [(x[0], x[1], dist_dict[x[0].lower()])
                              for x in nodes
                              if dist_dict[x[0].lower()] > start_distance]
        if include_root:
            node_distances.append(('root', '0.0.0', dist_dict['root']))
    else:  # return type dict
        if keep_untouched_nodes:
            node_distances = {(x[0], x[1]): dist_dict[x[0].lower()]
                              for x in nodes}
        else:
            node_distances = {(x[0], x[1]): dist_dict[x[0].lower()]
                              for x in nodes
                              if dist_dict[x[0].lower()] > start_distance}
        if include_root:
            node_distances[('root', '0.0.0')] = dist_dict['root']

    # Return type dict:
    return node_distances


def vex_query_nodes_eges_in_venv(venv_bin=None):
    """Generate Nodes and Edges of packages in virtual env.

    :param venv_bin: bin directory of virtualenv
    :rtype list, list
    :return: nodes, edges
    """

    venv_bin = '' if venv_bin is None else venv_bin

    # Get super_unique_name for temporary file
    super_unique_name = 'super_unique_name.py'
    while True:
        if not os.path.exists(super_unique_name):
            break
        super_unique_name = "{}.py".format(_get_random_string_of_length_n(16))

    # write script
    with open(super_unique_name, 'w') as f:
        f.write(_return_script_string())

    # execute
    run_in_subprocess('{0}python {1}'.format(venv_bin, super_unique_name))
    run_in_subprocess('rm {}'.format(super_unique_name))

    # Load in nodes and edges pickles
    nodes = pickle.load(open('nodes.p', 'rb'))
    edges = pickle.load(open('edges.p', 'rb'))

    return nodes, edges


def query_nodes_edges_in_venv(venv_bin=None):
    """Generate Nodes and Edges of packages in virtual env.

    :param venv_bin: bin directory of virtualenv
    :rtype list, list
    :return: nodes, edges
    """

    venv_bin = '' if venv_bin is None else venv_bin

    # Get super_unique_name for temporary file
    super_unique_name = 'super_unique_name.py'
    while True:
        if not os.path.exists(super_unique_name):
            break  
        super_unique_name = "{}.py".format(_get_random_string_of_length_n(16))

    # write script
    with open(super_unique_name, 'w') as f:
        f.write(_return_script_string())

    # execute
    run_in_subprocess('{0}python {1}'.format(venv_bin, super_unique_name))
    run_in_subprocess('rm {}'.format(super_unique_name))

    # Load in nodes and edges pickles
    nodes = pickle.load(open('nodes.p', 'rb'))
    edges = pickle.load(open('edges.p', 'rb'))
    
    return nodes, edges


def write_dot_graph_to_disk(nodes, edges, filename):
    """Write dot graph to disk."""

    node_template = 'n{}'
    node_index = {(nodes[x][0].lower(), nodes[x][1]): node_template.format(x+1)
                  for x in range(len(nodes))}
    node_index[('root', '0.0.0')] = node_template.format(0)

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


def vex_gen_pipdeptree_reports(venv_name, out_file='PDP_Output_Tree.txt',
                               err_file='PDP_Output_Errs.txt'):
    """Runs pipdeptree and outputs two files: regular output and errors"""

    #  run pipdeptree and process outputs
    cmd_args = shlex.split('vex {0} pipdeptree'.format(venv_name))

    try:
        with open(err_file, 'w') as errfile, open(out_file, 'w') as outfile:
            retcode = subprocess.call(cmd_args, stderr=errfile, stdout=outfile)
    except Exception as e:
        print("LAPU LAPU! Error in analysis.py, gen_pipdeptree_reports when "
              "attempting to run: {}".format(cmd_args))
        sys.exit(e)
    return retcode


def gen_pipdeptree_reports(venv_bin=None, out_file='PDP_Output_Tree.txt',
                           err_file='PDP_Output_Errs.txt'):

    """Runs pipdeptree and outputs two files: regular output and errors"""

    env_string = venv_bin if venv_bin is not None else ''
    # else run in current env

    #  run pipdeptree and process outputs
    cmd_args = shlex.split(env_string + 'pipdeptree')
    try:
        with open(err_file, 'w') as errfile, open(out_file, 'w') as outfile:
            retcode = subprocess.call(cmd_args, stderr=errfile, stdout=outfile)
    except Exception as e:
        print("LAPU LAPU! Error in analysis.py, gen_pipdeptree_reports when "
              "attempting to run: {}".format(cmd_args))
        sys.exit(e)
        # todo (aj) log to errorlog
    return retcode


def _parse_pipdeptree_output_file(f):
    """Takes a file object as input and parses that into a tree.
    
    Returns a graph as a dictionary
    """
    
    output = {'nodes': [], 'dependencies': {}}

    for line in f:
        level = len(re.search('(\s)+', line).group()) / 2
        if level < 1:
            # package_name = re.search('^[(A-Za-z)+\-*]+', line).group()
            package_name = re.search('.*==', line).group()[0:-2]
#            package_version = re.search('==[\d*\.*]*', line).group()[2:]
            package_version = re.search('==.*', line).group()[2:]
            # Add node if not extant:
            pv = (package_name, package_version)
            if pv not in output['nodes']:
                output['nodes'].append(pv)
            # update last package-version tuple if next line is dependency
            last_pv = pv
        else:  # process dependencies
            if last_pv not in output['dependencies']:
                output['dependencies'][last_pv] = []
            output['dependencies'][last_pv].append(line)            
    
    return output
    

def _parse_pipdeptree_error_file(f):
    """Takes the output from pipdeptree stderr and parses into dictionary"""
    
    output = {}
    curr_node = ''

    f.readline()  # eat the head
    for line in f:
        if "-----" in line:  # eat the tail
            continue
            
        if "*" in line:  # new node
            curr_node = re.search('(->\s*).*\[', line).group()[3:-2]
            ancestor = re.search('.*->', line).group()[2:-3]
            output[curr_node] = {}
        else:
            ancestor = re.search('.*->', line)
            if ancestor is not None:
                ancestor = ancestor.group()[:-3]
        
        anc_name = re.search('.*==', ancestor).group()[0:-2]
        anc_ver = re.search('==.*', ancestor).group()[2:]

        tmp = re.search('\[.*\]', line).group()
        output[curr_node][(anc_name, anc_ver)] = tmp
        
    return output
    
    
def parse_pipdeptree_file(input_file=None, output_or_error="output"):
    """Takes output from pipdeptree and returns dictionary
    
    If output_or_error is anything other than "output" it will be processed
    as though it is the output from stderr.
    
    """
    if input_file is None:
        print("No file given, please specifiy.")
    
    with open(input_file, 'r') as f:
        if output_or_error == "output":
            return _parse_pipdeptree_output_file(f)
        else:
            return _parse_pipdeptree_error_file(f)


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


def _get_random_string_of_length_n(n):
    """Returns random string of length n"""
    import random
    import string
    return "".join(random.choice(string.ascii_letters) for _ in range(n))


def _return_script_string():
    """Returns a script to write into local dir; execute under virtualenv"""

    script = """
from pprint import pprint
import pickle
import pip

#default_skip = ['setuptools', 'pip', 'python', 'distribute']
# something is relying on setuptools, apparently

default_skip = ['pip', 'python', 'distribute']
skip = default_skip + ['pipdeptree', 'virtualenv', 'magellan']
local_only = True
pkgs = pip.get_installed_distributions(local_only=local_only,
                                        skip=skip)

# FORM NODES
nodes = [(x.project_name, x.version) for x in pkgs]

# FORM EDGES
installed_vers = {x.key: x.version for x in pkgs}
edges = []
for p in pkgs:
    p_tup = (p.project_name, p.version)
    edges.append([('root','0.0.0'), p_tup])
    reqs = p.requires()
    if reqs:
        for r in reqs:
            if r.key in installed_vers:
                r_tup = (r.key, installed_vers[r.key])
            else:
                r_tup = (r.key)
            edges.append([p_tup, r_tup, r.specs])

# Output:
#for node in nodes:
#    print("N#{}".format(node))
#for edge in edges:
#    print("E#{}".format(edge))

# Record nodes and edges to disk to be read in  by main program if needed.
pickle.dump(nodes, open('nodes.p','wb'))
pickle.dump(edges, open('edges.p','wb'))
"""
    return script