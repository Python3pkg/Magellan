from setuptools import setup
import os


# req_file = os.path.join(
#     os.path.split(os.path.abspath(__file__))[0], 'requirements.txt')
# install_requires = open(req_file).read().split()
print("*="*100)
print(__file__)
install_requires = open('requirements.txt').read().split()

test_requires = ['mock',]  # for Python2.*

classifiers = ['Development Status :: 2 - Pre-Alpha',
               'Intended Audience :: Developers',
               'Natural Language :: English',
               'Operating System :: POSIX :: Linux',
               'Programming Language :: Python :: 2.7',
               ]

setup(
    name='magellan',
    description='Explore python packages like your name is Fernando.',
    author='AJ De-Gol',
    author_email='anthony.de-gol@maplecroft.com',
    version='0.9',
    classifiers=classifiers,
    long_description=open('README.rst').read(),
    packages=['magellan'],
    package_dir={'magellan': 'magellan'},
    package_data={'magellan': ['data/*']},
    install_requires=install_requires+test_requires,
    entry_points={'console_scripts': ['magellan = magellan.main:main']},
)
