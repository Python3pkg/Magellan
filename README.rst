Magellan - Explore Python Package Dependencies like your name is Fernando!

Mission / Goals:
    The overall aim is to do with package exploration for conflict detection.
    
    E.g. Going from one version of a library to another (i.e. upgrading Django)
    can cause conflicts when some dependencies need to be upgraded, but others
    depend on the earlier versions. It may be necessary to upgrade due to 
    important security updates no longer being maintained on a platform, thus
    this requires a solution.

    NB: Logic of running script due to change imminently! Plan is to only run
    analytics specified on CLI. The current script is an iteration of
    functionality which must be refactored for logical flow.


    
Installation:
    python setup.py install


Command line interfaces:
    magellan

        Options:

        positional arguments:
          packages                  Packages to explore.

       optional arguments:
          -h, --help                Show this help message and exit.
          -n, --venv-name           Specify name for virtual environment, default is
                                    MagEnv0, MagEnv1 etc
          -s, --show-all-packages   Show all packages by name and exit.
          -p, --show-all-packages-and-versions
                                    Show all packages with versions and exit.
          -r, --requirements        requirements file (e.g. requirements.txt) to install.
          -o, --pip-options         String. Pip options for installation of
                                    requirements.txt. E.g. '-f
                                    http://my_server.com/deployment_libs/ --trusted-host
                                    my_server.com'
          -v, --verbose             Verbose mode
          --super-verbose           Super verbose mode; also sets VERBOSE as True.
          --path-to-env-bin         Path to virtual env bin.
          -f, --package-file        File with list of packages.
          --skip-generic-analysis   Skip generic analysis - useful for purely package
                                    analysis.
          -c, --check-versions      Just checks the versions of input packages and exits.
                                    Make sure this is not superseded by '-s or -p'
          --output-dir              Set output directory for package specific reports,
                                    default = 'MagellanReports'
          -P, --package-conflicts   Check whether a package will conflict with the current
                                    environment, either through addition or change. NB Can
                                    be used multiple times but must always specify desired
                                    version. Usage -P <package-name> <desired-version>.
          --cache-dir               Cache directory - used for pip installs.
          --keep-pipdeptree-output  Don't delete the pipdeptree output reports.
          --keep-env-files          Don't delete the nodes, edges, package_requirements env files.
          --list-all-versions       List all versions of package on PyPI and exit.



Example Usage:
    1. "magellan" or "magellan -h"
            Prints out help file.
    2. "magellan -r requirements.txt -n MyEnv"
            Sets up virtual environment "MyEnv", installs the requirements
            file using pip and runs generic analysis.
    3. "magellan -s"
            Shows all packages in current environment. Performs no further
            analysis.
    4. magellan -p"
            As above, with versions.
    5. "magellan -s -n MyEnv"
            Shows all packages in MyEnv environment.
    6. "magellan Package1 Package2 -n MyEnv -v"
            Searches MyEnv for the packages "Package1" and "Package2" in
            verbose mode. Will produce a dependency graph and reports for MyEnv
            as well as reports for the specified package.
    7. "magellan Package1 Package2 -n MyEnv --package-file myPackageFile.txt"
            Same as above but will also take, in addition to Package[s]1/2 a
            file containing a list of packages (csv, space or newline delimited.)
    8. "magellan -n MyEnv --package-file myPackageFile.txt --skip-generic-analysis"
            Only package analysis.
    9. "magellan -n MyEnv -p myPackageFile.txt -c"
            Only check versions of everything in myPackageFile.txt
    10. "magellan -n MyEnv -p myPackageFile.txt --check-versions | grep Outdated"
            Same as above but highlight the outdated packages using grep.
    11. "magellan -n MyEnv -P PackageToCheck Version"
            Highlight conflicts with current environment when upgrading or adding a new package.
            Note this argument can be called multiple times, e.g., "magellan -n MyEnv -P Django 1.8.1 -P pbr 1.0.1"