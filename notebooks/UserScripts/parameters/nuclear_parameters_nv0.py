import numpy as np
import time, datetime, os, itertools
import UserScripts.helpers.sequence_creation_helpers as sch
reload(sch)
import multi_channel_awg_seq as MCAS
reload(MCAS)
import UserScripts.helpers.snippets_awg as sna
reload(sna)
from pi3diamond import pi3d

nuclear = pi3d.nuclear
tt = pi3d.tt
odmr = pi3d.odmr
gated_counter = pi3d.gated_counter

seq_name = os.path.basename(__file__).split('.')[0]

def rabi_x(pd):
    try:
        est_per = tt.rp(pd['transition'], amp=1).recalc(pd['amp'], 'period')
    except:
        est_per = tt.rp(pd['transition'], amp=0.4).recalc(pd['amp'], 'period')
    return np.arange(0, np.ceil(2 * est_per), np.around(est_per / 5, 2))

def ret_ret_mcas(pd):
    def ret_mcas(seq_num, point):
        mcas = MCAS.MultiChSeq(seq_name=seq_name)
        sms = sch.ret_sms(transition=pd['transition'])
        mcas.start_new_segment('red', loop_count=500)
        mcas.asc(length_smpl=192*63, red=False)
        if sms['ms'] != '0':
            if sms['nuc'] == '13C90':
                sna.init(mcas, sms['nuc'])
                sna.ssr(mcas, frequencies=tt.mfl(sms['nuc'], ms_trans=sms['ms']), nuc=sms['nuc'], robust=True, repetitions=900)
            sna.electron_rabi(mcas,
                              iq_mixer=True,
                              transition='left',
                              frequencies=tt.mfl(sms['nuc'], ms_trans=sms['ms']),
                              length_mus=sna.periods[sms['nuc']]/2.0,
                              amplitudes=[tt.rp('e_rabi_left', period=sna.periods[sms['nuc']]).amp]
            )
        if pd["mt"] == "rabi":
            sna.nuclear_rabi(mcas, new_segment=True, amplitudes=[pd['amp']], name=pd['transition'], length_mus=nuclear.x[point])
        elif pd['mt'] == 'sweep':
            amp = 0.4
            sna.nuclear_rabi(mcas,
                             name='freq_sweep',
                             frequencies=[nuclear.x[point]],
                             amplitudes=[amp],
                             length_mus=tt.rp(pd['transition'], amp=amp).pi*1.5
            )
        elif pd['mt'] == 'fid':
            def pi2():
                sna.nuclear_rabi(mcas,
                                 new_segment=True,
                                 name='fidpi2',
                                 frequencies=tt.t(pd['transition']).current_frequency + pd['freq_offset'],
                                 amplitudes=[1], length_mus=tt.rp(pd['transition'], amp=1).pi2
                )
            mcas.start_new_segment(name='FID')
            pi2()
            mcas.asc(name='tau')
            pi2()
        sna.ssr(mcas, laser_dur=0.164, frequencies=tt.mfl(sms['nuc'], ms_trans=sms['ms']), nuc=sms['nuc'], transition='left', robust=True)
        return mcas
    return ret_mcas

def settings(pd):
    sch.settings(script_path=os.path.abspath(__file__),
                 ret_mcas=ret_ret_mcas(pd),
                 analyze_sequence=[['result', '<', 'auto', 1200, 1]],
                 pd=pd)
    sms = sch.ret_sms(transition=pd['transition'])
    if sms['nuc'] == '13C90':
        gated_counter.points = 1000
        nuclear.analyze_type = 'consecutive'
        if sms['ms'] != '0':
            nuclear.ana_trace.analyze_sequence = [['init', '<', 'auto', 900, 1],
                                                  ['result', '<', 'auto', 2800, 1]]

    else:
        gated_counter.points = 3000
        nuclear.analyze_type = 'consecutive'

    odmr.refocus_zfs = False
    nuclear.save_after = 'end'
    nuclear.use_manual_x = True
    nuclear.variable = None
    if pd['mt'] == 'fid':
        nuclear.planned_sweeps = 1 #1 is enough
        nuclear.fit_function = 'Cosinus dec offset'
        nuclear.x = np.arange(0, 2.0 / pd['freq_offset'], 1 / (10 * pd['freq_offset']))
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters_nv0/nuclear_fid_nv0'
    elif pd['mt'] == 'rabi':
        nuclear.planned_sweeps = 5
        if 'mS-1' in pd['transition']:
            nuclear.planned_sweeps = 1 #one sweep is ok, some more is bit better
        nuclear.fit_function = 'Cosinus decay'
        nuclear.x = rabi_x(pd)
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters_nv0/nuclear_rabi_nv0'
    elif pd['mt'] == 'sweep':
        nuclear.planned_sweeps = 5
        nuclear.fit_function = 'Lorentz neg'
        center_freq = tt.transition(pd['transition']).current_frequency
        center_freq = 9.335#tt.transition(pd['transition']).current_frequency
        nuclear.x = center_freq + np.arange(-pd['range']/2., pd['range']/2., pd['range']/pd['nsteps'])
        nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters_nv0/nuclear_sweep_nv0'

def run_fun(abort, **kwargs):

    ####################################################################################################
    #predefined transition lists
    ####################################################################################################
    transition_list = ['14N+1 mS0', '14N-1 mS0', '14N+1 mS-1', '14N-1 mS-1', '14N+1 mS+1', '14N-1 mS+1',
                                       '13C414 mS0', '13C414 mS-1', '13C414 mS+1',
                                       '13C90 mS-1', '13C90 mS+1']
    reduced_transition_list = ['14N+1 mS0', '14N-1 mS0', '14N+1 mS-1', '14N-1 mS-1',
                               '13C414 mS0', '13C414 mS-1'
                               '13C90 mS-1']
    minimal_transition_list = ['14N+1 mS0', '14N-1 mS0', '13C414 mS0', '13C414 mS-1' '13C90 mS-1']

    ####################################################################################################
    #FID
    ####################################################################################################
    param_lists = list()
    param_lists.append(['transition', ['14N+1 mS0', '14N-1 mS0', '14N+1 mS-1', '14N-1 mS-1', '14N-1 mS+1',
                                       '13C414 mS0', '13C414 mS-1', '13C414 mS+1'
                                       '13C90 mS-1', '13C90 mS+1']])
    param_lists.append(['mt', ['fid']])
    param_lists.append(['freq_offset', [0.002]])
    tl = sch.ret_tl(param_lists)
    pds_fid = sch.ret_pds(param_lists, tl)

    ####################################################################################################
    #RABI
    ####################################################################################################
    param_lists = list()
    param_lists.append(['transition', ['14N+1 mS0']])
    param_lists.append(['mt', ['rabi']])
    param_lists.append(['amp', [0.4]])
    tl = sch.ret_tl(param_lists)
    pds_rabi = sch.ret_pds(param_lists, tl)

    ####################################################################################################
    #FREQUENCY SWEEP
    ####################################################################################################
    param_lists = list()
    param_lists.append(['transition', ['14N+1 mS0']])
    param_lists.append(['mt', ['sweep']])
    param_lists.append(['range', [0.15]])
    param_lists.append(['nsteps', [8]])
    tl = sch.ret_tl(param_lists)
    pds_sweep = sch.ret_pds(param_lists, tl)

    pds = pds_sweep

    for i, pd in enumerate(pds):
        if abort.is_set(): break
        print pd
        settings(pd)
        # nuclear.test_rf(0, 1, 0, 1)
        # return
        nuclear.start(abort)
        nuclear.thread.join()
        if nuclear.sweeps > 0:
            if pd['mt'] == 'rabi':
                nuclear.fit_function = 'Cosinus decay'
                nuclear.do_fit()
                nuclear.file_notes = "per: {}".format(nuclear.cos_period)
                tt.add_rabi_parameter(name=pd['transition'], amp=pd['amp'], period=nuclear.cos_period)
            elif pd['mt'] == 'fid':
                nuclear.fit_function = 'Cosinus decay'
                nuclear.do_fit()
                nuclear.file_notes = "per: {}".format(nuclear.cos_period)
                tt.change_transition_frequency_fid(pd['transition'], pd['freq_offset'], nuclear.cos_period)
            elif pd['mt'] == 'sweep':
                nuclear.fit_function = 'Lorentz neg'
                nuclear.do_fit()
            pi3d.dump(tt)
            nuclear.save(force=True)