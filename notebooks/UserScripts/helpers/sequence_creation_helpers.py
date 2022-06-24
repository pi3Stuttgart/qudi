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
import NuclearOPs
import os
# import cPickle
import collections
from qutip_enhanced import data_handling
import datetime

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
    nuclear.ana_trace.analyze_sequence=analyze_sequence
    nuclear.meas_code = meas_code
    nuclear.ret_mcas = ret_mcas

def confocal_settings():
    pi3d.confocal.reset_settings()
    pi3d.confocal.aom_voltage = -6

def gated_counter_settings():
    pi3d.gated_counter.reset_settings()

def settings(**kwargs):
    nuclear_settings(**kwargs)
    confocal_settings()

def file_notes_frequencies():
    out = ""
    for t in pi3d.tt.transitions:
        out += "{}\t{}\n".format(t.name, t.current_frequency)
    return out[:-1]

def create_nuclear(script_path):
    if not os.path.isfile(script_path):
        raise Exception('Error: ', script_path)
    nuclear = NuclearOPs.NuclearOPs()
    nuclear.make_save_location_params(script_path=script_path, folder=r"D:/data/NuclearOps", sub_folder_kw="UserScripts")
    nuclear_name = "NuclearOPs{}_{}".format(nuclear.file_name, datetime.datetime.strftime(nuclear.date_of_creation, nuclear.__TITLE_DATE_FORMAT__))
    nuclear.pld = data_handling.PlotData(title=nuclear_name, gui=True)
    nuclear.file_notes = file_notes_frequencies()
    setattr(pi3d, nuclear_name, nuclear)
    return nuclear


if __name__ == '__main__':
    print(ret_sms(transition='13C90 ms-1'))