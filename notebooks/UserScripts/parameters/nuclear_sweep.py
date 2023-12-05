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
import lmfit.models

import collections
from qutip_enhanced import *

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

__WAIT_TIME_SEGMENT_LENGTH_MUS__ = 320/12e3

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():

            pi3d.gated_counter.trace.consecutive_valid_result_numbers = [1, 2] if '14n-1' in _I_['transition'].lower() else [0, 1]

            sms = sch.ret_sms(transition=_I_['transition'])
            sna.polarize(mcas, new_segment=True)  # needed because of electron T1 during rf_power_safety
            if sms['ms'] != '0':
                sna.single_robust_electron_pi(mcas,
                                              nuc='all',
                                              transition={'-1': 'left', '+1': 'right'}[sms['ms']],
                                              frequencies=pi3d.tt.mfl({'14n': [0]}, ms_trans=sms['ms']),
                                              new_segment=True,
                                              )
            def pi():
                try:
                    amp = pi3d.tt.rp(_I_['transition'], omega=pdc['max_rabi_freq']).amp
                except:
                    amp = 1.0
                    print("Amplitude set to 1.0, the desired max_rabi_freq could not be reached, probably due to power constraints.")

                sna.nuclear_rabi(mcas,
                                 new_segment=True,
                                 amplitudes=[amp],
                                 name=_I_['transition'],
                                 frequencies=[pi3d.tt.t(_I_['transition']).current_frequency + _I_['x']],
                                 length_mus=pi3d.tt.rp(_I_['transition'], amp=amp).pi)
            pi()
            ssr_frequencies = [pi3d.tt.mfl(sms['nuc'] + '_left'), 
                               pi3d.tt.mfl(sms['nuc'] + '_right')] if '13c' in sms['nuc'] else [pi3d.tt.mfl({'14N': [+1]}), pi3d.tt.mfl({'14N': [0]}), pi3d.tt.mfl({'14N': [-1]})]
            sna.ssr(mcas, frequencies=ssr_frequencies, nuc=sms['nuc'], transition='left', robust=True, mixer_deg=-90, step_idx=0)
        return mcas
    return ret_mcas

def settings(pdc):
    ana_seq = [
        ['result', '<', 0, 123, 0, 2],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code,
        script_path=__file__,
    )

    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 3
    nuclear.maximum_odmr_drift = 0.02
    nuclear.refocus_moving_average_factor = 1
    nuclear.pld.custom_model = lmfit_models.SincModel()

    pi3d.gated_counter.n_values = 1200 * 1500
    pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values % pi3d.gated_counter.trace.binning_factor
    pi3d.gated_counter.trace.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.average_results = True

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(3)),
            ('transition', ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1', '14n-1 ms-1']),
            # ('transition', ['13c414 ms0', '13c414 ms-1', '13c90 ms-1']),
            # ('transition', ['13c414 ms-1', '13c90 ms-1']),
            ('x', np.arange(-3*pdc['max_rabi_freq'], 3*pdc['max_rabi_freq']+1e-12, pdc['max_rabi_freq']/4.))
        )
    )

    for ti in nuclear.parameters['transition']:
        nuclear.file_notes += "{}\t{}\n".format(ti, pi3d.tt.t(ti).current_frequency)
    nuclear.number_of_simultaneous_measurements = 1
    nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_sweep'


param_lists = list()
param_lists.append(['max_rabi_freq', [0.001]])
tl = sch.ret_tl(param_lists)
pds = sch.ret_pds(param_lists, tl)

pi3d.pds = pds

def run_fun(abort, **kwargs):

    nuclear.debug_mode = False

    for i, pdc in enumerate(pds):
        if abort.is_set(): break
        print(pdc)
        settings(pdc)
        nuclear.run(abort)
        if not nuclear.debug_mode and not abort.is_set():
            data = nuclear.data
            fd = dict()
            fit_result_list = []
            for d, d_idx, idx, df in data.iterator(column_names=['transition']):
                print(d)
                dfagg = df.groupby(['transition', 'x']).agg({'result_0': np.mean}).reset_index()
                x = np.array(dfagg.x)
                y = np.array(dfagg.result_0)
                mod = lmfit_models.SincModel(rabi_frequency=pdc['max_rabi_freq'], negative=True)
                params = mod.guess(data=y, x=x)
                fit_result_list.append(mod.fit(y, params=params, x=x))
                fd[pi3d.tt.correct_transition_name(d['transition'])] = pi3d.tt.t(d['transition']).current_frequency + fit_result_list[-1].params['center'].value
            pi3d.tt.change_transition_frequency(fd, test_mode=False)

