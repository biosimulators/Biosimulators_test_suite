from biosimulators_test_suite.validate_simulator import SimulatorValidator
from biosimulators_test_suite.data_model import TestCaseResult, TestCaseResultType, CombineArchiveTestCase
from unittest import mock
import unittest


class ValidateSimulatorTestCase(unittest.TestCase):
    def test_get_combine_archive_cases(self):
        cases = SimulatorValidator.get_combine_archive_cases([
            'sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations',
            'sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint',
        ])
        self.assertEqual(len(cases), 2)
        self.assertEqual(set(case.name for case in cases), set([
            "Caravagna et al. Journal of Theoretical Biology 2010: Tumor-suppressive oscillations",
            "Ciliberto et al. Journal Cell Biology 2003: Morphogenesis checkpoint in budding yeast",
        ]))

    def test_summarize_results(self):
        results = [
            TestCaseResult(case=CombineArchiveTestCase(id='A'), type=TestCaseResultType.passed, duration=1.),
            TestCaseResult(case=CombineArchiveTestCase(id='B'), type=TestCaseResultType.passed, duration=2.),
            TestCaseResult(case=CombineArchiveTestCase(id='C'), type=TestCaseResultType.failed, duration=3., exception=Exception()),
            TestCaseResult(case=CombineArchiveTestCase(id='D'), type=TestCaseResultType.skipped),
            TestCaseResult(case=CombineArchiveTestCase(id='E'), type=TestCaseResultType.skipped),
            TestCaseResult(case=CombineArchiveTestCase(id='F'), type=TestCaseResultType.skipped),
        ]
        summary = SimulatorValidator.summarize_results(results)
        self.assertRegex(summary, 'Passed 2 test cases')
        self.assertRegex(summary, 'Failed 1 test cases')
        self.assertRegex(summary, 'Skipped 3 test cases')

    def test_run(self):
        specifications = 'https://raw.githubusercontent.com/biosimulators/Biosimulators_COPASI/dev/biosimulators.json'
        validator = SimulatorValidator()
        validator.cases.extend(validator.get_combine_archive_cases([
            'sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint',
            'sbml-core/Tomida-EMBO-J-2003-NFAT-translocation',
            'sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML',
            'sbml-core/Vilar-PNAS-2002-minimal-circardian-clock',
        ]))
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

        with mock.patch.object(CombineArchiveTestCase, 'eval', side_effect=eval):
            results = validator.run(specifications)
        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result.type, TestCaseResultType.failed)
