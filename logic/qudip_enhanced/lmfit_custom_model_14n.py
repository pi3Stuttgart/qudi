import numpy as np
import collections
import lmfit
from .analyze import NVHamFit14nParams


class NVHam14NModel(lmfit.Model):

    def __init__(self, fd, diag=True, *args, **kwargs):
        def calc_transition_frequency(x, magnet_field, gamma_e, gamma_n, qp, hf_para_n, hf_perp_n):
            nvham = NVHamFit14nParams(diag=diag)
            nvham.set_frequency_dict(collections.OrderedDict(fd))
            return nvham.transition_frequencies(
                magnetic_field=magnet_field,
                transition_numbers=np.int32(x),
                gamma={'e': gamma_e, '14n': gamma_n},
                qp={'14n': qp},
                hf_para_n={'14n': hf_para_n},
                hf_perp_n={'14n': hf_perp_n}
            )

        super(NVHam14NModel, self).__init__(calc_transition_frequency, *args, **kwargs)