""" Methods for testing that simulators support the features of SED-ML

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""
from ..exceptions import InvalidOutputsException, SkippedTestCaseException
from ..utils import simulation_results_isnan
from ..warnings import InvalidOutputsWarning
from .published_project import SingleMasterSedDocumentCombineArchiveTestCase, UniformTimeCourseTestCase, ExpectedResultOfSyntheticArchive
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.archive.io import ArchiveReader
from biosimulators_utils.config import get_config
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import (SedDocument, Task, Output, Report, Plot2D, Plot3D,  DataGenerator,  # noqa: F401
                                                  Variable, UniformTimeCourseSimulation,
                                                  DataSet, Curve, Surface, AxisScale,
                                                  Model, ModelAttributeChange, AlgorithmParameterChange,
                                                  AddElementModelChange, RemoveElementModelChange, ReplaceElementModelChange,
                                                  ComputeModelChange, Parameter,
                                                  RepeatedTask, Range, UniformRange, UniformRangeType, VectorRange, FunctionalRange,
                                                  SetValueComputeModelChange, SubTask)
from biosimulators_utils.sedml.exec import get_report_for_plot2d, get_report_for_plot3d
from biosimulators_utils.sedml.utils import get_xml_node_namespace_tag_target
from kisao import Kisao
from kisao.data_model import AlgorithmSubstitutionPolicy
from kisao.utils import get_substitutable_algorithms_for_policy
from lxml import etree
import abc
import copy
import numpy
import numpy.testing
import os
import PyPDF2
import re
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
    'SimulatorSupportsRepeatedTasksWithLinearUniformRanges',
    'SimulatorSupportsRepeatedTasksWithLogarithmicUniformRanges',
    'SimulatorSupportsRepeatedTasksWithVectorRanges',
    'SimulatorSupportsRepeatedTasksWithFunctionalRanges',
    'SimulatorSupportsRepeatedTasksWithNestedFunctionalRanges',
    'SimulatorSupportsRepeatedTasksWithFunctionalRangeVariables',
    'SimulatorSupportsRepeatedTasksWithMultipleSubTasks',
    'SimulatorSupportsRepeatedTasksWithNestedRepeatedTasks',
    'SimulatorSupportsRepeatedTasksWithSubTasksOfMixedTypes',
    'SimulatorProducesLinear2DPlots',
    'SimulatorProducesLogarithmic2DPlots',
    'SimulatorProducesLinear3DPlots',
    'SimulatorProducesLogarithmic3DPlots',
    'SimulatorProducesMultiplePlots',
    'SimulatorSupportsSubstitutingAlgorithms',
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
            :obj:`bool`: whether there were no warnings about the outputs
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
            raise InvalidOutputsException('Simulator did not produce the following reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_report_ids))
            ))

        if extra_report_ids:
            msg = 'Simulator produced extra reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_report_ids)))
            warnings.warn(msg, InvalidOutputsWarning)
            has_warnings = True

        # data sets
        expected_data_set_ids = set()
        data_set_ids = set()
        for doc_location, doc in synthetic_sed_docs.items():
            doc_id = os.path.relpath(doc_location, './')
            for output in doc.outputs:
                if isinstance(output, Report):
                    for data_set in output.data_sets:
                        expected_data_set_ids.add(os.path.join(doc_id, output.id, data_set.id))

                    results = ReportReader().run(output, outputs_dir, os.path.join(doc_id, output.id))
                    data_set_ids.update(set(os.path.join(doc_id, output.id, id) for id in results.keys()))

        missing_data_set_ids = expected_data_set_ids.difference(set(data_set_ids))
        extra_data_set_ids = set(data_set_ids).difference(expected_data_set_ids)

        if missing_data_set_ids:
            raise InvalidOutputsException('Simulator did not produce the following data sets:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_data_set_ids))
            ))

        if extra_data_set_ids:
            msg = 'Simulator produced extra data sets:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_data_set_ids)))
            warnings.warn(msg, InvalidOutputsWarning)
            has_warnings = True

        return not has_warnings


class SimulatorCanResolveModelSourcesDefinedByUriFragments(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator can resolve model sources defined by URI fragments (e.g., ``#model1``). """

    REPORT_ERROR_AS_SKIP = True

    def __init__(self, *args, **kwargs):
        super(SimulatorCanResolveModelSourcesDefinedByUriFragments, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: False

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
        expected_results_of_synthetic_archives = super(SimulatorCanResolveModelSourcesDefinedByUriFragments, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        # change model source to URI fragment
        doc = list(curated_sed_docs.values())[0]

        model = doc.models[0]
        source_model = Model(id='__source__', source=model.source, language=model.language)
        doc.models.append(source_model)
        model.source = '#' + source_model.id

        return expected_results_of_synthetic_archives


class SimulatorCanResolveModelSourcesDefinedByUriFragmentsAndInheritChanges(
        SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator can resolve model sources defined by URI fragments (e.g., ``#model1``) and inherit the
    changes of the model."""

    REPORT_ERROR_AS_SKIP = True

    def __init__(self, *args, **kwargs):
        super(SimulatorCanResolveModelSourcesDefinedByUriFragmentsAndInheritChanges, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: isinstance(change, ModelAttributeChange)

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
        expected_results_of_synthetic_archives = super(SimulatorCanResolveModelSourcesDefinedByUriFragmentsAndInheritChanges,
                                                       self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        # change model source to URI fragment
        doc = list(curated_sed_docs.values())[0]

        model = doc.models[0]
        source_model = Model(id='__source__', source=model.source, language=model.language, changes=model.changes)
        doc.models.append(source_model)
        model.source = '#' + source_model.id
        model.changes = []

        return expected_results_of_synthetic_archives


class SimulatorSupportsModelAttributeChanges(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator supports changes to the attributes of model elements
    """
    REPORT_ERROR_AS_SKIP = True

    def __init__(self, *args, **kwargs):
        super(SimulatorSupportsModelAttributeChanges, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: False

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsModelAttributeChanges, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_archive = expected_results_of_synthetic_archives[0].archive
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        # get model
        doc = list(curated_sed_docs.values())[0]
        model = doc.models[0]

        try:
            model_etree = etree.parse(os.path.join(curated_archive_dir, model.source))
        except etree.XMLSyntaxError:
            msg = ('This test is only implemented for XML-based model languages. '
                   'Please contact the BioSimulators Team to discuss implementing tests for additional languages.')
            raise SkippedTestCaseException(msg)

        # add model changes
        model_root = model_etree.getroot()

        sed_docs_1 = copy.deepcopy(curated_sed_docs)
        sed_docs_2 = copy.deepcopy(sed_docs_1)
        doc_1 = list(sed_docs_1.values())[0]
        doc_2 = list(sed_docs_2.values())[0]
        model_1 = doc_1.models[0]
        model_2 = doc_2.models[0]
        nodes = [(model_root, 0, '', {})]
        while nodes:
            node, i_node, parent_target, parent_namespaces = nodes.pop()

            _, _, _, node_target, target_namespaces = get_xml_node_namespace_tag_target(
                node, target_namespaces=parent_namespaces)

            node_target = (
                parent_target
                + '/'
                + node_target
                + '[{}]'.format(i_node + 1)
            )

            for key, value in node.attrib.items():
                if key[0] == '{':
                    ns, _, key = key[1:].rpartition('}')
                    rev_namespaces = {v: k for k, v in node.nsmap.items()}
                    key = rev_namespaces[ns] + ':' + key

                model_1.changes.append(
                    ModelAttributeChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        new_value='x',
                    )
                )

                model_2.changes.append(
                    ModelAttributeChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        new_value='x',
                    )
                )
                model_2.changes.append(
                    ModelAttributeChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        new_value=value,
                    )
                )

            n_children = {}
            for child in node.getchildren():
                _, _, _, child_target, _ = get_xml_node_namespace_tag_target(
                    child, target_namespaces=target_namespaces)

                if child_target not in n_children:
                    n_children[child_target] = 0

                nodes.append((child, n_children[child_target], node_target, target_namespaces))

                n_children[child_target] += 1

        return [
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_1, False),
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_2, True),
        ]


class SimulatorSupportsComputeModelChanges(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator supports compute model changes
    """
    REPORT_ERROR_AS_SKIP = True

    def __init__(self, *args, **kwargs):
        super(SimulatorSupportsComputeModelChanges, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: False

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsComputeModelChanges, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_archive = expected_results_of_synthetic_archives[0].archive
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        # get model
        doc = list(curated_sed_docs.values())[0]
        model = doc.models[0]

        try:
            model_etree = etree.parse(os.path.join(curated_archive_dir, model.source))
        except etree.XMLSyntaxError:
            msg = ('This test is only implemented for XML-based model languages. '
                   'Please contact the BioSimulators Team to discuss implementing tests for additional languages.')
            raise SkippedTestCaseException(msg)

        # add model changes
        model_root = model_etree.getroot()

        sed_docs_1 = copy.deepcopy(curated_sed_docs)
        sed_docs_2 = copy.deepcopy(sed_docs_1)
        doc_1 = list(sed_docs_1.values())[0]
        doc_2 = list(sed_docs_2.values())[0]
        model_1 = doc_1.models[0]
        model_2 = doc_2.models[0]
        nodes = [(model_root, 0, '', {})]
        i_change = 0
        while nodes:
            node, i_node, parent_target, parent_namespaces = nodes.pop()

            _, _, _, node_target, target_namespaces = get_xml_node_namespace_tag_target(
                node, target_namespaces=parent_namespaces)

            node_target = (
                parent_target
                + '/'
                + node_target
                + '[{}]'.format(i_node + 1)
            )

            for key, value in node.attrib.items():
                if key[0] == '{':
                    ns, _, key = key[1:].rpartition('}')
                    rev_namespaces = {v: k for k, v in node.nsmap.items()}
                    key = rev_namespaces[ns] + ':' + key

                try:
                    float(value)
                except ValueError:
                    continue

                i_change += 1
                param_id = '__p_{}'.format(i_change)
                var_id = '__var_{}'.format(i_change)
                model_1.changes.append(
                    ComputeModelChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        parameters=[
                            Parameter(id=param_id, value=-1)
                        ],
                        variables=[
                            Variable(
                                id=var_id,
                                target=node_target + '/@' + key,
                                target_namespaces=target_namespaces,
                                model=model_1,
                            )
                        ],
                        math='{} * {}'.format(param_id, var_id),
                    )
                )

                model_2.changes.append(
                    ComputeModelChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        parameters=[
                            Parameter(id=param_id, value=-1)
                        ],
                        variables=[
                            Variable(
                                id=var_id,
                                target=node_target + '/@' + key,
                                target_namespaces=target_namespaces,
                                model=model_2,
                            )
                        ],
                        math='{} * {}'.format(param_id, var_id),
                    )
                )
                model_2.changes.append(
                    ModelAttributeChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        new_value=value,
                    )
                )

            n_children = {}
            for child in node.getchildren():
                _, _, _, child_target, _ = get_xml_node_namespace_tag_target(
                    child, target_namespaces=target_namespaces)

                if child_target not in n_children:
                    n_children[child_target] = 0

                nodes.append((child, n_children[child_target], node_target, target_namespaces))

                n_children[child_target] += 1

        return [
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_1, False),
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_2, True),
        ]


class SimulatorSupportsAddReplaceRemoveModelElementChanges(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator supports model changes that involve adding, replacing, and removing model elements. """
    REPORT_ERROR_AS_SKIP = True

    def __init__(self, *args, **kwargs):
        super(SimulatorSupportsAddReplaceRemoveModelElementChanges, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: False

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsAddReplaceRemoveModelElementChanges, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_archive = expected_results_of_synthetic_archives[0].archive
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        # get model
        doc = list(curated_sed_docs.values())[0]
        model = doc.models[0]

        try:
            model_etree = etree.parse(os.path.join(curated_archive_dir, model.source))
        except etree.XMLSyntaxError:
            msg = ('This test is only implemented for XML-based model languages. '
                   'Please contact the BioSimulators Team to discuss implementing tests for additional languages.')
            raise SkippedTestCaseException(msg)

        # add model changes
        model_root = model_etree.getroot()
        _, _, _, root_target, root_namespaces = get_xml_node_namespace_tag_target(model_root)

        sed_docs_1 = copy.deepcopy(curated_sed_docs)
        doc_1 = list(sed_docs_1.values())[0]
        model_1 = doc_1.models[0]
        for child in model_root.getchildren():
            _, _, _, child_target, target_namespaces = get_xml_node_namespace_tag_target(
                child, target_namespaces=root_namespaces)
            model_1.changes.append(
                RemoveElementModelChange(
                    target='/' + root_target + '/' + child_target,
                    target_namespaces=target_namespaces,
                )
            )

        sed_docs_2 = copy.deepcopy(sed_docs_1)
        doc_2 = list(sed_docs_2.values())[0]
        model_2 = doc_2.models[0]
        for child in model_root.getchildren():
            model_2.changes.append(
                AddElementModelChange(
                    target='/' + root_target,
                    target_namespaces=root_namespaces,
                    new_elements=etree.tostring(child).decode(),
                )
            )

        sed_docs_3 = copy.deepcopy(curated_sed_docs)
        doc_3 = list(sed_docs_3.values())[0]
        model_3 = doc_3.models[0]
        for child in model_root.getchildren():
            child_uri, child_prefix, _, child_target, target_namespaces = get_xml_node_namespace_tag_target(
                child, target_namespaces=root_namespaces)
            model_3.changes.append(
                ReplaceElementModelChange(
                    target='/' + root_target + '/' + child_target,
                    target_namespaces=target_namespaces,
                    new_elements='<biosimulatorsTestSuite:node xmlns:biosimulatorsTestSuite="https://biosimulatos.org" />',
                )
            )

        return [
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_1, False),
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_2, True),
            ExpectedResultOfSyntheticArchive(curated_archive, sed_docs_3, False),
        ]


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
        expected_results_of_synthetic_archives = super(SimulatorSupportsAlgorithmParameters, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

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

        return expected_results_of_synthetic_archives


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

        Returns:
            :obj:`bool`: whether there were no warnings about the outputs
        """
        doc = list(synthetic_sed_docs.values())[0]
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')

        report = doc.outputs[0]
        data = ReportReader().run(report, outputs_dir, os.path.join(doc_id, report.id))

        for alg_specs in specifications['algorithms']:
            if alg_specs['kisaoId']['id'] == doc.simulations[0].algorithm.kisao_id:
                break

        expected_dims = alg_specs['dependentDimensions']

        data_set_data = data[report.data_sets[0].id]
        if numpy.squeeze(data_set_data).ndim != len(expected_dims):
            msg = ('The specifications for the number of dimensions of each data set of algorithm `{}` differs '
                   'from the actual number of dimensions, {} != {}.').format(
                doc.simulations[0].algorithm.kisao_id, numpy.squeeze(data_set_data).ndim, len(expected_dims))
            warnings.warn(msg, InvalidOutputsWarning)
            return False
        else:
            return True


class SimulatorSupportsMultipleTasksPerSedDocument(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports multiple tasks per SED document

    Attributes:
        _expected_reports (:obj:`list` of :obj:`tuple` of :obj:`str`): list of pairs of
            original reports and their expected duplicates
    """

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsMultipleTasksPerSedDocument, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

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
                            copy_var = Variable(
                                id=var.id + '__test_suite_copy',
                                target=var.target,
                                target_namespaces=var.target_namespaces,
                                symbol=var.symbol,
                                model=var.model,
                            )
                            copy_var.task = copy_tasks[var.task.id]
                            copy_data_gen.variables.append(copy_var)

                            copy_data_gen.math = re.sub(r'((^|\b){}(\b|$))'.format(var.id), copy_var.id, copy_data_gen.math)
                    copy_data_set.data_generator = copy_data_gen

        # return modified SED document
        return expected_results_of_synthetic_archives

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

        return True


class SimulatorSupportsMultipleReportsPerSedDocument(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator supports multiple reports per SED document """

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsMultipleReportsPerSedDocument, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

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
        sed_doc.outputs[1].data_sets.append(DataSet(
            id=original_data_sets[0].id + '__copy__',
            label=original_data_sets[0].label,
            data_generator=original_data_sets[0].data_generator,
        ))

        # return modified SED document
        return expected_results_of_synthetic_archives

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

        try:
            report_ids = ReportReader().get_ids(outputs_dir)
        except Exception:
            report_ids = []

        doc_location = os.path.relpath(list(synthetic_sed_docs.keys())[0], './')
        expected_report_ids = set([os.path.join(doc_location, 'report_1'), os.path.join(doc_location, 'report_2')])

        missing_report_ids = expected_report_ids.difference(set(report_ids))
        extra_report_ids = set(report_ids).difference(expected_report_ids)

        if missing_report_ids:
            raise InvalidOutputsException('Simulator did not produce the following reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_report_ids))
            ))

        if extra_report_ids:
            msg = 'Simulator produced extra reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_report_ids)))
            warnings.warn(msg, InvalidOutputsWarning)
            has_warnings = True

        return not has_warnings


class SimulatorSupportsUniformTimeCoursesWithNonZeroOutputStartTimes(UniformTimeCourseTestCase):
    """ Test that a simulator supports time courses with non-zero output start times """

    TEST_TIME = True

    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        simulation.output_start_time = simulation.output_end_time / 2
        simulation.number_of_points = int(simulation.number_of_points / 2)


class SimulatorSupportsUniformTimeCoursesWithNonZeroInitialTimes(UniformTimeCourseTestCase):
    """ Test that a simulator supports multiple time courses with non-zero initial times """

    TEST_TIME = True
    REPORT_ERROR_AS_SKIP = True

    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        simulation.initial_time = simulation.output_end_time / 2
        simulation.output_start_time = simulation.output_end_time / 2
        simulation.number_of_points = int(simulation.number_of_points / 2)


class RepeatedTasksTestCase(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Test that a simulator supports repeated tasks """
    REPORT_ERROR_AS_SKIP = True

    def __init__(self, *args, **kwargs):
        super(RepeatedTasksTestCase, self).__init__(*args, **kwargs)
        self._model_change_filter = lambda change: False

    RANGE_TYPE = VectorRange
    UNIFORM_RANGE_TYPE = UniformRangeType.linear
    RANGE_LENS = (3,)
    FUNCTONAL_RANGE_USES_VARIABLES = False
    NUM_NESTED_RANGES = 0

    def get_ranges(self, i_repeated_task, curated_archive_dir, model, range_len, breaking_range):
        """ Get ranges

        Args:
            i_repeated_task (:obj:`int`): index of repeated task
            curated_archive_dir (:obj:`str`): directory where COMBINE/OMEX archive was unpacked
            model (:obj:`Model`): model
            range_len
            breaking_range (:obj:`bool`): whether the functional range should break the simulation

        Returns:
            :obj:`list` of :obj:`Range`: ranges
        """

        if self.FUNCTONAL_RANGE_USES_VARIABLES:
            try:
                model_etree = etree.parse(os.path.join(curated_archive_dir, model.source))
            except etree.XMLSyntaxError:
                msg = ('This test is only implemented for XML-based model languages. '
                       'Please contact the BioSimulators Team to discuss implementing tests for additional languages.')
                raise SkippedTestCaseException(msg)

            model_root = model_etree.getroot()
            nodes = [(model_root, 0, '', {})]
            variables = []
            while nodes:
                node, i_node, parent_target, parent_namespaces = nodes.pop()

                _, _, _, node_target, target_namespaces = get_xml_node_namespace_tag_target(
                    node, target_namespaces=parent_namespaces)

                node_target = (
                    parent_target
                    + '/'
                    + node_target
                    + '[{}]'.format(i_node + 1)
                )

                for key, value in node.attrib.items():
                    if key[0] == '{':
                        ns, _, key = key[1:].rpartition('}')
                        rev_namespaces = {v: k for k, v in node.nsmap.items()}
                        key = rev_namespaces[ns] + ':' + key

                    try:
                        float(value)
                    except ValueError:
                        continue

                    variables.append(
                        Variable(
                            target=node_target + '/@' + key,
                            target_namespaces=target_namespaces,
                        ),
                    )

                n_children = {}
                for child in node.getchildren():
                    _, _, _, child_target, _ = get_xml_node_namespace_tag_target(
                        child, target_namespaces=target_namespaces)

                    if child_target not in n_children:
                        n_children[child_target] = 0

                    nodes.append((child, n_children[child_target], node_target, target_namespaces))

                    n_children[child_target] += 1

        if self.RANGE_TYPE is UniformRange:
            if self.UNIFORM_RANGE_TYPE == UniformRangeType.linear:
                return [UniformRange(
                    id='__repeated_task_range_' + str(i_repeated_task),
                    start=0.,
                    end=2.,
                    number_of_points=range_len - 1,
                    type=self.UNIFORM_RANGE_TYPE
                )]

            elif self.UNIFORM_RANGE_TYPE == UniformRangeType.log:
                return [UniformRange(
                    id='__repeated_task_range_' + str(i_repeated_task),
                    start=10. ** 0.,
                    end=10. ** 2.,
                    number_of_points=range_len - 1,
                    type=self.UNIFORM_RANGE_TYPE
                )]

        elif self.RANGE_TYPE is VectorRange:
            return [VectorRange(id='__repeated_task_range_' + str(i_repeated_task), values=list(range(range_len)))]

        else:
            ranges = [VectorRange(id='__repeated_task_range_' + str(i_repeated_task), values=list(range(range_len)))]
            for i_range in range(self.NUM_NESTED_RANGES + 1):
                ranges.append(
                    FunctionalRange(
                        id='__repeated_task_range_' + str(i_repeated_task) + '_' + str(i_range + 1),
                        range=ranges[-1],
                        parameters=[
                            Parameter(id='__repeated_task_range_p_' + str(i_repeated_task) + '_' + str(i_range + 1) + '_1', value=0.),
                        ],
                    )
                )
                ranges[-1].math = '{} * {}'.format(ranges[-1].range.id, ranges[-1].parameters[0].id)

                if self.FUNCTONAL_RANGE_USES_VARIABLES:
                    ranges[-1].parameters.append(
                        Parameter(
                            id='__repeated_task_range_p_' + str(i_repeated_task) + '_' + str(i_range + 1) + '_2',
                            value=-1 if breaking_range else 0.,
                        ),
                    )
                    ranges[-1].variables.append(
                        Variable(
                            id='__repeated_task_range_var_' + str(i_repeated_task) + '_' + str(i_range + 1),
                            target=variables[0].target,
                            target_namespaces=variables[0].target_namespaces,
                            model=model,
                        ),
                    )
                    ranges[-1].math += ' + {} * {}'.format(ranges[-1].variables[0].id, ranges[-1].parameters[1].id)
            return ranges

    HAS_CHANGES = False

    def get_changes(self, curated_archive_dir, model, i_repeated_task, range, only_breaking_changes):
        """ Get changes

        Args:
            curated_archive_dir (:obj:`str`): directory where COMBINE/OMEX archive was unpacked
            model (:obj:`Model`): model
            i_repeated_task (:obj:`int`): index of repeated task
            range (:obj:`range`): range
            only_breaking_changes (:obj:`bool`): whether to include breaking or breaking and changes

        Returns:
            :obj:`list` of :obj:`SetValueComputeModelChange`: changes
        """
        if not self.HAS_CHANGES:
            return []

        try:
            model_etree = etree.parse(os.path.join(curated_archive_dir, model.source))
        except etree.XMLSyntaxError:
            msg = ('This test is only implemented for XML-based model languages. '
                   'Please contact the BioSimulators Team to discuss implementing tests for additional languages.')
            raise SkippedTestCaseException(msg)

        model_root = model_etree.getroot()
        nodes = [(model_root, 0, '', {})]
        changes = []
        while nodes:
            node, i_node, parent_target, parent_namespaces = nodes.pop()

            _, _, _, node_target, target_namespaces = get_xml_node_namespace_tag_target(
                node, target_namespaces=parent_namespaces)

            node_target = (
                parent_target
                + '/'
                + node_target
                + '[{}]'.format(i_node + 1)
            )

            for key, value in node.attrib.items():
                if key[0] == '{':
                    ns, _, key = key[1:].rpartition('}')
                    rev_namespaces = {v: k for k, v in node.nsmap.items()}
                    key = rev_namespaces[ns] + ':' + key

                try:
                    original_value = float(value)
                except ValueError:
                    continue

                changes.append(
                    SetValueComputeModelChange(
                        target=node_target + '/@' + key,
                        target_namespaces=target_namespaces,
                        model=model,
                        range=range,
                        parameters=[
                            Parameter(
                                id='p_0_' + str(len(changes)) + '_' + str(i_repeated_task),
                                value=1. if self.FUNCTONAL_RANGE_USES_VARIABLES else 0.,
                            ),
                            Parameter(
                                id='p_1_' + str(len(changes)) + '_' + str(i_repeated_task),
                                value=1. if self.FUNCTONAL_RANGE_USES_VARIABLES else -1,
                            ),
                        ],
                        variables=[
                            Variable(
                                id='var_' + str(len(changes)) + '_' + str(i_repeated_task),
                                model=model,
                                target=node_target + '/@' + key,
                                target_namespaces=target_namespaces,
                            )
                        ],
                        math='{} * {} + {} * {}'.format(
                            'p_0_' + str(len(changes)) + '_' + str(i_repeated_task), range.id,
                            'p_1_' + str(len(changes)) + '_' + str(i_repeated_task), 'var_' +
                            str(len(changes)) + '_' + str(i_repeated_task),
                        )
                    )
                )
                if not only_breaking_changes:
                    changes.append(
                        SetValueComputeModelChange(
                            target=node_target + '/@' + key,
                            target_namespaces=target_namespaces,
                            model=model,
                            range=range,
                            parameters=[
                                Parameter(id='p_2_' + str(len(changes)) + '_' + str(i_repeated_task), value=original_value),
                            ],
                            math='p_2_' + str(len(changes)) + '_' + str(i_repeated_task),
                        )
                    )

            n_children = {}
            for child in node.getchildren():
                _, _, _, child_target, _ = get_xml_node_namespace_tag_target(
                    child, target_namespaces=target_namespaces)

                if child_target not in n_children:
                    n_children[child_target] = 0

                nodes.append((child, n_children[child_target], node_target, target_namespaces))

                n_children[child_target] += 1

        return changes

    NUM_NESTED_REPEATED_TASKS = 0
    MIXED_SUB_TASK_TYPES = False
    NUM_SUB_TASKS = 1

    @abc.abstractmethod
    def is_concrete(self):
        """ Whether the class is abstract

        Returns:
            :obj:`bool`: whether the class is abstract
        """
        pass  # pragma: no cover

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
        expected_results_of_synthetic_archives = super(RepeatedTasksTestCase, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        if self.HAS_CHANGES:
            expected_results_of_synthetic_archive_1 = expected_results_of_synthetic_archives[0]
            expected_results_of_synthetic_archive_2 = copy.deepcopy(expected_results_of_synthetic_archive_1)
            expected_results_of_synthetic_archives.append(expected_results_of_synthetic_archive_2)

            expected_results_of_synthetic_archive_1.is_success_expected = False
            expected_results_of_synthetic_archive_2.is_success_expected = True

            only_breaking_changes = [True, False]
        else:
            if self.MIXED_SUB_TASK_TYPES:
                expected_results_of_synthetic_archive_1 = expected_results_of_synthetic_archives[0]
                expected_results_of_synthetic_archive_2 = copy.deepcopy(expected_results_of_synthetic_archive_1)
                expected_results_of_synthetic_archives.append(expected_results_of_synthetic_archive_2)

                expected_results_of_synthetic_archive_1.is_success_expected = True
                expected_results_of_synthetic_archive_2.is_success_expected = True

                only_breaking_changes = [None, None]
            else:
                only_breaking_changes = [None]

        for i_archive, (expected_results_of_synthetic_archive, only_breaking_change) in enumerate(zip(
                expected_results_of_synthetic_archives, only_breaking_changes)):
            curated_sed_docs = expected_results_of_synthetic_archive.sed_documents

            # get a suitable SED document to modify
            sed_doc = list(curated_sed_docs.values())[0]
            model = sed_doc.models[0]

            # add repeated task
            for i_repeated_task in range(self.NUM_NESTED_REPEATED_TASKS + 1):
                repeated_task = RepeatedTask(id='__repeated_task_' + str(i_repeated_task))
                for i_sub_task in range(self.NUM_SUB_TASKS):
                    if not self.HAS_CHANGES and self.MIXED_SUB_TASK_TYPES and i_sub_task == i_archive:
                        task = sed_doc.tasks[0]
                    else:
                        task = sed_doc.tasks[-1]
                    repeated_task.sub_tasks.append(SubTask(order=self.NUM_SUB_TASKS - i_sub_task, task=task))
                sed_doc.tasks.append(repeated_task)

                repeated_task.ranges = self.get_ranges(i_repeated_task, curated_archive_dir, model,
                                                       self.RANGE_LENS[self.NUM_NESTED_REPEATED_TASKS - i_repeated_task],
                                                       only_breaking_change)
                repeated_task.range = repeated_task.ranges[-1]
                repeated_task.changes = self.get_changes(curated_archive_dir, model,
                                                         i_repeated_task, repeated_task.ranges[-1], only_breaking_change)

            report = sed_doc.outputs[0]
            report.id = 'task_report'
            report_2 = Report(id='__repeated_task_report')
            sed_doc.outputs.append(report_2)
            for i_data_set, data_set in enumerate(report.data_sets):
                data_set_2 = DataSet(id='__repeated_task_data_set_' + str(i_data_set), label=data_set.label)
                report_2.data_sets.append(data_set_2)

                data_gen = data_set.data_generator
                data_gen_2 = DataGenerator(
                    id='__repeated_task_data_generator_' + str(i_data_set),
                    math='__repeated_task_variable_' + str(i_data_set),
                )
                data_set_2.data_generator = data_gen_2
                sed_doc.data_generators.append(data_gen_2)

                variable = data_gen.variables[0]
                variable_2 = Variable(
                    id=data_gen_2.math,
                    symbol=variable.symbol,
                    target=variable.target,
                    target_namespaces=variable.target_namespaces,
                    task=repeated_task)
                data_gen_2.variables.append(variable_2)

        # return modified SED document
        return expected_results_of_synthetic_archives

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
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')
        doc = synthetic_sed_docs[doc_location]
        report = doc.outputs[0]
        repeated_report = doc.outputs[1]
        results = ReportReader().run(report, outputs_dir, os.path.join(doc_id, report.id))
        repeated_results = ReportReader().run(repeated_report, outputs_dir, os.path.join(doc_id, repeated_report.id))

        for data_set, repeated_data_set in zip(report.data_sets, repeated_report.data_sets):
            results_data_set = results[data_set.id]
            repeated_results_data_set = repeated_results[repeated_data_set.id]

            if results_data_set.ndim == 0:
                results_data_set = results_data_set.reshape((1,))

            if repeated_results_data_set.ndim - results_data_set.ndim != 2 * (self.NUM_NESTED_REPEATED_TASKS + 1):
                raise InvalidOutputsException('Each level of repeated task should contribute two additional dimensions to reports')

            if not self.MIXED_SUB_TASK_TYPES:
                if repeated_results_data_set.shape[0:2 * (self.NUM_NESTED_REPEATED_TASKS + 1):2] != self.RANGE_LENS:
                    raise InvalidOutputsException('The results of the repeated tasks should have a slice for each iteration')

                if not set(repeated_results_data_set.shape[1:2 * (self.NUM_NESTED_REPEATED_TASKS + 1):2]) == set([self.NUM_SUB_TASKS]):
                    raise InvalidOutputsException('The results of the repeated tasks should have a slice for each sub-task')

                if (
                    not numpy.any(simulation_results_isnan(results_data_set))
                    and numpy.any(simulation_results_isnan(repeated_results_data_set))
                ):
                    raise InvalidOutputsException('The results of the repeated tasks have unexpected NaNs')
            else:
                shape = results_data_set.shape
                repeated_shape = repeated_results_data_set.shape

                if repeated_shape[0] != self.RANGE_LENS[0]:
                    raise InvalidOutputsException('The results of the repeated tasks should have a slice for each iteration')

                if repeated_shape[1] != self.NUM_SUB_TASKS:
                    raise InvalidOutputsException('The results of the repeated tasks should have a slice for each sub-task')

                if repeated_shape[2] != max(self.RANGE_LENS[1], shape[0]):
                    raise InvalidOutputsException('The results of the repeated tasks should have a slice for each iteration')

                if (
                    (len(shape) == 1 and repeated_shape[3] != self.NUM_SUB_TASKS)
                    or (len(shape) > 1 and repeated_shape[3] != max(self.NUM_SUB_TASKS, shape[1]))
                ):
                    raise InvalidOutputsException('The results of the repeated tasks should have a slice for each sub-task')

                if repeated_shape[2 * (self.NUM_NESTED_REPEATED_TASKS + 1):] != shape:
                    msg = 'The results of the repeated tasks should have a slice for each dimension of output of the basic task'
                    raise InvalidOutputsException(msg)

                sub_tasks = sorted(doc.tasks[-1].sub_tasks, key=lambda sub_task: sub_task.order)
                for i_sub_task, sub_task in enumerate(sub_tasks):
                    if isinstance(sub_task.task, RepeatedTask):
                        slices = tuple([
                            slice(0, repeated_shape[0]),
                            slice(i_sub_task, i_sub_task + 1),
                            slice(0, self.RANGE_LENS[1]),
                            slice(0, self.NUM_SUB_TASKS),
                        ] + [slice(0, dim_len) for dim_len in repeated_shape[4:]])
                        if (
                            not numpy.any(simulation_results_isnan(results_data_set))
                            and numpy.any(simulation_results_isnan(repeated_results_data_set[slices]))
                        ):
                            raise InvalidOutputsException('The results of repeated tasks have unexpected NaNs')

                        slices = tuple([
                            slice(0, repeated_shape[0]),
                            slice(i_sub_task, i_sub_task + 1),
                            slice(self.RANGE_LENS[1], repeated_shape[2]),
                            slice(0, repeated_shape[3]),
                        ] + [slice(0, dim_len) for dim_len in repeated_shape[4:]])
                        if not numpy.all(simulation_results_isnan(repeated_results_data_set[slices])):
                            raise InvalidOutputsException('The results of repeated tasks have unexpected non-NaNs')

                    else:
                        slices = tuple([
                            slice(0, repeated_shape[0]),
                            slice(i_sub_task, i_sub_task + 1),
                        ] + [
                            slice(0, dim_len) for dim_len in shape
                        ] + [
                            slice(0, 1) for dim_len in repeated_shape[2 + len(shape):]
                        ])
                        if (
                            not numpy.any(simulation_results_isnan(results_data_set))
                            and numpy.any(simulation_results_isnan(repeated_results_data_set[slices]))
                        ):
                            raise InvalidOutputsException('The results of repeated tasks have unexpected NaNs')

                        remaining_dims = repeated_shape[2 + len(shape):]
                        for i_dim, dim_len in enumerate(remaining_dims):
                            slices = [
                                slice(0, repeated_shape[0]),
                                slice(i_sub_task, i_sub_task + 1),
                            ] + [
                                slice(0, dim_len) for dim_len in shape
                            ]
                            slices.extend([slice(0, remaining_dims[ii_dim]) for ii_dim in range(i_dim)])
                            slices.append(slice(1, remaining_dims[i_dim]))
                            slices.extend([slice(0, remaining_dims[ii_dim]) for ii_dim in range(i_dim + 1, len(remaining_dims))])
                            slices = tuple(slices)

                            if not numpy.all(simulation_results_isnan(repeated_results_data_set[slices])):
                                raise InvalidOutputsException('The results of repeated tasks have unexpected non-NaNs')

        return True


class SimulatorSupportsRepeatedTasksWithLinearUniformRanges(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks over uniform ranges """
    RANGE_TYPE = UniformRange
    UNIFORM_RANGE_TYPE = UniformRangeType.linear
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithLogarithmicUniformRanges(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks over uniform ranges """
    RANGE_TYPE = UniformRange
    UNIFORM_RANGE_TYPE = UniformRangeType.log
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithVectorRanges(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks over vector ranges """
    RANGE_TYPE = VectorRange
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithFunctionalRanges(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks over functional ranges """
    RANGE_TYPE = FunctionalRange
    NUM_NESTED_RANGES = 0
    FUNCTONAL_RANGE_USES_VARIABLES = False
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithNestedFunctionalRanges(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks over nested functional ranges based on model (specification) variables """
    RANGE_TYPE = FunctionalRange
    NUM_NESTED_RANGES = 1
    FUNCTONAL_RANGE_USES_VARIABLES = False
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithFunctionalRangeVariables(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks over nested functional ranges based on model (specification) variables """
    RANGE_TYPE = FunctionalRange
    NUM_NESTED_RANGES = 0
    FUNCTONAL_RANGE_USES_VARIABLES = True
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0
    HAS_CHANGES = True

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithMultipleSubTasks(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks with multiple subtasks """
    RANGE_TYPE = VectorRange
    NUM_SUB_TASKS = 2
    NUM_NESTED_REPEATED_TASKS = 0

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithChanges(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks with multiple subtasks """
    RANGE_TYPE = VectorRange
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 0
    HAS_CHANGES = True

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithNestedRepeatedTasks(RepeatedTasksTestCase):
    """ Test that a simulator supports nested repeated tasks"""
    RANGE_TYPE = VectorRange
    RANGE_LENS = (3, 3)
    NUM_SUB_TASKS = 1
    NUM_NESTED_REPEATED_TASKS = 1
    MIXED_SUB_TASK_TYPES = False

    def is_concrete(self): return True


class SimulatorSupportsRepeatedTasksWithSubTasksOfMixedTypes(RepeatedTasksTestCase):
    """ Test that a simulator supports repeated tasks whose sub-tasks have mixed types.
    Also tests that sub-types executed in order of the values of their ``order`` attributes
    and that reports of the results of repeated tasks handle sub-tasks to produce results of
    different shapes.
    """
    RANGE_TYPE = VectorRange
    RANGE_LENS = (2, 3)
    NUM_SUB_TASKS = 2
    NUM_NESTED_REPEATED_TASKS = 1
    MIXED_SUB_TASK_TYPES = True

    def is_concrete(self): return True


class SimulatorProducesPlotsTestCase(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that a simulator produces plots """

    @property
    def _num_plots(self):
        return 1

    @property
    @abc.abstractmethod
    def _axis_scale(self):
        pass  # pragma: no cover

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
        expected_results_of_synthetic_archives = super(SimulatorProducesPlotsTestCase, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        sed_docs_1 = copy.deepcopy(curated_sed_docs)
        sed_docs_2 = copy.deepcopy(curated_sed_docs)

        # get a suitable SED document to modify
        doc_1 = list(sed_docs_1.values())[0]
        doc_2 = list(sed_docs_2.values())[0]

        # replace report with plot(s)
        doc_1.outputs = self.build_plots(doc_1.data_generators, False)
        doc_2.outputs = self.build_plots(doc_2.data_generators, True)

        # return modified SED document
        return [
            ExpectedResultOfSyntheticArchive(
                curated_archive,
                sed_docs_1,
                True,
                expected_results_of_synthetic_archives[0].environment),
            ExpectedResultOfSyntheticArchive(
                curated_archive,
                sed_docs_2,
                True,
                expected_results_of_synthetic_archives[0].environment),
        ]

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
            raise SkippedTestCaseException('Simulator did not produce plots')

        tempdir = tempfile.mkdtemp()
        try:
            archive = ArchiveReader().run(plots_path, tempdir)
        except Exception:
            shutil.rmtree(tempdir)
            raise InvalidOutputsException('Simulator produced an invalid zip archive of plots')

        for file in archive.files:
            with open(file.local_path, 'rb') as file:
                try:
                    PyPDF2.PdfFileReader(file)
                except Exception:
                    shutil.rmtree(tempdir)
                    raise InvalidOutputsException('Simulator produced an invalid PDF plot')

        doc = list(synthetic_sed_docs.values())[0]
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')

        plots = [output for output in doc.outputs if isinstance(output, (Plot2D, Plot3D))]
        expected_plot_ids = set(os.path.join(doc_id, plot.id + '.pdf') for plot in plots)
        plot_ids = set(os.path.relpath(file.archive_path, './') for file in archive.files)

        missing_plot_ids = expected_plot_ids.difference(plot_ids)
        extra_plot_ids = plot_ids.difference(expected_plot_ids)

        if missing_plot_ids:
            shutil.rmtree(tempdir)
            raise InvalidOutputsException('Simulator did not produce the following plots:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_plot_ids))
            ))

        if extra_plot_ids:
            msg = 'Simulator produced extra plots:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in extra_plot_ids)))
            warnings.warn(msg, InvalidOutputsWarning)

        # check plot data saved
        expected_plot_ids = set()
        for doc_location, doc in synthetic_sed_docs.items():
            doc_id = os.path.relpath(doc_location, './')
            for output in plots:
                if isinstance(output, (Plot2D, Plot3D)):
                    expected_plot_ids.add(os.path.join(doc_id, output.id))

        try:
            plot_ids = ReportReader().get_ids(outputs_dir)
        except Exception:
            plot_ids = []

        missing_plot_ids = expected_plot_ids.difference(set(plot_ids))

        if missing_plot_ids:
            raise InvalidOutputsException('Simulator did not produce data for the following plots:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_plot_ids))
            ))

        # check plot data saved in expected format
        for doc_location, doc in synthetic_sed_docs.items():
            doc_id = os.path.relpath(doc_location, './')
            for output in plots:
                if isinstance(output, Plot2D):
                    report = get_report_for_plot2d(output)
                elif isinstance(output, Plot3D):
                    report = get_report_for_plot3d(output)

                results = ReportReader().run(report, outputs_dir, os.path.join(doc_id, output.id))

                data_gen_ids = set(results.keys())
                expected_data_gen_ids = set(data_set.id for data_set in report.data_sets)
                missing_data_gen_ids = expected_data_gen_ids.difference(data_gen_ids)
                extra_data_gen_ids = data_gen_ids.difference(expected_data_gen_ids)
                if missing_data_gen_ids:
                    raise InvalidOutputsException('Simulator did not record the following data generators:\n  - {}'.format(
                        '\n  - '.join(sorted('`' + id + '`' for id in missing_data_gen_ids))
                    ))
                if extra_data_gen_ids:
                    msg = 'Simulator recorded extra data generators:\n  - {}'.format(
                        '\n  - '.join(sorted('`' + id + '`' for id in extra_data_gen_ids)))
                    warnings.warn(msg, InvalidOutputsWarning)

                for value in results.values():
                    sim = doc.simulations[0]

                    if value.shape[-1] != sim.number_of_points + 1:
                        raise InvalidOutputsException('Data set does not have the expected shape')

                    if numpy.any(simulation_results_isnan(value)):
                        raise InvalidOutputsException('Data set has unexpected non-NaN values')

        # remove temporary directory
        shutil.rmtree(tempdir)


class SimulatorProduces2DPlotsTestCase(SimulatorProducesPlotsTestCase):
    """ Test that a simulator produces 2D plots """

    def is_curated_sed_report_suitable_for_building_synthetic_archive(self, specifications, report, sed_doc_location):
        """ Determine if a SED report is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            report (:obj:`Report`): SED report in curated archive
            sed_doc_location (:obj:`str`): location of the SED document within its parent COMBINE/OMEX archive

        Returns:
            :obj:`bool`: whether the report is suitable for testing
        """
        if not super(SimulatorProduces2DPlotsTestCase, self).is_curated_sed_report_suitable_for_building_synthetic_archive(
                specifications, report, sed_doc_location):
            return False

        sed_doc_id = os.path.relpath(sed_doc_location, '.')
        expected_report = next((expected_report for expected_report in self._published_projects_test_case.expected_reports
                                if expected_report.id == os.path.join(sed_doc_id, report.id)), None)

        if expected_report is None:
            return False

        return len(expected_report.points) == 1

    def build_plots(self, data_generators, include_report=False):
        """ Build plots from the defined data generators

        Args:
            data_generators (:obj:`list` of :obj:`DataGenerator`): data generators
            include_report (:obj:`bool`, optional): whether to define a report with the
                same data generators involved in the plots

        Returns:
            :obj:`list` of :obj:`Output`: outputs
        """
        outputs = []
        for i in range(self._num_plots):
            outputs.append(Plot2D(id='plot_' + str(i)))

        for i_data_generator, data_generator in enumerate(data_generators):
            outputs[i_data_generator % self._num_plots].curves.append(
                Curve(
                    id='curve_' + str(i_data_generator),
                    x_data_generator=data_generator,
                    y_data_generator=data_generator,
                    x_scale=self._axis_scale,
                    y_scale=self._axis_scale,
                ),
            )

        # report with same data generators
        if include_report:
            report = Report(id='__report_with_same_data_generators__')
            for i_data_generator, data_generator in enumerate(data_generators):
                report.data_sets.append(DataSet(
                    id='__report_data_set_{}__'.format(i_data_generator),
                    label='__report_data_set_{}_label__'.format(i_data_generator),
                    name='{} (Report with same data generators)'.format(data_generator.name or data_generator.id),
                    data_generator=data_generator,
                ))
            outputs.append(report)

        return outputs


class SimulatorProduces3DPlotsTestCase(SimulatorProducesPlotsTestCase):
    """ Test that a simulator produces 3D plots """

    def is_curated_sed_report_suitable_for_building_synthetic_archive(self, specifications, report, sed_doc_location):
        """ Determine if a SED report is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            report (:obj:`Report`): SED report in curated archive
            sed_doc_location (:obj:`str`): location of the SED document within its parent COMBINE/OMEX archive

        Returns:
            :obj:`bool`: whether the report is suitable for testing
        """
        if not super(SimulatorProduces3DPlotsTestCase, self).is_curated_sed_report_suitable_for_building_synthetic_archive(
                specifications, report, sed_doc_location):
            return False

        sed_doc_id = os.path.relpath(sed_doc_location, '.')
        expected_report = next((expected_report for expected_report in self._published_projects_test_case.expected_reports
                                if expected_report.id == os.path.join(sed_doc_id, report.id)), None)
        if expected_report is None:
            return False

        return len(expected_report.points) == 2

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


class SimulatorSupportsDataGeneratorsWithDifferentShapes(UniformTimeCourseTestCase):
    """ Test that a simulator supports data generators with different shapes """

    TEST_TIME = False
    REPORT_ERROR_AS_SKIP = True

    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        pass  # pragma: no cover

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsDataGeneratorsWithDifferentShapes, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents
        doc = list(curated_sed_docs.values())[0]

        sim = doc.simulations[0]
        sim2 = UniformTimeCourseSimulation(
            id=sim.id + '__copy_2',
            initial_time=sim.initial_time,
            output_start_time=sim.output_start_time,
            output_end_time=sim.output_end_time + (sim.output_end_time - sim.output_start_time),
            number_of_points=sim.number_of_points * 2,
            algorithm=copy.deepcopy(sim.algorithm),
        )
        doc.simulations.append(sim2)

        task = doc.tasks[0]
        task2 = Task(
            id=task.id + '__copy_2',
            model=task.model,
            simulation=sim2,
        )
        doc.tasks.append(task2)

        report = doc.outputs.pop()
        report2 = Report(id=report.id + '__copy_2')
        doc.outputs.append(report2)

        for data_gen in list(doc.data_generators):
            data_gen2 = DataGenerator(
                id=data_gen.id + '__copy_2',
                variables=[
                    Variable(
                        id=data_gen.variables[0].id + '__copy_1',
                        task=task,
                        symbol=data_gen.variables[0].symbol,
                        target=data_gen.variables[0].target,
                        target_namespaces=data_gen.variables[0].target_namespaces,
                    ),
                    Variable(
                        id=data_gen.variables[0].id + '__copy_2',
                        task=task2,
                        symbol=data_gen.variables[0].symbol,
                        target=data_gen.variables[0].target,
                        target_namespaces=data_gen.variables[0].target_namespaces,
                    ),
                ],
                math='{} + {}'.format(data_gen.variables[0].id + '__copy_1', data_gen.variables[0].id + '__copy_2'),
            )
            doc.data_generators.append(data_gen2)

            report2.data_sets.append(DataSet(id=data_gen2.id + '_data_set', label=data_gen2.id + '_data_set', data_generator=data_gen2))

        return expected_results_of_synthetic_archives

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
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')
        doc = synthetic_sed_docs[doc_location]
        sim1 = doc.simulations[0]
        sim2 = doc.simulations[-1]
        report2 = doc.outputs[-1]

        results2 = ReportReader().run(report2, outputs_dir, os.path.join(doc_id, report2.id))
        for value in results2.values():
            self._eval_data_set(value, sim2.number_of_points + 1, sim1.number_of_points + 1)

    def _eval_data_set(self, value, length, non_nan_points):
        if value.shape[-1] != length:
            raise InvalidOutputsException('Data set does not have the expected shape')

        data_set_slice = tuple([slice(0, dim_len) for dim_len in value.shape[0:-1]] + [slice(0, non_nan_points)])
        if numpy.any(simulation_results_isnan(value[data_set_slice])):
            raise InvalidOutputsException('Data set has unexpected NaN values')

        data_set_slice = tuple(
            [slice(0, dim_len) for dim_len in value.shape[0:-1]]
            + [slice(non_nan_points, length)]
        )
        if not numpy.all(simulation_results_isnan(value[data_set_slice])):
            raise InvalidOutputsException('Data set has unexpected non-NaN values')


class SimulatorSupportsDataSetsWithDifferentShapes(UniformTimeCourseTestCase):
    """ Test that a simulator supports data generators with different shapes """

    TEST_TIME = False
    REPORT_ERROR_AS_SKIP = True

    def modify_simulation(self, simulation):
        """ Modify a simulation

        Args:
            simulation (:obj:`UniformTimeCourseSimulation`): simulation
        """
        pass  # pragma: no cover

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
        expected_results_of_synthetic_archives = super(SimulatorSupportsDataSetsWithDifferentShapes, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        curated_sed_docs = expected_results_of_synthetic_archives[0].sed_documents
        doc = list(curated_sed_docs.values())[0]

        sim = doc.simulations[0]
        sim2 = UniformTimeCourseSimulation(
            id=sim.id + '__copy_2',
            initial_time=sim.initial_time,
            output_start_time=sim.output_start_time,
            output_end_time=sim.output_end_time + (sim.output_end_time - sim.output_start_time),
            number_of_points=sim.number_of_points * 2,
            algorithm=copy.deepcopy(sim.algorithm),
        )
        doc.simulations.append(sim2)

        task = doc.tasks[0]
        task2 = Task(
            id=task.id + '__copy_2',
            model=task.model,
            simulation=sim2,
        )
        doc.tasks.append(task2)

        report = doc.outputs[0]

        for data_gen in list(doc.data_generators):
            data_gen2 = DataGenerator(
                id=data_gen.id + '__copy_2',
                variables=[
                    Variable(
                        id=data_gen.variables[0].id + '__copy_2',
                        task=task2,
                        symbol=data_gen.variables[0].symbol,
                        target=data_gen.variables[0].target,
                        target_namespaces=data_gen.variables[0].target_namespaces,
                    ),
                ],
                math='{}'.format(data_gen.variables[0].id + '__copy_2'),
            )
            doc.data_generators.append(data_gen2)

            report.data_sets.append(DataSet(id=data_gen2.id + '_data_set', label=data_gen2.id + '_data_set', data_generator=data_gen2))

        return expected_results_of_synthetic_archives

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
        doc_location = list(synthetic_sed_docs.keys())[0]
        doc_id = os.path.relpath(doc_location, './')
        doc = synthetic_sed_docs[doc_location]
        sim1 = doc.simulations[0]
        sim2 = doc.simulations[-1]
        task1 = doc.tasks[0]
        report = doc.outputs[0]

        results = ReportReader().run(report, outputs_dir, os.path.join(doc_id, report.id))

        values1 = {}
        values2 = {}

        for data_set in report.data_sets:
            value = results[data_set.id]

            if data_set.data_generator.variables[0].task == task1:
                expected_length = sim1.number_of_points + 1

                if data_set.data_generator.variables[0].symbol:
                    values1[data_set.data_generator.id] = value

            else:
                expected_length = sim2.number_of_points + 1

                if data_set.data_generator.variables[0].symbol:
                    values2[data_set.data_generator.id.replace('__copy_2', '')] = value[0:sim1.number_of_points + 1]

            self._eval_data_set(data_set.id, value, expected_length)

        for key in values1.keys():
            self._eval_time_data_sets(values1[key], values2[key])

    def _eval_data_set(self, id, value, expected_length):
        if value.shape[-1] != expected_length:
            raise InvalidOutputsException('Data set `{}` does not have the expected shape'.format(id))

        if numpy.any(simulation_results_isnan(value)):
            raise InvalidOutputsException('Data set `{}` has unexpected NaN values'.format(id))

    def _eval_time_data_sets(self, value1, value2):
        try:
            numpy.testing.assert_allclose(value1, value2)
        except Exception as exception:
            raise InvalidOutputsException('Simulations with the same time courses should produce equivalent time data sets:\n\n  {}'.format(
                str(exception).replace('\n', '\n  ')))


class SimulatorSupportsSubstitutingAlgorithms(SimulatorSupportsModelsSimulationsTasksDataGeneratorsAndReports):
    """ Check that a simulator can substitute algorithms that it doesn't implement with similar
    algorithms when the algorithm substitution policy is less restrictive than
    :obj:`AlgorithmSubstitutionPolicy.SAME_METHOD`. Also check that a simulator ignores unsupported
    algorithm parameters when the algorithm substitution policy is less restrictive than
    :obj:`AlgorithmSubstitutionPolicy.NONE`.
    """
    REPORT_ERROR_AS_SKIP = True

    def is_curated_sed_algorithm_suitable_for_building_synthetic_archive(self, specifications, algorithm):
        """ Determine if a SED algorithm is suitable for testing

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            algorithm (:obj:`Algorithm`): SED algorithm in curated archive

        Returns:
            :obj:`bool`: whether the algorithm is suitable for testing
        """
        kisao = Kisao()
        alg_term = kisao.get_term(algorithm.kisao_id)
        sub_algs = get_substitutable_algorithms_for_policy(
            alg_term,
            substitution_policy=AlgorithmSubstitutionPolicy.SIMILAR_VARIABLES)
        sub_alg_ids = kisao.get_term_ids(sub_algs)

        for alg_specs in specifications['algorithms']:
            if alg_specs['kisaoId']['id'] in sub_alg_ids:
                sub_alg_ids.remove(alg_specs['kisaoId']['id'])

        if sub_alg_ids:
            if 'KISAO_0000019' in sub_alg_ids:
                self._alt_alg = 'KISAO_0000019'
            elif 'KISAO_0000088' in sub_alg_ids:
                self._alt_alg = 'KISAO_0000088'
            else:
                self._alt_alg = sub_alg_ids[0]
            return True
        else:
            return False

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
        super(SimulatorSupportsSubstitutingAlgorithms, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)

        sed_docs_1 = copy.deepcopy(curated_sed_docs)
        doc = list(sed_docs_1.values())[0]
        doc.simulations[0].algorithm.kisao_id = self._alt_alg
        doc.simulations[0].algorithm.changes = []

        sed_docs_2 = copy.deepcopy(curated_sed_docs)
        doc = list(sed_docs_2.values())[0]
        doc.simulations[0].algorithm.changes.append(AlgorithmParameterChange(
            kisao_id='KISAO_0000428',
            new_value='0.1',
        ))

        return [
            ExpectedResultOfSyntheticArchive(
                curated_archive,
                sed_docs_1,
                False,
                environment={'ALGORITHM_SUBSTITUTION_POLICY': AlgorithmSubstitutionPolicy.NONE.name}),
            ExpectedResultOfSyntheticArchive(
                curated_archive,
                sed_docs_1,
                True,
                environment={'ALGORITHM_SUBSTITUTION_POLICY': AlgorithmSubstitutionPolicy.SIMILAR_VARIABLES.name}),
            ExpectedResultOfSyntheticArchive(
                curated_archive,
                sed_docs_2,
                False,
                environment={'ALGORITHM_SUBSTITUTION_POLICY': AlgorithmSubstitutionPolicy.NONE.name}),
            ExpectedResultOfSyntheticArchive(
                curated_archive,
                sed_docs_2,
                True,
                environment={'ALGORITHM_SUBSTITUTION_POLICY': AlgorithmSubstitutionPolicy.SIMILAR_VARIABLES.name}),
        ]
