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

import pym8190a.elements as E
import collections

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

wave_file = [
    r"\\PI3-PC161\d\Python\pi3diamond\UserScripts\Robust\algorithmic_cooling\zno10FN1.40e-01\MW.dat",
    r"\\PI3-PC161\d\Python\pi3diamond\UserScripts\Robust\algorithmic_cooling\zno10FN3.07e-01(14n0.64)\MW.dat",
]

wave_file_steps = [
    [
        [0, 42],
        [42, 84],
        [84, 126],
    ],
    [
        [0, 28],
        [28, 84],
        [84, 112],
    ],
]

wfd = dict()
for pn, wfpath in enumerate(wave_file):
    for idx, s in enumerate(wave_file_steps[pn]):
        # u_i_j (i:pulse, j:part)
        wfd["u_{}_{}".format(pn, idx)] = E.WaveFile(
            filepath=wfpath,
            rp=pi3d.tt.rp('e_rabi', mixer_deg=-90),
            part=s
        )


def ret_ret_mcas(pds):
    def ret_mcas(current_iterator_df):

        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})

        for idx, _I_ in current_iterator_df.iterrows():

            #init
            pi3d.gated_counter.trace.analyze_sequence[0][2] = _I_['init_threshold']
            pi3d.gated_counter.trace.analyze_sequence[0][3] = _I_['ssr_repetitions']
            pi3d.gated_counter.trace.analyze_sequence[0][5] = _I_['n_freq_init']

            #csd
            pi3d.gated_counter.trace.analyze_sequence[1][2] = _I_['csd_threshold']
            pi3d.gated_counter.trace.analyze_sequence[1][3] = _I_['csd_repetitions']
            pi3d.gated_counter.trace.analyze_sequence[1][5] = _I_['n_freq_csd']

            #result
            pi3d.gated_counter.trace.analyze_sequence[2][5] = 3 if _I_['readout_on'] == '14n' else 2
            pi3d.gated_counter.trace.analyze_sequence[2][2] = -1 if _I_['readout_on'] == '14n' else 0
            pi3d.gated_counter.trace.analyze_sequence[2][2] = _I_['result_threshold']
            if _I_['readout_on'] not in ['14n', '13c414', '13c90']:
                pi3d.gated_counter.trace.analyze_sequence[2][5] = _I_['n_freq_result']

            nuclear.analyze_type = 'multifreq' if _I_['readout_on'] == '14n' else 'standard'

            def electron_gate(pulse_num, step_num):
                mcas.asc(length_mus=0.5)
                sna.electron_rabi(mcas,
                                  name='cphase',
                                  wave_file=wfd["u_{}_{}".format(pulse_num, step_num)],
                                  frequencies=(pi3d.tt.mfl({'14N': [0]})),
                                  new_segment=False,
                                  mixer_deg=-90,
                                  )
                mcas.asc(length_mus=0.5)

            def nucpi2(nuc, phase, new_segment=False):
                rabi_period = 200.
                sna.nuclear_rabi(mcas,
                                 name='pi/2_' + nuc,
                                 frequencies=[pi3d.tt.t(nuc + ' ms0').current_frequency],
                                 amplitudes=[pi3d.tt.rp(nuc + ' ms0', period=rabi_period).amp],
                                 length_mus=pi3d.tt.rp(nuc + ' mS0', period=rabi_period).pi2,
                                 phases=[phase],
                                 new_segment=new_segment,
                                 )

            def waveform():
                mcas.start_new_segment('waveform')
                # CNOTNOT
                nucpi2('13C414', phase=0)
                if _I_["part"] >= 0:
                    electron_gate(_I_["pulse_num"], 0)
                nucpi2('13C414', phase=np.rad2deg(np.pi))
                nucpi2('14n+1', phase=np.rad2deg(np.pi))
                if _I_["part"] >= 1:
                    electron_gate(_I_["pulse_num"], 1)
                nucpi2('14n+1', phase=0)
                nucpi2('13C414', phase=0)
                if _I_["part"] >= 2:
                    electron_gate(_I_["pulse_num"], 2)

                nucpi2('13C414', phase=np.rad2deg(np.pi))

            def wf_rabi():
                nuc = _I_['nuc']
                rabi_period = 200.
                sna.nuclear_rabi(mcas,
                                 name='rabi' + nuc,
                                 frequencies=[pi3d.tt.t(nuc + ' ms0').current_frequency],
                                 amplitudes=[pi3d.tt.rp(nuc + ' ms0', period=rabi_period).amp],
                                 length_mus=_I_['tau_rabi'],
                                 phases=[0.],
                                 new_segment=True,
                                 )

            mn_14n = [+1, 0, -1] if _I_['init_14n'] is "not" else [int(_I_['init_14n'])]
            mn_13c414 = [+.5, -.5] if _I_['init_13c414'] is "not" else [.5 * int("{}1".format(_I_['init_13c414']))]
            mn_13c90 = [+.5, -.5] if _I_['init_13c90'] is "not" else [.5 * int("{}1".format(_I_['init_13c90']))]
            sna.init_13c(mcas, s='90', state=_I_['init_13c90'], new_segment=True)
            sna.init_13c(mcas, s='414', state=_I_['init_13c414'], new_segment=True)
            sna.init_14N(mcas, mn=_I_['init_14n'], new_segment=True)
            frequencies_init = pi3d.tt.mfl({'14N': mn_14n, '13c414': mn_13c414, '13c90': mn_13c90})
            frequencies_not_init = pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5, -.5]})
            frequencies_not_init = np.delete(frequencies_not_init, np.argwhere(frequencies_not_init == frequencies_init[0])[0, 0])
            sna.ssr(mcas, frequencies=[frequencies_init, frequencies_not_init], nuc='13c90', robust=False, repetitions=_I_['ssr_repetitions'], mixer_deg=-90, length_mus_mw=_I_['length_mus_mw'])

            sna.polarize_red(mcas)

            nucpi2('14n-1', 0., new_segment=True)
            nucpi2('14n-1', 0.)

            waveform()

            sna.ssr(mcas, frequencies=[frequencies_init, frequencies_not_init], nuc='13c90', robust=False, repetitions=_I_['csd_repetitions'], mixer_deg=-90, length_mus_mw=_I_['length_mus_mw'])

            if _I_['readout_on'] == '14n':
                sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14N': [+1]}),
                                           pi3d.tt.mfl({'14N': [0]}),
                                           pi3d.tt.mfl({'14N': [-1]})
                                           ], nuc='14N', robust=True, repetitions=int(1200), mixer_deg=-90)
            elif _I_['readout_on'] == '13c414':
                sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5]}),
                                           pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [-.5]})], nuc='13c414', robust=True, repetitions=int(1200), mixer_deg=-90)
            elif _I_['readout_on'] == '13c90':
                sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5]}),
                                           pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [-.5]})], nuc='13c90', robust=True, repetitions=int(1200), mixer_deg=-90)
            else:
                frequencies = pi3d.tt.mfl({'14N': [int(_I_['readout_on'][:2])], '13C414': [float("{}0.5".format(_I_['readout_on'][2]))], '13C90': [float("{}0.5".format(_I_['readout_on'][3]))]})
                if _I_['n_freq_result'] == 1:
                    rfl = [frequencies]
                elif _I_['n_freq_result'] == 2:
                    frequencies_not = pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5, -.5]})
                    frequencies_not = np.delete(frequencies_not, np.argwhere(frequencies_not == frequencies[0])[0, 0])
                    rfl = [frequencies, frequencies_not]
                sna.ssr(mcas, frequencies=rfl, nuc='13c90', robust=False, repetitions=1200, mixer_deg=-90, length_mus_mw=_I_['length_mus_mw'])

        return mcas

    return ret_mcas


def settings(pdc={}):
    ana_seq = [
        ['init', '<', 0, 0, 1, 2],
        ['init', '>', 0, 0, 1, 2],
        ['result', '<', -1, 1200, 1, 3],
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
            ('sweeps', range(30)),
            # ('nuc', ['14n+1', '13c414', '13c90']),
            # ('tau_rabi', E.round_length_mus_full_sample(np.arange(0.0, 250., 15.))),
            ("pulse_num", list(range(len(wave_file)))),
            ("part", [-1, 0, 1, 2]),  # 0: CNN, 1:CNN+NCC, 2:CNN+NCC+CNN
            ('ssr_repetitions', [450]),  # 360, 400, 450, 500, 550, 600, 650, 700]),
            ('csd_repetitions', [300]),  # 360, 400, 450, 500, 550, 600, 650, 700]),
            ('csd_threshold', [+5]),  # 360, 400, 450, 500, 550, 600, 650, 700]),
            ('init_threshold', [-5]),
            ('result_threshold', [0]),
            # ('ssr_repetitions', [200]), #360, 400, 450, 500, 550, 600, 650, 700]),
            # ('phase', np.linspace(0, 2*np.pi, 49)),
            # ('phase', np.linspace(0, 2*np.pi, 9)),
            ('n_freq_init', [2]),
            ('n_freq_csd', [2]),
            ('n_freq_result', [2]),
            ('init_14n', ["-1"]),
            ('init_13c90', ["-"]),
            ('init_13c414', ["-"]),
            ('length_mus_mw', [15.]),
            # ('readout_on', ["".join(i) for i in itertools.product(["+1", "00", "-1"], ["+", "-"], ["+", "-"])]), #
            ('readout_on', ['14n', '13c414', '13c90']),
            # ('readout_on', ["+1++"])
        )
    )

    nuclear.number_of_simultaneous_measurements = 1


def run_fun(abort, **kwargs):
    settings()
    pi3d.gated_counter.points = 500
    nuclear.debug_mode = False
    nuclear.run(abort)