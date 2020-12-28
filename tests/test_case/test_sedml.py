from biosimulators_test_suite.data_model import IgnoredTestCaseWarning
from biosimulators_test_suite.test_case import sedml
from biosimulators_test_suite.test_case.published_project import PublishedProjectTestCase
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import SedDocument, Task, Report
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

    def test_MultipleTasksPerSedDocumentTestCase_get_suitable_sed_doc(self):
        self.assertEqual(sedml.MultipleTasksPerSedDocumentTestCase.get_suitable_sed_doc({
            'loc': SedDocument(),
        }), None)

        self.assertEqual(sedml.MultipleTasksPerSedDocumentTestCase.get_suitable_sed_doc({
            'loc-1': SedDocument(),
            'loc-2': SedDocument(tasks=[Task()], outputs=[Report()]),
        }), 'loc-2')

        self.assertEqual(sedml.MultipleTasksPerSedDocumentTestCase.get_suitable_sed_doc({
            'loc-1': SedDocument(tasks=[Task()]),
            'loc-2': SedDocument(tasks=[Task()], outputs=[Report()]),
        }), 'loc-2')

        self.assertEqual(sedml.MultipleTasksPerSedDocumentTestCase.get_suitable_sed_doc({
            'loc-1': SedDocument(outputs=[Report()]),
            'loc-2': SedDocument(tasks=[Task()], outputs=[Report()]),
        }), 'loc-2')

    def test_MultipleTasksPerSedDocumentTestCase_eval_outputs(self):
        case = sedml.MultipleTasksPerSedDocumentTestCase()
        case._expected_reports = [
            ('a.sedml/b', 'a.sedml/b'),
        ]

        with self.assertRaisesRegex(ValueError, 'were not generated'):
            case.eval_outputs(None, None, self.dirname)

        data_frame = pandas.DataFrame(numpy.array([[1, 2, 3], [4, 5, 6]]), index=['A', 'B'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/b')
        case.eval_outputs(None, None, self.dirname)

    def test_MultipleTasksPerSedDocumentTestCase(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = PublishedProjectTestCase(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.MultipleTasksPerSedDocumentTestCase(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

        # no curated cases to use
        case = sedml.MultipleTasksPerSedDocumentTestCase(
            published_projects_test_cases=[])
        with self.assertWarnsRegex(IgnoredTestCaseWarning, 'No curated COMBINE/OMEX archives are available'):
            case.eval(specs)
