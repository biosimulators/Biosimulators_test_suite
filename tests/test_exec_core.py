from biosimulators_test_suite.exec_core import SimulatorValidator
from biosimulators_test_suite.data_model import TestCase, SedTaskRequirements
from biosimulators_test_suite.exceptions import SkippedTestCaseException
from biosimulators_test_suite.results.data_model import TestCaseResult, TestCaseResultType
from biosimulators_test_suite.test_case import published_project
from biosimulators_test_suite.test_case.docker_image import HasBioContainersLabels
from biosimulators_test_suite.warnings import TestCaseWarning, IgnoredTestCaseWarning
from unittest import mock
import sys
import shutil
import tempfile
import unittest
import warnings


class ValidateSimulatorTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_summarize_results(self):
        reqs = [
            SedTaskRequirements(model_format='format_2585', simulation_algorithm='KISAO_0000019'),
        ]
        results = [
            TestCaseResult(case=published_project.SimulatorCanExecutePublishedProject(
                id='A', task_requirements=reqs), type=TestCaseResultType.passed, duration=1.),
            TestCaseResult(case=published_project.SimulatorCanExecutePublishedProject(
                id='B', task_requirements=reqs), type=TestCaseResultType.passed, duration=2.),
            TestCaseResult(case=published_project.SimulatorCanExecutePublishedProject(
                id='C', task_requirements=reqs), type=TestCaseResultType.failed, duration=3.,
                exception=Exception('Summary of error'), log="Detail of error"),
            TestCaseResult(case=published_project.SimulatorCanExecutePublishedProject(
                id='D', task_requirements=reqs), type=TestCaseResultType.skipped, duration=3.),
            TestCaseResult(case=published_project.SimulatorCanExecutePublishedProject(
                id='E', task_requirements=reqs), type=TestCaseResultType.skipped, duration=3.),
            TestCaseResult(case=published_project.SimulatorCanExecutePublishedProject(
                id='F', task_requirements=reqs), type=TestCaseResultType.skipped, duration=3.),
            TestCaseResult(
                case=HasBioContainersLabels(
                    id='docker_image.HasBioContainersLabels',
                ),
                type=TestCaseResultType.passed,
                warnings=[
                    mock.Mock(message=TestCaseWarning('Summary of warning 1')),
                    mock.Mock(message=TestCaseWarning('Summary of warning 2')),
                ],
                duration=3.,
            ),
            TestCaseResult(
                case=HasBioContainersLabels(
                    id='docker_image.HasBioContainersLabels',
                    description='Description of test case'
                ),
                type=TestCaseResultType.failed,
                duration=3.,
                exception=Exception('Summary of error'),
                warnings=[
                    mock.Mock(message=TestCaseWarning('Summary of warning 1')),
                    mock.Mock(message=TestCaseWarning('Summary of warning 2')),
                ],
                log="Detail of error",
            ),
        ]
        summary, failure_details, warning_details, skipped_details = SimulatorValidator.summarize_results(results, debug=True)
        self.assertRegex(summary, 'Passed 3 test cases')
        self.assertRegex(summary, 'Failed 2 test cases')
        self.assertRegex(summary, 'Skipped 3 test cases')
        self.assertEqual(len(failure_details), 2)
        self.assertEqual(len(warning_details), 2)
        self.assertEqual(len(skipped_details), 3)

    def test_find_cases(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'

        case_ids = [
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Vilar-PNAS-2002-minimal-circardian-clock',
        ]
        validator = SimulatorValidator(specifications, case_ids=case_ids)
        n_cases = 0
        for suite_cases in validator.cases.values():
            n_cases += len(suite_cases)
        self.assertEqual(n_cases, 6)

        case_ids = [
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Vilar-PNAS-2002-minimal-circardian-clock-continuous',
        ]
        validator = SimulatorValidator(specifications, case_ids=case_ids)
        self.assertGreaterEqual(len(validator.cases), 4)
        n_cases = 0
        for suite_cases in validator.cases.values():
            n_cases += len(suite_cases)
        self.assertEqual(n_cases, 3)
        self.assertEqual(len(validator.cases['published_project']), 3)
        self.assertEqual(set(case_ids).difference(set(case.id for case in validator.cases['published_project'])), set())

        case_ids.append('doesn_not_exist')
        with self.assertWarnsRegex(IgnoredTestCaseWarning, 'were not found'):
            validator = SimulatorValidator(specifications, case_ids=case_ids)
        n_cases = 0
        for suite_cases in validator.cases.values():
            n_cases += len(suite_cases)
        self.assertEqual(n_cases, 3)

        case_ids.append('docker_image.HasOciLabels')
        case_ids.append('sedml.SimulatorSupportsMultipleTasksPerSedDocument')
        with self.assertWarnsRegex(IgnoredTestCaseWarning, 'were not found'):
            validator = SimulatorValidator(specifications, case_ids=case_ids)
        n_cases = 0
        for suite_cases in validator.cases.values():
            n_cases += len(suite_cases)
        self.assertEqual(n_cases, 5)
        self.assertEqual(len(validator.cases['docker_image']), 1)
        self.assertEqual(validator.cases['docker_image'][0].description,
                         'Test that a Docker image has Open Container Initiative (OCI) labels with metadata about the image')
        self.assertEqual(len(validator.cases['sedml']), 1)
        self.assertEqual(validator.cases['sedml'][0].description,
                         'Test that a simulator supports multiple tasks per SED document')

    def test_eval_case(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        case_ids = []
        validator = SimulatorValidator(specifications, case_ids=case_ids)
        n_cases = 0
        for suite_cases in validator.cases.values():
            n_cases += len(suite_cases)
        self.assertEqual(n_cases, 0)

        # passed
        class Case(TestCase):
            def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
                pass

        case = Case()
        result = validator.eval_case(case, self.dirname)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.passed)
        self.assertGreater(result.duration, 0.)
        self.assertLess(result.duration, 1.)
        self.assertEqual(result.exception, None)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.log, '')

        # passed, stdout
        class Case(TestCase):
            def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
                print('Message')

        case = Case()
        result = validator.eval_case(case, self.dirname)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.passed)
        self.assertGreater(result.duration, 0.)
        self.assertLess(result.duration, 1.)
        self.assertEqual(result.exception, None)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.log.replace('\r', '').strip(), 'Message')

        # passed, stdout and std errr
        class Case(TestCase):
            def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
                print('Stdout', file=sys.stdout)
                print('Stderr', file=sys.stderr)

        case = Case()
        result = validator.eval_case(case, self.dirname)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.passed)
        self.assertGreater(result.duration, 0.)
        self.assertLess(result.duration, 1.)
        self.assertEqual(result.exception, None)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.log.replace('\r', '').strip(), 'Stdout\nStderr')

        # passed, warnings
        class Case(TestCase):
            def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
                warnings.warn('Warning-1', TestCaseWarning)
                warnings.warn('Warning-2', UserWarning)
                warnings.warn('Warning-3', TestCaseWarning)

        case = Case()
        result = validator.eval_case(case, self.dirname)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.passed)
        self.assertGreater(result.duration, 0.)
        self.assertLess(result.duration, 1.)
        self.assertEqual(result.exception, None)
        self.assertEqual(len(result.warnings), 2)
        self.assertEqual(str(result.warnings[0].message), 'Warning-1')
        self.assertEqual(str(result.warnings[1].message), 'Warning-3')
        self.assertEqual(result.log.replace('\r', '').strip(), '')

        # error
        class Case(TestCase):
            def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
                raise Exception('Big error')

        case = Case()
        result = validator.eval_case(case, self.dirname)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.failed)
        self.assertGreater(result.duration, 0.)
        self.assertLess(result.duration, 1.)
        self.assertEqual(str(result.exception), 'Big error')
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.log.replace('\r', '').strip(), '')

        # skipped
        class Case(TestCase):
            def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
                raise SkippedTestCaseException('Reason for skipping')

        case = Case()
        result = validator.eval_case(case, self.dirname)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.skipped)
        self.assertGreater(result.duration, 0.)
        self.assertLess(result.duration, 1.)
        self.assertEqual(result.exception, None)
        self.assertEqual(str(result.skip_reason), 'Reason for skipping')
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.log.replace('\r', '').strip(), '')

    def test_run(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        case_ids = [
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Vilar-PNAS-2002-minimal-circardian-clock-continuous',
        ]
        validator = SimulatorValidator(specifications, case_ids=case_ids)
        self.assertGreaterEqual(len(validator.cases), 3)

        results = validator.run()

        passed = []
        failed = []
        skipped = []
        for result in results:
            if result.type == TestCaseResultType.passed:
                passed.append(result)
            elif result.type == TestCaseResultType.failed:
                failed.append(result)
            else:
                skipped.append(result)
        self.assertEqual(len(passed), 2)
        self.assertEqual(len(skipped), 1)

    def test_run_with_passed(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        case_ids = [
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Vilar-PNAS-2002-minimal-circardian-clock-continuous',
        ]
        validator = SimulatorValidator(specifications, case_ids=case_ids)

        def eval(*args, **kwargs):
            warnings.warn('Important warning', TestCaseWarning)

        with mock.patch.object(published_project.SimulatorCanExecutePublishedProject, 'eval', side_effect=eval):
            results = validator.run()
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.type, TestCaseResultType.passed)

    def test_run_with_failures(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        case_ids = [
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Vilar-PNAS-2002-minimal-circardian-clock-continuous',
        ]
        validator = SimulatorValidator(specifications, case_ids=case_ids)

        def eval(*args, **kwargs):
            raise RuntimeError("Bad")

        with mock.patch.object(published_project.SimulatorCanExecutePublishedProject, 'eval', side_effect=eval):
            results = validator.run()
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.type, TestCaseResultType.failed)

    def test_run_with_skips(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        case_ids = [
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'published_project.SimulatorCanExecutePublishedProject:sbml-core/Vilar-PNAS-2002-minimal-circardian-clock-continuous',
        ]
        validator = SimulatorValidator(specifications, case_ids=case_ids)

        def eval(*args, **kwargs):
            raise SkippedTestCaseException("Not applicable")

        with mock.patch.object(published_project.SimulatorCanExecutePublishedProject, 'eval', side_effect=eval):
            results = validator.run()
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.type, TestCaseResultType.skipped)
