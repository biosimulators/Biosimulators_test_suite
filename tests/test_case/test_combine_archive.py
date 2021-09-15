from biosimulators_test_suite.test_case import combine_archive
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject
from biosimulators_test_suite.warnings import InvalidOutputsWarning
from biosimulators_utils.combine.data_model import CombineArchive, CombineArchiveContent, CombineArchiveContentFormat
from biosimulators_utils.report.data_model import DataSetResults
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import SedDocument, Report, DataSet
from unittest import mock
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

    def test_CombineArchiveTestCase_eval_outputs(self):
        case = combine_archive.WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments()

        archive = CombineArchive(
            contents=[
                CombineArchiveContent(
                    'a.sedml',
                    CombineArchiveContentFormat.SED_ML,
                ),
            ],
        )
        sed_docs = {
            archive.contents[0].location: SedDocument(
                outputs=[
                    Report(id='b'),
                ],
            )
        }
        with self.assertRaisesRegex(ValueError, 'did not generate'):
            case.eval_outputs(None, archive, sed_docs, os.path.join(self.dirname, 'does_not_exist'))
        with self.assertRaisesRegex(ValueError, 'did not generate'):
            case.eval_outputs(None, archive, sed_docs, self.dirname)

        report = Report(id='report', data_sets=[DataSet(id='A', label='A'), DataSet(id='B', label='B')])
        data = DataSetResults({
            'A': numpy.array([1, 2, 3]),
            'B': numpy.array([4, 5, 6]),
        })
        ReportWriter().run(report, data, self.dirname, 'a.sedml/b')
        ReportWriter().run(report, data, self.dirname, 'a.sedml/c')
        with self.assertWarnsRegex(InvalidOutputsWarning, 'extra unexpected reports'):
            case.eval_outputs(None, archive, sed_docs, self.dirname)

        sed_docs[archive.contents[0].location].outputs.append(Report(id='c'))
        case.eval_outputs(None, archive, sed_docs, self.dirname)

    def test_WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = combine_archive.WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile(
            published_projects_test_cases=[curated_case])

        base_get_expected_reports = case.get_expected_reports

        def get_expected_reports(archive, sed_documents):
            expected_reports = base_get_expected_reports(archive, sed_documents)
            assert expected_reports == set(['BIOMD0000000678_sim.sedml/report'])
            return expected_reports

        with mock.patch.object(combine_archive.WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile,
                               'get_expected_reports', side_effect=get_expected_reports):
            case.eval(specs, self.dirname)

    def test_WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = combine_archive.WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments(
            published_projects_test_cases=[curated_case])

        base_get_expected_reports = case.get_expected_reports

        def get_expected_reports(archive, sed_documents):
            expected_reports = base_get_expected_reports(archive, sed_documents)

            assert expected_reports == set([
                'BIOMD0000000678_sim.sedml/report',
                'BIOMD0000000678_sim__copy.sedml/report',
            ])
            return expected_reports

        with mock.patch.object(combine_archive.WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments,
                               'get_expected_reports', side_effect=get_expected_reports):
            case.eval(specs, self.dirname)

    def test_CombineArchiveHasSedDocumentsInNestedDirectories(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = combine_archive.CombineArchiveHasSedDocumentsInNestedDirectories(
            published_projects_test_cases=[curated_case])

        base_get_expected_reports = case.get_expected_reports

        def get_expected_reports(archive, sed_documents):
            expected_reports = base_get_expected_reports(archive, sed_documents)
            assert expected_reports == set([
                'subdir/BIOMD0000000678_sim.sedml/report',
            ])
            return expected_reports

        with mock.patch.object(combine_archive.CombineArchiveHasSedDocumentsInNestedDirectories,
                               'get_expected_reports', side_effect=get_expected_reports):
            case.eval(specs, self.dirname)

    def test_CombineArchiveHasSedDocumentsWithSameNamesInDifferentInNestedDirectories(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = combine_archive.CombineArchiveHasSedDocumentsWithSameNamesInDifferentInNestedDirectories(
            published_projects_test_cases=[curated_case])

        base_get_expected_reports = case.get_expected_reports

        def get_expected_reports(archive, sed_documents):
            expected_reports = base_get_expected_reports(archive, sed_documents)
            assert expected_reports == set([
                'subdir/BIOMD0000000678_sim.sedml/report',
                'subdir__copy/BIOMD0000000678_sim.sedml/report',
            ])
            return expected_reports

        with mock.patch.object(combine_archive.CombineArchiveHasSedDocumentsWithSameNamesInDifferentInNestedDirectories,
                               'get_expected_reports', side_effect=get_expected_reports):
            case.eval(specs, self.dirname)
