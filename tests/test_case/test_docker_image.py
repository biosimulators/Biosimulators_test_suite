from biosimulators_test_suite.test_case import docker_image
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.exceptions import TestCaseException
from biosimulators_test_suite.warnings import TestCaseWarning
import os
import shutil
import tempfile
import unittest


class DockerImageTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
    CURATED_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'sbml-core', 'Tomida-EMBO-J-2003-NFAT-translocation.omex')

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_DefaultUserIsRoot(self):
        case = docker_image.DefaultUserIsRoot()
        with self.assertWarnsRegex(TestCaseWarning, 'should not declare default users'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname, expected_user=('undefined',))

    def test_DeclaresSupportedEnvironmentVariables(self):
        case = docker_image.DeclaresSupportedEnvironmentVariables()
        with self.assertWarnsRegex(TestCaseWarning, 'should declare the environment variables'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

    def test_HasOciLabels(self):
        case = docker_image.HasOciLabels()
        case.eval({'image': {'url': self.IMAGE}}, self.dirname)
        with self.assertWarnsRegex(TestCaseWarning, 'are encouraged to have the following'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

    def test_HasBioContainersLabels(self):
        case = docker_image.HasBioContainersLabels()
        case.eval({'image': {'url': self.IMAGE}}, self.dirname)
        with self.assertWarnsRegex(TestCaseWarning, 'are encouraged to have the following'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)

    def test_SingularityImageExecutesSimulationsSuccessfully(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = docker_image.SingularityImageExecutesSimulationsSuccessfully(
            published_projects_test_cases=[curated_case])

        case.eval({'image': {'url': self.IMAGE}}, self.dirname)

        with self.assertRaisesRegex(TestCaseException, 'could not be successfully executed as a Singularity'):
            case.eval({'image': {'url': 'hello-world'}}, self.dirname)
