#!/usr/bin/env python
# -*- coding: utf-8 -*-

# todo s (aj) 
# todo (aj) PIP OPTIONS ARE HARDCODED MAPLECROFT AT PRESENT
# See analysis
# see README.rst
# verbosity level

import argparse
import sys

from utils import (
    run_in_subprocess,
    make_virtual_env,
    install_requirements,
    resolve_venv_name
)

from analysis import (
    gen_pipdeptree_reports,
    parse_pipdeptree_file,
    print_pdp_tree_parsed,
)

from reports import produce_package_report

VERBOSE = False


def _go_analyse(**kwargs):
    """Script portion of the magellan analysis package.    
    
    """
    venv_name, name_bit, venv_bin = resolve_venv_name(kwargs['venv_name'])

    from analysis import write_dot_graph_to_disk, query_nodes_eges_in_venv
    
    nodes, edges = query_nodes_eges_in_venv(venv_bin)
    write_dot_graph_to_disk(nodes, edges, "{}DependencyGraph.gv".format(venv_name))

    sys.exit("gotta go")

    # Run pipdeptree reports
    pdpft = "{0}PDP_Output_{1}.txt"
    pdp_tree_file = pdpft.format(venv_name + name_bit, "Tree")
    pdp_err_file = pdpft.format(venv_name + name_bit, "Errs")
    gen_pipdeptree_reports(venv_bin=venv_bin, out_file=pdp_tree_file, err_file=pdp_err_file)

    # Parse pipdeptree reports
    pdp_tree_parsed = parse_pipdeptree_file(pdp_tree_file, output_or_error="output")
    pdp_errs_parsed = parse_pipdeptree_file(pdp_err_file, output_or_error="error")
    if VERBOSE: 
        print_pdp_tree_parsed(pdp_tree_parsed)
        
    # By specific package:
    package_list = kwargs['packages']
    if package_list:
        for package in package_list:
            produce_package_report(package, pdp_tree_parsed, pdp_errs_parsed)
    

def analysis_main():
    """Command line entry for analysis module
    
    Allows package specification; otherwise produces generic reports for environment.
    
    """
    
    parser = argparse.ArgumentParser(
        description="Magellan analysis",
        prog="Magellan",
    )

    # POSITIONAL ARGUMENTS:
    parser.add_argument(
        'packages',
        nargs='*',
        type=str,
        help="List package/s "
    )
    
    # OPTIONAL ARGUMENTS: 
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False, 
        help="Verbose mode"
    )
    parser.add_argument(
        '-n', '--venv-name', default=None,
        help="Specify name for virtual environment, default is MagEnv0, MagEnv1 etc",
    )

    # PROCESS ARGUMENTS:
    args = parser.parse_args()
    kwargs = vars(args)
    
    global VERBOSE 
    VERBOSE = kwargs['verbose']
    
    _go_analyse(**kwargs)
    

def _go(**kwargs):
    """Main script of magellan program.
    
    Accomplishes the following:
        Makes virtual env
        Installs requirements
        Runs analysis and reports on venv
    """
    
    # todo(aj) make verbose global
    # verbose = kwargs['verbose']
    # print(verbose)

    # Install packages into new virtual env
    venv_name = make_virtual_env(kwargs["venv_name"])
    venv_bin = venv_name + '/bin/'
    
    run_in_subprocess(venv_bin + 'pip install pipdeptree')
    install_requirements(kwargs["requirements"], venv_bin)

    # Run analytics for reports:
    gen_pipdeptree_reports(venv_bin=venv_bin)

    # Clean up
    keep_virtual_env = kwargs["keep_virtualenv"]
    print(keep_virtual_env)
    
    if not keep_virtual_env:
        print("Deleting virtual env; you can change this option on invocation.")
        run_in_subprocess('rm -rf ' + venv_name)
    else:
        print("keeping venv")


def main():
    """Command line entry point for magellan."""

    parser = argparse.ArgumentParser(
        description=("Explore Python Package Dependencies "
                     "like your name is Fernando!"),
        prog="Magellan",
    )

    # POSITIONAL ARGUMENTS:
    parser.add_argument(
        'requirements',
        type=str,
        help="Input files e.g. requirements.txt or similar."
    )
    
    # OPTIONAL ARGUMENTS: 
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False, 
        help="Verbose mode"
    )
    parser.add_argument(
        '-n', '--venv-name', default=None,
        help="Specify name for virtual environment, default is MagEnv0, MagEnv1 etc",
    )
    parser.add_argument(
        '-k', '--keep-virtualenv', action='store_true', default=False,
        help='Keep virtualenv after installation. NB: Default=False, virtualenv is deleted!'
    )

    # PROCESS ARGUMENTS:
    args = parser.parse_args()
    kwargs = vars(args)
    
    _go(**kwargs)


if __name__ == "__main__":
    main()
    sys.exit()