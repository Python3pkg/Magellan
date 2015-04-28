#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
from pprint import pprint

from utils import resolve_venv_name
from analysis import (gen_pipdeptree_reports, parse_pipdeptree_file,
                      print_pdp_tree_parsed, direct_links_to_package,
                      write_dot_graph_to_disk_with_distance_colour,
                      calc_node_distances, calc_weighted_connections,
                      calc_connected_nodes, ancestor_trace,
                      write_dot_graph_subset, write_dot_graph_to_disk,
                      query_nodes_eges_in_venv)

from reports import produce_package_report

VERBOSE = False
SUPER_VERBOSE = False


def _go_analyse(**kwargs):
    """Script portion of the magellan analysis package.

    There are 2 main routes through the script based on whether 1+ packages
    are specified. If no packages are named then generic reports will be
    run on the environment. If packages are given in command line then
    package specific reports are run.

    There is the "pre-option" of -S on the command line which simply lists all
    packages in the environment and exits.

    """

    global VERBOSE
    global SUPER_VERBOSE

    venv_name, name_bit, venv_bin = resolve_venv_name(kwargs['venv_name'])
    nodes, edges = query_nodes_eges_in_venv(venv_bin)

    show_all_packages_and_exit = kwargs['show_all_packages']
    if show_all_packages_and_exit:
        print('"Show all packages" selected. Nodes found:')
        pprint(nodes)
        sys.exit(0)

    # Run pipdeptree reports
    # These are package agnostic, but need to be done if parsing for specific packages.
    # These reports aren't that great and might be cut.
    pdp_file_template = '{0}PDP_Output_{1}.txt'
    pdp_tree_file = pdp_file_template.format(venv_name + name_bit, "Tree")
    pdp_err_file = pdp_file_template.format(venv_name + name_bit, "Errs")
    if VERBOSE:
        print("Generating pipdeptree report")
    gen_pipdeptree_reports(venv_bin=venv_bin, out_file=pdp_tree_file, err_file=pdp_err_file)
    # Parse pipdeptree reports
    if VERBOSE:
        print("Parsing pipdeptree report and outputting to: {0} and {1}"
              .format(pdp_tree_file, pdp_err_file))
    pdp_tree_parsed = parse_pipdeptree_file(pdp_tree_file, output_or_error="output")
    pdp_errs_parsed = parse_pipdeptree_file(pdp_err_file, output_or_error="error")
    if SUPER_VERBOSE:
        print_pdp_tree_parsed(pdp_tree_parsed)

    # MAIN ANALYSIS
    package_list = kwargs['packages']

    if not package_list:  # generic package-agnostic reports
        dep_graph_name = "{}DependencyGraph.gv".format(venv_name)
        write_dot_graph_to_disk(nodes, edges, dep_graph_name)
        if VERBOSE:
            print("Writing dependency graph to {}".format(dep_graph_name))

        # Calculate connectedness of graph
        if VERBOSE:
            print("Calculating connectedness of nodes in environment")
        abs_conn = calc_connected_nodes(nodes, edges)
        write_dot_graph_to_disk_with_distance_colour(nodes, edges, 'abs_card.gv', abs_conn)
        weighted_conn, sq_weighted_conn = calc_weighted_connections(nodes, edges)
        write_dot_graph_to_disk_with_distance_colour(nodes, edges, 'weighted_card.gv', weighted_conn)
        write_dot_graph_to_disk_with_distance_colour(nodes, edges, 'sq_weighted_card.gv', sq_weighted_conn)

    else:  # package specific analysis
        for package in package_list:
            produce_package_report(package, pdp_tree_parsed, pdp_errs_parsed)

            ancestors, descendants = direct_links_to_package(package, edges)
            distances_dict = calc_node_distances(
                package, nodes, edges, include_root=False, list_or_dict='dict')
            write_dot_graph_to_disk_with_distance_colour(
                nodes, edges, '{}.gv'.format(package), distances_dict)

            if SUPER_VERBOSE:
                print("\n" + "-"*50 + "\n" + package + "\n")
                print("DIRECT DESCENDENTS - depended on by {}".format(package))
                pprint(descendants)
                print("DIRECT ANCESTORS - these depend on {}".format(package))
                pprint(ancestors)

            # Calculate ancestor trace of package
            if VERBOSE:
                print("Calculating ancestor trace for {}".format(package))
            anc_track = ancestor_trace(package, nodes, edges)
            write_dot_graph_to_disk_with_distance_colour(nodes, edges, '{}_anc_track.gv'.format(package), anc_track)
            write_dot_graph_subset(nodes, edges, '{}_anc_track_trunc.gv'.format(package), anc_track)


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
        '-sv', '--super-verbose', action='store_true', default=False,
        help="Super verbose mode; also sets VERBOSE as True."
    )

    parser.add_argument(
        '-n', '--venv-name', default=None,
        help="Specify name for virtual environment to analyse.",
    )

    parser.add_argument(
        '-S', '--show-all-packages', action='store_true', default=False,
        help="Show all packages and exit."
    )

    # PROCESS ARGUMENTS:
    args = parser.parse_args()
    kwargs = vars(args)

    global VERBOSE
    VERBOSE = kwargs['verbose']
    global SUPER_VERBOSE
    SUPER_VERBOSE = kwargs['super_verbose']
    if SUPER_VERBOSE:
        VERBOSE = True

    _go_analyse(**kwargs)


if __name__ == "__main__":
    analysis_main()
    sys.exit()