import os
import operator
from pprint import pprint
import pickle
from pkg_resources import parse_version
import requests
import json

from magellan.env_utils import Environment
from magellan.utils import MagellanConfig, run_in_subprocess


class DepTools(object):
    ops = {'<': operator.lt, '<=': operator.le,
           '==': operator.eq, '!=': operator.ne,
           '>=': operator.ge, '>': operator.gt, }

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

        req_out_file = ("{0}_{1}_req.dat"
                        .format(package.lower(), version.replace(".", "_")))

        # 0. Check if this has already been done and cached & return that.
        import os
        cached_file = MagellanConfig.cache_dir + "/" + req_out_file
        if os.path.exists(cached_file):
            print("Using previously cached result at {0}".format(cached_file))
            # return pickle.load(open(cached_file, 'rb'))

        # todo (aj) Tests as this is fragile in too many ways!

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
            outfile.write(_return_interrogation_script(package, req_out_file))

        # 4. Run file, which pickles results to temp file
        run_in_subprocess("vex {0} python {1}"
                          .format(tmp_env.name, tmp_out_file))

        # 5. reads that file from current program
        result = pickle.load(open(req_out_file, 'rb'))

        # 6. Move file to cache dir or delete file and return info
        if MagellanConfig.caching:
            cmd_to_run = "mv {0} {1}/"\
                .format(req_out_file, MagellanConfig.cache_dir)
            run_in_subprocess(cmd_to_run)
        else:
            run_in_subprocess("rm {0}".format(req_out_file))
        run_in_subprocess("rm {0}".format(tmp_out_file))

        # 7. Delete tmp virtual env - not necessary as it's always overwritten?
        tmp_env.vex_delete_env_self()

        return result

    @staticmethod
    def get_deps_for_package_version_json(package, version):
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

        # todo (aj) Tests as this is fragile in too many ways!

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
        tmp_env.vex_delete_env_self()

        return result



    @staticmethod
    def check_requirement_version_vs_current(cur_ver, requirement_spec):
        """ tests to see whether a requirement is satisfied by the
        current version.
        :param str cur_ver: current version to use for comparison.
        :param tuple (str, str) requirement_spec: is tuple of: (spec, version)
        :returns: bool

        """
        requirement_ver = requirement_spec[1]
        requirement_sym = requirement_spec[0]

        requirement_met = DepTools.ops[requirement_sym](
            parse_version(cur_ver), parse_version(requirement_ver))

        # print(cur_ver, requirement_sym, requirement_ver, requirement_met)
        return requirement_met, (cur_ver, requirement_sym,
                                 requirement_ver, requirement_met)

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
        :rtype dict, dict
        :return: checks, conflicts
        """

        to_check = [x[0][0] for x in ancestors if x[0][0] != 'root']
        checks = {}
        conflicts = {}
        for a in to_check:
            anc_specs = package_requirements[a]['requires'][package]['specs']
            checks[a] = anc_specs
            # print(anc_specs)
            for s in anc_specs:
                is_ok, dets = DepTools.check_requirement_version_vs_current(
                    new_version, s)
                if not is_ok:
                    if a in conflicts:
                        conflicts[a].append(dets)
                    else:
                        conflicts[a] = dets

        # pprint(checks)
        # pprint(conflicts)
        return checks, conflicts

    @staticmethod
    def check_changes_in_requirements_vs_env(requirements, descendants):
        """
        Checks to see if there are any new or removed packages in a
        requirements set vs what is currently in the env.
        NB: Checks name only, not version!

        :param <class 'pip._vendor.pkg_resources.Distribution'> requirements:
        :param list descendants: current env dependencies of package.
        :rtype: list, list
        :returns

        requirements = DepTools.get_deps_for_package_version(package, version)

        descendants look like a list of edges in acyclic graph e.g.:
            [..[('celery', '3.0.19'), ('kombu', '2.5.16')
                , [('>=', '2.5.10'), ('<', '3.0')]]..[] etc]
            (NB: specs are optional)
        """
        # todo (aj) urgent: test!
        dec_keys = {x[1][0].lower(): x[1][0] for x in descendants}
        rec_keys = {x.key: x.project_name for x in requirements.requires()}

        dset = set(dec_keys.keys())
        rset = set(rec_keys.keys())

        removed_deps = [dec_keys[x] for x in (dset - rset)]
        new_deps = [rec_keys[x] for x in (rset - dset)]
        # package = "celery"
        # f = "/tmp/magellan/cache/celery_3_0_19_req.dat"
        # # This is what's returned from
        # DepTools.get_deps_for_package_version(package, version)
        # # where "version" here is desired version.
        # uc_deps = {package: {"requirements": pickle.load(open(f, 'rb'))}}
        # requirements = uc_deps[package]['requirements']
        # ancs, descendants = Package.get_direct_links_to_any_package(
        # package, venv.edges)
        return removed_deps, new_deps

    @staticmethod
    def check_req_deps_satisfied_by_current_env(requirements, nodes):
        """
        Checks nodes (package, version) of current environment against requirements
        to see if they are satisfied

        :param <class 'pip._vendor.pkg_resources.Distribution'> requirements:
        :param list nodes: current env nodes (package, version) tuples list

        :rtype dict{dict, dict, list}
        :returns: to_return{checks, conflicts, missing}

        "checks" is a dictionary of the current checks
        "conflicts" has at least 1 conflict with required specs
        "missing" highlights any packages that are not in current environment

        """
        #todo (aj) test and break, e.g. bad nodes etc

        check_ret = DepTools.check_requirement_version_vs_current
        node_keys = {x[0].lower(): x[1] for x in nodes}

        checks = {}
        conflicts = {}
        missing = []

        for r in requirements.requires():
            checks[r.project_name] = []

            if r.key not in node_keys.keys():
                print("Requirement {0}{1} not in current environment"
                      .format(r.project_name, r.specs))
                checks[r.project_name].append(None)
                missing.append(r.project_name)
            else:
                for s in r.specs:
                    req_satisfied, req_dets = check_ret(node_keys[r.key], s)
                    # print(req_dets)
                    checks[r.project_name].append(req_dets)
                    if not req_satisfied:
                        if conflicts[r.project_name]:
                            conflicts[r.project_name].append(req_dets)
                        else:
                            conflicts[r.project_name] = [req_dets]


        to_return = {
            'checks': checks,
            'conflicts': conflicts,
            'missing': missing,
        }
        return to_return

    @staticmethod
    def detect_upgrade_conflicts(data):
        """
        Detect conflicts between packages in current environment when upgrading
        other packages.

        :param data: List of (package, desired_version)'s
        """

        uc_deps = {}
        for u in data:
            # todo (aj) check version exists on PyPI first.
            package = u[0]
            version = u[1]

            if not PyPIHelper.check_package_version_on_pypi(package, version):
                uc_deps[package] = None
                continue

            uc_deps[package] = DepTools.get_deps_for_package_version(
                package, version)
            pprint(uc_deps)

            if not uc_deps[package].requires():
                print("No requirement specs for {0} {1}"
                      .format(package, version))
            else:
                for r in uc_deps[package].requires():
                    print(r.project_name, r.key, r.specs)


def _return_interrogation_script(package, filename=None):
    """Return script to interrogate deps for package inside env"""
    head = """
import pip
import pickle
pkgs  = pip.get_installed_distributions()
"""
    mid = "p = [x for x in pkgs if x.key == '{0}'.lower()][0]".format(package)

    if not filename:
        out = ('fn = "{0}_{1}_req.dat"'
               '.format(p.key, p.version.replace(".","_"))')
    else:
        out = 'fn = "{0}"'.format(filename)

    end = "pickle.dump(p, open(fn, 'wb'))"

    nl = '\n'
    ll = 'print(p.requires())'
    return head + nl + mid + nl + out + nl + end + nl  +ll # last one for PEP8 :p


def _return_interrogation_script_json(package, filename=None):
    """Return script to interrogate deps for package inside env.
    Uses json.dump instead of pickle due to cryptic pickle/requests bug."""
    head = """
import pip
import json
pkgs  = pip.get_installed_distributions()
"""
    mid = "p = [x for x in pkgs if x.key == '{0}'.lower()][0]".format(package)

    if not filename:
        out = ('fn = "{0}_{1}_req.dat"'
               '.format(p.key, p.version.replace(".","_"))')
    else:
        out = 'fn = "{0}"'.format(filename)

    conv = """
req_dic = {'project_name': x.project_name}
for r in x.requires():
    req_dic[r.key] = {}
    req_dic[r.key]['project_name'] = r.project_name
    req_dic[r.key]['specs'] = r.specs
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

        PyPITemplate = 'https://pypi.python.org/pypi/{0}/json'

        r = requests.get(PyPITemplate.format(package))
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