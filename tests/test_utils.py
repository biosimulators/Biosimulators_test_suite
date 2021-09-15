from biosimulators_test_suite import utils
from biosimulators_test_suite.config import Config
import math
import numpy
import os
import unittest


class UtilsTestCase(unittest.TestCase):
    def test_get_singularity_image_filename(self):
        base_dir = Config().singularity_image_dirname
        filename = utils.get_singularity_image_filename('ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.2.0')
        print(filename)
        self.assertTrue(os.path.relpath(filename, base_dir).startswith('ghcr.io_'))
        self.assertTrue(filename.endswith('_2.2.0.sif'))

    def test_simulation_results_isnan(self):
        self.assertTrue(utils.simulation_results_isnan(math.nan))
        self.assertFalse(utils.simulation_results_isnan(2))
        self.assertFalse(utils.simulation_results_isnan(3.))

        self.assertTrue(numpy.any(utils.simulation_results_isnan(numpy.array([math.nan]))))
        self.assertFalse(numpy.any(utils.simulation_results_isnan(numpy.array([3]))))
        self.assertFalse(numpy.any(utils.simulation_results_isnan(numpy.array([4.]))))

        with self.assertRaises(TypeError):
            utils.simulation_results_isnan('a')
        with self.assertRaises(TypeError):
            utils.simulation_results_isnan(numpy.array(['a']))
