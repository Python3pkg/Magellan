Magellan - Explore Python Package Dependencies like your name is Fernando!

Mission / Goals:
    The overall aim is to do with package exploration for conflict detection.
    
    E.g. Going from one version of a library to another (i.e. upgrading Django)
    can cause conflicts when some dependencies need to be upgraded, but others
    depend on the earlier versions. It may be necessary to upgrade due to 
    important security updates no longer being maintained on a platform, thus
    this requires a solution.

    
Installation:
    python setup.py install


Command line interfaces:
    magellan

        Options:
        positional arguments:
          packages              Packages to explore.

        optional arguments:
          -h, --help            show this help message and exit
          -s, --show-all-packages
                                Show all packages and exit.
          -n VENV_NAME, --venv-name VENV_NAME
                                Specify name for virtual environment, default is
                                MagEnv0, MagEnv1 etc
          -r REQUIREMENTS, --requirements REQUIREMENTS
                                requirements file (e.g. requirements.txt) to install.
          -po PIP_OPTIONS, --pip-options PIP_OPTIONS
                                String. Pip options for installation of
                                requirements.txt. E.g. '-f http://my_server.com/deployment_libs/ --trusted-host my_server.com'
          -v, --verbose         Verbose mode
          -sv, --super-verbose  Super verbose mode; also sets VERBOSE as True.


Example Usage:
    1. "magellan" or "magellan -h"
            Prints out help file.
    2. "magellan -r requirements.txt -n MyEnv"
            Sets up virtual environment "MyEnv", installs the requirements
            file using pip and runs generic analysis.
    3. "magellan -s"
            Shows all packages in current environment. Performs no further
            analysis.
    4. "magellan -s -n MyEnv"
            Shows all packages in MyEnv environment.
    4. "magellan Package1 Package2 -n MyEnv -v"
            Searches MyEnv for the packages "Package1" and "Package2" in
            verbose mode. Will produce a dependency graph and reports for MyEnv
            as well as reports for the specified package.


Roadmap:
- Use vex to handle virtualenv stuff
- list outdated major and minor versions
- accept a file containing packages "-pf --package-file" which augments the package_list
- Implement snakefood
- highlight dependencies/packages that are actually unused - redundant imports