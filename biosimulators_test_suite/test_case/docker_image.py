""" Methods for test cases involving checking Docker images

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..data_model import AbstractTestCase
import docker
import warnings


class OciLabelsCase(AbstractTestCase):
    """ Test that a Docker image has Open Container Initiative (OCI) labels with metadata about image """
    EXPECTED_LABELS = [
        'org.opencontainers.image.authors',
        'org.opencontainers.image.description',
        'org.opencontainers.image.documentation',
        'org.opencontainers.image.licenses',
        'org.opencontainers.image.revision',
        'org.opencontainers.image.source',
        'org.opencontainers.image.title',
        'org.opencontainers.image.url',
        'org.opencontainers.image.vendor',
        'org.opencontainers.image.version',
    ]

    def eval(self, specifications):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate

        Raises:
            :obj:`Exception`: if the simulator did not pass the test case
        """
        docker_client = docker.from_env()
        image = docker_client.images.pull(specifications['image']['url'])
        missing_labels = set(self.EXPECTED_LABELS).difference(set(image.labels.keys()))
        if missing_labels:
            warnings.warn('The Docker image should have the following Open Container Initiative (OCI) labels:\n  {}'.format(
                '\n  '.join(sorted(missing_labels))))
