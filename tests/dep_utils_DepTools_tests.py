"""
Test suite for the Magellan dep_utils module.

Tests are for DepTools class; specfic focus on following methods:
? SETUP:
? - get_deps_for_package_version

DEPENDENCY SET:
- check_changes_in_requirements_vs_env
(Checks whether any packages have been added or removed, by name,
from current environment as compared to the requirements of the
(package, version) specified.

REQUIRED VERSIONS:
- check_requirement_version_vs_current
- check_req_deps_satisfied_by_current_env

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

        self.ancestors, self.descendants = \
            Package.get_direct_links_to_any_package(
                self.package, self.venv.edges)

    def test_sanity(self):
        """
        Check it runs without crashing.
        """
        DepTools.check_changes_in_requirements_vs_env(
            self.fab_reqs, self.descendants)

    def test_returns_dict(self):
        """
        method should return dictionary.
        """
        res = DepTools.check_changes_in_requirements_vs_env(
            self.fab_reqs, self.descendants)
        self.assertEqual(type(res), dict)

    def test_empty_lists_in_removed_and_new_for_fabtools(self):
        """
        There should be no differences as we are comparing a package and
        version that is already in the environment.
        """

        res = DepTools.check_changes_in_requirements_vs_env(
            self.fab_reqs, self.descendants)

        self.assertEqual(res['removed_deps'], [])
        self.assertEqual(res['new_deps'], [])


class TestDependencySetContrivedExamples(unittest.TestCase):
    """
    Testing contrived and obvious examples for Dependency Set.
    Aka: - check_changes_in_requirements_vs_env

    Contrived example:
    Current Env:
    Nodes: [('A', '1.0.0'), ('B', '1.0.0'), ('C', '1.0.0')]
    Edges: [[('A', '1.0.0'), ('B', '1.0.0'), ('==', '1.0.0')],
            [('A', '1.0.0'), ('C', '1.0.0'), ('>=', '0.5.0')],]


    NB: Edges equivalent to nodes for A.
    A 1.0.0 depends on B (==1.0.0) and C (>=0.5.0)

    """

    def setUp(self):
        self.nodes = [('A', '1.0.0'), ('B', '1.0.0'), ('C', '1.0.0')]
        self.edges = [[('A', '1.0.0'), ('B', '1.0.0'), ('==', '1.0.0')],
                      [('A', '1.0.0'), ('C', '1.0.0'), ('>=', '0.5.0')], ]
        self.ancestors, self.descendants = \
            Package.get_direct_links_to_any_package('A', self.edges)

    def test_contrived_obvious_example_1(self):
        """
        No new or removed dependencies for current package.
        """

        req_ex1 = {'project_name': 'A',
                   'version': '1.0.0',
                   'requires': {'b': {'key': 'b',
                                      'project_name': 'B',
                                      'specs': [['==', '1.0.0']], },
                                'c': {'key': 'c',
                                      'project_name': 'C',
                                      'specs': [['>=', '0.5.0']], }
                                },
                   }

        res = DepTools.check_changes_in_requirements_vs_env(
            req_ex1, self.descendants)
        self.assertEqual(res['removed_deps'], [])
        self.assertEqual(res['new_deps'], [])

    def test_contrived_obvious_example_2(self):
        """
        Add D, remove B
        A 2.0.0
        Req:
        D == 1.0.0
        C >= 0.0.5
        """

        req_ex1 = {'project_name': 'A',
                   'version': '2.0.0',
                   'requires': {'b': {'key': 'd',
                                      'project_name': 'D',
                                      'specs': [['==', '1.0.0']], },
                                'c': {'key': 'c',
                                      'project_name': 'C',
                                      'specs': [['>=', '0.5.0']], }
                                },
                   }

        res = DepTools.check_changes_in_requirements_vs_env(
            req_ex1, self.descendants)
        self.assertEqual(res['removed_deps'], ['B'])
        self.assertEqual(res['new_deps'], ['D'])

    def test_contrived_obvious_example_empty_reqs(self):
        """
        remove B and C
        A 3.0.0
        Req: Nothing
        """

        req_ex1 = {'project_name': 'A',
                   'version': '3.0.0',
                   'requires': {}, }

        res = DepTools.check_changes_in_requirements_vs_env(
            req_ex1, self.descendants)
        self.assertEqual(sorted(res['removed_deps']),
                         sorted(['B', 'C']))
        self.assertEqual(res['new_deps'], [])


class TestVersionRequirements(unittest.TestCase):
    """
    Required Version tests, methods:
    - check_requirement_satisfied

    """
    def setUp(self):
        self.cur_ver = '1.0.0'

    def test_sanity_run(self):
        """ Check runs. """
        req = ("==", "1.0.1")
        DepTools.check_requirement_satisfied(self.cur_ver, req)

    def test_returns_bool(self):
        """Should return boolean."""
        req = ("==", "1.0.1")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertEqual(type(res), bool)

    def test_details_returned(self):
        """
        Return tuple should be:
        (cur_ver, requirement_sym, requirement_ver, requirement_met)
        """
        req = ("==", "1.0.1")
        res, details = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertEqual(details, (self.cur_ver, req[0], req[1], res))

    def test_returns_true(self):
        """Should return True.

        all reqs should be satisfied.
        """
        # self.cur_ver = '1.0.0'
        req = ("==", "1.0.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = (">=", "1.0.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = (">=", "0.0.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = (">=", "0.9.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = ("!=", "1.0.1")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = ("<=", "1.0.1")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = ("<", "1.0.1")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

        req = (">", "0.0.9")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertTrue(res)

    def test_returns_false(self):
        """Should return False.

        all reqs should fail.
        """
        # self.cur_ver = '1.0.0'
        req = ("==", "1.0.1")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertFalse(res)

        req = (">=", "1.0.1")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertFalse(res)

        req = ("!=", "1.0.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertFalse(res)

        req = ("<=", "0.0.9")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertFalse(res)

        req = ("<", "1.0.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertFalse(res)

        req = (">", "1.0.0")
        res, _ = DepTools.check_requirement_satisfied(self.cur_ver, req)
        self.assertFalse(res)


class TestRequiredVersions(TestPackageClass):
    """
    - check_req_deps_satisfied_by_current_env(requirements, nodes)
        :param dict requirements:
        requirements = DepTools.get_deps_for_package_version(package, version)

        :param list nodes: current env nodes (package, version) tuples list

    Using for test: fabtools : 0.19.0
    """

    def setUp(self):
        """Augment prior setup for specific requirements"""
        super(TestRequiredVersions, self).setUp()

        self.package = "fabtools"
        self.version = "0.19.0"
        self.fab_reqs = json.load(
            open("tests/deputils_data/fabtools_0_19_0_req.json", 'rb'))

        self.ancestors, self.descendants = \
            Package.get_direct_links_to_any_package(
                self.package, self.venv.edges)

    def sanity_checks(self, res):
        """Standard true everytime"""
        self.assertEqual(type(res), dict)

        self.assertTrue('checks' in res)
        self.assertEqual(type(res['checks']), dict)

        self.assertTrue('conflicts' in res)
        self.assertEqual(type(res['conflicts']), dict)

        self.assertTrue('missing' in res)
        self.assertEqual(type(res['missing']), list)

    def test_sanity_run(self):
        """Check runs without crashing"""
        res = DepTools.check_req_deps_satisfied_by_current_env(
            self.fab_reqs, self.nodes)
        self.sanity_checks(res)


class TestRequiredVersionsContrivedExamples(unittest.TestCase):
    """
    Testing contrived and obvious examples for Required Versions

    aka: check_req_deps_satisfied_by_current_env(requirements, nodes):

    Checks nodes (package, version) of current environment against
        requirements to see if they are satisfied

        :param dict requirements:
        requirements = DepTools.get_deps_for_package_version(package, version)

        :param list nodes: current env nodes (package, version) tuples list

        :rtype dict{dict, dict, list}
        :returns: to_return{checks, conflicts, missing}

        "checks" is a dictionary of the current checks
        "conflicts" has at least 1 conflict with required specs
        "missing" highlights any packages that are not in current environment
    """

    def setUp(self):
        # Current Env:
        self.nodes = [('A', '1.0.0'), ('B', '1.0.0'), ('C', '1.0.0')]
        self.edges = [[('A', '1.0.0'), ('B', '1.0.0'), ('==', '1.0.0')],
                      [('A', '1.0.0'), ('C', '1.0.0'), ('>=', '0.5.0')], ]
        self.ancestors, self.descendants = \
            Package.get_direct_links_to_any_package('A', self.edges)

    def sanity_checks(self, res):
        """Standard true everytime"""
        self.assertEqual(type(res), dict)

        self.assertTrue('checks' in res)
        self.assertEqual(type(res['checks']), dict)

        self.assertTrue('conflicts' in res)
        self.assertEqual(type(res['conflicts']), dict)

        self.assertTrue('missing' in res)
        self.assertEqual(type(res['missing']), list)

    def test_contrived_obvious_example_1(self):
        """
        Should run with no requirements.
        """
        req_ex1 = {'project_name': 'A',
                   'version': '1.0.0',
                   'requires': {}, }
        res = DepTools.check_req_deps_satisfied_by_current_env(
            req_ex1, self.nodes)
        self.sanity_checks(res)

    def test_contrived_obvious_example_2(self):
        """
        All reqs should be satisfied.
        """
        req_ex1 = {'project_name': 'A',
                   'version': '1.0.0',
                   'requires': {'b': {'key': 'b',
                                      'project_name': 'B',
                                      'specs': [['==', '1.0.0']], },
                                'c': {'key': 'c',
                                      'project_name': 'C',
                                      'specs': [['>=', '0.5.0']], }, }, }
        res = DepTools.check_req_deps_satisfied_by_current_env(
            req_ex1, self.nodes)
        self.sanity_checks(res)

        missing = []  # no missing
        conflicts = {}  # no conflicts
        self.assertEqual(res['missing'], missing)
        self.assertEqual(res['conflicts'], conflicts)

    def test_contrived_obvious_eg2_missing_req(self):
        """
        'D' should be in missing

        A 2.
        """
        req_ex1 = {'project_name': 'A',
                   'version': '1.0.0',
                   'requires': {'b': {'key': 'b',
                                      'project_name': 'B',
                                      'specs': [['==', '1.0.0']], },
                                'c': {'key': 'c',
                                      'project_name': 'C',
                                      'specs': [['>=', '0.5.0']], },
                                'd': {'key': 'd',
                                      'project_name': 'D',
                                      'specs': [['>=', '1.5.0']], },
                                },
                   }
        res = DepTools.check_req_deps_satisfied_by_current_env(
            req_ex1, self.nodes)
        self.sanity_checks(res)

        missing = ['D']  # no missing
        conflicts = {}  # no conflicts
        self.assertEqual(res['missing'], missing)
        self.assertEqual(res['conflicts'], conflicts)


    def test_multiple_requirements(self):
        """Multiple requirements should be evaluated when present."""
        self.fail("Write test.")

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
