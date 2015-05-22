from pprint import pprint
import pickle
import operator
from pkg_resources import parse_version

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
            return pickle.load(open(cached_file, 'rb'))

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
        # tmp_env.vex_delete_env_self()

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

        print(cur_ver, requirement_sym, requirement_ver, requirement_met)
        return requirement_met

    @staticmethod
    def check_changes_in_requirements_vs_env(requirements, descendants):
        """ Checks to see if there are any new or removed packages in a
        requirements set vs what is currently in the env.
        NB: Checks name only, not version!

        :param <class 'pip._vendor.pkg_resources.Distribution'> requirements:
        :param list descendants: current env dependencies of package.
        :rtype: list, list
        :returns

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

        # todo (aj) remove after commit for backup
        # previous way - using loops
        # removed_deps = []
        # new_deps = []
        # for r in requirements.requires():
        #     # if rec key doesn't exist in decs it must be new.
        #     if r.key not in dec_keys.keys():
        #         new_deps.append(r.project_name)
        #
        # for d in dec_keys:
        #     # if descendant not in requirements it must have been removed.
        #     if d not in rec_keys.keys():
        #         removed_deps.append(dec_keys[d])

        return removed_deps, new_deps

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
            uc_deps[package] = DepTools.get_deps_for_package_version(
                package, version)

            pprint(uc_deps)
            if not uc_deps[package].requires():
                print("No requirement specs for {}".format(package))
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
    return head + nl + mid + nl + out + nl + end + nl  # last one for PEP8 :p


## for safekeeping / immediate delete - don't look here!
# ## PRE SETUP
# f = "/home/ade-gol/code/Magellan/dev/playground/nodes.p"
# nodes = pickle.load(open(f, 'rb'))
# #pprint(nodes)
#
# f = "/home/ade-gol/code/Magellan/dev/playground/edges.p"
# edges = pickle.load(open(f, 'rb'))
# #pprint(edges)
#
#
# from mock import MagicMock
# venv = MagicMock()
# venv.nodes = nodes
# venv.edges = edges
#
# ## defs
# import pip
# from pprint import pprint
# import pickle
# import operator
# from pkg_resources import parse_version
#
# ops = {'<': operator.lt, '<=': operator.le,
#         '==': operator.eq,'!=': operator.ne,
#         '>=': operator.ge, '>': operator.gt, }
#
# def requirements_met(cur_ver, requirement_spec):
#     """ tests to see whether a requirement is satisfied by the current version.
#     requirement_spec is tuple of: (spec, version)
#     :returns: bool
#
#     """
#     requirement_ver = requirement_spec[1]
#     requirement_sym = requirement_spec[0]
#
#     requirement_met = ops[requirement_sym](parse_version(cur_ver), parse_version(requirement_ver))
#
#     print(cur_ver, requirement_sym, requirement_ver, requirement_met)
#     return(requirement_met)
#
#
#
# ##
# package = 'fabtools'
# f = "/tmp/magellan/cache/fabtools_0_19_0_req.dat"
#
# package = "celery"
# f = "/tmp/magellan/cache/celery_3_0_19_req.dat"
# # This is what's returned from  DepTools.get_deps_for_package_version(package, version)
# # where "version" here is desired version.
# uc_deps = {package: {"requirements": pickle.load(open(f, 'rb'))}}
#
# ##
#
# pprint(uc_deps)
# if not uc_deps[package]['requirements'].requires():
#     print("No requirement specs for {}".format(package))
#
# # SOME CODE VALID BUT NOT ALL!
# for r in uc_deps[package]['requirements'].requires():
#     print(r.project_name, r.key, r.specs)
#     # using venv.nodes as pip.get_installed_distributions() is for cur. env
#     current_version = [x for x in venv.nodes if x[0].lower() == r.key][0][1]
#     for s in r.specs:
#         requirements_met(current_version, s)
#
#
# # for
# # django-chimpaign==0.1.1 -> Django [required: ==1.4.5, installed: 1.6.8]
# #
