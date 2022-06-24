from pi3diamond import pi3d
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
import UserScripts.helpers.shared as shared; reload(shared)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.snippets_awg as sna; reload(sna)
import UserScripts.helpers.shared as ush;reload(ush)
from qutip_enhanced import *
import AWG_M8190A_Elements as E
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
            # def erabi(freq, length, amp, phase=0.0):
            #     sna.electron_rabi(mcas,
            #                       name='electron rabi',
            #                       length_mus=length,
            #                       amplitudes=[amp],
            #                       frequencies=freq,
            #                       phases=np.rad2deg(phase),
            #                       new_segment=False,
            #                       mixer_deg=-90,
            #                       )
            #
            # def waveform(seq):
            #     mcas.start_new_segment('waveform')
            #     sna.polarize(mcas, new_segment=False)
            #     mw = seq.times_fields_aphi('mw')
            #     wait = seq.times_fields_aphi('wait')
            #     for step in seq.sequence_steps:
            #         idx = int(step[1]) - 1
            #         if step[0] == 'mw':
            #             erabi(freq=freq, length=mw[idx, 0], amp=pi3d.tt.rp('e_rabi', period=1 / mw[idx, 1], mixer_deg=-90).amp, phase=mw[idx, 2])
            #         elif step[0] == 'wait':
            #             mcas.asc(length_mus=wait[idx, 0])


            # rabi_period = _I_['rabi_period']
            # def dd():
            #     pi2x = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1 / rabi_period, phase=0.0, control_field='mw')
            #     pi2_2 = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1 / rabi_period, phase=_I_['phase_pi2_2'], control_field='mw')
            #     dd = sc.DD(dd_type='{}_{}'.format(_I_['n_rep_dd'], _I_['ddt']), rabi_period=_I_['rabi_period'], total_tau=_I_['total_tau'])
            #     seq = sc.Concatenated([pi2x, dd, pi2_2], controls=['mw', 'wait'])
            #     waveform(seq)

            freq = pi3d.tt.mfl({'14N': [+1]}, ms_trans=_I_['ms'])
            mcas.start_new_segment('waveform')
            #mcas.asc(length_mus=0.5)
            if _I_['green_polarize'] == True:
                sna.polarize_green(mcas,length_mus = 2000.0)
            else:
                pass
            mcas.asc(length_mus=0.5)
            sna.ssr(mcas, frequencies=freq, wait_dur =0.0, robust=False, nuc='charge_state', mixer_deg=-90, step_idx=0)
            if _I_['red_disturb'] == True:
                mcas.start_new_segment('red apply',loop_count=_I_["N"])
                sna.polarize_red(mcas, length_mus=_I_['total_tau'], new_segment = False)
            elif _I_['red_disturb'] == False and _I_['green_disturb'] == True:
                sna.polarize_green(mcas, length_mus=2000.0, new_segment=True)

            sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False, nuc='charge_state', mixer_deg=-90, step_idx=1)
            # dd()
            #mcas.asc(length_mus=0.5)

            # trf = '14N+1 mS0'
            # arf = 1.0
            # sna.nuclear_rabi(mcas,
            #                  name=trf,
            #                  frequencies=[pi3d.tt.t(trf).current_frequency],
            #                  amplitudes=[arf],
            #                  length_mus=pi3d.tt.rp(trf, amp=arf).pi)
            # sna.ssr(mcas, frequencies=freq, nuc='14N+1', robust=True, mixer_deg=-90, step_idx=0)
            pi3d.gated_counter.set_n_values(mcas)
        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['init', '>', 7, 1, 5, 1],
        ['result', '>', 7, 1, 4, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )
    nuclear.x_axis_title = 'tau_half [mus]'

    pi3d.gated_counter.trace.analyze_type = 'standard'

    pi3d.gated_counter.trace.average_results = False
    #pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0]

    nuclear.odmr_pd = dict(
        n=0,
        freq=None,
        size={'left': '', 'right': ''},
        repeat=False,
    )
    nuclear.odmr_pd_refocus = dict(
        n=1,
        freq=None,
        size={'left': '', 'right': ''},
        repeat=False,
    )
    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('rabi_period', [0.1]),
            ('ms', [-1]),
            ('ddt', ['hahn']),# 'fid','hahn', 'xy4', 'xy16', 'kdd4', 'kdd16']),
            ('n_rep_dd', [1]),
            ('total_tau', E.round_length_mus_full_sample(np.hstack([[1.0], np.linspace(10.0, 30000.0, 10.0)]))),
            ('N', [10]),
            ('green_polarize',[True]),
            ('red_disturb',[True]),
            ('green_disturb', [False])
            #('phase_pi2_2', [0.0, np.pi])

        )
    )
    nuclear.number_of_simultaneous_measurements = 1#len(nuclear.parameters['green'])

def run_fun(abort, **kwargs):
    pi3d.readout_duration = 150e6 # 150/0.1
    nuclear.debug_mode = False
    settings()
    nuclear.run(abort)
