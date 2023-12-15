# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 11:40:25 2013

@author: yy3
"""
from pi3diamond import pi3d
import datetime
import time

def run_fun(abort,
            freq=None,
            zfs=2870.3,
            size={'left': '012', 'right': ''},
            track_file={'left': 'current_local_oscillator_freq', 'right': 'zfs'},
            refocus_runtime=    [5, 8,    8, 6],
            # refocus_runtime=    [6,  8,    20, 6],
            refocus_resolution= [0.5, 0.04, 0.006, 1.],
            refocus_range=      [12.,  2.0,  0.12, 100],
            refocus_power=16.,
            awg2g_seq_name=['pulsed0.80', 'pulsed3.00', 'pulsed20.00', 'pulsed0.10'],
            awg128m_seq_name=['', '', '13C90_pi', ''],
            refocus_fit_function=['trip_lorentz_14N', 'trip_lorentz_13C414', 'Lorentz', 'Lorentz'],
            refocus_line=[1, 1, 0, 0],
            repeat=False,     # <===============================================================================
            repeat_refocus_interval=500.,
            repeat_smallest_only=True,
            live_plot=True,
            show_matrix=True,
            wait_repeat=0.0,
            final_transition='both',
            n=0):
    # if pi3d.odmr.state != 'idle' or pi3d.confocal.state != 'idle':
    #     raise Exception('Stop ODMR and Confocal first.')
    # pi3d.odmr.reset_settings()
    # pi3d.odmr.refocus_power = refocus_power
    # pi3d.odmr.live_plot = live_plot
    # pi3d.odmr.show_matrix = show_matrix
    # pi3d.odmr.external_stop_request = abort
    confocal_pos, date = pi3d.get_last_values_from_file('confocal_pos', flg_out_date=True)
    pi3d.confocal.x = confocal_pos[0]
    pi3d.confocal.y = confocal_pos[1]
    pi3d.confocal.z = confocal_pos[2]
    if (datetime.datetime.now() - date).seconds > 3600.*24:
        raise Exception('Last refocus was too long ago, do by hand first.')
    for _ in range(n):
        if abort.is_set(): break
        pi3d.confocal.run_refocus()
    if freq is not None:
        pi3d.tt.current_local_oscillator_freq = freq
    if zfs is not None:
        pi3d.tt.zero_field_splitting = zfs
    while True:
        for s in sorted(size):
            if abort.is_set(): break
            for j, char in enumerate(size[s]):
                if abort.is_set(): break
                i = int(char)
                tf = track_file if j == len(size[s]) - 1 else {'left': None, 'right': None} #tf = None will automatically track to current_local_oscillator_freq and zfs respectively
                pi3d.odmr.do_frequency_refocus(
                    refocus_runtime=refocus_runtime[i],
                    refocus_range=refocus_range[i],
                    awg2g_seq_name_left="{}_left".format(awg2g_seq_name[i]),
                    awg2g_seq_name_right="{}_right".format(awg2g_seq_name[i]),
                    awg128m_seq_name=awg128m_seq_name[i],
                    refocus_resolution=refocus_resolution[i],
                    refocus_line=refocus_line[i],
                    refocus_fit_function=refocus_fit_function[i],
                    refocus_transition=s,
                    track_file=tf,
                    update_tt=True
                )
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

def evaluate(**kwargs):
    l = pi3d.get_values_time_span('current_local_oscillator_freq', '20160429-h00m00s00')

