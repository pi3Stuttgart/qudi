from __future__ import print_function, absolute_import, division

__metaclass__ = type
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import numpy as np

import datetime
import time
import numpy as np
import struct
import collections
import itertools
import logging
import sys, traceback
from numbers import Number
import types

from . import util

__SAMPLE_FREQUENCY__ = 12e3
__ADVANCE_MODE_MAP__ = {'AUTO': 0, 'COND': 1, 'REP': 2, 'SING': 3}
__AMPLITUDE_GRANULARITY__ = 1 / 2. ** 11
__MAX_LENGTH_SMPL__ = 2e9  # most probably wrong, but a reasonable estimate
__BLM__ = 384. / __SAMPLE_FREQUENCY__
__SAMPLE_DURATION_TOLERANCE__ = 1e-2 / __SAMPLE_FREQUENCY__
__MIN_SEGMENT_LENGTH_MUS__ = 320 / __SAMPLE_FREQUENCY__

def round_length_mus_full_sample(length_mus):
    return np.around(np.array(length_mus) * __SAMPLE_FREQUENCY__) / __SAMPLE_FREQUENCY__



def round_length_mus_to_64_multiple(length_mus):
    def r(lm):
        return np.around(np.array(lm) * __SAMPLE_FREQUENCY__ / 64.) / __SAMPLE_FREQUENCY__ * 64.
    return round_length_mus_full_sample(r(length_mus))

def valid_length_mus(length_mus):
    if not np.allclose(length_mus, round_length_mus_full_sample(length_mus=length_mus), __SAMPLE_DURATION_TOLERANCE__):
        raise Exception(
            'length mus {} is not valid for the current sample_frequency {}'.format(length_mus, __SAMPLE_FREQUENCY__))


def valid_length_smpl(length_smpl):
    if not length_smpl.is_integer():
        raise Exception(
            'length mus {} is not valid'.format(length_smpl))


def length_mus2length_smpl(length_mus):
    valid_length_mus(length_mus=length_mus)
    return np.around(length_mus * __SAMPLE_FREQUENCY__).astype(np.int64)


def length_smpl2length_mus(length_smpl):
    valid_length_smpl(length_smpl)
    return length_smpl / __SAMPLE_FREQUENCY__


def round_to_amplitude_granularity(amplitude):
    return np.around(np.array(amplitude) / __AMPLITUDE_GRANULARITY__) * __AMPLITUDE_GRANULARITY__


class list_repeat(list):
    """
    Allows one wavefile to be used for driving at multiple frequencies without copying it.
    """

    def __getitem__(self, i):
        try:
            return super(list_repeat, self).__getitem__(i)
        except Exception:
            if len(self) != 1:
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)
        return super(list_repeat, self).__getitem__(0)


class DataList(collections.MutableSequence):
    def __init__(self, oktypes, list_owner, *args, **kwargs):
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
        if type(self.list_owner) == SequenceStep:
            self.list_owner.set_write_awg(idx=i, val=v, action='set')

    def insert(self, i, v):
        self.check(v)
        self.set_parent(v)
        self.list.insert(i, v)
        self.list_owner.set_write_awg(idx=i, val=v, action='insert')

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

class Root:
    def __init__(self, **kwargs): pass


class Base(Root):
    def __init__(self, name='', comment='', parent=None, **kwargs):  # sample_frequency=12.,
        super(Base, self).__init__(**kwargs)
        self.name = name
        self.comment = comment
        self.parent = parent

    name = util.ret_property_typecheck('name', str)
    comment = util.ret_property_typecheck('comment', str)

    @property
    def parent(self):
        return getattr(self, '_parent', None)

    @parent.setter
    def parent(self, val):
        self._parent = val

    @property
    def repeated_length_mus(self):
        return self.length_mus * getattr(self, 'loop_count', 1)

    @property
    def repeated_length_smpl(self):
        return self.length_smpl * getattr(self, 'loop_count', 1)

    def ret_list(self, l, row=0, prefix=''):
        # return ("{}{:<6}{:<18}{:<10.6f}" + (len(l) - 2) * "{:<8}").format(prefix, row, *l)
        print(prefix)
        print (row)
        print (*l) 
        return ("{}{:<6} {:<18} {:<10.6f}" + (len(l) - 2) * " {:<8}").format(prefix, row, *l)


    def print_list(self, *args, **kwargs):
        print(self.ret_list(*args, **kwargs))

class WaveFile(Base):
    __doc__ = "Nothing"

    def __init__(self, rp=None, tni=None, filepath=None, filedata=None,
                 scaling_factor=None, part=None, frequency_scaling_factor=None, **kwargs):
        super(WaveFile, self).__init__(**kwargs)
        self.set_part(part)
        self.set_rp(rp)
        self.set_tni(tni)
        self.set_scaling_factor(scaling_factor)
        self.set_frequency_scaling_factor(frequency_scaling_factor)
        self.read_filedata(filepath=filepath, filedata=filedata)
        self.update_data()

    @Base.parent.setter
    def parent(self, val):
        if val is not None:
            Base.parent.fset(self, val)
            if val.type == 'robust':
                self.parent.length_mus = self.length_mus

    @property
    def part(self):
        return getattr(self, '_part', [0, None])

    def set_part(self, val):
        if val is not None:
            if not float(val[0]).is_integer() and (float(val[1]).is_integer() or val[1] is None):
                raise Exception("Error: {}".format(val))
            self._part = val

    @property
    def filepath(self):
        return self._filepath

    def read_filedata(self, filepath=None, filedata=None):
        if (filepath is not None) ^ (filedata is not None):
            if filepath is not None:
                self._filepath = filepath
                filedata = np.loadtxt(self.filepath)
            self.process_filedata(filedata)
        else:
            raise Exception("Error!")

    def process_filedata(self, filedata):
        if filedata is not None:
            dr = filedata[self.part[0]:self.part[1]]
            self.step_length_mus_raw = dr[:, 0]
            self.data_raw = dr[:, 1:]

    @property
    def rp(self):
        return self._rp

    def set_rp(self, val):
        if val is None:
            raise Exception('Error!')
        self._rp = val

    @property
    def tni(self):
        return self._tni

    def set_tni(self, val):
        self._tni = val

    @property
    def scaling_factor(self):
        return self._scaling_factor

    def set_scaling_factor(self, val):
        if val is None:
            self._scaling_factor = 1.0
        elif type(val) in [float, int]:
            self._scaling_factor = val
        else:
            raise ValueError

    @property
    def frequency_scaling_factor(self):
        return self._frequency_scaling_factor

    def set_frequency_scaling_factor(self, val):
        if val is None:
            self._frequency_scaling_factor = 1.0
        elif type(val) in [float, int]:
            self._frequency_scaling_factor = val
        else:
            raise ValueError('Error: {}'.format(val))

    @property
    def number_of_frequencies(self):
        nc = np.size(self.data_raw, 1)
        if nc % 3 == 0 or nc >= 6:  # assumes, that for 7 columns, two frequencies with [amplitudes, phase, detuning] are given in the file
            return int(nc / 3.0)
        elif nc % 2 == 0:
            return int(nc / 2.0)
        else:
            raise Exception("Wave file does not have correct number of columns")

    @property
    def detuning_given(self):
        nc = np.size(self.data_raw, 1)
        if nc % 3 == 0 or nc >= 6:  # assumes, that for 7 columns, two frequencies with [amplitudes, phase, detuning] are given in the file
            return True
        elif nc % 2 == 0:
            return False
        else:
            raise Exception("Wave file does not have correct number of columns")

    @property
    def data_raw_extended(self):
        wfd = self.data_raw
        if not self.detuning_given:
            for i in range(self.number_of_frequencies):
                wfd = np.insert(wfd, 3 * (i + 1) - 1, 0, axis=1)
        return wfd

    @property
    def number_of_steps(self):
        return np.size(self.data_raw, 0)

    @property
    def rabi_frequencies_raw(self):
        return self.data_raw_extended[:, ::3]

    @property
    def rabi_frequencies(self):
        return self.rabi_frequencies_raw * self.scaling_factor * self.frequency_scaling_factor

    @property
    def amplitudes(self):
        return self._amplitudes

    @amplitudes.setter
    def amplitudes(self, val):
        val = np.around(val / __AMPLITUDE_GRANULARITY__) * __AMPLITUDE_GRANULARITY__
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
        self.amplitudes = self.rp.amplitude(tni=self.tni, omega=self.rabi_frequencies)

    def set_phases(self):
        self.phases = self.data_raw_extended[:, 1::3]

    def set_detunings(self):
        self.detunings = self.data_raw_extended[:, 2::3]

    def amplitude(self, n_step, n_freq):
        return self.get_val('amplitudes', n_step, n_freq)

    def phase(self, n_step, n_freq):
        return self.get_val('phases', n_step, n_freq)

    def detuning(self, n_step, n_freq):
        return self.get_val('detunings', n_step, n_freq)

    def get_val(self, name, n_step, n_freq):
        if n_step > self.number_of_steps:
            raise Exception('No parameters given for n_step {}'.format(n_step))
        elif self.number_of_frequencies == 1:
            return getattr(self, name)[n_step, 0]
        elif n_freq > self.number_of_frequencies:
            raise Exception('No parameters given for frequency {}'.format(n_freq))
        else:
            return getattr(self, name)[n_step, n_freq]

    def update_data(self):
        self.set_amplitudes()
        self.set_phases()
        self.set_detunings()
        self.set_length_mus()
        self.precompile_amplitudes_phases()

    def set_length_mus(self):
        self.length_mus = np.sum(self.step_length_mus)
        self.length_smpl = length_mus2length_smpl(self.length_mus)
        if hasattr(self, '_parent') and self.parent.type == 'robust':
            self.parent.length_mus = self.length_mus

    @property
    def step_length_mus(self):
        val = self.step_length_mus_raw / self.scaling_factor
        valid_length_mus(val)
        return val

    @property
    def step_length_smpl(self):
        return length_mus2length_smpl(self.step_length_mus)

    def ret_part(self, start_duration, end_duration):
        if self.part != [0, None] and self.part != [0, self.number_of_steps]:
            raise Exception('Part has already been set, operation not allowed.')
        csd = np.concatenate([[0.0], np.cumsum(self.step_length_mus)])
        part = []
        for key, val in [('start_duration', start_duration), ('end_duration', end_duration)]:
            delta = csd - val
            i = np.where(np.abs(delta) < __SAMPLE_DURATION_TOLERANCE__)
            if len(i) == 1:
                part.append(i[0][0])
            else:
                raise Exception('No more than one element should be found. Found elements: {}'.format(i))
        return part

    def precompile_amplitudes_phases(self):
        self.amplitudes_samples = list_repeat()
        self.phases_samples = list_repeat()
        csls = np.concatenate([np.array([0]), np.cumsum(self.step_length_smpl)])
        for n_freq in range(self.number_of_frequencies):
            self.amplitudes_samples.append(np.empty(self.length_smpl))
            self.phases_samples.append(np.empty(self.length_smpl))
            for n_step in range(self.number_of_steps):
                self.phases_samples[n_freq][csls[n_step]:csls[n_step + 1]] = np.degrees(self.phase(n_step, n_freq))
                self.amplitudes_samples[n_freq][csls[n_step]:csls[n_step + 1]] = self.amplitude(n_step, n_freq)

    def ret_info(self, prefix=''):
        return str(type(self))

    def print_info(self, *args, **kwargs):
        print(self.ret_info(*args, **kwargs))

class BaseWave(Base):

    def __init__(self, **kwargs):
        super(BaseWave, self).__init__(**kwargs)

    def samples_amp(self, coherent_offset):
        """
        This is the real value the awg will output, rounded to 12 bit resolution
        """
        return (self.samples_dac(coherent_offset) >> 4) / 2047.

    def samples_dac(self, coherent_offset):
        return self.samples_waveform(coherent_offset) - self.samples_marker


class WaveStep(BaseWave):
    def __init__(self, type='wait', phase_offset_type='coherent', frequencies=None, amplitudes=None, constant_value=None,
                 phases=None, smpl_marker=False, sync_marker=False, wave_file=None, length_mus=None,
                 length_smpl=None, wf_start=0,  **kwargs):
        super(WaveStep, self).__init__(**kwargs)
        self.length_mus = length_mus
        self.length_smpl = length_smpl
        self.wave_file = wave_file
        self.type = type
        self.phase_offset_type = phase_offset_type
        self.frequencies = np.array([0]) if frequencies is None else frequencies
        self.amplitudes = np.array([0]) if amplitudes is None else amplitudes
        self.constant_value = 0 if constant_value is None else constant_value
        self.phases = np.array([0]) if phases is None else phases
        self.smpl_marker = smpl_marker
        self.sync_marker = sync_marker
        self.wf_start = wf_start

    phase_offset_type = util.ret_property_list_element('phase_offset_type', ['coherent', 'absolute'])
    smpl_marker = util.ret_property_typecheck('smpl_marker', bool)
    sync_marker = util.ret_property_typecheck('sync_marker', bool)

    @property
    def length_mus(self):
        return self._length_mus

    @property
    def length_smpl(self):
        return self._length_smpl

    @length_mus.setter
    def length_mus(self, val):
        if val is not None:
            valid_length_mus(val)
            self._length_mus = util.check_range(util.check_type(val, 'length_mus', Number), 'length_mus', 0, (__MAX_LENGTH_SMPL__-1) / __SAMPLE_FREQUENCY__)
            self._length_smpl = length_mus2length_smpl(self._length_mus)

    @length_smpl.setter
    def length_smpl(self, val):
        if val is not None:
            self._length_mus = util.check_range(util.check_type(val, 'length_smpl', Number), 'length_smpl', 0, __MAX_LENGTH_SMPL__-1) / __SAMPLE_FREQUENCY__
            self._length_smpl = length_mus2length_smpl(self._length_mus)

    @property
    def wave_file(self):
        return getattr(self, '_wave_file', None)

    @wave_file.setter
    def wave_file(self, val):
        if val is not None:
            if isinstance(val, WaveFile):
                val.parent = self
                self._wave_file = val
            else:
                raise Exception('wave_file can be None or of type WaveFile but is {}'.format(val))

    @property
    def type(self):
        return getattr(self, '_type', None)

    @type.setter
    def type(self, val):
        self._type = util.check_list_element(val, 'type', ['wait', 'constant', 'sine', 'robust','gauss',
                                                           'gauss_6ns','gauss_10ns','gauss_2_pulses'])
        if self.type == 'robust' and hasattr(self, '_wave_file'):
            self.length_mus = self.wave_file.length_mus

    @property
    def frequencies(self):
        return self._frequencies

    @frequencies.setter
    def frequencies(self, val):
        self._frequencies = np.array(util.check_array_like_typ(val, 'frequencies', Number), dtype=float)
        self._frequencies.setflags(write=False)

    @property
    def amplitudes(self):
        amps = self._amplitudes
        if len(amps) == 1:
            amps = np.zeros(len(self.frequencies)) + amps[0]
        if sum(amps) - 1.0 > 10 * np.finfo(np.float64).eps:  # larger than 10 times machine precision
            raise Exception("Wavestep {} has amplitudes {} whose sum is larger than one (delta = {}, frequencies {})".format(self.name, self._amplitudes, sum(amps) - 1.0, self.frequencies))
        if np.sum(amps<0): 
            raise Exception("Wave amplitude {} is below 0, which will generate a moduled output".format(self._amplitudes))
        return amps

    @amplitudes.setter
    def amplitudes(self, val):
        self._amplitudes = np.array(util.check_array_like_typ(val, 'amplitudes', Number), dtype=float)
        self._amplitudes.setflags(write=False)

    @property
    def constant_value(self):
        return self._constant_value

    @constant_value.setter
    def constant_value(self, val):
        self._constant_value = util.check_range_type(val, 'constant_value', Number, -(1 + 10 * np.finfo(np.float64).eps), 1 + 10 * np.finfo(np.float64).eps)

    @property
    def phases(self):
        phases = self._phases
        if len(phases) == 1:
            phases = np.zeros(len(self.frequencies)) + phases[0]
        return phases

    @phases.setter
    def phases(self, val):
        self._phases = np.array(util.check_array_like_typ(val, 'phases', Number), dtype=float)
        self._phases.setflags(write=False)

    def effective_offset(self, coherent_offset):
        if self.phase_offset_type == 'coherent':
            return coherent_offset
        elif self.phase_offset_type == 'absolute':
            return 0

    def sin(self, samples, start, amps, freqs, phases, length_smpl, coherent_offset):
        for i, freq in enumerate(freqs):
            arg = np.arange(coherent_offset, length_smpl + coherent_offset, dtype=np.float)
            arg *= 2 * np.pi * freq / __SAMPLE_FREQUENCY__
            arg += np.radians(phases[i] + self.phases[i])
            np.sin(arg, out=arg)
            arg *= amps[i] * 2047
            samples[start:start + length_smpl] += np.int16(arg)


    def gauss(self, samples, start, amps, inv_fwhm, length_smpl):
        """

        """
        # used before 29.3.2022
        data = np.array([-1.187220848286749e-03, 4.828135447051377e-04,
                               -1.570595079336148e-03, 1.519657203184075e-04,
                               -7.996707125387561e-04, -9.518278420321668e-04,
                               8.271197265701059e-05, -1.246645942314141e-03,
                               -4.261105672183860e-04, -4.129308105529412e-04,
                               -1.290559586043219e-03, 1.907771497834774e-04,
                               -1.259821077601645e-03, -4.385490732717420e-04,
                               -1.574702953326387e-04, -1.463174472267478e-03,
                               5.311776108453019e-04, -1.225533197685965e-03,
                               -1.987414331442351e-04, 2.082109532119589e-04,
                               -1.250137331188974e-03, 1.360595952372436e-03,
                               -1.274010038876359e-03, 1.446533564216293e-03,
                               4.583614608476091e-04, 5.094054884033549e-04,
                               2.901866204589467e-03, 7.382345974521427e-04,
                               3.945260940998565e-03, 3.412756494777475e-03,
                               4.346007262495008e-03, 7.047734685909570e-03,
                               6.230908136158720e-03, 1.021797949625769e-02,
                               1.118950399710470e-02, 1.299190805636981e-02,
                               1.822691797730730e-02, 1.817228406686634e-02,
                               2.514525868648966e-02, 2.760635075989784e-02,
                               3.259564341020692e-02, 4.017215480895030e-02,
                               4.338188958010710e-02, 5.384186549397474e-02,
                               5.961783450662857e-02, 6.846428946111142e-02,
                               8.019557584145742e-02, 8.787307152041185e-02,
                               1.017448495488176e-01, 1.141825073807222e-01,
                               1.255812450710469e-01, 1.443882225159034e-01,
                               1.553800342169497e-01, 1.757115377453983e-01,
                               1.927019153728625e-01, 2.085029170215569e-01,
                               2.344185898278406e-01, 2.477124174326581e-01,
                               2.746662469479907e-01, 2.969817866430157e-01,
                               3.129423554619521e-01, 3.512688393560967e-01,
                               3.580522222776337e-01, 3.985423436988085e-01,
                               4.194964721645641e-01, 4.356999745971852e-01,
                               4.881706471099623e-01, 4.816768477354881e-01,
                               5.379402480887451e-01, 5.584364280578269e-01,
                               5.640529312078183e-01, 6.315552090551189e-01,
                               6.453641462811487e-01, 6.391011757791680e-01,
                               6.023233902912025e-01, 5.597180191305234e-01,
                               5.440126473652497e-01, 4.950026803665584e-01,
                               4.862580243887986e-01, 4.428305912248688e-01,
                               4.215047452993929e-01, 4.002942939197273e-01,
                               3.611125172774522e-01, 3.493872895111963e-01,
                               3.149098531184308e-01, 2.951555525686909e-01,
                               2.739984648972335e-01, 2.439223667736971e-01,
                               2.324692382551374e-01, 2.056406661927798e-01,
                               1.896886128834519e-01, 1.731737055234980e-01,
                               1.500423102395862e-01, 1.402191513851385e-01,
                               1.197264472216335e-01, 1.086072155370430e-01,
                               9.681228243750822e-02, 8.207941586825049e-02,
                               7.780038281276332e-02, 6.378097670020084e-02,
                               5.801990249706088e-02, 5.036146009131819e-02,
                               4.129528507352542e-02, 3.838394139068932e-02,
                               3.082260331017087e-02, 2.857700327197328e-02,
                               2.506342584715331e-02, 2.069062621844419e-02,
                               2.064342447800129e-02, 1.670394892664422e-02,
                               1.602463360425435e-02, 1.510209781224914e-02,
                               1.300532349529761e-02, 1.420888436881342e-02,
                               1.294619059022093e-02, 1.279391643505694e-02,
                               1.411984321320433e-02, 1.232111360958776e-02,
                               1.457260511188235e-02, 1.372829583126379e-02,
                               1.440220018590172e-02, 1.556206076565903e-02,
                               1.475908919774308e-02, 1.654078746340604e-02,
                               1.687048163048245e-02, 1.689611825646551e-02,
                               1.902957529330989e-02, 1.780304626589155e-02,
                               1.973444646750805e-02, 1.984986298132285e-02,
                               1.987995960799330e-02, 2.176575588812998e-02,
                               2.081604356756117e-02, 2.247513561444445e-02,
                               2.249466752146313e-02, 2.279051364418394e-02,
                               2.378691722272342e-02, 2.378710596048950e-02,
                               2.423522126985043e-02, 2.540181689808894e-02,
                               2.438092484941018e-02, 2.627631596688861e-02,
                               2.533411765846286e-02, 2.629267506450126e-02,
                               2.666513939759461e-02, 2.621743046983100e-02,
                               2.757458908093041e-02, 2.666697262284525e-02,
                               2.775985067354432e-02, 2.751624069176209e-02,
                               2.765210578795191e-02, 2.817961337814501e-02,
                               2.783707274093527e-02, 2.854466396443029e-02,
                               2.835335166356281e-02, 2.871864317735837e-02,
                               2.875959153660370e-02, 2.898111623853316e-02,
                               2.904441614063746e-02, 2.916665009490122e-02,
                               2.935103370451005e-02, 2.930838925426440e-02,
                               2.949537924357919e-02, 2.959613792591936e-02,
                               2.939003552210203e-02, 3.015590653003138e-02,
                               2.929138340847443e-02, 3.034496042995757e-02,
                               2.965564382875747e-02, 3.014096372348452e-02,
                               3.034978031885796e-02, 2.989438662209618e-02,
                               3.064634063767212e-02, 2.997924955633573e-02,
                               3.048747153499247e-02, 3.038378000914685e-02,
                               3.010636967431244e-02, 3.064601900962012e-02,
                               2.998501425169493e-02, 3.059962688495744e-02,
                               3.026963998222486e-02, 3.036973812075321e-02,
                               3.068479903285581e-02, 3.024636908142493e-02,
                               3.090060878404350e-02, 3.052881078478045e-02,
                               3.095070291466764e-02, 3.079697718412723e-02,
                               3.077684887951113e-02, 3.103133264556676e-02,
                               3.076886320880957e-02, 3.121924107031207e-02,
                               3.101986427117443e-02, 3.110856470476481e-02,
                               3.128963663424317e-02, 3.102285124304649e-02,
                               3.131738756449253e-02, 3.120811089365338e-02,
                               3.122774308593926e-02, 3.162191684173581e-02,
                               3.105322822234963e-02, 3.159594002544566e-02,
                               3.117097711702129e-02, 3.176393599737457e-02,
                               3.179319834065974e-02, 3.166798888980572e-02,
                               3.207099338121262e-02, 3.164836229211677e-02,
                               3.225679218885995e-02, 3.210797021742068e-02,
                               3.217127254727237e-02, 3.259702078741498e-02,
                               3.223958037229752e-02, 3.305310118153576e-02,
                               3.255892015183633e-02, 3.334252982397867e-02,
                               3.313051595868696e-02, 3.337813289557888e-02,
                               3.362440847098369e-02, 3.346764339831276e-02,
                               3.387250416956725e-02, 3.389773171431332e-02,
                               3.370641053075200e-02, 3.415175863343368e-02,
                               3.345709670740268e-02, 3.406954154043584e-02,
                               3.354285975659641e-02, 3.387281262677213e-02,
                               3.370556607160000e-02, 3.374548768735407e-02,
                               3.373327922365550e-02, 3.388166392306644e-02,
                               3.360925929810678e-02, 3.402186918322487e-02,
                               3.360389169488727e-02, 3.395367524276306e-02,
                               3.371542668877341e-02, 3.378337262527319e-02,
                               3.391672670981354e-02, 3.362225928466498e-02,
                               3.405454823457088e-02, 3.349746330191918e-02,
                               3.416865868029258e-02, 3.357359307486561e-02,
                               3.400674382032217e-02, 3.393337939003085e-02,
                               3.362930310548836e-02, 3.435210076853194e-02,
                               3.335650984414699e-02, 3.458859882488390e-02,
                               3.359185765393378e-02, 3.424012274390059e-02,
                               3.426037745738734e-02, 3.361497957792255e-02,
                               3.488155238962121e-02, 3.334098218793631e-02,
                               3.483158399816697e-02, 3.365819136335152e-02,
                               3.415964794263619e-02, 3.432490248260361e-02,
                               3.344348202062990e-02, 3.448177324651668e-02,
                               3.337933661364700e-02, 3.409080534008876e-02,
                               3.378338439983872e-02, 3.353737700241886e-02,
                               3.407137935878446e-02, 3.343941041692204e-02,
                               3.386857289211592e-02, 3.363727068390962e-02,
                               3.342219996130363e-02, 3.383602408362369e-02,
                               3.321515390393526e-02, 3.361091889549563e-02,
                               3.338982249480387e-02, 3.322238611608093e-02,
                               3.362822816359687e-02, 3.290817389204112e-02,
                               3.374252408754664e-02, 3.284834574751514e-02,
                               3.357625694356343e-02, 3.298659986297680e-02,
                               3.330398465227426e-02, 3.312603749113500e-02,
                               3.307733825995046e-02, 3.313018978847630e-02,
                               3.304290943127367e-02, 3.316077051433232e-02,
                               3.310122304031424e-02, 3.326593979860049e-02,
                               3.320911946415341e-02, 3.337329302133726e-02,
                               3.324967224748260e-02, 3.364085318084925e-02,
                               3.322504006252641e-02, 3.393151887072261e-02,
                               3.328553693620566e-02, 3.414993461442831e-02,
                               3.357040565772779e-02, 3.410069188683598e-02,
                               3.413894662171004e-02, 3.386827712677275e-02,
                               3.466105795393684e-02, 3.384987702672126e-02,
                               3.467474780073154e-02, 3.423903264433187e-02,
                               3.443906062472722e-02, 3.471421493722900e-02,
                               3.410161954946701e-02, 3.501428280782459e-02,
                               3.402498751891360e-02, 3.501491077394207e-02,
                               3.424909033922704e-02, 3.477526381200626e-02,
                               3.460585282892871e-02, 3.451916134056977e-02,
                               3.478200286198209e-02, 3.440952814515681e-02,
                               3.474914313585543e-02, 3.448990802011982e-02,
                               3.454789387264701e-02, 3.454116525452236e-02,
                               3.438096358490079e-02, 3.454866506240563e-02,
                               3.419359627388727e-02, 3.438946642053603e-02,
                               3.418042208915815e-02, 3.422409498769011e-02,
                               3.416834154160663e-02, 3.436795229838243e-02,
                               3.388239054676346e-02, 3.462439403325659e-02,
                               3.347634344094966e-02, 3.469263663782566e-02,
                               3.354043524343399e-02, 3.420944351972984e-02,
                               3.398197244099875e-02, 3.359083872388073e-02,
                               3.437820688103754e-02, 3.344779248720017e-02,
                               3.425555697176469e-02, 3.380463843325388e-02,
                               3.361979414535057e-02, 3.449325674409356e-02,
                               3.309110273192550e-02, 3.477400131983227e-02,
                               3.316883401300161e-02, 3.454990561283709e-02,
                               3.371587799488544e-02, 3.412294044248113e-02,
                               3.426753524739025e-02, 3.388614321911240e-02,
                               3.443587781774957e-02, 3.411707675195387e-02,
                               3.432663305964054e-02, 3.447452412938973e-02,
                               3.422118782506291e-02, 3.465777251594818e-02,
                               3.428444611385943e-02, 3.455241744213355e-02,
                               3.459664463897635e-02, 3.430990453352706e-02,
                               3.493005205258781e-02, 3.414040129262881e-02,
                               3.506482384028910e-02, 3.427124116588567e-02,
                               3.489262295016174e-02, 3.464002963924086e-02,
                               3.446025647539284e-02, 3.494323310030659e-02,
                               3.413889080384189e-02, 3.495917470829300e-02,
                               3.416668444551071e-02, 3.468591118316260e-02,
                               3.443776863194185e-02, 3.431424211129673e-02,
                               3.455988060207296e-02, 3.433511480612023e-02,
                               3.425761119854711e-02, 3.472678385861751e-02,
                               3.388053160900312e-02, 3.497223687177688e-02,
                               3.396864949541722e-02, 3.469844278766761e-02,
                               3.452670784877116e-02, 3.422903138820844e-02,
                               3.505664855164936e-02, 3.413682892847824e-02,
                               3.501385140272600e-02, 3.467226010953377e-02,
                               3.446833192932739e-02, 3.537578680325849e-02,
                               3.424582265861417e-02, 3.542063347291982e-02,
                               3.473157847887778e-02, 3.500395496816594e-02,
                               3.527956468212912e-02, 3.474612912967798e-02,
                               3.553270958271387e-02, 3.484753394974442e-02,
                               3.551019189257812e-02, 3.507201831631156e-02,
                               3.547010763766056e-02, 3.517521602408802e-02,
                               3.560587944514344e-02, 3.515305893273550e-02,
                               3.553033966094291e-02, 3.542770249150801e-02,
                               3.535849182230862e-02, 3.553514224021543e-02,
                               3.546214622480456e-02, 3.534243011214805e-02,
                               3.579446872783990e-02, 3.519519788962452e-02,
                               3.591039930922465e-02, 3.541775767428191e-02,
                               3.528980277571380e-02, 3.614923854239279e-02,
                               3.482687957692427e-02, 3.616452572173329e-02,
                               3.537259416044980e-02, 3.533826691588583e-02,
                               3.627226201745910e-02, 3.423502106182098e-02,
                               3.634959376129698e-02, 3.481847085182868e-02,
                               3.542398985871489e-02, 3.593774678925047e-02,
                               3.476658486982215e-02, 3.582990314086372e-02,
                               3.545358423877494e-02, 3.498993803680634e-02,
                               3.597205036018003e-02, 3.446155855797314e-02,
                               3.581126231987367e-02, 3.478015905080063e-02,
                               3.443810893728961e-02, 3.569590158872352e-02,
                               3.432753190054284e-02, 3.544836843313778e-02,
                               3.543386307485829e-02, 3.475414975257572e-02,
                               3.623532577187224e-02, 3.498589418669603e-02,
                               3.601035760359522e-02, 3.571598482439355e-02,
                               3.534934671238836e-02, 3.653479201847239e-02,
                               3.514669636147733e-02, 3.647867000742373e-02,
                               3.598325202148640e-02, 3.558951505402629e-02,
                               3.682573897489994e-02, 3.534076002299529e-02,
                               3.636272692795870e-02, 3.655068671208204e-02,
                               3.493682960177780e-02, 3.779155472817561e-02,
                               3.483490749431894e-02, 3.678881243506238e-02,
                               3.686808328654698e-02, 3.468309812080880e-02,
                               3.824179402913956e-02, 3.470961121452373e-02,
                               3.650575961292887e-02, 3.749696733203377e-02,
                               3.338198185796528e-02, 3.937055618169764e-02,
                               3.310853107320778e-02, 3.700959517482681e-02,
                               3.704612693606451e-02, 3.203443339179724e-02,
                               4.071226135228286e-02, 3.104691103039200e-02,
                               3.739743903050310e-02, 3.793245311181700e-02,
                               2.866205938771973e-02, 4.474093222324696e-02,
                               2.873628504976361e-02, 3.015069375755837e-02,
                               6.145563946363480e-02])


        data = data[self.wf_start:]
        if length_smpl < np.size(data):
            N = length_smpl
        else:
            N = np.size(data)
        # print('length_smpl ', length_smpl)
        # print('N ', N)
        # print('start ', start)
        res = np.zeros(length_smpl)
        res[0:N] = data[0:N]
        samples[start:start + length_smpl] = np.int16(np.round(res * amps * 2047, 1))


        # print('length_smpl ', length_smpl)
        # print('N ', N)
        # print('start ', start)
        #
        # res[0:N] = data[start:N]
        # samples[0:0 + length_smpl] = np.int16(np.round(res * amps * 2047, 1))


    def gauss_2_pulses(self, samples, start, amps, inv_fwhm, length_smpl):
        """

        """

        # data = np.array([-4.610970857527044858e-02,-6.126813234247070576e-03,-1.341811312972887062e-02,-2.335288531591001721e-02,-1.598154023173111241e-02,-1.192942805050370599e-02,-1.777954793019742921e-02,-1.952513954784329889e-02,-1.641152669528820815e-02,-1.687037622725566163e-02,-1.827059240161742898e-02,-1.609923104673754296e-02,-1.501409042979431376e-02,-1.728183443008354456e-02,-1.823143091646705835e-02,-1.716674507000364239e-02,-1.697595944941361623e-02,-1.733001076441499297e-02,-1.680256775238564773e-02,-1.674092979625666638e-02,-1.725021375632914897e-02,-1.693754282266250050e-02,-1.645898567229149567e-02,-1.696364414475200894e-02,-1.719343953965888488e-02,-1.647031385028132136e-02,-1.610599362764154538e-02,-1.660462205811580327e-02,-1.686027084250737995e-02,-1.612316170768544193e-02,-1.519690696191768747e-02,-1.463236179542415361e-02,-1.449772199081176410e-02,-1.456288968814337809e-02,-1.393092607592382251e-02,-1.209042851139170358e-02,-1.043405314436063672e-02,-9.931746062629004390e-03,-8.807304740583533909e-03,-6.447740941275898786e-03,-4.312668072980888230e-03,-2.543383309160227122e-03,-1.873239396736836810e-05,3.292173277742670243e-03,6.392992681303266526e-03,9.872805242392103039e-03,1.440554848877182922e-02,1.853581815261793123e-02,2.227013858747900130e-02,2.837918608953574409e-02,3.532511917883404684e-02,3.969879150911393567e-02,4.539171031174849685e-02,5.526453850791975680e-02,6.224418386858204810e-02,6.647017639900566766e-02,7.776570145748978868e-02,8.994677373437517942e-02,9.311756983581755132e-02,1.007948165441109600e-01,1.194443226534057795e-01,1.282989136330174584e-01,1.281049683147732210e-01,1.444184456545461182e-01,1.669259828779971477e-01,1.682719290347610697e-01,1.684003784550684446e-01,1.958389942367213254e-01,2.193835192071081353e-01,2.084924671557258358e-01,2.086563385538391657e-01,2.527318868305432065e-01,2.860594541322840079e-01,2.513292877856522223e-01,2.234801754178154243e-01,2.231910823940019273e-01,2.147298805986296022e-01,1.943992082506731389e-01,1.855373665172416198e-01,1.844114464315786128e-01,1.741335694650869292e-01,1.581011926527048084e-01,1.464612310527161065e-01,1.375224758428913174e-01,1.279106976737468537e-01,1.195075141904260035e-01,1.124145438026339372e-01,1.042271881882374657e-01,9.507059611725370007e-02,8.623771166004393085e-02,7.792902401353625497e-02,7.048743281458058618e-02,6.445655747140419112e-02,5.902392984064849107e-02,5.299409437433842684e-02,4.716346675891044948e-02,4.240244027934682997e-02,3.790001683047996422e-02,3.340189767196481696e-02,2.990840566304822992e-02,2.726556610288011218e-02,2.400769175392282809e-02,2.040870721522275791e-02,1.782213236566308409e-02,1.476093722611250547e-02,1.694570017485887148e-02,1.410210779007631948e-02,1.047624260870548725e-02,9.633259168789100671e-03,1.019920999369575317e-02,8.309142086123386464e-03,7.707421801121711394e-03,7.640122062500167427e-03,7.194261195203948897e-03,6.512460328683281410e-03,6.155484203282625237e-03,6.160820805415411459e-03,6.073224083868736939e-03,6.086847915268498409e-03,6.198146124981453869e-03,6.220369362879991579e-03,6.174099386581786281e-03,6.254608488465062711e-03,6.498082159698795497e-03,6.605626097591376679e-03,6.495377394372065481e-03,6.516025049726532729e-03,6.789509901921873120e-03,6.867485998702074594e-03,6.840355703294342254e-03,6.908115610795770994e-03,7.080071945053164478e-03,7.112754306946233833e-03,7.090097786632529146e-03,7.178528465263040760e-03,7.368352979981623516e-03,7.347852363043357732e-03,7.257432187905115371e-03,7.324559263900473974e-03,7.354660383288774694e-03,7.151397144650873186e-03,7.062018760408754828e-03,7.123585033657009458e-03,7.140301879010000144e-03,7.048300776904336401e-03,7.117846958066614479e-03,7.227510803491174127e-03,7.076564479147582319e-03,6.879424281407313553e-03,6.855925069408875042e-03,7.027889205535669051e-03,7.002213040492840171e-03,6.924177207452073858e-03,7.023755624140279839e-03,7.012563128033632610e-03,6.879997399267827676e-03,6.875761836766871270e-03,7.028004158375338907e-03,7.124308191471319038e-03,7.203856145280213008e-03,7.274717203085707962e-03,7.350656752630711777e-03,7.340395381953215143e-03,7.277034564038550174e-03,7.387729658018741923e-03,7.374472408347545853e-03,7.390364145943958268e-03,7.516461490011396365e-03,7.599856418284736161e-03,7.650039988106105589e-03,7.697556735149261274e-03,7.695542331443852059e-03,7.629962443390854963e-03,7.616549081353832761e-03,7.736565194905127563e-03,7.916657101521293663e-03,7.812626390445918251e-03,7.713926798702960830e-03,7.826367379123304671e-03,7.883098000654405191e-03,7.789791924523190546e-03,7.796783989752211451e-03,7.930577529662908437e-03,8.024425817292533958e-03,7.926044857720818126e-03,7.935629782033284951e-03,8.053316927810458270e-03,8.045967452672945358e-03,7.970646213204571687e-03,7.972804237367436472e-03,8.144223971234685472e-03,8.200830799768679333e-03,8.173502005168770818e-03,8.148533978467166136e-03,8.071707564974293925e-03,8.101106187705556239e-03,8.240509983429795959e-03,8.469973999272522799e-03,8.611196134861004090e-03,8.564965282397278210e-03,8.471087606111283100e-03,8.573916250758305616e-03,8.842742512666463758e-03,9.156341371143600361e-03,9.309677657649300178e-03,9.388185235203225232e-03,9.529762617063227553e-03,9.581292526635275253e-03,9.726443204782025953e-03,1.003217201260437133e-02,1.040321699911857765e-02,1.057319868672130028e-02,1.053672737902984491e-02,1.063523578548761749e-02,1.082471152226780614e-02,1.091088766204468576e-02,1.089147903506327252e-02,1.088061218321897082e-02,1.089820678832239577e-02,1.092470455970770936e-02,1.094692337961914071e-02,1.091676004290663589e-02,1.092083781876129582e-02,1.098695292141092274e-02,1.106663918521565496e-02,1.105197096835752908e-02,1.099956713016200967e-02,1.103102600849844954e-02,1.110353105190693516e-02,1.109851086429050442e-02,1.102535757964545095e-02,1.104020912766440210e-02,1.115487430710008360e-02,1.107516616562042970e-02,1.100144918738327204e-02,1.109179939658094111e-02,1.113242904595269749e-02,1.112235433513995321e-02,1.123005308803495979e-02,1.122321512594580580e-02,1.111355018962217889e-02,1.116387554773828894e-02,1.116495899946907955e-02,1.105993203259040929e-02,1.089558792455744274e-02,1.092760710365052283e-02,1.089758894047220678e-02,1.058721413375764836e-02,1.030247311346607977e-02,1.036681982010047645e-02,1.027272428772604308e-02,9.535199213827141168e-03,9.182880279425612025e-03,9.833329974621801695e-03,8.237863192211257110e-03,8.974243799585399431e-03,8.747198280954540314e-03,6.755281397392345726e-03,7.838572340012990233e-03,6.857166908239996708e-03,6.095302934533466596e-03,5.877375472156004185e-03,5.387202789225336783e-03,4.657607883066938390e-03,4.052562388793954501e-03,3.439533641103488699e-03,2.650076708284633976e-03,1.933616490799617508e-03,1.229686378858219336e-03,3.463182001491382843e-04,-5.877038621140232575e-04,-1.345811616370509245e-03,-1.983958358660288610e-03,-2.914511516663123147e-03,-4.094560812359577737e-03,-5.125085372969506552e-03,-5.769706611115840537e-03,-6.153910983945059393e-03,-6.522839403377831032e-03,-6.712630055586998358e-03,-6.850883030307172022e-03,-7.190018180046203917e-03,-7.517713392439613444e-03,-7.387361412402390290e-03,-6.841228187547510921e-03,-6.194510453874296947e-03,-5.546202757684632993e-03,-4.805133354546869788e-03,-4.027629593684901171e-03,-3.374002938294951796e-03,-2.838434123421584073e-03,-2.184597307595723559e-03,-1.442856001687346183e-03,-7.431833205015386280e-04,-2.354783499681415069e-05,6.153894292643075168e-04,1.246290608376369406e-03,1.940645892907587235e-03,2.496493002499695999e-03,3.019096653683300390e-03,3.535101277351419304e-03,4.109228689118183883e-03,4.609407471880688431e-03,5.105025426469727602e-03,5.540621490188053257e-03,5.932826323834980951e-03,6.452014182219813730e-03,6.807050418451398785e-03,7.046141158540981247e-03,7.384407155570117502e-03,7.786550003499544126e-03,8.114752964562875134e-03,8.361361318126227932e-03,8.728966511116655405e-03,8.610524299686945007e-03,8.997416424925403292e-03,9.754229700109326093e-03,9.553439182478648886e-03,9.658425289161026717e-03,1.029332753738751959e-02,1.065908191521699848e-02,1.039935096605201087e-02,1.018628758298771760e-02,1.058657231207529165e-02,1.105570038465361789e-02,1.099521953971989256e-02,1.060154647321476934e-02,1.055792818810695304e-02,1.088048243504654948e-02,1.102608308830275996e-02,1.089989413371851741e-02,1.087286766857007217e-02,1.097813153918195464e-02,1.097637145649932831e-02,1.095016687536045849e-02,1.105537052360976331e-02,1.117886197849537154e-02,1.118594525425636345e-02,1.116624051988443327e-02,1.124940296323473365e-02,1.131589469199317105e-02,1.127260509750636561e-02,1.119054061798619749e-02,1.126882573834925988e-02,1.140410683912348837e-02,1.137821832408645283e-02,1.118744442655239535e-02,1.120944458712839521e-02,1.135332640670763497e-02,1.131241638155814841e-02,1.116356319215882492e-02,1.121616243696280622e-02,1.137378734776997233e-02,1.129828801513991024e-02,1.109041903439653316e-02,1.115766328569611950e-02,1.123982716926157088e-02,1.127435465034098624e-02,1.133243475327722245e-02,1.131651397422991923e-02,1.123585565188719645e-02,1.121976576659961151e-02,1.129175899811130784e-02,1.134114605313449840e-02,1.129775008862872986e-02,1.128235458194424938e-02,1.138312736974612070e-02,1.136069036004539595e-02,1.142071145554217002e-02,1.151003747951548188e-02,1.160172665926506239e-02,1.154641120805065778e-02,1.156560210039253925e-02,1.168194000109241439e-02,1.169958659010430189e-02,1.171804335027713979e-02,1.179937884088498243e-02,1.183037848996732963e-02,1.184828463678082484e-02,1.185724935129642277e-02,1.200506579908192616e-02,1.200794146113811321e-02,1.199961215156987969e-02,
        #                  1.210274558572099757e-02,1.218729832322906249e-02,1.230760526858500244e-02,1.229622234664857171e-02,1.232394706440672304e-02,1.247414458382598533e-02,1.244246528478684492e-02,1.250932271303105935e-02,1.269673511719909310e-02,1.276177752641493961e-02,1.275788372171739703e-02,1.282482755106696334e-02,1.292619897881601247e-02,1.291416162295729378e-02,1.300644611236629992e-02,1.315220011647312039e-02,1.324022287584372855e-02,1.312025193345503667e-02,1.319149542949940752e-02,1.340506248131227186e-02,1.339152437914791459e-02,1.328280599755997382e-02,1.335522476871840725e-02,1.350707957028324940e-02,1.350502893360740718e-02,1.341157590507763807e-02,1.356129348584497567e-02,1.367197876467003172e-02,1.350075155569342190e-02,1.343714752480422263e-02,1.360984199372418033e-02,1.372167596868312071e-02,1.378659712505370984e-02,1.362477274034044721e-02,1.361340694803284471e-02,1.377461372367108118e-02,1.385305310212942530e-02,1.379124510951322373e-02,1.379394833068160742e-02,1.387919513959053573e-02,1.395232334811153871e-02,1.395233113173161184e-02,1.395321900183274337e-02,1.400173728827218758e-02,1.409580213493751184e-02,1.406340161120196372e-02,1.408931317579418911e-02,1.421338918472296944e-02,1.427442168191483951e-02,1.425691438118390636e-02,1.436068199905476267e-02,1.440803568798207195e-02,1.440026136243546633e-02,1.435901316551945958e-02,1.453436515689811998e-02,1.475294970746646867e-02,1.466502546508751705e-02,1.453276124353505491e-02,1.469442670496278955e-02,1.491617902722842080e-02,1.488679513032144415e-02,1.475152424994882229e-02,1.478286423332464579e-02,1.497220236231062464e-02,1.491017146643712835e-02,1.479090418972656314e-02,1.490483245719248853e-02,1.501294959223617442e-02,1.490002131394980653e-02,1.485510783336663893e-02,1.490098184219105712e-02,1.492572956121609833e-02,1.504471782182627282e-02,1.513015383780990340e-02,1.506670777348086653e-02,1.503790004199156982e-02,1.516714869849482283e-02,1.522607338782398963e-02,1.510492163332747065e-02,1.516150779583110876e-02,1.534531093927031173e-02,1.540198788774877967e-02,1.542212660424369802e-02,1.540540298947320509e-02,1.538929073189574184e-02,1.534903443115208377e-02,1.544178676095126282e-02,1.551855401746945334e-02,1.555802772477075414e-02,1.556704893930936640e-02,1.561733069720361473e-02,1.562105675350406418e-02,1.547602112880513622e-02,1.557081155845567791e-02,1.581432795889645138e-02,1.591533592517839490e-02,1.588669621551504207e-02,1.591219253037903097e-02,1.600559979523045323e-02,1.611490963333439205e-02,1.615753002240306185e-02,1.617869163132088992e-02,1.625790312378915664e-02,1.629828965284991701e-02,1.626976893651471343e-02,1.629248122563526843e-02,1.646750856587753456e-02,1.669709338945276483e-02,1.667029701568578659e-02,1.652997864837668987e-02,1.663058490860070196e-02,1.694039401251884458e-02,1.688290154787065733e-02,1.679383246254322407e-02,1.696364639621230491e-02,1.705496855639822631e-02,1.709236782284516767e-02,1.709722005264252553e-02,1.715462180168741621e-02,1.723782666864939056e-02,1.734086350694062986e-02,1.745800577738352774e-02,1.758400263606495900e-02,1.753920392262849418e-02,1.753181835466757765e-02,1.766466584366890163e-02,1.771275253743934824e-02,1.775910168027776057e-02,1.789591995976062486e-02,1.795617338764898124e-02,1.793899956019158817e-02,1.788247204577736102e-02,1.793103559829384297e-02,1.801669098705688948e-02,1.807171551762100717e-02,1.815325952196299164e-02,1.809186942002985812e-02,1.801955188187560897e-02,1.813350271901850372e-02,1.818537016009756993e-02,1.817261884559449869e-02,1.808479084950680507e-02,1.815623345754463838e-02,1.826823906314387069e-02,1.814649403575395795e-02,1.808031806300680264e-02,1.824842137377430049e-02,1.830528009441493784e-02,1.827618303616788606e-02,1.824737595161673651e-02,1.825245229677991202e-02,1.845433049511796542e-02,1.854357046308584625e-02,1.846720201298285291e-02,1.843447803624211415e-02,1.850158969976825607e-02,1.865413482816794324e-02,1.861342846756201125e-02,1.852037390530575714e-02,1.869126949152218747e-02,1.883084207655665032e-02,1.881811405695225231e-02,1.886954202851538753e-02,1.902617031539908382e-02,1.906237341066721255e-02,1.907620060945914089e-02,1.923651585810967277e-02,1.930324797795572936e-02,1.930160748732151835e-02,1.941908335920769849e-02,1.950729450822004385e-02,1.942900495361350385e-02,1.949623521607971727e-02,1.961279682348552461e-02,1.973560852478941849e-02,1.980859334137710995e-02,1.978266448134179817e-02,1.985851553088926677e-02,1.984668200778481884e-02,1.991267050897558080e-02,2.014101614170766066e-02,2.016718694899065009e-02,2.004431888170164072e-02,2.000922073692120232e-02,2.020247135790812984e-02,2.017514695324045676e-02,2.007261308284620169e-02,2.010664433525566688e-02,2.021860726456165686e-02,2.026720885385938434e-02,2.016976669850029449e-02,2.017066838481045010e-02,2.015739774214520344e-02,2.021929593750488793e-02,2.015165637016240116e-02,2.003548371140067424e-02,1.997356880266875148e-02,1.999756921151962449e-02,2.002738396590112921e-02,1.992446174218302779e-02,1.980350001278177383e-02,1.986509033250305131e-02,1.993756509284451070e-02,1.986685186859083949e-02,1.985614736023589774e-02,1.982616106101592682e-02,1.990089368464497202e-02,1.993610662654781915e-02,1.991992368905970423e-02,1.995333919024596184e-02,2.003502217845303662e-02,2.002486189947276507e-02,1.987864595347254085e-02,1.988851360973849236e-02,2.010759796642870231e-02,2.018546882667864029e-02,2.013174342661779026e-02,2.013663178412494759e-02,2.021593286386354563e-02,2.023278945655238026e-02,2.022153786173116682e-02,2.028434448060414952e-02,2.033398920149015118e-02,2.028688397115662595e-02,2.033750435970370710e-02,2.046327140598944161e-02,2.045984547021294925e-02,2.036260825558636189e-02,2.050490757434847780e-02,2.054013621121513269e-02,2.045738298077677889e-02,2.044748613466544976e-02,2.064907902739301221e-02,2.066111546679112385e-02,2.053780234430680959e-02,2.059307531378961817e-02,2.068153998170056337e-02,2.057798233217722483e-02,2.049449839258156089e-02,2.062918529494695008e-02,2.059605772598243484e-02,2.057610499554777747e-02,2.076548210211263262e-02,2.070004714062106954e-02,2.058222541566656280e-02,2.067577165116255000e-02,2.068431006533806224e-02,2.064459705238951698e-02,2.058439959112031564e-02,2.062291602692443993e-02,2.067493429019976250e-02,2.051704050921080227e-02,2.035657897821065848e-02,2.052649566985146473e-02,2.076528921013408649e-02,2.060508200363714987e-02,2.053433917425747518e-02,2.070101076763612019e-02,2.066471818211312525e-02,2.062242076699209725e-02,2.084342956036708619e-02,2.094024263595662197e-02,2.073591535080857723e-02,2.072285100366424646e-02,2.101030292217633336e-02,2.105919288528071073e-02,2.091979134173757582e-02,2.096068297768602373e-02,2.121719334198067519e-02,2.114750740028183834e-02,2.099062851776893959e-02,2.124568387580592563e-02,2.147322347507069421e-02,2.136862131954997412e-02,2.140471396278505536e-02,2.156078423894391624e-02,2.148083226996447617e-02,2.137009171681871281e-02,2.151301641708857834e-02,2.165487347427751813e-02,2.153134678463110643e-02,2.146296371902854314e-02,2.171961771216417147e-02,2.186092381744217730e-02,2.161135126050689123e-02,2.152177250133488831e-02,2.179095468200518623e-02,2.180800564024842902e-02,2.159513652374575599e-02,2.168871499079308776e-02,2.196876918983973331e-02,2.180687408074325970e-02,2.149991336840611708e-02,2.170773060010627864e-02,2.203371837092014951e-02,2.181277803338770374e-02,2.160727325832071527e-02,2.190347121473117456e-02,2.199490769545988517e-02,2.156541561334376217e-02,2.162544963701622594e-02,2.197241715583619914e-02,2.169980742597853521e-02,2.150084979866268009e-02,2.189843197662175861e-02,2.206402235469757597e-02,2.151785460623793084e-02,2.165757486312587868e-02,2.226589242632252830e-02,2.209805059057865298e-02,2.163845163386465473e-02,2.208243311736552555e-02,2.275728515663625121e-02,2.264559893736986171e-02,2.254362178360519095e-02,2.331841629375194444e-02,2.391741780730123959e-02,2.374286220591924346e-02,2.437291326975866632e-02,2.569094192369912946e-02,2.611356206885151812e-02,2.676324291602508523e-02,2.822377124564854137e-02,2.972960571655978643e-02,3.085174734897654786e-02,3.236683449351833441e-02,3.453994491607101369e-02,3.677487544239062961e-02,3.910727585805379852e-02,4.203350453583824115e-02,4.519565986307996774e-02,4.824271278734815899e-02,5.221905655753642655e-02,5.697479185302802701e-02,6.111862050020457071e-02,6.580885944472217308e-02,7.255464058407226635e-02,7.846931595232024825e-02,8.294267974327716730e-02,9.081124720301095299e-02,1.003682794068662537e-01,1.051581866536124427e-01,1.116100633868015168e-01,1.252503383540418957e-01,1.339136808703097481e-01,1.364336418764486025e-01,1.496849293659864022e-01,1.669530356517577030e-01,1.698663052354531799e-01,1.743753250232979168e-01,1.968243908492337824e-01,2.120017435622984225e-01,2.079217425138853992e-01,2.189094095410903384e-01,2.513318064325824608e-01,2.601702602423536237e-01,2.453323227756885050e-01,2.651797367444666542e-01,3.151229877058428497e-01,3.193972415159876954e-01,2.790432979722464735e-01,2.638744434260752447e-01,2.646967903000920219e-01,2.493552296919204214e-01,2.315202302596118256e-01,2.278503240696084231e-01,2.242222463496043872e-01,2.103520919706559911e-01,1.957097325075488892e-01,1.858554139995705345e-01,1.763975862644217296e-01,1.670341040479249861e-01,1.598896573305326752e-01,1.523877903022783920e-01,1.432187015026979426e-01,1.350750549765252773e-01,1.262927322576932743e-01,1.174281027424922408e-01,1.107579583574779258e-01,1.068899006436014737e-01,9.859029643246512709e-02,9.403427125298881306e-02,8.877051922881165624e-02,8.367387642922752278e-02,7.956072208885274499e-02,7.545819423159529082e-02,
        #                  7.180574911908700619e-02,6.932475063477087918e-02,6.648822049575617288e-02,6.248228074653330161e-02,5.968531514493010531e-02,5.935182372493827407e-02,5.884976479994613596e-02,5.619682169046166104e-02,5.350042920759705972e-02,5.273003097049130949e-02,5.262668341919841952e-02,5.166817301099124737e-02,5.068348283496371121e-02,5.047398645819808904e-02,5.014830952204099579e-02,4.949979188277182224e-02,4.921538171899558778e-02,4.927179134401470789e-02,4.903041119828912414e-02,4.884507947331070271e-02,4.904028245443414064e-02,4.916998300821068951e-02,4.904734230321188687e-02,4.897265059336478044e-02,4.929736340398242767e-02,4.938786287418225895e-02,4.923376763095404368e-02,4.931105772221826972e-02,4.959795423216939447e-02,4.974950638366112260e-02,4.971180004505113686e-02,4.971545908225546984e-02,4.988569931080821807e-02,5.004887464768453115e-02,5.001527235089828910e-02,5.001993168404181289e-02,5.017534994549845834e-02,5.038898287031901707e-02,5.047416374727790173e-02,5.039722635489295166e-02,5.041206631979213565e-02,5.053763540410649568e-02,5.069833415630002615e-02,5.067194047669591056e-02,5.062184583674642080e-02,5.076514153407391677e-02,5.104468055069465854e-02,
        #                  5.114585944839523945e-02,5.098967679685631471e-02,5.101384467515045207e-02,5.116518484088360130e-02,5.126335343291358454e-02,5.129273192519661489e-02,5.136848671106522546e-02,5.149184776367791289e-02,5.164900503489416178e-02,5.175205193481990928e-02,5.177673612928839625e-02,5.175415529358513844e-02,5.191137199829599924e-02,5.212099857594505031e-02,5.225729396543190436e-02,5.227486710427841493e-02,5.230374310052753745e-02,5.244263632869412134e-02,5.251747056101564032e-02,5.249101063657746202e-02,5.256246469516215325e-02,5.279015915894552657e-02,5.301922571520552990e-02,5.301984610054589347e-02,5.297519455793995441e-02,5.299219072555744897e-02,5.304283075752660309e-02,5.306614555888688328e-02,5.318475117702858163e-02,5.326057781251263001e-02,5.321697245587803798e-02,5.325403243553145788e-02,5.338427585067714864e-02,5.340448563717319769e-02,5.343740601165396925e-02,5.353513304070015716e-02,5.366637092670597381e-02,5.369245933237006690e-02,5.356969254976504807e-02,5.367816205028411863e-02,5.387699739122894099e-02,5.392013687840309377e-02,5.374018592678114076e-02,5.383368823593393665e-02,5.408472705742729120e-02,5.417971998872130740e-02,5.409507464299246476e-02,5.414009190829086743e-02,5.431747905215888322e-02,5.445382912664939457e-02,5.452168000059621350e-02,5.468016535029529557e-02,5.488039793482465262e-02,5.491387519453015675e-02,5.494238188953137064e-02,5.518098303741258981e-02,5.546118398997106069e-02,5.556615711079480185e-02,5.557470093320084764e-02,5.570207814624762027e-02,5.592865722224291819e-02,5.618155559976837493e-02,5.635483087554218895e-02,5.650540541374726028e-02,5.654212385965095428e-02,5.664994241689674109e-02,5.679432046631266440e-02,5.694511219199754892e-02,5.702238653854544564e-02,5.712520720130687818e-02,5.727884689136136104e-02,5.729644527490184575e-02,5.720962551316691180e-02,5.724540321179499153e-02,5.733047998506220905e-02,5.744097598910727354e-02,5.739661021092593018e-02,5.733546814565310124e-02,5.744663689586185229e-02,5.752768627220267855e-02,5.748480937879497238e-02,5.750860877345183308e-02,5.753236139143744210e-02,5.754681234261369710e-02,5.757884032291624155e-02,5.760645486672309745e-02,5.748028565905616283e-02,5.743613597446629165e-02,5.763741502135591444e-02,5.778286683646148558e-02,5.768488525213708029e-02,5.762920734398245537e-02,5.770631400716137727e-02,5.765200830784335956e-02,5.767560034273504915e-02,5.775468302644296004e-02,5.773024663729457717e-02,5.767581765707486402e-02,5.768393380501517231e-02,5.762929682992486841e-02,5.740339995026479125e-02,5.726583803177389548e-02,5.736910221380892710e-02,5.725672531702795387e-02,5.689587029932070134e-02,5.669895482781384805e-02,5.652033955498131368e-02,5.624670931677889368e-02,5.594511951867721378e-02,5.574512573473007493e-02,5.536801476785200432e-02,5.473510136705655310e-02,5.448971785449598093e-02,5.441222774887703728e-02,5.360209397378187801e-02,5.281328669615369814e-02,5.277776534892607285e-02,5.230943325469473992e-02,5.098673921055178054e-02,5.045186443641271751e-02,5.093760736288122093e-02,4.942256488130732095e-02,4.696159663439204712e-02,4.976428210907862110e-02,4.676749456958797374e-02,4.419279538377984817e-02,4.745934190726465440e-02,4.419995560578469235e-02,4.249084023716610814e-02,4.300137089446559591e-02,4.244694116092857100e-02,4.110761117365831219e-02,4.099265748552727295e-02,4.151794392608984530e-02,4.104627132918155924e-02,4.024358029305164647e-02,4.039302117238874335e-02,4.108278835263982909e-02,4.136001269621297771e-02,4.164442484992541410e-02,4.273480712543072102e-02,4.397506230824323181e-02,4.420741512518354399e-02,4.448880856665581029e-02,4.610619884960483889e-02,4.584447426389642866e-02,4.724048140438719817e-02,4.699112507930373189e-02,4.961955995877852937e-02,4.777087938098235897e-02,4.994281956771939174e-02,5.086556522718465451e-02,5.062532268329651003e-02,5.126334142623430873e-02,5.233303044123850667e-02,5.282694964886181649e-02,5.320868222331519293e-02,5.379922771308717072e-02,5.420914564813196501e-02,5.463861646169076297e-02,5.530013738720713362e-02,5.579750998247962751e-02,5.598530025686910411e-02,5.624736178655502516e-02,5.692671638556869029e-02,5.743970905280056105e-02,5.752751585438941467e-02,5.771850522964049740e-02,5.827801405685634206e-02,5.890257370145420002e-02,5.912852171946880731e-02,5.914465851021863396e-02,5.946729250394634791e-02,6.018349039404607970e-02,6.051121098278251786e-02,6.028035507601273851e-02,6.031402144256720055e-02,6.084497829003256836e-02,6.116724419385059786e-02,6.086667046847708817e-02,6.062494043568548291e-02,6.101084613390680284e-02,6.137502630820806243e-02,6.120948702905349564e-02,6.116165125094206317e-02,6.134058260915398186e-02,6.142153628547888239e-02,6.129890526718097948e-02,6.127393071001581426e-02,6.144300757540643865e-02,6.155958537610975445e-02,6.154776040354759808e-02,6.154605029661480015e-02,6.159516043319216566e-02,6.164711609883155585e-02,6.166506210348137590e-02,6.158708279439215061e-02,6.157984212467189356e-02,6.161557240156084747e-02,6.164879158079682175e-02,6.173519486004788032e-02,6.179744962179484213e-02,6.171791492321614114e-02,6.164114406493019505e-02,6.179089167195016274e-02,6.191421853303272910e-02,6.186414435480705465e-02,6.177529208459097559e-02,6.190974236770836747e-02,6.215085011646070967e-02,6.207417681507534923e-02,6.211937622704542111e-02,6.223746714365059607e-02,6.222850070535254630e-02,6.223354988820903322e-02,6.233349802134659223e-02,6.256974313817120770e-02,6.263975793171769335e-02,6.262615654585737546e-02,6.266549445933906892e-02,6.282446116756226773e-02,6.294402877534889529e-02,6.315099856515445087e-02,6.329839699297842848e-02,6.326502250416389528e-02,6.330763063668534696e-02,6.352721346566161942e-02,6.361044939566552758e-02,6.361954386197093969e-02,6.367757235634982638e-02,6.381712876622783193e-02,6.382363259030809921e-02,6.390116988523808494e-02,6.401491490191571487e-02,6.399776609715653042e-02,6.404194975863088113e-02,6.419744705925160833e-02,6.419871321957931753e-02,6.412535416779813202e-02,6.420963123843227705e-02,6.443526843356825462e-02,6.450710250443067451e-02,6.434301535900288638e-02,6.438672818035581780e-02,6.466067746389554671e-02,6.468744434187854997e-02,6.454601869529308367e-02,6.466708991480957236e-02,6.489144324153138521e-02,6.494671606322828528e-02,6.497186660916166867e-02,6.505203439085259498e-02,6.499927538139624317e-02,6.500405361687078276e-02,6.509441132296849009e-02,6.522585566409459801e-02,6.522966581381157980e-02,6.523419451750894771e-02,6.533666557727516033e-02,6.530828032679031336e-02,6.536465052854492641e-02,6.552633938942302450e-02,6.565647035187344160e-02,6.573747743268709698e-02,6.581051232039303311e-02,6.582841928005313259e-02,6.596807452427995433e-02,6.607393643845516085e-02,6.606838601342769624e-02,6.620915715028917459e-02,6.645376156981991356e-02,6.660777025810440954e-02,6.661278064502894336e-02,6.662773853212125563e-02,6.685331300658356457e-02,6.707153568127034726e-02,6.713628882644415152e-02,6.710941529312465514e-02,6.729541078098322249e-02,6.760670626340854750e-02,6.767465449770593278e-02,6.760150495330947973e-02,6.767174128155607760e-02,6.785882268088347380e-02,6.795418924619621437e-02,6.802758518769048968e-02,6.810523414688506028e-02,6.808579253334270942e-02,6.815586385247794643e-02,6.840512600791952280e-02,6.846633655046237277e-02,6.841753547283611903e-02,6.835625844780053584e-02,6.845245279612485745e-02,6.859635375066629182e-02,6.862104853249963166e-02,6.868407971283950475e-02,6.870344705138992092e-02,6.860775027105626978e-02,6.863929670762367041e-02,6.872420039165634542e-02,6.871829804686678533e-02,6.869079869622872481e-02,6.871329947858435816e-02,6.884989828686537139e-02,6.894395345829273936e-02,6.883292014614436627e-02,6.867381658952474710e-02,6.880533584664742797e-02,6.911620275281539494e-02,6.904695036702833411e-02,6.888389527230159848e-02,6.901284458750824025e-02,6.918470127792540614e-02,6.919905999896082405e-02,6.931991454297997679e-02,6.939082553508622853e-02,6.923633770369862217e-02,6.932925702922039524e-02,6.980830898116976990e-02,6.982742156222034036e-02,6.935212179049418668e-02,6.952170371943815208e-02,7.017271972497168830e-02,7.005505042910967206e-02,6.960858348998655298e-02,6.990647600115398874e-02,7.026788077743179040e-02,7.016170595637770402e-02,7.023139733153245523e-02,7.069368045930428390e-02,7.045284313784717922e-02,7.012288438986001571e-02,7.062249279864966922e-02,7.109775486098333930e-02,7.073633556024729041e-02,7.045342774492986682e-02,7.099821517211855892e-02,7.134190127262213243e-02,7.101642825415613314e-02,7.094091530545006130e-02,7.141520865982392552e-02,7.146458344183484468e-02,7.126846483064358528e-02,7.161992171089424930e-02,7.207104201552899658e-02,7.164839994845229043e-02,7.136032394869794293e-02,7.201084455571710174e-02,7.242980786580616170e-02,7.211058421089876214e-02,7.171700236579606202e-02,7.197743922580521203e-02,7.266249363844200226e-02,7.279282151432156511e-02,7.220188838120260300e-02,7.173787768803309428e-02,7.258593877211043377e-02,7.347652053646905324e-02,7.249403394789014077e-02,7.137538299575449385e-02,7.316413785579532758e-02,7.429380769686572128e-02,7.156615096900514894e-02,7.133477463656236195e-02,7.512320031212411930e-02,7.356563731765260183e-02,6.930363184809668065e-02,7.408015833979943177e-02,7.812486779914860902e-02,6.984349834382956590e-02,6.762635612380407668e-02,7.948597847543763251e-02,7.864561135673790726e-02,6.370375599686332879e-02,6.884246527824246231e-02,8.681146806071075861e-02,7.640131891575568934e-02,5.543397237054552978e-02,7.346380778800730427e-02,9.895277728804306727e-02,7.008451911375943033e-02,3.531916184443940898e-02,8.022353200700803322e-02,1.643963039511294189e-01])

        data = np.array([2.031498053601147463e-02,8.529486274017724495e-03,2.397319766939973174e-02,1.143586741259722782e-02,1.775368600255809726e-02,1.700770669298284909e-02,1.282193814335232801e-02,1.929268021814642062e-02,1.236120443985816615e-02,1.757949868192488357e-02,1.549499368394587073e-02,1.384476795329001725e-02,1.771458605808090211e-02,1.351896165438468654e-02,1.622913619660312778e-02,1.503063801605163813e-02,1.416713754919336765e-02,1.616156564363371503e-02,1.410628568485777085e-02,1.597127359630532914e-02,1.514854629357501904e-02,1.533329553486611173e-02,1.557672874097058326e-02,1.585351087747674179e-02,1.594844816192545964e-02,1.624684682571233760e-02,1.739980572521818147e-02,1.720939644937275609e-02,1.900496107382587674e-02,1.955737510136926552e-02,2.018138348968457479e-02,2.311885628906781148e-02,2.279752333104380010e-02,2.657129252766099112e-02,2.791756418080332258e-02,3.076914324457595551e-02,3.493743173562249144e-02,3.684158785069840958e-02,4.372013805674293541e-02,4.627083000883069203e-02,5.330014780449531669e-02,5.971931182076654909e-02,6.579607952743887767e-02,7.570939085127624535e-02,8.333474122402953488e-02,9.409563355034873677e-02,1.056143908791346425e-01,1.165962947288295276e-01,1.317953303796747799e-01,1.442674322762037553e-01,1.616750010975752938e-01,1.776541055901966759e-01,1.961481868830190212e-01,2.161207804845577674e-01,2.361045656286251404e-01,2.579713235748978817e-01,2.822508279361632955e-01,3.034967811208045818e-01,3.321199829746436238e-01,3.561309923671870381e-01,3.818743850565646247e-01,4.165627622395289831e-01,4.339023226837250835e-01,4.771134227872765310e-01,4.979895549083007689e-01,5.288984191507797306e-01,5.741244792781204920e-01,5.807846816155376457e-01,6.423080456615605227e-01,6.574867524980068101e-01,6.821466343400504062e-01,7.465095322964395708e-01,7.627954418777288526e-01,7.599730350076698837e-01,7.184267540344996261e-01,6.813047711836274223e-01,6.523976548054079005e-01,6.076745821885677357e-01,5.876261681726603348e-01,5.424159740383479589e-01,5.184974841165004289e-01,4.878771554603441585e-01,4.505816645902321338e-01,4.295157772735994639e-01,3.933191194428999893e-01,3.700171560564897155e-01,3.417901702634965622e-01,3.123655352635876792e-01,2.928398772229847680e-01,2.651177573284292932e-01,2.452150304858043972e-01,2.247199372276840190e-01,2.008918584030232324e-01,1.863392994483032417e-01,1.644858882412765788e-01,1.514751163983492077e-01,1.359953733810035092e-01,1.216022968233996665e-01,1.132353815290169791e-01,9.912643373743194875e-02,9.122261933445595383e-02,8.213155637583702262e-02,7.228202537947496509e-02,6.760918066091994860e-02,5.949227242209077088e-02,5.618897429706659619e-02,5.164521456875636324e-02,4.736852343647991737e-02,4.618716983667252307e-02,4.177904553285181899e-02,4.147564204401332083e-02,3.891904374635533209e-02,3.802012232472194025e-02,3.810491847747105032e-02,3.658530258396746476e-02,3.775231317072015591e-02,3.669182215179944001e-02,3.733369503634932640e-02,3.778954662235264189e-02,3.748006531280632936e-02,3.846474645073341692e-02,
                         3.849791869394134092e-02,3.923868925644534433e-02,3.998007009634664544e-02,4.038163370986349449e-02,4.118768423397176082e-02,4.188510924760306675e-02,4.228117224885379055e-02,4.320257622507440304e-02,4.370175283266704291e-02,4.406463258990347964e-02,4.497901787082961289e-02,4.520014848807863556e-02,4.603302641103770854e-02,4.654890177259218831e-02,4.657927815603774002e-02,4.783662534743687855e-02,4.740041243065002546e-02,4.855712359461598210e-02,4.881567101358198768e-02,4.883657706764880230e-02,4.994794606055678876e-02,4.938646199591688324e-02,5.045005721494430495e-02,5.040356597078673312e-02,5.042600796884039865e-02,5.143989009518360606e-02,5.077578664655588159e-02,5.177021248769944628e-02,5.173824513205179526e-02,5.189398428351407744e-02,5.281968162652801030e-02,5.216124109241177670e-02,5.299726197590100274e-02,5.295704189319784538e-02,5.280542664148764331e-02,5.371152099765168914e-02,5.297850964875396723e-02,5.384287876779645515e-02,5.382925414361801331e-02,5.369050406780508794e-02,5.457827638920322716e-02,5.372588758208787785e-02,5.484138266007552998e-02,5.442386402403633777e-02,5.473771728262198655e-02,5.493107400032568727e-02,5.466239640653867277e-02,5.540805471692949319e-02,5.461677984902842814e-02,5.561520318671268198e-02,5.472050765378542320e-02,5.549141720667424837e-02,5.518674784552493606e-02,5.527978671706806207e-02,5.550527544239461375e-02,5.525522105827090913e-02,5.545849974016373723e-02,5.554361415012813719e-02,5.533008161385209039e-02,5.572022074916473805e-02,5.550416580655818249e-02,5.580016614583251794e-02,5.556654575665027906e-02,5.596887329297873387e-02,5.580349805933135926e-02,5.612609133159963959e-02,5.620692822578923775e-02,5.628637771802714324e-02,5.627041811770212149e-02,5.624726534797479943e-02,5.635743697433009958e-02,5.663241239198190530e-02,5.636284493908507581e-02,
                         5.702927514273550130e-02,5.626620002347785393e-02,5.705225950219294795e-02,5.644970866149297273e-02,5.670371795865455228e-02,5.657778474197731194e-02,5.626508074638078560e-02,5.659145047922171240e-02,5.553377813689840820e-02,5.643372350027158618e-02,5.611483194554956616e-02,5.616880051965884857e-02,5.665146705013021644e-02,5.627529490082709002e-02,5.718560612020099493e-02,5.695204878835800899e-02,5.746922703214882300e-02,5.760321030234405448e-02,5.788141761422532783e-02,5.796673191499462918e-02,5.831032410084800721e-02,5.828705613712150541e-02,5.877761691659676851e-02,5.855797804007931845e-02,5.915391744523340600e-02,5.864261644295484799e-02,5.926723003822691183e-02,5.879792206600038124e-02,5.910418720786975860e-02,5.894537476001986132e-02,5.870302133862644739e-02,5.897468268165109717e-02,5.887720637392225564e-02,5.861864246394080796e-02,5.918268483243525890e-02,5.817242588181659180e-02,5.957165493324301231e-02,5.825087492228046143e-02,5.929793615078185476e-02,5.846809019360007381e-02,5.887006701655956437e-02,5.900775806391901634e-02,5.826826559627680535e-02,5.897523954884469066e-02,5.832679258306698589e-02,5.871901332079827729e-02,5.836632412241746226e-02,5.822120178920564548e-02,5.842983078066375097e-02,5.782554564212451925e-02,5.830893350522763086e-02,5.780560882945437462e-02,5.796946699136864417e-02,5.777963358512534092e-02,5.765306939878048209e-02,5.774746250214335408e-02,5.759940029138337081e-02,5.743170855161707639e-02,5.761958369577158123e-02,5.700190788958724858e-02,5.768623583641831892e-02,5.702004904387830003e-02,5.746153438309124784e-02,5.731653259001182055e-02,5.705336055593654421e-02,5.763249482054024625e-02,5.700116408601534068e-02,5.754905432987292985e-02,5.724351230472867619e-02,5.717841669513703401e-02,5.745438312750291571e-02,5.690768218277596213e-02,5.732569649108495285e-02,5.686974590711491723e-02,5.706028797137698699e-02,5.693375567525128106e-02,5.685213933835295969e-02,5.712431988351456685e-02,5.685272767134715716e-02,5.709982889738837719e-02,5.703186586488383919e-02,5.695265774360026845e-02,5.708422041800351870e-02,5.694033555549180697e-02,5.719276838003963664e-02,5.708777224910180359e-02,5.721726630449669448e-02,5.710965501052887860e-02,5.732428591734570200e-02,5.712128146875015966e-02,5.741802411953950830e-02,5.712362507644258569e-02,5.766477660713358738e-02,5.701582845268359651e-02,5.817087854209346265e-02,5.700531851138077727e-02,5.839632978422976128e-02,5.746630828202384939e-02,5.801400426840835206e-02,5.831436101963539259e-02,5.750412000728800238e-02,5.899553399605083487e-02,5.727056693672753773e-02,5.901606551049328603e-02,5.786524014921220344e-02,5.856414715151340294e-02,5.855762299686342875e-02,5.847440501701341165e-02,5.875485025513763754e-02,5.863373607315192776e-02,5.865474086647804591e-02,5.914113564355059222e-02,5.815150432028820537e-02,5.958893732587337844e-02,5.793863449955927170e-02,5.958995000893903271e-02,5.832470675131245369e-02,5.937387946392332083e-02,5.859230691329871121e-02,5.897734216279700709e-02,5.897498461269989889e-02,
                         5.886717136950225110e-02,5.877477525433023181e-02,5.907436719152189125e-02,5.850712202419501573e-02,5.906276702865724537e-02,5.871198193205564436e-02,5.859906280222632047e-02,5.907656461837829109e-02,5.824769381093550941e-02,5.907362132122379733e-02,5.825897800850997343e-02,5.880413623365969567e-02,5.843204051316885222e-02,5.840961294375894564e-02,5.878071570070735746e-02,5.833956678608545610e-02,5.885152000333127714e-02,5.825912236898404123e-02,5.868106986839541350e-02,5.835533834388941660e-02,5.851777179769448306e-02,5.866072759275711701e-02,5.836356284133040889e-02,5.878734431360503609e-02,5.835107046643170370e-02,5.868375227692457924e-02,5.874917111495751160e-02,5.857381109950259013e-02,5.902875837232543499e-02,5.856542469532067391e-02,5.892744256915207618e-02,5.896446896405416194e-02,5.869661899567057972e-02,5.930276484108758933e-02,5.856704679347531084e-02,5.947290382381157509e-02,5.876865415944144272e-02,5.948504169455969687e-02,5.908865143548246851e-02,5.940057826065716501e-02,5.949654822162334794e-02,5.963671043464764676e-02,5.941437400467224766e-02,6.022326232593659678e-02,5.929441950767471575e-02,6.042441970254538303e-02,5.945328570282683300e-02,6.034719352178029295e-02,6.019751236087708679e-02,5.999544465104423435e-02,6.081404367156259538e-02,5.985125637674403726e-02,6.086696749770293541e-02,6.017180688068800298e-02,6.069857359932515073e-02,6.064073770996564888e-02,6.070832632663674538e-02,6.087861448780130386e-02,6.125544678959240347e-02,6.063534487262180889e-02,6.163502549588256024e-02,6.061246804956393897e-02,6.154694119351612758e-02,6.102031233762157669e-02,6.116392829149655541e-02,6.149540314734009555e-02,6.047301094613685007e-02,6.155899884838671177e-02,6.058243240984589884e-02,6.116289285692137756e-02,6.082515068143891368e-02,6.063942294512469910e-02,
                         6.102480420302633379e-02,6.035130848941266252e-02,6.087667608434339100e-02,6.027605713234449741e-02,6.078024043844793001e-02,6.028466132944504396e-02,6.060666442508912122e-02,6.041672207378488008e-02,6.030848868800367524e-02,6.057172518427519914e-02,6.004282224894724046e-02,6.046224587812840806e-02,6.010404549738723734e-02,5.997364694268670499e-02,6.035797774770110952e-02,5.984354646840105152e-02,6.011432009843992869e-02,5.978248915645933276e-02,5.984440953250089179e-02,5.984983681877260875e-02,5.955271705573918911e-02,5.967702795576179664e-02,5.950117099405426851e-02,5.937999987284090647e-02,5.970366581858820021e-02,5.894929128572100330e-02,5.979473871850524147e-02,5.912933954481434246e-02,5.934978654857694935e-02,5.947847370796254668e-02,5.903139178221641220e-02,5.991764640214197052e-02,5.898952586255485492e-02,5.992697097207567297e-02,5.946955286885700909e-02,5.958388744738682408e-02,6.012910771648478231e-02,5.944501506743679609e-02,6.044992003803507929e-02,5.982210764158869126e-02,6.036816515718303883e-02,6.047360744568700680e-02,6.018157809620563320e-02,6.104242708480585311e-02,6.031456800140176655e-02,6.120357602420196247e-02,6.079907639759922489e-02,6.109978411839776802e-02,6.134841189130349481e-02,6.099740460426595484e-02,6.184418512523064126e-02,6.119619233290008592e-02,6.156816652440592202e-02,6.170672354795643522e-02,6.124807112474516674e-02,6.216283974518158756e-02,6.103703055711224429e-02,6.197597088405128879e-02,6.116935583984012270e-02,6.158364033785265756e-02,6.164889170181407640e-02,6.078107920718919810e-02,6.189205914137434900e-02,6.060847154129415243e-02,6.173905340791056851e-02,6.080404833154467309e-02,6.134211292625539602e-02,6.119722639253608737e-02,6.083293180092660263e-02,6.154594742150128889e-02,6.060602783699097634e-02,6.124012008313457073e-02,6.088065396340953950e-02,6.085161816894018444e-02,6.130815319797629226e-02,6.058123466546257857e-02,6.142467867161314349e-02,6.088402767529658283e-02,6.127078472615563737e-02,6.141359818801742088e-02,6.109009474681352525e-02,6.147518026011888209e-02,6.104682133117355497e-02,6.133497571751239663e-02,6.146945210100279722e-02,6.109036285840855479e-02,6.161961894227698661e-02,6.112850286003829875e-02,6.163879349035745331e-02,6.132638160100298275e-02,6.150108939989008122e-02,6.172686144867040037e-02,6.144200174933393127e-02,6.164782051516889266e-02,6.157288703265749452e-02,6.177299432136226787e-02,6.173914677595324085e-02,6.169298165868971479e-02,6.216784114106604225e-02,6.177344517666794738e-02,6.218218846007893957e-02,6.190877662743864834e-02,6.217210256966860388e-02,6.220227972189399518e-02,6.212924456478508689e-02,6.244593841786211935e-02,6.243059291962529261e-02,6.228519405229802214e-02,6.279876881065603322e-02,6.229158231330544221e-02,6.308813624726110347e-02,6.235013900266576925e-02,6.279652664623981695e-02,6.275757143393827231e-02,6.249783536632124575e-02,6.297877899964161863e-02,6.234086597846310446e-02,6.285664402352779401e-02,6.233916852255572821e-02,6.275093671199113987e-02,6.257496764110177800e-02,
                         6.239060098957555783e-02,6.256372935024817616e-02,6.234511727668950315e-02,6.277290248902597791e-02,6.221119232263803978e-02,6.253750727034983192e-02,6.265825597839728978e-02,6.237266061069770412e-02,6.299295424251588615e-02,6.230265399280535826e-02,6.301845720557838759e-02,6.292049788821522938e-02,6.286240464164390140e-02,6.346810069454369985e-02,6.292866633760342554e-02,6.363400817739951754e-02,6.327109981366060842e-02,6.363984109533465938e-02,6.364373599045351770e-02,6.365681615318900810e-02,6.410650025994112100e-02,6.362896745751193961e-02,6.440982022374681926e-02,6.375520475882918980e-02,6.438138811208758694e-02,6.426032417442265054e-02,6.418297178041608431e-02,6.454499736865292048e-02,6.413675789735820421e-02,6.463339570564938241e-02,6.423998639473181560e-02,6.444222481832638516e-02,6.450767021928739686e-02,6.429993440723542897e-02,6.453834370494394845e-02,6.419754871791154283e-02,6.421175476930275627e-02,6.423629374727350683e-02,6.370760292634011779e-02,6.412645586578578916e-02,6.365886385440157336e-02,6.384349201964696630e-02,6.366877843456973662e-02,6.334114127708759256e-02,6.381602382772622040e-02,6.302233931400408329e-02,6.355356954990831753e-02,6.322243060548209115e-02,6.303065062253714046e-02,6.342856161276357041e-02,6.288405527058306410e-02,6.334361091700428659e-02,6.287111641166272247e-02,
                         6.300212207848798762e-02,6.294764046974214711e-02,6.271727192790653438e-02,6.290257808286052466e-02,6.263441360408684988e-02,6.270699609943472530e-02,6.289604543791214863e-02,6.252579497334556646e-02,6.324805757604683165e-02,6.243753498622788695e-02,6.324254415223806713e-02,6.279333099458987710e-02,6.294361522037059120e-02,6.333206771308516614e-02,6.268603225504978949e-02,6.360539644413647220e-02,6.281814389944638533e-02,6.356213613283250019e-02,6.334615233878401752e-02,6.330513712249490055e-02,6.370356405904054053e-02,6.331963732595728700e-02,6.402110479585938763e-02,6.372096820384302862e-02,6.394828617925925329e-02,6.408401546179569308e-02,6.378535868296872358e-02,6.429161942490581316e-02,6.371930280755402909e-02,6.450221908067776955e-02,6.388196264543281877e-02,6.448357069708933464e-02,6.415836047595704916e-02,6.434298806592250730e-02,6.452121686297997150e-02,6.415022545660391262e-02,6.429434287437785223e-02,6.459814390499561687e-02,6.395982781365487646e-02,6.481630311488098539e-02,6.379622250394964555e-02,6.481688732546714293e-02,6.408728128046262129e-02,6.444600689676363570e-02,6.450993211341850275e-02,6.425987259664898976e-02,6.475731649537702639e-02,6.409093942403236432e-02,6.459517953380973510e-02,6.421048992708341951e-02,6.411082201636968125e-02,6.450277844450892639e-02,6.368472068109028161e-02,6.417539752061106328e-02,6.367413468822780143e-02,6.374110511267155887e-02,6.388789438044201185e-02,6.339159223978653446e-02,6.393760196386207018e-02,6.360368726575643672e-02,6.373800911836617622e-02,6.397375717739478551e-02,6.352350883504710721e-02,6.435579064567520380e-02,6.356063977823836475e-02,6.446514376604041419e-02,6.398377533249664795e-02,6.425099665135075577e-02,6.455060348247636248e-02,6.425365162782421813e-02,6.507811763874940536e-02,6.455160637568679860e-02,6.513722585557540912e-02,6.514369373865928903e-02,6.525032740946934418e-02,6.557474607680180423e-02,6.555054057059177264e-02,6.596732306778038679e-02,6.614177271111343348e-02,6.598770725102999501e-02,6.670354764229281808e-02,6.624278801926342108e-02,6.713365020861636334e-02,6.653888754386227955e-02,6.720716286687228314e-02,6.676156522907925051e-02,6.721442225676239890e-02,6.715487034431034952e-02,6.695119462597028115e-02,6.728110624789054861e-02,6.692046348951495582e-02,6.724063418587498953e-02,6.729596406816977516e-02,6.702834118889539061e-02,6.733299652077652520e-02,6.710757942893438854e-02,6.719954075813068528e-02,6.740838170676757835e-02,6.687931826166845783e-02,6.744499440143371383e-02,6.706616226816772275e-02,6.686390646430134810e-02,6.728844122381151538e-02,6.652152457161777943e-02,6.710746982940703209e-02,6.639058581781055735e-02,6.670052024087058662e-02,6.659765460009908766e-02,6.609004260018885857e-02,6.676138527797001454e-02,6.602973990788572889e-02,6.647908629108999212e-02,6.606413465347467373e-02,6.621858080282001791e-02,6.607550685436242022e-02,6.600361322844096323e-02,6.626264472242189563e-02,6.589092916497038543e-02,6.624762622909498300e-02,6.591050266081480147e-02,6.628263033791777226e-02,
                         6.625671823982316744e-02,6.614963985987684647e-02,6.668167643007991141e-02,6.590362832424627448e-02,6.676498392420930628e-02,6.629266506618275434e-02,6.679511630046622295e-02,6.703000733297080627e-02,6.679363055247140857e-02,6.788167563026527296e-02,6.703972525278374672e-02,6.851532716638410181e-02,6.797770052214981151e-02,6.886813509322854687e-02,6.964061566283685778e-02,6.971315932783635205e-02,7.169242148519772151e-02,7.180277610957208623e-02,7.395385310960518599e-02,7.520463341876140739e-02,7.672418722085663778e-02,8.016762236308605516e-02,8.089030829105299525e-02,8.582880060423932200e-02,8.779967377498840153e-02,9.239843802031107167e-02,9.778909507356767228e-02,1.012569927152159321e-01,1.098323799635803621e-01,1.142929757595523149e-01,1.236808948694914090e-01,1.320290993661092649e-01,1.406324989155041116e-01,1.533436348015969619e-01,1.627319818650639349e-01,1.770920630038521626e-01,1.910756350412149418e-01,2.045309097905855245e-01,2.236130761978679382e-01,2.385918116039898174e-01,2.586888303166439695e-01,2.795507061026062945e-01,2.981384965315291291e-01,3.237050448839886019e-01,3.453974260875160018e-01,3.686158376615247256e-01,3.994665800945166878e-01,4.182122439034944850e-01,4.536848453992754493e-01,4.784872573003656759e-01,5.035151264081872968e-01,5.472219792954408080e-01,5.580098979444461094e-01,6.086254556670349647e-01,6.314143286363463892e-01,6.546412882351163587e-01,7.160928188115716075e-01,7.107105806965567929e-01,7.678665488259730498e-01,8.131204742668757257e-01,8.185642641534252029e-01,8.062674650321903780e-01,7.515940799749605272e-01,7.323131510562540525e-01,6.849897236651848464e-01,6.576714277840601808e-01,6.258750853775185696e-01,5.851926412802294086e-01,5.657345834990867850e-01,5.255963239470106130e-01,4.985813218829732718e-01,4.708420097185723741e-01,4.378043042489991321e-01,
                         4.158114350983476148e-01,3.836887850982796389e-01,3.600438951419711597e-01,3.372619456959983220e-01,3.112247514567559326e-01,2.931321614890890492e-01,2.695783865690314918e-01,2.498150743836898557e-01,2.334977478218379643e-01,2.128813402990283599e-01,2.018241436618317675e-01,1.839882530888221346e-01,1.742217261081956958e-01,1.627919458175158540e-01,1.507902483943893701e-01,1.434371931458513216e-01,1.330469824909385756e-01,1.257413471578081587e-01,1.201227332738033643e-01,1.131435023977036408e-01,1.107598681134596974e-01,1.051315011435723645e-01,1.032444838809758736e-01,1.003688886754168230e-01,9.787080888986755822e-02,9.677542908664711618e-02,9.478223453361196704e-02,9.431689214961438972e-02,9.431369112659004905e-02,9.314915039595804414e-02,9.425198332984199845e-02,9.325351931367617531e-02,9.430329781579717408e-02,9.460031472634880534e-02,9.444116514298542264e-02,9.589751908136377734e-02,9.527150257190515614e-02,9.675534790264779528e-02,9.720771228616061077e-02,9.768708914549659172e-02,9.887919673958801836e-02,9.878781554219615013e-02,9.982133697223458113e-02,1.004437529203300178e-01,1.008833135667358688e-01,1.018791418230449164e-01,1.018931185279688678e-01,1.031020712417806268e-01,1.031514631093859158e-01,1.041958022677133555e-01,1.042392041183116819e-01,1.051515156913006011e-01,1.054046234456525177e-01,1.059885120439280626e-01,1.064897277694145661e-01,1.065050206972445040e-01,1.075980352247939975e-01,1.068949494592478094e-01,1.085321720588051653e-01,1.075162618860278502e-01,1.089946937303582220e-01,1.085273270812827928e-01,1.090549512194834841e-01,1.094671528783213305e-01,1.094730335529290749e-01,1.096518266660040375e-01,1.102552121203417557e-01,1.099790015504002877e-01,1.108468954644542259e-01,1.103901335323370925e-01,1.109969223922101511e-01,1.111706391969156660e-01,1.107734733262418642e-01,1.120909678643123852e-01,1.108725654452534515e-01,1.123363168843265758e-01,1.114316896563944670e-01,1.124575002887884673e-01,1.120633802520979716e-01,1.126136238590344507e-01,1.125728787878804010e-01,1.126734651467955484e-01,1.130902170130885648e-01,1.131502631794625985e-01,1.134109155334338398e-01,1.134538395718119042e-01,1.136867028422119535e-01,1.138266894391104511e-01,1.140156409065067045e-01,1.138748318337985399e-01,1.144734776791627717e-01,1.141593096048397760e-01,1.146380833331187565e-01,1.146193595260791426e-01,1.147584892093706926e-01,1.149732838352455905e-01,1.150110082711298110e-01,1.151440504563179534e-01,1.153316303235873003e-01,1.153366854881478776e-01,1.155158035067914563e-01,1.156441432372037337e-01,1.158511747364652927e-01,1.155352491475133969e-01,1.160974203534552579e-01,1.153161776995888232e-01,1.161922969804459749e-01,1.155204371922512185e-01,1.160771470473758726e-01,1.159044472036512841e-01,1.156636401567699562e-01,1.161201522976041539e-01,1.156456373508492064e-01,1.161129335925345507e-01,1.156348711215012814e-01,1.159268537867682858e-01,1.155338570497285167e-01,1.153792951520645621e-01,1.159829783572779299e-01,1.157445164025999312e-01,1.165627322369516550e-01,
                         1.161325251799800728e-01,1.169122831822701353e-01,1.169850985583971575e-01,1.175875967671824313e-01,1.174295976564262434e-01,1.179954397476059569e-01,1.178506894663514798e-01,1.183113232485044630e-01,1.184197326813809792e-01,1.188386009451834202e-01,1.189157259840635111e-01,1.192468320885579636e-01,1.192969817888071687e-01,1.193774964033594704e-01,1.198342526573484418e-01,1.195613960936626613e-01,1.200184230186363415e-01,1.196404707769344322e-01,1.200566919659797338e-01,1.197577812149522442e-01,1.200054442045191960e-01,1.198401918303775154e-01,1.201690381395769669e-01,1.199389631995042421e-01,1.201378902508998536e-01,1.199955942162754668e-01,1.199555889563280742e-01,1.200211356557991105e-01,1.197766722742642787e-01,1.199931296235586392e-01,1.195012999843497042e-01,1.200448210278637629e-01,1.192995802314515547e-01,1.199164855930089646e-01,1.192490336269171752e-01,1.195475111794276485e-01,1.192057850971307426e-01,1.190361667862692291e-01,1.192454395625176661e-01,1.187893602456368547e-01,1.192288061055680054e-01,1.190585932903826388e-01,1.191195314289952567e-01,1.191340099097799726e-01,1.190704409824814430e-01,1.193060123960293095e-01,1.193283710101396000e-01,1.191156515659988618e-01,1.196737952661906107e-01,1.190148317119450183e-01,1.198591277276413181e-01,1.191644085540780190e-01,1.199206741940556931e-01,1.194669780199959092e-01,1.200298620208216510e-01,1.199115770206471143e-01,1.202325128058756576e-01,1.200129776687583333e-01,1.204918884091270431e-01,1.199448328343560299e-01,1.206576857223728289e-01,1.201522870127997994e-01,1.207044435116030323e-01,1.203720508509257270e-01,1.207797973242739076e-01,1.207550894361885674e-01,1.208736292509734606e-01,1.208769225709167977e-01,1.212993017454754574e-01,1.209340517350286498e-01,1.214517326608139658e-01,1.213602936558167561e-01,
                         1.215191690353476101e-01,1.217244545095592240e-01,1.215870411275813689e-01,1.221715417306901141e-01,1.217089933928585249e-01,1.222822027398987876e-01,1.219071910243721690e-01,1.223637695685854399e-01,1.220541784447288225e-01,1.222037625456269122e-01,1.223765005856997656e-01,1.223291331593059916e-01,1.226882020495295572e-01,1.223024486028682217e-01,1.228281345992975060e-01,1.225781311876187191e-01,1.227313875978875840e-01,1.230064836927244332e-01,1.226277902682943732e-01,1.232589609146684528e-01,1.228342204455128844e-01,1.232645579884300291e-01,1.234715372417663493e-01,1.230128421153333235e-01,1.241515066297723124e-01,1.232987298184645003e-01,1.240603802449506410e-01,1.237348782077773435e-01,1.237285732695442980e-01,1.244807111761610935e-01,1.235457817550754678e-01,1.247697745091055493e-01,1.236747442383627077e-01,1.247326079102206858e-01,1.242213203635835900e-01,1.245421420524964046e-01,1.247710294304253675e-01,1.244650928947143992e-01,1.248271119128254725e-01,1.247987360690676617e-01,1.244685938288479510e-01,1.251338747809676299e-01,1.243771159482582322e-01,1.252789706328314989e-01,1.246231032928620946e-01,1.249164720778899174e-01,1.249746234291334301e-01,1.248485392952793788e-01,1.250028774501653062e-01,1.248366749738733794e-01,1.250750864014727459e-01,1.252656885306378531e-01,1.250640305224609838e-01,1.255927199627266677e-01,1.250991326051976160e-01,1.255408475358684994e-01,1.252616464573189925e-01,1.255958134260753145e-01,1.256201425374331160e-01,1.255613818890158329e-01,1.257255168047575200e-01,1.256844032608949724e-01,1.258183951777515353e-01,1.258892199078921470e-01,1.256981782912165446e-01,1.261420680135666439e-01,1.257854232311886866e-01,1.262112241799145662e-01,1.259517175583438064e-01,1.260501679740780034e-01,1.264028660980600349e-01,1.258588794606759487e-01,1.266462258133378982e-01,1.258102918597778785e-01,1.267537007128687054e-01,1.260159294915754458e-01,1.269427750301107272e-01,1.262796147505322042e-01,1.268580690506043440e-01,1.265621346892543131e-01,1.270183142417593281e-01,1.266493115782252599e-01,1.271868747791729537e-01,1.268090707763924463e-01,1.272315987485296840e-01,1.269442153293607600e-01,1.271665231116866912e-01,1.274034859740506287e-01,1.270660508997033533e-01,1.275690933404570737e-01,1.273285077956537448e-01,1.273703953242355524e-01,1.279372307542886722e-01,1.271266009253600171e-01,1.283805567904676148e-01,1.272289721936145368e-01,1.283323969088152328e-01,1.277866008346764115e-01,1.278586069156599225e-01,1.284177946607787946e-01,1.276221769517117410e-01,1.287891346329899100e-01,1.274624266599788669e-01,1.288429859851013271e-01,1.276564802771160412e-01,1.284824986067857333e-01,1.280534650278348507e-01,1.278979145529080264e-01,1.284061831155639821e-01,1.275960381095439244e-01,1.281630652556758343e-01,1.276554582589541909e-01,1.277532367593929574e-01,1.279687839503659275e-01,1.275040584512444064e-01,1.279953779092038446e-01,1.277529591912991980e-01,1.275936440463603661e-01,1.281604754376561572e-01,1.274382425591763790e-01,1.280865956045645626e-01,
                         1.276599662573240368e-01,1.276386662313028497e-01,1.280824283794094742e-01,1.271722942469360740e-01,1.282651072987733287e-01,1.272482379583022849e-01,1.281785875823587273e-01,1.278008837459483349e-01,1.276934034631450610e-01,1.285385759182999799e-01,1.276078420271227198e-01,1.286676189334068354e-01,1.279695309714427021e-01,1.285938715660517040e-01,1.285544916516359881e-01,1.282783293978369821e-01,1.288402666328852253e-01,1.286335730182974202e-01,1.287528152978134055e-01,1.291555070826490015e-01,1.286957030500819887e-01,1.296158906432092750e-01,1.292087846614850266e-01,1.294455631743748614e-01,1.302491673342879575e-01,1.290494350451469874e-01,1.307554863411240775e-01,1.295565538701594077e-01,1.306567239573366845e-01,1.303942367465983077e-01,1.306363409290102751e-01,1.308907628172946980e-01,1.309992900602313659e-01,1.312270441176822955e-01,1.310281191065970630e-01,1.318220629901263874e-01,1.310072627208296037e-01,1.320108814833260980e-01,1.315333629309878294e-01,1.318150179857346116e-01,1.322368150178674651e-01,1.316326093925790641e-01,1.326124755333480953e-01,1.322200143133004380e-01,1.318568878194977256e-01,1.334823055346094078e-01,1.315834286354000404e-01,1.336588792584333385e-01,1.323491157952836339e-01,1.326568895384335478e-01,1.337903866196421265e-01,1.320865798511019207e-01,1.337021923561222958e-01,1.330039285398801063e-01,1.326595847573002473e-01,1.340491205937471841e-01,1.324742770821852877e-01,1.336068622593845068e-01,1.335869827935711185e-01,1.324631847151671871e-01,1.344936906391304143e-01,1.325397435466846296e-01,1.337551898633244918e-01,1.337510091414972069e-01,1.330374608801367098e-01,1.341220130261062404e-01,1.337234587057465340e-01,1.331049098917186368e-01,1.348006709526923530e-01,1.327133189113006706e-01,1.346167431059989705e-01,1.337339734896857424e-01,1.333423033531289381e-01,
                         1.347572432880176363e-01,1.329780794757820794e-01,1.340886049726614238e-01,1.342904954550953600e-01,1.326039203748758111e-01,1.353474237211804987e-01,1.326188992341015560e-01,1.340956357102968677e-01,1.343585775884374445e-01,1.327029032105706829e-01,1.351924831752717160e-01,1.328742166157218518e-01,1.342768098953187050e-01,1.342265106954476650e-01,1.331413543954850787e-01,1.350230616582517584e-01,1.335099914695636325e-01,1.343317950720706311e-01,1.345681154593684481e-01,1.335080839482725990e-01,1.352364562767141010e-01,1.333036847480604525e-01,1.351031857484326359e-01,1.340064811859398297e-01,1.343984471610959186e-01,1.347901061537269407e-01,1.336595438800022573e-01,1.354533996072884994e-01,1.335209359852788658e-01,1.350587265972487683e-01,1.349238319729045565e-01,1.335536393817107759e-01,1.364262671548826522e-01,1.334400501917671067e-01,1.355636555918020847e-01,1.358612201190445568e-01,1.332392084265087429e-01,1.378801589641773795e-01,1.338780464322649189e-01,1.357571782814440131e-01,1.383370171344892319e-01,1.320845907907548522e-01,1.406159288004036056e-01,1.340227460699492390e-01,1.352269477854095014e-01,1.425757720606773693e-01,1.280849828354365116e-01,1.455961924036168198e-01,1.330221677790578982e-01,1.332550899492858376e-01,1.504958123526211333e-01,1.198131550300526732e-01,1.522171980844701233e-01,1.343682283420394030e-01,1.241790162331177505e-01,1.680474896393668593e-01,1.044785735030478446e-01,1.384028302032833668e-01,2.177348128303986385e-01])

        data = data[self.wf_start:]
        if length_smpl < np.size(data):
            N = length_smpl
        else:
            N = np.size(data)
        # print('length_smpl ', length_smpl)
        # print('N ', N)
        # print('start ', start)
        res = np.zeros(length_smpl)
        res[0:N] = data[0:N]
        samples[start:start + length_smpl] = np.int16(np.round(res * amps * 2047, 1))


        # print('length_smpl ', length_smpl)
        # print('N ', N)
        # print('start ', start)
        #
        # res[0:N] = data[start:N]
        # samples[0:0 + length_smpl] = np.int16(np.round(res * amps * 2047, 1))


    def gauss_6ns(self, samples, start, amps, inv_fwhm, length_smpl):
            """

            """

            data = np.array([-1.187220848286748903e-03,
                             -1.187220848286748903e-03,
                             -1.187220848286748903e-03,
                             4.828135447051377254e-04,
                             4.828135447051377254e-04,
                             4.828135447051377254e-04,
                             -1.570595079336148045e-03,
                             -1.570595079336148045e-03,
                             -1.570595079336148045e-03,
                             1.519657203184074867e-04,
                             1.519657203184074867e-04,
                             1.519657203184074867e-04,
                             -7.996707125387561262e-04,
                             -7.996707125387561262e-04,
                             -7.996707125387561262e-04,
                             -9.518278420321667904e-04,
                             -9.518278420321667904e-04,
                             -9.518278420321667904e-04,
                             8.271197265701058583e-05,
                             8.271197265701058583e-05,
                             8.271197265701058583e-05,
                             -1.246645942314140998e-03,
                             -1.246645942314140998e-03,
                             -1.246645942314140998e-03,
                             -4.261105672183859738e-04,
                             -4.261105672183859738e-04,
                             -4.261105672183859738e-04,
                             -4.129308105529412186e-04,
                             -4.129308105529412186e-04,
                             -4.129308105529412186e-04,
                             -1.290559586043219095e-03,
                             -1.290559586043219095e-03,
                             -1.290559586043219095e-03,
                             1.907771497834773893e-04,
                             1.907771497834773893e-04,
                             1.907771497834773893e-04,
                             -1.259821077601645106e-03,
                             -1.259821077601645106e-03,
                             -1.259821077601645106e-03,
                             -4.385490732717420184e-04,
                             -4.385490732717420184e-04,
                             -4.385490732717420184e-04,
                             -1.574702953326387106e-04,
                             -1.574702953326387106e-04,
                             -1.574702953326387106e-04,
                             -1.463174472267477974e-03,
                             -1.463174472267477974e-03,
                             -1.463174472267477974e-03,
                             5.311776108453019393e-04,
                             5.311776108453019393e-04,
                             5.311776108453019393e-04,
                             -1.225533197685965041e-03,
                             -1.225533197685965041e-03,
                             -1.225533197685965041e-03,
                             -1.987414331442351060e-04,
                             -1.987414331442351060e-04,
                             -1.987414331442351060e-04,
                             2.082109532119588962e-04,
                             2.082109532119588962e-04,
                             2.082109532119588962e-04,
                             -1.250137331188973938e-03,
                             -1.250137331188973938e-03,
                             -1.250137331188973938e-03,
                             1.360595952372435939e-03,
                             1.360595952372435939e-03,
                             1.360595952372435939e-03,
                             -1.274010038876359063e-03,
                             -1.274010038876359063e-03,
                             -1.274010038876359063e-03,
                             1.446533564216293108e-03,
                             1.446533564216293108e-03,
                             1.446533564216293108e-03,
                             4.583614608476091088e-04,
                             4.583614608476091088e-04,
                             4.583614608476091088e-04,
                             5.094054884033548608e-04,
                             5.094054884033548608e-04,
                             5.094054884033548608e-04,
                             2.901866204589466803e-03,
                             2.901866204589466803e-03,
                             2.901866204589466803e-03,
                             7.382345974521427106e-04,
                             7.382345974521427106e-04,
                             7.382345974521427106e-04,
                             3.945260940998564572e-03,
                             3.945260940998564572e-03,
                             3.945260940998564572e-03,
                             3.412756494777474930e-03,
                             3.412756494777474930e-03,
                             3.412756494777474930e-03,
                             4.346007262495008190e-03,
                             4.346007262495008190e-03,
                             4.346007262495008190e-03,
                             7.047734685909570404e-03,
                             7.047734685909570404e-03,
                             7.047734685909570404e-03,
                             6.230908136158719995e-03,
                             6.230908136158719995e-03,
                             6.230908136158719995e-03,
                             1.021797949625768975e-02,
                             1.021797949625768975e-02,
                             1.021797949625768975e-02,
                             1.118950399710470084e-02,
                             1.118950399710470084e-02,
                             1.118950399710470084e-02,
                             1.299190805636980979e-02,
                             1.299190805636980979e-02,
                             1.299190805636980979e-02,
                             1.822691797730729979e-02,
                             1.822691797730729979e-02,
                             1.822691797730729979e-02,
                             1.817228406686633921e-02,
                             1.817228406686633921e-02,
                             1.817228406686633921e-02,
                             2.514525868648966045e-02,
                             2.514525868648966045e-02,
                             2.514525868648966045e-02,
                             2.760635075989784082e-02,
                             2.760635075989784082e-02,
                             2.760635075989784082e-02,
                             3.259564341020691758e-02,
                             3.259564341020691758e-02,
                             3.259564341020691758e-02,
                             4.017215480895029722e-02,
                             4.017215480895029722e-02,
                             4.017215480895029722e-02,
                             4.338188958010710111e-02,
                             4.338188958010710111e-02,
                             4.338188958010710111e-02,
                             5.384186549397473875e-02,
                             5.384186549397473875e-02,
                             5.384186549397473875e-02,
                             5.961783450662856698e-02,
                             5.961783450662856698e-02,
                             5.961783450662856698e-02,
                             6.846428946111142444e-02,
                             6.846428946111142444e-02,
                             6.846428946111142444e-02,
                             8.019557584145742268e-02,
                             8.019557584145742268e-02,
                             8.019557584145742268e-02,
                             8.787307152041184954e-02,
                             8.787307152041184954e-02,
                             8.787307152041184954e-02,
                             1.017448495488176008e-01,
                             1.017448495488176008e-01,
                             1.017448495488176008e-01,
                             1.141825073807222063e-01,
                             1.141825073807222063e-01,
                             1.141825073807222063e-01,
                             1.255812450710468986e-01,
                             1.255812450710468986e-01,
                             1.255812450710468986e-01,
                             1.443882225159034138e-01,
                             1.443882225159034138e-01,
                             1.443882225159034138e-01,
                             1.553800342169497084e-01,
                             1.553800342169497084e-01,
                             1.553800342169497084e-01,
                             1.757115377453982996e-01,
                             1.757115377453982996e-01,
                             1.757115377453982996e-01,
                             1.927019153728624923e-01,
                             1.927019153728624923e-01,
                             1.927019153728624923e-01,
                             2.085029170215569050e-01,
                             2.085029170215569050e-01,
                             2.085029170215569050e-01,
                             2.344185898278406122e-01,
                             2.344185898278406122e-01,
                             2.344185898278406122e-01,
                             2.477124174326580941e-01,
                             2.477124174326580941e-01,
                             2.477124174326580941e-01,
                             2.746662469479906887e-01,
                             2.746662469479906887e-01,
                             2.746662469479906887e-01,
                             2.969817866430157216e-01,
                             2.969817866430157216e-01,
                             2.969817866430157216e-01,
                             3.129423554619520931e-01,
                             3.129423554619520931e-01,
                             3.129423554619520931e-01,
                             3.512688393560967071e-01,
                             3.512688393560967071e-01,
                             3.512688393560967071e-01,
                             3.580522222776337249e-01,
                             3.580522222776337249e-01,
                             3.580522222776337249e-01,
                             3.985423436988084767e-01,
                             3.985423436988084767e-01,
                             3.985423436988084767e-01,
                             4.194964721645640937e-01,
                             4.194964721645640937e-01,
                             4.194964721645640937e-01,
                             4.356999745971851801e-01,
                             4.356999745971851801e-01,
                             4.356999745971851801e-01,
                             4.881706471099622746e-01,
                             4.881706471099622746e-01,
                             4.881706471099622746e-01,
                             4.816768477354880784e-01,
                             4.816768477354880784e-01,
                             4.816768477354880784e-01,
                             5.379402480887450766e-01,
                             5.379402480887450766e-01,
                             5.379402480887450766e-01,
                             5.584364280578268946e-01,
                             5.584364280578268946e-01,
                             5.584364280578268946e-01,
                             5.640529312078182977e-01,
                             5.640529312078182977e-01,
                             5.640529312078182977e-01,
                             6.315552090551188602e-01,
                             6.315552090551188602e-01,
                             6.315552090551188602e-01,
                             6.453641462811486873e-01,
                             6.453641462811486873e-01,
                             6.453641462811486873e-01,
                             6.391011757791680292e-01,
                             6.391011757791680292e-01,
                             6.391011757791680292e-01,
                             6.023233902912025206e-01,
                             6.023233902912025206e-01,
                             6.023233902912025206e-01,
                             5.597180191305234365e-01,
                             5.597180191305234365e-01,
                             5.597180191305234365e-01,
                             5.440126473652496797e-01,
                             5.440126473652496797e-01,
                             5.440126473652496797e-01,
                             4.950026803665584230e-01,
                             4.950026803665584230e-01,
                             4.950026803665584230e-01,
                             4.862580243887986153e-01,
                             4.862580243887986153e-01,
                             4.862580243887986153e-01,
                             4.428305912248687859e-01,
                             4.428305912248687859e-01,
                             4.428305912248687859e-01,
                             4.215047452993929133e-01,
                             4.215047452993929133e-01,
                             4.215047452993929133e-01,
                             4.002942939197273176e-01,
                             4.002942939197273176e-01,
                             4.002942939197273176e-01,
                             3.611125172774521941e-01,
                             3.611125172774521941e-01,
                             3.611125172774521941e-01,
                             3.493872895111962973e-01,
                             3.493872895111962973e-01,
                             3.493872895111962973e-01,
                             3.149098531184307825e-01,
                             3.149098531184307825e-01,
                             3.149098531184307825e-01,
                             2.951555525686909154e-01,
                             2.951555525686909154e-01,
                             2.951555525686909154e-01,
                             2.739984648972335068e-01,
                             2.739984648972335068e-01,
                             2.739984648972335068e-01,
                             2.439223667736971080e-01,
                             2.439223667736971080e-01,
                             2.439223667736971080e-01,
                             2.324692382551374059e-01,
                             2.324692382551374059e-01,
                             2.324692382551374059e-01,
                             2.056406661927797919e-01,
                             2.056406661927797919e-01,
                             2.056406661927797919e-01,
                             1.896886128834519014e-01,
                             1.896886128834519014e-01,
                             1.896886128834519014e-01,
                             1.731737055234980061e-01,
                             1.731737055234980061e-01,
                             1.731737055234980061e-01,
                             1.500423102395861963e-01,
                             1.500423102395861963e-01,
                             1.500423102395861963e-01,
                             1.402191513851384908e-01,
                             1.402191513851384908e-01,
                             1.402191513851384908e-01,
                             1.197264472216335029e-01,
                             1.197264472216335029e-01,
                             1.197264472216335029e-01,
                             1.086072155370430004e-01,
                             1.086072155370430004e-01,
                             1.086072155370430004e-01,
                             9.681228243750822360e-02,
                             9.681228243750822360e-02,
                             9.681228243750822360e-02,
                             8.207941586825048819e-02,
                             8.207941586825048819e-02,
                             8.207941586825048819e-02,
                             7.780038281276331624e-02,
                             7.780038281276331624e-02,
                             7.780038281276331624e-02,
                             6.378097670020084486e-02,
                             6.378097670020084486e-02,
                             6.378097670020084486e-02,
                             5.801990249706087677e-02,
                             5.801990249706087677e-02,
                             5.801990249706087677e-02,
                             5.036146009131819284e-02,
                             5.036146009131819284e-02,
                             5.036146009131819284e-02,
                             4.129528507352542288e-02,
                             4.129528507352542288e-02,
                             4.129528507352542288e-02,
                             3.838394139068931898e-02,
                             3.838394139068931898e-02,
                             3.838394139068931898e-02,
                             3.082260331017086866e-02,
                             3.082260331017086866e-02,
                             3.082260331017086866e-02,
                             2.857700327197328083e-02,
                             2.857700327197328083e-02,
                             2.857700327197328083e-02,
                             2.506342584715330959e-02,
                             2.506342584715330959e-02,
                             2.506342584715330959e-02,
                             2.069062621844418998e-02,
                             2.069062621844418998e-02,
                             2.069062621844418998e-02,
                             2.064342447800128835e-02,
                             2.064342447800128835e-02,
                             2.064342447800128835e-02,
                             1.670394892664421940e-02,
                             1.670394892664421940e-02,
                             1.670394892664421940e-02,
                             1.602463360425435135e-02,
                             1.602463360425435135e-02,
                             1.602463360425435135e-02,
                             1.510209781224913957e-02,
                             1.510209781224913957e-02,
                             1.510209781224913957e-02,
                             1.300532349529760941e-02,
                             1.300532349529760941e-02,
                             1.300532349529760941e-02,
                             1.420888436881342053e-02,
                             1.420888436881342053e-02,
                             1.420888436881342053e-02,
                             1.294619059022092920e-02,
                             1.294619059022092920e-02,
                             1.294619059022092920e-02,
                             1.279391643505694079e-02,
                             1.279391643505694079e-02,
                             1.279391643505694079e-02,
                             1.411984321320432917e-02,
                             1.411984321320432917e-02,
                             1.411984321320432917e-02,
                             1.232111360958776033e-02,
                             1.232111360958776033e-02,
                             1.232111360958776033e-02,
                             1.457260511188234950e-02,
                             1.457260511188234950e-02,
                             1.457260511188234950e-02,
                             1.372829583126379017e-02,
                             1.372829583126379017e-02,
                             1.372829583126379017e-02,
                             1.440220018590171978e-02,
                             1.440220018590171978e-02,
                             1.440220018590171978e-02,
                             1.556206076565903006e-02,
                             1.556206076565903006e-02,
                             1.556206076565903006e-02,
                             1.475908919774308013e-02,
                             1.475908919774308013e-02,
                             1.475908919774308013e-02,
                             1.654078746340604048e-02,
                             1.654078746340604048e-02,
                             1.654078746340604048e-02,
                             1.687048163048245064e-02,
                             1.687048163048245064e-02,
                             1.687048163048245064e-02,
                             1.689611825646551019e-02,
                             1.689611825646551019e-02,
                             1.689611825646551019e-02,
                             1.902957529330989023e-02,
                             1.902957529330989023e-02,
                             1.902957529330989023e-02,
                             1.780304626589155129e-02,
                             1.780304626589155129e-02,
                             1.780304626589155129e-02,
                             1.973444646750804887e-02,
                             1.973444646750804887e-02,
                             1.973444646750804887e-02,
                             1.984986298132284874e-02,
                             1.984986298132284874e-02,
                             1.984986298132284874e-02,
                             1.987995960799330067e-02,
                             1.987995960799330067e-02,
                             1.987995960799330067e-02,
                             2.176575588812998049e-02,
                             2.176575588812998049e-02,
                             2.176575588812998049e-02,
                             2.081604356756117102e-02,
                             2.081604356756117102e-02,
                             2.081604356756117102e-02,
                             2.247513561444445043e-02,
                             2.247513561444445043e-02,
                             2.247513561444445043e-02,
                             2.249466752146312906e-02,
                             2.249466752146312906e-02,
                             2.249466752146312906e-02,
                             2.279051364418394066e-02,
                             2.279051364418394066e-02,
                             2.279051364418394066e-02,
                             2.378691722272342074e-02,
                             2.378691722272342074e-02,
                             2.378691722272342074e-02,
                             2.378710596048949980e-02,
                             2.378710596048949980e-02,
                             2.378710596048949980e-02,
                             2.423522126985043143e-02,
                             2.423522126985043143e-02,
                             2.423522126985043143e-02,
                             2.540181689808894069e-02,
                             2.540181689808894069e-02,
                             2.540181689808894069e-02,
                             2.438092484941017934e-02,
                             2.438092484941017934e-02,
                             2.438092484941017934e-02,
                             2.627631596688860885e-02,
                             2.627631596688860885e-02,
                             2.627631596688860885e-02,
                             2.533411765846286037e-02,
                             2.533411765846286037e-02,
                             2.533411765846286037e-02,
                             2.629267506450125996e-02,
                             2.629267506450125996e-02,
                             2.629267506450125996e-02,
                             2.666513939759461091e-02,
                             2.666513939759461091e-02,
                             2.666513939759461091e-02,
                             2.621743046983100039e-02,
                             2.621743046983100039e-02,
                             2.621743046983100039e-02,
                             2.757458908093041172e-02,
                             2.757458908093041172e-02,
                             2.757458908093041172e-02,
                             2.666697262284525166e-02,
                             2.666697262284525166e-02,
                             2.666697262284525166e-02,
                             2.775985067354432012e-02,
                             2.775985067354432012e-02,
                             2.775985067354432012e-02,
                             2.751624069176208942e-02,
                             2.751624069176208942e-02,
                             2.751624069176208942e-02,
                             2.765210578795190832e-02,
                             2.765210578795190832e-02,
                             2.765210578795190832e-02,
                             2.817961337814501102e-02,
                             2.817961337814501102e-02,
                             2.817961337814501102e-02,
                             2.783707274093526890e-02,
                             2.783707274093526890e-02,
                             2.783707274093526890e-02,
                             2.854466396443029047e-02,
                             2.854466396443029047e-02,
                             2.854466396443029047e-02,
                             2.835335166356281120e-02,
                             2.835335166356281120e-02,
                             2.835335166356281120e-02,
                             2.871864317735836961e-02,
                             2.871864317735836961e-02,
                             2.871864317735836961e-02,
                             2.875959153660369999e-02,
                             2.875959153660369999e-02,
                             2.875959153660369999e-02,
                             2.898111623853315971e-02,
                             2.898111623853315971e-02,
                             2.898111623853315971e-02,
                             2.904441614063745999e-02,
                             2.904441614063745999e-02,
                             2.904441614063745999e-02,
                             2.916665009490122112e-02,
                             2.916665009490122112e-02,
                             2.916665009490122112e-02,
                             2.935103370451004959e-02,
                             2.935103370451004959e-02,
                             2.935103370451004959e-02,
                             2.930838925426439839e-02,
                             2.930838925426439839e-02,
                             2.930838925426439839e-02,
                             2.949537924357919019e-02,
                             2.949537924357919019e-02,
                             2.949537924357919019e-02,
                             2.959613792591936007e-02,
                             2.959613792591936007e-02,
                             2.959613792591936007e-02,
                             2.939003552210203013e-02,
                             2.939003552210203013e-02,
                             2.939003552210203013e-02,
                             3.015590653003137958e-02,
                             3.015590653003137958e-02,
                             3.015590653003137958e-02,
                             2.929138340847442859e-02,
                             2.929138340847442859e-02,
                             2.929138340847442859e-02,
                             3.034496042995757023e-02,
                             3.034496042995757023e-02,
                             3.034496042995757023e-02,
                             2.965564382875747126e-02,
                             2.965564382875747126e-02,
                             2.965564382875747126e-02,
                             3.014096372348451860e-02,
                             3.014096372348451860e-02,
                             3.014096372348451860e-02,
                             3.034978031885796068e-02,
                             3.034978031885796068e-02,
                             3.034978031885796068e-02,
                             2.989438662209617861e-02,
                             2.989438662209617861e-02,
                             2.989438662209617861e-02,
                             3.064634063767212105e-02,
                             3.064634063767212105e-02,
                             3.064634063767212105e-02,
                             2.997924955633573044e-02,
                             2.997924955633573044e-02,
                             2.997924955633573044e-02,
                             3.048747153499246909e-02,
                             3.048747153499246909e-02,
                             3.048747153499246909e-02,
                             3.038378000914684907e-02,
                             3.038378000914684907e-02,
                             3.038378000914684907e-02,
                             3.010636967431244010e-02,
                             3.010636967431244010e-02,
                             3.010636967431244010e-02,
                             3.064601900962012071e-02,
                             3.064601900962012071e-02,
                             3.064601900962012071e-02,
                             2.998501425169492959e-02,
                             2.998501425169492959e-02,
                             2.998501425169492959e-02,
                             3.059962688495743849e-02,
                             3.059962688495743849e-02,
                             3.059962688495743849e-02,
                             3.026963998222486144e-02,
                             3.026963998222486144e-02,
                             3.026963998222486144e-02,
                             3.036973812075320980e-02,
                             3.036973812075320980e-02,
                             3.036973812075320980e-02,
                             3.068479903285581054e-02,
                             3.068479903285581054e-02,
                             3.068479903285581054e-02,
                             3.024636908142493141e-02,
                             3.024636908142493141e-02,
                             3.024636908142493141e-02,
                             3.090060878404349981e-02,
                             3.090060878404349981e-02,
                             3.090060878404349981e-02,
                             3.052881078478044893e-02,
                             3.052881078478044893e-02,
                             3.052881078478044893e-02,
                             3.095070291466764031e-02,
                             3.095070291466764031e-02,
                             3.095070291466764031e-02,
                             3.079697718412723051e-02,
                             3.079697718412723051e-02,
                             3.079697718412723051e-02,
                             3.077684887951112960e-02,
                             3.077684887951112960e-02,
                             3.077684887951112960e-02,
                             3.103133264556676152e-02,
                             3.103133264556676152e-02,
                             3.103133264556676152e-02,
                             3.076886320880957079e-02,
                             3.076886320880957079e-02,
                             3.076886320880957079e-02,
                             3.121924107031207041e-02,
                             3.121924107031207041e-02,
                             3.121924107031207041e-02,
                             3.101986427117443129e-02,
                             3.101986427117443129e-02,
                             3.101986427117443129e-02,
                             3.110856470476481075e-02,
                             3.110856470476481075e-02,
                             3.110856470476481075e-02,
                             3.128963663424316755e-02,
                             3.128963663424316755e-02,
                             3.128963663424316755e-02,
                             3.102285124304648978e-02,
                             3.102285124304648978e-02,
                             3.102285124304648978e-02,
                             3.131738756449253119e-02,
                             3.131738756449253119e-02,
                             3.131738756449253119e-02,
                             3.120811089365338117e-02,
                             3.120811089365338117e-02,
                             3.120811089365338117e-02,
                             3.122774308593926143e-02,
                             3.122774308593926143e-02,
                             3.122774308593926143e-02,
                             3.162191684173581291e-02,
                             3.162191684173581291e-02,
                             3.162191684173581291e-02,
                             3.105322822234963046e-02,
                             3.105322822234963046e-02,
                             3.105322822234963046e-02,
                             3.159594002544566238e-02,
                             3.159594002544566238e-02,
                             3.159594002544566238e-02,
                             3.117097711702129098e-02,
                             3.117097711702129098e-02,
                             3.117097711702129098e-02,
                             3.176393599737457191e-02,
                             3.176393599737457191e-02,
                             3.176393599737457191e-02,
                             3.179319834065973821e-02,
                             3.179319834065973821e-02,
                             3.179319834065973821e-02,
                             3.166798888980572324e-02,
                             3.166798888980572324e-02,
                             3.166798888980572324e-02,
                             3.207099338121262300e-02,
                             3.207099338121262300e-02,
                             3.207099338121262300e-02,
                             3.164836229211676760e-02,
                             3.164836229211676760e-02,
                             3.164836229211676760e-02,
                             3.225679218885994792e-02,
                             3.225679218885994792e-02,
                             3.225679218885994792e-02,
                             3.210797021742067825e-02,
                             3.210797021742067825e-02,
                             3.210797021742067825e-02,
                             3.217127254727236707e-02,
                             3.217127254727236707e-02,
                             3.217127254727236707e-02,
                             3.259702078741497783e-02,
                             3.259702078741497783e-02,
                             3.259702078741497783e-02,
                             3.223958037229752299e-02,
                             3.223958037229752299e-02,
                             3.223958037229752299e-02,
                             3.305310118153576004e-02,
                             3.305310118153576004e-02,
                             3.305310118153576004e-02,
                             3.255892015183633331e-02,
                             3.255892015183633331e-02,
                             3.255892015183633331e-02,
                             3.334252982397867271e-02,
                             3.334252982397867271e-02,
                             3.334252982397867271e-02,
                             3.313051595868696242e-02,
                             3.313051595868696242e-02,
                             3.313051595868696242e-02,
                             3.337813289557887975e-02,
                             3.337813289557887975e-02,
                             3.337813289557887975e-02,
                             3.362440847098369101e-02,
                             3.362440847098369101e-02,
                             3.362440847098369101e-02,
                             3.346764339831276303e-02,
                             3.346764339831276303e-02,
                             3.346764339831276303e-02,
                             3.387250416956724686e-02,
                             3.387250416956724686e-02,
                             3.387250416956724686e-02,
                             3.389773171431331722e-02,
                             3.389773171431331722e-02,
                             3.389773171431331722e-02,
                             3.370641053075199706e-02,
                             3.370641053075199706e-02,
                             3.370641053075199706e-02,
                             3.415175863343367785e-02,
                             3.415175863343367785e-02,
                             3.415175863343367785e-02,
                             3.345709670740267677e-02,
                             3.345709670740267677e-02,
                             3.345709670740267677e-02,
                             3.406954154043583677e-02,
                             3.406954154043583677e-02,
                             3.406954154043583677e-02,
                             3.354285975659641178e-02,
                             3.354285975659641178e-02,
                             3.354285975659641178e-02,
                             3.387281262677212940e-02,
                             3.387281262677212940e-02,
                             3.387281262677212940e-02,
                             3.370556607160000301e-02,
                             3.370556607160000301e-02,
                             3.370556607160000301e-02,
                             3.374548768735406712e-02,
                             3.374548768735406712e-02,
                             3.374548768735406712e-02,
                             3.373327922365550180e-02,
                             3.373327922365550180e-02,
                             3.373327922365550180e-02,
                             3.388166392306644209e-02,
                             3.388166392306644209e-02,
                             3.388166392306644209e-02,
                             3.360925929810677781e-02,
                             3.360925929810677781e-02,
                             3.360925929810677781e-02,
                             3.402186918322486903e-02,
                             3.402186918322486903e-02,
                             3.402186918322486903e-02,
                             3.360389169488726957e-02,
                             3.360389169488726957e-02,
                             3.360389169488726957e-02,
                             3.395367524276306226e-02,
                             3.395367524276306226e-02,
                             3.395367524276306226e-02,
                             3.371542668877341303e-02,
                             3.371542668877341303e-02,
                             3.371542668877341303e-02,
                             3.378337262527319335e-02,
                             3.378337262527319335e-02,
                             3.378337262527319335e-02,
                             3.391672670981354248e-02,
                             3.391672670981354248e-02,
                             3.391672670981354248e-02,
                             3.362225928466498065e-02,
                             3.362225928466498065e-02,
                             3.362225928466498065e-02,
                             3.405454823457088054e-02,
                             3.405454823457088054e-02,
                             3.405454823457088054e-02,
                             3.349746330191918225e-02,
                             3.349746330191918225e-02,
                             3.349746330191918225e-02,
                             3.416865868029257680e-02,
                             3.416865868029257680e-02,
                             3.416865868029257680e-02,
                             3.357359307486561251e-02,
                             3.357359307486561251e-02,
                             3.357359307486561251e-02,
                             3.400674382032217030e-02,
                             3.400674382032217030e-02,
                             3.400674382032217030e-02,
                             3.393337939003084752e-02,
                             3.393337939003084752e-02,
                             3.393337939003084752e-02,
                             3.362930310548836038e-02,
                             3.362930310548836038e-02,
                             3.362930310548836038e-02,
                             3.435210076853194294e-02,
                             3.435210076853194294e-02,
                             3.435210076853194294e-02,
                             3.335650984414698789e-02,
                             3.335650984414698789e-02,
                             3.335650984414698789e-02,
                             3.458859882488390242e-02,
                             3.458859882488390242e-02,
                             3.458859882488390242e-02,
                             3.359185765393377793e-02,
                             3.359185765393377793e-02,
                             3.359185765393377793e-02,
                             3.424012274390059174e-02,
                             3.424012274390059174e-02,
                             3.424012274390059174e-02,
                             3.426037745738733792e-02,
                             3.426037745738733792e-02,
                             3.426037745738733792e-02,
                             3.361497957792255326e-02,
                             3.361497957792255326e-02,
                             3.361497957792255326e-02,
                             3.488155238962121346e-02,
                             3.488155238962121346e-02,
                             3.488155238962121346e-02,
                             3.334098218793631052e-02,
                             3.334098218793631052e-02,
                             3.334098218793631052e-02,
                             3.483158399816697198e-02,
                             3.483158399816697198e-02,
                             3.483158399816697198e-02,
                             3.365819136335151951e-02,
                             3.365819136335151951e-02,
                             3.365819136335151951e-02,
                             3.415964794263619264e-02,
                             3.415964794263619264e-02,
                             3.415964794263619264e-02,
                             3.432490248260360727e-02,
                             3.432490248260360727e-02,
                             3.432490248260360727e-02,
                             3.344348202062989717e-02,
                             3.344348202062989717e-02,
                             3.344348202062989717e-02,
                             3.448177324651668235e-02,
                             3.448177324651668235e-02,
                             3.448177324651668235e-02,
                             3.337933661364699683e-02,
                             3.337933661364699683e-02,
                             3.337933661364699683e-02,
                             3.409080534008875757e-02,
                             3.409080534008875757e-02,
                             3.409080534008875757e-02,
                             3.378338439983871733e-02,
                             3.378338439983871733e-02,
                             3.378338439983871733e-02,
                             3.353737700241885694e-02,
                             3.353737700241885694e-02,
                             3.353737700241885694e-02,
                             3.407137935878445933e-02,
                             3.407137935878445933e-02,
                             3.407137935878445933e-02,
                             3.343941041692204130e-02,
                             3.343941041692204130e-02,
                             3.343941041692204130e-02,
                             3.386857289211592237e-02,
                             3.386857289211592237e-02,
                             3.386857289211592237e-02,
                             3.363727068390962027e-02,
                             3.363727068390962027e-02,
                             3.363727068390962027e-02,
                             3.342219996130362664e-02,
                             3.342219996130362664e-02,
                             3.342219996130362664e-02,
                             3.383602408362369057e-02,
                             3.383602408362369057e-02,
                             3.383602408362369057e-02,
                             3.321515390393525724e-02,
                             3.321515390393525724e-02,
                             3.321515390393525724e-02,
                             3.361091889549563255e-02,
                             3.361091889549563255e-02,
                             3.361091889549563255e-02,
                             3.338982249480387104e-02,
                             3.338982249480387104e-02,
                             3.338982249480387104e-02,
                             3.322238611608092917e-02,
                             3.322238611608092917e-02,
                             3.322238611608092917e-02,
                             3.362822816359686828e-02,
                             3.362822816359686828e-02,
                             3.362822816359686828e-02,
                             3.290817389204112042e-02,
                             3.290817389204112042e-02,
                             3.290817389204112042e-02,
                             3.374252408754663951e-02,
                             3.374252408754663951e-02,
                             3.374252408754663951e-02,
                             3.284834574751514108e-02,
                             3.284834574751514108e-02,
                             3.284834574751514108e-02,
                             3.357625694356342755e-02,
                             3.357625694356342755e-02,
                             3.357625694356342755e-02,
                             3.298659986297679952e-02,
                             3.298659986297679952e-02,
                             3.298659986297679952e-02,
                             3.330398465227425719e-02,
                             3.330398465227425719e-02,
                             3.330398465227425719e-02,
                             3.312603749113499779e-02,
                             3.312603749113499779e-02,
                             3.312603749113499779e-02,
                             3.307733825995046173e-02,
                             3.307733825995046173e-02,
                             3.307733825995046173e-02,
                             3.313018978847630247e-02,
                             3.313018978847630247e-02,
                             3.313018978847630247e-02,
                             3.304290943127367181e-02,
                             3.304290943127367181e-02,
                             3.304290943127367181e-02,
                             3.316077051433231893e-02,
                             3.316077051433231893e-02,
                             3.316077051433231893e-02,
                             3.310122304031423712e-02,
                             3.310122304031423712e-02,
                             3.310122304031423712e-02,
                             3.326593979860049261e-02,
                             3.326593979860049261e-02,
                             3.326593979860049261e-02,
                             3.320911946415341237e-02,
                             3.320911946415341237e-02,
                             3.320911946415341237e-02,
                             3.337329302133725667e-02,
                             3.337329302133725667e-02,
                             3.337329302133725667e-02,
                             3.324967224748259786e-02,
                             3.324967224748259786e-02,
                             3.324967224748259786e-02,
                             3.364085318084925058e-02,
                             3.364085318084925058e-02,
                             3.364085318084925058e-02,
                             3.322504006252641195e-02,
                             3.322504006252641195e-02,
                             3.322504006252641195e-02,
                             3.393151887072261286e-02,
                             3.393151887072261286e-02,
                             3.393151887072261286e-02,
                             3.328553693620565912e-02,
                             3.328553693620565912e-02,
                             3.328553693620565912e-02,
                             3.414993461442830669e-02,
                             3.414993461442830669e-02,
                             3.414993461442830669e-02,
                             3.357040565772779345e-02,
                             3.357040565772779345e-02,
                             3.357040565772779345e-02,
                             3.410069188683598207e-02,
                             3.410069188683598207e-02,
                             3.410069188683598207e-02,
                             3.413894662171004096e-02,
                             3.413894662171004096e-02,
                             3.413894662171004096e-02,
                             3.386827712677274727e-02,
                             3.386827712677274727e-02,
                             3.386827712677274727e-02,
                             3.466105795393684130e-02,
                             3.466105795393684130e-02,
                             3.466105795393684130e-02,
                             3.384987702672125759e-02,
                             3.384987702672125759e-02,
                             3.384987702672125759e-02,
                             3.467474780073154239e-02,
                             3.467474780073154239e-02,
                             3.467474780073154239e-02,
                             3.423903264433186822e-02,
                             3.423903264433186822e-02,
                             3.423903264433186822e-02,
                             3.443906062472722185e-02,
                             3.443906062472722185e-02,
                             3.443906062472722185e-02,
                             3.471421493722900292e-02,
                             3.471421493722900292e-02,
                             3.471421493722900292e-02,
                             3.410161954946701324e-02,
                             3.410161954946701324e-02,
                             3.410161954946701324e-02,
                             3.501428280782459268e-02,
                             3.501428280782459268e-02,
                             3.501428280782459268e-02,
                             3.402498751891359918e-02,
                             3.402498751891359918e-02,
                             3.402498751891359918e-02,
                             3.501491077394207341e-02,
                             3.501491077394207341e-02,
                             3.501491077394207341e-02,
                             3.424909033922703822e-02,
                             3.424909033922703822e-02,
                             3.424909033922703822e-02,
                             3.477526381200626154e-02,
                             3.477526381200626154e-02,
                             3.477526381200626154e-02,
                             3.460585282892870984e-02,
                             3.460585282892870984e-02,
                             3.460585282892870984e-02,
                             3.451916134056977337e-02,
                             3.451916134056977337e-02,
                             3.451916134056977337e-02,
                             3.478200286198208924e-02,
                             3.478200286198208924e-02,
                             3.478200286198208924e-02,
                             3.440952814515681191e-02,
                             3.440952814515681191e-02,
                             3.440952814515681191e-02,
                             3.474914313585542730e-02,
                             3.474914313585542730e-02,
                             3.474914313585542730e-02,
                             3.448990802011982215e-02,
                             3.448990802011982215e-02,
                             3.448990802011982215e-02,
                             3.454789387264701334e-02,
                             3.454789387264701334e-02,
                             3.454789387264701334e-02,
                             3.454116525452236020e-02,
                             3.454116525452236020e-02,
                             3.454116525452236020e-02,
                             3.438096358490078802e-02,
                             3.438096358490078802e-02,
                             3.438096358490078802e-02,
                             3.454866506240562851e-02,
                             3.454866506240562851e-02,
                             3.454866506240562851e-02,
                             3.419359627388726675e-02,
                             3.419359627388726675e-02,
                             3.419359627388726675e-02,
                             3.438946642053603009e-02,
                             3.438946642053603009e-02,
                             3.438946642053603009e-02,
                             3.418042208915814811e-02,
                             3.418042208915814811e-02,
                             3.418042208915814811e-02,
                             3.422409498769010683e-02,
                             3.422409498769010683e-02,
                             3.422409498769010683e-02,
                             3.416834154160663245e-02,
                             3.416834154160663245e-02,
                             3.416834154160663245e-02,
                             3.436795229838243010e-02,
                             3.436795229838243010e-02,
                             3.436795229838243010e-02,
                             3.388239054676345924e-02,
                             3.388239054676345924e-02,
                             3.388239054676345924e-02,
                             3.462439403325658777e-02,
                             3.462439403325658777e-02,
                             3.462439403325658777e-02,
                             3.347634344094965742e-02,
                             3.347634344094965742e-02,
                             3.347634344094965742e-02,
                             3.469263663782565926e-02,
                             3.469263663782565926e-02,
                             3.469263663782565926e-02,
                             3.354043524343398863e-02,
                             3.354043524343398863e-02,
                             3.354043524343398863e-02,
                             3.420944351972984160e-02,
                             3.420944351972984160e-02,
                             3.420944351972984160e-02,
                             3.398197244099875058e-02,
                             3.398197244099875058e-02,
                             3.398197244099875058e-02,
                             3.359083872388073100e-02,
                             3.359083872388073100e-02,
                             3.359083872388073100e-02,
                             3.437820688103754296e-02,
                             3.437820688103754296e-02,
                             3.437820688103754296e-02,
                             3.344779248720017306e-02,
                             3.344779248720017306e-02,
                             3.344779248720017306e-02,
                             3.425555697176468906e-02,
                             3.425555697176468906e-02,
                             3.425555697176468906e-02,
                             3.380463843325388212e-02,
                             3.380463843325388212e-02,
                             3.380463843325388212e-02,
                             3.361979414535057331e-02,
                             3.361979414535057331e-02,
                             3.361979414535057331e-02,
                             3.449325674409355752e-02,
                             3.449325674409355752e-02,
                             3.449325674409355752e-02,
                             3.309110273192549662e-02,
                             3.309110273192549662e-02,
                             3.309110273192549662e-02,
                             3.477400131983227061e-02,
                             3.477400131983227061e-02,
                             3.477400131983227061e-02,
                             3.316883401300160794e-02,
                             3.316883401300160794e-02,
                             3.316883401300160794e-02,
                             3.454990561283709238e-02,
                             3.454990561283709238e-02,
                             3.454990561283709238e-02,
                             3.371587799488544313e-02,
                             3.371587799488544313e-02,
                             3.371587799488544313e-02,
                             3.412294044248113251e-02,
                             3.412294044248113251e-02,
                             3.412294044248113251e-02,
                             3.426753524739024892e-02,
                             3.426753524739024892e-02,
                             3.426753524739024892e-02,
                             3.388614321911240235e-02,
                             3.388614321911240235e-02,
                             3.388614321911240235e-02,
                             3.443587781774957307e-02,
                             3.443587781774957307e-02,
                             3.443587781774957307e-02,
                             3.411707675195387035e-02,
                             3.411707675195387035e-02,
                             3.411707675195387035e-02,
                             3.432663305964053779e-02,
                             3.432663305964053779e-02,
                             3.432663305964053779e-02,
                             3.447452412938972754e-02,
                             3.447452412938972754e-02,
                             3.447452412938972754e-02,
                             3.422118782506290702e-02,
                             3.422118782506290702e-02,
                             3.422118782506290702e-02,
                             3.465777251594818337e-02,
                             3.465777251594818337e-02,
                             3.465777251594818337e-02,
                             3.428444611385943197e-02,
                             3.428444611385943197e-02,
                             3.428444611385943197e-02,
                             3.455241744213354699e-02,
                             3.455241744213354699e-02,
                             3.455241744213354699e-02,
                             3.459664463897634684e-02,
                             3.459664463897634684e-02,
                             3.459664463897634684e-02,
                             3.430990453352705805e-02,
                             3.430990453352705805e-02,
                             3.430990453352705805e-02,
                             3.493005205258781221e-02,
                             3.493005205258781221e-02,
                             3.493005205258781221e-02,
                             3.414040129262881085e-02,
                             3.414040129262881085e-02,
                             3.414040129262881085e-02,
                             3.506482384028909716e-02,
                             3.506482384028909716e-02,
                             3.506482384028909716e-02,
                             3.427124116588566721e-02,
                             3.427124116588566721e-02,
                             3.427124116588566721e-02,
                             3.489262295016173909e-02,
                             3.489262295016173909e-02,
                             3.489262295016173909e-02,
                             3.464002963924085743e-02,
                             3.464002963924085743e-02,
                             3.464002963924085743e-02,
                             3.446025647539283782e-02,
                             3.446025647539283782e-02,
                             3.446025647539283782e-02,
                             3.494323310030658658e-02,
                             3.494323310030658658e-02,
                             3.494323310030658658e-02,
                             3.413889080384188701e-02,
                             3.413889080384188701e-02,
                             3.413889080384188701e-02,
                             3.495917470829300322e-02,
                             3.495917470829300322e-02,
                             3.495917470829300322e-02,
                             3.416668444551070744e-02,
                             3.416668444551070744e-02,
                             3.416668444551070744e-02,
                             3.468591118316260297e-02,
                             3.468591118316260297e-02,
                             3.468591118316260297e-02,
                             3.443776863194184662e-02,
                             3.443776863194184662e-02,
                             3.443776863194184662e-02,
                             3.431424211129673052e-02,
                             3.431424211129673052e-02,
                             3.431424211129673052e-02,
                             3.455988060207296209e-02,
                             3.455988060207296209e-02,
                             3.455988060207296209e-02,
                             3.433511480612023298e-02,
                             3.433511480612023298e-02,
                             3.433511480612023298e-02,
                             3.425761119854710962e-02,
                             3.425761119854710962e-02,
                             3.425761119854710962e-02,
                             3.472678385861750761e-02,
                             3.472678385861750761e-02,
                             3.472678385861750761e-02,
                             3.388053160900311722e-02,
                             3.388053160900311722e-02,
                             3.388053160900311722e-02,
                             3.497223687177687668e-02,
                             3.497223687177687668e-02,
                             3.497223687177687668e-02,
                             3.396864949541721773e-02,
                             3.396864949541721773e-02,
                             3.396864949541721773e-02,
                             3.469844278766760770e-02,
                             3.469844278766760770e-02,
                             3.469844278766760770e-02,
                             3.452670784877116122e-02,
                             3.452670784877116122e-02,
                             3.452670784877116122e-02,
                             3.422903138820843766e-02,
                             3.422903138820843766e-02,
                             3.422903138820843766e-02,
                             3.505664855164936089e-02,
                             3.505664855164936089e-02,
                             3.505664855164936089e-02,
                             3.413682892847823974e-02,
                             3.413682892847823974e-02,
                             3.413682892847823974e-02,
                             3.501385140272599700e-02,
                             3.501385140272599700e-02,
                             3.501385140272599700e-02,
                             3.467226010953376736e-02,
                             3.467226010953376736e-02,
                             3.467226010953376736e-02,
                             3.446833192932739071e-02,
                             3.446833192932739071e-02,
                             3.446833192932739071e-02,
                             3.537578680325848685e-02,
                             3.537578680325848685e-02,
                             3.537578680325848685e-02,
                             3.424582265861417230e-02,
                             3.424582265861417230e-02,
                             3.424582265861417230e-02,
                             3.542063347291982134e-02,
                             3.542063347291982134e-02,
                             3.542063347291982134e-02,
                             3.473157847887777677e-02,
                             3.473157847887777677e-02,
                             3.473157847887777677e-02,
                             3.500395496816594010e-02,
                             3.500395496816594010e-02,
                             3.500395496816594010e-02,
                             3.527956468212912339e-02,
                             3.527956468212912339e-02,
                             3.527956468212912339e-02,
                             3.474612912967797729e-02,
                             3.474612912967797729e-02,
                             3.474612912967797729e-02,
                             3.553270958271387281e-02,
                             3.553270958271387281e-02,
                             3.553270958271387281e-02,
                             3.484753394974442198e-02,
                             3.484753394974442198e-02,
                             3.484753394974442198e-02,
                             3.551019189257811903e-02,
                             3.551019189257811903e-02,
                             3.551019189257811903e-02,
                             3.507201831631155675e-02,
                             3.507201831631155675e-02,
                             3.507201831631155675e-02,
                             3.547010763766055702e-02,
                             3.547010763766055702e-02,
                             3.547010763766055702e-02,
                             3.517521602408801851e-02,
                             3.517521602408801851e-02,
                             3.517521602408801851e-02,
                             3.560587944514344294e-02,
                             3.560587944514344294e-02,
                             3.560587944514344294e-02,
                             3.515305893273550086e-02,
                             3.515305893273550086e-02,
                             3.515305893273550086e-02,
                             3.553033966094291257e-02,
                             3.553033966094291257e-02,
                             3.553033966094291257e-02,
                             3.542770249150801326e-02,
                             3.542770249150801326e-02,
                             3.542770249150801326e-02,
                             3.535849182230862281e-02,
                             3.535849182230862281e-02,
                             3.535849182230862281e-02,
                             3.553514224021542961e-02,
                             3.553514224021542961e-02,
                             3.553514224021542961e-02,
                             3.546214622480455686e-02,
                             3.546214622480455686e-02,
                             3.546214622480455686e-02,
                             3.534243011214804886e-02,
                             3.534243011214804886e-02,
                             3.534243011214804886e-02,
                             3.579446872783990236e-02,
                             3.579446872783990236e-02,
                             3.579446872783990236e-02,
                             3.519519788962451740e-02,
                             3.519519788962451740e-02,
                             3.519519788962451740e-02,
                             3.591039930922464846e-02,
                             3.591039930922464846e-02,
                             3.591039930922464846e-02,
                             3.541775767428190919e-02,
                             3.541775767428190919e-02,
                             3.541775767428190919e-02,
                             3.528980277571380081e-02,
                             3.528980277571380081e-02,
                             3.528980277571380081e-02,
                             3.614923854239279061e-02,
                             3.614923854239279061e-02,
                             3.614923854239279061e-02,
                             3.482687957692427033e-02,
                             3.482687957692427033e-02,
                             3.482687957692427033e-02,
                             3.616452572173328717e-02,
                             3.616452572173328717e-02,
                             3.616452572173328717e-02,
                             3.537259416044979954e-02,
                             3.537259416044979954e-02,
                             3.537259416044979954e-02,
                             3.533826691588583258e-02,
                             3.533826691588583258e-02,
                             3.533826691588583258e-02,
                             3.627226201745910317e-02,
                             3.627226201745910317e-02,
                             3.627226201745910317e-02,
                             3.423502106182098326e-02,
                             3.423502106182098326e-02,
                             3.423502106182098326e-02,
                             3.634959376129698327e-02,
                             3.634959376129698327e-02,
                             3.634959376129698327e-02,
                             3.481847085182868118e-02,
                             3.481847085182868118e-02,
                             3.481847085182868118e-02,
                             3.542398985871488687e-02,
                             3.542398985871488687e-02,
                             3.542398985871488687e-02,
                             3.593774678925047011e-02,
                             3.593774678925047011e-02,
                             3.593774678925047011e-02,
                             3.476658486982214802e-02,
                             3.476658486982214802e-02,
                             3.476658486982214802e-02,
                             3.582990314086371975e-02,
                             3.582990314086371975e-02,
                             3.582990314086371975e-02,
                             3.545358423877494058e-02,
                             3.545358423877494058e-02,
                             3.545358423877494058e-02,
                             3.498993803680634090e-02,
                             3.498993803680634090e-02,
                             3.498993803680634090e-02,
                             3.597205036018003010e-02,
                             3.597205036018003010e-02,
                             3.597205036018003010e-02,
                             3.446155855797314316e-02,
                             3.446155855797314316e-02,
                             3.446155855797314316e-02,
                             3.581126231987367264e-02,
                             3.581126231987367264e-02,
                             3.581126231987367264e-02,
                             3.478015905080063253e-02,
                             3.478015905080063253e-02,
                             3.478015905080063253e-02,
                             3.443810893728960904e-02,
                             3.443810893728960904e-02,
                             3.443810893728960904e-02,
                             3.569590158872352342e-02,
                             3.569590158872352342e-02,
                             3.569590158872352342e-02,
                             3.432753190054284309e-02,
                             3.432753190054284309e-02,
                             3.432753190054284309e-02,
                             3.544836843313777658e-02,
                             3.544836843313777658e-02,
                             3.544836843313777658e-02,
                             3.543386307485828918e-02,
                             3.543386307485828918e-02,
                             3.543386307485828918e-02,
                             3.475414975257572203e-02,
                             3.475414975257572203e-02,
                             3.475414975257572203e-02,
                             3.623532577187223852e-02,
                             3.623532577187223852e-02,
                             3.623532577187223852e-02,
                             3.498589418669603018e-02,
                             3.498589418669603018e-02,
                             3.498589418669603018e-02,
                             3.601035760359522220e-02,
                             3.601035760359522220e-02,
                             3.601035760359522220e-02,
                             3.571598482439355265e-02,
                             3.571598482439355265e-02,
                             3.571598482439355265e-02,
                             3.534934671238836035e-02,
                             3.534934671238836035e-02,
                             3.534934671238836035e-02,
                             3.653479201847238678e-02,
                             3.653479201847238678e-02,
                             3.653479201847238678e-02,
                             3.514669636147733228e-02,
                             3.514669636147733228e-02,
                             3.514669636147733228e-02,
                             3.647867000742373300e-02,
                             3.647867000742373300e-02,
                             3.647867000742373300e-02,
                             3.598325202148640323e-02,
                             3.598325202148640323e-02,
                             3.598325202148640323e-02,
                             3.558951505402629251e-02,
                             3.558951505402629251e-02,
                             3.558951505402629251e-02,
                             3.682573897489994225e-02,
                             3.682573897489994225e-02,
                             3.682573897489994225e-02,
                             3.534076002299529201e-02,
                             3.534076002299529201e-02,
                             3.534076002299529201e-02,
                             3.636272692795870093e-02,
                             3.636272692795870093e-02,
                             3.636272692795870093e-02,
                             3.655068671208203807e-02,
                             3.655068671208203807e-02,
                             3.655068671208203807e-02,
                             3.493682960177779684e-02,
                             3.493682960177779684e-02,
                             3.493682960177779684e-02,
                             3.779155472817560812e-02,
                             3.779155472817560812e-02,
                             3.779155472817560812e-02,
                             3.483490749431893824e-02,
                             3.483490749431893824e-02,
                             3.483490749431893824e-02,
                             3.678881243506237908e-02,
                             3.678881243506237908e-02,
                             3.678881243506237908e-02,
                             3.686808328654698347e-02,
                             3.686808328654698347e-02,
                             3.686808328654698347e-02,
                             3.468309812080880294e-02,
                             3.468309812080880294e-02,
                             3.468309812080880294e-02,
                             3.824179402913956138e-02,
                             3.824179402913956138e-02,
                             3.824179402913956138e-02,
                             3.470961121452373344e-02,
                             3.470961121452373344e-02,
                             3.470961121452373344e-02,
                             3.650575961292887306e-02,
                             3.650575961292887306e-02,
                             3.650575961292887306e-02,
                             3.749696733203376764e-02,
                             3.749696733203376764e-02,
                             3.749696733203376764e-02,
                             3.338198185796528022e-02,
                             3.338198185796528022e-02,
                             3.338198185796528022e-02,
                             3.937055618169763710e-02,
                             3.937055618169763710e-02,
                             3.937055618169763710e-02,
                             3.310853107320777672e-02,
                             3.310853107320777672e-02,
                             3.310853107320777672e-02,
                             3.700959517482681205e-02,
                             3.700959517482681205e-02,
                             3.700959517482681205e-02,
                             3.704612693606450929e-02,
                             3.704612693606450929e-02,
                             3.704612693606450929e-02,
                             3.203443339179724153e-02,
                             3.203443339179724153e-02,
                             3.203443339179724153e-02,
                             4.071226135228286219e-02,
                             4.071226135228286219e-02,
                             4.071226135228286219e-02,
                             3.104691103039200137e-02,
                             3.104691103039200137e-02,
                             3.104691103039200137e-02,
                             3.739743903050309765e-02,
                             3.739743903050309765e-02,
                             3.739743903050309765e-02,
                             3.793245311181699803e-02,
                             3.793245311181699803e-02,
                             3.793245311181699803e-02,
                             2.866205938771973147e-02,
                             2.866205938771973147e-02,
                             2.866205938771973147e-02,
                             4.474093222324695973e-02,
                             4.474093222324695973e-02,
                             4.474093222324695973e-02,
                             2.873628504976361020e-02,
                             2.873628504976361020e-02,
                             2.873628504976361020e-02,
                             3.015069375755836945e-02,
                             3.015069375755836945e-02,
                             3.015069375755836945e-02,
                             6.145563946363479663e-02,
                             6.145563946363479663e-02,
                             6.145563946363479663e-02,
                             ])

            if length_smpl < np.size(data):
                N = length_smpl
            else:
                N = np.size(data)

            res = np.zeros(length_smpl)
            res[0:N] = data[0:N]
            samples[start:start + length_smpl] = np.int16(np.round(res * amps * 2047, 1))


    def gauss_10ns(self, samples, start, amps, inv_fwhm, length_smpl):
            """

            """

            data = np.array([
                -1.187220848286748903e-03,
                -1.187220848286748903e-03,
                -1.187220848286748903e-03,
                -1.187220848286748903e-03,
                -1.187220848286748903e-03,
                4.828135447051377254e-04,
                4.828135447051377254e-04,
                4.828135447051377254e-04,
                4.828135447051377254e-04,
                4.828135447051377254e-04,
                -1.570595079336148045e-03,
                -1.570595079336148045e-03,
                -1.570595079336148045e-03,
                -1.570595079336148045e-03,
                -1.570595079336148045e-03,
                1.519657203184074867e-04,
                1.519657203184074867e-04,
                1.519657203184074867e-04,
                1.519657203184074867e-04,
                1.519657203184074867e-04,
                -7.996707125387561262e-04,
                -7.996707125387561262e-04,
                -7.996707125387561262e-04,
                -7.996707125387561262e-04,
                -7.996707125387561262e-04,
                -9.518278420321667904e-04,
                -9.518278420321667904e-04,
                -9.518278420321667904e-04,
                -9.518278420321667904e-04,
                -9.518278420321667904e-04,
                8.271197265701058583e-05,
                8.271197265701058583e-05,
                8.271197265701058583e-05,
                8.271197265701058583e-05,
                8.271197265701058583e-05,
                -1.246645942314140998e-03,
                -1.246645942314140998e-03,
                -1.246645942314140998e-03,
                -1.246645942314140998e-03,
                -1.246645942314140998e-03,
                -4.261105672183859738e-04,
                -4.261105672183859738e-04,
                -4.261105672183859738e-04,
                -4.261105672183859738e-04,
                -4.261105672183859738e-04,
                -4.129308105529412186e-04,
                -4.129308105529412186e-04,
                -4.129308105529412186e-04,
                -4.129308105529412186e-04,
                -4.129308105529412186e-04,
                -1.290559586043219095e-03,
                -1.290559586043219095e-03,
                -1.290559586043219095e-03,
                -1.290559586043219095e-03,
                -1.290559586043219095e-03,
                1.907771497834773893e-04,
                1.907771497834773893e-04,
                1.907771497834773893e-04,
                1.907771497834773893e-04,
                1.907771497834773893e-04,
                -1.259821077601645106e-03,
                -1.259821077601645106e-03,
                -1.259821077601645106e-03,
                -1.259821077601645106e-03,
                -1.259821077601645106e-03,
                -4.385490732717420184e-04,
                -4.385490732717420184e-04,
                -4.385490732717420184e-04,
                -4.385490732717420184e-04,
                -4.385490732717420184e-04,
                -1.574702953326387106e-04,
                -1.574702953326387106e-04,
                -1.574702953326387106e-04,
                -1.574702953326387106e-04,
                -1.574702953326387106e-04,
                -1.463174472267477974e-03,
                -1.463174472267477974e-03,
                -1.463174472267477974e-03,
                -1.463174472267477974e-03,
                -1.463174472267477974e-03,
                5.311776108453019393e-04,
                5.311776108453019393e-04,
                5.311776108453019393e-04,
                5.311776108453019393e-04,
                5.311776108453019393e-04,
                -1.225533197685965041e-03,
                -1.225533197685965041e-03,
                -1.225533197685965041e-03,
                -1.225533197685965041e-03,
                -1.225533197685965041e-03,
                -1.987414331442351060e-04,
                -1.987414331442351060e-04,
                -1.987414331442351060e-04,
                -1.987414331442351060e-04,
                -1.987414331442351060e-04,
                2.082109532119588962e-04,
                2.082109532119588962e-04,
                2.082109532119588962e-04,
                2.082109532119588962e-04,
                2.082109532119588962e-04,
                -1.250137331188973938e-03,
                -1.250137331188973938e-03,
                -1.250137331188973938e-03,
                -1.250137331188973938e-03,
                -1.250137331188973938e-03,
                1.360595952372435939e-03,
                1.360595952372435939e-03,
                1.360595952372435939e-03,
                1.360595952372435939e-03,
                1.360595952372435939e-03,
                -1.274010038876359063e-03,
                -1.274010038876359063e-03,
                -1.274010038876359063e-03,
                -1.274010038876359063e-03,
                -1.274010038876359063e-03,
                1.446533564216293108e-03,
                1.446533564216293108e-03,
                1.446533564216293108e-03,
                1.446533564216293108e-03,
                1.446533564216293108e-03,
                4.583614608476091088e-04,
                4.583614608476091088e-04,
                4.583614608476091088e-04,
                4.583614608476091088e-04,
                4.583614608476091088e-04,
                5.094054884033548608e-04,
                5.094054884033548608e-04,
                5.094054884033548608e-04,
                5.094054884033548608e-04,
                5.094054884033548608e-04,
                2.901866204589466803e-03,
                2.901866204589466803e-03,
                2.901866204589466803e-03,
                2.901866204589466803e-03,
                2.901866204589466803e-03,
                7.382345974521427106e-04,
                7.382345974521427106e-04,
                7.382345974521427106e-04,
                7.382345974521427106e-04,
                7.382345974521427106e-04,
                3.945260940998564572e-03,
                3.945260940998564572e-03,
                3.945260940998564572e-03,
                3.945260940998564572e-03,
                3.945260940998564572e-03,
                3.412756494777474930e-03,
                3.412756494777474930e-03,
                3.412756494777474930e-03,
                3.412756494777474930e-03,
                3.412756494777474930e-03,
                4.346007262495008190e-03,
                4.346007262495008190e-03,
                4.346007262495008190e-03,
                4.346007262495008190e-03,
                4.346007262495008190e-03,
                7.047734685909570404e-03,
                7.047734685909570404e-03,
                7.047734685909570404e-03,
                7.047734685909570404e-03,
                7.047734685909570404e-03,
                6.230908136158719995e-03,
                6.230908136158719995e-03,
                6.230908136158719995e-03,
                6.230908136158719995e-03,
                6.230908136158719995e-03,
                1.021797949625768975e-02,
                1.021797949625768975e-02,
                1.021797949625768975e-02,
                1.021797949625768975e-02,
                1.021797949625768975e-02,
                1.118950399710470084e-02,
                1.118950399710470084e-02,
                1.118950399710470084e-02,
                1.118950399710470084e-02,
                1.118950399710470084e-02,
                1.299190805636980979e-02,
                1.299190805636980979e-02,
                1.299190805636980979e-02,
                1.299190805636980979e-02,
                1.299190805636980979e-02,
                1.822691797730729979e-02,
                1.822691797730729979e-02,
                1.822691797730729979e-02,
                1.822691797730729979e-02,
                1.822691797730729979e-02,
                1.817228406686633921e-02,
                1.817228406686633921e-02,
                1.817228406686633921e-02,
                1.817228406686633921e-02,
                1.817228406686633921e-02,
                2.514525868648966045e-02,
                2.514525868648966045e-02,
                2.514525868648966045e-02,
                2.514525868648966045e-02,
                2.514525868648966045e-02,
                2.760635075989784082e-02,
                2.760635075989784082e-02,
                2.760635075989784082e-02,
                2.760635075989784082e-02,
                2.760635075989784082e-02,
                3.259564341020691758e-02,
                3.259564341020691758e-02,
                3.259564341020691758e-02,
                3.259564341020691758e-02,
                3.259564341020691758e-02,
                4.017215480895029722e-02,
                4.017215480895029722e-02,
                4.017215480895029722e-02,
                4.017215480895029722e-02,
                4.017215480895029722e-02,
                4.338188958010710111e-02,
                4.338188958010710111e-02,
                4.338188958010710111e-02,
                4.338188958010710111e-02,
                4.338188958010710111e-02,
                5.384186549397473875e-02,
                5.384186549397473875e-02,
                5.384186549397473875e-02,
                5.384186549397473875e-02,
                5.384186549397473875e-02,
                5.961783450662856698e-02,
                5.961783450662856698e-02,
                5.961783450662856698e-02,
                5.961783450662856698e-02,
                5.961783450662856698e-02,
                6.846428946111142444e-02,
                6.846428946111142444e-02,
                6.846428946111142444e-02,
                6.846428946111142444e-02,
                6.846428946111142444e-02,
                8.019557584145742268e-02,
                8.019557584145742268e-02,
                8.019557584145742268e-02,
                8.019557584145742268e-02,
                8.019557584145742268e-02,
                8.787307152041184954e-02,
                8.787307152041184954e-02,
                8.787307152041184954e-02,
                8.787307152041184954e-02,
                8.787307152041184954e-02,
                1.017448495488176008e-01,
                1.017448495488176008e-01,
                1.017448495488176008e-01,
                1.017448495488176008e-01,
                1.017448495488176008e-01,
                1.141825073807222063e-01,
                1.141825073807222063e-01,
                1.141825073807222063e-01,
                1.141825073807222063e-01,
                1.141825073807222063e-01,
                1.255812450710468986e-01,
                1.255812450710468986e-01,
                1.255812450710468986e-01,
                1.255812450710468986e-01,
                1.255812450710468986e-01,
                1.443882225159034138e-01,
                1.443882225159034138e-01,
                1.443882225159034138e-01,
                1.443882225159034138e-01,
                1.443882225159034138e-01,
                1.553800342169497084e-01,
                1.553800342169497084e-01,
                1.553800342169497084e-01,
                1.553800342169497084e-01,
                1.553800342169497084e-01,
                1.757115377453982996e-01,
                1.757115377453982996e-01,
                1.757115377453982996e-01,
                1.757115377453982996e-01,
                1.757115377453982996e-01,
                1.927019153728624923e-01,
                1.927019153728624923e-01,
                1.927019153728624923e-01,
                1.927019153728624923e-01,
                1.927019153728624923e-01,
                2.085029170215569050e-01,
                2.085029170215569050e-01,
                2.085029170215569050e-01,
                2.085029170215569050e-01,
                2.085029170215569050e-01,
                2.344185898278406122e-01,
                2.344185898278406122e-01,
                2.344185898278406122e-01,
                2.344185898278406122e-01,
                2.344185898278406122e-01,
                2.477124174326580941e-01,
                2.477124174326580941e-01,
                2.477124174326580941e-01,
                2.477124174326580941e-01,
                2.477124174326580941e-01,
                2.746662469479906887e-01,
                2.746662469479906887e-01,
                2.746662469479906887e-01,
                2.746662469479906887e-01,
                2.746662469479906887e-01,
                2.969817866430157216e-01,
                2.969817866430157216e-01,
                2.969817866430157216e-01,
                2.969817866430157216e-01,
                2.969817866430157216e-01,
                3.129423554619520931e-01,
                3.129423554619520931e-01,
                3.129423554619520931e-01,
                3.129423554619520931e-01,
                3.129423554619520931e-01,
                3.512688393560967071e-01,
                3.512688393560967071e-01,
                3.512688393560967071e-01,
                3.512688393560967071e-01,
                3.512688393560967071e-01,
                3.580522222776337249e-01,
                3.580522222776337249e-01,
                3.580522222776337249e-01,
                3.580522222776337249e-01,
                3.580522222776337249e-01,
                3.985423436988084767e-01,
                3.985423436988084767e-01,
                3.985423436988084767e-01,
                3.985423436988084767e-01,
                3.985423436988084767e-01,
                4.194964721645640937e-01,
                4.194964721645640937e-01,
                4.194964721645640937e-01,
                4.194964721645640937e-01,
                4.194964721645640937e-01,
                4.356999745971851801e-01,
                4.356999745971851801e-01,
                4.356999745971851801e-01,
                4.356999745971851801e-01,
                4.356999745971851801e-01,
                4.881706471099622746e-01,
                4.881706471099622746e-01,
                4.881706471099622746e-01,
                4.881706471099622746e-01,
                4.881706471099622746e-01,
                4.816768477354880784e-01,
                4.816768477354880784e-01,
                4.816768477354880784e-01,
                4.816768477354880784e-01,
                4.816768477354880784e-01,
                5.379402480887450766e-01,
                5.379402480887450766e-01,
                5.379402480887450766e-01,
                5.379402480887450766e-01,
                5.379402480887450766e-01,
                5.584364280578268946e-01,
                5.584364280578268946e-01,
                5.584364280578268946e-01,
                5.584364280578268946e-01,
                5.584364280578268946e-01,
                5.640529312078182977e-01,
                5.640529312078182977e-01,
                5.640529312078182977e-01,
                5.640529312078182977e-01,
                5.640529312078182977e-01,
                6.315552090551188602e-01,
                6.315552090551188602e-01,
                6.315552090551188602e-01,
                6.315552090551188602e-01,
                6.315552090551188602e-01,
                6.453641462811486873e-01,
                6.453641462811486873e-01,
                6.453641462811486873e-01,
                6.453641462811486873e-01,
                6.453641462811486873e-01,
                6.391011757791680292e-01,
                6.391011757791680292e-01,
                6.391011757791680292e-01,
                6.391011757791680292e-01,
                6.391011757791680292e-01,
                6.023233902912025206e-01,
                6.023233902912025206e-01,
                6.023233902912025206e-01,
                6.023233902912025206e-01,
                6.023233902912025206e-01,
                5.597180191305234365e-01,
                5.597180191305234365e-01,
                5.597180191305234365e-01,
                5.597180191305234365e-01,
                5.597180191305234365e-01,
                5.440126473652496797e-01,
                5.440126473652496797e-01,
                5.440126473652496797e-01,
                5.440126473652496797e-01,
                5.440126473652496797e-01,
                4.950026803665584230e-01,
                4.950026803665584230e-01,
                4.950026803665584230e-01,
                4.950026803665584230e-01,
                4.950026803665584230e-01,
                4.862580243887986153e-01,
                4.862580243887986153e-01,
                4.862580243887986153e-01,
                4.862580243887986153e-01,
                4.862580243887986153e-01,
                4.428305912248687859e-01,
                4.428305912248687859e-01,
                4.428305912248687859e-01,
                4.428305912248687859e-01,
                4.428305912248687859e-01,
                4.215047452993929133e-01,
                4.215047452993929133e-01,
                4.215047452993929133e-01,
                4.215047452993929133e-01,
                4.215047452993929133e-01,
                4.002942939197273176e-01,
                4.002942939197273176e-01,
                4.002942939197273176e-01,
                4.002942939197273176e-01,
                4.002942939197273176e-01,
                3.611125172774521941e-01,
                3.611125172774521941e-01,
                3.611125172774521941e-01,
                3.611125172774521941e-01,
                3.611125172774521941e-01,
                3.493872895111962973e-01,
                3.493872895111962973e-01,
                3.493872895111962973e-01,
                3.493872895111962973e-01,
                3.493872895111962973e-01,
                3.149098531184307825e-01,
                3.149098531184307825e-01,
                3.149098531184307825e-01,
                3.149098531184307825e-01,
                3.149098531184307825e-01,
                2.951555525686909154e-01,
                2.951555525686909154e-01,
                2.951555525686909154e-01,
                2.951555525686909154e-01,
                2.951555525686909154e-01,
                2.739984648972335068e-01,
                2.739984648972335068e-01,
                2.739984648972335068e-01,
                2.739984648972335068e-01,
                2.739984648972335068e-01,
                2.439223667736971080e-01,
                2.439223667736971080e-01,
                2.439223667736971080e-01,
                2.439223667736971080e-01,
                2.439223667736971080e-01,
                2.324692382551374059e-01,
                2.324692382551374059e-01,
                2.324692382551374059e-01,
                2.324692382551374059e-01,
                2.324692382551374059e-01,
                2.056406661927797919e-01,
                2.056406661927797919e-01,
                2.056406661927797919e-01,
                2.056406661927797919e-01,
                2.056406661927797919e-01,
                1.896886128834519014e-01,
                1.896886128834519014e-01,
                1.896886128834519014e-01,
                1.896886128834519014e-01,
                1.896886128834519014e-01,
                1.731737055234980061e-01,
                1.731737055234980061e-01,
                1.731737055234980061e-01,
                1.731737055234980061e-01,
                1.731737055234980061e-01,
                1.500423102395861963e-01,
                1.500423102395861963e-01,
                1.500423102395861963e-01,
                1.500423102395861963e-01,
                1.500423102395861963e-01,
                1.402191513851384908e-01,
                1.402191513851384908e-01,
                1.402191513851384908e-01,
                1.402191513851384908e-01,
                1.402191513851384908e-01,
                1.197264472216335029e-01,
                1.197264472216335029e-01,
                1.197264472216335029e-01,
                1.197264472216335029e-01,
                1.197264472216335029e-01,
                1.086072155370430004e-01,
                1.086072155370430004e-01,
                1.086072155370430004e-01,
                1.086072155370430004e-01,
                1.086072155370430004e-01,
                9.681228243750822360e-02,
                9.681228243750822360e-02,
                9.681228243750822360e-02,
                9.681228243750822360e-02,
                9.681228243750822360e-02,
                8.207941586825048819e-02,
                8.207941586825048819e-02,
                8.207941586825048819e-02,
                8.207941586825048819e-02,
                8.207941586825048819e-02,
                7.780038281276331624e-02,
                7.780038281276331624e-02,
                7.780038281276331624e-02,
                7.780038281276331624e-02,
                7.780038281276331624e-02,
                6.378097670020084486e-02,
                6.378097670020084486e-02,
                6.378097670020084486e-02,
                6.378097670020084486e-02,
                6.378097670020084486e-02,
                5.801990249706087677e-02,
                5.801990249706087677e-02,
                5.801990249706087677e-02,
                5.801990249706087677e-02,
                5.801990249706087677e-02,
                5.036146009131819284e-02,
                5.036146009131819284e-02,
                5.036146009131819284e-02,
                5.036146009131819284e-02,
                5.036146009131819284e-02,
                4.129528507352542288e-02,
                4.129528507352542288e-02,
                4.129528507352542288e-02,
                4.129528507352542288e-02,
                4.129528507352542288e-02,
                3.838394139068931898e-02,
                3.838394139068931898e-02,
                3.838394139068931898e-02,
                3.838394139068931898e-02,
                3.838394139068931898e-02,
                3.082260331017086866e-02,
                3.082260331017086866e-02,
                3.082260331017086866e-02,
                3.082260331017086866e-02,
                3.082260331017086866e-02,
                2.857700327197328083e-02,
                2.857700327197328083e-02,
                2.857700327197328083e-02,
                2.857700327197328083e-02,
                2.857700327197328083e-02,
                2.506342584715330959e-02,
                2.506342584715330959e-02,
                2.506342584715330959e-02,
                2.506342584715330959e-02,
                2.506342584715330959e-02,
                2.069062621844418998e-02,
                2.069062621844418998e-02,
                2.069062621844418998e-02,
                2.069062621844418998e-02,
                2.069062621844418998e-02,
                2.064342447800128835e-02,
                2.064342447800128835e-02,
                2.064342447800128835e-02,
                2.064342447800128835e-02,
                2.064342447800128835e-02,
                1.670394892664421940e-02,
                1.670394892664421940e-02,
                1.670394892664421940e-02,
                1.670394892664421940e-02,
                1.670394892664421940e-02,
                1.602463360425435135e-02,
                1.602463360425435135e-02,
                1.602463360425435135e-02,
                1.602463360425435135e-02,
                1.602463360425435135e-02,
                1.510209781224913957e-02,
                1.510209781224913957e-02,
                1.510209781224913957e-02,
                1.510209781224913957e-02,
                1.510209781224913957e-02,
                1.300532349529760941e-02,
                1.300532349529760941e-02,
                1.300532349529760941e-02,
                1.300532349529760941e-02,
                1.300532349529760941e-02,
                1.420888436881342053e-02,
                1.420888436881342053e-02,
                1.420888436881342053e-02,
                1.420888436881342053e-02,
                1.420888436881342053e-02,
                1.294619059022092920e-02,
                1.294619059022092920e-02,
                1.294619059022092920e-02,
                1.294619059022092920e-02,
                1.294619059022092920e-02,
                1.279391643505694079e-02,
                1.279391643505694079e-02,
                1.279391643505694079e-02,
                1.279391643505694079e-02,
                1.279391643505694079e-02,
                1.411984321320432917e-02,
                1.411984321320432917e-02,
                1.411984321320432917e-02,
                1.411984321320432917e-02,
                1.411984321320432917e-02,
                1.232111360958776033e-02,
                1.232111360958776033e-02,
                1.232111360958776033e-02,
                1.232111360958776033e-02,
                1.232111360958776033e-02,
                1.457260511188234950e-02,
                1.457260511188234950e-02,
                1.457260511188234950e-02,
                1.457260511188234950e-02,
                1.457260511188234950e-02,
                1.372829583126379017e-02,
                1.372829583126379017e-02,
                1.372829583126379017e-02,
                1.372829583126379017e-02,
                1.372829583126379017e-02,
                1.440220018590171978e-02,
                1.440220018590171978e-02,
                1.440220018590171978e-02,
                1.440220018590171978e-02,
                1.440220018590171978e-02,
                1.556206076565903006e-02,
                1.556206076565903006e-02,
                1.556206076565903006e-02,
                1.556206076565903006e-02,
                1.556206076565903006e-02,
                1.475908919774308013e-02,
                1.475908919774308013e-02,
                1.475908919774308013e-02,
                1.475908919774308013e-02,
                1.475908919774308013e-02,
                1.654078746340604048e-02,
                1.654078746340604048e-02,
                1.654078746340604048e-02,
                1.654078746340604048e-02,
                1.654078746340604048e-02,
                1.687048163048245064e-02,
                1.687048163048245064e-02,
                1.687048163048245064e-02,
                1.687048163048245064e-02,
                1.687048163048245064e-02,
                1.689611825646551019e-02,
                1.689611825646551019e-02,
                1.689611825646551019e-02,
                1.689611825646551019e-02,
                1.689611825646551019e-02,
                1.902957529330989023e-02,
                1.902957529330989023e-02,
                1.902957529330989023e-02,
                1.902957529330989023e-02,
                1.902957529330989023e-02,
                1.780304626589155129e-02,
                1.780304626589155129e-02,
                1.780304626589155129e-02,
                1.780304626589155129e-02,
                1.780304626589155129e-02,
                1.973444646750804887e-02,
                1.973444646750804887e-02,
                1.973444646750804887e-02,
                1.973444646750804887e-02,
                1.973444646750804887e-02,
                1.984986298132284874e-02,
                1.984986298132284874e-02,
                1.984986298132284874e-02,
                1.984986298132284874e-02,
                1.984986298132284874e-02,
                1.987995960799330067e-02,
                1.987995960799330067e-02,
                1.987995960799330067e-02,
                1.987995960799330067e-02,
                1.987995960799330067e-02,
                2.176575588812998049e-02,
                2.176575588812998049e-02,
                2.176575588812998049e-02,
                2.176575588812998049e-02,
                2.176575588812998049e-02,
                2.081604356756117102e-02,
                2.081604356756117102e-02,
                2.081604356756117102e-02,
                2.081604356756117102e-02,
                2.081604356756117102e-02,
                2.247513561444445043e-02,
                2.247513561444445043e-02,
                2.247513561444445043e-02,
                2.247513561444445043e-02,
                2.247513561444445043e-02,
                2.249466752146312906e-02,
                2.249466752146312906e-02,
                2.249466752146312906e-02,
                2.249466752146312906e-02,
                2.249466752146312906e-02,
                2.279051364418394066e-02,
                2.279051364418394066e-02,
                2.279051364418394066e-02,
                2.279051364418394066e-02,
                2.279051364418394066e-02,
                2.378691722272342074e-02,
                2.378691722272342074e-02,
                2.378691722272342074e-02,
                2.378691722272342074e-02,
                2.378691722272342074e-02,
                2.378710596048949980e-02,
                2.378710596048949980e-02,
                2.378710596048949980e-02,
                2.378710596048949980e-02,
                2.378710596048949980e-02,
                2.423522126985043143e-02,
                2.423522126985043143e-02,
                2.423522126985043143e-02,
                2.423522126985043143e-02,
                2.423522126985043143e-02,
                2.540181689808894069e-02,
                2.540181689808894069e-02,
                2.540181689808894069e-02,
                2.540181689808894069e-02,
                2.540181689808894069e-02,
                2.438092484941017934e-02,
                2.438092484941017934e-02,
                2.438092484941017934e-02,
                2.438092484941017934e-02,
                2.438092484941017934e-02,
                2.627631596688860885e-02,
                2.627631596688860885e-02,
                2.627631596688860885e-02,
                2.627631596688860885e-02,
                2.627631596688860885e-02,
                2.533411765846286037e-02,
                2.533411765846286037e-02,
                2.533411765846286037e-02,
                2.533411765846286037e-02,
                2.533411765846286037e-02,
                2.629267506450125996e-02,
                2.629267506450125996e-02,
                2.629267506450125996e-02,
                2.629267506450125996e-02,
                2.629267506450125996e-02,
                2.666513939759461091e-02,
                2.666513939759461091e-02,
                2.666513939759461091e-02,
                2.666513939759461091e-02,
                2.666513939759461091e-02,
                2.621743046983100039e-02,
                2.621743046983100039e-02,
                2.621743046983100039e-02,
                2.621743046983100039e-02,
                2.621743046983100039e-02,
                2.757458908093041172e-02,
                2.757458908093041172e-02,
                2.757458908093041172e-02,
                2.757458908093041172e-02,
                2.757458908093041172e-02,
                2.666697262284525166e-02,
                2.666697262284525166e-02,
                2.666697262284525166e-02,
                2.666697262284525166e-02,
                2.666697262284525166e-02,
                2.775985067354432012e-02,
                2.775985067354432012e-02,
                2.775985067354432012e-02,
                2.775985067354432012e-02,
                2.775985067354432012e-02,
                2.751624069176208942e-02,
                2.751624069176208942e-02,
                2.751624069176208942e-02,
                2.751624069176208942e-02,
                2.751624069176208942e-02,
                2.765210578795190832e-02,
                2.765210578795190832e-02,
                2.765210578795190832e-02,
                2.765210578795190832e-02,
                2.765210578795190832e-02,
                2.817961337814501102e-02,
                2.817961337814501102e-02,
                2.817961337814501102e-02,
                2.817961337814501102e-02,
                2.817961337814501102e-02,
                2.783707274093526890e-02,
                2.783707274093526890e-02,
                2.783707274093526890e-02,
                2.783707274093526890e-02,
                2.783707274093526890e-02,
                2.854466396443029047e-02,
                2.854466396443029047e-02,
                2.854466396443029047e-02,
                2.854466396443029047e-02,
                2.854466396443029047e-02,
                2.835335166356281120e-02,
                2.835335166356281120e-02,
                2.835335166356281120e-02,
                2.835335166356281120e-02,
                2.835335166356281120e-02,
                2.871864317735836961e-02,
                2.871864317735836961e-02,
                2.871864317735836961e-02,
                2.871864317735836961e-02,
                2.871864317735836961e-02,
                2.875959153660369999e-02,
                2.875959153660369999e-02,
                2.875959153660369999e-02,
                2.875959153660369999e-02,
                2.875959153660369999e-02,
                2.898111623853315971e-02,
                2.898111623853315971e-02,
                2.898111623853315971e-02,
                2.898111623853315971e-02,
                2.898111623853315971e-02,
                2.904441614063745999e-02,
                2.904441614063745999e-02,
                2.904441614063745999e-02,
                2.904441614063745999e-02,
                2.904441614063745999e-02,
                2.916665009490122112e-02,
                2.916665009490122112e-02,
                2.916665009490122112e-02,
                2.916665009490122112e-02,
                2.916665009490122112e-02,
                2.935103370451004959e-02,
                2.935103370451004959e-02,
                2.935103370451004959e-02,
                2.935103370451004959e-02,
                2.935103370451004959e-02,
                2.930838925426439839e-02,
                2.930838925426439839e-02,
                2.930838925426439839e-02,
                2.930838925426439839e-02,
                2.930838925426439839e-02,
                2.949537924357919019e-02,
                2.949537924357919019e-02,
                2.949537924357919019e-02,
                2.949537924357919019e-02,
                2.949537924357919019e-02,
                2.959613792591936007e-02,
                2.959613792591936007e-02,
                2.959613792591936007e-02,
                2.959613792591936007e-02,
                2.959613792591936007e-02,
                2.939003552210203013e-02,
                2.939003552210203013e-02,
                2.939003552210203013e-02,
                2.939003552210203013e-02,
                2.939003552210203013e-02,
                3.015590653003137958e-02,
                3.015590653003137958e-02,
                3.015590653003137958e-02,
                3.015590653003137958e-02,
                3.015590653003137958e-02,
                2.929138340847442859e-02,
                2.929138340847442859e-02,
                2.929138340847442859e-02,
                2.929138340847442859e-02,
                2.929138340847442859e-02,
                3.034496042995757023e-02,
                3.034496042995757023e-02,
                3.034496042995757023e-02,
                3.034496042995757023e-02,
                3.034496042995757023e-02,
                2.965564382875747126e-02,
                2.965564382875747126e-02,
                2.965564382875747126e-02,
                2.965564382875747126e-02,
                2.965564382875747126e-02,
                3.014096372348451860e-02,
                3.014096372348451860e-02,
                3.014096372348451860e-02,
                3.014096372348451860e-02,
                3.014096372348451860e-02,
                3.034978031885796068e-02,
                3.034978031885796068e-02,
                3.034978031885796068e-02,
                3.034978031885796068e-02,
                3.034978031885796068e-02,
                2.989438662209617861e-02,
                2.989438662209617861e-02,
                2.989438662209617861e-02,
                2.989438662209617861e-02,
                2.989438662209617861e-02,
                3.064634063767212105e-02,
                3.064634063767212105e-02,
                3.064634063767212105e-02,
                3.064634063767212105e-02,
                3.064634063767212105e-02,
                2.997924955633573044e-02,
                2.997924955633573044e-02,
                2.997924955633573044e-02,
                2.997924955633573044e-02,
                2.997924955633573044e-02,
                3.048747153499246909e-02,
                3.048747153499246909e-02,
                3.048747153499246909e-02,
                3.048747153499246909e-02,
                3.048747153499246909e-02,
                3.038378000914684907e-02,
                3.038378000914684907e-02,
                3.038378000914684907e-02,
                3.038378000914684907e-02,
                3.038378000914684907e-02,
                3.010636967431244010e-02,
                3.010636967431244010e-02,
                3.010636967431244010e-02,
                3.010636967431244010e-02,
                3.010636967431244010e-02,
                3.064601900962012071e-02,
                3.064601900962012071e-02,
                3.064601900962012071e-02,
                3.064601900962012071e-02,
                3.064601900962012071e-02,
                2.998501425169492959e-02,
                2.998501425169492959e-02,
                2.998501425169492959e-02,
                2.998501425169492959e-02,
                2.998501425169492959e-02,
                3.059962688495743849e-02,
                3.059962688495743849e-02,
                3.059962688495743849e-02,
                3.059962688495743849e-02,
                3.059962688495743849e-02,
                3.026963998222486144e-02,
                3.026963998222486144e-02,
                3.026963998222486144e-02,
                3.026963998222486144e-02,
                3.026963998222486144e-02,
                3.036973812075320980e-02,
                3.036973812075320980e-02,
                3.036973812075320980e-02,
                3.036973812075320980e-02,
                3.036973812075320980e-02,
                3.068479903285581054e-02,
                3.068479903285581054e-02,
                3.068479903285581054e-02,
                3.068479903285581054e-02,
                3.068479903285581054e-02,
                3.024636908142493141e-02,
                3.024636908142493141e-02,
                3.024636908142493141e-02,
                3.024636908142493141e-02,
                3.024636908142493141e-02,
                3.090060878404349981e-02,
                3.090060878404349981e-02,
                3.090060878404349981e-02,
                3.090060878404349981e-02,
                3.090060878404349981e-02,
                3.052881078478044893e-02,
                3.052881078478044893e-02,
                3.052881078478044893e-02,
                3.052881078478044893e-02,
                3.052881078478044893e-02,
                3.095070291466764031e-02,
                3.095070291466764031e-02,
                3.095070291466764031e-02,
                3.095070291466764031e-02,
                3.095070291466764031e-02,
                3.079697718412723051e-02,
                3.079697718412723051e-02,
                3.079697718412723051e-02,
                3.079697718412723051e-02,
                3.079697718412723051e-02,
                3.077684887951112960e-02,
                3.077684887951112960e-02,
                3.077684887951112960e-02,
                3.077684887951112960e-02,
                3.077684887951112960e-02,
                3.103133264556676152e-02,
                3.103133264556676152e-02,
                3.103133264556676152e-02,
                3.103133264556676152e-02,
                3.103133264556676152e-02,
                3.076886320880957079e-02,
                3.076886320880957079e-02,
                3.076886320880957079e-02,
                3.076886320880957079e-02,
                3.076886320880957079e-02,
                3.121924107031207041e-02,
                3.121924107031207041e-02,
                3.121924107031207041e-02,
                3.121924107031207041e-02,
                3.121924107031207041e-02,
                3.101986427117443129e-02,
                3.101986427117443129e-02,
                3.101986427117443129e-02,
                3.101986427117443129e-02,
                3.101986427117443129e-02,
                3.110856470476481075e-02,
                3.110856470476481075e-02,
                3.110856470476481075e-02,
                3.110856470476481075e-02,
                3.110856470476481075e-02,
                3.128963663424316755e-02,
                3.128963663424316755e-02,
                3.128963663424316755e-02,
                3.128963663424316755e-02,
                3.128963663424316755e-02,
                3.102285124304648978e-02,
                3.102285124304648978e-02,
                3.102285124304648978e-02,
                3.102285124304648978e-02,
                3.102285124304648978e-02,
                3.131738756449253119e-02,
                3.131738756449253119e-02,
                3.131738756449253119e-02,
                3.131738756449253119e-02,
                3.131738756449253119e-02,
                3.120811089365338117e-02,
                3.120811089365338117e-02,
                3.120811089365338117e-02,
                3.120811089365338117e-02,
                3.120811089365338117e-02,
                3.122774308593926143e-02,
                3.122774308593926143e-02,
                3.122774308593926143e-02,
                3.122774308593926143e-02,
                3.122774308593926143e-02,
                3.162191684173581291e-02,
                3.162191684173581291e-02,
                3.162191684173581291e-02,
                3.162191684173581291e-02,
                3.162191684173581291e-02,
                3.105322822234963046e-02,
                3.105322822234963046e-02,
                3.105322822234963046e-02,
                3.105322822234963046e-02,
                3.105322822234963046e-02,
                3.159594002544566238e-02,
                3.159594002544566238e-02,
                3.159594002544566238e-02,
                3.159594002544566238e-02,
                3.159594002544566238e-02,
                3.117097711702129098e-02,
                3.117097711702129098e-02,
                3.117097711702129098e-02,
                3.117097711702129098e-02,
                3.117097711702129098e-02,
                3.176393599737457191e-02,
                3.176393599737457191e-02,
                3.176393599737457191e-02,
                3.176393599737457191e-02,
                3.176393599737457191e-02,
                3.179319834065973821e-02,
                3.179319834065973821e-02,
                3.179319834065973821e-02,
                3.179319834065973821e-02,
                3.179319834065973821e-02,
                3.166798888980572324e-02,
                3.166798888980572324e-02,
                3.166798888980572324e-02,
                3.166798888980572324e-02,
                3.166798888980572324e-02,
                3.207099338121262300e-02,
                3.207099338121262300e-02,
                3.207099338121262300e-02,
                3.207099338121262300e-02,
                3.207099338121262300e-02,
                3.164836229211676760e-02,
                3.164836229211676760e-02,
                3.164836229211676760e-02,
                3.164836229211676760e-02,
                3.164836229211676760e-02,
                3.225679218885994792e-02,
                3.225679218885994792e-02,
                3.225679218885994792e-02,
                3.225679218885994792e-02,
                3.225679218885994792e-02,
                3.210797021742067825e-02,
                3.210797021742067825e-02,
                3.210797021742067825e-02,
                3.210797021742067825e-02,
                3.210797021742067825e-02,
                3.217127254727236707e-02,
                3.217127254727236707e-02,
                3.217127254727236707e-02,
                3.217127254727236707e-02,
                3.217127254727236707e-02,
                3.259702078741497783e-02,
                3.259702078741497783e-02,
                3.259702078741497783e-02,
                3.259702078741497783e-02,
                3.259702078741497783e-02,
                3.223958037229752299e-02,
                3.223958037229752299e-02,
                3.223958037229752299e-02,
                3.223958037229752299e-02,
                3.223958037229752299e-02,
                3.305310118153576004e-02,
                3.305310118153576004e-02,
                3.305310118153576004e-02,
                3.305310118153576004e-02,
                3.305310118153576004e-02,
                3.255892015183633331e-02,
                3.255892015183633331e-02,
                3.255892015183633331e-02,
                3.255892015183633331e-02,
                3.255892015183633331e-02,
                3.334252982397867271e-02,
                3.334252982397867271e-02,
                3.334252982397867271e-02,
                3.334252982397867271e-02,
                3.334252982397867271e-02,
                3.313051595868696242e-02,
                3.313051595868696242e-02,
                3.313051595868696242e-02,
                3.313051595868696242e-02,
                3.313051595868696242e-02,
                3.337813289557887975e-02,
                3.337813289557887975e-02,
                3.337813289557887975e-02,
                3.337813289557887975e-02,
                3.337813289557887975e-02,
                3.362440847098369101e-02,
                3.362440847098369101e-02,
                3.362440847098369101e-02,
                3.362440847098369101e-02,
                3.362440847098369101e-02,
                3.346764339831276303e-02,
                3.346764339831276303e-02,
                3.346764339831276303e-02,
                3.346764339831276303e-02,
                3.346764339831276303e-02,
                3.387250416956724686e-02,
                3.387250416956724686e-02,
                3.387250416956724686e-02,
                3.387250416956724686e-02,
                3.387250416956724686e-02,
                3.389773171431331722e-02,
                3.389773171431331722e-02,
                3.389773171431331722e-02,
                3.389773171431331722e-02,
                3.389773171431331722e-02,
                3.370641053075199706e-02,
                3.370641053075199706e-02,
                3.370641053075199706e-02,
                3.370641053075199706e-02,
                3.370641053075199706e-02,
                3.415175863343367785e-02,
                3.415175863343367785e-02,
                3.415175863343367785e-02,
                3.415175863343367785e-02,
                3.415175863343367785e-02,
                3.345709670740267677e-02,
                3.345709670740267677e-02,
                3.345709670740267677e-02,
                3.345709670740267677e-02,
                3.345709670740267677e-02,
                3.406954154043583677e-02,
                3.406954154043583677e-02,
                3.406954154043583677e-02,
                3.406954154043583677e-02,
                3.406954154043583677e-02,
                3.354285975659641178e-02,
                3.354285975659641178e-02,
                3.354285975659641178e-02,
                3.354285975659641178e-02,
                3.354285975659641178e-02,
                3.387281262677212940e-02,
                3.387281262677212940e-02,
                3.387281262677212940e-02,
                3.387281262677212940e-02,
                3.387281262677212940e-02,
                3.370556607160000301e-02,
                3.370556607160000301e-02,
                3.370556607160000301e-02,
                3.370556607160000301e-02,
                3.370556607160000301e-02,
                3.374548768735406712e-02,
                3.374548768735406712e-02,
                3.374548768735406712e-02,
                3.374548768735406712e-02,
                3.374548768735406712e-02,
                3.373327922365550180e-02,
                3.373327922365550180e-02,
                3.373327922365550180e-02,
                3.373327922365550180e-02,
                3.373327922365550180e-02,
                3.388166392306644209e-02,
                3.388166392306644209e-02,
                3.388166392306644209e-02,
                3.388166392306644209e-02,
                3.388166392306644209e-02,
                3.360925929810677781e-02,
                3.360925929810677781e-02,
                3.360925929810677781e-02,
                3.360925929810677781e-02,
                3.360925929810677781e-02,
                3.402186918322486903e-02,
                3.402186918322486903e-02,
                3.402186918322486903e-02,
                3.402186918322486903e-02,
                3.402186918322486903e-02,
                3.360389169488726957e-02,
                3.360389169488726957e-02,
                3.360389169488726957e-02,
                3.360389169488726957e-02,
                3.360389169488726957e-02,
                3.395367524276306226e-02,
                3.395367524276306226e-02,
                3.395367524276306226e-02,
                3.395367524276306226e-02,
                3.395367524276306226e-02,
                3.371542668877341303e-02,
                3.371542668877341303e-02,
                3.371542668877341303e-02,
                3.371542668877341303e-02,
                3.371542668877341303e-02,
                3.378337262527319335e-02,
                3.378337262527319335e-02,
                3.378337262527319335e-02,
                3.378337262527319335e-02,
                3.378337262527319335e-02,
                3.391672670981354248e-02,
                3.391672670981354248e-02,
                3.391672670981354248e-02,
                3.391672670981354248e-02,
                3.391672670981354248e-02,
                3.362225928466498065e-02,
                3.362225928466498065e-02,
                3.362225928466498065e-02,
                3.362225928466498065e-02,
                3.362225928466498065e-02,
                3.405454823457088054e-02,
                3.405454823457088054e-02,
                3.405454823457088054e-02,
                3.405454823457088054e-02,
                3.405454823457088054e-02,
                3.349746330191918225e-02,
                3.349746330191918225e-02,
                3.349746330191918225e-02,
                3.349746330191918225e-02,
                3.349746330191918225e-02,
                3.416865868029257680e-02,
                3.416865868029257680e-02,
                3.416865868029257680e-02,
                3.416865868029257680e-02,
                3.416865868029257680e-02,
                3.357359307486561251e-02,
                3.357359307486561251e-02,
                3.357359307486561251e-02,
                3.357359307486561251e-02,
                3.357359307486561251e-02,
                3.400674382032217030e-02,
                3.400674382032217030e-02,
                3.400674382032217030e-02,
                3.400674382032217030e-02,
                3.400674382032217030e-02,
                3.393337939003084752e-02,
                3.393337939003084752e-02,
                3.393337939003084752e-02,
                3.393337939003084752e-02,
                3.393337939003084752e-02,
                3.362930310548836038e-02,
                3.362930310548836038e-02,
                3.362930310548836038e-02,
                3.362930310548836038e-02,
                3.362930310548836038e-02,
                3.435210076853194294e-02,
                3.435210076853194294e-02,
                3.435210076853194294e-02,
                3.435210076853194294e-02,
                3.435210076853194294e-02,
                3.335650984414698789e-02,
                3.335650984414698789e-02,
                3.335650984414698789e-02,
                3.335650984414698789e-02,
                3.335650984414698789e-02,
                3.458859882488390242e-02,
                3.458859882488390242e-02,
                3.458859882488390242e-02,
                3.458859882488390242e-02,
                3.458859882488390242e-02,
                3.359185765393377793e-02,
                3.359185765393377793e-02,
                3.359185765393377793e-02,
                3.359185765393377793e-02,
                3.359185765393377793e-02,
                3.424012274390059174e-02,
                3.424012274390059174e-02,
                3.424012274390059174e-02,
                3.424012274390059174e-02,
                3.424012274390059174e-02,
                3.426037745738733792e-02,
                3.426037745738733792e-02,
                3.426037745738733792e-02,
                3.426037745738733792e-02,
                3.426037745738733792e-02,
                3.361497957792255326e-02,
                3.361497957792255326e-02,
                3.361497957792255326e-02,
                3.361497957792255326e-02,
                3.361497957792255326e-02,
                3.488155238962121346e-02,
                3.488155238962121346e-02,
                3.488155238962121346e-02,
                3.488155238962121346e-02,
                3.488155238962121346e-02,
                3.334098218793631052e-02,
                3.334098218793631052e-02,
                3.334098218793631052e-02,
                3.334098218793631052e-02,
                3.334098218793631052e-02,
                3.483158399816697198e-02,
                3.483158399816697198e-02,
                3.483158399816697198e-02,
                3.483158399816697198e-02,
                3.483158399816697198e-02,
                3.365819136335151951e-02,
                3.365819136335151951e-02,
                3.365819136335151951e-02,
                3.365819136335151951e-02,
                3.365819136335151951e-02,
                3.415964794263619264e-02,
                3.415964794263619264e-02,
                3.415964794263619264e-02,
                3.415964794263619264e-02,
                3.415964794263619264e-02,
                3.432490248260360727e-02,
                3.432490248260360727e-02,
                3.432490248260360727e-02,
                3.432490248260360727e-02,
                3.432490248260360727e-02,
                3.344348202062989717e-02,
                3.344348202062989717e-02,
                3.344348202062989717e-02,
                3.344348202062989717e-02,
                3.344348202062989717e-02,
                3.448177324651668235e-02,
                3.448177324651668235e-02,
                3.448177324651668235e-02,
                3.448177324651668235e-02,
                3.448177324651668235e-02,
                3.337933661364699683e-02,
                3.337933661364699683e-02,
                3.337933661364699683e-02,
                3.337933661364699683e-02,
                3.337933661364699683e-02,
                3.409080534008875757e-02,
                3.409080534008875757e-02,
                3.409080534008875757e-02,
                3.409080534008875757e-02,
                3.409080534008875757e-02,
                3.378338439983871733e-02,
                3.378338439983871733e-02,
                3.378338439983871733e-02,
                3.378338439983871733e-02,
                3.378338439983871733e-02,
                3.353737700241885694e-02,
                3.353737700241885694e-02,
                3.353737700241885694e-02,
                3.353737700241885694e-02,
                3.353737700241885694e-02,
                3.407137935878445933e-02,
                3.407137935878445933e-02,
                3.407137935878445933e-02,
                3.407137935878445933e-02,
                3.407137935878445933e-02,
                3.343941041692204130e-02,
                3.343941041692204130e-02,
                3.343941041692204130e-02,
                3.343941041692204130e-02,
                3.343941041692204130e-02,
                3.386857289211592237e-02,
                3.386857289211592237e-02,
                3.386857289211592237e-02,
                3.386857289211592237e-02,
                3.386857289211592237e-02,
                3.363727068390962027e-02,
                3.363727068390962027e-02,
                3.363727068390962027e-02,
                3.363727068390962027e-02,
                3.363727068390962027e-02,
                3.342219996130362664e-02,
                3.342219996130362664e-02,
                3.342219996130362664e-02,
                3.342219996130362664e-02,
                3.342219996130362664e-02,
                3.383602408362369057e-02,
                3.383602408362369057e-02,
                3.383602408362369057e-02,
                3.383602408362369057e-02,
                3.383602408362369057e-02,
                3.321515390393525724e-02,
                3.321515390393525724e-02,
                3.321515390393525724e-02,
                3.321515390393525724e-02,
                3.321515390393525724e-02,
                3.361091889549563255e-02,
                3.361091889549563255e-02,
                3.361091889549563255e-02,
                3.361091889549563255e-02,
                3.361091889549563255e-02,
                3.338982249480387104e-02,
                3.338982249480387104e-02,
                3.338982249480387104e-02,
                3.338982249480387104e-02,
                3.338982249480387104e-02,
                3.322238611608092917e-02,
                3.322238611608092917e-02,
                3.322238611608092917e-02,
                3.322238611608092917e-02,
                3.322238611608092917e-02,
                3.362822816359686828e-02,
                3.362822816359686828e-02,
                3.362822816359686828e-02,
                3.362822816359686828e-02,
                3.362822816359686828e-02,
                3.290817389204112042e-02,
                3.290817389204112042e-02,
                3.290817389204112042e-02,
                3.290817389204112042e-02,
                3.290817389204112042e-02,
                3.374252408754663951e-02,
                3.374252408754663951e-02,
                3.374252408754663951e-02,
                3.374252408754663951e-02,
                3.374252408754663951e-02,
                3.284834574751514108e-02,
                3.284834574751514108e-02,
                3.284834574751514108e-02,
                3.284834574751514108e-02,
                3.284834574751514108e-02,
                3.357625694356342755e-02,
                3.357625694356342755e-02,
                3.357625694356342755e-02,
                3.357625694356342755e-02,
                3.357625694356342755e-02,
                3.298659986297679952e-02,
                3.298659986297679952e-02,
                3.298659986297679952e-02,
                3.298659986297679952e-02,
                3.298659986297679952e-02,
                3.330398465227425719e-02,
                3.330398465227425719e-02,
                3.330398465227425719e-02,
                3.330398465227425719e-02,
                3.330398465227425719e-02,
                3.312603749113499779e-02,
                3.312603749113499779e-02,
                3.312603749113499779e-02,
                3.312603749113499779e-02,
                3.312603749113499779e-02,
                3.307733825995046173e-02,
                3.307733825995046173e-02,
                3.307733825995046173e-02,
                3.307733825995046173e-02,
                3.307733825995046173e-02,
                3.313018978847630247e-02,
                3.313018978847630247e-02,
                3.313018978847630247e-02,
                3.313018978847630247e-02,
                3.313018978847630247e-02,
                3.304290943127367181e-02,
                3.304290943127367181e-02,
                3.304290943127367181e-02,
                3.304290943127367181e-02,
                3.304290943127367181e-02,
                3.316077051433231893e-02,
                3.316077051433231893e-02,
                3.316077051433231893e-02,
                3.316077051433231893e-02,
                3.316077051433231893e-02,
                3.310122304031423712e-02,
                3.310122304031423712e-02,
                3.310122304031423712e-02,
                3.310122304031423712e-02,
                3.310122304031423712e-02,
                3.326593979860049261e-02,
                3.326593979860049261e-02,
                3.326593979860049261e-02,
                3.326593979860049261e-02,
                3.326593979860049261e-02,
                3.320911946415341237e-02,
                3.320911946415341237e-02,
                3.320911946415341237e-02,
                3.320911946415341237e-02,
                3.320911946415341237e-02,
                3.337329302133725667e-02,
                3.337329302133725667e-02,
                3.337329302133725667e-02,
                3.337329302133725667e-02,
                3.337329302133725667e-02,
                3.324967224748259786e-02,
                3.324967224748259786e-02,
                3.324967224748259786e-02,
                3.324967224748259786e-02,
                3.324967224748259786e-02,
                3.364085318084925058e-02,
                3.364085318084925058e-02,
                3.364085318084925058e-02,
                3.364085318084925058e-02,
                3.364085318084925058e-02,
                3.322504006252641195e-02,
                3.322504006252641195e-02,
                3.322504006252641195e-02,
                3.322504006252641195e-02,
                3.322504006252641195e-02,
                3.393151887072261286e-02,
                3.393151887072261286e-02,
                3.393151887072261286e-02,
                3.393151887072261286e-02,
                3.393151887072261286e-02,
                3.328553693620565912e-02,
                3.328553693620565912e-02,
                3.328553693620565912e-02,
                3.328553693620565912e-02,
                3.328553693620565912e-02,
                3.414993461442830669e-02,
                3.414993461442830669e-02,
                3.414993461442830669e-02,
                3.414993461442830669e-02,
                3.414993461442830669e-02,
                3.357040565772779345e-02,
                3.357040565772779345e-02,
                3.357040565772779345e-02,
                3.357040565772779345e-02,
                3.357040565772779345e-02,
                3.410069188683598207e-02,
                3.410069188683598207e-02,
                3.410069188683598207e-02,
                3.410069188683598207e-02,
                3.410069188683598207e-02,
                3.413894662171004096e-02,
                3.413894662171004096e-02,
                3.413894662171004096e-02,
                3.413894662171004096e-02,
                3.413894662171004096e-02,
                3.386827712677274727e-02,
                3.386827712677274727e-02,
                3.386827712677274727e-02,
                3.386827712677274727e-02,
                3.386827712677274727e-02,
                3.466105795393684130e-02,
                3.466105795393684130e-02,
                3.466105795393684130e-02,
                3.466105795393684130e-02,
                3.466105795393684130e-02,
                3.384987702672125759e-02,
                3.384987702672125759e-02,
                3.384987702672125759e-02,
                3.384987702672125759e-02,
                3.384987702672125759e-02,
                3.467474780073154239e-02,
                3.467474780073154239e-02,
                3.467474780073154239e-02,
                3.467474780073154239e-02,
                3.467474780073154239e-02,
                3.423903264433186822e-02,
                3.423903264433186822e-02,
                3.423903264433186822e-02,
                3.423903264433186822e-02,
                3.423903264433186822e-02,
                3.443906062472722185e-02,
                3.443906062472722185e-02,
                3.443906062472722185e-02,
                3.443906062472722185e-02,
                3.443906062472722185e-02,
                3.471421493722900292e-02,
                3.471421493722900292e-02,
                3.471421493722900292e-02,
                3.471421493722900292e-02,
                3.471421493722900292e-02,
                3.410161954946701324e-02,
                3.410161954946701324e-02,
                3.410161954946701324e-02,
                3.410161954946701324e-02,
                3.410161954946701324e-02,
                3.501428280782459268e-02,
                3.501428280782459268e-02,
                3.501428280782459268e-02,
                3.501428280782459268e-02,
                3.501428280782459268e-02,
                3.402498751891359918e-02,
                3.402498751891359918e-02,
                3.402498751891359918e-02,
                3.402498751891359918e-02,
                3.402498751891359918e-02,
                3.501491077394207341e-02,
                3.501491077394207341e-02,
                3.501491077394207341e-02,
                3.501491077394207341e-02,
                3.501491077394207341e-02,
                3.424909033922703822e-02,
                3.424909033922703822e-02,
                3.424909033922703822e-02,
                3.424909033922703822e-02,
                3.424909033922703822e-02,
                3.477526381200626154e-02,
                3.477526381200626154e-02,
                3.477526381200626154e-02,
                3.477526381200626154e-02,
                3.477526381200626154e-02,
                3.460585282892870984e-02,
                3.460585282892870984e-02,
                3.460585282892870984e-02,
                3.460585282892870984e-02,
                3.460585282892870984e-02,
                3.451916134056977337e-02,
                3.451916134056977337e-02,
                3.451916134056977337e-02,
                3.451916134056977337e-02,
                3.451916134056977337e-02,
                3.478200286198208924e-02,
                3.478200286198208924e-02,
                3.478200286198208924e-02,
                3.478200286198208924e-02,
                3.478200286198208924e-02,
                3.440952814515681191e-02,
                3.440952814515681191e-02,
                3.440952814515681191e-02,
                3.440952814515681191e-02,
                3.440952814515681191e-02,
                3.474914313585542730e-02,
                3.474914313585542730e-02,
                3.474914313585542730e-02,
                3.474914313585542730e-02,
                3.474914313585542730e-02,
                3.448990802011982215e-02,
                3.448990802011982215e-02,
                3.448990802011982215e-02,
                3.448990802011982215e-02,
                3.448990802011982215e-02,
                3.454789387264701334e-02,
                3.454789387264701334e-02,
                3.454789387264701334e-02,
                3.454789387264701334e-02,
                3.454789387264701334e-02,
                3.454116525452236020e-02,
                3.454116525452236020e-02,
                3.454116525452236020e-02,
                3.454116525452236020e-02,
                3.454116525452236020e-02,
                3.438096358490078802e-02,
                3.438096358490078802e-02,
                3.438096358490078802e-02,
                3.438096358490078802e-02,
                3.438096358490078802e-02,
                3.454866506240562851e-02,
                3.454866506240562851e-02,
                3.454866506240562851e-02,
                3.454866506240562851e-02,
                3.454866506240562851e-02,
                3.419359627388726675e-02,
                3.419359627388726675e-02,
                3.419359627388726675e-02,
                3.419359627388726675e-02,
                3.419359627388726675e-02,
                3.438946642053603009e-02,
                3.438946642053603009e-02,
                3.438946642053603009e-02,
                3.438946642053603009e-02,
                3.438946642053603009e-02,
                3.418042208915814811e-02,
                3.418042208915814811e-02,
                3.418042208915814811e-02,
                3.418042208915814811e-02,
                3.418042208915814811e-02,
                3.422409498769010683e-02,
                3.422409498769010683e-02,
                3.422409498769010683e-02,
                3.422409498769010683e-02,
                3.422409498769010683e-02,
                3.416834154160663245e-02,
                3.416834154160663245e-02,
                3.416834154160663245e-02,
                3.416834154160663245e-02,
                3.416834154160663245e-02,
                3.436795229838243010e-02,
                3.436795229838243010e-02,
                3.436795229838243010e-02,
                3.436795229838243010e-02,
                3.436795229838243010e-02,
                3.388239054676345924e-02,
                3.388239054676345924e-02,
                3.388239054676345924e-02,
                3.388239054676345924e-02,
                3.388239054676345924e-02,
                3.462439403325658777e-02,
                3.462439403325658777e-02,
                3.462439403325658777e-02,
                3.462439403325658777e-02,
                3.462439403325658777e-02,
                3.347634344094965742e-02,
                3.347634344094965742e-02,
                3.347634344094965742e-02,
                3.347634344094965742e-02,
                3.347634344094965742e-02,
                3.469263663782565926e-02,
                3.469263663782565926e-02,
                3.469263663782565926e-02,
                3.469263663782565926e-02,
                3.469263663782565926e-02,
                3.354043524343398863e-02,
                3.354043524343398863e-02,
                3.354043524343398863e-02,
                3.354043524343398863e-02,
                3.354043524343398863e-02,
                3.420944351972984160e-02,
                3.420944351972984160e-02,
                3.420944351972984160e-02,
                3.420944351972984160e-02,
                3.420944351972984160e-02,
                3.398197244099875058e-02,
                3.398197244099875058e-02,
                3.398197244099875058e-02,
                3.398197244099875058e-02,
                3.398197244099875058e-02,
                3.359083872388073100e-02,
                3.359083872388073100e-02,
                3.359083872388073100e-02,
                3.359083872388073100e-02,
                3.359083872388073100e-02,
                3.437820688103754296e-02,
                3.437820688103754296e-02,
                3.437820688103754296e-02,
                3.437820688103754296e-02,
                3.437820688103754296e-02,
                3.344779248720017306e-02,
                3.344779248720017306e-02,
                3.344779248720017306e-02,
                3.344779248720017306e-02,
                3.344779248720017306e-02,
                3.425555697176468906e-02,
                3.425555697176468906e-02,
                3.425555697176468906e-02,
                3.425555697176468906e-02,
                3.425555697176468906e-02,
                3.380463843325388212e-02,
                3.380463843325388212e-02,
                3.380463843325388212e-02,
                3.380463843325388212e-02,
                3.380463843325388212e-02,
                3.361979414535057331e-02,
                3.361979414535057331e-02,
                3.361979414535057331e-02,
                3.361979414535057331e-02,
                3.361979414535057331e-02,
                3.449325674409355752e-02,
                3.449325674409355752e-02,
                3.449325674409355752e-02,
                3.449325674409355752e-02,
                3.449325674409355752e-02,
                3.309110273192549662e-02,
                3.309110273192549662e-02,
                3.309110273192549662e-02,
                3.309110273192549662e-02,
                3.309110273192549662e-02,
                3.477400131983227061e-02,
                3.477400131983227061e-02,
                3.477400131983227061e-02,
                3.477400131983227061e-02,
                3.477400131983227061e-02,
                3.316883401300160794e-02,
                3.316883401300160794e-02,
                3.316883401300160794e-02,
                3.316883401300160794e-02,
                3.316883401300160794e-02,
                3.454990561283709238e-02,
                3.454990561283709238e-02,
                3.454990561283709238e-02,
                3.454990561283709238e-02,
                3.454990561283709238e-02,
                3.371587799488544313e-02,
                3.371587799488544313e-02,
                3.371587799488544313e-02,
                3.371587799488544313e-02,
                3.371587799488544313e-02,
                3.412294044248113251e-02,
                3.412294044248113251e-02,
                3.412294044248113251e-02,
                3.412294044248113251e-02,
                3.412294044248113251e-02,
                3.426753524739024892e-02,
                3.426753524739024892e-02,
                3.426753524739024892e-02,
                3.426753524739024892e-02,
                3.426753524739024892e-02,
                3.388614321911240235e-02,
                3.388614321911240235e-02,
                3.388614321911240235e-02,
                3.388614321911240235e-02,
                3.388614321911240235e-02,
                3.443587781774957307e-02,
                3.443587781774957307e-02,
                3.443587781774957307e-02,
                3.443587781774957307e-02,
                3.443587781774957307e-02,
                3.411707675195387035e-02,
                3.411707675195387035e-02,
                3.411707675195387035e-02,
                3.411707675195387035e-02,
                3.411707675195387035e-02,
                3.432663305964053779e-02,
                3.432663305964053779e-02,
                3.432663305964053779e-02,
                3.432663305964053779e-02,
                3.432663305964053779e-02,
                3.447452412938972754e-02,
                3.447452412938972754e-02,
                3.447452412938972754e-02,
                3.447452412938972754e-02,
                3.447452412938972754e-02,
                3.422118782506290702e-02,
                3.422118782506290702e-02,
                3.422118782506290702e-02,
                3.422118782506290702e-02,
                3.422118782506290702e-02,
                3.465777251594818337e-02,
                3.465777251594818337e-02,
                3.465777251594818337e-02,
                3.465777251594818337e-02,
                3.465777251594818337e-02,
                3.428444611385943197e-02,
                3.428444611385943197e-02,
                3.428444611385943197e-02,
                3.428444611385943197e-02,
                3.428444611385943197e-02,
                3.455241744213354699e-02,
                3.455241744213354699e-02,
                3.455241744213354699e-02,
                3.455241744213354699e-02,
                3.455241744213354699e-02,
                3.459664463897634684e-02,
                3.459664463897634684e-02,
                3.459664463897634684e-02,
                3.459664463897634684e-02,
                3.459664463897634684e-02,
                3.430990453352705805e-02,
                3.430990453352705805e-02,
                3.430990453352705805e-02,
                3.430990453352705805e-02,
                3.430990453352705805e-02,
                3.493005205258781221e-02,
                3.493005205258781221e-02,
                3.493005205258781221e-02,
                3.493005205258781221e-02,
                3.493005205258781221e-02,
                3.414040129262881085e-02,
                3.414040129262881085e-02,
                3.414040129262881085e-02,
                3.414040129262881085e-02,
                3.414040129262881085e-02,
                3.506482384028909716e-02,
                3.506482384028909716e-02,
                3.506482384028909716e-02,
                3.506482384028909716e-02,
                3.506482384028909716e-02,
                3.427124116588566721e-02,
                3.427124116588566721e-02,
                3.427124116588566721e-02,
                3.427124116588566721e-02,
                3.427124116588566721e-02,
                3.489262295016173909e-02,
                3.489262295016173909e-02,
                3.489262295016173909e-02,
                3.489262295016173909e-02,
                3.489262295016173909e-02,
                3.464002963924085743e-02,
                3.464002963924085743e-02,
                3.464002963924085743e-02,
                3.464002963924085743e-02,
                3.464002963924085743e-02,
                3.446025647539283782e-02,
                3.446025647539283782e-02,
                3.446025647539283782e-02,
                3.446025647539283782e-02,
                3.446025647539283782e-02,
                3.494323310030658658e-02,
                3.494323310030658658e-02,
                3.494323310030658658e-02,
                3.494323310030658658e-02,
                3.494323310030658658e-02,
                3.413889080384188701e-02,
                3.413889080384188701e-02,
                3.413889080384188701e-02,
                3.413889080384188701e-02,
                3.413889080384188701e-02,
                3.495917470829300322e-02,
                3.495917470829300322e-02,
                3.495917470829300322e-02,
                3.495917470829300322e-02,
                3.495917470829300322e-02,
                3.416668444551070744e-02,
                3.416668444551070744e-02,
                3.416668444551070744e-02,
                3.416668444551070744e-02,
                3.416668444551070744e-02,
                3.468591118316260297e-02,
                3.468591118316260297e-02,
                3.468591118316260297e-02,
                3.468591118316260297e-02,
                3.468591118316260297e-02,
                3.443776863194184662e-02,
                3.443776863194184662e-02,
                3.443776863194184662e-02,
                3.443776863194184662e-02,
                3.443776863194184662e-02,
                3.431424211129673052e-02,
                3.431424211129673052e-02,
                3.431424211129673052e-02,
                3.431424211129673052e-02,
                3.431424211129673052e-02,
                3.455988060207296209e-02,
                3.455988060207296209e-02,
                3.455988060207296209e-02,
                3.455988060207296209e-02,
                3.455988060207296209e-02,
                3.433511480612023298e-02,
                3.433511480612023298e-02,
                3.433511480612023298e-02,
                3.433511480612023298e-02,
                3.433511480612023298e-02,
                3.425761119854710962e-02,
                3.425761119854710962e-02,
                3.425761119854710962e-02,
                3.425761119854710962e-02,
                3.425761119854710962e-02,
                3.472678385861750761e-02,
                3.472678385861750761e-02,
                3.472678385861750761e-02,
                3.472678385861750761e-02,
                3.472678385861750761e-02,
                3.388053160900311722e-02,
                3.388053160900311722e-02,
                3.388053160900311722e-02,
                3.388053160900311722e-02,
                3.388053160900311722e-02,
                3.497223687177687668e-02,
                3.497223687177687668e-02,
                3.497223687177687668e-02,
                3.497223687177687668e-02,
                3.497223687177687668e-02,
                3.396864949541721773e-02,
                3.396864949541721773e-02,
                3.396864949541721773e-02,
                3.396864949541721773e-02,
                3.396864949541721773e-02,
                3.469844278766760770e-02,
                3.469844278766760770e-02,
                3.469844278766760770e-02,
                3.469844278766760770e-02,
                3.469844278766760770e-02,
                3.452670784877116122e-02,
                3.452670784877116122e-02,
                3.452670784877116122e-02,
                3.452670784877116122e-02,
                3.452670784877116122e-02,
                3.422903138820843766e-02,
                3.422903138820843766e-02,
                3.422903138820843766e-02,
                3.422903138820843766e-02,
                3.422903138820843766e-02,
                3.505664855164936089e-02,
                3.505664855164936089e-02,
                3.505664855164936089e-02,
                3.505664855164936089e-02,
                3.505664855164936089e-02,
                3.413682892847823974e-02,
                3.413682892847823974e-02,
                3.413682892847823974e-02,
                3.413682892847823974e-02,
                3.413682892847823974e-02,
                3.501385140272599700e-02,
                3.501385140272599700e-02,
                3.501385140272599700e-02,
                3.501385140272599700e-02,
                3.501385140272599700e-02,
                3.467226010953376736e-02,
                3.467226010953376736e-02,
                3.467226010953376736e-02,
                3.467226010953376736e-02,
                3.467226010953376736e-02,
                3.446833192932739071e-02,
                3.446833192932739071e-02,
                3.446833192932739071e-02,
                3.446833192932739071e-02,
                3.446833192932739071e-02,
                3.537578680325848685e-02,
                3.537578680325848685e-02,
                3.537578680325848685e-02,
                3.537578680325848685e-02,
                3.537578680325848685e-02,
                3.424582265861417230e-02,
                3.424582265861417230e-02,
                3.424582265861417230e-02,
                3.424582265861417230e-02,
                3.424582265861417230e-02,
                3.542063347291982134e-02,
                3.542063347291982134e-02,
                3.542063347291982134e-02,
                3.542063347291982134e-02,
                3.542063347291982134e-02,
                3.473157847887777677e-02,
                3.473157847887777677e-02,
                3.473157847887777677e-02,
                3.473157847887777677e-02,
                3.473157847887777677e-02,
                3.500395496816594010e-02,
                3.500395496816594010e-02,
                3.500395496816594010e-02,
                3.500395496816594010e-02,
                3.500395496816594010e-02,
                3.527956468212912339e-02,
                3.527956468212912339e-02,
                3.527956468212912339e-02,
                3.527956468212912339e-02,
                3.527956468212912339e-02,
                3.474612912967797729e-02,
                3.474612912967797729e-02,
                3.474612912967797729e-02,
                3.474612912967797729e-02,
                3.474612912967797729e-02,
                3.553270958271387281e-02,
                3.553270958271387281e-02,
                3.553270958271387281e-02,
                3.553270958271387281e-02,
                3.553270958271387281e-02,
                3.484753394974442198e-02,
                3.484753394974442198e-02,
                3.484753394974442198e-02,
                3.484753394974442198e-02,
                3.484753394974442198e-02,
                3.551019189257811903e-02,
                3.551019189257811903e-02,
                3.551019189257811903e-02,
                3.551019189257811903e-02,
                3.551019189257811903e-02,
                3.507201831631155675e-02,
                3.507201831631155675e-02,
                3.507201831631155675e-02,
                3.507201831631155675e-02,
                3.507201831631155675e-02,
                3.547010763766055702e-02,
                3.547010763766055702e-02,
                3.547010763766055702e-02,
                3.547010763766055702e-02,
                3.547010763766055702e-02,
                3.517521602408801851e-02,
                3.517521602408801851e-02,
                3.517521602408801851e-02,
                3.517521602408801851e-02,
                3.517521602408801851e-02,
                3.560587944514344294e-02,
                3.560587944514344294e-02,
                3.560587944514344294e-02,
                3.560587944514344294e-02,
                3.560587944514344294e-02,
                3.515305893273550086e-02,
                3.515305893273550086e-02,
                3.515305893273550086e-02,
                3.515305893273550086e-02,
                3.515305893273550086e-02,
                3.553033966094291257e-02,
                3.553033966094291257e-02,
                3.553033966094291257e-02,
                3.553033966094291257e-02,
                3.553033966094291257e-02,
                3.542770249150801326e-02,
                3.542770249150801326e-02,
                3.542770249150801326e-02,
                3.542770249150801326e-02,
                3.542770249150801326e-02,
                3.535849182230862281e-02,
                3.535849182230862281e-02,
                3.535849182230862281e-02,
                3.535849182230862281e-02,
                3.535849182230862281e-02,
                3.553514224021542961e-02,
                3.553514224021542961e-02,
                3.553514224021542961e-02,
                3.553514224021542961e-02,
                3.553514224021542961e-02,
                3.546214622480455686e-02,
                3.546214622480455686e-02,
                3.546214622480455686e-02,
                3.546214622480455686e-02,
                3.546214622480455686e-02,
                3.534243011214804886e-02,
                3.534243011214804886e-02,
                3.534243011214804886e-02,
                3.534243011214804886e-02,
                3.534243011214804886e-02,
                3.579446872783990236e-02,
                3.579446872783990236e-02,
                3.579446872783990236e-02,
                3.579446872783990236e-02,
                3.579446872783990236e-02,
                3.519519788962451740e-02,
                3.519519788962451740e-02,
                3.519519788962451740e-02,
                3.519519788962451740e-02,
                3.519519788962451740e-02,
                3.591039930922464846e-02,
                3.591039930922464846e-02,
                3.591039930922464846e-02,
                3.591039930922464846e-02,
                3.591039930922464846e-02,
                3.541775767428190919e-02,
                3.541775767428190919e-02,
                3.541775767428190919e-02,
                3.541775767428190919e-02,
                3.541775767428190919e-02,
                3.528980277571380081e-02,
                3.528980277571380081e-02,
                3.528980277571380081e-02,
                3.528980277571380081e-02,
                3.528980277571380081e-02,
                3.614923854239279061e-02,
                3.614923854239279061e-02,
                3.614923854239279061e-02,
                3.614923854239279061e-02,
                3.614923854239279061e-02,
                3.482687957692427033e-02,
                3.482687957692427033e-02,
                3.482687957692427033e-02,
                3.482687957692427033e-02,
                3.482687957692427033e-02,
                3.616452572173328717e-02,
                3.616452572173328717e-02,
                3.616452572173328717e-02,
                3.616452572173328717e-02,
                3.616452572173328717e-02,
                3.537259416044979954e-02,
                3.537259416044979954e-02,
                3.537259416044979954e-02,
                3.537259416044979954e-02,
                3.537259416044979954e-02,
                3.533826691588583258e-02,
                3.533826691588583258e-02,
                3.533826691588583258e-02,
                3.533826691588583258e-02,
                3.533826691588583258e-02,
                3.627226201745910317e-02,
                3.627226201745910317e-02,
                3.627226201745910317e-02,
                3.627226201745910317e-02,
                3.627226201745910317e-02,
                3.423502106182098326e-02,
                3.423502106182098326e-02,
                3.423502106182098326e-02,
                3.423502106182098326e-02,
                3.423502106182098326e-02,
                3.634959376129698327e-02,
                3.634959376129698327e-02,
                3.634959376129698327e-02,
                3.634959376129698327e-02,
                3.634959376129698327e-02,
                3.481847085182868118e-02,
                3.481847085182868118e-02,
                3.481847085182868118e-02,
                3.481847085182868118e-02,
                3.481847085182868118e-02,
                3.542398985871488687e-02,
                3.542398985871488687e-02,
                3.542398985871488687e-02,
                3.542398985871488687e-02,
                3.542398985871488687e-02,
                3.593774678925047011e-02,
                3.593774678925047011e-02,
                3.593774678925047011e-02,
                3.593774678925047011e-02,
                3.593774678925047011e-02,
                3.476658486982214802e-02,
                3.476658486982214802e-02,
                3.476658486982214802e-02,
                3.476658486982214802e-02,
                3.476658486982214802e-02,
                3.582990314086371975e-02,
                3.582990314086371975e-02,
                3.582990314086371975e-02,
                3.582990314086371975e-02,
                3.582990314086371975e-02,
                3.545358423877494058e-02,
                3.545358423877494058e-02,
                3.545358423877494058e-02,
                3.545358423877494058e-02,
                3.545358423877494058e-02,
                3.498993803680634090e-02,
                3.498993803680634090e-02,
                3.498993803680634090e-02,
                3.498993803680634090e-02,
                3.498993803680634090e-02,
                3.597205036018003010e-02,
                3.597205036018003010e-02,
                3.597205036018003010e-02,
                3.597205036018003010e-02,
                3.597205036018003010e-02,
                3.446155855797314316e-02,
                3.446155855797314316e-02,
                3.446155855797314316e-02,
                3.446155855797314316e-02,
                3.446155855797314316e-02,
                3.581126231987367264e-02,
                3.581126231987367264e-02,
                3.581126231987367264e-02,
                3.581126231987367264e-02,
                3.581126231987367264e-02,
                3.478015905080063253e-02,
                3.478015905080063253e-02,
                3.478015905080063253e-02,
                3.478015905080063253e-02,
                3.478015905080063253e-02,
                3.443810893728960904e-02,
                3.443810893728960904e-02,
                3.443810893728960904e-02,
                3.443810893728960904e-02,
                3.443810893728960904e-02,
                3.569590158872352342e-02,
                3.569590158872352342e-02,
                3.569590158872352342e-02,
                3.569590158872352342e-02,
                3.569590158872352342e-02,
                3.432753190054284309e-02,
                3.432753190054284309e-02,
                3.432753190054284309e-02,
                3.432753190054284309e-02,
                3.432753190054284309e-02,
                3.544836843313777658e-02,
                3.544836843313777658e-02,
                3.544836843313777658e-02,
                3.544836843313777658e-02,
                3.544836843313777658e-02,
                3.543386307485828918e-02,
                3.543386307485828918e-02,
                3.543386307485828918e-02,
                3.543386307485828918e-02,
                3.543386307485828918e-02,
                3.475414975257572203e-02,
                3.475414975257572203e-02,
                3.475414975257572203e-02,
                3.475414975257572203e-02,
                3.475414975257572203e-02,
                3.623532577187223852e-02,
                3.623532577187223852e-02,
                3.623532577187223852e-02,
                3.623532577187223852e-02,
                3.623532577187223852e-02,
                3.498589418669603018e-02,
                3.498589418669603018e-02,
                3.498589418669603018e-02,
                3.498589418669603018e-02,
                3.498589418669603018e-02,
                3.601035760359522220e-02,
                3.601035760359522220e-02,
                3.601035760359522220e-02,
                3.601035760359522220e-02,
                3.601035760359522220e-02,
                3.571598482439355265e-02,
                3.571598482439355265e-02,
                3.571598482439355265e-02,
                3.571598482439355265e-02,
                3.571598482439355265e-02,
                3.534934671238836035e-02,
                3.534934671238836035e-02,
                3.534934671238836035e-02,
                3.534934671238836035e-02,
                3.534934671238836035e-02,
                3.653479201847238678e-02,
                3.653479201847238678e-02,
                3.653479201847238678e-02,
                3.653479201847238678e-02,
                3.653479201847238678e-02,
                3.514669636147733228e-02,
                3.514669636147733228e-02,
                3.514669636147733228e-02,
                3.514669636147733228e-02,
                3.514669636147733228e-02,
                3.647867000742373300e-02,
                3.647867000742373300e-02,
                3.647867000742373300e-02,
                3.647867000742373300e-02,
                3.647867000742373300e-02,
                3.598325202148640323e-02,
                3.598325202148640323e-02,
                3.598325202148640323e-02,
                3.598325202148640323e-02,
                3.598325202148640323e-02,
                3.558951505402629251e-02,
                3.558951505402629251e-02,
                3.558951505402629251e-02,
                3.558951505402629251e-02,
                3.558951505402629251e-02,
                3.682573897489994225e-02,
                3.682573897489994225e-02,
                3.682573897489994225e-02,
                3.682573897489994225e-02,
                3.682573897489994225e-02,
                3.534076002299529201e-02,
                3.534076002299529201e-02,
                3.534076002299529201e-02,
                3.534076002299529201e-02,
                3.534076002299529201e-02,
                3.636272692795870093e-02,
                3.636272692795870093e-02,
                3.636272692795870093e-02,
                3.636272692795870093e-02,
                3.636272692795870093e-02,
                3.655068671208203807e-02,
                3.655068671208203807e-02,
                3.655068671208203807e-02,
                3.655068671208203807e-02,
                3.655068671208203807e-02,
                3.493682960177779684e-02,
                3.493682960177779684e-02,
                3.493682960177779684e-02,
                3.493682960177779684e-02,
                3.493682960177779684e-02,
                3.779155472817560812e-02,
                3.779155472817560812e-02,
                3.779155472817560812e-02,
                3.779155472817560812e-02,
                3.779155472817560812e-02,
                3.483490749431893824e-02,
                3.483490749431893824e-02,
                3.483490749431893824e-02,
                3.483490749431893824e-02,
                3.483490749431893824e-02,
                3.678881243506237908e-02,
                3.678881243506237908e-02,
                3.678881243506237908e-02,
                3.678881243506237908e-02,
                3.678881243506237908e-02,
                3.686808328654698347e-02,
                3.686808328654698347e-02,
                3.686808328654698347e-02,
                3.686808328654698347e-02,
                3.686808328654698347e-02,
                3.468309812080880294e-02,
                3.468309812080880294e-02,
                3.468309812080880294e-02,
                3.468309812080880294e-02,
                3.468309812080880294e-02,
                3.824179402913956138e-02,
                3.824179402913956138e-02,
                3.824179402913956138e-02,
                3.824179402913956138e-02,
                3.824179402913956138e-02,
                3.470961121452373344e-02,
                3.470961121452373344e-02,
                3.470961121452373344e-02,
                3.470961121452373344e-02,
                3.470961121452373344e-02,
                3.650575961292887306e-02,
                3.650575961292887306e-02,
                3.650575961292887306e-02,
                3.650575961292887306e-02,
                3.650575961292887306e-02,
                3.749696733203376764e-02,
                3.749696733203376764e-02,
                3.749696733203376764e-02,
                3.749696733203376764e-02,
                3.749696733203376764e-02,
                3.338198185796528022e-02,
                3.338198185796528022e-02,
                3.338198185796528022e-02,
                3.338198185796528022e-02,
                3.338198185796528022e-02,
                3.937055618169763710e-02,
                3.937055618169763710e-02,
                3.937055618169763710e-02,
                3.937055618169763710e-02,
                3.937055618169763710e-02,
                3.310853107320777672e-02,
                3.310853107320777672e-02,
                3.310853107320777672e-02,
                3.310853107320777672e-02,
                3.310853107320777672e-02,
                3.700959517482681205e-02,
                3.700959517482681205e-02,
                3.700959517482681205e-02,
                3.700959517482681205e-02,
                3.700959517482681205e-02,
                3.704612693606450929e-02,
                3.704612693606450929e-02,
                3.704612693606450929e-02,
                3.704612693606450929e-02,
                3.704612693606450929e-02,
                3.203443339179724153e-02,
                3.203443339179724153e-02,
                3.203443339179724153e-02,
                3.203443339179724153e-02,
                3.203443339179724153e-02,
                4.071226135228286219e-02,
                4.071226135228286219e-02,
                4.071226135228286219e-02,
                4.071226135228286219e-02,
                4.071226135228286219e-02,
                3.104691103039200137e-02,
                3.104691103039200137e-02,
                3.104691103039200137e-02,
                3.104691103039200137e-02,
                3.104691103039200137e-02,
                3.739743903050309765e-02,
                3.739743903050309765e-02,
                3.739743903050309765e-02,
                3.739743903050309765e-02,
                3.739743903050309765e-02,
                3.793245311181699803e-02,
                3.793245311181699803e-02,
                3.793245311181699803e-02,
                3.793245311181699803e-02,
                3.793245311181699803e-02,
                2.866205938771973147e-02,
                2.866205938771973147e-02,
                2.866205938771973147e-02,
                2.866205938771973147e-02,
                2.866205938771973147e-02,
                4.474093222324695973e-02,
                4.474093222324695973e-02,
                4.474093222324695973e-02,
                4.474093222324695973e-02,
                4.474093222324695973e-02,
                2.873628504976361020e-02,
                2.873628504976361020e-02,
                2.873628504976361020e-02,
                2.873628504976361020e-02,
                2.873628504976361020e-02,
                3.015069375755836945e-02,
                3.015069375755836945e-02,
                3.015069375755836945e-02,
                3.015069375755836945e-02,
                3.015069375755836945e-02,
                6.145563946363479663e-02,
                6.145563946363479663e-02,
                6.145563946363479663e-02,
                6.145563946363479663e-02,
                6.145563946363479663e-02,
            ])

            if length_smpl < np.size(data):
                N = length_smpl
            else:
                N = np.size(data)

            res = np.zeros(length_smpl)
            res[0:N] = data[0:N]
            samples[start:start + length_smpl] = np.int16(np.round(res * amps * 2047, 1))

    def constant(self, samples, start, constant_value, length_smpl):
        samples[start:start + length_smpl] += np.int16(constant_value * 2047)

    def samples_waveform(self, coherent_offset, start=0, samples=None):
        samples = np.zeros(self.length_smpl, dtype=np.int16) if samples is None else samples
        effective_coherent_offset = self.effective_offset(coherent_offset)
        if self.type in ['sine', 'robust']:
            if self.type == 'sine':
                amplitudes = self.amplitudes
                phases = list_repeat([0.0])  # self.phases is added automatically
            elif self.type == 'robust':
                amplitudes = self.wave_file.amplitudes_samples
                phases = self.wave_file.phases_samples  # self.phases is added automatically
            self.sin(samples=samples,
                     start=start,
                     amps=amplitudes,
                     freqs=self.frequencies,
                     phases=phases,
                     length_smpl=self.length_smpl,
                     coherent_offset=effective_coherent_offset)
        elif self.type == 'constant':
            self.constant(samples=samples,
                          start=start,
                          constant_value=self.constant_value,
                          length_smpl=self.length_smpl)
        elif self.type == 'gauss':
            amplitudes = self.amplitudes
            self.gauss(samples=samples,
                       start=start,
                       amps=amplitudes,
                       inv_fwhm=self.frequencies,
                       length_smpl=self.length_smpl)
        elif self.type == 'gauss_2_pulses':
            amplitudes = self.amplitudes
            self.gauss_2_pulses(samples=samples,
                       start=start,
                       amps=amplitudes,
                       inv_fwhm=self.frequencies,
                       length_smpl=self.length_smpl)

        elif self.type == 'gauss_6ns':
            amplitudes = self.amplitudes
            self.gauss_6ns(samples=samples,
                       start=start,
                       amps=amplitudes,
                       inv_fwhm=self.frequencies,
                       length_smpl=self.length_smpl)


        elif self.type == 'gauss_10ns':
            amplitudes = self.amplitudes
            self.gauss_10ns(samples=samples,
                       start=start,
                       amps=amplitudes,
                       inv_fwhm=self.frequencies,
                       length_smpl=self.length_smpl)



        samples[start:start + self.length_smpl] *= 2 ** 4
        samples[start:start + self.length_smpl] += self.marker
        return samples

    @property
    def samples_smpl_marker(self):
        return np.full(self.length_smpl, self.smpl_marker, dtype=np.int8)

    @property
    def samples_sync_marker(self):
        return np.full(self.length_smpl, self.sync_marker, dtype=np.int8)

    @property
    def marker(self):
        return self.smpl_marker + 2 * self.sync_marker

    @property
    def samples_marker(self):
        return np.full(self.length_smpl, self.smpl_marker + 2 * self.sync_marker, dtype=np.int8)

    @property
    def normalized_avg_sine_power(self):
        if self.type == 'sine':
            return sum(self.amplitudes ** 2)
        elif self.type == 'robust':
            return sum([self.wave_file.amplitude(i[0], i[1]) ** 2 for i in itertools.product(range(self.wave_file.number_of_steps), range(len(self.frequencies)))]) / self.wave_file.number_of_steps
        elif self.type == 'wait':
            return 0
        elif self.type == 'constant':
            return 0
        elif self.type == 'gauss':
            return 0
        elif self.type == 'gauss_2_pulses':
            return 0

        elif self.type == 'gauss_6ns':
            return 0

        elif self.type == 'gauss_10ns':
            return 0

        else:
            raise Exception('Neither sine nor robust do apply here...{}'.format(self.type))

    def ret_info(self, row=0, prefix=''):
        if self.type == 'wait':
            l = [self.name, self.length_mus, self.type, int(self.smpl_marker), int(self.sync_marker)]
        if self.type == 'constant':
            l = [self.name, self.length_mus, self.type, self.constant_value, int(self.smpl_marker), int(self.sync_marker)]
        elif self.type == 'sine':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.amplitudes, self.phases, int(self.smpl_marker), int(self.sync_marker)]
        elif self.type == 'robust':
            l = [self.name, self.length_mus, self.type, self.frequencies, 'wave_file', self.phases, int(self.smpl_marker), int(self.sync_marker)]
        elif self.type == 'gauss':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.amplitudes, int(self.smpl_marker),
                 int(self.sync_marker)]
        elif self.type == 'gauss_2_pulses':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.amplitudes, int(self.smpl_marker),
                 int(self.sync_marker)]



        elif self.type == 'gauss_6ns':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.amplitudes, int(self.smpl_marker),
                 int(self.sync_marker)]
        elif self.type == 'gauss_10ns':
            l = [self.name, self.length_mus, self.type, self.frequencies, self.amplitudes, int(self.smpl_marker),
                 int(self.sync_marker)]
        return self.ret_list(l, row=row, prefix=prefix)

    def print_info(self, *args, **kwargs):
        print(self.ret_info(*args, **kwargs))

class BaseLoopAdvance(Root):

    def __init__(self, loop_count=1, **kwargs):
        super(BaseLoopAdvance, self).__init__(**kwargs)
        self.loop_count = loop_count
        self.advance_mode = kwargs['advance_mode']

    loop_count = util.ret_property_range('loop_count', int, 0, 2 ** 32 - 1)
    advance_mode = util.ret_property_list_element('advance_mode', ['AUTO', 'COND', 'REP', 'SING'])


class BaseDataList(Root):

    def __init__(self, data_list=None, **kwargs):
        super(BaseDataList, self).__init__(**kwargs)
        self.data_list = [] if data_list is None else data_list

    @property
    def length_mus(self):
        return np.sum(step.repeated_length_mus for step in self.data_list)

    @property
    def length_smpl(self):
        return length_mus2length_smpl(self.length_mus)

    @property
    def data_list(self):
        return self._data_list

    @data_list.setter
    def data_list(self, val):
        for i in util.check_type(val, 'data_list', (list, DataList)):
            if not isinstance(i, self.__DATA_LIST_ITEM_TYPE__):
                raise Exception("Elements of property data_list of a {} - instance must be of type {} but is of type {}".format(type(self), self.__DATA_LIST_ITEM_TYPE__, type(i)))
        self._data_list = DataList(self.__DATA_LIST_ITEM_TYPE__, self, *val)

    def samples_waveform(self, coherent_offset, start=0, samples=None):
        samples = np.zeros(self.length_smpl, dtype=np.int16) if samples is None else samples
        idx = start
        for i, step in enumerate(self.data_list):
            loop_count = 1 if not hasattr(step, '_loop_count') else step.loop_count
            for _ in range(loop_count):
                step.samples_waveform(coherent_offset + idx, start=idx, samples=samples)  # , loop_count #samples[: idx + rls] =
                idx += step.length_smpl
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
        return sum([step.repeated_length_mus * step.normalized_avg_sine_power for step in self.data_list]) / self.repeated_length_mus

    def ret_info(self, row=0, prefix=''):
        out = []
        if hasattr(self, 'loop_count'):
            out.append(self.ret_list([self.name, self.repeated_length_mus, self.loop_count], row=row, prefix=prefix))
        else:
            print('does not have loop count')
            out.append(self.ret_list([self.name, self.repeated_length_mus], row=row, prefix=prefix))
        for i, step in enumerate(self.data_list):
            out.append(step.ret_info(row=i, prefix="   " + prefix))
        return "\n".join(out)

    def print_info(self, *args, **kwargs):
        print(self.ret_info(*args, **kwargs))

    def pi(self, *args, **kwargs):
        self.print_info(*args, **kwargs)


class BaseSequenceStep(BaseWave, BaseLoopAdvance):

    def __init__(self, marker_enable=True, advance_mode='AUTO', **kwargs):
        super(BaseSequenceStep, self).__init__(advance_mode=advance_mode, **kwargs)
        self.marker_enable = marker_enable
        self.set_segment_offsets(**kwargs)

    @property
    def sequence_id(self):
        return self._sequence_id

    @BaseLoopAdvance.loop_count.setter
    def loop_count(self, val):
        BaseLoopAdvance.loop_count.fset(self, val)
        self.write_sequence_memory = True

    @BaseLoopAdvance.advance_mode.setter
    def advance_mode(self, val):
        BaseLoopAdvance.advance_mode.fset(self, val)
        self.write_sequence_memory = True

    @property
    def marker_enable(self):
        return self._marker_enable

    @marker_enable.setter
    def marker_enable(self, val):
        if val is False:
            print('Warning: ONLY SET TO FALSE IF YOU KNOW WHAT YOU ARE DOING')
        self._marker_enable = util.check_type(val, 'marker_enable', bool)
        self.write_sequence_memory = True

    def set_segment_offsets(self, **kwargs):
        default = {'segment_start_offset': 0, 'segment_end_offset': 2 ** 32 - 1}
        for s in ['segment_start_offset', 'segment_end_offset']:
            if s not in kwargs and s+'_mus' not in kwargs:
                setattr(self, s, default[s])
            elif s in kwargs and s+'_mus' in kwargs:
                raise Exception('Error: overdetermination. {}'.format(kwargs))
            elif s in kwargs:
                setattr(self, s, kwargs[s])
            else:
                setattr(self, s, kwargs[s+'_mus'])

    @property
    def segment_start_offset_mus(self):
        return self._segment_start_offset_mus

    @property
    def segment_start_offset(self):
        return self._segment_start_offset

    @segment_start_offset_mus.setter
    def segment_start_offset_mus(self, val):
        if val is not None:
            valid_length_mus(val)
            self._segment_start_offset_mus = util.check_range(util.check_type(val, 'segment_start_offset_mus', Number), 'segment_start_offset_mus', 0, __MAX_LENGTH_SMPL__ / __SAMPLE_FREQUENCY__)
            self._segment_start_offset = length_mus2length_smpl(self._segment_start_offset_mus)

    @segment_start_offset.setter
    def segment_start_offset(self, val):
        if val is not None:
            self._segment_start_offset_mus = util.check_range(util.check_type(val, 'segment_start_offset_mus', Number), 'segment_start_offset_mus', 0, __MAX_LENGTH_SMPL__) / __SAMPLE_FREQUENCY__
            self._segment_start_offset = length_mus2length_smpl(self._segment_start_offset_mus)

    @property
    def segment_end_offset_mus(self):
        return self._segment_end_offset_mus

    @property
    def segment_end_offset(self):
        return self._segment_end_offset

    @segment_end_offset_mus.setter
    def segment_end_offset_mus(self, val):
        if val is not None:
            valid_length_mus(val)
            self._segment_end_offset_mus = util.check_range(util.check_type(val, 'segment_end_offset_mus', Number), 'segment_end_offset_mus', 0, __MAX_LENGTH_SMPL__ / __SAMPLE_FREQUENCY__)
            self._segment_end_offset = length_mus2length_smpl(self._segment_end_offset_mus)

    @segment_end_offset.setter
    def segment_end_offset(self, val):
        if val is not None:
            if val == 2 ** 32 - 1:
                self._segment_end_offset_mus = np.inf
                self._segment_end_offset = val
            else:
                self._segment_end_offset_mus = util.check_range(util.check_type(val, 'segment_end_offset_mus', Number), 'segment_end_offset_mus', 0, __MAX_LENGTH_SMPL__) / __SAMPLE_FREQUENCY__
                self._segment_end_offset = length_mus2length_smpl(self._segment_end_offset_mus)


class SequenceStepReuseSegment(BaseSequenceStep):
    def __init__(self, reused_sequence_step=None, **kwargs):
        super(SequenceStepReuseSegment, self).__init__(**kwargs)
        if reused_sequence_step is not None:
            self.reused_sequence_step = reused_sequence_step
        else:
            raise Exception('Error!')
        self.write_sequence_memory = True

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
            return self.reused_sequence_step.__getattribute__(name)


class SequenceStep(BaseDataList, BaseSequenceStep):

    __DATA_LIST_ITEM_TYPE__ = WaveStep

    @property
    def segment_size_bytes(self):
        return 2 * self.length_smpl

    def segment_block_data(self, coherent_offset):
        return self.samples_waveform(coherent_offset)

    @property
    def wavestep_list(self):
        return list(itertools.chain(*itertools.repeat(self.data_list, self.loop_count)))

    @property
    def segment_id(self):
        return self._segment_id

    def precompile_samples_waveform(self, coherent_offset, start=0, samples=None, notify=True):
        t0 = time.time()
        self._samples_waveform = self.samples_waveform(coherent_offset, start=0, samples=None)

        def samples_waveform(self, *args, **kwargs):
            return self._samples_waveform

        self.samples_waveform = types.MethodType(samples_waveform, self)
        if notify:
            logging.getLogger().debug("type {} {} precompiled ({} s).".format(self.name, type(self), time.time() - t0))

    def set_write_awg(self, **kwargs):
        self.write_segment_memory = True


class Sequence(BaseWave, BaseLoopAdvance, BaseDataList):
    def __init__(self, name, advance_mode='COND', **kwargs):
        super(Sequence, self).__init__(name=name, advance_mode=advance_mode, **kwargs)
        self.date = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    __DATA_LIST_ITEM_TYPE__ = BaseSequenceStep

    date = util.ret_property_typecheck('date', str)

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

    def precompile_samples_waveform(self, coherent_offset, start=0, samples=None, notify=True):
        t0 = time.time()
        idx = start
        for i, step in enumerate(self.data_list):
            if isinstance(step, SequenceStepReuseSegment):
                continue
            step.precompile_samples_waveform(coherent_offset + idx, start=idx, samples=samples)  # , loop_count #samples[: idx + rls] =
            idx += step.length_smpl * step.loop_count
        if notify:
            logging.getLogger().debug("type {} {} precompiled ({} s).".format(self.name, type(self), time.time() - t0))

    @BaseLoopAdvance.loop_count.setter
    def loop_count(self, val):
        BaseLoopAdvance.loop_count.fset(self, val)
        if hasattr(self, '_data_list') and len(self.data_list) > 0:
            self.data_list[0].write_sequence_memory = True

    @BaseLoopAdvance.advance_mode.setter
    def advance_mode(self, val):
        BaseLoopAdvance.advance_mode.fset(self, val)
        if hasattr(self, '_data_list') and len(self.data_list) > 0:
            self.data_list[0].write_sequence_memory = True

    def sequence_table_data_block(self, segment_ids, sequence_id_offset=0):
        if self.number_of_steps != len(segment_ids):
            raise Exception('What happened?')


        nbytes = str(24 * self.number_of_steps)
        bytes_length = str(len(nbytes))

        ###
        cmd = '{},{}'.format(sequence_id_offset, '#' + bytes_length + str(nbytes))
        seq_loop_count = struct.pack('I', self.loop_count)
        advance_map = {'AUTO': 0, 'COND': 1, 'REP': 2, 'SING': 3}
        for i, step in enumerate(self.data_list):
            control = 0
            # init and end sequence markers
            if i == 0:
                control += 2 ** 28
            if i == self.number_of_steps - 1:
                control += 2 ** 30
            # marker enable:
            control += step.marker_enable * 2 ** 24
            # sequence advance
            control += advance_map[self.advance_mode] * 2 ** 20
            # wave advance
            wave_start_offset = struct.pack('I', step.segment_start_offset)
            wave_end_offset = struct.pack('I', step.segment_end_offset)

            control += advance_map[step.advance_mode] * 2**16
            control = struct.pack('I', control)
            wave_id = struct.pack('I', segment_ids[i])
            wave_lc = struct.pack('I', step.loop_count)
            data = ( control + seq_loop_count + wave_lc
                   + wave_id + wave_start_offset + wave_end_offset)
            if type(cmd) == str:
                cmd = cmd.encode()
            cmd += data
            step._sequence_id = sequence_id_offset + i
            # control += advance_map[step.advance_mode] * 2 ** 16
            # control = struct.pack('I', control)
            # # wave_id = struct.pack('I', segment_ids[i])
            # wave_lc = struct.pack('I', step.loop_count)
           
            # data = (control + seq_loop_count + wave_lc
            #         + wave_id + wave_start_offset + wave_end_offset)
            # cmd += data
            # step._sequence_id = sequence_id_offset + i
        return cmd

    def dl(self, sequence_step_num, wave_step_num=None):
        if wave_step_num is None:
            return self.data_list[sequence_step_num]
        else:
            return self.data_list[sequence_step_num].data_list[wave_step_num]

    def set_write_awg(self, idx=None, val=None, action=None):
        if idx == 0:  # the first step in a sequence must be marked
            val.write_sequence_memory = True
            if action == 'insert' and hasattr(self, '_data_list') and len(self.data_list) > 1:  # the now second step no more is start of the sequence and must be unmarked
                self.data_list[1].write_sequence_memory = True