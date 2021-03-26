""" Configuration

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-30
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import os


class Config(object):
    """ Configuration

    Attributes:
        pull_docker_image (:obj:`bool`): whether to pull the Docker image for the simulator (default: :obj:`True`)
        docker_hub_username (:obj:`str`): username for Docker Hub
        docker_hub_token (:obj:`str`): Token for Docker Hub
        biosimulators_auth_endpoint (:obj:`str`): Authentification endpoint for the BioSimulators API
        biosimulators_audience (:obj:`str`): Open API audience for the BioSimulators API
        biosimulators_api_client_id (:obj:`str`): Client id of the BioSimulators API
        biosimulators_api_client_secret (:obj:`str`): Client secret of the BioSimulators API
        biosimulators_api_endpoint (:obj:`str`): Base URL for the BioSimulators API
        biosimulators_curator_gh_ids (:obj:`list` of :obj:`str`): GitHub user ids of the BioSimulators curators
        biosimulators_default_specifications_version (:obj:`str`): Default version of the BioSimulators simulation specifications
        biosimulators_default_image_version (:obj:`str`): Default version of the BioSimulators Docker image format
        biosimulators_docker_registry_url (:obj:`str`): URL of the Docker registry for simulators
        biosimulators_docker_registry_username (:obj:`str`): username for Docker registry for simulators
        biosimulators_docker_registry_token (:obj:`str`): token for Docker registry for simulators
        biosimulators_docker_image_url_pattern (:obj:`str`): URL pattern for Docker images for simulators
        runbiosimulations_auth_endpoint (:obj:`str`): Authentification endpoint for the runBioSimulations API
        runbiosimulations_audience (:obj:`str`): Open API audience for the runBioSimulations API
        runbiosimulations_api_client_id (:obj:`str`): Client id of the runBioSimulations API
        runbiosimulations_api_client_secret (:obj:`str`): Client secret of the runBioSimulations API
        runbiosimulations_api_endpoint (:obj:`str`): Base URL for the runBioSimulations API
        test_case_timeout (:obj:`int`): time out for test cases in seconds
        user_to_exec_in_simulator_containers (:obj:`str` or :obj:`None`): user id or name to execute calls inside simulator containers

            * Use ``_CURRENT_USER_`` to indicate that the Docker container should execute commands as the current user (``os.getuid()``)
            * Use the format ``<name|uid>[:<group|gid>]`` to indicate any other user/group that the Docker container should use to
              execute commands
    """

    def __init__(self,
                 pull_docker_image=None, docker_hub_username=None, docker_hub_token=None,
                 biosimulators_auth_endpoint=None, biosimulators_audience=None,
                 biosimulators_api_client_id=None, biosimulators_api_client_secret=None,
                 biosimulators_api_endpoint=None,
                 biosimulators_curator_gh_ids=None, biosimulators_default_specifications_version=None,
                 biosimulators_default_image_version=None, biosimulators_docker_registry_url=None,
                 biosimulators_docker_registry_username=None, biosimulators_docker_registry_token=None,
                 biosimulators_docker_image_url_pattern=None,
                 runbiosimulations_auth_endpoint=None, runbiosimulations_audience=None,
                 runbiosimulations_api_client_id=None, runbiosimulations_api_client_secret=None,
                 runbiosimulations_api_endpoint=None,
                 test_case_timeout=None,
                 user_to_exec_in_simulator_containers=None):
        """
        Args:
            pull_docker_image (:obj:`bool`, optional): whether to pull the Docker image for the simulator (default: :obj:`True`)
            docker_hub_username (:obj:`str`, optional): username for Docker Hub
            docker_hub_token (:obj:`str`, optional): Token for Docker Hub
            biosimulators_auth_endpoint (:obj:`str`, optional): Authentification endpoint for the BioSimulators API
            biosimulators_audience (:obj:`str`, optional): Open API audience for the BioSimulators API
            biosimulators_api_client_id (:obj:`str`, optional): Client id of the BioSimulators API
            biosimulators_api_client_secret (:obj:`str`, optional): Client secret of the BioSimulators API
            biosimulators_api_endpoint (:obj:`str`, optional): Base URL for the BioSimulators API
            biosimulators_curator_gh_ids (:obj:`list` of :obj:`str`, optional): GitHub user ids of the BioSimulators curators
            biosimulators_default_specifications_version (:obj:`str`, optional): Default version of the BioSimulators simulation specifications
            biosimulators_default_image_version (:obj:`str`, optional): Default version of the BioSimulators Docker image format
            biosimulators_docker_registry_url (:obj:`str`, optional): URL of the Docker registry for simulators
            biosimulators_docker_registry_username (:obj:`str`, optional): username for Docker registry for simulators
            biosimulators_docker_registry_token (:obj:`str`, optional): token for Docker registry for simulators
            biosimulators_docker_image_url_pattern (:obj:`str`, optional): URL pattern for Docker images for simulators
            runbiosimulations_auth_endpoint (:obj:`str`, optional): Authentification endpoint for the runBioSimulations API
            runbiosimulations_audience (:obj:`str`, optional): Open API audience for the runBioSimulations API
            runbiosimulations_api_client_id (:obj:`str`, optional): Client id of the runBioSimulations API
            runbiosimulations_api_client_secret (:obj:`str`, optional): Client secret of the runBioSimulations API
            runbiosimulations_api_endpoint (:obj:`str`, optional): Base URL for the runBioSimulations API
            test_case_timeout (:obj:`int`, optional): time out for test cases in seconds
            user_to_exec_in_simulator_containers (:obj:`str`, optional): user id or name to execute calls inside simulator containers

                * Use ``_CURRENT_USER_`` to indicate that the Docker container should execute commands as the current user (``os.getuid()``)
                * Use the format ``<name|uid>[:<group|gid>]`` to indicate any other user/group that the Docker container should use to
                  execute commands
        """
        # Docker registry
        if pull_docker_image is None:
            self.pull_docker_image = os.getenv('PULL_DOCKER_IMAGE', '1').lower() in ['1', 'true']
        else:
            self.pull_docker_image = pull_docker_image

        # Docker Hub
        if docker_hub_username is None:
            self.docker_hub_username = os.getenv('DOCKER_HUB_USERNAME')
        else:
            self.docker_hub_username = docker_hub_username

        if docker_hub_token is None:
            self.docker_hub_token = os.getenv('DOCKER_HUB_TOKEN')
        else:
            self.docker_hub_token = docker_hub_token

        # BioSimulators
        if biosimulators_auth_endpoint is None:
            self.biosimulators_auth_endpoint = os.getenv('BIOSIMULATORS_AUTH_ENDPOINT', 'https://auth.biosimulations.org/oauth/token')
        else:
            self.biosimulators_auth_endpoint = biosimulators_auth_endpoint

        if biosimulators_audience is None:
            self.biosimulators_audience = os.getenv('BIOSIMULATORS_AUDIENCE', 'api.biosimulators.org')
        else:
            self.biosimulators_audience = biosimulators_audience

        if biosimulators_api_client_id is None:
            self.biosimulators_api_client_id = os.getenv('BIOSIMULATORS_API_CLIENT_ID')
        else:
            self.biosimulators_api_client_id = biosimulators_api_client_id

        if biosimulators_api_client_secret is None:
            self.biosimulators_api_client_secret = os.getenv('BIOSIMULATORS_API_CLIENT_SECRET')
        else:
            self.biosimulators_api_client_secret = biosimulators_api_client_secret

        if biosimulators_api_endpoint is None:
            self.biosimulators_api_endpoint = os.getenv('BIOSIMULATORS_API_ENDPOINT', 'https://api.biosimulators.org/')
        else:
            self.biosimulators_api_endpoint = biosimulators_api_endpoint

        if biosimulators_curator_gh_ids is None:
            ids = os.getenv('BIOSIMULATORS_CURATOR_GH_IDS', 'jonrkarr').strip()
            if ids:
                self.biosimulators_curator_gh_ids = [id.strip() for id in ids.split(',')]
            else:
                self.biosimulators_curator_gh_ids = []
        else:
            self.biosimulators_curator_gh_ids = biosimulators_curator_gh_ids

        if biosimulators_default_specifications_version is None:
            self.biosimulators_default_specifications_version = os.getenv('BIOSIMULATORS_DEFAULT_SPECIFICATIONS_VERSION', '1.0.0')
        else:
            self.biosimulators_default_specifications_version = biosimulators_default_specifications_version

        if biosimulators_default_image_version is None:
            self.biosimulators_default_image_version = os.getenv('BIOSIMULATORS_DEFAULT_IMAGE_VERSION', '1.0.0')
        else:
            self.biosimulators_default_image_version = biosimulators_default_image_version

        if biosimulators_docker_registry_url is None:
            self.biosimulators_docker_registry_url = os.getenv(
                'BIOSIMULATORS_DOCKER_REGISTRY_URL', os.getenv('DOCKER_REGISTRY_URL', 'ghcr.io'))
        else:
            self.biosimulators_docker_registry_url = biosimulators_docker_registry_url

        if biosimulators_docker_registry_username is None:
            self.biosimulators_docker_registry_username = os.getenv(
                'BIOSIMULATORS_DOCKER_REGISTRY_USERNAME', os.getenv('DOCKER_REGISTRY_USERNAME'))
        else:
            self.biosimulators_docker_registry_username = biosimulators_docker_registry_username

        if biosimulators_docker_registry_token is None:
            self.biosimulators_docker_registry_token = os.getenv(
                'BIOSIMULATORS_DOCKER_REGISTRY_TOKEN', os.getenv('DOCKER_REGISTRY_TOKEN'))
        else:
            self.biosimulators_docker_registry_token = biosimulators_docker_registry_token

        if biosimulators_docker_image_url_pattern is None:
            self.biosimulators_docker_image_url_pattern = os.getenv(
                'BIOSIMULATORS_DOCKER_REGISTRY_IMAGE_URL_PATTERN', 'ghcr.io/biosimulators/{}:{}')
        else:
            self.biosimulators_docker_image_url_pattern = biosimulators_docker_image_url_pattern

        # runBioSimulations
        if runbiosimulations_auth_endpoint is None:
            self.runbiosimulations_auth_endpoint = os.getenv(
                'RUNBIOSIMULATIONS_AUTH_ENDPOINT', 'https://auth.biosimulations.org/oauth/token')
        else:
            self.runbiosimulations_auth_endpoint = runbiosimulations_auth_endpoint

        if runbiosimulations_audience is None:
            self.runbiosimulations_audience = os.getenv('RUNBIOSIMULATIONS_AUDIENCE', 'dispatch.biosimulations.org')
        else:
            self.runbiosimulations_audience = runbiosimulations_audience

        if runbiosimulations_api_client_id is None:
            self.runbiosimulations_api_client_id = os.getenv('RUNBIOSIMULATIONS_API_CLIENT_ID')
        else:
            self.runbiosimulations_api_client_id = runbiosimulations_api_client_id

        if runbiosimulations_api_client_secret is None:
            self.runbiosimulations_api_client_secret = os.getenv('RUNBIOSIMULATIONS_API_CLIENT_SECRET')
        else:
            self.runbiosimulations_api_client_secret = runbiosimulations_api_client_secret

        if runbiosimulations_api_endpoint is None:
            self.runbiosimulations_api_endpoint = os.getenv('RUNBIOSIMULATIONS_API_ENDPOINT', 'https://run.api.biosimulations.org/')
        else:
            self.runbiosimulations_api_endpoint = runbiosimulations_api_endpoint

        if test_case_timeout is None:
            self.test_case_timeout = int(os.getenv('TEST_CASE_TIMEOUT', '300'))  # 300 seconds
        else:
            self.test_case_timeout = test_case_timeout

        if user_to_exec_in_simulator_containers is None:
            self.user_to_exec_in_simulator_containers = os.getenv('USER_TO_EXEC_IN_SIMULATOR_CONTAINERS', '_CURRENT_USER_') or None
        else:
            self.user_to_exec_in_simulator_containers = user_to_exec_in_simulator_containers
