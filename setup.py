from setuptools import setup

install_requires = open('requirements.txt').read().split()

setup(
    author='AJ De-Gol',
    author_email='anthony.de-gol@maplecroft.com',
    name='magellan',
    description=('Exploration of python package dependencies '
                 'in your environment.'),
    version='0.1',
    long_description=open('README.rst').read(),
    packages=['magellan'],
    install_requires=install_requires,
    entry_points={'console_scripts': ['magellan = magellan.cmd:main']},
)
