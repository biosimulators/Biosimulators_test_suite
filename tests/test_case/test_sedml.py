from biosimulators_test_suite.exceptions import InvalidOutputsException, SkippedTestCaseException
from biosimulators_test_suite.test_case import sedml
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject, SyntheticCombineArchiveTestCase
from biosimulators_test_suite.warnings import InvalidOutputsWarning
from biosimulators_utils.archive.data_model import Archive, ArchiveFile
from biosimulators_utils.archive.io import ArchiveWriter
from biosimulators_utils.config import get_config
from biosimulators_utils.combine.data_model import CombineArchive, CombineArchiveContent, CombineArchiveContentFormat
from biosimulators_utils.report.data_model import DataSetResults
from biosimulators_utils.report.io import ReportWriter, ReportReader
from biosimulators_utils.sedml.data_model import (SedDocument, Task, Report, DataSet,
                                                  DataGenerator, Variable, UniformTimeCourseSimulation,
                                                  Algorithm, Symbol, Model, ModelLanguage,
                                                  Plot2D, Plot3D, Surface, AxisScale, RepeatedTask, SubTask)
from biosimulators_utils.simulator.io import read_simulator_specs
from unittest import mock
from kisao import Kisao
from kisao.data_model import AlgorithmSubstitutionPolicy
from kisao.utils import get_substitutable_algorithms_for_policy
import numpy
import os
import PyPDF2
import shutil
import tempfile
import unittest


class SedmlTestCaseTest(unittest.TestCase):
    IMAGE = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
    CURATED_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'sbml-core', 'Tomida-EMBO-J-2003-NFAT-translocation.omex')
    CURATED_NON_XML_ARCHIVE_FILENAME = os.path.join(
        os.path.dirname(__file__), '..', '..',
        'examples', 'bngl', 'test-bngl.omex')

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports_eval_outputs(self):
        case = sedml.SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports()

        doc = SedDocument(
            outputs=[
                Report(
                    id='b',
                    data_sets=[
                        DataSet(id='x', label='x'),
                        DataSet(id='y', label='y'),
                    ],
                ),
            ],
        )

        report = doc.outputs[0]

        with self.assertRaisesRegex(InvalidOutputsException, 'did not produce the following reports'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({'x': numpy.array([1, 2, 3])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/b')
        with self.assertRaisesRegex(InvalidOutputsException, 'did not produce the following data sets'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({'x': numpy.array([1, 2, 3]), 'y': numpy.array([4, 5, 6])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/b')
        self.assertTrue(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

        data_set_results = DataSetResults({'x': numpy.array([1, 2, 3]), 'y': numpy.array([4, 5, 6]), 'z': numpy.array([7, 8, 9])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/b')
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/c')
        with self.assertWarnsRegex(InvalidOutputsWarning, 'extra reports'):
            self.assertFalse(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

        with self.assertWarnsRegex(InvalidOutputsWarning, 'extra data sets'):
            _report_reader_run = ReportReader().run

            def report_reader_run(output, outputs_dir, report_id):
                report = _report_reader_run(output, outputs_dir, report_id)
                report['z'] = numpy.array([7, 8, 9])
                return report

            with mock.patch.object(ReportReader, 'run', side_effect=report_reader_run):
                self.assertFalse(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

    def test_SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsMultipleTasksPerSedDocument_is_curated_sed_doc_suitable_for_building_synthetic_archive(self):
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument()

        def get_suitable_sed_doc(sed_docs, case=case):
            specs = {
                'algorithms': [
                    {'kisaoId': {'id': 'KISAO_0000001'}}
                ]
            }
            for location, doc in sed_docs.items():
                if case.is_curated_sed_doc_suitable_for_building_synthetic_archive(specs, doc, location):
                    return location
            return None

        good_doc = SedDocument()
        good_doc.tasks.append(
            Task(
                model=Model(
                    id='model',
                    source='model.xml',
                    language='urn:sedml:language:sbml'
                ),
                simulation=UniformTimeCourseSimulation(
                    algorithm=Algorithm(kisao_id='KISAO_0000001'),
                    initial_time=0.,
                    output_start_time=0.,
                    output_end_time=10.,
                    number_of_points=10,
                ),
            ),
        )
        good_doc.data_generators.append(
            DataGenerator(
                variables=[
                    Variable(
                        id='var_1',
                        task=good_doc.tasks[0]
                    ),
                ],
            ),
        )
        good_doc.outputs.append(
            Report(
                data_sets=[
                    DataSet(data_generator=good_doc.data_generators[0]),
                ],
            ),
        )
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(),
            'loc-2': good_doc,
        }), 'loc-2')

        good_doc.data_generators[0].variables.append(
            Variable(
                id='var_2',
                task=good_doc.tasks[0]
            ),
        )
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(),
            'loc-2': good_doc,
        }), 'loc-2')

        good_doc = SedDocument()
        good_doc.tasks.append(
            Task(
                model=Model(
                    id='model',
                    source='model.xml',
                    language='urn:sedml:language:sbml'
                ),
                simulation=UniformTimeCourseSimulation(
                    algorithm=Algorithm(kisao_id='KISAO_0000001'),
                    initial_time=0.,
                    output_start_time=0.,
                    output_end_time=10.,
                    number_of_points=10,
                ),
            ),
        )
        good_doc.data_generators.append(
            DataGenerator(
                variables=[
                    Variable(
                        id='var_1',
                        task=good_doc.tasks[0]
                    ),
                ],
            ),
        )
        good_doc.data_generators.append(
            DataGenerator(
                variables=[
                    Variable(
                        id='var_2',
                        task=good_doc.tasks[0]
                    ),
                ],
            ),
        )
        good_doc.outputs.append(
            Report(
                data_sets=[
                    DataSet(data_generator=good_doc.data_generators[0]),
                ],
            ),
        )
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(tasks=[Task()]),
            'loc-2': good_doc,
        }), 'loc-2')

        good_doc.outputs[0].data_sets.append(
            DataSet(data_generator=good_doc.data_generators[1]),
        )
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(tasks=[Task()]),
            'loc-2': good_doc,
        }), 'loc-2')

        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(outputs=[Report()]),
            'loc-2': good_doc,
        }), 'loc-2')

        good_doc.tasks[0].model.source = '#'
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(outputs=[Report()]),
            'loc-2': good_doc,
        }), None)

        good_doc.tasks[0].model.source = None
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(outputs=[Report()]),
            'loc-2': good_doc,
        }), None)

        good_doc.tasks[0].model = None
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(outputs=[Report()]),
            'loc-2': good_doc,
        }), None)

    def test_SimulatorSupportsMultipleTasksPerSedDocument_eval_outputs(self):
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument()
        case._expected_reports = [
            ('a.sedml/b', 'a.sedml/b'),
        ]

        with self.assertRaisesRegex(ValueError, 'were not generated'):
            case.eval_outputs(None, None, None, self.dirname)

        report = Report(id='report', data_sets=[DataSet(id='A', label='A'), DataSet(id='B', label='B')])
        data_set_results = DataSetResults({'A': numpy.array([1, 2, 3]), 'B': numpy.array([4, 5, 6])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/b')
        case.eval_outputs(None, None, None, self.dirname)

    def test_SimulatorSupportsMultipleTasksPerSedDocument(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        # no curated cases to use
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument(
            published_projects_test_cases=[])
        with self.assertRaisesRegex(SkippedTestCaseException, 'No curated COMBINE/OMEX archives are available'):
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsMultipleReportsPerSedDocument_eval_outputs(self):
        case = sedml.SimulatorSupportsMultipleReportsPerSedDocument()

        doc = SedDocument(
            outputs=[
                Report(
                    id='report_1',
                    data_sets=[
                        DataSet(id='x', label='x'),
                    ],
                ),
                Report(
                    id='report_2',
                    data_sets=[
                        DataSet(id='y', label='y'),
                    ],
                ),
            ],
        )

        with self.assertRaisesRegex(InvalidOutputsException, 'did not produce the following reports'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        report = doc.outputs[0]
        data_set_results = DataSetResults({'x': numpy.array([1, 2, 3])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_1')
        report = doc.outputs[1]
        data_set_results = DataSetResults({'y': numpy.array([4, 5, 6])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_2')
        self.assertTrue(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

        report = Report(id='report', data_sets=[DataSet(id='z', label='z')])
        data_set_results = DataSetResults({'z': numpy.array([7, 8, 9])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_3')
        with self.assertWarnsRegex(InvalidOutputsWarning, 'extra reports'):
            self.assertFalse(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

    def test_SimulatorSupportsMultipleReportsPerSedDocument(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsMultipleReportsPerSedDocument(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes_build_synthetic_archives(self):
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes()

        archive = CombineArchive(
            contents=[
                CombineArchiveContent(
                    location='./a.sedml',
                    format=CombineArchiveContentFormat.SED_ML,
                ),
            ],
        )

        doc = SedDocument()
        doc.models.append(Model(source='model.xml', language=ModelLanguage.SBML.value))
        doc.simulations.append(
            UniformTimeCourseSimulation(
                algorithm=Algorithm(),
                initial_time=0.,
                output_start_time=0.,
                output_end_time=10.,
                number_of_points=100,
            )
        )

        self.assertFalse(case.is_curated_sed_task_suitable_for_building_synthetic_archive(None, None))
        self.assertFalse(case.is_curated_sed_task_suitable_for_building_synthetic_archive(None, Task(
            simulation=UniformTimeCourseSimulation(initial_time=10.),
            model=doc.models[0],
        )))
        self.assertFalse(case.is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, './a.sedml'))
        self.assertFalse(case.is_curated_archive_suitable_for_building_synthetic_archive(None, archive, {'./a.sedml': doc}))

        doc.tasks.append(Task(model=doc.models[0], simulation=doc.simulations[0]))
        doc.data_generators.append(DataGenerator(
            id='data_gen_x',
            variables=[Variable(id='var_x', task=doc.tasks[0])],
            math='var_x'))
        doc.data_generators.append(DataGenerator(
            id='data_gen_y',
            variables=[Variable(id='var_y', task=doc.tasks[0])],
            math='var_y'))
        doc.outputs.append(Report(
            id='report_1',
            data_sets=[
                DataSet(id='data_set_x', label='x', data_generator=doc.data_generators[0]),
                DataSet(id='data_set_y', label='y', data_generator=doc.data_generators[1]),
            ],
        ))
        sed_docs = {'./a.sedml': doc}

        self.assertTrue(case.is_curated_sed_task_suitable_for_building_synthetic_archive(None, doc.tasks[0]))
        self.assertTrue(case.is_curated_sed_report_suitable_for_building_synthetic_archive(None, doc.outputs[0], None))
        self.assertTrue(case.is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc, './a.sedml'))
        self.assertTrue(case.is_curated_archive_suitable_for_building_synthetic_archive(None, archive, sed_docs))

        case.build_synthetic_archives(None, archive, None, sed_docs)
        self.assertEqual(len(doc.data_generators), 3)
        self.assertEqual(doc.data_generators[-1].variables[0].symbol, Symbol.time)
        self.assertEqual(len(doc.outputs[0].data_sets), 3)
        self.assertEqual(doc.outputs[0].data_sets[-1].data_generator, doc.data_generators[-1])
        self.assertEqual(doc.outputs[0].data_sets[-1].label, '__data_set_time__')

        doc.simulations[0].initial_time = 0.
        doc.simulations[0].output_start_time = 0.
        doc.simulations[0].number_of_points = 100
        doc.outputs[0].data_sets[-1].label = 'time'
        case.build_synthetic_archives(None, archive, None, sed_docs)
        self.assertEqual(doc.outputs[0].data_sets[-1].id, '__data_set_time__')

        doc.outputs[0].data_sets = []
        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(None, doc.outputs[0], None))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes_eval_outputs(self):
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes()

        doc = SedDocument(
            simulations=[
                UniformTimeCourseSimulation(output_start_time=10., output_end_time=20., number_of_points=2),
            ],
            outputs=[
                Report(
                    id='report_1',
                    data_sets=[
                        DataSet(id='__data_set_time__', label='__data_set_time__'),
                    ],
                ),
            ],
        )

        report = doc.outputs[0]

        data_set_results = DataSetResults({'__data_set_time__': numpy.array([10., 15., numpy.nan])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_1')
        with self.assertRaisesRegex(ValueError, 'did not produce the expected time course'):
            with self.assertWarnsRegex(InvalidOutputsWarning, 'include `NaN`'):
                case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({'__data_set_time__': numpy.array([10., 15., 20.])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_1')
        self.assertTrue(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        with mock.patch('biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator',
                        side_effect=Exception('Simulation failed')):
            with self.assertRaises(SkippedTestCaseException):
                self.assertFalse(case.eval(specs, self.dirname))
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsRepeatedTasksWithLinearUniformRanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithLinearUniformRanges(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithLogarithmicUniformRanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithLogarithmicUniformRanges(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithVectorRanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithVectorRanges(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

        # error handling
        doc = SedDocument()
        doc.outputs.append(
            Report(
                id='task_report',
                data_sets=[
                    DataSet(id='A', label='A'),
                    DataSet(id='B', label='B'),
                    DataSet(id='C', label='C'),
                ]
            )
        )
        doc.outputs.append(
            Report(
                id='__repeated_task_report',
                data_sets=[
                    DataSet(id='A', label='A'),
                    DataSet(id='B', label='B'),
                    DataSet(id='C', label='C'),
                ]
            )
        )
        data_set_results = DataSetResults({
            'A': numpy.array(range(0, 50)),
            'B': numpy.array(range(10, 60)),
            'C': numpy.array(range(20, 70)),
        })
        ReportWriter().run(doc.outputs[0], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[0].id)
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'two additional dimensions to reports'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.array([[range(0, 50)] * 2]),
            'B': numpy.array([[range(10, 60)] * 2]),
            'C': numpy.array([[range(20, 70)] * 2]),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'slice for each iteration'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.array([[range(0, 50)] * 2] * 3),
            'B': numpy.array([[range(10, 60)] * 2] * 3),
            'C': numpy.array([[range(20, 70)] * 2] * 3),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'slice for each sub-task'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.array([[[numpy.nan] * 50]] * 3),
            'B': numpy.array([[[numpy.nan] * 50]] * 3),
            'C': numpy.array([[[numpy.nan] * 50]] * 3),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'unexpected NaNs'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.array([[range(0, 50)]] * 3),
            'B': numpy.array([[range(10, 60)]] * 3),
            'C': numpy.array([[range(20, 70)]] * 3),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

    def test_SimulatorSupportsRepeatedTasksWithFunctionalRanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithFunctionalRanges(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithNestedFunctionalRanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithNestedFunctionalRanges(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithFunctionalRangeVariables(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithFunctionalRangeVariables(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

        # test test ignored for non-XML models
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_NON_XML_ARCHIVE_FILENAME)
        case = sedml.SimulatorSupportsRepeatedTasksWithFunctionalRangeVariables(
            published_projects_test_cases=[curated_case])
        with self.assertRaisesRegex(SkippedTestCaseException, 'only implemented for XML-based model'):
            case.eval(specs, self.dirname)

    def test_SimulatorSupportsRepeatedTasksWithMultipleSubTasks(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithMultipleSubTasks(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithChanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithChanges(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        # test test ignored for non-XML models
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_NON_XML_ARCHIVE_FILENAME)
        case = sedml.SimulatorSupportsRepeatedTasksWithChanges(
            published_projects_test_cases=[curated_case])
        with self.assertRaisesRegex(SkippedTestCaseException, 'only implemented for XML-based model'):
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsRepeatedTasksWithNestedRepeatedTasks(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithNestedRepeatedTasks(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithSubTasksOfMixedTypes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithSubTasksOfMixedTypes(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

    def test_SimulatorSupportsRepeatedTasksWithSubTasksOfMixedTypes_eval_outputs(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        case = sedml.SimulatorSupportsRepeatedTasksWithSubTasksOfMixedTypes(
            published_projects_test_cases=[curated_case])

        # error handling
        doc = SedDocument()
        doc.tasks.append(RepeatedTask(sub_tasks=[
            SubTask(order=0, task=Task()),
            SubTask(order=1, task=RepeatedTask()),
        ]))
        doc.outputs.append(
            Report(
                id='task_report',
                data_sets=[
                    DataSet(id='A', label='A'),
                ]
            )
        )
        doc.outputs.append(
            Report(
                id='__repeated_task_report',
                data_sets=[
                    DataSet(id='A', label='A'),
                ]
            )
        )
        data_set_results = DataSetResults({
            'A': numpy.array(range(0, 50)),
        })
        ReportWriter().run(doc.outputs[0], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[0].id)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 2, 50), numpy.nan),
        })
        data_set_results['A'][0, 0, 0:50, 0, 0] = range(0, 50)
        data_set_results['A'][1, 0, 0:50, 0, 0] = range(0, 50)
        for i in range(0, 3):
            for j in range(0, 2):
                data_set_results['A'][0, 1, i, j, 0:50] = range(0, 50)
                data_set_results['A'][1, 1, i, j, 0:50] = range(0, 50)
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((3, 2, 50, 2, 50), numpy.nan),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'slice for each iteration'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 3, 50, 2, 50), numpy.nan),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'slice for each sub-task'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((1, 2, 40, 2, 50), numpy.nan),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'slice for each iteration'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 1, 50), numpy.nan),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'slice for each sub-task'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 2, 60), numpy.nan),
        })
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'output of the basic task'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 2, 50), numpy.nan),
        })
        for i in range(0, 3):
            for j in range(0, 2):
                data_set_results['A'][0, 1, i, j, 0:50] = range(0, 50)
                data_set_results['A'][1, 1, i, j, 0:50] = range(0, 50)
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'unexpected NaNs'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 2, 50), numpy.nan),
        })
        data_set_results['A'][0, 0, 0:50, 0, 0] = range(0, 50)
        data_set_results['A'][0, 0, 0:50, 1, 0] = range(0, 50)
        data_set_results['A'][1, 0, 0:50, 0, 0] = range(0, 50)
        data_set_results['A'][1, 0, 0:50, 1, 0] = range(0, 50)
        for i in range(0, 3):
            for j in range(0, 2):
                data_set_results['A'][0, 1, i, j, 0:50] = range(0, 50)
                data_set_results['A'][1, 1, i, j, 0:50] = range(0, 50)
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'unexpected non-NaNs'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 2, 50), numpy.nan),
        })
        data_set_results['A'][0, 0, 0:50, 0, 0] = range(0, 50)
        data_set_results['A'][1, 0, 0:50, 0, 0] = range(0, 50)
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'unexpected NaNs'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({
            'A': numpy.full((2, 2, 50, 2, 50), numpy.nan),
        })
        data_set_results['A'][0, 0, 0:50, 0, 0] = range(0, 50)
        data_set_results['A'][1, 0, 0:50, 0, 0] = range(0, 50)
        for i in range(0, 3):
            for j in range(0, 2):
                data_set_results['A'][0, 1, i, j, 0:50] = range(0, 50)
                data_set_results['A'][1, 1, i, j, 0:50] = range(0, 50)
        data_set_results['A'][0, 1, 49, 0, 0:50] = range(0, 50)
        data_set_results['A'][1, 1, 49, 0, 0:50] = range(0, 50)
        ReportWriter().run(doc.outputs[1], data_set_results, self.dirname, 'a.sedml/' + doc.outputs[1].id)
        with self.assertRaisesRegex(InvalidOutputsException, 'unexpected non-NaNs'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

    def test_SimulatorProducesLinear2DPlots_is_curated_sed_report_suitable_for_building_synthetic_archive(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)
        curated_case.from_json(self.CURATED_ARCHIVE_FILENAME[0:-5], 'expected-results.json')
        case = sedml.SimulatorProducesLinear2DPlots()
        case._published_projects_test_case = curated_case

        specs = None
        report = Report(id='__report__')
        sed_doc_location = 'sim.sedml'

        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

        report.data_sets.append(
            DataSet(
                data_generator=DataGenerator(
                    variables=[
                        Variable(
                            task=Task(
                                model=Model(
                                    source='model.xml'),
                                simulation=UniformTimeCourseSimulation(
                                    initial_time=0.,
                                    output_start_time=0.,
                                    output_end_time=10.,
                                    number_of_points=10,
                                ),
                            ),
                        ),
                    ],
                ),
            ),
        )
        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

        sed_doc_location, _, report.id = curated_case.expected_reports[0].id.rpartition('/')
        self.assertTrue(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

    def test_SimulatorProducesLinear2DPlots_eval_outputs(self):
        case = sedml.SimulatorProducesLinear2DPlots()

        doc = SedDocument(
            outputs=[
                Plot2D(
                    id='plot_1',
                ),
                Plot2D(
                    id='plot_2',
                ),
            ],
        )

        with self.assertRaisesRegex(SkippedTestCaseException, 'did not produce plots'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plots_path = os.path.join(self.dirname, get_config().PLOTS_PATH)

        with open(plots_path, 'w') as file:
            file.write('not a zip')
        with self.assertRaisesRegex(InvalidOutputsException, 'invalid zip archive'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plot_1_path = os.path.join(self.dirname, 'plot_1.pdf')
        with open(plot_1_path, 'w') as file:
            file.write('not a PDF')
        archive = Archive(
            files=[
                ArchiveFile(archive_path='a.sedml/plot_1.pdf', local_path=plot_1_path)
            ],
        )
        ArchiveWriter().run(archive, plots_path)
        with self.assertRaisesRegex(InvalidOutputsException, 'invalid PDF'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        with open(plot_1_path, 'wb') as file:
            writer = PyPDF2.PdfFileWriter()
            writer.addBlankPage(width=20, height=20)
            writer.write(file)
        ArchiveWriter().run(archive, plots_path)
        with self.assertRaisesRegex(InvalidOutputsException, 'did not produce'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plot_2_path = os.path.join(self.dirname, 'plot_2.pdf')
        with open(plot_2_path, 'wb') as file:
            writer = PyPDF2.PdfFileWriter()
            writer.addBlankPage(width=20, height=20)
            writer.write(file)
        archive.files.append(ArchiveFile(archive_path='a.sedml/plot_2.pdf', local_path=plot_2_path))
        ArchiveWriter().run(archive, plots_path)
        with self.assertRaisesRegex(InvalidOutputsException, 'did not produce data for the following plots'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_set_results = DataSetResults({'x': numpy.array([1, 2, 3])})
        plot = Report(id='plot_1')
        ReportWriter().run(plot, data_set_results, self.dirname, 'a.sedml/plot_1')
        plot = Report(id='plot_2')
        ReportWriter().run(plot, data_set_results, self.dirname, 'a.sedml/plot_2')
        case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plot_3_path = os.path.join(self.dirname, 'plot_3.pdf')
        with open(plot_3_path, 'wb') as file:
            writer = PyPDF2.PdfFileWriter()
            writer.addBlankPage(width=20, height=20)
            writer.write(file)
        archive.files.append(ArchiveFile(archive_path='a.sedml/plot_3.pdf', local_path=plot_3_path))
        ArchiveWriter().run(archive, plots_path)
        case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

    def test_SimulatorProduces3DPlots__axis_scale(self):
        case = sedml.SimulatorProducesLinear3DPlots()
        self.assertEqual(case._axis_scale, AxisScale.linear)

        case = sedml.SimulatorProducesLogarithmic3DPlots()
        self.assertEqual(case._axis_scale, AxisScale.log)

    def test_SimulatorProducesLinear3DPlots_is_curated_sed_report_suitable_for_building_synthetic_archive(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)
        curated_case.from_json(self.CURATED_ARCHIVE_FILENAME[0:-5], 'expected-results.json')
        case = sedml.SimulatorProducesLinear3DPlots()
        case._published_projects_test_case = curated_case

        specs = None
        report = Report(id='__report__')
        sed_doc_location = 'sim.sedml'

        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

        report.data_sets.append(
            DataSet(
                data_generator=DataGenerator(
                    variables=[
                        Variable(
                            task=Task(
                                model=Model(
                                    source='model.xml'),
                                simulation=UniformTimeCourseSimulation(
                                    initial_time=0.,
                                    output_start_time=0.,
                                    output_end_time=10.,
                                    number_of_points=10,
                                ),
                            ),
                        ),
                    ],
                ),
            ),
        )
        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

        sed_doc_location, _, report.id = curated_case.expected_reports[0].id.rpartition('/')
        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

        curated_case.expected_reports[0].points = (10, 2)
        self.assertTrue(case.is_curated_sed_report_suitable_for_building_synthetic_archive(specs, report, sed_doc_location))

    def test_SimulatorProducesLinear3DPlots_build_plots(self):
        case = sedml.SimulatorProducesLinear3DPlots()

        data_generators = [
            DataGenerator()
        ]
        plots = case.build_plots(data_generators)
        self.assertEqual(len(plots), 1)
        self.assertTrue(plots[0].is_equal(Plot3D(
            id='plot_0',
            surfaces=[
                Surface(
                    id='surface_0',
                    x_data_generator=data_generators[0],
                    y_data_generator=data_generators[0],
                    z_data_generator=data_generators[0],
                    x_scale=AxisScale.linear,
                    y_scale=AxisScale.linear,
                    z_scale=AxisScale.linear,
                ),
            ]
        )))

    def test_SimulatorProducesPlots(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)
        curated_case.from_json(self.CURATED_ARCHIVE_FILENAME[0:-5], 'expected-results.json')

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorProducesLinear2DPlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        case = sedml.SimulatorProducesLogarithmic2DPlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        with self.assertRaises(SkippedTestCaseException):
            case = sedml.SimulatorProducesLinear3DPlots(
                published_projects_test_cases=[curated_case])
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        with self.assertRaises(SkippedTestCaseException):
            case = sedml.SimulatorProducesLogarithmic3DPlots(
                published_projects_test_cases=[curated_case])
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        case = sedml.SimulatorProducesMultiplePlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorCanResolveModelSourcesDefinedByUriFragments(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorCanResolveModelSourcesDefinedByUriFragments(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)

    def test_SimulatorCanResolveModelSourcesDefinedByUriFragmentsAndInheritChanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorCanResolveModelSourcesDefinedByUriFragmentsAndInheritChanges(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)

    def test_SimulatorSupportsModelAttributeChanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsModelAttributeChanges(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        # test test ignored for non-XML models
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_NON_XML_ARCHIVE_FILENAME)
        case = sedml.SimulatorSupportsModelAttributeChanges(
            published_projects_test_cases=[curated_case])
        with self.assertRaisesRegex(SkippedTestCaseException, 'only implemented for XML-based model'):
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsComputeModelChanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsComputeModelChanges(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        # test test ignored for non-XML models
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_NON_XML_ARCHIVE_FILENAME)
        case = sedml.SimulatorSupportsComputeModelChanges(
            published_projects_test_cases=[curated_case])
        with self.assertRaisesRegex(SkippedTestCaseException, 'only implemented for XML-based model'):
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsAddReplaceRemoveModelElementChanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsAddReplaceRemoveModelElementChanges(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

        # test test ignored for non-XML models
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_NON_XML_ARCHIVE_FILENAME)
        case = sedml.SimulatorSupportsAddReplaceRemoveModelElementChanges(
            published_projects_test_cases=[curated_case])
        with self.assertRaisesRegex(SkippedTestCaseException, 'only implemented for XML-based model'):
            case.eval(specs, self.dirname)
        if os.path.isdir(self.dirname):
            shutil.rmtree(self.dirname)

    def test_SimulatorSupportsAlgorithmParameters(self):
        specs_path = os.path.join(
            os.path.dirname(__file__), '..', 'fixtures', 'COPASI.specs.json')
        specs = read_simulator_specs(specs_path)
        specs['image']['url'] = 'ghcr.io/biosimulators/biosimulators_copasi/copasi:latest'
        curated_case = SimulatorCanExecutePublishedProject(
            filename=os.path.join(
                os.path.dirname(__file__), '..', '..',
                'examples', 'sbml-core', 'Tomida-EMBO-J-2003-NFAT-translocation.omex'))

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsAlgorithmParameters(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs, self.dirname))

        specs = {'algorithms': []}
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, Algorithm(kisao_id='KISAO_0000001')))

        specs = {'algorithms': [
            {
                'kisaoId': {'id': 'KISAO_0000001'},
                'parameters': [],
            },
        ]}
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, Algorithm(kisao_id='KISAO_0000001')))

        specs = {'algorithms': [
            {
                'kisaoId': {'id': 'KISAO_0000001'},
                'parameters': [{
                    'value': None,
                }],
            },
        ]}
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, Algorithm(kisao_id='KISAO_0000001')))

        specs = {'algorithms': [
            {
                'kisaoId': {'id': 'KISAO_0000001'},
                'parameters': [{
                    'value': '2.0',
                }],
            },
        ]}
        self.assertTrue(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, Algorithm(kisao_id='KISAO_0000001')))

    def test_SimulatorProducesReportsWithCuratedNumberOfDimensions(self):
        # is_curated_sed_algorithm_suitable_for_building_synthetic_archive
        case = sedml.SimulatorProducesReportsWithCuratedNumberOfDimensions()
        specs = {
            'algorithms': []
        }
        alg = Algorithm(kisao_id='KISAO_0000001')
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        specs['algorithms'].append({
            'kisaoId': {'id': 'KISAO_0000002'}
        })
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        specs['algorithms'].append({
            'kisaoId': {'id': 'KISAO_0000001'},
            'dependentDimensions': None,
        })
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        specs['algorithms'].append({
            'kisaoId': {'id': 'KISAO_0000001'},
            'dependentDimensions': [],
        })
        self.assertTrue(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        with mock.patch.object(SyntheticCombineArchiveTestCase,
                               'is_curated_sed_algorithm_suitable_for_building_synthetic_archive', return_value=False):
            self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        # eval_outputs
        specs['algorithms'] = [specs['algorithms'][-1]]
        doc = SedDocument(
            simulations=[mock.Mock(algorithm=alg)],
            outputs=[
                Report(
                    id='report_1',
                    data_sets=[DataSet(id='A', label='A'), DataSet(id='B', label='B'), DataSet(id='C', label='C')],
                ),
            ],
        )

        report = doc.outputs[0]

        data_set_results = DataSetResults({'A': numpy.array(1.), 'B': numpy.array(2.), 'C': numpy.array(3.)})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_1')
        self.assertTrue(case.eval_outputs(specs, None, {'./a.sedml': doc}, self.dirname))

        data_set_results = DataSetResults({'A': numpy.array([1., 2.]), 'B': numpy.array([2., 3.]), 'C': numpy.array([3., 4.])})
        ReportWriter().run(report, data_set_results, self.dirname, 'a.sedml/report_1')
        self.assertFalse(case.eval_outputs(specs, None, {'./a.sedml': doc}, self.dirname))

        # everything
        specs = {
            'image': {'url': self.IMAGE},
            'algorithms': [
                {
                    'kisaoId': {'id': 'KISAO_0000560'},
                    'dependentDimensions': [
                        {'namespace': 'SIO', 'id': 'SIO_time'},
                    ]
                }
            ],
        }
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)
        curated_case.from_json(self.CURATED_ARCHIVE_FILENAME[0:-5], 'expected-results.json')
        case = sedml.SimulatorProducesReportsWithCuratedNumberOfDimensions(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)

    def test_SimulatorSupportsDataGeneratorsWithDifferentShapes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsDataGeneratorsWithDifferentShapes(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)

        case._eval_data_set(numpy.array([1, 3, 4, numpy.nan]), 4, 3)

        with self.assertRaises(InvalidOutputsException):
            case._eval_data_set(numpy.array([1, 3, 4, numpy.nan]), 5, 3)

        with self.assertRaises(InvalidOutputsException):
            case._eval_data_set(numpy.array([1, 3, numpy.nan, numpy.nan]), 4, 3)

        with self.assertRaises(InvalidOutputsException):
            case._eval_data_set(numpy.array([1, 3, 4, 6]), 4, 3)

    def test_SimulatorSupportsDataSetsWithDifferentShapes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsDataSetsWithDifferentShapes(
            published_projects_test_cases=[curated_case])
        case.eval(specs, self.dirname)

        case._eval_data_set('', numpy.array([1, 3, 4, 6]), 4)

        with self.assertRaises(InvalidOutputsException):
            case._eval_data_set('', numpy.array([1, 3, 4, 6]), 5)

        with self.assertRaises(InvalidOutputsException):
            case._eval_data_set('', numpy.array([1, 3, 4, numpy.nan]), 4)

        case._eval_time_data_sets(numpy.array([1, 2, 3]), numpy.array([1, 2, 3]))

        with self.assertRaises(InvalidOutputsException):
            case._eval_time_data_sets(numpy.array([1, 2, 3]), numpy.array([3, 2, 1]))

    def test_SimulatorSupportsSubstitutingAlgorithms(self):
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsSubstitutingAlgorithms(
            published_projects_test_cases=[curated_case])

        specs = {
            'algorithms': [
                {'kisaoId': {'id': 'KISAO_0000019'}}
            ]
        }
        alg = Algorithm(kisao_id='KISAO_0000019')
        self.assertTrue(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        specs = {
            'algorithms': [],
        }
        alg = Algorithm(kisao_id='KISAO_0000019')
        kisao = Kisao()
        cvode = kisao.get_term(alg.kisao_id)
        alt_algs = get_substitutable_algorithms_for_policy(cvode, AlgorithmSubstitutionPolicy.SIMILAR_VARIABLES)
        for alt_alg_id in kisao.get_term_ids(alt_algs):
            specs['algorithms'].append({'kisaoId': {'id': alt_alg_id}})
        self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        specs = {
            'image': {'url': self.IMAGE},
            'algorithms': [
                {'kisaoId': {'id': 'KISAO_0000560'}},
            ]
        }
        case.eval(specs, self.dirname)
