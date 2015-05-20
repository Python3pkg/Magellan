"""
NB: This is less than draft work-in-progress and subject to change very soon!

Example Usage:
"magellan" or "magellan -h"
Prints out help file.

"magellan -r requirements.txt -n MyEnv"
Sets up virtual environment "MyEnv", installs the requirements file using pip and runs generic analysis.

"magellan -s"
Shows all packages in current environment. Performs no further analysis.

magellan -sv"
As above, with versions.

"magellan -s -n MyEnv"
Shows all packages in MyEnv environment.

"magellan Package1 Package2 -n MyEnv -v"
Searches MyEnv for the packages "Package1" and "Package2" in verbose mode. Will produce a dependency graph and reports for MyEnv as well as reports for the specified package.

"magellan Package1 Package2 -n MyEnv --package-file myPackageFile.txt"
Same as above but will also take, in addition to Package[s]1/2 a file containing a list of packages (csv, space or newline delimited.)

"magellan -n MyEnv --package-file myPackageFile.txt --skip-generic-analysis"
Only package analysis.

"magellan -n MyEnv -p myPackageFile.txt --check-versions"
Only check versions of everything in myPackageFile.txt

"magellan -n MyEnv -p myPackageFile.txt -c | grep Outdated"
Same as above but highlight the outdated packages using grep.
"""

from magellan.utils import run_in_subp_ret_stdout as runna
