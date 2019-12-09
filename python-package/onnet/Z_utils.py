'''
    1 晕   Pytorch居然不支持复向量 https://github.com/pytorch/pytorch/issues/755

'''

import torch
from torch.nn import ReflectionPad2d
from torch.nn.functional import relu, max_pool2d, dropout, dropout2d
import numpy as np

class COMPLEX_utils(object):
    @staticmethod
    def isComplex(input):
        return input.size(-1) == 2

    @staticmethod
    def isReal(input):
        return input.size(-1) == 1

    @staticmethod
    def ToZ(u0):
        if COMPLEX_utils.isComplex(u0):
            return u0
        else:
            z0 = u0.new_zeros(u0.shape + (2,))
            z0[..., 0] = u0
            assert(COMPLEX_utils.isComplex(z0))
            return z0

    @staticmethod
    def relu(input_r,input_i):
        return relu(input_r), relu(input_i)

    @staticmethod
    def max_pool2d(input_r,input_i,kernel_size, stride=None, padding=0,
                                    dilation=1, ceil_mode=False, return_indices=False):

        return max_pool2d(input_r, kernel_size, stride, padding, dilation,
                          ceil_mode, return_indices), \
               max_pool2d(input_i, kernel_size, stride, padding, dilation,
                          ceil_mode, return_indices)

    @staticmethod
    def dropout(input_r,input_i, p=0.5, training=True, inplace=False):
        return dropout(input_r, p, training, inplace), \
               dropout(input_i, p, training, inplace)

    @staticmethod
    def dropout2d(input_r,input_i, p=0.5, training=True, inplace=False):
        return dropout2d(input_r, p, training, inplace), \
               dropout2d(input_i, p, training, inplace)

    #the absolute value or modulus of z     https://en.wikipedia.org/wiki/Absolute_value#Complex_numbers
    @staticmethod
    def modulus(x):
        shape = x.size()[:-1]
        norm = torch.zeros(shape).double()
        #norm[...,0] = (x[...,0]*x[...,0] + x[...,1]*x[...,1]).sqrt()
        norm[...] = (x[..., 0] * x[..., 0] + x[..., 1] * x[..., 1]).sqrt()
        return norm

    @staticmethod
    def fft(input, direction='C2C', inverse=False):
        """
            Interface with torch FFT routines for 2D signals.

            Example
            -------
            x = torch.randn(128, 32, 32, 2)
            x_fft = fft(x, inverse=True)

            Parameters
            ----------
            input : tensor
                complex input for the FFT
            direction : string
                'C2R' for complex to real, 'C2C' for complex to complex
            inverse : bool
                True for computing the inverse FFT.
                NB : if direction is equal to 'C2R', then the transform
                is automatically inverse.
        """
        if direction == 'C2R':
            inverse = True

        if not COMPLEX_utils.isComplex(input):
            raise(TypeError('The input should be complex (e.g. last dimension is 2)'))

        if (not input.is_contiguous()):
            raise (RuntimeError('Tensors must be contiguous!'))

        if direction == 'C2R':
            output = torch.irfft(input, 2, normalized=False, onesided=False)*input.size(-2)*input.size(-3)
        elif direction == 'C2C':
            if inverse:
                #output = torch.ifft(input, 2, normalized=False)*input.size(-2)*input.size(-3)
                output = torch.ifft(input, 2, normalized=False)
            else:
                output = torch.fft(input, 2, normalized=False)

        return output

    @staticmethod
    def Hadamard(A, B, inplace=False):
        """
            Complex pointwise multiplication between (batched) tensor A and tensor B.

            Parameters
            ----------
            A : tensor
                A is a complex tensor of size (B, C, M, N, 2)
            B : tensor
                B is a complex tensor of size (M, N, 2) or real tensor of (M, N, 1)
            inplace : boolean, optional
                if set to True, all the operations are performed inplace

            Returns
            -------
            C : tensor
                output tensor of size (B, C, M, N, 2) such that:
                C[b, c, m, n, :] = A[b, c, m, n, :] * B[m, n, :]
        """
        if not COMPLEX_utils.isComplex(A):
            raise TypeError('The input must be complex, indicated by a last '
                            'dimension of size 2')

        if B.ndimension() != 3:
            raise RuntimeError('The filter must be a 3-tensor, with a last '
                               'dimension of size 1 or 2 to indicate it is real '
                               'or complex, respectively')

        if not COMPLEX_utils.isComplex(B) and not COMPLEX_utils.isReal(B):
            raise TypeError('The filter must be complex or real, indicated by a '
                            'last dimension of size 2 or 1, respectively')

        if A.size()[-3:-1] != B.size()[-3:-1]:
            raise RuntimeError('The filters are not compatible for multiplication!')

        if A.dtype is not B.dtype:
            raise RuntimeError('A and B must be of the same dtype')

        if A.device.type != B.device.type:
            raise RuntimeError('A and B must be of the same device type')

        if A.device.type == 'cuda':
            if A.device.index != B.device.index:
                raise RuntimeError('A and B must be on the same GPU!')

        if COMPLEX_utils.isReal(B):
            if inplace:
                return A.mul_(B)
            else:
                return A * B
        else:
            C = A.new(A.size())

            A_r = A[..., 0].contiguous().view(-1, A.size(-2)*A.size(-3))
            A_i = A[..., 1].contiguous().view(-1, A.size(-2)*A.size(-3))

            B_r = B[...,0].contiguous().view(B.size(-2)*B.size(-3)).unsqueeze(0).expand_as(A_i)
            B_i = B[..., 1].contiguous().view(B.size(-2)*B.size(-3)).unsqueeze(0).expand_as(A_r)

            C[..., 0].view(-1, C.size(-2)*C.size(-3))[:] = A_r * B_r - A_i * B_i
            C[..., 1].view(-1, C.size(-2)*C.size(-3))[:] = A_r * B_i + A_i * B_r

            return C if not inplace else A.copy_(C)