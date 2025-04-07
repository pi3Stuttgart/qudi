# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division
from imp import reload

#from pi3diamond import pi3d
import numpy as np
import itertools
import fractions
import copy
import types
# import Analysis
import logic.NuclearOPs
import os
# import cPickle
import collections
from logic.qudip_enhanced import data_handling
import datetime
from importlib import reload as reload
from scipy import special

# def full_wavelength(flf, target_length_mus):
#     """
#     WORKS FOR ONE OR TWO FREQUENCIES RIGHT NOW
#
#     returns a length_mus, for which all frequencies f_i in frequency list make a full wavelength.
#
#     :param flf: list of frequencies given as fractions.Fraction(f)
#     :param target_length_mus: float
#     This method tries to output the length_mus which is closest to target_length_mus
#     :return: float
#     length_mus
#     """
#     dn_list = [flf.denominator for f in flf]
#     n_list =  [flf.nominator for f in flf]
#     pd = np.prod(dn_list)
#     n_list =
#     cd = np.prod(dn_list)
#     n_f_cd_list = [int(f.numerator/float(f.denominator)*cd) for f in flf]
#     return  fractions.Fraction(np.prod(n_f_cd_list), cd)

    # if len(frequency_list) == 1:
    #     f = round(frequency_list[0], num_digits)
    #     return round(target_length_mus*f)/f
    # n = max([len(str(round(f, num_digits)).split('.')) for f in frequency_list])
    # fl = np.array(frequency_list)*n
    # min_lm = fractions.Fraction(fl[0], fl[1])
    # if target_length_mus < min_lm:
    #     raise Exception("The chosen 'target_length_mus' is too short or the given frequencies are too odd or too many decimal places have been given. \nSuggested procedure is either reducing num_digits or enlengthening 'num_digits'.")
    # length_mus = round(target_length_mus/min_lm)*min_lm
    # return length_mus

    
def envelope(t0, t_space, pulse_dur, rise_time = .256):
    # hermite envelope after Bradley et al.
    a = 0.5*special.erf(2*(rise_time-t_space+t0)/rise_time)
    b = 0.5*special.erf(2*(rise_time+t_space-(pulse_dur+t0))/rise_time)
    return 1-a-b-1
    
def sin_envelope(t0, t_space, pulse_dur, phase, rf_freq, rise_time = .256/4):
    # sine signal under envelope
    sin = np.sin(2*np.pi*rf_freq*t_space+phase)
    return sin*envelope(t0, t_space, pulse_dur, rise_time)


def check_shift(t0, t_space, pulse_dur, phase, rf_freq, rise_time = .001):
    # t0: start of pulse
    # t_space: sample list
    # rise_time: rise time of error function for envelope. When no envelope is used, rectangular is approximated by rise time of 1ns.
    # shifts beginning of rf pulse by maximum of rf-period/2 to minimize the area under the rf signal.
    time_steps = t_space[1]-t_space[0]
    area_up = np.abs(np.sum(sin_envelope(t0, t_space, pulse_dur, rf_freq, phase, rise_time)))
    area_down = area_up
    n_up = 0
    n_down = 0
    while time_steps * n_up < 1/rf_freq/2:
        n_up+=1
        next_area_up = np.abs(np.sum(sin_envelope(t0 + time_steps * n_up, t_space, pulse_dur, phase, rf_freq, rise_time)))
        if next_area_up > area_up:
            n_up -= 1
            break
        else:
            area_up = next_area_up
    while time_steps * n_down < 1/rf_freq/2:
        n_down-=1
        next_area_down = np.abs(np.sum(sin_envelope(t0 + time_steps * n_down, t_space, pulse_dur, phase, rf_freq, rise_time)))
        if next_area_down > area_down:
            n_down += 1
            break
        else:
            area_down = next_area_down
    if area_up < area_down:
        n = n_up
    elif area_up > area_down:
        n = n_down
    else:
        n = 0
    return time_steps * n


def shift_pulse(seq, t_space, rf_freq):
    # Shift RF Pulse to be aligned with start of period of sine wave.
    total_time = 0
    for key in seq.column_dict.keys():
        total_time += np.sum(seq.times_fields_aphi(key), axis = 0)[0]
    mw = seq.times_fields_aphi('mw')
    rf = seq.times_fields_aphi('rf')
    wait = seq.times_fields_aphi('wait')
    shifts = []
    current_time = 0
    # loop over all sequence steps
    # if step is an rf pulse, check by how much it needs to be shifted to be aligned with the rotating frame.
    for step in seq.sequence_steps:
        idx = int(step[1])-1
        if step[0] == 'mw':
            current_time += mw[idx, 0]
        if step[0] == 'rf':
            shifts.append(check_shift(current_time, t_space, rf[idx, 0], rf[idx, 2], rf_freq))
            current_time += rf[idx, 0]
        elif step[0] == 'wait':
            current_time += wait[idx, 0]
    #print(shifts)
    return shifts


def full_wavelength_improved(frequency_list, target_length_mus, num_digits=3, sampling_frequency=12):
    fl = copy.deepcopy(frequency_list)
    if target_length_mus < 5*64/(sampling_frequency*1000):
        raise Exception('target_length_mus too short!')
    fl.append(fractions.Fraction(sampling_frequency*1000, 64))
    n = max([len(str(round(f, num_digits)).split('.')) for f in fl])
    fl = np.array(fl)*n
    min_lm = fractions.Fraction(fl[0], fl[1])
    if target_length_mus < min_lm:
        raise Exception("The chosen 'target_length_mus' is too short or the given frequencies are too odd or too many decimal places have been given. \nSuggested procedure is either reducing num_digits or enlengthening num_digits.")
    length_mus = round(target_length_mus/min_lm)*min_lm
    return length_mus - 0.9/(sampling_frequency*1e3)


def ret_sms(**kwargs):
    def sspin_type(nuc):
        s = nuc.split(' ')[0].replace('14N', '').replace('13C', '').replace('14n', '').replace('13c', '')
        nuc = nuc.replace('14N', '14n')
        if '14n' in nuc:
            spin_type = '14n ' + s
        else:
            spin_type = '13c'
        return {'s': s, 'spin_type': spin_type}
    if 'transition' in kwargs:
        transition = kwargs['transition'].split(' ')
        ms = transition[1][2:]
        nuc = transition[0]
        r = {'nuc': nuc, 'ms': ms}
        r.update(sspin_type(nuc))
        return r
    elif 'nuc' in kwargs:
        return sspin_type(kwargs['nuc'])

def ret_tl(param_lists):
    return list(itertools.product(*[x[1] for x in param_lists]))

def ret_pds(param_lists, tl):
    return [collections.OrderedDict([[param_lists[i][0], config[i]] for i in range(len(config))]) for config in tl]

def nuclear_settings(nuclear, ret_mcas, analyze_sequence, meas_code, pdc=None, **kwargs):
    if pdc is None:
        pdc = {}
    nuclear.reset_settings()
    if 'script_path' in kwargs:
        nuclear.make_save_location_params(script_path=kwargs['script_path'], folder=r"D:/data/NuclearOps", sub_folder_kw="UserScripts")
    for key, val in pdc.items():
        if hasattr(val, '__iter__'):
            nuclear.file_name += "_{}{}".format(key, "_".join([str(i) for i in val]))
        else:
            nuclear.file_name += "_{}{}".format(key, val)

    # FIXME
    nuclear.ana_trace.analyze_sequence=analyze_sequence
    nuclear.meas_code = meas_code
    nuclear.ret_mcas = ret_mcas

def confocal_settings():
    pass
    #print('fix me 2')
    #FIXME later deprecarted in qudi
    #pi3d.confocal.reset_settings()
    #pi3d.confocal.aom_voltage = -6

def gated_counter_settings():
    pass
    #FIXME depracated in qudi
    #print('fix me 3')
    #pi3d.gated_counter.reset_settings()

def settings(**kwargs):
    nuclear_settings(**kwargs)
    confocal_settings()

def file_notes_frequencies():
    out = ""
    for t in pi3d.tt.transitions:
        out += "{}\t{}\n".format(t.name, t.current_frequency)
    return out[:-1]

def create_nuclear(script_path):
    reload(logic.NuclearOPs)
    if not os.path.isfile(script_path):
        raise Exception('Error: ', script_path)
    nuclear = logic.NuclearOPs.NuclearOPs()#TODO fill config here
    nuclear.make_save_location_params(script_path=script_path,
                                      folder= r"D:/Data/NuclearOps",
                                      sub_folder_kw="UserScripts")
    nuclear_name = "NuclearOPs{}_{}".format(nuclear.file_name, datetime.datetime.strftime(nuclear.date_of_creation, nuclear.__TITLE_DATE_FORMAT__))
    nuclear.pld = data_handling.PlotData(title=nuclear_name, gui=True)
    nuclear.file_notes = ''#TODO get transition tracker here... file_notes_frequencies()
    #setattr(pi3d, nuclear_name, nuclear)##todo
    return nuclear

if __name__ == '__main__':
    print(ret_sms(transition='13C90 ms-1'))