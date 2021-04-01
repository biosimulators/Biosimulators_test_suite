""" Methods for checking support for reports of the execution status of modeling projects

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-29
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..exceptions import InvalidOutputsException, SkippedTestCaseException
from .published_project import SingleMasterSedDocumentCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.config import get_config
from biosimulators_utils.log.data_model import Status
from biosimulators_utils.sedml.data_model import SedDocument, Report  # noqa: F401
import abc
import os
import yaml

__all__ = [
    'LoggingTestCase',
    'SimulatorReportsTheStatusOfTheExecutionOfCombineArchives',
    'SimulatorReportsTheStatusOfTheExecutionOfSedDocuments',
    'SimulatorReportsTheStatusOfTheExecutionOfSedTasks',
    'SimulatorReportsTheStatusOfTheExecutionOfSedOutputs',
]


class LoggingTestCase(SingleMasterSedDocumentCombineArchiveTestCase):
    """ Test that simulation tool can log its execution """

    REPORT_ERROR_AS_SKIP = True
    VALIDATE_SED_DOCUMENT_LOGS = False
    VALIDATE_TASK_LOGS = False
    VALIDATE_OUTPUT_LOGS = False

    @abc.abstractmethod
    def is_concrete(self):
        """ Whether the class is abstract

        Returns:
            :obj:`bool`: whether the class is abstract
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
        log_path = os.path.join(outputs_dir, get_config().LOG_PATH)

        if not os.path.isfile(log_path):
            msg = (
                'The simulator did not export information about the status of its execution. '
                'Simulators are encouraged to stream information about their execution status.\n\n'
                'More information: https://biosimulators.org/conventions/status'
            )
            raise SkippedTestCaseException(msg)

        try:
            with open(log_path, 'r') as file:
                log = yaml.load(file)
        except Exception as exception:
            msg = 'The execution status report produced by the simulator is not valid:\n\n  {}'.format(
                str(exception).replace('\n', '\n  '))
            raise InvalidOutputsException(msg)

        self._status_valid = True

        def is_status_valid(status, self=self):
            if status not in [
                Status.SUCCEEDED.value,
                Status.SKIPPED.value,
                Status.FAILED.value,
            ]:
                self._status_valid = False

        try:
            is_status_valid(log['status'])

            if log.get('sedDocuments', None) or self.VALIDATE_SED_DOCUMENT_LOGS:
                for doc_log in log['sedDocuments']:
                    is_status_valid(doc_log['status'])

                    if doc_log.get('tasks', None) or self.VALIDATE_TASK_LOGS:
                        for task_log in doc_log['tasks']:
                            is_status_valid(task_log['status'])

                    if doc_log.get('outputs', None) or self.VALIDATE_OUTPUT_LOGS:
                        for output_log in doc_log['outputs']:
                            is_status_valid(output_log['status'])

                            els = output_log.get('dataSets', output_log.get('curves', output_log.get('surfaces', None)))
                            if els is None:
                                raise KeyError('Outputs must have one of the keys `dataSets`, `curves` or `surfaces`')
                            for el in els:
                                is_status_valid(el['status'])

        except Exception as exception:
            msg = 'The execution status report produced by the simulator is not valid:\n\n  {}'.format(
                str(exception).replace('\n', '\n  '))
            raise InvalidOutputsException(msg)

        if not self._status_valid:
            msg = (
                'The execution status report produced by the simulator is not valid. '
                'By the end of the execution of a COMBINE/OMEX archive, the status of '
                'the archive, each SED document, and each SED element should be '
                '`SUCCEEDED`, `SKIPPED`, or `FAILED`.'
            )
            raise InvalidOutputsException(msg)

        return True


class SimulatorReportsTheStatusOfTheExecutionOfCombineArchives(LoggingTestCase):
    """ Test that simulator logs the execution of COMBINE/OMEX archives """

    def is_concrete(self):
        """ Whether the class is concrete

        Returns:
            :obj:`bool`: whether the class is concrete
        """
        return True


class SimulatorReportsTheStatusOfTheExecutionOfSedDocuments(LoggingTestCase):
    """ Test that simulator logs the execution of individual SED document in COMBINE/OMEX archives """

    VALIDATE_SED_DOCUMENT_LOGS = True

    def is_concrete(self):
        """ Whether the class is concrete

        Returns:
            :obj:`bool`: whether the class is concrete
        """
        return True


class SimulatorReportsTheStatusOfTheExecutionOfSedTasks(LoggingTestCase):
    """ Test that simulator logs the execution of individual SED tasks in COMBINE/OMEX archives """

    VALIDATE_SED_DOCUMENT_LOGS = True
    VALIDATE_TASK_LOGS = True

    def is_concrete(self):
        """ Whether the class is concrete

        Returns:
            :obj:`bool`: whether the class is concrete
        """
        return True


class SimulatorReportsTheStatusOfTheExecutionOfSedOutputs(LoggingTestCase):
    """ Test that simulator logs the execution of individual SED outputs in COMBINE/OMEX archives """

    VALIDATE_SED_DOCUMENT_LOGS = True
    VALIDATE_OUTPUT_LOGS = True

    def is_concrete(self):
        """ Whether the class is concrete

        Returns:
            :obj:`bool`: whether the class is concrete
        """
        return True
