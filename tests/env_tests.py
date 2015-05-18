"""
Test suite for the env_utils module.
"""
import unittest
from mock import MagicMock, mock_open, patch
from magellan.env_utils import Environment

class TestEnvSetup(unittest.TestCase):
    """
    Test the environment properly initialises
    """
    def test_init(self):
        venv = Environment("testName")
        self.assertEqual(venv.name, "testName")


if __name__ == '__main__':
    unittest.main()
