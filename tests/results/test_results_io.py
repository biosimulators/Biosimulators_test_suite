from biosimulators_test_suite import __version__
from biosimulators_test_suite.data_model import TestCase
from biosimulators_test_suite.results.data_model import TestCaseResult, TestCaseResultType
from biosimulators_test_suite.results.io import write_test_results
from biosimulators_test_suite.warnings import TestCaseWarning
import json
import os
import shutil
import tempfile
import unittest
import warnings


class ResultsIoTestCase(unittest.TestCase):
    def setUp(self):
        class ConcreteTestCase(TestCase):
            def eval():
                pass

        try:
            raise NotImplementedError('Not implemented')
        except Exception as ex:
            exception = ex

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("ignore")
            warnings.simplefilter("always", TestCaseWarning)
            warnings.warn('A first important warning', TestCaseWarning)
            warnings.warn('A second important warning', TestCaseWarning)

        result = TestCaseResult(
            case=ConcreteTestCase(id='sedml.SimulatorSupportsReports', description='Test if simulator supports reports'),
            type=TestCaseResultType.failed,
            duration=1.5,
            exception=exception,
            warnings=caught_warnings,
            log='Long log',
        )
        self.results = [result]

        self.expected_results_report = {
            'testSuiteVersion': __version__,
            'results': [{
                'case': {
                    'id': 'sedml.SimulatorSupportsReports',
                    'description': 'Test if simulator supports reports',
                },
                'resultType': 'failed',
                'duration': 1.5,
                'exception': {
                    'category': 'NotImplementedError',
                    'message': 'Not implemented',
                    'traceback': None,
                },
                'warnings': [
                    {'category': 'TestCaseWarning', 'message': 'A first important warning'},
                    {'category': 'TestCaseWarning', 'message': 'A second important warning'},
                ],
                'skipReason': None,
                'log': 'Long log',
            }],
            'ghIssue': None,
            'ghActionRun': None,
        }

        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_to_dict(self):
        self.assertEqual(self.results[0].to_dict(), self.expected_results_report['results'][0])

    def test_write_test_results(self):
        filename = os.path.join(self.dirname, 'results.json')
        write_test_results(self.results, filename)

        with open(filename, 'r') as file:
            results = json.load(file)

        self.assertEqual(results, self.expected_results_report)
