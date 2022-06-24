from __future__ import print_function, absolute_import, division
from imp import reload

from pi3diamond import pi3d
import numpy as np
import time, datetime, os, itertools
import UserScripts.helpers.sequence_creation_helpers as sch

reload(sch)
import multi_channel_awg_seq as MCAS

reload(MCAS)
import UserScripts.helpers.snippets_awg as sna

reload(sna)
import AWG_M8190A_Elements as E
import collections

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

def ret_ret_mcas(pds):
    def ret_mcas(current_iterator_df):

        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})

        for idx, _I_ in current_iterator_df.iterrows():

            pi3d.gated_counter.trace.analyze_sequence[0][2] = _I_['init_threshold']
            pi3d.gated_counter.trace.analyze_sequence[0][3] = _I_['init_repetitions']
            pi3d.gated_counter.trace.analyze_sequence[0][4] = _I_['init_threshold_diff']
            pi3d.gated_counter.trace.analyze_sequence[0][5] = _I_['n_freq_init']
            pi3d.gated_counter.trace.analyze_sequence[1][2] = _I_['result_threshold']
            pi3d.gated_counter.trace.analyze_sequence[1][4] = _I_['result_threshold_diff']
            if _I_['readout_on'] in ['14n', '13c414', '13c90']:
                n_freq_result = 3 if _I_['readout_on'] == '14n' else 2
            else:
                n_freq_result = _I_['n_freq_result']
            pi3d.gated_counter.trace.analyze_sequence[1][5] = n_freq_result

            mn_14n = [+1, 0, -1] if _I_['init_14n'] is "not" else [int(_I_['init_14n'])]
            mn_13c414 = [+.5, -.5] if _I_['init_13c414'] is "not" else [.5 * int("{}1".format(_I_['init_13c414']))]
            mn_13c90 = [+.5, -.5] if _I_['init_13c90'] is "not" else [.5 * int("{}1".format(_I_['init_13c90']))]
            sna.init_13c(mcas, s='90', state=_I_['init_13c90'], new_segment=True)
            sna.init_13c(mcas, s='414', state=_I_['init_13c414'], new_segment=True)
            sna.init_14N(mcas, mn=_I_['init_14n'], new_segment=True)
            frequencies_init = pi3d.tt.mfl({'14N': mn_14n, '13c414': mn_13c414, '13c90': mn_13c90})
            frequencies_not_init = pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5, -.5]})
            frequencies_not_init = np.delete(frequencies_not_init, np.argwhere(frequencies_not_init == frequencies_init[0])[0, 0])
            sna.ssr(mcas, frequencies=[frequencies_init, frequencies_not_init], nuc='13c90', robust=False, repetitions=_I_['init_repetitions'], mixer_deg=-90, length_mus_mw=_I_['length_mus_mw'])
            sna.nuclear_rabi(mcas,
                             new_segment=True,
                             amplitudes=[pi3d.tt.rp(_I_['transition_rf'],  period=200.).amp],
                             name=_I_['transition_rf'],
                             frequencies=[pi3d.tt.t(_I_['transition_rf']).current_frequency],
                             length_mus=_I_['tau_rf'])
            frequencies = pi3d.tt.mfl({'14N': [int(_I_['readout_on'][:2])], '13C414': [float("{}0.5".format(_I_['readout_on'][2]))], '13C90': [float("{}0.5".format(_I_['readout_on'][3]))]})
            if _I_['n_freq_result'] == 1:
                rfl = [frequencies]
            elif _I_['n_freq_result'] == 2:
                frequencies_not = pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5, -.5]})
                frequencies_not = np.delete(frequencies_not, np.argwhere(frequencies_not == frequencies[0])[0, 0])
                rfl = [frequencies, frequencies_not]
            sna.ssr(mcas, frequencies=rfl, nuc='13c90', robust=False, repetitions=_I_['result_repetitions'], mixer_deg=-90, length_mus_mw=_I_['length_mus_mw'])
        return mcas

    return ret_mcas


def settings(pdc={}):
    ana_seq = [
        ['init', '<', 0, 0, 0, 2],
        ['result', '<', 0, 1200, 0, 2],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )
    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 1
    nuclear.maximum_odmr_drift = 0.015
    nuclear.refocus_moving_average_factor = 1

    nuclear.analyze_type = 'standard'

    nuclear.parameters = collections.OrderedDict(
        (
            ('sweeps', range(100)),
            ('init_repetitions', [1000]), #360, 400, 450, 500, 550, 600, 650, 700]),
            ('result_repetitions', [1000]), #360, 400, 450, 500, 550, 600, 650, 700]),
            # ('ssr_repetitions', [200]), #360, 400, 450, 500, 550, 600, 650, 700]),
            # ('tau_rf', E.round_length_mus_full_sample(np.arange(0.0, 200., 10.))),
            ('tau_rf', [0.0]),
            # ('transition_rf', ['13c414 mS0', '13c90 ms0', '14n+1 ms0', '14n-1 ms0']),
            ('transition_rf', ['13c414 mS0']),
            ('init_threshold', ['auto']),
            ('result_threshold', ['auto']),
            ('init_threshold_diff', [20]),
            ('result_threshold_diff', [20]),
            ('n_freq_init', [1]),
            ('n_freq_result', [1]),
            ('init_14n', ["+1"]),
            ('init_13c90', ["-"]),
            ('init_13c414', ["-"]),
            ('length_mus_mw', [15.]),
            # ('readout_on', ["".join(i) for i in itertools.product(["+1", "00", "-1"], ["+", "-"], ["+", "-"])]), # '14n', '13c414', '13c90',
            # ('readout_on', ["".join(i) for i in itertools.product(["+1", "00", "-1"], ["-", "+"], ["-", "+"])])
            ('readout_on', ["+1--", "+1++"])
        )
    )

    nuclear.number_of_simultaneous_measurements = 1


def run_fun(abort, **kwargs):
    settings()
    pi3d.gated_counter.points = 1000
    nuclear.debug_mode = False
    nuclear.run(abort)