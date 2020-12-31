""" Methods for checking support for reports of the execution status of modeling projects

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-29
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..warnings import TestCaseWarning
from .published_project import SingleMasterSedDocumentCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.config import get_config
from biosimulators_utils.exec_status.data_model import ExecutionStatus
from biosimulators_utils.sedml.data_model import SedDocument, Report  # noqa: F401
import os
import warnings
import yaml

__all__ = [
    'SimulatorReportsTheStatusOfTheExecutionOfCombineArchives',
]


class SimulatorReportsTheStatusOfTheExecutionOfCombineArchives(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that when a COMBINE/OMEX archive defines a (single) master file, the simulator only
    executes this file.
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
            :obj:`bool`: :obj:`True`, if simulator passes the test
        """
        exec_status_path = os.path.join(outputs_dir, get_config().EXEC_STATUS_PATH)

        has_warning = False

        if not os.path.isfile(exec_status_path):
            msg = (
                'The simulator did not export information about the status of its execution. '
                'Simulators are encouraged to stream information about their execution status.\n\n'
                'More information: https://biosimulators.org/standards/status'
            )
            warnings.warn(msg, TestCaseWarning)
            has_warning = True

        try:
            with open(exec_status_path, 'r') as file:
                status = yaml.load(file)
        except Exception as exception:
            warnings.warn('The execution status report produced by the simulator is not valid:\n\n  {}'.format(
                str(exception).replace('\n', '\n  ')), TestCaseWarning)
            has_warning = True

        self._status_valid = True

        def is_status_valid(status, self=self):
            if status not in [
                ExecutionStatus.SUCCEEDED.value,
                ExecutionStatus.SKIPPED.value,
                ExecutionStatus.FAILED.value,
            ]:
                self._status_valid = False

        try:
            is_status_valid(status['status'])

            for doc in status['sedDocuments'].values():
                is_status_valid(doc['status'])

                for task in doc['tasks'].values():
                    is_status_valid(task['status'])

                for output in doc['outputs'].values():
                    is_status_valid(output['status'])

                    els = output.get('dataSets', output.get('curves', output.get('surfaces', None)))
                    if els is None:
                        raise KeyError('Outputs must have one of the keys `dataSets`, `curves` or `surfaces`')
                    for status in els.values():
                        is_status_valid(status)

        except Exception as exception:
            warnings.warn('The execution status report produced by the simulator is not valid:\n\n  {}'.format(
                str(exception).replace('\n', '\n  ')), TestCaseWarning)
            has_warning = True

        if not self._status_valid:
            msg = (
                'The execution status report produced by the simulator is not valid. '
                'By the end of the execution of a COMBINE/OMEX archive, the status of '
                'the archive, each SED document, and each SED element should be '
                '`SUCCEEDED`, `SKIPPED`, or `FAILED`.'
            )
            warnings.warn(msg, TestCaseWarning)
            has_warning = True

        return not has_warning
