""" Program for validating that simulation tools are consistent with the BioSimulators standards

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-22
:Copyright: 2020, BioSimulators Team
:License: MIT
"""

from .config import TERMINAL_COLORS
from .data_model import OutputMedium
from .results.data_model import TestCaseResultType
from .results.io import write_test_results
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
            (['-c', '--combine-case'], dict(
                type=str,
                nargs='+',
                default=None,
                dest='case_ids',
                help=(
                    "Ids of test cases of evaluate (e.g., "
                      "'sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations'). "
                      "Default: evaluate all test cases"
                ),
            )),
            (['-o', '--report'], dict(
                default=None,
                help="Path to save a report of the results in JSON format",
            )),
            (['--verbose'], dict(
                action='store_true',
                help="If set, print the stdout and stderr of the execution of the tests in real time.",
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
                output_medium=OutputMedium.console)
            results = validator.run()

            # print summary
            summary, failure_details, warning_details = validator.summarize_results(results)
            print('')
            print('=============== SUMMARY ===============')
            print('')
            print(summary + '\n\n')
            if failure_details:
                color = TERMINAL_COLORS['failure']
                print(termcolor.colored('=============== FAILURES ===============', color))
                print(termcolor.colored('', color))
                print(termcolor.colored('* ' + '\n\n* '.join(failure_details), color))
                print('')
            if warning_details:
                color = TERMINAL_COLORS['warning']
                print(termcolor.colored('=============== WARNINGS ===============', color))
                print(termcolor.colored('', color))
                print(termcolor.colored('* ' + '\n\n* '.join(warning_details), color))
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
