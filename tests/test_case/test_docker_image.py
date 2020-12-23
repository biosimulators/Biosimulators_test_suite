from biosimulators_test_suite.test_case import docker_image
import unittest


class DockerImageTestCaseTest(unittest.TestCase):
    def test_OciLabelsCase(self):
        case = docker_image.OciLabelsCase()
        case.eval({'image': {'url': 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'}})
        with self.assertWarnsRegex(UserWarning, 'should have the following'):
            case.eval({'image': {'url': 'hello-world'}})
