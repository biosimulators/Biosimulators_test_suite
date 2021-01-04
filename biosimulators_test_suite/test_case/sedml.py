""" Methods for testing that simulators support the features of SED-ML

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""
from ..exceptions import InvalidOuputsException
from ..warnings import InvalidOuputsWarning
from .published_project import SingleMasterSedDocumentCombineArchiveTestCase, UniformTimeCourseTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.archive.io import ArchiveReader
from biosimulators_utils.config import get_config
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import (SedDocument, Output, Report, Plot2D, Plot3D,  DataGenerator,  # noqa: F401
                                                  DataGeneratorVariable, UniformTimeCourseSimulation,
                                                  DataSet, Curve, Surface, AxisScale,
                                                  Model, ModelAttributeChange, AlgorithmParameterChange)
import abc
import copy
import numpy
import os
import PyPDF2
import shutil
import tempfile
import warnings

__all__ = [
    'SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports',
    'SimulatorSupportsModelAttributeChanges',
    'SimulatorSupportsAlgorithmParameters',
    'SimulatorProducesReportsWithCuratedNumberOfDimensions',
    'SimulatorSupportsMultipleTasksPerSedDocument',
    'SimulatorSupportsMultipleReportsPerSedDocument',
    'SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes',
    'SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes',
    'SimulatorProducesLinear2DPlots',
    'SimulatorProducesLogarithmic2DPlots',
    'SimulatorProducesLinear3DPlots',
    'SimulatorProducesLogarithmic3DPlots',
    'SimulatorProducesMultiplePlots',
]


class SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports the core elements of SED: models, simulations, tasks, data generators for
    individual variables, and reports
    """

    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive

        Returns:
            :obj:`bool`: :obj:`True`, if succeeded without warnings
        """
        has_warnings = False

        # reports
        try:
            report_ids = ReportReader().get_ids(outputs_dir)
        except Exception:
            report_ids = []

        expected_report_ids = set()
        for doc_location, doc in synthetic_sed_docs.items():
            doc_id = os.path.relpath(doc_location, './')
            for output in doc.outputs:
                if isinstance(output, Report):
                    expected_report_ids.add(os.path.join(doc_id, output.id))

        missing_report_ids = expected_report_ids.difference(set(report_ids))
        extra_report_ids = set(report_ids).difference(expected_report_ids)

        if missing_report_ids:
            raise InvalidOuputsException('Simulator did not produce the following reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_report_ids))
            ))

        if extra_report_ids:
            msg = 'Simulator produced extra reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_report_ids)))
            warnings.warn(msg, InvalidOuputsWarning)
            has_warnings = True

        # data sets
        expected_data_set_labels = set()
        data_set_labels = set()
        for doc_location, doc in synthetic_sed_docs.items():
            doc_id = os.path.relpath(doc_location, './')
            for output in doc.outputs:
                if isinstance(output, Report):
                    for data_set in output.data_sets:
                        expected_data_set_labels.add(os.path.join(doc_id, output.id, data_set.label))

                    results = ReportReader().run(outputs_dir, os.path.join(doc_id, output.id))
                    data_set_labels.update(set(os.path.join(doc_id, output.id, label) for label in results.index))

        missing_data_set_labels = expected_data_set_labels.difference(set(data_set_labels))
        extra_data_set_labels = set(data_set_labels).difference(expected_data_set_labels)

        if missing_data_set_labels:
            raise InvalidOuputsException('Simulator did not produce the following data sets:\n  - {}'.format(
                '\n  - '.join(sorted('`' + label + '`' for label in missing_data_set_labels))
            ))

        if extra_data_set_labels:
            msg = 'Simulator produced extra data sets:\n  - {}'.format(
                '\n  - '.join(sorted('`' + label + '`' for label in extra_data_set_labels)))
            warnings.warn(msg, InvalidOuputsWarning)
            has_warnings = True

        return not has_warnings


class SimulatorSupportsModelAttributeChanges(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator supports changes to the attributes of model elements
    """

    def __init__(self, *args, **kwargs):
        super(SimulatorSupportsModelAttributeChanges, self).__init__(*args, **kwargs)
        self._types_of_model_changes_to_keep = (ModelAttributeChange,)

    def is_curated_sed_model_suitable_for_building_synthetic_archive(self, specifications, model):
        """ Determine if a SED model is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            model (:obj:`Model`): SED task in curated archive

        Returns:
            :obj:`bool`: whether the model is suitable for testing
        """
        return next((True for change in model.changes if isinstance(change, ModelAttributeChange)), False)


class SimulatorSupportsAlgorithmParameters(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator supports setting the values of parameters of algorithms """

    def is_curated_sed_algorithm_suitable_for_building_synthetic_archive(self, specifications, algorithm):
        """ Determine if a SED algorithm is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            algorithm (:obj:`Algorithm`): SED algorithm in curated archive

        Returns:
            :obj:`bool`: whether the algorithm is suitable for testing
        """
        for alg_specs in specifications['algorithms']:
            if alg_specs['kisaoId']['id'] == algorithm.kisao_id:
                for param_spec in alg_specs['parameters']:
                    if param_spec['value'] is not None:
                        return True

        return False

    def build_synthetic_archive(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with a copy of each task and each report

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`tuple`:

                * :obj:`CombineArchive`: synthetic COMBINE/OMEX archive for testing the simulator
                * :obj:`dict` of :obj:`str` to :obj:`SedDocument`: map from locations to
                  SED documents in synthetic archive
        """
        curated_archive, curated_sed_docs = super(SimulatorSupportsAlgorithmParameters, self).build_synthetic_archive(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # set algorithm parameters
        doc = list(curated_sed_docs.values())[0]

        algorithm = doc.simulations[0].algorithm

        for alg_specs in specifications['algorithms']:
            if alg_specs['kisaoId']['id'] == algorithm.kisao_id:
                if alg_specs['parameters']:
                    break

        algorithm.changes = []
        for param_spec in alg_specs['parameters']:
            if param_spec['value'] is not None:
                algorithm.changes.append(
                    AlgorithmParameterChange(
                        kisao_id=param_spec['kisaoId']['id'],
                        new_value=param_spec['value'],
                    )
                )

        return (curated_archive, curated_sed_docs)


class SimulatorProducesReportsWithCuratedNumberOfDimensions(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that that the curated number of output dimensions matches the actual number of output dimensions
    """

    def is_curated_sed_algorithm_suitable_for_building_synthetic_archive(self, specifications, algorithm):
        """ Determine if a SED algorithm is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            algorithm (:obj:`Algorithm`): SED algorithm in curated archive

        Returns:
            :obj:`bool`: whether the algorithm is suitable for testing
        """
        if not (super(SimulatorProducesReportsWithCuratedNumberOfDimensions, self).
                is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specifications, algorithm)):
            return False

        for alg_specs in specifications['algorithms']:
            if alg_specs['kisaoId']['id'] == algorithm.kisao_id:
                if alg_specs.get('dependentDimensions', None) is not None:
                    return True

        return False

    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive
        """
        doc = list(synthetic_sed_docs.values())[0]
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')

        report = doc.outputs[0]
        data = ReportReader().run(outputs_dir, os.path.join(doc_id, report.id))

        for alg_specs in specifications['algorithms']:
            if alg_specs['kisaoId']['id'] == doc.simulations[0].algorithm.kisao_id:
                break

        expected_dims = alg_specs['dependentDimensions']

        if numpy.squeeze(data).ndim != 1 + len(expected_dims):
            msg = ('The specifications for the number of dimensions of each data set of algorithm `{}` differs '
                   'from the actual number of dimensions, {} != {}.').format(
                doc.simulations[0].algorithm.kisao_id, data.ndim - 1, len(expected_dims))
            warnings.warn(msg, InvalidOuputsWarning)
            return False
        else:
            return True


class SimulatorSupportsMultipleTasksPerSedDocument(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports multiple tasks per SED document

    Attributes:
        _expected_reports (:obj:`list` of :obj:`tuple` of :obj:`str`): list of pairs of
            original reports and their expected duplicates
    """

    def build_synthetic_archive(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with a copy of each task and each report

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`tuple`:

                * :obj:`CombineArchive`: synthetic COMBINE/OMEX archive for testing the simulator
                * :obj:`dict` of :obj:`str` to :obj:`SedDocument`: map from locations to
                  SED documents in synthetic archive
        """
        curated_archive, curated_sed_docs = super(SimulatorSupportsMultipleTasksPerSedDocument, self).build_synthetic_archive(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # get a suitable SED document to modify
        location = list(curated_sed_docs.keys())[0]
        doc_id = os.path.relpath(location, './')
        sed_doc = curated_sed_docs[location]

        # duplicate tasks and reports
        copy_tasks = {}
        for task in list(sed_doc.tasks):
            copy_task = copy.copy(task)
            copy_task.id += '__test_suite_copy'
            sed_doc.tasks.append(copy_task)
            copy_tasks[task.id] = copy_task

        self._expected_reports = []
        copy_data_gens = {}
        for output in list(sed_doc.outputs):
            if isinstance(output, Report):
                copy_output = Report(id=output.id + '__test_suite_copy')
                sed_doc.outputs.append(copy_output)

                self._expected_reports.append((
                    os.path.join(doc_id, output.id),
                    os.path.join(doc_id, copy_output.id)))

                for data_set in output.data_sets:
                    copy_data_set = DataSet(id=data_set.id + '__test_suite_copy', label=data_set.label)
                    copy_output.data_sets.append(copy_data_set)

                    data_gen = data_set.data_generator
                    copy_data_gen_id = data_gen.id + '__test_suite_copy'
                    copy_data_gen = copy_data_gens.get(copy_data_gen_id, None)
                    if not copy_data_gen:
                        copy_data_gen = DataGenerator(id=copy_data_gen_id, parameters=data_gen.parameters, math=data_gen.math)
                        sed_doc.data_generators.append(copy_data_gen)

                        for var in data_set.data_generator.variables:
                            copy_var = DataGeneratorVariable(id=var.id, target=var.target, symbol=var.symbol, model=var.model)
                            copy_var.task = copy_tasks[var.task.id]
                            copy_data_gen.variables.append(copy_var)
                    copy_data_set.data_generator = copy_data_gen

        # return modified SED document
        return (curated_archive, curated_sed_docs)

    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive
        """
        try:
            report_ids = ReportReader().get_ids(outputs_dir)
        except Exception:
            report_ids = []

        missing_reports = []
        for report_loc, copy_report_loc in self._expected_reports:
            if report_loc not in report_ids:
                missing_reports.append(report_loc)
            if copy_report_loc not in report_ids:
                missing_reports.append(copy_report_loc)

        if missing_reports:
            raise ValueError('Reports for duplicate tasks were not generated:\n  {}'.format(
                '\n  '.join(sorted(missing_reports))))


class SimulatorSupportsMultipleReportsPerSedDocument(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports multiple reports per SED document """

    def build_synthetic_archive(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with a copy of each task and each report

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`tuple`:

                * :obj:`CombineArchive`: synthetic COMBINE/OMEX archive for testing the simulator
                * :obj:`dict` of :obj:`str` to :obj:`SedDocument`: map from locations to
                  SED documents in synthetic archive
        """
        curated_archive, curated_sed_docs = super(SimulatorSupportsMultipleReportsPerSedDocument, self).build_synthetic_archive(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # get a suitable SED document to modify
        sed_doc = list(curated_sed_docs.values())[0]

        # divide data sets between two reports
        original_data_sets = sed_doc.outputs[0].data_sets
        sed_doc.outputs = [
            Report(id='report_1'),
            Report(id='report_2'),
        ]

        for i_dataset, data_set in enumerate(original_data_sets):
            sed_doc.outputs[i_dataset % 2].data_sets.append(data_set)

        # to ensure that each report has at least one data set, including when there's only 1 data set total
        sed_doc.outputs[1].data_sets.append(original_data_sets[0])

        # return modified SED document
        return (curated_archive, curated_sed_docs)

    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive
        """
        has_warnings = False

        try:
            report_ids = ReportReader().get_ids(outputs_dir)
        except Exception:
            report_ids = []

        doc_location = os.path.relpath(list(synthetic_sed_docs.keys())[0], './')
        expected_report_ids = set([os.path.join(doc_location, 'report_1'), os.path.join(doc_location, 'report_2')])

        missing_report_ids = expected_report_ids.difference(set(report_ids))
        extra_report_ids = set(report_ids).difference(expected_report_ids)

        if missing_report_ids:
            raise InvalidOuputsException('Simulator did not produce the following reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_report_ids))
            ))

        if extra_report_ids:
            msg = 'Simulator produced extra reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_report_ids)))
            warnings.warn(msg, InvalidOuputsWarning)
            has_warnings = True

        return not has_warnings


class SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes(UniformTimeCourseTestCase):
    """ Test that a simulator supports time courses with non-zero output start times """

    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        simulation.output_start_time = simulation.output_end_time / 2
        simulation.number_of_points = int(simulation.number_of_points / 2)


class SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes(UniformTimeCourseTestCase):
    """ Test that a simulator supports multiple time courses with non-zero initial times """

    @property
    def report_error_as_warning(self):
        return True

    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        simulation.initial_time = simulation.output_end_time / 2
        simulation.output_start_time = simulation.output_end_time / 2
        simulation.number_of_points = int(simulation.number_of_points / 2)


class SimulatorProducesPlotsTestCase(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator produces plots """

    @property
    def _num_plots(self):
        return 1

    @property
    @abc.abstractmethod
    def _axis_scale(self):
        pass  # pragma: no cover

    def build_synthetic_archive(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with a copy of each task and each report

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`tuple`:

                * :obj:`CombineArchive`: synthetic COMBINE/OMEX archive for testing the simulator
                * :obj:`dict` of :obj:`str` to :obj:`SedDocument`: map from locations to
                  SED documents in synthetic archive
        """
        curated_archive, curated_sed_docs = super(SimulatorProducesPlotsTestCase, self).build_synthetic_archive(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # get a suitable SED document to modify
        doc = list(curated_sed_docs.values())[0]

        # replace report with plot(s)
        doc.outputs = self.build_plots(doc.data_generators)

        # return modified SED document
        return (curated_archive, curated_sed_docs)

    @abc.abstractmethod
    def build_plots(self, data_generators):
        """ Build plots from the defined data generators

        Args:
            data_generators (:obj:`list` of :obj:`DataGenerator`): data generators

        Returns:
            :obj:`list` of :obj:`Output`: plots
        """
        pass  # pragma: no cover

    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive
        """
        plots_path = os.path.join(outputs_dir, get_config().PLOTS_PATH)
        if not os.path.isfile(plots_path):
            warnings.warn('Simulator did not produce plots', InvalidOuputsWarning)
            return

        tempdir = tempfile.mkdtemp()
        try:
            archive = ArchiveReader().run(plots_path, tempdir)
        except Exception:
            shutil.rmtree(tempdir)
            raise InvalidOuputsException('Simulator produced an invalid zip archive of plots')

        for file in archive.files:
            with open(file.local_path, 'rb') as file:
                try:
                    PyPDF2.PdfFileReader(file)
                except Exception:
                    shutil.rmtree(tempdir)
                    raise InvalidOuputsException('Simulator produced an invalid PDF plot')

        doc = list(synthetic_sed_docs.values())[0]
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')

        expected_plot_ids = set(os.path.join(doc_id, output.id + '.pdf') for output in doc.outputs)
        plot_ids = set(os.path.relpath(file.archive_path, './') for file in archive.files)

        missing_plot_ids = expected_plot_ids.difference(plot_ids)
        extra_plot_ids = plot_ids.difference(expected_plot_ids)

        if missing_plot_ids:
            shutil.rmtree(tempdir)
            raise InvalidOuputsException('Simulator did not produce the following plots:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_plot_ids))
            ))

        if extra_plot_ids:
            msg = 'Simulator produced extra plots:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_plot_ids)))
            warnings.warn(msg, InvalidOuputsWarning)

        shutil.rmtree(tempdir)


class SimulatorProduces2DPlotsTestCase(SimulatorProducesPlotsTestCase):
    """ Test that a simulator produces 2D plots """

    def build_plots(self, data_generators):
        """ Build plots from the defined data generators

        Args:
            data_generators (:obj:`list` of :obj:`DataGenerator`): data generators

        Returns:
            :obj:`list` of :obj:`Output`: plots
        """
        plots = []
        for i in range(self._num_plots):
            plots.append(Plot2D(id='plot_' + str(i)))

        for i_data_generator, data_generator in enumerate(data_generators):
            plots[i_data_generator % self._num_plots].curves.append(
                Curve(
                    id='curve_' + str(i_data_generator),
                    x_data_generator=data_generator,
                    y_data_generator=data_generator,
                    x_scale=self._axis_scale,
                    y_scale=self._axis_scale,
                ),
            )

        return plots


class SimulatorProduces3DPlotsTestCase(SimulatorProducesPlotsTestCase):
    """ Test that a simulator produces 3D plots """

    def build_plots(self, data_generators):
        """ Build plots from the defined data generators

        Args:
            data_generators (:obj:`list` of :obj:`DataGenerator`): data generators

        Returns:
            :obj:`list` of :obj:`Output`: plots
        """
        plots = []
        for i in range(self._num_plots):
            plots.append(Plot3D(id='plot_' + str(i)))

        for i_data_generator, data_generator in enumerate(data_generators):
            plots[i_data_generator % self._num_plots].surfaces.append(
                Surface(
                    id='surface_' + str(i_data_generator),
                    x_data_generator=data_generator,
                    y_data_generator=data_generator,
                    z_data_generator=data_generator,
                    x_scale=self._axis_scale,
                    y_scale=self._axis_scale,
                    z_scale=self._axis_scale,
                ),
            )

        return plots


class SimulatorProducesLinear2DPlots(SimulatorProduces2DPlotsTestCase):
    """ Test that a simulator produces linear 2D plots """

    @property
    def _axis_scale(self):
        return AxisScale.linear


class SimulatorProducesLogarithmic2DPlots(SimulatorProduces2DPlotsTestCase):
    """ Test that a simulator produces logarithmic 2D plots """

    @property
    def _axis_scale(self):
        return AxisScale.log


class SimulatorProducesLinear3DPlots(SimulatorProduces3DPlotsTestCase):
    """ Test that a simulator produces linear 3D plots """

    @property
    def _axis_scale(self):
        return AxisScale.linear


class SimulatorProducesLogarithmic3DPlots(SimulatorProduces3DPlotsTestCase):
    """ Test that a simulator produces logarithmic 3D plots """

    @property
    def _axis_scale(self):
        return AxisScale.log


class SimulatorProducesMultiplePlots(SimulatorProduces2DPlotsTestCase):
    """ Test that a simulator produces multiple plots """

    @property
    def _num_plots(self):
        return 2

    @property
    def _axis_scale(self):
        return AxisScale.linear
