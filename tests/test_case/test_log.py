from biosimulators_test_suite.exceptions import InvalidOutputsException, SkippedTestCaseException
from biosimulators_test_suite.test_case import log
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.warnings import TestCaseWarning
from biosimulators_utils.config import get_config
from biosimulators_utils.sedml.data_model import SedDocument, Task, Report
import numpy
import os
import pandas
import shutil
import tempfile
import unittest


class LogTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
    CURATED_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'sbml-core', 'Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint.omex')

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_SimulatorReportsTheStatusOfTheExecutionOfCombineArchives_eval_outputs(self):
        case = log.SimulatorReportsTheStatusOfTheExecutionOfCombineArchives()

        with self.assertRaisesRegex(SkippedTestCaseException, 'did not export information about the status'):
            self.assertEqual(case.eval_outputs(None, None, None, self.dirname), False)

        log_path = os.path.join(self.dirname, get_config().LOG_PATH)
        with open(log_path, 'w') as file:
            file.write('{"a": 2')
        with self.assertRaisesRegex(InvalidOutputsException, 'is not valid'):
            self.assertEqual(case.eval_outputs(None, None, None, self.dirname), False)

        with open(log_path, 'w') as file:
            file.write('status: RUNNING\n')
            file.write('sedDocuments:\n')
            file.write('  doc_1:\n')
        with self.assertRaisesRegex(InvalidOutputsException, 'is not valid'):
            self.assertEqual(case.eval_outputs(None, None, None, self.dirname), False)

        with open(log_path, 'w') as file:
            file.write('status: RUNNING\n')
            file.write('sedDocuments:\n')
            file.write('  - id: doc_1\n')
            file.write('    status: RUNNING\n')
            file.write('    tasks:\n')
            file.write('      - id: task_1\n')
            file.write('        status: RUNNING\n')
            file.write('    outputs:\n')
            file.write('      - id: output_1\n')
            file.write('        status: RUNNING\n')
            file.write('        dataSets:\n')
            file.write('          - id: data_set_1\n')
            file.write('            status: RUNNING\n')
            file.write('      - id: output_2\n')
            file.write('        status: RUNNING\n')
            file.write('        curves:\n')
            file.write('          - id curve_1\n')
            file.write('            status: RUNNING\n')
            file.write('      - id: output_3\n')
            file.write('        status: RUNNING\n')
        with self.assertRaisesRegex(InvalidOutputsException, 'is not valid'):
            self.assertEqual(case.eval_outputs(None, None, None, self.dirname), False)

        with open(log_path, 'w') as file:
            file.write('status: RUNNING\n')
            file.write('sedDocuments:\n')
            file.write('  - id: doc_1\n')
            file.write('    status: RUNNING\n')
            file.write('    tasks:\n')
            file.write('      - id: task_1\n')
            file.write('        status: RUNNING\n')
            file.write('    outputs:\n')
            file.write('      - id: output_1\n')
            file.write('        status: RUNNING\n')
            file.write('        dataSets:\n')
            file.write('          - id: data_set_1\n')
            file.write('            status: RUNNING\n')
            file.write('      - id: output_2\n')
            file.write('        status: RUNNING\n')
            file.write('        curves:\n')
            file.write('          - id: curve_1\n')
            file.write('            status: RUNNING\n')
            file.write('      - id: output_3\n')
            file.write('        status: RUNNING\n')
            file.write('        surfaces:\n')
            file.write('          - id: surface_1\n')
            file.write('            status: RUNNING\n')
        with self.assertRaisesRegex(InvalidOutputsException, 'is not valid. By the end of the execution'):
            self.assertEqual(case.eval_outputs(None, None, None, self.dirname), False)

    def test_SimulatorReportsTheStatusOfTheExecutionOfCombineArchives(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = log.SimulatorReportsTheStatusOfTheExecutionOfCombineArchives(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))
