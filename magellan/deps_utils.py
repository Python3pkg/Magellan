import os
import operator
from pkg_resources import parse_version
from pkg_resources import resource_filename as pkg_res_resource_filename
from pprint import pformat
import requests
import json
import logging

# from terminaltables import AsciiTable as OutputTableType
from terminaltables import SingleTable as OutputTableType


from magellan.package_utils import Package
from magellan.env_utils import Environment
from magellan.utils import MagellanConfig, run_in_subprocess, print_col

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
        try:
            dec_keys = {x[1][0].lower(): x[1][0] for x in descendants}
        except KeyError:
            maglog.exception("Error in check_changes_in_requirements_vs_env")
            return {'removed_deps': [], 'new_deps': []}

        try:
            rec_keys = {x['key']: x['project_name']
                        for x in requirements['requires'].values()}
        except KeyError as e:
            maglog.debug("Error in check_changes_in_requirements_vs_env: {}"
                         .format(e))
            return {'removed_deps': [], 'new_deps': []}

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

        if 'requires' not in requirements:
            maglog.error("Requirements missing in "
                         "check_req_deps_satisfied_by_current_env")
            return

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
    def get_deps_for_package_version(package, version, vex_options=None):
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

        if vex_options is None:
            vex_options = ''

        req_out_file = ("{0}_{1}_req.json"
                        .format(package.lower(), version.replace(".", "_")))

        # 0. Check if this has already been done and cached & return that.
        cached_file = os.path.join(MagellanConfig.cache_dir, req_out_file)

        if os.path.exists(cached_file):
            maglog.info("Using previously cached result at {0}"
                        .format(cached_file))
            return json.load(open(cached_file, 'r'))

        # 1. Set up temporary virtualenv
        tmp_env = Environment(name=MagellanConfig.tmp_env_dir)
        tmp_env.create_vex_new_virtual_env(vex_options)  # NB: delete if extant!!

        # todo (aj); by default?
        # 1.5 Upgrade pip
        run_in_subprocess("vex {} {} pip install pip --upgrade"
                          .format(vex_options, tmp_env.name))

        # 2. installs package/version into there using pip
        # tmp_pip_options = "--cache-dir {}".format(MagellanConfig.cache_dir)
        tmp_pip_options = ("--cache-dir {} --no-deps"
                           .format(MagellanConfig.cache_dir))
        pip_package_str = '{0}=={1}'.format(package, version)
        tmp_env.vex_install_requirement(
            tmp_env.name, pip_package_str, tmp_pip_options, vex_options)

        # 3. File to interrogate through virtual env for package
        interrogation_file = pkg_res_resource_filename(
            'magellan', 'package_interrogation.py')

        # 4. Run file, which pickles results to temp file
        run_in_subprocess("vex {} {} python {} {} {}".format(
            vex_options, tmp_env.name, interrogation_file, package,
            MagellanConfig.cache_dir))

        # 5. reads that file from current program
        try:
            result = json.load(open(cached_file, 'r'))
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
    def detect_upgrade_conflicts(packages, venv, pretty=False):
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

            p_key = package.lower()
            cur_ver = venv.all_packages[p_key].version
            if parse_version(cur_ver) == parse_version(version):
                s = ("{} version {} is same as current!"
                     .format(package, version))
                print_col(s, 'red', 'black', pretty)

                continue

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                continue

            uc_deps[p_v]['requirements'] = \
                DepTools.get_deps_for_package_version(
                    package, version, vex_options=MagellanConfig.vex_options)

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
            try:
                conflicts[p_v]['dep_set'] = uc_deps[p_v]['dependency_set']
                conflicts[p_v]['req_ver'] = \
                    uc_deps[p_v]['required_versions']['conflicts']
                conflicts[p_v]['missing_packages'] = \
                    uc_deps[p_v]['required_versions']['missing']
                conflicts[p_v]['anc_dep'] = \
                    uc_deps[p_v]['ancestor_dependencies']['conflicts']
            except TypeError as e:
                maglog.debug("Error when attempting to assess conflicts {}"
                             .format(e))

        return conflicts, uc_deps

    @staticmethod
    def highlight_conflicts_in_current_env(
            nodes, package_requirements, pretty=False):
        """
        Checks through all nodes (packages) in the venv environment

        :param list nodes: list of nodes (packages) as (name, ver) tuple
        :param dict package_requirements: dependencies dictionary.
        :rtype list
        :return: current_env_conflicts
        """
        if not nodes or not package_requirements:
            print("venv missing required data: nodes or package_requirements.")
            return []

        current_env_conflicts = []

        ver_info = {n[0].lower(): n[1] for n in nodes}

        if 'argparse' not in ver_info:
            ver_info['argparse'] = ""

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
                    maglog.debug("KeyError for {}".format(r))
                    cur_ver = ''
                for s in node_requirements[r]['specs']:
                    req_met, req_details = \
                        DepTools.check_requirement_satisfied(cur_ver, s)
                    if not req_met:
                        current_env_conflicts.append(
                            (n, node_requirements[r]['project_name'],
                             req_details))

        DepTools.table_print_cur_env_conflicts(current_env_conflicts, pretty)
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
                package, version, vex_options=MagellanConfig.vex_options)

            deps[p_v]['requirements'] = requirements
            deps[p_v]['new_packages'] = []
            deps[p_v]['may_try_upgrade'] = []
            deps[p_v]['may_be_okay'] = []

            if not requirements:
                deps[p_v] = {"status": "NO DATA returned from function."}
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
    def process_package_conflicts(conflict_list, venv, pretty=False):
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
            else:  # NB: may also be non-existent package
                addition_conflicts.append(p)

        if upgrade_conflicts:
            maglog.info(upgrade_conflicts)
            upgrade_conflicts, uc_deps = DepTools.detect_upgrade_conflicts(
                upgrade_conflicts, venv, pretty)

            DepTools.table_print_upgrade_conflicts(
                upgrade_conflicts, uc_deps, venv, pretty)
            maglog.info(pformat(upgrade_conflicts))
            maglog.debug(pformat(uc_deps))

        if addition_conflicts:
            maglog.info(addition_conflicts)
            addition_conflicts = DepTools.detect_package_addition_conflicts(
                addition_conflicts, venv)

            DepTools.table_print_additional_package_conflicts(
                addition_conflicts, pretty)
            maglog.info(pformat(addition_conflicts))

        return addition_conflicts, upgrade_conflicts

    @staticmethod
    def table_print_upgrade_conflicts(conflicts, dep_info, venv, pretty=False):
        """
        Prints the upgrade conflicts to stdout in format easily digestible
        for people.

        :param dict conflicts: dict of upgrade conflicts
        :param dict dep_info: dependency information
        :param Environment venv: virtual environment
        """

        if not conflicts:
            return
        print("\n")
        s = "Upgrade Conflicts:"
        print_col(s, pretty=pretty, header=True)

        for p_k, p in conflicts.items():

            has_recs = dep_info.get(p_k).get('requirements')
            if not has_recs:
                print_col("Requirements not found for {}, possible failure "
                           "when installating package into temporary "
                           "directory?".format(p_k), pretty=pretty)
                continue

            p_name = dep_info[p_k]['requirements']['project_name']
            ver = dep_info[p_k]['requirements']['version']
            cur_ver = venv.all_packages[p_name.lower()].version

            if parse_version(cur_ver) < parse_version(ver):
                direction = "upgrade"
            else:
                direction = "downgrade"

            s = ("{} {}: {} from {} to {}.".format(
                p_name, ver, direction, cur_ver, ver))
            print_col(s, pretty=pretty)

            missing_from_env = p['missing_packages']
            new_dependencies = p['dep_set']['new_deps']
            removed_dependencies = p['dep_set']['removed_deps']
            broken_reqs = ["{0}: {1}".format(x, v)
                           for x, v in p['anc_dep'].items()]

            if not (missing_from_env or new_dependencies
                    or removed_dependencies or broken_reqs):
                print_col("No conflicts detected", pretty=pretty)

            _print_if(missing_from_env,
                      "Packages not in environment (to be installed):",
                      pretty=pretty)
            _print_if(new_dependencies,
                      "New dependencies of {}:".format(p_name), pretty=pretty)
            _print_if(removed_dependencies,
                      "{} will no longer depend on:".format(p_name),
                      pretty=pretty)
            _print_if(broken_reqs,
                      "These packages will have their requirements broken:{}",
                      pretty=pretty)

            print("\n")

    @staticmethod
    def table_print_additional_package_conflicts(conflicts, pretty=False):
        """
        Prints the upgrade conflicts to stdout in format easily digestible
        for people.

        :param conflicts: dict of upgrade conflicts
        """
        print_col("Package Addition Conflicts:", pretty=pretty, header=True)

        for p_k, p in conflicts.items():
            has_recs = p.get('requirements')
            if not has_recs:
                print_col("Requirements not found for {}, possible failure "
                           "when installating package into temporary "
                           "directory?".format(p_k), pretty=pretty)
                continue

            p_name = p.get('requirements').get('project_name')
            ver = p.get('requirements').get('version')

            print_col("{0} {1}:".format(p_name, ver),
                      pretty=pretty, header=True)

            okay = p['may_be_okay']
            up = p['may_try_upgrade']
            new_ps = p['new_packages']

            if not (okay or up or new_ps):
                s = ("  No conflicts detected for the addition of {0} {1}."
                     .format(p_name, ver))
                print_col(s, pretty=pretty)

            _print_if(okay, "Should be okay:", pretty=pretty)
            _print_if(up, "May try to upgrade:", pretty=pretty)
            _print_if(new_ps, "New packages to add:", pretty=pretty)

            print("\n")

    @staticmethod
    def table_print_cur_env_conflicts(conflicts, pretty=False):
        """
        Print current conflicts in environment using terminaltables.
        """

        ts = "No conflicts detected in environment"

        if conflicts:
            print_col("Conflicts in environment:", pretty=pretty, header=True)

            table_data = [['PACKAGE', 'DEPENDENCY', 'CONFLICT']]

            for conflict in conflicts:
                maglog.info(conflict)

                try:
                    c_name = conflict[0][0]
                    c_ver = conflict[0][1]
                    c_dep = conflict[1]
                    c_dep_dets = conflict[-1]

                    t_row = [" ".join([c_name, c_ver]),
                             c_dep,
                             _string_requirement_details(c_dep_dets)]

                    table_data.append(t_row)
                except Exception as e:
                    maglog.exception(e)
                    print("There was an error in printing output; check -v")

            ts = OutputTableType(table_data).table

        print_col(ts, pretty=pretty)

    @staticmethod
    def acquire_and_display_dependencies(package_version_list, pretty=False):
        """
        Gets the dependencies information by installing the package and
        version from PyPI
        """
        for p in package_version_list:
            package = p[0]
            version = p[1]

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                print_col("{} {} not found on PyPI.".format(package, version),
                          pretty=pretty, header=True)
                continue

            requirements = DepTools.get_deps_for_package_version(
                package, version, vex_options=MagellanConfig.vex_options)

            maglog.debug(pformat(requirements))
            _table_print_requirements(requirements, pretty)

    @staticmethod
    def get_ancestors_of_packages(package_list, venv, pretty=False):
        """
        Prints a list of ancestors of package to indicate what brought a
        package into the environment.

        :param package_list: list of names of package to query
        :param venv: magellan.env_utils.Environment

        :rtype dict:
        :returns: dictionary with list of ancestors.
        """

        anc_dict = {}
        for p in package_list:
            p_key = p[0].lower()  # [0] as list of lists from argparse
            if p_key not in venv.all_packages:
                anc_dict[p_key] = None
                maglog.info("{} not found in env".format(p_key))
                continue
            ancs = venv.all_packages[p_key].ancestors(venv.edges)
            anc_dict[p_key] = [x[0] for x in ancs if x[0][0] != "root"]

        DepTools().pprint_anc_dict(anc_dict, venv, pretty)
        return anc_dict

    @staticmethod
    def pprint_anc_dict(ancestor_dictionary, venv, pretty=False):
        """
        Pretty prints ancestors dictionary to standard out.

        :param ancestor_dictionary:
        :param venv: magellan.env_utils.Environment
        """
        env_name = "the current environment" if not venv.name else venv.name

        for pk, p in ancestor_dictionary.items():
            if p:
                s = "These packages depend on {} in {}:"\
                    .format(venv.all_packages[pk].name, env_name)
                print_col(s, pretty=pretty, header=True)
                for a in p:
                    try:
                        print_col("{} {}".format(a[0], a[1]), pretty=pretty)
                    except Exception as e:
                        maglog.exception(e)

    @staticmethod
    def get_descendants_of_packages(package_list, venv, pretty=False):
        """
        Prints a list of descendants of package to indicate what brought a
        package into the environment.

        :param package_list: list of names of package to query
        :param venv: magellan.env_utils.Environment

        :rtype dict:
        :returns: dictionary with list of descendants.
        """

        dec_dic = {}
        for p in package_list:
            p_key = p[0].lower()  # [0] as list of lists from argparse
            if p_key not in venv.all_packages:
                dec_dic[p_key] = None
                maglog.info("{} not found in env".format(p_key))
                continue
            decs = venv.all_packages[p_key].descendants(venv.edges)
            dec_dic[p_key] = [x[1] for x in decs]

        DepTools().pprint_dec_dict(dec_dic, venv, pretty)
        return dec_dic

    # todo (aj) refactor the anc dic
    @staticmethod
    def pprint_dec_dict(descendant_dictionary, venv, pretty=False):
        """
        Pretty prints ancestors dictionary to standard out.

        :param descendant_dictionary:
        :param venv: magellan.env_utils.Environment
        """
        env_name = "the current environment" if not venv.name else venv.name

        for pk, p in descendant_dictionary.items():
            if p:
                s = "{} depends on these packages in {}:"\
                    .format(venv.all_packages[pk].name, env_name)
                print_col(s, pretty=pretty, header=True)
                for a in p:
                    try:
                        print_col("{} {}".format(a[0], a[1]), pretty=pretty)
                    except Exception as e:
                        maglog.exception(e)


def _table_print_requirements(requirements, pretty=False):
    """
    Table print requirements to stdout for human consumption.

    :param dict requirements: dictionary of requirements from PyPI
    """

    package = requirements.get('project_name')
    version = requirements.get('version')

    reqs = requirements.get('requires', {})

    if not reqs:
        s = "{} {} appears to have no dependencies.".format(package, version)
        print_col(s, pretty=pretty, header=True)
    else:
        s = "Dependencies of {} {}:".format(package, version)
        print_col(s, pretty=pretty, header=True)

        table_data = [['PACKAGE', 'SPECS']]

        for r_key, r in reqs.items():
            table_row = [r['project_name']]
            if r['specs']:
                spec_string = ""
                for s in r['specs']:
                    spec_string += "{} {}\n".format(s[0], s[1])
                table_row.append(spec_string)
            else:
                table_row.append('\n')

            table_data.append(table_row)

        table = OutputTableType(table_data)
        print_col(table.table, pretty=pretty)


def _print_if(list_in, lead_in_text=None, tab_space=2, pretty=False):
    """
    prints the list if it has items.
    :param list list_in: list of input items
    :param str lead_in_text: what to print before list print.
    :param int tab_space: indentation for prettiness.
    :param bool lead_nl: lead print with newline
    """
    if list_in:
        if lead_in_text:
            print_col(" "*tab_space + lead_in_text, pretty=pretty)

        for item in list_in:
            if type(item) == tuple:
                _item = item[0] + " as " + _string_requirement_details(item[1])
            else:
                _item = item
            print_col("  "*tab_space + "".join(_item), pretty=pretty)


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
            with open(f, 'r') as ff:
                return json.load(ff)

        pypi_template = 'https://pypi.python.org/pypi/{0}/json'

        try:
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
        except requests.ConnectionError as e:
            maglog.warn("Connection to PyPI failed: {}".format(e))
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
            out = list(all_package_info['releases'].keys())
        return out
