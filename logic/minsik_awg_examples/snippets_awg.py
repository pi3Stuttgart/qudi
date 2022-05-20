from __future__ import print_function, absolute_import, division
from imp import reload

import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)

from traits.api import *
import numpy as np
from decimal import Decimal
import copy
import traceback
import sys

import misc
from pi3diamond import pi3d
from AWG_M8190A_Elements import WaveFile, WaveStep, SequenceStep, Sequence
import pym8190a
import numbers
import TransitionTracker
import collections

__CURRENT_POL_RED__ = 76
__T_POL_RED__ = 60.
__RED_LASER__DELAY__ = 2.
__SSR_REPETITIONS__ = {'14n+1': 1500, '14n-1': 1500, '14n': 1500, '14n0': 1200, '13c414': 1500, '13c90': 2000, 'charge_state':1}
__LASER_DUR_DICT__ = {'14n+1': .175, '14n-1': .175, '14n': .175, '14n0': .2, '13c414': .2, '13c90': .21, 'single_state': .2, 'charge_state': 2000.0} # us
__PERIODS__ = {'14n+1': 1.6, '14n-1': 1.6, '14n': 1.6, '14n0': 1.6, '13c414': 6.0, '13c90': 20., 'charge_state': 0.0}
__WAVE_FILE_SCALING_FACTOR_DICT__ = {'14n+1': 2.5, '14n-1': 2.5, '14n': 2.5, '14n0': 2.5, '13c414': 1.0, 'charge_state': 1.0}
__STANDARD_WAVEFILE__ = 'D:\data\Robust_Pulses\single_pulse_ON03_OFF05_Rabi10_02.dat'
__STANDARD_WAVEFILES__ = {'14n+1': "D:\data\NuclearOPs\Robust\test_pi_three_nitrogen\20171204-h18m52s32CnROTe-gateFN3.08e-01_selective_to_all\MW.dat"}

__WAIT_SWITCH__ = 0.0
__IQ_MIXER__ = True
__TT_TRIGGER_LENGTH__ = 10*192/12e3

def nuclear_rabi(mcas, new_segment=False, **kwargs):
    type = 'robust' if 'wave_file' in kwargs else 'sine'
    if new_segment:
        mcas.start_new_segment(name='nuclear_rabi')
    if 'pd128m' in kwargs:
        raise Exception('Error!')
    pd = {}
    for awg_str, chl in mcas.ch_dict.items():
        for ch in chl:
            if 'pd' + awg_str + str(ch) in kwargs:
                pd['pd' + awg_str + str(ch)] = kwargs.pop('pd' + awg_str + str(ch), None)
    mcas.asc(pd128m1=dict(type=type, **kwargs), name=kwargs.get('name', 'rf'), **pd)

def electron_pi_and_rf_on(mcas, new_segment = False,iq_mixer=__IQ_MIXER__, **allkwargs):
    """
    Should be similar to electron rabi but with RF on....
    :param mcas:
    :param new_segment:
    :param kwargs:
    :return:
    """
    kwargs = allkwargs['d2g']
    rfkwargs = allkwargs['d128m']
    type_mw = 'robust' if 'wave_file' in kwargs else 'sine'
    type_rf = 'sine'
    if new_segment:
        mcas.start_new_segment(name='Electron Rabi with RF')
    pd = {}
    for awg_str, chl in mcas.ch_dict.items():
        for ch in chl:
            if 'pd' + awg_str + str(ch) in kwargs:
                pd['pd' + awg_str + str(ch)] = kwargs.pop('pd' + awg_str + str(ch), None)
    if kwargs['mixer_deg'] is None:
        raise Exception('Error: mixer_deg must be given.')
    elif isinstance(kwargs['mixer_deg'], (list, np.ndarray)):
        if len(kwargs['mixer_deg']) != len(kwargs['frequencies']):
            raise Exception
        else:
            mixer_deg = np.array(kwargs['mixer_deg'])
    elif isinstance(kwargs['mixer_deg'], (int, long, float, complex)):
        kwargs['mixer_deg'] = np.array([kwargs['mixer_deg']])
    else:
        raise Exception
    if 'phases' in kwargs:
        if isinstance(kwargs['phases'], (np.ndarray, list)):
            if len(kwargs['phases']) != len(kwargs['frequencies']):
                raise Exception
            kwargs['phases'] = np.array(kwargs['phases'])
        elif isinstance(kwargs['phases'], (int, long, float, complex)):
            kwargs['phases'] = np.array([kwargs['phases']])
    else:
        kwargs['phases'] = np.zeros(len(kwargs['frequencies']))
    ch_list = [1, 2] if iq_mixer else [1]
    pd2g = dict([(ch, dict(type=type_mw, **kwargs)) for ch in ch_list])
    if iq_mixer:
        pd2g[2]['phases'] = np.array(pd2g[2]['phases']) + kwargs['mixer_deg']
        pd2g[2]['smpl_marker'] = False
    pd128ml = dict(type=type_rf, **rfkwargs)
    mcas.asc(pd2g1=pd2g[1], pd2g2=pd2g[2],pd128m1=pd128ml, name=kwargs.get('name', 'mw+rf'), **pd)

def electron_rabi(mcas, name='e_rabi', iq_mixer=__IQ_MIXER__, mixer_deg=-90, new_segment=False, **kwargs):

    """
    :param transition: addressed transition in ODMR, i.e. 'left' or 'right', just like in TransitionTracker
    """
    if new_segment:
        mcas.start_new_segment(name='electron_rabi')
    type = 'robust' if 'wave_file' in kwargs else 'sine'
    if 'pd2g1' in kwargs or 'pd2g2' in kwargs:
        raise Exception('Error!')
    pd = {}
    for awg_str, chl in mcas.ch_dict.items():
        for ch in chl:
            if 'pd' + awg_str + str(ch) in kwargs:
                pd['pd' + awg_str + str(ch)] = kwargs.pop('pd' + awg_str + str(ch), None)
    if mixer_deg is None:
        raise Exception('Error: mixer_deg must be given.')
    elif isinstance(mixer_deg, (list, np.ndarray)):
        if len(mixer_deg) != len(kwargs['frequencies']):
            raise Exception
        else:
            mixer_deg = np.array(mixer_deg)
    elif isinstance(mixer_deg, (int, long, float, complex)):
        mixer_deg = np.array([mixer_deg])
    else:
        raise Exception
    if 'phases' in kwargs:
        if isinstance(kwargs['phases'], (np.ndarray, list)):
            if len(kwargs['phases']) != len(kwargs['frequencies']):
                raise Exception
            kwargs['phases'] = np.array(kwargs['phases'])
        elif isinstance(kwargs['phases'], (int, long, float, complex)):
            kwargs['phases'] = np.array([kwargs['phases']])
    else:
        kwargs['phases'] = np.zeros(len(kwargs['frequencies']))
    ch_list = [1, 2] if iq_mixer else [1]
    pd2g = dict([(ch, dict(type=type, **kwargs)) for ch in ch_list])
    if iq_mixer:
        pd2g[2]['phases'] = np.array(pd2g[2]['phases']) + mixer_deg
        pd2g[2]['smpl_marker'] = False
    mcas.asc(pd2g1=pd2g[1], pd2g2=pd2g[2], name=name, **pd)

def single_robust_electron_pi(mcas, nuc, **kwargs):
    if 'mixer_deg' in kwargs:
        raise Exception('Error: mixer_deg can not be set manually.')
    nuc = nuc.replace('14N', '14n').replace('13C', '13c')
    if nuc in ['14n+1', '14n-1', '14n', '13c414']:
        wave_file = WaveFile(filepath=__STANDARD_WAVEFILE__,
                             rp=pi3d.tt.rabi_parameters['e_rabi_ou{:.0f}deg-90'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000)],
                             scaling_factor=__WAVE_FILE_SCALING_FACTOR_DICT__[nuc])
        kwargs['wave_file'] = wave_file
        kwargs['mixer_deg'] = -90
    elif nuc == 'all': #flip electron independently of nuclear spin state
        max_rabi_file = 'e_rabi_ou{:.0f}deg-90'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000)
        # if pi3d.tt.rp(max_rabi_file, amp=1.0).omega > 15.:
        kwargs['length_mus'] = pi3d.tt.rp(max_rabi_file, amp=1.0).pi
        kwargs['amplitudes'] = [1.0]
        kwargs['mixer_deg'] = -90
        # else:
        #     wave_file = WaveFile(filepath='D:/Python/pi3diamond/UserScripts/Robust/test_pi_three_nitrogen/p4.dat',
        #                          rp=pi3d.tt.rabi_parameters['e_rabi_ou{:.0f}deg-90'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000)],
        #                          )
        #     kwargs['wave_file'] = wave_file
        #     kwargs['mixer_deg'] = -90
    else:
        raise Exception('Nuc does not exist!')
    electron_rabi(mcas, **kwargs)

def polarize_red(mcas, new_segment=False, length_mus=__T_POL_RED__, red_laserdelay =__RED_LASER__DELAY__, **kwargs):
    if new_segment:
        mcas.start_new_segment(name='polarize')
    pd = {}
    for awg_str, chl in mcas.ch_dict.items():
        for ch in chl:
            if 'pd' + awg_str + str(ch) in kwargs:
                if not awg_str in pd:
                    pd[awg_str] = {}
                pd[awg_str][ch] = kwargs.pop('pd' + awg_str + str(ch))
    mcas.asc(length_mus=length_mus, name='polarize', red=True, **pd)
    mcas.asc(length_mus=red_laserdelay, name='red_laserdelay', **pd)
    mcas.asc(length_mus=1.0, name='wait_cts', **pd)

def polarize_green(mcas, new_segment=False, length_mus=0.2, laser_delay=0.1, **kwargs):
    if new_segment:
        mcas.start_new_segment(name='polarize')
    pd = {}
    for awg_str, chl in mcas.ch_dict.items():
        for ch in chl:
            if 'pd' + awg_str + str(ch) in kwargs:
                if not awg_str in pd:
                    pd[awg_str] = {}
                pd[awg_str][ch] = kwargs.pop('pd' + awg_str + str(ch))
    mcas.asc(length_mus=length_mus, name='polarize', green=True, **pd)
    mcas.asc(length_mus=laser_delay, name='laserdelay', **pd)
    mcas.asc(length_mus=1.0, name='wait_cts', **pd)

polarize = polarize_red

def init_13c(mcas, s='90', state='left', new_segment=False, waitmwrf=0.5, rotation_angles=None, **pd):
    rotation_angles = [np.pi] if rotation_angles is None else rotation_angles
    if state in {'+', '-'}: #only true for ms-1
        state = {'-': 'left', '+': 'right'}[state]
    if new_segment:
        mcas.start_new_segment(name='init_13c' + s)
    polarize(mcas=mcas, new_segment=False, **pd)
    mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
    if s == '414':
        single_robust_electron_pi(
            mcas,
            nuc='13c{}'.format(s),
            frequencies=pi3d.tt.mfl("13c{}_{}".format(s, {'left': 'right', 'right': 'left'}[state])),
        )
        mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
    elif s == '90':
        period = 40.
        electron_rabi(mcas,
                      length_mus=0.5*period,
                      amplitudes=[pi3d.tt.rp('e_rabi_ou{:.0f}deg-90'.format(1000*pi3d.awgs['2g'].ch[1].output_amplitude), period=period).amp],
                      frequencies=pi3d.tt.mfl("13c{}_{}".format(s, {'left': 'right', 'right': 'left'}[state])),
                      new_segment=False,
                      mixer_deg=-90,
                      **pd
                      )
        mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
    else:
        raise Exception('Nuc does not exist!')
    transition = "13c{} mS-1".format(s)
    try:
        amp = pi3d.tt.rp(transition, period=100.).amp
    except:
        amp = 1.
    nuclear_rabi(mcas,
                 length_mus=pym8190a.elements.round_length_mus_full_sample(pi3d.tt.rp(transition, amp=amp).pi*rotation_angles[0]/np.pi),
                 amplitudes=[amp],
                 name=transition,
                 new_segment=False,
                 frequencies=[pi3d.tt.t(transition).current_frequency],
                 **pd)
    mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)

init_13C = init_13c

def init_14n(mcas, mn='+1', new_segment=False, waitmwrf=0.5, rotation_angles=None, **pd):
    rotation_angles = [np.pi, np.pi] if rotation_angles is None else rotation_angles
    if mn == '+':
        mn = '+1'
    if mn == '-':
        mn = '-1'
    if isinstance(mn, numbers.Number):
        mn = "{:+d}".format(mn)
    if mn == "+0":
        mn = "0"
    s = [
        dict(
            e={'+1': '0', '0': '0', '-1': '0'},
            n={'+1': '-1', '0': '-1', '-1': '+1'}
        ),
        dict(
            e={'+1': '+1', '0': '0', '-1': '-1'},
            n={'+1': '+1', '0': '+1', '-1': '-1'}
        )
    ]
    if new_segment:
        mcas.start_new_segment(name='init_14n' + mn)
    for idx, ss in enumerate(s):
        if rotation_angles[idx] > 0.0:
            polarize(mcas, new_segment=False, **pd)
            mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
            single_robust_electron_pi(mcas, frequencies=pi3d.tt.mfl({'14n': [int(ss['e'][mn])]}), nuc='14n', new_segment=False, **pd)
            mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
            try:
                amp = pi3d.tt.rp(transition, period=100.).amp
            except:
                amp = 1.0
            transition = '14n{} mS0'.format(ss['n'][mn])
            nuclear_rabi(mcas,
                         amplitudes=[amp],
                         length_mus=pym8190a.elements.round_length_mus_full_sample(pi3d.tt.rp(transition, amp=amp).pi*rotation_angles[idx]/np.pi),
                         name=transition,
                         frequencies=[pi3d.tt.t(transition).current_frequency],
                         new_segment=False,
                         **pd)
            mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)


init_14N = init_14n


def init(mcas, nuc, n=1, **kwargs):
    nuc = nuc.replace('14N', '14n').replace('13C', '13c')
    sms = sch.ret_sms(nuc=nuc)
    if '13c' in nuc:
        initf = init_13c
    elif '14n' in nuc:
        initf = init_14n
    else:
        raise Exception('Nuc {} not found'.format(nuc))
    for i in range(n):
        initf(mcas, sms['s'], **kwargs)


# def init_multiple(mcas, init_14n='not', init_13c414='not', init_13c90='not', ssr_repetitions=450, number_of_frequencies=1, **kwargs):
#     mn_14n = [+1, 0, -1] if init_14n is "not" else [int(init_14n)]
#     mn_13c414 = [+.5, -.5] if init_13c414 is "not" else [.5 * int("{}1".format(init_13c414))]
#     mn_13c90 = [+.5, -.5] if init_13c90 is "not" else [.5 * int("{}1".format(init_13c90))]
#     nuc = None
#     if init_13c90 != 'not':
#         nuc = '13c90'
#         init_13c(mcas, s='90', state=init_13c90, new_segment=True)
#         frequencies = pi3d.tt.mfl({'14N': mn_14n, '13c414': mn_13c414, '13c90': mn_13c90})
#     if init_13c414 != 'not':
#         init_13c(mcas, s='414', state=init_13c414, new_segment=True)
#         if nuc is None:
#             nuc = '13c414'
#             frequencies = pi3d.tt.mfl({'14N': mn_14n, '13c414': mn_13c414})
#     if init_14n != 'not':
#         init_14N(mcas, mn=init_14n, new_segment=True)
#         if nuc is None:
#             nuc = '14n'
#             frequencies = pi3d.tt.mfl({'14N': mn_14n})
#     if number_of_frequencies == 1:
#         ssr(mcas, frequencies=frequencies, nuc=nuc, robust=True, repetitions=ssr_repetitions, mixer_deg=-90, **kwargs)
#     elif number_of_frequencies == 2:
#         frequencies_not = pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5, -.5]})
#         frequencies_not = np.delete(frequencies_not, np.argwhere(frequencies_not == frequencies[0])[0, 0])
#         ssr(mcas, frequencies=[frequencies, frequencies_not], nuc='13c90', robust=True, repetitions=ssr_repetitions, mixer_deg=-90, **kwargs)

# def make_csd(mcas, ms='-1', mn='+1', e_amp=.05, robust=False):
#     mcas.start_new_segment(name='csd')
#     polarize(mcas)
#     frequencies = pi3d.tt.mfl({'14n': [int(mn)], '13c414': [-0.5], '13c90': [-0.5]})
#     if ms == '-1':
#         # electron pi to ms-1
#         if robust is True:
#             rpd = dict(wave_file='D:/data/Robust_Pulses/Pi-20130222T131525_YaWang.dat',
#                        er2d=TransitionTracker.ElectronRabi2d(lr='left'),
#                        wave_file_nonlinear_rabi=True)
#             mcas.asc(wos='wave', name='robust_pi', pd2g1=dict(frequencies=frequencies, type='robust', rpd=rpd))
#         else:
#             # amp = 0.05  # nuclei are initialized, high power does no harm
#             # amp = 0.2
#             electron_rabi(mcas, wos='wave', frequencies=frequencies, amplitudes=[e_amp], length_mus=pi3d.tt.rp('e_rabi_left', amp=e_amp).pi)
#     # nuclear pi on 14n
#     transition = "14n{} mS{}".format(mn, ms)
#     amp_t = pi3d.tt.rp(transition, period=100.).amp
#     amp = amp_t if amp_t <= 1.0 else 1.0
#     nuclear_rabi(mcas,
#                  name=transition,
#                  amplitudes=[amp],
#                  frequencies=[pi3d.tt.t(transition).current_frequency],
#                  length_mus=pi3d.tt.rp(transition, amp=amp).pi
#                  )


class SSR(object):

    __ALTERNATING_REPETITIONS__ = 1
    __LENGTH_MUS_FINAL_WAIT__ = 0.1
    __TRANSITION__ = 'left'
    __ADVANCE_MODE__ = 'AUTO'
    __ROBUST__ = False
    __GATE_OR_TRIGGER__ = 'trigger'
    # __WAIT_DARK_COUNTS__ = 10*192 #5*1920

    def __init__(self, mcas, frequencies, wait_dur=1., **kwargs):
        super(SSR, self).__init__()

        if 'nuc' in kwargs and kwargs['nuc'] is not None:
            kwargs['nuc'] = kwargs['nuc'].replace('14N', '14n').replace('13C', '13c')

        self.mcas = mcas
        self.frequencies = frequencies

        self.gate_or_trigger = kwargs.get('gate_or_trigger', self.__GATE_OR_TRIGGER__)
        self.set_laser_dur(kwargs)
        self.iq_mixer = kwargs.get('iq_mixer', __IQ_MIXER__)
        self.set_transition(kwargs)
        self.wait_dur = wait_dur
        self.check_kwargs_validity(kwargs)
        self.set_mixer_deg(kwargs)
        self.set_rp(kwargs)
        self.set_robust(kwargs)
        self.set_wave_file_kwargs(kwargs)
        self.set_length_mus_mw(kwargs)
        self.set_repetitions(kwargs)
        self.set_name(kwargs)
        self.set_amplitudes(kwargs)
        self.advance_mode = kwargs.get('advance_mode', self.__ADVANCE_MODE__)
        self.set_final_wait(kwargs)
        self.set_dur_step()
        self.kwargs = kwargs

    laser_dur = misc.ret_property_typecheck('laser_dur', float)
    wait_dur = misc.ret_property_typecheck('wait_dur', float)
    rabi_file = misc.ret_property_typecheck('rabi_file', str)

    def check_kwargs_validity(self, kwargs):
        if 'robust' in  kwargs and kwargs['robust']:
            if ('length_mus_mw' in kwargs or 'amplitudes' in kwargs):
                raise Exception("When 'robust' is True, neither 'length_mus_mw' nor 'amplitudes' must be given.")
        elif 'wave_file' in kwargs:
                raise Exception("'wave_file' is not None but 'robust' is False")
        if 'amplitudes' in kwargs and 'rabi_file' in kwargs:
            raise Exception("Either parameter 'amplitudes' or give parameter 'rabi_file' can be given.")
        if not 'nuc' in kwargs and not 'repetitions' in kwargs:
            raise Exception("At least one out of parameters ['nuc','repetitions'] must be given.")

    @property
    def frequencies(self):
        return self._frequencies

    @frequencies.setter
    def frequencies(self, val):
        if type(val) in [list, np.ndarray]:
            for i in val:
                if all([isinstance(i, numbers.Number) for i in val]):
                    self._frequencies = [val]
                elif all([isinstance(i, list) or isinstance(i, np.ndarray)]):
                    self._frequencies = val
                else:
                    raise Exception('SSR._frequencies must be a list of (list, numpy.ndarray) of numbers. If you pass a (list, np.ndarray) of numbers. this will be converted.')
        else:
            raise Exception('frequencies must be an numpy array or a list.')

    @property
    def number_of_alternating_steps(self):
        return len(self.frequencies)

    def set_robust(self, kwargs):
        self.robust = kwargs.get('robust', self.__ROBUST__)
        if kwargs.get('nuc', None) == '13c90' and self.robust and not 'wave_file_kwargs' in kwargs:
            self.robust = False

    def set_mixer_deg(self, kwargs):
        if 'mixer_deg' not in kwargs:
            raise Exception('Error: mixer_deg must be given.')
        self.mixer_deg = kwargs['mixer_deg']

    def set_laser_dur(self, kwargs):
        if 'laser_dur' in kwargs:
            self.laser_dur = kwargs['laser_dur']
        else:
            self.laser_dur = __LASER_DUR_DICT__[kwargs['nuc']]

    def set_rp(self, kwargs):
        if 'rp' in kwargs:
            self.rp = kwargs['rp']
        elif 'mixer_deg' in kwargs:
            self.rp = pi3d.tt.rabi_parameters['e_rabi_ou{:.0f}deg{}'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000, self.mixer_deg)]
        else:
            raise Exception('TransitionTracker.RabiParametersStatic or mixer_deg instance must be given.')

    def set_wave_file_kwargs(self, kwargs):
        if self.robust:
            if 'wave_file_kwargs' in kwargs:
                if isinstance(kwargs['wave_file_kwargs'], list) and len(kwargs['wave_file_kwargs']) == self.number_of_alternating_steps:
                    self.wave_file_kwargs = kwargs['wave_file_kwargs']
                elif self.number_of_alternating_steps == 1 and isinstance(kwargs['wave_file_kwargs'], dict):
                    self.wave_file_kwargs = [kwargs['wave_file_kwargs']]
                else:
                    raise Exception('Error: {}'.format(kwargs))
            else:
                fp = kwargs.get('wave_file_filepath', __STANDARD_WAVEFILE__)
                if 'nuc' in kwargs:
                    sf = __WAVE_FILE_SCALING_FACTOR_DICT__[kwargs['nuc']]
                else:
                    sf = kwargs.get('wave_file_scaling_factor', 1.0)
                self.wave_file_kwargs = [dict(filepath=fp, rp=self.rp, scaling_factor=sf) for i in range(self.number_of_alternating_steps)]
            self.wave_file = [WaveFile(**i) for i in self.wave_file_kwargs]

    def set_length_mus_mw(self, kwargs):
        if self.robust:
            self.length_mus_mw = [self.wave_file[n].length_mus for n in range(self.number_of_alternating_steps)]
            self.mw_step_length_mus = [self.wave_file[n].step_length_mus for n in range(self.number_of_alternating_steps)]
        else:
            self.length_mus_mw = kwargs['length_mus_mw'] if 'length_mus_mw' in kwargs else [__PERIODS__[kwargs['nuc']]/2.]*self.number_of_alternating_steps
            if not hasattr(self.length_mus_mw, '__iter__'):
                self.length_mus_mw = [self.length_mus_mw]*self.number_of_alternating_steps
            if len(self.length_mus_mw) != self.number_of_alternating_steps:
                raise Exception('Wrong number of length_mus_mw. Allowed is 1 or number_of_alternating_steps')

    @property
    def alternating(self):
        return True if self.number_of_alternating_steps > 1 else False

    def set_repetitions(self, kwargs):
        r = kwargs['repetitions'] if 'repetitions' in kwargs else __SSR_REPETITIONS__[kwargs['nuc']]
        if int(r) != r:
            raise Exception('repetititons is not an integer')
        if self.alternating:
            if r%self.number_of_alternating_steps != 0:
                raise Exception('Repetitions must be divisible by number_of_alternating_steps.', kwargs['repetitions'], self.number_of_alternating_steps)
            else:
                self.repetitions = int(r/self.number_of_alternating_steps)
        else:
            self.repetitions = r
        if self.repetitions == 0:
            print('Something went wrong with your ssr repetitions! {}'.format(self.repetitions))

    def set_name(self, kwargs):
        if 'name' in kwargs:
            self.name = kwargs['name']
        elif 'nuc' in kwargs:
            self.name = 'ssr' + kwargs['nuc']
        else:
            self.name = 'ssrt{}'.format("t".join("{:.2f}".format(i) for i in self.length_mus_mw))

    def set_amplitudes(self, kwargs):
        if not self.robust:
            if 'amplitudes' in kwargs:
                raise NotImplementedError
            if any(np.array(self.length_mus_mw) == 0): # Implemented here in order to charge state control
                self.amplitudes = [[0] for i in self.length_mus_mw]
            else:
                self.amplitudes = [self.rp.amplitude(tni={'left': [0], 'right': [1]}[self.transition], period=[2*i]) for i in self.length_mus_mw]

    def set_transition(self, kwargs):
        t = kwargs.get('transition', self.__TRANSITION__).replace('14N', '14n').replace('13C', '13c').replace('mS', 'ms')
        if t not in ['left', 'right']:
            raise Exception('Error {}, {}'.format(t, kwargs['transition']))
        self.transition = t

    def set_final_wait(self, kwargs):
        self.final_wait = kwargs.get('final_wait', 0.1)
        if self.final_wait == 0.0 and self.alternating:
            raise Exception("When alternating is True, final_wait must not be False. (I AM NOT SURE IF THIS IS TRUE FOR TIMETAGGER AS COUNTER)")

    def set_dur_step(self):
        self.dur_step = [
            {
             2: self.length_mus_mw[n],
             5: self.laser_dur,
             6: self.wait_dur} for n in range(self.number_of_alternating_steps)]

    def part_step(self, n):
        t = np.cumsum([0.0, self.dur_step[n][2]])
        return {
            2: self.wave_file[n].ret_part(t[0], t[1]),
        }


    def pd2g_dict(self, n):
        if n > len(self.frequencies) - 1:
            raise Exception('Not enough frequencies given.')

        pd2g_dict = {1: {}, 2: {}}
        for ch in [1, 2]:
            # for i in [2, 3, 4]:
            for i in [2]:
                pd2g_dict[ch][i] = {}
                if ch == 2 and not self.iq_mixer:
                    continue
                pd2g_dict[ch][i]['frequencies'] = self.frequencies[n]
                if self.robust:
                    pd2g_dict[ch][i].update(dict(type='robust', wave_file=WaveFile(part=self.part_step(n)[i], **self.wave_file_kwargs[n])))
                else:
                    pd2g_dict[ch][i].update(dict(type='sine', amplitudes=self.amplitudes[n], length_mus=self.dur_step[n][i]))
                if ch == 2 and self.iq_mixer:
                    pd2g_dict[ch][i]['phases'] = np.array([self.mixer_deg])
                else:
                    pd2g_dict[2][i] = {}
                # if ch == 1 and self.wait_switch > 0:
                #     pd2g_dict[ch][i]['smpl_marker'] = True
        return pd2g_dict

    def compile(self):
        aa = dict()
        if self.repetitions != 0:
            self.mcas.start_new_segment(name=self.name, loop_count=self.repetitions, advance_mode=self.advance_mode)
            for alt_step in range(self.number_of_alternating_steps):
                d = self.pd2g_dict(alt_step)
                self.mcas.asc(pd2g1=d[1][2], pd2g2=d[2][2], name='MW', **aa)
                if self.gate_or_trigger == 'trigger':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True)
                else:
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True)

                if 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'charge_state':
                    self.mcas.asc(length_mus=self.dur_step[alt_step][5], orange=True, name='Orange_Laser', **aa)
                else:
                    self.mcas.asc(length_mus=self.dur_step[alt_step][5], green=True, name='Laser', **aa)

                self.mcas.asc(length_mus=self.dur_step[alt_step][6], name='Count', **aa)
                if self.gate_or_trigger == 'trigger':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True)

def ssr(mcas, **kwargs):
    s = SSR(mcas, **kwargs)
    s.compile()
    if not 'step_idx' in kwargs:
        raise Exception('SSR step index must be given, or the gated counter wont know how to readout and treat the data.')
    if kwargs['step_idx'] is not None:
        pi3d.gated_counter.trace.analyze_sequence[kwargs['step_idx']][3] = s.repetitions * s.number_of_alternating_steps
        pi3d.gated_counter.trace.analyze_sequence[kwargs['step_idx']][5] = s.number_of_alternating_steps
        if pi3d.gated_counter.trace.analyze_sequence[kwargs['step_idx']][5] != 1 and pi3d.gated_counter.trace.analyze_sequence[kwargs['step_idx']][2] == 'auto':
            pi3d.gated_counter.trace.analyze_sequence[kwargs['step_idx']][2] = 0

wfpd_standard = collections.OrderedDict(
    [
        ('+++',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h01m45s17crot10_20_30_t10.00n80FN5.32e-01\\MW.dat'),
        ('++-',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h02m45s50crot10_20_31_t10.00n80FN5.29e-01\\MW.dat'),
        ('+-+',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h03m46s26crot10_21_30_t10.00n80FN5.11e-01\\MW.dat'),
        ('+--',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h04m46s59crot10_21_31_t10.00n80FN5.26e-01\\MW.dat'),
        ('0++',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h05m47s31crot11_20_30_t10.00n80FN5.26e-01\\MW.dat'),
        ('0+-',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h06m48s06crot11_20_31_t10.00n80FN5.13e-01\\MW.dat'),
        ('0-+',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h07m48s50crot11_21_30_t10.00n80FN5.21e-01\\MW.dat'),
        ('0--',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h08m49s23crot11_21_31_t10.00n80FN5.38e-01\\MW.dat'),
        ('-++',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h09m49s58crot12_20_30_t10.00n80FN5.15e-01\\MW.dat'),
        ('-+-',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h10m50s29crot12_20_31_t10.00n80FN5.11e-01\\MW.dat'),
        ('--+',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h11m50s58crot12_21_30_t10.00n80FN5.23e-01\\MW.dat'),
        ('---',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h12m51s29crot12_21_31_t10.00n80FN5.33e-01\\MW.dat'),
        ('nn+',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h14m18s27crot1012_201_30_t10.00n100FN1.24e+00\\MW.dat'),
        ('+',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h14m41s19crot10_t1.00n100FN6.57e-02\\MW.dat'),
        ('n+',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h14m43s07crot1012_20_t2.50n100FN7.63e-01\\MW.dat'),
        ('nn-',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h14m49s43crot1012_201_31_t10.00n100FN1.24e+00\\MW.dat'),
        ('n-',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h15m43s39crot1012_21_t2.50n100FN7.75e-01\\MW.dat'),
        ('0',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h19m13s56crot11_t1.00n100FN7.75e-02\\MW.dat'),
        ('-',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h21m14s57crot12_t1.00n100FN5.70e-02\\MW.dat')
    ]
)

wfpd_all_but_standard = collections.OrderedDict(
    [
        ('+++',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h01m45s11crotall_but10_20_30_t10.00n80FN5.10e-01\\MW.dat'),
        ('++-',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h02m45s47crotall_but10_20_31_t10.00n80FN5.10e-01\\MW.dat'),
        ('+-+',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h03m46s19crotall_but10_21_30_t10.00n80FN5.09e-01\\MW.dat'),
        ('+--',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h04m46s54crotall_but10_21_31_t10.00n80FN5.09e-01\\MW.dat'),
        ('0++',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h05m47s27crotall_but11_20_30_t10.00n80FN5.11e-01\\MW.dat'),
        ('0+-',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h06m48s04crotall_but11_20_31_t10.00n80FN5.10e-01\\MW.dat'),
        ('0-+',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h07m48s36crotall_but11_21_30_t10.00n80FN5.10e-01\\MW.dat'),
        ('0--',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h08m49s05crotall_but11_21_31_t10.00n80FN5.10e-01\\MW.dat'),
        ('-++',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h09m49s33crotall_but12_20_30_t10.00n80FN5.09e-01\\MW.dat'),
        ('-+-',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h10m49s59crotall_but12_20_31_t10.00n80FN5.09e-01\\MW.dat'),
        ('--+',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h11m50s26crotall_but12_21_30_t10.00n80FN5.09e-01\\MW.dat'),
        ('---',
        '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssrn80\\20180825-h12m50s55crotall_but12_21_31_t10.00n80FN5.10e-01\\MW.dat'),
        ('+',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h15m41s54crotall_but10_t1.00n100FN3.81e-02\\MW.dat'),
        ('0',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h20m14s30crotall_but11_t1.00n100FN7.12e-02\\MW.dat'),
        ('-',
         '\\\\PI3-PC161\\d\\Python\\pi3diamond\\UserScripts\\Robust\\pulses_ssr\\pulses_ssr_single_spin\\batch3\\20180902-h21m52s06crotall_but12_t1.00n100FN5.34e-02\\MW.dat')
    ]
)

def ssr_single_state(mcas, state, **kwargs):
    if (len(state) == 1 and state !='qutrit') or len(state) == len(state.lstrip('n')) == 3:
        wave_file_kwargs = kwargs.pop(
            'wave_file_kwargs',
            [
                dict(
                    filepath=kwargs.get('wfpd', wfpd_standard)[state],
                    rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)
                ),
                dict(
                    filepath=kwargs.get('wfpd_all_but', wfpd_all_but_standard)[state],
                    rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)
                ),
            ]
        )
        if (len(state) == 1 and state !='qutrit'):
            nuc = '14n'
        else:
            nuc = '13c90'
    else:
        if state == 'qutrit':
            nuc = '14n'
            wfksl = ['+', '0', '-']
        else:
            nuc = '13c414' if len(state) == 2 else '13c90'
            wfksl = [state.lstrip('n')]
            wfksl.append({'+': '-', '-': '+'}[wfksl[0]])
        if 'wave_file_kwargs' in kwargs:
            wave_file_kwargs = kwargs.pop('wave_file_kwargs')
        else:
            wave_file_kwargs =[
                dict(
                    filepath=kwargs.get('wfpd', wfpd_standard)[wfks],
                    rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)
                ) for wfks in wfksl]
    ssr(mcas,
        transition='left',
        robust=True,
        laser_dur=kwargs.pop('laser_dur', __LASER_DUR_DICT__.get(state, __LASER_DUR_DICT__['single_state'])),
        mixer_deg=-90,
        nuc=kwargs.pop('nuc', nuc),
        frequencies=kwargs.pop('frequencies', [pi3d.tt.mfl({'14n': [0]}) for i in range(len(wave_file_kwargs))]),
        wave_file_kwargs=wave_file_kwargs, **kwargs
    )