from builtins import range

import numpy as np
from numpy.fft import fft, ifft, rfft, irfft

from cnns.nnlib.utils.general_utils import *


# import pyfftw
# from pyfftw.interfaces.numpy_fft import fft, ifft, rfft, irfft


def affine_forward(x, w, b):
    """
    Computes the forward pass for an affine (fully-connected) layer.

    The input x has shape (N, d_1, ..., d_k) and contains a minibatch of N
    examples, where each example x[i] has shape (d_1, ..., d_k). We will
    reshape each input into a vector of dimension D = d_1 * ... * d_k, and
    then transform it to an output vector of dimension M.

    Inputs:
    - x: A numpy array containing input data, of shape (N, d_1, ..., d_k)
    - w: A numpy array of weights, of shape (D, M)
    - b: A numpy array of biases, of shape (M,)

    Returns a tuple of:
    - out: output, of shape (N, M)
    - cache: (x, w, b)
    """
    out = None
    ###########################################################################
    # TODO: Implement the affine forward pass. Store the result in out. You   #
    # will need to reshape the input into rows.                               #
    ###########################################################################

    # Number of images in the batch.
    NN = x.shape[0]

    # Reshape each input in our batch to a vector.
    reshaped_input = np.reshape(x, [NN, -1])

    # FC layer forward pass.
    # print("shape reshaped input: ", reshaped_input.shape)
    # print("shape of w: ", w.shape)
    out = np.dot(reshaped_input, w) + b

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = (x, w, b)
    return out, cache


def affine_backward(dout, cache):
    """
    Computes the backward pass for an affine layer.

    Inputs:
    - dout: Upstream derivative, of shape (N, M)
    - cache: Tuple of:
      - x: Input data, of shape (N, d_1, ... d_k)
      - w: Weights, of shape (D, M)

    Returns a tuple of:
    - dx: Gradient with respect to x, of shape (N, d1, ..., d_k)
    - dw: Gradient with respect to w, of shape (D, M)
    - db: Gradient with respect to b, of shape (M,)
    """
    x, w, b = cache
    dx, dw, db = None, None, None
    ###########################################################################
    # TODO: Implement the affine backward pass.                               #
    ###########################################################################

    # Number of images in the batch.
    NN = x.shape[0]

    # Reshape each input in our batch to a vector.
    reshaped_x = np.reshape(x, [NN, -1])

    # Calculate dx = w*dout - remember to reshape back to shape of x.
    dx = np.dot(dout, w.T)
    dx = np.reshape(dx, x.shape)

    # Calculate dw = x*dout
    dw = np.dot(reshaped_x.T, dout)

    # Calculate db = dout
    db = np.sum(dout, axis=0)

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    return dx, dw, db


def relu_forward(x):
    """
    Computes the forward pass for a layer of rectified linear units (ReLUs).

    Input:
    - x: Inputs, of any shape

    Returns a tuple of:
    - out: Output, of the same shape as x
    - cache: x
    """
    out = None
    ###########################################################################
    # TODO: Implement the ReLU forward pass.                                  #
    ###########################################################################

    # Forward Relu.
    out = x.copy()  # Must use copy in numpy to avoid pass by reference.
    out[out < 0] = 0

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = x

    return out, cache


def relu_backward(dout, cache):
    """
    Computes the backward pass for a layer of rectified linear units (ReLUs).

    Input:
    - dout: Upstream derivatives, of any shape
    - cache: Input x, of same shape as dout

    Returns:
    - dx: Gradient with respect to x
    """
    dx, x = None, cache

    ###########################################################################
    # TODO: Implement the ReLU backward pass.                                 #
    ###########################################################################

    # For Relu we only backprop to non-negative elements of x
    relu_mask = (x >= 0)
    dx = dout * relu_mask

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    return dx


def batchnorm_forward(x, gamma, beta, bn_param):
    """
    Forward pass for batch normalization.

    During training the sample mean and (uncorrected) sample variance are
    computed from minibatch statistics and used to normalize the incoming data.
    During training we also keep an exponentially decaying running mean of the
    mean and variance of each feature, and these averages are used to normalize
    data at test-time.

    At each timestep we update the running averages for mean and variance using
    an exponential decay based on the momentum parameter:

    running_mean = momentum * running_mean + (1 - momentum) * sample_mean
    running_var = momentum * running_var + (1 - momentum) * sample_var

    Note that the batch normalization paper suggests a different test-time
    behavior: they compute sample mean and variance for each feature using a
    large number of training images rather than using a running average. For
    this implementation we have chosen to use running averages instead since
    they do not require an additional estimation step; the torch7
    implementation of batch normalization also uses running averages.

    Input:
    - x: Data of shape (N, D)
    - gamma: Scale parameter of shape (D,)
    - beta: Shift paremeter of shape (D,)
    - bn_param: Dictionary with the following keys:
      - mode: 'train' or 'test'; required
      - eps: Constant for numeric stability
      - momentum: Constant for running mean / variance.
      - running_mean: Array of shape (D,) giving running mean of features
      - running_var Array of shape (D,) giving running variance of features

    Returns a tuple of:
    - out: of shape (N, D)
    - cache: A tuple of values needed in the backward pass
    """
    mode = bn_param['mode']
    eps = bn_param.get('eps', 1e-5)
    momentum = bn_param.get('momentum', 0.9)

    N, D = x.shape
    running_mean = bn_param.get('running_mean', np.zeros(D, dtype=x.dtype))
    running_var = bn_param.get('running_var', np.zeros(D, dtype=x.dtype))

    out, cache = None, None
    if mode == 'train':
        #######################################################################
        # TODO: Implement the training-time forward pass for batch norm.      #
        # Use minibatch statistics to compute the mean and variance, use      #
        # these statistics to normalize the incoming data, and scale and      #
        # shift the normalized data using gamma and beta.                     #
        #                                                                     #
        # You should store the output in the variable out. Any intermediates  #
        # that you need for the backward pass should be stored in the cache   #
        # variable.                                                           #
        #                                                                     #
        # You should also use your computed sample mean and variance together #
        # with the momentum variable to update the running mean and running   #
        # variance, storing your result in the running_mean and running_var   #
        # variables.                                                          #
        #######################################################################

        # Take sample mean & var of our minibatch across each dimension.
        sample_mean = np.mean(x, axis=0)
        sample_var = np.var(x, axis=0)

        # Normalise our batch then shift and scale with gamma/beta.
        normalized_data = (x - sample_mean) / np.sqrt(sample_var + eps)
        out = gamma * normalized_data + beta

        # Update our running mean and variance then store.
        running_mean = momentum * running_mean + (1 - momentum) * sample_mean
        running_var = momentum * running_var + (1 - momentum) * sample_var
        bn_param['running_mean'] = running_mean
        bn_param['running_var'] = running_var

        # Store intermediate results needed for backward pass.
        cache = {
            'x_minus_mean': (x - sample_mean),
            'normalized_data': normalized_data,
            'gamma': gamma,
            'ivar': 1. / np.sqrt(sample_var + eps),
            'sqrtvar': np.sqrt(sample_var + eps),
        }

        #######################################################################
        #                           END OF YOUR CODE                          #
        #######################################################################
    elif mode == 'test':
        #######################################################################
        # TODO: Implement the test-time forward pass for batch normalization. #
        # Use the running mean and variance to normalize the incoming data,   #
        # then scale and shift the normalized data using gamma and beta.      #
        # Store the result in the out variable.                               #
        #######################################################################

        # ExperimentSpectralSpatial time batch norm using learned gamma/beta and calculated running mean/var.
        out = (gamma / (np.sqrt(running_var + eps)) * x) + (
                    beta - (gamma * running_mean) / np.sqrt(running_var + eps))

        #######################################################################
        #                          END OF YOUR CODE                           #
        #######################################################################
    else:
        raise ValueError('Invalid forward batchnorm mode "%s"' % mode)

    # Store the updated running means back into bn_param
    bn_param['running_mean'] = running_mean
    bn_param['running_var'] = running_var

    return out, cache


def batchnorm_backward(dout, cache):
    """
    Backward pass for batch normalization.

    For this implementation, you should write out a computation graph for
    batch normalization on paper and propagate gradients backward through
    intermediate nodes.

    Inputs:
    - dout: Upstream derivatives, of shape (N, D)
    - cache: Variable of intermediates from batchnorm_forward.

    Returns a tuple of:
    - dx: Gradient with respect to inputs x, of shape (N, D)
    - dgamma: Gradient with respect to scale parameter gamma, of shape (D,)
    - dbeta: Gradient with respect to shift parameter beta, of shape (D,)
    """
    dx, dgamma, dbeta = None, None, None
    ###########################################################################
    # TODO: Implement the backward pass for batch normalization. Store the    #
    # results in the dx, dgamma, and dbeta variables.                         #
    ###########################################################################

    # Get cached results from the forward pass.
    N, D = dout.shape
    normalized_data = cache.get('normalized_data')
    gamma = cache.get('gamma')
    ivar = cache.get('ivar')
    x_minus_mean = cache.get('x_minus_mean')
    sqrtvar = cache.get('sqrtvar')

    # Backprop dout to calculate dbeta and dgamma.
    dbeta = np.sum(dout, axis=0)
    dgamma = np.sum(dout * normalized_data, axis=0)

    # Carry on the backprop in steps to calculate dx.
    # Step1
    dxhat = dout * gamma
    # Step2
    dxmu1 = dxhat * ivar
    # Step3
    divar = np.sum(dxhat * x_minus_mean, axis=0)
    # Step4
    dsqrtvar = divar * (-1 / sqrtvar ** 2)
    # Step5
    dvar = dsqrtvar * 0.5 * (1 / sqrtvar)
    # Step6
    dsq = (1 / N) * dvar * np.ones_like(dout)
    # Step7
    dxmu2 = dsq * 2 * x_minus_mean
    # Step8
    dx1 = dxmu1 + dxmu2
    dmu = -1 * np.sum(dxmu1 + dxmu2, axis=0)
    # Step9
    dx2 = (1 / N) * dmu * np.ones_like(dout)
    # Step10
    dx = dx2 + dx1

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################

    return dx, dgamma, dbeta


def batchnorm_backward_alt(dout, cache):
    """
    Alternative backward pass for batch normalization.

    For this implementation you should work out the derivatives for the batch
    normalizaton backward pass on paper and simplify as much as possible. You
    should be able to derive a simple expression for the backward pass.

    Note: This implementation should expect to receive the same cache variable
    as batchnorm_backward, but might not use all of the values in the cache.

    Inputs / outputs: Same as batchnorm_backward
    """
    dx, dgamma, dbeta = None, None, None
    ###########################################################################
    # TODO: Implement the backward pass for batch normalization. Store the    #
    # results in the dx, dgamma, and dbeta variables.                         #
    #                                                                         #
    # After computing the gradient with respect to the centered inputs, you   #
    # should be able to compute gradients with respect to the inputs in a     #
    # single statement; our implementation fits on a single 80-character line.#
    ###########################################################################

    # Get cached variables from foward pass.
    N, D = dout.shape
    normalized_data = cache.get('normalized_data')
    gamma = cache.get('gamma')
    ivar = cache.get('ivar')
    x_minus_mean = cache.get('x_minus_mean')
    sqrtvar = cache.get('sqrtvar')

    # Backprop dout to calculate dbeta and dgamma.
    dbeta = np.sum(dout, axis=0)
    dgamma = np.sum(dout * normalized_data, axis=0)

    # Alternative faster formula way of calculating dx. ref: http://cthorey.github.io./backpropagation/
    dx = (1 / N) * gamma * 1 / sqrtvar * (
            (N * dout) - np.sum(dout, axis=0) - (x_minus_mean) * np.square(
        ivar) * np.sum(dout * (x_minus_mean),
                       axis=0))

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################

    return dx, dgamma, dbeta


def dropout_forward(x, dropout_param):
    """
    Performs the forward pass for (inverted) dropout.

    Inputs:
    - x: Input data, of any shape
    - dropout_param: A dictionary with the following keys:
      - p: Dropout parameter. We drop each neuron output with probability p.
      - mode: 'test' or 'train'. If the mode is train, then perform dropout;
        if the mode is test, then just return the input.
      - seed: Seed for the random number generator. Passing seed makes this
        function deterministic, which is needed for gradient checking but not
        in real networks.

    Outputs:
    - out: Array of the same shape as x.
    - cache: tuple (dropout_param, mask). In training mode, mask is the dropout
      mask that was used to multiply the input; in test mode, mask is None.
    """
    p, mode = dropout_param['p'], dropout_param['mode']
    if 'seed' in dropout_param:
        np.random.seed(dropout_param['seed'])

    mask = None
    out = None

    if mode == 'train':
        #######################################################################
        # TODO: Implement training phase forward pass for inverted dropout.   #
        # Store the dropout mask in the mask variable.                        #
        #######################################################################

        # Ref on dropout: http://nnlib.github.io/neural-networks-2/

        # During training randomly drop out neurons with probability P, here we create the mask that does this.
        mask = (np.random.random_sample(x.shape) >= p)

        # Inverted dropout scales the remaining neurons during training so we don't have to at test time.
        dropout_scale_factor = 1 / (1 - p)
        mask = mask * dropout_scale_factor

        # Apply the dropout mask to the input.
        out = x * mask

        #######################################################################
        #                           END OF YOUR CODE                          #
        #######################################################################
    elif mode == 'test':
        #######################################################################
        # TODO: Implement the test phase forward pass for inverted dropout.   #
        #######################################################################

        # ExperimentSpectralSpatial time we don't drop anything so just pass input through, also scaling was done during training.
        out = x

        #######################################################################
        #                            END OF YOUR CODE                         #
        #######################################################################

    cache = (dropout_param, mask)
    out = out.astype(x.dtype, copy=False)

    return out, cache


def dropout_backward(dout, cache):
    """
    Perform the backward pass for (inverted) dropout.

    Inputs:
    - dout: Upstream derivatives, of any shape
    - cache: (dropout_param, mask) from dropout_forward.
    """
    dropout_param, mask = cache
    mode = dropout_param['mode']

    dx = None
    if mode == 'train':
        #######################################################################
        # TODO: Implement training phase backward pass for inverted dropout   #
        #######################################################################

        # Only backprop to the neurons we didn't drop.
        dx = dout * mask * 1

        #######################################################################
        #                          END OF YOUR CODE                           #
        #######################################################################
    elif mode == 'test':
        dx = dout
    return dx


def next_power2(x):
    """
    :param x: an integer number
    :return: the power of 2 which is the larger than x but the smallest possible

    >>> result = next_power2(5)
    >>> np.testing.assert_equal(result, 8)
    """
    return 2 ** np.ceil(np.log2(x)).astype(int)


def conv_forward_fft_1D_correct(x, w, b, conv_param, preserve_energy_rate=1.0):
    """
    Forward pass of 1D convolution.
    SOURCE: http://www.aip.de/groups/soe/local/numres/bookfpdf/f13-1.pdf

    The input consists of N data points with each data point representing a time-series of length W.

    We also have the notion of channels in the 1-D convolution. We want to use more than a single filter even for the
    input time-series, so the output is a batch with the same size but the number of output channels is equal to the
    number of input filters.

    The function convolves a real data set x (0:n) (including any user supplied zero padding) with a response function
    w (weights also called filter or kernel), stored in wrap-around order in a real array of length WW <= W (WW should
    be an odd integer). Wrap-around order means that the first half of the array contains the impulse response function
    at positive times, while the second half of the array contains the impulse response function at negative times,
    counting down from the highest element w(WW-1).

    The answer is returned in the first out_W components.

    :param x: Input data of shape (N, C, W)
    :param w: Filter weights of shape (F, C, WW)
    :param b: biases, of shape (F,)
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions. The stride is not supported for FFT.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
     - out: output data, of shape (N, out_W) where out_W is given by:
     out_W = W + 2*pad - WW + 1
     - cache: (x, w, b, conv_param)

     :see:
     main source: http://www.aip.de/groups/soe/local/numres/bookfpdf/f13-1.pdf

     https://stackoverflow.com/questions/40703751/using-fourier-transforms-to-do-convolution?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
     short: https://goo.gl/GwyhXz
    """
    # Grab conv parameters
    # print("conv_param: ", conv_param)
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')
    if stride != 1:
        raise AttributeError(
            "stride is not supported for fft-based convolution")

    N, C, W = x.shape
    F, C, WW = w.shape

    # Calculate output for the time domain dimensions (for a standard direct convolution).
    out_W = W + 2 * pad - WW + 1  # no padding for fft based convolution

    # Initialise the output.
    out = np.zeros([N, F, out_W])

    # We need to pad the data with a number of zeros on one end equal to the maximum positive duration or maximum
    # negative duration of the response function, whichever is larger. For example, if w_0 through w_6 are non-zero,
    # while w_7, w_8, w_9, ... are all zero, then we need at least K = 6 padding zeros at the end of the data: x_W-6 =
    # x_W-5 = ... = x_W-1 = 0. We approximate it (to be precise: over-approximate) the estimation by setting the
    xw_size = W + WW - 1
    # The FFT padding is the biggest possible padding (otherwise, you return additional zeros - with bigger
    # convolutional padding).
    # The FFT is faster if the input signal is a power of 2.
    fftsize = next_power2(xw_size)
    fft_pad = fftsize - W

    # Zero pad our tensor along the spatial dimensions.
    # Do not pad N (0,0) and C (0,0) dimensions, but only the 1D array - the W dimension (pad, pad).
    padded_x = (
        np.pad(x, ((0, 0), (0, 0), (fft_pad // 2, fft_pad // 2)), 'constant'))
    padded_filters = (np.pad(w, ((0, 0), (0, 0), (0, fft_pad)), 'constant'))

    # Naive convolution loop.
    for nn in range(N):  # For each time-series in the input batch.
        for ff in range(F):  # For each filter in w
            sum_out = np.zeros([out_W])
            for cc in range(C):
                xfft = np.fft.fft(padded_x[nn, cc], fftsize)
                # print("first xfft: ", xfft)
                # print("first xfft shape: ", xfft.shape)
                # the output is symmetric so cut off the second half
                # xfft = xfft[:np.ceil(len(xfft) / 2).astype(int)]
                squared_abs = np.abs(xfft) ** 2
                full_energy = np.sum(squared_abs)
                current_energy = 0.0
                preserve_energy = full_energy * preserve_energy_rate
                index = 0
                while current_energy < preserve_energy and index < len(
                        squared_abs):
                    current_energy += squared_abs[index]
                    # preserve the index as a power of 2
                    if index == 0:
                        index = 1
                    else:
                        index *= 2
                # print("index: ", index)
                xfft = xfft[:index]
                # print("xfft: ", xfft)
                # xfft = xfft[:xfft.shape[0] // 2, :xfft.shape[1] // 2]
                # print("xfft shape: ", xfft.shape)
                filters = padded_filters[ff, cc]
                print("filters: ", filters)
                print("last shape of xfft: ", xfft.shape[-1])
                # The convolution theorem takes the duration of the response to be the same as the period of the data.
                # The are both
                filters[-WW // 2:] = filters[WW // 2:WW]
                filters[WW // 2:WW] = 0
                print("filters: ", filters)
                filterfft = np.fft.fft(filters, xfft.shape[-1])
                # filterfft = filterfft[:filterfft.shape[0] // 2, :filterfft.shape[1] // 2]
                print("filterfft: ", filterfft)
                filterfft = np.conj(filterfft)
                outfft = xfft * filterfft
                # take the inverse of the output from the frequency domain and return the modules of the complex numbers
                outifft = np.fft.ifft(outfft)  # out_W: crop or pad with zeros
                # out[nn, ff] += np.abs(np.fft.ifft2(xfft * filterfft, (out_H, out_W)))
                # outdouble = np.array(outifft, np.double)
                out_real = np.real(outifft)
                # out_real = np.abs(outifft)
                # if len(out_real) < out_W:
                #     out_real = np.pad(out_real, (0, out_W - len(out_real)), 'constant')
                # sum_out += out_real[:out_W]
                if len(out_real) < out_W:
                    out_real = np.pad(out_real, (0, out_W - len(out_real)),
                                      'constant')
                sum_out += out_real[:out_W]
            # crop the output to the expected shape
            # print("shape of expected results: ", out[nn, ff].shape)
            # print("shape of sum_out: ", sum_out.shape)
            out[nn, ff] = sum_out + b[ff]

    cache = (x, w, b, conv_param)
    return out, cache


def conv_forward_fftw_1D(x, w, b, conv_param, preserve_energy_rate=1.0):
    """
    Forward pass of 1D convolution.

    The input consists of N data points with each data point representing a time-series of length W.

    We also have the notion of channels in the 1-D convolution. We want to use more than a single filter even for the
    input time-series, so the output is a batch with the same size but the number of output channels is equal to the
    number of input filters.

    :param x: Input data of shape (N, C, W)
    :param w: Filter weights of shape (F, C, WW)
    :param b: biases, of shape (F,)
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
     - out: output data, of shape (N, W') where W' is given by:
     W' = 1 + (W + 2*pad - WW) / stride
     - cache: (x, w, b, conv_param)

     :see:  source: https://stackoverflow.com/questions/40703751/using-fourier-transforms-to-do-convolution?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
     short: https://goo.gl/GwyhXz
    """
    # Grab conv parameters
    # print("conv_param: ", conv_param)
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')

    N, C, W = x.shape
    F, C, WW = w.shape

    xw_size = W + WW - 1
    # The FFT is faster if the input signal is a power of 2.
    fftsize = 2 ** np.ceil(np.log2(xw_size)).astype(int)

    # Zero pad our tensor along the spatial dimensions.
    # Do not pad N (0,0) and C (0,0) dimensions, but only the 1D array - the W dimension (pad, pad).
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad, pad)), 'constant'))

    # Calculate output spatial/time domain dimensions.
    out_W = np.int(((W + 2 * pad - WW) / stride) + 1)

    # Initialise the output.
    out = np.zeros([N, F, out_W])

    # Naive convolution loop.
    for nn in range(N):  # For each time-series in the input batch.
        for ff in range(F):  # For each filter in w
            sum_out = np.zeros([out_W])
            for cc in range(C):
                xfft = pyfftw.interfaces.numpy_fft.fft(padded_x[nn, cc],
                                                       fftsize)
                # print("first xfft: ", xfft)
                # xfft = xfft[:len(xfft) // 2]
                if preserve_energy_rate < 1.0:
                    squared_abs = np.abs(xfft) ** 2
                    full_energy = np.sum(squared_abs)
                    current_energy = 0.0
                    preserve_energy = full_energy * preserve_energy_rate
                    index = 0
                    while current_energy < preserve_energy and index < len(
                            squared_abs):
                        current_energy += squared_abs[index]
                        index += 1
                    # print("index: ", index)
                    xfft = xfft[:index]
                # print("xfft: ", xfft)
                # xfft = xfft[:xfft.shape[0] // 2, :xfft.shape[1] // 2]
                # print("xfft shape: ", xfft.shape)
                filters = w[ff, cc]
                # print("filters: ", filters)
                # print("last shape of xfft: ", xfft.shape[-1])
                # The convolution theorem takes the duration of the response to be the same as the period of the data.
                filterfft = pyfftw.interfaces.numpy_fft.fft(filters,
                                                            xfft.shape[-1])
                # filterfft = np.fft.fft(filters, xfft.shape[-1]*2)
                # filterfft = filterfft[:filterfft.shape[0] // 2, :filterfft.shape[1] // 2]
                # filterfft = filterfft[:filterfft.shape[-1] // 2]
                # print("filterfft: ", filterfft)
                filterfft = np.conj(filterfft)
                outfft = xfft * filterfft
                # outfft = np.concatenate(outfft, reversed(outfft))
                # take the inverse of the output from the frequency domain and return the modules of the complex numbers
                outifft = pyfftw.interfaces.numpy_fft.ifft(outfft)
                # out[nn, ff] += np.abs(np.fft.ifft2(xfft * filterfft, (out_H, out_W)))
                # outdouble = np.array(outifft, np.double)
                out_real = np.real(outifft)
                # out_real = np.abs(outifft)
                if len(out_real) < out_W:
                    out_real = np.pad(out_real, (0, out_W - len(out_real)),
                                      'constant')
                sum_out += out_real[:out_W]

            # import matplotlib.pyplot as plt
            # plt.plot(range(0, len(sum_out)), sum_out)
            # plt.title("cross-correlation output full 1D fft cross-correlation")
            # plt.xlabel('time')
            # plt.ylabel('Amplitude')
            # plt.show()
            # crop the output to the expected shape
            # print("shape of expected resuls: ", out[nn, ff].shape)
            # print("shape of sum_out: ", sum_out.shape)
            out[nn, ff] = sum_out + b[ff]

    cache = (x, w, b, conv_param)
    return out, cache


def reconstruct_signal(xfft, fft_size):
    xfft = np.concatenate(
        (xfft, np.zeros(max(fft_size // 2 - len(xfft) + 1, 0))))
    xfft = np.concatenate((xfft, np.conj(np.flip(xfft[1:-1], axis=0))))
    return xfft


log_file = "index_back_filter_signal2" + get_log_time() + ".log"


def correlate_signals(x, y, fft_size, out_size, preserve_energy_rate=None,
                      index_back=None):
    """
    Cross-correlation of the signals: x and h.

    :param x: input signal
    :param y: filter
    :param out_len: required output len
    :param preserve_energy_rate: compressed to this energy rate
    :param index_back: how many coefficients to remove
    :return: output signal after correlation of signals x and h

    >>> x = [1.0,2.0,3.0,4.0]
    >>> h = [1.0,3.0]
    >>> result = correlate_signals(x=x, h=h, fft_size=len(x), out_size=(len(x)-len(h) + 1))
    >>> expected_result = np.correlate(x, h, mode='valid')
    >>> np.testing.assert_array_almost_equal(result, expected_result)

    >>> x = np.random.rand(10)
    >>> h = np.random.rand(3)
    >>> result = correlate_signals(x=x, h=h, fft_size=len(x), out_size=(len(x)-len(h) + 1))
    >>> expected_result = np.correlate(x, h, mode='valid')
    >>> np.testing.assert_array_almost_equal(result, expected_result)

    >>> x = np.random.rand(100)
    >>> h = np.random.rand(11)
    >>> result = correlate_signals(x=x, h=h, fft_size=len(x), out_size=(len(x)-len(h) + 1))
    >>> expected_result = np.correlate(x, h, mode='valid')
    >>> np.testing.assert_array_almost_equal(result, expected_result)
    """
    # print("x input size: ", x)
    # print("fft size: ", fft_size)
    xfft = fft(x, fft_size)
    yfft = fft(y, fft_size)
    if preserve_energy_rate is not None or index_back is not None:
        index_xfft = half_preserve_energy_index(xfft, preserve_energy_rate,
                                                index_back)
        index_yfft = half_preserve_energy_index(yfft, preserve_energy_rate,
                                                index_back)
        # with open(log_file, "a+") as f:
        #     f.write("index: " + str(compress_rate) + ";preserved energy input: " + str(
        #         compute_energy(xfft[:index]) / compute_energy(xfft[:fft_size // 2 + 1])) +
        #             ";preserved energy filter: " + str(
        #         compute_energy(yfft[:index]) / compute_energy(yfft[:fft_size // 2 + 1])) + "\n")
        index = max(index_xfft, index_yfft)
        xfft = xfft[:index]
        yfft = yfft[:index]
        # print("the signal size after compression: ", index)
        xfft = reconstruct_signal(xfft, fft_size)
        yfft = reconstruct_signal(yfft, fft_size)
    out = ifft(xfft * np.conj(yfft))

    # plot_signal(out, "out after ifft")
    out = out[:out_size]
    # plot_signal(out, "after truncating to xlen: " + str(x_len))
    return_value = np.real(out)
    return return_value


def get_full_energy(xfft):
    """
    Return the full energy of the signal. The energy E(xfft) of a sequence xfft is defined as the sum of energies
    (squares of the amplitude |x|) at every point of the sequence.

    see: http://www.cs.cmu.edu/~christos/PUBLICATIONS.OLDER/sigmod94.pdf (equation 7)

    :param x: an array of complex numbers
    :return: the full energy of signal x

    >>> x = np.array([1.2 + 1.0j])
    >>> full_energy, squared = get_full_energy(x)
    >>> np.testing.assert_almost_equal(full_energy, 2.4400, decimal=4)
    >>> np.testing.assert_array_almost_equal(squared, np.array([2.4400]))

    >>> x = np.array([1.2 + 1.0j, 0.5 + 1.4j])
    >>> full_energy, squared = get_full_energy(x)
    >>> expected_squared = np.power(np.absolute(np.array(x)), 2)
    >>> expected_full_energy = np.sum(expected_squared)
    >>> np.testing.assert_almost_equal(full_energy, expected_full_energy, decimal=4)
    >>> np.testing.assert_array_almost_equal(squared, expected_squared, decimal=4)

    >>> x = np.array([-10.0 + 1.5j, 2.5 + 1.8j, 1.0 -9.0j])
    >>> full_energy, squared = get_full_energy(x)
    >>> expected_squared = np.power(np.absolute(np.array(x)), 2)
    >>> expected_full_energy = np.sum(expected_squared)
    >>> np.testing.assert_almost_equal(full_energy, expected_full_energy, decimal=4)
    >>> np.testing.assert_array_almost_equal(squared, expected_squared, decimal=4)
    """
    # squared = np.abs(xfft) ** 2
    squared = np.imag(xfft) ** 2 + np.real(xfft) ** 2
    full_energy = np.sum(squared)
    return full_energy, squared


def half_preserve_energy_index(xfft, energy_rate=None, index_back=None):
    """
    The same as the function preserve_energy_index but we discard half of the input signal since it is Hermitian
    symmetric.
    """
    initial_length = len(xfft)
    half_fftsize = initial_length // 2  # the signal in frequency domain is symmetric so we can discard one half
    xfft = xfft[0:half_fftsize + 1]  # we preserve the middle element
    return preserve_energy_index(xfft, energy_rate, index_back)


def preserve_energy_index(xfft, energy_rate=None, index_back=None):
    """
    To which index should we preserve the xfft signal (and discard the remaining coefficients). This is based on the
    provided energy_rate, or if the energy_rate is not provided, then compress_rate is applied. If none of the params are
    provided, we

    :param xfft: the input signal to be truncated
    :param energy_rate: how much energy should we preserve in the xfft signal
    :param index_back: how many coefficients of xfft should we discard counting from the back of the xfft
    :return: calculated index, no truncation applied to xfft itself, returned at least the index of first coefficient

    >>> xfft = np.array([3.+10.j, 1.+1.j, 0.1+0.1j])
    >>> squared_numpy = np.power(np.absolute(xfft), 2)
    >>> full_energy_numpy = np.sum(squared_numpy)
    >>> # set energy rate to preserve only the first and second coefficients
    >>> energy_rate = squared_numpy[0]/full_energy_numpy + 0.0001
    >>> result = preserve_energy_index(xfft, energy_rate=energy_rate)
    >>> np.testing.assert_equal(result, 2)
    >>> # set energy rate to preserved only the first coefficient
    >>> energy_rate = squared_numpy[0]/full_energy_numpy - 0.0001
    >>> result = preserve_energy_index(xfft, energy_rate=energy_rate)
    >>> np.testing.assert_equal(result, 1)

    >>> xfft = np.array([1.+2.j, 3.+ 4.j, 0.1 + 0.1j])
    >>> result = preserve_energy_index(xfft, energy_rate=1.0)
    >>> np.testing.assert_equal(result, 3)

    >>> xfft = np.array([])
    >>> result = preserve_energy_index(xfft, energy_rate=1.0)
    >>> np.testing.assert_equal(result, None)

    >>> xfft = [1.+2.j, 3.+4.j]
    >>> result = preserve_energy_index(xfft)
    >>> np.testing.assert_equal(result, 2)

    >>> xfft = [1.+2.j, 3. + 4.j, 5.+6.j]
    >>> result = preserve_energy_index(xfft, compress_rate=1)
    >>> np.testing.assert_equal(result, 2)

    >>> xfft = np.array([1.+2.j, 3.+4.j, 0.1+0.1j])
    >>> result = preserve_energy_index(xfft, energy_rate=0.9)
    >>> np.testing.assert_equal(result, 2)

    >>> xfft = np.array([3.+10.j, 1.+1.j, 0.1+0.1j])
    >>> result = preserve_energy_index(xfft, energy_rate=0.5)
    >>> np.testing.assert_equal(result, 1)

    >>> xfft = np.array([3.+10.j, 1.+1.j, 0.1+0.1j])
    >>> result = preserve_energy_index(xfft, energy_rate=0.0)
    >>> np.testing.assert_equal(result, 1)

    """
    if xfft is None or len(xfft) == 0:
        return None
    if energy_rate is not None:
        # squared = np.power(np.absolute(xfft), 2)
        squared = np.imag(xfft) ** 2 + np.real(xfft) ** 2
        full_energy = np.sum(squared)  # sum of squared values of the signal
        current_energy = 0.0
        preserved_energy = full_energy * energy_rate
        index = 0
        while current_energy < preserved_energy and index < len(squared):
            current_energy += squared[index]
            index += 1
        return max(index, 1)
    elif index_back is not None:
        return len(xfft) - index_back
    return len(xfft)  # no truncation applied to xfft


def convolve1D_fft(x, w, fftsize, out_size, preserve_energy_rate=1.0):
    """
    Convolve inputs x and w using fft.
    :param x: the first signal in time-domain (1 dimensional)
    :param w: the second signal in time-domain (1 dimensional)
    :param fftsize: the size of the transformed signals (in the frequency domain)
    :param out_size: the expected size of the output
    :param preserve_energy_rate: how much energy of the signal to preserve in the frequency domain
    :return: the output of the convolved signal x and w
    """
    xfft = fft(x, fftsize)
    filterfft = fft(w, fftsize)
    if preserve_energy_rate is not None:
        half_fftsize = fftsize // 2
        xfft = xfft[0:half_fftsize]
        filterfft = filterfft[0:half_fftsize]
        squared_abs = np.abs(xfft) ** 2
        full_energy = np.sum(squared_abs)
        current_energy = 0.0
        preserve_energy = full_energy * preserve_energy_rate
        index = 0
        while current_energy < preserve_energy and index < len(squared_abs):
            current_energy += squared_abs[index]
            index += 1
        # print("index: ", index)
        xfft = xfft[:index]
        # plot_signal(np.abs(filterfft), "Before compression in frequency domain")
        full_energy_filter = np.sum(np.abs(filterfft) ** 2)
        filterfft = filterfft[:index]
        # filter_lost_energy_rate = (full_energy_filter - np.sum(np.abs(filterfft) ** 2)) / full_energy_filter
        # print("filter_lost_energy_rate: ", filter_lost_energy_rate)
        # plot_signal(np.abs(filterfft), "After compression in frequency domain")
    # xfft = xfft / norm(xfft)
    # filterfft = filterfft / norm(filterfft)
    out = xfft * np.conj(filterfft)
    out = np.pad(out, (0, fftsize - len(out)), 'constant')
    out = ifft(out)
    out = np.real(out)
    if preserve_energy_rate is not None:
        # out *= len(out)
        out *= 2
    if len(out) < out_size:
        out = np.pad(out, (0, out_size - len(out)), 'constant')
    out = out[:out_size]
    # import matplotlib.pyplot as plt
    # plt.plot(range(0, len(out)), out)
    # plt.title("cross-correlation output fft")
    # plt.xlabel('time')
    # plt.ylabel('Amplitude')
    # plt.show()
    return out


def convolve1D_fft_new(x, w, fftsize, out_size, preserve_energy_rate=1.0):
    """
    Convolve inputs x and w using fft.

    :param x: the first signal in time-domain (1 dimensional)
    :param w: the second signal in time-domain (1 dimensional)
    :param fftsize: the size of the transformed signals (in the frequency domain)
    :param out_size: the expected size of the output
    :param preserve_energy_rate: how much energy of the signal to preserve in the frequency domain
    :return: the output of the convolved signal x and w
    """
    xfft = fft(x, fftsize)
    filterfft = np.fft.fft(w, fftsize)
    plot_signal_time(np.abs(xfft), "full signal")
    plot_signal_time(np.abs(filterfft), "full filter")
    if preserve_energy_rate is not None:
        initial_energy = np.sum(np.abs(xfft) ** 2)
        half_fftsize = fftsize // 2
        xfft = xfft[0:half_fftsize]
        filterfft = filterfft[0:half_fftsize]
        print("initial number of coefficients: ", half_fftsize)
        squared_abs = np.abs(xfft) ** 2
        full_energy = np.sum(squared_abs)
        current_energy = 0.0
        preserve_energy = full_energy * preserve_energy_rate
        index = 0
        currents = []
        currents.append(0)
        while current_energy < preserve_energy and index < len(squared_abs):
            current_energy += squared_abs[index]
            index += 1
            currents.append(current_energy)
        import matplotlib.pyplot as plt
        plt.plot(range(0, len(currents)), currents / full_energy)
        plt.title("cumulative energy")
        plt.xlabel('# of coefficients')
        plt.ylabel('cumulative energy')
        plt.show()
        print("coefficients preserved: ", index)
        xfft = xfft[:index]
        filterfft = filterfft[:index]
        plot_signal_time(np.abs(xfft), "compressed signal")
        plot_signal_time(np.abs(filterfft), "compressed filter")
    # xfft = xfft / norm(xfft)
    # filterfft = filterfft / norm(filterfft)
    out = xfft * np.conj(filterfft)
    # plot_signal(out, "out after multiplication")
    # out = np.pad(out, (0, fftsize//2 - len(out)), 'constant')
    # out = np.concatenate((out, np.flip(out, axis=0)))
    # plot_signal(out, "out after reversing the signal")
    out = ifft(out)
    out = np.real(out)
    if preserve_energy_rate != None:
        # out *= len(out)
        energy_scale = initial_energy / current_energy
        # print("energy scale:", energy_scale)
        out *= energy_scale
    if len(out) < out_size:
        out = np.pad(out, (0, out_size - len(out)), 'constant')
    out = out[:out_size]
    # if preserve_energy_rate is not None:
    #     print("scale the output signal")
    #     out *= fftsize
    return out


def conv_forward_fft_1D(x, w, b, conv_param):
    """
    Forward pass of 1D convolution.

    The input consists of N data points with each data point representing a time-series of length W.

    We also have the notion of channels in the 1-D convolution. We want to use more than a single filter even for the
    input time-series, so the output is a batch with the same size but the number of output channels is equal to the
    number of input filters.

    :param x: Input data of shape (N, C, W), N - number of data points in the batch, C - number of channels, W - the
    width of the time-series (number of data points in a univariate series)
    :param w: Filter weights of shape (F, C, WW),F - number of filters, C - number of channels, WW - size of the filter
    :param b: biases, of shape (F,)
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
     - out: output data, of shape (N, F, W') where W' is given by: W' = 1 + (W + 2*pad - WW) / stride
     - cache: (x, w, b, conv_param)

     :see:  source short: https://goo.gl/GwyhXz
     full: https://stackoverflow.com/questions/40703751/
     using-fourier-transforms-to-do-convolution?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1}
    >>> result, cache = conv_forward_fft_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> # expected_result = [4., 7.]
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1, 'preserve_energy_rate' :0.9}
    >>> result, cache = conv_forward_fft_1D(x, h, b, conv_param)
    >>> expected_result = [3.5, 7.5]
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    """
    preserve_energy_rate = conv_param.get('preserve_energy_rate', None)
    index_back = conv_param.get('compress_rate', None)
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')
    if stride != 1:
        raise ValueError(
            "convolution via fft can have stride only 1, but given: " + str(
                stride))
    N, C, W = x.shape
    F, C, WW = w.shape
    fftsize = next_power2(W + WW - 1)
    # pad only the dimensions for the time-series (and neither data points nor the channels)
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad, pad)), 'constant'))
    out_W = W + 2 * pad - WW + 1

    out = np.zeros([N, F, out_W])
    for nn in range(N):  # For each time-series in the input batch.
        for ff in range(F):  # For each filter in w
            for cc in range(C):
                out[nn, ff] += correlate_signals(padded_x[nn, cc], w[ff, cc],
                                                 fftsize,
                                                 out_size=out_W,
                                                 preserve_energy_rate=preserve_energy_rate,
                                                 index_back=index_back)
            out[nn, ff] += b[ff]  # add the bias term

    cache = (x, w, b, conv_param, fftsize)
    return out, cache


def conv_backward_fft_1D(dout, cache):
    """
    An fft-based implementation of the backward pass for a 1D convolutional layer.

    Inputs:
    - dout: Upstream derivatives.
    - cache: A tuple of (x, w, b, conv_param) as in conv_forward_fft_1D

    Returns a tuple of:
    - dx: Gradient with respect to x
    - dw: Gradient with respect to w
    - db: Gradient with respect to b

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1}
    >>> dout = np.array([[[0.1, -0.2]]])
    >>> # first, get the expected results from direct naive approach to convolution
    >>> result, cache = conv_forward_naive_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> # is the forward naive convolution correct?
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    >>> expected_dx, expected_dw, expected_db = conv_backward_naive_1D(dout, cache)
    >>> # get the results from the backward pass
    >>> result, cache = conv_forward_fft_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> # is the FFT based forward convolution correct?
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    >>> # finally: are the gradients correct?
    >>> dx, dw, db = conv_backward_fft_1D(dout, cache)
    >>> np.testing.assert_array_almost_equal(dx, expected_dx)
    >>> np.testing.assert_array_almost_equal(dw, expected_dw)
    >>> np.testing.assert_array_almost_equal(db, expected_db)
    """
    x, w, b, conv_param, fftsize = cache
    preserve_energy_rate = conv_param.get('preserve_energy_rate', None)
    index_back = conv_param.get('compress_rate', None)
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')
    if stride != 1:
        raise ValueError("fft requires stride = 1, but given: ", stride)

    N, C, W = x.shape
    F, C, WW = w.shape
    N, F, W_out = dout.shape

    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad, pad)), 'constant'))

    # W = padded_out_W - WW + 1; padded_out_W = W + WW - 1; pad_out = W + WW - 1 // 2
    pad_out = (W + WW - 1 - W_out) // 2
    # print("pad_out: ", pad_out)
    if pad_out < 0:
        padded_dout = dout[:, :, abs(pad_out):pad_out]
    else:
        padded_dout = np.pad(dout, ((0, 0), (0, 0), (pad_out, pad_out)),
                             mode='constant')

    # Initialize gradient output tensors.
    dx = np.zeros_like(x)  # the x used for convolution was with padding
    dw = np.zeros_like(w)
    db = np.zeros_like(b)

    # Calculate dB (the gradient for the bias term).
    # We sum up all the incoming gradients for each filters bias (as in the affine layer).
    for ff in range(F):
        db[ff] += np.sum(dout[:, ff, :])

    # print("padded x: ", padded_x)
    # print("dout: ", dout)
    # Calculate dw - the gradient for the filters w.
    # By chain rule dw is computed as: dout*x
    fftsize = next_power2(W + W_out - 1)
    for nn in range(N):
        for ff in range(F):
            for cc in range(C):
                # accumulate gradient for a filter from each channel
                # dw[ff, cc] += convolve1D_fft(padded_x[nn, cc], np.flip(dout[nn, ff], axis=0), fftsize, WW,
                #                              preserve_energy_rate=preserve_energy_rate)
                dw[ff, cc] += correlate_signals(padded_x[nn, cc], dout[nn, ff],
                                                fftsize, WW,
                                                preserve_energy_rate=preserve_energy_rate,
                                                index_back=index_back)
                # print("dw fft: ", dw[ff, cc])

    # Calculate dx - the gradient for the input x.
    # By chain rule dx is dout*w. We need to make dx same shape as padded x for the gradient calculation.
    # fftsize = next_power2(W_out + WW - 1)
    # print("padded_dout len: ", padded_dout.shape[-1])
    # print("W_out len: ", W_out)
    # fftsize = W
    fftsize = next_power2(padded_dout.shape[-1] + WW - 1)
    # print("fftsize: ", fftsize)
    for nn in range(N):
        for ff in range(F):
            for cc in range(C):
                # print("dout[nn, ff]: ", dout[nn, ff])
                # print("dout[nn, ff] shape: ", dout[nn, ff].shape)
                # print("padded_dout[nn, ff] shape: ", padded_dout[nn, ff].shape)
                # print("w[ff, cc]: ", w[ff, cc])
                # print("w[ff, cc] shape: ", w[ff, cc].shape)
                # dx[nn, cc] += correlate_signals(padded_dout[nn, ff], np.flip(w[ff, cc], axis=0), fftsize, W,
                #                                 preserve_energy_rate=preserve_energy_rate, compress_rate=compress_rate)
                dx[nn, cc] += correlate_signals(padded_dout[nn, ff],
                                                np.flip(w[ff, cc], axis=0),
                                                fftsize, W,
                                                preserve_energy_rate=preserve_energy_rate,
                                                index_back=index_back)
                # print("dx fft: ", dx[nn, cc])

    return dx, dw, db


def conv_forward_numpy_1D(x, w, b, conv_param):
    """
    Forward pass of 1D convolution.

    The input consists of N data points with each data point representing a time-series of length W.

    We also have the notion of channels in the 1-D convolution. We want to use more than a single filter even for the
    input time-series, so the output is a the batch with the same size but the number of output channels is equal to the
    number of input filters.

    :param x: Input data of shape (N, C, W)
    :param w: Filter weights of shape (F, C, WW)
    :param b: biases, of shape (F,)
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
     - out: output data, of shape (N, W') where W' is given by:
     W' = 1 + (W + 2*pad - WW) / stride
     - cache: (x, w, b, conv_param)

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1}
    >>> result, cache = conv_forward_numpy_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    """
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')
    if stride != 1:
        raise ValueError("numpy requires stride = 1, but given: ", stride)
    N, C, W = x.shape
    F, C, WW = w.shape
    out_W = W + 2 * pad - WW + 1
    out = np.zeros([N, F, out_W])
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad, pad)), 'constant'))
    for nn in range(N):  # For each time-series in the input batch.
        for ff in range(F):  # For each filter in w
            for cc in range(C):
                out[nn, ff] += np.correlate(padded_x[nn, cc], w[ff, cc],
                                            mode="valid")
            # we have a single bias per filter
            # at the end - sum all the values in the obtained tensor
            out[nn, ff] += b[ff]

    cache = (x, w, b, conv_param)
    return out, cache


def conv_backward_numpy_1D(dout, cache):
    """
    A numpy-based implementation of the backward pass for a 1D convolutional layer.

    Inputs:
    - dout: Upstream derivatives.
    - cache: A tuple of (x, w, b, conv_param) as in conv_forward_numpy

    Returns a tuple of:
    - dx: Gradient with respect to x
    - dw: Gradient with respect to w
    - db: Gradient with respect to b

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1}
    >>> dout = np.array([[[0.1, -0.2]]])
    >>> # first, get the expected results from direct naive approach to convolution
    >>> result, cache = conv_forward_naive_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> # is the forward naive convolution correct?
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    >>> expected_dx, expected_dw, expected_db = conv_backward_naive_1D(dout, cache)
    >>> # get the results from the backward pass
    >>> result, cache = conv_forward_numpy_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> # is the FFT based forward convolution correct?
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    >>> # finally: are the gradients correct?
    >>> dx, dw, db = conv_backward_numpy_1D(dout, cache)
    >>> np.testing.assert_array_almost_equal(dx, expected_dx)
    >>> np.testing.assert_array_almost_equal(dw, expected_dw)
    >>> np.testing.assert_array_almost_equal(db, expected_db)
    """
    dx, dw, db = None, None, None
    x, w, b, conv_param = cache
    stride = conv_param.get('stride')
    if stride != 1:
        raise ValueError("numpy requires stride = 1, but given: ", stride)
    pad = conv_param.get('pad')

    N, C, W = x.shape
    F, C, WW = w.shape
    N, F, W_out = dout.shape

    padded_x = np.pad(x, ((0, 0), (0, 0), (pad, pad)), mode='constant')

    # W = padded_out_W - WW + 1; padded_out_W = W + WW - 1; pad_out = W + WW - 1 // 2
    pad_out = (W + WW - 1 - W_out) // 2
    # print("pad_out: ", pad_out)
    if pad_out < 0:
        padded_dout = dout[:, :, abs(pad_out):pad_out]
    else:
        padded_dout = np.pad(dout, ((0, 0), (0, 0), (pad_out, pad_out)),
                             mode='constant')

    # Initialise gradient output tensors.
    dx = np.zeros_like(x)  # the x used for convolution was with padding
    dw = np.zeros_like(w)
    db = np.zeros_like(b)

    # Calculate dB.
    # Just like in the affine layer we sum up all the incoming gradients for each filters bias.
    for ff in range(F):
        db[ff] += np.sum(dout[:, ff, :])

    # print("padded x: ", padded_x)
    # print("dout: ", dout)
    # Calculate dw.
    # By chain rule dw is dout*x
    for nn in range(N):
        for ff in range(F):
            for cc in range(C):
                # accumulate gradient for a filter from each channel
                dw[ff, cc] += np.correlate(padded_x[nn, cc], dout[nn, ff],
                                           mode="valid")
                # print("dw numpy: ", dw[ff, cc])

    # Calculate dx.
    # By chain rule dx is dout*w. We need to make dx same shape as padded x for the gradient calculation.
    for nn in range(N):
        for ff in range(F):
            for cc in range(C):
                # print("dout[nn, ff]: ", dout[nn, ff])
                # print("dout[nn, ff] shape: ", dout[nn, ff].shape)
                # print("w[ff, cc]: ", w[ff, cc])
                # print("w[ff, cc] shape: ", w[ff, cc].shape)
                dx[nn, cc] += np.correlate(padded_dout[nn, ff],
                                           np.flip(w[ff, cc], axis=0),
                                           mode="valid")
                # print("dx fft: ", dx[nn, cc])
    return dx, dw, db


def conv_forward_naive_1D(x, w, b, conv_param):
    """
    Forward pass of 1D convolution.

    The input consists of N data points with each data point representing a time-series of length W.

    We also have the notion of channels in the 1-D convolution. We want to use more than a single filter even for the
    input time-series, so the output is a the batch with the same size but the number of output channels is equal to the
    number of input filters.

    :param x: Input data of shape (N, C, W)
    :param w: Filter weights of shape (F, C, WW)
    :param b: biases, of shape (F,)
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
     - out: output data, of shape (N, W') where W' is given by:
     W' = 1 + (W + 2*pad - WW) / stride
     - cache: (x, w, b, conv_param)

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1}
    >>> result, cache = conv_forward_naive_1D(x, h, b, conv_param)
    >>> # print("result: ", result)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    """
    pad = conv_param.get('pad')
    if isinstance(pad, int):
        pad_left = pad
        pad_right = pad
    else:
        pad_left = pad[0]
        pad_right = pad[1]
    stride = conv_param.get('stride')

    N, C, W = x.shape
    F, C, WW = w.shape

    # Zero pad our tensor along the spatial dimensions.
    # Do not pad N (0,0) and C (0,0) dimensions, but only the 1D array - the W dimension (pad, pad).
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad_left, pad_right)), 'constant'))

    # Calculate output spatial dimensions.
    out_W = np.int(((W + pad_left + pad_right - WW) / stride) + 1)

    # Initialise the output.
    out = np.zeros([N, F, out_W])

    # Naive convolution loop.
    for nn in range(N):  # For each time-series in the input batch.
        for ff in range(F):  # For each filter in w
            for ii in range(0, out_W):  # For each output value
                for cc in range(C):
                    # multiplying tensors - we sum all values along all channels
                    out[nn, ff, ii] = \
                        np.sum(
                            # padded x is multiplied for the range: from ii*stride to ii*stride + WW
                            w[ff, ...] * padded_x[nn, :,
                                         ii * stride: ii * stride + WW]) + b[ff]
                # we have a single bias per filter
                # at the end - sum all the values in the obtained tensor
    # import matplotlib.pyplot as plt
    # plt.plot(range(0, len(out[0, 0])), out[0, 0])
    # plt.title("cross-correlation output direct (naive)")
    # plt.xlabel('time')
    # plt.ylabel('Amplitude')
    # plt.show()
    cache = (x, w, b, conv_param)
    return out, cache


def compress_fft_1D_fast(x, y_len):
    """
    Compress the fft signal fast with padding to the next power of 2.

    :param x: input 1D signal
    :param y_len: the length of the output. Based on this value, we calculate the discard_count: how many
    coefficients (in the frequency domain) we should discard from both halves of the input x signal
    :return: compressed signal
    """
    x_len = len(x)
    # print("energy of x: ", energy(x))
    fft_len = next_power2(x_len)
    # take the Fourier matrix for FFT in its standard form: 1/sqrt(N) * FourierMatrix to preserve scale of energies
    # in the input and output of the fft
    xfft = fft(x, fft_len) / np.sqrt(fft_len)
    # print("energy of uncompressed xfft: ", energy(np.abs(xfft)))
    plot_signal_time(np.abs(xfft), title="xfft before compression")
    discard_count = (x_len - y_len) // 2 + (fft_len - x_len) // 2
    # print("discard count: ", discard_count)
    half_fft_len = fft_len // 2
    zeros = np.zeros(discard_count, dtype=complex)
    xfft[half_fft_len - discard_count:half_fft_len] = zeros
    xfft[half_fft_len:half_fft_len + discard_count] = zeros
    # print("energy of compressed xfft: ", energy(np.abs(xfft)))
    plot_signal_time(np.abs(xfft), title="xfft after compression")
    # print("xfft len after compression: ", len(xfft))
    # print("expected y_len: ", y_len)
    y = ifft(xfft) * np.sqrt(fft_len)
    # print("size of the output: ", len(h))
    y = np.real(y)
    # print("energy of h before truncation: ", energy(h))
    plot_signal_time(y, "h after ifft and real")
    y = y[:y_len]
    plot_signal_time(y, "h after truncation to y_len")
    # h = h * energy(x) / energy(h) # scale the signal
    # print("energy ratio: ", energy(h) / energy(x))
    # print("len ratio: ", x_len / y_len)
    # print("energy of h: ", energy(h))
    return y


def compress_spectral_1D(x, y_len):
    """
    Compress the signal (this is the forward step) in the spectral domain.

    :param x: input 1D signal
    :param y_len: the length of the output. Based on this value, we calculate the discard_count: how many
    coefficients (in the frequency domain) we should discard from both halves of the input x signal
    :return: compressed signal
    """
    assert y_len >= 3
    xfft = fft(x, norm="ortho")
    if y_len % 2 == 1:
        n = (y_len - 1) // 2
    # TODO


def compress_fft_1D(x, y_len):
    """
    Compress the fft signal (this is the forward step).

    :param x: input 1D signal
    :param y_len: the length of the output. Based on this value, we calculate the discard_count: how many
    coefficients (in the frequency domain) we should discard from both halves of the input x signal
    :return: compressed signal
    """
    # x_len = len(x)
    # print("energy of x: ", energy(x))
    # take the Fourier matrix for FFT in its standard form: 1/sqrt(N) * FourierMatrix to preserve scale of energies
    # in the input and output of the fft
    # xfft = fft(x) / np.sqrt(x_len)
    # xfft = rfft(x, norm="ortho")
    xfft = rfft(x)
    # plot_signal(xfft, "signal x after rfft")
    # print("energy of uncompressed xfft: ", energy(np.abs(xfft)))
    # plot_signal(np.abs(xfft), title="xfft before compression")
    # discard_count = (x_len - y_len) // 2
    # half_fft_len = len(xfft) // 2
    # xfft_first_half = xfft[:half_fft_len - discard_count]
    # if y_len % 2 == x_len % 2:
    #     xfft_first_half = np.append(xfft_first_half, np.zeros(1))
    # xfft = np.append(xfft_first_half, xfft[half_fft_len + 1 + discard_count:])
    # print("energy of compressed xfft: ", energy(np.abs(xfft)))
    # plot_signal(np.abs(xfft), title="xfft after compression")
    # print("xfft len after compression: ", len(xfft))
    # print("expected y_len: ", y_len)
    # h = irfft(xfft, norm="ortho", n=y_len)
    y = irfft(xfft, n=y_len)
    # yfft = fft(h, 512)
    # plot_signal(h, "signal h after irfft")
    # plot_signal(ifft(yfft), "signal yfft after inverse 512")
    # print("size of the output: ", len(h))
    # h = np.real(h)
    # plot_signal(h, "h after ifft and real")
    # print("energy ratio: ", energy(h)/energy(x))
    return y


def compress_fft_1D_gradient(g, x_len):
    """
    Compress the fft signal - this is the backward propagation for fft 1D compression.

    The final returned gradient should be: gradient_out = g (the input gradient) * gradient_fft compression with respect
    to h - which is just the Fourier (transformation) matrix.

    :param g: the gradient: the gradient of the loss L with respect to the output of the 1D fft compression h
    \frac{\gradient L}{\gradient of \hat{h}}
    :param y_len: the length of the output. Based on this value, we calculate the pad_count: how many
    zeros we should add (in the frequency domain) to both halves of the gradient signal g.
    :return: gradient of the loss R with respect to x (the input signal to the forward 1D fft compression).
    """

    # g_len = len(g)
    # plot_signal(g, "g input gradients")
    # gfft = rfft(g, norm="ortho")
    gfft = rfft(g)
    # plot_signal(gfft, "first gfft after rfft")
    # discard_count = (x_len - g_len) // 2
    # half_fft_len = len(gfft) // 2
    # gfft_first_half = np.append(gfft[:half_fft_len], np.zeros(discard_count))
    # gfft_first_half = np.append(gfft_first_half, gfft[half_fft_len])
    # if g_len % 2 != x_len % 2:
    #     gfft_first_half = np.append(gfft_first_half, np.zeros(1))
    # gfft_second_half = np.append(np.zeros(discard_count), gfft[half_fft_len + 1:])
    # gfft_padded = np.append(gfft_first_half, gfft_second_half)
    # plot_signal(gfft_padded, "gfft padded: ")
    # dx = irfft(gfft, norm="ortho", n=x_len)
    dx = irfft(gfft, n=x_len)
    # dx = np.real(dx)
    # plot_signal(dx, "output of the dx after irfft")
    return dx


def fft_pool_forward_1D(x, pool_param):
    """
    An fft-based implementation of the forward pass for a pooling layer.

    Inputs:
    - x: Input data, of shape (N, C, W)
    - pool_param: dictionary with the following keys:
      - 'pool_height': The height of each pooling region
      - 'pool_width': The width of each pooling region
      - 'stride': The distance between adjacent pooling regions
      - these keys are used to calculate the expected size of the output

    Returns a tuple of:
    - out: Output data
    - cache: (x, pool_param)
    """
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    N, C, W = x.shape

    # Calculate output spatial dimensions of the output of max pool.
    out_W = np.int(((W - pool_width) // stride) + 1)

    # Initialise output.
    out = np.zeros([N, C, out_W])
    for n in range(N):
        for c in range(C):
            out[n, c] = compress_fft_1D(x[n, c], out_W)

    cache = (x, pool_param)
    return out, cache


def fft_pool_backward_1D(dout, cache):
    """
    An fft base implementation of the backward pass for a 1D fft pooling layer.

    Inputs:
    - dout: Upstream derivatives
    - cache: A tuple of (x, pool_param) as in the forward pass.

    Returns:
    - dx: Gradient with respect to x
    """
    x, pool_param = cache

    N, C, W = x.shape
    N, C, dout_W = dout.shape

    # Initialise dx to be same shape as fft pool input x.
    dx = np.zeros_like(x)

    for n in range(N):
        for c in range(C):
            dx[n, c] = compress_fft_1D_gradient(dout[n, c], W)

    return dx


def max_pool_forward_naive_1D(x, pool_param):
    """
    A naive implementation of the forward pass for a max pooling layer.

    Inputs:
    - x: Input data, of shape (N, C, W)
    - pool_param: dictionary with the following keys:
      - 'pool_width': The width of each pooling region
      - 'stride': The distance between adjacent pooling regions

    Returns a tuple of:
    - out: Output data
    - cache: (x, pool_param)
    """
    out = None
    ###########################################################################
    # TODO: Implement the 1D max pooling forward pass                         #
    ###########################################################################

    # Grab the pooling parameters.
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    N, C, W = x.shape

    # Calculate output spatial dimensions of the output of max pool.
    out_W = np.int(((W - pool_width) // stride) + 1)

    # Initialise output.
    out = np.zeros([N, C, out_W])

    # Naive maxpool for loop.
    for n in range(N):  # For each time-series (in the batch).
        for c in range(C):  # For each channel.
            for i in range(out_W):  # For each output value.
                out[n, c, i] = np.max(
                    x[n, c, i * stride: i * stride + pool_width])

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = (x, pool_param)
    return out, cache


def max_pool_backward_naive_1D(dout, cache):
    """
    A naive implementation of the backward pass for a 1D max pooling layer.

    Inputs:
    - dout: Upstream derivatives
    - cache: A tuple of (x, pool_param) as in the forward pass.

    Returns:
    - dx: Gradient with respect to x
    """
    dx = None
    ###########################################################################
    # TODO: Implement the 1D max pooling backward pass                        #
    ###########################################################################

    # Grab the pooling parameters.
    x, pool_param = cache
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    N, C, W = x.shape
    N, C, dout_W = dout.shape

    # Initialise dx to be same shape as maxpool input x.
    dx = np.zeros_like(x)

    for n in range(N):
        for c in range(C):
            for w in range(dout_W):
                current_vector = x[n, c, w * stride: w * stride + pool_width]
                current_max = np.max(current_vector)
                for i in range(pool_width):
                    if current_vector[i] == current_max:
                        dx[n, c, w * stride + i] += dout[n, c, w]

    # # Naive loop to backprop dout through maxpool layer.
    # for n in range(N):  # For each time-series.
    #     for c in range(C):  # For each channel.
    #         for i in range(dout_W):  # For each value of the upstream gradient.
    #             # Using argmax get the linear index of the max of each segment.
    #             # print(x[n, c, i * stride: i * stride + pool_width])
    #             max_index = np.argmax(x[n, c, i * stride: i * stride + pool_width])
    #             # print("backward pool max index: ", max_index)
    #             # Using unravel_index convert this linear index to matrix coordinate.
    #             max_coord = np.unravel_index(max_index, [pool_width])
    #             # print("backward pool max coord: ", max_coord)
    #             # Only backprop the dout to the max location.
    #             dx[n, c, i * stride: i * stride + pool_width][max_coord] += dout[n, c, i]

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    return dx


def conv_backward_naive_1D(dout, cache):
    """
    A naive implementation of the backward pass for a 1D convolutional layer.

    Inputs:
    - dout: Upstream derivatives.
    - cache: A tuple of (x, w, b, conv_param) as in conv_forward_naive

    Returns a tuple of:
    - dx: Gradient with respect to x
    - dw: Gradient with respect to w
    - db: Gradient with respect to b

    >>> x = np.array([[[1., 2., 3.]]])
    >>> h = np.array([[[2., 1.]]])
    >>> b = np.array([0.0])
    >>> conv_param = {'pad' : 0, 'stride' :1}
    >>> result, cache = conv_forward_naive_1D(x, h, b, conv_param)
    >>> expected_result = np.correlate(x[0, 0,:], h[0, 0,:], mode="valid")
    >>> np.testing.assert_array_almost_equal(result, np.array([[expected_result]]))
    >>> dout = np.array([[[0.1, -0.2]]])
    >>> dx, dw, db = conv_backward_naive_1D(dout, cache)
    >>> np.testing.assert_array_almost_equal(dx, np.array([[[ 0.2, -0.3, -0.2]]]))
    >>> np.testing.assert_array_almost_equal(dw, np.array([[[-0.3, -0.4]]]))
    >>> np.testing.assert_array_almost_equal(db, np.array([-0.1]))
    """
    dx, dw, db = None, None, None
    # print("cache: ", cache)
    # print("dout: ", dout)
    # Grab conv parameters and pad x if needed.
    x, w, b, conv_param = cache
    stride = conv_param.get('stride')
    pad = conv_param.get('pad')
    if isinstance(pad, int):
        pad_left = pad
        pad_right = pad
    else:
        pad_left = pad[0]
        pad_right = pad[1]
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad_left, pad_right)), 'constant'))
    # print("padded x:", padded_x)

    N, C, W = x.shape
    F, C, WW = w.shape
    N, F, W_out = dout.shape

    # Initialise gradient output tensors.
    dx_temp = np.zeros_like(padded_x)
    dw = np.zeros_like(w)
    db = np.zeros_like(b)

    # Calculate dB.
    # Just like in the affine layer we sum up all the incoming gradients for each filters bias.
    for ff in range(F):
        db[ff] += np.sum(dout[:, ff, :])

    # Calculate dw.
    # By chain rule dw is dout*x
    for nn in range(N):
        for ff in range(F):
            for ii in range(W_out):
                # dF[i] - gradient for the i-th element of the filter
                # dO[j] - gradient for the j-th output of the convolution
                # TS[k] - k-th value of the input time-series
                # dF = convolution(TS, dO)
                # Note that the filter value F[0] influenced 0 + (output-length - WW + 1 = out) values
                # dF[0] = TS[0]*dO[0] + TS[1]*d0[1] + ... + TS[out]*d0[out]
                # dF[1] = TS[1]*dO[0] + TS[2]*dO[1] + ... + TS[out+1]*d0[out]
                # the below computation is element at a time for both df[0] and dF[1]:
                # dF[0:1] += dO[0] * TS[0:1]
                dw[ff, ...] += dout[nn, ff, ii] * padded_x[nn, :,
                                                  ii * stride: ii * stride + WW]

    # Calculate dx.
    # By chain rule dx is dout*w. We need to make dx same shape as padded x for the gradient calculation.
    for nn in range(N):
        for ff in range(F):
            for ii in range(W_out):
                dx_temp[nn, :, ii * stride:ii * stride + WW] += dout[
                                                                    nn, ff, ii] * \
                                                                w[ff, ...]

    # Remove the padding from dx so it matches the shape of x.
    dx = dx_temp[:, :, pad_left: W + pad_right]

    return dx, dw, db


def get_conv_shape(x_shape, w_shape, conv_param):
    """
    Calculate the output shape after the forward pass of the convolution.

    :param x: the input of the convolution
    :param w: the weights of the convolution (filter)
    :param conv_param: the padding and stride of the convolutio
    :return: the output shape after the forward pass of the convolution
    """
    # Grab conv parameters
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')

    H, W = x_shape
    HH, WW = w_shape

    # Calculate output spatial dimensions.
    out_H = np.int(((H + 2 * pad - HH) / stride) + 1)
    out_W = np.int(((W + 2 * pad - WW) / stride) + 1)

    return out_H, out_W


def conv_forward_fftw(x, w, b, conv_param):
    """
    The implementation of convolution via the frequency domain (fft).

    The input consists of N data points, each with C channels, height H and
    width W. We convolve each input with F different filters, where each filter
    spans all C channels and has height HH and width HH.

    :param x: Input data of shape (N, C, H, W)
    :param w: Filter weights of shape (F, C, HH, WW)
    :param b: Biases, of shape (F,) - we have as many bias terms as the number of filters
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
    - out: Output data, of shape (N, F, H', W') where H' and W' are given by
      H' = 1 + (H + 2 * pad - HH) / stride
      W' = 1 + (W + 2 * pad - WW) / stride
    - cache: (x, w, b, conv_param)
    """
    # Grab conv parameters
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')
    if stride != 1:
        raise Exception(
            "Convolution via fft is only possible with stride = 1, while given stride=" + str(
                stride))

    N, C, H, W = x.shape
    F, C, HH, WW = w.shape

    # Calculate the output spatial dimensions.
    out_H, out_W = get_conv_shape((H, W), (HH, WW), conv_param)

    # Zero pad our tensor along the spatial dimensions.
    padded_x = (
        np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)), mode='constant'))

    # Initialise the output.
    # out = np.zeros([N, F, out_H, out_W])
    out = np.zeros([N, F, out_H, out_W])

    fftpadded_x = np.pad(padded_x, ((0, 0), (0, 0), (0, H - 1), (0, W - 1)),
                         mode='constant')
    _, _, Hpad, Wpad = fftpadded_x.shape
    fftpadded_filter = np.pad(w,
                              ((0, 0), (0, 0), (0, Hpad - HH), (0, Wpad - WW)),
                              mode='constant')

    # Hpow2, Wpow2 = find_next_power2(Hpad), find_next_power2(Wpad)
    Hpow2, Wpow2 = Hpad, Wpad

    # Naive convolution loop.
    for nn in range(N):  # For each image in the input batch.
        for ff in range(F):  # For each filter in w
            sum_out = np.zeros([out_H, out_W])
            for cc in range(C):
                xfft = pyfftw.interfaces.numpy_fft.fft2(fftpadded_x[nn, cc],
                                                        (Hpow2, Wpow2))
                # print("xfft: ", xfft)
                # xfft = xfft[:xfft.shape[0] // 2, :xfft.shape[1] // 2]
                # print("xfft shape: ", xfft.shape)
                filterfft = pyfftw.interfaces.numpy_fft.fft2(
                    fftpadded_filter[ff, cc], xfft.shape)
                # filterfft = filterfft[:filterfft.shape[0] // 2, :filterfft.shape[1] // 2]
                # print("filterfft: ", filterfft)
                filterfft = np.conjugate(filterfft)
                # out[nn, ff] += np.abs(np.fft.ifft2(xfft * filterfft, (out_H, out_W)))
                # H2 = H // 2
                # W2 = W // 2
                out_real = pyfftw.interfaces.numpy_fft.ifft2(
                    xfft * filterfft).real
                # print("out_real: ", out_real.astype(int))
                # sum_out += out_real[H2:H2 + H, W2:W2 + W]
                sum_out += out_real[:out_H, :out_W]
            # crop the output to the expected shape
            out[nn, ff] = sum_out + b[ff]
    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = (x, w, b, conv_param)
    return out, cache


def conv_forward_fft(x, w, b, conv_param):
    """
    The implementation of convolution via the frequency domain (fft).

    The input consists of N data points, each with C channels, height H and
    width W. We convolve each input with F different filters, where each filter
    spans all C channels and has height HH and width HH.

    :param x: Input data of shape (N, C, H, W)
    :param w: Filter weights of shape (F, C, HH, WW)
    :param b: Biases, of shape (F,) - we have as many bias terms as the number of filters
    :param conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.
    :return: a tuple of:
    - out: Output data, of shape (N, F, H', W') where H' and W' are given by
      H' = 1 + (H + 2 * pad - HH) / stride
      W' = 1 + (W + 2 * pad - WW) / stride
    - cache: (x, w, b, conv_param)
    """
    # Grab conv parameters
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')
    if stride != 1:
        raise Exception(
            "Convolution via fft is only possible with stride = 1, while given stride=" + str(
                stride))

    N, C, H, W = x.shape
    F, C, HH, WW = w.shape

    # Calculate the output spatial dimensions.
    out_H, out_W = get_conv_shape((H, W), (HH, WW), conv_param)

    # Zero pad our tensor along the spatial dimensions.
    padded_x = (
        np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)), mode='constant'))

    # Initialise the output.
    # out = np.zeros([N, F, out_H, out_W])
    out = np.zeros([N, F, out_H, out_W])

    fftpadded_x = np.pad(padded_x, ((0, 0), (0, 0), (0, H - 1), (0, W - 1)),
                         mode='constant')
    _, _, Hpad, Wpad = fftpadded_x.shape
    fftpadded_filter = np.pad(w,
                              ((0, 0), (0, 0), (0, Hpad - HH), (0, Wpad - WW)),
                              mode='constant')

    # Hpow2, Wpow2 = find_next_power2(Hpad), find_next_power2(Wpad)
    Hpow2, Wpow2 = Hpad, Wpad

    # Naive convolution loop.
    for nn in range(N):  # For each image in the input batch.
        for ff in range(F):  # For each filter in w
            sum_out = np.zeros([out_H, out_W])
            for cc in range(C):
                xfft = np.fft.fft2(fftpadded_x[nn, cc], (Hpow2, Wpow2))
                # print("xfft: ", xfft)
                # xfft = xfft[:xfft.shape[0] // 2, :xfft.shape[1] // 2]
                # print("xfft shape: ", xfft.shape)
                filterfft = np.fft.fft2(fftpadded_filter[ff, cc], xfft.shape)
                # filterfft = filterfft[:filterfft.shape[0] // 2, :filterfft.shape[1] // 2]
                # print("filterfft: ", filterfft)
                filterfft = np.conjugate(filterfft)
                # out[nn, ff] += np.abs(np.fft.ifft2(xfft * filterfft, (out_H, out_W)))
                # H2 = H // 2
                # W2 = W // 2
                out_real = np.fft.ifft2(xfft * filterfft).real
                # print("out_real: ", out_real.astype(int))
                # sum_out += out_real[H2:H2 + H, W2:W2 + W]
                sum_out += out_real[:out_H, :out_W]
            # crop the output to the expected shape
            out[nn, ff] = sum_out + b[ff]
    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = (x, w, b, conv_param)
    return out, cache


def conv_forward_naive(x, w, b, conv_param):
    """
    A naive implementation of the forward pass for a convolutional layer.

    The input consists of N data points, each with C channels, height H and
    width W. We convolve each input with F different filters, where each filter
    spans all C channels and has height HH and width HH.

    Input:
    - x: Input data of shape (N, C, H, W)
    - w: Filter weights of shape (F, C, HH, WW)
    - b: Biases, of shape (F,)
    - conv_param: A dictionary with the following keys:
      - 'stride': The number of pixels between adjacent receptive fields in the
        horizontal and vertical directions.
      - 'pad': The number of pixels that will be used to zero-pad the input.

    Returns a tuple of:
    - out: Output data, of shape (N, F, H', W') where H' and W' are given by
      H' = 1 + (H + 2 * pad - HH) / stride
      W' = 1 + (W + 2 * pad - WW) / stride
    - cache: (x, w, b, conv_param)
    """

    # Grab conv parameters
    pad = conv_param.get('pad')
    stride = conv_param.get('stride')

    N, C, H, W = x.shape
    F, C, HH, WW = w.shape

    # Zero pad our tensor along the spatial dimensions.
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)), 'constant'))

    # Calculate the output spatial dimensions.
    out_H, out_W = get_conv_shape((H, W), (HH, WW), conv_param)

    # Initialize the output.
    out = np.zeros([N, F, out_H, out_W])

    # Naive convolution loop.
    for nn in range(N):  # For each image in the input batch.
        for ff in range(F):  # For each filter in w
            for jj in range(0, out_H):  # For each output pixel height
                for ii in range(0, out_W):  # For each output pixel width
                    # multiplying tensors
                    out[nn, ff, jj, ii] = \
                        np.sum(
                            w[ff, ...] * padded_x[nn, :,
                                         jj * stride:jj * stride + HH,
                                         ii * stride:ii * stride + WW]) + \
                        b[ff]
                    # we have a single bias per filter
                    # at the end - sum all the values in the obtained tensor

    cache = (x, w, b, conv_param)
    return out, cache


def conv_backward_naive(dout, cache):
    """
    A naive implementation of the backward pass for a convolutional layer.

    Inputs:
    - dout: Upstream derivatives.
    - cache: A tuple of (x, w, b, conv_param) as in conv_forward_naive

    Returns a tuple of:
    - dx: Gradient with respect to x
    - dw: Gradient with respect to w
    - db: Gradient with respect to b
    """
    dx, dw, db = None, None, None

    # Grab conv parameters and pad x if needed.
    x, w, b, conv_param = cache
    stride = conv_param.get('stride')
    pad = conv_param.get('pad')
    padded_x = (np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)), 'constant'))

    N, C, H, W = x.shape
    F, C, HH, WW = w.shape
    N, F, H_out, W_out = dout.shape

    # Initialise gradient output tensors.
    dx_temp = np.zeros_like(padded_x)
    dw = np.zeros_like(w)
    db = np.zeros_like(b)

    # Calculate dB.
    # Just like in the affine layer we sum up all the incoming gradients for
    # each filters bias.
    for ff in range(F):
        db[ff] += np.sum(dout[:, ff, :, :])

    # Calculate dw.
    # By chain rule dw is dout*x
    for nn in range(N):
        for ff in range(F):
            for jj in range(H_out):
                for ii in range(W_out):
                    dw[ff, ...] += dout[nn, ff, jj, ii] * padded_x[nn, :,
                                                          jj * stride:jj * stride + HH,
                                                          ii * stride: ii * stride + WW]

    # Calculate dx.
    # By chain rule dx is dout*w. We need to make dx same shape as padded x for the gradient calculation.
    for nn in range(N):
        for ff in range(F):
            for jj in range(H_out):
                for ii in range(W_out):
                    dx_temp[nn, :, jj * stride:jj * stride + HH,
                    ii * stride:ii * stride + WW] += dout[nn, ff, jj, ii] * \
                                                     w[ff, ...]

    # Remove the padding from dx so it matches the shape of x.
    dx = dx_temp[:, :, pad:H + pad, pad:W + pad]

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    return dx, dw, db


def get_out_pool_shape(x_shape, pool_param):
    """
    Get the shape of the output of the max pool.

    :param x: the input to the max pool
    :param pool_param: the params of the max pool
    :return: the output shape of the max pool
    """
    # Grab the pooling parameters.
    pool_height = pool_param.get('pool_height')
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    H, W = x_shape

    # Calculate output spatial dimensions.
    out_H = np.int(((H - pool_height) / stride) + 1)
    out_W = np.int(((W - pool_width) / stride) + 1)

    return out_H, out_W


def fft_pool_forward(x, pool_param):
    """
    An fft-based implementation of the forward pass for the spectral pooling layer.

    Inputs:
    - x: Input data, of shape (N, C, H, W)
    - pool_param: dictionary with the following keys:
      - 'pool_height': The height of each pooling region
      - 'pool_width': The width of each pooling region
      - 'stride': The distance between adjacent pooling regions

    Returns a tuple of:
    - out: Output data
    - cache: (x, pool_param)
    """
    pool_height = pool_param.get('pool_height')
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    N, C, H, W = x.shape
    out_H, out_W = get_out_pool_shape((H, W), pool_param)
    # Initialise output.
    out = np.zeros([N, C, out_H, out_W])

    # Naive maxpool for loop.
    for n in range(N):  # For each image.
        for c in range(C):  # For each channel

            for h in range(out_H):  # For each output row.
                for w in range(out_W):  # For each output col.
                    out[n, c, h, w] = np.max(
                        x[n, c, h * stride:h * stride + pool_height,
                        w * stride:w * stride + pool_width])

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = (x, pool_param)
    return out, cache


def max_pool_forward_naive(x, pool_param):
    """
    A naive implementation of the forward pass for a max pooling layer.

    Inputs:
    - x: Input data, of shape (N, C, H, W)
    - pool_param: dictionary with the following keys:
      - 'pool_height': The height of each pooling region
      - 'pool_width': The width of each pooling region
      - 'stride': The distance between adjacent pooling regions

    Returns a tuple of:
    - out: Output data
    - cache: (x, pool_param)
    """
    out = None
    ###########################################################################
    # TODO: Implement the max pooling forward pass                            #
    ###########################################################################
    # Grab the pooling parameters.
    pool_height = pool_param.get('pool_height')
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    N, C, H, W = x.shape
    out_H, out_W = get_out_pool_shape((H, W), pool_param)
    # Initialise output.
    out = np.zeros([N, C, out_H, out_W])

    # Naive maxpool for loop.
    for n in range(N):  # For each image.
        for c in range(C):  # For each channel
            for h in range(out_H):  # For each output row.
                for w in range(out_W):  # For each output col.
                    out[n, c, h, w] = np.max(
                        x[n, c, h * stride:h * stride + pool_height,
                        w * stride:w * stride + pool_width])

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    cache = (x, pool_param)
    return out, cache


def max_pool_backward_naive(dout, cache):
    """
    A naive implementation of the backward pass for a max pooling layer.

    Inputs:
    - dout: Upstream derivatives
    - cache: A tuple of (x, pool_param) as in the forward pass.

    Returns:
    - dx: Gradient with respect to x
    """
    dx = None
    ###########################################################################
    # TODO: Implement the max pooling backward pass                           #
    ###########################################################################

    # Grab the pooling parameters.
    x, pool_param = cache
    pool_height = pool_param.get('pool_height')
    pool_width = pool_param.get('pool_width')
    stride = pool_param.get('stride')

    N, C, H, W = x.shape
    _, _, dout_H, dout_W = dout.shape

    # Initialise dx to be of the same shape as maxpool input x.
    dx = np.zeros_like(x)

    for n in range(N):
        for c in range(C):
            for h in range(dout_H):
                for w in range(dout_W):
                    current_matrix = x[n, c,
                                     h * stride: h * stride + pool_height,
                                     w * stride: w * stride + pool_width]
                    current_max = np.max(current_matrix)
                    for (i, j) in [(i, j) for i in range(pool_height) for j in
                                   range(pool_width)]:
                        if current_matrix[i, j] == current_max:
                            dx[n, c, h * stride + i, w * stride + j] += dout[
                                n, c, h, w]

    # # Naive loop to backprop dout through maxpool layer.
    # for n in range(N):  # For each image.
    #     for c in range(C):  # For each channel
    #         for j in range(dout_H):  # For each row of dout.
    #             for i in range(dout_W):  # For each col of dout.
    #                 # Using argmax get the linear index of the max of each patch.
    #                 max_index = np.argmax(
    #                     x[n, c, j * stride:j * stride + pool_height, i * stride:i * stride + pool_width])
    #                 # Using unravel_index convert this linear index to matrix coordinate.
    #                 max_coord = np.unravel_index(max_index, [pool_height, pool_width])
    #                 # Only backprop the dout to the max location.
    #                 dx[n, c, j * stride:j * stride + pool_height, i * stride:i * stride + pool_width][max_coord] = dout[
    #                     n, c, j, i]

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################
    return dx


def spatial_batchnorm_forward(x, gamma, beta, bn_param):
    """
    Computes the forward pass for spatial batch normalization.

    Inputs:
    - x: Input data of shape (N, C, H, W)
    - gamma: Scale parameter, of shape (C,)
    - beta: Shift parameter, of shape (C,)
    - bn_param: Dictionary with the following keys:
      - mode: 'train' or 'test'; required
      - eps: Constant for numeric stability
      - momentum: Constant for running mean / variance. momentum=0 means that
        oldConvNetFFT1D information is discarded completely at every time step, while
        momentum=1 means that new information is never incorporated. The
        default of momentum=0.9 should work well in most situations.
      - running_mean: Array of shape (D,) giving running mean of features
      - running_var Array of shape (D,) giving running variance of features

    Returns a tuple of:
    - out: Output data, of shape (N, C, H, W)
    - cache: Values needed for the backward pass
    """
    out, cache = None, None

    ###########################################################################
    # TODO: Implement the forward pass for spatial batch normalization.       #
    #                                                                         #
    # HINT: You can implement spatial batch normalization using the vanilla   #
    # version of batch normalization defined above. Your implementation should#
    # be very short; ours is less than five lines.                            #
    ###########################################################################

    # We transpose to get channels as last dim and then reshape to size (-1, C) so we can use normal batchnorm.
    x_t = x.transpose((0, 2, 3, 1))
    x_flat = x_t.reshape(-1, x.shape[1])

    out, cache = batchnorm_forward(x_flat, gamma, beta, bn_param)

    # Reshape our results back to our desired shape.
    out_reshaped = out.reshape(*x_t.shape)
    out = out_reshaped.transpose((0, 3, 1, 2))

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################

    return out, cache


def spatial_batchnorm_backward(dout, cache):
    """
    Computes the backward pass for spatial batch normalization.

    Inputs:
    - dout: Upstream derivatives, of shape (N, C, H, W)
    - cache: Values from the forward pass

    Returns a tuple of:
    - dx: Gradient with respect to inputs, of shape (N, C, H, W)
    - dgamma: Gradient with respect to scale parameter, of shape (C,)
    - dbeta: Gradient with respect to shift parameter, of shape (C,)
    """
    dx, dgamma, dbeta = None, None, None

    ###########################################################################
    # TODO: Implement the backward pass for spatial batch normalization.      #
    #                                                                         #
    # HINT: You can implement spatial batch normalization using the vanilla   #
    # version of batch normalization defined above. Your implementation should#
    # be very short; ours is less than five lines.                            #
    ###########################################################################

    # We transpose to get channels as last dim and then reshape to size (-1, C) so we can use normal batchnorm.
    dout_t = dout.transpose((0, 2, 3, 1))
    dout_flat = dout_t.reshape(-1, dout.shape[1])

    dx, dgamma, dbeta = batchnorm_backward(dout_flat, cache)

    # We need to reshape dx back to our desired shape.
    dx_reshaped = dx.reshape(*dout_t.shape)
    dx = dx_reshaped.transpose((0, 3, 1, 2))

    ###########################################################################
    #                             END OF YOUR CODE                            #
    ###########################################################################

    return dx, dgamma, dbeta


def svm_loss(x, y):
    """
    Computes the loss and gradient using for multiclass SVM classification.

    Inputs:
    - x: Input data, of shape (N, C) where x[i, j] is the score for the jth
      class for the ith input.
    - h: Vector of labels, of shape (N,) where h[i] is the label for x[i] and
      0 <= h[i] < C

    Returns a tuple of:
    - loss: Scalar giving the loss
    - dx: Gradient of the loss with respect to x
    """
    N = x.shape[0]
    correct_class_scores = x[np.arange(N), y]
    margins = np.maximum(0, x - correct_class_scores[:, np.newaxis] + 1.0)
    margins[np.arange(N), y] = 0
    loss = np.sum(margins) / N
    num_pos = np.sum(margins > 0, axis=1)
    dx = np.zeros_like(x)
    dx[margins > 0] = 1
    dx[np.arange(N), y] -= num_pos
    dx /= N
    return loss, dx


def softmax_loss(x, y):
    """
    Computes the loss and gradient for softmax classification.

    Inputs:
    - x: Input data, of shape (N, C) where x[i, j] is the score for the jth
      class for the ith input.
    - h: Vector of labels, of shape (N,) where h[i] is the label for x[i] and
      0 <= h[i] < C

    Returns a tuple of:
    - loss: Scalar giving the loss
    - dx: Gradient of the loss with respect to x
    """
    shifted_logits = x - np.max(x, axis=1, keepdims=True)
    Z = np.sum(np.exp(shifted_logits), axis=1, keepdims=True)
    log_probs = shifted_logits - np.log(Z)
    probs = np.exp(log_probs)
    N = x.shape[0]
    loss = -np.sum(log_probs[np.arange(N), y]) / N
    dx = probs.copy()
    dx[np.arange(N), y] -= 1
    dx /= N
    return loss, dx


if __name__ == "__main__":
    import sys
    import doctest

    sys.exit(doctest.testmod()[0])
