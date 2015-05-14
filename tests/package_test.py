"""
Test suite for the package_utils module.

First we define the correct and incorrect Package behaviour:

Package CLASS should:
STATIC METHODS:
- Given a virtual environment (ENVIRONMENT CLASS), and a list of packages (in
the form of a file [comma, space and/or \n delimited], or as a list supplied
from the command line) resolve which packages exist in the environment, and
return a list of those packages by name.

- Given any individual package name, and a list of nodes and edges(*) Calculate
the "distance" between all other vertices.
(*) nodes are a list of (PackageName, Version) tuples, edges are a list of
node-tuple pairs such that the former is the direct ancestor of the latter,
said another way: the edges are the edges of a directed graph where the vertices
are the node tuples.

- Given a package and edges, return the immediate ancestors and descendants of
said package.



Package INSTANCES should:
- Have a name
- Optionally a version
- Be able to return a list of ancestors and descendants based on being
passed a list of edges.
    * Edges of the form:
    [[('root', '0.0.0'), ('haystack-static-pages', '0.3.0')],
    [('root', '0.0.0'), ('django-mailchimp-v1.3-dj16', '1.3.4-mc')],
    [('root', '0.0.0'), ('django-cms-saq', '0.3.2')]]
- Calculate an ancestor trace: all the packages that depend on it up to the
environment root.
-


"""
import unittest
from mock import MagicMock
from magellan.package_utils import Package
import pickle


class TestPackageSetup(unittest.TestCase):
    """
    Basic setup tests for package.
    """

    def test_package_create_and_name(self):
        """New package has as name"""
        tp = Package("test")
        self.assertEqual(tp.name, 'test')

    def test_package_lowers_name_for_key(self):
        """New package has key which is name.lower()"""
        tp = Package("Test")
        self.assertEqual(tp.key, 'test')

    def test_package_versions(self):
        """Package has version or None if not supplied"""
        tp_with_ver = Package("Test", '1.0')
        self.assertEqual(tp_with_ver.version, '1.0')

        tp_without_ver = Package("Test")
        self.assertEqual(tp_without_ver.version, None)

    def test_package_ancestors(self):
        """Newly created ancestor list (internal _var) is empty."""

        tp = Package("haystack-static-pages",  '0.3.0')
        self.assertEqual(len(tp._ancestors), 0)


class TestPackageClass(unittest.TestCase):
    def setUp(self):
        self.edges = pickle.load(open('tests/Django16edges.p', 'rb'))
        self.nodes = pickle.load(open('tests/Django16nodes.p', 'rb'))


class TestPackageFunctionalityResolvePackageList(TestPackageClass):
    """
    Using data from environment (nodes, edges) test correct functionality.

    Given a list and/or a filename with packages (comma, csv, \n delim.);
    return a list of all packages in the environment
    """

    def test_resolve_package_list_single_package_Django(self):
        """Check package "Django" is valid from command line."""
        venv = MagicMock()
        venv.nodes = self.nodes

        # Single package Django
        kwargs = {'package_file': None, 'packages': ['Django']}

        self.assertEqual(
            Package.resolve_package_list(venv, kwargs), ['Django'])

    def test_resolve_package_list_two_packages(self):
        """Check ['Django', 'whowhatwhere'] resolve from cmd line"""
        venv = MagicMock()
        venv.nodes = self.nodes

        # Single package Django
        kwargs = {'package_file': None, 'packages': ['Django, whowhatwhere']}

        self.assertEqual(
            Package.resolve_package_list(venv, kwargs), ['Django', 'whowhatwhere'])

    def test_resolve_package_list_two_packages(self):
        """Check ['Django', 'whowhatwhere'] resolve from cmd line"""
        venv = MagicMock()
        venv.nodes = self.nodes

        # Single package Django
        kwargs = {'package_file': None, 'packages': ['Django, whowhatwhere']}

        self.assertEqual(
            Package.resolve_package_list(venv, kwargs), ['Django', 'whowhatwhere'])




if __name__ == '__main__':
    unittest.main()