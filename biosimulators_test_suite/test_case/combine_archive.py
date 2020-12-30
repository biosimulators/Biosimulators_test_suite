""" Methods for test cases involving checking support for the COMBINE/OMEX standards

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..warnings import TestCaseWarning
from .published_project import SyntheticCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import SedDocument, Report  # noqa: F401
import abc
import copy
import os
import warnings

__all__ = [
    'ConfigurableMasterCombineArchiveTestCase',
    'SingleMasterSedDocumentCombineArchiveTestCase',
    'WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile',
    'WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments',
]


class ConfigurableMasterCombineArchiveTestCase(SyntheticCombineArchiveTestCase):
    """ Class for generating synthetic archives with a single master SED-ML file or two non-master
    copies of the same file

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    @property
    @abc.abstractmethod
    def _archive_has_master(self):
        pass  # pragma: no cover

    def build_synthetic_archive(self, curated_archive, curated_archive_dir, curated_sed_docs):
        """ Generate a synthetic archive with master and non-master SED documents

        Args:
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
        # get a suitable SED document to modify
        doc_location = self.get_suitable_sed_doc(curated_sed_docs)
        doc = curated_sed_docs[doc_location]
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

        # duplicate document
        doc_content_copy = copy.deepcopy(doc_content)
        doc_content_copy.master = False
        doc_content_copy.location = os.path.join(
            os.path.dirname(doc_content_copy.location),
            '__copy__' + os.path.basename(doc_content_copy.location))
        curated_archive.contents.append(doc_content_copy)

        curated_sed_docs = {
            doc_content.location: doc,
            doc_content_copy.location: copy.deepcopy(doc),
        }

        self._expected_report_ids = []
        for output in doc.outputs:
            if isinstance(output, Report):
                self._expected_report_ids.append(os.path.join(os.path.relpath(doc_content.location, './'), output.id))
                if not self._archive_has_master:
                    self._expected_report_ids.append(os.path.join(os.path.relpath(doc_content_copy.location, './'), output.id))

        # return modified SED document
        return (curated_archive, curated_sed_docs)


class SingleMasterSedDocumentCombineArchiveTestCase(ConfigurableMasterCombineArchiveTestCase):
    """ Class for generating synthetic COMBINE/OMEX archives with a single master SED-ML file

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    @property
    def _archive_has_master(self):
        return True


class CombineArchiveTestCase(ConfigurableMasterCombineArchiveTestCase):
    """ Base class for testing for the execution of master and non-master files in COMBINE/OMEX archives

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

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

        missing_reports = set(self._expected_report_ids).difference(set(report_ids))
        unexpected_reports = set(report_ids).difference(set(self._expected_report_ids))

        if missing_reports:
            raise ValueError('Simulator did not generate the following expected reports\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in missing_reports))))

        if unexpected_reports:
            warnings.warn('Simulator generated the following extra unexpected reports:\n  - {}'.format(
                '\n  - '.join(sorted('`' + id + '`' for id in unexpected_reports))), TestCaseWarning)


class WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile(CombineArchiveTestCase):
    """ Test that when a COMBINE/OMEX archive defines a (single) master file, the simulator only
    executes this file.

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    @property
    def _archive_has_master(self):
        return True


class WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments(CombineArchiveTestCase):
    """ Test that when a COMBINE/OMEX archive does not have a defined master file, the simulator
    executes all SED-ML files.

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    @property
    def _archive_has_master(self):
        return False
