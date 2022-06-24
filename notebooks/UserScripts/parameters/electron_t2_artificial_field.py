from pi3diamond import pi3d
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
import UserScripts.helpers.shared as shared; reload(shared)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.snippets_awg as sna; reload(sna)
import UserScripts.helpers.shared as ush;reload(ush)
import AWG_M8190A_Elements as E
from qutip_enhanced import *

from collections import OrderedDict

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

__TAU_HALF__ = 2*192/12e3

ael = 1.0

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():

                # init
            def erabi(freq, length, amp, phase=0.0):
                sna.electron_rabi(mcas,
                                  name='electron rabi',
                                  length_mus=length,
                                  amplitudes=[amp],
                                  frequencies=freq,
                                  phases=np.rad2deg(phase),
                                  new_segment=False,
                                  mixer_deg=-90,
                                  )

            def wrfmw_fix():
                mcas.asc(length_mus=0.5)

            def artificial_field(freq, length, amp, phase=0.0, phase_offset_type='absolute'):
                wrfmw_fix()
                wrfmw_fix()
                sna.nuclear_rabi(mcas,
                                 name = 'artificial_field',
                                 length_mus = length,
                                 amplitudes = [amp],
                                 frequencies= freq,
                                 phases = [np.rad2deg(phase)],
                                 phase_offset_type = phase_offset_type)
                wrfmw_fix()
                wrfmw_fix()

            rabi_period = _I_['rabi_period']

            def waveform():
                mcas.start_new_segment('waveform')
                sna.polarize(mcas, new_segment=False)
                # pi/2
                erabi(freq, length = 0.25*rabi_period, amp=pi3d.tt.rp('e_rabi', period=rabi_period, mixer_deg=-90).amp, phase=0)
                wrfmw_fix()
                ph = [0,np.pi]

                for i in range(_I_['number_of_pi_pulses']):

                    artificial_field(freq=[1.0], length=_I_['total_tau'],amp=_I_['field_amp'],phase_offset_type=_I_['phase_type'],phase=ph[i%2])
                    erabi(freq=freq, length=0.5*rabi_period, amp=pi3d.tt.rp('e_rabi', period=rabi_period, mixer_deg=-90).amp, phase=0) # N times _I_['number_of_pi_pulses']
                    wrfmw_fix()


                artificial_field(freq=[1.0], length=_I_['total_tau'],amp=_I_['field_amp'],phase_offset_type=_I_['phase_type'],phase=ph[_I_['number_of_pi_pulses']%2])
                erabi(freq, length=0.25 * rabi_period, amp=pi3d.tt.rp('e_rabi', period=rabi_period, mixer_deg=-90).amp, phase=_I_['phase_pi2_2'])

            def waveform2():
                wrfmw_fix()
                ph = [0, np.pi]

                for i in range(_I_['number_of_pi_pulses']):
                    artificial_field(freq=[1.0], length=_I_['total_tau'], amp=_I_['field_amp'], phase_offset_type=_I_['phase_type'], phase=ph[i % 2])
                    erabi(freq=freq, length=0.5 * rabi_period, amp=pi3d.tt.rp('e_rabi', period=rabi_period, mixer_deg=-90).amp, phase=0)  # N times _I_['number_of_pi_pulses']
                    wrfmw_fix()

                artificial_field(freq=[1.0], length=_I_['total_tau'], amp=_I_['field_amp'], phase_offset_type=_I_['phase_type'], phase=ph[_I_['number_of_pi_pulses'] % 2])
                erabi(freq, length=0.25 * rabi_period, amp=pi3d.tt.rp('e_rabi', period=rabi_period, mixer_deg=-90).amp, phase=_I_['phase_pi2_2'])

            freq = pi3d.tt.mfl({'14N': [+1]}, ms_trans=_I_['ms'])
            waveform()
            mcas.asc(length_mus=0.5)
            trf = '14N+1 mS0'
            arf = 1.0
            sna.nuclear_rabi(mcas,
                             name=trf,
                             frequencies=[pi3d.tt.t(trf).current_frequency],
                             amplitudes=[arf],
                             length_mus=pi3d.tt.rp(trf, amp=arf).pi)
            mcas.asc(length_mus=10)
            waveform2()
            sna.ssr(mcas, frequencies=freq, nuc='14N+1', robust=True, mixer_deg=-90, step_idx=0)

            pi3d.gated_counter.set_n_values(mcas)
        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '<', 'auto', 123123, 1, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )
    nuclear.x_axis_title = 'tau_half [mus]'
    nuclear.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0]
    pi3d.gated_counter.trace.average_results = True
    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('rabi_period', [0.1]),
            ('ms', [-1]),
            ('field_amp', np.linspace(0.2,0.3,40)),
            #('ddt', ['hahn']),# 'fid','hahn', 'xy4', 'xy16', 'kdd4', 'kdd16']),
            #('n_rep_dd', [1]),
            #('total_tau', E.round_length_mus_full_sample( np.hstack([[0.0], np.linspace(0.03, 1000, 100)]))),
            #('total_tau', E.round_length_mus_full_sample(np.hstack([[0.0], np.linspace(0.03, 5, 100)]))),
            #('total_tau', E.round_length_mus_full_sample(np.linspace(0.01,2.0,40))),
            #('total_tau', E.round_length_mus_full_sample(np.array([0.01,0.415,0.93,1.44]))),
            ('total_tau', E.round_length_mus_full_sample(np.array([0.93]))),
            ('number_of_pi_pulses',[11]),
            ('phase_type',['absolute']),
            ('phase_field', [np.pi]),
            #('phase_pi2_2', [0.0, np.pi]),
            ('phase_pi2_2', [0.0]),# np.pi]),
        )
    )
    nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['phase_pi2_2'])

def run_fun(abort, **kwargs):
    pi3d.readout_duration = 50e6#150e6
    nuclear.debug_mode = False
    settings()
    nuclear.run(abort)
