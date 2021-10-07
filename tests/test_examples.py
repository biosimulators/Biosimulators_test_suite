from biosimulators_utils.combine.io import CombineArchiveReader
from biosimulators_utils.combine.data_model import CombineArchiveContentFormat
from biosimulators_utils.combine.utils import get_sedml_contents
from biosimulators_utils.combine.validation import validate
from biosimulators_utils.config import Config
from biosimulators_utils.omex_meta.data_model import OmexMetadataSchema
from biosimulators_utils.report.data_model import ReportFormat
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import Report, Plot2D
from biosimulators_utils.sedml.exec import get_report_for_plot2d, get_report_for_plot3d
from biosimulators_utils.sedml.io import SedmlSimulationReader
from biosimulators_utils.utils.core import flatten_nested_list_of_strings
from unittest import mock
import glob
import h5py
import json
import numpy
import os
import parameterized
import shutil
import tempfile
import unittest

EXAMPLES_DIRNAME = os.path.join(os.path.dirname(__file__), '..', 'examples')
EXAMPLE_FILENAMES = sorted(glob.glob(os.path.join(EXAMPLES_DIRNAME, '**', '*.omex')))
EXAMPLES = [
    (os.path.relpath(example_filename, EXAMPLES_DIRNAME)[0:-5], example_filename)
    for example_filename in EXAMPLE_FILENAMES
]


class ExamplesTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    @parameterized.parameterized.expand(EXAMPLES)
    def test_example(self, name, example_filename):
        example_specs_filename = os.path.join(example_filename[0:-5], 'expected-results.json')

        example_base_dir = os.path.join(os.path.dirname(example_filename))
        reports_filename = os.path.join(example_filename[0:-5], 'reports.h5')

        with open(example_specs_filename, 'rb') as file:
            specs = json.load(file)

        archive_filename = os.path.join(example_base_dir, specs['filename'])
        archive_dirname = os.path.join(self.dirname, os.path.relpath(example_filename.replace('.omex', ''), EXAMPLES_DIRNAME))
        archive = CombineArchiveReader().run(archive_filename, archive_dirname)

        errors, _ = validate(archive, archive_dirname,
                             formats_to_validate=list(CombineArchiveContentFormat.__members__.values()),
                             config=Config(
                                 OMEX_METADATA_SCHEMA=OmexMetadataSchema.biosimulations),
                             )
        if errors:
            msg = 'COMBINE/OMEX archive `{}` is invalid.\n  {}'.format(
                archive_filename,
                flatten_nested_list_of_strings(errors).replace('\n', '\n  '))
            raise ValueError(msg)

        # check lists of reports and plots
        expected_reports = []
        expected_plots = []
        sedml_contents = get_sedml_contents(archive)
        for sedml_content in sedml_contents:
            doc = SedmlSimulationReader().run(os.path.join(archive_dirname, sedml_content.location))
            for output in doc.outputs:
                output_uri = os.path.join(os.path.relpath(sedml_content.location, '.'), output.id)
                if isinstance(output, Report):
                    expected_reports.append(output_uri)
                else:
                    expected_plots.append(output_uri)

        reports = []
        for report in specs['expectedReports']:
            reports.append(os.path.relpath(report['id'], '.'))

        plots = []
        for plot in specs['expectedPlots']:
            plots.append(os.path.relpath(plot['id'], '.'))

        self.assertEqual(set(reports), set(expected_reports))
        self.assertEqual(set(plots), set(expected_plots))

        # check contents of HDF5 file
        outputs = [
            os.path.relpath(output_uri, '.')
            for output_uri in ReportReader().get_ids(example_filename[0:-5], format=ReportFormat.h5)
        ]
        self.assertEqual(set(outputs), set(reports) | set(plots))

        # check each report
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
            self.assertEqual(set(report_results.keys()), set([data_set['id'] for data_set in expected_report['dataSets']]))
            expected_data_set_id_labels = {data_set['id']: data_set['label'] for data_set in expected_report['dataSets']}
            data_set_id_labels = {data_set.id: data_set.label for data_set in report.data_sets}
            self.assertEqual(data_set_id_labels, expected_data_set_id_labels)

            self.assertEqual(report_results[report.data_sets[0].id].shape, tuple(expected_report['points']))
            for data_set_result in report_results.values():
                self.assertFalse(numpy.any(numpy.isnan(data_set_result)))

            for expected_data_set_value in expected_report['values']:
                self.assertEqual(expected_data_set_value['label'], expected_data_set_id_labels[expected_data_set_value['id']])
                expected_value = expected_data_set_value['value']
                value = report_results[expected_data_set_value['id']]
                if isinstance(expected_value, dict):
                    for idx in expected_value.keys():
                        numpy.testing.assert_allclose(value[int(idx)], expected_value[idx])
                else:
                    numpy.testing.assert_allclose(value, expected_value)

            with h5py.File(os.path.join(example_base_dir, report_path), 'r') as file:
                group_ids = expected_report['id'].split(os.path.sep)[0:-1]
                for i_group in range(len(group_ids)):
                    uri = '/'.join(group_ids[0:i_group + 1])
                    group = file[uri]
                    assert group.attrs['uri'] == uri, example_filename
                    assert group.attrs['combineArchiveLocation'] == uri, example_filename

                data_set = file[expected_report['id']]
                assert data_set.attrs['uri'] == expected_report['id'], example_filename

        # check each plot
        plot_path = os.path.join(specs['filename'][0:-5], 'reports.h5')
        for expected_plot in specs['expectedPlots']:
            sedml_location = os.path.dirname(expected_plot['id'])
            plot_id = os.path.basename(expected_plot['id'])
            sedml_filename = os.path.join(archive_dirname, sedml_location)
            doc = SedmlSimulationReader().run(sedml_filename)

            plot = next(output for output in doc.outputs if output.id == plot_id)

            if isinstance(plot, Plot2D):
                report = get_report_for_plot2d(plot)
            else:
                report = get_report_for_plot3d(plot)

            with mock.patch.dict(os.environ, {'H5_REPORTS_PATH': plot_path}):
                plot_results = ReportReader().run(report, example_base_dir, expected_plot['id'], format=ReportFormat.h5)

            self.assertEqual(set(plot_results.keys()), set([data_set.id for data_set in report.data_sets]))

            for data_set_result in plot_results.values():
                self.assertFalse(numpy.any(numpy.isnan(data_set_result)))

            with h5py.File(os.path.join(example_base_dir, plot_path), 'r') as file:
                group_ids = expected_plot['id'].split(os.path.sep)[0:-1]
                for i_group in range(len(group_ids)):
                    uri = '/'.join(group_ids[0:i_group + 1])
                    group = file[uri]
                    assert group.attrs['uri'] == uri, example_filename
                    assert group.attrs['combineArchiveLocation'] == uri, example_filename

                data_set = file[expected_plot['id']]
                assert data_set.attrs['uri'] == expected_plot['id'], example_filename
