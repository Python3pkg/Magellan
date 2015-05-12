import unittest

from magellan.package_utils import Package


class TestPackageClass(unittest.TestCase):

    def test_package_create_and_name(self):
        tp = Package("test")
        self.assertEqual(tp.name, 'test')

    def test_package_lowers_name_for_key(self):
        tp = Package("Test")
        self.assertEqual(tp.key, 'test')

    def test_package_versions(self):
        tp_with_ver = Package("Test", '1.0')
        self.assertEqual(tp_with_ver.version, '1.0')

        tp_without_ver = Package("Test")
        self.assertEqual(tp_without_ver.version, None)