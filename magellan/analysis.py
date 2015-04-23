#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package contains numerous analysis routines and links to third party libraries in order to
analyse and explore packages for Magellan.
"""

import subprocess
import shlex
import sys
import re
import pickle
import os
from utils import run_in_subprocess


def query_nodes_eges_in_venv(venv_bin=None):
    """Generate Nodes and Edges of packages in virtual env."""

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
    # create dot graph:
    node_template = 'n{}'
    node_index = {(nodes[x][0].lower(), nodes[x][1]): node_template.format(x+1) for x in range(len(nodes))}
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
            # print(from_e, to_e, node_index[from_e], node_index[to_e])
            f.write("    {0} -> {1};\n".format(node_index[from_e], node_index[to_e]))
        
        f.write('}')


def gen_pipdeptree_reports(venv_bin=None, out_file='PDP_Output_Tree.txt', err_file='PDP_Output_Errs.txt'):
    """Runs pipdeptree and outputs results to two files: regular output and errors"""

    env_string = venv_bin if venv_bin is not None else ''  # else run in current env

    #  run pipdeptree and process outputs
    cmd_args = shlex.split(env_string + 'pipdeptree')
    try:
        with open(err_file, 'w') as errfile, open(out_file, 'w') as outfile:
            retcode = subprocess.call(cmd_args, stderr=errfile, stdout=outfile)
    except Exception as e:
        print("LAPU LAPU! Error in analysis.py, gen_pipdeptree_reports when attempting to run: {}".format(cmd_args))
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
        anc_version = re.search('==.*', ancestor).group()[2:]
        
        output[curr_node][(anc_name, anc_version)] = re.search('\[.*\]', line).group()
        
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
    print("NODES!")
    for n in pdp_tree_parsed['nodes']:
        print(n)
    print("DEPS!")
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

#default_skip = ['setuptools', 'pip', 'python', 'distribute'] # something is relying on setuptools, apparently
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

# Record nodes and edges to disk to be read in  by main program if needed (saves parsing)
pickle.dump(nodes, open('nodes.p','wb'))
pickle.dump(edges, open('edges.p','wb'))
"""
    return script