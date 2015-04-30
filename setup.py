from setuptools import setup

install_requires = open('requirements.txt').read().split()

classifiers = ['Development Status :: 2 - Pre-Alpha',
               'Intended Audience :: Developers',
               'Natural Language :: English',
               'Operating System :: POSIX :: Linux',
               'Programming Language :: Python :: 2.7',
               ]

setup(
    name='magellan',
    description=('Exploration of python package dependencies '
                 'in your environment.'),
    author='AJ De-Gol',
    author_email='anthony.de-gol@maplecroft.com',
    version='0.1',
    classifiers=classifiers,
    long_description=open('README.rst').read(),
    packages=['magellan'],
    install_requires=install_requires,
    entry_points={'console_scripts': ['magellan = magellan.cmd:main']},
)
