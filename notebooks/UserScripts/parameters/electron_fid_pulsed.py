# coding=utf-8
from __future__ import print_function, absolute_import, division
from imp import reload
__metaclass__ = type

from pi3diamond import pi3d
import AWG_M8190A_Elements as E
#
from qutip_enhanced import *
import time, datetime

import UserScripts.helpers.sequence_creation_helpers as sch;reload(sch)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.standard_awg_sequences as sas; reload(sas)
import UserScripts.helpers.snippets_awg as sna; reload(sna)

seq_name = os.path.basename(__file__).split('.')[0]

def write_sequence():
    nstep = 80
    total_dur = 100.
    total_dur = nstep*np.around(np.array(total_dur/nstep)*12e3)/12e3
    pi3d.pulsed.mcas = sas.ret_awg_seq(
        name='fid',
        length_mus=total_dur,
        transition='left',
        frequencies=[200.],
        num_step=nstep,
    )


def settings():
    write_sequence()
    pi3d.pulsed.refocus_interval = 1
    pi3d.pulsed.odmr_interval = 30
    pi3d.pulsed.mw_power = 16.
    pi3d.pulsed.sequence_name = seq_name
    pi3d.pulsed.planned_sweeps = 1e5
    pi3d.pulsed.fit_function = 'CosineMultiDet'


def run_fun(abort, **kwargs):
    settings()
    pi3d.pulsed.run(abort)
    #     pi3d.pulsed._do_fit_changed()
    #     data.set_observations([dict(omega="{:.6f}".format(1000./pi3d.pulsed.rabi_period),
    #                                 date=pd.to_datetime('now').__str__())])
    #
    # for d, d_idx, idx, sub in data.iterator(['mixer_deg']):
    #     sub = sub.drop('mixer_deg', axis=1)
    #     if len(sub) == len(collections.OrderedDict(param_lists)['amp0']) and len(sub) > 3:
    #         print('Updating e_rabi {}'.format(d))
    #         pi3d.tt.rabi_parameters["e_rabi_ou{:.0f}deg{}".format(1000 * pi3d.awgs['2g'].ch[1].output_amplitude, d['mixer_deg'])].update_file(sub)
