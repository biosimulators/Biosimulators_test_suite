""" Data model for test cases for validating simulators

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .exceptions import SkippedTestCaseException  # noqa: F401
from biosimulators_utils.image import get_docker_image
import abc
import docker
import enum

__all__ = [
    'OutputMedium',
    'TestCase', 'SedTaskRequirements', 'ExpectedSedReport', 'ExpectedSedPlot',
    'AlertType',
]


class OutputMedium(str, enum.Enum):
    """ Output medium """
    console = 'console'
    gh_issue = 'gh_issue'


class TestCase(abc.ABC):
    """ A test case for validating a simulator

    Attributes:
        id (:obj:`str`): id
        name (:obj:`str`): name
        description (:obj:`str`): description
        output_medium (:obj:`OutputMedium`): medium the description should be formatted for
    """

    def __init__(self, id=None, name=None, description=None, output_medium=OutputMedium.console):
        """
        Args:
            id (:obj:`str`, optional): id
            name (:obj:`str`, optional): name
            description (:obj:`str`): description
            output_medium (:obj:`OutputMedium`, optional): medium the description should be formatted
        """
        self.id = id
        self.name = name
        self.description = description
        self.output_medium = output_medium

    @abc.abstractmethod
    def eval(self, specifications):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate

        Raises:
            :obj:`SkippedTestCaseException`: if the test case is not applicable to the simulator
            :obj:`Exception`: if the simulator did not pass the test case
        """
        pass  # pragma: no cover

    def get_simulator_docker_image(self, specifications, pull=True):
        """ Get the Docker image for a simulator, pulling if necessary

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate

        Returns:
            :obj:`docker.models.images.Image`: Docker image
        """
        docker_client = docker.from_env()
        image_url = specifications['image']['url']
        return get_docker_image(docker_client, image_url, pull=pull)


class SedTaskRequirements(object):
    """ Required model format for simulation algorithm for each task in a SED document

    Attributes:
        model_format (:obj:`str`): EDAM id for the format of the model involved in the task
        simulation_algorithm (:obj:`str`): KiSAO id for the simulation algorithm involved in the task
    """

    def __init__(self, model_format=None, simulation_algorithm=None):
        """
        Args:
            model_format (:obj:`str`, optional): EDAM id for the format of the model involved in the task
            simulation_algorithm (:obj:`str`, optional): KiSAO id for the simulation algorithm involved in the task
        """
        self.model_format = model_format
        self.simulation_algorithm = simulation_algorithm


class ExpectedSedReport(object):
    """ An expected SED report

    Attributes
        id (:obj:`str`): id
        data_sets (:obj:`list` of :obj:`str`): ids of expected datasets
        points (:obj:`tuple` of :obj:`int`): number of expected points of
        values (:obj:`dict` of :obj:`str` to :obj:`dict` of :obj:`list`): expected values of datasets or elements of datasets
    """

    def __init__(self, id=None, data_sets=None, points=None, values=None):
        """
        Args:
            id (:obj:`str`, optional): id
            data_sets (:obj:`set` of :obj:`str`, optional): ids of expected datasets
            points (:obj:`tuple` of :obj:`int`, optional): number of expected points of
            values (:obj:`dict` of :obj:`str` to :obj:`dict` of :obj:`list`, optional): expected values of datasets or elements of datasets
        """
        self.id = id
        self.data_sets = data_sets or set()
        self.points = points
        self.values = values


class ExpectedSedPlot(object):
    """ An expected SED report

    Attributes
        id (:obj:`str`): id
    """

    def __init__(self, id=None):
        """
        Args:
            id (:obj:`str`, optional): id
        """
        self.id = id


class AlertType(str, enum.Enum):
    """ Type of alert upon the failure of a test case """
    exception = 'exception'
    warning = 'warning'
