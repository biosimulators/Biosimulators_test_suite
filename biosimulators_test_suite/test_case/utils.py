""" Utility methods

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-02
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

__all__ = ['are_array_shapes_equivalent', 'reduce_array_shape']


def are_array_shapes_equivalent(shape_1, shape_2, same_dims=False):
    """ Determine if two NumPy arrays have equivalent shape

    * Trim trailing ones
    * Check that remaining non-zero dimension sizes are equal
    * If :obj:`same_dims` is :obj:`True`, all check that the length of the shapes are equal

    Args:
        shape_1 (:obj:`list` of :obj:`int`): shape of first array
        shape_2 (:obj:`list` of :obj:`int`): shape of second array
        same_dims (:obj:`bool`, optional): if :obj:`True`, check that the dimensions
            are also the same

    Returns:
        :obj:`bool`: :obj:`True` if the shapes are equivalent
    """
    reduced_shape_1 = reduce_array_shape(shape_1)
    reduced_shape_2 = reduce_array_shape(shape_2)

    if reduced_shape_1 != reduced_shape_2:
        return False

    if same_dims and len(shape_1) != len(shape_2):
        return False

    return True


def reduce_array_shape(shape):
    """ Reduce the shape of a NumPy array

    * Trim trailing ones
    * Check that remaining non-zero dimension sizes are equal

    Args:
        shape (:obj:`list` of :obj:`int`): shape of array

    Returns:
        :obj:`:obj:`list` of :obj:`int`: reduced shape
    """
    shape = list(shape)

    while shape and shape[-1] == 1:
        shape.pop()

    return shape
