from biosimulators_test_suite.exceptions import InvalidOuputsException
from biosimulators_test_suite.test_case import sedml
from biosimulators_test_suite.test_case.published_project import SimulatorCanExecutePublishedProject, SyntheticCombineArchiveTestCase
from biosimulators_test_suite.warnings import IgnoredTestCaseWarning, InvalidOuputsWarning
from biosimulators_utils.archive.data_model import Archive, ArchiveFile
from biosimulators_utils.archive.io import ArchiveWriter
from biosimulators_utils.config import get_config
from biosimulators_utils.combine.data_model import CombineArchive, CombineArchiveContent, CombineArchiveContentFormat
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import (SedDocument, Task, Report, DataSet,
                                                  DataGenerator, DataGeneratorVariable, UniformTimeCourseSimulation,
                                                  Algorithm, DataGeneratorVariableSymbol, Model,
                                                  Plot2D, Curve)
from biosimulators_utils.simulator.io import read_simulator_specs
from unittest import mock
import numpy
import os
import pandas
import PyPDF2
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

    def test_SimulatorSupportsMultipleTasksPerSedDocument_is_curated_sed_doc_suitable_for_building_synthetic_archive(self):
        case = sedml.SimulatorSupportsMultipleTasksPerSedDocument()

        def get_suitable_sed_doc(sed_docs, case=case):
            specs = {
                'algorithms': [
                    {'kisaoId': {'id': 'KISAO_0000001'}}
                ]
            }
            for location, doc in sed_docs.items():
                if case.is_curated_sed_doc_suitable_for_building_synthetic_archive(specs, doc):
                    return location
            return None

        good_doc = SedDocument()
        good_doc.tasks.append(Task(simulation=UniformTimeCourseSimulation(
            algorithm=Algorithm(kisao_id='KISAO_0000001'),
            initial_time=0.,
            output_start_time=0.,
            output_end_time=10.,
            number_of_points=10)))
        good_doc.data_generators.append(
            DataGenerator(
                variables=[
                    DataGeneratorVariable(
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
            DataGeneratorVariable(
                id='var_2',
                task=good_doc.tasks[0]
            ),
        )
        self.assertEqual(get_suitable_sed_doc({
            'loc-1': SedDocument(),
            'loc-2': good_doc,
        }), 'loc-2')

        good_doc = SedDocument()
        good_doc.tasks.append(Task(simulation=UniformTimeCourseSimulation(
            algorithm=Algorithm(kisao_id='KISAO_0000001'),
            initial_time=0.,
            output_start_time=0.,
            output_end_time=10.,
            number_of_points=10)))
        good_doc.data_generators.append(
            DataGenerator(
                variables=[
                    DataGeneratorVariable(
                        id='var_1',
                        task=good_doc.tasks[0]
                    ),
                ],
            ),
        )
        good_doc.data_generators.append(
            DataGenerator(
                variables=[
                    DataGeneratorVariable(
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

    def test_SimulatorSupportsMultipleReportsPerSedDocument_eval_outputs(self):
        case = sedml.SimulatorSupportsMultipleReportsPerSedDocument()

        doc = SedDocument(
            outputs=[
                Report(
                    id='report_1',
                    data_sets=[
                        DataSet(label='x'),
                    ],
                ),
                Report(
                    id='report_2',
                    data_sets=[
                        DataSet(label='y'),
                    ],
                ),
            ],
        )

        with self.assertRaisesRegex(InvalidOuputsException, 'did not produce the following reports'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_frame = pandas.DataFrame(numpy.array([[1, 2, 3]]), index=['x'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_1')
        data_frame = pandas.DataFrame(numpy.array([[4, 5, 6]]), index=['y'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_2')
        self.assertTrue(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

        data_frame = pandas.DataFrame(numpy.array([[7, 8, 9]]), index=['z'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_3')
        with self.assertWarnsRegex(InvalidOuputsWarning, 'extra reports'):
            self.assertFalse(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

    def test_SimulatorSupportsMultipleReportsPerSedDocument(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsMultipleReportsPerSedDocument(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes_build_synthetic_archive(self):
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes()

        now = case.get_current_time_utc()
        archive = CombineArchive(
            contents=[
                CombineArchiveContent(
                    location='./a.sedml',
                    format=CombineArchiveContentFormat.SED_ML,
                    updated=now,
                ),
            ],
            updated=now,
        )

        doc = SedDocument()
        doc.models.append(Model())
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
        )))
        self.assertFalse(case.is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc))
        self.assertFalse(case.is_curated_archive_suitable_for_building_synthetic_archive(None, archive, {'./a.sedml': doc}))

        doc.tasks.append(Task(model=doc.models[0], simulation=doc.simulations[0]))
        doc.data_generators.append(DataGenerator(
            id='data_gen_x',
            variables=[DataGeneratorVariable(id='var_x', task=doc.tasks[0])],
            math='var_x'))
        doc.data_generators.append(DataGenerator(
            id='data_gen_y',
            variables=[DataGeneratorVariable(id='var_y', task=doc.tasks[0])],
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
        self.assertTrue(case.is_curated_sed_report_suitable_for_building_synthetic_archive(None, doc.outputs[0]))
        self.assertTrue(case.is_curated_sed_doc_suitable_for_building_synthetic_archive(None, doc))
        self.assertTrue(case.is_curated_archive_suitable_for_building_synthetic_archive(None, archive, sed_docs))

        case.build_synthetic_archive(None, archive, None, sed_docs)
        self.assertEqual(len(doc.data_generators), 3)
        self.assertEqual(doc.data_generators[-1].variables[0].symbol, DataGeneratorVariableSymbol.time)
        self.assertEqual(len(doc.outputs[0].data_sets), 3)
        self.assertEqual(doc.outputs[0].data_sets[-1].data_generator, doc.data_generators[-1])
        self.assertEqual(doc.outputs[0].data_sets[-1].label, '__data_set_time__')

        doc.simulations[0].initial_time = 0.
        doc.simulations[0].output_start_time = 0.
        doc.simulations[0].number_of_points = 100
        doc.outputs[0].data_sets[-1].label = 'time'
        case.build_synthetic_archive(None, archive, None, sed_docs)
        self.assertEqual(doc.outputs[0].data_sets[-1].label, '__data_set_time__')

        doc.outputs[0].data_sets = []
        self.assertFalse(case.is_curated_sed_report_suitable_for_building_synthetic_archive(None, doc.outputs[0]))

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
                        DataSet(label='__data_set_time__'),
                    ],
                ),
            ],
        )

        data_frame = pandas.DataFrame(numpy.array([[10., 15., numpy.nan]]), index=['__data_set_time__'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_1')
        with self.assertRaisesRegex(ValueError, 'did not produce the expected time course'):
            with self.assertWarnsRegex(InvalidOuputsWarning, 'include `NaN`'):
                case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        data_frame = pandas.DataFrame(numpy.array([[10., 15., 20.]]), index=['__data_set_time__'])
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_1')
        self.assertTrue(case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))

    def test_SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))

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

        with self.assertWarnsRegex(InvalidOuputsWarning, 'did not produce plots'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plots_path = os.path.join(self.dirname, get_config().PLOTS_PATH)

        with open(plots_path, 'w') as file:
            file.write('not a zip')
        with self.assertRaisesRegex(InvalidOuputsException, 'invalid zip archive'):
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
        with self.assertRaisesRegex(InvalidOuputsException, 'invalid PDF'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        with open(plot_1_path, 'wb') as file:
            writer = PyPDF2.PdfFileWriter()
            writer.addBlankPage(width=20, height=20)
            writer.write(file)
        ArchiveWriter().run(archive, plots_path)
        with self.assertRaisesRegex(InvalidOuputsException, 'did not produce'):
            case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plot_2_path = os.path.join(self.dirname, 'plot_2.pdf')
        with open(plot_2_path, 'wb') as file:
            writer = PyPDF2.PdfFileWriter()
            writer.addBlankPage(width=20, height=20)
            writer.write(file)
        archive.files.append(ArchiveFile(archive_path='a.sedml/plot_2.pdf', local_path=plot_2_path))
        ArchiveWriter().run(archive, plots_path)
        case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

        plot_3_path = os.path.join(self.dirname, 'plot_3.pdf')
        with open(plot_3_path, 'wb') as file:
            writer = PyPDF2.PdfFileWriter()
            writer.addBlankPage(width=20, height=20)
            writer.write(file)
        archive.files.append(ArchiveFile(archive_path='a.sedml/plot_3.pdf', local_path=plot_3_path))
        ArchiveWriter().run(archive, plots_path)
        case.eval_outputs(None, None, {'./a.sedml': doc}, self.dirname)

    def test_SimulatorProducesPlots(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorProducesLinear2DPlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

        case = sedml.SimulatorProducesLogarithmic2DPlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

        case = sedml.SimulatorProducesLinear3DPlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

        case = sedml.SimulatorProducesLogarithmic3DPlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

        case = sedml.SimulatorProducesMultiplePlots(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

    def test_SimulatorSupportsModelAttributeChanges(self):
        specs = {'image': {'url': self.IMAGE}}
        curated_case = SimulatorCanExecutePublishedProject(filename=self.CURATED_ARCHIVE_FILENAME)

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsModelAttributeChanges(
            published_projects_test_cases=[curated_case])
        case.eval(specs)

    def test_SimulatorSupportsAlgorithmParameters(self):
        specs_path = os.path.join(
            os.path.dirname(__file__), '..', 'fixtures', 'COPASI.specs.json')
        specs = read_simulator_specs(specs_path)
        curated_case = SimulatorCanExecutePublishedProject(
            filename=os.path.join(
                os.path.dirname(__file__), '..', '..',
                'examples', 'sbml-core', 'Tomida-EMBO-J-2003-NFAT-translocation.omex'))

        # test synthetic case generated and used to test simulator
        case = sedml.SimulatorSupportsAlgorithmParameters(
            published_projects_test_cases=[curated_case])
        self.assertTrue(case.eval(specs))

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

        with mock.patch.object(SyntheticCombineArchiveTestCase, 'is_curated_sed_algorithm_suitable_for_building_synthetic_archive', return_value=False):
            self.assertFalse(case.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specs, alg))

        # eval_outputs
        specs['algorithms'] = [specs['algorithms'][-1]]
        doc = SedDocument(
            simulations=[mock.Mock(algorithm=alg)],
            outputs=[
                Report(
                    id='report_1',
                ),
            ],
        )

        data = numpy.array([numpy.array(1.), numpy.array(2.), numpy.array(3.), ])
        index = ['A', 'B', 'C']
        data_frame = pandas.DataFrame(data, index=index)
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_1')
        self.assertTrue(case.eval_outputs(specs, None, {'./a.sedml': doc}, self.dirname))

        data = numpy.array([numpy.array([1., 2.]), numpy.array([2., 3.]), numpy.array([3., 4.]), ])
        index = ['A', 'B', 'C']
        data_frame = pandas.DataFrame(data, index=index)
        ReportWriter().run(data_frame, self.dirname, 'a.sedml/report_1')
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
        case = sedml.SimulatorProducesReportsWithCuratedNumberOfDimensions(
            published_projects_test_cases=[curated_case])
        case.eval(specs)
