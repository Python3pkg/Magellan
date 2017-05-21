"""
Test suite for the package_utils module.
"""

import unittest
from mock import MagicMock, mock_open, patch
from magellan.package_utils import (Package, InvalidEdges)
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
    *****************
    ***** NODES ***** (list):
    *****************
    [('haystack-static-pages', '0.3.0'),
     ('django-mailchimp-v1.3-dj16', '1.3.4-mc'),
        ... etc...
     ('pybbm', '0.16.3'),
     ('newrelic', '2.46.0.37')]

     *****************
     ***** EDGES ***** (list)
     *****************
     [[('root', '0.0.0'), ('haystack-static-pages', '0.3.0')],
     [('root', '0.0.0'), ('django-mailchimp-v1.3-dj16', '1.3.4-mc')],
     [('root', '0.0.0'), ('django-cms-saq', '0.3.2')],
     [('django-cms-saq', '0.3.2'), ('beautifulsoup4', '4.3.2'),
      [('>=', '4.3.1')]],
     [('django-cms-saq', '0.3.2'), ('djangocms-text-ckeditor', '2.4.1'), []],
        ... etc ...
      [('pybbm', '0.16.3'), ('markdown', '1.7'), []],
     [('pybbm', '0.16.3'), ('postmarkup', '1.2.2'), []],
     [('pybbm', '0.16.3'), ('django-annoying', '0.8.0'), []],
     [('root', '0.0.0'), ('newrelic', '2.46.0.37')]]
    """

    def setUp(self):
        self.edges = pickle.load(open('tests/Django16edges.p', 'rb'))
        self.nodes = pickle.load(open('tests/Django16nodes.p', 'rb'))

        self.venv = MagicMock()
        self.venv.nodes = self.nodes
        self.venv.edges = self.edges

    def tearDown(self):
        pass


class TestPackageCheckVersion(TestPackageClass):
    """
    Tests for whether the package version is out of date for
    both major and minor versions.

    This module queries PyPI
    """

    def setUp(self):
        super(TestPackageCheckVersion, self).setUp()

        self.curp = 'foo'  # test package
        self.curv = '1.9.9'  # test version

    def test_Django_sanity_test(self):
        """Test outdated minor and major versions of Django"""
        test_p = "Django"
        n = [x for x in self.nodes if x[0].lower() == test_p.lower()][0]
        p = Package(n[0], n[1])
        return_info = p.check_versions()
        self.assertEqual(return_info['major_version']['outdated'], True)
        self.assertEqual(return_info['minor_version']['outdated'], True)

    def test_false_package_returns_None(self):
        """Given nonsense package, return None"""
        p = Package("abcde12345GGGGGG", '0.0.0')
        info = p.check_versions()
        self.assertEqual(info['minor_version']['outdated'], None)
        self.assertEqual(info['minor_version']['latest'], None)
        self.assertEqual(info['major_version']['outdated'], None)
        self.assertEqual(info['major_version']['latest'], None)

    def run_as_pypi_patched(self, vers, curv=None):
        """helper fn to run and get mocked pypi responses"""
        if curv is None:
            curv = self.curv

        to_patch = "magellan.package_utils.Package"
        with patch(to_patch) as MockClass:
            MockClass.get_package_versions_from_pypi.return_value = vers
            return_info = Package.check_latest_major_minor_versions(
                self.curp, curv)
        return return_info

    def test_up_to_date_maj_out_min_none(self):
        """
        Mock packages to return correct version.
        No minor.
        Maj outdated
        """
        version_list = ['2.0.0']
        info = self.run_as_pypi_patched(version_list)

        self.assertEqual(info['minor_version']['outdated'], None)
        self.assertEqual(info['minor_version']['latest'], None)
        self.assertEqual(info['major_version']['outdated'], True)
        self.assertEqual(info['major_version']['latest'], '2.0.0')

    def test_up_to_date_min_in_maj_out(self):
        """
        Mock packages to return correct version
        Minor up to date.
        Major outdated.
        """
        version_list = ['1.9.9', '2.0.0']
        info = self.run_as_pypi_patched(version_list)

        self.assertEqual(info['minor_version']['outdated'], False)
        self.assertEqual(info['minor_version']['latest'], '1.9.9')
        self.assertEqual(info['major_version']['outdated'], True)
        self.assertEqual(info['major_version']['latest'], '2.0.0')

    def test_up_to_date_fully(self):
        """
        Mock packages to return correct version
        Minor up to date.
        Major outdated.
        """
        version_list = ['1.9.9']
        info = self.run_as_pypi_patched(version_list)
        self.assertEqual(info['minor_version']['outdated'], False)
        self.assertEqual(info['minor_version']['latest'], '1.9.9')
        self.assertEqual(info['major_version']['outdated'], False)
        self.assertEqual(info['major_version']['latest'], '1.9.9')

    def test_check_vers_with_no_ver(self):
        """Pass name but not versions"""
        p = Package("Django")  # no version
        info = p.check_versions()
        self.assertEqual(info['minor_version']['outdated'], True)
        self.assertEqual(info['major_version']['outdated'], True)

    def test_check_beyond_up_to_date(self):
        """current version > latest on pypi is "up to date"

        self.curp = 'foo'  # test package
        self.curv = '1.9.9'  # test version

        the checking will return the versions in version_list

        so 1.9.9 > 1.8.1 but that is the latest on PyPI.

        """
        version_list = ['1.8.1']
        info = self.run_as_pypi_patched(version_list)
        self.assertEqual(info['minor_version']['outdated'], False)
        self.assertEqual(info['minor_version']['latest'], '1.8.1')
        self.assertEqual(info['major_version']['outdated'], False)
        self.assertEqual(info['major_version']['latest'], '1.8.1')


class TestPackageDescendantsAncestors(TestPackageClass):
    """
    Tests for class methods related to ancestors and descendants.
    In a directed graph, for a node N, with connected nodes N-1 and N+1,
    where N-1 "points"/depends on N; a similar for N+1. N-1 is the ancestor
    of N and N+1 is its descendant.

    Good candidate (from Django16) for tests is: celery
    'celery': 4 ancestors (inc. root), 3 descendants:

    ANCESTORS:
    [[('django-celery', '3.0.17'), ('celery', '3.0.19'), [('>=', '3.0.17')]],
     [('marvin', '0.7.8'), ('celery', '3.0.19'), [('==', '3.0.19')]],
     [('root', '0.0.0'), ('celery', '3.0.19')],
     [('flower', '0.8.2'), ('celery', '3.0.19'), [('>=', '2.5.0')]]]
    DESCENDANTS:
    [[('celery', '3.0.19'),  ('billiard', '2.7.3.34'),
        [('>=', '2.7.3.28'), ('<', '3.0')]],
     [('celery', '3.0.19'), ('python-dateutil', '2.4.2'),
        [('>=', '1.5')]],
     [('celery', '3.0.19'), ('kombu', '2.5.16'), [('>=', '2.5.10'),
        ('<', '3.0')]]]

    """

    def setUp(self):
        """Augment prior setup for specific celery stuff"""
        super(TestPackageDescendantsAncestors, self).setUp()
        self.celery_ancestors = [
            [('django-celery', '3.0.17'), ('celery', '3.0.19'),
             [('>=', '3.0.17')]],
            [('marvin', '0.7.8'), ('celery', '3.0.19'), [('==', '3.0.19')]],
            [('root', '0.0.0'), ('celery', '3.0.19')],
            [('flower', '0.8.2'), ('celery', '3.0.19'), [('>=', '2.5.0')]]]
        self.celery_descendants = [
            [('celery', '3.0.19'),  ('billiard', '2.7.3.34'),
             [('>=', '2.7.3.28'), ('<', '3.0')]],
            [('celery', '3.0.19'), ('python-dateutil', '2.4.2'),
             [('>=', '1.5')]],
            [('celery', '3.0.19'), ('kombu', '2.5.16'),
             [('>=', '2.5.10'), ('<', '3.0')]]]

    def test_get_ancestors_for_celery(self):
        """Celery returns correct ancestors"""
        p = Package('celery')
        self.assertEqual(p.ancestors(self.edges), self.celery_ancestors)

    def test_get_descendants_for_celery(self):
        """Celery returns correct descendants"""
        p = Package('celery')
        self.assertEqual(p.descendants(self.edges), self.celery_descendants)

    def test_all_ancestors_and_descendants_in_Django16(self):
        """test call to ancestors and descendants in Django16 twice!

        2nd call should come from cached result.
        """
        packages = {x[0].lower(): Package(x[0], x[1]) for x in self.nodes}
        for p, P in list(packages.items()):
            _ = P.ancestors(self.edges)
            _ = P.ancestors(self.edges)
            _ = P.descendants(self.edges)
            _ = P.descendants(self.edges)


class TestPackageGetDirectLinksToPackage(TestPackageClass):
    """test get_direct_links_to_package"""

    def setUp(self):
        """Augment prior setup for specific celery stuff"""
        super(TestPackageGetDirectLinksToPackage, self).setUp()
        self.celery_ancestors = [
            [('django-celery', '3.0.17'), ('celery', '3.0.19'),
             [('>=', '3.0.17')]],
            [('marvin', '0.7.8'), ('celery', '3.0.19'), [('==', '3.0.19')]],
            [('root', '0.0.0'), ('celery', '3.0.19')],
            [('flower', '0.8.2'), ('celery', '3.0.19'), [('>=', '2.5.0')]]]
        self.celery_descendants = [
            [('celery', '3.0.19'),  ('billiard', '2.7.3.34'),
             [('>=', '2.7.3.28'), ('<', '3.0')]],
            [('celery', '3.0.19'), ('python-dateutil', '2.4.2'),
             [('>=', '1.5')]],
            [('celery', '3.0.19'), ('kombu', '2.5.16'),
             [('>=', '2.5.10'), ('<', '3.0')]]]

    def test_simple_anc_dec_test(self):
        """ simply returns ancestors and descendants """
        p = Package('celery', '3.0.19')
        anc, dec = p.get_direct_links_to_package(self.edges)
        self.assertEqual(anc, self.celery_ancestors)
        self.assertEqual(dec, self.celery_descendants)


class TestPackageAncestorTrace(TestPackageClass):
    """test ancestor_trace"""

    def test_returns_dict(self):
        p = Package("Django")
        at = p.ancestor_trace(self.venv)
        self.assertEqual(type(at), dict)

    def test_check_ancestor_trace(self):

        fake_nodes = [('a', '1.0.0'), ('b', '2.0.0'),
                      ('c', '1.4.0'), ('d', '2.0.0'),
                      ('e', '1.6.0'), ('f', '210.0'), ]
        fake_edges = [[('root', '0.0.0'), fake_nodes[0]],
                      [('root', '0.0.0'), fake_nodes[1]],
                      [fake_nodes[0], fake_nodes[1]],
                      [fake_nodes[1], fake_nodes[2]],
                      [fake_nodes[2], fake_nodes[3]],
                      [fake_nodes[3], fake_nodes[4]],
                      [fake_nodes[4], fake_nodes[5]], ]

        f_venv = MagicMock()
        f_venv.nodes = fake_nodes
        f_venv.edges = fake_edges

        p = Package(fake_nodes[0][0], fake_nodes[0][1])
        ret = p.ancestor_trace(f_venv)
        self.assertEqual(ret,  {('root', '0.0.0'): 1, ('a', '1.0.0'): 0})

        p2 = Package(fake_nodes[1][0], fake_nodes[1][1])
        ret = p2.ancestor_trace(f_venv)
        self.assertEqual(ret, {('root', '0.0.0'): 1,
                               ('b', '2.0.0'): 0,
                               ('a', '1.0.0'): 1})

        p5 = Package(fake_nodes[5][0], fake_nodes[5][1])
        ret = p5.ancestor_trace(f_venv)
        self.assertEqual(ret, {('f', '210.0'): 0,
                               ('e', '1.6.0'): 1,
                               ('d', '2.0.0'): 2,
                               ('c', '1.4.0'): 3,
                               ('b', '2.0.0'): 4,
                               ('a', '1.0.0'): 5,
                               ('root', '0.0.0'): 5, })


class TestPackageResolvePackageList(TestPackageClass):
    """
    Using data from environment (nodes, edges) test correct functionality of
    static method resolve_package_list.

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


class TestPackageGetDirectLinksToAnyPackage(TestPackageClass):
    """ Tests the static method get_direct_links_to_any_package;
    similar to TestPackageFunctionalityDescendantsAncestors
    but is static and always calculates.
    """
    def setUp(self):
        """Augment prior setup for specific celery stuff"""
        super(TestPackageGetDirectLinksToAnyPackage, self).setUp()
        self.celery_ancestors = [
            [('django-celery', '3.0.17'), ('celery', '3.0.19'),
             [('>=', '3.0.17')]],
            [('marvin', '0.7.8'), ('celery', '3.0.19'), [('==', '3.0.19')]],
            [('root', '0.0.0'), ('celery', '3.0.19')],
            [('flower', '0.8.2'), ('celery', '3.0.19'), [('>=', '2.5.0')]]]
        self.celery_descendants = [
            [('celery', '3.0.19'),  ('billiard', '2.7.3.34'),
             [('>=', '2.7.3.28'), ('<', '3.0')]],
            [('celery', '3.0.19'), ('python-dateutil', '2.4.2'),
             [('>=', '1.5')]],
            [('celery', '3.0.19'), ('kombu', '2.5.16'),
             [('>=', '2.5.10'), ('<', '3.0')]]]

    def test_return_from_celery(self):
        """ancestors and descendants should match test data."""
        anc, dec = Package.get_direct_links_to_any_package(
            'celery', self.edges)
        self.assertEqual(anc, self.celery_ancestors)
        self.assertEqual(dec, self.celery_descendants)

    def test_empty_list_returned_from_invalid_package(self):
        """[],[] should be returned if package is invalid."""
        anc, dec = Package.get_direct_links_to_any_package(
            'NONSENSE_PACKAGE', self.edges)
        self.assertEqual(anc, [])
        self.assertEqual(dec, [])

    def test_raise_invalid_edges_with_invalid_edges(self):
        """Raises InvalidEdges Exception if given bad data"""
        args = ('celery', 1)
        self.assertRaises(InvalidEdges,
                          Package.get_direct_links_to_any_package, *args)

        args = ('celery', "This is bad edge data though")
        self.assertRaises(InvalidEdges,
                          Package.get_direct_links_to_any_package, *args)

    def test_raise_invalid_edges_if_edges_empty(self):
        args = ('celery', [])
        self.assertRaises(InvalidEdges,
                          Package.get_direct_links_to_any_package, *args)


if __name__ == '__main__':
    unittest.main()
