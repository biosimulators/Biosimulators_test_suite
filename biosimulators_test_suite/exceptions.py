""" Common exceptions for test cases

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

__all__ = [
    'TestCaseException',
    'InvalidOutputsException',
    'SkippedTestCaseException',
    'TimeoutException',
]


class TestCaseException(Exception):
    """ Exception raised when outputs of execution of COMBINE/OMEX archive are not as expected """
    pass  # pragma: no cover


class InvalidOutputsException(TestCaseException):
    """ Exception raised when outputs of execution of COMBINE/OMEX archive are not as expected """
    pass  # pragma: no cover


class SkippedTestCaseException(TestCaseException):
    """ Exception raised that indicates that a test case should be skipped """
    pass  # pragma: no cover


class TimeoutException(TestCaseException):
    """ Exception raised that indicates that a test case timed out """
    pass  # pragma: no cover
