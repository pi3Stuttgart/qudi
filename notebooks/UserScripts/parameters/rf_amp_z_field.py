from pi3diamond import pi3d
import numpy as np
import time
import datetime
import os
import itertools
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.snippets_awg as sna; reload(sna)

nuclear = pi3d.nuclear
tt = pi3d.tt
seq_name = os.path.basename(__file__).split('.')[0]
odmr = pi3d.odmr
gated_counter = pi3d.gated_counter

__FREQ__ = pi3d.tt.t('13C mS0').current_frequency + 0.15

def ret_ret_mcas(pd):

    if pd['dd_type'] == 'hahn':
        __TAU_TOT__ = 50
    elif pd['dd_type'] == 'knill':
        __TAU_TOT__ = 7

    def ret_mcas(seq_num, point):
        mcas = MCAS.MultiChSeq(seq_name=seq_name)
        def decoupling_waveform():
            def pulse(factor=0.0, total_phase=0.0):
                sna.electron_rabi(mcas,
                                  length_mus=factor * rabi_period,
                                  amplitudes=[tt.rp("e_rabi_left", period=rabi_period).amp],
                                  frequencies=freq,
                                  phases=[np.degrees(total_phase)],
                                  new_segment=False
                                  )

            def wait_tauhalf():
                rf_dur = (pi3d.nuclear.x[point])/__FREQ__
                sna.nuclear_rabi(mcas, new_segment=False, length_mus=rf_dur, amplitudes=[1], frequencies=[__FREQ__])
                mcas.asc(length_mus=__TAU_TOT__ - rf_dur, name='tau')

            def wait_tau():
                wait_tauhalf()
                wait_tauhalf()

            mcas.start_new_segment('dd')
            pulse(factor=0.25, total_phase=0.0)
            if pd['dd_type'] == 'hahn':
                wait_tauhalf()
                pulse(factor=0.5, total_phase=0.0)
                wait_tauhalf()

            elif 'knill' in pd['dd_type']:
                def kdd5(phase=0.0, shift=0.0):
                    wait_tauhalf()
                    pulse(factor=0.5, total_phase=np.pi / 6.0 + phase + shift)
                    wait_tau()
                    pulse(factor=0.5, total_phase=phase + shift)
                    wait_tau()
                    pulse(factor=0.5, total_phase=np.pi / 2.0 + phase + shift)
                    wait_tau()
                    pulse(factor=0.5, total_phase=phase + shift)
                    wait_tau()
                    pulse(factor=0.5, total_phase=np.pi / 6.0 + phase + shift)
                    wait_tauhalf()

                if pd['dd_type'] == 'knill':
                    kdd5(phase=0.0, shift=0.0)
                    kdd5(phase=0.0, shift=np.pi / 2.0)
                    kdd5(phase=0.0, shift=0.0)
                    kdd5(phase=0.0, shift=np.pi / 2.0)
            pulse(factor=0.25, total_phase=0.0)

        rabi_period = tt.rp('e_rabi_left', amp=1.0).period
        freq = tt.mfl({'14N': [+1]}, ms_trans='left')
        decoupling_waveform()
        transition = '14N+1 mS0'
        sna.nuclear_rabi(mcas, name=transition, amplitudes=[1], length_mus=tt.rp(transition, amp=1).pi)
        sna.ssr(mcas, frequencies=freq, nuc='14N+1', robust=True)
        return mcas
    return ret_mcas

def settings(pd):
    sch.settings(script_path=os.path.abspath(__file__),
                 ret_mcas=ret_ret_mcas(pd),
                 analyze_sequence=[['result', '<', 'auto', 1200, 1]],
                 pd=pd)
    nuclear.number_of_sequences = 1
    nuclear.planned_sweeps = 1
    gated_counter.points = 3000
    nuclear.variable = None
    nuclear.x_axis_title = 'tau_half [mus]'
    nuclear.use_manual_x = True
    nuclear.analyze_type = 'consecutive'

    if pd['dd_type'] == 'hahn':
        nuclear.x = np.arange(100, 103, 0.025)
    elif pd['dd_type'] == 'knill':
        nuclear.x = np.arange(100, 103, 0.01)

def run_fun(abort, **kwargs):
    param_lists = []
    param_lists.append(['dd_type', ['hahn', 'knill']])
    tl = sch.ret_tl(param_lists)
    pds = sch.ret_pds(param_lists, tl)
    for i, pd in enumerate(pds):
        if abort.is_set(): break
        print pd
        settings(pd)
        nuclear.start(abort)
        nuclear.thread.join()



#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# from pi3diamond import pi3d
# import numpy as np
# import time, datetime, os, itertools
#
# import UserScripts.helpers.sequence_creation_helpers as sch
# reload(sch)
# import multi_channel_awg_seq as MCAS
# reload(MCAS)
# import UserScripts.helpers.snippets_awg as sna
# reload(sna)
#
# seq_name = os.path.basename(__file__).split('.')[0]
#
# def ret_ret_mcas(pd):
#
#     def ret_mcas(seq_num, point):
#         mcas = MCAS.MultiChSeq(seq_name=seq_name)
#         sna.ssr(mcas, frequencies=pi3d.tt.mfl({'14N': [1]}), nuc='14N', robust=True)
#         if point == 0:
#             mcas.start_new_segment('rf')
#
#         mcas.asc(name='wait_decay', length_mus=__TAU__)
#
#         sna.nuclear_rabi(mcas, name='14N+1 mS0', amplitudes=[1], length_mus=pi3d.tt.rp('14N+1 mS0', amp=1).pi)
#         return mcas
#     return ret_mcas
#
# def settings(pd={}):
#     sch.settings(script_path=os.path.abspath(__file__),
#                  ret_mcas=ret_ret_mcas(pd),
#                  analyze_sequence=[['result', '<', 'auto', 1200, 1]],
#                  pd=pd)
#     pi3d.nuclear.analyze_type = 'consecutive'
#     pi3d.nuclear.show_in_plot = 'complete result'
#     pi3d.nuclear.x_axis_title = 'factor'
#     pi3d.nuclear.number_of_sequences = 10
#     pi3d.gated_counter.points = 2000
#     pi3d.gated_counter.samples_per_read = 200
#     pi3d.nuclear.planned_sweeps = 5
#     pi3d.nuclear.use_manual_x = np.arange(0.0, 0.5+0.001, 0.025)
#     pi3d.nuclear.x = range(0, pd['n_full_wl'])
#     pi3d.nuclear.save_after = 'sequence'
#
#
# def run_fun(abort, **kwargs):
#     settings()
#     pi3d.nuclear.start(abort)
#     pi3d.nuclear.thread.join()
