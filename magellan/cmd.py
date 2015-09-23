#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import logging
import sys
import pkg_resources

from magellan.utils import MagellanConfig

maglog = logging.getLogger('magellan_logger')

def cmds():
    """Commands for magellan."""

    parser = argparse.ArgumentParser(
        prog="Magellan",
        description=("Explore Python Package Dependencies "
                     "like your name is Fernando!"),
    )
    parser.add_argument('packages', nargs='*', type=str,
                        help="Packages to explore.")

    parser.add_argument(
        '-f', '--package-file', type=str, metavar="<package_file>",
        help="File with list of packages")
    parser.add_argument(
        '-r', '--requirements-file', type=str, metavar="<requirements_file>",
        help="requirements file (e.g. requirements.txt) to check.")

    # Optional Arguments
    parser.add_argument(
        '-n', '--venv-name', default=None, metavar="<venv_name>",
        help=("Specify name of virtual environment, "
              "if nothing Magellan will use current environment."))

    parser.add_argument(
        '-A', '--get-ancestors', action='append', nargs=1,
        metavar="<package-name>",
        help="Show which packages in environment depend on <package-name>")
    parser.add_argument(
        '-Z', '--get-descendants', action='append', nargs=1,
        metavar="<package-name>",
        help="Show which packages in environment <package-name> depends on; "
             "can be useful if package not on PyPI.")
    parser.add_argument(
        '-D', '--get-dependencies', action='append', nargs=2,
        metavar=("<package-name>", "<version>"),
        help=("Get dependencies of package, version combo, from PyPI. "
              "NB Can be used multiple times but must always specify desired "
              "version.  Usage -D <package-name> <version>."))
    parser.add_argument(
        '-C', '--detect-env-conflicts', action='store_true', default=False,
        help="Runs through installed packages in specified environment to "
             "detect if there are any conflicts between dependencies and "
             "versions.")
    parser.add_argument(
        '-P', '--package-conflicts', action='append', nargs=2,
        metavar=("<package-name>", "<version>"),
        help=("Check whether a package will conflict with the current "
              "environment, either through addition or change. NB Can be used "
              "multiple times but must always specify desired version. "
              "Usage -P <package-name> <version>."))

    parser.add_argument(
        '-O', '--outdated', action='store_true', default=False,
        help=("Checks whether the major/minor versions of a package "
              "are outdated."))

    parser.add_argument(
        '-R', '--compare-env-to-req-file', action='store_true', default=False,
        help="Compare a requirements file to an environment."
    )

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

    # Configuration
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help="Verbose mode")
    parser.add_argument(
        '--super-verbose', action='store_true', default=False,
        help="Super verbose mode")

    parser.add_argument(
        '--path-to-env-bin', default=None, metavar="<path-to-env-bin>",
        help="Path to virtual env bin")
    parser.add_argument(
        '--cache-dir', type=str, default=MagellanConfig.cache_dir,
        metavar="<cache-dir>",
        help="Cache directory - used for pip installs.")
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
    parser.add_argument(
        '--colour', '--color', action='store_true', default=False,
        help="Prints output to console with pretty colours.")

    mag_ver = [x for x in pkg_resources.working_set
               if x.key == 'magellan'][0].version
    parser.add_argument('--version', action='version', version=mag_ver)

    # If no args, just display help and exit
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()

    # Process arguments:
    args = parser.parse_args()
    kwargs = vars(args)

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

    return kwargs