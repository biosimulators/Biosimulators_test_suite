""" Data model for results of test cases

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-01
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .._version import __version__
from ..warnings import TestCaseWarning  # noqa: F401
import enum
import traceback

__all__ = [
    'TestCaseResultType',
    'TestCaseResult',
    'TestResultsReport',
]


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
        exception_traceback (:obj:`str`): traceback
        warnings (:obj:`list` of :obj:`TestCaseWarning`): warnings
        skip_reason (:obj:`Exception`): Exception which explains reason for skip
        log (:obj:`str`): log of execution
    """

    def __init__(self, case=None, type=None, duration=None, exception=None, exception_traceback=None, warnings=None, skip_reason=None, log=None):
        """
        Args:
            case (:obj:`TestCase`, optional): test case
            type (:obj:`obj:`TestCaseResultType`, optional): type
            duration (:obj:`float`, optional): execution duration in seconds
            exception (:obj:`Exception`, optional): exception
            exception_traceback (:obj:`str`, optional): traceback
            warnings (:obj:`list` of :obj:`TestCaseWarning`, optional): warnings
            skip_reason (:obj:`Exception`, optional): Exception which explains reason for skip
            log (:obj:`str`, optional): log of execution
        """
        self.case = case
        self.type = type
        self.duration = duration
        self.exception = exception
        self.exception_traceback = exception_traceback
        self.warnings = warnings or []
        self.skip_reason = skip_reason
        self.log = log

    def to_dict(self, max_log_len=None, debug=True):
        """ Generate a dictionary representation e.g., for export to JSON

        Args:
            max_log_len (:obj:`int`, optional): maximum log length
            debug (:obj:`bool`, optional): whether to display traceback information about each error
                with additional information for debugging

        Returns:
            :obj:`dict`: dictionary representation
        """
        log = self.log
        if max_log_len is not None and log and len(log) > max_log_len:
            log = log[0:max_log_len - 1] + ' ...'

        return {
            'case': {
                'id': self.case.id,
                'description': self.case.description,
            },
            'resultType': self.type.value,
            'duration': self.duration,
            'exception': {
                'category': self.exception.__class__.__name__,
                'message': str(self.exception),
                'traceback': traceback.format_tb(self.exception_traceback) if self.exception_traceback else None,
            } if self.exception else None,
            'warnings': [{'category': warning.category.__name__, 'message': str(warning.message)}
                         for warning in self.warnings],
            'skipReason': {
                'category': self.skip_reason.__class__.__name__,
                'message': str(self.skip_reason),
            } if self.skip_reason else None,
            'log': log,
        }


class TestResultsReport(object):
    """ A report of the results of executing the test suite with a simulation tool

    Attributes:
        test_suite_version (:obj:`str`): version of the test suite which was executed
        results (:obj:`list` of :obj:`TestCaseResult`): results of the test cases of the test suite
        gh_issue (:obj:`int`): GitHub issue for which the test suite was executed
        gh_action_run (:obj:`int`): GitHub action run in which the test suite was executed
    """

    def __init__(self, test_suite_version=__version__, results=None, gh_issue=None, gh_action_run=None):
        """
        Args:
            test_suite_version (:obj:`str`, optional): version of the test suite which was executed
            results (:obj:`list` of :obj:`TestCaseResult`, optional): results of the test cases of the test suite
            gh_issue (:obj:`int`, optional): GitHub issue for which the test suite was executed
            gh_action_run (:obj:`int`, optional): GitHub action run in which the test suite was executed
        """
        self.test_suite_version = test_suite_version
        self.results = results or []
        self.gh_issue = gh_issue
        self.gh_action_run = gh_action_run

    def to_dict(self, max_log_len=None):
        """ Generate a dictionary representation e.g., for export to JSON

        Args:
            max_log_len (:obj:`int`, optional): maximum log length

        Returns:
            :obj:`dict`: dictionary representation
        """
        return {
            'testSuiteVersion': self.test_suite_version,
            'results': [result.to_dict(max_log_len=max_log_len) for result in self.results],
            'ghIssue': self.gh_issue,
            'ghActionRun': self.gh_action_run,
        }
