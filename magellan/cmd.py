#!/usr/bin/env python
# -*- coding: utf-8 -*-
# todo (security) remove default pip options before making repo public!!

from __future__ import print_function

import argparse
import logging
import os
import sys
from pprint import pprint, pformat


from magellan.utils import MagellanConfig
from magellan.env_utils import Environment
from magellan.package_utils import Package
from magellan.deps_utils import DepTools, PyPIHelper
from magellan.analysis import (
    write_dot_graph_to_disk_with_distance_colour, write_dot_graph_subset,)
from magellan.reports import produce_pdp_package_report

maglog = logging.getLogger('magellan_logger')

def _go(venv_name, **kwargs):
    """Main script of magellan program.
    
    If passed a requirements file it will install those requirements into
    a fresh virtual environment. If that environment exists, it shall be
    deleted and a new one setup for installation.

    If an environment is passed in but doesn't exist, then exit.
    If no environment is passed in, do analysis on current env.

    If packages are specified then do package specific analysis.
    Otherwise perform general analysis on environment.
    """

    if kwargs['list_all_versions']:
        for p in kwargs['list_all_versions']:
            print(p[0])
            pprint(sorted(PyPIHelper.all_package_versions_on_pypi(p[0])))
        sys.exit()

    # Environment Setup
    if not os.path.exists(MagellanConfig.cache_dir) and MagellanConfig.caching:
        MagellanConfig.setup_cache()

    venv = Environment(venv_name)
    venv.magellan_setup_go_env(kwargs)

    package_list = Package.resolve_package_list(venv, kwargs)
    packages = {p.lower(): venv.all_packages[p.lower()] for p in package_list}

    if kwargs['check_versions']:
        if package_list:
            Package.check_outdated_packages(packages)
        else:
            Package.check_outdated_packages(venv.all_packages)
        sys.exit()

    MagellanConfig.setup_output_dir(kwargs, package_list)

    if kwargs['get_dependencies']:
        DepTools.acquire_and_display_dependencies(kwargs['get_dependencies'])

    if kwargs['package_conflicts']:
        addition_conflicts, upgrade_conflicts = \
            DepTools.process_package_conflicts(
                kwargs['package_conflicts'], venv)

    if kwargs['detect_env_conflicts']:
        cur_env_conflicts = DepTools.highlight_conflicts_in_current_env(
            venv.nodes, venv.package_requirements)

    # Analysis
    if package_list:
        # pipdeptree reports are parsed for individual package analysis.
        venv.gen_pipdeptree_reports()
        venv.parse_pipdeptree_reports()
        if not kwargs['keep_pipdeptree_output']:
            venv.rm_pipdeptree_report_files()

        for p_k, p in packages.items():
            print("Analysing {}".format(p.name))

            # todo (aj) Improve output Mag Report with conflict & outdated info
            f_template = os.path.join(
                MagellanConfig.output_dir, "Mag_Report_{}.txt")
            produce_pdp_package_report(
                p.name, venv.pdp_tree, venv.pdp_errs, f_template)

            maglog.info(p.name)

            maglog.info("Package Descendants - depended on by {}".format(p.name))
            maglog.debug(pformat(p.descendants(venv.edges)))

            maglog.info("Package Ancestors - these depend on {}".format(p.name))
            maglog.debug(pformat(p.ancestors(venv.edges)))

            if kwargs['output_dot_file']:
                f = os.path.join(MagellanConfig.output_dir, '{}.gv'
                                 .format(p.name))
                write_dot_graph_to_disk_with_distance_colour(
                    venv, f, p.calc_self_node_distances(venv))

            if kwargs['get_ancestor_trace']:  # Ancestor trace of package
                f = os.path.join(MagellanConfig.output_dir,
                                 '{}_anc_track.gv'.format(p.name))
                write_dot_graph_to_disk_with_distance_colour(
                    venv, f, p.ancestor_trace(venv))

                f = os.path.join(MagellanConfig.output_dir,
                                 '{}_anc_track_trunc.gv'.format(p.name))
                write_dot_graph_subset(venv, f, p.ancestor_trace(venv))


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

    # Positional Arguments
    parser.add_argument('packages', nargs='*', type=str,
                        help="Packages to explore.")

    # Optional Arguments
    # Fundamental:
    parser.add_argument(
        '-n', '--venv-name', default=None, metavar="<venv_name>",
        help=("Specify name for virtual environment, "
              "default is MagEnv0, MagEnv1 etc"))
    parser.add_argument(
        '-r', '--install-requirements', type=str, metavar="<requirements_file>",
        help="requirements file (e.g. requirements.txt) to install.")

    # Functional with output
    parser.add_argument(
        '-l', '--list-all-versions', action='append', nargs=1, type=str,
        metavar="<package>",
        help="List all versions of package on PyPI and exit. NB Can be used "
             "multiple times")
    parser.add_argument(
        '-s', '--show-all-packages', action='store_true', default=False,
        help="Show all packages by name and exit.")
    parser.add_argument(
        '-p', '--show-all-packages-and-versions', action='store_true',
        default=False, help="Show all packages with versions and exit.")
    parser.add_argument(
        '-c', '--check-versions', action='store_true', default=False,
        help=("Just checks the versions of input packages and exits. "
              "Make sure this is not superseded by '-s'"))
    parser.add_argument(
        '-P', '--package-conflicts', action='append', nargs=2,
        metavar=("<package-name>", "<version>"),
        help=("Check whether a package will conflict with the current "
              "environment, either through addition or change. NB Can be used "
              "multiple times but must always specify desired version. "
              "Usage -P <package-name> <version>."))
    parser.add_argument(
        '-D', '--get-dependencies', action='append', nargs=2,
        metavar=("<package-name>", "<version>"),
        help=("Get dependencies of package, version combo, from PyPI. "
              "NB Can be used multiple times but must always specify desired "
              "version.  Usage -D <package-name> <version>."))
    parser.add_argument(
        '-d', '--detect-env-conflicts', action='store_true', default=False,
        help="Runs through installed packages in specified environment to "
             "detect if there are any conflicts between dependencies and "
             "versions.")
    parser.add_argument(
        '--output-dot-file', action='store_true', default=False,
        help="Output a .gv file showing connectedness of package.")
    parser.add_argument(
        '--get-ancestor-trace', action='store_true', default=False,
        help="Output .gv files showing ancestor trace of package and a "
             "truncated version.")

    # Configuration
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help="Verbose mode")
    parser.add_argument(
        '--super-verbose', action='store_true', default=False,
        help="Super verbose mode")

    # todo (aj) change this before release
    pip_options = ("-f http://sw-srv.maplecroft.com/deployment_libs/ "
                   "--trusted-host sw-srv.maplecroft.com ")
    parser.add_argument(
        '-o', '--pip-options', type=str, default=pip_options,
        metavar="pip_string",
        help=("String. Pip options for installation of requirements.txt. "
              "E.g. '-f http://my_server.com/deployment_libs/ "
              "--trusted-host my_server.com'"))
    parser.add_argument(
        '--path-to-env-bin', default=None, metavar="<path-to-env-bin>",
        help="Path to virtual env bin")
    parser.add_argument(
        '-f', '--package-file', type=str, metavar="<package_file>",
        help="File with list of packages")
    parser.add_argument(
        '--output-dir', type=str, default=MagellanConfig.output_dir,
        metavar="<output_dir>",
        help=("Set output directory for package specific reports, "
              "default = 'MagellanReports'"))
    parser.add_argument(
        '--cache-dir', type=str, default=MagellanConfig.cache_dir,
        metavar="<cache-dir>",
        help="Cache directory - used for pip installs.")
    parser.add_argument(
        '--keep-pipdeptree-output', action='store_true', default=False,
        help="Don't delete the pipdeptree output reports.")
    parser.add_argument(
        '--keep-env-files', action='store_true', default=False,
        help="Don't delete the nodes, edges, package_requirements env files.")
    parser.add_argument(
        '--no-pip-update', action='store_true', default=False,
        help="If invoked will not update to latest version of pip when"
             "creating new virtual env.")
    parser.add_argument(
        '--logfile', action='store_true', default=False,
        help="Set this flag to enable output to magellan.log."
    )

    # If no args, just display help and exit
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()

    # Process arguments:
    args = parser.parse_args()
    kwargs = vars(args)

    # Update cache options
    if "--cache-dir" not in kwargs['pip_options']:
        kwargs['pip_options'] += " --cache-dir {}".format(kwargs['cache_dir'])

    # Logging depends on verbosity level:
    ch = logging.StreamHandler()  # Console handler
    ch.setFormatter(logging.Formatter("MagLog %(levelname)s: %(message)s"))
    maglog.addHandler(ch)

    if kwargs['logfile']:
        fh = logging.FileHandler("magellan.log")  # file handler
        fh.setFormatter(logging.Formatter("MagLog %(levelname)s: %(message)s"))
        fh.setLevel(logging.DEBUG)
        maglog.addHandler(fh)
        del fh

    if kwargs['verbose']:
        maglog.setLevel(logging.INFO)
        ch.setLevel(logging.INFO)
        maglog.info("Maglog verbose mode")
    if kwargs['super_verbose']:
        maglog.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
        maglog.debug("Maglog super verbose mode")

    del ch

    # **************** #
    # run main script: #
    # **************** #
    _go(**kwargs)


if __name__ == "__main__":
    main()
    sys.exit()
