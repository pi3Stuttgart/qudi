# coding=utf-8

from pi3diamond import pi3d
import AWG_M8190A_Elements as E
#
import numpy as np
import time, datetime, os, itertools

import pandas as pd
import itertools

import UserScripts.helpers.sequence_creation_helpers as sch;reload(sch)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.standard_awg_sequences as sas; reload(sas)
import UserScripts.helpers.snippets_awg as sna; reload(sna)

from qutip_enhanced import *
reload(sc)

seq_name = os.path.basename(__file__).split('.')[0]
# final_phases_list = [0.0, np.pi]
# final_phases_list = [np.pi, 0.0]
final_phases_list = [0.0]

def write_awg_seq(tau_list, **kwargs):

    e_freq = pi3d.tt.mfl({'14N': [0]})

    def pulse_single(factor=0.0, total_phase=0.0):
        if factor == 0.0:
            return None
        sna.electron_rabi(mcas,
                          length_mus=E.round_length_mus_full_sample(factor * kwargs['rabi_period']),
                          amplitudes=[pi3d.tt.rp("e_rabi", period=kwargs['rabi_period']).amp],
                          frequencies=e_freq,
                          phases=[np.degrees(total_phase)],
                          new_segment=False,
                          wait_switch=0.0,
                          )

    def pulse_kdd(total_phase=0.0, factor=None):
        phases = sc.__PHASES_DD__['knillpi']
        for p in phases:
            pulse_single(factor=0.5, total_phase=p + total_phase)


    mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2]})
    mcas.start_new_segment('sync_timetagger')
    mcas.asc(name='sync', length_mus=0.01, gate=True)  # Changed when timetagger was going to be used
    mcas.start_new_segment(kwargs['dd_type'])
    for tau in tau_list:
        dda = sc.DD(tau=tau, **kwargs)

        phase_list = dda.phases
        tau_list = dda.tau_list()

        pi_pulse = pulse_single

        for phase in final_phases_list:
            # pulse_single(factor=0.25, total_phase=0.0)
            # mcas.asc(length_mus=tau_list[0], name='_pulsed_tau_')
            # for phase_i, tau_i in zip(phase_list[:-1], tau_list[1:-1]):
            #     pi_pulse(factor=0.5, total_phase=phase_i)
            #     mcas.asc(length_mus=tau_i, name='tauhalf')
            # if len(phase_list) > 0:
            #   pi_pulse(factor=0.5, total_phase=phase_list[-1])
            # mcas.asc(length_mus=tau_list[-1], name='tauhalf')
            # pulse_single(factor=0.25, total_phase=phase)
    # for factor, tau in zip([0.0, 0.25, 0.5, 0.75, 1.0], np.arange(1, 6)*1/12e3):
    #     for i in range(2):
    #         mcas.asc(length_mus=tau, name='_pulsed_tau_')
    #         pulse_single(factor=factor, total_phase=0.0)
            sna.electron_rabi(mcas,
                              length_mus=E.round_length_mus_full_sample(tau * kwargs['rabi_period']),
                              amplitudes=[pi3d.tt.rp("e_rabi", period=kwargs['rabi_period']).amp],
                              frequencies=e_freq,
                              phases=[np.degrees(phase)],
                              new_segment=False,
                              wait_switch=0.0,
                              name='_pulsed_tau_'
                              )

            mcas.asc(name='compensate', length_mus=E.round_length_mus_full_sample((tau_list[-1] - tau) * kwargs['rabi_period']))
            mcas.asc(name='green', length_mus=0.01, green=True)
            mcas.asc(name='green', length_mus=2.99, green=True)
            mcas.asc(name='wait', length_mus=0.9)
    mcas.write_seq()

def write_sequence(pdc):
    # dd_type, rabi_period, vary_times=None, time_digitization=None, **kwargs):
    rabi_period = pi3d.tt.rp('e_rabi_left', amp=0.375).period
    write_awg_seq(dd_type='03_kdd4',
                  rabi_period=rabi_period,
                  time_digitization=1/12e3,
                  # tau_list=np.concatenate([[0.0], E.round_length_mus_full_sample(np.logspace(-2, 1.5, 11))]))
                  # tau_list=np.concatenate([[0.0], E.round_length_mus_full_sample(np.logspace(0, 3, 20))]))
                  tau_list=np.arange(0, 1., 0.01))

def settings(pdc):
    write_sequence(pdc)
    pi3d.pulsed.mw_power = 16.
    pi3d.pulsed.sequence_name = seq_name
    pi3d.pulsed.planned_sweeps = 5e9
    pi3d.pulsed.refocus_interval = 1
    pi3d.pulsed.odmr_interval = 90
    pi3d.pulsed.alternating_sequence = {1: False, 2:True}[len(final_phases_list)]
    pi3d.pulsed.fit_function = 'CosineMultiDet'


def run_fun(abort, **kwargs):

    settings({})
    # pi3d.confocal.run_refocus()
    # pi3d.odmr.external_stop_request = abort
    # pi3d.odmr.do_frequency_refocus()
    pi3d.pulsed.mw_freq = pi3d.tt.current_local_oscillator_freq
    pi3d.pulsed.state = 'run'
    time.sleep(1)
    while pi3d.pulsed.thread is None:
        time.sleep(0.1)
    pi3d.pulsed.thread.join()
    # pi3d.pulsed._do_fit_changed()

        # pi3d.tt.rabi_parameters['e_rabi'].archive()
        # fp = "{}/electron_rabi_frequencies.dat".format(path)
        # fp = pi3d.tt.rabi_parameters['e_rabi'].filepath
        # result.to_csv(fp, "\t")