import subprocess
import shlex
import os
import sys


def run_in_subprocess(cmds):
    """Splits command line arguments and runs in subprocess"""
    cmd_args = shlex.split(cmds)
    subprocess.call(cmd_args)


def get_virtual_env_name(venv_name=None):
    """Create a virtual env in which to install packages
    :returns : venv_name - name of virtual environment.
    :rtype : str
    """

    if venv_name is None:
        exists = False
        venv_template = "MagEnv{}"
        # check if name exists and bump repeatedly until new
        i = 0
        while True:
            venv_name = venv_template.format(i)
            if not os.path.exists(venv_name):
                break
            i += 1
    else:
        if os.path.exists(venv_name):
            exists = True

    return venv_name, exists


def resolve_venv_name(venv_name=None):
    """Check whether virtual env exists,
    if not then indicate to perform analysis on current environment"""

    if venv_name is None:
        print("No virtual env specified, analysing local env")
        venv_name = ''
        name_bit = ''
        venv_bin = None
    else:
        venv_name = venv_name.rstrip('/')
        print("Attempting analysis of {}".format(venv_name))
        # First check specified environment exists:
        if not os.path.exists(venv_name):
            sys.exit('LAPU LAPU! Virtual Env "{}" does not exist, '
                     'please check name and try again'.format(venv_name))
        venv_bin = venv_name + '/bin/'
        name_bit = '_'
        
    return venv_name, name_bit, venv_bin

