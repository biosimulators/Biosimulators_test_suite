""" Methods for checking support for reports of simulation results

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-29
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ..warnings import TestCaseWarning
from .published_project import SingleMasterSedDocumentCombineArchiveTestCase
from biosimulators_utils.combine.data_model import CombineArchive  # noqa: F401
from biosimulators_utils.report.data_model import ReportFormat
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import SedDocument, Report  # noqa: F401
import os
import numpy
import warnings

__all__ = [
    'SimulatorGeneratesReportsOfSimulationResults',
]


class SimulatorGeneratesReportsOfSimulationResults(SingleMasterSedDocumentCombineArchiveTestCase):
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
            :obj:`bool`: whether there were no warnings about the outputs
        """
        try:
            ReportReader().get_ids(outputs_dir)
        except Exception:
            raise ValueError('Simulator must generate reports of simulation results')

        has_warning = False
        for doc_location, sed_doc in synthetic_sed_docs.items():
            doc_id = os.path.relpath(doc_location, '.')
            for output in sed_doc.outputs:
                if isinstance(output, Report):
                    report_data = ReportReader().run(output, outputs_dir, os.path.join(doc_id, output.id), format=ReportFormat.h5)

                    expected_data_sets = set(data_set.id for data_set in output.data_sets)
                    data_sets = set(report_data.keys())

                    missing_data_sets = expected_data_sets.difference(data_sets)
                    # extra_data_sets = data_sets.difference(expected_data_sets)

                    if missing_data_sets:
                        raise ValueError('Simulator did not produce the following data sets:\n  - {}'.format(
                            '\n  - '.join(sorted(missing_data_sets))))

                    for data_set_data in report_data.values():
                        if numpy.any(numpy.isnan(data_set_data)):
                            warnings.warn('The results produced by the simulator include `NaN`.', TestCaseWarning)
                            has_warning = True

        return not has_warning
