import numpy as np

from .layers import Layer, ParamMixin
from ..fillers import filler
from ..base import Parameter
import cudarray as ca

class Convolutional(Layer, ParamMixin):
    def __init__(self, n_output, filter_shape, weights, bias=0.0, weight_decay=0.0):
        self.n_output = n_output
        self.filter_shape = filter_shape
        self.weight_filler = filler(weights)
        self.weight_decay = weight_decay
        self.bias_filler = filler(bias)

    def _setup(self, input_shape):
        n_channels = input_shape[1]
        W_shape = (n_channels, self.n_output) + self.filter_shape
        b_shape = self.n_output
        self.W = ca.array(self.weight_filler.array(W_shape), np.float)
        self.b = ca.array(self.bias_filler.array(b_shape), np.float)
        self.W_grad = ca.empty_like(self.W, np.float)
        self.b_grad = ca.empty_like(self.b, np.float)

        if self.weight_decay > 0.0:
            def penalty_fun():
                return -2*self.weight_decay*self.W
        else:
            penalty_fun = None

        self.W_param = Parameter(self.W, gradient=self.W_grad, name='W',
                                 penalty_fun=penalty_fun, monitor=True)
        self.b_param = Parameter(self.b, gradient=self.b_grad, name='b')

    def fprop(self, input, phase):
        self.last_input = input
        self.last_input_shape = input.shape
        print ("calling conv_bc01")
        convout = ca.conv_bc01(input, self.W)
        return convout + self.b[np.newaxis, :, np.newaxis, np.newaxis]

    def bprop(self, Y_grad):
        print("calling  bprop_imgs")
        input_grad = ca.conv_bc01_bprop_imgs(self.W, Y_grad)
        print("calling  conv_bc01_bprop_filters")
        self.W_grad = ca.conv_bc01_bprop_filters(self.last_input, Y_grad)
        print("done")
        n_imgs = Y_grad.shape[0]
        self.b_grad = ca.sum(Y_grad, axis=(0, 2, 3)) / (n_imgs)
        return input_grad

    def params(self):
        return self.W_param, self.b_param

    def output_shape(self, input_shape):
        h = input_shape[2]
        w = input_shape[3]
        shape = (input_shape[0], self.n_output, h, w)
        return shape

class Flatten(Layer):
    def fprop(self, input, phase):
        self.last_input_shape = input.shape
        return np.reshape(input, (input.shape[0], -1))

    def bprop(self, Y_grad):
        return np.reshape(Y_grad, self.last_input_shape)

    def output_shape(self, input_shape):
        return (input_shape[0], np.prod(input_shape[1:]))
