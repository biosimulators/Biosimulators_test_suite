from biosimulators_test_suite.test_case import results_report
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.warnings import TestCaseWarning
from biosimulators_utils.report.data_model import DataSetResults
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import SedDocument, Report, DataSet
import numpy
import os
import shutil
import tempfile
import unittest


class CombineArchiveTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
    CURATED_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'sbml-core', 'Tomida-EMBO-J-2003-NFAT-translocation.omex')

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_SimulatorGeneratesReportsOfSimulationResults_eval_outputs(self):
        case = results_report.SimulatorGeneratesReportsOfSimulationResults()

        with self.assertRaisesRegex(ValueError, 'Simulator must generate reports'):
            case.eval_outputs(None, None, None, self.dirname)

        doc = SedDocument(
            outputs=[
                Report(
                    id='report_1',
                    data_sets=[
                        DataSet(id='A', label='A'),
                        DataSet(id='B', label='B'),
                    ],
                )
            ],
        )
        synthetic_sed_docs = {'test.sedml': doc}

        report = Report(id='report', data_sets=[DataSet(id='A', label='A'), DataSet(id='C', label='C')])
        data_set_results = DataSetResults({
            'A': numpy.array([1., 2., 3.]),
            'C': numpy.array([4., 5., 6.]),
        })
        ReportWriter().run(report, data_set_results, self.dirname, os.path.join('test.sedml', 'report_1'))
        with self.assertRaisesRegex(ValueError, 'did not produce'):
            case.eval_outputs(None, None, synthetic_sed_docs, self.dirname)

        report = Report(id='report', data_sets=[DataSet(id='A', label='A'), DataSet(id='B', label='B'), DataSet(id='C', label='C')])
        data_set_results = DataSetResults({
            'A': numpy.array([1., 2., 3.]),
            'B': numpy.array([4., 5., numpy.nan]),
            'C': numpy.array([7., 8., numpy.nan]),
        })
        ReportWriter().run(report, data_set_results, self.dirname, os.path.join('test.sedml', 'report_1'))
        with self.assertWarnsRegex(TestCaseWarning, 'include `NaN`'):
            self.assertEqual(case.eval_outputs(None, None, synthetic_sed_docs, self.dirname), False)

        report = Report(id='report', data_sets=[DataSet(id='A', label='A'), DataSet(id='B', label='B')])
        data_set_results = DataSetResults({
            'A': numpy.array([1., 2., 3.]),
            'B': numpy.array([4., 5., 6.]),
        })
        ReportWriter().run(report, data_set_results, self.dirname, os.path.join('test.sedml', 'report_1'))
        self.assertEqual(case.eval_outputs(None, None, synthetic_sed_docs, self.dirname), True)

    def test_SimulatorGeneratesReportsOfSimulationResults(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = results_report.SimulatorGeneratesReportsOfSimulationResults(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))
