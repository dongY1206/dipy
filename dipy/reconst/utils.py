import numpy as np

def dki_design_matrix(gtab):
    r""" Constructs B design matrix for DKI

    Parameters
    ---------
    gtab : GradientTable
        Measurement directions.

    Returns
    -------
    B : array (N, 22)
        Design matrix or B matrix for the DKI model
        B[j, :] = (Bxx, Bxy, Bzz, Bxz, Byz, Bzz,
                   Bxxxx, Byyyy, Bzzzz, Bxxxy, Bxxxz,
                   Bxyyy, Byyyz, Bxzzz, Byzzz, Bxxyy,
                   Bxxzz, Byyzz, Bxxyz, Bxyyz, Bxyzz,
                   BlogS0)
    """
    b = gtab.bvals
    bvec = gtab.bvecs

    B = np.zeros((len(b), 22))
    B[:, 0] = -b * bvec[:, 0] * bvec[:, 0]
    B[:, 1] = -2 * b * bvec[:, 0] * bvec[:, 1]
    B[:, 2] = -b * bvec[:, 1] * bvec[:, 1]
    B[:, 3] = -2 * b * bvec[:, 0] * bvec[:, 2]
    B[:, 4] = -2 * b * bvec[:, 1] * bvec[:, 2]
    B[:, 5] = -b * bvec[:, 2] * bvec[:, 2]
    B[:, 6] = b * b * bvec[:, 0]**4 / 6
    B[:, 7] = b * b * bvec[:, 1]**4 / 6
    B[:, 8] = b * b * bvec[:, 2]**4 / 6
    B[:, 9] = 4 * b * b * bvec[:, 0]**3 * bvec[:, 1] / 6
    B[:, 10] = 4 * b * b * bvec[:, 0]**3 * bvec[:, 2] / 6
    B[:, 11] = 4 * b * b * bvec[:, 1]**3 * bvec[:, 0] / 6
    B[:, 12] = 4 * b * b * bvec[:, 1]**3 * bvec[:, 2] / 6
    B[:, 13] = 4 * b * b * bvec[:, 2]**3 * bvec[:, 0] / 6
    B[:, 14] = 4 * b * b * bvec[:, 2]**3 * bvec[:, 1] / 6
    B[:, 15] = b * b * bvec[:, 0]**2 * bvec[:, 1]**2
    B[:, 16] = b * b * bvec[:, 0]**2 * bvec[:, 2]**2
    B[:, 17] = b * b * bvec[:, 1]**2 * bvec[:, 2]**2
    B[:, 18] = 2 * b * b * bvec[:, 0]**2 * bvec[:, 1] * bvec[:, 2]
    B[:, 19] = 2 * b * b * bvec[:, 1]**2 * bvec[:, 0] * bvec[:, 2]
    B[:, 20] = 2 * b * b * bvec[:, 2]**2 * bvec[:, 0] * bvec[:, 1]
    B[:, 21] = np.ones(len(b))

    return B


def probabilistic_least_squares(design_matrix, y, regularization_matrix=None, return_posterior_precision=False):
    # Solve least-squares problem on the form
    # design_matrix * coef = y

    if regularization_matrix is None:
        # In single voxel case: np.dot(design_matrix.T, design_matrix)
        unscaled_posterior_precision = np.einsum('...ki, ...kj->...ij', design_matrix, design_matrix)
    else:
        # In single voxel case: np.dot(design_matrix.T, design_matrix) + regularization_matrix
        unscaled_posterior_precision = (np.einsum('...ki, ...kj->...ij', design_matrix, design_matrix)
                                        + regularization_matrix)

    pseudoInv = np.linalg.solve(unscaled_posterior_precision, np.swapaxes(design_matrix, -1, -2))
    coef_posterior_mean = np.einsum('...ij, ...j->...i', pseudoInv, y)

    smoother_matrix = np.einsum('...ik, ...kj->...ij', design_matrix, pseudoInv)
    residual_matrix = np.eye(smoother_matrix.shape[-1]) - smoother_matrix
    residuals = y - np.einsum('...ij, ...j->...i', design_matrix, coef_posterior_mean)
    residual_variance = (np.sum(residuals ** 2, axis=-1) /
                         np.sum(residual_matrix ** 2, axis=(-1, -2)))

    if not return_posterior_precision:
        return coef_posterior_mean, residual_variance
    else:
        coef_posterior_mean = np.atleast_2d(coef_posterior_mean)
        n_voxels, n_coefs = coef_posterior_mean.shape
        coef_posterior_mean = np.squeeze(coef_posterior_mean)

        coef_posterior_precision = unscaled_posterior_precision / residual_variance
        coef_posterior_precision = coef_posterior_precision.reshape(n_voxels, n_coefs, n_coefs)

        coef_posterior_precision = np.squeeze(coef_posterior_precision)

        return coef_posterior_mean, residual_variance, coef_posterior_precision


def sample_coef_posterior(mean, precision, n_samples):
    mean = np.atleast_2d(mean)
    n_voxels, n_coefs = mean.shape
    precision = precision.reshape(n_voxels, n_coefs, n_coefs)
    samples = np.zeros((n_voxels, n_coefs, n_samples))

    # Loop over voxels and draw samples for each
    for i in range(n_voxels):
        standard_normal_samples = np.random.randn(n_coefs, n_samples)

        L = np.linalg.cholesky(precision[i, :, :])
        samples[i, :, :] = (mean[i, :, None] +
                            np.linalg.solve(L, standard_normal_samples))

    samples = np.squeeze(samples)

    return samples
