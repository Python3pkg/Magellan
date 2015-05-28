"""
Test suite for the Magellan dep_utils module.

Tests are for DepTools class; specfic focus on following methods:
- check_changes_in_requirements_vs_env
- check_req_deps_satisfied_by_current_env
- check_requirement_version_vs_current
- get_deps_for_package_version
- check_if_ancestors_still_satisfied
"""

import unittest
from mock import MagicMock, mock_open, patch


class TestPackageClass(unittest.TestCase):
    """Base class for testing boilerplate."""
    pass

# def test_(self):
#         """
#
#         """
#         self.fail("Write Test!!!")
