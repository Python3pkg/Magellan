"""
Test suite for the env_utils module.
"""
from mock import MagicMock, patch, mock_open
import pickle
import unittest
from magellan.env_utils import (Environment, _write_dot_graph_to_disk,)


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


class TestWriteDotGraphs(TestPackageClass):
    """
    Testing the _write_dot_graph_to_disk method.
    Params: nodes, edges, filename
    """

    def test_sanity(self):
        """
        check it runs and returns okay; patch write.
        """

        with patch('{}.open'.format("magellan.env_utils"),
                   mock_open(), create=True):
            _write_dot_graph_to_disk(self.venv.nodes,
                                     self.venv.edges,
                                     "FakeFileName.txt")

    def test_arg_parse_bug(self):
        """
        should gracefully ignore bad data.

        In this test, one node is not (package, version) but ('a','r')
        """
        nodes = self.venv.nodes
        nodes.append(('a','r'))
        edges = self.venv.edges
        edges.append([('root', '0.0.0'), ('a', 'r')])

        with patch('{}.open'.format("magellan.env_utils"),
                   mock_open(), create=True):
            _write_dot_graph_to_disk(nodes, edges, "FakeFileName.txt")

    def test_no_version(self):
        """
        should gracefully handle missing version in nodes/edges

        In this test, one node is not (package, version) but ('package', None)
        """
        nodes = self.venv.nodes
        nodes.append(('package','None'))
        edges = self.venv.edges
        edges.append([('root', '0.0.0'), ('package', 'None')])

        with patch('{}.open'.format("magellan.env_utils"),
                   mock_open(), create=True):
            _write_dot_graph_to_disk(nodes, edges, "FakeFileName.txt")



if __name__ == '__main__':
    unittest.main()
