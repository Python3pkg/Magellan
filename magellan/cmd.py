#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import virtualenv
from pprint import pprint

from magellan.utils import (run_in_subprocess, get_virtual_env_name,
                            resolve_venv_name,)

from magellan.analysis import (gen_pipdeptree_reports, parse_pipdeptree_file,
                               print_pdp_tree_parsed, direct_links_to_package,
                               write_dot_graph_to_disk_with_distance_colour,
                               calc_node_distances, calc_weighted_connections,
                               calc_connected_nodes, ancestor_trace,
                               write_dot_graph_subset, write_dot_graph_to_disk,
                               query_nodes_eges_in_venv)

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

    #################
    # INITIAL SETUP #
    #################
    req_file = kwargs['requirements']
    if req_file:  # Install requirements
        venv_name, env_exists = get_virtual_env_name(kwargs["venv_name"])
        if env_exists:
            # todo (aj) delete virtual env once on vex
            sys.exit("*env exists* TODO: Delete virtual env and then install")
        if VERBOSE:
            print("installing into virtual environment {}".format(venv_name))
        venv_bin = venv_name + '/bin/'
        name_bit = '_'

        # Install into virtual env
        # todo (aj) switch this to vex
        if VERBOSE:
            print("Creating virtualenv {}".format(venv_name))
            print("Installing requirements.")
        virtualenv.create_environment(venv_name)
        cmd_to_run = (venv_bin + 'pip install -r {0} {1}'
                      .format(req_file, kwargs["pip_options"]))
        run_in_subprocess(cmd_to_run)
        run_in_subprocess(venv_bin + 'pip install pipdeptree')
    else:
        venv_name, name_bit, venv_bin = resolve_venv_name(kwargs["venv_name"])

    # todo (aj) switch this fn. to vex
    nodes, edges = query_nodes_eges_in_venv(venv_bin)

    ####################
    # ANALYSIS SECTION #
    ####################
    show_all_packages_and_exit = kwargs['show_all_packages']
    if show_all_packages_and_exit:
        print('"Show all packages" selected. Nodes found:')
        pprint(nodes)
        sys.exit()

    # Pipdeptree
    # These are package agnostic, but need to be done if parsing for specific
    # packages. Would prefer to remove
    pdp_file_template = '{0}PDP_Output_{1}.txt'
    pdp_tree_file = pdp_file_template.format(venv_name + name_bit, "Tree")
    pdp_err_file = pdp_file_template.format(venv_name + name_bit, "Errs")
    if VERBOSE:
        print("Generating pipdeptree report")
    gen_pipdeptree_reports(
        venv_bin=venv_bin, out_file=pdp_tree_file, err_file=pdp_err_file)
    # Parse pipdeptree reports
    if VERBOSE:
        print("Parsing pipdeptree report and outputting to: {0} and {1}"
              .format(pdp_tree_file, pdp_err_file))

    pdp_tree_parsed = parse_pipdeptree_file(
        pdp_tree_file, output_or_error="output")
    pdp_errs_parsed = parse_pipdeptree_file(
        pdp_err_file, output_or_error="error")

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
        write_dot_graph_to_disk_with_distance_colour(
            nodes, edges, 'abs_card.gv', abs_conn)

        wghtd_conn, sq_wghtd_conn = calc_weighted_connections(nodes, edges)

        write_dot_graph_to_disk_with_distance_colour(
            nodes, edges, 'weighted_card.gv', wghtd_conn)

        write_dot_graph_to_disk_with_distance_colour(
            nodes, edges, 'sq_weighted_card.gv', sq_wghtd_conn)

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

            ft = '{}_anc_track.gv'
            write_dot_graph_to_disk_with_distance_colour(
                nodes, edges, ft.format(package), anc_track)

            ft = '{}_anc_track_trunc.gv'
            write_dot_graph_subset(
                nodes, edges, ft.format(package), anc_track)
            del ft


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
        help="Show all packages and exit."
    )
    parser.add_argument(
        '-n', '--venv-name', default=None,
        help=("Specify name for virtual environment, "
              "default is MagEnv0, MagEnv1 etc")
    )
    parser.add_argument(
        '-r', '--requirements', type=str,
        help="requirements file (e.g. requirements.txt) to install."
    )
    pip_options = ("-f http://sw-srv.maplecroft.com/deployment_libs/ "
                   "--trusted-host sw-srv.maplecroft.com")
    parser.add_argument(
        '-po', '--pip-options', type=str, default=pip_options,
        help=("String. Pip options for installation of requirements.txt. "
              "E.g. '-f http://sw-srv.maplecroft.com/deployment_libs/ "
              "--trusted-host sw-srv.maplecroft.com'")
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help="Verbose mode"
    )
    parser.add_argument(
        '-sv', '--super-verbose', action='store_true', default=False,
        help="Super verbose mode; also sets VERBOSE as True."
    )

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