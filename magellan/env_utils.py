"""Module containing Environment class.

Collection of methods concerning analysis of virtual environment.
"""

import logging
import os
import pickle
import re
import shlex
import subprocess
import sys

from magellan.utils import (run_in_subprocess, run_in_subp_ret_stdout,)
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

        # Pipdeptree:
        self.pdp_meta = {'generated': False, 'parsed': False,
                         'pdp_tree_file': '', 'pdp_err_file': '', }
        self.pdp_tree = {}
        self.pdp_errs = {}

        # Connectedness:
        self.connectedness = {}

        maglog.info("logging setup in Environment")

    def magellan_setup_go_env(self, kwargs):
        """ Set up environment for main script."""
        req_file = kwargs['install_requirements']
        if req_file:
            self.create_vex_new_virtual_env()

            pip_update_cmd = ("vex {} pip install pip --upgrade"
                              .format(self.name))

            if not kwargs['no_pip_update']:  # update pip
                print("RA"*100)
                run_in_subprocess(pip_update_cmd)
                self.vex_install_requirements(self.name, req_file,
                                              kwargs['pip_options'])

            self.vex_install_requirement(self.name, "pipdeptree", "")
        else:
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

    def create_vex_new_virtual_env(self):
        """Create a virtual env in which to install packages
        :returns : venv_name - name of virtual environment.
        :rtype : str
        """
        if self.name is None:
            venv_template = "MagEnv{}"
            # check if name exists and bump repeatedly until new
            i = 0
            while True:
                self.name = venv_template.format(i)
                if not self.vex_check_venv_exists(self.name):
                    run_in_subprocess("vex -m {} true".format(self.name))
                    break
                i += 1
        else:
            if self.vex_check_venv_exists(self.name):
                # vex -r removes virtual env
                run_in_subprocess("vex -r {} true".format(self.name))

        # vex -m ; makes env
        print("Creating virtual env: {}".format(self.name))
        run_in_subprocess("vex -m {} true".format(self.name))

    @staticmethod
    def vex_check_venv_exists(venv_name):
        """ Checks whether a virtual env exists using vex.
        :return : Bool if env exists or not."""
        vex_list = run_in_subp_ret_stdout('vex --list')[0].split("\n")
        return venv_name in vex_list

    @staticmethod
    def vex_install_requirements(env_name, req_file, pip_options):
        """ Installs requirements into virtual env
        :param req_file: Requirements to install
        :param pip_options:
        """
        cmd_to_run = ('vex {0} pip install -r {1} {2}'
                      .format(env_name, req_file, pip_options))
        run_in_subprocess(cmd_to_run)

    @staticmethod
    def vex_install_requirement(env_name, requirement, pip_options):
        """Install SINGLE requirement into env_name using vex."""
        cmd_to_run = ('vex {0} pip install {1} {2}'
                      .format(env_name, requirement, pip_options))
        run_in_subprocess(cmd_to_run)

    @staticmethod
    def vex_resolve_venv_name(venv_name=None):
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
            if not Environment.vex_check_venv_exists(venv_name):
                maglog.critical('Virtual Env "{}" does not exist, '
                                'please check name and try again'
                                .format(venv_name))
                sys.exit('LAPU LAPU! Virtual Env "{}" does not exist, '
                         'please check name and try again'.format(venv_name))
            name_bit = '_'

        return venv_name, name_bit

    @staticmethod
    def vex_remove_virtual_env(venv_name=None):
        """Removes virtual environment"""
        if venv_name is not None:
            run_in_subprocess("vex -r {} true".format(venv_name))

    def vex_delete_env_self(self):
        """Deletes itself as a virtual environment; be careful!"""
        self.vex_remove_virtual_env(self.name)

    def resolve_venv_bin(self, bin_path):
        """ Resolves the bin directory.
        """

        if not bin_path and self.name == '':
            self.bin = None
            return

        # If not supplied path, derive from v_name.
        if not bin_path and self.name:
            user = os.environ.get('USER')
            self.bin = ("/home/{0}/.virtualenvs/{1}/bin/"
                        .format(user, self.name))

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

        interrogation_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'interrogation_scripts',  'env_interrogation.py')

        # execute
        self.add_file_to_extant_env_files('nodes.p')
        self.add_file_to_extant_env_files('edges.p')
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
        self.nodes = pickle.load(open('nodes.p', 'rb'))
        self.edges = pickle.load(open('edges.p', 'rb'))

        self.package_requirements = pickle.load(
            open('package_requirements.p', 'rb'))
        self.add_file_to_extant_env_files('package_requirements.p')

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

    def gen_pipdeptree_reports(self,):
        """
        Runs pipdeptree and outputs analysis to disk.

        These are package agnostic, but need to be done if parsing for specific
        packages.
        """
        file_template = '{0}PDP_Output_{1}.txt'
        pdp_tree_file = file_template.format(self.name + self.name_bit, "Tree")
        pdp_err_file = file_template.format(self.name + self.name_bit, "Errs")

        self.pdp_meta['pdp_tree_file'] = pdp_tree_file
        self.pdp_meta['pdp_err_file'] = pdp_err_file

        maglog.info("Generating pipdeptree report")

        self._gen_pipdeptree_reports(
            out_file=pdp_tree_file, err_file=pdp_err_file)

        self.pdp_meta['generated'] = True

    def _gen_pipdeptree_reports(self, out_file, err_file):
        """ Helper function to do work for gen_pipdeptree_reports."""

        if not self.bin:
            cmd_args = shlex.split('pipdeptree')
        else:
            cmd_args = shlex.split('vex {0} pipdeptree'.format(self.name))
        try:
            with open(err_file, 'w') as efile, open(out_file, 'w') as ofile:
                _ = subprocess.call(cmd_args, stderr=efile, stdout=ofile)
        except Exception as e:
            maglog.exception("LAPU LAPU! Error {0} in analysis.py, "
                             "gen_pipdeptree_reports when attempting to run: "
                             "{1}".format(e, cmd_args))
            sys.exit()

    def parse_pipdeptree_reports(self):
        """Takes output from pipdeptree and returns dictionaries."""
        with open(self.pdp_meta['pdp_tree_file'], 'r') as f:
            self.pdp_tree = _parse_pipdeptree_output_file(f)
        with open(self.pdp_meta['pdp_err_file'], 'r') as f:
            self.pdp_errs = _parse_pipdeptree_error_file(f)
        self.pdp_meta['parsed'] = True

    def rm_pipdeptree_report_files(self):
        """
        Removes the pdp_meta['pdp_tree_file'] and pdp_meta['pdp_err_file']
        files.
        """
        files_to_remove = [
            self.pdp_meta['pdp_err_file'],
            self.pdp_meta['pdp_tree_file'],
        ]

        for f in files_to_remove:
            if os.path.exists(f):
                run_in_subprocess("rm {}".format(f))

    def write_dot_graph_to_disk(self):
        """Writes dependency graph of environment to disk as dot file."""
        dep_graph_name = "{}DependencyGraph.gv".format(self.name)
        _write_dot_graph_to_disk(self.nodes, self.edges, dep_graph_name)

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

    # todo (aj) refactor out repetition on connected nodes
    def connected_nodes(self, include_root=False):
        """
        Returns dictionary of how many nodes all nodes are connected to.

        If including root then everything is connected to everything.
        Root is env root.

        :return: dictionary of how many nodes any other is connected to.
        """
        if 'conn_nodes' not in self.connectedness:
            self._calc_connected_nodes(include_root)
        return self.connectedness['conn_nodes']

    def _calc_connected_nodes(self, include_root=False):
        """
        sets dictionary of how many nodes all nodes are connected to.

        If including root then everything is connected to everything.
        Root is env root.

        :return: dictionary of how many nodes any other is connected to.
        """
        conn_nodes = {}
        for n in self.nodes:
            n_key = n[0].lower()
            dist_dict = Package.calc_node_distances(
                n_key, self.nodes, self.edges, include_root,
                list_or_dict='dict')
            conn_nodes[n] = len(dist_dict)

        self.connectedness['conn_nodes'] = conn_nodes


def _parse_pipdeptree_output_file(f):
    """
    Takes a file object as input and parses that into a tree.

    Returns a graph as a dictionary
    """

    output = {'nodes': [], 'dependencies': {}}

    for line in f:
        level = len(re.search('(\s)+', line).group()) / 2
        if level < 1:
            # package_name = re.search('^[(A-Za-z)+\-*]+', line).group()
            package_name = re.search('.*==', line).group()[0:-2]
#            package_version = re.search('==[\d*\.*]*', line).group()[2:]
            package_version = re.search('==.*', line).group()[2:]
            # Add node if not extant:
            pv = (package_name, package_version)
            if pv not in output['nodes']:
                output['nodes'].append(pv)
            # update last package-version tuple if next line is dependency
            last_pv = pv
        else:  # process dependencies
            if last_pv not in output['dependencies']:
                output['dependencies'][last_pv] = []
            output['dependencies'][last_pv].append(line)

    return output


def _parse_pipdeptree_error_file(f):
    """Takes the output from pipdeptree stderr and parses into dictionary"""

    output = {}
    curr_node = ''

    f.readline()  # eat the head
    for line in f:
        if "-----" in line:  # eat the tail
            continue

        if "*" in line:  # new node
            curr_node = re.search('(->\s*).*\[', line).group()[3:-2]
            ancestor = re.search('.*->', line).group()[2:-3]
            output[curr_node] = {}
        else:
            ancestor = re.search('.*->', line)
            if ancestor is not None:
                ancestor = ancestor.group()[:-3]

        anc_name = re.search('.*==', ancestor).group()[0:-2]
        anc_ver = re.search('==.*', ancestor).group()[2:]

        tmp = re.search('\[.*\]', line).group()
        output[curr_node][(anc_name, anc_ver)] = tmp

    return output


def _write_dot_graph_to_disk(nodes, edges, filename):
    """
    Write dot graph to disk.
    :param nodes: list of nodes to write (package, version) tuple
    :param edges: list of connected nodes and optionally specs
    :param filename: string of output filename
    """

    node_template = 'n{}'
    node_index = {(nodes[x][0].lower(), nodes[x][1]): node_template.format(x+1)
                  for x in range(len(nodes))}
    node_index[('root', '0.0.0')] = node_template.format(0)

    # Fill in nodes
    node_template = '    {0} [label="{1}"];\n'

    with open(filename, 'wb') as f:

        f.write('digraph magout {\n')

        # Nodes
        f.write(node_template.format("n0", "root"))
        for n in node_index:
            f.write(node_template.format(node_index[n], n))

        # Fill in edge
        for e in edges:
            from_e = (e[0][0].lower(), e[0][1])
            to_e = (e[1][0].lower(), e[1][1])
            try:
                f.write("    {0} -> {1};\n"
                        .format(node_index[from_e], node_index[to_e]))
            except KeyError:
                pass  # don't write node if key error.

        f.write('}')
