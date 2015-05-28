"""
Test suite for the Magellan dep_utils module.

Tests are for PyPIHelper class

"""

from magellan.deps_utils import PyPIHelper
import unittest
# from mock import MagicMock, mock_open, patch


class TestPackageClass(unittest.TestCase):
    """Base class for testing boilerplate."""
    pass


class TestAcquireJSONInfo(TestPackageClass):
    """
    Testing general JSON acquisition from PyPI
    """

    def test_runs(self):
        """sanity check"""
        package = "Django"
        PyPIHelper.acquire_package_json_info(package)

    def test_returns_dict(self):
        """ should return dict"""
        package = "Django"
        res = PyPIHelper.acquire_package_json_info(package)
        self.assertEqual(type(res), dict)

    def test_bad_package_returns_empty_dict(self):
        """If package is not found, return empty dict"""
        package = "BooDangoFangoMeMango"
        res = PyPIHelper.acquire_package_json_info(package)
        self.assertEqual(res, {})

class TestAvailableVersions(TestPackageClass):
    """
    Testing of PyPI available versions.
    """

    def test_callable_sanity(self):
        """
        Asserts it exists to be called with package.
        """
        package = "Django"
        PyPIHelper.all_package_versions_on_pypi(package)

    def test_returns_list(self):
        """
        return type is list
        """
        package = "Django"
        self.assertEqual(
            type(PyPIHelper.all_package_versions_on_pypi(package)), list)

    def test_specific_django_version_in_results(self):
            """
            Check version is in Django results
            """
            package = "Django"
            spec_ver = "1.6.8"
            self.assertIn(
                spec_ver, PyPIHelper.all_package_versions_on_pypi(package))

    def test_invalid_package(self):
        """
        Returns empty list on receiving bad package info.
        """

        package = "Bjango112358"
        self.assertEqual(PyPIHelper.all_package_versions_on_pypi(package), [])


class TestCheckPackageVersionOnPyPI(TestPackageClass):
    """ Tests for check_package_version_on_pypi"""

    def test_sanity_check(self):
        """
        Check it runs
        """
        package, version = "Django", "1.6.8"
        PyPIHelper.check_package_version_on_pypi(package, version)

    def test_returns_bool(self):
        """
        check bool is return type
        """
        package, version = "Django", "1.6.8"
        res = PyPIHelper.check_package_version_on_pypi(package, version)
        self.assertEqual(type(res), bool)

    def test_good_package_true(self):
        """
        check Django 1.6.8 is on PyPI
        """
        package, version = "Django", "1.6.8"
        res = PyPIHelper.check_package_version_on_pypi(package, version)
        self.assertEqual(res, True)

    def test_bad_package_false(self):
        """
        check BangoDjango 1.6.8 is not on PyPI
        """
        package, version = "BangoDjango", "1.6.8"
        res = PyPIHelper.check_package_version_on_pypi(package, version)
        self.assertEqual(res, False)

    def test_bad_version_false(self):
        """
        check Django 9999.9999.9999 is not on PyPI
        """
        package, version = "Django", "9999.9999.9999"
        res = PyPIHelper.check_package_version_on_pypi(package, version)
        self.assertEqual(res, False)