from biosimulators_test_suite.test_case import cli
from biosimulators_test_suite.warnings import TestCaseWarning
import unittest


class DockerImageTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'

    def test_InlineHelpTestCase(self):
        case = cli.InlineHelpTestCase()

        case.eval({'image': {'url': self.IMAGE}})

        with self.assertWarnsRegex(TestCaseWarning, 'should display basic help'):
            case.eval({'image': {'url': 'hello-world'}})

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `-h` option'):
            case.eval({'image': {'url': 'hello-world'}})

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `--help` option'):
            case.eval({'image': {'url': 'hello-world'}})

    def test_InlineVersionInformationTestCase(self):
        case = cli.InlineVersionInformationTestCase()

        case.eval({'image': {'url': self.IMAGE}})

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `-v` option'):
            case.eval({'image': {'url': 'hello-world'}})

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `--version` option'):
            case.eval({'image': {'url': 'hello-world'}})
