import warnings
warnings.simplefilter(action = "ignore", category = FutureWarning)
import numpy as np
np.set_printoptions(linewidth=500, suppress=True)
import datetime
import scipy.interpolate
import scipy.optimize
import numpy as np
import pandas as pd
import struct
import collections
import copy
import itertools
from numbers import Number
#from pi3diamond import pi3d

# TODO: Add type 'key' to SequenceStep(). Length sample then ideally could be read out from AWG by key number,
# TODO: or it would be 0. Then however also checks for the fulfillment of the linear playtime requirement would have to
# TODO: be included.

__ADVANCE_MODE_MAP__ = {'AUTO': 0, 'COND': 1, 'REP': 2, 'SING': 3}
__AMPLITUDE_GRANULARITY__ = 1/2.**12
__MAX_LENGTH_SMPL__ = 2e9 #most probably wrong, but a reasonable estimate
__BLM__ = 384./12e3


def check_type(val, name, typ):
    if issubclass(type(val), typ):
        return val
    else:
        raise Exception("Property {} must be {} but is {}".format(name, typ, type(val)))

def check_range(val, name, start, stop):
    if start <= val <= stop:
        return val
    else:
        raise Exception("Property {} must be in range ({}, {}) but has a value of {}".format(name, start, stop, val))

def check_array_like(val, name):
    at = [list, np.ndarray]
    if type(val) in at:
        return val
    else:
        raise Exception("Type of property {} must be in list {}. Tried to assign val {} of type {}.".format(name, at, val, type(val)))

def check_array_like_typ(val, name, typ):
    val = [check_type(i, name+'_i', typ) for i in check_array_like(val, name)]
    if typ in [float, int, Number]:
        val = np.array(val)
    return val

def check_list_element(val, name, list):
    if val in list:
        return val
    else:
        raise Exception("Property {} must be in list {} but has a value of {}".format(name, list, val))

def ret_getter(name):
    def getter(self):
        return getattr(self, '_'+name)
    return getter

def ret_property_typecheck(name, typ):
    def setter(self, val):
        setattr(self, '_'+name, check_type(val, name, typ))
    return property(ret_getter(name), setter)

def ret_property_range(name, typ, start, stop):
    def setter(self, val):
        setattr(self, '_'+name, check_range(check_type(val, name, typ), name, start, stop))
    return property(ret_getter(name), setter)

def ret_property_list_element(name, list):
    def setter(self, val):
        setattr(self, '_'+name, check_list_element(val, name, list))
    return property(ret_getter(name), setter)

def ret_property_array_like_typ(name, typ):
    def setter(self, val):
        setattr(self, '_'+name, check_array_like_typ(val, name, typ))
    return property(ret_getter(name), setter)

class DataList(collections.MutableSequence):

    def __init__(self, oktypes, list_owner, *args):
        self.oktypes = oktypes
        self.list_owner = list_owner
        self.list = list()
        self.extend(list(args))
        
    
    def check(self, v):
        if not isinstance(v, self.oktypes):
            raise TypeError("list item {} is not allowed, as it can not be found in {}".format(v, self.oktypes))

    def set_parent(self, v):
        v.parent = self.list_owner

    @property
    def missing_smpl(self):
        ls = sum([step.length_smpl for step in self.list])
        return max(5 * 64 - ls, (-ls) % 64)

    @property
    def missing_smpl_step(self):
        return WaveStep(length_smpl=self.missing_smpl, name='_missing_smpls_')

    def __len__(self):
        l = len(self.list)
        if type(self.list_owner) == SequenceStep:
            l += 1
        return l

    def __getitem__(self, i):
        if type(self.list_owner) == SequenceStep and i == len(self.list):
            return self.missing_smpl_step
        else:
            return self.list[i]

    def __delitem__(self, i):
        del self.list[i]

    def __setitem__(self, i, v):
        self.check(v)
        self.set_parent(v)
        self.list[i] = v

    def insert(self, i, v):
        self.check(v)
        self.set_parent(v)
        self.list.insert(i, v)

    def __str__(self):
        return str(self.list)

    def __iadd__(self, other):
        self.extend(list(other))
        return self.list

    def __radd__(self, other):
        for v in other[::-1]:
            self.insert(0, v)
        return self.list

    def __add__(self, other):
        self.extend(list(other))
        return self.list

    def __imul__(self, other):
        raise NotImplementedError

    def __rmul__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

class Base(object):
    def __init__(self, name='', comment='', length_mus=None,
                 length_smpl=None, sample_frequency=12., parent=None):
        super(Base, self).__init__()
        self.name = name
        self.comment = comment
        self.sample_frequency = sample_frequency
        self.parent = parent

    name = ret_property_typecheck('name', str)
    comment = ret_property_typecheck('comment', str)

    @property
    def parent(self):
        return getattr(self, '_parent', None)

    @parent.setter
    def parent(self, val):
        if val is None or hasattr(self, 'sample_frequency'):
            self._parent = val
        else:
            raise Exception('Parent is type {}, but something is wrong with it.'.format(val))

    @property
    def sample_frequency(self):
        return getattr(getattr(self, '_parent', None), 'sample_frequency', getattr(self, '_sample_frequency', 12.))

    @sample_frequency.setter
    def sample_frequency(self, val):
        self._sample_frequency = check_range(check_type(val, 'sample_frequency', Number), 'sample_frequency', 0.125, 12.)

    def length_mus2length_smpl(self, length_mus):
        return int(round(length_mus * (self.sample_frequency * 1e3)))

    @property
    def length_smpl(self):
        return self.length_mus2length_smpl(self.length_mus) # FIXME here

    @property
    def repeated_length_mus(self):
        return self.length_mus*getattr(self, 'loop_count', 1)

    @property
    def repeated_length_smpl(self):
        return self.length_smpl*getattr(self, 'loop_count', 1)

    @property
    def length_mus_single_smpl(self):
        return 1./(self.sample_frequency*1e3)

    def print_list(self, l, row=0, prefix=''):
        for i in range(len(l)):
            if type(l[i]) == type(np.array([])):
                l[i] = str(l[i])
        print(("{}{:<6}{:<18}{:<8.6f}"+(len(l)-2)*"{:<8}").format(prefix, row, *l))

class WaveFile(Base):
    __doc__ = "Nothing"

    def __init__(self, filepath=None, nonlinear_params=None,
                 scaling_factor=None, part=None, part_str=None, **kwargs):
        super(WaveFile, self).__init__(**kwargs)
        self.part = part
        self.part_str = part_str
        self.nonlinear_params = nonlinear_params
        self.scaling_factor = scaling_factor
        self.filepath = filepath

    @Base.parent.setter
    def parent(self, val):
        Base.parent.fset(self, val)
        self.read_file_data()

    @property
    def part_str(self):
        return self._part_str

    @part_str.setter
    def part_str(self, val):
        if type(val) is str:
            self._part_str = val
        elif val is None:
            self._part_str = '0, -1'
        else:
            raise TypeError('part_str must be of type str')
        self.read_file_data()

    @property
    def part(self):
        p = list(np.array(self.part_str.split(','), dtype=int))
        if p[-1] == -1:
            p[-1] = None
        return p

    @part.setter
    def part(self, val):
        if type(val) is str or val is None:
            self.part_str = val
        else:
            raise Exception('For sake of backwards compatibility part must be string (e.g. (0, -1) or None when set. Getter returns a list')

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, val):
        if val is not None:
            self._filepath = val
            self.read_file_data()

    def read_file_data(self):
        if hasattr(self, '_filepath') and hasattr(self, '_part_str'):
            dr = np.loadtxt(self.filepath)[self.part[0]:self.part[1]]
            self.set_step_length_mus_raw(dr)
            self.data_raw = dr[:, 1:]
            self.update_data()

    def set_step_length_mus_raw(self, dr):
        tol_time = 0.1 * 1 / 12e3
        if np.size(dr, axis=0) == 0:
            raise Exception('Taking part {} results in an empty robust pulse'.format(self.part_str))
        elif np.size(dr, axis=0) > 1:
            if dr[1, 0] - dr[0, 0] > tol_time:
                self.step_length_mus_raw = (dr[1, 0] - dr[0, 0])
            else:
                self.step_length_mus_raw = dr[0, 0]

    @property
    def nonlinear_params(self):
        return self._nonlinear_params

    @nonlinear_params.setter
    def nonlinear_params(self, val):
        if val is not None:
            if isinstance(val, np.ndarray) and len(val.shape) == 2 and val.shape[1] == 2:
                self.calc_amplitudes = self.calc_amplitudes1d(val)
            elif isinstance(val, list) and len(val) == 2:
                self.calc_amplitudes = self.calc_amplitudes2d(val)
            self._nonlinear_params = val
            self.update_data()

    def calc_amplitudes1d(self, nonlinear_params):
        def f(rabi_frequencies):
            ff = scipy.interpolate.interp1d(nonlinear_params[:, 1], nonlinear_params[:, 0], kind='cubic')
            total_rabi = np.sum(rabi_frequencies, axis=1)
            total_amp = ff(total_rabi)
            amplitudes = (total_amp*np.divide(rabi_frequencies.T, total_rabi)).T
            return amplitudes
        return f

    def calc_amplitudes2d(self, nonlinear_params):
        def f(rabi_frequencies):
            fl = []
            for npi in nonlinear_params:
                resonant_axis = 1 if 0.0 in npi[:, 0] else 0
                np_tidy = pd.DataFrame(npi, columns=['amp_left', 'amp_right', 'omega'])
                axes = [set(npi[:, 0]), set(npi[:, 1])]
                axes[resonant_axis].update([0.0])
                axes[not resonant_axis].update([1.0])
                np2d = pd.DataFrame(np.zeros([len(axes[0]), len(axes[1])]), index=axes[0], columns=axes[1])
                np2d.update(np_tidy.pivot_table(values='omega', index=['amp_left'], columns='amp_right'))
                np2d = np2d.sort().sort(axis=1)
                for l, c in enumerate(np.argmin(np2d.values, axis=not resonant_axis)):
                    if resonant_axis == 0:
                        np2d.iloc[l, c:] = np2d.iloc[l, c - 1]
                    elif resonant_axis == 1:
                        np2d.iloc[c:, l] = np2d.iloc[c-1, l]
                fl.append(scipy.interpolate.interp2d(x=np2d.index, y=np2d.columns, z=np2d.values.T, kind='cubic', bounds_error=False))
            al = []
            for rfn, o in enumerate(rabi_frequencies):
                def f(a):
                    return (fl[0](a[0], a[1]) - o[0])**2 + (fl[1](a[0], a[1]) - o[1])**2
                def fconstr(a):
                    x = np.array([a[0], a[1], 1. - a[0] - a[1]])
                    return np.sum(np.take(x, np.where(x < 0)))
                al.append(scipy.optimize.minimize(f, [0.0, 0.0], method='COBYLA',
                                                 constraints=(dict(type='ineq', fun=fconstr)))['x'])
                for i,ff in enumerate(fl):
                    if sum(al[-1]) > 1.0:
                        al[-1] = np.floor(al[-1]*2.**12)/2.**12
                        # fval = ff(al[-1][0], al[-1][1])
                        # if np.abs((fval - o[i])/fval) > 0.005:
                        #     raise Exception('For line {} of rabi_frequencies no suitable amplitudes could be found, '
                        #                     'probably because the rabi frequencies is too high for the current experimental '
                        #                     'conditions'.format(rfn))
            return np.array(al)
        return f

    @property
    def scaling_factor(self):
        return self._scaling_factor

    @scaling_factor.setter
    def scaling_factor(self, val):
        if val is None:
            self._scaling_factor = 1.0
        elif type(val) in [float, int]:
            self._scaling_factor = val
            self.update_data()
        else:
            raise ValueError

    @property
    def number_of_frequencies(self):
        nc = np.size(self.data_raw, 1)
        if nc%3 == 0 or nc >= 6: #assumes, that for 7 columns, two frequencies with [amplitudes, phase, detuning] are given in the file
            return int(nc / 3.0)
        elif nc%2 == 0:
            return int(nc / 2.0)
        else:
            raise Exception("Wave file does not have correct number of columns")

    @property
    def detuning_given(self):
        nc = np.size(self.data_raw, 1)
        if nc%3 == 0 or nc >= 6: #assumes, that for 7 columns, two frequencies with [amplitudes, phase, detuning] are given in the file
            return True
        elif nc%2 == 0:
            return False
        else:
            raise Exception("Wave file does not have correct number of columns")

    @property
    def data_raw_extended(self):
        wfd = self.data_raw
        if not self.detuning_given:
            for i in range(self.number_of_frequencies):
                wfd = np.insert(wfd, 3*(i+1) - 1, 0, axis=1)
        return wfd

    @property
    def number_of_steps(self):
        return np.size(self.data_raw, 0)

    @property
    def rabi_frequencies_raw(self):
        return self.data_raw_extended[:, ::3]

    @property
    def rabi_frequencies(self):
        return self.rabi_frequencies_raw*self.scaling_factor

    @property
    def amplitudes(self):
        return self._amplitudes

    @amplitudes.setter
    def amplitudes(self, val):
        val = np.around(val/__AMPLITUDE_GRANULARITY__)*__AMPLITUDE_GRANULARITY__
        if np.any(val < 0.0):
            raise Exception('The rabi frequencies given in the robust pulse file result \n '
                            'in awg amplitudes smaller than 0 which indicates, \n '
                            'that the given nonlinear_params or the interoplation algorithm are chosen badly.')
        elif np.any(np.sum(val, axis=1) > 1.0):
            raise Exception('The rabi frequencies given in the robust pulse file result \n '
                            'in awg amplitudes larger than 1.\n Probably the rabi frequencies in the robust '
                            'pulse file are too high for the current experimental conditions.')
        else:
            self._amplitudes = val

    def rabi_frequency(self, n_step, n_freq):
        if n_step > self.number_of_steps:
            raise Exception('No parameters given for n_step {}'.format(n_step))
        elif self.number_of_frequencies == 1:
            return self.rabi_frequencies[n_step, 0]
        elif n_freq > self.number_of_frequencies:
            raise Exception('No parameters given for frequency {}'.format(n_freq))
        else:
            return self.rabi_frequencies[n_step, n_freq]

    def set_amplitudes(self):
        self.amplitudes = self.calc_amplitudes(self.rabi_frequencies)

    def set_phases(self):
        self.phases = self.data_raw_extended[:, 1::3]

    def set_detunings(self):
        self.detunings = self.data_raw_extended[:, 2::3]

    def detuning(self, n_step, n_freq):
        if n_step > self.number_of_steps:
            raise Exception('No parameters given for n_step {}'.format(n_step))
        elif self.number_of_frequencies == 1:
            return self.detunings[n_step, 0]
        elif n_freq > self.number_of_frequencies:
            raise Exception('No parameters given for frequency {}'.format(n_freq))
        else:
            return self.detunings[n_step, n_freq]

    def update_data(self):
        for attr in ['_nonlinear_params', '_filepath', '_scaling_factor']:
            if not hasattr(self, attr):
                return
        self.set_amplitudes()
        self.set_phases()
        self.set_detunings()
        self.set_length_mus()

    def amplitude(self, n_step, n_freq):
        if n_step > self.number_of_steps:
            raise Exception('No parameters given for n_step {}'.format(n_step))
        elif self.number_of_frequencies == 1:
            return self.amplitudes[n_step, 0]
        elif n_freq > self.number_of_frequencies:
            raise Exception('No parameters given for frequency {}'.format(n_freq))
        else:
            return self.amplitudes[n_step, n_freq]

    def phase(self, n_step, n_freq):
        if n_step > self.number_of_steps:
            raise Exception('No parameters given for n_step {}'.format(n_step))
        elif self.number_of_frequencies == 1:
            return self.phases[n_step, 0]
        elif n_freq > self.number_of_frequencies:
            raise Exception('No parameters given for frequency {}'.format(n_freq))
        else:
            return self.phases[n_step, n_freq]

    def set_length_mus(self):
        for attr in ['data_raw', 'step_length_mus_raw', '_scaling_factor']:
            if not hasattr(self, attr):
                return
        sls = self.step_length_mus_raw/self.scaling_factor * 1e3 * self.sample_frequency
        relative_error = abs(sls - round(sls))/sls
        if relative_error > 0.0015:
            raise Exception(
                'Mismatch of step_length_mus and duration of one AWG sample (currently {} mus) '
                'leads to a relative error in step duration of {} percent'.format(1/12e3*self.sample_frequency, 100*relative_error))
        else:
            self._length_mus = int(round(sls))/(self.sample_frequency*1e3)*self.number_of_steps

    @property
    def length_mus(self):
        return getattr(self, '_length_mus', 0.0)

    @property
    def step_length_mus(self):
        return self.length_mus/float(self.number_of_steps)

    @property
    def step_length_smpl(self):
        return self.length_mus2length_smpl(self.step_length_mus)

    def print_info(self, prefix=''):
        print(str(type(self)))
        # print prefix + self.part_str + self.scaling_factor
        # for i in range(min(self.number_of_steps, 5)):
        #     print prefix + str(self.step_length_mus) + str(self.data_raw[i])

class BaseWave(Base):

    def samples_amp(self, coherent_offset):
        """
        This is the real value the awg will output, rounded to 12 bit resolution
        """
        return (self.samples_dac(coherent_offset) >> 4)/2047.

    def samples_dac(self, coherent_offset):
        return self.samples_waveform(coherent_offset) - self.samples_marker

class WaveStep(BaseWave):

    def __init__(self, type='wait', phase_offset_type='coherent', frequencies=None, amplitudes=None,
                 phases=None, smpl_marker=False, sync_marker=False, wave_file=None, length_mus=None, length_smpl=None, **kwargs):
        super(WaveStep, self).__init__(**kwargs)
        self.wave_file = wave_file
        self.type = type
        self.phase_offset_type = phase_offset_type
        self.frequencies = np.array([0]) if frequencies is None else frequencies
        self.amplitudes = np.array([0]) if amplitudes is None else amplitudes
        self.phases = np.array([0]) if phases is None else phases
        self.smpl_marker = smpl_marker
        self.sync_marker = sync_marker
        if length_mus is not None:
            self.length_mus = length_mus
        if length_smpl is not None:
            self.length_smpl = length_smpl

    phase_offset_type = ret_property_list_element('phase_offset_type', ['coherent', 'absolute'])
    smpl_marker = ret_property_typecheck('smpl_marker', bool)
    sync_marker = ret_property_typecheck('sync_marker', bool)

    @property
    def length_mus(self):
        if self.type != 'robust' or self.wave_file is None:
            return np.around(getattr(self, '_length_mus', 0.0)/self.length_mus_single_smpl)*self.length_mus_single_smpl
        else:
            return self.wave_file.length_mus

    @length_mus.setter
    def length_mus(self, val):
        self._length_mus = check_range(check_type(val, 'length_mus', Number), 'length_mus', 0, __MAX_LENGTH_SMPL__/(self.sample_frequency*1e3))

    @Base.length_smpl.setter
    def length_smpl(self, val):
        self.length_mus = check_range(check_type(val, 'length_smpl', Number), 'length_smpl', 0, __MAX_LENGTH_SMPL__) / (self.sample_frequency*1e3)

    @property
    def wave_file(self):
        return getattr(self, '_wave_file', None)

    @wave_file.setter
    def wave_file(self, val):
        if isinstance(val, WaveFile) or val is None:
            self._wave_file = val
        else:
            raise Exception('wave_file can be None or of type WaveFile')

    @property
    def type(self):
        return getattr(self, '_type', None)

    @type.setter
    def type(self, val):
        self._type = check_list_element(val, 'type', ['wait', 'sine', 'robust','sinegauss'])
        if self.type == 'robust':
            if self.wave_file is None:
                self.length_mus = 0.
            else:
                self.length_mus = self.wave_file.length_mus

    @property
    def frequencies_str(self):
        return ','.join([str(i) for i in self.frequencies])

    @frequencies_str.setter
    def frequencies_str(self, val):
        self.frequencies = check_type(val, 'frequencies_str', str).split(',')

    @property
    def frequencies(self):
        return self._frequencies

    @frequencies.setter
    def frequencies(self, val):
        self._frequencies = np.array(check_array_like_typ(val, 'frequencies', Number), dtype=float)
        self._frequencies.setflags(write=False)

    @property
    def amplitudes_str(self):
        return ','.join([str(i) for i in self.amplitudes])

    @amplitudes_str.setter
    def amplitudes_str(self, val):
        self.amplitudes = check_type(val, 'amplitudes_str', str).split(',')

    @property
    def amplitudes(self):
        amps = self._amplitudes
        if len(amps) == 1:
            amps = np.zeros(len(self.frequencies)) + amps[0]
        if sum(amps) > 1.:
            raise Exception('Maximum total amplitude of AWG is 1.')
        return amps

    @amplitudes.setter
    def amplitudes(self, val):
        self._amplitudes = np.array(check_array_like_typ(val, 'amplitudes', Number), dtype=float)
        self._amplitudes.setflags(write=False)

    @property
    def phases_str(self):
        return ','.join([str(i) for i in self.phases])

    @phases_str.setter
    def phases_str(self, val):
        self._phases = check_type(val, 'phases_str', str).split(',')

    @property
    def phases(self):
        phases = self._phases
        if len(phases) == 1:
            phases = np.zeros(len(self.frequencies)) + phases[0]
        return phases

    @phases.setter
    def phases(self, val):
        self._phases = np.array(check_array_like_typ(val, 'phases', Number), dtype=float)
        self._phases.setflags(write=False)

    def effective_offset(self, coherent_offset):
        if self.phase_offset_type == 'coherent':
            return coherent_offset
        elif self.phase_offset_type == 'absolute':
            return 0

    def sin(self, samples, start, stop, amps, freqs, phases, length_smpl, offset):
            for i, freq in enumerate(freqs):
                arg = np.arange(offset, length_smpl + offset, dtype=np.float)
                arg *= 2 * np.pi * freq / 1e3 / self.sample_frequency
                arg += np.radians(phases[i])
                s = np.sin(arg)
                s *= amps[i]*2047
                samples[start:stop] += np.int16(s)
#     def sin_gauss(self, samples, start, stop, amps, freqs, phases, length_smpl, offset):
#             for i, freq in enumerate(freqs):
#                 gaussoffset=length_smpl/2.+offset
#                 sigma=1/4.*length_smpl
#                 max_rabi=max(np.transpose(pi3d.rabi_calibration_params)[1])
#                 arg = np.arange(offset, length_smpl + offset, dtype=np.float)
#                 arg *= 2 * np.pi * freq / 1e3 / self.sample_frequency
#                 arg += np.radians(phases[i])
#                 s = np.sin(arg)
#
#                 gauss=np.arange(offset, length_smpl + offset, dtype=np.float)
#                 gauss=(amps[i]*np.exp(-(gauss-gaussoffset)**2/(2.*sigma**2))*max_rabi)
# #                gauss_amp=[]
# #                for entry in gauss:
# #                    gauss_amp.append(pi3d.getAwgAmpFromRabi(entry))
# #                gauss_amp=np.array(gauss_amp)
#                 gauss_amp=pi3d.getAwgAmpFromRabi(gauss)
#                 gauss_amp*=2047
#                 s*=gauss_amp
#                 samples[start:stop] += np.int16(s)

    def samples_waveform(self, coherent_offset):
        samples = np.zeros(self.length_smpl, dtype=np.int16)
        offset = self.effective_offset(coherent_offset)
        if self.type == 'sine':
            self.sin(samples=samples,
                     start=0,
                     stop=self.length_smpl,
                     amps=self.amplitudes,
                     freqs=self.frequencies,
                     phases=self.phases,
                     length_smpl=self.length_smpl,
                     offset=offset)
        elif self.type=='sinegauss':
            self.sin_gauss(samples=samples,
                     start=0,
                     stop=self.length_smpl,
                     amps=self.amplitudes,
                     freqs=self.frequencies,
                     phases=self.phases,
                     length_smpl=self.length_smpl,
                     offset=offset)
        elif self.type == 'robust':
            wf = self.wave_file
            sls = wf.step_length_smpl
            for n_step in range(wf.number_of_steps):
                for n_freq, f in enumerate(self.frequencies):
                    self.sin(samples=samples,
                             start=n_step*sls,
                             stop=(n_step+1)*sls,
                             amps=[wf.amplitude(n_step, n_freq)],
                             freqs=[f + wf.detuning(n_step, n_freq)],
                             phases=[self.phases[n_freq] + np.degrees(wf.phase(n_step, n_freq))],
                             length_smpl=sls,offset=offset+n_step*sls)
        samples = samples << 4
        samples += self.marker
        return samples

    @property
    def samples_smpl_marker(self):
        return np.full(self.length_smpl, self.smpl_marker, dtype=np.int8)

    @property
    def samples_sync_marker(self):
        return np.full(self.length_smpl, self.sync_marker, dtype=np.int8)

    @property
    def marker(self):
        return self.smpl_marker + 2*self.sync_marker

    @property
    def samples_marker(self):
        return np.full(self.length_smpl, self.smpl_marker+2*self.sync_marker, dtype=np.int8)

    @property
    def normalized_avg_sine_power(self):
        if self.type is 'sine':
            return sum(self.amplitudes**2)
        elif self.type is 'robust':
            return sum([self.wave_file.amplitude(i[0], i[1])**2 for i in itertools.product(range(self.wave_file.number_of_steps), range(len(self.frequencies)))])/self.wave_file.number_of_steps
        else:
            return 0

    def print_info(self, row=0, prefix=''):
        if self.type == 'wait':
            l = [self.name, self.length_mus, self.type, int(self.smpl_marker), int(self.sync_marker)]
        elif self.type == 'sine':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.amplitudes, self.phases, int(self.smpl_marker), int(self.sync_marker)]
        elif self.type == 'robust':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.wave_file, int(self.smpl_marker), int(self.sync_marker)]
        self.print_list(l, row=row, prefix=prefix)
        if self.type == 'robust':
            self.wave_file.print_info("    "+prefix)

class BaseWithDataList(BaseWave):

    def __init__(self, data_list=None, loop_count=1, advance_mode='AUTO', **kwargs):
        super(BaseWithDataList, self).__init__(**kwargs)
        self.data_list = [] if data_list is None else data_list
        self.loop_count = loop_count
        self.advance_mode = advance_mode

    loop_count = ret_property_range('loop_count', Number, 0, 2**32-1)
    advance_mode = ret_property_list_element('advance_mode', ['AUTO', 'COND', 'REP', 'SING'])

    @property
    def length_mus(self):
        return np.sum(step.repeated_length_mus for step in self.data_list)

    @property
    def data_list(self):
        return self._data_list

    @data_list.setter
    def data_list(self, val):
        for i in check_type(val, 'data_list', (list, DataList)):
            if not isinstance(i, self.__DATA_LIST_ITEM_TYPE__):
                raise Exception("Elements of property data_list of a {} - instance must be of type {} but is of type {}".format(type(self), self.__DATA_LIST_ITEM_TYPE__, type(i)))
        self._data_list = DataList(self.__DATA_LIST_ITEM_TYPE__, self, *val)

    def samples_waveform(self, coherent_offset):
        samples = np.zeros(self.length_smpl, dtype=np.int16)
        idx = 0
        for i, step in enumerate(self.data_list):
            loop_count = 1 if not hasattr(step, '_loop_count') else step.loop_count
            rls = step.length_smpl*loop_count
            samples[idx: idx+rls] = np.tile(step.samples_waveform(coherent_offset + idx), loop_count)
            idx += rls
        return samples

    @property
    def samples_smpl_marker(self):
        return np.concatenate([step.samples_smpl_marker for step in self.data_list])

    @property
    def samples_sync_marker(self):
        return np.concatenate([step.samples_sync_marker for step in self.data_list])

    @property
    def samples_marker(self):
        return np.concatenate([step.samples_marker for step in self.data_list])

    @property
    def sample_offsets(self):
        return np.cumsum([step.length_smpl for step in self.data_list])

    @property
    def sample_offsets(self):
        return np.cumsum([step.length_smpl for step in self.data_list])

    @property
    def number_of_steps(self):
        return len(self.data_list)

    @property
    def step_name_list(self):
        return [step.name for step in self.data_list]

    def ret_step(self, name):
        snl = self.step_name_list
        if snl.count(name) == 1:
            return self.data_list[snl.index(name)]
        elif snl.count(name) == 0:
            return None
        elif snl.count(name) > 1:
            raise Exception('name {} occured more than once'.format(name))

    @property
    def normalized_avg_sine_power(self):
        return sum([step.repeated_length_mus*step.normalized_avg_sine_power for step in self.data_list])/self.repeated_length_mus

    def print_info(self, row=0, prefix=''):
        self.print_list([self.name, self.repeated_length_mus], row=row, prefix=prefix)
        for i, step in enumerate(self.data_list):
            step.print_info(row=i, prefix="   "+prefix)

class SequenceStep(BaseWithDataList):

    def __init__(self, marker_enable=True, advance_mode='AUTO', reuse_segment=False, reused_sequence_step=None, **kwargs):
        super(SequenceStep, self).__init__(advance_mode=advance_mode, **kwargs)
        self.reuse_segment=reuse_segment
        if reused_sequence_step is not None:
            self.reused_sequence_step = reused_sequence_step
        self.marker_enable = marker_enable

    def __getattribute__(self, name):
        if name not in ['loop_count','_loop_count', 'name', 'advance_mode', 'marker_enable', 'reuse_segment', 'reused_sequence_step'] and getattr(self, 'reuse_segment', False):
            return self.reused_sequence_step.__getattribute__(name)
        else:
            return object.__getattribute__(self, name)

    __DATA_LIST_ITEM_TYPE__ = WaveStep

    marker_enable = ret_property_typecheck('marker_enable', bool) # ONLY SET TO FALSE IF YOU KNOW WHAT YOU ARE DOING

    @property
    def sequencer_table_sid(self):
        return self._sequencer_table_sid

    @property
    def segment_size_bytes(self):
        return 2*self.length_smpl

    def segment_block_data(self, coherent_offset):
        return self.samples_waveform(coherent_offset)

    @property
    def wavestep_list(self):
        return list(itertools.chain(*itertools.repeat(self.data_list, self.loop_count)))



class Sequence(BaseWithDataList):

    def __init__(self, name, advance_mode='COND', **kwargs):
        super(Sequence, self).__init__(name=name, advance_mode=advance_mode, **kwargs)
        self.date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    __DATA_LIST_ITEM_TYPE__ = SequenceStep

    date = ret_property_typecheck('date', str)

    @property
    def missing_smpl(self):
        return self.data_list.missing_smpl

    @property
    def wavestep_list(self):
        return list(itertools.chain(*[step.wavestep_list for step in self.data_list]))

    @property
    def step_list(self):
        step_list = []
        for seq_step in self.data_list:
            step_list.append(seq_step)
            step_list += seq_step.data_list
        return step_list

    def sequence_table_data_block(self, segment_ids):
        if self.number_of_steps != len(segment_ids):
            raise Exception('What happened?')

        sequence_id = 0
        bytes = str(24 * self.number_of_steps)
        bytes_length = str(len(bytes))

        ####
        cmd = '{},{}'.format(sequence_id,'#' + bytes_length + bytes)
        seq_loop_count = struct.pack('I',self.loop_count)
        wave_start_offset = struct.pack('I', 0)
        wave_end_offset = struct.pack('I', 2**32-1)
        advance_map = {'AUTO': 0, 'COND': 1, 'REP': 2, 'SING': 3}
        for i, step in enumerate(self.data_list):
            #init and end sequence markers
            if i == 0:
                control = 2**28
            elif i == self.number_of_steps - 1:
                control = 2**30
            else:
                control = 0
            #marker enable:
            control += step.marker_enable*2**24
            #sequence advance
            control += advance_map[self.advance_mode] * 2**20
            #wave advance
            control += advance_map[step.advance_mode] * 2**16
            control = struct.pack('I', control)
            wave_id = struct.pack('I', segment_ids[i])
            wave_lc = struct.pack('I', step.loop_count)
            data = ( control + seq_loop_count + wave_lc
                   + wave_id + wave_start_offset + wave_end_offset)
            if type(cmd) == str:
                cmd = cmd.encode()
            cmd += data
        return cmd

if __name__ == '__main__':
    import AWG_M8190A_Elements
    wait = AWG_M8190A_Elements.Sequence(name='wait', data_list=[AWG_M8190A_Elements.SequenceStep(data_list=[AWG_M8190A_Elements.WaveStep(length_smpl=3200000)], advance_mode='AUTO', name='wait')])

    # print a.ch[1].sequences
    # print a.ch[1].sequences.number_of_steps
    # print a.ch[1].sequences.data_list[0].number_of_steps
    # import AWG_M8190A_Elements as E
    # import numpy as np
    # wf = E.WaveFile(filepath=r"D:\data\Robust_Pulses\single_pulse_ON03_OFF05_Rabi10_02.dat",
    #              nonlinear_params=np.array([[0.0, 0.0], [0.1, 0.7], [0.2, 1.4], [0.3, 2.1], [1.0, 7.15]]))
    # ws1 = E.WaveStep(type='sine', frequencies=[0.5], amplitudes=[1.], length_mus=1.)
    # ws2 = E.WaveStep(type='sine', frequencies=[0.5], amplitudes=[1.], length_mus=1., phases=[180.])
    # ss = E.SequenceStep(data_list=[ws1, ws2])
    # s = E.Sequence(name='test', data_list=[ss])
    # import matplotlib.pyplot as plt
    # plt.plot(s.samples_dac(0))
    # print len(s.data_list)
    # s.data_list.append(ss)
    # print len(s.data_list)
    # import multi_channel_awg_seq as MCAS
    # mcas = MCAS.MultiChSeq(seq_name='test', ch_dict={'2g': [2]})
    # mcas.sequences['2g'][2].data_list.append(ss)
    # print mcas.sequences['2g'][2].data_list
    #
    # class A(object):
    #     def update_length_mus(self):
    #         print 'i did nothing.'
    # a = A()
    #
    # dl = DataList((int), a, *[])
    # dl = dl + [101, 102]
    # print len(dl)
    # # dl.append(2)
    # print len(dl)

    # s.length_smpl = 320
    # print s.length_mus
    # print s.sample_frequency
    # s.sample_frequency /=2.
    # print s.length_mus
    # print s.length_smpl
    # print s._phases
    # s.type = 'sine'
    # s.frequencies = [123.]
    # s.amplitudes = [1.]
    # print s.samples_dac(0)

    # s.data_list.append(SequenceStep(data_list=[WaveaveStep(length_mus = 12)], loop_count=12))
    # print s.length_mus