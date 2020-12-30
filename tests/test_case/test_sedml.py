from biosimulators_test_suite.exceptions import InvalidOuputsException
from biosimulators_test_suite.test_case import sedml
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.warnings import IgnoredTestCaseWarning, InvalidOuputsWarning
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import SedDocument, Task, Report, DataSet
import numpy
import os
import pandas
import shutil
import tempfile
import unittest


class SedmlTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
    CURATED_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'sbml-core', 'Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint.omex')

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports_eval_outputs(self):
        case = sedml.SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports()

        doc = SedDocument(
            outputs=[
                Report(
                    id='b',
                    data_sets=[
                        DataSet(label='x'),
                        DataSet(label='y'),
                    ],
                ),
            ],
        )

        with self.assertRaisesRegex(InvalidOuputsException, 'did not produce the following reports'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_frame = pandas.DataFrame(numpy.array([[1, 2, 3]]), index=['x'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/b')
        with self.assertRaisesRegex(InvalidOuputsException, 'did not produce the following data sets'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_frame = pandas.DataFrame(numpy.array([[1, 2, 3], [4, 5, 6]]), index=['x', 'y'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/b')
        self.assertTrue(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

        data_frame = pandas.DataFrame(numpy.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), index=['x', 'y', 'z'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/b')
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/c')
        with self.assertWarnsRegex(InvalidOuputsWarning, 'extra reports'):
            self.assertFalse(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))
        with self.assertWarnsRegex(InvalidOuputsWarning, 'extra data sets'):
            self.assertFalse(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

    def test_SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))

    def test_SimulatorSupportsMultipleTasksPerSedDocument_get_suitable_sed_doc(self):
        self.assertEqual(sedml.SimulatorSupportsMultipleTasksPerSedDocument.get_suitable_sed_doc({
            'loc': SedDocument(),
        }), None)

        self.assertEqual(sedml.SimulatorSupportsMultipleTasksPerSedDocument.get_suitable_sed_doc({
            'loc-1': SedDocument(),
            'loc-2': SedDocument(tasks=[Task()], outputs=[Report()]),
        }), 'loc-2')

        self.assertEqual(sedml.SimulatorSupportsMultipleTasksPerSedDocument.get_suitable_sed_doc({
            'loc-1': SedDocument(tasks=[Task()]),
            'loc-2': SedDocument(tasks=[Task()], outputs=[Report()]),
        }), 'loc-2')

        self.assertEqual(sedml.SimulatorSupportsMultipleTasksPerSedDocument.get_suitable_sed_doc({
            'loc-1': SedDocument(outputs=[Report()]),
            'loc-2': SedDocument(tasks=[Task()], outputs=[Report()]),
        }), 'loc-2')

    def test_SimulatorSupportsMultipleTasksPerSedDocument_eval_outputs(self):
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument()
        case._expected_reports = [
            ('a.sedml/b', 'a.sedml/b'),
        ]

        with self.assertRaisesRegex(ValueError, 'were not generated'):
            case.eval_outputs(None, None, None, self.dirname)

        data_frame = pandas.DataFrame(numpy.array([[1, 2, 3], [4, 5, 6]]), index=['A', 'B'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/b')
        case.eval_outputs(None, None, None, self.dirname)

    def test_SimulatorSupportsMultipleTasksPerSedDocument(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

        # no curated cases to use
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument(
            published_projects_test_cases=[])
        with self.assertWarnsRegex(IgnoredTestCaseWarning, 'No curated COMBINE/OMEX archives are available'):
            case.eval(specs)
