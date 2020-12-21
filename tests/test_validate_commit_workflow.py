from biosimulators_test_suite import validate_commit_workflow
from biosimulators_test_suite import validate_simulator
from biosimulators_utils.gh_action.core import GitHubActionCaughtError
from biosimulators_utils.simulator_registry.data_model import SimulatorSubmission, IssueLabel
from unittest import mock
import biosimulators_utils.image
import biosimulators_utils.simulator.io
import docker
import os
import re
import unittest


class ValidateCommitWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.env = {
            'GH_REPO': 'biosimulators/Biosimulators_tellurium',
            'GH_ISSUE_NUMBER': '11',
            'GH_ACTION_RUN_ID': '17',
            'GH_ISSUES_USER': 'biosimulatorsdaemon',
            'GH_ISSUES_ACCESS_TOKEN':  '**********',
            'DOCKER_HUB_USERNAME': 'biosimulatorsdaemon',
            'DOCKER_HUB_TOKEN': '**********',
            'BIOSIMULATORS_DOCKER_REGISTRY_USERNAME': 'biosimulatorsdaemon',
            'BIOSIMULATORS_DOCKER_REGISTRY_TOKEN': '**********',
            'BIOSIMULATORS_API_CLIENT_ID': '**********',
            'BIOSIMULATORS_API_CLIENT_SECRET': '**********',
        }

        self.submission = SimulatorSubmission(
            id='gillespy2',
            version='1.5.6',
            specifications_url='https://raw.githubusercontent.com/biosimulators/Biosimulators_GillesPy2/dev/biosimulators.json',
            validate_image=True,
            commit_simulator=True,
        )

        self.submitter = 'jonrkarr'

    def test_get_uncaught_exception_msg(self):
        msg = 'My custom message'
        exception = Exception(msg)
        self.assertRegex(validate_commit_workflow.get_uncaught_exception_msg(exception),
                         '\n\n  Type: Exception\n\n', re.MULTILINE)
        self.assertRegex(validate_commit_workflow.get_uncaught_exception_msg(exception),
                         '\n\n  Details:\n\n    ' + msg + '\n\n', re.MULTILINE)

        msg = 'My custom message'
        exception = ValueError(msg)
        self.assertRegex(validate_commit_workflow.get_uncaught_exception_msg(exception),
                         '\n\n  Type: ValueError\n\n', re.MULTILINE)
        self.assertRegex(validate_commit_workflow.get_uncaught_exception_msg(exception),
                         '\n\n  Details:\n\n    ' + msg + '\n\n', re.MULTILINE)

    def test_get_initial_message(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()
        msg = action.get_initial_message(self.submission, self.submitter)
        self.assertTrue(msg.startswith('Thank you @{} for your submission to the BioSimulators'.format(self.submitter)))
        self.assertTrue(msg.endswith('We will discuss any issues with your submission here.'))

        self.submission.validate_image = False
        self.submission.commit_simulator = False
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()
        msg = action.get_initial_message(self.submission, self.submitter)
        self.assertTrue(msg.startswith('Thank you @{} for your submission to the BioSimulators'.format(self.submitter)))
        self.assertTrue(msg.endswith('We will discuss any issues with your submission here.'))

    def test_validate_image(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        specs = {'id': 'tellurium', 'image': {'url': 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.1.6'}}
        run_results = (
            [None], [], None
        )

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertEqual(json['body'], 'Your simulator passed 1 test cases.')
            return mock.Mock(raise_for_status=lambda: None)

        with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
            with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                    with mock.patch.object(validate_simulator.SimulatorValidator, 'run', return_value=run_results):
                        with mock.patch('requests.post', side_effect=requests_post):
                            action.validate_image(specs)

        run_results = (
            [], [mock.Mock(test_case='x', exception='y')], None
        )

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertRegex(json['body'], 'Your simulator did not pass 1 test cases.')
            return mock.Mock(raise_for_status=lambda: None)
        with self.assertRaisesRegex(GitHubActionCaughtError, '^Your simulator did not pass 1 test cases.'):
            with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
                with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                    with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                        with mock.patch.object(validate_simulator.SimulatorValidator, 'run', return_value=run_results):
                            with mock.patch('requests.post', side_effect=requests_post):
                                action.validate_image(specs)

        run_results = (
            [], [], None
        )

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertRegex(json['body'], 'No test cases are applicable to your simulator.')
            return mock.Mock(raise_for_status=lambda: None)
        with self.assertRaisesRegex(GitHubActionCaughtError, '^No test cases are applicable to your simulator.'):
            with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
                with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                    with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                        with mock.patch.object(validate_simulator.SimulatorValidator, 'run', return_value=run_results):
                            with mock.patch('requests.post', side_effect=requests_post):
                                action.validate_image(specs)

    def test_validate_simulator(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        class RequestMock(object):
            def __init__(self, parent):
                self.parent = parent
                self.n_post = 0

            def post(self, url, json=None, auth=None, headers=None):
                self.n_post = self.n_post + 1
                if self.n_post == 1:
                    self.parent.assertRegex(json['body'], 'The specifications of your simulator is valid!')
                else:
                    self.parent.assertRegex(json['body'], 'The image for your simulator is valid!')
                return mock.Mock(raise_for_status=lambda: None)

        requests_mock = RequestMock(parent=self)

        specs = {'id': 'tellurium'}
        with mock.patch('biosimulators_utils.simulator.io.read_simulator_specs', return_value=specs):
            with mock.patch.object(validate_commit_workflow.ValidateCommitSimulatorGitHubAction, 'validate_image', return_value=None):
                with mock.patch('requests.post', side_effect=requests_mock.post):
                    specs2 = action.validate_simulator(self.submission)
        self.assertEqual(specs2, specs)
        self.assertEqual(requests_mock.n_post, 2)

    def test_is_simulator_approved(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        requests_get_1_true = mock.Mock(raise_for_status=lambda: None, json=lambda: [{'name': IssueLabel.approved.value}])
        with mock.patch('requests.get', return_value=requests_get_1_true):
            self.assertTrue(action.does_submission_have_approved_label())

        requests_get_1_false = mock.Mock(raise_for_status=lambda: None, json=lambda: [{'name': IssueLabel.validated.value}])
        with mock.patch('requests.get', return_value=requests_get_1_false):
            self.assertFalse(action.does_submission_have_approved_label())

        specs = {'id': 'tellurium'}

        existing_version_specs_false = [
            {'version': '2.1.5', 'biosimulators': {'validated': False}},
            {'version': '2.1.6', 'biosimulators': {'validated': False}},
        ]
        self.assertFalse(action.is_other_version_of_simulator_validated(specs, existing_version_specs_false))

        existing_version_specs_true = [
            {'version': '2.1.5', 'biosimulators': {'validated': True}},
            {'version': '2.1.6', 'biosimulators': {'validated': False}},
        ]
        self.assertTrue(action.is_other_version_of_simulator_validated(specs, existing_version_specs_true))

        with mock.patch('requests.get', side_effect=[requests_get_1_false]):
            self.assertFalse(action.is_simulator_approved(specs, existing_version_specs_false))
        with mock.patch('requests.get', side_effect=[requests_get_1_false]):
            self.assertTrue(action.is_simulator_approved(specs, existing_version_specs_true))
        with mock.patch('requests.get', side_effect=[requests_get_1_true]):
            self.assertTrue(action.is_simulator_approved(specs, existing_version_specs_false))
        with mock.patch('requests.get', side_effect=[requests_get_1_true]):
            self.assertTrue(action.is_simulator_approved(specs, existing_version_specs_true))

    def test_is_submission_latest_version_of_simulator(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        existing_version_specs = [
            {'version': '2.1.5', 'image': True, 'biosimulators': {'validated': True}},
            {'version': '2.1.6', 'image': True, 'biosimulators': {'validated': True}},
            {'version': '3.1.5', 'image': False, 'biosimulators': {'validated': True}},
            {'version': '3.1.5', 'image': True, 'biosimulators': {'validated': False}},
        ]
        self.assertTrue(action.is_submission_latest_version_of_simulator({'version': '2.1.7'}, existing_version_specs))
        self.assertTrue(action.is_submission_latest_version_of_simulator({'version': '2.1.17'}, existing_version_specs))
        self.assertFalse(action.is_submission_latest_version_of_simulator({'version': '2.1.3'}, existing_version_specs))
        self.assertFalse(action.is_submission_latest_version_of_simulator({'version': '2.0.3'}, existing_version_specs))
        self.assertFalse(action.is_submission_latest_version_of_simulator({'version': '2.1.03'}, existing_version_specs))

    def test_push_image(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        specs = {
            'id': 'Tellurium',
            'version': '2.1.6',
            'image': {
                'url': 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.1.6',
            }
        }

        class DockerMock(object):
            def __init__(self, parent):
                self.parent = parent
                self.n_tag = 0
                self.n_push = 0

            def pull(self, old_url):
                self.parent.assertEqual(old_url, specs['image']['url'])
                return mock.Mock(tag=self.tag)

            def tag(self, new_url):
                self.n_tag = self.n_tag + 1
                if self.n_tag < 3:
                    self.parent.assertEqual(new_url, 'ghcr.io/biosimulators/tellurium:2.1.6')
                else:
                    self.parent.assertEqual(new_url, 'ghcr.io/biosimulators/tellurium:latest')
                return True

            def push(self, new_url):
                self.n_push = self.n_push + 1
                if self.n_push < 3:
                    self.parent.assertEqual(new_url, 'ghcr.io/biosimulators/tellurium:2.1.6')
                else:
                    self.parent.assertEqual(new_url, 'ghcr.io/biosimulators/tellurium:latest')
                return '{}'
        docker_mock = DockerMock(parent=self)

        existing_version_specs = [
            {'version': '2.1.7', 'image': True, 'biosimulators': {'validated': True}},
        ]

        with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
            with mock.patch.object(docker.models.images.ImageCollection, 'pull', side_effect=docker_mock.pull):
                with mock.patch.object(docker.models.images.Image, 'tag', side_effect=docker_mock.tag):
                    with mock.patch.object(docker.models.images.ImageCollection, 'push', side_effect=docker_mock.push):
                        action.push_image(specs, existing_version_specs)
        self.assertEqual(docker_mock.n_tag, 1)
        self.assertEqual(docker_mock.n_push, 1)
        self.assertEqual(specs['image']['url'], 'ghcr.io/biosimulators/tellurium:2.1.6')

        specs['image']['url'] = 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.1.6'
        existing_version_specs[0]['version'] = '2.1.5'
        with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
            with mock.patch.object(docker.models.images.ImageCollection, 'pull', side_effect=docker_mock.pull):
                with mock.patch.object(docker.models.images.Image, 'tag', side_effect=docker_mock.tag):
                    with mock.patch.object(docker.models.images.ImageCollection, 'push', side_effect=docker_mock.push):
                        action.push_image(specs, existing_version_specs)
        self.assertEqual(docker_mock.n_tag, 3)
        self.assertEqual(docker_mock.n_push, 3)
        self.assertEqual(specs['image']['url'], 'ghcr.io/biosimulators/tellurium:2.1.6')

    def test_post_entry_to_biosimulators_api(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        class RequestMock(object):
            def __init__(self, parent, action):
                self.parent = parent
                self.action = action
                self.n_post = 0
                self.n_put = 0

            def post(self, url, json=None, headers=None):
                self.n_post = self.n_post + 1
                if self.n_post < 3:
                    self.parent.assertEqual(url, self.action.BIOSIMULATORS_AUTH_ENDPOINT)
                    self.parent.assertEqual(headers, None)
                    self.parent.assertIn('grant_type', json)
                    return mock.Mock(raise_for_status=lambda: None, json=lambda: {'token_type': 'Bearer', 'access_token': '******'})
                else:
                    self.parent.assertEqual(url, 'https://api.biosimulators.org/simulators')
                    self.parent.assertEqual(headers, {'Authorization': 'Bearer ******'})
                    self.parent.assertEqual(json, {'id': 'tellurium', 'version': '2.1.6'})
                    return mock.Mock(raise_for_status=lambda: None)

            def put(self, url, json=None, headers=None):
                self.n_put = self.n_put + 1
                self.parent.assertEqual(url, 'https://api.biosimulators.org/simulators/tellurium/2.1.6')
                self.parent.assertEqual(json, {'id': 'tellurium', 'version': '2.1.6'})
                return mock.Mock(raise_for_status=lambda: None)

        requests_mock = RequestMock(parent=self, action=action)

        specs = {'id': 'tellurium', 'version': '2.1.6'}
        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.6'}]
        with mock.patch('requests.post', side_effect=requests_mock.post):
            with mock.patch('requests.put', side_effect=requests_mock.put):
                action.post_entry_to_biosimulators_api(specs, existing_version_specs)
        self.assertEqual(requests_mock.n_post, 1)
        self.assertEqual(requests_mock.n_put, 1)

        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.5'}]
        with mock.patch('requests.post', side_effect=requests_mock.post):
            with mock.patch('requests.put', side_effect=requests_mock.put):
                action.post_entry_to_biosimulators_api(specs, existing_version_specs)
        self.assertEqual(requests_mock.n_post, 3)
        self.assertEqual(requests_mock.n_put, 1)

    def test_commit_simulator(self):
        with mock.patch.dict(os.environ, self.env):
            action = validate_commit_workflow.ValidateCommitSimulatorGitHubAction()

        class RequestMock(object):
            def __init__(self):
                self.n_post = 0
                self.n_put = 0

            def post(self, url, json=None, headers=None, auth=None):
                self.n_post = self.n_post + 1
                return mock.Mock(raise_for_status=lambda: None, json=lambda: {'token_type': 'Bearer', 'access_token': '****'})

            def put(self, url, json=None, headers=None, auth=None):
                self.n_put = self.n_put + 1
                return mock.Mock(raise_for_status=lambda: None)
        requests_mock = RequestMock()
        specs = {'id': 'tellurium', 'version': '2.1.6'}

        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.5'}]
        with mock.patch('requests.post', side_effect=requests_mock.post):
            action.commit_simulator(SimulatorSubmission(validate_image=False), specs, existing_version_specs)
        self.assertEqual(requests_mock.n_post, 3)

        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.5'}]
        with mock.patch('requests.post', side_effect=requests_mock.post):
            with mock.patch.object(validate_commit_workflow.ValidateCommitSimulatorGitHubAction, 'push_image', return_value=None):
                action.commit_simulator(SimulatorSubmission(validate_image=True), specs, existing_version_specs)
        self.assertEqual(requests_mock.n_post, 6)

        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.6'}]
        with mock.patch('requests.post', side_effect=requests_mock.post):
            with mock.patch('requests.put', side_effect=requests_mock.put):
                action.commit_simulator(SimulatorSubmission(validate_image=False), specs, existing_version_specs)
        self.assertEqual(requests_mock.n_post, 8)
        self.assertEqual(requests_mock.n_put, 1)
