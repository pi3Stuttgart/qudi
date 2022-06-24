from pi3diamond import pi3d
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
import UserScripts.helpers.shared as shared; reload(shared)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.snippets_awg as sna; reload(sna)

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(seq_name)

__TAU_HALF__ = 2*192/12e3

ael = 1.0
pel = pi3d.tt.rp('e_rabi_left', amp=ael).period

def ret_ret_mcas(pdc):
    def ret_mcas(seq_num, point):
        mcas = MCAS.MultiChSeq(seq_name=seq_name)
        def decoupling_waveform():

            def pulse(factor=0.0, total_phase=0.0):
                sna.electron_rabi(mcas,
                                  length_mus=shared.round_to(factor * pel, 1/12.e3),
                                  amplitudes=[ael],
                                  frequencies=freq,
                                  phases=[np.degrees(total_phase)],
                                  new_segment=False
                                  )
            def make_tau(tau):
                mcas.asc(length_mus=tau, name='tau')

            mcas.start_new_segment(name='waveform', loop_count=1)
            pulse(factor=0.25, total_phase=0.0)
            make_tau(nuclear.x[point])
            pulse(factor=0.25, total_phase=[0., np.pi][seq_num])

        freq = pi3d.tt.mfl({'14N': [+1]}, ms_trans=pdc['ms_trans'])
        decoupling_waveform()
        trf = '14N+1 mS0'
        mcas.asc(length_mus=0.5)
        arf = 0.2
        sna.nuclear_rabi(mcas,
                         name=trf,
                         frequencies=[pi3d.tt.t(trf).current_frequency],
                         amplitudes=[arf],
                         length_mus=pi3d.tt.rp(trf, amp=arf).pi)
        sna.ssr(mcas, frequencies=freq, nuc='14N+1', robust=True)
        return mcas
    return ret_mcas

def settings(pdc):
    sch.settings(script_path=os.path.abspath(__file__),
                 ret_mcas=ret_ret_mcas(pdc),
                 analyze_sequence=[['result', '<', 'auto', 1200, 1]],
                 pdc=pdc)
    nuclear.number_of_sequences = 2
    nuclear.planned_sweeps = 100
    nuclear.variable = None
    nuclear.x_axis_title = 'tau [mus]'
    nuclear.use_manual_x = True
    nuclear.analyze_type = 'consecutive'
    pi3d.gated_counter.points = 4000
    # def rx(start, stop, nstep):
    #     start = start if start > __TAU_HALF__ else __TAU_HALF__
    #     return np.around(np.array(np.linspace(start, stop, nstep), dtype=np.float)/ __TAU_HALF__)*__TAU_HALF__
    nuclear.x = np.arange(0., 120., 0.25)
    nuclear.parameter_names = ['sweeps', 'seq_num', 'tau']


def run_fun(abort, **kwargs):
    param_lists = []
    param_lists.append(['ms_trans', ['left']])
    tl = sch.ret_tl(param_lists)
    pds = sch.ret_pds(param_lists, tl)

    for i, pdc in enumerate(pds):
        if abort.is_set(): break
        print pdc
        settings(pdc)
        nuclear.run(abort)


# from pi3diamond import pi3d
# import numpy as np
# import os
# import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
# import UserScripts.helpers.shared as shared; reload(shared)
# import multi_channel_awg_seq as MCAS; reload(MCAS)
# import UserScripts.helpers.snippets_awg as sna; reload(sna)
#
# seq_name = os.path.basename(__file__).split('.')[0]
# nuclear = sch.create_nuclear(seq_name)
#
# __TAU_HALF__ = 2*192/12e3
#
# ael = 1.0
# pel = pi3d.tt.rp('e_rabi_left', amp=ael).period
#
# def ret_ret_mcas(pdc):
#     def ret_mcas(seq_num, point):
#         mcas = MCAS.MultiChSeq(seq_name=seq_name)
#         def decoupling_waveform():
#
#             def pulse(factor=0.0, total_phase=0.0):
#                 sna.electron_rabi(mcas,
#                                   length_mus=shared.round_to(factor * pel, 1/12.e3),
#                                   amplitudes=[ael],
#                                   frequencies=freq,
#                                   phases=[np.degrees(total_phase)],
#                                   new_segment=False
#                                   )
#             def make_tau(tau):
#                 mcas.asc(length_mus=tau, name='tau')
#             ddp = shared.DDParameters(pdc['dd_type'], nuclear.x[point], rabi_period=pel)
#             tau_list = shared.round_to(ddp.tau_list, 1/12.e3)
#
#             mcas.start_new_segment(name='waveform', loop_count=1)
#             pulse(factor=0.25, total_phase=0.0)
#             make_tau(tau_list[0])
#             for i, phase_i in enumerate(ddp.phases):
#                 pulse(factor=0.5, total_phase=phase_i)
#                 make_tau(tau_list[i+1])
#             pulse(factor=0.25, total_phase=[0., np.pi][seq_num])
#
#         freq = pi3d.tt.mfl({'14N': [+1]}, ms_trans=pdc['ms_trans'])
#         decoupling_waveform()
#         trf = '14N+1 mS0'
#         mcas.asc(length_mus=0.5)
#         arf = 0.2
#         sna.nuclear_rabi(mcas,
#                          name=trf,
#                          frequencies=[pi3d.tt.t(trf).current_frequency],
#                          amplitudes=[arf],
#                          length_mus=pi3d.tt.rp(trf, amp=arf).pi)
#         sna.ssr(mcas, frequencies=freq, nuc='14N+1', robust=True)
#         return mcas
#     return ret_mcas
#
# def settings(pdc):
#     sch.settings(script_path=os.path.abspath(__file__),
#                  ret_mcas=ret_ret_mcas(pdc),
#                  analyze_sequence=[['result', '<', 'auto', 1200, 1]],
#                  pdc=pdc)
#     nuclear.number_of_sequences = 2
#     nuclear.planned_sweeps = 3
#     nuclear.variable = None
#     nuclear.x_axis_title = 'tau_half [mus]'
#     nuclear.use_manual_x = True
#     nuclear.analyze_type = 'consecutive'
#     pi3d.gated_counter.points = 8000
#     # def rx(start, stop, nstep):
#     #     start = start if start > __TAU_HALF__ else __TAU_HALF__
#     #     return np.around(np.array(np.linspace(start, stop, nstep), dtype=np.float)/ __TAU_HALF__)*__TAU_HALF__
#
#     if pdc['dd_type'] == 'hahn':
#         nuclear.x = np.linspace(1., 1200., 15)
#     elif pdc['dd_type'] == 'kdd4':
#         nuclear.x = np.linspace(1, 10000., 15)
#     elif pdc['dd_type'] == 'xy16':
#         nuclear.x = np.linspace(1, 10000., 15)
#     elif pdc['dd_type'] == 'kdd16':
#         nuclear.x = np.linspace(1, 10000, 20)
#     else:
#         raise Exception("Error")
#
# def run_fun(abort, **kwargs):
#     param_lists = []
#     param_lists.append(['dd_type', ['kdd16']])#['kdd16_uhrig', 'kdd16', 'kdd4_uhrig', 'kdd4', 'cpmg32_uhrig', 'cpmg32', 'cpmg128_uhrig', 'cpmg128']])
#     param_lists.append(['ms_trans', ['left']])
#     tl = sch.ret_tl(param_lists)
#     pds = sch.ret_pds(param_lists, tl)
#
#     for i, pdc in enumerate(pds):
#         if abort.is_set(): break
#         print pdc
#         settings(pdc)
#         nuclear.run(abort)
