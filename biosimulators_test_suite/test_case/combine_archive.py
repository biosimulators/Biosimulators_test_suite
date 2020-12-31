""" Methods for test cases involving checking support for the COMBINE/OMEX standards

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-21
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..warnings import TestCaseWarning
from .published_project import ConfigurableMasterCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import SedDocument, Report  # noqa: F401
import warnings

__all__ = [
    'WhenACombineArchiveHasAMasterFileSimulatorOnlyExecutesThisFile',
    'WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments',
]


class CombineArchiveTestCase(ConfigurableMasterCombineArchiveTestCase):
    """ Base class for testing for the execution of master and non-master files in COMBINE/OMEX archives

    Attributes:
        _expected_report_ids (:obj:`list` of :obj:`str`): ids of expected reports
    """

    @property
    def _include_non_master(self):
        return True

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
    """

    @property
    def _archive_has_master(self):
        return True


class WhenACombineArchiveHasNoMasterFileSimulatorExecutesAllSedDocuments(CombineArchiveTestCase):
    """ Test that when a COMBINE/OMEX archive does not have a defined master file, the simulator
    executes all SED-ML files.

    Attributes:
        _archive_has_master (:obj:`bool`): whether the synthetic archive should  have a master file
    """

    @property
    def _archive_has_master(self):
        return False
