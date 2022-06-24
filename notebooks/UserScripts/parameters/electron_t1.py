from pi3diamond import pi3d
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.snippets_awg as sna; reload(sna)

from collections import OrderedDict


seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            sna.polarize(mcas, new_segment=True)
            if _I_['ms'] == -1:
                sna.single_robust_electron_pi(mcas,
                                              nuc='all',
                                              transition='left',
                                              frequencies=pi3d.tt.mfl({'14n': [0]}),
                                              new_segment=True,
                                              )
            lc = np.around((_I_['tau'] / (320 / 12e3))).astype(int)
            if lc > 0:
                mcas.start_new_segment(name='tau_t1', loop_count=lc)
                mcas.asc(length_mus=320 / 12e3, name='tau')
            mcas.start_new_segment(name='safety')
            mcas.asc(length_mus=0.5)
            t = '13c90 ms0'
            a = 1.0
            sna.nuclear_rabi(mcas,
                             name=t,
                             amplitudes=[a],
                             length_mus=pi3d.tt.rp(t, amp=a).pi,
                             frequencies=[pi3d.tt.t(t).current_frequency],
                             new_segment=True,

                             )
            sna.ssr(mcas, frequencies=[pi3d.tt.mfl('13C90_left'), pi3d.tt.mfl('13C90_right')], nuc='13C90', robust=True, mixer_deg=75)
        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '<', 0, 1200, 1, 2],
        ['init', '>', -1, 1, 1, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )
    nuclear.analyze_type = 'consecutive_b'

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('ms', [0, -1]),
            ('tau', np.hstack([[0.0], np.logspace(0.5, 5 , 30)])),
        )
    )
    nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['tau'])

def run_fun(abort, **kwargs):

    pi3d.gated_counter.points = 4000
    nuclear.debug_mode=False
    settings()
    nuclear.run(abort)

# def settings(pdc={}):
#     ana_seq=[
#         ['result', '<', 'auto', 1200, 1, 1],
#         ['init', '>', -1, 1, 1, 1],
#     ]
#     sch.settings(
#         nuclear=nuclear,
#         ret_mcas=ret_ret_mcas(pdc),
#         analyze_sequence=ana_seq,
#         pdc=pdc,
#         meas_code=meas_code
#     )
#     nuclear.x_axis_title = 'tau_half [mus]'
#     nuclear.analyze_type = 'consecutive'
#
#     nuclear.parameters = OrderedDict(
#         (
#             ('sweeps', range(100)),
#             ('rabi_period', [0.050]),
#             ('ms', [-1]),
#             ('ddt', ['hahn', 'xy4', 'xy16', 'kdd4', 'kdd16']),
#             ('n_rep_dd', [1]),
#             ('total_tau', np.hstack([[0.0], np.logspace(0.5, 4  , 40)])),
#             ('phase_pi2_2', [0.0, np.pi]),
#         )
#     )
#     nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['phase_pi2_2'])
#
# def run_fun(abort, **kwargs):
#
#     pi3d.gated_counter.points = 4000
#     nuclear.debug_mode=False
#     settings()
#     nuclear.run(abort)


# def settings(pdc={}):
#     sch.settings(script_path=os.path.abspath(__file__),
#                  ret_mcas=ret_ret_mcas(pdc),
#                  analyze_sequence=[['result', '<', 'auto', 1200, 1]],
#                  pdc=pdc)
#     nuclear.analyze_type = 'consecutive'
#     nuclear.show_in_plot = 'complete result'
#     nuclear.x_axis_title = 'Time [mus]'
#     nuclear.number_of_sequences = 2
#     pi3d.gated_counter.samples_per_read = 200
#     nuclear.planned_sweeps = 1
#     nuclear.use_manual_x = True
#     nuclear.x = shared.x_values_awg_fit(0., 30000, 40, f=np.logspace)
#     nuclear.save_after = 'sequence'
#
#
# def run_fun(abort, **kwargs):
#     settings()
#     nuclear.run(abort)
#     pi3d.gated_counter.points = 1500
    # nuclear.test_rf(0,1,0,1)
    # nuclear.start(abort)
    # nuclear.thread.join()
