import os
import operator
from pkg_resources import parse_version
import requests
import json

from magellan.package_utils import Package
from magellan.env_utils import Environment
from magellan.utils import MagellanConfig, run_in_subprocess


class DepTools(object):
    """Tools for conflict detection."""

    @staticmethod
    def check_changes_in_requirements_vs_env(requirements, descendants):
        """
        Checks to see if there are any new or removed packages in a
        requirements set vs what is currently in the env.
        NB: Checks name only, not version!

        :param dict requirements:
        :param list descendants: current env dependencies of package.
        :rtype: dict{list, list}
        :returns {new_deps, removed_deps} : new and removed(from previous
        dependency requirements) dependencies.

        requirements = DepTools.get_deps_for_package_version(package, version)

        descendants look like a list of edges in acyclic graph e.g.:
            [..[('celery', '3.0.19'), ('kombu', '2.5.16')
                , [('>=', '2.5.10'), ('<', '3.0')]]..[] etc]
            (NB: specs are optional)
        """
        dec_keys = {x[1][0].lower(): x[1][0] for x in descendants}

        rec_keys = {x['key']: x['project_name']
                    for x in requirements['requires'].values()}

        dset = set(dec_keys.keys())
        rset = set(rec_keys.keys())

        removed_deps = [dec_keys[x] for x in (dset - rset)]
        new_deps = [rec_keys[x] for x in (rset - dset)]

        # return new_deps, removed_deps  # as list
        out = {'removed_deps': removed_deps, 'new_deps': new_deps}
        return out

    @staticmethod
    def check_req_deps_satisfied_by_current_env(requirements, nodes):
        """
        Checks nodes (package, version) of current environment against
        requirements to see if they are satisfied

        :param dict requirements:
        requirements = DepTools.get_deps_for_package_version(package, version)

        :param list nodes: current env nodes (package, version) tuples list

        :rtype dict{dict, dict, list}
        :returns: to_return{checks, conflicts, missing}

        "checks" is a dictionary of the current checks
        "conflicts" has at least 1 conflict with required specs
        "missing" highlights any packages that are not in current environment

        """

        check_ret = DepTools.check_requirement_satisfied
        node_keys = {x[0].lower(): x[1] for x in nodes}

        checks = {}
        conflicts = {}
        missing = []

        for r in requirements['requires'].values():
            key = r['key']
            project_name = r['project_name']
            specs = r['specs']
            checks[project_name] = []

            if key not in node_keys.keys():
                print("Requirement {0}{1} not in current environment"
                      .format(project_name, specs))
                checks[project_name].append(None)
                missing.append(project_name)
            else:
                for s in specs:
                    req_satisfied, req_dets = check_ret(node_keys[key], s)
                    # print(req_dets)
                    checks[project_name].append(req_dets)
                    if not req_satisfied:
                        if project_name not in conflicts:
                            conflicts[project_name] = [req_dets]
                        else:
                            conflicts[project_name].append(req_dets)

        to_return = {
            'checks': checks,
            'conflicts': conflicts,
            'missing': missing,
        }
        return to_return

    @staticmethod
    def check_requirement_satisfied(cur_ver, requirement_spec):
        """ tests to see whether a requirement is satisfied by the
        current version.
        :param str cur_ver: current version to use for comparison.
        :param tuple (str, str) requirement_spec: is tuple of: (spec, version)
        :returns: bool

        """

        ops = {'<': operator.lt, '<=': operator.le,
           '==': operator.eq, '!=': operator.ne,
           '>=': operator.ge, '>': operator.gt, }

        requirement_ver = requirement_spec[1]
        requirement_sym = requirement_spec[0]

        requirement_met = ops[requirement_sym](
            parse_version(cur_ver), parse_version(requirement_ver))

        # print(cur_ver, requirement_sym, requirement_ver, requirement_met)
        return requirement_met, (cur_ver, requirement_sym,
                                 requirement_ver, requirement_met)

    @staticmethod
    def get_deps_for_package_version(package, version):
        """Gets dependencies for a specific version of a package.

        Specifically:
        0. Check if this has already been done and cached & return that.
            1. Set up temporary virtualenv
            2. installs package/version into there using pip
            3. Write file to interrogate through virtual env using
            vex/pip/setuptool combo
            4. Run file, which pickles results to temp file
            5. reads that file from current program
            6. deletes file and returns info

        7. Delete tmp env?
        """

        req_out_file = ("{0}_{1}_req.json"
                        .format(package.lower(), version.replace(".", "_")))

        # 0. Check if this has already been done and cached & return that.
        cached_file = MagellanConfig.cache_dir + "/" + req_out_file
        if os.path.exists(cached_file):
            print("Using previously cached result at {0}".format(cached_file))
            return json.load(open(cached_file, 'rb'))

        # 1. Set up temporary virtualenv
        tmp_env = Environment(MagellanConfig.tmp_env_dir)
        tmp_env.create_vex_new_virtual_env()  # NB: delete if extant!!

        # 2. installs package/version into there using pip
        # tmp_pip_options = "--cache-dir {}".format(MagellanConfig.cache_dir)
        tmp_pip_options = ("--cache-dir {} --no-deps"
                           .format(MagellanConfig.cache_dir))
        pip_package_str = '{0}=={1}'.format(package, version)
        tmp_env.vex_install_requirement(
            tmp_env.name, pip_package_str, tmp_pip_options)

        # 3. Write file to interrogate through virtual env using
        # vex/pip/setuptool combo
        tmp_out_file = 'mag_temp_file.py'
        with open(tmp_out_file, 'wb') as outfile:
            outfile.write(_return_interrogation_script_json(
                package, req_out_file))

        # 4. Run file, which pickles results to temp file
        run_in_subprocess("vex {0} python {1}"
                          .format(tmp_env.name, tmp_out_file))

        # 5. reads that file from current program
        result = json.load(open(req_out_file, 'rb'))

        # 6. Move file to cache dir or delete file and return info
        if MagellanConfig.caching:
            cmd_to_run = "mv {0} {1}/"\
                .format(req_out_file, MagellanConfig.cache_dir)
            run_in_subprocess(cmd_to_run)
        else:
            run_in_subprocess("rm {0}".format(req_out_file))
        run_in_subprocess("rm {0}".format(tmp_out_file))

        # 7. Delete tmp virtual env - not necessary as it's always overwritten?
        # tmp_env.vex_delete_env_self()

        return result

    @staticmethod
    def check_if_ancestors_still_satisfied(
            package, new_version, ancestors, package_requirements):
        """
        Makes sure you haven't offended any of your forefathers...

        Checks whether the packages which depend on the current package
        and version will still have their requirements satisfied.

        :param str package:
        :param str new_version:
        :param list ancestors:
        :param dict package_requirements: from virtual env
        :rtype dict{dict, dict}
        :return: checks, conflicts

        NB: Note distinction between package_requirements and the requirements
        that generally go in other methods in this class. The former lists the
        requirements for all packages int he current environment whereas the
        latter is package specific.
        """

        package_key = package.lower()

        to_check = [x[0][0] for x in ancestors if x[0][0] != 'root']
        checks = {}
        conflicts = {}
        for anc in to_check:
            anc_key = anc.lower()
            anc_specs = \
                package_requirements[anc_key]['requires'][package_key]['specs']
            checks[anc_key] = anc_specs
            # print(anc_specs)
            for s in anc_specs:
                is_ok, dets = DepTools.check_requirement_satisfied(
                    new_version, s)
                if not is_ok:
                    if anc_key in conflicts:
                        conflicts[anc_key].append(dets)
                    else:
                        conflicts[anc_key] = dets

        # pprint(checks)
        # pprint(conflicts)
        # return checks, conflicts
        return {'checks': checks, 'conflicts': conflicts}

    @staticmethod
    def detect_upgrade_conflicts(data, venv):
        """
        Detect conflicts between packages in current environment when upgrading
        other packages.

        At present this routine will look at just the immediate connections
        to a graph in the environment. It does this in 3 major ways:

        1. DEPENDENCY SET - check_changes_in_requirements_vs_env
            Checks the required dependencies of new version against
            current environment to see additions/removals BY NAME ONLY.

        2. REQUIRED VERSIONS - check_req_deps_satisfied_by_current_env
            For all dependencies of new version, checks to see whether
            they are satisfied by current environment versions.

        3. ANCESTOR DEPENDENCIES - check_if_ancestors_still_satisfied
            For all the ancestor nodes that depend on PACKAGE, it checks
            whether the dependency specs are satisfied by the new version.

        :param list data: List of (package, desired_version)'s
        :param Environment venv: virtual environment
        """

        uc_deps = {}
        conflicts = {}
        for u in data:
            package = u[0]
            version = u[1]
            p_v = "{0}_{1}".format(package, version.replace('.', '_'))

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                uc_deps[p_v] = None
                continue

            uc_deps[p_v] = {}

            uc_deps[p_v]['requirements'] = \
                DepTools.get_deps_for_package_version(package, version)

            ancestors, descendants = Package.get_direct_links_to_any_package(
                package, venv.edges)

            # 1:  DEPENDENCY SET - check_changes_in_requirements_vs_env
            uc_deps[p_v]['dependency_set'] = \
                DepTools.check_changes_in_requirements_vs_env(
                uc_deps[p_v]['requirements'], descendants)

            # 2. REQUIRED VERSIONS - check_req_deps_satisfied_by_current_env
            uc_deps[p_v]['required_versions'] = \
                DepTools.check_req_deps_satisfied_by_current_env(
                    uc_deps[p_v]['requirements'], venv.nodes)

            # 3. ANCESTOR DEPENDENCIES - check_if_ancestors_still_satisfied
            uc_deps[p_v]['ancestor_dependencies'] = \
                DepTools.check_if_ancestors_still_satisfied(
                    package, version, ancestors, venv.package_requirements)

            conflicts[p_v] = {}
            conflicts[p_v]['dep_set'] = uc_deps[p_v]['dependency_set']
            conflicts[p_v]['req_ver'] = \
                uc_deps[p_v]['required_versions']['conflicts']
            conflicts[p_v]['anc_dep'] = \
                uc_deps[p_v]['ancestor_dependencies']['conflicts']

        return conflicts, uc_deps

    @staticmethod
    def highlight_conflicts_in_current_env(nodes, package_requirements):
        """
        Checks through all nodes (packages) in the venv environment

        :param list nodes: list of nodes (packages) as (name, ver) tuple
        :param dict package_requirements: dependencies dictionary.
        :rtype list
        :return: current_env_conflicts
        """
        # todo (aj) tests.
        if not nodes or not package_requirements:
            print("venv missing required data: nodes or package_requirements.")
            return []

        current_env_conflicts = []

        ver_info = {n[0].lower(): n[1] for n in nodes}

        for n in nodes:
            n_key = n[0].lower()

            if n_key not in package_requirements:
                print ("{} missing from package_requirements".format(n))
                continue

            if 'requires' not in package_requirements[n_key]:
                print("{} does not have key 'requires'".format(n_key))
                continue

            node_requirements = package_requirements[n_key]['requires']
            for r in node_requirements:
                cur_ver = ver_info[r.lower()]
                for s in node_requirements[r]['specs']:
                    req_met, req_details = \
                        DepTools.check_requirement_satisfied(cur_ver, s)
                    if not req_met:
                        current_env_conflicts.append(
                            (n, node_requirements[r]['project_name'],
                             req_details))

        return current_env_conflicts


def _return_interrogation_script_json(package, filename=None):
    """Return script to interrogate deps for package inside env.
    Uses json.dump instead of pickle due to cryptic pickle/requests bug."""
    head = """
import pip
import json
pkgs  = pip.get_installed_distributions()
"""
    mid = "package = '{0}'".format(package.lower())

    if not filename:
        out = ('fn = "{0}_{1}_req.dat"'
               '.format(p.key, p.version.replace(".","_"))')
    else:
        out = 'fn = "{0}"'.format(filename)

    conv = """
p = [x for x in pkgs if x.key == package][0]

req_dic = {'project_name': p.project_name,
               'version': p.version, 'requires': {}}

for r in p.requires():
    req_dic['requires'][r.key] = {}
    req_dic['requires'][r.key]['project_name'] = r.project_name
    req_dic['requires'][r.key]['key'] = r.key
    req_dic['requires'][r.key]['specs'] = r.specs

"""

    end = "json.dump(req_dic, open(fn, 'wb'))"

    nl = '\n'
    return head + nl + mid + nl + conv + nl + out + nl + end + nl


class PyPIHelper(object):
    """Collection of static methods to assist in interrogating PyPI"""

    @staticmethod
    def check_package_version_on_pypi(package, version):
        """
        Queries PyPI to see if the specific version of "package" exists.
        """

        package_json = PyPIHelper.acquire_package_json_info(package)

        if not package_json:
            return False
        else:
            # print("JSON acquired")
            return version in package_json['releases'].keys()

    @staticmethod
    def acquire_package_json_info(package, localcache=None):
        """
        Perform lookup on packages and versions. Currently just uses PyPI.
        Returns JSON

        p is package name
        localCacheDir is a location of local cache
        """
        verbose = True

        package = str(package)

        if not localcache:
            f = MagellanConfig.cache_dir + '/' + package + '.json'
        else:
            # todo (aj) test invalid local cache, not robust
            f = localcache + '/' + package + '.json'

        if os.path.exists(f):
            if verbose:
                print("retrieving file {0} from local cache".format(f))
            with open(f, 'rb') as ff:
                return json.load(ff)

        pypi_template = 'https://pypi.python.org/pypi/{0}/json'

        r = requests.get(pypi_template.format(package))
        if r.status_code == 200:  # if successfully retrieved:
            if verbose:
                print("{0} JSON successfully retrieved from PyPI"
                      .format(package))

            # Save to local cache...
            with open(f, 'w') as outf:
                json.dump(r.json(), outf)
            # ... and return to caller:
            return r.json()

        else:  # retrieval failed
            if verbose:
                print("failed to download {0}".format(package))
            return {}

    @staticmethod
    def all_package_versions_on_pypi(package):
        """Return a list of all released packages on PyPI.

        :param str package: input package name
        :rtype: list
        :return: list of all package versions
        """
        all_package_info = PyPIHelper.acquire_package_json_info(package)
        out = []
        if 'releases' in all_package_info:
            out = all_package_info['releases'].keys()
        return out
