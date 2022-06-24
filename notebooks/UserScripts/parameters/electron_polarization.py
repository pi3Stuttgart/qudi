from __future__ import print_function, absolute_import, division
from imp import reload

import numpy as np
from collections import OrderedDict
import Analysis
import time, datetime, os, itertools
import UserScripts.helpers.sequence_creation_helpers as sch
reload(sch)
import multi_channel_awg_seq as MCAS
reload(MCAS)
import UserScripts.helpers.snippets_awg as sna
reload(sna)
import AWG_M8190A_Elements as E
import oxxius_laser

from pi3diamond import pi3d
seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):

        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            mcas.start_new_segment('hi')
            if _I_['laser'] == 'red':
                pi3d.oxxius_laser._set_laser_diode_current_fast(_I_['diode_current'])
            if _I_['e_pi']:
                sna.single_robust_electron_pi(mcas, nuc='all', frequencies=pi3d.tt.mfl('14N0'), new_segment=True)
            if _I_['laser'] == 'red' and _I_['x'] > 0:
                lc = np.around((_I_['x']/(320/12e3))).astype(int)
                mcas.start_new_segment(name='polarize', loop_count=lc)
                mcas.asc(length_mus=320/12e3, name='polarize', red=True)
            elif _I_['laser'] == 'green' and _I_['x'] > 0:
                mcas.start_new_segment(name='polarize')
                mcas.asc(length_mus=_I_['x'], name='polarize', green=True)

            mcas.start_new_segment(name='laserdelay')
            mcas.asc(length_mus=2., name='red_laserdelay')

            t = '13C414 mS0'
            period = 200.
            sna.nuclear_rabi(mcas,
                             name=t,
                             amplitudes=[pi3d.tt.rp(t, period=period).amp],
                             length_mus=period/2.,
                             frequencies=[pi3d.tt.t(t).current_frequency]
                             )
            sna.ssr(mcas, frequencies=[pi3d.tt.mfl('13C414_left'), pi3d.tt.mfl('13C414_right')], nuc='13C414', robust=True, mixer_deg=-90, step_idx=0)
        return mcas
    return ret_mcas

def settings(pdc):
    sch.settings(
                 nuclear=nuclear,
                 ret_mcas=ret_ret_mcas(pdc),
                 analyze_sequence=[
                    ['result', '<', 0, 123, 0, 2],
                ],
                 pdc=pdc,
                 meas_code=meas_code
    )
    nuclear.analyze_type = 'consecutive_b'
    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(20)),
            # ('diode_current', np.arange(74, 78, .5)),
            ('diode_current', [sna.__CURRENT_POL_RED__]),
            ('e_pi', [True, False]),
            ('laser', ['red']),
            # ('x', E.round_length_mus_full_sample(np.arange(0, 75, 5)))
            ('x', E.round_length_mus_full_sample(np.arange(0, 100., 8.)))
        )
    )

    nuclear.odmr_interval =1
    nuclear.refocus_interval = 3
    nuclear.maximum_odmr_drift = 0.03
    nuclear.refocus_moving_average_factor = 1

    nuclear.number_of_simultaneous_measurements = 1 #len(nuclear.parameters['x'])


def run_fun(abort, **kwargs):

    settings({})
    pi3d.gated_counter.points = 1000
    nuclear.debug_mode = False
    nuclear.run(abort)