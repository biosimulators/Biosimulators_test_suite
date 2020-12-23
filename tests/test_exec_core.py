from biosimulators_test_suite.exec_core import SimulatorValidator
from biosimulators_test_suite.data_model import (TestCaseResult, TestCaseResultType,
                                                 IgnoredTestCaseWarning, SedTaskRequirements)
from biosimulators_test_suite.test_case.combine_archive import CuratedCombineArchiveTestCase
from biosimulators_test_suite.test_case.docker_image import BioContainersLabelsTestCase
from unittest import mock
import unittest


class ValidateSimulatorTestCase(unittest.TestCase):
    def test_find_cases(self):
        with self.assertWarnsRegex(IgnoredTestCaseWarning, r'Some test case\(s\) were not found'):
            SimulatorValidator().find_cases(ids=[
                'non-existent-case',
            ])

    def test_summarize_results(self):
        reqs = [
            SedTaskRequirements(model_format='format_2585', simulation_algorithm='KISAO_0000019'),
        ]
        results = [
            TestCaseResult(case=CuratedCombineArchiveTestCase(id='A', task_requirements=reqs), type=TestCaseResultType.passed, duration=1.),
            TestCaseResult(case=CuratedCombineArchiveTestCase(id='B', task_requirements=reqs), type=TestCaseResultType.passed, duration=2.),
            TestCaseResult(case=CuratedCombineArchiveTestCase(id='C', task_requirements=reqs), type=TestCaseResultType.failed, duration=3.,
                           exception=Exception('Summary of error'), log="Detail of error"),
            TestCaseResult(case=CuratedCombineArchiveTestCase(id='D', task_requirements=reqs), type=TestCaseResultType.skipped),
            TestCaseResult(case=CuratedCombineArchiveTestCase(id='E', task_requirements=reqs), type=TestCaseResultType.skipped),
            TestCaseResult(case=CuratedCombineArchiveTestCase(id='F', task_requirements=reqs), type=TestCaseResultType.skipped),
            TestCaseResult(case=BioContainersLabelsTestCase(id='docker_image.BioContainersLabelsTestCase'),
                           type=TestCaseResultType.passed, duration=3.),
            TestCaseResult(case=BioContainersLabelsTestCase(id='docker_image.BioContainersLabelsTestCase'),
                           type=TestCaseResultType.failed, duration=3.,
                           exception=Exception('Summary of error'), log="Detail of error"),
        ]
        summary, failure_details = SimulatorValidator.summarize_results(results)
        self.assertRegex(summary, 'Passed 3 test cases')
        self.assertRegex(summary, 'Failed 2 test cases')
        self.assertRegex(summary, 'Skipped 3 test cases')

    def test_run(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        validator = SimulatorValidator(case_ids=[
            'sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint',
            'sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'sbml-core/Vilar-PNAS-2002-minimal-circardian-clock',
        ])
        self.assertEqual(len(validator.cases), 4)

        results = validator.run(specifications)

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
        self.assertEqual(len(passed), 3)
        self.assertEqual(len(skipped), 1)

        def eval(*args, **kwargs):
            raise RuntimeError("Bad")

        with mock.patch.object(CuratedCombineArchiveTestCase, 'eval', side_effect=eval):
            results = validator.run(specifications)
        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result.type, TestCaseResultType.failed)
