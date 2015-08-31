"""
Test suite for the env_utils module.
"""
from mock import MagicMock
import pickle
import unittest
from magellan.env_utils import Environment


class TestEnvSetup(unittest.TestCase):
    """
    Test the environment properly initialises
    """
    def test_init(self):
        venv = Environment("testName")
        self.assertEqual(venv.name, "testName")

    def test_foo(self):
        pass


class TestPackageClass(unittest.TestCase):
    """
    Helper class for other tests to reduce boilerplate on things that
    never change.
    """

    def setUp(self):
        self.edges = pickle.load(open('tests/Django16edges.p', 'rb'))
        self.nodes = pickle.load(open('tests/Django16nodes.p', 'rb'))

        self.venv = MagicMock()
        self.venv.nodes = self.nodes
        self.venv.edges = self.edges

    def tearDown(self):
        pass


class TestVexCheckEnvExists(unittest.TestCase):
    """
    Should invoke vex to check found environments.
    Buffer API and string issues crop up in py34
    """

    def test_sanity(self):
        """should run"""

        bool_back = Environment.vex_check_venv_exists('TestName')
        self.assertIn(bool_back, [True, False])


if __name__ == '__main__':
    unittest.main()
