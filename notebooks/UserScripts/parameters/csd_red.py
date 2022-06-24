from __future__ import print_function, absolute_import, division
from imp import reload

import numpy as np
import time, datetime, os, itertools
import UserScripts.helpers.sequence_creation_helpers as sch
reload(sch)
import multi_channel_awg_seq as MCAS
reload(MCAS)
import UserScripts.helpers.snippets_awg as sna
reload(sna)
from pi3diamond import pi3d
import UserScripts.helpers.shared as ush;reload(ush)
import collections
import pym8190a.elements as E
from qutip_enhanced import *

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})

        for idx, _I_ in current_iterator_df.iterrows():
            pi3d.gated_counter.trace.analyze_sequence[0][-1] = int(_I_['n_csd'])
            sna.polarize_green(mcas, length_mus=_I_['length_mus_green'], new_segment=True)
            mcas.start_new_segment('csd', loop_count=int(_I_['n_csd']))
            mcas.asc(length_mus=192/12e3, gate=True)
            mcas.asc(length_smpl=_I_['length_mus_red'], red=True)
            mcas.asc(length_mus=192 / 12e3, memory=True)
        return mcas

    # (5000000, 'run')
    # (5000000, 'sm')
    # (5000000, 'step')
    # (0, 'k')
    # (0, 'memory')
    # (5000000, 'n')
    # len_step_l
    # Out[106]: [1]
    # number_of_steps
    # Out[107]: 1
    # len_k_l
    # Out[108]: [0]
    # len_memory_l
    # Out[109]: [300]

    return ret_mcas

def settings(pdc):
    ana_seq = [
        ['result', '<', 0, 1, 0, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code,
        script_path=__file__,
    )

    nuclear.analyze_type = None
    nuclear.parameters = collections.OrderedDict(
        (
            ('sweeps', range(100)),
            ('length_mus_red', [10.]),
            ('length_mus_green', [1.]),
            ('n_csd', [300])
        )
    )

    nuclear.odmr_pd = dict(
            n=1,
            freq=None,
            size={'left': '', 'right': ''},
            repeat=False,
        )

    nuclear.odmr_pd_refocus = dict(
            n=1,
            freq=None,
            size={'left': '', 'right': ''},
            repeat=False,
        )

    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 1000
    if hasattr(nuclear, 'maximum_odmr_drift'):
        del nuclear.maximum_odmr_drift
    nuclear.number_of_simultaneous_measurements = 1


def run_fun(abort, **kwargs):

    nuclear.debug_mode = False
    pi3d.gated_counter.n_values = 120000*1500
    pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values%pi3d.gated_counter.trace.binning_factor
    settings({})
    nuclear.run(abort)
