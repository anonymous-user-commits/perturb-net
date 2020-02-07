#include <torch/torch.h>

#include <vector>

// CUDA forward declarations

std::vector<at::Tensor> conv_cuda_forward(
    at::Tensor input,
    at::Tensor filter,
    at::Tensor bias,
    at::Tensor padding,
    at::Tensor index_back);

std::vector<at::Tensor> conv_cuda_backward(
    at::Tensor dout,
    at::Tensor xfft,
    at::Tensor yfft,
    at::Tensor W,
    at::Tensor WW,
    at::Tensor fft_size);

float plus_reduce_cuda(at::Tensor input);

// C++ interface

// NOTE: AT_ASSERT has become AT_CHECK on master after 0.4.
#define CHECK_CUDA(x) AT_ASSERTM(x.type().is_cuda(), #x " must be a CUDA tensor")
#define CHECK_CONTIGUOUS(x) AT_ASSERTM(x.is_contiguous(), #x " must be contiguous")
#define CHECK_INPUT(x) CHECK_CUDA(x); CHECK_CONTIGUOUS(x)

std::vector<at::Tensor> conv_forward(
    at::Tensor input,
    at::Tensor filter,
    at::Tensor bias,
    at::Tensor padding,
    at::Tensor index_back) {
  CHECK_INPUT(input);
  CHECK_INPUT(filter);
  CHECK_INPUT(bias);
  CHECK_INPUT(padding);
  CHECK_INPUT(index_back);

  return conv_cuda_forward(input, filter, bias, padding, index_back);
}

std::vector<at::Tensor> conv_backward(
    at::Tensor dout,
    at::Tensor xfft,
    at::Tensor yfft,
    at::Tensor W,
    at::Tensor WW,
    at::Tensor fft_size) {
  CHECK_INPUT(dout);
  CHECK_INPUT(xfft);
  CHECK_INPUT(yfft);
  CHECK_INPUT(W);
  CHECK_INPUT(WW);
  CHECK_INPUT(fft_size)

  return conv_cuda_backward(dout, xfft, yfft, W, WW, fft_size);
}

float plus_reduce(at::Tensor input) {
  CHECK_INPUT(input);
  return plus_reduce_cuda(input);
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
  // m.def("forward", &conv_forward, "Conv forward (CUDA)");
  // m.def("backward", &conv_backward, "Conv backward (CUDA)");
  m.def("plus_reduce", &plus_reduce, "plus_reduce (CUDA)");
}