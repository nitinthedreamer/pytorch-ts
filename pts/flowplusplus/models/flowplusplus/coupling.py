import torch.nn as nn

from pts.flowplusplus.models.flowplusplus import log_dist as logistic
from pts.flowplusplus.models.flowplusplus.nn import NN


class Coupling(nn.Module):
    """Mixture-of-Logistics Coupling layer in Flow++

    Args:
        in_channels (int): Number of channels in the input.
        mid_channels (int): Number of channels in the transformation network.
        num_blocks (int): Number of residual blocks in the transformation network.
        num_components (int): Number of components in the mixture.
        drop_prob (float): Dropout probability.
        use_attn (bool): Use attention in the NN blocks.
        aux_channels (int): Number of channels in optional auxiliary input.
    """
    def __init__(self, in_channels, mid_channels, num_blocks, num_components, drop_prob,
                 use_attn=True, aux_channels=None):
        super(Coupling, self).__init__()
        self.nn = NN(in_channels, mid_channels, num_blocks, num_components, drop_prob, use_attn, aux_channels)

    def forward(self, x, sldj=None, reverse=False, aux=None):
        x_change, x_id = x
        a, b, pi, mu, s = self.nn(x_id, aux)

        if reverse:
            out = x_change * a.mul(-1).exp() - b
            out, scale_ldj = logistic.inverse(out, reverse=True)
            out = out.clamp(1e-5, 1. - 1e-5)
            out = logistic.mixture_inv_cdf(out, pi, mu, s)
            logistic_ldj = logistic.mixture_log_pdf(out, pi, mu, s)
            sldj = sldj - (a + scale_ldj + logistic_ldj).flatten(1).sum(-1)
        else:
            out = logistic.mixture_log_cdf(x_change, pi, mu, s).exp()
            out, scale_ldj = logistic.inverse(out)
            out = (out + b) * a.exp()
            logistic_ldj = logistic.mixture_log_pdf(x_change, pi, mu, s)
            sldj = sldj + (logistic_ldj + scale_ldj + a).flatten(1).sum(-1)

        x = (out, x_id)

        return x, sldj
