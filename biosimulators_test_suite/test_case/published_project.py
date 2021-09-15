""" Methods for test cases involving manually curated COMBINE/OMEX archives

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..config import Config
from ..data_model import (TestCase, SedTaskRequirements, ExpectedSedReport, ExpectedSedDataSet, ExpectedSedPlot,
                          AlertType, OutputMedium)
from ..exceptions import InvalidOutputsException, SkippedTestCaseException, TimeoutException, TestCaseException
from ..utils import get_singularity_image_filename, simulation_results_isnan
from ..warnings import IgnoredTestCaseWarning, SimulatorRuntimeErrorWarning, InvalidOutputsWarning
from .utils import are_array_shapes_equivalent
from biosimulators_utils.combine.data_model import CombineArchive, CombineArchiveContentFormatPattern  # noqa: F401
from biosimulators_utils.combine.io import CombineArchiveReader, CombineArchiveWriter
from biosimulators_utils.config import get_config
from biosimulators_utils.image import convert_docker_image_to_singularity
from biosimulators_utils.report.data_model import ReportFormat
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import (  # noqa: F401
    Report, Task, UniformTimeCourseSimulation,
    DataGenerator, Variable, Symbol, DataSet,
    Model, ModelLanguagePattern, Simulation, Algorithm)
from biosimulators_utils.sedml.io import SedmlSimulationReader, SedmlSimulationWriter
from biosimulators_utils.sedml.utils import (remove_algorithm_parameter_changes,
                                             replace_complex_data_generators_with_generators_for_individual_variables,
                                             remove_plots)
import biosimulators_utils.archive.io
import biosimulators_utils.simulator.exec
import biosimulators_utils.report.io
import abc
import glob
import json
import numpy
import numpy.testing
import os
import re
import shutil
import subprocess
import types  # noqa: F401
import warnings

__all__ = [
    'SimulatorCanExecutePublishedProject',
    'SyntheticCombineArchiveTestCase',
    'ExpectedResultOfSyntheticArchive',
    'find_cases',
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
        skipped_simulators (:obj:`list` of :obj:`str`): list of simulation tools to not test the COMBINE archive with
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

    def __init__(self, id=None, name=None, filename=None,
                 task_requirements=None, skipped_simulators=None,
                 expected_reports=None, expected_plots=None,
                 runtime_failure_alert_type=AlertType.exception,
                 assert_no_extra_reports=False, assert_no_extra_datasets=False,
                 assert_no_missing_plots=False, assert_no_extra_plots=False,
                 r_tol=1e-4, a_tol=0.,
                 output_medium=OutputMedium.console):
        """
        Args:
            id (:obj:`str`, optional): id
            name (:obj:`str`, optional): name
            filename (:obj:`str`, optional): path to archive
            task_requirements (:obj:`list` of :obj:`SedTaskRequirements`, optional): list of the required model format and simulation algorithm
                for each task in the COMBINE/OMEX archive
            skipped_simulators (:obj:`list` of :obj:`str`, optional): list of simulation tools to not test the COMBINE archive with
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
        self.skipped_simulators = skipped_simulators or []
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

        id = filename.replace(os.sep + 'expected-results.json', '')
        self.id = 'published_project.SimulatorCanExecutePublishedProject' + ':' + id
        self.name = data['name']
        self.filename = os.path.join(
            base_path,
            os.path.relpath(os.path.join(os.path.dirname(filename), '..', data['filename']), '.'))

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
                model_format_features=set(task_req_def.get('modelFormatFeatures', [])),
                simulation_algorithm=task_req_def['simulationAlgorithm'],
            ))

        self.skipped_simulators = [simulator['id'] for simulator in data['skippedSimulators']]

        self.expected_reports = []
        for exp_report_def in data.get('expectedReports', []):
            id = exp_report_def['id']

            data_sets = [ExpectedSedDataSet(id=data_set.get('id', None), label=data_set.get('label', None))
                         for data_set in exp_report_def.get('dataSets', [])]
            data_set_ids = [data_set.id for data_set in data_sets]
            points = tuple(exp_report_def['points'])

            values = {}
            for labelVal in exp_report_def.get('values', []):
                data_set_id = labelVal['id']
                val = labelVal['value']
                if isinstance(val, dict):
                    values[data_set_id] = {}
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
                        values[data_set_id][multi_index] = v
                else:
                    values[data_set_id] = numpy.array(val)

            invalid_dataset_ids = set(values.keys()).difference(set(data_set_ids))
            if invalid_dataset_ids:
                raise ValueError((
                    "The `id` fields of the expected values of report `{}` of published project test case `{}` "
                    "should be defined in the 'dataSets' property. "
                    "The following keys were not in the 'dataSets' property:\n  - {}").format(
                    id, self.id.replace('published_project.SimulatorCanExecutePublishedProject:', ''),
                    '\n  - '.join(sorted(invalid_dataset_ids))))

            self.expected_reports.append(ExpectedSedReport(
                id=id,
                data_sets=data_sets,
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
        if specifications.get('id', None) in self.skipped_simulators:
            return False

        for task_reqs in self.task_requirements:
            reqs_satisfied = False
            for alg_specs in specifications['algorithms']:
                format_reqs_satisfied = False
                for format in alg_specs['modelFormats']:
                    if (
                        task_reqs.model_format == format['id']
                        and task_reqs.model_format_features == set(format.get('supportedFeatures', []) or [])
                    ):
                        format_reqs_satisfied = True
                        break
                if not format_reqs_satisfied:
                    break

                if task_reqs.simulation_algorithm == alg_specs['kisaoId']['id']:
                    reqs_satisfied = True
                    break

            if not reqs_satisfied:
                return False

        return True

    def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            working_dirname (:obj:`str`): directory for temporary files for evaluating test case
            synthetic_archives_dir (:obj:`str`, optional): Directory to save the synthetic COMBINE/OMEX archives
                generated by the test cases
            dry_run (:obj:`bool`): if :obj:`True`, do not use the simulator to execute COMBINE/OMEX archives.
            cli (:obj:`str`, optional): command-line interface to use to execute the tests involving the simulation of COMBINE/OMEX
                archives rather than a Docker image

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

        if dry_run:
            return

        if not os.path.isdir(working_dirname):
            os.makedirs(working_dirname)

        # pull image and execute COMBINE/OMEX archive for case
        try:
            self.exec_sedml_docs_in_archive(specifications, working_dirname, cli=cli)

        except Exception as exception:
            if os.path.isdir(working_dirname) and os.getenv('CI', 'false').lower() in ['1', 'true']:
                subprocess.run(['sudo', 'chown', '{}:{}'.format(os.getuid(), os.getgid()), '-R', working_dirname], check=True)

            if self.runtime_failure_alert_type == AlertType.exception:
                raise
            else:
                warnings.warn(str(exception), SimulatorRuntimeErrorWarning)
                return

        # check expected outputs created
        errors = []

        # check expected outputs created: reports
        if not os.path.isfile(os.path.join(working_dirname, get_config().H5_REPORTS_PATH)):
            errors.append('No reports were generated')

        else:
            report_reader = biosimulators_utils.report.io.ReportReader()
            for expected_report in self.expected_reports:
                report = Report()
                for data_set in expected_report.data_sets:
                    report.data_sets.append(DataSet(id=data_set.id, label=data_set.label))
                try:
                    report_results = report_reader.run(report, working_dirname, expected_report.id, format=ReportFormat.h5)
                except Exception:
                    errors.append('Report {} could not be read'.format(expected_report.id))
                    continue

                missing_data_sets = set([data_set.id for data_set in expected_report.data_sets]).difference(set(report_results.keys()))
                if missing_data_sets:
                    errors.append(('Report {} does not contain expected data sets:\n  {}\n\n'
                                   'Report contained these data sets:\n  {}').format(
                        expected_report.id,
                        '\n  '.join(sorted(missing_data_sets)),
                        '\n  '.join(sorted(report_results.keys())),
                    ))
                    continue

                points = report_results[report.data_sets[0].id].shape
                if not are_array_shapes_equivalent(points, expected_report.points):
                    errors.append('Report {} contains incorrect number of points: {} != {}'.format(
                                  expected_report.id, points, expected_report.points))
                    continue

                for data_set_id, expected_value in expected_report.values.items():
                    if isinstance(expected_value, dict):
                        value = report_results[data_set_id]
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
                                    data_set_id, expected_report.id, el_id, actual_el_value, expected_el_value))
                    else:
                        try:
                            numpy.testing.assert_allclose(
                                report_results[data_set_id],
                                expected_value,
                                rtol=self.r_tol,
                                atol=self.a_tol,
                            )
                        except AssertionError:
                            errors.append('Data set {} of report {} does not have expected values'.format(
                                data_set_id, expected_report.id))

            report_ids = set(report_reader.get_ids(working_dirname))
            expected_report_ids = set(report.id for report in self.expected_reports)
            extra_report_ids = report_ids.difference(expected_report_ids)
            if extra_report_ids:
                if self.assert_no_extra_reports:
                    errors.append('Unexpected reports were produced:\n  {}'.format(
                        '\n  '.join(sorted(extra_report_ids))))
                else:
                    warnings.warn('Unexpected reports were produced:\n  {}'.format(
                        '\n  '.join(sorted(extra_report_ids))), InvalidOutputsWarning)

        # check expected outputs created: plots
        if os.path.isfile(os.path.join(working_dirname, get_config().PLOTS_PATH)):
            archive = biosimulators_utils.archive.io.ArchiveReader().run(os.path.join(working_dirname, 'plots.zip'))
            plot_ids = set(os.path.splitext(file.archive_path)[0] for file in archive.files)
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
                    '\n  '.join(sorted(missing_plot_ids))), InvalidOutputsWarning)

        if extra_plot_ids:
            if self.assert_no_extra_plots:
                errors.append('Extra plots were produced:\n  {}'.format(
                    '\n  '.join(sorted(extra_plot_ids))))
            else:
                warnings.warn('Extra plots were produced:\n  {}'.format(
                    '\n  '.join(sorted(extra_plot_ids))), InvalidOutputsWarning)

        # raise errors
        if errors:
            raise InvalidOutputsException('\n\n'.join(errors))

    def exec_sedml_docs_in_archive(self, specifications, out_dir, cli=None):
        """
        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            out_dir (:obj:`str`): path to save simulation results
            cli (:obj:`str`, optional): command-line interface to use to execute the tests involving the simulation of COMBINE/OMEX
                archives rather than a Docker image
        """
        config = Config()
        pull_docker_image = config.pull_docker_image
        user_to_exec_within_container = config.user_to_exec_in_simulator_containers
        if os.getenv('CI', 'false').lower() in ['1', 'true']:
            user_to_exec_within_container = '_SUDO_'

        if cli:
            biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_simulator_cli(
                self.filename, out_dir, cli)

        else:
            biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator(
                self.filename, out_dir, specifications['image']['url'], pull_docker_image=pull_docker_image,
                user_to_exec_within_container=user_to_exec_within_container)

            if os.path.isdir(out_dir) and os.getenv('CI', 'false').lower() in ['1', 'true']:
                subprocess.run(['sudo', 'chown', '{}:{}'.format(os.getuid(), os.getgid()), '-R', out_dir], check=True)


class SyntheticCombineArchiveTestCase(TestCase):
    """ Test that involves a computationally-generated COMBINE/OMEX archive

    Attributes:
        id (:obj:`str`): id
        name (:obj:`str`): name
        description (:obj:`str`): description
        output_medium (:obj:`OutputMedium`): medium the description should be formatted for
        published_projects_test_cases (:obj:`list` of :obj:`SimulatorCanExecutePublishedProject`):
            curated COMBINE/OMEX archives that can be used to generate example archives for testing
        _published_projects_test_case (:obj:`SimulatorCanExecutePublishedProject`): COMBINE/OMEX archive
            that is used to generate example archives for testing
    """

    EXEC_WITH_SINGULARITY = False
    REPORT_ERROR_AS_SKIP = False

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
        self._published_projects_test_case = None

    def eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            working_dirname (:obj:`str`): directory for temporary files for evaluating test case
            synthetic_archives_dir (:obj:`str`, optional): Directory to save the synthetic COMBINE/OMEX archives
                generated by the test cases
            dry_run (:obj:`bool`): if :obj:`True`, do not use the simulator to execute COMBINE/OMEX archives.
            cli (:obj:`str`, optional): command-line interface to use to execute the tests involving the simulation of COMBINE/OMEX
                archives rather than a Docker image

        Returns:
            :obj:`bool`: whether there were no warnings about the outputs

        Raises:
            :obj:`Exception`: if the simulator did not pass the test case
        """
        try:
            return_value = self._eval(specifications, working_dirname,
                                      synthetic_archives_dir=synthetic_archives_dir, dry_run=dry_run, cli=cli)
        except Exception as exception:
            if not isinstance(exception, TimeoutException) and self.REPORT_ERROR_AS_SKIP:
                raise SkippedTestCaseException(str(exception))
            else:
                raise

        return return_value

    def _eval(self, specifications, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
        """ Evaluate a simulator's performance on a test case

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            working_dirname (:obj:`str`): directory for temporary files for evaluating test case
            synthetic_archives_dir (:obj:`str`, optional): Directory to save the synthetic COMBINE/OMEX archives
                generated by the test cases
            dry_run (:obj:`bool`): if :obj:`True`, do not use the simulator to execute COMBINE/OMEX archives.
            cli (:obj:`str`, optional): command-line interface to use to execute the tests involving the simulation of COMBINE/OMEX
                archives rather than a Docker image

        Returns:
            :obj:`bool`: whether there were no warnings about the outputs

        Raises:
            :obj:`Exception`: if the simulator did not pass the test case
        """
        if not os.path.isdir(working_dirname):
            os.makedirs(working_dirname)

        # read curated archives and find one that is suitable for testing
        suitable_curated_archive = False
        for published_projects_test_case in self.published_projects_test_cases:
            self._published_projects_test_case = published_projects_test_case

            # read archive
            curated_archive_filename = published_projects_test_case.filename
            shared_archive_dir = os.path.join(working_dirname, 'archive')
            if not os.path.isdir(shared_archive_dir):
                os.makedirs(shared_archive_dir)

            curated_archive = CombineArchiveReader().run(curated_archive_filename, shared_archive_dir)
            curated_sed_docs = {}
            sedml_reader = SedmlSimulationReader()
            for content in list(curated_archive.contents):
                if content.format and re.match(CombineArchiveContentFormatPattern.SED_ML, content.format):
                    sed_doc = sedml_reader.run(os.path.join(shared_archive_dir, content.location))
                    curated_sed_docs[content.location] = sed_doc

                # remove manifest from contents because libSED-ML occassionally has trouble with this
                elif (
                    content.location in ['manifest.xml', './manifest.xml']
                    and content.format == 'http://identifiers.org/combine.specifications/omex-manifest'
                ):
                    curated_archive.contents.remove(content)
                    os.remove(os.path.join(shared_archive_dir, content.location))

            # see if archive is suitable for testing
            if self.is_curated_archive_suitable_for_building_synthetic_archive(specifications, curated_archive, curated_sed_docs):
                suitable_curated_archive = True
                break

            # cleanup
            shutil.rmtree(shared_archive_dir)

        if not suitable_curated_archive:
            raise SkippedTestCaseException('No curated COMBINE/OMEX archives are available to generate archives for testing')

        expected_results_of_synthetic_archives = self.build_synthetic_archives(
            specifications, curated_archive, shared_archive_dir, curated_sed_docs)
        has_warnings = False
        for i_archive, expected_results_of_synthetic_archive in enumerate(expected_results_of_synthetic_archives):
            if self._eval_synthetic_archive(specifications, expected_results_of_synthetic_archive, shared_archive_dir,
                                            i_archive, os.path.join(working_dirname, str(i_archive + 1)),
                                            synthetic_archives_dir=synthetic_archives_dir, dry_run=dry_run,
                                            cli=cli):
                has_warnings = True
        return not has_warnings

    def _eval_synthetic_archive(self, specifications, expected_results_of_synthetic_archive, shared_archive_dir,
                                i_synthetic_archive, working_dirname, synthetic_archives_dir=None, dry_run=False, cli=None):
        synthetic_archive = expected_results_of_synthetic_archive.archive
        synthetic_sed_docs = expected_results_of_synthetic_archive.sed_documents
        is_success_expected = expected_results_of_synthetic_archive.is_success_expected
        environment = expected_results_of_synthetic_archive.environment

        if not os.path.isdir(working_dirname):
            os.makedirs(working_dirname)

        sedml_writer = SedmlSimulationWriter()
        synthetic_archive_filename = os.path.join(working_dirname, 'archive.omex')
        for location, sed_doc in synthetic_sed_docs.items():
            sedml_writer.run(sed_doc, os.path.join(shared_archive_dir, location))
        CombineArchiveWriter().run(synthetic_archive, shared_archive_dir, synthetic_archive_filename)

        if synthetic_archives_dir:
            cls = self.__class__
            module = cls.__module__.partition('biosimulators_test_suite.test_case.')[2]
            export_synthetic_archive_dirname = os.path.join(synthetic_archives_dir, module, cls.__name__)
            if not os.path.isdir(export_synthetic_archive_dirname):
                os.makedirs(export_synthetic_archive_dirname)
            export_synthetic_archive_filename = os.path.join(export_synthetic_archive_dirname,
                                                             '{}.{}.omex'.format(
                                                                 str(i_synthetic_archive + 1),
                                                                 'execution-should-succeed'
                                                                 if is_success_expected else
                                                                 'execute-should-fail'))
            shutil.copy(synthetic_archive_filename, export_synthetic_archive_filename)

        if dry_run:
            return False

        # use synthetic archive to test simulator
        outputs_dir = os.path.join(working_dirname, 'outputs')
        config = Config()
        pull_docker_image = config.pull_docker_image
        user_to_exec_within_container = config.user_to_exec_in_simulator_containers
        has_warnings = False
        try:
            if os.getenv('CI', 'false').lower() in ['1', 'true']:
                user_to_exec_within_container = '_SUDO_'

            if cli:
                biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_simulator_cli(
                    synthetic_archive_filename, outputs_dir, cli, environment=environment)

            elif self.EXEC_WITH_SINGULARITY:
                docker_image_url = specifications['image']['url']

                # get path for Singularity image
                singularity_filename = get_singularity_image_filename(docker_image_url)

                # convert image to Singularity format
                convert_docker_image_to_singularity(docker_image_url, singularity_filename=singularity_filename)

                # run a simulation with the Singularity image
                if not os.path.isdir(outputs_dir):
                    os.makedirs(outputs_dir)
                temp_filename = os.path.join(outputs_dir, os.path.basename(synthetic_archive_filename))
                shutil.copyfile(synthetic_archive_filename, temp_filename)

                cmd = [
                    'singularity', 'run',
                    '-B', outputs_dir + ':/root',
                    singularity_filename,
                    '-i', '/root/' + os.path.basename(synthetic_archive_filename),
                    '-o', '/root',
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                os.remove(temp_filename)
                if result.returncode != 0:
                    msg = 'The Docker image could not be successfully executed as a Singularity image:\n  {}'.format(
                        result.stderr.decode().replace('\n', '\n  '))
                    raise TestCaseException(msg)

            else:
                biosimulators_utils.simulator.exec.exec_sedml_docs_in_archive_with_containerized_simulator(
                    synthetic_archive_filename, outputs_dir, specifications['image']['url'], pull_docker_image=pull_docker_image,
                    environment=environment,
                    user_to_exec_within_container=user_to_exec_within_container)

            if os.path.isdir(outputs_dir) and os.getenv('CI', 'false').lower() in ['1', 'true']:
                subprocess.run(['sudo', 'chown', '{}:{}'.format(os.getuid(), os.getgid()), '-R', outputs_dir], check=True)

            if not self.eval_outputs(specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
                has_warnings = True

            succeeded = True

        except Exception:
            if os.path.isdir(outputs_dir) and os.getenv('CI', 'false').lower() in ['1', 'true']:
                subprocess.run(['sudo', 'chown', '{}:{}'.format(os.getuid(), os.getgid()), '-R', outputs_dir], check=True)

            succeeded = False
            if is_success_expected:
                raise

        if succeeded and not is_success_expected:
            msg = 'The execution of the COMBINE/OMEX archive did not fail as expected'
            raise ValueError(msg)

        return has_warnings

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
            if self.is_curated_sed_doc_suitable_for_building_synthetic_archive(specifications, sed_doc, location):
                return True
        return False

    def is_curated_sed_doc_suitable_for_building_synthetic_archive(self, specifications, sed_doc, sed_doc_location):
        """ Determine if a SED document is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            sed_doc (:obj:`SedDocument`): SED document in curated archive
            sed_doc_location (:obj:`str`): location of the SED document within its parent COMBINE/OMEX archive

        Returns:
            :obj:`bool`: whether the SED document is suitable for testing
        """
        split_sed_doc_location = os.path.split(os.path.relpath(sed_doc_location, '.'))
        if split_sed_doc_location[0] or len(split_sed_doc_location) > 2:
            return False

        for output in sed_doc.outputs:
            if isinstance(output, Report) and self.is_curated_sed_report_suitable_for_building_synthetic_archive(
                    specifications, output, sed_doc_location):
                return True

        return False

    def is_curated_sed_report_suitable_for_building_synthetic_archive(self, specifications, report, sed_doc_location):
        """ Determine if a SED report is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            report (:obj:`Report`): SED report in curated archive
            sed_doc_location (:obj:`str`): location of the SED document within its parent COMBINE/OMEX archive

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
        if not model or not model.source:
            return False
        source = model.source.lower()
        return not (
            source.startswith('#')
            or source.startswith('http://')
            or source.startswith('https://')
            or source.startswith('urn:')
        )

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
                or simulation.number_of_points < 1
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

    def build_synthetic_archives(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`list` of :obj:`ExpectedResultOfSyntheticArchive`
        """
        return [ExpectedResultOfSyntheticArchive(curated_archive, curated_sed_docs, True)]

    @abc.abstractmethod
    def eval_outputs(self, specifications, synthetic_archive, synthetic_sed_docs, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
            synthetic_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from the location of each SED
                document in the synthetic archive to the document
            outputs_dir (:obj:`str`): directory that contains the outputs produced from the execution of the synthetic archive

        Returns:
            :obj:`bool`: whether there were no warnings about the outputs
        """
        pass  # pragma: no cover


class ExpectedResultOfSyntheticArchive(object):
    """ An expected result of executing a synthetic COMBINE/OMEX archive

    Attributes:
        archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
        sed_documents (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
          SED documents in synthetic archive
        is_success_expected (:obj:`bool`, optional): whether the execution of the archive is expected to succeed
        environment (:obj:`dict`, optional): environment variables that the archive should be executed with
    """

    def __init__(self, archive, sed_documents, is_success_expected=True, environment=None):
        self.archive = archive
        self.sed_documents = sed_documents
        self.is_success_expected = is_success_expected
        self.environment = environment or {}


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
    for example_filename in glob.glob(os.path.join(dir_name, '**/*.omex'), recursive=True):
        md_filename = os.path.join(example_filename[0:-5], 'expected-results.json')
        rel_filename = os.path.relpath(md_filename, dir_name)
        case = SimulatorCanExecutePublishedProject(output_medium=output_medium).from_json(dir_name, rel_filename)
        all_cases.append(case)
        if case.compatible_with_specifications(specifications):
            compatible_cases.append(case)

    all_cases.sort(key=lambda case: case.filename)
    compatible_cases.sort(key=lambda case: case.filename)

    # return cases
    return (all_cases, compatible_cases)


class ConfigurableMasterCombineArchiveTestCase(SyntheticCombineArchiveTestCase):
    """ Class for generating synthetic archives with a single master SED-ML file or two non-master
    copies of the same file

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should have a master file
        _model_change_filter (:obj:`types.FunctionType`): filter for model changes to keep
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

    def __init__(self, *args, **kwargs):
        super(ConfigurableMasterCombineArchiveTestCase, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: False
        self._remove_algorithm_parameter_changes = True
        self._use_single_variable_data_generators = True
        self._remove_plots = True
        self._keep_one_task_one_report = True

    def build_synthetic_archives(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with master and non-master SED documents

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`list` of :obj:`ExpectedResultOfSyntheticArchive`
        """
        super(ConfigurableMasterCombineArchiveTestCase, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        # get a suitable SED document to modify
        for doc_location, doc in curated_sed_docs.items():
            if self.is_curated_sed_doc_suitable_for_building_synthetic_archive(specifications, doc, doc_location):
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
            model.changes = list(filter(self._model_change_filter, model.changes))

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
                if self.is_curated_sed_report_suitable_for_building_synthetic_archive(specifications, report, doc_location):
                    for data_set in report.data_sets:
                        task = data_set.data_generator.variables[0].task
                        if self.is_curated_sed_task_suitable_for_building_synthetic_archive(specifications, task):
                            key_report = report
                            key_task = task
                            break
                    if key_report:
                        break

            key_sim = key_task.simulation
            if isinstance(key_sim, UniformTimeCourseSimulation):
                key_sim.output_end_time = (
                    key_sim.output_start_time
                    + 10 / key_sim.number_of_points * (key_sim.output_end_time - key_sim.output_start_time)
                )
                key_sim.number_of_points = 10

            doc.models = [key_task.model]
            doc.simulations = [key_task.simulation]
            doc.tasks = [key_task]
            doc.data_generators = [data_gen for data_gen in doc.data_generators if data_gen.variables[0].task == key_task]
            doc.outputs = [key_report]
            key_report.data_sets = [data_set for data_set in key_report.data_sets if data_set.data_generator in doc.data_generators]

            # limit number of data set
            max_data_sets = 10
            key_report.data_sets = key_report.data_sets[0:max_data_sets]
            doc.data_generators = [data_set.data_generator for data_set in key_report.data_sets]

        curated_sed_docs = {
            doc_content.location: doc,
        }

        self._expected_report_ids = []
        for output in doc.outputs:
            if isinstance(output, Report):
                self._expected_report_ids.append(os.path.join(os.path.relpath(doc_content.location, './'), output.id))

        # return modified SED document
        return [ExpectedResultOfSyntheticArchive(curated_archive, curated_sed_docs, True)]


class SingleMasterSedDocumentCombineArchiveTestCase(ConfigurableMasterCombineArchiveTestCase):
    """ Class for generating synthetic COMBINE/OMEX archives with a single master SED-ML file

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
    """

    @property
    def _archive_has_master(self):
        return True


class UniformTimeCourseTestCase(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports multiple reports per SED document """

    TEST_TIME = True

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

    def build_synthetic_archives(self, specifications, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with a copy of each task and each report

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_archive_dir (:obj:`str`): directory with the contents of the curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`list` of :obj:`ExpectedResultOfSyntheticArchive`
        """
        expected_results_of_synthetic_archives = super(UniformTimeCourseTestCase, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        for expected_results_of_synthetic_archive in expected_results_of_synthetic_archives:
            curated_archive = expected_results_of_synthetic_archive.archive
            curated_sed_docs = expected_results_of_synthetic_archive.sed_documents

            # get a suitable SED document to modify
            doc = list(curated_sed_docs.values())[0]
            task = doc.tasks[0]
            sim = task.simulation
            self.modify_simulation(sim)
            report = doc.outputs[0]

            if self.TEST_TIME:
                self.add_time_data_set(doc, task, report)

            expected_results_of_synthetic_archive.archive = curated_archive
            expected_results_of_synthetic_archive.sed_documents = curated_sed_docs

        # return modified SED document
        return expected_results_of_synthetic_archives

    def add_time_data_set(self, doc, task, report):
        """ Rename or add a time data set to a SED report

        Args:
            doc (:obj:`SedDocument`): SED document
            task (:obj:`task`): SED task
            report (:obj:`Report`): SED report
        """
        time_data_gen = None
        for data_gen in doc.data_generators:
            var = data_gen.variables[0]
            if var.task == task and var.symbol == Symbol.time:
                time_data_gen = data_gen
                break

        if not time_data_gen:
            if re.match(ModelLanguagePattern.CellML.value, task.model.language):
                msg = (
                    'This test case requires a model language which supports the time symbol ({}). '
                    '{} does not support the time symbol.'
                ).format(Symbol.time.value, ModelLanguagePattern.CellML.name)
                raise SkippedTestCaseException(msg)

            time_data_gen = DataGenerator(
                id='__data_generator_time__',
                variables=[
                    Variable(
                        id='__variable_time__',
                        task=task,
                        symbol=Symbol.time,
                    ),
                ],
                math='__variable_time__',
            )
            doc.data_generators.append(time_data_gen)

        time_data_set = None
        for data_set in report.data_sets:
            if data_set.data_generator == time_data_gen:
                time_data_set = data_set
                data_set.id = '__data_set_time__'
                break

        if not time_data_set:
            report.data_sets.append(
                DataSet(
                    id='__data_set_time__',
                    label='__data_set_time__',
                    data_generator=time_data_gen,
                )
            )

    @abc.abstractmethod
    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
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

        Returns:
            :obj:`bool`: whether there were no warnings about the outputs
        """
        has_warnings = False

        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')
        doc = list(synthetic_sed_docs.values())[0]
        sim = doc.simulations[0]
        report = doc.outputs[0]

        data = ReportReader().run(report, outputs_dir, os.path.join(doc_id, report.id))

        for data_set_data in data.values():
            if numpy.any(simulation_results_isnan(data_set_data)):
                warnings.warn('The results produced by the simulator include `NaN`.', InvalidOutputsWarning)
                has_warnings = True
                break

        if self.TEST_TIME:
            try:
                numpy.testing.assert_allclose(
                    data['__data_set_time__'],
                    numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1),
                    rtol=1e-4,
                )
            except Exception as exception:
                raise ValueError('Simulator did not produce the expected time course:\n\n  {}'.format(
                    str(exception).replace('\n', '\n  ')))

        return not has_warnings
