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
import misc

import collections
from qutip_enhanced import *

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

__WAIT_TIME_SEGMENT_LENGTH_MUS__ = 320/12e3

def length_mus(factor, mixer_deg, amp0):
    return E.round_length_mus_full_sample(pi3d.tt.rp('e_rabi', mixer_deg=mixer_deg, amp=1.0).period*factor/float(amp0))

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            sna.init_13c(mcas, s='90', state=_I_['init_13c90'], new_segment=True)
            sna.init_13c(mcas, s='414', state=_I_['init_13c414'], new_segment=True)
            sna.init_14N(mcas, mn=_I_['init_14n'], new_segment=True)
            freq = pi3d.tt.mfl({'14N': [{'+1': +1, '0': 0, '-1': -1}[_I_['init_14n']]], '13c414': [{'+': +.5, '-': -.5}[_I_['init_13c414']]], '13c90': [{'+': +.5, '-': -.5}[_I_['init_13c90']]]}, ms_trans=['left', 'right'][_I_['transition']])
            sna.ssr(mcas, frequencies=freq, nuc='13c90', robust=True, repetitions=int(450), mixer_deg=75)

            sna.electron_rabi(
                mcas,
                new_segment=True,
                length_mus=length_mus(factor=_I_['factor'], mixer_deg=_I_['mixer_deg'], amp0=_I_['amp0']),
                amplitudes=[float(_I_['amp0'])],
                frequencies=0.0,
                mixer_deg=_I_['mixer_deg']
            )
            if idx == 0:
                mcas.start_new_segment('14n+1_ms0_pi_pulse', reuse_segment=False)
                t = '14n+1 ms0'
                a = 1.0
                sna.nuclear_rabi(mcas,
                                 name=t,
                                 amplitudes=[a],
                                 length_mus=pi3d.tt.rp(t, amp=a).pi,
                                 frequencies=[pi3d.tt.t(t).current_frequency],
                                 new_segment=False,
                                 )
            else:
                mcas.start_new_segment('14n+1_ms0_pi_pulse', reuse_segment=True)

            sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14n': [0]}), pi3d.tt.mfl({'14n': [+1, -1]})], nuc='14n', transition='left', robust=True, mixer_deg=75)
        return mcas
    return ret_mcas

def settings(pdc):
    ana_seq = [
        ['init', '<', 'auto', 450, 1, 1],
        ['init', '>', -1, 1, 1, 1],
        ['result', '<', 0, 1200, 1, 2],
        ['init', '>', -1, 1, 1, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code,
        script_path=__file__,
    )
    pi3d.gated_counter.points = 8000
    nuclear.analyze_type = 'standard'
    nuclear.odmr_interval = 20
    nuclear.maximum_odmr_drift = 0.02
    nuclear.refocus_interval = 2

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('init_13c90', ['+']),
            ('init_13c414', ['+']),
            ('init_14n', ['0']),
            ('transition', [0]),
            ('mixer_deg', [-90]),
            ('amp0', ["{:.6f}".format(i) for i in E.round_to_amplitude_granularity([i for i in np.linspace(0.0, 1.0, 20) if i != 0.0 and i > 0.15])]),
            ('factor', np.linspace(0.0, 10, 79))
        )
    )

    for md in nuclear.parameters['mixer_deg']:
        nuclear.file_notes += "{}\t{}\n".format('mixer_deg', pi3d.tt.rp('e_rabi', mixer_deg=md, amp=1.0).period)

    nuclear.number_of_simultaneous_measurements = 1 #len(nuclear.parameters['factor'])

def run_fun(abort, **kwargs):

    settings({})
    nuclear.debug_mode = False
    if len(nuclear.parameters['amp0']) <= 2:
        print('WARNING: Not enough amplitudes. Will not be saved for TransitionTracker. {}'.format(nuclear.parameters['amp']))
    nuclear.run(abort)

#     if len(nuclear.parameters['amp0']) > 2 and not nuclear.debug_mode and len(nuclear.iterator_df) == 0:
#         data = dh.Data(parameter_names=['mixer_deg'] + [pn for pn in nuclear.parameters.keys() if pn.startswith('amp')] + ['transition'],
#                          observation_names=['omega', 'date'],
#                          dtypes=dict(omega='float', date='str'))
#         data.init()
#
#         for md in nuclear.parameters['mixer_deg']:
#             data.append(collections.OrderedDict([('mixer_deg', md), ('amp0', '0.000000'), ('transition', 0)]))
#             data.set_observations([dict(omega='0.000000',
#                                         date=pd.to_datetime('now').__str__())])
#
#         for d, d_idx, idx, df_sub in nuclear.data.iterator(data.parameter_names):
#             parameter_table_selected_data = nuclear.pld.parameter_table_selected_data
#             parameter_table_selected_data.update(collections.OrderedDict([('sweeps', [])]))
#             parameter_table_selected_data.update(collections.OrderedDict([(key, [val]) for key, val in d.items()]))
#             nuclear.pld.update_parameter_table_selected_data(parameter_table_selected_data)
#             nuclear.pld.update_fit_results()
#             data.append(d)
#             data.set_observations([dict(omega="{:.6f}".format(1 / length_mus(factor=nuclear.pld.fit_results[0][1].params['T'].value, mixer_deg=d['mixer_deg'], amp0=d['amp0'])),
#                                         date=pd.to_datetime('now').__str__())])
#
#
#         for d, d_idx, idx, sub in data.iterator(['mixer_deg']):
#             sub = sub.drop('mixer_deg', axis=1)
#             if len(sub) == len(nuclear.parameters['amp0']) + 1 and len(sub) > 3:
#                 print('Updating e_rabi {}'.format(d))
#                 pi3d.tt.rabi_parameters["e_rabi_ou{:.0f}deg{}".format(1000 * pi3d.awgs['2g'].ch[1].output_amplitude, d['mixer_deg'])].update_file(sub)
#
#
# def rp(md):
#     return pi3d.tt.rabi_parameters['e_rabi_ou400deg{}'.format(md)]
#
# def arf(md):
#     return rp(md).amp_rabi_freq
#
# def dff(md):
#     o = data.df[data.df.mixer_deg == md]
#     return o
#
# def tf(i):
#     return np.array(i, dtype=float)
#
# fig, ax = plt.subplots(1,1)
# ax.plot(arf(-90)[0], arf(-90)[1], color='black')
# ax.plot(arf(75)[0], arf(75)[1],  color='red')
# ax.plot(tf(dff(75).amp0), tf(dff(75).omega), 'o', color='red')
# ax.plot(tf(dff(-90).amp0), tf(dff(-90).omega), 'o', color='black')