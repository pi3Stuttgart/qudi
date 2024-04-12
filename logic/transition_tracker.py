# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type
import warnings
import datetime
import time
import shutil

import logic.misc as misc
from importlib import reload
from numbers import Number
import scipy.interpolate
import scipy.optimize
from logic.qudip_enhanced.nv_hamilton import NVHam
from logic.qudip_enhanced import sort_eigenvalues_standard_basis
from logic.qudip_enhanced.analyze import flipped_spin_numbers, single_quantum_transitions_non_hf_spins, get_transition_frequency
import logic.qudip_enhanced.lmfit_models
from itertools import product
import numpy as np
import pandas as pd
import os
#from pi3diamond import pi3d
import collections
import matplotlib.pyplot as plt
import logging

from PyQt5.QtWidgets import QTableWidgetItem, QMainWindow
from PyQt5.QtCore import pyqtSignal
#from gui.qtgui import transition_tracker_gui

from PyQt5.uic import compileUi

from qutip import *
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import minimize
from scipy.interpolate import UnivariateSpline

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import time
import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt

from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex

####################################################################################################################
# single values
####################################################################################################################
app_dir = r'C:/src/qudi'
#app_dir= r'/Users/vvv/Documents/GitHub/qudi'

log_dir = '{}/log/'.format(app_dir)
log_archive_dir = '{}/log/archive/'.format(app_dir)
log_single_val_dir = '{}/log/single_values/'.format(app_dir)
log_tmp = '{}/log/temp/'.format(app_dir)

__TIME_FORMAT_STR__ = '%Y%m%d-h%Hm%Ms%S'


def nowstr():
    return datetime.datetime.now().strftime('%Y%m%d-h%Hm%Ms%S')
###################################################################

def latest_file_fn(fn_no_date, folder):
    file_list = sorted(os.listdir((folder)))
    return [s for s in file_list if fn_no_date in s][-1]

def get_path_for_save_value_to_file(filename):
    now = datetime.datetime.now()
    full_path = log_single_val_dir + os.path.splitext(filename)[0] + '/' + now.strftime('%Y%m') + filename + '.dat'
    return full_path

def date_str_in(date_str, start_date_str=None, end_date_str=None):
    date = datetime.datetime.strptime(date_str, __TIME_FORMAT_STR__)
    start_date = datetime.datetime.min if start_date_str is None else datetime.datetime.strptime(start_date_str, __TIME_FORMAT_STR__) #
    end_date = datetime.datetime.now() if end_date_str is None else datetime.datetime.strptime(end_date_str, __TIME_FORMAT_STR__) #
    return start_date <= date <= end_date

def save_value_to_file(val, filename):
    """Appends a given value 'val' to a text file with filename 'yymmdd_filename' (e.g. 130101_temperature.dat) and adds the current date and time (format'yymmdd hhmmss) separated by a tab. '
    """
    full_path = get_path_for_save_value_to_file(filename)
    folder = os.path.dirname(full_path)
    if not os.path.isdir(log_single_val_dir):
        os.mkdir(log_single_val_dir)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    now = datetime.datetime.now()
    fil = open(full_path, 'a')
    fil.write(now.strftime('%Y%m%d-h%Hm%Ms%S') + '\t' + str(val) + '\n')
    fil.close()

def save_values_to_file(val, filename, full_path=None):
    full_path = get_path_for_save_value_to_file(filename) if full_path is None else full_path
    folder = os.path.dirname(full_path)
    if not os.path.isdir(log_single_val_dir):
        os.mkdir(log_single_val_dir)
    if not os.path.isdir(folder):
        os.mkdir(folder)
    now = datetime.datetime.now()
    fil = open(full_path, 'a')
    fil.write(now.strftime('%Y%m%d-h%Hm%Ms%S') + '\t' + '\t'.join(str(v) for v in val) + '\n')
    fil.close()

def get_last_value_from_file(filename, flg_out_date=False):
    folder = os.path.dirname(get_path_for_save_value_to_file(filename))
    file_list = sorted(os.listdir((folder)))
    last_file_name = [s for s in file_list if filename in s][-1]
    fil = open(os.path.join(folder, last_file_name), 'r')
    line_str_list = fil.readlines()[-1].split('\t')
    fil.close()

    if 'fit_params' in filename or 'history' in filename:
        val = np.array(line_str_list[-1].rstrip('\n'))
    else:
        val = float(line_str_list[-1].rstrip('\n'))
    if flg_out_date == True:
        date = datetime.datetime.strptime(line_str_list[0], '%Y%m%d-h%Hm%Ms%S')
        return val, date
    return val

def get_last_values_from_file(filename, flg_out_date=False, full_path=None):
    if full_path is None:
        folder = os.path.dirname(get_path_for_save_value_to_file(filename))
        file_list = sorted(os.listdir((folder)))
        last_file_name = [s for s in file_list if filename in s][-1]
        full_path = os.path.join(folder,last_file_name)
    else:
        full_path = get_path_for_save_value_to_file(filename) if full_path is None else full_path
        full_path = get_path_for_save_value_to_file(filename) if full_path is None else full_path
    fil = open(full_path, 'r')

    line_str_list = fil.readlines()[-1].split('\t')
    line_str_list[-1].rstrip('\n')
    fil.close()
    val = []
    for i in line_str_list[1:]:
        try:
            val.append(float(i))
        except:
            val.append(i.rstrip('\n'))
    if flg_out_date is True:
        date = datetime.datetime.strptime(line_str_list[0], '%Y%m%d-h%Hm%Ms%S')
        return val, date
    print(val)
    return val

def get_values_time_span(filename, start_date_str, end_date_str=None):
    folder = os.path.dirname(get_path_for_save_value_to_file(filename))
    file_list = sorted(os.listdir(folder))
    result = {'dates': [], 'data': []}
    for fn in file_list:
        try:
            file_date_str = datetime.datetime.strptime(fn[0:6], '%Y%m').strftime(__TIME_FORMAT_STR__)
        except:
            file_list.remove(fn)
            continue
        with open("{}/{}".format(folder, fn), 'r') as f:
            for l in f:
                l = l.rstrip('\n').split('\t')

                if date_str_in(l[0], start_date_str, end_date_str):
                    result['dates'].append(datetime.datetime.strptime(l[0], __TIME_FORMAT_STR__))
                    result['data'].append(l[1:])
    result['data'] = np.array(result['data'])
    return result

def plot_single_values(filename, start_date_str, end_date_str=None, grating='m'):
    values = get_values_time_span(filename=filename, start_date_str=start_date_str, end_date_str=end_date_str)
    if end_date_str is None:
        end_date_str = datetime.datetime.now()
    else:
        end_date_str = datetime.datetime.strptime(end_date_str, __TIME_FORMAT_STR__)
    grating_dict = {'h': 1. / 60. / 60., 'm': 1. / 60., 's': 1.}
    labeldict = {'magnet_gradients': ['x', 'y'], 'confocal_pos': ['x', 'y', 'z'], 'magnet_pos': ['x', 'y', 'z', 'phi'], 'current_local_oscillator_freq': 'local oscillator'}
    legenddict = {'magnet_gradients': 'MHz/mu m', 'confocal_pos': 'mu m', 'magnet_pos': 'mu m', 'current_local_oscillator_freq': 'MHz'}
    precisiondict = {'magnet_gradients': 6, 'confocal_pos': 4, 'magnet_pos': 4, 'current_local_oscillator_freq': 3}
    tdelta = np.array([(values['dates'][i] - end_date_str).total_seconds() for i in range(len(values['dates']))]) * grating_dict['{}'.format(grating)]
    num_single_values = len(values['data'][0])
    num_dp = len(tdelta)
    data = dict()
    for num in range(num_single_values):
        data[num] = np.array([values['data'][i][num] for i in range(num_dp)]).astype(float)
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    fig, axes = plt.subplots(num_single_values)
    fig.suptitle(filename + ' since ' + '{}'.format(values['dates'][0].strftime('%Y%m%d-h%Hm%Ms%S')))
    if num_single_values != 1:
        for sv in range(num_single_values):
            axes[sv].plot(tdelta, data[sv], 'o-', label=labeldict[filename][sv])
            axes[sv].yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.{}f'.format(precisiondict[filename])))
            axes[sv].legend()
            axes[sv].set_ylabel(legenddict[filename])
            axes[sv].set_xlabel('time [{}]'.format(grating))
    else:
        axes.plot(tdelta, data[0], 'o-', label=labeldict[filename])
        axes.legend()
        axes.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.{}f'.format(precisiondict[filename])))
        axes.set_ylabel(legenddict[filename])
        axes.set_xlabel('time [s]')
    plt.show()

# def recompile_ui_file():
#     fold = "{}/qtgui".format(os.path.dirname(__file__))
#     name = "transition_tracker"
#     uipath = r"{}/{}.ui".format(fold, name)
#     pypath = r"{}/{}_gui.py".format(fold, name)
#     with open(pypath, 'w') as f:
#         compileUi(uipath, f)
#     reload(transition_tracker_gui)

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
        import hardware.Keysight_AWG_M8190.elements as E
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
        fil = r'C:\src\qudi\log\transition_tracker_log\rabi_parameters_archive\{}'.format(filename)
        date = datetime.datetime.fromtimestamp(os.path.getmtime(self.filepath)).strftime('%Y%m%dh%Hm%Ms%S')
        if not os.path.isdir(fil):
            os.mkdir(fil)
        shutil.copy(self.filepath, r'C:\src\qudi\log\transition_tracker_log\rabi_parameters_archive\{}\{}-{}_{}.dat'.format(filename, date, nowstr(), filename))

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
        key, val = list(kwargs.items())[0]
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
        key, val = list(kwargs.items())[0]
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
        val = np.array(list(kwargs.values())[0])
        if len(val.shape) not in [0, 1]:
            raise ValueError('Input value must be 0D or 1D but was {}'.format(len(val.shape)))
        if len(val.shape) == 1 and val.shape[0] > self.rp.tnf:
            raise ValueError('Input value is too large for given rabi file. ({}, tnf: {}'.format(val.shape[0], self.rp.tnf))
        if list(kwargs.keys())[0] not in ['amp', 'omega', 'period']:
            raise Exception("input parameter names must be in ['amp', 'omega', 'period'], but {} was given".format(list(kwargs.keys())[0]))
        return kwargs

class Transition:
    def __init__(self, name, parent=None, current_frequency=None):
        self.parent = parent
        if current_frequency is not None:
            self.current_frequency = current_frequency
        self.name = name
        self.set_meta()

    name = misc.ret_property_typecheck('name', str)
    ms_state = misc.ret_property_list_element('ms_state', [1.5, 0.5,-0.5, -1.5])
    spin_type = misc.ret_property_list_element('spin_type', ['14n', '13c','29si'])
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
        self.ms_state = float(ms[2:])
        self.spin_type = '14n' if '14n' in self.nuc else '13c' #Fixme should be 29si?
        if self.spin_type == '14n':
            self.start_angular_momentum, self.end_angular_momentum = sorted([0, int(self.nuc[-2:])])
        else:
            self.start_angular_momentum = -.5
            self.end_angular_momentum = +.5


# gui QMainWindow, transition_tracker_gui.Ui_window
class TransitionTracker(GenericLogic):

    c13_list = ConfigOption('c13_list', default=[])
    si29_list = ConfigOption('si29_list', default=[])
    transitions = misc.ret_property_array_like_typ('transitions', Transition)
    log_folder = r"C:\src\qudi\log\transition_tracker_log"
    g_factors = {'e': -2.0028 * 1.6021766208e-19 / (4 * np.pi * 9.10938356e-31) * 1e-6,
                 'C':10.78,'Si':-8.4} # why again? it is already in qutip enhanced.

    #transition_tracker_gui = Connector(interface="transition_tracker_gui")
    mcas_holder = Connector(interface='McasDictHolderInterface') #why?
    #rabi_logic= Connector(interface='RabiLogic') #why? we do it via nuclear ops.
    odmr_logic= Connector(interface='ODMRLogic_holder') #ok for refocus.
    ple_logic= Connector(interface='LaserScannerLogic') #ok for refocus
    powerstabilization_logic= Connector(interface='PowerStabilizationLogic') #ok for refocus
    
    update_tt_nuclear_gui = pyqtSignal()
    update_tt_electron_gui = pyqtSignal() #is it connected?

    def __init__(self,config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self._awg = self.mcas_holder()
        self._odmr_logic= self.odmr_logic()
        self._ple_logic= self.ple_logic()
        self._powerstabilization_logic= self.powerstabilization_logic()
    
        self.connect_signals()  # todo
        # title = '' if title is None else title
        # self.setWindowTitle(title)
        self.reload_nuclear_parameters()
        self.mw_mixing_frequency_L = get_last_value_from_file('mw_mixing_frequency_L')
        self.mw_mixing_frequency_C = get_last_value_from_file('mw_mixing_frequency_C')
        self.mw_mixing_frequency_R = get_last_value_from_file('mw_mixing_frequency_R')
        self.ple_A2 = get_last_value_from_file('ple_A2')
        self.ple_A2_fit_params = get_last_value_from_file('ple_A2_fit_params')
        self.interferometer_fit_params = get_last_value_from_file('interferometer_fit_params')
        self.interferometer_history = get_last_value_from_file('interferometer_history')
        self.ple_A1 = get_last_value_from_file('ple_A1')
        self.ple_A1_fit_params = get_last_value_from_file('ple_A1_fit_params')
        self.ple_repump = get_last_value_from_file('ple_repump') # we are not using itm  right?

        # self.xyz = pi3d.get_last_values_from_file('xyz')
        self.current_local_oscillator_freq = get_last_value_from_file('current_local_oscillator_freq') #also not using it.
        self.zero_field_splitting = get_last_value_from_file('zfs')
        self.transition_name_list = [['-1.5', '-0.5', '+0.5','+1.5']] + [['+0.5', '-0.5']] * (len(self.c13_list)+len(self.si29_list))
        self.states_list = [range(len(i)) for i in self.transition_name_list]
        self.spin_name_list = ['e'] + self.c13_list + self.si29_list
        self.set_h_diag()
        self.set_ntd() #nuclear transition dict
        self.load_transitions()
        if not self._awg.mcas_dict.debug_mode:
            self.load_rabi_parameters()
        self.update_stuff()
        pass
        #self._transition_tracker_gui = self.transition_tracker_gui()

    def on_deactivate(self):
        pass

    def do_nothing(self,*args,**kwargs):
        print("done nothing\n", "args are:\n",args)
        pass

    def update_ple(self,freqs=""):
        print("Updating PLE freq in TT...")
        print(freqs)
        if len(freqs.split(';')) == 3: # when PLE data has two peaks
            self.ple_A2 = float(freqs.split(';')[1])
            self.ple_A1 = float(freqs.split(';')[0])
        elif len(freqs.split(';')) < 3: # If only one peak is fitted to PLE data
            #self.ple_A1 = float(freqs.split(';')[0])
            self.ple_A2 = float(freqs.split(';')[0])
        else:
            print("Too many PLE peaks, dont know how to assign it in Transition Tracker.")
        # to set the constant voltage, thus lock the frequency, on the peak
        #self._ple_logic._change_voltage(self.ple_A2)

    def update_ODMR(self,freqs='', tag = ''):
        print("Updating MW freqs in TT...")
        print(tag)
        # print(freqs)
        freq_list = []
        for freq in freqs.split(';')[:-1]: # last entry in none
            freq_list.append(float(freq))
        #self.mw_mixing_frequency_L=float(freqs.split(';')[0])
        if (len(tag) != 0) and (tag[-1] == 'L'):
            print("updating left trans",np.mean(freq_list))
            self.mw_mixing_frequency_L=np.mean(freq_list)
        elif (len(tag) != 0) and (tag[-1] == 'R'):
            print("updating right trans",np.mean(freq_list))
            self.mw_mixing_frequency_R=np.mean(freq_list)

    def update_rabi(self,pi_dur):
        # pi_dur is already a float
        pass
        #print("Updating Rabi pi pulse in TT...")
        #print(pi_dur)
        #self.current_local_oscillator_freq=pi_dur

    def connect_signals(self):
        #self._rabi_logic.sigFitPerformed.connect(self.update_rabi)
        self._odmr_logic.sigFitPerformed.connect(self.update_ODMR)
        self._ple_logic.sigFitPerformed.connect(self.update_ple)
        #self._powerstabilization_logic.SigPowerCalibrationFinished.connect(self.update_power_calibration)

        #self.update_tt_nuclear_gui.connect(self.update_gui_nuclear)
        #self.update_tt_electron_gui.connect(self.update_gui_electron)

    def nuclear_transition_name(self, transition):
        """
        this transitions is for the nuclear spin.
        """

        ms = self.transition_name_list[0][transition[0][0]]
        fsn = flipped_spin_numbers(transition)[0]
        nuc = self.spin_name_list[fsn] #nuc = 29si8 ms = +1.5
        if ms == '0' and '13c' in nuc: # no there is never happens here. basically all are at larmor.
            return '13c ms0'
        else:
            if fsn == 1 and '14n' in nuc: #if it is nuclear spin flipped. (nitrogen, I assume?)
                if transition[0][1] == 0: #initial transition is '+1'
                    mn = '+1'
                elif transition[1][1] == 2: #initial transition is '0'
                    mn = '-1'
                nuc += mn

            #here is not used??
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
        
        # 14N is just an example. 
        self.g_factors['14n'] = get_last_values_from_file(filename='gamma_14n.dat', full_path=os.path.join(self.log_folder,'gamma_14n.dat'))[0]#r"{}\gamma_14n.dat".format(self.log_folder))[0]
        self.qp = {'14n': get_last_values_from_file(filename='qp_14n.dat', full_path=os.path.join(self.log_folder,'qp_14n.dat'))[0]}#r"{}\qp_14n.dat".format(self.log_folder))[0]}
        self.hf_para_n = {'14n': get_last_values_from_file(filename='hf_14n.dat',
                                                           full_path=os.path.join(self.log_folder,'hf_14n.dat'))[0]
                          }#r"{}\hf_14n.dat".format(self.log_folder))[0]}
        self.hf_perp_n = {'14n': get_last_values_from_file(filename='hf_perp_14n.dat', full_path=os.path.join(self.log_folder,'hf_perp_14n.dat'))[0]}#r"{}\hf_perp_14n.dat".format(self.log_folder))[0]}
        self.hf_para_n.update(dict([(key, 
                                     get_last_values_from_file(filename='hf_{}.dat'.format(key),
                                                               full_path=os.path.join(
                                                                   self.log_folder,'hf_{}.dat'.format(key)))[0]
                                                                   ) for key in self.c13_list+self.si29_list]))
        self.hf_perp_n.update(dict([(key, 
                                     get_last_values_from_file(filename='hf_perp_{}.dat'.format(key),
                                                               full_path=os.path.join(
                                                                   self.log_folder,'hf_perp_{}.dat'.format(key)))[0]
                                                                   ) for key in self.c13_list+self.si29_list]))

    def set_h_diag(self):
        self.nvham = NVHam(magnet_field={'z': self.current_magnetic_field},
                           n_type=None, nitrogen_levels=[],
                           electron_levels=[0,1,2,3], gamma=self.g_factors,
                           qp=self.qp, hf_para_n=self.hf_para_n,
                           hf_perp_n=self.hf_perp_n)
        for c13 in self.c13_list:
            self.nvham.add_spin(np.matrix(np.diag([self.hf_perp_n[c13], self.hf_perp_n[c13], self.hf_para_n[c13]])), 
                                self.nvham.h_13c(), [0, 1])

        for si29 in self.si29_list:
            self.nvham.add_spin(
                hft=np.matrix(np.diag([self.hf_perp_n[si29], self.hf_perp_n[si29], self.hf_para_n[si29]])),
                h_ns=self.nvham.h_29si(),
                nslvl_l=[0, 1])

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
                    current_frequency=-get_transition_frequency(h_diag=self.h_diag, dims=self.nvham.dims, transition=val) # fixme get it right
                )
            )

    def update_current_frequencies(self):
        for key, val in self.ntd.items():
            self.transition(key).current_frequency = -get_transition_frequency(h_diag=self.h_diag, dims=self.nvham.dims, 
                                                                               transition=val)
        self.update_tt_nuclear_gui.emit() #connect to gui.

    def load_rabi_parameters(self):
        self.rabi_parameters = dict()
        for f in os.listdir(self.log_folder):
            if 'e_rabi_ou{:.0f}deg'.format(1000*self._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude) in f:
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
        return r"{}transition_tracker_log".format(log_dir)


    @property
    def current_local_oscillator_freq(self):
        return self._current_local_oscillator_freq

    @current_local_oscillator_freq.setter
    def current_local_oscillator_freq(self, val):
        self._current_local_oscillator_freq = misc.check_type(val, 'current_local_oscillator_freq', Number)
        self.update_stuff()

    @property
    def mw_mixing_frequency_L(self):
        return self._mw_mixing_frequency_L

    @mw_mixing_frequency_L.setter
    def mw_mixing_frequency_L(self, val):
        print("TT:")
        print(val)
        self._mw_mixing_frequency_L = misc.check_type(val, '_mw_mixing_frequency_L', Number)
        if getattr(self, '_mw_mixing_frequency_L', 0.0) != 0.0:
            save_value_to_file(self.mw_mixing_frequency_L, 'mw_mixing_frequency_L')
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
        return self.mw_mixing_frequency_L# + self.current_local_oscillator_freq


    @property
    def mw_mixing_frequency_R(self):
        return self._mw_mixing_frequency_R

    @property
    def mw_mixing_frequency_C(self):
        return self._mw_mixing_frequency_C

    @mw_mixing_frequency_C.setter
    def mw_mixing_frequency_C(self, val):
        print("TT:")
        print(val)
        self._mw_mixing_frequency_C = misc.check_type(val, '_mw_mixing_frequency_C', Number)
        if getattr(self, '_mw_mixing_frequency_L', 0.0) != 0.0:
            save_value_to_file(self.mw_mixing_frequency_C, 'mw_mixing_frequency_C')
        self.update_stuff()

    @mw_mixing_frequency_R.setter
    def mw_mixing_frequency_R(self, val):
        self._mw_mixing_frequency_R = misc.check_type(val, '_mw_mixing_frequency_R', Number)
        if getattr(self, '_mw_mixing_frequency_R', 0.0) != 0.0:
            save_value_to_file(self.mw_mixing_frequency_R, 'mw_mixing_frequency_R')
        self.update_stuff()
        print('Field vector', self.current_magnetic_field_vector)
        angle = np.arctan(
            self.current_magnetic_field_vector[1]/self.current_magnetic_field_vector[0]) * 57.3248 # radian to degrees

        print('Field angle in degrees:',
              angle)


    @property
    def mw_transition_frequency_p1(self):
        return self.current_local_oscillator_freq_p1 + self.mw_mixing_frequency_R #TODO local oscillator_p1 to local oscillator_R

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
        for attr_name in ['_current_local_oscillator_freq', '_mw_mixing_frequency_L',
                          '_zero_field_splitting','mw_mixing_frequency_R','_ple_A2','_ple_A1','_ple_repump',
                          'ple_A2_fit_params','ple_A1_fit_params','interferometer_fit_params','interferometer_history']: #needs "ple_Ex", but where is this "ple_Ex" called?
            if not hasattr(self, attr_name):
                return
        self.update_tt_electron_gui.emit() #connect to the gui
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
    def ple_repump(self):
        return self._ple_repump


    @ple_repump.setter
    def ple_repump(self, val):
        self._ple_repump = misc.check_type(val, 'ple_repump', Number)
        if getattr(self, '_ple_repump', 0.0) != 0.0:
            save_value_to_file(self.ple_repump, 'ple_repump')
        self.update_stuff()




    @property
    def ple_A2(self):
        return self._ple_A2


    @ple_A2.setter
    def ple_A2(self, val):
        self._ple_A2 = misc.check_type(val, 'ple_A2', (list,Number, np.ndarray))
        # if getattr(self, '_ple_A2', 0.0) != 0.0:
        if getattr(self, '_ple_A2', 0.0) is not None:

            save_value_to_file(self.ple_A2, 'ple_A2')
        self.update_stuff()


    @property
    def ple_A2_fit_params(self):
        return self._ple_A2_fit_params


    @ple_A2_fit_params.setter
    def ple_A2_fit_params(self, val):
        self._ple_A2_fit_params = misc.check_type(val, 'ple_A2_fit_params', (list, np.ndarray))
        if getattr(self, '_ple_A2_fit_params', 0.0) is not None:

            save_value_to_file(self.ple_A2_fit_params, 'ple_A2_fit_params')
        self.update_stuff()

    @property
    def ple_A1_fit_params(self):
        return self._ple_A1_fit_params


    @ple_A1_fit_params.setter
    def ple_A1_fit_params(self, val):
        self._ple_A1_fit_params = misc.check_type(val, 'ple_A1_fit_params', (list, np.ndarray))
        if getattr(self, '_ple_A1_fit_params', 0.0) is not None:

            save_value_to_file(self.ple_A1_fit_params, 'ple_A1_fit_params')
        self.update_stuff()





    @property
    def ple_A1(self):
        return self._ple_A1

    @ple_A1.setter
    def ple_A1(self, val):
        self._ple_A1 = misc.check_type(val, 'ple_A1', (list,Number, np.ndarray))
        # if getattr(self, '_ple_A1', 0.0) != 0.0:
        if getattr(self, '_ple_A1', 0.0) is not None:

                save_value_to_file(self.ple_A1, 'ple_A1')
        self.update_stuff()


    @property
    def interferometer_fit_params(self):
        return self._interferometer_fit_params


    @interferometer_fit_params.setter
    def interferometer_fit_params(self, val):
        self._interferometer_fit_params = misc.check_type(val, 'interferometer_fit_params', (list, np.ndarray))
        if getattr(self, '_interferometer_fit_params', 0.0) is not None:

            save_value_to_file(self.interferometer_fit_params, 'interferometer_fit_params')
        self.update_stuff()

    @property
    def interferometer_history(self):
        return self._interferometer_history


    @interferometer_history.setter
    def interferometer_history(self, val):
        self._interferometer_history = misc.check_type(val, 'interferometer_history', (list, np.ndarray,tuple))
        if getattr(self, '_interferometer_history', 0.0) is not None:

            save_value_to_file(self.interferometer_history, 'interferometer_history')
        self.update_stuff()






    #this went to gui
    # def update_gui_electron(self):
    #     self.current_local_oscillator_freq_text_field.setText("{:.10f}".format(self.current_local_oscillator_freq))
    #     self.current_local_oscillator_freq_p1_text_field.setText("{:.10f}".format(self.current_local_oscillator_freq_p1))
    #     self.mw_mixing_frequency_text_field.setText("{:.10f}".format(self.mw_mixing_frequency))
    #     self.mw_mixing_frequency_p1_text_field.setText("{:.10f}".format(self.mw_mixing_frequency_p1))
    #     self.mw_transition_frequency_text_field.setText("{:.10f}".format(self.mw_transition_frequency))
    #     self.mw_transition_frequency_p1_text_field.setText("{:.10f}".format(self.mw_transition_frequency_p1))
    #     self.zero_field_splitting_text_field.setText("{:.10f}".format(self.zero_field_splitting))
    #     self.ple_A2_text_field.setText("{:.10f}".format(self.ple_A2))
    #     self.ple_A1_text_field.setText("{:.10f}".format(self.ple_A1))
    #     # self.ple_repump_text_field.setText("{:.10f}".format(self.ple_A1))
    #
    #
    #
    #
    # def update_gui_nuclear(self):
    #     column_names = ['name', 'current_frequency', 'ms_state', 'spin_type', 'start_level', 'end_level']
    #     self.script_queue_table.setColumnCount(len(column_names))
    #     self.script_queue_table.clearSelection()
    #     self.script_queue_table.clear()
    #     self.script_queue_table.setHorizontalHeaderLabels(column_names)
    #     self.script_queue_table.setEnabled(True)
    #     self.script_queue_table.setRowCount(len(self.transitions))
    #     for ridx, t in enumerate(self.transitions):
    #         for cidx, attr_name in enumerate(column_names):
    #             new_item = QTableWidgetItem(str(getattr(t, attr_name)))
    #             self.script_queue_table.setItem(ridx, cidx, new_item)

    @staticmethod
    def correct_transition_name(name):
        name = name.replace('13C', '13c').replace('14N', '14n').replace('mS', 'ms').replace('29Si','29si')
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
            mod = logic.qudip_enhanced.lmfit_models.NVHam14NModel(fd14n, diag=True)
            params = mod.make_params()
            params['magnet_field'].value = self.current_magnetic_field
            params['magnet_field'].vary = False
            params['gamma_e'].value = self.g_factors['e']
            params['gamma_e'].vary = False
            params['gamma_n'].value = self.g_factors['14n']
            params['gamma_n'].min = 3.07
            params['gamma_n'].max = 3.08
            params['qp'].value = self.qp['14n']
            params['qp'].min = - 5.
            params['qp'].max = - 4.9
            params['hf_para_n'].value = self.hf_para_n['14n']
            # params['hf_para_n'].min = -2.17
            # params['hf_para_n'].max = -2.16
            params['hf_perp_n'].value = self.hf_perp_n['14n']
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
            print("test_mode in TT:", result.eval(x=range(len(fd14n)), params=result.params))
        for t, target_frequency in fdc.items():
            previous_frequency = cfd[t]
            current_frequency = self.t(t).current_frequency
            logging.getLogger().info(
                'Frequency of {} changed from {} to {} (deviation from target_frequency: {}Hz).'.format(t, previous_frequency, current_frequency, (current_frequency-target_frequency)*1e6)
            )

    def update_nuclear_parameter(self, typ, val, old_val, transition_list, nuc, filename, test_mode=False):
        log_text = 'The {} of {} was changed from {} to {} from measurement of [{}].'.format(typ, nuc, old_val, val, ",".join(transition_list))
        if test_mode:
            #todo change loogger
            logging.getLogger().info('Test_mode!!!:            {}'.format(log_text))
        else:
            save_values_to_file(val=[val], full_path="{}/{}".format(self.log_folder, filename), filename=None)
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
        self.zero_field_splitting = (freq - self.current_local_oscillator_freq) / 2.0 + self.mw_mixing_frequency_L

    def get_rabi_parameter(self, name, **kwargs):
        name = self.correct_transition_name(name)
        # Javid added this to make sure we don't use wrong transition with old scripts
        # Or another bad case - one used old calibration sript, so that everything ws saved in wrong file
        if name =='e_rabi_ou350deg-90':
            warnings.warn('Specify if you want right or left transition \n-R or -L should be in file name'
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
            name = "{}_ou{:.0f}deg{}".format(name, 1000*self._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude, #TODO connect to it
                                             kwargs['mixer_deg'])
            del kwargs['mixer_deg']
        return RabiParametersSingle(rp=self.rabi_parameters[name], tni=tni, **kwargs)

    def rp(self, name, **kwargs):
        if len(kwargs) == 0:
            return self.rabi_parameters[name]
        elif (len(kwargs) == 1 and 'mixer_deg' in kwargs):
            return self.rabi_parameters['e_rabi_ou{:.0f}deg{}'.format(
                1000*self._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude,
                kwargs['mixer_deg'])]
        else:
            return self.get_rabi_parameter(name, **kwargs)

    @property
    def current_magnetic_field(self): #z field
        return -(self.current_local_oscillator_freq - self.mw_mixing_frequency_L + 
                 2*self.zero_field_splitting) / self.g_factors['e']

    @property
    def current_magnetic_field_vector(self):  # z and x field
        sx, sy, sz = jmat(1.5)
        print('B field calculator')
        f1 = self.mw_mixing_frequency_L
        f2 = self.mw_mixing_frequency_R
        f3 = self.mw_mixing_frequency_C
        def H(B_z, B_x):
            D = 34.9
            gamma_e = 2.804
            return D * sz ** 2 + gamma_e * B_z * sz + gamma_e * B_x * sx

        def odmr(B_z, B_x):
            enerriges = H(B_z, B_x).eigenenergies()
            return np.array([enerriges[1] - enerriges[0], 
                             enerriges[2]-enerriges[1],
                             enerriges[3]-enerriges[2]])

        def func(params):
            bz = params[0]
            bx = params[1]
            return (odmr(bz, bx)[0] - f1) ** 2 + (odmr(bz, bx)[1] - f2) ** 2 + (odmr(bz, bx)[2] - f3) ** 2 

        return minimize(fun =func,x0 = np.array([1.,0.])).x



    def get_f(self, typ):
        if '_qp' in typ:
            return self.qp[typ.split('_')[0].lower()]
        elif '_hf' in typ:
            return self.hf_para_n[typ.split('_')[0].lower()]

    def mfl(self, td, mw_mixing_frequency_L=None, ms_trans='L'):
        #TODO: update ms from NV to V2
        """

        :param td: dict
            e.g. {'14N':[1], '13C90': '0.5'}
        :param mw_mixing_frequency: float
        :return: list
            e.g. [17.6750, 19.8350]

        """
        if mw_mixing_frequency_L is None: mwfm = self.mw_mixing_frequency_L

        if type(td) is str:
            td = td.replace('14n', '14N').replace('13c', '13C').replace('29si','29Si')
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
                td[key.replace('14n', '14N').replace('13c', '13C').replace('29si','29Si')] = val
        f = list()
        for key in td.keys():
            if key not in ['14N', '13C414', '13C90','29Si8', '13C5','29Si8.00',"29Si2.2"]:
                raise Exception("Key '{}' is not a valid nuclear spin".format(key))
        for i in ['29Si2.2']:#why not put here all spin list?
        #for i in [*self.c13_list,*self.si29_list]:#why not put here all spin list?
            a = np.array(td.get(i, [])) * self.get_f("{}_hf".format(i.lower()))
            if np.size(a) > 0:
                f.append(a)
        ff = list(product(*f))
        mfl = np.array(sorted([mwfm + sum(fff) for fff in ff if not np.size(fff) == 0]))

        #here do some ms?
        if ms_trans in ['R']:
            return mfl - self.mw_mixing_frequency_L + self.mw_mixing_frequency_R

        elif ms_trans in ['C']:
            return mfl + -self._mw_mixing_frequency_L+self._mw_mixing_frequency_C
        else:
            return mfl
