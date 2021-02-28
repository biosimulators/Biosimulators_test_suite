from biosimulators_test_suite import __version__, exec_cli
from unittest import mock
import biosimulators_test_suite.data_model
import biosimulators_test_suite.exec_core
import biosimulators_test_suite.results.data_model
import biosimulators_test_suite.test_case.published_project
import biosimulators_test_suite.warnings
import json
import os
import shutil
import tempfile
import unittest


class MainTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_raw(self):
        with mock.patch('sys.argv', ['', '--help']):
            with self.assertRaises(SystemExit) as context:
                exec_cli.main()
                self.assertRegex(context.Exception, 'usage: ')

    def test_passes(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = [
            biosimulators_test_suite.results.data_model.TestCaseResult(
                case=biosimulators_test_suite.test_case.published_project.SimulatorCanExecutePublishedProject(
                    id='case-id',
                    task_requirements=[
                        biosimulators_test_suite.data_model.SedTaskRequirements(
                            model_format='format_2585',
                            simulation_algorithm='KISAO_000019',
                        )
                    ],
                ),
                type=biosimulators_test_suite.results.data_model.TestCaseResultType.passed,
                duration=1.,
            ),
        ]

        def find_cases(ids=None, results=results):
            return {'published_project': [result.case for result in results]}

        report_filename = os.path.join(self.dirname, 'results.json')
        with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                               'find_cases', side_effect=find_cases):
            with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                                   'eval_case', side_effect=results):
                with exec_cli.App(argv=[specs, '--report', report_filename]) as app:
                    app.run()

        with open(report_filename, 'rb') as file:
            results = json.load(file)

        self.assertEqual(results, {
            'testSuiteVersion': __version__,
            'results': [
                {
                    'case': {
                        'id': 'case-id',
                        'description': ('Required model formats and simulation algorithms for SED tasks:\n\n'
                                        '* Format: `format_2585`\n  Algorithm: `KISAO_000019`'),
                    },
                    'resultType': 'passed',
                    'duration': 1.,
                    'exception': None,
                    'warnings': [],
                    'skipReason': None,
                    'log': None,
                },
            ],
            'ghIssue': None,
            'ghActionRun': None,
        })

    def test_warnings(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = [
            biosimulators_test_suite.results.data_model.TestCaseResult(
                case=biosimulators_test_suite.test_case.published_project.SimulatorCanExecutePublishedProject(
                    id='case-id',
                    task_requirements=[
                        biosimulators_test_suite.data_model.SedTaskRequirements(
                            model_format='format_2585',
                            simulation_algorithm='KISAO_000019',
                        )
                    ],
                ),
                type=biosimulators_test_suite.results.data_model.TestCaseResultType.passed,
                duration=1.,
                warnings=[
                    mock.Mock(message=biosimulators_test_suite.warnings.TestCaseWarning('Warning-1')),
                    mock.Mock(message=biosimulators_test_suite.warnings.TestCaseWarning('Warning-2')),
                ],
            ),
        ]

        def find_cases(ids=None, results=results):
            return {'published_project': [result.case for result in results]}

        with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                               'find_cases', side_effect=find_cases):
            with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                                   'eval_case', side_effect=results):
                with exec_cli.App(argv=[specs]) as app:
                    app.run()

    def test_failed(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = [
            biosimulators_test_suite.results.data_model.TestCaseResult(
                case=biosimulators_test_suite.test_case.published_project.SimulatorCanExecutePublishedProject(
                    id='case-id',
                    task_requirements=[
                        biosimulators_test_suite.data_model.SedTaskRequirements(
                            model_format='format_2585',
                            simulation_algorithm='KISAO_000019',
                        )
                    ],
                ),
                type=biosimulators_test_suite.results.data_model.TestCaseResultType.failed,
                exception=Exception('Error'),
                log='Error',
                duration=1.,
            ),
        ]

        def find_cases(ids=None, results=results):
            return {'published_project': [result.case for result in results]}

        with self.assertRaises(SystemExit) as exception_cm:
            with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                                   'find_cases', side_effect=find_cases):
                with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                                       'eval_case', side_effect=results):
                    with exec_cli.App(argv=[specs]) as app:
                        app.run()
            self.assertEqual(exception_cm.exception.code, 1)

    def test_no_cases(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        results = []

        def find_cases(ids=None, results=results):
            return {'published_project': [result.case for result in results]}

        with self.assertRaises(SystemExit) as exception_cm:
            with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                                   'find_cases', side_effect=find_cases):
                with mock.patch.object(biosimulators_test_suite.exec_core.SimulatorValidator,
                                       'eval_case', side_effect=results):
                    with exec_cli.App(argv=[specs]) as app:
                        app.run()
            self.assertEqual(exception_cm.exception.code, 3)

    def test_specs_invalid(self):
        specs = 'invalid-url'

        with self.assertRaises(SystemExit) as exception_cm:
            with exec_cli.App(argv=[specs]) as app:
                app.run()
            self.assertEqual(exception_cm.exception.code, 2)

    def test_cases_dont_exist(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        with self.assertRaises(SystemExit) as exception_cm:
            with exec_cli.App(argv=[specs, '-c', 'adf']) as app:
                app.run()
            self.assertEqual(exception_cm.exception.code, 2)

    def test_exports_synthetic_archives(self):
        specs = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        synthetic_archives_dir = os.path.join(self.dirname, 'archives')
        with exec_cli.App(argv=[specs,
                                '-c', 'sedml.SimulatorSupportsMultipleReportsPerSedDocument',
                                '--synthetic-archives-dir', synthetic_archives_dir]) as app:
            app.run()

        self.assertEqual(os.listdir(synthetic_archives_dir),
                         ['sedml'])
        self.assertEqual(os.listdir(os.path.join(synthetic_archives_dir, 'sedml')),
                         ['SimulatorSupportsMultipleReportsPerSedDocument'])
        self.assertEqual(os.listdir(os.path.join(synthetic_archives_dir, 'sedml', 'SimulatorSupportsMultipleReportsPerSedDocument')),
                         ['1.execution-should-succeed.omex'])
