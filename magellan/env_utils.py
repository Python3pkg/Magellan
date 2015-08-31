"""Module containing Environment class.

Collection of methods concerning analysis of virtual environment.
"""

import logging
import json
import os
import sys
from pkg_resources import resource_filename as pkg_res_resource_filename

from magellan.utils import (run_in_subprocess,
                            run_in_subp_ret_stdout,
                            MagellanConfig,)
from magellan.package_utils import Package

# Logging:
maglog = logging.getLogger("magellan_logger")
maglog.info("Env imported")


class Environment(object):
    """ Environment class."""

    def __init__(self, name=None):
        self.name = name
        self.name_bit = ''
        self.bin = None
        self.nodes = []
        self.edges = []
        self.package_requirements = {}
        self.all_packages = {}
        self.extant_env_files = []

        maglog.info("logging setup in Environment")

    def magellan_setup_go_env(self, kwargs):
        """ Set up environment for main script."""

        self.name, self.name_bit = self.vex_resolve_venv_name(self.name)

        self.resolve_venv_bin(kwargs['path_to_env_bin'])

        self.query_nodes_edges_in_venv()
        if not kwargs['keep_env_files']:
            self.remove_extant_env_files_from_disk()

        self.all_packages = {p[0].lower(): Package(p[0], p[1]) 
                             for p in self.nodes}

        if (kwargs['show_all_packages'] or
                kwargs['show_all_packages_and_versions']):
            self.show_all_packages_and_exit(
                kwargs['show_all_packages_and_versions'])

    def create_vex_new_virtual_env(self, vex_options=None):
        """Create a virtual env in which to install packages
        :returns : venv_name - name of virtual environment.
        :rtype : str
        """

        if vex_options is None:
            vex_options = ''
        if self.name is None:
            venv_template = "MagEnv{}"
            # check if name exists and bump repeatedly until new
            i = 0
            while True:
                self.name = venv_template.format(i)
                if not self.vex_check_venv_exists(self.name, vex_options):  # make env
                    break
                i += 1
        else:
            if self.vex_check_venv_exists(self.name, vex_options):
                # vex -r removes virtual env
                run_in_subprocess("vex {} -r {} true".format(
                    vex_options, self.name))

        # vex -m ; makes env
        print("Creating virtual env: {}".format(self.name))
        run_in_subprocess("vex {} -m {} true".format(vex_options, self.name))

    @staticmethod
    def vex_check_venv_exists(venv_name, vex_options=None):
        """ Checks whether a virtual env exists using vex.
        :return : Bool if env exists or not."""

        if vex_options is None:
            vex_options = ''
        vex_list = run_in_subp_ret_stdout('vex {} --list'.format(vex_options))
        return venv_name in vex_list[0].decode('utf-8').split("\n")

    @staticmethod
    def vex_install_requirement(install_location, requirement, pip_options,
                                vex_options=None):
        """Install SINGLE requirement into env_name using vex.

        install_location is either the NAME of a virtual env or will be
        the path, specified as "--path /path/to/env"

        """
        if vex_options is None:
            vex_options = ''

        cmd_to_run = ('vex {} {} pip install {} {}'.format(
            vex_options, install_location, requirement, pip_options))
        run_in_subprocess(cmd_to_run)

    @staticmethod
    def vex_resolve_venv_name(venv_name=None, vex_options=None):
        """Check whether virtual env exists,
        if not then indicate to perform analysis on current environment"""

        if venv_name is None:
            maglog.info("No virtual env specified, analysing local env")
            venv_name = ''
            name_bit = ''
        else:
            venv_name = venv_name.rstrip('/')
            maglog.info("Locating {} environment".format(venv_name))
            # First check specified environment exists:
            if not Environment.vex_check_venv_exists(venv_name, vex_options):
                maglog.critical('Virtual Env "{}" does not exist, '
                                'please check name and try again'
                                .format(venv_name))
                sys.exit('LAPU LAPU! Virtual Env "{}" does not exist, '
                         'please check name and try again'.format(venv_name))
            name_bit = '_'

        return venv_name, name_bit

    @staticmethod
    def vex_remove_virtual_env(venv_name=None, vex_options=None):
        """Removes virtual environment"""
        if vex_options is None:
            vex_options = ''
        if venv_name is not None:
            run_in_subprocess("vex {} -r {} true".format(
                vex_options, venv_name))

    def vex_delete_env_self(self):
        """Deletes itself as a virtual environment; be careful!"""
        self.vex_remove_virtual_env(self.name,
                                    vex_options=MagellanConfig.vex_options)

    def resolve_venv_bin(self, bin_path):
        """ Resolves the bin directory.
        """

        if not bin_path and self.name == '':
            self.bin = None
            return

        # If not supplied path, derive from v_name.
        if not bin_path and self.name:
            user = os.environ.get('USER')
            venv_home = os.environ.get('WORKON_HOME')
            if not venv_home:
                venv_home = "/home/{}/.virtualenvs".format(user)
            specific_venv_dir = "{}/bin/".format(self.name)
            self.bin = os.path.join(venv_home, specific_venv_dir)

        # Check path and/or derived path.
        if bin_path:
            if not os.path.exists(bin_path):
                sys.exit('LAPU LAPU! {} does not exist, please specify path to'
                         ' {} bin using magellan -n ENV_NAME --path-to-env-bin'
                         ' ENV_BIN_PATH'.format(self.bin, self.name))
            else:
                self.bin = bin_path

    def query_nodes_edges_in_venv(self):
        """Generate Nodes and Edges of packages in virtual env.
        :rtype list, list
        :return: nodes, edges
        """

        interrogation_file = pkg_res_resource_filename(
            'magellan', 'env_interrogation.py')

        # execute
        self.add_file_to_extant_env_files('nodes.json')
        self.add_file_to_extant_env_files('edges.json')
        try:
            if self.name == "":
                run_in_subprocess("python {}".format(interrogation_file))
            else:
                run_in_subprocess("vex {0} python {1}"
                                  .format(self.name, interrogation_file))
        except Exception as e:
            maglog.exception(e)
            # Cleanup:
            self.remove_extant_env_files_from_disk()
            sys.exit("Error {} when trying to interrogate environment."
                     .format(e))

        # Load in nodes and edges pickles
        self.nodes = json.load(open('nodes.json', 'r'))
        self.edges = json.load(open('edges.json', 'r'))

        self.package_requirements = json.load(
            open('package_requirements.json', 'r'))
        self.add_file_to_extant_env_files('package_requirements.json')

    def add_file_to_extant_env_files(self, file_to_add):
        """
        Add file to list of existing environment files, to keep track for
        deletion.
        :param file_to_add: str, filename to add to self.extant_env_files list
        """
        self.extant_env_files.append(file_to_add)

    @staticmethod
    def remove_env_file_from_disk(file_to_remove):
        """
        Delete file from disk.
        :param file_to_remove: str, file to delete.
        """
        if os.path.exists(file_to_remove):
            run_in_subprocess('rm {}'.format(file_to_remove))

    def remove_extant_env_files_from_disk(self, to_remove=None):
        """
        Removes all files in self.extant_env_files
        :param list to_remove: list of files to remove, empty list remove
        all files.
        """
        if to_remove:  # remove all files if no list given
            for f in to_remove:
                self.remove_env_file_from_disk(f)
            self.extant_env_files = [x for x in self.extant_env_files
                                     if x not in to_remove]
        else:
            for f in self.extant_env_files:
                self.remove_env_file_from_disk(f)
            self.extant_env_files = []

    def show_all_packages_and_exit(self, with_versions=False):
        """ Prints nodes and exits"""
        maglog.info('"Show all packages" selected. Nodes found:')
        for _, p in self.all_packages.items():
            if with_versions:
                print("{0} : {1} ".format(p.name, p.version))
            else:
                print(p.name)  # just show nodes
        sys.exit(0)

    def package_in_env(self, package):
        """Interrogates current environment for existence of package.

        :param package: str package name
        :rtype bool, (str, str):
        :returns: True if package exists in env with (project_name, version)
        False if not with (None, None)
        """

        p_key = package.lower()
        if p_key in self.package_requirements.keys():
            return True, (
                self.package_requirements[p_key]['project_name'],
                self.package_requirements[p_key]['version'], )
        else:
            return False, (None, None)
