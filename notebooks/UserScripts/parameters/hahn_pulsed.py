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

seq_name = os.path.basename(__file__).split('.')[0]

def write_sequence(pdc):
    t = ['left']
    freq_list = np.array([pi3d.tt.mfl('14N0', ms_trans='left')[0], pi3d.tt.mfl('14N0', ms_trans='right')[0]])

    nstep = 25
    # total_dur = 10 * pi3d.tt.rp('e_rabi_left', amp=pdc['amp{}'.format(pdc['transition'])]).period
    # total_dur = nstep*np.around(np.array(total_dur/nstep)*12e3)/12e3

    sas.write_awg_seq('hahn',
                      length_mus=800.,
                      amplitudes=[1.0],
                      transition=t,
                      frequencies=freq_list[:1],
                      num_step=nstep,
                      name=seq_name)

def settings(pdc):
    write_sequence(pdc)
    pi3d.pulsed.mw_power = 16.
    pi3d.pulsed.sequence_name = seq_name
    pi3d.pulsed.planned_sweeps = 5e4
    pi3d.pulsed.fit_function = 'CosineMultiDet'


def run_fun(abort, **kwargs):



    settings({})
    pi3d.confocal.run_refocus()
    pi3d.odmr.external_stop_request = abort
    pi3d.odmr.do_frequency_refocus()
    pi3d.pulsed.mw_freq = pi3d.tt.current_local_oscillator_freq
    pi3d.pulsed.state = 'run'
    while pi3d.pulsed.thread is None:
        time.sleep(0.1)
    pi3d.pulsed.thread.join()
    pi3d.pulsed._do_fit_changed()

        # pi3d.tt.rabi_parameters['e_rabi'].archive()
        # fp = "{}/electron_rabi_frequencies.dat".format(path)
        # fp = pi3d.tt.rabi_parameters['e_rabi'].filepath
        # result.to_csv(fp, "\t")