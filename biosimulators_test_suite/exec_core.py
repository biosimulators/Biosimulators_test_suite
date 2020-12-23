""" Utilities for validate containerized simulators

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import (AbstractTestCase, TestCaseResult,  # noqa: F401
                         TestCaseResultType, SkippedTestCaseException, IgnoreTestCaseWarning)
from .test_case.combine_archive import CuratedCombineArchiveTestCase
import biosimulators_utils.simulator.io
import capturer
import datetime
import sys
import warnings

__all__ = ['SimulatorValidator']


class SimulatorValidator(object):
    """ Validate that a Docker image for a simulator implements the BioSimulations simulator interface by
    checking that the image produces the correct outputs for one of more test cases (e.g., COMBINE archive)

    Attributes:
        cases (:obj:`list` of :obj:`AbstractTestCase`): test cases
        verbose (:obj:`bool`): if :obj:`True`, display stdout/stderr from executing cases in real time
    """

    def __init__(self, case_ids=None, verbose=False):
        """
        Args:
            case_ids (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.
            verbose (:obj:`bool`, optional): if :obj:`True`, display stdout/stderr from executing cases in real time
        """
        self.cases = self.find_cases(ids=case_ids)
        self.verbose = verbose

    @classmethod
    def find_cases(cls, ids=None):
        """ Find test cases

        Args:
            ids (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.

        Returns:
            :obj:`list` of :obj:`AbstractTestCase`: test cases
        """
        cases = CuratedCombineArchiveTestCase.find_cases(ids=ids)

        if ids is not None:
            missing_ids = set(ids).difference(set(case.id for case in cases))
            if missing_ids:
                warnings.warn('Some test case(s) were not found:\n  {}'.format('\n  '.join(sorted(missing_ids))), IgnoreTestCaseWarning)

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
        print('Collected {} test cases ...'.format(len(self.cases)))
        for i_case, case in enumerate(self.cases):
            print('Executing case {}: {} ...'.format(i_case + 1, case.id), end='')
            sys.stdout.flush()
            result = self.eval_case(specifications, case)
            results.append(result)
            print(' {} ({}).'.format(result.type.value, result.duration))
        print()

        # return results
        return results

    def eval_case(self, specifications, case):
        """ Evaluate a test case for a simulator

        Args:
            specifications (:obj:`str` or :obj:`dict`): path or URL to the specifications of the simulator or the specifications of the simulator
            case (:obj:`AbstractTestCase`): test case

        Returns:
            :obj:`TestCaseResult`: test case result
        """
        start_time = datetime.datetime.now()
        with capturer.CaptureOutput(merged=True, relay=self.verbose) as captured:
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

            return TestCaseResult(case=case, type=type, duration=duration, exception=exception, log=captured.get_text())

    @staticmethod
    def summarize_results(results):
        """ Get a summary of the results of a set of test cases

        Args:
            results (:obj:`list` :obj:`TestCaseResult`): results of executing test cases

        Returns:
            :obj:`tuple` of :obj:`str`: summary of results of test cases and details of failures
        """
        passed = []
        failed = []
        skipped = []
        failure_details = []
        for result in sorted(results, key=lambda result: result.case.id):
            if result.type == TestCaseResultType.passed:
                result_str = '  * {} ({}, {:.3f} s)\n'.format(result.case.get_description(), result.case.id, result.duration)
                passed.append(result_str)

            elif result.type == TestCaseResultType.failed:
                result_str = '* {}: {} ({}, {:.3f} s)\n'.format(result.case.get_description(), result.case.id,
                                                                result.exception.__class__.__name__, result.duration)
                failed.append('  ' + result_str)
                failure_details.append(result_str + '    ```\n    {}\n\n    {}\n    ```\n'.format(
                    str(result.exception).replace('\n', '\n    '),
                    result.log.replace('\n', '\n    ')))

            elif result.type == TestCaseResultType.skipped:
                result_str = '  * {}\n'.format(result.case.id)
                skipped.append(result_str)

        return (
            '\n'.join([
                '* Executed {} test cases\n'.format(len(results)),
                '* Passed {} test cases{}\n{}'.format(len(passed), ':' if passed else '', ''.join(passed)),
                '* Failed {} test cases{}\n{}'.format(len(failed), ':' if failed else '', ''.join(failed)),
                '* Skipped {} test cases{}\n{}'.format(len(skipped), ':' if skipped else '', ''.join(skipped)),
            ]),
            '\n'.join(failure_details),
        )
