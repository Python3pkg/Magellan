import subprocess
import shlex
import virtualenv
import os
import sys


def run_in_subprocess(cmds):
    """Splits command line arguments and runs in subprocess"""
    
    cmd_args = shlex.split(cmds)
    subprocess.call(cmd_args)


def _make_virtual_env(venv_name=None):
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
            if not os.path.exists(venv_name):
                break
            i += 1
    else:
        if os.path.exists(venv_name):
            sys.exit("Name {} already exists; please select different name or delete!".format(venv_name))
            

    # todo(aj) wrap in try catch
    print("Attempting to create the temporary virtualenv {}".format(venv_name))
    virtualenv.create_environment(venv_name)

    return venv_name


def _install_requirements(requirements_txt, venv_bin):
    """ Install packages in environment based on requirements file. """
    print("-"*72)
    print("Installing requirements!")

    # pip install -r requirements.txt
    # -f http://sw-srv.maplecroft.com/deployment_libs/ --trusted-host sw-srv.maplecroft.com

    # with open('MagPip.cfg', 'r') as f:
    #    pip_options = f.read()

    pip_options = "-f http://sw-srv.maplecroft.com/deployment_libs/ --trusted-host sw-srv.maplecroft.com"
    # todo(aj) pass as config file as option
    # todo(aj) return codes to ensure success

    # todo(aj) try except
    print("Installing packages.")
    run_in_subprocess(venv_bin + 'pip install -r {0} {1}'.format(requirements_txt, pip_options))

def _resolve_venv_name(venv_name=None):
    """Check whether virtual env exists, if not then indicate to perform analysis on current environment"""
    if venv_name is None:
        print("No virtual env specified, analysing local env")
        venv_name = ''
        name_bit = ''
        venv_bin = None
    else:
        print("Attempting analysis of {}".format(venv_name))
        # First check specified environment exists:
        if not os.path.exists(venv_name):
            sys.exit('LAPU LAPU! Virtual Env "{}" does not exist, please check and try again'.format(venv_name))
        venv_bin = venv_name + '/bin/'
        name_bit = '_'
        
    return venv_name, name_bit, venv_bin