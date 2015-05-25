import os
import errno
import subprocess
import shlex


class MagellanConfig(object):
    """Holds magellan config info"""
    tmp_dir = '/tmp/magellan'
    caching = True
    cache_dir = '{0}/cache'.format(tmp_dir)
    tmp_env_dir = "MagellanTmp"

    @staticmethod
    def setup_cache():
        """Setup cache dir"""
        mkdir_p(MagellanConfig.cache_dir)

    @staticmethod
    def tear_down_cache():
        """remove cache dir"""
        # NB: mainly useful for debugging
        cmd_to_run = "rm -r {0}".format(MagellanConfig.tmp_dir)
        run_in_subprocess(cmd_to_run)


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
    """
    from stackoverflow:
    http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


