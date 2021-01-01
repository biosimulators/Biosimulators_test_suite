""" Data model for results of test cases

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-01
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..warnings import TestCaseWarning  # noqa: F401
import enum

__all__ = [
    'TestCaseResultType',
    'TestCaseResult',
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
        warnings (:obj:`list` of :obj:`TestCaseWarning`): warnings
        log (:obj:`str`): log of execution
    """

    def __init__(self, case=None, type=None, duration=None, exception=None, warnings=None, log=None):
        """
        Args:
            case (:obj:`TestCase`, optional): test case
            type (:obj:`obj:`TestCaseResultType`, optional): type
            duration (:obj:`float`, optional): execution duration in seconds
            exception (:obj:`Exception`, optional): exception
            warnings (:obj:`list` of :obj:`TestCaseWarning`): warnings
            log (:obj:`str`, optional): log of execution
        """
        self.case = case
        self.type = type
        self.duration = duration
        self.exception = exception
        self.warnings = warnings or []
        self.log = log

    def to_dict(self):
        """ Generate a dictionary representation e.g., for export to JSON

        Returns:
            :obj:`dict`: dictionary representation
        """
        return {
            'case': {
                'id': self.case.id,
                'description': self.case.description,
            },
            'type': self.type.value,
            'duration': self.duration,
            'exception': {
                'type': self.exception.__class__.__name__,
                'message': str(self.exception),
            } if self.exception else None,
            'warnings': [{'type': warning.category.__name__, 'message': str(warning.message)}
                         for warning in self.warnings],
            'log': self.log,
        }
