""" Methods for processing submissions to the BioSimulators registry
(CI workflows for reviewing and committing simulators to the registry)

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-06
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
from .data_model import OutputMedium
from .exec_core import SimulatorValidator
from .results.data_model import TestCaseResult, TestCaseResultType, TestResultsReport  # noqa: F401
from .results.io import write_test_results
from biosimulators_utils.biosimulations.utils import validate_biosimulations_api_response
from biosimulators_utils.config import Colors
from biosimulators_utils.gh_action.data_model import Comment, GitHubActionCaughtError  # noqa: F401
from biosimulators_utils.gh_action.core import GitHubAction, GitHubActionErrorHandling
from biosimulators_utils.image import get_docker_image
from biosimulators_utils.simulator_registry.data_model import SimulatorSubmission, IssueLabel  # noqa: F401
from biosimulators_utils.simulator_registry.process_submission import get_simulator_submission_from_gh_issue_body
from biosimulators_utils.simulator_registry.query import get_simulator_version_specs
from natsort import natsort_keygen
import biosimulators_utils.image
import biosimulators_utils.simulator.io
import requests
import requests.exceptions
import termcolor


__all__ = [
    'ValidateCommitSimulatorGitHubAction',
]


def get_uncaught_exception_msg(exception):
    """ Create an error message to display to users for all exceptions not caught during the
    exception of the :obj:`run` method (exceptions of all types except :obj:`GitHubActionCaughtError`)

    Args:
        exception (:obj:`Exception`): a failure encountered during the exception of the :obj:`run` method

    Returns:
        :obj:`str`: error message to display to users
    """
    gh_action_run_url = GitHubAction.get_gh_action_run_url()
    return [
        Comment(text='The validation/submission of your simulator failed.'),
        Comment(text=str(exception), error=True),
        Comment(text=('The complete log of your validation/submission job, including further information about the failure, '
                      + 'is available [here]({}).'.format(gh_action_run_url))),
        Comment(text=('If you chose to validate your Docker image, the results of the validation of your image will be '
                      'available shortly as a JSON file. A link to this file will be available from the "Artifacts" '
                      'section at the bottom of [this page]({}).'.format(gh_action_run_url))),
        Comment(text='Once you have fixed the problem, edit the first block of this issue to re-initiate this validation.'),
        Comment(text=('The BioSimulators Team is happy to help. '
                      'Questions and feedback can be directed to the BioSimulators Team by posting comments to this issues that '
                      'reference the GitHub team `@biosimulators/biosimulators` (without the backticks).')),
    ]


class ValidateCommitSimulatorGitHubAction(GitHubAction):
    """ Action to validate a containerized simulator

    Attributes:
        issue_number (:obj:`str`): number of GitHub issue which triggered the action
    """

    def __init__(self):
        super(ValidateCommitSimulatorGitHubAction, self).__init__()
        self.config = Config()
        self.issue_number = self.get_issue_number()

    @GitHubActionErrorHandling.catch_errors(uncaught_exception_msg_func=get_uncaught_exception_msg,
                                            caught_error_labels=[IssueLabel.invalid],
                                            uncaught_error_labels=[IssueLabel.invalid])
    def run(self):
        """ Validate and commit a simulator."""

        # Get properties of submission
        issue_props = self.get_issue(self.issue_number)
        submission = get_simulator_submission_from_gh_issue_body(issue_props['body'])
        submitter = issue_props['user']['login']

        # Send message that validation is starting
        self.add_comment_to_issue(self.issue_number, self.get_initial_message(submission, submitter))

        # reset labels except approved
        self.reset_issue_labels(self.issue_number, [IssueLabel.validated.value, IssueLabel.invalid.value, IssueLabel.action_error.value])

        # get specifications of simulator and validate simulator
        specifications, test_results = self.exec_core(submission, submitter)

        # label issue as validated
        self.add_labels_to_issue(self.issue_number, [IssueLabel.validated.value])

        # get specifications of other versions of simulator
        existing_version_specifications = get_simulator_version_specs(specifications['id'])

        # determine if simulator is approved: issue is a revision of an existing version of a validated simulator,
        # a new version of a validated simulator, or the issue has been manually approved by the BioSimulators Team
        approved = self.is_simulator_approved(specifications, existing_version_specifications)

        # if approved, label the issue as approved
        if approved and IssueLabel.approved.value not in self.get_labels_for_issue(self.issue_number):
            self.add_labels_to_issue(self.issue_number, [IssueLabel.approved.value])

        # commit simulator or indicate that further review is required
        if submission.commit_simulator:
            if approved:
                self.commit_simulator(submission, specifications, existing_version_specifications, test_results)

                # post success message
                self.add_comment_to_issue(
                    self.issue_number,
                    ''.join([
                        'Your submission was committed to the BioSimulators registry. Thank you!\n',
                        '\n',
                        'Future submissions of subsequent versions of {} to the BioSimulators registry '.format(specifications['id']),
                        'will be automatically validated. These submissions will not require manual review by the BioSimulators Team.',
                    ])
                )

                # close issue
                self.close_issue(self.issue_number)
            else:
                assigned = set([assignee['login'] for assignee in issue_props['assignees']])
                new_assignees = set(self.config.biosimulators_curator_gh_ids).difference(assigned)
                if new_assignees:
                    self.assign_issue(self.issue_number,  list(new_assignees))
                self.add_comment_to_issue(
                    self.issue_number,
                    ('A member of the BioSimulators team will review your submission and '
                     'publish your image before final committment to the registry.'))

    def get_initial_message(self, submission, submitter):
        """ Peport message that validation is starting

        Args:
            submission (:obj:`SimulatorSubmission`): simulator submission
            submitter (:obj:`str`): GitHub user name of person who executed the submission
        """
        actions = []
        not_actions = []

        actions.append('validating the specifications of your simulator')
        if submission.validate_image:
            actions.append('validating your Docker image')
            test_results_msg = (
                ' The results of the validation of your tool will also be saved as a JSON file.'
                'A link to this file will be available from the "Artifacts" section at the bottom of this page.'
            )
        else:
            not_actions.append('You have chosen not to have the Docker image for your simulator validated.')
            test_results_msg = ''
        if submission.commit_simulator:
            job_type = 'submission'
            actions.append('committing your simulator to the BioSimulators registry')
        else:
            job_type = 'validation'
            not_actions.append('You have chosen not to submit your simulator to the BioSimulators registry.')

        if len(actions) == 1:
            actions = actions[0]
        else:
            actions = ', '.join(actions[0:-1]) + ' and ' + actions[-1]
        not_actions = ' '.join(action.strip() for action in not_actions)

        return ('Thank you @{} for your submission to the BioSimulators simulator validation/submission system!\n\n'
                'The BioSimulators validator bot is {}. {}\n\n'
                'We will discuss any concerns with your submission in this issue.\n\n'
                'A complete log of your simulator {} job will be available [here]({}).{}\n\n'
                ).format(submitter, actions, not_actions, job_type, self.get_gh_action_run_url(), test_results_msg)

    def exec_core(self, submission, submitter):
        """ Validate simulator

        * Validate specifications
        * Validate image

        Args:
            submission (:obj:`SimulatorSubmission`): simulator submission
            submitter (:obj:`str`): GitHub id of the submitter

        Returns:
            :obj:`tuple`:

                * :obj:`dict`: specifications of a simulation tool
                * :obj:`list` of :obj:`TestCaseResults`: results of test cases
        """
        # validate specifications
        specifications = biosimulators_utils.simulator.io.read_simulator_specs(
            submission.specifications_url, submission.specifications_patch)

        # check permissions
        self.validate_permissions(specifications['id'], specifications['name'], submitter)

        # indicate that specifications are valid
        self.add_comment_to_issue(self.issue_number, 'The specifications of your simulator is valid!')

        # validate image
        if submission.validate_image:
            test_results = self.validate_image(specifications)
            self.add_comment_to_issue(self.issue_number, 'The image for your simulator is valid!')
        else:
            test_results = None

        # return specifications
        return specifications, test_results

    def validate_permissions(self, simulator_id, simulator_name, submitter):
        """ Validate that the submitter has permissions to submit or update the simulator

        Args:
            simulator_id (:obj:`str`): simulator id
            simulator_name (:obj:`str`): simulator name
            submitter (:obj:`str`): GitHub id of the submitter
        """
        # check if team exists
        response = requests.get(
            'https://api.github.com/orgs/biosimulators/teams/' + simulator_id,
            auth=self.get_gh_auth())
        try:
            response.raise_for_status()
            has_team = True
        except requests.exceptions.HTTPError:
            if response.status_code == 404:
                has_team = False
            else:
                raise

        # create team if none exists and add submitter as a maintainer of the team
        if not has_team:
            # get parent team
            response = requests.get(
                'https://api.github.com/orgs/biosimulators/teams/simulator-developers',
                auth=self.get_gh_auth())
            response.raise_for_status()
            base_team_id = response.json()['id']

            # create team
            response = requests.post(
                'https://api.github.com/orgs/biosimulators/teams',
                auth=self.get_gh_auth(), json={
                    'name': simulator_id,
                    'description': 'Developers of ' + simulator_name,
                    'parent_team_id': base_team_id,
                    'maintainers': [submitter],
                })
            response.raise_for_status()

            # tell user a group was created
            msg = (
                'We created the GitHub group @biosimulators/{} to manage permissions to change the specifications of {} '
                'and added you (@{}) to this group. You can manage permissions to change the specifications of {} at '
                'https://github.com/orgs/biosimulators/teams/{}/members.'
            ).format(simulator_id, simulator_name, submitter, simulator_name, simulator_id)
            self.add_comment_to_issue(self.issue_number, msg)

        # check submitter has permissions to team
        else:
            response = requests.get(
                'https://api.github.com/orgs/biosimulators/teams/{}/memberships/{}'.format(simulator_id, submitter),
                auth=self.get_gh_auth())
            try:
                response.raise_for_status()
                has_permissions = True
            except requests.exceptions.HTTPError:
                if response.status_code == 404:
                    has_permissions = False
                else:
                    raise

            if not has_permissions:
                msg = (
                    'You (@{}) do not have permissions to update the specifications of {}. Only the members of @biosimulators/{} '
                    'can update the specifications of {}. Please contact the members of this group to request permissions to update {}.'
                ).format(submitter, simulator_name, simulator_id, simulator_name, simulator_name)
                self.add_error_comment_to_issue(self.issue_number, [Comment(text=msg, error=True)])

    def validate_image(self, specifications):
        """ Validate a Docker image for simulation tool

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool

        Returns:
            :obj:`list` of :obj:`TestCaseResults`: results of test cases
        """
        docker_client = biosimulators_utils.image.login_to_docker_registry(
            'docker.io', self.config.docker_hub_username, self.config.docker_hub_token)

        # validate that container (Docker image) exists
        image_url = specifications['image']['url']
        get_docker_image(docker_client, image_url, pull=True)

        # validate that Docker image can be converted to a Singularity image
        biosimulators_utils.image.convert_docker_image_to_singularity(image_url)

        # validate that image is consistent with the BioSimulators standards
        validator = SimulatorValidator(specifications, output_medium=OutputMedium.gh_issue)
        case_results = validator.run()
        write_test_results(case_results, '.biosimulators-test-suite-results.json',
                           gh_issue=int(self.issue_number), gh_action_run=int(self.get_gh_action_run_id()))
        summary, failure_details, warning_details, skipped_details = validator.summarize_results(case_results)

        # print summary to console
        print('')
        print('=============== SUMMARY ===============')
        print('')
        print(summary + '\n\n')
        if failure_details:
            color = Colors.failure.value
            print(termcolor.colored('=============== FAILURES ===============', color))
            print(termcolor.colored('', color))
            print(termcolor.colored('* ' + '\n\n* '.join(failure_details), color))
            print('')
        if warning_details:
            color = Colors.warning.value
            print(termcolor.colored('=============== WARNINGS ===============', color))
            print(termcolor.colored('', color))
            print(termcolor.colored('* ' + '\n\n* '.join(warning_details), color))
            print('')
        if skipped_details:
            color = Colors.skipped.value
            print(termcolor.colored('================ SKIPS =================', color))
            print(termcolor.colored('', color))
            print(termcolor.colored('* ' + '\n\n* '.join(skipped_details), color))
            print('')

        # push summary to comments on GitHub issue
        unable_to_post_results_msg = (
            'The summary of the tests of your Docker image could not be posted to this GitHub issue. '
            'The most likely reason is that the summary is too long to post to a comment on a GitHub issue. '
            'Please use the [console log]({}) of the associated GitHub Action to see the summary of the tests of your '
            'Docker image.'
        ).format(self.get_gh_action_run_url())

        msg = '## Summary of tests\n\n{}\n\n'.format(summary)
        self.add_comment_to_issue(self.issue_number, msg, alternative_comment=unable_to_post_results_msg)

        if failure_details:
            msg = '\n## Failures\n\n{}\n\n'.format('### ' + '\n### '.join(failure_details))
            self.add_comment_to_issue(self.issue_number, msg, alternative_comment=unable_to_post_results_msg)

        if warning_details:
            msg = '\n## Warnings\n\n{}\n\n'.format('### ' + '\n### '.join(warning_details))
            self.add_comment_to_issue(self.issue_number, msg, alternative_comment=unable_to_post_results_msg)

        if skipped_details:
            msg = '\n## Skips\n\n{}\n\n'.format('### ' + '\n### '.join(skipped_details))
            self.add_comment_to_issue(self.issue_number, msg, alternative_comment=unable_to_post_results_msg)

        invalid_cases = [case_result for case_result in case_results if case_result.type == TestCaseResultType.failed]
        if invalid_cases:
            gh_action_run_url = self.get_gh_action_run_url()
            error_msg = (
                'After correcting your simulator, please edit the first block of this issue to re-initiate this validation.\n\n'
                'The complete log of your validation/submission job, including further information about the failure, '
                'is available [here]({}). The results of the validation of your image will also be '
                'available shortly as a JSON file. A link to this file will be available from the "Artifacts" '
                'section at the bottom of [this page]({}).'
            ).format(gh_action_run_url, gh_action_run_url)

            self.add_error_comment_to_issue(self.issue_number, [Comment(text=error_msg, error=True)])

        valid_cases = [case_result for case_result in case_results
                       if case_result.type == TestCaseResultType.passed and case_result.case.id.startswith('sedml.')]
        if not valid_cases:
            self.add_error_comment_to_issue(self.issue_number, [Comment(text=(
                'No test cases are applicable to your simulator. '
                'Please use this issue to share appropriate test COMBINE/OMEX files. '
                'The BioSimulators Team will add these files to this validation program and then re-review your simulator.'
            ))])

        return case_results

    def is_simulator_approved(self, specifications, existing_version_specifications):
        """ Determine whether a simulation tool has already been approved

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool
            existing_version_specifications (:obj:`list` of :obj:`dict`): specifications of other versions of simulation tool

        Returns:
            :obj:`bool`: :obj:`True`, if the simulation tool has already been approved
        """
        return (self.does_submission_have_approved_label()
                or self.is_other_version_of_simulator_validated(specifications, existing_version_specifications))

    def does_submission_have_approved_label(self):
        """ Determine whether an issue for submitting a simulator already has the approved label

        Returns:
            :obj:`bool`: :obj:`True`, if the issue for the submission already has the approved label
        """
        if IssueLabel.approved.value in self.get_labels_for_issue(self.issue_number):
            return True

    def is_other_version_of_simulator_validated(self, specifications, existing_version_specifications):
        """ Determine whether another version of the simulation tool has already been approved

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool
            existing_version_specifications (:obj:`list` of :obj:`dict`): specifications of other versions of simulation tool

        Returns:
            :obj:`bool`: :obj:`True`, if the simulation tool has already been approved
        """
        for version_spec in existing_version_specifications:
            if version_spec.get('biosimulators', {}).get('validated', False):
                return True
        return False

    def commit_simulator(self, submission, specifications, existing_version_specifications, test_results):
        """ Commit simulator to the BioSimulators registry

        Args:
            submission (:obj:`SimulatorSubmission`): simulator submission
            specifications (:obj:`dict`): specifications of a simulation tool
            existing_version_specifications (:obj:`list` of :obj:`dict`): specifications of other versions of simulation tool
            test_results (:obj:`list` of :obj:`TestCaseResults`): results of test cases
        """
        # commit image
        if submission.validate_image:
            # copy image to BioSimulators namespace of Docker registry (GitHub Container Registry)
            self.push_image(specifications, existing_version_specifications)

            # instruct runBioSimulations to generate a Singularity image for the Docker image
            self.trigger_conversion_of_docker_image_to_singularity(specifications)

        # commit submission to BioSimulators database
        if 'biosimulators' not in specifications:
            specifications['biosimulators'] = {}

        if submission.validate_image:
            specifications['biosimulators']['validated'] = True
            specifications['biosimulators']['validationTests'] = TestResultsReport(
                results=test_results, gh_issue=int(self.issue_number), gh_action_run=int(self.get_gh_action_run_id()),
            ).to_dict()

        else:
            specifications['biosimulators']['validated'] = False
            specifications['biosimulators']['validationTests'] = None

        self.post_entry_to_biosimulators_api(specifications, existing_version_specifications)

    def push_image(self, specifications, existing_version_specifications):
        """ Push the image for a simulation tool to the GitHub Container Registry

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool
            existing_version_specifications (:obj:`list` of :obj:`dict`): specifications of other versions of simulation tool
        """
        # get image, pulling if necessary
        original_image_url = specifications['image']['url']
        docker_client = biosimulators_utils.image.login_to_docker_registry(
            'docker.io', self.config.docker_hub_username, self.config.docker_hub_token)
        image = get_docker_image(docker_client, original_image_url, pull=True)

        # push image to BioSimulators namespace of Docker registry
        biosimulators_utils.image.login_to_docker_registry(
            self.config.biosimulators_docker_registry_url,
            self.config.biosimulators_docker_registry_username,
            self.config.biosimulators_docker_registry_token)

        copy_image_url = self.config.biosimulators_docker_image_url_pattern \
            .format(specifications['id'], specifications['version']) \
            .lower()
        biosimulators_utils.image.tag_and_push_docker_image(docker_client, image, copy_image_url)
        specifications['image']['url'] = copy_image_url

        is_latest = self.is_submission_latest_version_of_simulator(specifications, existing_version_specifications)

        if is_latest:
            latest_copy_image_url = self.config.biosimulators_docker_image_url_pattern \
                .format(specifications['id'], 'latest') \
                .lower()
            biosimulators_utils.image.tag_and_push_docker_image(docker_client, image, latest_copy_image_url)

        # make image public -- must be done manually; cannot be done via API as of 2020-11-11

    def is_submission_latest_version_of_simulator(self, specifications, existing_version_specifications):
        """ Determine whether the submitted version the latest version of the simulator (greatest tag)

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool
            existing_version_specifications (:obj:`list` of :obj:`dict`): specifications of other versions of simulation tool

        Returns:
            :obj:`bool`: :obj:`True` if the submitted version if the latest version of the simulator
        """
        version_comparison_func = natsort_keygen()
        for existing_version_spec in existing_version_specifications:
            if (
                existing_version_spec['image']
                and existing_version_spec.get('biosimulators', {}).get('validated', False)
                and version_comparison_func(existing_version_spec['version']) > version_comparison_func(specifications['version'])
            ):
                return False
        return True

    def trigger_conversion_of_docker_image_to_singularity(self, specifications):
        """ Post the simulation to the BioSimulators database

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool
        """
        auth_headers = self.get_auth_headers_for_biosimulations_api(
            self.config.runbiosimulations_auth_endpoint, self.config.runbiosimulations_audience,
            self.config.runbiosimulations_api_client_id, self.config.runbiosimulations_api_client_secret)

        response = requests.post(self.config.runbiosimulations_api_endpoint + 'images/refresh',
                                 headers=auth_headers,
                                 json={
                                     'simulator': specifications['id'],
                                     'version': specifications['version'],
                                 })
        validate_biosimulations_api_response(response, 'A Singularity image could not be generated for the Docker image')

    def post_entry_to_biosimulators_api(self, specifications, existing_version_specifications):
        """ Post the simulation to the BioSimulators database

        Args:
            specifications (:obj:`dict`): specifications of a simulation tool
            existing_version_specifications (:obj:`list` of :obj:`dict`): specifications of other versions of simulation tool
        """
        auth_headers = self.get_auth_headers_for_biosimulations_api(
            self.config.biosimulators_auth_endpoint, self.config.biosimulators_audience,
            self.config.biosimulators_api_client_id, self.config.biosimulators_api_client_secret)

        existing_versions = [existing_version_spec['version'] for existing_version_spec in existing_version_specifications]
        update_simulator = specifications['version'] in existing_versions
        if update_simulator:
            endpoint = '{}simulators/{}/{}'.format(self.config.biosimulators_api_endpoint, specifications['id'], specifications['version'])
            requests_method = requests.put
            method = 'updated'
        else:
            endpoint = '{}simulators'.format(self.config.biosimulators_api_endpoint)
            requests_method = requests.post
            method = 'added'
        response = requests_method(endpoint, headers=auth_headers, json=specifications)
        validate_biosimulations_api_response(response, 'Simulation tool `{}` could not be {} to the BioSimulators registry.'.format(
            specifications['id'], method))

    def get_auth_headers_for_biosimulations_api(self, endpoint, audience, client_id, client_secret):
        """ Get authorization headers for using one of the BioSimulations REST APIs
        (BioSimulators, runBioSimulations, etc.).

        Args:
            endpoint (:obj:`str`): URL for getting an authentication token
            audience (:obj:`str`): API audience
            client_id (:obj:`str`): id for this client
            client_secret (:obj:`str`): secret for this client

        Returns:
            :obj:`dict`: authorization headers
        """
        response = requests.post(endpoint, json={
            'client_id': client_id,
            'client_secret': client_secret,
            'audience': audience,
            "grant_type": "client_credentials",
        })
        response.raise_for_status()
        response_data = response.json()
        return {'Authorization': response_data['token_type'] + ' ' + response_data['access_token']}

    @classmethod
    def add_comment_to_issue(cls, issue_number, comment, alternative_comment=None, max_len=65536):
        """ Post a comment to the GitHub issue

        Args:
            issue_number (:obj:`str`): issue number
            comment (:obj:`str`): comment
            alternative_comment (:obj:`str`, optional): optional alternative comment to try posting to the GitHub issue
            max_len (:obj:`int`, optional): maximum comment length accepted by GitHub
        """
        try:
            if len(comment) > max_len:
                comment = comment[0:max_len - 4] + ' ...'
            super(ValidateCommitSimulatorGitHubAction, cls).add_comment_to_issue(issue_number, comment)

        except (requests.exceptions.RequestException, requests.exceptions.ProxyError, requests.exceptions.SSLError):
            if alternative_comment:
                super(ValidateCommitSimulatorGitHubAction, cls).add_comment_to_issue(issue_number, alternative_comment)
            else:
                raise
