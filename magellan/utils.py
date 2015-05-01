import subprocess
import shlex
import os
import sys
import re


def run_in_subprocess(cmds):
    """Splits command line arguments and runs in subprocess"""
    cmd_args = shlex.split(cmds)
    subprocess.call(cmd_args)


def run_in_subp_ret_stdout(cmds):
    """Runs in subprocess and returns std out output."""
    cmd_args = shlex.split(cmds)
    p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.communicate()


def vex_check_venv_exists(venv_name):
    """ Checks whether a virtual env exists using vex.

    :rtype Bool
    :return : True/False if env exists or not
    """

    vex_list = run_in_subp_ret_stdout('vex --list')[0].split("\n")
    return venv_name in vex_list


def create_vex_new_virtual_env(venv_name=None):
    """Create a virtual env in which to install packages
    :returns : venv_name - name of virtual environment.
    :rtype : str
    """

    if venv_name is None:
        venv_template = "MagEnv{}"
        # check if name exists and bump repeatedly until new
        i = 0
        while True:
            venv_name = venv_template.format(i)
            if not vex_check_venv_exists(venv_name):
                run_in_subprocess("vex -m {} true".format(venv_name))
                break
            i += 1
    else:
        if vex_check_venv_exists(venv_name):
            run_in_subprocess("vex -r {} true".format(venv_name))

        run_in_subprocess("vex -m {} true".format(venv_name))

    return venv_name


def vex_resolve_venv_name(venv_name=None):
    """Check whether virtual env exists,
    if not then indicate to perform analysis on current environment"""

    if venv_name is None:
        print("No virtual env specified, analysing local env")
        venv_name = ''
        name_bit = ''
    else:
        venv_name = venv_name.rstrip('/')
        print("Attempting analysis of {}".format(venv_name))
        # First check specified environment exists:
        if not vex_check_venv_exists(venv_name):
            sys.exit('LAPU LAPU! Virtual Env "{}" does not exist, '
                     'please check name and try again'.format(venv_name))
        name_bit = '_'

    return venv_name, name_bit


def resolve_venv_bin(v_name, v_bin=None):
    """
    :param venv_name: virtual env name
    :param venv_bin: virtual env bin dir, if any
    :return: path to venv bin directory.
    """

    # Analyse local env.
    if not v_bin and v_name == '':
        return None

    # If not supplied path, derive from v_name.
    if not v_bin and v_name:
        user = os.environ.get('USER')
        v_bin = "/home/{0}/.virtualenvs/{1}/bin/".format(user, v_name)

    # Check path and/or derived path.
    if not os.path.exists(v_bin):
        sys.exit('LAPU LAPU! {} does not exist, please specify path to '
                 '{} bin using magellan -n ENV_NAME --path-to-env-bin '
                 'ENV_BIN_PATH'.format(v_bin, v_name))
    return v_bin


def resolve_package_list(p_list, p_file):
    """Resolve packages into list from cmd line and file.

    Splits on " ", "," and "\n" when reading file.
    """

    pkg_list = p_list
    if not p_file:
        return pkg_list

    # otherwise:
    try:
        with open(p_file, 'rb') as pf:
            file_pkgs = [x for x in re.split(',|\s|\n', pf.read()) if x != '']
    except IOError as e:
        print("File not found {0}. {1}".format(p_file, e))
        file_pkgs = []

    return pkg_list + file_pkgs