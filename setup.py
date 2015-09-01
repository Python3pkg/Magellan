import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

from pip.req import parse_requirements
from pip.download import PipSession

# imports __version__ into setup.py namespace
with open('magellan/_version.py') as version:
    exec(version.read())

install_requires = [str(parsed.req) for parsed in parse_requirements(
    'requirements.txt', session=PipSession())]

tests_require = ['mock', 'tox']


class Tox(TestCommand):
    """
    We're going to use `tox` to run our test-suite so we test
    all supported versions of python/django
    """
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import tox here, because outside the eggs aren't loaded yet
        import tox
        errno = tox.cmdline(self.test_args)
        sys.exit(errno)


setup(
    name='magellan',
    description='Explore python packages like your name is Fernando.',
    author='AJ De-Gol',
    author_email='anthony.de-gol@maplecroft.com',
    version=__version__,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
    ],
    long_description=open('README.rst').read(),
    packages=['magellan'],
    package_dir={'magellan': 'magellan'},
    package_data={'magellan': ['data/*']},
    install_requires=install_requires,
    tests_require=tests_require,
    cmdclass={'test': Tox},
    entry_points={'console_scripts': ['magellan = magellan.main:main']},
)
