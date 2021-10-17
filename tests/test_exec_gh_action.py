from biosimulators_test_suite import exec_gh_action
from biosimulators_test_suite import exec_core
from biosimulators_test_suite.config import Config
from biosimulators_test_suite.results.data_model import TestCaseResult, TestCaseResultType
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.warnings import TestCaseWarning
from biosimulators_utils.gh_action.data_model import GitHubActionCaughtError
from biosimulators_utils.simulator_registry.data_model import SimulatorSubmission, IssueLabel
from unittest import mock
import docker
import os
import requests
import unittest


class ValidateCommitWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.env = {
            'GH_REPO': 'biosimulators/Biosimulators',
            'GH_ISSUE_NUMBER': '11',
            'GH_ACTION_RUN_ID': '17',
            'GH_ISSUES_USER': 'biosimulators-daemon',
            'GH_ISSUES_ACCESS_TOKEN':  '**********',
            'DOCKER_HUB_USERNAME': 'biosimulators-daemon',
            'DOCKER_HUB_TOKEN': '**********',
            'DOCKER_REGISTRY_USERNAME': 'biosimulators-daemon',
            'DOCKER_REGISTRY_TOKEN': '**********',
            'BIOSIMULATORS_API_CLIENT_ID': '**********',
            'BIOSIMULATORS_API_CLIENT_SECRET': '**********',
        }

        self.submission = SimulatorSubmission(
            id='gillespy2',
            version='1.5.5',
            specifications_url='https://raw.githubusercontent.com/biosimulators/Biosimulators_GillesPy2/dev/biosimulators.json',
            specifications_patch={'version': '1.5.6'},
            validate_image=True,
            commit_simulator=True,
        )

        self.submitter = 'jonrkarr'

    def test_get_uncaught_exception_msg(self):
        msg = 'My custom message'
        exception = Exception(msg)
        comments = exec_gh_action.get_uncaught_exception_msg(exception)
        error_comments = [comment.text for comment in comments if comment.error]
        self.assertEqual(error_comments, [msg])

        msg = 'My custom message'
        exception = ValueError(msg)
        comments = exec_gh_action.get_uncaught_exception_msg(exception)
        error_comments = [comment.text for comment in comments if comment.error]
        self.assertEqual(error_comments, [msg])

    def test_get_initial_message(self):
        with mock.patch.dict(os.environ, self.env):
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()
        msg = action.get_initial_message(self.submission, self.submitter)
        self.assertTrue(msg.startswith('Thank you @{} for your submission to the BioSimulators'.format(self.submitter)))
        self.assertIn('We will discuss any concerns with your submission in this issue.', msg)

        self.submission.validate_image = False
        self.submission.commit_simulator = False
        with mock.patch.dict(os.environ, self.env):
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()
        msg = action.get_initial_message(self.submission, self.submitter)
        self.assertTrue(msg.startswith('Thank you @{} for your submission to the BioSimulators'.format(self.submitter)))
        self.assertIn('We will discuss any concerns with your submission in this issue.', msg)

    def test_validate_image(self):
        with mock.patch.dict(os.environ, self.env):
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

        specs = {
            'id': 'tellurium',
            'name': 'tellurium',
            'image': {
                'url': 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.1.6',
            },
            'algorithms': [
            ],
        }
        run_results = [
            TestCaseResult(case=SimulatorCanExecutePublishedProject(id='sedml.case-1'), type=TestCaseResultType.passed, log='', duration=1.)
        ]

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertIn('Passed 1 test cases:', json['body'])
            return mock.Mock(raise_for_status=lambda: None)

        with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
            with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                    with mock.patch.object(exec_core.SimulatorValidator, 'run', return_value=run_results):
                        with mock.patch('requests.post', side_effect=requests_post):
                            with mock.patch.dict(os.environ, self.env):
                                action.validate_image(specs)

        run_results = [
            TestCaseResult(case=SimulatorCanExecutePublishedProject(id='sedml.x'), type=TestCaseResultType.failed,
                           exception=Exception('y'), log='', duration=2.),
        ]

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertTrue('Failed 1 test cases:' in json['body']
                            or '## Failures' in json['body']
                            or 'After correcting your simulator' in json['body'])
            return mock.Mock(raise_for_status=lambda: None)
        with self.assertRaisesRegex(GitHubActionCaughtError, '^After correcting your simulator,'):
            with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
                with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                    with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                        with mock.patch.object(exec_core.SimulatorValidator, 'run', return_value=run_results):
                            with mock.patch('requests.post', side_effect=requests_post):
                                with mock.patch.dict(os.environ, self.env):
                                    action.validate_image(specs)

        run_results = [
            TestCaseResult(case=SimulatorCanExecutePublishedProject(id='sedml.x'), type=TestCaseResultType.skipped,
                           skip_reason=Exception('y'), log='', duration=2.),
        ]

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertTrue('Skipped 1 test cases:' in json['body']
                            or '## Skips' in json['body']
                            or 'No test cases are applicable to your simulator' in json['body'])
            return mock.Mock(raise_for_status=lambda: None)
        with self.assertRaisesRegex(GitHubActionCaughtError, 'No test cases are applicable to your simulator.'):
            with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
                with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                    with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                        with mock.patch.object(exec_core.SimulatorValidator, 'run', return_value=run_results):
                            with mock.patch('requests.post', side_effect=requests_post):
                                with mock.patch.dict(os.environ, self.env):
                                    action.validate_image(specs)

        run_results = []

        def requests_post(url, json=None, auth=None, headers=None):
            self.assertTrue('Executed 0 test cases' in json['body'] or 'No test cases are applicable to your simulator' in json['body'])
            return mock.Mock(raise_for_status=lambda: None)
        with self.assertRaisesRegex(GitHubActionCaughtError, 'No test cases are applicable to your simulator.'):
            with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
                with mock.patch.object(docker.models.images.ImageCollection, 'pull', return_value=None):
                    with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity', return_value=None):
                        with mock.patch.object(exec_core.SimulatorValidator, 'run', return_value=run_results):
                            with mock.patch('requests.post', side_effect=requests_post):
                                with mock.patch.dict(os.environ, self.env):
                                    action.validate_image(specs)

    def test_exec_core(self):
        with mock.patch.dict(os.environ, self.env):
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

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

        specs = {'id': 'tellurium', 'name': 'tellurium'}
        with mock.patch('biosimulators_utils.simulator.io.read_simulator_specs', return_value=specs):
            with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'validate_image', return_value=None):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'validate_permissions', return_value=None):
                    with mock.patch('requests.post', side_effect=requests_mock.post):
                        specs2, results = action.exec_core(self.submission, 'submitter')
        self.assertEqual(specs2, specs)
        self.assertEqual(results, None)
        self.assertEqual(requests_mock.n_post, 2)

    def test_is_simulator_approved(self):
        with mock.patch.dict(os.environ, self.env):
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

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
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

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
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

        specs = {
            'id': 'tellurium',
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

            def get(self, url):
                return mock.Mock(tag=self.tag, attrs={'RepoDigests': [url + '@sha256:' + ('x' * 64)]})
        docker_mock = DockerMock(parent=self)

        existing_version_specs = [
            {'version': '2.1.7', 'image': True, 'biosimulators': {'validated': True}},
        ]

        with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
            with mock.patch.object(docker.models.images.ImageCollection, 'pull', side_effect=docker_mock.pull):
                with mock.patch.object(docker.models.images.Image, 'tag', side_effect=docker_mock.tag):
                    with mock.patch.object(docker.models.images.ImageCollection, 'push', side_effect=docker_mock.push):
                        with mock.patch.object(docker.models.images.ImageCollection, 'get', side_effect=docker_mock.get):
                            action.push_image(specs, existing_version_specs)
        self.assertEqual(docker_mock.n_tag, 1)
        self.assertEqual(docker_mock.n_push, 1)
        self.assertEqual(specs['image']['url'], 'ghcr.io/biosimulators/tellurium:2.1.6')
        self.assertEqual(specs['image']['digest'], 'sha256:' + ('x' * 64))

        specs['image']['url'] = 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.1.6'
        existing_version_specs[0]['version'] = '2.1.5'
        with mock.patch.object(docker.client.DockerClient, 'login', return_value=None):
            with mock.patch.object(docker.models.images.ImageCollection, 'pull', side_effect=docker_mock.pull):
                with mock.patch.object(docker.models.images.Image, 'tag', side_effect=docker_mock.tag):
                    with mock.patch.object(docker.models.images.ImageCollection, 'push', side_effect=docker_mock.push):
                        with mock.patch.object(docker.models.images.ImageCollection, 'get', side_effect=docker_mock.get):
                            action.push_image(specs, existing_version_specs)
        self.assertEqual(docker_mock.n_tag, 3)
        self.assertEqual(docker_mock.n_push, 3)
        self.assertEqual(specs['image']['url'], 'ghcr.io/biosimulators/tellurium:2.1.6')
        self.assertEqual(specs['image']['digest'], 'sha256:' + ('x' * 64))

    def test_post_entry_to_biosimulators_api(self):
        with mock.patch.dict(os.environ, self.env):
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

        class RequestMock(object):
            def __init__(self, parent, action):
                self.parent = parent
                self.action = action
                self.n_post = 0
                self.n_put = 0

            def post(self, url, json=None, headers=None):
                self.n_post = self.n_post + 1
                if self.n_post < 3:
                    self.parent.assertEqual(url, Config().biosimulators_auth_endpoint)
                    self.parent.assertEqual(headers, None)
                    self.parent.assertIn('grant_type', json)
                    return mock.Mock(raise_for_status=lambda: None, json=lambda: {'token_type': 'Bearer', 'access_token': '******'})
                else:
                    self.parent.assertEqual(url, Config().biosimulators_api_endpoint + 'simulators')
                    self.parent.assertEqual(headers, {'Authorization': 'Bearer ******'})
                    self.parent.assertEqual(json, {'id': 'tellurium', 'version': '2.1.6'})
                    return mock.Mock(raise_for_status=lambda: None)

            def put(self, url, json=None, headers=None):
                self.n_put = self.n_put + 1
                self.parent.assertEqual(url, Config().biosimulators_api_endpoint + 'simulators/tellurium/2.1.6')
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
            action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

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
            action.commit_simulator(SimulatorSubmission(validate_image=False), specs, existing_version_specs, [])
        self.assertEqual(requests_mock.n_post, 2)

        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.5'}]
        with mock.patch.dict(os.environ, self.env):
            with mock.patch('requests.post', side_effect=requests_mock.post):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'push_image', return_value=None):
                    action.commit_simulator(SimulatorSubmission(validate_image=True), specs, existing_version_specs, [])
        self.assertEqual(requests_mock.n_post, 6)

        existing_version_specs = [{'id': 'tellurium', 'version': '2.1.6'}]
        with mock.patch.dict(os.environ, self.env):
            with mock.patch('requests.post', side_effect=requests_mock.post):
                with mock.patch('requests.put', side_effect=requests_mock.put):
                    action.commit_simulator(SimulatorSubmission(validate_image=False), specs, existing_version_specs, [])
        self.assertEqual(requests_mock.n_post, 7)
        self.assertEqual(requests_mock.n_put, 1)

    def test_run(self):
        # validate specs of valid new simulator, fail on invalid specs
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=False, commit_simulator=False,
            previous_run_valid=None, manually_approved=False,
            specs_valid=False, singularity_error=False, validation_state='passes')
        with self.assertRaisesRegex(requests.RequestException, "specifications of simulation tools must adhere to BioSimulators' schema"):
            self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(requests_mock.simulator_versions, [])
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Invalid']))
        self.assertEqual(len(requests_mock.issue_messages), 2)
        self.assertRegex(requests_mock.issue_messages[-1], "specifications of simulation tools must adhere to BioSimulators' schema")
        self.assertEqual(docker_mock.remote_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(docker_mock.local_images, set([]))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs of valid new simulator
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=False, commit_simulator=False,
            previous_run_valid=None, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(requests_mock.simulator_versions, [])
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated']))
        self.assertEqual(len(requests_mock.issue_messages), 2)
        self.assertEqual(requests_mock.issue_messages[-1], 'The specifications of your simulator is valid!')
        self.assertEqual(docker_mock.remote_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(docker_mock.local_images, set([]))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator; fail on singularity error
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=True, commit_simulator=False,
            previous_run_valid=None, manually_approved=False,
            specs_valid=True, singularity_error=True, validation_state='passes')
        with self.assertRaisesRegex(Exception, 'Singularity error'):
            self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(requests_mock.simulator_versions, [])
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Invalid']))
        self.assertEqual(len(requests_mock.issue_messages), 3)
        self.assertRegex(requests_mock.issue_messages[-1], 'Singularity error')
        self.assertEqual(docker_mock.remote_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(docker_mock.local_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator; fail on validation error
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=True, commit_simulator=False,
            previous_run_valid=None, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='fails')
        with self.assertRaisesRegex(GitHubActionCaughtError, 'After correcting your simulator'):
            self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(requests_mock.simulator_versions, [])
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Invalid']))
        self.assertEqual(len(requests_mock.issue_messages), 5)
        self.assertRegex(requests_mock.issue_messages[-3], 'Passed 0 test cases')
        self.assertEqual(docker_mock.remote_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(docker_mock.local_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=True, commit_simulator=False,
            previous_run_valid=None, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='skips')
        with self.assertRaisesRegex(GitHubActionCaughtError, 'No test cases are applicable'):
            self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(requests_mock.simulator_versions, [])
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Invalid']))
        self.assertEqual(len(requests_mock.issue_messages), 4)
        self.assertRegex(requests_mock.issue_messages[-1], 'No test cases are applicable')
        self.assertEqual(docker_mock.remote_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(docker_mock.local_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=True, commit_simulator=False,
            previous_run_valid=None, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(requests_mock.simulator_versions, [])
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated']))
        self.assertEqual(len(requests_mock.issue_messages), 5)
        self.assertRegex(requests_mock.issue_messages[-3], 'Passed 1 test cases:')
        self.assertEqual(requests_mock.issue_messages[-1], 'The image for your simulator is valid!')
        self.assertEqual(docker_mock.remote_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(docker_mock.local_images, set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6']))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator, previous run passed and was approved
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=True, commit_simulator=True,
            previous_run_valid=True, manually_approved=True,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'closed')
        self.assertEqual(set(v['version'] for v in requests_mock.simulator_versions), set(['2.1.6']))
        self.assertEqual(requests_mock.refreshed_images, [{'simulator': 'tellurium', 'version': '2.1.6'}])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated', 'Approved']))
        self.assertEqual(len(requests_mock.issue_messages), 6)
        self.assertRegex(requests_mock.issue_messages[-1], 'Your submission was committed to the BioSimulators registry.')
        self.assertEqual(docker_mock.remote_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:latest',
        ]))
        self.assertEqual(docker_mock.local_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:latest',
        ]))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator, previous run failed and was not approved
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=True, previous_version_validated=False,
            validate_image=True, commit_simulator=True,
            previous_run_valid=False, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(set(v['version'] for v in requests_mock.simulator_versions), set([]))
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated']))
        self.assertEqual(len(requests_mock.issue_messages), 6)
        self.assertRegex(requests_mock.issue_messages[-1], 'A member of the BioSimulators team will review your submission')
        self.assertEqual(docker_mock.remote_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
        ]))
        self.assertEqual(docker_mock.local_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
        ]))
        self.assertEqual(requests_mock.issue_assignees, set(Config().biosimulators_curator_gh_ids))

        # validate specs and image of valid new simulator, previous run failed and was not approved
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=False, previous_version_validated=False,
            validate_image=True, commit_simulator=True,
            previous_run_valid=False, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'open')
        self.assertEqual(set(v['version'] for v in requests_mock.simulator_versions), set(['2.1.5']))
        self.assertEqual(requests_mock.refreshed_images, [])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated']))
        self.assertEqual(len(requests_mock.issue_messages), 6)
        self.assertRegex(requests_mock.issue_messages[-1], 'A member of the BioSimulators team will review your submission')
        self.assertEqual(docker_mock.remote_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
        ]))
        self.assertEqual(docker_mock.local_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
        ]))
        self.assertEqual(requests_mock.issue_assignees, set(Config().biosimulators_curator_gh_ids))

        # validate specs and image of valid new simulator, previous run passed and was approved
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            new_simulator=False, previous_version_validated=True,
            validate_image=True, commit_simulator=True,
            previous_run_valid=False, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'closed')
        self.assertEqual(set(v['version'] for v in requests_mock.simulator_versions), set(['2.1.5', '2.1.6']))
        self.assertEqual(requests_mock.refreshed_images, [{'simulator': 'tellurium', 'version': '2.1.6'}])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated', 'Approved']))
        self.assertEqual(len(requests_mock.issue_messages), 6)
        self.assertRegex(requests_mock.issue_messages[-1], 'Your submission was committed to the BioSimulators registry.')
        self.assertEqual(docker_mock.remote_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:latest',
        ]))
        self.assertEqual(docker_mock.local_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:2.1.6',
            'ghcr.io/biosimulators/tellurium:latest',
        ]))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator, previous run passed and was approved; not latest version
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            submitted_version='2.1.4',
            new_simulator=False, previous_version_validated=True,
            validate_image=True, commit_simulator=True,
            previous_run_valid=False, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'closed')
        self.assertEqual(set(v['version'] for v in requests_mock.simulator_versions), set(['2.1.5', '2.1.4']))
        self.assertEqual(requests_mock.refreshed_images, [{'simulator': 'tellurium', 'version': '2.1.4'}])
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated', 'Approved']))
        self.assertEqual(len(requests_mock.issue_messages), 6)
        self.assertRegex(requests_mock.issue_messages[-1], 'Your submission was committed to the BioSimulators registry.')
        self.assertEqual(docker_mock.remote_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.4',
            'ghcr.io/biosimulators/tellurium:2.1.4',
        ]))
        self.assertEqual(docker_mock.local_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.4',
            'ghcr.io/biosimulators/tellurium:2.1.4',
        ]))
        self.assertEqual(requests_mock.issue_assignees, set())

        # validate specs and image of valid new simulator, previous run passed and was approved; not latest version
        requests_mock, docker_mock, validation_run_results = self._build_run_mock_objs(
            submitted_version='2.1.5',
            new_simulator=False, previous_version_validated=True,
            validate_image=True, commit_simulator=True,
            previous_run_valid=False, manually_approved=False,
            specs_valid=True, singularity_error=False, validation_state='passes')
        self._exec_run_mock_objs(requests_mock, docker_mock, validation_run_results)
        self.assertEqual(requests_mock.issue_state, 'closed')
        self.assertEqual(set(v['version'] for v in requests_mock.simulator_versions), set(['2.1.5']))
        self.assertEqual(requests_mock.refreshed_images, [{'simulator': 'tellurium', 'version': '2.1.5'}])
        self.assertEqual(len(requests_mock.simulator_versions[-1]['biosimulators']['validationTests']['results']), 1)
        self.assertEqual(requests_mock.simulator_versions[-1]['biosimulators']
                         ['validationTests']['results'][0]['case']['id'], 'sedml.case-passed')
        self.assertEqual(requests_mock.issue_labels, set(['Validate/commit simulator', 'Validated', 'Approved']))
        self.assertEqual(len(requests_mock.issue_messages), 6)
        self.assertRegex(requests_mock.issue_messages[-1], 'Your submission was committed to the BioSimulators registry.')
        self.assertEqual(docker_mock.remote_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.5',
            'ghcr.io/biosimulators/tellurium:2.1.5',
            'ghcr.io/biosimulators/tellurium:latest',
        ]))
        self.assertEqual(docker_mock.local_images, set([
            'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.5',
            'ghcr.io/biosimulators/tellurium:2.1.5',
            'ghcr.io/biosimulators/tellurium:latest',
        ]))
        self.assertEqual(requests_mock.issue_assignees, set())

    def _build_run_mock_objs(self, submitted_version='2.1.6', new_simulator=True, previous_version_validated=False,
                             validate_image=False, commit_simulator=False, previous_run_valid=None, manually_approved=False,
                             specs_valid=True, singularity_error=False, validation_state='passes'):
        class RequestsMock(object):
            def __init__(self, submitted_version='2.1.6', new_simulator=True, previous_version_validated=False,
                         validate_image=False, commit_simulator=False,
                         previous_run_valid=None, manually_approved=False, issue_state='open', specs_valid=True):
                self.submitted_version = submitted_version
                self.specs_valid = specs_valid
                self.validate_image = validate_image
                self.commit_simulator = commit_simulator
                self.issue_state = issue_state

                if new_simulator:
                    self.simulator_versions = []
                else:
                    self.simulator_versions = [
                        {
                            'version': '2.1.5',
                            'image': {'url': 'ghcr.io/biosimulators/tellurium/2.1.5'},
                            'algorithms': [],
                            'biosimulators': {'validated': previous_version_validated},
                        },
                    ]

                self.refreshed_images = []

                self.issue_labels = set(['Validate/commit simulator'])
                if previous_run_valid is True:
                    self.issue_labels.add('Validated')
                elif previous_run_valid is False:
                    self.issue_labels.add('Invalid')
                if manually_approved:
                    self.issue_labels.add('Approved')

                self.issue_messages = []

                self.issue_assignees = set()

            def get(self, url, json=None, auth=None, headers=None):
                if url == 'https://raw.githubusercontent.com/biosimulators/Biosimulators_tellurium/d08f33/biosimulators.json':
                    response = {
                        'id': 'tellurium',
                        'name': 'tellurium',
                        'version': self.submitted_version,
                        'image': {
                            'url': 'ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:' + self.submitted_version
                        },
                        'algorithms': [],
                        'biosimulators': {
                            'validated': False,
                        },
                    }
                elif url == 'https://api.github.com/repos/biosimulators/Biosimulators/issues/11':
                    response = {
                        'user': {
                            'login': 'biosimulators-daemon',
                        },
                        'body': '\n'.join([
                            '---',
                            'id: vcell',
                            'version: ' + self.submitted_version,
                            ('specificationsUrl: https://raw.githubusercontent.com/biosimulators/'
                                'Biosimulators_tellurium/d08f33/biosimulators.json'),
                            'specificationsPatch:',
                            '  version: ' + self.submitted_version,
                            '  image:',
                            '    url: ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:' + self.submitted_version,
                            'validateImage: {}'.format('true' if self.validate_image else 'false'),
                            'commitSimulator: {}'.format('true' if self.commit_simulator else 'false'),
                            '',
                            '---',
                        ]),
                        'assignees': [
                        ],
                    }
                elif url == 'https://api.github.com/repos/biosimulators/Biosimulators/issues/11/labels':
                    response = [{'name': label} for label in self.issue_labels]
                elif url == Config().biosimulators_api_endpoint + 'simulators/tellurium':
                    response = self.simulator_versions
                else:
                    raise ValueError('Invalid url: {}'.format(url))
                return mock.Mock(raise_for_status=lambda: None, json=lambda: response)

            def post(self, url, json=None, auth=None, headers=None):
                if url == Config().biosimulators_auth_endpoint:
                    error = None
                    response = {'token_type': 'Bearer', 'access_token': '******'}
                elif url == Config().biosimulators_api_endpoint + 'simulators':
                    self.simulator_versions.append(json)
                    error = None
                    response = None
                elif url == Config().biosimulators_api_endpoint + 'simulators/validate':
                    if self.specs_valid:
                        error = None
                        response = None
                    else:
                        error = 'Specs are invalid'
                        response = {'error': [{'title': 'ValidationError', 'status': 400, 'detail': 'Specs are invalid'}]}
                elif url == Config().runbiosimulations_api_endpoint + 'images/refresh':
                    self.refreshed_images.append(json)
                    error = None
                    response = None
                elif url == 'https://api.github.com/repos/biosimulators/Biosimulators/issues/11/labels':
                    for label in json['labels']:
                        self.issue_labels.add(label)
                    error = None
                    response = None
                elif url == 'https://api.github.com/repos/biosimulators/Biosimulators/issues/11/comments':
                    self.issue_messages.append(json['body'])
                    error = None
                    response = None
                elif url == 'https://api.github.com/repos/biosimulators/Biosimulators/issues/11/assignees':
                    for assignee in json['assignees']:
                        self.issue_assignees.add(assignee)
                    error = None
                    response = None
                else:
                    raise ValueError('Invalid url: {}'.format(url))

                if error is None:
                    def raise_for_status(): return None
                else:
                    def raise_for_status(error=error):
                        raise requests.RequestException(error)
                return mock.Mock(raise_for_status=raise_for_status, json=lambda: response)

            def patch(self, url, json=None, auth=None, headers=None):
                if url == 'https://api.github.com/repos/biosimulators/Biosimulators/issues/11':
                    self.issue_state = json['state']
                    response = None
                else:
                    raise ValueError('Invalid url: {}'.format(url))

                return mock.Mock(raise_for_status=lambda: None, json=lambda: response)

            def put(self, url, json=None, auth=None, headers=None):
                if url.startswith(Config().biosimulators_api_endpoint + 'simulators/tellurium/'):
                    for i_version, version in enumerate(self.simulator_versions):
                        if version['version'] == json['version']:
                            self.simulator_versions[i_version] = json
                            break

                    response = None
                else:
                    raise ValueError('Invalid url: {}'.format(url))

                return mock.Mock(raise_for_status=lambda: None, json=lambda: response)

            def delete(self, url, json=None, auth=None, headers=None):
                if url.startswith('https://api.github.com/repos/biosimulators/Biosimulators/issues/11/labels/'):
                    _, _, label = url.rpartition('/')
                    self.issue_labels.remove(label)

                else:
                    raise ValueError('Invalid url: {}'.format(url))

                return mock.Mock(raise_for_status=lambda: None)

        class DockerMock(object):
            def __init__(self, local_images=None, remote_images=None, singularity_error=False, submitted_version='2.1.6'):
                self.auths = {}
                self.local_images = local_images or set()
                self.remote_images = remote_images or set(['ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:' + submitted_version])
                self.singularity_error = singularity_error

            def login(self, registry=None, username=None, password=None):
                self.auths[registry] = (username, password)

            def pull(self, old_url):
                assert old_url in self.remote_images
                self.local_images.add(old_url)
                return mock.Mock(tag=self.tag)

            def tag(self, new_url):
                self.local_images.add(new_url)
                return True

            def push(self, new_url):
                self.remote_images.add(new_url)
                return '{}'

            def get(self, url):
                return mock.Mock(tag=self.tag, attrs={'RepoDigests': [url + '@sha256:' + ('x' * 64)]})

            def convert_docker_image_to_singularity(self, image, singularity_filename=None):
                if self.singularity_error:
                    raise Exception('Singularity error')

        if validation_state == 'passes':
            validation_run_results = [
                TestCaseResult(
                    case=SimulatorCanExecutePublishedProject(id='sedml.case-passed'),
                    type=TestCaseResultType.passed,
                    duration=1.,
                    warnings=[
                        mock.Mock(category=TestCaseWarning, message=TestCaseWarning('Warning-1')),
                        mock.Mock(category=TestCaseWarning, message=TestCaseWarning('Warning-2')),
                    ],
                ),
            ]
        elif validation_state == 'fails':
            validation_run_results = [
                TestCaseResult(
                    case=SimulatorCanExecutePublishedProject(id='sedml.case-failed'),
                    type=TestCaseResultType.failed,
                    exception=Exception('Big error'),
                    log='Long log',
                    duration=2.,
                ),
            ]
        else:
            validation_run_results = []

        requests_mock = RequestsMock(submitted_version=submitted_version,
                                     new_simulator=new_simulator, previous_version_validated=previous_version_validated,
                                     validate_image=validate_image, commit_simulator=commit_simulator,
                                     previous_run_valid=previous_run_valid, manually_approved=manually_approved,
                                     specs_valid=specs_valid)
        docker_mock = DockerMock(singularity_error=singularity_error, submitted_version=submitted_version)

        return (requests_mock, docker_mock, validation_run_results)

    def _exec_run_mock_objs(self, requests_mock, docker_mock, validation_run_results):
        with mock.patch.dict(os.environ, self.env):
            with mock.patch('requests.get', side_effect=requests_mock.get):
                with mock.patch('requests.post', side_effect=requests_mock.post):
                    with mock.patch('requests.put', side_effect=requests_mock.put):
                        with mock.patch('requests.patch', side_effect=requests_mock.patch):
                            with mock.patch('requests.delete', side_effect=requests_mock.delete):
                                with mock.patch.object(docker.client.DockerClient, 'login', side_effect=docker_mock.login):
                                    with mock.patch.object(docker.models.images.ImageCollection, 'pull', side_effect=docker_mock.pull):
                                        with mock.patch.object(docker.models.images.ImageCollection, 'get', side_effect=docker_mock.get):
                                            with mock.patch('biosimulators_utils.image.convert_docker_image_to_singularity',
                                                            side_effect=docker_mock.convert_docker_image_to_singularity):
                                                with mock.patch.object(docker.models.images.Image, 'tag', side_effect=docker_mock.tag):
                                                    with mock.patch.object(docker.models.images.ImageCollection, 'push',
                                                                           side_effect=docker_mock.push):
                                                        cases = {
                                                            'suite': [result.case for result in validation_run_results]
                                                        }
                                                        with mock.patch.object(exec_core.SimulatorValidator, 'find_cases', return_value=cases):
                                                            with mock.patch.object(exec_core.SimulatorValidator, 'eval_case',
                                                                                   side_effect=validation_run_results):
                                                                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'validate_permissions', return_value=None):
                                                                    action = exec_gh_action.ValidateCommitSimulatorGitHubAction()
                                                                    action.run()

    def test_add_comment_to_issue(self):
        def requests_post(url, headers=None, auth=None, json=None):
            assert json['body'] == 'message'
            return mock.Mock(raise_for_status=lambda: None)
        with mock.patch('requests.post', side_effect=requests_post):
            exec_gh_action.ValidateCommitSimulatorGitHubAction.add_comment_to_issue(
                None, 'message', alternative_comment=None, max_len=65536)

        def requests_post(url, headers=None, auth=None, json=None):
            assert json['body'] == 'm ...'
            return mock.Mock(raise_for_status=lambda: None)
        with mock.patch('requests.post', side_effect=requests_post):
            exec_gh_action.ValidateCommitSimulatorGitHubAction.add_comment_to_issue(
                None, 'message', alternative_comment=None, max_len=5)

        def requests_post(url, headers=None, auth=None, json=None):
            assert json['body'] == 'm ...'

            def raise_for_status():
                raise ValueError('uncaught')
            return mock.Mock(raise_for_status=raise_for_status)
        with self.assertRaisesRegex(ValueError, 'uncaught'):
            with mock.patch('requests.post', side_effect=requests_post):
                exec_gh_action.ValidateCommitSimulatorGitHubAction.add_comment_to_issue(
                    None, 'message', alternative_comment=None, max_len=5)

        def requests_post(url, headers=None, auth=None, json=None):
            assert json['body'] == 'm ...'

            def raise_for_status():
                raise requests.exceptions.RequestException('uncaught')
            return mock.Mock(raise_for_status=raise_for_status, attr='A')
        with self.assertRaisesRegex(requests.exceptions.RequestException, 'uncaught'):
            with mock.patch('requests.post', side_effect=requests_post):
                exec_gh_action.ValidateCommitSimulatorGitHubAction.add_comment_to_issue(
                    None, 'message', alternative_comment=None, max_len=5)

        class RequestsPost(object):
            def __init__(self):
                self.count = 0

            def requests_post(self, url, headers=None, auth=None, json=None):
                self.count += 1

                if self.count == 1:
                    assert json['body'] == 'm ...'

                    def raise_for_status():
                        raise requests.exceptions.RequestException('caught')
                    return mock.Mock(raise_for_status=raise_for_status)

                else:
                    assert json['body'] == 'alt'
                    return mock.Mock(raise_for_status=lambda: None)

        with mock.patch('requests.post', side_effect=RequestsPost().requests_post):
            exec_gh_action.ValidateCommitSimulatorGitHubAction.add_comment_to_issue(
                None, 'message', alternative_comment='alt', max_len=5)

    def test_validate_permissions(self):
        action = exec_gh_action.ValidateCommitSimulatorGitHubAction()

        class RequestsMock(object):
            def __init__(self, check_team_error=False, check_member_error=False):
                self.check_team_error = check_team_error
                self.check_member_error = check_member_error
                self.new_team = False
                self.comment = None
                self.error = None

            def get(self, url, auth=None):
                if url == 'https://api.github.com/orgs/biosimulators/teams/simulator-developers':
                    return mock.Mock(raise_for_status=lambda: None, json=lambda: {'id': 10})
                elif url == 'https://api.github.com/orgs/biosimulators/teams/tellurium':
                    return mock.Mock(raise_for_status=lambda: None, json=lambda: {'id': 20})
                elif url == 'https://api.github.com/orgs/biosimulators/teams/tellurium2':
                    def raise_for_status():
                        raise requests.exceptions.HTTPError('404')
                    return mock.Mock(status_code=500 if self.check_team_error else 404, raise_for_status=raise_for_status)

                elif url == 'https://api.github.com/orgs/biosimulators/teams/tellurium/memberships/te-owner':
                    return mock.Mock(raise_for_status=lambda: None, json=lambda: {})
                elif url == 'https://api.github.com/orgs/biosimulators/teams/tellurium/memberships/te-owner2':
                    def raise_for_status():
                        raise requests.exceptions.HTTPError('404')
                    return mock.Mock(status_code=500 if self.check_member_error else 404, raise_for_status=raise_for_status)

            def post(self, url, auth=None, json=None):
                self.new_team = True
                return mock.Mock(raise_for_status=lambda: None)

            def add_comment(self, isse_number, comment):
                self.comment = comment

            def add_error(self, isse_number, comment):
                self.error = comment

        requests_mock = RequestsMock(check_team_error=False, check_member_error=False)
        with mock.patch('requests.get', requests_mock.get):
            with mock.patch('requests.post', requests_mock.post):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_comment_to_issue', requests_mock.add_comment):
                    with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_error_comment_to_issue', requests_mock.add_error):
                        action.validate_permissions('tellurium', 'tellurium', 'te-owner')
                        self.assertEqual(requests_mock.new_team, False)
                        self.assertEqual(requests_mock.comment, None)
                        self.assertEqual(requests_mock.error, None)

        requests_mock = RequestsMock(check_team_error=False, check_member_error=False)
        with mock.patch('requests.get', requests_mock.get):
            with mock.patch('requests.post', requests_mock.post):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_comment_to_issue', requests_mock.add_comment):
                    with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_error_comment_to_issue', requests_mock.add_error):
                        action.validate_permissions('tellurium2', 'tellurium', 'te-owner')
                        self.assertEqual(requests_mock.new_team, True)
                        self.assertNotEqual(requests_mock.comment, None)
                        self.assertEqual(requests_mock.error, None)

        requests_mock = RequestsMock(check_team_error=True, check_member_error=False)
        with mock.patch('requests.get', requests_mock.get):
            with mock.patch('requests.post', requests_mock.post):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_comment_to_issue', requests_mock.add_comment):
                    with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_error_comment_to_issue', requests_mock.add_error):
                        with self.assertRaisesRegex(requests.exceptions.HTTPError, '404'):
                            action.validate_permissions('tellurium2', 'tellurium', 'te-owner')
                            self.assertEqual(requests_mock.new_team, False)
                            self.assertEqual(requests_mock.comment, None)
                            self.assertEqual(requests_mock.error, None)

        requests_mock = RequestsMock(check_team_error=False, check_member_error=False)
        with mock.patch('requests.get', requests_mock.get):
            with mock.patch('requests.post', requests_mock.post):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_comment_to_issue', requests_mock.add_comment):
                    with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_error_comment_to_issue', requests_mock.add_error):
                        action.validate_permissions('tellurium', 'tellurium', 'te-owner2')
                        self.assertEqual(requests_mock.new_team, False)
                        self.assertEqual(requests_mock.comment, None)
                        self.assertNotEqual(requests_mock.error, None)

        requests_mock = RequestsMock(check_team_error=False, check_member_error=True)
        with mock.patch('requests.get', requests_mock.get):
            with mock.patch('requests.post', requests_mock.post):
                with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_comment_to_issue', requests_mock.add_comment):
                    with mock.patch.object(exec_gh_action.ValidateCommitSimulatorGitHubAction, 'add_error_comment_to_issue', requests_mock.add_error):
                        with self.assertRaisesRegex(requests.exceptions.HTTPError, '404'):
                            action.validate_permissions('tellurium', 'tellurium', 'te-owner2')
                            self.assertEqual(requests_mock.new_team, False)
                            self.assertEqual(requests_mock.comment, None)
                            self.assertEqual(requests_mock.error, None)
