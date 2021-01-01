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

        self.expected_dict_results = [{
            'case': {
                'id': 'sedml.SimulatorSupportsReports',
                'description': 'Test if simulator supports reports',
            },
            'type': 'failed',
            'duration': 1.5,
            'exception': {
                'type': 'NotImplementedError',
                'message': 'Not implemented',
            },
            'warnings': [
                {'type': 'TestCaseWarning', 'message': 'A first important warning'},
                {'type': 'TestCaseWarning', 'message': 'A second important warning'},
            ],
            'log': 'Long log',
        }]

        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_to_dict(self):
        self.assertEqual(self.results[0].to_dict(), self.expected_dict_results[0])

    def test_write_test_results(self):
        filename = os.path.join(self.dirname, 'results.json')
        write_test_results(self.results, filename)

        with open(filename, 'r') as file:
            results = json.load(file)

        self.assertEqual(results, self.expected_dict_results)
