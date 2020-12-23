from biosimulators_test_suite import __main__
from unittest import mock
import biosimulators_test_suite.data_model
import biosimulators_test_suite.validate_simulator
import unittest


class MainTestCase(unittest.TestCase):
    def test_raw(self):
        with mock.patch('sys.argv', ['', '--help']):
            with self.assertRaises(SystemExit) as context:
                __main__.main()
                self.assertRegex(context.Exception, 'usage: ')

    def test_passes(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = [
            biosimulators_test_suite.data_model.TestCaseResult(
                case=biosimulators_test_suite.data_model.CombineArchiveTestCase(
                    id='case-id',
                    task_requirements=[
                        biosimulators_test_suite.data_model.SedTaskRequirements(
                            model_format='format_2585',
                            simulation_algorithm='KISAO_000019',
                        )
                    ],
                ),
                type=biosimulators_test_suite.data_model.TestCaseResultType.passed,
                duration=1.,
            ),
        ]

        def get_combine_archive_cases(ids=None, results=results):
            return [result.case for result in results]

        with mock.patch.object(biosimulators_test_suite.validate_simulator.SimulatorValidator,
                               'get_combine_archive_cases', side_effect=get_combine_archive_cases):
            with mock.patch.object(biosimulators_test_suite.validate_simulator.SimulatorValidator,
                                   'eval_case', side_effect=results):
                with __main__.App(argv=[specs]) as app:
                    app.run()

    def test_failed(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = [
            biosimulators_test_suite.data_model.TestCaseResult(
                case=biosimulators_test_suite.data_model.CombineArchiveTestCase(
                    id='case-id',
                    task_requirements=[
                        biosimulators_test_suite.data_model.SedTaskRequirements(
                            model_format='format_2585',
                            simulation_algorithm='KISAO_000019',
                        )
                    ],
                ),
                type=biosimulators_test_suite.data_model.TestCaseResultType.failed,
                exception=Exception('Error'),
                log='Error',
                duration=1.,
            ),
        ]

        def get_combine_archive_cases(ids=None, results=results):
            return [result.case for result in results]

        with self.assertRaises(SystemExit) as exception_cm:
            with mock.patch.object(biosimulators_test_suite.validate_simulator.SimulatorValidator,
                                   'get_combine_archive_cases', side_effect=get_combine_archive_cases):
                with mock.patch.object(biosimulators_test_suite.validate_simulator.SimulatorValidator,
                                       'eval_case', side_effect=results):
                    with __main__.App(argv=[specs]) as app:
                        app.run()
            self.assertEqual(exception_cm.exception.code, 1)

    def test_no_cases(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = []

        def get_combine_archive_cases(ids=None, results=results):
            return [result.case for result in results]

        with self.assertRaises(SystemExit) as exception_cm:
            with mock.patch.object(biosimulators_test_suite.validate_simulator.SimulatorValidator,
                                   'get_combine_archive_cases', side_effect=get_combine_archive_cases):
                with mock.patch.object(biosimulators_test_suite.validate_simulator.SimulatorValidator,
                                       'eval_case', side_effect=results):
                    with __main__.App(argv=[specs]) as app:
                        app.run()
            self.assertEqual(exception_cm.exception.code, 3)

    def test_specs_invalid(self):
        specs = 'invalid-url'

        results = []

        with self.assertRaises(SystemExit) as exception_cm:
            with __main__.App(argv=[specs]) as app:
                app.run()
            self.assertEqual(exception_cm.exception.code, 2)

    def test_cases_dont_exist(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = []

        with self.assertRaises(SystemExit) as exception_cm:
            with __main__.App(argv=[specs, '-c', 'adf']) as app:
                app.run()
            self.assertEqual(exception_cm.exception.code, 2)
