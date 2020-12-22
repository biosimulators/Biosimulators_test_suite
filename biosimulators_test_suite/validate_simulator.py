""" Utilities for validate containerized simulators

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import (AbstractTestCase, CombineArchiveTestCase, TestCaseResult,  # noqa: F401
                         TestCaseResultType, SkippedTestCaseException, IgnoreTestCaseWarning)
import biosimulators_utils.simulator.io
import datetime
import glob
import os
import warnings

__all__ = ['SimulatorValidator']


class SimulatorValidator(object):
    """ Validate that a Docker image for a simulator implements the BioSimulations simulator interface by
    checking that the image produces the correct outputs for one of more test cases (e.g., COMBINE archive)

    Attributes:
        cases (:obj:`list` of :obj:`TestCase`): test cases
    """

    def __init__(self, cases=None, combine_archive_case_ids=None):
        """
        Args:
            cases (:obj:`list` of :obj:`AbstractTestCase`, optional): test cases
            combine_archive_case_ids (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.
        """
        self.cases = cases or []
        self.cases.extend(self.get_combine_archive_cases(ids=combine_archive_case_ids))

    @staticmethod
    def get_combine_archive_cases(ids=None):
        """ Collect test cases from a directory

        Args:
            id (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.

        Returns:
            :obj:`list` of :obj:`CombineArchiveTestCase`: test cases
        """
        dirname = os.path.join(os.path.dirname(__file__), '..', 'examples')

        cases = []
        found_ids = set()
        ignored_ids = set()
        for md_filename in glob.glob(os.path.join(dirname, '**/*.json'), recursive=True):
            rel_filename = os.path.relpath(md_filename, dirname)
            id = os.path.splitext(rel_filename)[0]
            if ids is None or id in ids:
                found_ids.add(id)
                case = CombineArchiveTestCase().from_json(dirname, rel_filename)
                cases.append(case)
            else:
                ignored_ids.add(id)

        if ids is not None:
            missing_ids = set(ids).difference(found_ids)
            if missing_ids:
                raise ValueError('Some test case(s) were not found:\n  {}'.format('\n  '.join(sorted(missing_ids))))

        if ignored_ids:
            warnings.warn('Some test case(s) were ignored:\n  {}'.format('\n  '.join(sorted(ignored_ids))), IgnoreTestCaseWarning)

        # return cases
        return cases

    def run(self, specifications):
        """ Validate that a Docker image for a simulator implements the BioSimulations simulator interface by
        checking that the image produces the correct outputs for test cases (e.g., COMBINE archive)

        Args:
            specifications (:obj:`str` or :obj:`dict`): path or URL to the specifications of the simulator, or the specifications of the simulator

        Returns:
            :obj:`list` :obj:`TestCaseResult`: results of executing test cases
        """
        # if necessary, get and validate specifications of simulator
        if isinstance(specifications, str):
            specifications = biosimulators_utils.simulator.io.read_simulator_specs(specifications)

        # execute test cases and collect results
        results = []
        for case in self.cases:
            result = self.eval_case(specifications, case)
            results.append(result)

        # summarize results
        print(self.summarize_results(results))

        # return results
        return results

    def eval_case(self, specifications, case):
        """ Evaluate a test case for a simulator

        Args:
            specifications (:obj:`str` or :obj:`dict`): path or URL to the specifications of the simulator or the specifications of the simulator
            case (:obj:`TestCase`): test case

        Returns:
            :obj:`TestCaseResult`: test case result
        """
        start_time = datetime.datetime.now()
        try:
            case.eval(specifications)
            type = TestCaseResultType.passed
            exception = None
            duration = (datetime.datetime.now() - start_time).total_seconds()

        except SkippedTestCaseException:
            type = TestCaseResultType.skipped
            exception = None
            duration = None

        except Exception as caught_exception:
            type = TestCaseResultType.failed
            exception = caught_exception
            duration = (datetime.datetime.now() - start_time).total_seconds()

        return TestCaseResult(case=case, type=type, duration=duration, exception=exception)

    @staticmethod
    def summarize_results(results):
        """ Get a summary of the results of a set of test cases

        Args:
            results (:obj:`list` :obj:`TestCaseResult`): results of executing test cases

        Returns:
            :obj:`str`: summary of results of test cases
        """
        passed = []
        failed = []
        skipped = []
        for result in sorted(results, key=lambda result: result.case.id):
            if result.type == TestCaseResultType.passed:
                result_str = '  {} ({}, {:.3f} s)\n'.format(result.case.get_description(), result.case.id, result.duration)
                passed.append(result_str)

            elif result.type == TestCaseResultType.failed:
                result_str = '  {}: {} ({}, {:.3f} s)\n'.format(result.case.get_description(), result.case.id,
                                                                result.exception.__class__.__name__, result.duration)
                failed.append(result_str)

            elif result.type == TestCaseResultType.skipped:
                result_str = '  {}\n'.format(result.case.id)
                skipped.append(result_str)

        return '\n'.join([
            'Passed {} test cases:\n{}'.format(len(passed), ''.join(passed)),
            'Failed {} test cases:\n{}'.format(len(failed), ''.join(failed)),
            'Skipped {} test cases:\n{}'.format(len(skipped), ''.join(skipped)),
        ])
