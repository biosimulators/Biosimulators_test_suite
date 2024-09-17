""" Common warnings for test cases

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

__all__ = [
    'TestCaseWarning',
    'IgnoredTestCaseWarning',
    'SimulatorRuntimeErrorWarning',
    'InvalidOutputsWarning',
]


class TestCaseWarning(UserWarning):
    """ Base class for warnings collected from test cases """
    pass


class SimulatorRuntimeErrorWarning(TestCaseWarning, RuntimeWarning):
    """ Warning that the execution of a test case failed """
    pass  # pragma: no co


class IgnoredTestCaseWarning(TestCaseWarning):
    """ Warning that a test case was ignored """
    pass  # pragma: no cover


class InvalidOutputsWarning(TestCaseWarning):
    """ Warning that the outputs of the execution of a COMBINE/OMEX archive were not as expected """
    pass  # pragma: no cover
