from biosimulators_test_suite import data_model
from biosimulators_utils.archive.data_model import Archive, ArchiveFile
from biosimulators_utils.archive.io import ArchiveWriter
from biosimulators_utils.report.io import ReportWriter, ReportFormat
from unittest import mock
import biosimulators_utils.simulator.exec
import functools
import json
import os
import numpy
import numpy.testing
import pandas
import unittest


class DataModelTestCase(unittest.TestCase):
    def test_SedTaskRequirements(self):
        reqs = data_model.SedTaskRequirements(model_format='format_2585', simulation_algorithm='KISAO_0000019')
        self.assertEqual(reqs.model_format, 'format_2585')
        self.assertEqual(reqs.simulation_algorithm, 'KISAO_0000019')

    def test_ExpectedSedReport(self):
        report = data_model.ExpectedSedReport(
            id='report-1',
            data_sets=set('time', 'A', 'B', 'C'),
            points=(1001,),
            values={
                'time': [0, 1, 2, 4, 5],
                'A': {
                    (0,): 10.,
                    (2,): 12.,
                },
            },
        )
        self.assertEqual(report.id, 'report-1')
        self.assertEqual(report.data_sets, set('time', 'A', 'B', 'C'))
        self.assertEqual(report.points, (1001,))
        self.assertEqual(report.values, {
            'time': [0, 1, 2, 4, 5],
            'A': {
                (0,): 10.,
                (2,): 12.,
            },
        })

    def test_ExpectedSedReport(self):
        plot = data_model.ExpectedSedPlot(id='plot-1')
        self.assertEqual(plot.id, 'plot-1')

    def test_CombineArchiveTestCase_from_dict(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.json')
        with open(os.path.join(base_path, filename), 'r') as file:
            data = json.load(file)
        data['expectedReports'][0]['values']['T'] = [0, 1, 2, 3, 4, 5]
        case = data_model.CombineArchiveTestCase().from_dict(data)
        numpy.testing.assert_allclose(case.expected_reports[0].values['T'], numpy.array([0, 1, 2, 3, 4, 5]))

    def test_CombineArchiveTestCase_from_json(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.json')
        case = data_model.CombineArchiveTestCase().from_json(base_path, filename)
        self.assertEqual(case.id, 'sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations')
        self.assertEqual(case.name, "Caravagna et al. Journal of Theoretical Biology 2010: Tumor-suppressive oscillations")
        self.assertTrue(case.filename.endswith('sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.omex'))
        self.assertEqual(len(case.task_requirements), 1)
        self.assertEqual(case.task_requirements[0].model_format, 'format_2585')
        self.assertEqual(case.task_requirements[0].simulation_algorithm, 'KISAO_0000019')
        self.assertEqual(len(case.expected_reports), 1)
        self.assertEqual(case.expected_reports[0].id, 'BIOMD0000000912_sim.sedml/BIOMD0000000912_sim')
        self.assertEqual(case.expected_reports[0].data_sets, set(["time", "T", "E", "I"]))
        self.assertEqual(case.expected_reports[0].points, (5001,))
        self.assertEqual(case.expected_reports[0].values, {
            "time": {
                (0,): 0.0,
                (1,): 0.2,
                (2,): 0.4,
                (999,): 199.8,
                (1000,): 200,
            },
        })
        self.assertEqual(len(case.expected_plots), 1)
        self.assertEqual(case.expected_plots[0].id, 'BIOMD0000000912_sim.sedml/plot_1')

        self.assertEqual(case.assert_no_extra_reports, False)
        self.assertEqual(case.assert_no_extra_datasets, False)
        self.assertEqual(case.assert_no_missing_plots, False)
        self.assertEqual(case.assert_no_extra_plots, False)
        self.assertEqual(case.r_tol, 1e-4)
        self.assertEqual(case.a_tol, 0.)

    def test_CombineArchiveTestCase_eval(self):
        base_path = os.path.join(os.path.dirname(__file__), '..', 'examples')
        filename = os.path.join('sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.json')
        case = data_model.CombineArchiveTestCase().from_json(base_path, filename)
        case.expected_reports[0].values['T'] = numpy.zeros((5001,))

        # skips
        specs = {
            'algorithms': [],
        }
        with self.assertRaisesRegex(data_model.SkippedTestCaseException, 'requires'):
            case.eval(specs)

        specs = {
            'algorithms': [{
                'kisaoId': {'id': 'KISAO_0000019'},
                'modelFormats': [{'id': 'format_2584'}],
            }],
        }
        with self.assertRaisesRegex(data_model.SkippedTestCaseException, 'requires'):
            case.eval(specs)

        specs = {
            'algorithms': [{
                'kisaoId': {'id': 'KISAO_0000018'},
                'modelFormats': [{'id': 'format_2585'}],
            }],
        }
        with self.assertRaisesRegex(data_model.SkippedTestCaseException, 'requires'):
            case.eval(specs)

        # execute case
        specs = {
            'image': {
                'url': 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest',
            },
            'algorithms': [{
                'kisaoId': {'id': 'KISAO_0000019'},
                'modelFormats': [{'id': 'format_2585'}],
            }],
        }
        exec_archive_method = 'biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator'

        def exec_archive(error, missing_report, extra_report, missing_data_set, extra_data_set,
                         incorrect_points, incorrect_values,
                         no_plots, missing_plot, extra_plot,
                         filename, out_dir, image, pull_docker_image=True):
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
            index = ['time', 'T', 'E', 'I']
            if missing_data_set:
                data.pop()
                index.pop()
            if extra_data_set:
                data.append(numpy.zeros((5001, )))
                index.append('extra')
            if incorrect_values:
                data[0][0] = -1
                data[1][0] = -1

            if extra_report:
                df = pandas.DataFrame(numpy.array(data), index=index)
                ReportWriter().run(df, out_dir, 'BIOMD0000000912_sim.sedml/extra', ReportFormat.h5)

            if not missing_report:
                df = pandas.DataFrame(numpy.array(data), index=index)
                ReportWriter().run(df, out_dir, 'BIOMD0000000912_sim.sedml/BIOMD0000000912_sim', ReportFormat.h5)

            plot_file = os.path.join(out_dir, 'plot.pdf')
            with open(plot_file, 'w') as file:
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
            case.eval(specs)

        with self.assertRaisesRegex(RuntimeError, 'Could not execute task'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, True, False, False, False, False, False, False, False, False, False)):
                case.eval(specs)

        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'No reports were generated'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, True, False, False, False, False, False, False, False, False)):
                case.eval(specs)

        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'could not be read'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, True, True, False, False, False, False, False, False, False)):
                case.eval(specs)

        with self.assertWarnsRegex(data_model.InvalidOuputsWarning, 'Unexpected reports were produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, True, False, False, False, False, False, False, False)):
                case.eval(specs)

        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'does not contain expected data sets'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, True, False, False, False, False, False, False)):
                case.eval(specs)

        with self.assertWarnsRegex(data_model.InvalidOuputsWarning, 'contains unexpected data sets'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, True, False, False, False, False, False)):
                case.eval(specs)

        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'incorrect number of points'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, True, False, False, False, False)):
                case.eval(specs)

        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'does not have expected value'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, True, False, False, False)):
                case.eval(specs)

        with self.assertWarnsRegex(data_model.InvalidOuputsWarning, 'Plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, True, False, False)):
                case.eval(specs)

        with self.assertWarnsRegex(data_model.InvalidOuputsWarning, 'Plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, False, True, False)):
                case.eval(specs)

        with self.assertWarnsRegex(data_model.InvalidOuputsWarning, 'Extra plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, False, False, True)):
                case.eval(specs)

        case.assert_no_extra_reports = True
        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'Unexpected reports were produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, True, False, False, False, False, False, False, False)):
                case.eval(specs)
        case.assert_no_extra_reports = False

        case.assert_no_extra_datasets = True
        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'contains unexpected data sets'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, True, False, False, False, False, False)):
                case.eval(specs)
        case.assert_no_extra_datasets = False

        case.assert_no_missing_plots = True
        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'Plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, True, False, False)):
                case.eval(specs)
        case.assert_no_missing_plots = False

        case.assert_no_extra_plots = True
        with self.assertRaisesRegex(data_model.InvalidOuputsException, 'Extra plots were not produced'):
            with mock.patch(exec_archive_method, functools.partial(
                    exec_archive, False, False, False, False, False, False, False, False, False, True)):
                case.eval(specs)
        case.assert_no_extra_plots = False

    def test_TestCaseResult(self):
        case = data_model.CombineArchiveTestCase(id='case')
        exception = Exception('message')
        result = data_model.TestCaseResult(case=case, type=data_model.TestCaseResultType.skipped, duration=10., exception=exception)
        self.assertEqual(result.case, case)
        self.assertEqual(result.type, data_model.TestCaseResultType.skipped)
        self.assertEqual(result.duration, 10.)
        self.assertEqual(result.exception, exception)
