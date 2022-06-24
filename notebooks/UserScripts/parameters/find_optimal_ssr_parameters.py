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
            d = {'14n+1': dict(frequencies=[pi3d.tt.mfl({'14n': [+1]}), pi3d.tt.mfl({'14n': [0, -1]})] , nuc='14N'),
                 '14n0':  dict(frequencies=[pi3d.tt.mfl({'14n': [0]}), pi3d.tt.mfl({'14n': [+1, -1]})], nuc='14N'),
                 '14n-1': dict(frequencies=[pi3d.tt.mfl({'14n': [-1]}), pi3d.tt.mfl({'14n': [+1, 0]})], nuc='14N'),
                 '14n': dict(frequencies=[pi3d.tt.mfl({'14N': [+1]}), pi3d.tt.mfl({'14N': [0]}), pi3d.tt.mfl({'14N': [-1]})], nuc='14N'),
                 '13c414': dict(frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5]}),
                                             pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [-.5]})], nuc='13C414'),
                 '13c90':  dict(frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5]}),
                                             pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [-.5]})], nuc='13C90'),
                 }
            sna.ssr(mcas,
                    transition='left',
                    robust=True,
                    repetitions=_I_['repetitions'],
                    laser_dur=_I_['laser_dur'],
                    wait_dur=_I_['wait_dur'],
                    mixer_deg=-90,
                    step_idx=0,
                    **d[_I_['transition']])
        return mcas
    return ret_mcas

def settings(pdc):
    ana_seq = [
        ['result', '<', 0, 100, 0, 2],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code,
        script_path=__file__,
    )

    nuclear.analyze_type = 'consecutive_b'
    nuclear.parameters = collections.OrderedDict(
        (
            ('sweeps', range(1)),
            ('transition', ['13c90', '13c414', '14n']),
            ('repetitions', [90]),
            ('laser_dur',   E.round_length_mus_full_sample(np.arange(0.1, 0.3+1e-12, 0.005))),
            ('wait_dur',    E.round_length_mus_full_sample([1.0])),
        )
    )
    nuclear.odmr_interval = 1
    nuclear.refocus_interval = 1
    nuclear.maximum_odmr_drift = 0.02
    nuclear.refocus_moving_average_factor = 1
    nuclear.number_of_simultaneous_measurements = 1


def run_fun(abort, **kwargs):

    nuclear.debug_mode = False
    pi3d.gated_counter.number_of_memories = 2
    pi3d.gated_counter.trace.average_results=True
    pi3d.gated_counter.trace.binning_factor = 13
    pi3d.gated_counter.n_values = 1200*1500
    pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values%pi3d.gated_counter.trace.binning_factor
    settings({})
    nuclear.run(abort)
