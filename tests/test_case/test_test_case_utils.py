from biosimulators_test_suite.test_case.utils import reduce_array_shape, are_array_shapes_equivalent
import unittest


class TestCaseUtilsTestCase(unittest.TestCase):
    def test_reduce_array_shape(self):
        self.assertEqual(reduce_array_shape([1, 2, 3]), [1, 2, 3])
        self.assertEqual(reduce_array_shape([3, 2, 1]), [3, 2])
        self.assertEqual(reduce_array_shape([3, 2, 1, 1]), [3, 2])
        self.assertEqual(reduce_array_shape([1, 1, 1]), [])
        self.assertEqual(reduce_array_shape([1, 1]), [])
        self.assertEqual(reduce_array_shape([1]), [])
        self.assertEqual(reduce_array_shape([]), [])

    def test_are_array_shapes_equivalent(self):
        self.assertTrue(are_array_shapes_equivalent([1], [1]))
        self.assertTrue(are_array_shapes_equivalent([1], []))
        self.assertTrue(are_array_shapes_equivalent([1, 1, 1], []))
        self.assertTrue(are_array_shapes_equivalent([1, 1, 1], [1]))
        self.assertFalse(are_array_shapes_equivalent([3, 1, 2], []))
        self.assertTrue(are_array_shapes_equivalent([3, 1, 2], [3, 1, 2]))
        self.assertTrue(are_array_shapes_equivalent([3, 1, 2, 1], [3, 1, 2]))
        self.assertTrue(are_array_shapes_equivalent([3, 1, 2, 1, 1], [3, 1, 2]))

        self.assertTrue(are_array_shapes_equivalent([1], [1], same_dims=False))
        self.assertFalse(are_array_shapes_equivalent([1], [], same_dims=True))
        self.assertFalse(are_array_shapes_equivalent([3, 1, 2, 1, 1], [3, 1, 2], same_dims=True))
