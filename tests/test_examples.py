from biosimulators_utils.combine.io import CombineArchiveReader
from biosimulators_utils.report.data_model import ReportFormat
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.io import SedmlSimulationReader
from unittest import mock
import glob
import json
import numpy
import os
import shutil
import tempfile
import unittest


class ExamplesTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test(self):
        examples_dir = os.path.join(os.path.dirname(__file__), '..', 'examples')
        for example_filename in glob.glob(os.path.join(examples_dir, '**', '*.json')):
            if example_filename.endswith('.vega.json'):
                continue

            example_base_dir = os.path.join(os.path.dirname(example_filename))
            reports_filename = example_filename.replace('.omex', '.h5')
            if not os.path.isfile(reports_filename):
                continue

            with open(example_filename, 'rb') as file:
                specs = json.load(file)

            archive_filename = os.path.join(example_base_dir, specs['filename'])
            archive_dirname = os.path.join(self.dirname, specs['filename'].replace('.omex', ''))
            CombineArchiveReader().run(archive_filename, archive_dirname)

            report_path = specs['filename'].replace('.omex', '.h5')
            for expectedReport in specs['expectedReports']:
                sedml_location = os.path.dirname(expectedReport['id'])
                report_id = os.path.basename(expectedReport['id'])
                sedml_filename = os.path.join(archive_dirname, sedml_location)
                doc = SedmlSimulationReader().run(sedml_filename)

                report = next(output for output in doc.outputs if output.id == report_id)

                with mock.patch.dict(os.environ, {'H5_REPORTS_PATH': report_path}):
                    report_results = ReportReader().run(report, example_base_dir, expectedReport['id'], format=ReportFormat.h5)

                self.assertEqual(set(report_results.keys()), set([data_set.id for data_set in report.data_sets]))
                self.assertEqual(report_results[report.data_sets[0].id].shape, tuple(expectedReport['points']))
                for data_set_result in report_results.values():
                    self.assertFalse(numpy.any(numpy.isnan(data_set_result)))
