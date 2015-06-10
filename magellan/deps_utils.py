import os
import operator
from pkg_resources import parse_version
from pprint import pformat
import requests
import json
import logging

from magellan.package_utils import Package
from magellan.env_utils import Environment
from magellan.utils import MagellanConfig, run_in_subprocess

# Logging:
maglog = logging.getLogger("magellan_logger")


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
                maglog.info("Requirement {0}{1} not in current environment"
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
        cached_file = os.path.join(MagellanConfig.cache_dir, req_out_file)

        if os.path.exists(cached_file):
            maglog.info("Using previously cached result at {0}"
                        .format(cached_file))
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

        # 3. File to interrogate through virtual env for package
        interrogation_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'interrogation_scripts',  'package_interrogation.py')

        # 4. Run file, which pickles results to temp file
        run_in_subprocess("vex {0} python {1} {2} {3}".format(
            tmp_env.name, interrogation_file,
            package, MagellanConfig.cache_dir))

        # 5. reads that file from current program
        try:
            result = json.load(open(cached_file, 'rb'))
        except IOError:
            result = {}

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
    def detect_upgrade_conflicts(packages, venv):
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

        :param list packages: List of (package, desired_version)'s
        :param Environment venv: virtual environment
        """

        uc_deps = {}
        conflicts = {}
        for u in packages:
            package = u[0]
            version = u[1]
            p_v = "{0}_{1}".format(package, version.replace('.', '_'))

            uc_deps[p_v] = {}

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                continue

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
            conflicts[p_v]['missing_packages'] = \
                uc_deps[p_v]['required_versions']['missing']
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
                try:
                    cur_ver = ver_info[r.lower()]
                except KeyError:
                    cur_ver = '0.0.0'
                for s in node_requirements[r]['specs']:
                    req_met, req_details = \
                        DepTools.check_requirement_satisfied(cur_ver, s)
                    if not req_met:
                        current_env_conflicts.append(
                            (n, node_requirements[r]['project_name'],
                             req_details))

        DepTools.pprint_cur_env_conflicts(current_env_conflicts)
        return current_env_conflicts

    @staticmethod
    def detect_package_addition_conflicts(packages, venv):
        """
        Detect if there will be any conflicts with the addition of a new
        package

        :param packages: list of (name, version) tuple
        :param venv: virtual env where package will be installed, of type
        magellan.env_utils.Environment
        :rtype dict
        :return: conflicts


        0. Check if package (name) is already in environment.
        1. Check new packages to be installed
        2. Check current environment satisfies requirements.
        """
        # todo (aj) tests
        ver_info = {x[0].lower(): x[1] for x in venv.nodes}

        deps = {}
        for p in packages:
            package = p[0]
            version = p[1]
            p_v = "{0}_{1}".format(package, version.replace('.', '_'))

            deps[p_v] = {}

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                print("Cannot get package info for {} {} on PyPI"
                      .format(package, version))
                deps[p_v]['status'] = "No package info on PyPI."
                continue

            # 0 EXTANT PACKAGE:
            p_extant, details = DepTools.package_in_environment(
                package, version, venv.nodes)

            if p_extant:  # should use upgrade conflict detection.
                deps[p_v]['status'] = (
                    "Package currently exists - use  upgrade -U.")
                continue

            # Get requirements if it's actually a new package & on PyPI.
            requirements = DepTools.get_deps_for_package_version(
                package, version)

            deps[p_v]['requirements'] = requirements
            deps[p_v]['new_packages'] = []
            deps[p_v]['may_try_upgrade'] = []
            deps[p_v]['may_be_okay'] = []

            if not requirements:
                deps[p_v] = "NO DATA returned from function."
                continue

            for r in requirements['requires']:
                r_key = r.lower()

                # 1 New packages
                if r_key not in ver_info:
                    deps[p_v]['new_packages'].append(
                        requirements['requires'][r]['project_name'])

                # 2 Packages that may try to upgrade. All n = 1
                else:
                    if not requirements['requires'][r]['specs']:
                        deps[p_v]['may_be_okay'].append(r)

                    current_version = ver_info[r_key]
                    for s in requirements['requires'][r]['specs']:
                        res, deets = DepTools.check_requirement_satisfied(
                            current_version, s)
                        if not res:
                            deps[p_v]['may_try_upgrade'].append((r, deets))
                        else:
                            deps[p_v]['may_be_okay'].append((r, deets))

        return deps

    @staticmethod
    def package_in_environment(package, version, nodes):
        """
        Check to see if package exists in current env and see if it
        matches the current version if so.

        :param package: str name of package
        :param version: str version of package
        :param nodes: list of env nodes
        :rtype bool, dict
        :return: whether package exists, and if so which version.
        """
        key = package.lower()
        ver_info = {x[0].lower(): x[1] for x in nodes if x[0].lower() == key}

        if ver_info:
            current_version = ver_info[key]
            if version == current_version:
                maglog.info("Package {0} exists with specified version {1}"
                            .format(package, version))
            else:
                maglog.info("Package {0} exists with version {1} that differs "
                            "from {2}. Try running with Upgrade Package flag"
                            " -U.".format(package, current_version, version))

            return True, {'name': package, 'env_version': current_version}
        else:
            maglog.info("Package {} does not exist in current env"
                        .format(package))
            return False, {}

    @staticmethod
    def process_package_conflicts(conflict_list, venv):
        """
        :param conflict_list: list of (package, version) tuples passed in
        from CLI
        :param venv: magellan.env_utils.Environment
        :return: addition_conflicts, upgrade_conflicts
        """
        upgrade_conflicts = []
        addition_conflicts = []
        for p in conflict_list:
            p_in_env, p_details = venv.package_in_env(p[0])
            if p_in_env:
                upgrade_conflicts.append(p)
            else:
                addition_conflicts.append(p)

        if upgrade_conflicts:
            maglog.info(upgrade_conflicts)
            upgrade_conflicts, uc_deps = DepTools.detect_upgrade_conflicts(
                upgrade_conflicts, venv)

            DepTools.pprint_upgrade_conflicts(upgrade_conflicts, uc_deps, venv)
            maglog.info(pformat(upgrade_conflicts))
            maglog.debug(pformat(uc_deps))

        if addition_conflicts:
            maglog.info(addition_conflicts)
            addition_conflicts = DepTools.detect_package_addition_conflicts(
                addition_conflicts, venv)

            DepTools.pprint_additional_package_conflicts(addition_conflicts)
            maglog.info(pformat(addition_conflicts))

        return addition_conflicts, upgrade_conflicts

    @staticmethod
    def pprint_upgrade_conflicts(conflicts, dep_info, venv):
        """
        Prints the upgrade conflicts to stdout in format easily digestible
        for people.

        :param dict conflicts: dict of upgrade conflicts
        :param dict dep_info: dependency information
        :param Environment venv: virtual environment
        """
        print("\n")
        s = "Upgrade Conflicts:"
        _print_ul(s, ul="=")

        for p_k, p in conflicts.items():
            p_name = dep_info[p_k]['requirements']['project_name']
            ver = dep_info[p_k]['requirements']['version']
            cur_ver = venv.all_packages[p_name.lower()].version

            s = "{0} {1}:".format(p_name, ver)
            _print_ul(s)

            missing_from_env = p['missing_packages']
            new_dependencies = p['dep_set']['new_deps']
            removed_dependencies = p['dep_set']['removed_deps']
            broken_reqs = ["{0}: {1}".format(x, v)
                           for x, v in p['anc_dep'].items()]

            if not (missing_from_env and new_dependencies and
                    removed_dependencies and broken_reqs):

                if parse_version(cur_ver) < parse_version(ver):
                    direction = "upgrade"
                else:
                    direction = "downgrade"

                print("  No conflicts detected for {} of {} from {} to {}."
                      .format(direction, p_name, cur_ver, ver))

            _print_if(missing_from_env,
                      "Packages not currently in environment:")
            _print_if(new_dependencies,
                      "New dependencies of {}:".format(p_name))
            _print_if(removed_dependencies,
                      "{} will no longer depend on:".format(p_name))
            _print_if(broken_reqs,
                      "These packages will have their requirements broken:")

            print("\n")

    @staticmethod
    def pprint_additional_package_conflicts(conflicts):
        """
        Prints the upgrade conflicts to stdout in format easily digestible
        for people.

        :param conflicts: dict of upgrade conflicts
        """
        print("\n")
        _print_ul("Package Addition Conflicts:", ul="=")

        for p_k, p in conflicts.items():
            p_name = p['requirements']['project_name']
            ver = p['requirements']['version']

            _print_ul("{0} {1}:".format(p_name, ver))

            okay = p['may_be_okay']
            up = p['may_try_upgrade']
            new_ps = p['new_packages']

            if not (okay or up or new_ps):
                print("  No conflicts detected for the addition of {0} {1}."
                      .format(p_name, ver))

            _print_if(okay, "Should be okay:")
            _print_if(up, "May try to upgrade:")
            _print_if(new_ps, "New packages to add:")

            print("\n")

    @staticmethod
    def pprint_cur_env_conflicts(conflicts):
        """
        Pretty print current conflicts in environment for human readability.
        """
        if conflicts:
            _print_ul("Conflicts in environment:", ul="=")
            for conflict in conflicts:
                maglog.info(conflict)

                try:
                    c_name = conflict[0][0]
                    c_ver = conflict[0][1]
                    c_dep = conflict[1]
                    c_dep_dets = conflict[-1]
                    print("{} {} dependency {} : ({})".format(
                        c_name, c_ver, c_dep,
                        _string_requirement_details(c_dep_dets)))
                except Exception as e:
                    maglog.exception(e)
                    print("There was an error in printing output; check -v")
        else:
            _print_ul("No conflicts detected in environment", ul="=")

    @staticmethod
    def acquire_and_display_dependencies(package_version_list):
        """
        Gets the dependencies information by installing the package and
        version from PyPI
        """
        for p in package_version_list:
            print("\n")
            package = p[0]
            version = p[1]

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                _print_ul("{} {} not found on PyPI.".format(package, version))
                continue

            requirements = DepTools.get_deps_for_package_version(
                package, version)

            maglog.debug(pformat(requirements))
            _pprint_requirements(requirements)


def _pprint_requirements(requirements):
    """
    Pretty print requiements to stdout for human consumption.

    :param dict requirements: dictionary of requirements from PyPI
    """
    package = requirements['project_name']
    version = requirements['version']

    reqs = requirements['requires']
    if not reqs:
        _print_ul("{} {} appears to have no dependencies."
                  .format(package, version))
    else:
        _print_ul("Dependencies of {} {}:".format(package, version))
        spacers = 2
        for r_key, r in reqs.items():
            print(" "*spacers + r['project_name'])
            for s in r['specs']:
                print("  "*spacers + " ".join(s))


def _print_if(list_in, lead_in_text=None, tab_space=2, lead_nl=False):
    """
    prints the list if it has items.
    :param list list_in: list of input items
    :param str lead_in_text: what to print before list print.
    :param int tab_space: indentation for prettiness.
    :param bool lead_nl: lead print with newline
    """
    if list_in:

        if lead_nl:
            print("\n")

        if lead_in_text:
            print(" "*tab_space + lead_in_text)

        for item in list_in:
            if type(item) == tuple:
                # todo (aj) change this as tied too closely to req details!
                _item = item[0] + " as " + _string_requirement_details(item[1])
            else:
                _item = item
            print("  "*tab_space + "".join(_item))


def _print_ul(s, ul="-"):
    """
    Prints string underlined to stdout
    :param s: string to print
    :param ul: underline character
    """
    print(s)
    print(ul * len(s))


def _string_requirement_details(dets):
    """
    Converts details from DepTools.check_requirement_satisfied into an
    easily readable string.

    :param dets: details from DepTools.check_requirement_satisfied
        e.g. dets = ('1.9.0', u'>=', u'1.7.3', True)
    :rtype str:
    :return:requirement details as a string.
    """
    try:
        passed = " is " if dets[-1] else " is not "
        s = dets[0] + passed + " ".join(dets[1:3])
    except Exception as e:
        maglog.error(e)
        s = ""
    return s


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

        :param str package: package name
        :param str version: package version
        :rtype bool:
        :return: True if package-version on PyPI
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
        package = str(package)
        p_json = package + '.json'

        if not localcache:
            f = os.path.join(MagellanConfig.cache_dir, p_json)
        else:
            f = os.path.join(localcache, p_json)

        if os.path.exists(f):
            maglog.info("retrieving file {0} from local cache".format(f))
            with open(f, 'rb') as ff:
                return json.load(ff)

        pypi_template = 'https://pypi.python.org/pypi/{0}/json'

        r = requests.get(pypi_template.format(package))
        if r.status_code == 200:  # if successfully retrieved:
            maglog.info("{0} JSON successfully retrieved from PyPI"
                        .format(package))

            # Save to local cache...
            with open(f, 'w') as outf:
                json.dump(r.json(), outf)
            # ... and return to caller:
            return r.json()

        else:  # retrieval failed
            maglog.info("failed to download {0}".format(package))
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
