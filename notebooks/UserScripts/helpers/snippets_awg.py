from __future__ import print_function, absolute_import, division
from imp import reload
import importlib
import hardware.Keysight_AWG_M8190.pym8190a as MCAS; importlib.reload(MCAS)
import notebooks.UserScripts.helpers.sequence_creation_helpers as sch; importlib.reload(sch)

from traits.api import *
import numpy as np
from decimal import Decimal
import copy
import traceback
import sys
import hardware.Keysight_AWG_M8190.elements as E

import logic.misc as misc
#from pi3diamond import pi3d
from hardware.Keysight_AWG_M8190.elements import WaveFile, WaveStep, SequenceStep, Sequence
import hardware.Keysight_AWG_M8190.pym8190a as pym8190a
import numbers
#import TransitionTracker
import collections

__CURRENT_POL_RED__ = 76
__T_POL_RED__ = 0.2
__RED_LASER__DELAY__ = 0.1
__SSR_REPETITIONS__ = {'14n+1': 1500, '14n-1': 1500, '14n': 1500, '14n0': 1200, '13c414': 1500, '13c90': 2000,
                       'charge_state':1,'charge_state_A1_aom_Ex':1,'charge_state_ExMW':1, 'ple_A2': 1,'ple_A1': 1,'Ex_pi_readout':1,'Ex_pi_readout_6ns':1,
                       'Ex_ampl_sweep_SSR' : 1,
                       'opt_mw_delays_calibration':1,
                       'opt_mw_delays_calibration2': 1,
                        '2_opt_mw_delays_calibration':1,
                       'Ex_RO':1,
                        '2opt_withMW_pi':1,
                       'entanglement_for_tests':1,
                        'HOM':1,
                        'entanglement':1,
                       'Ex_ampl_sweep_SSR_6ns' :10,
                       'Ex_pi_readout_10ns':10}
__LASER_DUR_DICT__ = {'14n+1': .175, '14n-1': .175, '14n': .175, '14n0': .9, '13c414': .9, '13c90': .21,
                      'single_state': .9, 'charge_state': 2000.0,'charge_state_ExMW': 2000.0,'charge_state_A1_aom_Ex':2000.0, 'ple_A2': 50.0,'ple_A1': 50.,
                      'Ex_pi_readout_6ns' : 481*3/12.0e3, # (Len in samples / sampling rate)
                      'Ex_ampl_sweep_SSR' : 481*1/12e3,
                      'opt_mw_delays_calibration': 481*1/12e3,
                      'opt_mw_delays_calibration2': 481 * 1 / 12e3,
                    '2_opt_mw_delays_calibration': 481 * 1 / 12e3,
                      'Ex_RO': 5.0,
                      '2opt_withMW_pi':481*1/12e3,
                      'entanglement_for_tests':481*1/12e3,
                        'HOM':481*1/12e3,
                      'entanglement':481*1/12e3,
                      'Ex_ampl_sweep_SSR_6ns' : 481*3/12e3,
                      'Ex_pi_readout_10ns' : 481*5/12.0e3,
                        'Ex_pi_readout' : 481/12.0e3 # (Len in samples / sampling rate)
                      } # us
__PERIODS__ = {'14n+1': 1.6, '14n-1': 1.6, '14n': 1.6, '14n0': 1.6, '13c414': 6.0, '13c90': 20., 'charge_state': 0.0,'charge_state_A1_aom_Ex': 0.0,
               'charge_state_ExMW': 0.0,'ple_A2': 0.0,'ple_A1': 0.0,'Ex_pi_readout':0.0,'Ex_pi_readout_6ns':0.0,'Ex_ampl_sweep_SSR' :0.0,
               'Ex_ampl_sweep_SSR_6ns' :0.0, 'Ex_pi_readout_10ns':0.0,'opt_mw_delays_calibration':0.0,
               'opt_mw_delays_calibration2':0.0,'2_opt_mw_delays_calibration':0.0,'Ex_RO':0.0,
               '2opt_withMW_pi':0.0,'entanglement':0.0,'entanglement_for_tests':0.0,'HOM':0.0}
__WAVE_FILE_SCALING_FACTOR_DICT__ = {'14n+1': 2.5, '14n-1': 2.5, '14n': 2.5, '14n0': 2.5, '13c414': 1.0,'charge_state_A1_aom_Ex':1.0, 'charge_state': 1.0,'ple_A2': 1.0,'ple_A1': 0.0}
__STANDARD_WAVEFILE__ = 'D:\data\Robust_Pulses\single_pulse_ON03_OFF05_Rabi10_02.dat'
__STANDARD_WAVEFILES__ = {'14n+1': r"D:\data\NuclearOPs\Robust\test_pi_three_nitrogen\20171204-h18m52s32CnROTe-gateFN3.08e-01_selective_to_all\MW.dat"}

__WAIT_SWITCH__ = 0.0
__IQ_MIXER__ = False
__TT_TRIGGER_LENGTH__ = 10*192/12e3
__SAMPLE_FREQUENCY__ = 12e3
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
    elif isinstance(kwargs['mixer_deg'], (int, float, complex)):
        kwargs['mixer_deg'] = np.array([kwargs['mixer_deg']])
    else:
        raise Exception
    if 'phases' in kwargs:
        if isinstance(kwargs['phases'], (np.ndarray, list)):
            if len(kwargs['phases']) != len(kwargs['frequencies']):
                raise Exception
            kwargs['phases'] = np.array(kwargs['phases'])
        elif isinstance(kwargs['phases'], (int, float, complex)):
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
    else:
        mcas.asc(pd2g1=pd2g[1], name=kwargs.get('name', 'mw+rf'), **pd)

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
    elif isinstance(mixer_deg, (int, int, float, complex)):
        mixer_deg = np.array([mixer_deg])
    else:
        raise Exception

    if 'phases' in kwargs:
        if isinstance(kwargs['phases'], (np.ndarray, list)):
            if len(kwargs['phases']) != len(kwargs['frequencies']):
                raise Exception
            kwargs['phases'] = np.array(kwargs['phases'])
        elif isinstance(kwargs['phases'], (int, int, float, complex)):
            kwargs['phases'] = np.array([kwargs['phases']])
    else:
        kwargs['phases'] = np.zeros(len(kwargs['frequencies']))
    ch_list = [1, 2] if iq_mixer else [1]
    pd2g = dict([(ch, dict(type=type, **kwargs)) for ch in ch_list])
    if iq_mixer:
        pd2g[2]['phases'] = np.array(pd2g[2]['phases']) + mixer_deg
        pd2g[2]['smpl_marker'] = False
        mcas.asc(pd2g1=pd2g[1], pd2g2=pd2g[2], name=name, **pd) #MW is set here
    else:
        mcas.asc(pd2g1=pd2g[1], name=name, **pd)

# def single_robust_electron_pi(mcas, nuc, **kwargs):
#     if 'mixer_deg' in kwargs:
#         raise Exception('Error: mixer_deg can not be set manually.')
#     nuc = nuc.replace('14N', '14n').replace('13C', '13c')
#     if nuc in ['14n+1', '14n-1', '14n', '13c414']:
#         wave_file = WaveFile(filepath=__STANDARD_WAVEFILE__,
#                              rp=pi3d.tt.rabi_parameters['e_rabi_ou{:.0f}deg-90'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000)],
#                              scaling_factor=__WAVE_FILE_SCALING_FACTOR_DICT__[nuc])
#         kwargs['wave_file'] = wave_file
#         kwargs['mixer_deg'] = -90
#     elif nuc == 'all': #flip electron independently of nuclear spin state
#         max_rabi_file = 'e_rabi_ou{:.0f}deg-90'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000)
#         # if pi3d.tt.rp(max_rabi_file, amp=1.0).omega > 15.:
#         kwargs['length_mus'] = pi3d.tt.rp(max_rabi_file, amp=1.0).pi
#         kwargs['amplitudes'] = [1.0]
#         kwargs['mixer_deg'] = -90
#         # else:
#         #     wave_file = WaveFile(filepath='D:/Python/pi3diamond/UserScripts/Robust/test_pi_three_nitrogen/p4.dat',
#         #                          rp=pi3d.tt.rabi_parameters['e_rabi_ou{:.0f}deg-90'.format(pi3d.awgs['2g'].ch[1].output_amplitude*1000)],
#         #                          )
#         #     kwargs['wave_file'] = wave_file
#         #     kwargs['mixer_deg'] = -90
#     else:
#         raise Exception('Nuc does not exist!')
#     electron_rabi(mcas, **kwargs)

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
    # print('Polarize Red New')
    mcas.asc(length_mus=length_mus, name='polarize', aom_A1=True, **pd)
    mcas.asc(length_mus=red_laserdelay, name='red_laserdelay', **pd)
    mcas.asc(length_mus=1.5, name='wait_cts', **pd)

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
    mcas.asc(length_mus=1.5, name='wait_cts', **pd)

polarize = polarize_red

# def init_13c(mcas, s='90', state='left', new_segment=False, waitmwrf=0.5, rotation_angles=None, **pd):
#     rotation_angles = [np.pi] if rotation_angles is None else rotation_angles
#     if state in {'+', '-'}: #only true for ms-1
#         state = {'-': 'left', '+': 'right'}[state]
#     if new_segment:
#         mcas.start_new_segment(name='init_13c' + s)
#     polarize(mcas=mcas, new_segment=False, **pd)
#     mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
#     if s == '414':
#         single_robust_electron_pi(
#             mcas,
#             nuc='13c{}'.format(s),
#             frequencies=pi3d.tt.mfl("13c{}_{}".format(s, {'left': 'right', 'right': 'left'}[state])),
#         )
#         mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
#     elif s == '90':
#         period = 40.
#         electron_rabi(mcas,
#                       length_mus=0.5*period,
#                       amplitudes=[pi3d.tt.rp('e_rabi_ou{:.0f}deg-90'.format(1000*pi3d.awgs['2g'].ch[1].output_amplitude), period=period).amp],
#                       frequencies=pi3d.tt.mfl("13c{}_{}".format(s, {'left': 'right', 'right': 'left'}[state])),
#                       new_segment=False,
#                       mixer_deg=-90,
#                       **pd
#                       )
#         mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
#     else:
#         raise Exception('Nuc does not exist!')
#     transition = "13c{} mS-1".format(s)
#     try:
#         amp = pi3d.tt.rp(transition, period=100.).amp
#     except:
#         amp = 1.
#     nuclear_rabi(mcas,
#                  length_mus=pym8190a.elements.round_length_mus_full_sample(pi3d.tt.rp(transition, amp=amp).pi*rotation_angles[0]/np.pi),
#                  amplitudes=[amp],
#                  name=transition,
#                  new_segment=False,
#                  frequencies=[pi3d.tt.t(transition).current_frequency],
#                  **pd)
#     mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)

# init_13C = init_13c

# def init_14n(mcas, mn='+1', new_segment=False, waitmwrf=0.5, rotation_angles=None, **pd):
#     rotation_angles = [np.pi, np.pi] if rotation_angles is None else rotation_angles
#     if mn == '+':
#         mn = '+1'
#     if mn == '-':
#         mn = '-1'
#     if isinstance(mn, numbers.Number):
#         mn = "{:+d}".format(mn)
#     if mn == "+0":
#         mn = "0"
#     s = [
#         dict(
#             e={'+1': '0', '0': '0', '-1': '0'},
#             n={'+1': '-1', '0': '-1', '-1': '+1'}
#         ),
#         dict(
#             e={'+1': '+1', '0': '0', '-1': '-1'},
#             n={'+1': '+1', '0': '+1', '-1': '-1'}
#         )
#     ]
#     if new_segment:
#         mcas.start_new_segment(name='init_14n' + mn)
#     for idx, ss in enumerate(s):
#         if rotation_angles[idx] > 0.0:
#             polarize(mcas, new_segment=False, **pd)
#             mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
#             single_robust_electron_pi(mcas, frequencies=pi3d.tt.mfl({'14n': [int(ss['e'][mn])]}), nuc='14n', new_segment=False, **pd)
#             mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)
#             try:
#                 amp = pi3d.tt.rp(transition, period=100.).amp
#             except:
#                 amp = 1.0
#             transition = '14n{} mS0'.format(ss['n'][mn])
#             nuclear_rabi(mcas,
#                          amplitudes=[amp],
#                          length_mus=pym8190a.elements.round_length_mus_full_sample(pi3d.tt.rp(transition, amp=amp).pi*rotation_angles[idx]/np.pi),
#                          name=transition,
#                          frequencies=[pi3d.tt.t(transition).current_frequency],
#                          new_segment=False,
#                          **pd)
#             mcas.asc(length_mus=waitmwrf, name='waitmwrf', **pd)


# init_14N = init_14n


# def init(mcas, nuc, n=1, **kwargs):
#     nuc = nuc.replace('14N', '14n').replace('13C', '13c')
#     sms = sch.ret_sms(nuc=nuc)
#     if '13c' in nuc:
#         initf = init_13c
#     elif '14n' in nuc:
#         initf = init_14n
#     else:
#         raise Exception('Nuc {} not found'.format(nuc))
#     for i in range(n):
#         initf(mcas, sms['s'], **kwargs)


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

    def __init__(self, mcas, queue, frequencies, wait_dur=1., **kwargs):
        super(SSR, self).__init__()

        if 'nuc' in kwargs and kwargs['nuc'] is not None:
            kwargs['nuc'] = kwargs['nuc'].replace('14N', '14n').replace('13C', '13c')
        self.queue = queue
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
            if 'ms_transition' in kwargs.keys():
                ms_transition = {'right': 'R', 'left': 'L'}[kwargs['ms_transition']]
            else:
                ms_transition = 'L'

            self.rp = self.queue.tt.rabi_parameters['e_rabi_ou{:.0f}deg{}-{}'.format(
                self.queue._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude*1000, #TODO
                self.mixer_deg,
                ms_transition
            )]
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
            if 'pi_pulse_factor' in kwargs:
                self.length_mus_mw *= kwargs['pi_pulse_factor']
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
                self.amplitudes = [[kwargs['amplitudes']] for i in self.length_mus_mw]

            else:# 'amplitudes' not in kwargs or None in np.array(self.amplitudes).flatten():
                if any(np.array(self.length_mus_mw) == 0): # Implemented here in order to charge state control
                    self.amplitudes = [[0] for i in self.length_mus_mw]
                else:
                    # self.amplitudes = [self.rp.amplitude(tni={'left': [0], 'right': [1]}[self.transition], period=[2*i]) for i in self.length_mus_mw]
                    # Right or left transition has already been taken into account by chosing proper self.rp initialization file
                    self.amplitudes = [self.rp.amplitude(tni=[0], period=[2*i]) for i in self.length_mus_mw]

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
        optical = False
        optical = ('nuc' in self.kwargs.keys()) and (self.kwargs['nuc'] in [
                        'charge_state',
                        'ple_A2',
                        'ple_A1',
                        # 'Ex_pi_readout_6ns',
                        # 'Ex_ampl_sweep_SSR',
                        # 'opt_mw_delays_calibration',
                        # 'opt_mw_delays_calibration2',
                        # '2_opt_mw_delays_calibration',

                        # '2opt_withMW_pi',
                        # 'entanglement_for_tests',
                        # 'HOM',
                        # 'entanglement',
                        # 'Ex_ampl_sweep_SSR_6ns',
                        # 'Ex_pi_readout_10ns' ,
                        # 'Ex_pi_readout'
                          ])
        if optical:
            self.compileOptical()
        else:
            self.compileMW()

    def compileMW(self):
        # print('compileMW in snippets_awg')
        aa = dict()
        if self.repetitions != 0:
            self.mcas.start_new_segment(name=self.name,
                                        loop_count=self.repetitions,
                                        advance_mode=self.advance_mode)

            if self.number_of_alternating_steps!= 1:
                raise Warning('most probably something is wrong with PulseStreamer - AWG syncronization')
            for alt_step in range(self.number_of_alternating_steps):
                d = self.pd2g_dict(alt_step)
                if 'cw_mw' in self.kwargs.keys():
                    laser = self.kwargs['cw_mw']
                else:
                    laser = False

                if self.gate_or_trigger == 'trigger':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name = 'triggerTrue_gate') # Gated counter
                else:
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name = 'triggerFalse_memory') # ODMR... ORABI
                    self.mcas.asc(length_mus=2.1, name = 'wait_after_memory')

                self.mcas.asc(pd2g1=d[1][2], pd2g2=d[2][2], name='MW', green=laser, **aa)
                ### ===============================
                ### Conventional repetitive readout
                ### ===============================
                self.mcas.asc(length_mus=self.dur_step[alt_step][5], green=True, name='Laser', **aa)
                self.mcas.asc(length_mus=self.dur_step[alt_step][6], name='Count', **aa)
                if self.gate_or_trigger == 'trigger':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'triggerTrue2_memory')
                if 'buffer_time' in self.kwargs.keys():
                    self.mcas.asc(length_mus=self.kwargs['buffer_time'], name = 'Buffer')

        # print('compileMW finished')

    def compileOptical(self):
        # print('compileOptical in snippets_awg')
        aa = dict()
        if self.repetitions != 0:
            if 'no_new_segment' in self.kwargs.keys():
                pass

            else:
                self.mcas.start_new_segment(name=self.name,
                                            loop_count=self.repetitions,
                                            advance_mode=self.advance_mode)

            for alt_step in range(self.number_of_alternating_steps):
                d = self.pd2g_dict(alt_step)

                # if self.gate_or_trigger == 'trigger':
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,name = 'gate1') # Gated counter
                # elif self.gate_or_trigger == 'gate_after_pulse':
                #     pass    # Correlation
                # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter

                if 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'charge_state':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter

                    #EOM on
                    # pd2g2 = dict(type='sine',
                    #              frequencies=[self.queue.ple_Ex.eom_freq],
                    #              amplitudes=[0.0],
                    #              )

                    self.mcas.asc(length_mus=self.dur_step[alt_step][5],
                                  A1=True, A2=True,
                                  name='State_check', **aa)

                    self.mcas.asc(length_mus=2.0,name = 'wait')
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')


                elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'ple_A2':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                    self.mcas.asc(A2=True, length_mus=self.dur_step[alt_step][5], name = 'ple_A2_readout')
                    self.mcas.asc(length_mus=1.0,name = 'wait')
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')

                elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'ple_A1':
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                    self.mcas.asc(A1=True, length_mus=self.dur_step[alt_step][5], name = 'ple_A1_readout')
                    self.mcas.asc(length_mus=1.0,name = 'wait')
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')

                    # delta+=self.dur_step[alt_step][5]
                #
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'Ex_pi_readout_6ns':
                #     # print('snipets were updated')
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #     for i in range(1):
                #         self.mcas.asc(length_mus=0.02, aom_Ex=True)
                #         self.mcas.asc(length_mus=0.145)
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss_6ns',
                #                 inv_fwhm=1,
                #                 amplitudes=[1.0]),
                #             # aom_Ex = True,
                #             # gate = True,
                #             # memory = True,
                #             length_smpl=481 * 3,
                #         )
                #         if i == 0:
                #             g=True
                #         else:
                #             g=False
                #         self.mcas.asc(gate=g, memory=False, length_mus=0.1)
                #         # mcas.asc(length_mus=0.550, aom_Ex=True)
                #         self.mcas.asc(length_mus=0.05)
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True)
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'Ex_pi_readout_10ns':
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #     # print('snipets were updated')
                #     self.mcas.asc(length_mus=0.050, aom_Ex=True)
                #     self.mcas.asc(length_mus=0.15)
                #     self.mcas.asc(
                #         name='Ex_pi_readout_10ns',
                #         pd2g2=dict(
                #             type='gauss_6ns',
                #             inv_fwhm=1,
                #             amplitudes=[1.0],
                #         ),
                #         length_smpl=481*5,
                #         **aa
                #     )
                #     self.mcas.asc(length_mus=1.0)
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'Ex_pi_readout':
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #     # print('snipets were updated')
                #     for i in range(10): # why we have here 10 iterations??
                #         self.mcas.asc(length_mus=0.050, aom_Ex=True)
                #         self.mcas.asc(length_mus=0.15)
                #         self.mcas.asc(
                #             name='Ex_pi_readout',
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[1.0],
                #             ),
                #             length_smpl=481,
                #             **aa
                #         )
                #         self.mcas.asc(length_mus=1.0)
                #
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True)
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'Ex_ampl_sweep_SSR_6ns':
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #     # print('snipets were updated')
                #     self.mcas.asc(length_mus=0.09, aom_Ex=True)
                #     self.mcas.asc(length_mus=0.08, name='aom_delay')
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss_6ns',
                #             inv_fwhm=1,
                #             amplitudes=[self.kwargs['eom_ampl']]),
                #         length_mus=481 * 3. / __SAMPLE_FREQUENCY__,
                #         name='Gauss')
                #
                #     self.mcas.asc(length_mus=1.0)
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True)
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'Ex_ampl_sweep_SSR':
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #
                #
                #     # self.mcas.asc(length_mus=0.02, aom_Ex=True)
                #     # self.mcas.asc(length_mus=0.137, name='aom_delay')
                #     #
                #     self.mcas.asc(length_mus=0.009, aom_Ex=True)
                #     self.mcas.asc(length_mus=0.151, name='aom_delay')
                #     # self.mcas.asc(length_mus=0.015, aom_Ex=True)
                #     # self.mcas.asc(length_mus=0.155, name='aom_delay')
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[self.kwargs['eom_ampl']]),
                #         length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #         name='Gauss')
                #
                #     self.mcas.asc(length_mus=0.1)
                #
                #
                #
                #     # =========DELETE IT AFTER TEST!!!
                #     #
                #     # self.mcas.asc(length_mus=0.009, aom_Ex=True)
                #     # self.mcas.asc(length_mus=0.151, name='aom_delay')
                #     # # self.mcas.asc(length_mus=0.015, aom_Ex=True)
                #     # # self.mcas.asc(length_mus=0.155, name='aom_delay')
                #     #
                #     # self.mcas.asc(
                #     #     pd2g2=dict(
                #     #         type='gauss',
                #     #         inv_fwhm=1,
                #     #         amplitudes=[self.kwargs['eom_ampl']]),
                #     #     length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #     #     name='Gauss')
                #     # =========DELETE IT AFTER TEST!!!
                #
                #
                #     self.mcas.asc(length_mus=0.5)
                #     self.mcas.asc(length_mus=self.laser_dur)
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'opt_mw_delays_calibration':
                #
                #     pi_dur = self.kwargs['pi_dur']
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     # print('kwargs keys: ',self.kwargs.keys())
                #     # print('self.frequencies: ',self.frequencies)
                #
                #     mw_freq = self.frequencies[0]
                #     tau = self.kwargs['tau']
                #     # aom_Ex_dur = 0.015#0.02
                #     # aom_delay = 0.155#0.137
                #     aom_Ex_dur = 0.02#0.02
                #     aom_delay = 0.137#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #     # print('======= Tau is: ',tau)
                #     # tau determines the start of the MW pulse relative to start of the aom pulse
                #
                #     if tau <0 and np.abs(tau)>=pi_dur:
                #
                #         # print('if_1')
                #         if np.abs(tau) < __TT_TRIGGER_LENGTH__:
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #             # print('if_1.1')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi',
                #             )
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(np.abs(tau) - pi_dur), name='wait')
                #
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(length_mus=aom_delay, name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #         elif np.abs(tau) >= __TT_TRIGGER_LENGTH__:
                #             # print('if_1.2')
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi',
                #             )
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(np.abs(tau) - pi_dur-__TT_TRIGGER_LENGTH__), name='wait')
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(length_mus=aom_delay, name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #
                #         self.mcas.asc(length_mus=self.laser_dur)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #     elif tau < 0 and np.abs(tau) < pi_dur:
                #         # print('if_2')
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(np.abs(tau)),
                #             name='MW_pi',
                #         )
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pi_dur-np.abs(tau)),
                #             name='MW_pi_with_aom_Ex',
                #             aom_Ex = True
                #         )
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur-(pi_dur-np.abs(tau))),
                #                       aom_Ex=True,name='Ex_aom_residual')
                #
                #         self.mcas.asc(length_mus=aom_delay, name='aom_delay')
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[self.kwargs['eom_ampl']]),
                #             length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #             name='Gauss')
                #
                #         self.mcas.asc(length_mus=self.laser_dur)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #     elif tau >= 0 and np.abs(tau) <aom_Ex_dur:
                #         # print('if_3')
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau),
                #                       aom_Ex=True,name='Ex_aom')
                #         if pi_dur <= (aom_Ex_dur-tau):
                #             # print('if_3.1')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi_with_aom_Ex', aom_Ex=True
                #             )
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur - (pi_dur + tau)),
                #                           aom_Ex=True,name='Ex_aom_residiual')
                #
                #             self.mcas.asc(length_mus=aom_delay, name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #
                #             self.mcas.asc(length_mus=self.laser_dur)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #         if pi_dur > (aom_Ex_dur-tau):
                #             # print('if_3.2')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_Ex_dur - tau),
                #                 name='MW_pi_with_aom_Ex',aom_Ex=True
                #             )
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur - (aom_Ex_dur - tau)),
                #                 name='MW_pi'
                #             )
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_delay - (pi_dur - (aom_Ex_dur - tau))),#aom_delay
                #                           name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #
                #             self.mcas.asc(length_mus=self.laser_dur)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #     elif tau > 0 and np.abs(tau) >= aom_Ex_dur and (np.abs(tau)+pi_dur)<=(aom_delay+aom_Ex_dur):
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         # print('if_4')
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                       aom_Ex=True,name='Ex_aom')
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - aom_Ex_dur))
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pi_dur),
                #             name='MW_pi')
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_delay-pi_dur-(tau - aom_Ex_dur)),
                #                       name='aom_delay')
                #
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[self.kwargs['eom_ampl']]),
                #             length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #             name='Gauss')
                #
                #         self.mcas.asc(length_mus=self.laser_dur)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #     elif tau > 0 and np.abs(tau) >= aom_Ex_dur and (np.abs(tau)+pi_dur)>(aom_delay+aom_Ex_dur):
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         # print('if_5')
                #         if np.abs(tau)<=(aom_delay+aom_Ex_dur):
                #             # print('if_5.1')
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                           aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - aom_Ex_dur))
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_delay - (tau - aom_Ex_dur)),
                #                 name='MW_pi')
                #
                #             remaining_mw_dur = pi_dur - (aom_delay-(tau-aom_Ex_dur))
                #             # print('remaining mw_dur = ',remaining_mw_dur)
                #             if remaining_mw_dur >= opt_pi_dur:
                #                 # print('if_5.1.1')
                #                 self.mcas.asc(
                #                     pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     length_mus=opt_pi_dur,
                #                     name='Gauss')
                #
                #                 self.mcas.asc(
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     length_mus=E.round_length_mus_full_sample(remaining_mw_dur - opt_pi_dur),
                #                     name='MW_pi')
                #                 self.mcas.asc(length_mus=self.laser_dur)
                #                 self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #             if remaining_mw_dur < opt_pi_dur:
                #                 # print('if_5.1.2')
                #                 self.mcas.asc(
                #                     pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     length_mus=remaining_mw_dur,
                #                     name='Gauss')
                #                 already_written_samples = np.around(remaining_mw_dur * __SAMPLE_FREQUENCY__).astype(int)
                #
                #                 self.mcas.asc(
                #                     pd2g2=dict(type='gauss', inv_fwhm=1, wf_start=already_written_samples,amplitudes=[self.kwargs['eom_ampl']]),
                #
                #                     length_mus=opt_pi_dur - remaining_mw_dur,
                #                     name='Gauss')
                #
                #                 self.mcas.asc(length_mus=self.laser_dur)
                #                 self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #
                #         if np.abs(tau)>(aom_delay+aom_Ex_dur):
                #             # print('if_5.2')
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                           aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(length_mus=aom_delay, name='aom_delay')
                #
                #
                #             if tau >=(aom_delay+aom_Ex_dur+opt_pi_dur):
                #                 # print('if_5.2.1')
                #                 if tau >=(aom_delay+aom_Ex_dur+opt_pi_dur+__TT_TRIGGER_LENGTH__):
                #                     self.mcas.asc(
                #                         pd2g2=dict(
                #                             type='gauss',
                #                             inv_fwhm=1,
                #                             amplitudes=[self.kwargs['eom_ampl']]),
                #                         length_mus=opt_pi_dur,
                #                         name='Gauss')
                #
                #
                #                     self.mcas.asc(length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #                     self.mcas.asc(length_mus=tau - (opt_pi_dur + aom_delay + aom_Ex_dur+__TT_TRIGGER_LENGTH__),
                #                                   name='wait for mw')
                #
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=E.round_length_mus_full_sample(pi_dur),
                #                         name='MW_pi',
                #                     )
                #
                #                     # self.mcas.asc(length_mus=self.laser_dur)
                #                     # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #
                #                 else:
                #                     self.mcas.asc(
                #                         pd2g2=dict(
                #                             type='gauss',
                #                             inv_fwhm=1,
                #                             amplitudes=[self.kwargs['eom_ampl']]),
                #                         length_mus=opt_pi_dur,
                #                         name='Gauss')
                #
                #                     self.mcas.asc(length_mus=tau - (opt_pi_dur+aom_delay+aom_Ex_dur), name='wait for mw')
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=E.round_length_mus_full_sample(pi_dur),
                #                         name='MW_pi',
                #                     )
                #
                #                     self.mcas.asc(length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #
                #             if tau < (aom_delay + aom_Ex_dur + opt_pi_dur):
                #                 # print('if_5.2.2')
                #
                #                 self.mcas.asc(
                #                     pd2g2=dict(
                #                         type='gauss',
                #                         inv_fwhm=1,
                #                         amplitudes=[self.kwargs['eom_ampl']]),
                #                     length_mus=E.round_length_mus_full_sample(tau-aom_Ex_dur-aom_delay),
                #                     name='Gauss_begin')
                #
                #                 already_written_samples = np.around((tau-aom_Ex_dur-aom_delay) * __SAMPLE_FREQUENCY__).astype(int)
                #                 remaining_optical = opt_pi_dur - (tau-aom_Ex_dur-aom_delay)
                #                 if pi_dur >= remaining_optical:
                #                     # print('if_5.2.2.1')
                #
                #                     self.mcas.asc(
                #                         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                         wf_start=already_written_samples,
                #
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=remaining_optical,
                #                         name='Gauss_end')
                #
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=E.round_length_mus_full_sample(pi_dur-remaining_optical),
                #                         name='MW_pi')
                #                     self.mcas.asc(length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #                 if pi_dur < remaining_optical:
                #                     # print('if_5.2.2.2')
                #
                #                     self.mcas.asc(
                #                         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                         wf_start=already_written_samples,
                #
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=pi_dur,
                #                         name='Gauss_MW')
                #                     already_written_samples+= np.around(pi_dur* __SAMPLE_FREQUENCY__).astype(int)
                #
                #                     self.mcas.asc(
                #                         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                         wf_start=already_written_samples,
                #                         # length_mus=pi_dur,
                #                         length_mus=opt_pi_dur - (tau-aom_Ex_dur-aom_delay)-pi_dur,
                #                         name='Gauss_end')
                #
                #                     self.mcas.asc(length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'opt_mw_delays_calibration2':
                #
                #     pi_dur = self.kwargs['pi_dur']
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     mw_freq = self.frequencies[0]
                #     tau = self.kwargs['tau']
                #     aom_Ex_dur = 0.02#0.02
                #     aom_delay = 0.137#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #
                #     if tau <0 and np.abs(tau)>=pi_dur:
                #
                #         # print('if_1')
                #         if np.abs(tau) < __TT_TRIGGER_LENGTH__:
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #             # print('if_1.1')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi',
                #             )
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(np.abs(tau) - pi_dur), name='wait')
                #
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=aom_Ex_dur, aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=aom_delay, name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #         elif np.abs(tau) >= __TT_TRIGGER_LENGTH__:
                #             # print('if_1.2')
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi',
                #             )
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(np.abs(tau) - pi_dur-__TT_TRIGGER_LENGTH__), name='wait')
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=aom_Ex_dur, aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=aom_delay, name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #
                #         self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=self.laser_dur,)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #     elif tau < 0 and np.abs(tau) < pi_dur:
                #         print('tau is : ', tau)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(np.abs(tau)),
                #             name='MW_pi',
                #         )
                #
                #         self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                       aom_Ex=True,name='Ex_aom_residual')
                #
                #         self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=aom_delay, name='aom_delay')
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[self.kwargs['eom_ampl']]),
                #             length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #             name='Gauss')
                #
                #         self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                       length_mus=self.laser_dur)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #     elif tau >= 0 and np.abs(tau) <aom_Ex_dur:
                #         # print('if_3')
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau),
                #                       aom_Ex=True,name='Ex_aom')
                #         if pi_dur <= (aom_Ex_dur-tau):
                #             # print('if_3.1')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi_with_aom_Ex', aom_Ex=True
                #             )
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur - (pi_dur + tau)),
                #                           pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                           aom_Ex=True,name='Ex_aom_residiual')
                #
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=aom_delay, name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                           length_mus=self.laser_dur)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #         if pi_dur > (aom_Ex_dur-tau):
                #             # print('if_3.2')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_Ex_dur - tau),
                #                 name='MW_pi_with_aom_Ex',aom_Ex=True
                #             )
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur - (aom_Ex_dur - tau)),
                #                 name='MW_pi'
                #             )
                #
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_delay - (pi_dur - (aom_Ex_dur - tau))),#aom_delay
                #                           name='aom_delay')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[self.kwargs['eom_ampl']]),
                #                 length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #                 name='Gauss')
                #
                #             self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=self.laser_dur)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True,name = 'memory')
                #
                #     elif tau > 0 and np.abs(tau) >= aom_Ex_dur and (np.abs(tau)+pi_dur)<=(aom_delay+aom_Ex_dur):
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         # print('if_4')
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                       aom_Ex=True,name='Ex_aom')
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - aom_Ex_dur))
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pi_dur),
                #             name='MW_pi')
                #
                #         self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(aom_delay-pi_dur-(tau - aom_Ex_dur)),
                #                       name='aom_delay')
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[self.kwargs['eom_ampl']]),
                #             length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #             name='Gauss')
                #
                #         self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                       length_mus=self.laser_dur)
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #     elif tau > 0 and np.abs(tau) >= aom_Ex_dur and (np.abs(tau)+pi_dur)>(aom_delay+aom_Ex_dur):
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #
                #         # print('if_5')
                #         if np.abs(tau)<=(aom_delay+aom_Ex_dur):
                #             # print('if_5.1')
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                           aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - aom_Ex_dur))
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_delay - (tau - aom_Ex_dur)),
                #                 name='MW_pi')
                #
                #             remaining_mw_dur = pi_dur - (aom_delay-(tau-aom_Ex_dur))
                #             # print('remaining mw_dur = ',remaining_mw_dur)
                #             if remaining_mw_dur >= opt_pi_dur:
                #                 # print('if_5.1.1')
                #                 self.mcas.asc(
                #                     pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     length_mus=opt_pi_dur,
                #                     name='Gauss')
                #
                #                 self.mcas.asc(
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     length_mus=E.round_length_mus_full_sample(remaining_mw_dur - opt_pi_dur),
                #                     name='MW_pi')
                #                 self.mcas.asc(length_mus=self.laser_dur)
                #                 self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #             if remaining_mw_dur < opt_pi_dur:
                #                 # print('if_5.1.2')
                #                 self.mcas.asc(
                #                     pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     length_mus=remaining_mw_dur,
                #                     name='Gauss')
                #                 already_written_samples = np.around(remaining_mw_dur * __SAMPLE_FREQUENCY__).astype(int)
                #
                #                 self.mcas.asc(
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                     pd2g2=dict(type='gauss', inv_fwhm=1, wf_start=already_written_samples,amplitudes=[self.kwargs['eom_ampl']]),
                #
                #                     length_mus=opt_pi_dur - remaining_mw_dur,
                #                     name='Gauss')
                #
                #                 self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                               length_mus=self.laser_dur)
                #                 self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #
                #         if np.abs(tau)>(aom_delay+aom_Ex_dur):
                #             # print('if_5.2')
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur),
                #                           aom_Ex=True,name='Ex_aom')
                #             self.mcas.asc(length_mus=aom_delay, name='aom_delay')
                #
                #
                #             if tau >=(aom_delay+aom_Ex_dur+opt_pi_dur):
                #                 # print('if_5.2.1')
                #                 if tau >=(aom_delay+aom_Ex_dur+opt_pi_dur+__TT_TRIGGER_LENGTH__):
                #                     self.mcas.asc(
                #                         pd2g2=dict(
                #                             type='gauss',
                #                             inv_fwhm=1,
                #                             amplitudes=[self.kwargs['eom_ampl']]),
                #                         length_mus=opt_pi_dur,
                #                         name='Gauss')
                #
                #
                #                     self.mcas.asc(length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #                     self.mcas.asc(length_mus=tau - (opt_pi_dur + aom_delay + aom_Ex_dur+__TT_TRIGGER_LENGTH__),
                #                                   name='wait for mw')
                #
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=E.round_length_mus_full_sample(pi_dur),
                #                         name='MW_pi',
                #                     )
                #
                #                     # self.mcas.asc(length_mus=self.laser_dur)
                #                     # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #
                #                 else:
                #                     self.mcas.asc(
                #                         pd2g2=dict(
                #                             type='gauss',
                #                             inv_fwhm=1,
                #                             amplitudes=[self.kwargs['eom_ampl']]),
                #                         length_mus=opt_pi_dur,
                #                         name='Gauss')
                #
                #                     self.mcas.asc(length_mus=tau - (opt_pi_dur+aom_delay+aom_Ex_dur), name='wait for mw')
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=E.round_length_mus_full_sample(pi_dur),
                #                         name='MW_pi',
                #                     )
                #
                #                     self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                                   length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #
                #             if tau < (aom_delay + aom_Ex_dur + opt_pi_dur):
                #                 # print('if_5.2.2')
                #
                #                 self.mcas.asc(
                #                     pd2g2=dict(
                #                         type='gauss',
                #                         inv_fwhm=1,
                #                         amplitudes=[self.kwargs['eom_ampl']]),
                #                     length_mus=E.round_length_mus_full_sample(tau-aom_Ex_dur-aom_delay),
                #                     name='Gauss_begin')
                #
                #                 already_written_samples = np.around((tau-aom_Ex_dur-aom_delay) * __SAMPLE_FREQUENCY__).astype(int)
                #                 remaining_optical = opt_pi_dur - (tau-aom_Ex_dur-aom_delay)
                #                 if pi_dur >= remaining_optical:
                #                     # print('if_5.2.2.1')
                #
                #                     self.mcas.asc(
                #                         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                         wf_start=already_written_samples,
                #
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=remaining_optical,
                #                         name='Gauss_end')
                #
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=E.round_length_mus_full_sample(pi_dur-remaining_optical),
                #                         name='MW_pi')
                #                     self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                                   length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                #
                #                 if pi_dur < remaining_optical:
                #                     # print('if_5.2.2.2')
                #
                #                     self.mcas.asc(
                #                         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                         wf_start=already_written_samples,
                #
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         length_mus=pi_dur,
                #                         name='Gauss_MW')
                #                     already_written_samples+= np.around(pi_dur* __SAMPLE_FREQUENCY__).astype(int)
                #
                #                     self.mcas.asc(
                #                         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #                         wf_start=already_written_samples,
                #                         # length_mus=pi_dur,
                #                         length_mus=opt_pi_dur - (tau-aom_Ex_dur-aom_delay)-pi_dur,
                #                         name='Gauss_end')
                #
                #                     self.mcas.asc(pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                                   length_mus=self.laser_dur)
                #                     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == '2_opt_mw_delays_calibration_old':
                #
                #
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     if 'mw_pihalf_ampl' in self.kwargs.keys():
                #         mw_pihalf_ampl = self.kwargs['mw_pihalf_ampl']
                #     else:
                #         mw_pihalf_ampl = mw_amplitude
                #
                #     optical_delay = self.kwargs['optical_delay'] #56ns (was 125ns) delay between optical pulses aka interferometer length
                #
                #     pi_dur = self.kwargs['pi_dur']
                #     mw_freq = self.frequencies[0]
                #     tau = self.kwargs['tau']
                #     pihalf_dur =self.kwargs['pihalf_dur']
                #     eom_ampl = self.kwargs['eom_ampl']
                #     aom_Ex_dur = 0.02#0.02
                #     aom_delay = 0.137#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #     # tau determines the start of the MW pulse relative to start of the aom pulse
                #     # if aom_delay +aom_Ex_dur + optical_delay <tau < (aom_delay+aom_Ex_dur):
                #
                #     if tau< optical_delay+aom_Ex_dur:
                #         raise Exception('Tau is too short. must be greater than 76ns')
                #
                #
                #     if tau <= (aom_delay+aom_Ex_dur):
                #         if tau+pi_dur>=(aom_delay+aom_Ex_dur):
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                           name='gate1')  # 160ns Gated counter
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=optical_delay - aom_Ex_dur-pihalf_dur,
                #                           name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #
                #             self.mcas.asc(length_mus=tau - (optical_delay+aom_Ex_dur) , name='wait_2')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_Ex_dur + aom_delay - tau),
                #                 name='MW_begin')  # 13.5ns. First pi/2 pulse
                #
                #             gauss1_begin = pi_dur - (aom_Ex_dur + aom_delay - tau)
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='Gauss1_MW')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #                 name='Gauss1_end')
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur),
                #                           name='wait')  #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=opt_pi_dur,  # 0.04008333333333333 ns Second EOM pulse starts
                #                 name='Gauss2')
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #
                #         else:
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                           name='gate1')  # 160ns Gated counter
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=optical_delay - aom_Ex_dur - pihalf_dur,
                #                           name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #
                #             self.mcas.asc(length_mus=tau - (optical_delay + aom_Ex_dur), name='wait_2')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_begin')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur +aom_delay - (tau+pi_dur)),
                #                           name='wait_3')
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #                 name='Gauss1')  # First EOM Pulse
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur),
                #                           name='wait')  #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=opt_pi_dur,  # 0.04008333333333333 ns Second EOM pulse starts
                #                 name='Gauss2')
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #     elif aom_delay +aom_Ex_dur + optical_delay <=tau<aom_delay +aom_Ex_dur + optical_delay +opt_pi_dur:
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #         self.mcas.asc(length_mus=optical_delay - aom_Ex_dur,
                #                       name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1')  # 7ns
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #             name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #         self.mcas.asc(length_mus=0.0605, name='wait_2')
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[eom_ampl]),
                #             length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #             name='Gauss1')  # First EOM Pulse
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur), name='wait_2')
                #
                #         gauss2_begin = tau - (aom_Ex_dur+aom_delay+optical_delay)
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[eom_ampl]),
                #             length_mus=E.round_length_mus_full_sample(gauss2_begin),
                #             name='Gauss2_begin')  # First EOM Pulse
                #         already_written_samples = np.around(gauss2_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #         if tau + pi_dur <= aom_delay +aom_Ex_dur + optical_delay +opt_pi_dur:
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),  #
                #                 name='Gauss2_MW')
                #             already_written_samples+=np.around(pi_dur * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - (gauss2_begin + pi_dur)),
                #                 name='Gauss2_end')
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #         else:
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss2_begin),  #
                #                 name='Gauss2_MW')
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur-(opt_pi_dur - gauss2_begin)),
                #                 name='MW_end')
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #     elif tau >= aom_delay + aom_Ex_dur + optical_delay + opt_pi_dur:
                #         # ---------------
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #         self.mcas.asc(length_mus=optical_delay - aom_Ex_dur,
                #                       name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1')  # 7ns
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #             name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #         self.mcas.asc(length_mus=0.0605, name='wait_2')
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[eom_ampl]),
                #             length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #             name='Gauss1')  # First EOM Pulse
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur), name='wait_2')
                #
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[eom_ampl]),
                #             length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #             name='Gauss2')  # Second EOM Pulse
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - ( aom_delay + aom_Ex_dur + optical_delay + opt_pi_dur)), name='wait_2')
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pi_dur),
                #             name='MW_pi')  # 27ns
                #
                #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #     else:
                #         # !!!!!! THIS PART IS USED
                #
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur),
                #                       name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1')  # 7ns
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #             name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #         self.mcas.asc(length_mus=0.0605, name='wait_2')
                #
                #         if tau >= aom_delay + aom_Ex_dur and tau + pi_dur <= (aom_delay + aom_Ex_dur + opt_pi_dur):
                #
                #             gauss1_begin = tau - (aom_delay + aom_Ex_dur)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='Gauss1_begin')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),  #
                #                 name='Gauss1_MW')
                #             already_written_samples += np.around(pi_dur * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - pi_dur - gauss1_begin),  #
                #                 name='Gauss1_end')
                #             self.mcas.asc(length_mus=optical_delay - opt_pi_dur,
                #                           name='wait_3')  # 14.5ns wait before second optical pi pulse
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=opt_pi_dur,  # 0.04008333333333333 ns Second EOM pulse starts
                #                 name='Gauss2')
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #         elif aom_delay + aom_Ex_dur < tau < aom_delay + aom_Ex_dur +opt_pi_dur \
                #                 and aom_delay + aom_Ex_dur +optical_delay>=tau + pi_dur > (aom_delay + aom_Ex_dur + opt_pi_dur):
                #             gauss1_begin = tau - (aom_delay + aom_Ex_dur)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='Gauss1_begin')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #                 name='Gauss1_MW')
                #
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur - (opt_pi_dur - gauss1_begin)),  #
                #                 name='MW_end')
                #
                #             self.mcas.asc(length_mus=optical_delay - (opt_pi_dur+pi_dur - (opt_pi_dur - gauss1_begin)),
                #                           name='wait_3')  # 14.5ns wait before second optical pi pulse
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=opt_pi_dur,  # 0.04008333333333333 ns Second EOM pulse starts
                #                 name='Gauss2')
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #         elif aom_delay + aom_Ex_dur < tau < aom_delay + aom_Ex_dur +opt_pi_dur \
                #                 and aom_delay + aom_Ex_dur +optical_delay < tau + pi_dur:
                #             # !!!!!! THIS PART IS USED
                #
                #             gauss1_begin = tau - (aom_delay + aom_Ex_dur)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='Gauss1_begin')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #                 name='Gauss1_MW')
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur),  #
                #                 name='MW')
                #
                #             gauss2_begin =E.round_length_mus_full_sample(pi_dur - (opt_pi_dur - gauss1_begin + optical_delay - opt_pi_dur))
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=gauss2_begin,  # 0.04008333333333333 ns Second EOM pulse starts
                #                 name='Gauss2_MW')
                #             already_written_samples = np.around(gauss2_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss2_begin),  #
                #                 name='Gauss2_end')
                #
                #
                #
                #             if 'tau_bell' in self.kwargs.keys():
                #                 self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.075917),
                #                               name='wait_before_MW')  # 100ns
                #                 tau_bell = self.kwargs['tau_bell']
                #                 self.mcas.asc(
                #                     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                     length_mus=E.round_length_mus_full_sample(tau_bell),
                #                     name='tau bell')  # 13.5ns. First pi/2 pulse
                #
                #
                #
                #
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #         elif aom_delay + aom_Ex_dur + optical_delay > tau > aom_delay + aom_Ex_dur + opt_pi_dur :
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #                 name='Gauss1_begin')  # First EOM Pulse
                #
                #             self.mcas.asc(length_mus=tau - (aom_delay + aom_Ex_dur + opt_pi_dur),
                #                           name='wait_3')  # 14.5ns wait before second optical pi pulse
                #
                #             # pd2g1 = dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_delay + aom_Ex_dur + optical_delay - tau),  #
                #                 name='MW_end')
                #
                #             gauss2_begin = pi_dur - (aom_delay + aom_Ex_dur + optical_delay - tau)
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=gauss2_begin,  # 0.04008333333333333 ns Second EOM pulse starts
                #                 name='Gauss2_MW')
                #             already_written_samples = np.around(gauss2_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss2_begin),  #
                #                 name='Gauss')
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == '2_opt_mw_delays_calibration':
                #
                #
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     if 'mw_pihalf_ampl' in self.kwargs.keys():
                #         mw_pihalf_ampl = self.kwargs['mw_pihalf_ampl']
                #     else:
                #         mw_pihalf_ampl = mw_amplitude
                #
                #     optical_delay = self.kwargs['optical_delay'] #56ns (was 125ns) delay between optical pulses aka interferometer length
                #
                #     pi_dur = self.kwargs['pi_dur']
                #     mw_freq = self.frequencies[0]
                #     tau = self.kwargs['tau']
                #     pihalf_dur =self.kwargs['pihalf_dur']
                #     eom_ampl = self.kwargs['eom_ampl']
                #     aom_Ex_dur = 0.009#0.02
                #     aom_delay = 0.151#0.137
                #     opt_pi_dur = 1201 * 1. / __SAMPLE_FREQUENCY__
                #     # tau determines the start of the MW pulse relative to start of the aom pulse
                #     # if aom_delay +aom_Ex_dur + optical_delay <tau < (aom_delay+aom_Ex_dur):
                #
                #     if tau< optical_delay+aom_Ex_dur:
                #         raise Exception('Tau is too short. must be greater than 76ns')
                #
                #
                #     if tau <= (aom_delay+aom_Ex_dur):
                #
                #         if tau+pi_dur>=(aom_delay+aom_Ex_dur):
                #             print(1)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                           name='gate1')  # 160ns Gated counter
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_1')  # 5 ns. AOM for the first pulse
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur-pihalf_dur),
                #                           name='wait_1.1')  # 37.3ns ns. Delay between first and second AOM_Ex pulses
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_2')  # 5 ns. AOM for the first puls
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - (optical_delay+aom_Ex_dur)),
                #                           name='wait_2')
                #
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(aom_Ex_dur + aom_delay - tau),
                #                 name='MW_begin')  #
                #
                #             gauss1_begin = pi_dur - (aom_Ex_dur + aom_delay - tau)
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='Gauss1_MW')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #                 name='Gauss1_end')
                #
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #
                #         else:
                #             print(2)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                           name='gate1')  # 160ns Gated counter
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_1')  # 5 ns. AOM for the first pulse
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur - pihalf_dur),
                #                           name='wait_1.1')  # 37.3 ns. Delay between first and second AOM_Ex pulses
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_2')  # 5 ns. AOM for the first puls
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - (optical_delay + aom_Ex_dur)),
                #                           name='wait_2')
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),
                #                 name='MW_pi')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_Ex_dur +aom_delay - (tau+pi_dur)),
                #                           name='wait_3')
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #                 name='Gauss1')  # First EOM Pulse
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #     elif (aom_delay+aom_Ex_dur + opt_pi_dur) > tau > (aom_delay+aom_Ex_dur): #0.155 to 0.255083333
                #         if tau + pi_dur < (aom_delay + aom_Ex_dur + opt_pi_dur): # tau <0.2280833333
                #             # THIS CASE IS USED
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                           name='gate1')  # 160ns Gated counter
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_1')  # 5 ns. AOM for the first pulse
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur - pihalf_dur),
                #                           name='wait_1.1')  # 37.3ns ns. Delay between first and second AOM_Ex pulses
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_2')  # 5 ns. AOM for the first puls
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_delay - optical_delay),
                #                      name='aom_delay_wait')
                #
                #
                #             gauss1_begin = tau - (aom_delay+aom_Ex_dur)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='2Gauss')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #
                #             self.mcas.asc(
                #
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(pi_dur),  #
                #                 name='2Gauss_MW')
                #             already_written_samples2 = np.around(pi_dur * __SAMPLE_FREQUENCY__).astype(int)
                #
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples2+already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - (gauss1_begin + pi_dur)),  #
                #                 name='2Gauss_end')
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #         else:
                #             print(4)
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                           name='gate1')  # 160ns Gated counter
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_1')  # 5 ns. AOM for the first pulse
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #             # print(optical_delay)
                #             # print(aom_Ex_dur)
                #             # print(pihalf_dur)
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur - pihalf_dur),
                #                           name='wait_1.1')  # 37.3ns ns. Delay between first and second AOM_Ex pulses
                #             self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                           name='Ex_aom_2')  # 5 ns. AOM for the first puls
                #
                #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_delay - optical_delay),
                #                      name='aom_delay_wait')
                #
                #
                #             gauss1_begin = tau - (aom_delay+aom_Ex_dur)
                #             self.mcas.asc(
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #                 length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #                 name='2Gauss')  # First EOM Pulse
                #             already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 pd2g2=dict(
                #                     type='gauss_2_pulses',
                #                     inv_fwhm=1,
                #                     amplitudes=[eom_ampl]),
                #
                #                 wf_start=already_written_samples,
                #                 length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #                 name='2Gauss_MW')
                #
                #
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pi_dur - (opt_pi_dur - gauss1_begin)),  #
                #                 name='MW_end')
                #
                #             self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #             self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #
                #
                #
                #     elif (aom_delay+aom_Ex_dur + opt_pi_dur) <= tau:
                #
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True,
                #                       name='gate1')  # 160ns Gated counter
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_1')  # 5 ns. AOM for the first pulse
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #             name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur - pihalf_dur),
                #                       name='wait_1.1')  # 37.3ns ns. Delay between first and second AOM_Ex pulses
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                       name='Ex_aom_2')  # 5 ns. AOM for the first puls
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(aom_delay - optical_delay),
                #                       name='aom_delay_wait')
                #
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss_2_pulses',
                #                 inv_fwhm=1,
                #                 amplitudes=[eom_ampl]),
                #             length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #             name='2Gauss')  # First EOM Pulse
                #
                #         self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - (aom_Ex_dur+aom_delay+opt_pi_dur)),
                #                       name='wait before MW')
                #
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pi_dur),
                #             name='MW_pi')  # 13.5ns. First pi/2 pulse
                #
                #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #
                #
                #
                #
                #
                #     else:
                #         raise('smth is wrong tau is {}'.format(tau))
                #     # elif aom_delay +aom_Ex_dur + optical_delay <= tau <aom_delay +aom_Ex_dur + optical_delay +opt_pi_dur:
                #     #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #     #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #     #                   name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #     #     self.mcas.asc(length_mus=optical_delay - aom_Ex_dur,
                #     #                   name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #     #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #     #                   name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1')  # 7ns
                #     #
                #     #     self.mcas.asc(
                #     #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #         name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #     #
                #     #     self.mcas.asc(length_mus=0.0605, name='wait_2')
                #     #     self.mcas.asc(
                #     #         pd2g2=dict(
                #     #             type='gauss',
                #     #             inv_fwhm=1,
                #     #             amplitudes=[eom_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #     #         name='Gauss1')  # First EOM Pulse
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur), name='wait_2')
                #     #
                #     #     gauss2_begin = tau - (aom_Ex_dur+aom_delay+optical_delay)
                #     #     self.mcas.asc(
                #     #         pd2g2=dict(
                #     #             type='gauss',
                #     #             inv_fwhm=1,
                #     #             amplitudes=[eom_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(gauss2_begin),
                #     #         name='Gauss2_begin')  # First EOM Pulse
                #     #     already_written_samples = np.around(gauss2_begin * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #     if tau + pi_dur <= aom_delay +aom_Ex_dur + optical_delay +opt_pi_dur:
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(pi_dur),  #
                #     #             name='Gauss2_MW')
                #     #         already_written_samples+=np.around(pi_dur * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - (gauss2_begin + pi_dur)),
                #     #             name='Gauss2_end')
                #     #
                #     #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #     #
                #     #     else:
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss2_begin),  #
                #     #             name='Gauss2_MW')
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             length_mus=E.round_length_mus_full_sample(pi_dur-(opt_pi_dur - gauss2_begin)),
                #     #             name='MW_end')
                #     #
                #     #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #     #
                #     # elif tau >= aom_delay + aom_Ex_dur + optical_delay + opt_pi_dur:
                #     #     # ---------------
                #     #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #     #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #     #                   name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #     #     self.mcas.asc(length_mus=optical_delay - aom_Ex_dur,
                #     #                   name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #     #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #     #                   name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1')  # 7ns
                #     #     self.mcas.asc(
                #     #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #         name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #     #     self.mcas.asc(length_mus=0.0605, name='wait_2')
                #     #     self.mcas.asc(
                #     #         pd2g2=dict(
                #     #             type='gauss',
                #     #             inv_fwhm=1,
                #     #             amplitudes=[eom_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #     #         name='Gauss1')  # First EOM Pulse
                #     #
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur), name='wait_2')
                #     #
                #     #     self.mcas.asc(
                #     #         pd2g2=dict(
                #     #             type='gauss',
                #     #             inv_fwhm=1,
                #     #             amplitudes=[eom_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #     #         name='Gauss2')  # Second EOM Pulse
                #     #
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(tau - ( aom_delay + aom_Ex_dur + optical_delay + opt_pi_dur)), name='wait_2')
                #     #
                #     #     self.mcas.asc(
                #     #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #         length_mus=E.round_length_mus_full_sample(pi_dur),
                #     #         name='MW_pi')  # 27ns
                #     #
                #     #     self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #     #
                #     # else:
                #     #     # !!!!!! THIS PART IS USED
                #     #
                #     #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #     #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #     #                   name='Ex_aom_1')  # 20 ns. AOM for the first pulse
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(optical_delay - aom_Ex_dur),
                #     #                   name='wait_1.1')  # 36ns ns. Delay between first and second AOM_Ex pulses
                #     #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #     #                   name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #     #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1')  # 7ns
                #     #
                #     #     self.mcas.asc(
                #     #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #     #         length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #         name='MW_pihalf')  # 13.5ns. First pi/2 pulse
                #     #
                #     #     self.mcas.asc(length_mus=0.0605, name='wait_2')
                #     #
                #     #     if tau >= aom_delay + aom_Ex_dur and tau + pi_dur <= (aom_delay + aom_Ex_dur + opt_pi_dur):
                #     #
                #     #         gauss1_begin = tau - (aom_delay + aom_Ex_dur)
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #     #             name='Gauss1_begin')  # First EOM Pulse
                #     #         already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(pi_dur),  #
                #     #             name='Gauss1_MW')
                #     #         already_written_samples += np.around(pi_dur * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - pi_dur - gauss1_begin),  #
                #     #             name='Gauss1_end')
                #     #         self.mcas.asc(length_mus=optical_delay - opt_pi_dur,
                #     #                       name='wait_3')  # 14.5ns wait before second optical pi pulse
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=opt_pi_dur,  # 0.04008333333333333 ns Second EOM pulse starts
                #     #             name='Gauss2')
                #     #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #     #
                #     #     elif aom_delay + aom_Ex_dur < tau < aom_delay + aom_Ex_dur +opt_pi_dur \
                #     #             and aom_delay + aom_Ex_dur +optical_delay>=tau + pi_dur > (aom_delay + aom_Ex_dur + opt_pi_dur):
                #     #         gauss1_begin = tau - (aom_delay + aom_Ex_dur)
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #     #             name='Gauss1_begin')  # First EOM Pulse
                #     #         already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #     #             name='Gauss1_MW')
                #     #
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             length_mus=E.round_length_mus_full_sample(pi_dur - (opt_pi_dur - gauss1_begin)),  #
                #     #             name='MW_end')
                #     #
                #     #         self.mcas.asc(length_mus=optical_delay - (opt_pi_dur+pi_dur - (opt_pi_dur - gauss1_begin)),
                #     #                       name='wait_3')  # 14.5ns wait before second optical pi pulse
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=opt_pi_dur,  # 0.04008333333333333 ns Second EOM pulse starts
                #     #             name='Gauss2')
                #     #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #     #
                #     #     elif aom_delay + aom_Ex_dur < tau < aom_delay + aom_Ex_dur +opt_pi_dur \
                #     #             and aom_delay + aom_Ex_dur +optical_delay < tau + pi_dur:
                #     #         # !!!!!! THIS PART IS USED
                #     #
                #     #         gauss1_begin = tau - (aom_delay + aom_Ex_dur)
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #     #             name='Gauss1_begin')  # First EOM Pulse
                #     #         already_written_samples = np.around(gauss1_begin * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss1_begin),  #
                #     #             name='Gauss1_MW')
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             length_mus=E.round_length_mus_full_sample(optical_delay - opt_pi_dur),  #
                #     #             name='MW')
                #     #
                #     #         gauss2_begin =E.round_length_mus_full_sample(pi_dur - (opt_pi_dur - gauss1_begin + optical_delay - opt_pi_dur))
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=gauss2_begin,  # 0.04008333333333333 ns Second EOM pulse starts
                #     #             name='Gauss2_MW')
                #     #         already_written_samples = np.around(gauss2_begin * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss2_begin),  #
                #     #             name='Gauss2_end')
                #     #
                #     #
                #     #
                #     #         if 'tau_bell' in self.kwargs.keys():
                #     #             self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.075917),
                #     #                           name='wait_before_MW')  # 100ns
                #     #             tau_bell = self.kwargs['tau_bell']
                #     #             self.mcas.asc(
                #     #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_pihalf_ampl]),
                #     #                 length_mus=E.round_length_mus_full_sample(tau_bell),
                #     #                 name='tau bell')  # 13.5ns. First pi/2 pulse
                #     #
                #     #
                #     #
                #     #
                #     #
                #     #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                #     #
                #     #     elif aom_delay + aom_Ex_dur + optical_delay > tau > aom_delay + aom_Ex_dur + opt_pi_dur :
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #     #             name='Gauss1_begin')  # First EOM Pulse
                #     #
                #     #         self.mcas.asc(length_mus=tau - (aom_delay + aom_Ex_dur + opt_pi_dur),
                #     #                       name='wait_3')  # 14.5ns wait before second optical pi pulse
                #     #
                #     #         # pd2g1 = dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             length_mus=E.round_length_mus_full_sample(aom_delay + aom_Ex_dur + optical_delay - tau),  #
                #     #             name='MW_end')
                #     #
                #     #         gauss2_begin = pi_dur - (aom_delay + aom_Ex_dur + optical_delay - tau)
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #             length_mus=gauss2_begin,  # 0.04008333333333333 ns Second EOM pulse starts
                #     #             name='Gauss2_MW')
                #     #         already_written_samples = np.around(gauss2_begin * __SAMPLE_FREQUENCY__).astype(int)
                #     #
                #     #         self.mcas.asc(
                #     #             pd2g2=dict(
                #     #                 type='gauss',
                #     #                 inv_fwhm=1,
                #     #                 amplitudes=[eom_ampl]),
                #     #
                #     #             wf_start=already_written_samples,
                #     #             length_mus=E.round_length_mus_full_sample(opt_pi_dur - gauss2_begin),  #
                #     #             name='Gauss')
                #     #
                #     #         self.mcas.asc(length_mus=self.laser_dur, name='wait_before_memory')  # 100ns
                #     #         self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')  # 160ns
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == '2opt_withMW_pi':
                #     pi_dur = self.kwargs['pi_dur']
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     mw_freq = self.frequencies[0]
                #     mw_delay = self.kwargs['mw_delay']#delay betweenn first optical pulse and MW pulse (measured from aom_Ex open)
                #     optical_delay = self.kwargs['optical_delay'] #delay between optical pulses aka interferometer length
                #     aom_Ex_dur = 0.015#0.02
                #     aom_delay = 0.155#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter
                #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_1')
                #     self.mcas.asc(length_mus=optical_delay - aom_Ex_dur, name='wait_1')
                #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_2')
                #     self.mcas.asc(length_mus=aom_delay-aom_Ex_dur-(optical_delay - aom_Ex_dur), name='wait_2')
                #
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[self.kwargs['eom_ampl']]),
                #         length_mus=E.round_length_mus_full_sample(mw_delay-aom_Ex_dur-aom_delay),
                #         name='Gauss1')
                #
                #     already_written_samples = np.around((mw_delay-aom_Ex_dur-aom_delay) * __SAMPLE_FREQUENCY__).astype(int)
                #     remaining_optical = opt_pi_dur - (mw_delay-aom_Ex_dur-aom_delay)
                #     self.mcas.asc(
                #         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #         wf_start=already_written_samples,
                #
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #         length_mus=remaining_optical,
                #         name='Gauss1_MW')
                #
                #     self.mcas.asc(
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #         length_mus=E.round_length_mus_full_sample(pi_dur - remaining_optical),
                #         name='MW_pi_residual')
                #
                #     self.mcas.asc(length_mus=optical_delay+aom_Ex_dur+aom_delay-(mw_delay+pi_dur), name='wait_3')
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[self.kwargs['eom_ampl']]),
                #         length_mus=481 * 1. / __SAMPLE_FREQUENCY__,
                #         name='Gauss2')
                #
                #     self.mcas.asc(length_mus=self.laser_dur,name='wait_4')
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory')
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'entanglement_for_tests':
                #
                #     eom_ampl = self.kwargs['eom_ampl']
                #
                #
                #
                #     pihalf_dur =self.kwargs['pihalf_dur'] #0.0135
                #     hahn_echo_tau = 0.075 # temp thing to make pi instead of first pi/2
                #
                #     pi_dur = self.kwargs['pi_dur'] #0.027
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     mw_freq = self.frequencies[0]
                #     mw_delay = self.kwargs['mw_delay']#213ns (was 180ns) delay betweenn first optical pulse and MW pulse (measured from aom_Ex open)
                #     optical_delay = self.kwargs['optical_delay'] #56ns (was 125ns) delay between optical pulses aka interferometer length
                #
                #     aom_Ex_dur = 0.02#0.02
                #     aom_delay = 0.137#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #     gauss1_begin = (optical_delay - pi_dur) / 2 #14.5ns - time between first opt pi begin and mw pi begin
                #     remaining_optical = opt_pi_dur - (gauss1_begin) # 0.025583333333333333 ns
                #     remaining_mw_dur = pi_dur - remaining_optical
                #     wait2 = hahn_echo_tau-gauss1_begin # 60.5ns
                #
                #     wait1 = 0.007 # 0.007000000000000018 ns delay between second aom_Ex and MW pi/2
                #     wait2 = aom_delay - (optical_delay-aom_Ex_dur) - aom_Ex_dur - wait1 - pihalf_dur
                #
                #
                #     # wait3 = gauss1_begin #14.5ns
                #     wait4 = hahn_echo_tau-gauss1_begin-opt_pi_dur #0.020416666666666666
                #
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #
                #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_1')  #20 ns. AOM for the first pulse
                #
                #     self.mcas.asc(length_mus=optical_delay-aom_Ex_dur, name='wait_1.1')# 36ns ns. Delay between first and second AOM_Ex pulses
                #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True,
                #                   name='Ex_aom_2')  # 20 ns. AOM for the first puls
                #
                #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(0.007), name='wait_1') #7ns
                #
                #
                #     self.mcas.asc(
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #         length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #         name='MW_pihalf')#13.5ns. First pi/2 pulse
                #
                #     self.mcas.asc(length_mus=0.0605, name='wait_2')
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[eom_ampl]),
                #         length_mus=E.round_length_mus_full_sample(opt_pi_dur),
                #         name='Gauss1') #14.5 ns. First EOM Pulse
                #
                #
                #     self.mcas.asc(length_mus=optical_delay - opt_pi_dur, name='wait_3') #14.5ns wait before second optical pi pulse
                #
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[eom_ampl]),
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #
                #         length_mus=pi_dur, # 0.04008333333333333 ns Second EOM pulse starts
                #         name='Gauss2_MW')
                #
                #     already_written_samples = np.around(pi_dur * __SAMPLE_FREQUENCY__).astype(int)
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[eom_ampl]),
                #
                #         wf_start = already_written_samples,
                #         length_mus=opt_pi_dur-pi_dur, # 0.013083333333333332 ns Second EOM pulse starts
                #         name='Gauss2end')
                #
                #
                #     self.mcas.asc(length_mus= 0.1165 - (opt_pi_dur-pi_dur), name='wait4')#111.91666666666664 ns
                #
                #     if 'tau_bell' in self.kwargs.keys():
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq,
                #                        amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(self.kwargs['tau_bell']),
                #             name='tau_bell')  # 14.5ns. Second pi/2 pulse
                #
                #
                #     self.mcas.asc(length_mus=self.laser_dur,name='wait_before_memory') #100ns
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory') #160ns
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'entanglement':
                #     pihalf_dur =self.kwargs['pihalf_dur'] #0.0135
                #     hahn_echo_tau = 0.075 # self.kwargs['hahn_echo_tau'] #373ns
                #
                #     pi_dur = self.kwargs['pi_dur'] #0.027
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     mw_freq = self.frequencies[0]
                #     mw_delay = self.kwargs['mw_delay']#190ns (was 180ns) delay betweenn first optical pulse and MW pulse (measured from aom_Ex open)
                #     optical_delay = self.kwargs['optical_delay'] #56ns (was 125ns) delay between optical pulses aka interferometer length
                #
                #     aom_Ex_dur = 0.02#0.02
                #     aom_delay = 0.137#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #     gauss1_begin = (optical_delay - pi_dur) / 2 #14.5ns - time between first opt pi begin and mw pi begin
                #     remaining_optical = opt_pi_dur - (gauss1_begin) # 0.025583333333333333 ns
                #     remaining_mw_dur = pi_dur - remaining_optical
                #     wait2 = hahn_echo_tau-gauss1_begin # 60.5ns
                #     wait1 = aom_delay-optical_delay-wait2-pihalf_dur # 0.007000000000000018 ns delay between second aom_Ex and MW pi/2
                #     wait3 = gauss1_begin #14.5ns
                #     wait4 = hahn_echo_tau-gauss1_begin-opt_pi_dur #0.020416666666666666
                #
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_1')  #20 ns. AOM for the first pulse
                #     self.mcas.asc(length_mus=optical_delay-aom_Ex_dur, name='wait_1.1')# 56ns ns. Delay between first and second AOM_Ex pulses
                #     self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_2')  #20 ns. AOM for the first puls
                #
                #     self.mcas.asc(length_mus=E.round_length_mus_full_sample(wait1), name='wait_1') #7ns
                #
                #
                #     self.mcas.asc(
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #         length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #         name='MW_pihalf')#13.5ns. First pi/2 pulse
                #
                #     self.mcas.asc(length_mus=wait2, name='wait_2')
                #
                #
                #
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[self.kwargs['eom_ampl']]),
                #         length_mus=E.round_length_mus_full_sample(gauss1_begin),
                #         name='Gauss1_begin') #14.5 ns. First EOM Pulse
                #
                #     already_written_samples = np.around((gauss1_begin) * __SAMPLE_FREQUENCY__).astype(int) # 174samples
                #     self.mcas.asc(
                #         pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #         wf_start=already_written_samples,
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #         length_mus=remaining_optical, #0.025583333333333333 ns. MW pi starts, first optical pi finishes
                #         name='Gauss1_end_MW')
                #
                #     self.mcas.asc(
                #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #         length_mus=E.round_length_mus_full_sample(remaining_mw_dur), # 00.0014166666666666668 MW pi ends
                #         name='remaining_mw')
                #
                #     self.mcas.asc(length_mus=wait3, name='wait_3') #14.5ns wait before second optical pi pulse
                #
                #
                #     self.mcas.asc(
                #         pd2g2=dict(
                #             type='gauss',
                #             inv_fwhm=1,
                #             amplitudes=[self.kwargs['eom_ampl']]),
                #
                #         length_mus=opt_pi_dur, # 0.04008333333333333 ns Second EOM pulse starts
                #         name='Gauss2')
                #
                #
                #     self.mcas.asc(length_mus=wait4, name='wait4')#111.91666666666664 ns
                #
                #     if 'readout_state' in self.kwargs.keys():
                #         if self.kwargs['readout_state']:
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(3*pihalf_dur),
                #                 name='_MW_3pihalf_2')  # 43.5ns. Second pi/2 pulse
                #         else:
                #             self.mcas.asc(
                #                 pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #                 length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #                 name='_MW_pihalf_2')  # 14.5ns. Second pi/2 pulse
                #
                #     else:
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #             name='MW_pihalf_2')  # 14.5ns. Second pi/2 pulse
                #
                #     self.mcas.asc(length_mus=self.laser_dur,name='wait_before_memory') #100ns
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory') #160ns
                #
                #
                #
                #     # pihalf_dur =self.kwargs['pihalf_dur'] #0.0135
                #     # hahn_echo_tau = 0.148 # self.kwargs['hahn_echo_tau'] #373ns
                #     #
                #     # pi_dur = self.kwargs['pi_dur'] #0.027
                #     # mw_amplitude = self.kwargs['mw_amplitude']
                #     # mw_freq = self.frequencies[0]
                #     # mw_delay = self.kwargs['mw_delay']#190ns (was 180ns) delay betweenn first optical pulse and MW pulse (measured from aom_Ex open)
                #     # optical_delay = self.kwargs['optical_delay'] #56ns (was 125ns) delay between optical pulses aka interferometer length
                #     #
                #     # aom_Ex_dur = 0.015#0.02
                #     # aom_delay = 0.155#0.137
                #     # opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #     #
                #     # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #     # self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_1') #15 ns. AOM for the first pulse
                #     #
                #     #
                #     #
                #     #
                #     # #wait1_2 = hahn echo delay - Gauss1_begin - wait2 - Ex_aom_2 ##Names of blocks below
                #     # wait1_2 = hahn_echo_tau-(E.round_length_mus_full_sample(mw_delay-aom_Ex_dur-aom_delay))-(aom_delay-(optical_delay - aom_Ex_dur)-aom_Ex_dur)-aom_Ex_dur
                #     # # wait1_1 = delay_between_two_aoms - wait1_2 -pihalf_dur
                #     # wait1_1 = (optical_delay-aom_Ex_dur)-wait1_2 -pihalf_dur
                #     #
                #     # self.mcas.asc(length_mus=wait1_1, name='wait_1.1')# 13.5 ns. Delay between first AOM_Ex pulse and MW pi/2
                #     # self.mcas.asc(
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #     name='MW_pihalf_1')#13.5ns. First pi/2 pulse
                #     # self.mcas.asc(length_mus=wait1_2, name='wait_1.2')#14 ns. Delay between MW pi/2 and the second AOM_Ex pulse
                #     #
                #     #
                #     #
                #     #
                #     # self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_2') #15 ns. The second AOM pulse
                #     # self.mcas.asc(length_mus=aom_delay-(optical_delay - aom_Ex_dur)-aom_Ex_dur, name='wait_2') #99ns
                #     #
                #     # self.mcas.asc(
                #     #     pd2g2=dict(
                #     #         type='gauss',
                #     #         inv_fwhm=1,
                #     #         amplitudes=[self.kwargs['eom_ampl']]),
                #     #     length_mus=E.round_length_mus_full_sample(mw_delay-aom_Ex_dur-aom_delay),
                #     #     name='Gauss1_begin') #20ns. First EOM Pulse
                #     #
                #     # already_written_samples = np.around((mw_delay-aom_Ex_dur-aom_delay) * __SAMPLE_FREQUENCY__).astype(int)
                #     # remaining_optical = opt_pi_dur - (mw_delay-aom_Ex_dur-aom_delay) # 20.083333333333342 ns
                #     # self.mcas.asc(
                #     #     pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #     #     wf_start=already_written_samples,
                #     #
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=remaining_optical, #20.083333333333342 ns. MW pi starts, first optical pi finishes
                #     #     name='Gauss1_end_MW')
                #     # # print ('remaining_optical ',remaining_optical)
                #     # self.mcas.asc(
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=E.round_length_mus_full_sample(pi_dur - remaining_optical), # 6.920000000000002 ???? for some reason was written this: 8.91666666666666ns MW pi finishes
                #     #     name='MW_pi_residual')
                #     # wait3_1 = optical_delay+aom_Ex_dur+aom_delay-(mw_delay+pi_dur)
                #     # self.mcas.asc(length_mus=wait3_1, name='wait_3_1') #9ns for some reason was written 7ns
                #     # self.mcas.asc(
                #     #     pd2g2=dict(
                #     #         type='gauss',
                #     #         inv_fwhm=1,
                #     #         amplitudes=[self.kwargs['eom_ampl']]),
                #     #     length_mus=481 * 1. / __SAMPLE_FREQUENCY__, #40ns. Second EOM pulse
                #     #     name='Gauss2')
                #     #
                #     # wait3_2 = hahn_echo_tau - wait3_1 - opt_pi_dur
                #     # self.mcas.asc(length_mus=wait3_2, name='wait3_2')#98.917ns
                #     #
                #     # if 'readout_state' in self.kwargs.keys():
                #     #     if self.kwargs['readout_state']:
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             length_mus=E.round_length_mus_full_sample(3*pihalf_dur),
                #     #             name='_MW_3pihalf_2')  # 14.5ns. Second pi/2 pulse
                #     #     else:
                #     #         self.mcas.asc(
                #     #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #             name='_MW_pihalf_2')  # 14.5ns. Second pi/2 pulse
                #     #
                #     # else:
                #     #     self.mcas.asc(
                #     #         pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #         length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #         name='MW_pihalf_2')  # 14.5ns. Second pi/2 pulse
                #     #
                #     # self.mcas.asc(length_mus=self.laser_dur,name='wait_4') #100ns
                #     # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory') #160ns
                #
                #     # self.mcas.asc(
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #     name='MW_pihalf_1',
                #     # )
                #     # self.mcas.asc(length_mus=0.033, name='wait_0')# 33.5ns
                #     # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #     # self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_1') #20ns
                #     # self.mcas.asc(length_mus=optical_delay - aom_Ex_dur, name='wait_1')#105ns
                #     # self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_2')#20ns
                #     # self.mcas.asc(length_mus=aom_delay-aom_Ex_dur-(optical_delay - aom_Ex_dur), name='wait_2') #12ns
                #     #
                #     #
                #     # self.mcas.asc(
                #     #     pd2g2=dict(
                #     #         type='gauss',
                #     #         inv_fwhm=1,
                #     #         amplitudes=[self.kwargs['eom_ampl']]),
                #     #     length_mus=E.round_length_mus_full_sample(mw_delay-aom_Ex_dur-aom_delay), #23ns
                #     #     name='Gauss1')
                #     #
                #     # already_written_samples = np.around((mw_delay-aom_Ex_dur-aom_delay) * __SAMPLE_FREQUENCY__).astype(int)
                #     # remaining_optical = opt_pi_dur - (mw_delay-aom_Ex_dur-aom_delay) #17ns
                #     # self.mcas.asc(
                #     #     pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #     #     wf_start=already_written_samples,
                #     #
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=remaining_optical, #17ns
                #     #     name='Gauss1_MW')
                #     #
                #     # self.mcas.asc(
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=E.round_length_mus_full_sample(pi_dur - remaining_optical), #12ns
                #     #     name='MW_pi_residual')
                #     #
                #     # self.mcas.asc(length_mus=optical_delay+aom_Ex_dur+aom_delay-(mw_delay+pi_dur), name='wait_3') #73ns
                #     # self.mcas.asc(
                #     #     pd2g2=dict(
                #     #         type='gauss',
                #     #         inv_fwhm=1,
                #     #         amplitudes=[self.kwargs['eom_ampl']]),
                #     #     length_mus=481 * 1. / __SAMPLE_FREQUENCY__, #40ns
                #     #     name='Gauss2')
                #     #
                #     # self.mcas.asc(length_mus=self.laser_dur,name='wait_4') #100ns
                #     # self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory') #160ns
                #     # self.mcas.asc(
                #     #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #     #     length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #     #     name='MW_pihalf_2',
                #     # )
                # elif 'nuc' in self.kwargs.keys() and self.kwargs['nuc'] == 'HOM':
                #
                #     pihalf_dur =self.kwargs['pihalf_dur']
                #     hahn_echo_tau = 0.148#self.kwargs['hahn_echo_tau'] #373ns
                #
                #     pi_dur = self.kwargs['pi_dur']
                #     mw_amplitude = self.kwargs['mw_amplitude']
                #     mw_freq = self.frequencies[0]
                #     mw_delay = self.kwargs['mw_delay']#190ns (was 180ns) delay betweenn first optical pulse and MW pulse (measured from aom_Ex open)
                #     optical_delay = self.kwargs['optical_delay'] #56ns (was 125ns) delay between optical pulses aka interferometer length
                #
                #     aom_Ex_dur = 0.015#0.02
                #     aom_delay = 0.155#0.137
                #     opt_pi_dur = 481 * 1. / __SAMPLE_FREQUENCY__
                #
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # 160ns Gated counter
                #
                #     for i in range(self.kwargs['n_repetitions']):
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_1') #15 ns. AOM for the first pulse
                #
                #         #wait1_2 = hahn echo delay - Gauss1_begin - wait2 - Ex_aom_2 ##Names of blocks below
                #         wait1_2 = hahn_echo_tau-(E.round_length_mus_full_sample(mw_delay-aom_Ex_dur-aom_delay))-(aom_delay-(optical_delay - aom_Ex_dur)-aom_Ex_dur)-aom_Ex_dur
                #         # wait1_1 = delay_between_two_aoms - wait1_2 -pihalf_dur
                #         wait1_1 = (optical_delay-aom_Ex_dur)-wait1_2 -pihalf_dur
                #
                #         self.mcas.asc(length_mus=wait1_1, name='wait_1.1')# ns. Delay between first AOM_Ex pulse and MW pi/2
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pihalf_dur),
                #             name='MW_pihalf_1')#14.5ns. First pi/2 pulse
                #         self.mcas.asc(length_mus=wait1_2, name='wait_1.2')#14 ns. Delay between MW pi/2 and the second AOM_Ex pulse
                #
                #         self.mcas.asc(length_mus=aom_Ex_dur, aom_Ex=True, name='Ex_aom_2') #15 ns. The second AOM pulse
                #         self.mcas.asc(length_mus=aom_delay-(optical_delay - aom_Ex_dur)-aom_Ex_dur, name='wait_2') #99ns
                #
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[self.kwargs['eom_ampl']]),
                #             length_mus=E.round_length_mus_full_sample(mw_delay-aom_Ex_dur-aom_delay),
                #             name='Gauss1_begin') #20ns. First EOM Pulse
                #
                #         already_written_samples = np.around((mw_delay-aom_Ex_dur-aom_delay) * __SAMPLE_FREQUENCY__).astype(int)
                #         remaining_optical = opt_pi_dur - (mw_delay-aom_Ex_dur-aom_delay) # 20.083333333333342 ns
                #         self.mcas.asc(
                #             pd2g2=dict(type='gauss', inv_fwhm=1, amplitudes=[self.kwargs['eom_ampl']]),
                #             wf_start=already_written_samples,
                #
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=remaining_optical, #20.083333333333342 ns. MW pi starts, first optical pi finishes
                #             name='Gauss1_end_MW')
                #         # print ('remaining_optical ',remaining_optical)
                #         self.mcas.asc(
                #             pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
                #             length_mus=E.round_length_mus_full_sample(pi_dur - remaining_optical), # 8.91666666666666ns MW pi finishes
                #             name='MW_pi_residual')
                #         wait3_1 = optical_delay+aom_Ex_dur+aom_delay-(mw_delay+pi_dur)
                #         self.mcas.asc(length_mus=wait3_1, name='wait_3_1') #7ns
                #         self.mcas.asc(
                #             pd2g2=dict(
                #                 type='gauss',
                #                 inv_fwhm=1,
                #                 amplitudes=[self.kwargs['eom_ampl']]),
                #             length_mus=481 * 1. / __SAMPLE_FREQUENCY__, #40ns. Second EOM pulse
                #             name='Gauss2')
                #         self.mcas.asc(length_mus=0.1, name='wait3_2')
                #
                #
                #     self.mcas.asc(length_mus=self.laser_dur,name='wait_4') #100ns
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True, name='memory') #160ns

                ### ===============================
                ### Conventional repetitive readout
                ### ===============================
                else:
                    # print('snipets_else')
                    self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, gate=True, name='gate1')  # Gated counter

                    self.mcas.asc(length_mus=self.dur_step[alt_step][5], green=True, name='Laser', **aa)

                self.mcas.asc(length_mus=self.dur_step[alt_step][6], name='Count', **aa)

                # if self.gate_or_trigger != 'trigger':
                #     print('self.gate_or_trigger != trigger')
                #     pass
                #     self.mcas.asc(length_mus=__TT_TRIGGER_LENGTH__, memory=True)

                if 'buffer_time' in self.kwargs.keys():
                    self.mcas.asc(length_mus=self.kwargs['buffer_time'], name = 'Buffer')




def ssr(mcas,queue,**kwargs):
    s = SSR(mcas = mcas, queue=queue, **kwargs)
    s.compile()
    if not 'step_idx' in kwargs:
        raise Exception('SSR step index must be given, or the gated counter wont know how to readout and treat the data.')
    if kwargs['step_idx'] is not None:
        queue._gated_counter.trace.analyze_sequence[kwargs['step_idx']][3] = s.repetitions * s.number_of_alternating_steps
        queue._gated_counter.trace.analyze_sequence[kwargs['step_idx']][5] = s.number_of_alternating_steps
        if queue._gated_counter.trace.analyze_sequence[kwargs['step_idx']][5] != 1 and queue._gated_counter.trace.analyze_sequence[kwargs['step_idx']][2] == 'auto':
            queue._gated_counter.trace.analyze_sequence[kwargs['step_idx']][2] = 0

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

# def ssr_single_state(mcas, state, **kwargs):
#     if (len(state) == 1 and state !='qutrit') or len(state) == len(state.lstrip('n')) == 3:
#         wave_file_kwargs = kwargs.pop(
#             'wave_file_kwargs',
#             [
#                 dict(
#                     filepath=kwargs.get('wfpd', wfpd_standard)[state],
#                     rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)
#                 ),
#                 dict(
#                     filepath=kwargs.get('wfpd_all_but', wfpd_all_but_standard)[state],
#                     rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)
#                 ),
#             ]
#         )
#         if (len(state) == 1 and state !='qutrit'):
#             nuc = '14n'
#         else:
#             nuc = '13c90'
#     else:
#         if state == 'qutrit':
#             nuc = '14n'
#             wfksl = ['+', '0', '-']
#         else:
#             nuc = '13c414' if len(state) == 2 else '13c90'
#             wfksl = [state.lstrip('n')]
#             wfksl.append({'+': '-', '-': '+'}[wfksl[0]])
#         if 'wave_file_kwargs' in kwargs:
#             wave_file_kwargs = kwargs.pop('wave_file_kwargs')
#         else:
#             wave_file_kwargs =[
#                 dict(
#                     filepath=kwargs.get('wfpd', wfpd_standard)[wfks],
#                     rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)
#                 ) for wfks in wfksl]
#     ssr(mcas,
#         transition='left',
#         robust=True,
#         laser_dur=kwargs.pop('laser_dur', __LASER_DUR_DICT__.get(state, __LASER_DUR_DICT__['single_state'])),
#         mixer_deg=-90,
#         nuc=kwargs.pop('nuc', nuc),
#         frequencies=kwargs.pop('frequencies', [pi3d.tt.mfl({'14n': [0]}) for i in range(len(wave_file_kwargs))]),
#         wave_file_kwargs=wave_file_kwargs, **kwargs
#     )