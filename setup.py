import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

install_requires = open('requirements.txt').read().split()

try:
    import argparse
except ImportError:
    install_requires.append('argparse')

setup(
    name='magellan',
    version='0.1a',
    description='exploration and comparison of python package dependencies',
    long_description=open('README.rst').read(),
    author='AJ De-Gol',
    author_email='anthony.de-gol@maplecroft.com',
    packages=['magellan'],
    install_requires=install_requires,
    entry_points={'console_scripts': [
                                        'magellan = magellan.cmd:main', 
                                        'mag-nav = magellan.cmd:analysis_main',
                                    ],
    },    
)
