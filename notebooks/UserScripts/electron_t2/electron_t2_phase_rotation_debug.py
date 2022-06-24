# coding=utf-8
from pi3diamond import pi3d
import datetime
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)
import UserScripts.helpers.shared as shared; reload(shared)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.snippets_awg as sna; reload(sna)
import UserScripts.helpers.shared as ush;reload(ush)
from qutip_enhanced import *
import AWG_M8190A_Elements as E
import pym8190a.elements as e
from collections import OrderedDict
import AWG_M8190A_Elements as E

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

__TAU_HALF__ = 2*192/12e3
__SAMPLE_FREQUENCY__ = e.__SAMPLE_FREQUENCY__

ael = 1.0

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        sequence_name = 'Electron_t2_phase_rotation'
        freq = np.array([pi3d.tt.mw_mixing_frequency])
        pi_2_dur = pi3d.tt.rp('e_rabi_ou350deg-90-L', amp=1.0).pi2
        pi_dur = pi3d.tt.rp('e_rabi_ou350deg-90-L', amp=1.0).pi


        mcas = MCAS.MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=0.1)  # Starting... histogram 0

        for idx, _I_ in current_iterator_df.iterrows():

            mcas.asc(length_mus=1.0, name = 'initial_delay')
            mcas.asc(green=True, length_mus=3., name = 'A1_init')  #

            mcas.asc(length_mus=3.0, name = 'initial_delay')
            mcas.asc(aom_A1=True, length_mus=50., name = 'A1_init')  # Init NV with A1 laser (about 1-3 µs). This step can be skipped for the very first tests #as the green laser will also intialise somehow.
            mcas.asc(length_mus=3.0)
            mcas.start_new_segment('sequence')

            pihalf_dur = pi_2_dur #0.0135
            hahn_echo_tau = 0.075

            pi_dur =pi_dur #0.027
            mw_amplitude = 1.0
            mw_freq = freq

            mcas.asc(length_mus=1.0, name='wait_1') #

            # mcas.asc(
            #     pd2g1=dict(type='sine', frequencies=mw_freq, amplitudes=[mw_amplitude]),
            #     length_mus=E.round_length_mus_full_sample(pihalf_dur),
            #     name='MW_pihalf')  # 13.5ns. First pi/2 pulse

            sna.electron_rabi(
                mcas,
                new_segment=True,
                length_mus=E.round_length_mus_full_sample(0.027),
                amplitudes=[mw_amplitude],
                frequencies=mw_freq,
                mixer_deg=[-90],
                name='MW_pihalf'
            )

            mcas.asc(length_mus=0.01, name='wait_2')

            #
            # mcas.asc(
            #     pd2g1=dict(type='sine', frequencies=mw_freq,
            #                amplitudes=[mw_amplitude]), phases=[_I_['RO_phase']],
            #     length_mus=E.round_length_mus_full_sample(pihalf_dur),
            #     name='phase_' + str(np.round(_I_['RO_phase'],2)))  # 14.5ns. Second pi/2 pulse
            #
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=E.round_length_mus_full_sample(0.027),
                amplitudes=[mw_amplitude],
                frequencies=mw_freq,
                mixer_deg=[-90],
                phases=[_I_['RO_phase']],
                name='phase_' + str(np.round(_I_['RO_phase'],2))
            )




            mcas.asc(name='buffer', length_mus=1.)


            sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False, nuc='Ex_RO', mixer_deg=-90,
                        step_idx=0, laser_dur=50.)


            mcas.asc(length_mus=3.)


            sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False, eom_ampl = 0.0 ,nuc='charge_state', mixer_deg=-90,
                        step_idx=1, laser_dur=100.0)

            mcas.asc(length_mus=3.)





        pi3d.gated_counter.set_n_values(mcas)
        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '>', 1, 1, 0, 1],
        ['init', '>', 5, 1, 0, 1],
    ]

    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )

    nuclear.x_axis_title = 'tau_half [mus]'
    #nuclear.analyze_type = 'consecutive'
    nuclear.analyze_type = 'standard'


    nuclear.do_ple_refocus = True
    nuclear.do_ple_refocusA1 = True
    nuclear.do_ple_refocusEx = True
    nuclear.do_confocal_red_refocus = False
    nuclear.do_confocal_zpl_refocus = True
    nuclear.do_odmr_refocus = False


    nuclear.ple_refocus_interval = 1
    nuclear.confocal_red_refocus_interval = 60  # 240
    nuclear.wavemeter_lock = True


    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0]
    pi3d.gated_counter.trace.average_results = False
    nuclear.two_zpl_apd = False

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(1000)),
            # ('leakege_type',[0,1,2]),
            ('aom_Ex_power_sweep', [2.0]),
            ('aom_A1_power_sweep', [-7.5]),
            ('Ex_RO_power_sweep', [-3.0]),
            ('RO_phase', np.linspace(-90., 360., 15)),

            # ('tau', E.round_length_mus_full_sample([0.075])),
            # ('mw_duration', np.linspace(0.0,0.1,15)),

        )
    )
    nuclear.number_of_simultaneous_measurements =  len(nuclear.parameters['RO_phase'])

def run_fun(abort, **kwargs):
    pi3d.readout_duration = 1e6*100
    pi3d.gated_counter.readout_duration = 5e6

    nuclear.debug_mode = False
    settings()

    nuclear.run(abort)
