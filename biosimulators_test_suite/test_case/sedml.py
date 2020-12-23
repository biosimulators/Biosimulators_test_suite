""" Methods for testing that simulators support the features of SED-ML

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""
from .combine_archive import SyntheticCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import (SedDocument, Report, DataSet,  # noqa: F401
                                                  DataGenerator, DataGeneratorVariable)
import copy
import os

__all__ = [
    'MultipleTasksPerSedDocumentTestCase',
]


class MultipleTasksPerSedDocumentTestCase(SyntheticCombineArchiveTestCase):
    """ Test that a simulator supports multiple tasks per SED document

    Attributes:
        _expected_reports (:obj:`list` of :obj:`tuple` of :obj:`str`): list of pairs of
            original reports and their expected duplicates
    """

    def is_curated_archive_suitable_for_building_synthetic_archive(self, archive, sed_docs):
        """ Find an archive with at least one report

        Args:
            archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`bool`: :obj:`True`, if the curated archive is suitable for generating a synthetic
                archive for testing
        """
        return self.get_suitable_sed_doc(sed_docs) is not None

    def build_synthetic_archive(self, curated_archive, curated_sed_docs):
        """ Generate a synthetic archive with a copy of each task and each report

        Args:
            curated_archive (:obj:`CombineArchive`): curated COMBINE/OMEX archive
            curated_sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`tuple`:

                * :obj:`CombineArchive`: synthetic COMBINE/OMEX archive for testing the simulator
                * :obj:`dict` of :obj:`str` to :obj:`SedDocument`: map from locations to
                  SED documents in synthetic archive
        """
        # get a suitable SED document to modify
        location = self.get_suitable_sed_doc(curated_sed_docs)
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

    @staticmethod
    def get_suitable_sed_doc(sed_docs):
        """ Get the location of a suitable SED document for testing

        Args:
            sed_docs (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): map from locations to
                SED documents in curated archive

        Returns:
            :obj:`str`: location of a suitable SED document
        """
        for location, sed_doc in sed_docs.items():
            if sed_doc.tasks:
                for output in sed_doc.outputs:
                    if isinstance(output, Report):
                        return location
        return None

    def eval_outputs(self, specifications, synthetic_archive, outputs_dir):
        """ Test that the expected outputs were created for the synthetic archive

        Args:
            specifications (:obj:`dict`): specifications of the simulator to validate
            synthetic_archive (:obj:`CombineArchive`): synthetic COMBINE/OMEX archive for testing the simulator
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
