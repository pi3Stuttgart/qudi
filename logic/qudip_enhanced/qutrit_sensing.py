# coding=utf-8

import numpy as np
import lmfit


def plus_t(x, Azz, x0, mn):
    arg = 2 * Azz * mn * np.pi * (x - x0)
    return 1/9.*(1+2*np.cos(arg))**2

def zero_t(x, Azz, x0, mn):
    arg = 2 * Azz * mn * np.pi * (x - x0)
    return 1/9.*(-1+np.cos(arg) + np.sqrt(3)*np.sin(arg))**2

def minus_t(x, Azz, x0, mn):
    arg = 2 * Azz * mn * np.pi * (x - x0)
    return 4/9.*np.sin(arg/2.)**2*(2+np.cos(arg) + np.sqrt(3)*np.sin(arg))

def ft(x, Azz, x0, mn):
    return np.real(np.array(
        [
            plus_t(x, Azz, x0, mn),
            zero_t(x, Azz, x0, mn),
            minus_t(x, Azz, x0, mn)
        ]
    ))

def decay_matrix(t, t2):
    a = 1- 2/3.*(1-np.exp(-t/t2))
    b = 1/3.*(1-np.exp(-t/t2))
    return np.array(
        [
            [a, b, b],
            [b, a, b],
            [b, b, a]
        ]
    )

def readout_fidelity_matrix(frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm):
    return np.array(
        [
            [frpp, frp0, frpm],
            [fr0p, fr00, fr0m],
            [frmp, frm0, frmm],
        ]
    )

def gate_fidelity_matrix(fg):
    return np.array(
        [
            [fg,           (1-fg)/2., (1-fg)/2.],
            [(1-fg)/2.,    fg,        (1-fg)/2.],
            [(1-fg)/2.,    (1-fg)/2., fg]
        ])


def f(x, Azz, x0, pnv0, fg, frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm, t2, mn):
    """
    NOTE: ALL variables (including x) must be scalars, can probably rewritten to take vectors
    """
    mfid_read = readout_fidelity_matrix(frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm)
    mt2 = decay_matrix(x, t2)
    mfid_gate = gate_fidelity_matrix(fg)
    p0 = ft(x, Azz, x0, mn) #np.array([fdd_t[i][mn](x, Azz, x0) for i in ['+', '0', '-']])
    p1 = np.dot(mfid_gate, p0)
    p2 = np.dot(mt2, p1)
    return np.dot(mfid_read, (1 - pnv0) * p2 + pnv0 * np.array([1, 0, 0]))

def fmn(x, Azz, x0, pnv0, fg, frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm, t2, pmnp):
    return pmnp*f(x, Azz, x0, pnv0, fg, frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm, t2, +1) + (1-pmnp)*f(x, Azz, x0, pnv0, fg, frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm, t2, -1)

def fit_function_qutrit_sensing_concurrent(params, x=None, data_d=None):
    n14_sn = {'+': 0, '0': 1, '-': 2}
    eval_l = []
    resid_l = []
    for xi in x:
        mod = fmn(xi, **params)
        eval_l.append(mod)
    eval_arr = np.array(eval_l)
    for key, val in data_d.items():
        resid_l.append(eval_arr[:, n14_sn[key]] - val)
    return np.concatenate(resid_l)

# class QutritSensingModel(lmfit.Model):
#     def __init__(self,  mn,  n14_state, *args, **kwargs):
#         n14_sn = {'+1': 0, '0': 1, '-1': 2}[n14_state]
#         def the_fun(x, Azz, x0, pnv0, fg, frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm, t2):
#             return [f(xi, Azz, x0, pnv0, fg, frpp, frp0, frpm, fr0p, fr00, fr0m, frmp, frm0, frmm, t2, mn)[n14_sn] for xi in x]
#         super(QutritSensingModel, self).__init__(the_fun, *args, **kwargs)