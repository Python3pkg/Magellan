#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import logging
import os
import sys
from pprint import pprint

from natsort import natsorted

from magellan.utils import MagellanConfig
from magellan.env_utils import Environment
from magellan.package_utils import Package, Requirements
from magellan.deps_utils import DepTools, PyPIHelper
from magellan.cmd import cmds

maglog = logging.getLogger('magellan_logger')


def _go(venv_name, **kwargs):
    """Main script of magellan program.

    If an environment is passed in but doesn't exist, then exit.
    If no environment is passed in, do analysis on current env.

    If packages are specified then do package specific analysis.
    Otherwise perform general analysis on environment.
    """

    print_col = kwargs.get('colour')  # print in colour

    # Environment Setup
    if not os.path.exists(MagellanConfig.cache_dir) and MagellanConfig.caching:
        MagellanConfig.setup_cache()

    if kwargs['list_all_versions']:
        for p in kwargs['list_all_versions']:
            print(p[0])
            all_package_versions = PyPIHelper.all_package_versions_on_pypi(
                p[0])
            pprint(natsorted(all_package_versions))
        sys.exit()

    venv = Environment(venv_name)
    venv.magellan_setup_go_env(kwargs)

    requirements_file = kwargs.get('requirements_file')

    package_list = Package.resolve_package_list(venv, kwargs)
    packages = {p.lower(): venv.all_packages[p.lower()] for p in package_list}

    if kwargs['outdated']:
        if package_list:
            Package.check_outdated_packages(packages, print_col)
        elif requirements_file:
            print("Analysing requirements file for outdated packages.")
            Requirements.check_outdated_requirements_file(
                requirements_file, pretty=print_col)
        else:  # if nothing passed in then check local env.
            Package.check_outdated_packages(venv.all_packages, print_col)

        sys.exit()

    if kwargs['get_dependencies']:  # -D
        DepTools.acquire_and_display_dependencies(
            kwargs['get_dependencies'], print_col)

    if kwargs['get_ancestors']:  # -A
        ancestor_dictionary = \
            DepTools.get_ancestors_of_packages(
                kwargs['get_ancestors'], venv, print_col)

    if kwargs['get_descendants']:  # -Z
        descendants_dictionary = \
            DepTools.get_descendants_of_packages(
                kwargs['get_descendants'], venv, print_col)

    if kwargs['package_conflicts']:  # -P
        addition_conflicts, upgrade_conflicts = \
            DepTools.process_package_conflicts(
                kwargs['package_conflicts'], venv, print_col)

    if kwargs['detect_env_conflicts']:  # -C
        cur_env_conflicts = DepTools.highlight_conflicts_in_current_env(
            venv.nodes, venv.package_requirements, print_col)

    if kwargs['compare_env_to_req_file']:  # -R
        if not requirements_file:
            print("Please specify a requirements file with -r <file>")
        else:
            same, verdiff, req_only, env_only = \
                Requirements.compare_req_file_to_env(requirements_file, venv)
            Requirements.print_req_env_comp_lists(
                same, verdiff, req_only, env_only, print_col)




def main():
    kwargs = cmds()
    _go(**kwargs)


if __name__ == "__main__":
    main()
