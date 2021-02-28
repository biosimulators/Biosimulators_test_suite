""" Methods for test cases involving checking support for the COMBINE/OMEX standards

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..warnings import InvalidOutputsWarning
from .published_project import SingleMasterSedDocumentCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive, CombineArchiveContent, CombineArchiveContentFormat  # noqa: F401
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import SedDocument, Report  # noqa: F401
import abc
import copy
import datetime
import os
import shutil
import warnings

__all__ = [
    'CombineArchiveTestCase',
    'WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile',
    'WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments',
    'CombineArchiveHasSedDocumentsInNestedDirectories',
    'CombineArchiveHasSedDocumentsWithSameNamesInDifferentInNestedDirectories',
]


class CombineArchiveTestCase(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Base class for testing for the execution of master and non-master files in COMBINE/OMEX archives

    Attributes:
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    SED_DOCUMENT_LOCATIONS_ARE_NESTED = False
    SED_DOCUMENTS_HAVE_SAME_NAMES = False

    @abc.abstractmethod
    def _is_concrete():
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
        expected_results_of_synthetic_archives = super(CombineArchiveTestCase, self).build_synthetic_archives(
            specifications, curated_archive, curated_archive_dir, curated_sed_docs)
        archive = expected_results_of_synthetic_archives[0].archive
        sed_docs = expected_results_of_synthetic_archives[0].sed_documents

        if self.SED_DOCUMENT_LOCATIONS_ARE_NESTED:
            for content in list(archive.contents):
                location_b = os.path.join('subdir', os.path.relpath(content.location, '.'))
                if self.SED_DOCUMENTS_HAVE_SAME_NAMES:
                    location_b_copy = os.path.join('subdir__copy', os.path.relpath(content.location, '.'))

                if not os.path.isdir(os.path.dirname(os.path.join(curated_archive_dir, location_b))):
                    os.makedirs(os.path.dirname(os.path.join(curated_archive_dir, location_b)))
                    if self.SED_DOCUMENTS_HAVE_SAME_NAMES:
                        os.makedirs(os.path.dirname(os.path.join(curated_archive_dir, location_b_copy)))

                shutil.copy(os.path.join(curated_archive_dir, content.location), os.path.join(curated_archive_dir, location_b))
                if self.SED_DOCUMENTS_HAVE_SAME_NAMES:
                    shutil.copy(os.path.join(curated_archive_dir, content.location), os.path.join(curated_archive_dir, location_b_copy))
                if content.format == CombineArchiveContentFormat.SED_ML:
                    sed_docs[location_b] = sed_docs.pop(content.location)
                content.location = location_b
                if content.format != CombineArchiveContentFormat.SED_ML and self.SED_DOCUMENTS_HAVE_SAME_NAMES:
                    content_copy = copy.deepcopy(content)
                    content_copy.location = location_b_copy
                    archive.contents.append(content_copy)

        doc_location = list(sed_docs.keys())[0]
        doc = sed_docs[doc_location]

        if not self.SED_DOCUMENTS_HAVE_SAME_NAMES:
            name, ext = os.path.splitext(doc_location)
            doc_location_2 = name + '__copy' + ext
        elif self.SED_DOCUMENT_LOCATIONS_ARE_NESTED:
            doc_location_2 = os.path.join('subdir__copy', *os.path.split(doc_location)[1:])

        doc_2 = copy.deepcopy(doc)
        sed_docs[doc_location_2] = doc_2
        now = datetime.datetime.now()
        archive.contents.append(
            CombineArchiveContent(
                doc_location_2,
                CombineArchiveContentFormat.SED_ML,
                master=False,
                created=now,
                updated=now),
        )

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

        expected_report_ids = self.get_expected_reports(synthetic_archive, synthetic_sed_docs)

        missing_reports = set(expected_report_ids).difference(set(report_ids))
        unexpected_reports = set(report_ids).difference(set(expected_report_ids))

        if missing_reports:
            raise ValueError('Simulator did not generate the following expected reports\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_reports))))

        if unexpected_reports:
            warnings.warn('Simulator generated the following extra unexpected reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in unexpected_reports))), InvalidOutputsWarning)
            return False

        return True

    def get_expected_reports(self, archive, sed_documents):
        """ Get the ids of the reports expected to be produced from a COMBINE/OMEX archive

        Args:
            archive (:obj:`CombineArchive`): COMBINE/OMEX archive
            sed_documents (:obj:`dict` of :obj:`str` to :obj:`SedDocument`): dictionary that maps the
                location of each SED document to the document

        Returns:
            :obj:`set` of :obj:`str`: ids of the reports expected to be produced from a COMBINE/OMEX archive
        """
        expected_report_ids = set()
        for content in archive.contents:
            if (
                ((self._archive_has_master and content.master) or (not self._archive_has_master))
                and content.format == CombineArchiveContentFormat.SED_ML
            ):
                doc = sed_documents[content.location]
                for output in doc.outputs:
                    if isinstance(output, Report):
                        expected_report_ids.add(os.path.join(os.path.relpath(content.location, '.'), output.id))
        return expected_report_ids


class WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile(CombineArchiveTestCase):
    """ Test that when a COMBINE/OMEX archive defines a (single) master file, the simulator only
    executes this file.

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
    """

    def _is_concrete(): return True

    @property
    def _archive_has_master(self):
        return True


class WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments(CombineArchiveTestCase):
    """ Test that when a COMBINE/OMEX archive does not have a defined master file, the simulator
    executes all SED-ML files.

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
    """

    def _is_concrete(): return True

    @property
    def _archive_has_master(self):
        return False


class CombineArchiveHasSedDocumentsInNestedDirectories(WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile):
    """ Test that SED documents in nested directories can be executed

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
    """

    def _is_concrete(): return True

    SED_DOCUMENT_LOCATIONS_ARE_NESTED = True
    SED_DOCUMENTS_HAVE_SAME_NAMES = False


class CombineArchiveHasSedDocumentsWithSameNamesInDifferentInNestedDirectories(
        WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments):
    """ Test that SED documents with the same names in nested directories can be executed and their outputs are saved to distinct paths

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
    """

    def _is_concrete(): return True

    SED_DOCUMENT_LOCATIONS_ARE_NESTED = True
    SED_DOCUMENTS_HAVE_SAME_NAMES = True
