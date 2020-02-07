"""
Custom FFT based convolution that:
1) computes forward and backward manually (this is the main part);
2) manually computes the forward pass and relies on the autograd (a tape-based
automatic differentiation library that supports all differentiable Tensor
operations in PyTorch) for automatic differentiation for the backward pass.
"""
import logging
import sys
import math
import numpy as np
import torch
import time
from torch import tensor
from torch.nn import Module
from torch.nn.functional import pad as torch_pad
from torch.nn.parameter import Parameter
from torch.nn import init

from cnns.nnlib.pytorch_layers.pytorch_utils import correlate_fft_signals2D
from cnns.nnlib.pytorch_layers.pytorch_utils import from_tensor
from cnns.nnlib.pytorch_layers.pytorch_utils import get_pair
from cnns.nnlib.pytorch_layers.pytorch_utils import preserve_energy2D_symmetry
from cnns.nnlib.pytorch_layers.pytorch_utils import pytorch_conjugate
from cnns.nnlib.pytorch_layers.pytorch_utils import complex_mul
from cnns.nnlib.pytorch_layers.pytorch_utils import complex_mul2
from cnns.nnlib.pytorch_layers.pytorch_utils import complex_mul3
from cnns.nnlib.pytorch_layers.pytorch_utils import complex_mul4
from cnns.nnlib.pytorch_layers.pytorch_utils import complex_mul5
from cnns.nnlib.pytorch_layers.pytorch_utils import to_tensor
from cnns.nnlib.pytorch_layers.pytorch_utils import cuda_mem_show
from cnns.nnlib.pytorch_layers.pytorch_utils import compress_2D_index_forward
from cnns.nnlib.pytorch_layers.pytorch_utils import compress_2D_index_back
from cnns.nnlib.pytorch_layers.pytorch_utils import zero_out_min
from cnns.nnlib.pytorch_layers.pytorch_utils import get_spectrum
from cnns.nnlib.pytorch_layers.pytorch_utils import get_elem_size
from cnns.nnlib.pytorch_layers.pytorch_utils import get_tensors_elem_size
from cnns.nnlib.pytorch_layers.pytorch_utils import get_step_estimate
from cnns.nnlib.pytorch_layers.pytorch_utils import restore_size_2D
from cnns.nnlib.utils.general_utils import CompressType, next_power2
from cnns.nnlib.utils.general_utils import ConvExecType
from cnns.nnlib.utils.general_utils import StrideType
from cnns.nnlib.utils.arguments import Arguments
from cnns.nnlib.utils.general_utils import additional_log_file

MAX_BLOCK_THREADS = 1024

if torch.cuda.is_available() and sys.platform != 'win32':
    # from complex_mul_cpp import complex_mul as complex_mul_cpp
    # from complex_mul_cuda import complex_mul as complex_mul_cuda
    # from complex_mul_cuda import complex_mul_stride as complex_mul_stride_cuda
    from complex_mul_cuda import \
        complex_mul_stride_no_permute as complex_mul_stride_no_permute_cuda
    from complex_mul_cuda import \
        complex_mul_shared_log as complex_mul_shared_log_cuda
    from complex_mul_cuda import \
        complex_mul_deep as complex_mul_deep_cuda

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
consoleLog = logging.StreamHandler()
logger.addHandler(consoleLog)

current_file_name = __file__.split("/")[-1].split(".")[0]

# forward pass
global_preserve_energy_time = 0.0
global_correlation_time = 0.0
global_fft_time = 0.0
global_irfft_time = 0.0
global_complex_time = 0.0
global_permute_time = 0.0
global_complex_dxfft = 0.0
global_pad_time = 0.0
global_counter = 0
global_conjugate_time = 0.0
global_restore_time = 0.0
global_init_time = 0.0

# backward pass
global_init_time_back = 0.0
global_irfft_time_back = 0.0
global_correlation_time_back_filter = 0.0
global_correlation_time_back_input = 0.0
global_pad_grad = 0.0
global_fft_grad = 0.0
global_correlate_input_grad = 0.0
global_correlate_filter_grad = 0.0
global_conjugate_filter = 0.0
global_restore_input = 0.0
global_irfft_input = 0.0
global_restore_filter = 0.0
global_irfft_filter = 0.0

# global_threshold = 10000
global_threshold = 5321


def fast_multiply(xfft, yfft):
    """
    Fast complex multiplication (3 real multiplications instead of 4) using
    torch.matmul (SGEMM).

    :param xfft: input with dims: (H, W, N, C, I)
    :param yfft: input with dims: (H, W, C, F, I
    :return: outfft: output with dims: (N, F, H, W, I)
    """
    x_re = xfft[..., 0]
    x_im = xfft[..., 1]
    y_re = yfft[..., 0]
    y_im = yfft[..., 1]

    # Change to matrix multiply.
    # UaVc = x_re * (y_re + y_im)
    # out_re = UaVc - (x_re + x_im) * y_im
    # out_im = (x_im - x_re) * y_re + UaVc
    UaVc = torch.matmul(x_re, (y_re + y_im))
    out_re = UaVc - torch.matmul((x_re + x_im), y_im)
    out_im = torch.matmul((x_im - x_re), y_re) + UaVc
    outfft = torch.cat((out_re.unsqueeze(-1),
                        out_im.unsqueeze(-1)),
                       dim=-1)
    return outfft


class Conv2dfftFunction(torch.autograd.Function):
    """
    Implement the 2D convolution via FFT with compression in the spectral domain
    of the input map (activation) and the filter.
    """
    signal_ndim = 2

    @staticmethod
    def forward(ctx, input, filter, bias=None, padding=(0, 0), stride=(1, 1),
                args=Arguments(), out_size=None, is_manual=tensor([0]),
                conv_index=None):
        """
        Compute the forward pass for the 2D convolution.

        :param ctx: context to save intermediate results, in other words,
        a context object that can be used to stash information for backward
        computation.
        :param input: the input map (activation) to the convolution (e.g. an
        image).
        :param filter: the filter (a.k.a. kernel of the convolution).
        :param bias: the bias term for each filter.
        :param padding: how much to pad each end of the height and width of the
        input map, implicit applies zero padding on both sides of the input. It
        can be a single number or a tuple (padH, padW).
        Default: None (no padding).
        :param stride: what is the stride for the height and width dimensions
        when convolving the input map with the filter, implicitly we do not
        apply the stride (move one pixel at a time).
        Default: None (no padding).
        :param compress_rate: how many of the last height and width elements in the
        fft-ed map to discard. It Can be a single number or a tuple
        (compress_rate_H, compress_rate_W). Default: None (no compression).
        :param preserve_energy: how much energy of the input images should be
        preserved.
        :param out_size: what is the expected output size - one can discard
        the elements in the frequency domain and do the spectral pooling within
        the convolution. It can be a single number or a tuple (outH, outW). It
        is more flexible than the pooling or striding.
        Default: None (the standard size, e.g., outW = W - WW + 1).
        :param use_next_power2: should we extend the size of the input for the
        FFT convolution to the next power of 2.
        :param is_manual: to check if the backward computation of convolution
        was computed manually.
        :param conv_index: the index of the convolution.
        :param is_debug: is the debug mode of execution.
        :param compress_type: NO_FILTER - should the filter be compressed or
        only the input signal? BIG_COEF: should we keep only the largest
        coefficients or delete the coefficients from the end of the signal
        representation in the frequency domain? STANDARD: cut off the same
        number of coefficients for each signal and filter in the batch based on
        the whole energy of the signals in the batch.

        :return: the result of convolution.
        """
        # print("input size: ", input.size(), ", filter size:", filter.size())

        Conv2dfftFunction.mark_dirty(input)

        if args.mem_test:
            torch.cuda.empty_cache()

        compress_rate = args.compress_rate
        if conv_index is not None and args.layers_compress_rates is not None:
            if len(args.layers_compress_rates) < conv_index:
                raise Exception("Not enough compress rates provided for "
                                "the fft based convolution.")
            compress_rate = args.layers_compress_rates[conv_index]
        preserve_energy = args.preserve_energy
        use_next_power2 = args.next_power2
        is_debug = args.is_debug
        stride_type = args.stride_type

        dtype = input.dtype
        device = input.device

        if is_debug:
            # print("debug enabled")
            global global_counter
            global global_threshold
            global_counter += 1
            print("global_counter: ", global_counter)

        if is_debug:
            global global_init_time
            start_init_time = time.time()

        INPUT_ERROR = "Specify only one of: compress_rate, out_size, or " \
                      "preserve_energy"
        if (compress_rate is not None and compress_rate > 0) and (
                out_size is not None):
            raise TypeError(INPUT_ERROR)
        if (compress_rate is not None and compress_rate > 0) and (
                preserve_energy is not None and preserve_energy < 100):
            raise TypeError(INPUT_ERROR)
        if out_size is not None and (
                preserve_energy is not None and preserve_energy < 100):
            raise TypeError(INPUT_ERROR)

        # N - number of input maps (or images in the batch).
        # C - number of input channels.
        # H - height of the input map (e.g., height of an image).
        # W - width of the input map (e.g. width of an image).
        N, C, H, W = input.size()

        # F - number of filters.
        # C - number of channels in each filter.
        # HH - the height of the filter.
        # WW - the width of the filter (its length).
        F, C, HH, WW = filter.size()

        compress_rate_H, compress_rate_W = get_pair(value=compress_rate,
                                                    val_1_default=None,
                                                    val2_default=None)
        if compress_rate_H != compress_rate_W:
            raise Exception(
                "We only support a symmetric compression in the frequency domain.")

        pad_H, pad_W = get_pair(value=padding, val_1_default=0, val2_default=0,
                                name="padding")

        if pad_H != pad_W:
            raise Exception(
                "We only support a symmetric padding in the frequency domain.")

        out_size_H, out_size_W = get_pair(value=out_size, val_1_default=None,
                                          val2_default=None, name="out_size")

        if out_size_H != out_size_W:
            raise Exception(
                "We only support a symmetric outputs in the frequency domain.")

        stride_H, stride_W = get_pair(value=stride, val_1_default=None,
                                      val2_default=None, name="stride")

        if stride_H != stride_W:
            raise Exception(
                "We only support a symmetric striding in the frequency domain.")

        if out_size_H:
            out_H = out_size_H
        elif out_size or stride_type is StrideType.SPECTRAL:
            out_H = (H - HH + 2 * pad_H) // stride_H + 1
        else:
            out_H = H - HH + 1 + 2 * pad_H

        if out_size_W:
            out_W = out_size_W
        elif out_size or stride_type is StrideType.SPECTRAL:
            out_W = (W - WW + 2 * pad_W) // stride_W + 1
        else:
            out_W = W - WW + 1 + 2 * pad_W

        if out_H != out_W:
            raise Exception(
                "We only support a symmetric compression in the frequency domain.")

        # We have to pad input with (WW - 1) to execute fft correctly (no
        # overlapping signals) and optimize it by extending the signal to the
        # next power of 2. We want to reuse the fft-ed input x, so we use the
        # larger size chosen from: the filter width WW or output width out_W.
        # Larger padding does not hurt correctness of fft but makes it slightly
        # slower, in terms of the computation time.

        HHH = max(out_H, HH)
        init_H_fft = H + 2 * pad_H + HHH - 1

        WWW = max(out_W, WW)
        init_W_fft = W + 2 * pad_W + WWW - 1

        if use_next_power2 is True:
            init_H_fft = next_power2(init_H_fft)
            init_W_fft = next_power2(init_W_fft)

        if is_debug:
            global_init_time += time.time() - start_init_time
            if global_counter % global_threshold == 0:
                print("global init time: ", global_init_time)

        if is_debug:
            start_pad_time = time.time()

        # How many padded (zero) values there are because of going to the next
        # power of 2?
        fft_padding_input_H = init_H_fft - 2 * pad_H - H
        fft_padding_input_W = init_W_fft - 2 * pad_W - W

        # Pad only the dimensions for the height and width and neither the data
        # points (the batch dimension) nor the channels.
        input = torch_pad(
            input, (pad_W, pad_W + fft_padding_input_W, pad_H,
                    pad_H + fft_padding_input_H), 'constant', 0)

        fft_padding_filter_H = init_H_fft - HH
        fft_padding_filter_W = init_W_fft - WW

        filter = torch_pad(
            filter, (0, fft_padding_filter_W, 0, fft_padding_filter_H),
            'constant', 0)

        if is_debug:
            global global_pad_time
            global_pad_time += time.time() - start_pad_time
            if global_counter % global_threshold == 0:
                print("global pad time: ", global_pad_time)

        if args.mem_test:
            torch.cuda.empty_cache()

        if is_debug:
            global global_fft_time
            start_fft_time = time.time()

        if args.fft_type == "real_fft":
            # This is the main fft (real) type. However, PyTorch might run this
            # slower than the fft complex type.
            # fft of the input and filters
            xfft = torch.rfft(input, signal_ndim=Conv2dfftFunction.signal_ndim,
                              onesided=True)
            del input

            yfft = torch.rfft(filter,
                              signal_ndim=Conv2dfftFunction.signal_ndim,
                              onesided=True)
            del filter
        else:
            # build complex tensors with 0 in the imaginary part
            n, c, h, w = input.size()
            zeros = torch.zeros(n, c, h, w, 1, dtype=input.dtype,
                                device=input.device)
            input.unsqueeze_(-1)
            filter.unsqueeze(-1)
            input = torch.cat((input, zeros), dim=-1)
            filter = torch.cat((filter, zeros), dim=-1)
            xfft = torch.fft(input, signal_ndim=Conv2dfftFunction.signal_ndim)
            yfft = torch.fft(filter, signal_ndim=Conv2dfftFunction.signal_ndim)

            del input
            del filter

        if is_debug:
            global_fft_time += time.time() - start_fft_time
            if global_counter % global_threshold == 0:
                print("(r)fft time: ", global_fft_time)

        if args.mem_test:
            torch.cuda.empty_cache()

        # The last dimension (-1) has size 2 as it represents the complex
        # numbers with real and imaginary parts. The last but one dimension (-2)
        # represents the length of the signal in the frequency domain.
        init_half_W_fft = xfft.shape[-2]
        init_H_fft = xfft.shape[-3]

        # Pooling either via stride or explicitly via out_size_W.
        if out_size or stride_type is StrideType.SPECTRAL:
            # We take one-sided fft so the output after the inverse fft should
            # be out size, thus the representation in the spectral domain is
            # twice smaller than the one in the spatial domain.
            half_fft_W = out_W // 2 + 1
            xfft = compress_2D_index_forward(xfft, half_fft_W)
            yfft = compress_2D_index_forward(yfft, half_fft_W)

        # Compression.
        if preserve_energy is not None and preserve_energy < 100.0:
            if is_debug:
                start_energy = time.time()

            xfft, yfft = preserve_energy2D_symmetry(
                xfft, yfft, preserve_energy_rate=preserve_energy,
                is_debug=is_debug)

            if is_debug:
                global global_preserve_energy_time
                global_preserve_energy_time += time.time() - start_energy
                if global_counter % global_threshold == 0:
                    print("preserve energy time: ", global_preserve_energy_time)

        elif compress_rate_W is not None and compress_rate_W > 0:
            is_fine_grained_sparsification = False  # this is for tests
            if is_fine_grained_sparsification:
                xfft_spectrum = get_spectrum(xfft)
                yfft_spectrum = get_spectrum(yfft)
                for _ in range(compress_rate_W):
                    xfft, xfft_spectrum = zero_out_min(xfft, xfft_spectrum)
                    yfft, yfft_spectrum = zero_out_min(yfft, yfft_spectrum)
            else:
                retain_rate_W = 100 - compress_rate_W
                retain_ratio = math.sqrt(retain_rate_W / 100)
                index_forward_W_fft = int(init_half_W_fft * retain_ratio)
                # # At least one coefficient is removed.
                # index_forward_W_fft = min(index_forward_W_fft,
                #                           init_half_W_fft - 1)
                xfft = compress_2D_index_forward(xfft, index_forward_W_fft)
                yfft = compress_2D_index_forward(yfft, index_forward_W_fft)

        _, _, half_fft_compressed_H, half_fft_compressed_W, _ = xfft.size()

        if args.mem_test:
            torch.cuda.empty_cache()

        if args.log_conv_size is True:
            # if True:
            with open(additional_log_file, "a") as file:
                # file.write(str(half_fft_compressed_H) + "," + str(
                #     half_fft_compressed_W) + ",")
                # file.write(str(conv_index) + "," + str(
                #     half_fft_compressed_H * half_fft_compressed_W * C) + ",")
                file.write(
                    str(
                        half_fft_compressed_H * half_fft_compressed_W * C) + ",")
                # file.write("C:" + str(C) + "," + "H:" + str(
                #     half_fft_compressed_H) + "," + "W:" + str(
                #     half_fft_compressed_W) + ",")
        cuda_block_threads = min(MAX_BLOCK_THREADS,
                                 half_fft_compressed_H * half_fft_compressed_W)

        if bias is not None:
            unsqueezed_bias = bias.unsqueeze(-1).unsqueeze(-1)

        # C, H, W = xfft.size(1), xfft.size(2), xfft.size(3)
        # print(f"C,{C},H,{H},W,{W},C*H*W,{C*H*W}")

        if is_debug:
            global global_conjugate_time
            start_conjugate = time.time()

        yfft = pytorch_conjugate(yfft)

        if is_debug:
            global_conjugate_time += time.time() - start_conjugate
            if global_counter % global_threshold == 0:
                print("conjugate time: ", global_conjugate_time)

        if is_debug:
            start_correlation = time.time()

        if args.conv_exec_type is ConvExecType.SERIAL:
            # Serially convolve each input map with all filters.
            out = torch.empty([N, F, out_H, out_W], dtype=dtype, device=device)
            for nn in range(N):  # For each time-series in the batch.
                # Take one time series and unsqueeze it for broadcasting with
                # many filters.
                xfft_nn = xfft[nn].unsqueeze(0)
                out[nn] = correlate_fft_signals2D(
                    xfft=xfft_nn, yfft=yfft,
                    input_height=init_H_fft, input_width=init_W_fft,
                    init_fft_height=init_H_fft,
                    init_half_fft_width=init_half_W_fft,
                    out_height=out_H, out_width=out_W, is_forward=True)
                if bias is not None:
                    # Add the bias term for each filter (it has to be unsqueezed to
                    # the dimension of the out to properly sum up the values).
                    out[nn] += unsqueezed_bias
        else:
            if args.conv_exec_type is ConvExecType.SGEMM:
                # We want for xfft: H, W, C, N, I
                xfft = xfft.permute(2, 3, 1, 0, 4).contiguous()
                # We want for yfft: H, W, F, C, I
                yfft = yfft.permute(2, 3, 0, 1, 4).contiguous()

                # result: H, W, F, N, I
                outfft = fast_multiply(yfft, xfft)

                # From H, W, F, N, I to N, F, H, W, I
                outfft = outfft.permute(3, 2, 0, 1, 4)

            elif args.conv_exec_type is ConvExecType.CUDA_SHARED_LOG:
                if torch.cuda.is_available():
                    # print("complex cuda multiplication")
                    outfft = torch.zeros([N, F, half_fft_compressed_H,
                                          half_fft_compressed_W, 2],
                                         dtype=dtype, device=device)
                    # Move the channels to the last but one dimension.
                    # We want for xfft: N, H, W, C, I.
                    xfft = xfft.permute(0, 2, 3, 1, 4).contiguous()
                    # We want for yfft: F, H, W, C, I.
                    yfft = yfft.permute(0, 2, 3, 1, 4).contiguous()
                    # start_complex_time = time.time()
                    complex_mul_shared_log_cuda(xfft, yfft, outfft)
                    torch.cuda.synchronize()
                    # global global_complex_time
                    # global_complex_time += time.time() - start_complex_time
                    # print("complex multiply time: ", global_complex_time)
                else:
                    raise Exception("Selected CUDA conv execution but no cuda "
                                    "device is available.")
            elif args.conv_exec_type is ConvExecType.CUDA_DEEP:
                if torch.cuda.is_available():
                    # print("complex cuda multiplication")
                    outfft = torch.empty([N, F, half_fft_compressed_H,
                                          half_fft_compressed_W, 2],
                                         dtype=dtype, device=device)
                    # Move the channels to the last but one dimension.
                    # We want for xfft: N, H, W, C, I.
                    xfft = xfft.permute(0, 2, 3, 1, 4).contiguous()
                    # We want for yfft: F, H, W, C, I.
                    yfft = yfft.permute(0, 2, 3, 1, 4).contiguous()
                    # start_complex_time = time.time()
                    complex_mul_deep_cuda(xfft, yfft, outfft)
                    torch.cuda.synchronize()
                    # global global_complex_time
                    # global_complex_time += time.time() - start_complex_time
                    # print("complex multiply time: ", global_complex_time)
                else:
                    raise Exception("Selected CUDA conv execution but no cuda "
                                    "device is available.")
            elif args.conv_exec_type is ConvExecType.CUDA:
                if torch.cuda.is_available():
                    # print("complex cuda multiplication")
                    # print("xfft size: ", xfft.size())
                    # start_complex_time = time.time()
                    outfft = torch.zeros([N, F, half_fft_compressed_H,
                                          half_fft_compressed_W, 2],
                                         dtype=dtype, device=device)
                    # complex_mul_cuda(xfft, yfft, outfft)
                    xfft = xfft.contiguous()
                    yfft = yfft.contiguous()

                    complex_mul_stride_no_permute_cuda(xfft, yfft, outfft,
                                                       cuda_block_threads)
                    torch.cuda.synchronize()
                    # global global_complex_time
                    # global_complex_time += time.time() - start_complex_time
                    # print("complex multiply time: ", global_complex_time)
                else:
                    raise Exception("Selected CUDA conv execution but no cuda "
                                    "device is available.")

            # Convolve some part of the input batch with all filters.
            # 2 is for complex numbers
            # start = 0
            # step = get_step_estimate(xfft, yfft, args.memory_size, scale=1)
            # step = max(args.min_batch_size // 4, 1)
            # step = args.min_batch_size
            # For each slice of batch.

            # for start in range(start, N, step):
            #     stop = min(start + step, N)
            #     # Take one time series and unsqueeze it for broadcasting with
            #     # many filters.
            #     xfft_nn = xfft[start:stop]
            #     outfft[start:stop] = complex_mul_cpp(xfft_nn, yfft).sum(dim=2)
            elif args.conv_exec_type is ConvExecType.BATCH:
                xfft = xfft.unsqueeze(dim=1)
                # outfft = torch.empty([N, F, C, xfft.shape[2], xfft.shape[3], 2],
                #                      dtype=dtype, device=device)
                # complex_mul5(xfft, yfft, outfft)
                outfft = complex_mul(xfft, yfft)
                # outfft = complex_mul_cpp(xfft, yfft)
                outfft = outfft.sum(dim=2)
                # torch.cuda.synchronize()
                xfft = xfft.squeeze(dim=1)

            else:
                raise Exception(f"Unknown conv exec "
                                f"type: {args.conv_exec_type.name}.")

            if is_debug:
                global global_correlation_time
                global_correlation_time += time.time() - start_correlation
                if global_counter % global_threshold == 0:
                    print("correlation time: ", global_correlation_time)

            if is_debug:
                start_restore = time.time()

            outfft = restore_size_2D(outfft,
                                     init_H_fft=init_H_fft,
                                     init_half_W_fft=init_half_W_fft)

            if is_debug:
                global global_restore_time
                global_restore_time += time.time() - start_restore
                if global_counter % global_threshold == 0:
                    print("restore time (de-compress/concat output): ",
                          global_restore_time)

            if is_debug:
                start_irfft_time = time.time()

            if args.fft_type == "real_fft":
                out = torch.irfft(input=outfft,
                                  signal_ndim=Conv2dfftFunction.signal_ndim,
                                  signal_sizes=(init_H_fft, init_W_fft),
                                  onesided=True)
            elif args.fft_type == "complex_fft":
                out = torch.ifft(input=outfft,
                                 signal_ndim=Conv2dfftFunction.signal_ndim)
                # print("out: ", out)
                out = out[..., 0]  # retain only the real numbers

            if is_debug:
                global global_irfft_time
                global_irfft_time += time.time() - start_irfft_time
                if global_counter % global_threshold == 0:
                    print("i(r)fft time: ", global_irfft_time)

            del outfft
            out = out[..., :out_H, :out_W]
            if bias is not None:
                # Add the bias term for each filter (it has to be unsqueezed to
                # the dimension of the out to properly sum up the values).
                out += unsqueezed_bias

        # global global_correlation_time
        # global_correlation_time += time.time() - start_correlation
        # print("complex correlation time: ", global_correlation_time)

        if args.mem_test:
            torch.cuda.empty_cache()

        if (stride_H != 1 or stride_W != 1) and (
                stride_type is StrideType.STANDARD):
            out = out[:, :, ::stride_H, ::stride_W]

        if ctx:
            # for dx size
            ctx.H = H
            ctx.HH = HH
            # for dw size
            ctx.W = W
            ctx.WW = WW
            # for padding
            ctx.pad_H = pad_H
            ctx.pad_W = pad_W
            # for standard stride
            ctx.out_H = out_H
            ctx.out_W = out_W
            ctx.stride_H = stride_H
            ctx.stride_W = stride_W
            # for debug
            ctx.is_manual = is_manual
            # for debug
            ctx.conv_index = conv_index
            # for fft operations
            ctx.init_H_fft = init_H_fft
            ctx.init_W_fft = init_W_fft
            ctx.cuda_block_threads = cuda_block_threads
            ctx.half_fft_compressed_H = half_fft_compressed_H
            ctx.half_fft_compressed_W = half_fft_compressed_W
            ctx.C = C
            ctx.args = args
            ctx.save_for_backward(xfft, yfft)

        return out.clone()

    @staticmethod
    def backward(ctx, dout):
        """
        Compute the gradient using FFT.

        Requirements from PyTorch: backward() - gradient formula.
        It will be given as many Variable arguments as there were
        outputs, with each of them representing gradient w.r.t. that
        output. It should return as many Variables as there were
        inputs, with each of them containing the gradient w.r.t. its
        corresponding input. If your inputs did not require gradient
        (see needs_input_grad), or were non-Variable objects, you can
        return None. Also, if you have optional arguments to forward()
        you can return more gradients than there were inputs, as long
        as they’re all None.
        In short, backward() should return as many tensors, as there
        were inputs to forward().

        :param ctx: context with saved variables
        :param dout: output gradient
        :return: gradients for input map x, filter w and bias b
        """
        # print("execute backward")

        H = ctx.H
        HH = ctx.HH
        W = ctx.W
        WW = ctx.WW
        pad_H = ctx.pad_H
        pad_W = ctx.pad_W
        out_H = ctx.out_H
        out_W = ctx.out_W
        stride_H = ctx.stride_H
        stride_W = ctx.stride_W
        ctx.is_manual[0] = 1  # Mark the manual execution of the backward pass.
        conv_index = ctx.conv_index
        init_H_fft = ctx.init_H_fft
        init_W_fft = ctx.init_W_fft
        cuda_block_threads = ctx.cuda_block_threads
        half_fft_compressed_H = ctx.half_fft_compressed_H
        half_fft_compressed_W = ctx.half_fft_compressed_W
        C = ctx.C
        args = ctx.args
        xfft, yfft = ctx.saved_tensors

        if args.mem_test:
            torch.cuda.empty_cache()

        is_debug = args.is_debug
        # if is_debug:
        #     print(f"execute backward pass for convolution index: {conv_index}")

        if is_debug:
            global global_counter
            global_counter += 1
            start_init = time.time()

        need_input_grad = ctx.needs_input_grad[0]
        need_filter_grad = ctx.needs_input_grad[1]
        need_bias_grad = ctx.needs_input_grad[2]

        if args.mem_test:
            for tensor_obj in ctx.saved_tensors:
                del tensor_obj
            omit_objs = [id(ctx)]
            del ctx

            torch.cuda.empty_cache()

        if is_debug and args.mem_test:
            cuda_mem_show(info="backward start", omit_objs=omit_objs)

        dtype = xfft.dtype
        device = xfft.device

        if (stride_H != 1 or stride_W != 1) and (
                args.stride_type is StrideType.STANDARD):
            N, F, HHH, WWW = dout.size()
            assert HHH == WWW
            grad = torch.zeros(N, F, out_H, out_W, device=device, dtype=dtype)
            if out_H > HHH and out_W > WWW:
                grad[..., ::stride_H, ::stride_W] = dout
            else:
                assert out_H == HHH and out_W == WWW
            dout = grad
            del grad

        N, F, H_out, W_out = dout.shape
        if H_out != W_out:
            raise Exception("We only support square outputs.")

        dx = dw = db = None

        # Take the fft of dout (the gradient of the output of the forward pass).
        # We have to pad the flowing back gradient in the time (spatial) domain,
        # since it does not give correct results even for the case without
        # compression if we pad in the spectral (frequency) domain.
        fft_padding_dout_H = init_H_fft - H_out
        fft_padding_dout_W = init_W_fft - W_out

        if need_bias_grad:
            # The number of bias elements is equal to the number of filters.
            db = torch.zeros(F, dtype=dtype, device=device)

            # Calculate dB (the gradient for the bias term).
            # We sum up all the incoming gradients for each filter
            # bias (as in the affine layer).
            for ff in range(F):
                db[ff] += torch.sum(dout[:, ff, :])

        if is_debug:
            global global_init_time_back
            global_init_time_back += time.time() - start_init
            global global_threshold
            if global_counter % global_threshold == 0:
                print("global init time back: ", global_init_time_back)

        if is_debug:
            start_pad_grad = time.time()

        padded_dout = torch_pad(
            dout, (0, fft_padding_dout_W, 0, fft_padding_dout_H),
            'constant', 0)
        del dout

        if is_debug:
            global global_pad_grad
            global_pad_grad += time.time() - start_pad_grad
            if global_counter % global_threshold == 0:
                print("pad gradient: ", global_pad_grad)

        if args.mem_test:
            torch.cuda.empty_cache()

        if is_debug:
            start_fft_grad = time.time()

        doutfft = torch.rfft(padded_dout,
                             signal_ndim=Conv2dfftFunction.signal_ndim,
                             onesided=True)
        del padded_dout

        if is_debug:
            global global_fft_grad
            global_fft_grad += time.time() - start_fft_grad
            if global_counter % global_threshold == 0:
                print("fft gradient: ", global_fft_grad)

        if args.mem_test:
            torch.cuda.empty_cache()

        # the last dimension is for real and imaginary parts of the complex
        # numbers
        N, F, init_half_H_fft, init_half_W_fft, _ = doutfft.shape

        if half_fft_compressed_W < init_half_W_fft:
            doutfft = compress_2D_index_forward(doutfft, half_fft_compressed_W)

        if need_input_grad:
            if is_debug:
                start_conjugate_filter = time.time()

            yfft = pytorch_conjugate(yfft)

            if is_debug:
                global global_conjugate_filter
                global_conjugate_filter += time.time() - start_conjugate_filter
                if global_counter % global_threshold == 0:
                    print("conjugate filter: ", global_conjugate_filter)

            if is_debug:
                start_correlate_input_grad = time.time()

            # Initialize gradient output tensors.
            # the x used for convolution was with padding
            if args.conv_exec_type is ConvExecType.SERIAL:
                # Serially convolve each input map with all filters.
                dx = torch.zeros([N, C, H, W], dtype=dtype, device=device)
                for nn in range(N):
                    # Take one time series and unsqueeze it for broadcast with
                    # many gradients dout.
                    doutfft_nn = doutfft[nn].unsqueeze(1)
                    out = correlate_fft_signals2D(
                        xfft=doutfft_nn, yfft=yfft,
                        input_height=init_H_fft, input_width=init_W_fft,
                        init_fft_height=init_half_H_fft,
                        init_half_fft_width=init_half_W_fft,
                        out_height=H, out_width=W,
                        is_forward=False)
                    # Sum over all the Filters (F).
                    out = torch.sum(out, dim=0)
                    out = torch.unsqueeze(input=out, dim=0)
                    dx[nn] = out
            else:
                if args.conv_exec_type is ConvExecType.SGEMM:
                    # We want for doutfft: H, W, N, F, I
                    doutfft = doutfft.permute(2, 3, 0, 1, 4).contiguous()
                    # We have yfft: H, W, F, C, I

                    # returns: H, W, N, C, I
                    dxfft = fast_multiply(doutfft, yfft)

                    dxfft = dxfft.permute(2, 3, 0, 1, 4).contiguous()

                elif args.conv_exec_type is ConvExecType.CUDA_SHARED_LOG:
                    if torch.cuda.is_available():
                        dxfft = torch.zeros([N, C, half_fft_compressed_H,
                                             half_fft_compressed_W, 2],
                                            dtype=dtype, device=device)

                        # global global_permute_time
                        # start_permute = time.time()
                        # yfft is F, H, W, C -> C, H, W, F
                        yfft = yfft.permute(3, 1, 2, 0, 4).contiguous()
                        # Set the channels of doutfft permute as the last but
                        # one dimension.
                        # N,F,H,W,I -> N, H, W, F, I
                        doutfft = doutfft.permute(0, 2, 3, 1, 4).contiguous()
                        # global_permute_time += time.time() - start_permute
                        # print("permute time: ", global_permute_time)
                        # global global_complex_dxfft
                        # start_complex = time.time()
                        complex_mul_shared_log_cuda(doutfft, yfft, dxfft)
                        torch.cuda.synchronize()
                        # global_complex_dxfft += time.time() - start_complex
                        # print("complex dxfft: ", global_complex_dxfft)
                    else:
                        raise Exception(
                            "Selected CUDA conv execution but no cuda "
                            "device is available.")
                elif args.conv_exec_type is ConvExecType.CUDA_DEEP:
                    if torch.cuda.is_available():
                        dxfft = torch.zeros([N, C, half_fft_compressed_H,
                                             half_fft_compressed_W, 2],
                                            dtype=dtype, device=device)
                        # global global_permute_time
                        # start_permute = time.time()
                        # yfft is F, H, W, C -> C, H, W, F
                        yfft = yfft.permute(3, 1, 2, 0, 4).contiguous()
                        # Set the channels of doutfft permute as the last but
                        # one dimension.
                        # N,F,H,W,I -> N, H, W, F, I
                        doutfft = doutfft.permute(0, 2, 3, 1, 4).contiguous()
                        # global_permute_time += time.time() - start_permute
                        # print("permute time: ", global_permute_time)
                        # global global_complex_dxfft
                        # start_complex = time.time()
                        complex_mul_deep_cuda(doutfft, yfft, dxfft)
                        torch.cuda.synchronize()
                        # global_complex_dxfft += time.time() - start_complex
                        # print("complex dxfft: ", global_complex_dxfft)
                    else:
                        raise Exception(
                            "Selected CUDA conv execution but no cuda "
                            "device is available.")
                elif args.conv_exec_type is ConvExecType.CUDA:
                    if torch.cuda.is_available():
                        dxfft = torch.zeros([N, C, half_fft_compressed_H,
                                             half_fft_compressed_W, 2],
                                            dtype=dtype, device=device)
                        # global global_permute_time
                        # start_permute = time.time()
                        doutfft = doutfft.contiguous()
                        dxfft = dxfft.contiguous()
                        yfft = yfft.permute(1, 0, 2, 3, 4).contiguous()
                        # global_permute_time += time.time() - start_permute
                        # print("permute time: ", global_permute_time)
                        # global global_complex_dxfft
                        # start_complex = time.time()

                        complex_mul_stride_no_permute_cuda(doutfft, yfft, dxfft,
                                                           cuda_block_threads)
                        torch.cuda.synchronize()
                        # global_complex_dxfft += time.time() - start_complex
                        # print("complex dxfft: ", global_complex_dxfft)
                    else:
                        raise Exception(
                            "Selected CUDA conv execution but no cuda "
                            "device is available.")

                elif args.conv_exec_type is ConvExecType.BATCH:

                    dxfft = torch.zeros([N, C, half_fft_compressed_H,
                                         half_fft_compressed_W, 2],
                                        dtype=dtype, device=device)

                    # Convolve some part of the dout batch with all filters.
                    # 2 is for complex numbers
                    start = 0
                    # step = get_step_estimate(xfft, yfft, args.memory_size, scale=1)
                    step = args.min_batch_size
                    doutfft = doutfft.unsqueeze(dim=2)
                    for start in range(start, N, step):
                        stop = min(start + step, N)
                        doutfft_nn = doutfft[start:stop]
                        dxfft[start:stop] = complex_mul(doutfft_nn,
                                                        yfft).sum(dim=1)
                else:
                    raise Exception(f"Unknown conv exec "
                                    f"type: {args.conv_exec_type.name}.")

                if is_debug:
                    global global_correlate_input_grad
                    global_correlate_input_grad += time.time() - start_correlate_input_grad
                    if global_counter % global_threshold == 0:
                        print("correlate input grad: ",
                              global_correlate_input_grad)

                if is_debug:
                    start_restore_input = time.time()

                dxfft = restore_size_2D(dxfft, init_H_fft=init_H_fft,
                                        init_half_W_fft=init_half_W_fft)

                if is_debug:
                    global global_restore_input
                    global_restore_input += time.time() - start_restore_input
                    if global_counter % global_threshold == 0:
                        print("restore input back: ", global_restore_input)

                if is_debug:
                    start_irfft_input = time.time()

                dx = torch.irfft(input=dxfft,
                                 signal_ndim=Conv2dfftFunction.signal_ndim,
                                 signal_sizes=(init_H_fft, init_W_fft),
                                 onesided=True)
                del dxfft

                if is_debug:
                    global global_irfft_input
                    global_irfft_input += time.time() - start_irfft_input
                    if global_counter % global_threshold == 0:
                        print("irfft input back: ", global_irfft_input)

                dx = dx[..., pad_H:H + pad_H, pad_W:W + pad_W]
            del yfft

        if args.mem_test:
            torch.cuda.empty_cache()

        if need_filter_grad:
            # Calculate dw - the gradient for the filters w.
            # By chain rule dw is computed as: dout*x
            """
            More specifically:
            if the forward convolution is: [x1, x2, x3, x4] * [w1, w2], where *
            denotes the convolution operation, 
            Conv (out) = [x1 w1 + x2 w2, x2 w1 + x3 w2, x3 w1 + x4 w2]
            then the bacward to compute the 
            gradient for the weights is as follows (L - is the Loss function):
            gradient L / gradient w = 
            gradient L / gradient Conv x (times) gradient Conv / gradient w =
            dout x gradient Conv / gradient w = (^)
            
            gradient Conv / gradient w1 = [x1, x2, x3]
            gradient Conv / gradient w2 = [x2, x3, x4]
            
            dout = [dx1, dx2, dx3]
            
            gradient L / gradient w1 = dout * gradient Conv / gradient w1 =
            [dx1 x1 + dx2 x2 + dx3 x3]
            
            gradient L / gradient w2 = dout * gradient Conv / gradient w2 =
            [dx1 x2 + dx2 x3 + dx3 x4]
            
            Thus, the gradient for the weights is the convolution between the 
            flowing back gradient dout and the input x:
            gradient L / gradient w = [x1, x2, x3, x4] * [dx1, dx2, dx3]
            """
            if is_debug:
                start_correlate_filter_grad = time.time()

            doutfft = pytorch_conjugate(doutfft)
            if args.conv_exec_type is ConvExecType.SERIAL:
                # Serially convolve each input dout with all input maps xfft.
                dw = torch.empty([F, C, HH, WW], dtype=dtype, device=device)
                for ff in range(F):
                    # doutfft_ff has as many channels as number of input filters.
                    doutfft_ff = doutfft[:, ff, ...].unsqueeze(1)
                    out = correlate_fft_signals2D(
                        xfft=xfft, yfft=doutfft_ff,
                        input_height=init_H_fft, input_width=init_W_fft,
                        init_fft_height=init_half_H_fft,
                        init_half_fft_width=init_half_W_fft,
                        out_height=HH, out_width=WW,
                        is_forward=False)
                    # For a given filter, we have to sum up all its contributions
                    # to all the input maps.
                    out = torch.sum(input=out, dim=0)
                    # `unsqueeze` the dimension 0 for the input data points (N).
                    out = torch.unsqueeze(input=out, dim=0)
                    # print("conv name: {}, out shape: {}, dw shape: {}, N: {}, C: {}, F: {}".format(
                    #     "conv"+str(conv_index), out.size(), dw.size(), str(N),
                    #     str(C), str(F)))
                    dw[ff] = out
            else:

                if args.conv_exec_type is ConvExecType.SGEMM:
                    # We have xfft: H, W, C, N, I

                    if need_input_grad == False:
                        # doutfft is: N, F, H, W, I
                        # We want for doutfft: H, W, N, F, I
                        doutfft = doutfft.permute(2, 3, 0, 1, 4).contiguous()
                    # We have doutfft: H, W, N, F, I

                    # returns: H, W, C, F, I
                    dwfft = fast_multiply(xfft, doutfft)

                    # go to: F, C, H, W, I
                    dwfft = dwfft.permute(3, 2, 0, 1, 4)

                elif args.conv_exec_type is ConvExecType.CUDA_SHARED_LOG:
                    if torch.cuda.is_available():

                        # 2 is for the complex numbers
                        dwfft = torch.zeros([F, C, half_fft_compressed_H,
                                             half_fft_compressed_W, 2],
                                            dtype=dtype, device=device)

                        # Set the F channels as the last but one dimension in
                        # both the fft-ed gradient and xfft.
                        # size of doutfft: N, H, W, F, I -> F,H,W,N,I
                        # print("N,F,half_fft_compressed_H,half_fft_compressed_W,C:", N, F, half_fft_compressed_H, half_fft_compressed_W, C)
                        # print("doutfft size before permute: ", doutfft.size())
                        if need_input_grad:
                            doutfft = doutfft.permute(3, 1, 2, 0,
                                                      4).contiguous()
                        else:
                            # N, F, H, W, I -> F,H,W,N,I
                            doutfft = doutfft.permute(1, 2, 3, 0,
                                                      4).contiguous()
                        # print("doutfft size after permute: ", doutfft.size())
                        # xfft: N,H,W,C,I -> C,H,W,N,I
                        xfft = xfft.permute(3, 1, 2, 0, 4).contiguous()
                        # print("xfft size: ", xfft.size())
                        complex_mul_shared_log_cuda(doutfft, xfft, dwfft)
                        torch.cuda.synchronize()
                    else:
                        raise Exception(
                            "Selected CUDA conv execution but no cuda "
                            "device is available.")
                elif args.conv_exec_type is ConvExecType.CUDA_DEEP:
                    if torch.cuda.is_available():

                        # 2 is for the complex numbers
                        dwfft = torch.zeros([F, C, half_fft_compressed_H,
                                             half_fft_compressed_W, 2],
                                            dtype=dtype, device=device)

                        # Set the F channels as the last but one dimension in
                        # both the fft-ed gradient and xfft.
                        # size of doutfft: N, H, W, F, I -> F,H,W,N,I
                        # print("N,F,half_fft_compressed_H,half_fft_compressed_W,C:", N, F, half_fft_compressed_H, half_fft_compressed_W, C)
                        # print("doutfft size before permute: ", doutfft.size())
                        if need_input_grad:
                            doutfft = doutfft.permute(3, 1, 2, 0,
                                                      4).contiguous()
                        else:
                            # N, F, H, W, I -> F,H,W,N,I
                            doutfft = doutfft.permute(1, 2, 3, 0,
                                                      4).contiguous()
                        # print("doutfft size after permute: ", doutfft.size())
                        # xfft: N,H,W,C,I -> C,H,W,N,I
                        xfft = xfft.permute(3, 1, 2, 0, 4).contiguous()
                        # print("xfft size: ", xfft.size())
                        complex_mul_deep_cuda(doutfft, xfft, dwfft)
                        torch.cuda.synchronize()
                    else:
                        raise Exception(
                            "Selected CUDA conv execution but no cuda "
                            "device is available.")
                elif args.conv_exec_type is ConvExecType.CUDA:
                    if torch.cuda.is_available():

                        # 2 is for the complex numbers
                        dwfft = torch.zeros([F, C, half_fft_compressed_H,
                                             half_fft_compressed_W, 2],
                                            dtype=dtype, device=device)

                        doutfft = doutfft.permute(1, 0, 2, 3, 4).contiguous()
                        xfft = xfft.permute(1, 0, 2, 3, 4).contiguous()
                        complex_mul_stride_no_permute_cuda(doutfft, xfft, dwfft,
                                                           cuda_block_threads)
                        torch.cuda.synchronize()
                    else:
                        raise Exception(
                            "Selected CUDA conv execution but no cuda "
                            "device is available.")
                elif args.conv_exec_type is ConvExecType.BATCH:

                    # 2 is for the complex numbers
                    dwfft = torch.zeros([F, C, half_fft_compressed_H,
                                         half_fft_compressed_W, 2],
                                        dtype=dtype, device=device)

                    # Convolve some part of the dout batch with all input maps.
                    start = 0
                    # step = get_step_estimate(xfft, doutfft, memory_size=memory_size,
                    #                          scale=4)
                    step = args.min_batch_size
                    if len(
                            doutfft.shape) == 5:  # we did not need grad for input
                        doutfft.unsqueeze_(dim=2)
                    doutfft = doutfft.permute(1, 0, 2, 3, 4, 5)
                    for start in range(start, F, step):
                        stop = min(start + step, F)
                        doutfft_nn = doutfft[start:stop]
                        dwfft[start:stop] = complex_mul(xfft, doutfft_nn).sum(
                            dim=1)
                else:
                    raise Exception(f"Unknown conv exec "
                                    f"type: {args.conv_exec_type.name}.")

                if is_debug:
                    global global_correlate_filter_grad
                    global_correlate_filter_grad += time.time() - start_correlate_filter_grad
                    if global_counter % global_threshold == 0:
                        print("correlate filter grad: ",
                              global_correlate_filter_grad)

                if is_debug:
                    start_restore_filter = time.time()

                dwfft = restore_size_2D(dwfft, init_H_fft=init_H_fft,
                                        init_half_W_fft=init_half_W_fft)

                if is_debug:
                    global global_restore_filter
                    global_restore_filter += time.time() - start_restore_filter
                    if global_counter % global_threshold == 0:
                        print("filter restore back: ", global_restore_filter)

                if is_debug:
                    start_irfft_filter = time.time()

                dw = torch.irfft(input=dwfft,
                                 signal_ndim=Conv2dfftFunction.signal_ndim,
                                 signal_sizes=(init_H_fft, init_W_fft),
                                 onesided=True)
                del dwfft

                if is_debug:
                    global global_irfft_filter
                    global_irfft_filter += time.time() - start_irfft_filter
                    if global_counter % global_threshold == 0:
                        print("irfft filter back: ", global_irfft_filter)

                dw = dw[..., :HH, :WW]
        del doutfft
        del xfft

        if args.mem_test:
            torch.cuda.empty_cache()

        # if dx is not None:
        #     print("dx size: ", dx.size(), ", dw size: ", dw.size())
        # else:
        #     print("dw size: ", dw.size())

        return dx, dw, db, None, None, None, None, None, None


class Conv2dfft(Module):
    """
    :conv_index_counter: the counter to index (number) of the convolutional
    2d fft layers .
    """
    conv_index_counter = 0

    def __init__(self, in_channels=None, out_channels=None, kernel_size=None,
                 stride=1, padding=0, dilation=None, groups=None, bias=False,
                 weight_value=None, bias_value=None, is_manual=tensor([0]),
                 args=Arguments(), out_size=None):
        """

        2D convolution using FFT implemented fully in PyTorch.

        :param in_channels: (int) – Number of channels in the input series.
        :param out_channels: (int) – Number of channels produced by the
        convolution (equal to the number of filters in the given conv layer).
        :param kernel_size: (int) - Size of the convolving kernel (the width and
        height of the filter).
        :param stride: what is the stride for the convolution (the pattern for
        omitted values).
        :param padding: the padding added to the (top and bottom) and to the
        (left and right) of the input signal.
        :param dilation: (int) – Spacing between kernel elements. Default: 1
        :param groups: (int) – Number of blocked connections from input channels
        to output channels. Default: 1
        :param bias: (bool) - add bias or not
        :param compress_rate: how many frequency coefficients should be
        discarded
        :param preserve_energy: how much energy should be preserved in the input
        image.
        :param out_size: what is the expected output size of the
        operation (when compression is used and the out_size is
        smaller than the size of the input to the convolution, then
        the max pooling can be omitted and the compression
        in this layer can serve as the frequency-based (spectral)
        pooling.
        :param weight_value: you can provide the initial filter, i.e.
        filter weights of shape (F, C, HH, WW), where
        F - number of filters, C - number of channels, HH - height of the
        filter, WW - width of the filter
        :param bias_value: you can provide the initial value of the bias,
        of shape (F,)
        :param use_next_power2: should we extend the size of the input for the
        FFT convolution to the next power of 2.
        :param is_manual: to check if the backward computation of convolution
        was computed manually.

        Regarding the stride parameter: the number of pixels between
        adjacent receptive fields in the horizontal and vertical
        directions, we can generate the full output, and then remove the
        redundant elements according to the stride parameter. The more relevant
        method is to apply spectral pooling as a means to achieving the strided
        convolution.
        """
        super(Conv2dfft, self).__init__()
        self.args = args

        if dilation is not None and dilation > 1:
            raise NotImplementedError("dilation > 1 is not supported.")
        if groups is not None and groups > 1:
            raise NotImplementedError("groups > 1 is not supported.")

        self.is_weight_value = None  # Was the filter value provided?
        if weight_value is None:
            self.is_weight_value = False
            if out_channels is None or in_channels is None or \
                    kernel_size is None:
                raise ValueError("Either specify filter_value or provide all"
                                 "the required parameters (out_channels, "
                                 "in_channels and kernel_size) to generate the "
                                 "filter.")
            self.kernel_height, self.kernel_width = get_pair(kernel_size)
            if args.dtype is torch.float:
                weight = torch.randn(out_channels, in_channels,
                                     self.kernel_height,
                                     self.kernel_width, dtype=args.dtype)
            elif args.dtype is torch.half:
                weight = torch.randn(out_channels, in_channels,
                                     self.kernel_height,
                                     self.kernel_width).to(torch.half)
            else:
                raise Exception(f"Unknown dtype in args: {args.dtype}")
            self.weight = Parameter(weight)
        else:
            self.is_weight_value = True
            self.weight = weight_value
            out_channels = weight_value.shape[0]
            in_channels = weight_value.shape[1]
            self.kernel_height = weight_value.shape[2]
            self.kernel_width = weight_value.shape[3]

        self.is_bias_value = None  # Was the bias value provided.
        if bias_value is None:
            self.is_bias_value = False
            if bias is True:
                self.bias = Parameter(
                    torch.randn(out_channels, dtype=args.dtype))
            else:
                self.register_parameter('bias', None)
                self.bias = None
        else:
            self.is_bias_value = True
            self.bias = bias_value

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = padding
        self.stride = stride
        self.is_manual = is_manual
        self.conv_index = Conv2dfft.conv_index_counter
        Conv2dfft.conv_index_counter += 1
        self.out_size = out_size

        if args is None:
            self.compress_rate = None
            self.preserve_energy = None
            self.is_debug = False
            self.next_power2 = False
            self.is_debug = False
            self.compress_type = CompressType.STANDARD
        else:
            self.compress_rate = args.compress_rate
            self.preserve_energy = args.preserve_energy
            self.next_power2 = args.next_power2
            self.is_debug = args.is_debug
            self.compress_type = args.compress_type

        self.reset_parameters()

    def reset_parameters(self):
        if self.is_weight_value is not None and self.is_weight_value is False:
            if self.weight.dtype is torch.half:
                dtype = self.weight.dtype
                weight = self.weight.to(torch.float)
                init.kaiming_uniform_(weight, a=math.sqrt(5))
                self.weight = Parameter(weight.to(dtype))
            else:
                init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        if self.bias is not None and self.is_bias_value is False:
            fan_in, _ = init._calculate_fan_in_and_fan_out(self.weight)
            bound = 1 / math.sqrt(fan_in)
            init.uniform_(self.bias, -bound, bound)

    def reset_parameters_old(self):
        n = self.in_channels
        n *= self.kernel_height * self.kernel_width
        stdv = 1. / math.sqrt(n)
        if self.is_weight_value is not None and self.is_weight_value is False:
            self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None and self.is_bias_value is False:
            self.bias.data.uniform_(-stdv, stdv)

    def forward(self, input):
        """
        This is the fully manual implementation of the forward and backward
        passes via the torch.autograd.Function.

        :param input: the input map (e.g., an image)
        :return: the result of 2D convolution
        """
        # ctx, input, filter, bias, padding = (0, 0), stride = (1, 1),
        # args = None, out_size = None, is_manual = tensor([0]),
        # conv_index = None
        return Conv2dfftFunction.apply(
            input, self.weight, self.bias, self.padding, self.stride,
            self.args, self.out_size, self.is_manual, self.conv_index)


class Conv2dfftAutograd(Conv2dfft):
    def __init__(self, in_channels=None, out_channels=None, kernel_size=None,
                 stride=1, padding=0, dilation=None, groups=None, bias=True,
                 weight_value=None, bias_value=None, is_manual=tensor([0]),
                 conv_index=None,
                 args=Arguments(conv_exec_type=ConvExecType.BATCH),
                 out_size=None):
        """
        2D convolution using FFT with backward pass executed via PyTorch's
        autograd.
        """
        super(Conv2dfftAutograd, self).__init__(
            in_channels=in_channels, out_channels=out_channels,
            kernel_size=kernel_size, stride=stride, padding=padding,
            dilation=dilation, groups=groups, bias=bias,
            weight_value=weight_value, bias_value=bias_value,
            is_manual=is_manual, args=args, out_size=out_size)

    def forward(self, input):
        """
        Forward pass of 2D convolution.

        The input consists of N data points with each data point
        representing a signal (e.g., time-series) of length W.

        We also have the notion of channels in the 1-D convolution.
        We want to use more than a single filter even for
        the input signal, so the output is a batch with the same size
        but the number of output channels is equal to the
        number of input filters.

        We want to use the auto-grad (auto-differentiation so call the
        forward method directly).

        :param input: Input data of shape (N, C, W), N - number of data
        points in the batch, C - number of channels, W - the
        width of the signal or time-series (number of data points in
        a univariate series)
        :return: output data, of shape (N, F, W') where W' is given
        by: W' = 1 + (W + 2*pad - WW)

         :see:
         source short: https://goo.gl/GwyhXz
         source full: https://stackoverflow.com/questions/40703751/
         using-fourier-transforms-to-do-convolution?utm_medium=orga
         nic&utm_source=google_rich_qa&utm_campaign=google_rich_qa

        >>> # Test stride for 3 channels and 2 filters.
        >>> # based on: http://cs231n.github.io/convolutional-networks/
        >>> x = tensor(
        ... [[[
        ... [2.0, 0.0, 2.0, 0.0, 1.0],
        ... [0.0, 1.0, 0.0, 1.0, 2.0],
        ... [0.0, 2.0, 0.0, 0.0, 0.0],
        ... [2.0, 2.0, 2.0, 0.0, 2.0],
        ... [2.0, 0.0, 1.0, 1.0, 1.0],
        ... ],[
        ... [1.0, 1.0, 2.0, 1.0, 0.0],
        ... [0.0, 1.0, 2.0, 2.0, 1.0],
        ... [0.0, 1.0, 2.0, 1.0, 2.0],
        ... [2.0, 1.0, 0.0, 2.0, 1.0],
        ... [2.0, 1.0, 2.0, 1.0, 2.0],
        ... ],[
        ... [1.0, 1.0, 2.0, 1.0, 2.0],
        ... [1.0, 2.0, 0.0, 0.0, 1.0],
        ... [0.0, 0.0, 2.0, 0.0, 0.0],
        ... [1.0, 2.0, 2.0, 0.0, 2.0],
        ... [0.0, 2.0, 2.0, 0.0, 0.0],
        ... ]]])
        >>> y = tensor([[
        ... [[ 1.0, 0.0, 0.0],
        ...  [-1.0,-1.0, 0.0],
        ...  [ 1.0, 0.0, 0.0]],
        ... [[-1.0, 0.0, 1.0],
        ...  [ 0.0, 1.0,-1.0],
        ...  [-1.0,-1.0, 1.0]],
        ... [[-1.0, 0.0, 1.0],
        ...  [ 0.0, 0.0, 1.0],
        ...  [ 0.0,-1.0,-1.0]]],
        ... [
        ... [[ 1.0, 0.0,-1.0],
        ...  [-1.0, 0.0, 1.0],
        ...  [-1.0, 1.0, 0.0]],
        ... [[-1.0,-1.0, 0.0],
        ...  [ 0.0, -1.0, 1.0],
        ...  [ 1.0, 1.0,-1.0]],
        ... [[ 1.0,-1.0, 1.0],
        ...  [ 0.0,-1.0,-1.0],
        ...  [ 1.0, 1.0,-1.0]]],
        ... ])
        >>> b = tensor([1.0, 0.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias_value=b,
        ... padding=(1, 1), stride=(2, 2))
        >>> result = conv.forward(input=x)
        >>> expect = np.array([[[
        ... [-2.0, 1.0,-3.0],
        ... [-1.0, 1.0,-3.0],
        ... [ 5.0, 2.0,-1.0]],[
        ... [-4.0,-2.0, 3.0],
        ... [ 5.0,-3.0, 2.0],
        ... [-6.0,-1.0,-8.0]],
        ... ]])
        >>> np.testing.assert_array_almost_equal(x=expect, y=result, decimal=5,
        ... err_msg="The expected array x and computed y are not almost equal.")

        >>> # Test 3 channels and 2 filters.
        >>> x = tensor(
        ... [[[
        ... [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ... [0.0, 2.0, 0.0, 2.0, 0.0, 1.0, 0.0],
        ... [0.0, 0.0, 1.0, 0.0, 1.0, 2.0, 0.0],
        ... [0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0],
        ... [0.0, 2.0, 2.0, 2.0, 0.0, 2.0, 0.0],
        ... [0.0, 2.0, 0.0, 1.0, 1.0, 1.0, 0.0],
        ... [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ... ],[
        ... [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ... [0.0, 1.0, 1.0, 2.0, 1.0, 0.0, 0.0],
        ... [0.0, 0.0, 1.0, 2.0, 2.0, 1.0, 0.0],
        ... [0.0, 0.0, 1.0, 2.0, 1.0, 2.0, 0.0],
        ... [0.0, 2.0, 1.0, 0.0, 2.0, 1.0, 0.0],
        ... [0.0, 2.0, 1.0, 2.0, 1.0, 2.0, 0.0],
        ... [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ... ],[
        ... [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ... [0.0, 1.0, 1.0, 2.0, 1.0, 2.0, 0.0],
        ... [0.0, 1.0, 2.0, 0.0, 0.0, 1.0, 0.0],
        ... [0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0],
        ... [0.0, 1.0, 2.0, 2.0, 0.0, 2.0, 0.0],
        ... [0.0, 0.0, 2.0, 2.0, 0.0, 0.0, 0.0],
        ... [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        ... ]]])
        >>> y = tensor([[
        ... [[ 1.0, 0.0, 0.0],
        ...  [-1.0,-1.0, 0.0],
        ...  [ 1.0, 0.0, 0.0]],
        ... [[-1.0, 0.0, 1.0],
        ...  [ 0.0, 1.0,-1.0],
        ...  [-1.0,-1.0, 1.0]],
        ... [[-1.0, 0.0, 1.0],
        ...  [ 0.0, 0.0, 1.0],
        ...  [ 0.0,-1.0,-1.0]]],
        ... [
        ... [[ 1.0, 0.0,-1.0],
        ...  [-1.0, 0.0, 1.0],
        ...  [-1.0, 1.0, 0.0]],
        ... [[-1.0,-1.0, 0.0],
        ...  [ 0.0, -1.0, 1.0],
        ...  [ 1.0, 1.0,-1.0]],
        ... [[ 1.0,-1.0, 1.0],
        ...  [ 0.0,-1.0,-1.0],
        ...  [ 1.0, 1.0,-1.0]]],
        ... ])
        >>> b = tensor([1.0, 0.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias_value=b)
        >>> result = conv.forward(input=x)
        >>> expect = np.array(
        ... [[[[-2.0000e+00, -1.0000e+00,  1.0000e+00, -2.0000e+00, -3.0000e+00],
        ... [ 5.0000e+00,  2.0000e+00, -2.0000e+00,  1.0000e+00, -6.0000e+00],
        ... [-1.0000e+00, -4.0000e+00,  1.0000e+00, -1.0000e+00, -3.0000e+00],
        ... [ 1.7881e-07,  1.0000e+00, -7.0000e+00, -4.7684e-07, -3.0000e+00],
        ... [ 5.0000e+00,  1.0000e+00,  2.0000e+00,  1.0000e+00, -1.0000e+00]],
        ... [[-4.0000e+00,  1.0000e+00, -2.0000e+00, -2.0000e+00,  3.0000e+00],
        ... [-3.0000e+00, -2.0000e+00, -1.0000e+00,  4.0000e+00, -2.0000e+00],
        ... [ 5.0000e+00,  1.0000e+00, -3.0000e+00, -5.0000e+00,  2.0000e+00],
        ... [-3.0000e+00, -5.0000e+00,  2.0000e+00, -1.0000e+00, -3.0000e+00],
        ... [-6.0000e+00, -6.0000e+00, -1.0000e+00,  3.0000e+00, -8.0000e+00]]]]
        ... )
        >>> np.testing.assert_array_almost_equal(x=expect, y=result, decimal=5,
        ... err_msg="The expected array x and computed y are not almost equal.")

        >>> # Test with compression (index back)
        >>> # A single input map.
        >>> x = tensor([[[[1.0, 2.0, 3.0], [3.0, 4.0, 1.0], [1., 2., 1.]]]])
        >>> # A single filter.
        >>> y = tensor([[[[1.0, 2.0], [3.0, 2.0]]]])
        >>> b = tensor([0.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias_value=b, args=Arguments(compress_rate=1, preserve_energy=100))
        >>> result = conv.forward(input=x)
        >>> # expect = np.array([[[[21.5, 22.0], [17.5, 13.]]]])
        >>> expect = np.array([[[[21.75, 21.75], [18.75, 13.75]]]])
        >>> np.testing.assert_array_almost_equal(x=expect, y=result,
        ... err_msg="The expected array x and computed y are not almost equal.")

        >>> # Test 2D convolution.
        >>> # A single input map.
        >>> x = tensor([[[[1.0, 2.0, 3.0], [3.0, 4.0, 1.0], [1., 2., 1.]]]])
        >>> # A single filter.
        >>> y = tensor([[[[1.0, 2.0], [3.0, 2.0]]]])
        >>> b = tensor([0.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias_value=b)
        >>> result = conv.forward(input=x)
        >>> expect = np.array([[[[22.0, 22.0], [18., 14.]]]])
        >>> np.testing.assert_array_almost_equal(x=expect, y=result,
        ... err_msg="The expected array x and computed y are not almost equal.")

        >>> # Test bias.
        >>> # A single input map.
        >>> x = tensor([[[[1.0, 2.0, 3.0], [3.0, 4.0, 1.0], [1., 2., 1.]]]])
        >>> # A single filter.
        >>> y = tensor([[[[1.0, 2.0], [3.0, 2.0]]]])
        >>> b = tensor([-1.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias_value=b)
        >>> result = conv.forward(input=x)
        >>> expect = np.array([[[[21.0, 21.0], [17., 13.]]]])
        >>> np.testing.assert_array_almost_equal(x=expect, y=result,
        ... err_msg="The expected array x and computed y are not almost equal.")

        >>> # Don't use next power of 2.
        >>> # A single input map.
        >>> x = tensor([[[[1.0, 2.0, 3.0], [3.0, 4.0, 1.0], [1., 2., 1.]]]])
        >>> # A single filter.
        >>> y = tensor([[[[1.0, 2.0], [3.0, 2.0]]]])
        >>> b = tensor([0.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias=b)
        >>> result = conv.forward(input=x)
        >>> expect = np.array([[[[22.0, 22.0], [18., 14.]]]])
        >>> np.testing.assert_array_almost_equal(x=expect, y=result,
        ... err_msg="The expected array x and computed y are not almost equal.")

        >>> # Test 2 channels and 2 filters.
        >>> x = tensor([[[[1.0, 2.0, 3.0], [3.0, 4.0, 1.0], [1., 2., 1.]],
        ... [[1., 1., 2.], [2., 3., 1.], [2., -1., 3.]]]])
        >>> y = tensor([[[[1.0, 2.0], [3.0, 2.0]], [[-1.0, 2.0],[3.0, -2.0]]],
        ... [[[-1.0, 1.0], [2.0, 3.0]], [[-2.0, 1.0], [1.0, -3.0]]]])
        >>> b = tensor([0.0, 0.0])
        >>> conv = Conv2dfftAutograd(weight_value=y, bias_value=b)
        >>> result = conv.forward(input=x)
        >>> expect = np.array([[[[23.0, 32.0], [30., 4.]],[[11.0, 12.0],
        ... [13.0, -11.0]]]])
        >>> np.testing.assert_array_almost_equal(x=expect, y=result, decimal=5,
        ... err_msg="The expected array x and computed y are not almost equal.")
        """
        return Conv2dfftFunction.forward(
            ctx=None, input=input, filter=self.weight, bias=self.bias,
            padding=self.padding, stride=self.stride, is_manual=self.is_manual,
            conv_index=self.conv_index, args=self.args, out_size=self.out_size)


def test_run():
    torch.manual_seed(231)
    filter = np.array(
        [[[[1.3, 2.1, 3.6], [2.9, -4.1, 1.1], [-2.1, 1.2, -1.3]]]],
        dtype=np.float32)
    filter = torch.from_numpy(filter)
    module = Conv2dfft(filter)
    print("filter and bias parameters: ", list(module.parameters()))
    input = torch.randn(1, 1, 10, 10, requires_grad=True)
    output = module(input)
    print("forward output: ", output)
    output.backward(torch.randn(1, 1, 8, 8))
    print("gradient for the input: ", input.grad)


if __name__ == "__main__":
    test_run()

    import doctest

    sys.exit(doctest.testmod()[0])
