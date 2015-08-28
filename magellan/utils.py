import os
import errno
import subprocess
import shlex
from pkg_resources import resource_filename as pkg_res_resource_filename

class MagellanConfig(object):
    """Holds magellan config info"""
    tmp_dir = '/tmp/magellan'
    caching = True
    cache_dir = os.path.join(tmp_dir, 'cache')
    tmp_env_dir = "MagellanTmp"
    vexrc = pkg_res_resource_filename('magellan', 'data/tmpVexRC')
    vex_options = '--config {}'.format(vexrc)


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
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def print_col(s, bg=None, fg=None, pretty=False, header=False):
    """Interface for pretty printing in colour"""
    if not (bg or fg):
        if header:
            bg = "white"
            fg = "blue"
        else:
            bg = "blue"
            fg = "white"
    if not bg:
        bg = "white"
    if not fg:
        fg = "black"
    _print_col(s, bg, fg, pretty)


def _print_col(s, bg, fg, pretty=False):
    """
    Save some boilerplate with Colour class.

    May fall down if supplied invalid colours - up to user.

    :param s: string to print
    :param bg: background colour
    :param fg:  text colour
    """
    from colorclass import Color  # better at top?

    # This looks dense because of escaping; essentially it's to get something
    # that looks like: {bgcolor}{fgcolor}#string_to_print#{/bgcolor}{/fgcolor}
    if pretty:
        full_s = r'{{bg{0}}}{{{1}}}{2}{{/bg{0}}}{{/{1}}}'.format(bg, fg, s)
        print(Color(full_s))
    else:
        print(s)

