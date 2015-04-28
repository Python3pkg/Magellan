#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

from utils import (
    run_in_subprocess,
    make_virtual_env,
    install_requirements,
)

from analysis import gen_pipdeptree_reports

VERBOSE = False


def _go(**kwargs):
    """Main script of magellan program.
    
    Accomplishes the following:
        Makes virtual env
        Installs requirements
        Runs analysis and reports on venv
    """
    
    # todo(aj) make verbose global
    # verbose = kwargs['verbose']
    # print(verbose)

    # Install packages into new virtual env
    venv_name = make_virtual_env(kwargs["venv_name"])
    venv_bin = venv_name + '/bin/'
    
    run_in_subprocess(venv_bin + 'pip install pipdeptree')
    # todo (aj) PIP OPTIONS ARE HARDCODED MAPLECROFT AT PRESENT
    pip_options = "-f http://sw-srv.maplecroft.com/deployment_libs/ --trusted-host sw-srv.maplecroft.com"
    install_requirements(kwargs["requirements"], venv_bin, pip_options)

    # Run analytics for reports:
    gen_pipdeptree_reports(venv_bin=venv_bin)

    # Clean up
    keep_virtual_env = kwargs["keep_virtualenv"]
    if not keep_virtual_env:
        print("Deleting virtual env; you can change this option on invocation.")
        run_in_subprocess('rm -rf ' + venv_name)
    elif VERBOSE:
        print("Keeping virtual env: {}".format(venv_name))


def main():
    """Command line entry point for magellan."""

    parser = argparse.ArgumentParser(
        description=("Explore Python Package Dependencies "
                     "like your name is Fernando!"),
        prog="Magellan",
    )

    # POSITIONAL ARGUMENTS:
    parser.add_argument(
        'requirements',
        type=str,
        help="Input files e.g. requirements.txt or similar."
    )
    
    # OPTIONAL ARGUMENTS: 
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False, 
        help="Verbose mode"
    )
    parser.add_argument(
        '-n', '--venv-name', default=None,
        help="Specify name for virtual environment, default is MagEnv0, MagEnv1 etc",
    )
    parser.add_argument(
        '-k', '--keep-virtualenv', action='store_true', default=False,
        help='Keep virtualenv after installation. NB: Default=False, virtualenv is deleted!'
    )

    # PROCESS ARGUMENTS:
    args = parser.parse_args()
    kwargs = vars(args)
    
    _go(**kwargs)


if __name__ == "__main__":
    main()
    sys.exit()