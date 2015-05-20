import pickle

from magellan.env_utils import Environment
from magellan.utils import MagellanConfig, run_in_subprocess


class DepTools(object):
    @staticmethod
    def get_deps_for_package_version(package, version):
        """Gets dependencies for a specific version of a package.

        Specifically:
            1. sets up temporary virtualenv
            2. installs package/version into there using pip
            3. interrogates through virtual env using vex/pip/setuptool combo
            4. pickles results to temp file
            5. reads that file from current program
            6. deletes file and returns info
        """

        # todo (aj) Tests as this is fragile in too many ways!

        # 1. sets up temporary virtualenv
        tmp_env = Environment(MagellanConfig.tmp_env_dir)
        tmp_env.create_vex_new_virtual_env()  # NB: delete if extant!!

        # 2. installs package/version into there using pip
        # tmp_pip_options = "--cache-dir {}".format(MagellanConfig.cache_dir)
        tmp_pip_options = ("--cache-dir {} --no-deps"
                           .format(MagellanConfig.cache_dir))
        pip_package_str = '{0}=={1}'.format(package, version)
        tmp_env.vex_install_requirement(
            tmp_env.name, pip_package_str, tmp_pip_options)

        # 3. interrogates through virtual env using vex/pip/setuptool combo
        # Output to disk:

        tmp_out_file = 'mag_temp_file.py'
        req_out_file = ("{0}_{1}_req.dat"
              .format(package.lower(), version.replace(".","_")))

        with open(tmp_out_file, 'wb') as outfile:
            outfile.write(_return_interrogation_script(package, req_out_file))

        # 4. pickles results to temp file
        # run file:
        run_in_subprocess("vex {0} python {1}"
                          .format(tmp_env.name, tmp_out_file))

        # 5. reads that file from current program
        result = pickle.load(open(req_out_file, 'rb'))

        # 6. deletes file and returns info
        # run_in_subprocess("rm {0} {1}".format(tmp_out_file, req_out_file))
        run_in_subprocess("rm {0}".format(tmp_out_file))  # leaving dep file
        # tmp_env.vex_delete_env_self()

        return result

    @staticmethod
    def detect_upgrade_conflicts(data):
        """
        Detect conflicts between packages in current environment when upgrading
        other packages.

        :param data: List of (package, desired_version)'s
        """

        UCdeps = {}
        for u in data:
            # todo (aj) check version exists on PyPI first.
            package = u[0]
            version = u[1]
            UCdeps[package] = DepTools.get_deps_for_package_version(
                package, version)

            for r in UCdeps[package].requires():
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

