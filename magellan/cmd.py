#!/usr/bin/env python
# -*- coding: utf-8 -*-

# todo (security) remove default pip options before making repo public!!

import argparse
import os
import sys
from pprint import pprint

from magellan.package_utils import Package

from magellan.env_utils import Environment

from magellan.analysis import (
    write_dot_graph_to_disk_with_distance_colour, write_dot_graph_subset,)

from magellan.reports import produce_pdp_package_report

from magellan.utils import MagellanConfig

from magellan.deps_utils import DepTools

VERBOSE = False
SUPER_VERBOSE = False


def _go(venv_name, **kwargs):
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
    # todo (aj) update above.

    global VERBOSE
    global SUPER_VERBOSE

    skip_generic_analysis = kwargs['skip_generic_analysis']

    check_versions = kwargs['check_versions']
    if check_versions:
        skip_generic_analysis = True

    # Environment Setup
    if not os.path.exists(MagellanConfig.cache_dir) and MagellanConfig.caching:
        MagellanConfig.setup_cache()

    venv = Environment(venv_name)
    venv.magellan_setup_go_env(kwargs)

    package_list = Package.resolve_package_list(venv, kwargs)
    packages = {p.lower(): venv.all_packages[p.lower()] for p in package_list}

    if kwargs['upgrade_conflicts']:
        DepTools.detect_upgrade_conflicts(kwargs['upgrade_conflicts'])

    sys.exit()

    # Analysis
    if package_list or not skip_generic_analysis:
        # pipdeptree reports are parsed for individual package analysis.
        venv.gen_pipdeptree_reports(VERBOSE)
        venv.parse_pipdeptree_reports()

    # todo (aj) NBNBNBNBNBNBNBNBNBNB refactor prox.onda
    skip_generic_analysis = True
    # Generic Analysis - package-agnostic reports
    if not skip_generic_analysis:
        venv.write_dot_graph_to_disk()
        # Calculate connectedness of graph
        # todo (aj) profile and speed up! ..all nodes as Packages! proxima onda
        f = output_dir + 'abs_card.gv'
        write_dot_graph_to_disk_with_distance_colour(
            venv, f, venv.connected_nodes())
        f = output_dir + 'weighted_card.gv'
        write_dot_graph_to_disk_with_distance_colour(
            venv, f, venv.weighted_connections())
        f = output_dir + 'sq_weighted_card.gv'
        write_dot_graph_to_disk_with_distance_colour(
            venv, f, venv.sq_weighted_connections())

    # Package Specific Analysis
    if package_list:
        
        if check_versions:
            for p_k, p in packages.items():
                print("Analysing {}".format(p.name))
                _, _ = p.check_versions()
            sys.exit(0)

        for p_k, p in packages.items():
            if VERBOSE:
                print("Analysing {}".format(p.name))

            f_template = output_dir + "Mag_Report_{}.txt"
            produce_pdp_package_report(
                p.name, venv.pdp_tree, venv.pdp_errs, f_template, VERBOSE)

            f = output_dir + '{}.gv'.format(p.name)
            write_dot_graph_to_disk_with_distance_colour(
                venv, f, p.calc_self_node_distances(venv))

            if SUPER_VERBOSE:
                print("\n" + "-" * 50 + "\n" + p.name + "\n")
                print("DIRECT DESCENDENTS - depended on by {}".format(p.name))
                pprint(p.descendants(venv.edges))
                print("DIRECT ANCESTORS - these depend on {}".format(p.name))
                pprint(p.ancestors(venv.edges))

            # Ancestor trace of package
            f = output_dir + '{}_anc_track.gv'
            write_dot_graph_to_disk_with_distance_colour(
                venv, f.format(p.name), p.ancestor_trace(venv))

            f = output_dir + '{}_anc_track_trunc.gv'
            write_dot_graph_subset(
                venv, f.format(p.name), p.ancestor_trace(venv))


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
        help="Show all packages by name and exit.")
    parser.add_argument(
        '-p', '--show-all-packages-and-versions', action='store_true',
        default=False, help="Show all packages with versions and exit.")
    parser.add_argument(
        '-n', '--venv-name', default=None,
        help=("Specify name for virtual environment, "
              "default is MagEnv0, MagEnv1 etc"))
    parser.add_argument(
        '-r', '--requirements', type=str,
        help="requirements file (e.g. requirements.txt) to install.")
    # todo (aj) change this before release
    pip_options = ("-f http://sw-srv.maplecroft.com/deployment_libs/ "
                   "--trusted-host sw-srv.maplecroft.com ")

    parser.add_argument(
        '-o', '--pip-options', type=str, default=pip_options,
        help=("String. Pip options for installation of requirements.txt. "
              "E.g. '-f http://my_server.com/deployment_libs/ "
              "--trusted-host my_server.com'"))
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help="Verbose mode")
    parser.add_argument(
        '--super-verbose', action='store_true', default=False,
        help="Super verbose mode; also sets VERBOSE as True.")
    parser.add_argument(
        '--path-to-env-bin', default=None, help="Path to virtual env bin")
    parser.add_argument(
        '-f', '--package-file', type=str, help="File with list of packages")
    parser.add_argument(
        '--skip-generic-analysis', action='store_true', default=False,
        help="Skip generic analysis - useful for purely package analysis.")
    parser.add_argument(
        '-c', '--check-versions', action='store_true', default=False,
        help=("Just checks the versions of input packages and exits. "
              "Make sure this is not superseded by '-s'"))
    parser.add_argument(
        '--output-dir', type=str, default="MagellanReports/",
        help=("Set output directory for package specific reports, "
              "default = 'MagellanReports'"))
    parser.add_argument(
        '-U', '--upgrade-conflicts', action='append', nargs=2,
        help=("Check whether upgrading a package will conflict with the "
              "current environment. NB Can be used multiple times but must "
              "always specify desired version. "
              "Usage -U <package-name> <desired-version>."))
    parser.add_argument(
        '--cache-dir', type=str, default=MagellanConfig.cache_dir,
        help="Cache directory - used for pip installs.")

    # If no args, just display help and exit
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()

    # Process arguments:
    args = parser.parse_args()
    kwargs = vars(args)

    # Update cache options
    kwargs['pip_options'] += " --cache-dir {}".format(kwargs['cache_dir'])

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
