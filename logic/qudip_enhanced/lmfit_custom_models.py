# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import numpy as np
import lmfit.models
import lmfit.lineshapes
import itertools
import scipy
import operator
import copy



def guess_from_peak(model, y, x, negative, ampscale=1.0, sigscale=1.0):
    """Estimate amp, cen, sigma for a peak, create params."""
    if 'intercept' in model.param_names:
        if negative:
            intercept = np.max(y)
        else:
            intercept = np.min(y)
        y -= intercept
    pars = lmfit.models.guess_from_peak(model=model, y=y, x=x, negative=negative, ampscale=ampscale, sigscale=sigscale)
    if 'intercept' in model.param_names:
        pars['intercept'] = lmfit.Parameter(name='intercept', value=intercept)
    if 'slope' in model.param_names:
        pars['slope'] = lmfit.Parameter(name='intercept', value=0.0, vary=False)
    return pars


def cosine_no_decay_no_offset(x, amplitude, T, x0):
    return amplitude * np.cos(2 * np.pi * (x - x0) / float(T))


def cosine_no_decay(x, amplitude, T, x0, c):
    return cosine_no_decay_no_offset(x, amplitude, T, x0) + c


def cosine(x, amplitude, T, x0, c, t2):
    out = cosine_no_decay_no_offset(x, amplitude, T, x0) * np.exp(-(x - x0) / t2) + c
    return out


def abs_cosine(x, amplitude, T, x0, c, t2):
    return np.abs(cosine_no_decay_no_offset(x, amplitude, T, x0) * np.exp(-(x - x0) / t2)) + c


def abs_cosine_minus_amp_half_decay(x, amplitude, T, x0, c, t2, p):
    return (np.abs(cosine_no_decay_no_offset(x, amplitude, T, x0)) - amplitude / 2.) * np.exp(-(x - x0) ** p / t2) + c + amplitude / 2.


def exp_power_decay(x, amplitude, dec, x0, p, c):
    return amplitude * np.exp(-((x-x0) / dec) ** p) + c

def exp_power_decay_pos0(x, amplitude, dec, p, c):
    return amplitude * np.exp(-((x) / dec) ** p) + c


def sinc(x, amplitude, center, rabi_frequency, y0):
    """

    :param x: detuning
    :param amplitude:
    :param x0:
    :param rabi_frequency:
    :param y0:
    :return:
    """
    a = (rabi_frequency ** 2 + (x - center) ** 2)
    return amplitude * rabi_frequency ** 2 / a * np.sin(np.sqrt(a) * np.pi / (2 * rabi_frequency)) ** 2 + y0

class SincModel(lmfit.Model):
    def __init__(self, rabi_frequency=None, vary_rabi_frequency=True, negative=False, *args, **kwargs):
        self.rabi_frequency = rabi_frequency
        self.vary_rabi_frequency = vary_rabi_frequency
        self.negative = negative
        super(SincModel, self).__init__(sinc, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        data = copy.deepcopy(data)
        mod = lmfit.models.LorentzianModel() + lmfit.models.LinearModel()
        result = mod.fit(data=data, x=x, params=guess_from_peak(model=mod, y=data, x=x, negative=self.negative, **kwargs))
        center = result.params['center'].value
        y0 = result.params['intercept'].value
        amplitude = -(y0 - data.min())

        rabi_frequency = result.params['fwhm'].value if self.rabi_frequency is None else self.rabi_frequency
        pars = lmfit.models.update_param_vals(self.make_params(center=center, y0=y0, amplitude=amplitude, rabi_frequency=rabi_frequency), self.prefix, **kwargs)
        pars['rabi_frequency'].vary = self.vary_rabi_frequency
        return pars


class TripleSincHfModel(lmfit.Model):
    def __init__(self, hf, rabi_frequency, sweep_guess=False, *args, **kwargs):
        self.hf = hf
        self.rabi_frequency = rabi_frequency
        self.sweep_guess = sweep_guess

        def triple_sinc_hf(x, amplitude, center, y0):
            hf = self.hf
            s0 = sinc(x, .5 * amplitude, center - hf, self.rabi_frequency, y0)
            s1 = sinc(x, amplitude, center, self.rabi_frequency, y0)
            s2 = sinc(x, .5 * amplitude, center + hf, self.rabi_frequency, y0)
            return (s0 + s1 + s2) / 3.

        super(TripleSincHfModel, self).__init__(triple_sinc_hf, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        center = x[data.argmin()]
        y0 = data.max()
        amplitude = -(y0 - data.min())
        return lmfit.models.update_param_vals(self.make_params(center=center, y0=y0, amplitude=amplitude), self.prefix, **kwargs)


# def double_gaussian(x, amplitude_1, amplitude_2, center_1, center_2, sigma_1, sigma_2, c):
#     return amplitude_1 * np.exp(-0.5 * ((x - center_1) / sigma_1) ** 2) + amplitude_2 * np.exp(-0.5 * ((x - center_2) / sigma_2) ** 2) + c
# def guess_from_peak(y, x, negative, ampscale=1.0, sigscale=1.0):
#     """Estimate amp, cen, sigma for a peak, create params."""
#     if x is None:
#         return 1.0, 0.0, 1.0
#     maxy, miny = max(y), min(y)
#     maxx, minx = max(x), min(x)
#     imaxy = lmfit.models.index_of(y, maxy)
#     cen = x[imaxy]
#     amp = (maxy - miny)*3.0
#     sig = (maxx-minx)/6.0
#
#     halfmax_vals = np.where(y > (maxy+miny)/2.0)[0]
#     if negative:
#         # imaxy = lmfit.models.index_of(y, miny)
#         amp = -(maxy - miny)*3.0
#         halfmax_vals = np.where(y < (maxy+miny)/2.0)[0]
#     if len(halfmax_vals) > 2:
#         sig = (x[halfmax_vals[-1]] - x[halfmax_vals[0]])/2.0
#         cen = x[halfmax_vals].mean()
#     amp = amp*sig*ampscale
#     sig = sig*sigscale
#     return amp, cen, sig

class LorentzianModel(lmfit.CompositeModel):

    def __init__(self, left=lmfit.models.LorentzianModel(), right=lmfit.models.LinearModel(), negative=False):
        super(LorentzianModel, self).__init__(left=left, right=right, op=operator.add)
        self.negative = negative

    def guess(self, data, x=None, **kwargs):
        return lmfit.models.update_param_vals(guess_from_peak(model=self, y=data, x=x, negative=self.negative, **kwargs), self.prefix, **kwargs)

class LorentzModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        def Lorentzian_neg(x, center, g, a, c):
            """Lorentzian centered at x0, with amplitude a, offset y0 and HWHM g."""
            return -abs(a) / np.pi * (abs(g) / ((x - center) ** 2 + g ** 2)) + c

        super(LorentzModel, self).__init__(Lorentzian_neg, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        x = np.array(x)
        data = np.array(data)

        def LorentzianEstimator_neg(y=None, x=None):
            c = scipy.mean(y)
            yp = np.array(y - c)
            c = scipy.mean(c + abs(yp))
            yp = y - c
            Y = np.sum(yp) * (x[-1] - x[0]) / len(x)
            y0 = yp.min()
            center = x[y.argmin()]
            g = Y / (np.pi * y0)
            a = y0 * np.pi * g
            return center, g, a, c

        center, g, a, c = LorentzianEstimator_neg(y=data, x=x)
        return lmfit.models.update_param_vals(self.make_params(center=center, g=g, a=a, c=c), self.prefix, **kwargs)


class TripLorentzModel(lmfit.Model):
    def __init__(self, splitting, *args, **kwargs):
        self.splitting = np.abs(splitting)

        def trip_lorentz(x, center, g, a1, a2, a3, c):
            """Lorentzian centered at x0, with amplitude a, offset y0 and HWHM g."""
            x2 = center - self.splitting
            x3 = center + self.splitting
            return -abs(a1) / np.pi * (g ** 2 / ((x - center) ** 2 + g ** 2)) - abs(a2) / np.pi * (g ** 2 / ((x - x2) ** 2 + g ** 2)) - abs(a3) / np.pi * (g ** 2 / ((x - x3) ** 2 + g ** 2)) + c

        super(TripLorentzModel, self).__init__(trip_lorentz, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        def trip_lorentz_estimator(y=None, x=None):
            dx = abs(x[1] - x[0])
            split_index1 = int(np.floor(self.splitting / dx))
            split_index2 = min(int(np.floor(self.splitting * 2. / dx)), len(y) - 1)
            trip_mean = []
            for i in range(len(y) - split_index2):
                trip_mean.append((y[i] + y[i + split_index1] + y[i + split_index2]) / 3.)
            trip_mean = np.array(trip_mean)
            c = trip_mean.max()
            center = x[trip_mean.argmin()] + self.splitting
            g = self.splitting / 4.
            a1 = a2 = a3 = (trip_mean.min() - c) * np.pi
            return center, g, a1, a2, a3, c

        center, g, a1, a2, a3, c = trip_lorentz_estimator(y=data, x=x)
        return lmfit.models.update_param_vals(self.make_params(center=center, g=g, a1=a1, a2=a2, a3=a3, c=c), self.prefix, **kwargs)


# class DoubleGaussianModel(lmfit.Model):
#     def __init__(self, *args, **kwargs):
#
#         super(DoubleGaussianModel, self).__init__(double_gaussian, *args, **kwargs)
#
#     def guess(self, data, x=None, negative=False, **kwargs):
#         def DoubleGaussianEstimator(x=None, y=None):
#             # c = y[0]
#             # y = y-c
#             c = 0.45
#             center = (x * y).sum() / y.sum()
#             ylow = y[x < center]
#             yhigh = y[x > center]
#             a1, cen1, sig1 = guess_from_peak(y[x < center], x=x[x < center], negative=negative)
#             a2, cen2, sig2 = guess_from_peak(y[x > center], x=x[x > center], negative=negative)
#             print(a1, a2, cen1, cen2, sig1, sig2)
#             # x01 = x[ylow.argmax()]
#             # x02 = x[len(ylow) + yhigh.argmax()]
#             # a1 = ylow.max()
#             # a2 = yhigh.max()
#             # w1 = w2 = np.abs((center+0j) ** 0.5)
#             return a1, a2, cen1, cen2, sig1, sig2, c
#
#         amplitude_1, amplitude_2, center_1, center_2, sigma_1, sigma_2, c = DoubleGaussianEstimator(x=x, y=data)
#         return lmfit.models.update_param_vals(self.make_params(amplitude_1=amplitude_1, amplitude_2=amplitude_2, center_1=center_1, center_2=center_2, sigma_1=sigma_1, sigma_2=sigma_2, c=c), self.prefix, **kwargs)

class CosineNoOffsetNoDecayModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        super(CosineNoOffsetNoDecayModel, self).__init__(cosine_no_decay_no_offset, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        def CosineNoOffsetNoDecayEstimator(y=None, x=None):
            y = np.array(y)
            x = np.array(x)
            a = 2 ** 0.5 * np.sqrt((y ** 2).sum())
            # better to do estimation of period from
            Y = np.fft.fft(y)
            N = len(Y)
            D = float(x[1] - x[0])
            i = abs(Y[1:int(N / 2 + 1)]).argmax() + 1
            T = (N * D) / i
            x0 = 0
            return a, T, x0

        amplitude, T, x0 = CosineNoOffsetNoDecayEstimator(y=data, x=x)
        if amplitude < 0:
            amplitude *= -1
            x0 = ((x0 / T + 0.5) % 1) * T
        return lmfit.models.update_param_vals(self.make_params(amplitude=amplitude, T=T, x0=x0), self.prefix, **kwargs)


class ExpDecayModel(lmfit.Model):

    def __init__(self, *args, **kwargs):
        super(ExpDecayModel, self).__init__(exp_decay, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        def exp_decay_estimator(y=None, x=None):
            c = y[-1]
            amplitude = y[0] - c
            t1 = x[-1] / 5.
            return amplitude, t1, c

        amplitude, t1, c = exp_decay_estimator(y=data, x=x)

        return lmfit.models.update_param_vals(self.make_params(amplitude=amplitude, t1=t1, c=c), self.prefix, **kwargs)


class ExpPowerDecayModel(lmfit.Model):

    def __init__(self, *args, **kwargs):
        #super(ExpPowerDecayModel, self).__init__(exp_power_decay, *args, **kwargs)
        super(ExpPowerDecayModel, self).__init__(exp_power_decay, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        def exp_decay_estimator(y=None, x=None):
            c = y[-1]
            amplitude = y[0] - c
            dec = x[-1] / 5.
            return amplitude, dec, c

        amplitude, dec, c = exp_decay_estimator(y=data, x=x)


        return lmfit.models.update_param_vals(self.make_params(amplitude=amplitude, dec=dec, x0=0, p=1, c=c), self.prefix, **kwargs)

class CosineNoOffsetNoDecayModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        super(CosineNoOffsetNoDecayModel, self).__init__(cosine_no_decay_no_offset, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        def CosineNoOffsetNoDecayEstimator(y=None, x=None):
            a = 2 ** 0.5 * np.sqrt((y ** 2).sum())
            # better to do estimation of period from
            Y = np.fft.fft(y)
            N = len(Y)
            D = float(x[1] - x[0])
            i = abs(Y[1:int(N / 2 + 1)]).argmax() + 1
            T = (N * D) / i
            x0 = 0
            return a, T, x0

        amplitude, T, x0 = CosineNoOffsetNoDecayEstimator(y=data, x=x)
        if amplitude < 0:
            amplitude *= -1
            x0 = ((x0 / T + 0.5) % 1) * T
        return lmfit.models.update_param_vals(self.make_params(amplitude=amplitude, T=T, x0=x0), self.prefix, **kwargs)


class CosineNoDecayModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        super(CosineNoDecayModel, self).__init__(cosine_no_decay, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        c = data.mean()
        y_temp = data - c
        m = CosineNoOffsetNoDecayModel()
        p = m.fit(y_temp, m.guess(data=y_temp, x=x), x=x).result.params
        if p['amplitude'] < 0:
            p['amplitude'].value *= -1
            p['x0'].value = ((p['x0'] / p['T'] + 0.5) % 1) * p['T']
            p = m.fit(y_temp, m.guess(data=y_temp, x=x), x=x).result.params
        return lmfit.models.update_param_vals(self.make_params(amplitude=p['amplitude'].value, T=p['T'].value, x0=p['x0'].value, c=c), self.prefix, **kwargs)


class AbsCosineModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        super(AbsCosineModel, self).__init__(abs_cosine, *args, **kwargs)


class AbsCosineMinusAmpHalfDecayModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        super(AbsCosineMinusAmpHalfDecayModel, self).__init__(abs_cosine_minus_amp_half_decay, *args, **kwargs)


class CosineModel(lmfit.Model):
    def __init__(self, *args, **kwargs):
        super(CosineModel, self).__init__(cosine, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        p = CosineNoDecayModel().guess(data, x=x)
        if p['amplitude'] < 0:
            p['amplitude'].value *= -1
            p['x0'].value = ((p['x0'] / p['T'] + 0.5) % 1) * p['T']
        return lmfit.models.update_param_vals(self.make_params(amplitude=p['amplitude'].value, T=p['T'].value, x0=p['x0'].value, c=p['c'].value, t2=10 * (max(np.abs(x)) - min(np.abs(x)))), self.prefix, **kwargs)


class CosineMultiDetModel(lmfit.Model):
    def __init__(self, hyperfine_list, *args, **kwargs):
        self.hyperfine_list = hyperfine_list

        def cosine_multi_det_lmfit(x, amplitude, T, x0, c, t2, f0):
            hfsl = [[+self.hyperfine_list[0], 0.0, -self.hyperfine_list[0]]]
            for hf in self.hyperfine_list[1:]:
                hfsl.append([-hf / 2., hf / 2.])
            delta_l = [sum(i) for i in itertools.product(*hfsl)]
            rabi_0 = 1 / float(T)

            def rabi(delta, x):
                rabi_eff = np.sqrt(rabi_0 ** 2 + delta ** 2)
                A = rabi_0 ** 2 / (rabi_0 ** 2 + delta ** 2)
                return A * np.cos(2 * np.pi * rabi_eff * (x - x0)) * np.exp(-(x - x0) / t2)

            return amplitude * sum(rabi(d - f0, x) for d in delta_l) + c

        super(CosineMultiDetModel, self).__init__(cosine_multi_det_lmfit, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        p = CosineModel().guess(data, x=x)
        return lmfit.models.update_param_vals(self.make_params(amplitude=p['amplitude'].value, T=p['T'].value, x0=p['x0'].value, c=p['c'].value, t2=p['t2'].value, f0=0.0), self.prefix, **kwargs)


#     y_offset = self.results.mean()
#     x = self.tau
#     y = self.results - y_offset
#     try:
#         p = pi3d.Fit.Fit(x, y, pi3d.Fit.CosinusNoOffset, pi3d.Fit.CosinusNoOffsetEstimator)
#     except:
#         return None
#     if p[0] < 0:
#         p[0] = -p[0]
#         p[2] = ((p[2] / p[1] + 0.5) % 1) * p[1]
#         p = pi3d.Fit.Fit(x, y, pi3d.Fit.CosinusNoOffset, p)
#     p = (p[0], p[1], p[2], y_offset)
#     p = pi3d.Fit.Fit(x, self.results, pi3d.Fit.Cosinus, p)
#     while (p[2] > 0.5 * p[1]):
#         p[2] -= p[1]
#     p = pi3d.Fit.Fit(x, self.results, pi3d.Fit.Cosinus, p)
#     p = list(p)
#     p.append(10 * max(x))
#     p = pi3d.Fit.Fit(x, self.results, pi3d.Fit.Cosinus_dec, p)
#     pp = list(p)
#     pp.append(self.centerfreq)
#     import Fitmodule
#
#     d = dict(zip(['a', 'T', 'x0', 'c', 't2', 'f0'], pp))
#     fitresult, fitparams = Fitmodule.Fit(x, self.results, pi3d.Fit.CosineMultiDetLmFit, d)
#     self.rabi_contrast = 200 * fitparams['a'] / fitparams['c']
#     self.rabi_period = fitparams['T'] * 1e3
#     self.rabi_decay = fitparams['t2']
#     self.rabi_offset = fitparams['x0'] * 1e3
#     self.plot_results_data.set_data('fit', fitresult)
# self.plot_results.plot(('x', 'fit'), style='line', color='red')
# self.plot_results.request_redraw()


if __name__ == '__main__':
    fp = "D:\data/NuclearOPs\CNOT_KDD\cnot_kdd/20170411-h13m43s31_cnot_kdd/20170411-h14m04s25_kdd_data.hdf"

    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    import os
    import lmfit

    data = pd.read_hdf(fp)

    d = data.groupby(['seq_num', 'x']).agg({'result_0': np.mean}).reset_index([0, 1])
    aggd = d.pivot(columns='seq_num', index='x')
    fig, ax = plt.subplots()
    aggd.plot(ax=ax, legend=False)
    ax.set_title("Rabi_oscillations (x-axis scaling wrong)")

    mod = CosineModel()
    y = np.array(d[d.seq_num == int(0)].result_0)
    x = aggd.index.values
    pars = mod.guess(data=y, x=x)
    pars['T'].value = 2 * np.pi
    pars['T'].vary = False
    result = mod.fit(y, pars, x=x)
    plt.plot(x, result.best_fit)
    plt.title("Fit of rabi_oscillations (x-axis scaling right)")
    a = np.array([0, result.params['T'].value, result.params['x0'].value])
