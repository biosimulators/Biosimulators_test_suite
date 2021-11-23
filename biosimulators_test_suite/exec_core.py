""" Utilities for validate containerized simulators

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
from .data_model import TestCase, OutputMedium
from .exceptions import SkippedTestCaseException, TimeoutException
from .results.data_model import TestCaseResult, TestCaseResultType
from .test_case import cli
from .test_case import combine_archive
from .test_case import docker_image
from .test_case import log
from .test_case import published_project
from .test_case import results_report
from .test_case import sedml
from .warnings import TestCaseWarning, IgnoredTestCaseWarning
from biosimulators_utils.config import Colors
from biosimulators_utils.log.utils import StandardOutputErrorCapturer
import biosimulators_utils.simulator.io
import collections
import contextlib
import datetime
import inspect
import os
import shutil
import signal
import sys
import tempfile
import termcolor
import traceback
import warnings

__all__ = ['SimulatorValidator']


class SimulatorValidator(object):
    """ Validate that a Docker image for a simulator implements the BioSimulations simulator interface by
    checking that the image produces the correct outputs for one of more test cases (e.g., COMBINE archive)

    Attributes:
        specifications (:obj:`str` or :obj:`dict`): path or URL to the specifications of the simulator, or the specifications of the simulator
        cases (:obj:`collections.OrderedDict` of :obj:`types.ModuleType` to :obj:`TestCase`): groups of test cases
        verbose (:obj:`bool`): if :obj:`True`, display stdout/stderr from executing cases in real time
        synthetic_archives_dir (:obj:`str`): Directory to save the synthetic COMBINE/OMEX archives generated by the test cases
        output_medium (:obj:`OutputMedium`): environment where outputs will be sent
        log_std_out_err (:obj:`bool`): whether to log the standard output and error generated by each test case
        working_dirname (:obj:`str`): directory for temporary files for evaluating test case
        dry_run (:obj:`bool`): if :obj:`True`, do not use the simulator to execute COMBINE/OMEX archives.
        cli (:obj:`str`): command-line interface to use to execute the tests involving the simulation of COMBINE/OMEX
            archives rather than a Docker image
    """

    def __init__(self, specifications, case_ids=None, verbose=False, synthetic_archives_dir=None, output_medium=OutputMedium.console,
                 log_std_out_err=True, working_dirname=None, dry_run=False, cli=None, validate_specs=True):
        """
        Args:
            specifications (:obj:`str` or :obj:`dict`): path or URL to the specifications of the simulator, or the specifications of the simulator
            case_ids (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.
            verbose (:obj:`bool`, optional): if :obj:`True`, display stdout/stderr from executing cases in real time
            synthetic_archives_dir (:obj:`str`, optional): Directory to save the synthetic COMBINE/OMEX archives generated by the test cases
            output_medium (:obj:`OutputMedium`, optional): environment where outputs will be sent
            log_std_out_err (:obj:`bool`, optional): whether to log the standard output and error generated by each test case
            working_dirname (:obj:`str`, optional): directory for temporary files for evaluating test case
            dry_run (:obj:`bool`, optional): if :obj:`True`, do not use the simulator to execute COMBINE/OMEX archives.
            cli (:obj:`str`, optional): command-line interface to use to execute the tests involving the simulation of COMBINE/OMEX
                archives rather than a Docker image
            validate_specs (:obj:`bool`, optional): whether to validate specifications
        """
        # if necessary, get and validate specifications of simulator
        if isinstance(specifications, str):
            specifications = biosimulators_utils.simulator.io.read_simulator_specs(specifications, validate=validate_specs)

        self.specifications = specifications
        self.verbose = verbose
        if synthetic_archives_dir and not os.path.isdir(synthetic_archives_dir):
            os.makedirs(synthetic_archives_dir)
        self.synthetic_archives_dir = synthetic_archives_dir
        self.output_medium = output_medium
        self.log_std_out_err = log_std_out_err
        self.working_dirname = working_dirname
        self.dry_run = dry_run
        self.cli = cli

        self.cases = self.find_cases(ids=case_ids)

        self.test_case_timeout = Config().test_case_timeout

    def find_cases(self, ids=None):
        """ Find test cases

        Args:
            ids (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.

        Returns:
            :obj:`collections.OrderedDict` of :obj:`types.ModuleType` to :obj:`TestCase`: groups of test cases
        """
        cases = collections.OrderedDict()

        # get cases involving curated published COMBINE/OMEX archives
        all_published_projects_test_cases, compatible_published_projects_test_cases = published_project.find_cases(
            self.specifications, output_medium=self.output_medium)

        # get Docker image cases
        suite_name = docker_image.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = self.find_cases_in_module(docker_image, compatible_published_projects_test_cases, ids=ids)

        # get command-line interface cases
        suite_name = cli.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = self.find_cases_in_module(cli, compatible_published_projects_test_cases, ids=ids)

        # get COMBINE archive test cases
        suite_name = combine_archive.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = self.find_cases_in_module(combine_archive, compatible_published_projects_test_cases, ids=ids)

        # get SED-ML cases
        suite_name = sedml.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = self.find_cases_in_module(sedml, compatible_published_projects_test_cases, ids=ids)

        # get cases for reports of simulation results
        suite_name = results_report.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = self.find_cases_in_module(results_report, compatible_published_projects_test_cases, ids=ids)

        # get cases for reporting status of the execution of modeling projects
        suite_name = log.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = self.find_cases_in_module(log, compatible_published_projects_test_cases, ids=ids)

        # add cases involving published COMBINE/OMEX archives
        suite_name = published_project.__name__.replace('biosimulators_test_suite.test_case.', '')
        cases[suite_name] = []
        for case in all_published_projects_test_cases:
            if ids is None:
                cases[suite_name].append(case)
                break
            for id in ids:
                if id in case.id:
                    cases[suite_name].append(case)
                    break

        # warn if desired cases weren't found
        if ids is not None:
            found_case_ids = set()
            for suite_cases in cases.values():
                for case in suite_cases:
                    found_case_ids.add(case.id)

            missing_ids = set(ids).difference(found_case_ids)
            if missing_ids:
                warnings.warn('Some test case(s) were not found:\n  {}'.format('\n  '.join(sorted(missing_ids))), IgnoredTestCaseWarning)

        # return discovered cases
        return cases

    def find_cases_in_module(self, module, published_projects_test_cases, ids=None):
        """ Discover test cases in a module

        Args:
            module (:obj:`types.ModuleType`): module
            ids (:obj:`list` of :obj:`str`, optional): List of ids of test cases to verify. If :obj:`ids`
                is none, all test cases are verified.
            published_projects_test_cases (:obj:`list` of :obj:`published_project.SimulatorCanExecutePublishedProject`): test cases involving
                executing curated COMBINE/OMEX archives

        Returns:
            :obj:`list` of :obj:`TestCase`: test cases
        """
        cases = []
        ignored_ids = []
        module_name = module.__name__.replace('biosimulators_test_suite.test_case.', '')
        for child_name in dir(module):
            child = getattr(module, child_name)
            if (
                getattr(child, '__module__', None) == module.__name__
                and isinstance(child, type)
                and issubclass(child, TestCase)
                and not inspect.isabstract(child)
            ):
                case_id = module_name + '.' + child_name

                if ids is None:
                    use_case = True
                else:
                    use_case = False
                    for id in ids:
                        if id in case_id:
                            use_case = True
                            break

                if use_case:
                    description = child.__doc__ or None
                    if description:
                        description_lines = (description
                                             .replace('\r', '')
                                             .replace('\n    ', '\n')
                                             .partition('\n\n')[0]
                                             .strip()
                                             .split('\n'))
                        description = ' '.join(line.strip() for line in description_lines) or None
                    if issubclass(child, published_project.SyntheticCombineArchiveTestCase):
                        case = child(id=case_id, description=description, output_medium=self.output_medium,
                                     published_projects_test_cases=published_projects_test_cases)
                    else:
                        case = child(id=case_id, description=description, output_medium=self.output_medium)
                    cases.append(case)

                else:
                    ignored_ids.append(case_id)

        if ignored_ids:
            warnings.warn('Some test case(s) were ignored:\n  {}'.format('\n  '.join(sorted(ignored_ids))), IgnoredTestCaseWarning)

        cases.sort(key=lambda case: case.id)

        return cases

    def run(self):
        """ Validate that a Docker image for a simulator implements the BioSimulations simulator interface by
        checking that the image produces the correct outputs for test cases (e.g., COMBINE archive)

        Returns:
            :obj:`list` :obj:`TestCaseResult`: results of executing test cases
        """
        # print starting message
        n_cases = 0
        for suite_cases in self.cases.values():
            n_cases += len(suite_cases)
        print('Collected {} test cases.'.format(n_cases))

        # get start time
        start = datetime.datetime.now()

        # execute test cases and collect results
        results = []
        working_dirname = self.working_dirname or tempfile.mkdtemp()
        for suite_name, suite_cases in self.cases.items():
            print('\nExecuting {} {} tests ... {}'.format(len(suite_cases), suite_name, 'done' if not suite_cases else ''))
            for i_case, case in enumerate(suite_cases):
                print('  {}: {} ... '.format(i_case + 1, case.id), end='')
                sys.stdout.flush()

                result = self.eval_case(case, os.path.join(working_dirname, suite_name, case.id))
                results.append(result)

                print(termcolor.colored(result.type.value, Colors[result.type.value].value), end='')
                print(' (', end='')
                if result.warnings:
                    print(termcolor.colored(str(len(result.warnings)) + ' warnings, ', Colors.warned.value), end='')
                print('{:.1f} s'.format(result.duration), end='')
                print(').')

        if self.working_dirname is None:
            shutil.rmtree(working_dirname)

        # get total duration
        duration = (datetime.datetime.now() - start).total_seconds()

        # print completion message
        print('\n{} tests completed in {:.1f} s'.format(n_cases, duration))

        # return results
        return results

    def eval_case(self, case, working_dirname):
        """ Evaluate a test case for a simulator

        Args:
            case (:obj:`TestCase`): test case
            working_dirname (:obj:`str`): directory for temporary files for evaluating test case

        Returns:
            :obj:`TestCaseResult`: test case result
        """
        start_time = datetime.datetime.now()

        with StandardOutputErrorCapturer(relay=self.verbose, disabled=not self.log_std_out_err) as captured:
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("ignore")
                warnings.simplefilter("always", TestCaseWarning)

                try:

                    with time_limit(seconds=self.test_case_timeout):
                        case.eval(self.specifications,
                                  working_dirname,
                                  synthetic_archives_dir=self.synthetic_archives_dir,
                                  dry_run=self.dry_run,
                                  cli=self.cli)
                    type = TestCaseResultType.passed
                    exception = None
                    exception_traceback = None
                    skip_reason = None

                except SkippedTestCaseException as caught_exception:
                    type = TestCaseResultType.skipped
                    exception = None
                    exception_traceback = None
                    skip_reason = caught_exception

                except Exception as caught_exception:
                    type = TestCaseResultType.failed
                    exception = caught_exception
                    exception_traceback = sys.exc_info()[2]
                    skip_reason = None

                duration = (datetime.datetime.now() - start_time).total_seconds()

                return TestCaseResult(
                    case=case,
                    type=type,
                    duration=duration,
                    exception=exception,
                    exception_traceback=exception_traceback,
                    warnings=caught_warnings,
                    skip_reason=skip_reason,
                    log=captured.get_text())

    @staticmethod
    def summarize_results(results, debug=False, output_medium=OutputMedium.console):
        """ Get a summary of the results of a set of test cases

        Args:
            results (:obj:`list` :obj:`TestCaseResult`): results of executing test cases
            debug (:obj:`bool`, optional): whether to display traceback information about each error with
                additional information for debugging
            output_medium (:obj:`OutputMedium`, optional): environment where outputs will be sent

        Returns:
            :obj:`tuple`

                * :obj:`str`: summary of results of test cases
                * :obj:`list` of :obj:`str`: details of failures
                * :obj:`list` of :obj:`str`: details of warnings
                * :obj:`list` of :obj:`str`: details of skips
        """
        passed = []
        failed = []
        skipped = []
        warning_details = []
        failure_details = []
        skipped_details = []
        for result in sorted(results, key=lambda result: result.case.id):
            if result.type == TestCaseResultType.passed:
                result_str = '  * `{}`\n'.format(result.case.id)
                passed.append(result_str)

            elif result.type == TestCaseResultType.failed:
                result_str = '  * `{}`\n'.format(result.case.id)
                failed.append(result_str)

                detail = ''
                if output_medium == OutputMedium.gh_issue:
                    detail += '<details><summary><b><code>{}</code> ({:.1f} s)</b></summary>\n<br/>\n'.format(result.case.id, result.duration)
                else:
                    detail += '`{}` ({:.1f} s)\n'.format(result.case.id, result.duration)
                detail += '\n'
                if result.case.description:
                    detail += '  {}\n'.format(result.case.description.replace('\n', '\n  '))
                    detail += '\n'

                detail += '  Exception:\n'
                detail += '\n'
                detail += '  ```\n'
                detail += '  {}\n'.format(str(result.exception).replace('\n', '\n  '))
                if debug and result.exception_traceback:
                    detail += '\n'
                    detail += '  {}\n'.format('\n'.join(traceback.format_tb(result.exception_traceback)).replace('\n', '\n  '))
                detail += '  ```\n'
                detail += '\n'

                if result.log:
                    detail += '  Log:\n'
                    detail += '\n'
                    detail += '  ```\n'
                    detail += '  {}\n'.format(result.log.replace('\n', '\n  '))
                    detail += '  ```'
                else:
                    detail += '  Log: None'

                if output_medium == OutputMedium.gh_issue:
                    detail += '\n</details>'

                failure_details.append(detail)

            elif result.type == TestCaseResultType.skipped:
                result_str = '  * `{}`\n'.format(result.case.id)
                skipped.append(result_str)

                detail = ''
                if output_medium == OutputMedium.gh_issue:
                    detail += '<details><summary><b><code>{}</code> ({:.1f} s)</b></summary>\n<br/>\n'.format(result.case.id, result.duration)
                else:
                    detail += '`{}` ({:.1f} s)\n'.format(result.case.id, result.duration)
                detail += '\n'
                if result.case.description:
                    detail += '  {}\n'.format(result.case.description.replace('\n', '\n  '))
                    detail += '\n'

                detail += '  Reason for skip:\n'
                detail += '\n'
                detail += '  ```\n'
                detail += '  {}\n'.format(str(result.skip_reason).replace('\n', '\n  '))
                detail += '  ```\n'
                detail += '\n'

                if result.warnings:
                    detail += '  Warnings:\n'
                    for warning in result.warnings:
                        detail += '\n'
                        detail += '  ```\n'
                        detail += '  {}\n'.format(str(warning.message).replace('\n', '\n  '))
                        detail += '  ```\n'
                    detail += '\n'

                if result.log:
                    detail += '  Log:\n'
                    detail += '\n'
                    detail += '  ```\n'
                    detail += '  {}\n'.format(result.log.replace('\n', '\n  '))
                    detail += '  ```'
                else:
                    detail += '  Log: None\n'

                if output_medium == OutputMedium.gh_issue:
                    detail += '\n</details>'

                skipped_details.append(detail)

            if result.warnings:
                detail = ''
                if output_medium == OutputMedium.gh_issue:
                    detail += '<details><summary><b><code>{}</code> ({:.1f} s)</b></summary>\n<br/>\n'.format(result.case.id, result.duration)
                else:
                    detail += '`{}` ({:.1f} s)\n'.format(result.case.id, result.duration)
                detail += '\n'
                if result.case.description:
                    detail += '  {}\n'.format(result.case.description.replace('\n', '\n  '))
                    detail += '\n'

                detail += '  Warnings:\n'
                for warning in result.warnings:
                    detail += '\n'
                    detail += '  ```\n'
                    detail += '  {}\n'.format(str(warning.message).replace('\n', '\n  '))
                    detail += '  ```\n'
                detail += '\n'

                if result.log:
                    detail += '  Log:\n'
                    detail += '\n'
                    detail += '  ```\n'
                    detail += '  {}\n'.format(result.log.replace('\n', '\n  '))
                    detail += '  ```'
                else:
                    detail += '  Log: None'

                if output_medium == OutputMedium.gh_issue:
                    detail += '\n</details>'

                warning_details.append(detail)

        return (
            '\n'.join([
                '* Executed {} test cases\n'.format(len(results)),
                '* Passed {} test cases{}\n{}'.format(len(passed), ':' if passed else '', ''.join(passed)),
                '* Failed {} test cases{}\n{}'.format(len(failed), ':' if failed else '', ''.join(failed)),
                '* Skipped {} test cases{}\n{}'.format(len(skipped), ':' if skipped else '', ''.join(skipped)),
            ]).strip(),
            failure_details,
            warning_details,
            skipped_details,
        )


@contextlib.contextmanager
def time_limit(seconds):
    """ Context manager for timing out long operations

    Args:
        seconds (:obj:`int`): length in seconds before time out

    Raises:
        :obj:`TimeoutException`: if the operation timed out
    """
    def signal_handler(signum, frame):
        raise TimeoutException("Operation did not complete within {} seconds".format(seconds))
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(int(seconds))
    try:
        yield
    finally:
        signal.alarm(0)
