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
import UserScripts.helpers.shared as ush;reload(ush)

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(seq_name)

__TAU_HALF__ = 2*192/12e3

def ret_ret_mcas(pdc):
    def ret_mcas(seq_num, point):
        mcas = MCAS.MultiChSeq(seq_name=seq_name)

        trf = '14N+1 mS0'
        arf = 0.2

        tau_half = E.round_length_mus_full_sample(nuclear.x[point]/2.)

        sna.nuclear_rabi(mcas,
                         name=trf,
                         frequencies=[pi3d.tt.t(trf).current_frequency],
                         amplitudes=[arf],
                         length_mus=pi3d.tt.rp(trf, amp=arf).pi2)

        mcas.asc(length_mus=tau_half)

        sna.nuclear_rabi(mcas,
                         name=trf,
                         frequencies=[pi3d.tt.t(trf).current_frequency],
                         amplitudes=[arf],
                         length_mus=pi3d.tt.rp(trf, amp=arf).pi)

        mcas.asc(length_mus=tau_half)

        phase = 180. if seq_num == 1 else 0.

        sna.nuclear_rabi(mcas,
                         name=trf,
                         frequencies=[pi3d.tt.t(trf).current_frequency],
                         amplitudes=[arf],
                         phases=[phase],
                         length_mus=pi3d.tt.rp(trf, amp=arf).pi2)

        sna.ssr(mcas, frequencies=pi3d.tt.mfl({'14N': [+1]}), nuc='14N+1', robust=True, repetitions=1200)

        return mcas
    return ret_mcas

def settings(pdc):
    sch.settings(script_path=os.path.abspath(__file__),
                 ret_mcas=ret_ret_mcas(pdc),
                 analyze_sequence=[['result', '<', 'auto', 1200, 1]],
                 pdc=pdc)
    nuclear.number_of_sequences = 2
    nuclear.planned_sweeps = 3
    nuclear.variable = None
    nuclear.x_axis_title = 'tau [mus]'
    nuclear.use_manual_x = True
    nuclear.analyze_type = 'consecutive'

    if pdc['dd_type'] == 'hahn':
        nuclear.x = np.logspace(0., np.log10(30000.), 20)
    else:
        raise Exception("Error")


param_lists = []
param_lists.append(['dd_type', ['hahn']])
param_lists.append(['ms_trans', ['left']])
tl = sch.ret_tl(param_lists)
pds = sch.ret_pds(param_lists, tl)

ush.test_ret_ret_mcas(ret_ret_mcas, pds, nuclear=nuclear, settings=settings)

def run_fun(abort, **kwargs):

    for i, pdc in enumerate(pds):
        if abort.is_set(): break
        print pdc
        settings(pdc)
        pi3d.gated_counter.points = 1500
        nuclear.run(abort)