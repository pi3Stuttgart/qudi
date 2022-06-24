from __future__ import print_function, absolute_import, division
from imp import reload

import numpy as np
import time, datetime, os, itertools
import UserScripts.helpers.sequence_creation_helpers as sch
reload(sch)
import multi_channel_awg_seq as MCAS
reload(MCAS)
import UserScripts.helpers.snippets_awg as sna
reload(sna)
from pi3diamond import pi3d
import more_itertools
import UserScripts.helpers.shared as ush;reload(ush)
import pandas as pd
from collections import OrderedDict
import AWG_M8190A_Elements as E

try:
    seq_name = os.path.basename(__file__).split('.')[0]
    nuclear = sch.create_nuclear(seq_name)
except:
    seq_name = 'NOSEQNAME'


__WAIT_TIME_SEGMENT_LENGTH_MUS__ = 320/12e3

tt = pi3d.tt
gated_counter = pi3d.gated_counter


max_dur = 5000
rabi_full_amp_amplitudes = np.linspace(0, 1, 50)
rabi_full_amp_number_of_oscillations = 5

def rabi_x(pdc):
    nofp = 0.0 # 0.1 if '13C90' in pdc['transition'] else 0.0  #number of oscillations for first point, mainly necessary for 13C90
    oscillations = 1.5
    points_per_oscillation = 20
    est_per = tt.rp(pdc['transition'], amp=pdc[u'amp']).period
    t0 = nofp*est_per
    t1 = np.ceil((oscillations + nofp) * est_per)
    if t1 > max_dur:
        raise Exception('Error: {}, {}'.format(t1, max_dur))

    x = np.linspace(t0, t1, oscillations*points_per_oscillation)
    return E.round_length_mus_full_sample(x, sample_frequency=12.)

def rabi_stability_x(pdc):
    oscillations = [2.0, 2.5]
    points_per_oscillation = 10
    est_per = tt.rp(pdc['transition'], amp=pdc['amp']).period
    x = est_per*np.linspace(oscillations[0], oscillations[1], (oscillations[1] - oscillations[0])*points_per_oscillation)
    return E.round_length_mus_full_sample(x, sample_frequency=12.)

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            sweeps, sweeps_idx, seq_num, seq_num_idx, x, x_idx = (_I_[key] for key in ['sweeps', 'sweeps_idx', 'seq_num', 'seq_num_idx', 'x', 'x_idx'])
            sms = sch.ret_sms(transition=pdc['transition'])
            frequencies = [tt.mfl(sms['nuc']+'_left'), tt.mfl(sms['nuc']+'_right')] if '13C' in sms['nuc'] else [tt.mfl(sms['nuc']), np.delete(pi3d.tt.mfl('14N_all'), np.where(pi3d.tt.mfl('14N_all') == pi3d.tt.mfl(sms['nuc']))[0][0])]
            if sms['ms'] == '0':
                sna.polarize(mcas) #needed because of electron T1 during rf_power_safety
            else:
                if sms['nuc'] == '13C90':
                    sna.init(mcas, sms['nuc'])
                    # sna.ssr(mcas, frequencies=tt.mfl(sms['nuc'], ms_trans=sms['ms']), nuc=sms['nuc'], robust=True, repetitions=1200)
                    sna.ssr(mcas, frequencies=frequencies, nuc=sms['nuc'], robust=True, repetitions=900)
                sna.polarize(mcas)
                sna.single_robust_electron_pi(mcas,
                                              nuc='all',
                                              transition={'-1': 'left', '+1':'right'}[sms['ms']],
                                              frequencies=tt.mfl({'14N': [0]}, ms_trans=sms['ms']),
                                              )
            if pdc["mt"] in ["rabi", 'rabi_full']:
                sna.nuclear_rabi(mcas,
                                 new_segment=True,
                                 amplitudes=[pdc['amp']],
                                 name=pdc['transition'],
                                 frequencies=[pi3d.tt.t(pdc['transition']).current_frequency],
                                 length_mus=x)
            elif pdc["mt"] in ['rabi_full_amp']:
                sna.nuclear_rabi(mcas,
                                 new_segment=True,
                                 amplitudes=[x],
                                 name=pdc['transition'],
                                 frequencies=[pi3d.tt.t(pdc['transition']).current_frequency],
                                 length_mus=min(rabi_full_amp_number_of_oscillations*pi3d.tt.rp(pdc['transition'], amp=1.).period, 1000.)
                                 )
            elif pdc["mt"] == 'rabi_stability':
                pi3d.gated_counter.points = 2000
                sna.nuclear_rabi(mcas,
                                 new_segment=True,
                                 amplitudes=[pdc['amp']],
                                 name=pdc['transition'],
                                 frequencies=[pi3d.tt.t(pdc['transition']).current_frequency],
                                 length_mus=E.round_length_mus_full_sample(2.25*pi3d.tt.rp(pdc['transition'], amp=pdc['amp']).period)
                                 )
            elif pdc['mt'] == 'sweep':
                amp = 0.1
                sna.nuclear_rabi(mcas,
                                 name='freq_sweep',
                                 frequencies=[x],
                                 amplitudes=[amp],
                                 length_mus=tt.rp(pdc['transition'], amp=amp).pi
                )
            elif pdc['mt'] == 'fid':
                amp=.125
                def pi2():
                    sna.nuclear_rabi(mcas,
                                     new_segment=True,
                                     name='fidpi2',
                                     frequencies=[tt.t(pdc['transition']).current_frequency + pdc['freq_offset']],
                                     amplitudes=[amp],
                                     length_mus=tt.rp(pdc['transition'], amp=amp).pi2
                    )

                pi2()
                if x == 0.0:
                    mcas.start_new_segment(name='tau', loop_count=1)
                    mcas.asc(name='tau', length_mus=x)
                else:
                    def loop_count(x):
                        n = x/__WAIT_TIME_SEGMENT_LENGTH_MUS__
                        if np.abs(np.around(n) - n) > E.__SAMPLE_DURATION_TOLERANCE__:
                            raise Exception('Error: {}, {}, {}, {}'.format(x, n, np.around(n), n-np.around(n)))
                        return int(np.around(n))
                    mcas.start_new_segment(name='tau', loop_count=loop_count(x))
                    mcas.asc(name='tau', length_mus=__WAIT_TIME_SEGMENT_LENGTH_MUS__)
                pi2()
            sna.ssr(mcas, frequencies=frequencies, nuc=sms['nuc'], transition='left', robust=True)
        return mcas
    return ret_mcas

def settings(pdc):
    sch.settings(script_path=os.path.abspath(__file__),
                 ret_mcas=ret_ret_mcas(pdc),
                 analyze_sequence=[['result', '<', 0, 1200, 1, 2]],
                 pdc=pdc)
    pi3d.gated_counter.number_of_memories = 2
    sms = sch.ret_sms(transition=pdc['transition'])
    nuclear.analyze_type = 'consecutive'
    nuclear.initial_confocal_odmr_refocus = False
    if sms['nuc'] == '13C90':
        if sms['ms'] != '0':
            nuclear.analyze_type = 'standard'
            nuclear.ana_trace.analyze_sequence = [['init', '<', 0, 900, 1, 2],
                                                  ['result', '<', 0, 5000, 1, 2]]
    if pdc['mt'] == 'fid':
        nuclear.parameters = OrderedDict(
            (
                ('sweeps', range(500)),
                ('seq_num', range(1)),
                ('x', E.round_length_mus_full_sample(np.linspace(0, 10.0 / np.abs(pdc['freq_offset']), 60), sample_frequency=1e-3/__WAIT_TIME_SEGMENT_LENGTH_MUS__))
            )
        )
        nuclear.number_of_simultaneous_measurements = 1#len(nuclear.parameters['x'])
        nuclear.fit_function = 'Cosinus dec offset'
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_fid'
    elif pdc["mt"] in ["rabi", 'rabi_full']:
        nuclear.parameters = OrderedDict(
            (
                ('sweeps', range(5)),
                ('seq_num', range(1)),
                ('x', rabi_x(pdc))
            )
        )
        nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['x'])
        nuclear.fit_function = 'Cosinus decay'
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_rabi'
    elif pdc["mt"] in ['rabi_full_amp']:
        nuclear.parameters = OrderedDict(
            (
                ('sweeps', range(3)),
                ('seq_num', range(1)),
                ('x', rabi_full_amp_amplitudes)
            )
        )
        nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['x'])
        nuclear.fit_function = 'Cosinus decay'
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_rabi_amp'
    elif pdc['mt'] == 'sweep':
        center_freq = tt.transition(pdc['transition']).current_frequency
        nuclear.parameters = OrderedDict(
            (
                ('sweeps', range(5)),
                ('seq_num', range(1)),
                ('x', center_freq + np.linspace(-pdc['range']/2., pdc['range']/2., pdc['nsteps']))
            )
        )
        nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['x'])
        nuclear.fit_function = 'Lorentz neg'
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_sweep'
    elif pdc['mt'] == 'rabi_stability':
        nuclear.parameters = OrderedDict(
            (
                ('sweeps', range(1)),
                ('seq_num', range(1000)),
                ('x', range(250))
            )
        )
        nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['x'])
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/rabi_stability'

####################################################################################################
# predefined transition lists
####################################################################################################
transition_list = ['14N+1 mS0', '14N-1 mS0', '14N+1 mS-1', '14N-1 mS-1', '14N+1 mS+1', '14N-1 mS+1',
                   '13C414 mS0', '13C414 mS-1', '13C414 mS+1',
                   '13C90 mS-1', '13C90 mS+1']

update_tt = True

####################################################################################################
# FID
####################################################################################################
param_lists = list()
# param_lists.append(['transition', ['13C90 mS0', '13C90 mS-1', '13C414 mS-1', '14N+1 mS0', '14N+1 mS0', '14N-1 mS0', '14N+1 mS-1']])
param_lists.append(['transition', ['13C90 mS-1', '13C90 mS0']])
param_lists.append(['mt', ['fid']])
param_lists.append(['freq_offset', [-0.005]])
tl = sch.ret_tl(param_lists)
pds_fid = sch.ret_pds(param_lists, tl)

####################################################################################################

####################################################################################################
# RABI
####################################################################################################
param_lists = list()
# param_lists.append(['transition', ['14N+1 mS-1', '14N-1 mS-1', '14N+1 mS0', '14N-1 mS0']])
param_lists.append(['transition', ['14N+1 mS0']])
param_lists.append(['mt', ['rabi']])
param_lists.append(['amp', [1.0]])
tl = sch.ret_tl(param_lists)
pds_rabi14N = sch.ret_pds(param_lists, tl)

param_lists = list()
param_lists.append(['transition', ['13C414 mS-1']])
param_lists.append(['mt', ['rabi']])
param_lists.append(['amp', [1.0]])
tl = sch.ret_tl(param_lists)
pds_rabi13C = sch.ret_pds(param_lists, tl)

pds_rabi = pds_rabi13C + pds_rabi14N

####################################################################################################
# Rabi_full
####################################################################################################
param_lists = list()
rftr_list = ['13C90 mS-1']
param_lists.append(['transition', rftr_list])
param_lists.append(['mt', ['rabi_full']])
nonlinear_threshold = E.round_to_amplitude_granularity(0.4, 0.7])
absolute_threshold = 1.0
# rabi_amp = E.round_to_amplitude_granularity([nonlinear_threshold] + list(np.arange(0.0, nonlinear_threshold-1e-5, 0.05)) + [0.05] + list(np.arange(nonlinear_threshold + 0.1, 1.01, 0.1)))
amplitude_list = [0.0] + [absolute_threshold] + [nonlinear_threshold[0]] + [nonlinear_threshold[1]] + list(np.arange(0.0, nonlinear_threshold[1] - 1e-5, 0.05))[1:] + list(np.arange(nonlinear_threshold[1], 1.0, 0.1))[1:] + [1.0]
rabi_amp = list(more_itertools.unique_everseen(E.round_to_amplitude_granularity(amplitude_list)))
param_lists.append(['amp', rabi_amp])
tl = sch.ret_tl(param_lists)
pds_rabi_full = sch.ret_pds(param_lists, tl)


####################################################################################################
# Rabi_full_amp
####################################################################################################
param_lists = list()
rftr_list_amp = ['13C90 mS-1', '13C414 mS0', '13C414 mS-1']
param_lists.append(['transition', rftr_list_amp])
param_lists.append(['mt', ['rabi_full_amp']])
tl = sch.ret_tl(param_lists)
pds_rabi_full_amp = sch.ret_pds(param_lists, tl)

####################################################################################################
# RABI Stability
####################################################################################################
param_lists = list()
param_lists.append(['transition', ['13C90 mS-1']])
param_lists.append(['mt', ['rabi_stability']])
param_lists.append(['amp', [0.25]])
tl = sch.ret_tl(param_lists)
pds_rabi_stability = sch.ret_pds(param_lists, tl)

# ####################################################################################################
# #FREQUENCY SWEEP
# ####################################################################################################
param_lists = list()
param_lists.append(['transition', ['13C90 mS0', '13C90 mS-1', '13C414 mS-1']])
param_lists.append(['mt', ['sweep']])
param_lists.append(['range', [0.02]])
param_lists.append(['nsteps', [15]])
tl = sch.ret_tl(param_lists)
pds_sweep = sch.ret_pds(param_lists, tl)

pds = pds_rabi_full #pds_sweep + pds_rabi13C

if 'rabi_full' in [pdc['mt'] for pdc in pds]:
    index = pd.MultiIndex.from_tuples(list(itertools.product(*(rftr_list, ['{:.6f}'.format(rabi_amp[i]) for i in range(len(rabi_amp))]))), names=['nuc'] + ['amp0'])
    columns = ['transition', 'omega', 'date']
    result = pd.DataFrame(index=index, columns=columns).sort()
    result['transition'] = str(0)
    pi3d.result = result

def run_fun(abort, **kwargs):

    nuclear.debug_mode = True

    for i, pdc in enumerate(pds):
        if abort.is_set(): break
        print(pdc)
        if pdc['mt'] == 'rabi_full':
            lc = tuple([pdc['transition'], '{:.6f}'.format(pdc['amp'])])
            if not np.isnan(result['omega'].loc[lc]):
                print('already there')
                continue
            elif pdc['amp'] == 0.0:
                print('0.0')
                result['omega'].loc[lc] = "0.000000"
                result['date'].loc[lc] = pd.to_datetime(0, unit='s')
                continue
            elif pdc['amp'] > absolute_threshold:
                print('absolute_threshold')
                omega_absolute_threshold = float(result['omega'].loc[tuple([pdc['transition'], '{:.6f}'.format(absolute_threshold)])])
                omega_slope = omega_absolute_threshold/absolute_threshold
                result['omega'].loc[lc] = '{:.6f}'.format(omega_slope * float(lc[1]))
                result['date'].loc[lc] = result['date'].loc[tuple([pdc['transition'], '{:.6f}'.format(absolute_threshold)])]
                continue
            elif (nonlinear_threshold[0] < pdc['amp'] < nonlinear_threshold[1]) and pdc['amp'] != absolute_threshold:
                print(pdc)
                print('nonlinear_threshold')
                omega_nonlinear_threshold = [float(result['omega'].loc[tuple([pdc['transition'], '{:.6f}'.format(i)])]) for i in nonlinear_threshold]
                omega_slope = (max(omega_nonlinear_threshold) - min(omega_nonlinear_threshold))/(max(nonlinear_threshold) - min(nonlinear_threshold))
                result['omega'].loc[lc] = '{:.6f}'.format(omega_slope * float(lc[1]))
                result['date'].loc[lc] = result['date'].loc[tuple([pdc['transition'], '{:.6f}'.format(min(nonlinear_threshold))])]
                continue
            print('is measured')
        if pdc.get('amp', 0.0) >  MCAS.__MAX_RF_AMPLITUDE__:
            raise Exception('This amplitude is above the threshold!')
        settings(pdc)
        if sch.ret_sms(transition=pdc['transition'])['nuc'] == '13C90':
            gated_counter.points = 1000
        else:
            gated_counter.points = 4000
        nuclear.run(abort)
        if nuclear.current_parameters_dict_list[0]['sweeps'] > 1 or len(pi3d.nuclear_parameters.iterator_list) == 0:
            if pdc["mt"] in ["rabi", 'rabi_full']:
                if not nuclear.debug_mode:
                    nuclear.do_fit()
                    nuclear.file_notes = "per: {}".format(nuclear.fit_result.params['T'].value)
                if pdc['mt'] == 'rabi':
                    t = pdc['transition'] if not ('13C' in pdc['transition'] and 'mS0' in pdc['transition']) else '13C mS0'
                    if update_tt and not nuclear.debug_mode:
                        pi3d.tt.rabi_parameters[t].generate_linear_file(1/(nuclear.fit_result.params['T'].value*pdc['amp']))
                if pdc['mt'] == 'rabi_full':
                    if nuclear.debug_mode:
                        period = 1/pdc['amp']
                    else:
                        period = nuclear.fit_result.params['T'].value
                    result['omega'].loc[lc] = "{:.6f}".format(1/period)
                    result['date'].loc[lc] = pd.to_datetime('now').__str__()
                    print(result)
            elif pdc['mt'] == 'fid':
                nuclear.do_fit()
                nuclear.file_notes = "per: {}".format(nuclear.fit_result.params['T'].value)
                if update_tt:
                    tt.change_transition_frequency_fid(pdc['transition'], pdc['freq_offset'], nuclear.fit_result.params['T'].value)
            elif pdc['mt'] == 'sweep':
                nuclear.do_fit()
            nuclear.save()
    if not abort.is_set() and 'rabi_full' in [pdc['mt'] for pdc in pds] and update_tt:
        for transition in rftr_list:
            rpn = '13C mS0' if transition in ['13C90 mS0', '13C414 mS0'] else transition
            pi3d.tt.rabi_parameters[rpn].update_file(result.loc[transition].sort())
    pi3d.gated_counter.number_of_memories = 1
