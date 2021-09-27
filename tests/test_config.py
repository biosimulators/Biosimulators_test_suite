from biosimulators_test_suite.config import Config
from unittest import mock
import os
import unittest


class ConfigTestCase(unittest.TestCase):
    def test_defaults(self):
        Config()

    def test_env_vars(self):
        with mock.patch.dict(os.environ, {
            'PULL_DOCKER_IMAGE': '0',
            'BIOSIMULATORS_CURATOR_GH_IDS': '',
        }):
            config = Config()
        self.assertEqual(config.pull_docker_image, False)
        self.assertEqual(config.biosimulators_curator_gh_ids, [])

        with mock.patch.dict(os.environ, {
            'PULL_DOCKER_IMAGE': '0',
            'BIOSIMULATORS_CURATOR_GH_IDS': 'user1,user2, user3',
        }):
            config = Config()
        self.assertEqual(config.pull_docker_image, False)
        self.assertEqual(config.biosimulators_curator_gh_ids, ['user1', 'user2', 'user3'])

        with mock.patch.dict(os.environ, {
            'BIOSIMULATORS_DOCKER_REGISTRY_USERNAME': 'user1',
            'DOCKER_REGISTRY_USERNAME': 'user2',
        }):
            config = Config()
        self.assertEqual(config.biosimulators_docker_registry_username, 'user1')

        with mock.patch.dict(os.environ, {
            'DOCKER_REGISTRY_USERNAME': 'user2',
        }):
            config = Config()
        self.assertEqual(config.biosimulators_docker_registry_username, 'user2')

    def test_arguments(self):
        config = Config(
            pull_docker_image=True, docker_hub_username='user', docker_hub_token='token',
            biosimulators_auth_endpoint='https://auth.biosimulators.org', biosimulators_audience='biosimulators_audience',
            biosimulators_api_client_id='biosimulators_client_id', biosimulators_api_client_secret='biosimulators_client_secret',
            biosimulators_api_endpoint='https://api.biosimulators.org',
            biosimulators_curator_gh_ids=['user'], biosimulators_default_specifications_version='1.0.0',
            biosimulators_default_image_version='1.0.0', biosimulators_docker_registry_url='ghcr.io',
            biosimulators_docker_registry_username='user@ghcr.io', biosimulators_docker_registry_token='token@ghcr.io',
            biosimulators_docker_image_url_pattern='ghcr.io/biosimulators/{}:{}',
            runbiosimulations_auth_endpoint='https://run.auth.biosimulations.org', runbiosimulations_audience='runbiosimulations_audience',
            runbiosimulations_api_client_id='runbiosimulations_client_id',
            runbiosimulations_api_client_secret='runbiosimulations_client_secret',
            runbiosimulations_api_endpoint='https://api.biosimulations.org')

        self.assertEqual(config.pull_docker_image, True)
        self.assertEqual(config.docker_hub_username, 'user')
        self.assertEqual(config.docker_hub_token, 'token')
        self.assertEqual(config.biosimulators_auth_endpoint, 'https://auth.biosimulators.org')
        self.assertEqual(config.biosimulators_audience, 'biosimulators_audience')
        self.assertEqual(config.biosimulators_api_client_id, 'biosimulators_client_id')
        self.assertEqual(config.biosimulators_api_client_secret, 'biosimulators_client_secret')
        self.assertEqual(config.biosimulators_api_endpoint, 'https://api.biosimulators.org')
        self.assertEqual(config.biosimulators_curator_gh_ids, ['user'])
        self.assertEqual(config.biosimulators_default_specifications_version, '1.0.0')
        self.assertEqual(config.biosimulators_default_image_version, '1.0.0')
        self.assertEqual(config.biosimulators_docker_registry_url, 'ghcr.io')
        self.assertEqual(config.biosimulators_docker_registry_username, 'user@ghcr.io')
        self.assertEqual(config.biosimulators_docker_registry_token, 'token@ghcr.io')
        self.assertEqual(config.biosimulators_docker_image_url_pattern, 'ghcr.io/biosimulators/{}:{}')
        self.assertEqual(config.runbiosimulations_auth_endpoint, 'https://run.auth.biosimulations.org')
        self.assertEqual(config.runbiosimulations_audience, 'runbiosimulations_audience')
        self.assertEqual(config.runbiosimulations_api_client_id, 'runbiosimulations_client_id')
        self.assertEqual(config.runbiosimulations_api_client_secret, 'runbiosimulations_client_secret')
        self.assertEqual(config.runbiosimulations_api_endpoint, 'https://api.biosimulations.org')
