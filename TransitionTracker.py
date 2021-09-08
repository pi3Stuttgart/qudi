# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type
import warnings
import datetime
import time
import shutil
import misc
from numbers import Number
import scipy.interpolate
import scipy.optimize
from qutip_enhanced.nv_hamilton import NVHam
from qutip_enhanced import sort_eigenvalues_standard_basis
from qutip_enhanced.analyze import flipped_spin_numbers, single_quantum_transitions_non_hf_spins, get_transition_frequency
import qutip_enhanced.lmfit_models
from itertools import product
import numpy as np
import pandas as pd
import os
from pi3diamond import pi3d
import collections
import matplotlib.pyplot as plt
import logging

from PyQt5.QtWidgets import QTableWidgetItem, QMainWindow
from PyQt5.QtCore import pyqtSignal
from qtgui import transition_tracker_gui
from PyQt5.uic import compileUi

from qutip import *
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import minimize



def recompile_ui_file():
    fold = "{}/qtgui".format(os.path.dirname(__file__))
    name = "transition_tracker"
    uipath = r"{}/{}.ui".format(fold, name)
    pypath = r"{}/{}_gui.py".format(fold, name)
    with open(pypath, 'w') as f:
        compileUi(uipath, f)
    reload(transition_tracker_gui)

class RabiParametersStatic:
    def __init__(self, filepath, transition_name=None):
        self.filepath = filepath
        self.transition_name = transition_name

    @property
    def filename(self):
        return os.path.splitext(os.path.basename(self.filepath))[0]

    def __deepcopy__(self, memo):
        return self

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, val):
        if hasattr(self, '_filepath'):
            raise Exception('The filepath must not be be set after instantiation.')
        elif not isinstance(val, str):
            raise Exception('filepath must be string')
        else:
            self._filepath = val
            self.set_data_array()

    def read_file_data(self, fp=None):
        fp = self.filepath if fp is None else fp
        return np.genfromtxt(fp, dtype=str, delimiter='\t')

    def update_file(self, data):
        self.archive_file()
        data.to_csv(self.filepath, "\t", index=False)
        self.set_data_array()

    def generate_linear_file(self, maxfreq_l):
        if type(maxfreq_l) is float:
            maxfreq_l = [maxfreq_l]
        import AWG_M8190A_Elements as E
        n = 11
        arr = np.array(
            list(
                product(
                    *([map(lambda x: "{:.6f}".format(x), E.round_to_amplitude_granularity(np.linspace(0., 1., n)))] * len(maxfreq_l))
                )
            )
        )
        arr = [np.insert(arr, [len(maxfreq_l)], str(idx), axis=1) for idx, item in enumerate(maxfreq_l)]
        arr = [np.hstack([item, o * item[:, idx].astype(float).reshape(-1, 1)]) for idx, (item, o) in enumerate(zip(arr, maxfreq_l))]
        arr = np.vstack(arr)
        arr = np.insert(arr, [len(maxfreq_l) + 2], pd.to_datetime('now').__str__(), axis=1)
        d = collections.OrderedDict()
        for key, val in zip(["amp{}".format(i) for i in range(len(maxfreq_l))] + ['transition', 'omega', 'date'], arr.T):
            d[key] = val
        self.update_file(pd.DataFrame.from_dict(d))

    def replace_data(self):
        pass

    def archive_file(self):
        filename = os.path.splitext(os.path.basename(self.filepath))[0]
        fil = r'D:\Python\pi3diamond\log\transition_tracker_log\rabi_parameters_archive\{}'.format(filename)
        date = datetime.datetime.fromtimestamp(os.path.getmtime(self.filepath)).strftime('%Y%m%dh%Hm%Ms%S')
        if not os.path.isdir(fil):
            os.mkdir(fil)
        shutil.copy(self.filepath, r'D:\Python\pi3diamond\log\transition_tracker_log\rabi_parameters_archive\{}\{}-{}_{}.dat'.format(filename, date, pi3d.nowstr, filename))

    def file_header(self, tnf):
        return ["amp{}".format(i) for i in range(tnf)] + ['transition', 'omega', 'date']

    def data_dataframe(self, fp=None):
        fp = self.filepath if fp is None else fp
        fd = self.read_file_data(fp=fp)
        self.tnf = len([i for i in list(fd[0]) if 'amp' in i])
        ecn = self.file_header(self.tnf)
        cn = list(fd[0])
        if cn != ecn:
            raise Exception('File column names not allowed. expected {}, found{}'.format(ecn, cn))
        return pd.DataFrame(data=fd[1:, :], columns=fd[0, :])

    def set_data_array(self):
        out = self.data_dataframe().values
        if '' in out:
            raise Exception("Error while loading file '{}'".format(self.filepath))
        else:
            self.data_array = out

    @property
    def amp_rabi_freq(self):
        nonlinear_params = np.delete(self.data_array, [self.tnf, self.data_array.shape[1] - 1], axis=1)
        val = np.array(nonlinear_params[:, :self.tnf], dtype=float), np.array(nonlinear_params[:, self.tnf:2 * self.tnf], dtype=float)
        if self.tnf == 1:
            val = tuple([np.squeeze(i, 1) for i in val])
        return val

    def calc_omegas(self, amplitude):
        amp, rabi_freq = self.amp_rabi_freq
        return np.array(scipy.interpolate.griddata(amp, rabi_freq, amplitude, method='linear'))

    def calc_amplitudes(self, omega):
        amp, rabi_freq = self.amp_rabi_freq
        return np.array(scipy.interpolate.griddata(rabi_freq, amp, omega, method='linear'))

    def amplitude(self, **kwargs):
        key, val, tni = self.parse(**kwargs)
        if 'amplitude' in kwargs:
            val = kwargs['amplitude']
        else:
            val = self.calc_amplitudes(self.omega(**kwargs))
        self.check_amplitudes(val, **kwargs)
        return self.deparse(tni, val)

    def check_amplitudes(self, val, **kwargs):
        try:
            anynan = np.any(np.isnan(val))
        except:
            try:
                isstr = np.array(val).dtype.kind == str
            except:
                raise Exception('The given ampitudes {} neither could be tested for np.nan nor are they some kind of string type: {}'.format(val, type(val)))
            if not isstr:
                raise Exception('I DONT KNOW WHATS GOING ON .Amplitudes: {}, kwargs: {}'.format(val, kwargs))
        if anynan:
            raise Exception('For at least one of given parameters, no valid amplitude could be obtained which resulted in the value NaN. Amplitudes: {}, kwargs: {}'.format(val, kwargs))

    def omega(self, **kwargs):
        key, val, tni = self.parse(**kwargs)
        fd = {'omega': (lambda x: x),
              'period': (lambda x: 1. / x),
              'pi': (lambda x: .5 / x),
              'pi2': (lambda x: .25 / x),
              'amplitude': (lambda x: self.calc_omegas(amplitude=self.amplitude(amplitude=x)))}
        return self.deparse(tni, fd[key](val))

    def period(self, **kwargs):
        return 1. / self.omega(**kwargs)

    def pi(self, **kwargs):
        return 0.5 / self.omega(**kwargs)

    def pi2(self, **kwargs):
        return 0.25 / self.omega(**kwargs)

    def is_valid_input(self, val):
        ctnf1shape1 = self.tnf == 1 and len(val.shape) == 1
        ctnf1shape2 = self.tnf == 1 and len(val.shape) == 2 and val.shape[1] == 1
        ctnf2shape1 = self.tnf == 2 and len(val.shape) == 2 and val.shape[1] == 2
        if ctnf1shape1 or ctnf1shape2 or ctnf2shape1:
            return val
        else:
            raise ValueError('Combination is not allowed: val.shape: {}, tnf: {}'.format(val.shape, self.tnf))

    def parse(self, **kwargs):
        tni, kwargs = self.pop_tni(**kwargs)
        key, val = kwargs.items()[0]
        val = np.array(val)
        if len(val.shape) > 2:
            raise Exception('Arrays must be 1D or 2D. Given shape is {}'.format(val.shape))
        elif len(val.shape) == 2:
            if val.shape[1] > self.tnf:
                raise ValueError(
                    'Too many columns. Maybe you need to transpose the input matrix? The input matrix has shape {} but'
                    ' the input rabi file includes only {} transition(s).'.format(val.shape, self.tnf))
            if val.shape[1] > len(tni):
                raise ValueError('variable tni assumes maximally {} columns in input value. Found {}'.format(len(tni), val.shape[1]))
            out = np.zeros([val.shape[0], self.tnf])
            for i, vali in enumerate(tni):
                out[:, vali] = val[:, i]
            val = out
        elif len(val.shape) == 1:
            if self.tnf != 1:
                raise ValueError('Input can only be 1D, if file contains one single transition')
        elif len(val.shape) == 0:
            raise Exception('Arrays must be 1D or 2D. Given shape is {}'.format(val.shape))
        self.is_valid_input(val)
        return key, val, tni

    def deparse(self, tni, val):
        if len(val.shape) == 2:
            val = val[:, tni]
        return val

    def pop_tni(self, **kwargs):
        if len(kwargs) == 2:
            tni = kwargs.pop('tni')
        elif len(kwargs) == 1:
            tni = None
        elif len(kwargs) == 0:
            if len(kwargs) != 1:
                raise ValueError('Not allowed')
        if tni is None:
            tni = np.arange(self.tnf)
        tni = np.array(tni)


        if len(tni.shape) != 1:
            raise Exception("shape of 'transition_number' must be 1D (list or np.ndarray)")
        if (tni >= 0).all() and (tni < self.tnf).all():
            return tni, kwargs
        else:
            raise ValueError('Something is wrong either with the given value for tni. val: {}, tnf: {}'.format(tni, self.tnf))

    def plot(self, **kwargs):
        sample_amp = np.linspace(0.01, 1., 100)
        mino = 0.
        maxo = self.omega(amplitude=[1.0])[0]
        sample_omega = np.linspace(mino, maxo, 100)
        arf, orf = self.amp_rabi_freq
        eorf = self.omega(amplitude=sample_amp)
        earf = self.amplitude(omega=sample_omega)
        if len(kwargs) == 0:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(1, 2)
            ax0 = ax[0]
            ax1 = ax[1]
            fig.canvas.set_window_title(self.transition_name)
            fig.suptitle(self.filename)
        elif len(kwargs) == 2:
            ax0 = kwargs['ax0']
            ax1 = kwargs['ax1']
        else:
            raise Exception('Error: {}'.format(kwargs))
        ax0.set_title("{}, {}".format(self.filename, self.transition_name))
        ax0.set_xlabel('rabi frequency [MHz]')
        ax0.set_ylabel('amplitude [a.u.]')
        ax1.set_xlabel('amplitude [a.u.]')
        ax1.set_ylabel('rabi frequency [MHz]')
        ax1.set_title("{}, {}".format(self.filename, self.transition_name))
        ax0.plot(orf, arf, 'o', sample_omega, earf, '-')
        ax1.plot(arf, orf, 'o', sample_amp, eorf, '-')
        if len(kwargs) == 0:
            plt.show()

class RabiParametersSingle(object):
    def __init__(self, rp, tni=None, **kwargs):
        self.rp = rp #rabi parameters
        self.is_valid_input(**kwargs)
        self.set_statics(tni=tni, **kwargs)

    def set_statics(self, tni=None, round_to_full_sample=True, **kwargs):
        key, val = kwargs.items()[0]
        val = np.array(val)
        zero_d_input = False
        if len(val.shape) == 0:
            zero_d_input = True
            val = np.array([val])
            if self.rp.tnf == 2:
                val = np.array([val])
        elif len(val.shape) == 1:
            if self.rp.tnf == 2:
                val = np.array([val])
        if key == 'amp':
            kwargs = {'amplitude': val}
        else:
            kwargs[key] = val
        amp = getattr(self.rp, 'amplitude')(tni=tni, **kwargs)
        omega = getattr(self.rp, 'omega')(tni=tni, **kwargs)
        if zero_d_input:
            amp = amp[0]
            omega = omega[0]
            if self.rp.tnf == 2:
                amp = amp[0]
                omega = omega[0]
        else:
            if self.rp.tnf == 2:
                amp = amp[0]
                omega = omega[0]
        self.amp = amp
        if round_to_full_sample:
            self.period = np.around(12e3 / (omega)) / 12e3
            self.omega = 1 / self.period
            self.pi = np.around(12e3 / (2 * omega)) / 12e3
            self.pi2 = np.around(12e3 / (4 * omega)) / 12e3
        elif not round_to_full_sample:
            self.period = 1. / omega
            self.omega = omega
            self.pi = 0.5 / omega
            self.pi2 = 0.25 / omega

    def is_valid_input(self, **kwargs):
        if len(kwargs) != 1:
            raise ValueError('Exactly one input must be given. (Instead of {})'.format(len(kwargs)))
        val = np.array(kwargs.values()[0])
        if len(val.shape) not in [0, 1]:
            raise ValueError('Input value must be 0D or 1D but was {}'.format(len(val.shape)))
        if len(val.shape) == 1 and val.shape[0] > self.rp.tnf:
            raise ValueError('Input value is too large for given rabi file. ({}, tnf: {}'.format(val.shape[0], self.rp.tnf))
        if kwargs.keys()[0] not in ['amp', 'omega', 'period']:
            raise Exception("input parameter names must be in ['amp', 'omega', 'period'], but {} was given".format(kwargs.keys()[0]))
        return kwargs

class Transition:
    def __init__(self, name, parent=None, current_frequency=None):
        self.parent = parent
        if current_frequency is not None:
            self.current_frequency = current_frequency
        self.name = name
        self.set_meta()

    name = misc.ret_property_typecheck('name', str)
    ms_state = misc.ret_property_list_element('ms_state', [+1, 0, -1])
    spin_type = misc.ret_property_list_element('spin_type', ['14n', '13c'])
    current_frequency = misc.ret_property_typecheck('current_frequency', Number)

    @property
    def start_level(self):
        return np.argwhere(np.array(self.angular_momentum_arr)==self.start_angular_momentum)[0,0]

    @property
    def end_level(self):
        return np.argwhere(np.array(self.angular_momentum_arr)==self.end_angular_momentum)[0,0]

    @property
    def angular_momentum_arr(self):
        if self.spin_type == '14n':
            return np.array([+1, 0, -1])
        else:
            return np.array([.5, -.5])

    def set_meta(self):
        name = TransitionTracker.correct_transition_name(self.name)
        self.nuc, ms = name.split(' ')
        self.ms_state = int(ms[2:])
        self.spin_type = '14n' if '14n' in self.nuc else '13c'
        if self.spin_type == '14n':
            self.start_angular_momentum, self.end_angular_momentum = sorted([0, int(self.nuc[-2:])])
        else:
            self.start_angular_momentum = -.5
            self.end_angular_momentum = +.5

class TransitionTracker(QMainWindow, transition_tracker_gui.Ui_window):
    c13_list = []#['13c414', '13c90', '13c13', '13c6', '13c-5', '13c-6']

    transitions = misc.ret_property_array_like_typ('transitions', Transition)
    log_folder = r"D:\Python\pi3diamond\log\transition_tracker_log"

    g_factors = {'e': -2.0028 * 1.6021766208e-19 / (4 * np.pi * 9.10938356e-31) * 1e-6}

    def __init__(self, title='TransitionTracker', parent=None):
        super(TransitionTracker, self).__init__()
        self.setupUi(self)
        self.connect_signals()
        title = '' if title is None else title
        self.setWindowTitle(title)
        self.reload_nuclear_parameters()
        self.mw_mixing_frequency = pi3d.get_last_value_from_file('mw_mixing_frequency')
        self.mw_mixing_frequency_p1 = pi3d.get_last_value_from_file('mw_mixing_frequency_p1')
        self.ple_Ex = pi3d.get_last_value_from_file('ple_Ex')
        self.ple_A1 = pi3d.get_last_value_from_file('ple_A1')


        #self.xyz = pi3d.get_last_values_from_file('xyz')
        self.current_local_oscillator_freq = pi3d.get_last_value_from_file('current_local_oscillator_freq')
        self.zero_field_splitting = pi3d.get_last_value_from_file('zfs')
        self.transition_name_list = [['+1', '0', '-1'], ['+1', '0', '-1']] + [['+0.5', '-0.5']]*len(self.c13_list)
        self.states_list = [range(len(i)) for i in self.transition_name_list]
        self.spin_name_list = ['e', '14n'] + self.c13_list
        self.set_h_diag()
        self.set_ntd()
        self.load_transitions()
        self.load_rabi_parameters()
        self.update_stuff()

    update_tt_nuclear_gui = pyqtSignal()
    update_tt_electron_gui = pyqtSignal()

    def connect_signals(self):
        self.update_tt_nuclear_gui.connect(self.update_gui_nuclear)
        self.update_tt_electron_gui.connect(self.update_gui_electron)

    def nuclear_transition_name(self, transition):
        ms = self.transition_name_list[0][transition[0][0]]
        fsn = flipped_spin_numbers(transition)[0]
        nuc = self.spin_name_list[fsn]
        if ms == '0' and '13c' in nuc:
            return '13c ms0'
        else:
            if fsn == 1:
                if transition[0][1] == 0: #initial transition is '+1'
                    mn = '+1'
                elif transition[1][1] == 2: #initial transition is '0'
                    mn = '-1'
                nuc += mn
            return "{} ms{}".format(nuc, ms)

    def set_ntd(self):
        ntd = {}
        c13ms0_added = False
        for t in single_quantum_transitions_non_hf_spins(self.states_list, hf_spin_list=[0]):
            name = self.nuclear_transition_name(t)
            if name == '13c ms0':
                if c13ms0_added:
                    continue
                else:
                    c13ms0_added = True
            ntd[name] = t
        self.ntd = ntd

    def reload_nuclear_parameters(self):
        self.g_factors['13c'] = pi3d.get_last_values_from_file(filename='gamma_13c.dat', full_path=r"{}\gamma_13c.dat".format(self.log_folder))[0]
        self.g_factors['14n'] = pi3d.get_last_values_from_file(filename='gamma_14n.dat', full_path=r"{}\gamma_14n.dat".format(self.log_folder))[0]
        self.qp = {'14n': pi3d.get_last_values_from_file(filename='qp_14n.dat', full_path=r"{}\qp_14n.dat".format(self.log_folder))[0]}
        self.hf_para_n = {'14n': pi3d.get_last_values_from_file(filename='hf_14n.dat', full_path=r"{}\hf_14n.dat".format(self.log_folder))[0]}
        self.hf_perp_n = {'14n': pi3d.get_last_values_from_file(filename='hf_perp_14n.dat', full_path=r"{}\hf_perp_14n.dat".format(self.log_folder))[0]}
        self.hf_para_n.update(dict([(key, pi3d.get_last_values_from_file(filename='hf_1{}.dat'.format(key), full_path=r"{}\hf_{}.dat".format(self.log_folder, key))[0]) for key in self.c13_list]))

    def set_h_diag(self):
        self.nvham = NVHam(magnet_field={'z': self.current_magnetic_field},
                           n_type='14n', nitrogen_levels=[0, 1, 2],
                           electron_levels=[0, 1, 2], gamma=self.g_factors,
                           qp=self.qp, hf_para_n=self.hf_para_n,
                           hf_perp_n=self.hf_perp_n)
        for c13 in self.c13_list:
            self.nvham.add_spin(np.matrix(np.diag([0.0, 0.0, self.hf_para_n[c13]])), self.nvham.h_13c(), [0, 1])
        eval_evec = self.nvham.h_nv.eigenstates()
        # *np.linalg.eig(self.nvham.h_nv.data.todense())[::-1]
        self.h_diag = sort_eigenvalues_standard_basis(self.nvham.dims, eval_evec[1], eval_evec[0])

    def load_transitions(self):
        self.transitions = []
        for key, val in self.ntd.items():
            self.transitions.append(
                Transition(
                    parent=self,
                    name=key,
                    current_frequency=-get_transition_frequency(h_diag=self.h_diag, dims=self.nvham.dims, transition=val)
                )
            )

    def update_current_frequencies(self):
        for key, val in self.ntd.items():
            self.transition(key).current_frequency = -get_transition_frequency(h_diag=self.h_diag, dims=self.nvham.dims, transition=val)
        self.update_tt_nuclear_gui.emit()

    def load_rabi_parameters(self):
        self.rabi_parameters = dict()
        for f in os.listdir(self.log_folder):
            if 'e_rabi_ou{:.0f}deg'.format(1000*pi3d.mcas_dict.awgs['2g'].ch[1].output_amplitude) in f:
                if len(f.split('.')) > 2:
                    raise Exception('Error: floating point values or any other reason to have points in the filename other than for the file extension may not a good idea. {}'.format(f))
                self.rabi_parameters[f.split('.')[0]] = RabiParametersStatic(filepath=os.path.join(self.log_folder, f), transition_name='e_rabi')
        for t in self.transitions:
            if any([n in t.name for n in ['13c13', '13c6', '13c-5', '13c-6']]) and not 'ms0' in t.name:
                t_name = "13c ms0"
            else:
                t_name = t.name
            self.rabi_parameters[t.name] = RabiParametersStatic(filepath=os.path.join(self.log_folder, "{}_rabi.dat".format(t_name)), transition_name=t.name)

    def plot_rabi_parameters(self):
        idx = 0
        c13ms0_shown=False
        for tn, rp in self.rabi_parameters.items():
            try:
                if 'ms+1' in tn:
                    continue

                if rp.filename == '13c ms0_rabi':
                    if c13ms0_shown:
                        continue
                    else:
                        c13ms0_shown = True
                idx += 1
            except:
                pass
        fig, axes = plt.subplots(idx, 2, figsize=(10, 6*(idx)))
        idx=0
        c13ms0_shown=False
        for tn, rp in self.rabi_parameters.items():
            try:
                if 'ms+1' in tn:
                    continue

                if rp.filename == '13c ms0_rabi':
                    if c13ms0_shown:
                        continue
                    else:
                        c13ms0_shown = True
                # rp.plot()
                rp.plot(ax0=axes[idx, 0], ax1=axes[idx, 1])
                idx += 1
            except:
                print('could not plot {}'.format(tn))

    @property
    def log_folder(self):
        return r"{}transition_tracker_log".format(pi3d.log_dir)



    @property
    def current_local_oscillator_freq(self):
        return self._current_local_oscillator_freq

    @current_local_oscillator_freq.setter
    def current_local_oscillator_freq(self, val):
        self._current_local_oscillator_freq = misc.check_type(val, 'current_local_oscillator_freq', Number)
        self.update_stuff()

    @property
    def mw_mixing_frequency(self):
        return self._mw_mixing_frequency

    @mw_mixing_frequency.setter
    def mw_mixing_frequency(self, val):
        self._mw_mixing_frequency = misc.check_type(val, '_mw_mixing_frequency', Number)
        if getattr(self, '_mw_mixing_frequency', 0.0) != 0.0:
            pi3d.save_value_to_file(self.mw_mixing_frequency, 'mw_mixing_frequency')
        self.update_stuff()

    @property
    def zero_field_splitting(self):
        return self._zero_field_splitting

    @zero_field_splitting.setter
    def zero_field_splitting(self, val):
        self._zero_field_splitting = misc.check_type(val, 'zero_field_splitting', Number)
        self.update_stuff()

    @property
    def mw_transition_frequency(self):
        return self.mw_mixing_frequency + self.current_local_oscillator_freq


    @property
    def mw_mixing_frequency_p1(self):
        return self._mw_mixing_frequency_p1


    @mw_mixing_frequency_p1.setter
    def mw_mixing_frequency_p1(self, val):
        self._mw_mixing_frequency_p1 = misc.check_type(val, '_mw_mixing_frequency_p1', Number)
        if getattr(self, '_mw_mixing_frequency_p1', 0.0) != 0.0:
            pi3d.save_value_to_file(self.mw_mixing_frequency_p1, 'mw_mixing_frequency_p1')
        self.update_stuff()
        print('Field vector', self.current_magnetic_field_vector)
        angle = np.arctan(
            self.current_magnetic_field_vector[1]/self.current_magnetic_field_vector[0]) * 57.3248 # radian to degrees

        print('Field angle in degrees:',
              angle)


    @property
    def mw_transition_frequency_p1(self):
        return self.current_local_oscillator_freq_p1 + self.mw_mixing_frequency_p1

    @property
    def current_local_oscillator_freq_p1(self):
        return self.current_local_oscillator_freq# + self.mw_mixing_frequency




    # @property
    # def mw_mixing_frequency_p1(self):
    #     return 2*self.zero_field_splitting - self.mw_mixing_frequency

    # @property
    # def mw_transition_frequency_p1(self):
    #     return self.current_local_oscillator_freq + self.mw_mixing_frequency_p1
    #
    # @property
    # def current_local_oscillator_freq_p1(self):
    #     return self.mw_transition_frequency_p1 + self.mw_mixing_frequency





    def update_stuff(self):
        for attr_name in ['_current_local_oscillator_freq', '_mw_mixing_frequency', '_zero_field_splitting','mw_mixing_frequency_p1','_ple_Ex','_ple_A1']:
            if not hasattr(self, attr_name):
                return
        self.update_tt_electron_gui.emit()
        self.set_h_diag()
        if not hasattr(self, 'ntd'):
            return
        self.update_current_frequencies()

    # @property
    # def xyz(self):
    #     return self._xyz
    #
    # @xyz.setter
    # def xyz(self, vector):
    #     self._xyz = vector
    #     pi3d.save_values_to_file(self._xyz, 'xyz')


    @property
    def ple_Ex(self):
        return self._ple_Ex


    @ple_Ex.setter
    def ple_Ex(self, val):
        self._ple_Ex = misc.check_type(val, 'ple_Ex', Number)
        if getattr(self, '_ple_Ex', 0.0) != 0.0:
            pi3d.save_value_to_file(self.ple_Ex, 'ple_Ex')
        self.update_stuff()

    @property
    def ple_A1(self):
        return self._ple_A1

    @ple_A1.setter
    def ple_A1(self, val):
        self._ple_A1 = misc.check_type(val, 'ple_A1', Number)
        if getattr(self, '_ple_A1', 0.0) != 0.0:
            pi3d.save_value_to_file(self.ple_A1, 'ple_A1')
        self.update_stuff()


    def update_gui_electron(self):
        self.current_local_oscillator_freq_text_field.setText("{:.10f}".format(self.current_local_oscillator_freq))
        self.current_local_oscillator_freq_p1_text_field.setText("{:.10f}".format(self.current_local_oscillator_freq_p1))
        self.mw_mixing_frequency_text_field.setText("{:.10f}".format(self.mw_mixing_frequency))
        self.mw_mixing_frequency_p1_text_field.setText("{:.10f}".format(self.mw_mixing_frequency_p1))
        self.mw_transition_frequency_text_field.setText("{:.10f}".format(self.mw_transition_frequency))
        self.mw_transition_frequency_p1_text_field.setText("{:.10f}".format(self.mw_transition_frequency_p1))
        self.zero_field_splitting_text_field.setText("{:.10f}".format(self.zero_field_splitting))
        self.ple_Ex_text_field.setText("{:.10f}".format(self.ple_Ex))
        self.ple_A1_text_field.setText("{:.10f}".format(self.ple_A1))

    def update_gui_nuclear(self):
        column_names = ['name', 'current_frequency', 'ms_state', 'spin_type', 'start_level', 'end_level']
        self.script_queue_table.setColumnCount(len(column_names))
        self.script_queue_table.clearSelection()
        self.script_queue_table.clear()
        self.script_queue_table.setHorizontalHeaderLabels(column_names)
        self.script_queue_table.setEnabled(True)
        self.script_queue_table.setRowCount(len(self.transitions))
        for ridx, t in enumerate(self.transitions):
            for cidx, attr_name in enumerate(column_names):
                new_item = QTableWidgetItem(str(getattr(t, attr_name)))
                self.script_queue_table.setItem(ridx, cidx, new_item)

    @staticmethod
    def correct_transition_name(name):
        name = name.replace('13C', '13c').replace('14N', '14n').replace('mS', 'ms')
        if '13c' in name and 'ms0' in name:
            name = '13c ms0'
        if 'e_rabi' in name:
            name = name.replace('+1', 'right').replace('-1', 'left')
        return name

    def transition(self, name):
        name=self.correct_transition_name(name)
        for transition in self.transitions:
            if str(transition.name) in name:
                return transition
        else:
            return None

    t = transition

    def change_transition_frequency(self, fd, current_magnetic_field=None, test_mode=False):
        """
        all transition frequencies are defined from lower to higher angular momentum, i.e. 14N+1 mS0 is transition from 14N0 to 14N+1 in ms0
        gamma = -zeeman/B
        """
        current_magnetic_field = self.current_magnetic_field if current_magnetic_field is None else current_magnetic_field
        fdc = dict([(self.correct_transition_name(name), val) for name, val in fd.items()])

        fd14n = dict([(name, val) for name, val in fdc.items() if '14n' in name])
        cfd = dict([(name, self.t(name).current_frequency) for name, val in fdc.items()])
        if len(fd14n) > 0:
            if not '14n+1 ms0' in fd14n and '14n-1 ms0' in fd14n:
                raise Exception('Error: {}'.format(fd14n))
            mod = qutip_enhanced.lmfit_models.NVHam14NModel(fd14n, diag=True)
            params = mod.make_params()
            params['magnet_field'].value = pi3d.tt.current_magnetic_field
            params['magnet_field'].vary = False
            params['gamma_e'].value = pi3d.tt.g_factors['e']
            params['gamma_e'].vary = False
            params['gamma_n'].value = pi3d.tt.g_factors['14n']
            params['gamma_n'].min = 3.07
            params['gamma_n'].max = 3.08
            params['qp'].value = pi3d.tt.qp['14n']
            params['qp'].min = - 5.
            params['qp'].max = - 4.9
            params['hf_para_n'].value = pi3d.tt.hf_para_n['14n']
            # params['hf_para_n'].min = -2.17
            # params['hf_para_n'].max = -2.16
            params['hf_perp_n'].value = pi3d.tt.hf_perp_n['14n']
            # params['hf_perp_n'].min = -2.8
            # params['hf_perp_n'].max = -2.6
            # params['hf_perp_n'].vary = False
            if len(fd14n) <= 2:
                params['hf_para_n'].vary = False
            if len(fd14n) <=3:
                params['hf_perp_n'].vary = False
            # result = mod.fit(data=fd14n.values(), x=range(len(fd14n.keys())), params=params, method='lbfgsb', fit_kws=dict(options=dict(ftol=1e-17, gtol=1e-17, maxls=100, disp=True, maxiter=100, maxfun=10000)))
            result = mod.fit(data=fd14n.values(), x=range(len(fd14n.keys())), params=params, method='powell', fit_kws=dict(options=dict(ftol=1e-17, xtol=1e-17, disp=True)))
            # result = mod.fit(data=fd14n.values(), x=range(len(fd14n.keys())), params=params, method='powell', fit_kws=dict(options=dict(ftol=1e-17, xtol=1e-17, disp=True)))
            # result = mod.fit(data=fd14n.values(), x=range(len(fd14n.keys())), params=params, method='leastsqr', fit_kws=dict(ftol=1e-15, gtol=1e-15, maxfev=10000)) #https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.leastsq.html#scipy.optimize.leastsq
            cd = dict(transition_list=fd14n.keys(), nuc='14n', test_mode=test_mode)
            self.update_nuclear_parameter(val=result.params['gamma_n'].value,
                                          old_val=self.g_factors['14n'],
                                          filename='gamma_14n.dat',
                                          typ='gyromagnetic ratio',
                                          **cd)
            self.update_nuclear_parameter(val=result.params['qp'].value,
                                          old_val=self.qp['14n'],
                                          filename='qp_14n.dat',
                                          typ='quadrupole splitting',
                                          **cd)
            if len(fd14n) > 2:
                self.update_nuclear_parameter(val=result.params['hf_para_n'].value,
                                              old_val=self.hf_para_n['14n'],
                                              filename='hf_14n.dat',
                                              typ='hyperfine',
                                              **cd)
            if len(fd14n) > 3:
                self.update_nuclear_parameter(val=result.params['hf_perp_n'].value,
                                              old_val=self.hf_perp_n['14n'],
                                              filename='hf_perp_14n.dat',
                                              typ='perpendicular hyperfine',
                                              **cd)

        for name, new_freq in fdc.items():
            if '13c' in name and 'ms0' in name:
                nuc = name[:-4]
                self.update_nuclear_parameter(val=-new_freq / self.current_magnetic_field,
                                              old_val=self.g_factors['13c'],
                                              filename='gamma_13c.dat',
                                              typ='gyromagnetic ratio',
                                              nuc=nuc,
                                              transition_list=[name],
                                              test_mode=test_mode)
        for name, new_freq in fdc.items():
            if '13c' in name and not 'ms0' in name:
                ms = int(name[-2:])
                nuc = name[:-5]
                self.update_nuclear_parameter(val=ms * (self.g_factors['13c'] * current_magnetic_field + new_freq),
                                              old_val=self.hf_para_n[nuc],
                                              filename='hf_{}.dat'.format(nuc),
                                              typ='hyperfine',
                                              nuc=nuc,
                                              transition_list=[name],
                                              test_mode=test_mode)
        if test_mode and len(fd14n) >=2 :
            print(result.eval(x=range(len(fd14n)), params=result.params))
        for t, target_frequency in fdc.items():
            previous_frequency = cfd[t]
            current_frequency = self.t(t).current_frequency
            logging.getLogger().info(
                'Frequency of {} changed from {} to {} (deviation from target_frequency: {}Hz).'.format(t, previous_frequency, current_frequency, (current_frequency-target_frequency)*1e6)
            )

    def update_nuclear_parameter(self, typ, val, old_val, transition_list, nuc, filename, test_mode=False):
        log_text = 'The {} of {} was changed from {} to {} from measurement of [{}].'.format(typ, nuc, old_val, val, ",".join(transition_list))
        if test_mode:
            logging.getLogger().info('Test_mode!!!:            {}'.format(log_text))
        else:
            pi3d.save_values_to_file(val=[val], full_path="{}/{}".format(self.log_folder, filename), filename=None)
            logging.getLogger().info(log_text)
            self.reload_nuclear_parameters()
            self.set_h_diag()
            self.update_current_frequencies()

    @staticmethod
    def frequency_fid(assumed_frequency, frequency_offset, measured_period, max_diff_factor=.2):
        delta_abs_f = np.abs(frequency_offset) - np.abs(1 / float(measured_period))
        max_delta_abs_f = max_diff_factor*np.abs(frequency_offset)
        if max_diff_factor is not None and delta_abs_f > max_delta_abs_f:
            raise Exception('The measured period indicates a frequency change of {} MHz (allowed:  {}) MHz.'.format(delta_abs_f, max_delta_abs_f))
        return assumed_frequency + frequency_offset - np.sign(frequency_offset)/measured_period

    # def change_transition_frequency_fid(self, name, frequency_offset, period):
    #     """
    #     updates the frequency of self.transition(name)
    #     :param name: str
    #         nuclear transition name
    #     :param frequency_offset: float
    #         frequency offset used for fid, usually 0.002 [MHz]
    #     :param period:
    #         fid period that was actually measured (for perfect frequency match its 1/frequency_offset
    #     :return:
    #     """
    #     new_freq = self.t(name).current_frequency + frequency_offset - 1 / period
    #     max_dif = 0.002
    #     if abs(new_freq - self.t(name).current_frequency) < max_dif:
    #         self.change_transition_frequency(name, new_freq)
    #     else:
    #         print("Not Possible. Frequency difference is larger than {} MHz.".format(max_dif))

    def update_zero_field_splitting(self, freq):
        """
        updates the zero_field_splitting considering current_local_oscillator_freq, mw_mixing_frequency
        :param freq: float
            local oscillator frequency ms 0 -> +1 for mixing frequency mw_mixing_frequency
        """
        self.zero_field_splitting = (freq - self.current_local_oscillator_freq) / 2.0 + self.mw_mixing_frequency

    def get_rabi_parameter(self, name, **kwargs):
        name = self.correct_transition_name(name)
        # Javid added this to make sure we don't use wrong transition with old scripts
        # Or another bad case - one used old calibration sript, so that everything ws saved in wrong file
        if name =='e_rabi_ou350deg-90':
            warnings.warn('Specify if you want riht or left transition \n-R or -L should be in file name'
                          '\nBy default left transition will be used')
        if '_left' in name:
            tni = [0]
            name = name.replace('_left', '')
        elif '_right' in name:
            tni = [1]
            name = name.replace('_right', '')
        else:
            tni = None
        if 'e_rabi' in name and not '_ou' in name:
            name = "{}_ou{:.0f}deg{}".format(name, 1000*pi3d.mcas_dict.awgs['2g'].ch[1].output_amplitude,
                                             kwargs['mixer_deg'])
            del kwargs['mixer_deg']
        return RabiParametersSingle(rp=self.rabi_parameters[name], tni=tni, **kwargs)

    def rp(self, name, **kwargs):
        if len(kwargs) == 0:
            return self.rabi_parameters[name]
        elif (len(kwargs) == 1 and 'mixer_deg' in kwargs):
            return self.rabi_parameters['e_rabi_ou{:.0f}deg{}'.format(
                1000*pi3d.mcas_dict.awgs['2g'].ch[1].output_amplitude,
                kwargs['mixer_deg'])]
        else:
            return self.get_rabi_parameter(name, **kwargs)

    @property
    def current_magnetic_field(self): #z field
        return -(self.current_local_oscillator_freq - self.mw_mixing_frequency + self.zero_field_splitting) / self.g_factors['e']

    @property
    def current_magnetic_field_vector(self):  # z and x field
        sx, sy, sz = jmat(1)
        f1 = self.mw_mixing_frequency
        f2 = self.mw_mixing_frequency_p1
        def H(B_z, B_x):
            D = 2878.0
            gamma_e = 2.8
            return D * sz ** 2 + gamma_e * B_z * sz + gamma_e * B_x * sx

        def odmr(B_z, B_x):
            enerriges = H(B_z, B_x).eigenenergies()
            return (enerriges - enerriges[0])[1:]

        def func(params):
            bz = params[0]
            bx = params[1]
            return (odmr(bz, bx)[0] - f1) ** 2 + (odmr(bz, bx)[1] - f2) ** 2

        return minimize(fun =func,x0 = [300.,50.]).x



    def get_f(self, typ):
        if '_qp' in typ:
            return self.qp[typ.split('_')[0].lower()]
        elif '_hf' in typ:
            return self.hf_para_n[typ.split('_')[0].lower()]

    def mfl(self, td, mw_mixing_frequency=None, ms_trans='-1'):
        """

        :param td: dict
            e.g. {'14N':[1], '13C90': '0.5'}
        :param mw_mixing_frequency: float
        :return: list
            e.g. [17.6750, 19.8350]

        """
        if mw_mixing_frequency is None: mwfm = self.mw_mixing_frequency

        if type(td) is str:
            td = td.replace('14n', '14N').replace('13c', '13C')
            if td == '14N_all':
                td = {'14N': [-1, 0, 1]}
            elif td == '14N+1':
                td = {'14N': [1]}
            elif td == '14N-1':
                td = {'14N': [-1]}
            elif td == '14N0':
                td = {'14N': [0]}
            elif td == '13C414_all':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5, 0.5]}
            elif td == '13C414':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5]}
            elif td == '13C414_left':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5]}
            elif td == '13C414_right':
                td = {'14N': [-1, 0, 1], '13C414': [0.5]}
            elif td == '13C90_all':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5, 0.5], '13C90': [-0.5, 0.5]}
            elif td == '13C90':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5, 0.5], '13C90': [-0.5]}
            elif td == '13C90_left':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5, 0.5], '13C90': [-0.5]}
            elif td == '13C90_right':
                td = {'14N': [-1, 0, 1], '13C414': [-0.5, 0.5], '13C90': [0.5]}
            else:
                raise Exception("{} is not and allowed value for td".format(td))
        else:
            for key, val in td.items():
                del td[key]
                td[key.replace('14n', '14N').replace('13c', '13C')] = val
        f = list()
        for key in td.keys():
            if key not in ['14N', '13C414', '13C90']:
                raise Exception("Key '{}' is not a valid nuclear spin".format(key))
        for i in ['14N']:#, '13C414', '13C90']:
            a = np.array(td.get(i, [])) * self.get_f("{}_hf".format(i.lower()))
            if np.size(a) > 0:
                f.append(a)
        ff = list(product(*f))
        mfl = np.array(sorted([mwfm + sum(fff) for fff in ff if not np.size(fff) == 0]))
        if ms_trans in ['right', '+1']:
            return mfl - self.mw_mixing_frequency + self.mw_mixing_frequency_p1
        else:
            return mfl
