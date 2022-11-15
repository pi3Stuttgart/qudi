# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 11:40:25 2013

@author: yy3
"""
# from pi3diamond import pi3d
import datetime
import time
import importlib
# from qutip_enhanced import *
from logic.qudip_enhanced import *
importlib.reload(lmfit_models)
import collections
import notebooks.UserScripts.helpers.snippets_awg as sna; importlib.reload(sna)
import notebooks.UserScripts.helpers.shared as shared; importlib.reload(shared)
import notebooks.UserScripts.helpers.sequence_creation_helpers as sch; importlib.reload(sch)

def run_fun(self,
            abort,
            freq=None,
            zfs=70,
            repeat=False,
            repeat_refocus_interval=60.,
            repeat_smallest_only=True,
            wait_repeat=0.0,
            final_transition='both',
            n=1, **kwargs):
    
    _tt = self.queue._transition_tracker
    _pODMR = self.queue._ODMR_logic.pulsedODMRLogic
    _awg = self.queue._awg
    # which setting to use from the following list of parameters.
    # 0th- means first, '01' - means first and subsequenty second
    size = kwargs.pop('size', {'left': '2', 'right': '2'})

    # center frequency 0
    #_tt.mw_mixing_frequency = 2729.0
    #_tt.mw_mixing_frequency_p1 = 3023.0

    track_file = kwargs.pop('track_file', {'left': 'mw_mixing_frequency', 'right': 'zfs'})

    # Nr. of executions.
    odmr_runs = kwargs.pop('odmr_runs', [50000, 500000] + [50000]*3)

    # AWG amplitde. If None then its adjusted to be a pi pulse for pi pulse duration.
    amplitudes = kwargs.pop('amplitudes', [0.5] + [None] + [None] + [0.5]*2)  # Don't touch!
    readout  = kwargs.pop('readout', ['A2']*5)

    # Pi pulse for pulsed or Readout duration for CW
    pi_duration = kwargs.pop('pi_duration', [0.3, 0.3] + [1.0] + [0.3] * 2)

    # df step in the ODMR
    refocus_resolution = kwargs.pop('refocus_resolution', [4.0, 1.0]+[0.15]*3)

    # The span of the ODMR sweep
    refocus_range = kwargs.pop('refocus_range', [3000.0]+[50.0] + [15.0] + [12.8] + [10.])

    refocus_power = kwargs.pop('refocus_power', 16.) # If there is a Pi pulse duration why there is a power here?
    td = kwargs.pop('td', [str({'14N': [0]}),
                           str({'14N': [0]}),
                           str({'14N': [0]}),
                           str({'14N': [0]}),
                           str({'14N': [0]})])
    # buffer time for not overheating the  sample
    buffer_time = kwargs.pop('buffer_time', [10.0]*5)

    # for readout of pulsed odmr
    laser_dur = kwargs.pop('laser_dur', [0.35] * 5)

    # CW or pulsed odmr
    cw_mw = kwargs.pop('cw_mw', [False]+[False] *2 + [False]*2)
    #pi_pulse_factor = kwargs.pop('pi_pulse_factor', [0.5,0.5,1,1,1])
    flip_13c90 = kwargs.pop('flip_13c90', [False]*5) # What does it mean??

    # fit function for ODMR...
    refocus_model = kwargs.pop('refocus_model',
                               [lmfit_models.SincModel(rabi_frequency=10.)] * 2 +
                               [lmfit_models.TripLorentzModel(_tt.get_f('14n_hf'))]*3

    )

    #pi3d.odmr.power = refocus_power
    _pODMR.pulsed_MW1_Power = -41 # refocus_power #FIXME translate power into dBm
    
    # Skipping confocal refocus for now since this is done already via nuclear ops. TODO Add confocal refocus such that this file can be a standalone
    # confocal_pos, date = pi3d.get_last_values_from_file('confocal_pos', flg_out_date=True)
    # pi3d.confocal.x = confocal_pos[0] #why needed? But can be taken from TT
    # pi3d.confocal.y = confocal_pos[1]
    # pi3d.confocal.z = confocal_pos[2]
    # if (datetime.datetime.now() - date).seconds > 3600.*24:
    #     raise Exception('Last refocus was too long ago, do by hand first.')
    # for _ in range(n):
    #     if abort.is_set(): break
    #     pi3d.confocal.run_refocus()
    if freq is not None:
        _tt.current_local_oscillator_freq = freq
    if zfs is not None:
        _tt.zero_field_splitting = zfs
    while True:
        for s in sorted(size):
            if abort.is_set(): break
            for j, char in enumerate(size[s]):
                if abort.is_set(): break
                i = int(char)
                if 'ODMR' in _awg.mcas_dict:
                    del _awg.mcas_dict['ODMR']
                pi3d.odmr.odmr_runs = odmr_runs[i]
                pi3d.odmr.readout_interval = 0.004
                # pi3d.odmr.readout_interval = 1.0
                pi3d.odmr.update_tt = True
                pi3d.odmr.track_file = track_file if j == len(size[s]) - 1 else {'left': None, 'right': None} #tf = None will automatically track to current_local_oscillator_freq and zfs respectively
                pi3d.odmr.custom_model = refocus_model[i]
                pi3d.odmr.parameters = collections.OrderedDict(
                    [
                        ('sweeps', [0]),
                        ('flip_13c90', [flip_13c90[i]]),
                        ('mixer_deg', [-90]),
                        ('transition', [s]),
                        ('pi_duration', [pi_duration[i]]),
                        #('pi_pulse_factor', [pi_pulse_factor[i]]),
                        # ('amplitudes',[amplitudes[i]]),
                        ('buffer_time', [buffer_time[i]]),
                        ('laser_dur', [laser_dur[i]]),
                        ('resonant_ro', [True]),
                        ('cw_mw', [cw_mw[i]]),
                        ('td', [td[i]]),
                        ('center_frequency', np.arange(-refocus_range[i]/2., refocus_range[i]/2.+1e-9, refocus_resolution[i]))
                    ]
                )
                if amplitudes[i] is not None:
                    pi3d.odmr.parameters['amplitudes'] = [amplitudes[i]]
                pi3d.odmr.run(abort)



        if repeat and not abort.is_set():
            if repeat_smallest_only:
                for s in size:
                    if size[s] != '':
                        size[s] = size[s][-1]
            t = 0
            while t < wait_repeat:
                t+=1
                time.sleep(1)
                if abort.is_set(): break
            dummy, date = pi3d.get_last_value_from_file('confocal_pos', flg_out_date=True)
            if (datetime.datetime.now() - date).seconds > repeat_refocus_interval:
                pi3d.confocal.run_refocus()
        else:
            break
    if size['right'] == '':
        final_transition = 'left'
    pi3d.odmr.refocus_transition = final_transition
    pi3d.track_file = track_file
