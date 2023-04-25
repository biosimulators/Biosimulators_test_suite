from biosimulators_test_suite.data_model import OutputMedium
from biosimulators_test_suite.results.data_model import TestCaseResultType
from biosimulators_utils.config import Colors
import biosimulators_test_suite.exec_core
import termcolor

try:
    # execute tests
    validator = biosimulators_test_suite.exec_core.SimulatorValidator(
        "/Biosimulators/BSTS/specs/vcell.specs",
        case_ids=None,
        verbose=False,
        # synthetic_archives_dir=args.synthetic_archives_dir,
        output_medium=OutputMedium.console,
        log_std_out_err=True)
    results = validator.run()

    # print summary
    summary, failure_details, warning_details, skipped_details = validator.summarize_results(results, True)
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
    # if args.report:
    #     write_test_results(results, args.report)
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
