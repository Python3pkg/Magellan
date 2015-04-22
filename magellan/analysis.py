#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package contains numerous analysis routines and links to third party libraries in order to
analyse and explore packages for Magellan.
"""

# todo s (aj):
# 1. 
# 2. Parse error file looking for conflicts
# 3. Generate dependency graph (using pip rather than parsing file

import subprocess
import shlex
import sys
import re
from pprint import pprint


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


def gen_dependency_graph_pip():
    """Generates a dependency graph using pip tools"""
    # todo (aj)
    
    print("Generate dependency graph")





def _parse_pipdeptree_output_file(f):
    """Takes a file object as input and parses that into a tree.
    
    Returns a graph as a dictionary
    """
    
    output = {}
    output['nodes'] = []
    output['dependencies'] = {}
    
    for line in f:
        level = len(re.search('(\s)+',line).group()) / 2
        if level < 1:
            #package_name = re.search('^[(A-Za-z)+\-*]+', line).group()
            package_name = re.search('.*==', line).group()[0:-2]
#            package_version = re.search('==[\d*\.*]*', line).group()[2:]
            package_version = re.search('==.*', line).group()[2:]
            # Add node if not extant:
            pv = (package_name, package_version)
            if pv not in output['nodes']:
                output['nodes'].append(pv)
            # update last package-version tuple if next line is dependency
            last_pv = pv
        else: # process dependencies
            if last_pv not in output['dependencies']:
                output['dependencies'][last_pv] = []
            output['dependencies'][last_pv].append(line)            
    
    return output
    
        
def _parse_pipdeptree_error_file(f):
    """Takes the output from pipdeptree stderr and parses into dictionary"""
    
    output = {}
    curr_node = ''

    f.readline() # eat the head   
    for line in f:
        if "-----" in line: # eat the tail
            continue
            
        if "*" in line: # new node
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
        if output_or_error=="output":
            return _parse_pipdeptree_output_file(f)
        else:
            return _parse_pipdeptree_error_file(f)


def _print_PDP_errs_parsed(PDP_errs_parsed):
    print(PDP_errs_parsed)
    
def _print_PDP_tree_parsed(PDP_tree_parsed):
    print("NODES!")
    for n in PDP_tree_parsed['nodes']:
        print(n)
    print("DEPS!")
    for n in PDP_tree_parsed['dependencies']:
        print('-'*72)
        print(n)
        for d in PDP_tree_parsed['dependencies'][n]:
            print(d)