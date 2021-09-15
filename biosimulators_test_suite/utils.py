""" Utility methods

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-06-05
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
import numpy
import os

__all__ = ['get_singularity_image_filename', 'simulation_results_isnan']


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


def simulation_results_isnan(value):
    """ Determine whether a scalar or each element of an array is NaN.

    Args:
        value (:obj:`int`, :obj:`float`, or :obj:`numpy.ndarray`): scalar or array

    Returns:
        :obj:`bool` or :obj:`numpy.ndarray`: whether the value or each element of the value is NaN
    """
    try:
        return numpy.isnan(value)
    except TypeError:
        if isinstance(value, numpy.ndarray):
            value_type = 'a NumPy array of dtype `{}`'.format(str(value.dtype))
        else:
            value_type = 'a `{}`'.format(value.__class__.__name__)

        msg = (
            'Simulation results must be numerical (e.g., `int`, `float`, or NumPy array of dtype `float64`, `int64`). '
            'Simulation results are {}.'
        ).format(value_type)
        raise TypeError(msg)
