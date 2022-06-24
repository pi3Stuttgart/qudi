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

def rabi_x_amp1(pdc, oscillations=None, points_per_oscillation=None, maximum_rabi_duration=5000.):
    est_per = pi3d.tt.rp(pdc['transition'], amp=1.0).period
    t0 = 0.0
    t1 = oscillations*est_per
    if t1 > maximum_rabi_duration:
        raise Exception('Error: {}, {}, {}'.format(t1, maximum_rabi_duration, pdc))
    return E.round_length_mus_full_sample(np.linspace(t0, t1, oscillations*(points_per_oscillation - 1) + 1))

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            sms = sch.ret_sms(transition=pdc['transition'])
            sna.polarize(mcas, new_segment=True)
            if sms['ms'] != '0':
                sna.single_robust_electron_pi(mcas,
                                              nuc='all',
                                              transition={'-1': 'left', '+1':'right'}[sms['ms']],
                                              frequencies=pi3d.tt.mfl({'14n': [0]}, ms_trans=sms['ms']),
                                              new_segment=True,
                                              )
            sna.nuclear_rabi(mcas,
                             new_segment=True,
                             amplitudes=[_I_['amp']],
                             name=pdc['transition'],
                             frequencies=[pi3d.tt.t(pdc['transition']).current_frequency],
                             length_mus=E.round_length_mus_full_sample(_I_['x']/_I_['amp']))
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

    pi3d.gated_counter.trace.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [1, 2] if '14n-1' in pdc['transition'].lower() else [0, 1]
    pi3d.gated_counter.trace.average_results = True

    if sch.ret_sms(transition=pdc['transition'])['nuc'] == '13c90':
        nuclear.odmr_interval = 20
        nuclear.maximum_odmr_drift = 0.02
        nuclear.refocus_interval = 2
    else:
        nuclear.odmr_interval = 30
        nuclear.maximum_odmr_drift = 0.03
        nuclear.refocus_interval = 1

    nuclear.refocus_moving_average_factor = 1
    print(pdc['amp_list'])
    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(1)),
            ('amp', pdc['amp_list']),
            ('x', rabi_x_amp1(pdc, oscillations=3., points_per_oscillation=12.))
        )
    )
    nuclear.seq_names = ["{:.6f}".format(amp) for amp in nuclear.parameters['amp']]

    nuclear.number_of_simultaneous_measurements = 3 #len(nuclear.parameters['x'])


    nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_rabi'


    nuclear.odmr_pd = dict(
        n=0,
        freq=None,
        size={'left': '2', 'right': ''},
        repeat=False,
    )

####################################################################################################
# predefined transition lists
####################################################################################################
transition_list = ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1', '14n-1 ms-1', '14n+1 ms+1', '14n-1 ms+1',
                   '13c414 ms0', '13c414 ms-1', '13c414 ms+1',
                   '13c90 ms-1', '13c90 ms+1']

####################################################################################################
# RABI
####################################################################################################
param_lists = list()
#param_lists.append(['transition', ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1', '14n-1 ms-1', '13c90 ms-1', '13c414 ms0', '13c414 ms-1']])
param_lists.append(['transition', ['13c90 ms-1']])
# param_lists.append(['transition', ['14n+1 ms0']])
# param_lists.append(['transition', ['14n+1 ms0', '14n-1 ms0', '14n+1 ms-1', '14n-1 ms-1', '13c90 ms-1', '13c414 ms0', '13c414 ms-1']])
# param_lists.append(['transition', ['13c90 ms-1', '14n+1 ms0']])
# param_lists.append(['transition', ['13c90 ms-1', '13c414 ms0', '13c414 ms-1']])

# param_lists.append(['amp_list', [np.hstack([np.arange(0.0, 0.1, 0.05)[1:], np.arange(0., 1.+1e-7, .1)[1:]])]])
param_lists.append(['amp_list', [E.round_to_amplitude_granularity(np.arange(0.2, 1.001, 0.1))]])
# param_lists.append(['amp_list', [E.round_to_amplitude_granularity(np.arange(0.3, 1.001, 0.1))]])
tl = sch.ret_tl(param_lists)
pds = sch.ret_pds(param_lists, tl)

def run_fun(abort, **kwargs):

    nuclear.debug_mode = False

    for i, pdc in enumerate(pds):
        if abort.is_set(): break
        print('PDC',pdc)
        settings(pdc)
        pi3d.gated_counter.n_values = 1200 * 1500
        pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values % pi3d.gated_counter.trace.binning_factor
        if len(nuclear.parameters['amp']) <= 2:
            print('WARNING: Not enough amplitudes. Will not be saved for TransitionTracker. {}'.format(nuclear.parameters['amp']))
        pi3d.cun.pld.gui.update_window_title("NuclearOPs_nuclear_rabi{}_{}".format(pdc['transition'], datetime.datetime.strftime(nuclear.date_of_creation, nuclear.__TITLE_DATE_FORMAT__)))
        nuclear.run(abort)

        if len(nuclear.parameters['amp']) > 2 and not nuclear.debug_mode and len(nuclear.iterator_df) == 0:
            data = data_handling.Data(parameter_names=['amp0', 'transition'],
                                      observation_names=['omega', 'date'],
                                      dtypes=dict(date='str'))
            data.init()

            def add_rabi_parameter_file_line(amp, transition_num, omega, date_str_or_date):
                data.append([collections.OrderedDict([('amp0', amp), ('transition', transition_num)])])
                data.set_observations([collections.OrderedDict([('omega', omega), ('date', date_str_or_date)])])

            add_rabi_parameter_file_line(amp=0.0, transition_num=0, omega=0.0, date_str_or_date='19700101-h00m00s00')
            for d, _, _, df in nuclear.data.iterator(column_names=['amp']):
                if len(data.df) == 2:
                    #  TODO: This only works for amplitues: 0 < amp < amp[1]. for missing values somewhere else, take minimum amplitude distance in nuclear.parameters['amp'] and check if distance between two values is smaller. If the case, do the same that is d one here, but for np.arange(smaller_amplitude, larger amplitude, minimum_amplitude-distance)[1:])
                    al = nuclear.parameters['amp']
                    da = min(al[1:]) - min(al[:-1])
                    al_extrapol = np.arange(0, al[1], da)[1:]
                    df_last = data.df.iloc[-1, :]
                    for amp in al_extrapol:
                        add_rabi_parameter_file_line(amp, 0, df_last.loc['omega']*amp/df_last.loc['amp0'], df_last.loc['date'])
                    data._df = data.df.sort_values(by='amp0')
                dfagg = df.groupby(['amp', 'x']).agg({'result_0': np.mean}).reset_index()
                x = np.array(dfagg.x)
                y = np.array(dfagg.result_0)
                mod = lmfit_models.CosineModel()
                params = mod.guess(data=y, x=x)
                fit_result = mod.fit(y, params=params, x=x)
                date = nuclear.data.df[nuclear.data.df.amp == d['amp']].end_time.iloc[-1]
                if date == '': #probably useless statement
                    date = '19700101-h00m00s00' #probably useless statement
                # TODO remove for calibration
                #add_rabi_parameter_file_line(amp=d['amp'], transition_num=0, omega=d['amp']/fit_result.params['T'].value, date_str_or_date=date)
                pi3d.rabi_results = data
            t = pdc['transition'] if not ('13c' in pdc['transition'] and 'ms0' in pdc['transition']) else '13c ms0'
            t = t.lower()
            # TODO remove for calibration
            #pi3d.tt.rabi_parameters[t].update_file(data.df)