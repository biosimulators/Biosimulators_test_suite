from biosimulators_test_suite.test_case import cli
from biosimulators_test_suite.warnings import TestCaseWarning
import shutil
import tempfile
import unittest


class DockerImageTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_CliDisplaysHelpInline(self):
        case = cli.CliDisplaysHelpInline()

        case.eval({'image': {'url': self.IMAGE}}, self.dirname)

        with self.assertWarnsRegex(TestCaseWarning, 'should display basic help'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `-h` option'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `--help` option'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

    def test_CliDescribesSupportedEnvironmentVariablesInline(self):
        case = cli.CliDescribesSupportedEnvironmentVariablesInline()

        with self.assertWarnsRegex(TestCaseWarning, 'should describe the environment variables'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

    def test_CliDisplaysVersionInformationInline(self):
        case = cli.CliDisplaysVersionInformationInline()

        case.eval({'image': {'url': self.IMAGE}}, self.dirname)

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `-v` option'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

        with self.assertWarnsRegex(TestCaseWarning, 'should support the `--version` option'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)
