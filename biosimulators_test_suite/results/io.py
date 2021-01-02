""" Methods for export test results

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-01
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import TestCaseResult, TestResultsReport  # noqa: F401
import json

__all__ = ['write_test_results']


def write_test_results(results, filename):
    """ Write the results of test cases to a JSON file

    Args:
        results (:obj:`list` of :obj:`TestCaseResult`): results of test cases
        filename (:obj:`str`): path to save results
    """
    report = TestResultsReport(results=results)
    with open(filename, 'w') as file:
        json.dump(report.to_dict(), file)
