from __future__ import print_function, absolute_import, division
from imp import reload

from pi3diamond import pi3d
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch

reload(sch)
import multi_channel_awg_seq as MCAS

reload(MCAS)
import UserScripts.helpers.snippets_awg as sna

reload(sna)
import AWG_M8190A_Elements as E
import copy
from collections import OrderedDict
from qutip_enhanced import *

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        freq = pi3d.tt.mfl({'14N': [0]})
        wait_rf_mw = .5
        fl = pi3d.tt.t('13c ms0').current_frequency

        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():


            def erabi(freq, length, amp, phase=0.0):
                sna.electron_rabi(mcas,
                                  name='electron rabi',
                                  length_mus=length,
                                  amplitudes=[amp],
                                  frequencies=freq,
                                  phases=np.rad2deg(phase),
                                  new_segment=False,
                                  mixer_deg=-90
                                  )

            def waveform(seq, n):
                if _I_['pol_14n_init'] in ['+1', '0', '-1']:
                    sna.init_14N(mcas, mn=_I_['pol_14n_init'], new_segment=True)
                mcas.start_new_segment('plenio_flipflop', loop_count=n)
                sna.polarize_green(mcas, new_segment=False, length_mus=0.2)
                sna.polarize_red(mcas, new_segment=False)
                mw = seq.times_fields_aphi('mw')
                wait = seq.times_fields_aphi('wait')
                for _ in range(n_rep_flipflop):
                    for step in seq.sequence_steps:
                        idx = int(step[1]) - 1
                        if step[0] == 'mw':
                            erabi(freq=freq,
                                  length=mw[idx, 0],
                                  amp=pi3d.tt.rp('e_rabi', mixer_deg=-90, period=1 / mw[idx, 1]).amp,
                                  phase=mw[idx, 2])
                        elif step[0] == 'wait':
                            mcas.asc(length_mus=wait[idx, 0])

            dd_type = '{}_{}'.format(n_rep_dd, ddt)
            n_pi = len(sc.__PHASES_DD__[dd_type])
            tau = 2 / (4 * np.abs(fl) + 2 * Azz_init) - .5*rabi_period
            add_x = .25
            total_tau_90 = tau * (n_pi+add_x)
            tau_90 = total_tau_90 / n_pi if n_pi > 0 else 0.0
            tau_90 +=  _I_['tau_offset']
            def plenio_flipflop(n):
                pi2x = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1 / rabi_period, phase=0.0, control_field='mw')
                pi2y = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1 / rabi_period, phase=+np.pi / 2., control_field='mw')
                dd = sc.DD(dd_type=dd_type, rabi_period=rabi_period, tau=tau_90)
                seq = sc.Concatenated([pi2x, dd, pi2x, pi2y, dd, pi2y], controls=['mw', 'wait'])
                waveform(seq, n)

            # readout
            task = _I_['task']
            Azz_read = _I_['Azz_read']
            periods = {'sensing': 1.0, 'cnot': 0.5}[task]
            max_tau4 = 100
            if Azz_read == 0.0:
                tau4 = E.round_length_mus_full_sample(max_tau4)
            else:
                tau4 = E.round_length_mus_full_sample(min(max_tau4, periods / (4 * np.abs(Azz_read))))
            T_pi_small = _I_['T_pi_small'] # E.round_length_mus_full_sample(calibration_factors['small']*_I_['tau'])
            T_pi_big = _I_['T_pi_big'] #.round_length_mus_full_sample(calibration_factors['big']*_I_['tau'])
            T_pi_small_eff = 2*wait_rf_mw + T_pi_small
            T_pi_big_eff = 2*wait_rf_mw + T_pi_big



            def nucrabi(freq, length_mus_pi, nuctype, amplitude_factor=1., phase=0.):
                sna.nuclear_rabi(mcas,
                                 name='nuclear rabi',
                                 frequencies=np.array([freq]),
                                 amplitudes=[amplitude_factor * pi3d.tt.rp(nuctype, period=2 * length_mus_pi).amp],
                                 length_mus=length_mus_pi,
                                 phases=np.array([phase]),
                                 new_segment=False,
                                 )

            def cnot(nt):
                sna.electron_rabi(mcas,
                                  name='cnot' + nt,
                                  wave_file=wfd[nt],
                                  frequencies=(pi3d.tt.mfl({'14N': [+1]}) + pi3d.tt.mfl({'14N': [0]})) / 2.,
                                  new_segment=False,
                                  mixer_deg=-90,
                                  )

            def nuclearpi2(phase):
                amplitude = 1.0
                sna.nuclear_rabi(mcas,
                                 name='pi2' + '14N+1 mS0',
                                 frequencies=[pi3d.tt.t('14N+1 mS0').current_frequency],
                                 amplitudes=[amplitude],
                                 length_mus=pi3d.tt.rp('14N+1 mS0', amp=amplitude).pi2,
                                 phases=[phase],
                                 new_segment=False,
                                 )

            Azz_tau = pi3d.tt.get_f('14n_hf')
            Azz_T_small = pi3d.tt.get_f('14n_hf')  # as the effective duration of 'small' (2 pi-pulses) and 'big' (one pi-pulse) is the same, the offset frequencies have to be the same if the same oscillation frequencies should be seen
            Azz_T_big = pi3d.tt.get_f('14n_hf')
            n14pi2phase = dict()
            n14pi2phase['cnot'] = 1.767 + 0.2
            n14pi2phase['tau'] = .5*2*np.pi*Azz_tau*4*tau4 #factor 0.5 due to cnot frequency being between +1 and 0 and thus phase accumulation ~.5Azz
            n14pi2phase['T_pi_small'] = 2*np.pi*Azz_T_small*(2*T_pi_small_eff)
            n14pi2phase['T_pi_big'] = 2*np.pi*Azz_T_big*T_pi_big_eff
            n14pi2phase['offset'] = {'sensing': 0.0, 'cnot': np.pi / 2.}[task] + _I_['14nphaseoffset']
            n14pi2phase = np.rad2deg(sum(n14pi2phase.values()))

            target_13c_freq_small = target_13c_freq_big = fl - Azz_read + _I_['freq_offset']
            def f():
                mcas.start_new_segment('dd_wf')
                mcas.asc(length_mus=wait_rf_mw)
                nuclearpi2(phase=.0)
                mcas.asc(length_mus=wait_rf_mw)
                cnot('14N0')
                mcas.asc(length_mus=tau4)
                cnot('14N+1')
                mcas.asc(length_mus=wait_rf_mw)
                nucrabi(target_13c_freq_small, length_mus_pi=T_pi_small, amplitude_factor=1., nuctype='13c ms0')
                mcas.asc(length_mus=wait_rf_mw)
                cnot('14N0')
                mcas.asc(length_mus=tau4)
                cnot('14N0')
                mcas.asc(length_mus=wait_rf_mw)
                nucrabi(target_13c_freq_big, length_mus_pi=T_pi_big, amplitude_factor=1., nuctype='13c ms0')
                mcas.asc(length_mus=wait_rf_mw)
                cnot('14N+1')
                mcas.asc(length_mus=tau4)
                cnot('14N+1')
                mcas.asc(length_mus=wait_rf_mw)
                nucrabi(target_13c_freq_small, length_mus_pi=T_pi_small, amplitude_factor=1., nuctype='13c ms0')
                mcas.asc(length_mus=wait_rf_mw)
                cnot('14N0')
                mcas.asc(length_mus=tau4)
                cnot('14N+1')
                mcas.asc(length_mus=wait_rf_mw)
                nuclearpi2(phase=n14pi2phase)
                mcas.asc(length_mus=wait_rf_mw)

            if n_init > 0:
                plenio_flipflop(n_init)

            sna.init_14N(mcas, new_segment=True)
            sna.ssr(mcas, frequencies=pi3d.tt.mfl({'14N': [+1]}), nuc='14N+1', robust=True, repetitions=500, mixer_deg=75)
            sna.polarize_green(mcas, length_mus=0.2, new_segment=True)  # to pump back from nv0
            sna.polarize(mcas, new_segment=True)
            f()
            sna.ssr(mcas, frequencies=pi3d.tt.mfl({'14N': [+1]}), nuc='14N+1', robust=True, mixer_deg=75)
        return mcas

    return ret_mcas


def settings(pdc={}):
    ana_seq = [
        ['init', '<', 'auto', 500, 1.0],
        ['init', '>', -1, 1, 1],
        ['result', '<', 'auto', 1100, 1],
        ['init', '>', -1, 1, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )

    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 3
    nuclear.maximum_odmr_drift = 0.04
    nuclear.refocus_moving_average_factor = 1

    nuclear.analyze_type = 'standard'

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('task', ['cnot']),
            ('freq_offset', [0.]),
            ('T_pi_small', [150.]),
            ('T_pi_big', [500]),
            ('Azz_read', [pi3d.tt.get_f('13c13_hf')]),
            ('rabi_period', [0.07]), #np.arange(0.045, 0.1+1e-12, 0.005)),
            ('n_rep_dd', [1]),
            ('n_rep_flipflop', [30]),  # number of times the whole flipflop sequence pi/2 - dd - pi2  - tau/2 - dd - tau/2 - pi2 is repeated
            ('n_init', [300]),  # number of electron spin reinitializations with red
            ('ddt', ['xy4']),  # base sequence that forms dd (can be repeated)
            ('14nphaseoffset', [np.pi]),
            ('Azz_init', [0.0]),
            ('pol_14n_init', ['0', 'none', '+1', '-1']),
            ('tau_offset', np.arange(-0.003, -0.001+1e-12, 0.00025))
        )
    )

    nuclear.number_of_simultaneous_measurements = 3

def run_fun(abort, **kwargs):
    settings()
    pi3d.gated_counter.points = 2000
    pi3d.gated_counter.number_of_memories = 1
    nuclear.debug_mode = False
    nuclear.run(abort)
