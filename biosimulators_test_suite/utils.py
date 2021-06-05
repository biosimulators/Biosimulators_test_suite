""" Utility methods

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-06-05
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
import os

__all__ = ['get_singularity_image_filename']


def get_singularity_image_filename(docker_image):
    """ Get the location where a Singularity version of a Docker image should be saved

    Args:
        docker_image (:obj:`str`): URL for the Docker version of the image

    Returns:
        :obj:`str`: path where a Singularity version of a Docker image should be saved
    """

    return os.path.join(
        Config().singularity_image_dirname,
        docker_image.replace('/', '_').replace(':', '_') + '.sif')
