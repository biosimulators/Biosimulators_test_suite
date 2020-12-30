from biosimulators_test_suite.test_case import docker_image
import unittest


class DockerImageTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'

    def test_HasOciLabels(self):
        case = docker_image.HasOciLabels()
        case.eval({'image': {'url': self.IMAGE}})
        with self.assertWarnsRegex(UserWarning, 'should have the following'):
            case.eval({'image': {'url': 'hello-world'}})

    def test_HasBioContainersLabels(self):
        case = docker_image.HasBioContainersLabels()
        case.eval({'image': {'url': self.IMAGE}})
        with self.assertWarnsRegex(UserWarning, 'should have the following'):
            case.eval({'image': {'url': 'hello-world'}})
