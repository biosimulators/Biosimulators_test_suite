from biosimulators_test_suite import data_model
import unittest


class DataModelTestCase(unittest.TestCase):
    def test_SedTaskRequirements(self):
        reqs = data_model.SedTaskRequirements(model_format='format_2585', simulation_algorithm='KISAO_0000019')
        self.assertEqual(reqs.model_format, 'format_2585')
        self.assertEqual(reqs.simulation_algorithm, 'KISAO_0000019')

    def test_ExpectedSedReport(self):
        report = data_model.ExpectedSedReport(
            id='report-1',
            data_sets=set(['time', 'A', 'B', 'C']),
            points=(1001,),
            values={
                'time': [0, 1, 2, 4, 5],
                'A': {
                    (0,): 10.,
                    (2,): 12.,
                },
            },
        )
        self.assertEqual(report.id, 'report-1')
        self.assertEqual(report.data_sets, set(['time', 'A', 'B', 'C']))
        self.assertEqual(report.points, (1001,))
        self.assertEqual(report.values, {
            'time': [0, 1, 2, 4, 5],
            'A': {
                (0,): 10.,
                (2,): 12.,
            },
        })

    def test_ExpectedSedReport_2(self):
        plot = data_model.ExpectedSedPlot(id='plot-1')
        self.assertEqual(plot.id, 'plot-1')
