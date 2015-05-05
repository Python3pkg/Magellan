import subprocess
import shlex


def run_in_subprocess(cmds):
    """Splits command line arguments and runs in subprocess"""
    cmd_args = shlex.split(cmds)
    subprocess.call(cmd_args)


def run_in_subp_ret_stdout(cmds):
    """Runs in subprocess and returns std out output."""
    cmd_args = shlex.split(cmds)
    p = subprocess.Popen(cmd_args,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.communicate()
