Magellan - Explore Python Package Dependencies like your name is Fernando!

Mission / Goals:
    Magellan will be an interface to several third party packages going up in
    complexity with each. Beginning with pipdeptree and moving to snakefood.
    
    The overall aim is to do with conflict detection and resolution. 
    
    E.g. Going from one version of a library to another (i.e. upgrading Django)
    can cause conflicts when some dependencies need to be upgraded, but others
    depend on the earlier versions. It may be necessary to upgrade due to 
    important security updates no longer being maintained on a platform, thus
    this is requires a solution.
    
    Attempting to parse the requirements of an individual package is fraught
    with difficulty; particularly as the requirements can change at the runtime
    of the install. 
    
    pip itself has no "proper" conflict resolution, but it is acceptable for 
    most use cases. Due to this, in order to get the "current" conflict res
    that pip uses, we set up a virtualenv and install all the required packages 
    into it. From here, as the files are installed, there are many packages and
    commands that assist in exploring.
    
    
    
Installation:
    python setup.py install
    NB: Uses ez_install so DO NOT use sudo! (And don't do that anyway!)
    

Command line interfaces:
    magellan    +options
        sets up venv
        installs the requirements from file
        runs quick analysis
        deletes (optionally) venv
        
    mag-nav     +options    
        runs analysis on venv or environment
        can specify any number of individual packages

