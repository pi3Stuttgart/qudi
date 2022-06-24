
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
import UserScripts.helpers.shared as ush;reload(ush)
import collections
import pym8190a
from qutip_enhanced import *

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

wave_file = [
    r"\\PI3-PC161\d\Python\pi3diamond\UserScripts\Robust\multi_nuc_pi\20180904-h19m46s00selective_nuclear_piFN6.59e-05\RF.dat"
]

wfd = dict()
for pn, wfpath in enumerate(wave_file):
    wfd[pn] = pym8190a.elements.WaveFile(
        filepath=wfpath,
        rp=pi3d.tt.rp('13c ms0'),
    )

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            sms = sch.ret_sms(transition= '13c90 ms-1'),
            sna.polarize(mcas, new_segment=True)
            mcas.asc(length_mus=0.5)
            sna.single_robust_electron_pi(mcas,
                                              nuc='all',
                                              transition='left',
                                              frequencies=pi3d.tt.mfl({'14n': [0]}, ms_trans='-1'),
                                              new_segment=True,
                                              )
            mcas.asc(length_mus=0.5)
            # sna.nuclear_rabi(mcas,
            #                  new_segment=True,
            #                  amplitudes=[_I_['amp']],
            #                  name=pdc['transition'],
            #                  frequencies=[pi3d.tt.t(pdc['transition']).current_frequency],
            #                  length_mus=E.round_length_mus_full_sample(_I_['x'] / _I_['amp']))

            # NUCLEAR PI PULSE
            base_frequency = _I_['frequency_offset']
            base_frequency += pi3d.tt.t('13c90 ms-1').current_frequency
            sna.nuclear_rabi(
                    mcas,
                    name='pi',
                    frequencies=base_frequency + np.array([pi3d.tt.hf_para_n['13c-6'], pi3d.tt.hf_para_n['13c-5'], pi3d.tt.hf_para_n['13c6'], pi3d.tt.hf_para_n['13c13']]),
                    amplitudes=[pi3d.tt.rp('13c ms0', period=2 * _I_['t_pi']).amp],
                    length_mus=_I_['t_pi'],
                    new_segment=True,
                )


            ssr_frequencies = [
                pi3d.tt.mfl('13C90' + '_left'),
                pi3d.tt.mfl('13C90' + '_right')
            ]
            sna.ssr(mcas, frequencies=ssr_frequencies, nuc='13C90', transition='left', robust=True, mixer_deg=-90, step_idx=0)


            # Was before in Sebastian'S RUN.
            # d = {'14n+1': dict(frequencies=[pi3d.tt.mfl({'14n': [+1]}), pi3d.tt.mfl({'14n': [0, -1]})] , nuc='14N'),
            #      '14n0':  dict(frequencies=[pi3d.tt.mfl({'14n': [0]}), pi3d.tt.mfl({'14n': [+1, -1]})], nuc='14N'),
            #      '14n-1': dict(frequencies=[pi3d.tt.mfl({'14n': [-1]}), pi3d.tt.mfl({'14n': [+1, 0]})], nuc='14N'),
            #      '14n': dict(frequencies=[pi3d.tt.mfl({'14N': [+1]}), pi3d.tt.mfl({'14N': [0]}), pi3d.tt.mfl({'14N': [-1]})], nuc='14N'),
            #      '13c414': dict(frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5]}),
            #                                  pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [-.5]})], nuc='13C414'),
            #      '13c90':  dict(frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5]}),
            #                                  pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [-.5]})], nuc='13C90'),
            #      }
            # sna.ssr(mcas,
            #         transition='left',
            #         robust=True,
            #         repetitions=_I_['repetitions'],
            #         mixer_deg=-90,
            #         step_idx=0,
            #         **d[_I_['transition']])
            # #sna.polarize_red(mcas, new_segment=True)
            # sna.polarize_green(mcas, new_segment=False, length_mus=0.2)
            # base_frequency = _I_['frequency_offset']
            # if _I_['e_pi']:
            #     mcas.asc(length_mus=0.5)
            #     sna.single_robust_electron_pi(mcas, nuc='all', frequencies=pi3d.tt.mfl('14N0'))
            #     mcas.asc(length_mus=0.5)
            #     base_frequency += pi3d.tt.t('13c90 ms-1').current_frequency
            # else:
            #     base_frequency += pi3d.tt.t('13c ms0').current_frequency
            # sna.nuclear_rabi(
            #     mcas,
            #     name='pi',
            #     frequencies=base_frequency + np.array([pi3d.tt.hf_para_n['13c-6'], pi3d.tt.hf_para_n['13c-5'], pi3d.tt.hf_para_n['13c6'], pi3d.tt.hf_para_n['13c13']]),
            #     amplitudes=[pi3d.tt.rp('13c ms0', period=2 * _I_['t_pi']).amp],
            #     length_mus=_I_['t_pi'],
            #     new_segment=True,
            # )




        return mcas
    return ret_mcas

def settings(pdc):
    ana_seq = [
        ['result', '<', 0, 100, 0, 2],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code,
        script_path=__file__,
    )
    pi3d.gated_counter.trace.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0, 1]
    pi3d.gated_counter.trace.average_results = True
    nuclear.refocus_moving_average_factor = 1

    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 1
    nuclear.maximum_odmr_drift = 0.02
    nuclear.number_of_simultaneous_measurements = 1

    #????
    pi3d.gated_counter.n_values = 1200 * 1500
    pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values % pi3d.gated_counter.trace.binning_factor




    nuclear.parameters = collections.OrderedDict(
        (
            ('sweeps', range(10)),
            ('transition', ['13c90']),
            ('e_pi', [True]),
            ('t_pi', [787]),
            # ('e_pi', [False]),
            ('repetitions', [2000]),
            ('frequency_offset', np.arange(-0.014, 0.008, 0.0004)),
        )
    )



def run_fun(abort, **kwargs):

    nuclear.debug_mode = False
    #pi3d.gated_counter.number_of_memories = 2
    #pi3d.gated_counter.trace.average_results=True
    #pi3d.gated_counter.trace.binning_factor = 1
    #pi3d.gated_counter.n_values = 1200*1500
    #pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values%pi3d.gated_counter.trace.binning_factor
    settings({})
    nuclear.run(abort)
