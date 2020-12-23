""" Data model for test cases for validating simulators

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import abc
import enum

__all__ = ['AbstractTestCase', 'SedTaskRequirements', 'ExpectedSedReport', 'ExpectedSedPlot',
           'TestCaseResultType', 'TestCaseResult',
           'InvalidOuputsException', 'InvalidOuputsWarning',
           'SkippedTestCaseException', 'IgnoreTestCaseWarning']


class AbstractTestCase(abc.ABC):
    """ A test case for validating a simulator

    Attributes:
        id (:obj:`str`): id
        name (:obj:`str`): name
        description (:obj:`str`): description
    """

    def __init__(self, id=None, name=None, description=None):
        """
        Args:
            id (:obj:`str`, optional): id
            name (:obj:`str`, optional): name
            description (:obj:`str`): description
        """
        self.id = id
        self.name = name
        self.description = description

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


class TestCaseResultType(str, enum.Enum):
    """ Type of test case result """
    passed = 'passed'
    failed = 'failed'
    skipped = 'skipped'


class TestCaseResult(object):
    """ A result of executing a test case

    Attributes:
        case (:obj:`TestCase`): test case
        type (:obj:`obj:`TestCaseResultType`): type
        duration (:obj:`float`): execution duration in seconds
        exception (:obj:`Exception`): exception
        log (:obj:`str`): log of execution
    """

    def __init__(self, case=None, type=None, duration=None, exception=None, log=None):
        """
        Args:
            case (:obj:`TestCase`, optional): test case
            type (:obj:`obj:`TestCaseResultType`, optional): type
            duration (:obj:`float`, optional): execution duration in seconds
            exception (:obj:`Exception`, optional): exception
            log (:obj:`str`, optional): log of execution
        """
        self.case = case
        self.type = type
        self.duration = duration
        self.exception = exception
        self.log = log


class InvalidOuputsException(Exception):
    """ Exception raised when outputs of execution of COMBINE/OMEX archive are not as expected """
    pass  # pragma: no cover


class InvalidOuputsWarning(UserWarning):
    """ Warning raised when outputs of execution of COMBINE/OMEX archive are not as expected """
    pass  # pragma: no cover


class SkippedTestCaseException(Exception):
    """ Exception raised that indicates that a test case should be skipped """
    pass  # pragma: no cover


class IgnoreTestCaseWarning(UserWarning):
    """ Warning raised that indicates that a test case was ignored """
    pass  # pragma: no cover
