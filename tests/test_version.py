import biosimulators_test_suite
import unittest


class VersionTestCase(unittest.TestCase):
    def test(self):
        self.assertIsInstance(biosimulators_test_suite.__version__, str)
