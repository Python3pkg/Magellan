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
said another way: the edges are the edges of a directed graph where the
vertices are the node tuples.

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
from mock import MagicMock, mock_open, patch
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

        tp = Package("haystack-static-pages", '0.3.0')
        self.assertEqual(len(tp._ancestors), 0)


class TestPackageClass(unittest.TestCase):
    """
    Helper class for other tests to reduce boilerplate on things that
    never change.

    Nodes look like list:
    [('haystack-static-pages', '0.3.0'),
     ('django-mailchimp-v1.3-dj16', '1.3.4-mc'),
     ... etc...
     ('pybbm', '0.16.3'),
     ('newrelic', '2.46.0.37')]
    """

    def setUp(self):
        self.edges = pickle.load(open('tests/Django16edges.p', 'rb'))
        self.nodes = pickle.load(open('tests/Django16nodes.p', 'rb'))

        self.venv = MagicMock()
        self.venv.nodes = self.nodes

    def tearDown(self):
        pass


class TestPackageFunctionalityResolvePackageList(TestPackageClass):
    """
    Using data from environment (nodes, edges) test correct functionality.

    Given a list and/or a filename with packages (comma, csv, \n delim.);
    return a list of all packages in the environment
    """

    def test_resolve_package_list_single_package_Django(self):
        """Check package "Django" is valid from command line."""
        kwargs = {'package_file': None, 'packages': ['Django']}
        self.assertEqual(
            Package.resolve_package_list(self.venv, kwargs), ['Django'])

    def test_resolve_package_list_two_packages(self):
        """Check ['Django', 'whowhatwhere'] resolve from cmd line"""
        kwargs = {'package_file': None, 'packages': ['Django', 'whowhatwhere']}
        self.assertEqual(
            sorted(Package.resolve_package_list(self.venv, kwargs)),
            sorted(['Django', 'whowhatwhere']))

    def test_resolve_package_list_two_packages_one_bad(self):
        """Check ['Django', 'NONSENSE']  returns just Django"""
        kwargs = {'package_file': None, 'packages': ['Django', 'NONSENSE']}
        self.assertEqual(
            Package.resolve_package_list(self.venv, kwargs), ['Django'])

    def test_resolve_package_list_two_packages_all_bad(self):
        """Check ['bad1', 'bad2'] return []"""
        kwargs = {'package_file': None, 'packages': ['bad1', 'bad2']}
        self.assertEqual(
            Package.resolve_package_list(self.venv, kwargs), [])

    def test_resolve_package_list_no_packages(self):
        """Return [] if given nothing"""
        kwargs = {'package_file': None, 'packages': []}
        self.assertEqual(
            Package.resolve_package_list(self.venv, kwargs), [])

    def test_resolve_package_list_single_package_in_file(self):
        """Check file with contents Django returns ['Django']"""
        kwargs = {'package_file': 'FakePackageFile.txt', 'packages': []}
        data = "Django"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), ['Django'])

    def test_resolve_package_list_2_packs_in_file_1_bad(self):
        """Check file with contents "Django, Nonsense" returns ['Django']"""
        kwargs = {'package_file': 'FakePackageFile.txt', 'packages': []}
        data = "Django, Nonsense"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), ['Django'])

    def test_resolve_package_list_empty_file_returns_empty_list(self):
        """Empty file returns []"""
        kwargs = {'package_file': 'FakePackageFile.txt', 'packages': []}
        data = ""  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), [])

    def test_resolve_package_list_mixed_file_returns_Django(self):
        """file with "bad1, bad2 bad3 \n Django" returns ["Django"]"""
        kwargs = {'package_file': 'FakePackageFile.txt', 'packages': []}
        data = "bad1, bad2 bad3 \n Django"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), ['Django'])

    def test_resolve_package_list_two_packages_in_file(self):
        """file with 'Django pycrypto' returns ['Django', 'pycrypto']"""
        kwargs = {'package_file': 'FakePackageFile.txt', 'packages': []}
        data = "Django pycrypto"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                sorted(Package.resolve_package_list(self.venv, kwargs)),
                sorted(['Django', 'pycrypto']))

    def test_resolve_package_list_all_nodes_from_cmd_line(self):
        """Check all nodes return as list when given as list from cmd line"""
        kwargs = {'package_file': 'FakePackageFile.txt',
                  'packages': [x[0] for x in self.nodes]}
        data = ""
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                sorted(Package.resolve_package_list(self.venv, kwargs)),
                sorted(kwargs['packages']))

    def test_resolve_package_list_all_nodes_from_package_file(self):
        """Check all nodes return as list when given as list from file"""
        kwargs = {'package_file': 'FakePackageFile.txt', 'packages': []}
        all_nodes = [x[0] for x in self.nodes]
        data = " ".join(all_nodes)
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                sorted(Package.resolve_package_list(self.venv, kwargs)),
                sorted(all_nodes))

    def test_resolve_package_list_packages_from_file_and_cmd_line(self):
        """Django from cmd, pycrypt from file returns ['Django', 'pycrypt'"""
        kwargs = {'package_file': 'FakePackageFile.txt',
                  'packages': ['Django']}
        data = "pycrypto"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                sorted(Package.resolve_package_list(self.venv, kwargs)),
                sorted(['Django', 'pycrypto']))

    def test_resolve_package_list_same_package_from_file_and_cmd_line(self):
        """Duplicates are taken care of; Django from file and cmd returns just
        ['Django']"""
        kwargs = {'package_file': 'FakePackageFile.txt',
                  'packages': ['Django']}
        data = "Django"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), ['Django'])

    def test_resolve_package_list_bad_data_ints(self):
        """ Given bad data INTS, copes gracefully.  """
        kwargs = {'package_file': 'FakePackageFile.txt',
                  'packages': [1]}
        data = "2"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), [])

    def test_resolve_package_list_bad_data_obj(self):
        """ Given bad data INTS, copes gracefully.  """
        kwargs = {'package_file': 'FakePackageFile.txt',
                  'packages': [type, object]}
        data = "2"  # mocked file data
        with patch('{}.open'.format("magellan.package_utils"),
                   mock_open(read_data=data), create=True):
            self.assertEqual(
                Package.resolve_package_list(self.venv, kwargs), [])

if __name__ == '__main__':
    unittest.main()
    print("\n" * 3)