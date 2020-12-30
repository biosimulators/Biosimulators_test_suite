from biosimulators_test_suite.test_case import docker_image
from biosimulators_test_suite.warnings import TestCaseWarning
import unittest


class DockerImageTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'

    def test_DefaultUserIsRoot(self):
        case = docker_image.DefaultUserIsRoot()
        with self.assertWarnsRegex(TestCaseWarning, 'should not declare default users'):
            case.eval({'image': {'url': 'hello-world'}}, expected_user=('undefined',))

    def test_DeclaresSupportedEnvironmentVariables(self):
        case = docker_image.DeclaresSupportedEnvironmentVariables()
        with self.assertWarnsRegex(TestCaseWarning, 'should declare the environment variables'):
            case.eval({'image': {'url': 'hello-world'}})

    def test_HasOciLabels(self):
        case = docker_image.HasOciLabels()
        case.eval({'image': {'url': self.IMAGE}})
        with self.assertWarnsRegex(TestCaseWarning, 'should have the following'):
            case.eval({'image': {'url': 'hello-world'}})

    def test_HasBioContainersLabels(self):
        case = docker_image.HasBioContainersLabels()
        case.eval({'image': {'url': self.IMAGE}})
        with self.assertWarnsRegex(TestCaseWarning, 'should have the following'):
            case.eval({'image': {'url': 'hello-world'}})
