#!/usr/bin/env python
# -*- coding: utf-8 -*-

# todo (security) remove default pip options before making repo public!!

import argparse
import sys
from pprint import pprint

from magellan.package_utils import Package

from magellan.env_utils import Environment

from magellan.analysis import (
    print_pdp_tree_parsed,
    write_dot_graph_to_disk_with_distance_colour,
    write_dot_graph_subset, write_dot_graph_to_disk,
    calc_weighted_connections, calc_connected_nodes,
    )

from magellan.reports import produce_package_report

VERBOSE = False
SUPER_VERBOSE = False


def _go(**kwargs):
    """Main script of magellan program.
    
    1) If passed a requirements file it will install those requirements into
    a fresh virtual environment. If that environment exists, it shall be
    deleted and a new one setup for installation.

    2) If an environment is passed in but doesn't exist, then exit.

    3) If no environment is passed in, do analysis on current env.

    If -S just show all packages and exit.

    If packages are specified then do package specific analysis. Otherwise
    perform general analysis on environment.
    """

    global VERBOSE
    global SUPER_VERBOSE

    # INITIAL SETUP
    venv = Environment(kwargs['venv_name'])
    venv.magellan_setup_go_env(kwargs)
    # ANALYSIS SECTION
    venv.gen_pipdeptree_reports(VERBOSE)
    venv.parse_pipdeptree_reports()

    package_list = Package.resolve_package_list(venv, kwargs)
    packages = {p.lower(): Package(p) for p in package_list}


    sys.exit(0)

    ####################
    # Generic Analysis #
    ####################
    skip_generic_analysis = kwargs['skip_generic_analysis']
    if not skip_generic_analysis:  # generic package-agnostic reports
        dep_graph_name = "{}DependencyGraph.gv".format(venv_name)
        if VERBOSE:
            print("Writing dependency graph to {}".format(dep_graph_name))
        write_dot_graph_to_disk(nodes, edges, dep_graph_name)

        # Calculate connectedness of graph
        if VERBOSE:
            print("Calculating connectedness of nodes in environment")
        abs_conn = calc_connected_nodes(nodes, edges)
        write_dot_graph_to_disk_with_distance_colour(
            nodes, edges, 'abs_card.gv', abs_conn)
        wghtd_conn, sq_wghtd_conn = calc_weighted_connections(nodes, edges)

        write_dot_graph_to_disk_with_distance_colour(
            nodes, edges, 'weighted_card.gv', wghtd_conn)
        write_dot_graph_to_disk_with_distance_colour(
            nodes, edges, 'sq_weighted_card.gv', sq_wghtd_conn)

    #############################
    # Package Specific Analysis #
    #############################
    if package_list:
        for package in package_list:
            produce_package_report(
                package, pdp_tree_parsed, pdp_errs_parsed, VERBOSE)

            ancestors, descendants = direct_links_to_package(package, edges)
            distances_dict = calc_node_distances(
                package, nodes, edges, include_root=False, list_or_dict='dict')

            if distances_dict:
                write_dot_graph_to_disk_with_distance_colour(
                    nodes, edges, '{}.gv'.format(package), distances_dict)

            if SUPER_VERBOSE:
                print("\n" + "-" * 50 + "\n" + package + "\n")
                print("DIRECT DESCENDENTS - depended on by {}".format(package))
                pprint(descendants)
                print("DIRECT ANCESTORS - these depend on {}".format(package))
                pprint(ancestors)

            # Calculate ancestor trace of package
            if VERBOSE:
                print("Calculating ancestor trace for {}".format(package))

            anc_track = ancestor_trace(package, nodes, edges)

            # todo (aj)
            if anc_track:
                ft = '{}_anc_track.gv'
                write_dot_graph_to_disk_with_distance_colour(
                    nodes, edges, ft.format(package), anc_track)

                ft = '{}_anc_track_trunc.gv'
                write_dot_graph_subset(
                    nodes, edges, ft.format(package), anc_track)
                del ft


#######################
# Command Entry Point #
#######################
def main():
    """Command line entry point for magellan."""

    parser = argparse.ArgumentParser(
        prog="Magellan",
        description=("Explore Python Package Dependencies "
                     "like your name is Fernando!"),
    )

    # POSITIONAL ARGUMENTS:
    parser.add_argument('packages', nargs='*', type=str,
                        help="Packages to explore.")

    # OPTIONAL ARGUMENTS:
    parser.add_argument(
        '-s', '--show-all-packages', action='store_true', default=False,
        help="Show all packages and exit.")
    parser.add_argument(
        '-n', '--venv-name', default=None,
        help=("Specify name for virtual environment, "
              "default is MagEnv0, MagEnv1 etc"))
    parser.add_argument(
        '-r', '--requirements', type=str,
        help="requirements file (e.g. requirements.txt) to install.")

    pip_options = ("-f http://sw-srv.maplecroft.com/deployment_libs/ "
                   "--trusted-host sw-srv.maplecroft.com")

    parser.add_argument(
        '-po', '--pip-options', type=str, default=pip_options,
        help=("String. Pip options for installation of requirements.txt. "
              "E.g. '-f http://my_server.com/deployment_libs/ "
              "--trusted-host my_server.com'"))
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help="Verbose mode")
    parser.add_argument(
        '-sv', '--super-verbose', action='store_true', default=False,
        help="Super verbose mode; also sets VERBOSE as True.")
    parser.add_argument(
        '--path-to-env-bin', default=None, help="Path to virtual env bin")
    parser.add_argument(
        '--package-file', type=str, help="File with list of packages")
    parser.add_argument(
        '--skip-generic-analysis', action='store_true', default=False,
        help="Skip generic analysis - useful for purely package analysis.")

    # If no args, just display help and exit
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()

    # Process arguments:
    args = parser.parse_args()
    kwargs = vars(args)

    global VERBOSE
    global SUPER_VERBOSE
    VERBOSE = kwargs['verbose']
    SUPER_VERBOSE = kwargs['super_verbose']
    if SUPER_VERBOSE:
        VERBOSE = True

    _go(**kwargs)


if __name__ == "__main__":
    main()
    sys.exit()