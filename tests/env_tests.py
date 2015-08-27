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


if __name__ == '__main__':
    unittest.main()
