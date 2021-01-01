""" Methods for export test results

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-01
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import TestCaseResult  # noqa: F401
from .._version import __version__
import json

__all__ = ['build_test_results_report', 'write_test_results']


def build_test_results_report(results):
    """ Buid a report of the results of test cases

    Args:
        results (:obj:`list` of :obj:`TestCaseResult`): results of test cases

    Returns:
        :obj:`dict`: report of the results of test cases
    """
    return {
        'testSuiteVersion': __version__,
        'results': [result.to_dict() for result in results],
    }


def write_test_results(results, filename):
    """ Write the results of test cases to a JSON file

    Args:
        results (:obj:`list` of :obj:`TestCaseResult`): results of test cases
        filename (:obj:`str`): path to save results
    """
    report = build_test_results_report(results)
    with open(filename, 'w') as file:
        json.dump(report, file)
