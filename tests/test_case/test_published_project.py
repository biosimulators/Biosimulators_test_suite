from biosimulators_test_suite import data_model
from biosimulators_test_suite.exceptions import InvalidOutputsException, SkippedTestCaseException
from biosimulators_test_suite.results.data_model import TestCaseResult, TestCaseResultType
from biosimulators_test_suite.test_case.published_project import (
    SimulatorCanExecutePublishedProject, find_cases, SyntheticCombineArchiveTestCase,
    ExpectedResultOfSyntheticArchive, UniformTimeCourseTestCase)
from biosimulators_test_suite.warnings import IgnoredTestCaseWarning, SimulatorRuntimeErrorWarning, InvalidOutputsWarning
from biosimulators_utils.archive.data_model import Archive, ArchiveFile
from biosimulators_utils.archive.io import ArchiveWriter
from biosimulators_utils.combine.data_model import CombineArchive
from biosimulators_utils.combine.io import CombineArchiveReader, CombineArchiveWriter
from biosimulators_utils.report.data_model import DataSetResults
from biosimulators_utils.report.io import ReportWriter, ReportFormat
from biosimulators_utils.sedml.data_model import (SedDocument, Task, DataGenerator, Report,
                                                  DataSet, Plot2D, Symbol, Variable, Model, ModelLanguage)
from unittest import mock
import functools
import json
import os
import numpy
import numpy.testing
import shutil
import tempfile
import unittest


class TestSimulatorCanExecutePublishedProject(unittest.TestCase):
    def setUp(self):
        self.tmp_dirname = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

    def test_find_cases(self):
        all_cases, _ = find_cases({
            'algorithms': [
                {
                    'kisaoId': {'id': 'KISAO_0000019'},
                    'modelFormats': [{'id': 'format_2585', 'supportedFeatures': []}],
                }
            ]
        })
        self.assertGreater(len(all_cases), 2)
        self.assertEqual(set([
            "Caravagna et al. Journal of Theoretical Biology 2010: Tumor-suppressive oscillations",
        ]).difference(set(case.name for case in all_cases)), set())

        with self.assertWarnsRegex(IgnoredTestCaseWarning, 'not available'):
            all_cases, compatible_cases = find_cases({
                'algorithms': [
                    {
                        'kisaoId': {'id': 'KISAO_0000019'},
                        'modelFormats': [{'id': 'format_2585', 'supportedFeatures': []}],
                    }
                ]
            }, dir_name='does_not_exist')
        self.assertEqual(len(all_cases), 0)
        self.assertEqual(len(compatible_cases), 0)

    def test_SimulatorCanExecutePublishedProject_description(self):
        case = SimulatorCanExecutePublishedProject(task_requirements=[
            data_model.SedTaskRequirements(model_format='format_2585', simulation_algorithm='KISAO_0000027'),
            data_model.SedTaskRequirements(model_format='format_2585', simulation_algorithm='KISAO_0000019'),
        ])
        expected_description = '\n'.join([
            'Required model formats and simulation algorithms for SED tasks:',
            '',
            '* Format: `format_2585`',
            '  Algorithm: `KISAO_0000019`',
            '* Format: `format_2585`',
            '  Algorithm: `KISAO_0000027`',
        ])
        self.assertEqual(case.description, expected_description)

    def test_SimulatorCanExecutePublishedProject_from_dict(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations/expected-results.json')
        with open(os.path.join(base_path, filename), 'r') as file:
            data = json.load(file)
        data['expectedReports'][0]['values'][0]['value'] = [0, 1, 2, 3, 4, 5]
        id = ('published_project.SimulatorCanExecutePublishedProject:'
              'sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations/expected-results.json')
        case = SimulatorCanExecutePublishedProject(id=id).from_dict(data)
        numpy.testing.assert_allclose(case.expected_reports[0].values['data_set_time'], numpy.array([0, 1, 2, 3, 4, 5]))

    def test_SimulatorCanExecutePublishedProject_from_dict_error_handling(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations/expected-results.json')
        with open(os.path.join(base_path, filename), 'r') as file:
            data = json.load(file)
        id = ('published_project.SimulatorCanExecutePublishedProject:'
              'sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations/expected-results.json')

        data['expectedReports'][0]['values'] = [{'id': 't', 'label': 't', 'value': [0, 1, 2, 3, 4, 5]}]
        with self.assertRaisesRegex(ValueError, "keys were not in the 'dataSets' property"):
            SimulatorCanExecutePublishedProject(id=id).from_dict(data)

        data['expectedReports'][0]['values'] = [{'id': 'T', 'label': 'T', 'value': {'5001': 1000.2}}]
        with self.assertRaisesRegex(ValueError, "Key must be less than or equal to"):
            SimulatorCanExecutePublishedProject(id=id).from_dict(data)

        data['expectedReports'][0]['values'] = [{'id': 'data_set_time', 'label': 'T', 'value': {'5000': 1000.}}]
        SimulatorCanExecutePublishedProject(id=id).from_dict(data)

    def test_SimulatorCanExecutePublishedProject_from_json(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations/expected-results.json')
        case = SimulatorCanExecutePublishedProject().from_json(base_path, filename)
        self.assertEqual(case.id, ('published_project.SimulatorCanExecutePublishedProject:'
                                   'sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations'))
        self.assertEqual(case.name, "Caravagna et al. Journal of Theoretical Biology 2010: Tumor-suppressive oscillations")
        self.assertTrue(case.filename.endswith('sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.omex'))
        self.assertEqual(len(case.task_requirements), 1)
        self.assertEqual(case.task_requirements[0].model_format, 'format_2585')
        self.assertEqual(case.task_requirements[0].simulation_algorithm, 'KISAO_0000019')
        self.assertEqual(len(case.expected_reports), 1)
        self.assertEqual(case.expected_reports[0].id, 'BIOMD0000000912_sim.sedml/report')
        self.assertEqual(set(data_set.label for data_set in case.expected_reports[0].data_sets), set(["time", "T", "E", "I"]))
        self.assertEqual(case.expected_reports[0].points, (5001,))
        self.assertEqual(case.expected_reports[0].values, {
            "data_set_time": {
                (0,): 0.0,
                (1,): 0.2,
                (2,): 0.4,
                (999,): 199.8,
                (1000,): 200,
            },
        })
        self.assertEqual(len(case.expected_plots), 1)
        self.assertEqual(case.expected_plots[0].id, 'BIOMD0000000912_sim.sedml/Figure_1_bottom_left')

        self.assertEqual(case.assert_no_extra_reports, False)
        self.assertEqual(case.assert_no_extra_datasets, False)
        self.assertEqual(case.assert_no_missing_plots, False)
        self.assertEqual(case.assert_no_extra_plots, False)
        self.assertEqual(case.r_tol, 1e-4)
        self.assertEqual(case.a_tol, 0.)

    def test_SimulatorCanExecutePublishedProject_eval(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations/expected-results.json')
        case = SimulatorCanExecutePublishedProject().from_json(base_path, filename)
        case.expected_reports[0].values['data_set_time'] = numpy.linspace(0., 1000., 5001,)

        # skips
        specs = {
            'algorithms': [],
        }
        with self.assertRaisesRegex(SkippedTestCaseException, 'requires'):
            case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        specs = {
            'algorithms': [{
                'kisaoId': {'id': 'KISAO_0000019'},
                'modelFormats': [{'id': 'format_2584', 'supportedFeatures': []}],
            }],
        }
        with self.assertRaisesRegex(SkippedTestCaseException, 'requires'):
            case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        specs = {
            'algorithms': [{
                'kisaoId': {'id': 'KISAO_0000018'},
                'modelFormats': [{'id': 'format_2585', 'supportedFeatures': []}],
            }],
        }
        with self.assertRaisesRegex(SkippedTestCaseException, 'requires'):
            case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        # execute case
        specs = {
            'image': {
                'url': 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest',
            },
            'algorithms': [{
                'kisaoId': {'id': 'KISAO_0000019'},
                'modelFormats': [{'id': 'format_2585', 'supportedFeatures': []}],
            }],
        }
        exec_archive_method = 'biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator'

        def exec_archive(error, missing_report, extra_report, missing_data_set, extra_data_set,
                         incorrect_points, incorrect_values,
                         no_plots, missing_plot, extra_plot,
                         filename, out_dir, image, pull_docker_image=True,
                         user_to_exec_within_container=None):
            if error:
                raise RuntimeError('Could not execute task')

            points = 5001
            if incorrect_points:
                points = 1001

            data = [
                numpy.linspace(0., 1000., points),
                numpy.zeros((points, )),
                numpy.zeros((points, )),
                numpy.zeros((points, )),
            ]
            ids = ['data_set_time', 'data_set_T', 'data_set_E', 'data_set_I']
            labels = ['time', 'T', 'E', 'I']
            if missing_data_set:
                data.pop()
                ids.pop()
                labels.pop()
            if extra_data_set:
                data.append(numpy.zeros((5001, )))
                ids.append('extra')
                labels.append('extra')
            if incorrect_values:
                data[0][0] = -1
                data[1][0] = -1

            if extra_report:
                report = Report(id='report', data_sets=[DataSet(id=i, label=l) for i, l in zip(ids, labels)])
                data_set_results = DataSetResults({i: d for i, d in zip(ids, data)})
                ReportWriter().run(report, data_set_results, out_dir, 'BIOMD0000000912_sim.sedml/extra', ReportFormat.h5)

            if not missing_report:
                report = Report(id='report', data_sets=[DataSet(id=i, label=l) for i, l in zip(ids, labels)])
                data_set_results = DataSetResults({i: d for i, d in zip(ids, data)})
                ReportWriter().run(report, data_set_results, out_dir, 'BIOMD0000000912_sim.sedml/report', ReportFormat.h5)

            plot_file = os.path.join(out_dir, 'plot.pdf')
            with open(plot_file, 'w'):
                pass

            if not no_plots:
                archive = Archive(files=[ArchiveFile(local_path=plot_file, archive_path='BIOMD0000000912_sim.sedml/plot_1.pdf')])
                if missing_plot:
                    archive.files = []
                if extra_plot:
                    archive.files[0].archive_path = archive.files[0].archive_path.replace('plot_1', 'plot_2')
                ArchiveWriter().run(archive, os.path.join(out_dir, 'plots.zip'))

        with mock.patch(exec_archive_method, functools.partial(
                exec_archive, False, False, False, False, False, False, False, False, False, False)):
            case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertRaisesRegex(RuntimeError, 'Could not execute task'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, True, False, False, False, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        case.runtime_failure_alert_type = data_model.AlertType.warning
        with self.assertWarnsRegex(SimulatorRuntimeErrorWarning, 'Could not execute task'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, True, False, False, False, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)
        case.runtime_failure_alert_type = data_model.AlertType.exception

        with self.assertRaisesRegex(InvalidOutputsException, 'No reports were generated'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, True, False, False, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertRaisesRegex(InvalidOutputsException, 'could not be read'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, True, True, False, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertWarnsRegex(InvalidOutputsWarning, 'Unexpected reports were produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, True, False, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertRaisesRegex(InvalidOutputsException, 'does not contain expected data sets'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, True, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertRaisesRegex(InvalidOutputsException, 'incorrect number of points'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, True, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertRaisesRegex(InvalidOutputsException, 'does not have expected value'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, True, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertWarnsRegex(InvalidOutputsWarning, 'Plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, True, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertWarnsRegex(InvalidOutputsWarning, 'Plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, False, True, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertWarnsRegex(InvalidOutputsWarning, 'Extra plots were produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, False, False, True)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        case.assert_no_extra_reports = True
        with self.assertRaisesRegex(InvalidOutputsException, 'Unexpected reports were produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, True, False, False, False, False, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)
        case.assert_no_extra_reports = False

        case.assert_no_missing_plots = True
        with self.assertRaisesRegex(InvalidOutputsException, 'Plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, True, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)
        case.assert_no_missing_plots = False

        case.assert_no_extra_plots = True
        with self.assertRaisesRegex(InvalidOutputsException, 'Extra plots were produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, False, False, True)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)
        case.assert_no_extra_plots = False

        case.expected_reports[0].values = {
            'data_set_T': {
                (0,): 0.,
                (5000,): 1000.,
            }
        }

        def exec_archive(error, missing_report, extra_report, missing_data_set, extra_data_set,
                         incorrect_points, incorrect_values,
                         no_plots, missing_plot, extra_plot,
                         filename, out_dir, image, pull_docker_image=True,
                         user_to_exec_within_container=None):
            points = 5001
            data = [
                numpy.linspace(0., 1000., points),
                numpy.linspace(0., 1000., points),
                numpy.zeros((points, )),
                numpy.zeros((points, )),
            ]
            ids = ['data_set_time', 'data_set_T', 'data_set_E', 'data_set_I']
            labels = ['time', 'T', 'E', 'I']
            if incorrect_values:
                data[1][0] = -1

            if not missing_report:
                report = Report(id='report', data_sets=[DataSet(id=i, label=l) for i, l in zip(ids, labels)])
                data_set_results = DataSetResults({i: d for i, d in zip(ids, data)})
                ReportWriter().run(report, data_set_results, out_dir, 'BIOMD0000000912_sim.sedml/report', ReportFormat.h5)

            plot_file = os.path.join(out_dir, 'plot.pdf')
            with open(plot_file, 'w'):
                pass

            if not no_plots:
                archive = Archive(files=[ArchiveFile(local_path=plot_file, archive_path='BIOMD0000000912_sim.sedml/plot_1.pdf')])
                if missing_plot:
                    archive.files = []
                if extra_plot:
                    archive.files[0].archive_path = archive.files[0].archive_path.replace('plot_1', 'plot_2')
                ArchiveWriter().run(archive, os.path.join(out_dir, 'plots.zip'))

        with mock.patch(exec_archive_method, functools.partial(
                exec_archive, False, False, False, False, False, False, False, False, False, False)):
            case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

        with self.assertRaisesRegex(InvalidOutputsException, 'does not have expected value'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, True, False, False, False)):
                case.eval(specs, self.tmp_dirname)
        if os.path.isdir(self.tmp_dirname):
            shutil.rmtree(self.tmp_dirname)

    def test_TestCaseResult(self):
        case = SimulatorCanExecutePublishedProject(id='case')
        exception = Exception('message')
        result = TestCaseResult(case=case, type=TestCaseResultType.skipped, duration=10., exception=exception)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, TestCaseResultType.skipped)
        self.assertEqual(result.duration, 10.)
        self.assertEqual(result.exception, exception)

    def test_SyntheticCombineArchiveTestCase_no_suitable_archives(self):
        class TestCase(SyntheticCombineArchiveTestCase):
            def is_curated_archive_suitable_for_building_synthetic_archive(self, specifications, archive, sed_docs):
                return False

            def build_synthetic_archives(self):
                pass

            def eval_outputs(self):
                pass

        case = TestCase(published_projects_test_cases=[
            SimulatorCanExecutePublishedProject()
        ])

        with self.assertRaisesRegex(SkippedTestCaseException, 'No curated COMBINE/OMEX archives are available'):
            with mock.patch.object(CombineArchiveReader, 'run', return_value=CombineArchive()):
                case.eval(None, self.tmp_dirname)

    def test_SyntheticCombineArchiveTestCase_build_synthetic_archives(self):
        class ConcreteSyntheticCombineArchiveTestCase(SyntheticCombineArchiveTestCase):
            def eval_outputs():
                pass

        archive = CombineArchive()
        expected_results_of_synthetic_archives = ConcreteSyntheticCombineArchiveTestCase().build_synthetic_archives(None, archive, 'b', 'c')
        self.assertEqual(len(expected_results_of_synthetic_archives), 1)
        self.assertEqual(expected_results_of_synthetic_archives[0].archive, archive,)
        self.assertEqual(expected_results_of_synthetic_archives[0].sed_documents, 'c',)

    def test_SyntheticCombineArchiveTestCase_is_curated_sed_doc_suitable_for_building_synthetic_archive(self):
        class Concrete(SyntheticCombineArchiveTestCase):
            def is_curated_sed_model_suitable_for_building_synthetic_archive(self, specs, model):
                return False

            def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
                pass

        with mock.patch.object(Concrete, 'is_curated_sed_report_suitable_for_building_synthetic_archive', return_value=True):
            doc = SedDocument(outputs=[Report()])
            self.assertTrue(Concrete().is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, './doc.sedml'))
            self.assertTrue(Concrete().is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, 'doc.sedml'))

            self.assertFalse(Concrete().is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, './subdir/doc.sedml'))

            doc.outputs = [Plot2D()]
            self.assertFalse(Concrete().is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, './doc.sedml'))

            doc.outputs = []
            self.assertFalse(Concrete().is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, './doc.sedml'))

    def test_SyntheticCombineArchiveTestCase_is_curated_sed_task_suitable_for_building_synthetic_archive(self):
        class Concrete(SyntheticCombineArchiveTestCase):
            def is_curated_sed_model_suitable_for_building_synthetic_archive(self, specs, model):
                return False

            def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
                pass

        self.assertFalse(Concrete().is_curated_sed_task_suitable_for_building_synthetic_archive(None, None))
        self.assertFalse(Concrete().is_curated_sed_task_suitable_for_building_synthetic_archive(None, Task()))

    def test_SyntheticCombineArchiveTestCase__eval_synthetic_archive(self):
        class Concrete(SyntheticCombineArchiveTestCase):
            def is_curated_sed_model_suitable_for_building_synthetic_archive(self, specs, model):
                return False

            def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
                pass

        specifications = {'image': {'url': None}}
        expected_results_of_synthetic_archive = ExpectedResultOfSyntheticArchive(
            None, {}, True)
        shared_archive_dir = self.tmp_dirname

        with mock.patch('biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator', return_value=None):
            with mock.patch.object(CombineArchiveWriter, 'run', return_value=None):
                with mock.patch.object(Concrete, 'eval_outputs', return_value=True):
                    self.assertFalse(Concrete()._eval_synthetic_archive(
                        specifications, expected_results_of_synthetic_archive, shared_archive_dir, None, self.tmp_dirname))

        with mock.patch('biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator', return_value=None):
            with mock.patch.object(CombineArchiveWriter, 'run', return_value=None):
                with mock.patch.object(Concrete, 'eval_outputs', return_value=False):
                    self.assertTrue(Concrete()._eval_synthetic_archive(
                        specifications, expected_results_of_synthetic_archive, shared_archive_dir, None, self.tmp_dirname))

        with mock.patch('biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator',
                        side_effect=RuntimeError):
            with mock.patch.object(CombineArchiveWriter, 'run', return_value=None):
                with mock.patch.object(Concrete, 'eval_outputs', return_value=False):
                    with self.assertRaises(RuntimeError):
                        Concrete()._eval_synthetic_archive(
                            specifications, expected_results_of_synthetic_archive, shared_archive_dir, None, self.tmp_dirname)

        expected_results_of_synthetic_archive.is_success_expected = False
        with mock.patch('biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator',
                        side_effect=RuntimeError):
            with mock.patch.object(CombineArchiveWriter, 'run', return_value=None):
                with mock.patch.object(Concrete, 'eval_outputs', return_value=False):
                    self.assertFalse(Concrete()._eval_synthetic_archive(
                        specifications, expected_results_of_synthetic_archive, shared_archive_dir, None, self.tmp_dirname))

        with mock.patch('biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator', return_value=None):
            with mock.patch.object(CombineArchiveWriter, 'run', return_value=None):
                with mock.patch.object(Concrete, 'eval_outputs', return_value=False):
                    with self.assertRaisesRegex(ValueError, 'did not fail as expected'):
                        Concrete()._eval_synthetic_archive(
                            specifications, expected_results_of_synthetic_archive, shared_archive_dir, None, self.tmp_dirname)

    def test_UniformTimeCourseTestCase_add_time_data_set(self):
        class Concrete(UniformTimeCourseTestCase):
            def modify_simulation(self, simulation):
                pass

            def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
                pass

        doc = SedDocument()
        task = Task(model=Model(language=ModelLanguage.SBML.value))
        doc.tasks.append(task)
        report = Report()
        doc.outputs.append(report)
        self.assertFalse(Concrete().add_time_data_set(doc, task, report))
        self.assertEqual(len(doc.data_generators), 1)
        self.assertEqual(len(report.data_sets), 1)
        self.assertEqual(report.data_sets[0].id, '__data_set_time__')
        self.assertFalse(Concrete().add_time_data_set(doc, task, report))
        self.assertEqual(len(doc.data_generators), 1)
        self.assertEqual(len(report.data_sets), 1)
        self.assertEqual(report.data_sets[0].id, '__data_set_time__')

        doc = SedDocument()
        task = Task(model=Model(language=ModelLanguage.SBML.value))
        doc.tasks.append(task)
        doc.data_generators.append(DataGenerator(variables=[Variable(task=task, symbol=Symbol.time)]))
        report = Report()
        doc.outputs.append(report)
        self.assertFalse(Concrete().add_time_data_set(doc, task, report))
        self.assertEqual(len(doc.data_generators), 1)
        self.assertEqual(len(report.data_sets), 1)
        self.assertEqual(report.data_sets[0].id, '__data_set_time__')

        doc = SedDocument()
        task = Task(model=Model(language=ModelLanguage.SBML.value))
        doc.tasks.append(task)
        doc.data_generators.append(DataGenerator(variables=[Variable(task=task, symbol=None)]))
        report = Report()
        doc.outputs.append(report)
        self.assertFalse(Concrete().add_time_data_set(doc, task, report))
        self.assertEqual(len(doc.data_generators), 2)
        self.assertEqual(len(report.data_sets), 1)
        self.assertEqual(report.data_sets[0].id, '__data_set_time__')

        doc = SedDocument()
        task = Task(model=Model(language=ModelLanguage.SBML.value))
        doc.tasks.append(task)
        doc.data_generators.append(DataGenerator(variables=[Variable(task=task, symbol=Symbol.time)]))
        report = Report()
        doc.outputs.append(report)
        report.data_sets.append(DataSet(data_generator=doc.data_generators[0]))
        self.assertFalse(Concrete().add_time_data_set(doc, task, report))
        self.assertEqual(len(doc.data_generators), 1)
        self.assertEqual(len(report.data_sets), 1)
        self.assertEqual(report.data_sets[0].id, '__data_set_time__')

        doc = SedDocument()
        task = Task(model=Model(language=ModelLanguage.SBML.value))
        doc.tasks.append(task)
        doc.data_generators.append(DataGenerator(variables=[Variable(task=task, symbol=Symbol.time)]))
        report = Report()
        doc.outputs.append(report)
        report.data_sets.append(DataSet(data_generator=None))
        self.assertFalse(Concrete().add_time_data_set(doc, task, report))
        self.assertEqual(len(doc.data_generators), 1)
        self.assertEqual(len(report.data_sets), 2)
        self.assertEqual(report.data_sets[1].id, '__data_set_time__')

        doc = SedDocument()
        task = Task(model=Model(language=ModelLanguage.CellML.value))
        doc.tasks.append(task)
        report = Report()
        doc.outputs.append(report)
        with self.assertRaisesRegex(SkippedTestCaseException, 'supports the time symbol'):
            Concrete().add_time_data_set(doc, task, report)
