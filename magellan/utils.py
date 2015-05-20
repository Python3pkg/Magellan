import os
import errno
import subprocess
import shlex


class MagellanConfig(object):
    """Holds magellan config info"""
    cache_dir = '/tmp/magellan/cache'
    tmp_dir = '/tmp/magellan'
    tmp_env_dir = "MagellanTmp"


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


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


