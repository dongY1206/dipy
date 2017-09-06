""" Testing reconstruction utilities
"""

import numpy as np

from dipy.reconst.recspeed import (adj_to_countarrs,
                                   argmax_from_countarrs)
from dipy.reconst.utils import probabilistic_least_squares, sample_coef_posterior

from nose.tools import assert_true, assert_false, \
     assert_equal, assert_raises

from numpy.testing import (assert_array_equal,
                           assert_array_almost_equal,
                           assert_almost_equal)


def test_probabilistic_least_squares():

    # Test case: linear regression,
    # y = c_1 + c_2 * x
    # where true values are c_1 = 1, c_2 = 2

    A = np.array([[1, 0], [1, 1], [1, 2]])
    y = np.array([1, 3, 5])
    coef_ground_truth = np.array([1, 2])

    # Noise-less case
    coef, residual_variance = probabilistic_least_squares(A, y)
    assert_array_almost_equal(coef, coef_ground_truth)
    assert_almost_equal(residual_variance, 0)

    # Noisy case
    y_noisy = y + np.array([1, 2, -2])*1e-4
    coef, residual_variance = probabilistic_least_squares(A, y_noisy)
    assert_array_almost_equal(coef, coef_ground_truth, decimal=3)
    assert(residual_variance > 0)

    regularization_matrix = np.diag([0, np.inf])
    # This should force the second coefficient to zero
    coef_expected = np.array([3, 0])
    coef, residual_variance = probabilistic_least_squares(A, y, regularization_matrix=regularization_matrix)
    assert_array_almost_equal(coef, coef_expected)
    assert_almost_equal(residual_variance, 4)

    # Test case: y = c_1 * x + c_2 * x^2
    # Test posterior mean and residual variance correct when no model error
    np.random.seed(0)
    n_x = 1e4
    x = np.linspace(-3, 3, n_x).reshape(-1, 1)
    A = np.column_stack((x, x ** 2))
    variance_ground_truth = 0.1
    y_noisy = np.dot(A, coef_ground_truth) + np.sqrt(variance_ground_truth) * np.random.randn(n_x)
    posterior_mean, residual_variance, posterior_precision = \
        probabilistic_least_squares(A, y_noisy, return_posterior_precision=True)
    assert_almost_equal(residual_variance, variance_ground_truth, decimal=2)
    assert_array_almost_equal(posterior_precision, np.dot(A.T, A) / residual_variance)

def test_sample_posterior():
    np.random.seed(0)

    mean = np.array([1, 2])
    n_coefs = len(mean)
    precision = np.array([[10, 1], [1, 20]])

    # Test that sample mean matches posterior mean
    n_samples = 1e5
    samples = sample_coef_posterior(mean, precision, n_samples)
    samples_mean = np.mean(samples, -1, keepdims=False)
    assert_array_almost_equal(samples_mean, mean, decimal=3)

    # Test that sample covariance matches posterior variance
    samples_centered = samples - samples_mean[:, None]
    sample_covariance = (1/(n_samples - 1) *
                         np.dot(samples_centered, samples_centered.T))
    assert (np.linalg.norm(np.dot(sample_covariance, precision) - np.eye(n_coefs)) < 0.05)


def test_adj_countarrs():
    adj = [[0, 1, 2],
           [2, 3],
           [4, 5, 6, 7]]
    counts, inds = adj_to_countarrs(adj)
    assert_array_equal(counts, [3, 2, 4])
    assert_equal(counts.dtype.type, np.uint32)
    assert_array_equal(inds, [0, 1, 2, 2, 3, 4, 5, 6, 7])
    assert_equal(inds.dtype.type, np.uint32)


def test_argmax_from_countarrs():
    # basic case
    vals = np.arange(10, dtype=np.float)
    vertinds = np.arange(10, dtype=np.uint32)
    adj_counts = np.ones((10,), dtype=np.uint32)
    adj_inds_raw = np.arange(10, dtype=np.uint32)[::-1]
    # when contigous - OK
    adj_inds = adj_inds_raw.copy()
    inds = argmax_from_countarrs(vals, vertinds, adj_counts, adj_inds)
    # yield assert_array_equal(inds, [5, 6, 7, 8, 9])
    # test for errors - first - not contiguous
    #
    # The tests below cause odd errors and segfaults with numpy SVN
    # vintage June 2010 (sometime after 1.4.0 release) - see
    # http://groups.google.com/group/cython-users/browse_thread/thread/624c696293b7fe44?pli=1
    """
    yield assert_raises(ValueError,
                        argmax_from_countarrs,
                        vals,
                        vertinds,
                        adj_counts,
                        adj_inds_raw)
    # too few vertices
    yield assert_raises(ValueError,
                        argmax_from_countarrs,
                        vals,
                        vertinds[:-1],
                        adj_counts,
                        adj_inds)
    # adj_inds too short
    yield assert_raises(IndexError,
                        argmax_from_countarrs,
                        vals,
                        vertinds,
                        adj_counts,
                        adj_inds[:-1])
    # vals too short
    yield assert_raises(IndexError,
                        argmax_from_countarrs,
                        vals[:-1],
                        vertinds,
                        adj_counts,
                        adj_inds)
                        """
