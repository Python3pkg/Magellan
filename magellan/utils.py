import os
import errno
import subprocess
import shlex


class MagellanConfig(object):
    """Holds magellan config info"""
    tmp_dir = '/tmp/magellan'
    caching = True
    cache_dir = os.path.join(tmp_dir, 'cache')
    tmp_env_dir = "MagellanTmp"
    output_dir = "MagellanReports/"

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

    @staticmethod
    def setup_output_dir(kwargs, package_list):
        """Setup directory for output files if any are to be produced"""
        if kwargs['output_dir']:
            MagellanConfig.output_dir = kwargs['output_dir']

        if package_list:
            mkdir_p(MagellanConfig.output_dir)


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
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


