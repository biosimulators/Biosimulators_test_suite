""" Program for validating that simulation tools are consistent with the BioSimulators standards

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-22
:Copyright: 2020, BioSimulators Team
:License: MIT
"""

from .data_model import OutputMedium
from .results.data_model import TestCaseResultType
from .results.io import write_test_results
from biosimulators_utils.config import Colors
import biosimulators_test_suite
import biosimulators_test_suite.exec_core
import cement
import termcolor


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = "Validates that a simulation tool is consistent with the BioSimulators standards"
        help = "Validates that a simulation tool is consistent with the BioSimulators standards"
        arguments = [
            (['specifications'], dict(
                type=str,
                help='Path or URL to the specifications of the simulator',
            )),
            (['-c', '--test-case'], dict(
                type=str,
                nargs='+',
                default=None,
                dest='case_ids',
                help=(
                    "Ids of test cases of evaluate (e.g., "
                      "'sedml.SimulatorSupportsModelAttributeChanges', "
                      "'published_project.SimulatorCanExecutePublishedProject:"
                      "sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations') "
                      "substrings of ids of test cases to evaluate (e.g., 'sedml.', 'published_project.' "
                      "to evaluate all SED-ML test cases or all test cases involving published projects). "
                      "Default: evaluate all test cases"
                ),
            )),
            (['--cli'], dict(
                default=None,
                help=("Command-line interface to use to execute the tests involving "
                      "the simulation of COMBINE/OMEX archives rather than a Docker image"),
            )),
            (['--synthetic-archives-dir'], dict(
                default=None,
                help="Directory to save the synthetic COMBINE/OMEX archives generated by the test cases",
            )),
            (['--report'], dict(
                default=None,
                help="Path to save a report of the results in JSON format",
            )),
            (['--verbose'], dict(
                action='store_true',
                help="If set, print the stdout and stderr of the execution of the tests in real time.",
            )),
            (['--work-dir'], dict(
                default=None,
                help=(
                    "Working directory for files for evaluating tests. This option enables intermediate files "
                    "to be inspected rather than automatically cleaned up."
                ),
            )),
            (['--do-not-validate-specs'], dict(
                action='store_true',
                help="If set, don't validate the specifications of the simulator.",
            )),
            (['--do-not-log-std-out-err'], dict(
                action='store_true',
                help="If set, don't use capturer to collect stdout and stderr.",
            )),
            (['--dry-run'], dict(
                action='store_true',
                help="If set, create synthetic archives, but do not use the simulator to execute them.",
            )),
            (['-v', '--version'], dict(
                action='version',
                version=biosimulators_test_suite.__version__,
            )),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        try:
            # execute tests
            validator = biosimulators_test_suite.exec_core.SimulatorValidator(
                args.specifications,
                case_ids=args.case_ids,
                verbose=args.verbose,
                synthetic_archives_dir=args.synthetic_archives_dir,
                output_medium=OutputMedium.console,
                log_std_out_err=not args.do_not_log_std_out_err,
                working_dirname=args.work_dir,
                dry_run=args.dry_run,
                cli=args.cli,
                validate_specs=not args.do_not_validate_specs)
            results = validator.run()

            # print summary
            summary, failure_details, warning_details, skipped_details = validator.summarize_results(results, debug=args.debug)
            print('')
            print('=============== SUMMARY ===============')
            print('')
            print(summary + '\n\n')
            if failure_details:
                color = Colors.failure.value
                print(termcolor.colored('=============== FAILURES ===============', color))
                print(termcolor.colored('', color))
                print(termcolor.colored('* ' + '\n\n* '.join(failure_details), color))
                print('')
            if warning_details:
                color = Colors.warning.value
                print(termcolor.colored('=============== WARNINGS ===============', color))
                print(termcolor.colored('', color))
                print(termcolor.colored('* ' + '\n\n* '.join(warning_details), color))
                print('')
            if skipped_details:
                color = Colors.skipped.value
                print(termcolor.colored('================ SKIPS =================', color))
                print(termcolor.colored('', color))
                print(termcolor.colored('* ' + '\n\n* '.join(skipped_details), color))
                print('')

            # optionally, save report of results to a JSON file
            if args.report:
                write_test_results(results, args.report)
        except Exception as exception:
            raise SystemExit(str(exception))

        any_passed = False
        failed = False
        for result in results:
            if result.type == TestCaseResultType.passed:
                any_passed = True
            elif result.type == TestCaseResultType.failed:
                failed = True

        if failed:
            exit(1)
        if not any_passed:
            exit(3)


class App(cement.App):
    """ Command line application """
    class Meta:
        label = 'biosimulators-test-suite'
        base_controller = 'base'
        handlers = [
            BaseController,
        ]


def main():
    with App() as app:
        app.run()
