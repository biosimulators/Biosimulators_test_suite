""" Methods for test cases involving manually curated COMBINE/OMEX archives

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..data_model import (TestCase, SedTaskRequirements, ExpectedSedReport, ExpectedSedPlot,
                          AlertType, OutputMedium)
from ..exceptions import InvalidOuputsException, SkippedTestCaseException
from ..warnings import IgnoredTestCaseWarning, SimulatorRuntimeErrorWarning, InvalidOuputsWarning, TestCaseWarning
from .utils import are_array_shapes_equivalent
from biosimulators_utils.combine.data_model import CombineArchive, CombineArchiveContentFormatPattern  # noqa: F401
from biosimulators_utils.combine.io import CombineArchiveReader, CombineArchiveWriter
from biosimulators_utils.config import get_config
from biosimulators_utils.report.data_model import ReportFormat
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import (  # noqa: F401
    Report, Task, UniformTimeCourseSimulation,
    DataGenerator, DataGeneratorVariable, DataGeneratorVariableSymbol, DataSet,
    Model, Simulation, Algorithm)
from biosimulators_utils.sedml.io import SedmlSimulationReader, SedmlSimulationWriter
from biosimulators_utils.sedml.utils import (remove_algorithm_parameter_changes,
                                             replace_complex_data_generators_with_generators_for_individual_variables,
                                             remove_plots)
import biosimulators_utils.archive.io
import biosimulators_utils.simulator.exec
import biosimulators_utils.report.io
import abc
import copy
import datetime
import dateutil.tz
import glob
import json
import numpy
import numpy.testing
import os
import re
import shutil
import tempfile
import warnings

__all__ = [
    'SimulatorCanExecutePublishedProject',
    'SyntheticCombineArchiveTestCase',
    'ConfigurableMasterCombineArchiveTestCase',
    'SingleMasterSedDocumentCombineArchiveTestCase',
    'UniformTimeCourseTestCase',
]

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')


class SimulatorCanExecutePublishedProject(TestCase):
    """ A test case for validating a simulator that involves executing a COMBINE/OMEX archive

    Attributes:
        id (:obj:`str`): id
        name (:obj:`str`): name
        filename (:obj:`str`): path to archive
        task_requirements (:obj:`list` of :obj:`SedTaskRequirements`): list of the required model format and simulation algorithm
            for each task in the COMBINE/OMEX archive
        expected_reports (:obj:`list` of :obj:`ExpectedSedReport`): list of reports expected to be produced by algorithm
        expected_plots (:obj:`list` of :obj:`ExpectedSedPlot`): list of plots expected to be produced by algorithm
        runtime_failure_alert_type (:obj:`AlertType`): whether a run-time failure should be raised as an error or warning
        assert_no_extra_reports (:obj:`bool`): if :obj:`True`, raise an exception if the simulator produces unexpected reports
        assert_no_extra_datasets (:obj:`bool`): if :obj:`True`, raise an exception if the simulator produces unexpected datasets
        assert_no_missing_plots (:obj:`bool`): if :obj:`True`, raise an exception if the simulator doesn't produce the expected plots
        assert_no_extra_plots (:obj:`bool`): if :obj:`True`, raise an exception if the simulator produces unexpected plots
        r_tol (:obj:`float`): relative tolerence
        a_tol (:obj:`float`): absolute tolerence
    """

    def __init__(self, id=None, name=None, filename=None, task_requirements=None, expected_reports=None, expected_plots=None,
                 runtime_failure_alert_type=AlertType.exception,
                 assert_no_extra_reports=False, assert_no_extra_datasets=False, assert_no_missing_plots=False, assert_no_extra_plots=False,
                 r_tol=1e-4, a_tol=0.,
                 output_medium=OutputMedium.console):
        """
        Args:
            id (:obj:`str`, optional): id
            name (:obj:`str`, optional): name
            filename (:obj:`str`, optional): path to archive
            task_requirements (:obj:`list` of :obj:`SedTaskRequirements`, optional): list of the required model format and simulation algorithm
                for each task in the COMBINE/OMEX archive
            expected_reports (:obj:`list` of :obj:`ExpectedSedReport`, optional): list of reports expected to be produced by algorithm
            expected_plots (:obj:`list` of :obj:`ExpectedSedPlot`, optional): list of plots expected to be produced by algorithm
            runtime_failure_alert_type (:obj:`AlertType`, optional): whether a run-time failure should be raised as an error or warning
            assert_no_extra_reports (:obj:`bool`, optional): if :obj:`True`, raise an exception if the simulator produces unexpected reports
            assert_no_extra_datasets (:obj:`bool`, optional): if :obj:`True`, raise an exception if the simulator produces unexpected datasets
            assert_no_missing_plots (:obj:`bool`, optional): if :obj:`True`, raise an exception if the simulator doesn't produce the expected plots
            assert_no_extra_plots (:obj:`bool`, optional): if :obj:`True`, raise an exception if the simulator produces unexpected plots
            r_tol (:obj:`float`, optional): relative tolerence
            a_tol (:obj:`float`, optional): absolute tolerence
            output_medium (:obj:`OutputMedium`, optional): medium the description should be formatted for
        """
        super(SimulatorCanExecutePublishedProject, self).__init__(id, name, output_medium=output_medium)
        self.filename = filename
        self.task_requirements = task_requirements or []
        self.expected_reports = expected_reports or []
        self.expected_plots = expected_plots or []

        self.description = self.get_description()

        self.runtime_failure_alert_type = runtime_failure_alert_type
        self.assert_no_extra_reports = assert_no_extra_reports
        self.assert_no_extra_datasets = assert_no_extra_datasets
        self.assert_no_missing_plots = assert_no_missing_plots
        self.assert_no_extra_plots = assert_no_extra_plots
        self.r_tol = r_tol
        self.a_tol = a_tol

    def get_description(self):
        """ Get a description of the case

        Returns:
            :obj:`str`: description of the case
        """
        task_descriptions = []
        for req in self.task_requirements:
            format = '`{}`'.format(req.model_format)
            alg = '`{}`'.format(req.simulation_algorithm)

            if self.output_medium == OutputMedium.gh_issue:
                format_url = (
                    'https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri='
                    + 'http%3A%2F%2Fedamontology.org%2F'
                    + req.model_format
                )
                alg_url = (
                    'https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri='
                    + 'http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23'
                    + req.simulation_algorithm
                )
                format = '[{}]({})'.format(format, format_url)
                alg = '[{}]({})'.format(alg, alg_url)

            task_descriptions.append(''.join([
                '\n* Format: {}'.format(format),
                '\n  Algorithm: {}'.format(alg),
            ]))
        task_descriptions.sort()
        return 'Required model formats and simulation algorithms for SED tasks:\n' + ''.join(task_descriptions)

    def from_json(self, base_path, filename):
        """ Read test case from JSON file

        Args:
            base_path (:obj:`str`): bath directory for test cases
            filename (:obj:`str`): JSON file relative to :obj:`base_path`

        Returns:
            :obj:`SimulatorCanExecutePublishedProject`: this object
        """
        with open(os.path.join(base_path, filename), 'r') as file:
            data = json.load(file)

        self.id = 'published_project.SimulatorCanExecutePublishedProject' + ':' + os.path.splitext(filename)[0]
        self.name = data['name']
        self.filename = os.path.join(os.path.dirname(os.path.join(base_path, filename)), data['filename'])

        return self.from_dict(data)

    def from_dict(self, data):
        """ Read test case from dictionary

        Args:
            data (:obj:`dict`): dictionary with test case data

        Returns:
            :obj:`SimulatorCanExecutePublishedProject`: this object
        """
        self.task_requirements = []
        for task_req_def in data['taskRequirements']:
            self.task_requirements.append(SedTaskRequirements(
                model_format=task_req_def['modelFormat'],
                simulation_algorithm=task_req_def['simulationAlgorithm'],
            ))

        self.expected_reports = []
        for exp_report_def in data.get('expectedReports', []):
            id = exp_report_def['id']

            data_set_labels = set(exp_report_def.get('dataSets', []))
            points = tuple(exp_report_def['points'])

            values = {}
            for key, val in exp_report_def.get('values', {}).items():
                if isinstance(val, dict):
                    values[key] = {}
                    for k, v in val.items():
                        multi_index = tuple(int(index) for index in k.split(","))
                        try:
                            numpy.ravel_multi_index([multi_index], points)[0]
                        except ValueError:
                            raise ValueError((
                                "Key `{}` of the expected values of report `{}` of published project test case `{}` is invalid. "
                                "Key must be less than or equal to `{}`."
                            ).format(
                                multi_index,
                                self.id,
                                self.id.replace('published_project.SimulatorCanExecutePublishedProject:', ''),
                                tuple(p - 1 for p in points),
                            ))
                        values[key][multi_index] = v
                else:
                    values[key] = numpy.array(val)

            invalid_dataset_ids = set(values.keys()).difference(set(data_set_labels))
            if invalid_dataset_ids:
                raise ValueError((
                    "The keys of the expected values of report `{}` of published project test case `{}` "
                    "should be defined in the 'dataSets' property. "
                    "The following keys were not in the 'dataSets' property:\n  - {}").format(
                    id, self.id.replace('published_project.SimulatorCanExecutePublishedProject:', ''),
                    '\n  - '.join(sorted(invalid_dataset_ids))))

            self.expected_reports.append(ExpectedSedReport(
                id=id,
                data_sets=data_set_labels,
                points=points,
                values=values,
            ))

        self.expected_plots = []
        for exp_plot_def in data.get('expectedPlots', []):
            self.expected_plots.append(ExpectedSedPlot(
                id=exp_plot_def['id'],
            ))

        self.runtime_failure_alert_type = AlertType(data.get('runtimeFailureAlertType', 'exception'))
        self.assert_no_extra_reports = data.get('assertNoExtraReports', False)
        self.assert_no_extra_datasets = data.get('assertNoExtraDatasets', False)
        self.assert_no_missing_plots = data.get('assertNoMissingPlots', False)
        self.assert_no_extra_plots = data.get('assertNoExtraPlots', False)
        self.r_tol = data.get('r_tol', 1e-4)
        self.a_tol = data.get('a_tol', 0.)

        self.description = self.get_description()

        return self

    def compatible_with_specifications(self, specifications):
        # determine if case is applicable to simulator
        for task_reqs in self.task_requirements:
            reqs_satisfied = False
            for alg_specs in specifications['algorithms']:
                if (task_reqs.model_format in set(format['id'] for format in alg_specs['modelFormats'])
                        and task_reqs.simulation_algorithm == alg_specs['kisaoId']['id']):
                    reqs_satisfied = True
                    break

            if not reqs_satisfied:
                return False

        return True

    def eval(self, specifications):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate

        Raises:
            :obj:`SkippedTestCaseException`: if the test case is not applicable to the simulator
            :obj:`Exception`: if the simulator did not pass the test case
        """
        if not self.compatible_with_specifications(specifications):
            model_formats = set()
            simulation_algorithms = set()
            for task_req in self.task_requirements:
                model_formats.add(task_req.model_format)
                simulation_algorithms.add(task_req.simulation_algorithm)
            raise SkippedTestCaseException('Case requires model formats {} and simulation algorithms {}'.format(
                ', '.join(sorted(model_formats)), ', '.join(sorted(simulation_algorithms))))

        # create output directory for case
        out_dir = tempfile.mkdtemp()

        # pull image and execute COMBINE/OMEX archive for case
        try:
            biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator(
                self.filename, out_dir, specifications['image']['url'], pull_docker_image=True)

        except Exception as exception:
            shutil.rmtree(out_dir)
            if self.runtime_failure_alert_type == AlertType.exception:
                raise
            else:
                warnings.warn(str(exception), SimulatorRuntimeErrorWarning)
                return

        # check expected outputs created
        errors = []

        # check expected outputs created: reports
        if not os.path.isfile(os.path.join(out_dir, get_config().H5_REPORTS_PATH)):
            errors.append('No reports were generated')

        else:
            report_reader = biosimulators_utils.report.io.ReportReader()
            for expected_report in self.expected_reports:
                try:
                    report = report_reader.run(out_dir, expected_report.id, format=ReportFormat.h5)
                except Exception:
                    errors.append('Report {} could not be read'.format(expected_report.id))
                    continue

                missing_data_sets = set(expected_report.data_sets).difference(set(report.index))
                if missing_data_sets:
                    errors.append(('Report {} does not contain expected data sets:\n  {}\n\n'
                                   'Report contained these data sets:\n  {}').format(
                        expected_report.id,
                        '\n  '.join(sorted(missing_data_sets)),
                        '\n  '.join(sorted(report.index)),
                    ))
                    continue

                extra_data_sets = set(report.index).difference(set(expected_report.data_sets))
                if extra_data_sets:
                    if self.assert_no_extra_datasets:
                        errors.append('Report {} contains unexpected data sets:\n  {}'.format(
                            expected_report.id, '\n  '.join(sorted(extra_data_sets))))
                        continue
                    else:
                        warnings.warn('Report {} contains unexpected data sets:\n  {}'.format(
                            expected_report.id, '\n  '.join(sorted(extra_data_sets))), InvalidOuputsWarning)

                if not are_array_shapes_equivalent(report.shape[1:], expected_report.points):
                    errors.append('Report {} contains incorrect number of points: {} != {}'.format(
                                  expected_report.id, report.shape[1:], expected_report.points))
                    continue

                for data_set_label, expected_value in expected_report.values.items():
                    if isinstance(expected_value, dict):
                        value = report.loc[data_set_label, :]
                        for el_id, expected_el_value in expected_value.items():
                            el_index = numpy.ravel_multi_index([el_id], value.shape)[0]
                            actual_el_value = value[el_index]
                            try:
                                numpy.testing.assert_allclose(
                                    actual_el_value,
                                    expected_el_value,
                                    rtol=self.r_tol,
                                    atol=self.a_tol,
                                )
                            except AssertionError:
                                errors.append('Data set {} of report {} does not have expected value at {}: {} != {}'.format(
                                    data_set_label, expected_report.id, el_id, actual_el_value, expected_el_value))
                    else:
                        try:
                            numpy.testing.assert_allclose(
                                report.loc[data_set_label, :],
                                expected_value,
                                rtol=self.r_tol,
                                atol=self.a_tol,
                            )
                        except AssertionError:
                            errors.append('Data set {} of report {} does not have expected values'.format(
                                data_set_label, expected_report.id))

            report_ids = report_reader.get_ids(out_dir)
            expected_report_ids = set(report.id for report in self.expected_reports)
            extra_report_ids = report_ids.difference(expected_report_ids)
            if extra_report_ids:
                if self.assert_no_extra_reports:
                    errors.append('Unexpected reports were produced:\n  {}'.format(
                        '\n  '.join(sorted(extra_report_ids))))
                else:
                    warnings.warn('Unexpected reports were produced:\n  {}'.format(
                        '\n  '.join(sorted(extra_report_ids))), InvalidOuputsWarning)

        # check expected outputs created: plots
        if os.path.isfile(os.path.join(out_dir, get_config().PLOTS_PATH)):
            archive = biosimulators_utils.archive.io.ArchiveReader().run(os.path.join(out_dir, 'plots.zip'))
            plot_ids = set(file.archive_path for file in archive.files)
        else:
            plot_ids = set()

        expected_plot_ids = set(plot.id for plot in self.expected_plots)

        missing_plot_ids = expected_plot_ids.difference(plot_ids)
        extra_plot_ids = plot_ids.difference(expected_plot_ids)

        if missing_plot_ids:
            if self.assert_no_missing_plots:
                errors.append('Plots were not produced:\n  {}'.format(
                    '\n  '.join(sorted(missing_plot_ids))))
            else:
                warnings.warn('Plots were not produced:\n  {}'.format(
                    '\n  '.join(sorted(missing_plot_ids))), InvalidOuputsWarning)

        if extra_plot_ids:
            if self.assert_no_extra_plots:
                errors.append('Extra plots were not produced:\n  {}'.format(
                    '\n  '.join(sorted(extra_plot_ids))))
            else:
                warnings.warn('Extra plots were not produced:\n  {}'.format(
                    '\n  '.join(sorted(extra_plot_ids))), InvalidOuputsWarning)

        # cleanup outputs
        shutil.rmtree(out_dir)

        # raise errors
        if errors:
            raise InvalidOuputsException('\n\n'.join(errors))


class SyntheticCombineArchiveTestCase(TestCase):
    """ Test that involves a computationally-generated COMBINE/OMEX archive

    Attributes:
        id (:obj:`str`): id
        name (:obj:`str`): name
        description (:obj:`str`): description
        output_medium (:obj:`OutputMedium`): medium the description should be formatted for
        published_projects_test_cases (:obj:`list` of :obj:`SimulatorCanExecutePublishedProject`):
            curated COMBINE/OMEX archives that can be used to generate example archives for testing
    """

    def __init__(self, id=None, name=None, description=None, output_medium=OutputMedium.console, published_projects_test_cases=None):
        """
        Args:
            id (:obj:`str`, optional): id
            name (:obj:`str`, optional): name
            description (:obj:`str`): description
            output_medium (:obj:`OutputMedium`, optional): medium the description should be formatted for
            published_projects_test_cases (:obj:`list` of :obj:`SimulatorCanExecutePublishedProject`, optional):
                curated COMBINE/OMEX archives that can be used to generate example archives for testing
        """
        super(SyntheticCombineArchiveTestCase, self).__init__(id=id, name=name, description=description, output_medium=output_medium)
        self.published_projects_test_cases = published_projects_test_cases or []

    def eval(self, specifications):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate

        Returns:
            :obj:`object`: data returned by :obj:`eval_outputs`

        Raises:
            :obj:`Exception`: if the simulator did not pass the test case
        """
        temp_dir = tempfile.mkdtemp()

        # read curated archives and find one that is suitable for testing
        suitable_curated_archive = False
        for curated_combine_archive_test_case in self.published_projects_test_cases:
            # read archive
            curated_archive_filename = curated_combine_archive_test_case.filename
            shared_archive_dir = os.path.join(temp_dir, 'archive')
            os.mkdir(shared_archive_dir)

            curated_archive = CombineArchiveReader().run(curated_archive_filename, shared_archive_dir)
            curated_sed_docs = {}
            sedml_reader = SedmlSimulationReader()
            for content in curated_archive.contents:
                if re.match(CombineArchiveContentFormatPattern.SED_ML, content.format):
                    sed_doc = sedml_reader.run(os.path.join(shared_archive_dir, content.location))
                    curated_sed_docs[content.location] = sed_doc

            # see if archive is suitable for testing
            if self.is_curated_archive_suitable_for_building_synthetic_archive(specifications, curated_archive, curated_sed_docs):
                suitable_curated_archive = True
                break

            # cleanup
            shutil.rmtree(shared_archive_dir)

        if not suitable_curated_archive:
            warnings.warn('No curated COMBINE/OMEX archives are available to generate archives for testing',
                          IgnoredTestCaseWarning)
            shutil.rmtree(temp_dir)
            return False

        synthetic_archive_filename = os.path.join(temp_dir, 'archive.omex')
        synthetic_archive, synthetic_sed_docs = self.build_synthetic_archive(
            specifications, curated_archive, shared_archive_dir, curated_sed_docs)
        sedml_writer = SedmlSimulationWriter()
        for location, sed_doc in synthetic_sed_docs.items():
            sedml_writer.run(sed_doc, os.path.join(shared_archive_dir, location))
        CombineArchiveWriter().run(synthetic_archive, shared_archive_dir, synthetic_archive_filename)

        # use synthetic archive to test simulator
        outputs_dir = os.path.join(temp_dir, 'outputs')
        succeeded = False
        try:
            biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator(
                synthetic_archive_filename, outputs_dir, specifications['image']['url'], pull_docker_image=True)

            succeeded = self.eval_outputs(specifications, synthetic_archive, synthetic_sed_docs, outputs_dir)
        finally:
            shutil.rmtree(temp_dir)
        return succeeded

    def is_curated_archive_suitable_for_building_synthetic_archive(self, specifications, archive, sed_docs):
        """ Find an archive with at least one report

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`bool`: :obj:`True`, if the curated archive is suitable for generating a synthetic
                archive for testing
        """
        for location, sed_doc in sed_docs.items():
            if self.is_curated_sed_doc_suitable_for_building_synthetic_archive(specifications, sed_doc):
                return True
        return False

    def is_curated_sed_doc_suitable_for_building_synthetic_archive(self, specifications, sed_doc):
        """ Determine if a SED document is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            sed_doc (:obj:`SedDocument`): SED document in curated archive

        Returns:
            :obj:`bool`: whether the SED document is suitable for testing
        """
        for output in sed_doc.outputs:
            if isinstance(output, Report) and self.is_curated_sed_report_suitable_for_building_synthetic_archive(specifications, output):
                return True

        return False

    def is_curated_sed_report_suitable_for_building_synthetic_archive(self, specifications, report):
        """ Determine if a SED report is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            report (:obj:`Report`): SED report in curated archive

        Returns:
            :obj:`bool`: whether the report is suitable for testing
        """
        task_variables = {}
        for data_set in report.data_sets:
            for variable in data_set.data_generator.variables:
                if variable.task not in task_variables:
                    task_variables[variable.task] = set()
                task_variables[variable.task].add(variable.id)

        for task, variables in task_variables.items():
            if len(variables) >= 1 and self.is_curated_sed_task_suitable_for_building_synthetic_archive(specifications, task):
                return True

        return False

    def is_curated_sed_task_suitable_for_building_synthetic_archive(self, specifications, task):
        """ Determine if a SED task is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            task (:obj:`Task`): SED task in curated archive

        Returns:
            :obj:`bool`: whether the task is suitable for testing
        """
        if not isinstance(task, Task):
            return False

        if not self.is_curated_sed_model_suitable_for_building_synthetic_archive(specifications, task.model):
            return False

        if not self.is_curated_sed_simulation_suitable_for_building_synthetic_archive(specifications, task.simulation):
            return False

        return True

    def is_curated_sed_model_suitable_for_building_synthetic_archive(self, specifications, model):
        """ Determine if a SED model is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            model (:obj:`Model`): SED model in curated archive

        Returns:
            :obj:`bool`: whether the model is suitable for testing
        """
        return True

    def is_curated_sed_simulation_suitable_for_building_synthetic_archive(self, specifications, simulation):
        """ Determine if a SED simulation is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            simulation (:obj:`Simulation`): SED simulation in curated archive

        Returns:
            :obj:`bool`: whether the simulation is suitable for testing
        """
        if isinstance(simulation, UniformTimeCourseSimulation):
            if (
                simulation.initial_time != 0
                or simulation.output_start_time != 0
                or simulation.number_of_points <= 0
                or int(simulation.number_of_points / 2) != simulation.number_of_points / 2
            ):
                return False
        return self.is_curated_sed_algorithm_suitable_for_building_synthetic_archive(specifications, simulation.algorithm)

    def is_curated_sed_algorithm_suitable_for_building_synthetic_archive(self, specifications, algorithm):
        """ Determine if a SED algorithm is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            algorithm (:obj:`Algorithm`): SED algorithm in curated archive

        Returns:
            :obj:`bool`: whether the algorithm is suitable for testing
        """
        return True

    def build_synthetic_archive(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive for testing

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

        # set updated times because libCOMBINE requires this
        now = self.get_current_time_utc()
        curated_archive.updated = now
        for content in curated_archive.contents:
            content.updated = now

        return (curated_archive, curated_sed_docs)

    def get_current_time_utc(self):
        """ Get the current time in UTC

        Returns:
            :obj:`datetime.datetime`: current time in UTC
        """
        now = datetime.datetime.now()
        return datetime.datetime(now.year, now.month, now.day, now.hour, now.minute, now.second, tzinfo=dateutil.tz.tzutc())

    @abc.abstractmethod
    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive
        """
        pass  # pragma: no cover


def find_cases(specifications, dir_name=None, output_medium=OutputMedium.console):
    """ Collect test cases

    Args:
        specifications (:obj:`dict`): specifications of the simulator to validate
        dir_name (:obj:`str`, optional): path to find example COMBINE/OMEX archives
        output_medium (:obj:`OutputMedium`, optional): medium the description should be formatted for

    Returns:
        :obj:`list` of :obj:`SimulatorCanExecutePublishedProject`: test cases
    """
    if dir_name is None:
        dir_name = EXAMPLES_DIR
    if not os.path.isdir(dir_name):
        warnings.warn('Directory of example COMBINE/OMEX archives is not available', IgnoredTestCaseWarning)

    all_cases = []
    compatible_cases = []
    for md_filename in glob.glob(os.path.join(dir_name, '**/*.json'), recursive=True):
        rel_filename = os.path.relpath(md_filename, dir_name)
        case = SimulatorCanExecutePublishedProject(output_medium=output_medium).from_json(dir_name, rel_filename)
        all_cases.append(case)
        if case.compatible_with_specifications(specifications):
            compatible_cases.append(case)

    # return cases
    return (all_cases, compatible_cases)


class ConfigurableMasterCombineArchiveTestCase(SyntheticCombineArchiveTestCase):
    """ Class for generating synthetic archives with a single master SED-ML file or two non-master
    copies of the same file

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should have a master file
        _include_non_master (:obj:`bool`): whether the synthetic archive should also have a non-master file
        _types_of_model_changes_to_keep (:obj:`list` of :obj:`type`): types of model changes to keep
        _remove_algorithm_parameter_changes (:obj:`bool`): if :obj:`True`, remove instructions to change
            the values of the parameters of algorithms
        _use_single_variable_data_generators (:obj:`bool`): if :obj:`True`, replace data generators that
            involve multiple variables or parameters (and data sets, curves, and surfaces) with multiple
            data generators for each variable
        _remove_plots (:obj:`bool`): if :obj:`True`, remove plots
        _keep_one_task_one_report (:obj:`bool`): if :obj:`True`, keep only 1 task and only 1 report
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    @property
    @abc.abstractmethod
    def _archive_has_master(self):
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def _include_non_master(self):
        pass  # pragma: no cover

    def __init__(self, *args, **kwargs):
        super(ConfigurableMasterCombineArchiveTestCase, self).__init__(*args, **kwargs)
        self._types_of_model_changes_to_keep = ()
        self._remove_algorithm_parameter_changes = True
        self._use_single_variable_data_generators = True
        self._remove_plots = True
        self._keep_one_task_one_report = True

    def build_synthetic_archive(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with master and non-master SED documents

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
        super(ConfigurableMasterCombineArchiveTestCase, self).build_synthetic_archive(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # get a suitable SED document to modify
        for doc_location, doc in curated_sed_docs.items():
            if self.is_curated_sed_doc_suitable_for_building_synthetic_archive(specifications, doc):
                break
        doc_content = next(content for content in curated_archive.contents if content.location == doc_location)

        # remove all other SED documents from archive
        original_contents = curated_archive.contents
        curated_archive.contents = []
        for content in original_contents:
            if content == doc_content or content.location not in curated_sed_docs:
                curated_archive.contents.append(content)

        # make all content not master
        for content in curated_archive.contents:
            content.master = False

        # make document master
        doc_content.master = self._archive_has_master

        # retain some model changes
        for model in doc.models:
            model.changes = [change for change in model.changes if isinstance(change, self._types_of_model_changes_to_keep)]

        # remove algorithm parameter changes
        if self._remove_algorithm_parameter_changes:
            remove_algorithm_parameter_changes(doc)

        # replace data generator that involve mathematical expressions with multiple data generators for each individual variable
        if self._use_single_variable_data_generators:
            replace_complex_data_generators_with_generators_for_individual_variables(doc)

        # remove plots
        if self._remove_plots:
            remove_plots(doc)

        # keep only single task and single report
        if self._keep_one_task_one_report and self._use_single_variable_data_generators and self._remove_plots:
            key_report = None
            key_task = None
            for report in doc.outputs:
                if self.is_curated_sed_report_suitable_for_building_synthetic_archive(specifications, report):
                    for data_set in report.data_sets:
                        task = data_set.data_generator.variables[0].task
                        if self.is_curated_sed_task_suitable_for_building_synthetic_archive(specifications, task):
                            key_report = report
                            key_task = task
                            break
                    if key_report:
                        break

            doc.models = [key_task.model]
            doc.simulations = [key_task.simulation]
            doc.tasks = [key_task]
            doc.data_generators = [data_gen for data_gen in doc.data_generators if data_gen.variables[0].task == key_task]
            doc.outputs = [key_report]
            key_report.data_sets = [data_set for data_set in key_report.data_sets if data_set.data_generator in doc.data_generators]

        curated_sed_docs = {
            doc_content.location: doc,
        }

        # duplicate document
        if self._include_non_master:
            doc_content_copy = copy.deepcopy(doc_content)
            doc_content_copy.master = False
            doc_content_copy.location = os.path.join(
                os.path.dirname(doc_content_copy.location),
                '__copy__' + os.path.basename(doc_content_copy.location))
            curated_archive.contents.append(doc_content_copy)

            curated_sed_docs[doc_content_copy.location] = copy.deepcopy(doc)

        self._expected_report_ids = []
        for output in doc.outputs:
            if isinstance(output, Report):
                self._expected_report_ids.append(os.path.join(os.path.relpath(doc_content.location, './'), output.id))
                if not self._archive_has_master and self._include_non_master:
                    self._expected_report_ids.append(os.path.join(os.path.relpath(doc_content_copy.location, './'), output.id))

        # return modified SED document
        return (curated_archive, curated_sed_docs)


class SingleMasterSedDocumentCombineArchiveTestCase(ConfigurableMasterCombineArchiveTestCase):
    """ Class for generating synthetic COMBINE/OMEX archives with a single master SED-ML file

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
        _include_non_master (:obj:`bool`): whether the synthetic archive should also have a non-master file
    """

    @property
    def _archive_has_master(self):
        return True

    @property
    def _include_non_master(self):
        return False


class UniformTimeCourseTestCase(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports multiple reports per SED document """

    def is_curated_sed_task_suitable_for_building_synthetic_archive(self, specifications, task):
        """ Determine if a SED task is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            task (:obj:`Task`): SED task in curated archive

        Returns:
            :obj:`bool`: whether the task is suitable for testing
        """
        if not super(UniformTimeCourseTestCase, self) \
                .is_curated_sed_task_suitable_for_building_synthetic_archive(specifications, task):
            return False

        sim = task.simulation
        return (
            isinstance(sim, UniformTimeCourseSimulation)
            and sim.initial_time == 0
            and sim.output_start_time == 0
            and int(sim.number_of_points / 2) == sim.number_of_points / 2
        )

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
        curated_archive, curated_sed_docs = super(UniformTimeCourseTestCase, self).build_synthetic_archive(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # get a suitable SED document to modify
        doc = list(curated_sed_docs.values())[0]
        task = doc.tasks[0]
        sim = task.simulation
        self.modify_simulation(sim)
        report = doc.outputs[0]

        time_data_set = False
        for data_gen in doc.data_generators:
            var = data_gen.variables[0]
            if var.symbol == DataGeneratorVariableSymbol.time:
                for data_set in report.data_sets:
                    if data_set.data_generator == data_gen:
                        time_data_set = True
                        data_set.label = '__data_set_time__'
                        break
            if time_data_set:
                break

        if not time_data_set:
            doc.data_generators.append(
                DataGenerator(
                    id='__data_generator_time__',
                    variables=[
                        DataGeneratorVariable(
                            id='__variable_time__',
                            task=task,
                            symbol=DataGeneratorVariableSymbol.time,
                        ),
                    ],
                    math='__variable_time__',
                ),
            )
            report.data_sets.append(
                DataSet(
                    id='__data_set_time__',
                    label='__data_set_time__',
                    data_generator=doc.data_generators[-1],
                )
            )

        # return modified SED document
        return (curated_archive, curated_sed_docs)

    @abc.abstractmethod
    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        pass  # pragma: no cover

    @property
    def report_error_as_warning(self):
        return False

    def eval(self, specifications):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate

        Returns:
            :obj:`object`: data returned by :obj:`eval_outputs`

        Raises:
            :obj:`Exception`: if the simulator did not pass the test case
        """
        try:
            return_value = super(UniformTimeCourseTestCase, self).eval(specifications)
        except Exception as exception:
            if self.report_error_as_warning:
                warnings.warn(str(exception), TestCaseWarning)
                return_value = False
            else:
                raise

        return return_value

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

        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')
        doc = list(synthetic_sed_docs.values())[0]
        sim = doc.simulations[0]
        report = doc.outputs[0]

        data = ReportReader().run(outputs_dir, os.path.join(doc_id, report.id))

        if numpy.any(numpy.isnan(data)):
            warnings.warn('The results produced by the simulator include `NaN`.', InvalidOuputsWarning)
            has_warnings = True

        try:
            numpy.testing.assert_allclose(
                data.loc['__data_set_time__', :],
                numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1),
                rtol=1e-4,
            )
        except Exception as exception:
            raise ValueError('Simulator did not produce the expected time course:\n\n  {}'.format(
                str(exception).replace('\n', '\n  ')))

        return not has_warnings
