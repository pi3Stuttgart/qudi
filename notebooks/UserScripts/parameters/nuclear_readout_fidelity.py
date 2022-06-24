from __future__ import print_function, absolute_import, division
from imp import reload

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
from collections import OrderedDict
from qutip_enhanced.analyze import PlotData
import qutip_enhanced.sequence_creator as sc

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

ewf_l = np.repeat([
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170413-h18m16s29np14nzrot_crot_1_0/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)),
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170413-h18m05s34np14nzrot_crot_1_1/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)),
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170413-h17m56s13np14nzrot_crot_1_2/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)),
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170720-h09m28s46np14nzrot_crot_2_0/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)),
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170720-h09m36s40np14nzrot_crot_2_1/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=-90)),
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170720-h09m48s17np14nzrot_crot_3_0/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=75)),
    E.WaveFile(filepath="D:/Python/pi3diamond/UserScripts/Robust/test_electron_pi/pulses/20170720-h09m49s52np14nzrot_crot_3_1/mw_aphi.dat",
               rp=pi3d.tt.rp('e_rabi', mixer_deg=75)),
], 1)

_WAVE_FILE_DICT_ = {
    '13C414': r"D:/Python/pi3diamond/UserScripts/Robust/test_qutrit_cphase_gates/pulses/20170314-h11m24s03_qutrit_cphase_c14n_t414/mw_aphi.dat",
    '13C90': r"D:/Python/pi3diamond/UserScripts/Robust/test_qutrit_cphase_gates/pulses/20170317-h18m07s08_qutrit_cphase_c14n_t90/mw_aphi.dat",
    '13C': r"D:/Python/pi3diamond/UserScripts/Robust/test_qutrit_cphase_gates/pulses/20170318-h08m34s04_qutrit_cphase_c414_t90/mw_aphi.dat"
    }

wfd = dict()
for key, val in _WAVE_FILE_DICT_.items():
    wfd[key] = E.WaveFile(filepath=val,
                          rp=pi3d.tt.rp('e_rabi', mixer_deg=75))

def xy2aphi(xy):
    norm = np.array([np.linalg.norm(xy, axis=1)]).transpose()
    phi = np.arctan2(xy[:, 1:2], xy[:, 0:1])
    return np.concatenate([norm, phi], axis=1)

chrestenson = np.loadtxt(r"D:/Python/pi3diamond/UserScripts/Robust/test_doublequantumnuc/20170303-h16m20s26chrestenson/fields.dat")
chrestenson_aphi = [xy2aphi(chrestenson[:, 1:3]), xy2aphi(chrestenson[:, 3:5])]

waitmurf = 2.


def ret_ret_mcas(pds):
    def ret_mcas(current_iterator_df):

        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m':[1]})

        for idx, _I_ in current_iterator_df.iterrows():

            sna.init_14N(mcas, mn=_I_['init_14n'], new_segment=True)
            sna.ssr(mcas, frequencies=pi3d.tt.mfl({'14N': [int(_I_['init_14n'])]}), nuc='14N', robust=True, repetitions=int(450), mixer_deg=75)
            sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14N': [+1]}),
                                       pi3d.tt.mfl({'14N': [0]}),
                                       pi3d.tt.mfl({'14N': [-1]})
                                       ], nuc='14N', robust=True, repetitions=int(1200), mixer_deg=75)
        return mcas

    return ret_mcas


def settings(pdc={}):
    ana_seq = [
        ['init', '<', 'auto', 450, 1, 1],
        ['init', '>', -1, 1, 1, 1],
        ['result', '<', -1, 1200, 1, 3],
        ['init', '>', -1, 1, 1, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )
    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 1
    nuclear.maximum_odmr_drift = 0.05
    nuclear.refocus_moving_average_factor = 1

    nuclear.analyze_type = 'multifreq'


    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(10)),
            ('init_14n', ['+1', '0', '-1']),
            ('x', range(3)),
        )
    )

    nuclear.number_of_simultaneous_measurements = 1


def run_fun(abort, **kwargs):
    settings()
    pi3d.gated_counter.points = 32000
    nuclear.debug_mode = False
    nuclear.run(abort)