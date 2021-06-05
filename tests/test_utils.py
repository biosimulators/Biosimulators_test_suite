from biosimulators_test_suite import utils
from biosimulators_test_suite.config import Config
import os
import unittest


class UtilsTestCase(unittest.TestCase):
    def test_get_singularity_image_filename(self):
        base_dir = Config().singularity_image_dirname
        filename = utils.get_singularity_image_filename('ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.2.0')
        print(filename)
        self.assertTrue(os.path.relpath(filename, base_dir).startswith('ghcr.io_'))
        self.assertTrue(filename.endswith('_2.2.0.sif'))
