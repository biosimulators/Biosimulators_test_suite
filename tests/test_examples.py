from biosimulators_utils.combine.io import CombineArchiveReader
from biosimulators_utils.combine.data_model import CombineArchiveContentFormat
from biosimulators_utils.report.data_model import ReportFormat
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.io import SedmlSimulationReader
from biosimulators_utils.combine.validation import validate
from unittest import mock
import glob
import h5py
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
        for example_filename in glob.glob(os.path.join(examples_dir, '**', '*.omex')):
            example_specs_filename = os.path.join(example_filename[0:-5], 'expected-results.json')

            example_base_dir = os.path.join(os.path.dirname(example_filename))
            reports_filename = os.path.join(example_filename[0:-5], 'reports.h5')
            if not os.path.isfile(reports_filename):
                continue

            with open(example_specs_filename, 'rb') as file:
                specs = json.load(file)

            archive_filename = os.path.join(example_base_dir, specs['filename'])
            archive_dirname = os.path.join(self.dirname, specs['filename'].replace('.omex', ''))
            archive = CombineArchiveReader().run(archive_filename, archive_dirname)

            errors, _ = validate(archive, archive_dirname,
                                 formats_to_validate=list(CombineArchiveContentFormat.__members__.values()))
            if errors:
                msg = 'COMBINE/OMEX archive `{}` is invalid.\n  {}'.format(
                    archive_filename,
                    flatten_nested_list_of_strings(errors).replace('\n', '\n  '))
                raise ValueError(msg)

            report_path = os.path.join(specs['filename'][0:-5], 'reports.h5')
            for expected_report in specs['expectedReports']:
                sedml_location = os.path.dirname(expected_report['id'])
                report_id = os.path.basename(expected_report['id'])
                sedml_filename = os.path.join(archive_dirname, sedml_location)
                doc = SedmlSimulationReader().run(sedml_filename)

                report = next(output for output in doc.outputs if output.id == report_id)

                with mock.patch.dict(os.environ, {'H5_REPORTS_PATH': report_path}):
                    report_results = ReportReader().run(report, example_base_dir, expected_report['id'], format=ReportFormat.h5)

                self.assertEqual(set(report_results.keys()), set([data_set.id for data_set in report.data_sets]))
                self.assertEqual(report_results[report.data_sets[0].id].shape, tuple(expected_report['points']))
                for data_set_result in report_results.values():
                    self.assertFalse(numpy.any(numpy.isnan(data_set_result)))

                with h5py.File(os.path.join(example_base_dir, report_path), 'r') as file:
                    group_ids = expected_report['id'].split(os.path.sep)[0:-1]
                    for i_group in range(len(group_ids)):
                        uri = '/'.join(group_ids[0:i_group + 1])
                        group = file[uri]
                        assert group.attrs['uri'] == uri, example_filename
                        assert group.attrs['combineArchiveLocation'] == uri, example_filename

                    data_set = file[expected_report['id']]
                    assert data_set.attrs['uri'] == expected_report['id'], example_filename
