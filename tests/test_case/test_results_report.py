from biosimulators_test_suite.test_case import results_report
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.warnings import TestCaseWarning
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import SedDocument, Report, DataSet
import numpy
import os
import pandas
import shutil
import tempfile
import unittest


class CombineArchiveTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
    CURATED_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'sbml-core', 'Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint.omex')

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_SimulatorGeneratesReportsOfSimultionResults_eval_outputs(self):
        case = results_report.SimulatorGeneratesReportsOfSimultionResults()

        with self.assertRaisesRegex(ValueError, 'Simulator must generate reports'):
            case.eval_outputs(None, None, None, self.dirname)

        doc = SedDocument(
            outputs=[
                Report(
                    id='report_1',
                    data_sets=[
                        DataSet(label='A'),
                        DataSet(label='B'),
                    ],
                )
            ],
        )
        synthetic_sed_docs = {'test.sedml': doc}

        data = numpy.array([[1., 2., 3.], [4., 5., 6.]])
        data_frame = pandas.DataFrame(data, index=['A', 'C'])

        ReportWriter().run(data_frame, self.dirname, os.path.join('test.sedml', 'report_1'))
        with self.assertRaisesRegex(ValueError, 'did not produce'):
            case.eval_outputs(None, None, synthetic_sed_docs, self.dirname)

        data = numpy.array([[1., 2., 3.], [4., 5., 6.], [7., 8., numpy.nan]])
        data_frame = pandas.DataFrame(data, index=['A', 'B', 'C'])
        ReportWriter().run(data_frame, self.dirname, os.path.join('test.sedml', 'report_1'))
        with self.assertWarnsRegex(TestCaseWarning, 'produced the following extra'):
            self.assertEqual(case.eval_outputs(None, None, synthetic_sed_docs, self.dirname), False)
        with self.assertWarnsRegex(TestCaseWarning, 'include `NaN`'):
            self.assertEqual(case.eval_outputs(None, None, synthetic_sed_docs, self.dirname), False)

        data = numpy.array([[1., 2., 3.], [4., 5., 6.]])
        data_frame = pandas.DataFrame(data, index=['A', 'B'])
        ReportWriter().run(data_frame, self.dirname, os.path.join('test.sedml', 'report_1'))
        self.assertEqual(case.eval_outputs(None, None, synthetic_sed_docs, self.dirname), True)

    def test_SimulatorGeneratesReportsOfSimultionResults(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = results_report.SimulatorGeneratesReportsOfSimultionResults(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))
