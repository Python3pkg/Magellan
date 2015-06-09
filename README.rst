========
Magellan
========
*Explore Python Package Dependencies like your name is Fernando!*

**Mission / Goals:**

The overall aim is to do with package exploration for conflict detection.

E.g. Going from one version of a library to another (i.e. upgrading Django)
can cause conflicts when some dependencies need to be upgraded, but others
depend on the earlier versions. It may be necessary to upgrade due to
important security updates no longer being maintained on a platform, thus
this requires a solution.

*NB: Logic of running script subject to change at any point before version 1.0*


**Installation:**

python setup.py install


**Command line interfaces:**

magellan <options>


**Options:**

*Positional Arguments*

``<packages>`` e.g. ``Package1 Package2 etc..``
    Packages to explore.

*Optional Arguments*

*Fundamental*

``-h, --help``
    Show this help message and exit

``-n <venv_name>, --venv-name <venv_name>``
    Specify name for virtual environment, default isMagEnv0, MagEnv1 etc

``-r <requirements_file>, --install-requirements <requirements_file>``
    Requirements file (e.g. requirements.txt) to install.

*Functional with output*

``-l <package>, --list-all-versions <package>``
    List all versions of package on PyPI and exit. NB Can be used multiple times; supersedes -s/-p.

``-s, --show-all-packages``
    Show all packages by name and exit.

``-p, --show-all-packages-and-versions``
    Show all packages with versions and exit.

``-c, --check-versions``
    Just checks the versions of input packages and exits. Make sure this is not superseded by '-s'

``-P <package> <version>, --package-conflicts <package> <version>``
    Check whether a package will conflict with the current environment, either through addition or change. NB Can be used multiple times but must always specify desired version.

``-d, --detect-env-conflicts``
    Runs through installed packages in specified environment to detect if there are any conflicts between dependencies and versions.

``--output-dot-file``
    Output a .gv file showing connectedness of package.

``--get-ancestor-trace``
    Output .gv files showing ancestor trace of package and a truncated version.

*Configuration Arguments*

``-v, --verbose``
    Verbose mode

``--super-verbose``
    Super verbose mode

``-o pip_string, --pip-options pip_string``
    String. Pip options for installation of requirements.txt. E.g. '-f http://my_server.com/deployment_libs/ --trusted-host my_server.com'

``--path-to-env-bin <path-to-env-bin>``
    Path to virtual env bin

``-f <package_file>, --package-file <package_file>``
    File with list of packages

``--output-dir <output_dir>``
    Set output directory for package specific reports, default = 'MagellanReports'

``--cache-dir <cache-dir>``
    Cache directory - used for pip installs.

``--keep-pipdeptree-output``
    Don't delete the pipdeptree output reports.

``--keep-env-files``
    Don't delete the nodes, edges, package_requirements env files.

``--no-pip-update``
    If invoked will not update to latest version of pip when creating new virtual env.

``--logfile``
    Set this flag to enable output to magellan.log.


**Example Usage:**

- ``magellan  |  magellan -h``
        Prints out help file.
- ``magellan -r requirements.txt -n MyEnv``
        Sets up virtual environment "MyEnv", installs the requirements file using pip and runs generic analysis.
- ``magellan <packages> -c  |  magellan -c  |  magellan -c -f myPackageFile.txt``
        Checks packages to see if they are outdated on major/minor versions. If no packages or files are specified it checks all within the environment.
- ``magellan -n MyEnv -f myPackageFile.txt -c``
        Only check versions of everything in myPackageFile.txt that is in MyEnv.
- ``magellan -n MyEnv -P PackageToCheck Version``
        Highlight conflicts with current environment when upgrading or adding a new package.
        Note this argument can be called multiple times, e.g., "magellan -n MyEnv -P Django 1.8.1 -P pbr 1.0.1"
- ``magellan -n MyEnv -d``
        Detect conflicts in environment "MyEnv"
- ``magellan Package1 Package2 -n MyEnv -v``
        Searches MyEnv for the packages "Package1" and "Package2" in verbose mode. Will produce a report for MyEnv as well as reports for the specified package.
- ``magellan Package1 Package2 -n MyEnv --package-file myPackageFile.txt``
        Same as above but will also take, in addition to Package[s]1/2 a
        file containing a list of packages (csv, space or newline delimited.)
- ``magellan -n MyEnv --package-file myPackageFile.txt --super-verbose``
        Analyse packages in myPackageFile.txt, using "super verbose" (i.e. debug) mode.
- ``magellan -l <package>``
        List all versions of <package> available on PyPI.
- ``magellan -s | magellan -p``
        Shows all packages in current environment (-p with versions). Performs no further analysis.
- ``magellan -s -n MyEnv``
        Shows all packages in MyEnv environment.
- ``magellan -s > myPackageFile.txt``
        Output all packages in current environment and direct into myPackageFile.txt.
