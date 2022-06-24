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
import pym8190a.elements as E
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
                                              transition={'-1': 'left', '+1':'right'}[sms['ms']],
                                              frequencies=pi3d.tt.mfl({'14n': [0]}, ms_trans=sms['ms']),
                                              new_segment=True,
                                              )
            def pi2():
                amp = 1.0
                sna.nuclear_rabi(mcas,
                                 new_segment=True,
                                 amplitudes=[amp],
                                 name=_I_['transition'],
                                 frequencies=[pi3d.tt.t(_I_['transition']).current_frequency + pdc['freq_offset']],
                                 length_mus=pi3d.tt.rp(_I_['transition'], amp=amp).pi2)
            pi2()
            if _I_['x'] == 0.0:
                mcas.start_new_segment(name='tau', loop_count=1)
                mcas.asc(name='tau', length_mus=_I_['x'])
            else:
                def loop_count():
                    n = _I_['x']/__WAIT_TIME_SEGMENT_LENGTH_MUS__
                    if np.abs(np.around(n) - n) > E.__SAMPLE_DURATION_TOLERANCE__:
                        raise Exception('Error: {}, {}, {}, {}'.format(_I_['x'], n, np.around(n), n-np.around(n)))
                    return int(np.around(n))
                mcas.start_new_segment(name='tau', loop_count=loop_count())
                mcas.asc(name='tau', length_mus=__WAIT_TIME_SEGMENT_LENGTH_MUS__)
            pi2()
            ssr_frequencies = [pi3d.tt.mfl(sms['nuc'] + '_left'), pi3d.tt.mfl(sms['nuc'] + '_right')] if '13c' in sms['nuc'] else [pi3d.tt.mfl({'14N': [+1]}), pi3d.tt.mfl({'14N': [0]}), pi3d.tt.mfl({'14N': [-1]})]
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

    nuclear.odmr_interval = 60
    nuclear.refocus_interval = 3
    nuclear.maximum_odmr_drift = 0.05
    nuclear.refocus_moving_average_factor = 1
    pi3d.gated_counter.trace.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.average_results = True

    length_mus_fid = 10000.
    n_osc = length_mus_fid*pdc['freq_offset']
    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            # ('transition', ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1', '14n+1 ms-1', '13c414 ms0', '13c414 ms-1', '13c90 ms-1']),
            ('transition', ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1', '14n-1 ms-1']),
            # ('transition', ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1']),
            ('x', np.around(np.linspace(0, n_osc / np.abs(pdc['freq_offset']), n_osc*8)/__WAIT_TIME_SEGMENT_LENGTH_MUS__)*__WAIT_TIME_SEGMENT_LENGTH_MUS__)
        )
    )

    for ti in nuclear.parameters['transition']:
        nuclear.file_notes += "{}\t{}\n".format(pi3d.tt.t(ti).current_frequency, ti)
    nuclear.number_of_simultaneous_measurements = 1
    nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_fid'


param_lists = list()
param_lists.append(['freq_offset', [0.00025]])
tl = sch.ret_tl(param_lists)
pds = sch.ret_pds(param_lists, tl)


def run_fun(abort, **kwargs):

    nuclear.debug_mode = False
    pi3d.gated_counter.readout_duration = 30e6
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
                mod = lmfit_models.CosineModel()
                params = mod.guess(data=y, x=x)
                params['x0'].value = 1/(2.*pdc['freq_offset'])-pi3d.tt.rp(d['transition'], amp=1.0).pi
                params['x0'].vary = False
                fit_result_list.append(mod.fit(y, params=params, x=x))
                fd[pi3d.tt.correct_transition_name(d['transition'])] = pi3d.tt.frequency_fid(pi3d.tt.t(d['transition']).current_frequency, pdc['freq_offset'], fit_result_list[-1].params['T'].value, max_diff_factor=.2)
                # fd[pi3d.tt.correct_transition_name(d['transition'])] = pi3d.tt.t(d['transition']).current_frequency + fit_result_list[-1].params['center'].value
            pi3d.tt.change_transition_frequency(fd, test_mode=True)

        # if not nuclear.debug_mode and not abort.is_set():
        #     data = nuclear.data
        #     notes_path = os.path.join(nuclear.save_dir, 'notes.dat')
        #     cfd = {}
        #     with open(notes_path) as f:
        #         for line in f:
        #             ll = line.split('\t')
        #             cfd[ll[1][:-1]] = float(ll[0])
        #     fd = dict()
        #     for d, d_idx, idx, df in data.iterator(column_names=['transition']):
        #         current_frequency = cfd[d['transition']] if len(cfd) > 0 else pi3d.tt.t(d['transition']).current_frequency
        #         dfagg = df.groupby(['transition', 'x']).agg({'result_0': np.mean}).reset_index().dropna(subset=['result_0'])
        #         x = np.array(dfagg.x)
        #         y = np.array(dfagg.result_0)
        #         mod = lmfit_models.CosineModel()
        #         params = mod.guess(data=y, x=x)
        #         # params['x0'].value = 500.-pi3d.tt.rp(d['transition'], amp=1.0).pi
        #         params['x0'].value = 1/(2.*pdc['freq_offset'])-pi3d.tt.rp(d['transition'], amp=1.0).pi
        #         params['x0'].vary = False
        #         fit_result = mod.fit(y, params=params, x=x)
        #         fd[pi3d.tt.correct_transition_name(d['transition'])] = pi3d.tt.frequency_fid(current_frequency, pdc['freq_offset'], fit_result.params['T'].value, max_diff_factor=.2)
        #     pi3d.tt.change_transition_frequency(fd, test_mode=True)