"""
Test suite for the Magellan dep_utils module.

Tests are for DepTools class; specfic focus on following methods:
? SETUP:
? - get_deps_for_package_version

DEPENDENCY SET:
- check_changes_in_requirements_vs_env

REQUIRED VERSIONS:
- check_req_deps_satisfied_by_current_env
- check_requirement_version_vs_current

ANCESTOR DEPENDENCIES:
- check_if_ancestors_still_satisfied
"""

import unittest
import pickle
import json
from mock import MagicMock, mock_open, patch

from magellan.deps_utils import DepTools
from magellan.package_utils import Package


class TestPackageClass(unittest.TestCase):
    """Base class for testing boilerplate."""
    def setUp(self):
        self.edges = pickle.load(
            open("tests/deputils_data/deptest_edges.p", 'rb'))
        self.nodes = pickle.load(
            open("tests/deputils_data/deptest_nodes.p", 'rb'))
        self.package_requirements = pickle.load(
            open("tests/deputils_data/deptest_package_requirements.p", 'rb'))

        self.venv = MagicMock()
        self.venv.nodes = self.nodes
        self.venv.edges = self.edges
        self.venv.package_requirements = self.package_requirements

    def tearDown(self):
        pass


class TestDependencySet(TestPackageClass):
    """
    Dependency set tests, methods:
    - check_changes_in_requirements_vs_env

    good package for test is
    fabtools : 0.19.0
    """

    def setUp(self):
        """Augment prior setup for specific requirements"""
        super(TestDependencySet, self).setUp()

        self.package = "fabtools"
        self.version = "0.19.0"
        self.fab_reqs = json.load(
            open("tests/deputils_data/fabtools_0_19_0_req.json", 'rb'))

        self.ancestors, self.descendants = Package.get_direct_links_to_any_package(
            self.package, self.venv.edges)

    def test_sanity(self):
        """
        Check it runs without crashing.
        """
        res = DepTools.check_changes_in_requirements_vs_env(
            self.fab_reqs, self.descendants)




# class TestRequiredVersions(TestPackageClass):
#     """
#     Required Version tests, methods:
#     - check_req_deps_satisfied_by_current_env
#     - check_requirement_version_vs_current
#     """
#     def test_(self):
#         """
#
#         """
#         self.fail("Write Test!!!")
#
#
# class TestAncestorDependencies(TestPackageClass):
#     """
#     Ancestor Dependency tests, methods:
#     - check_if_ancestors_still_satisfied
#     """
#     def test_(self):
#         """
#
#         """
#         self.fail("Write Test!!!")
#







# def test_(self):
#         """
#
#         """
#         self.fail("Write Test!!!")
