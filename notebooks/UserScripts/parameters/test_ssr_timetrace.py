from __future__ import print_function, absolute_import, division
from imp import reload

from pi3diamond import pi3d
import numpy as np
import time, datetime, os, itertools
import UserScripts.helpers.sequence_creation_helpers as sch
from qutip_enhanced import *
reload(sch)

import pym8190a
import UserScripts.helpers.snippets_awg as sna

reload(sna)
import collections

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

def ret_ret_mcas(pds):
    def ret_mcas(current_iterator_df):

        mcas = pym8190a.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})

        for idx, _I_ in current_iterator_df.iterrows():

            mcas.start_new_segment('count1', loop_count=10)
            mcas.asc(length_mus=192/12e3, gate=True)
            mcas.asc(length_mus=20.,  green=True)
            mcas.asc(length_mus=192/12e3)
            mcas.asc(length_mus=5., green=True)
            mcas.asc(length_mus=192 / 12e3)
            mcas.asc(length_mus=10., green=True)
            mcas.start_new_segment('count2', loop_count=7)
            mcas.asc(length_mus=192/12e3, gate=True)
            mcas.asc(length_mus=20.,  green=True)
            mcas.asc(length_mus=192/12e3)
            mcas.asc(length_mus=5., green=True)
            mcas.asc(length_mus=192 / 12e3)
            mcas.asc(length_mus=10., green=True)

            # pi3d.gated_counter.trace.analyze_sequence[0] = ['init', '<', 60*_I_['init_threshold']/450., _I_['ssr_repetitions'], 1, _I_['n_freq_init']]
            # if _I_['readout_on'] == '14n':
            #     pi3d.gated_counter.trace.analyze_sequence[2] = ['result', '<', -1, 1200, 1, 3]
            # else:
            #     pi3d.gated_counter.trace.analyze_sequence[2] = ['result', '<', -1, 1200, 1, 2]
            # sna.init_multiple(mcas, number_of_frequencies=_I_['n_freq_init'], **_I_)
            #
            # if _I_['readout_on'] == '14n':
            #     nuclear.analyze_type = 'multifreq'
            #
            #     sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14N': [+1]}),
            #                                pi3d.tt.mfl({'14N': [0]}),
            #                                pi3d.tt.mfl({'14N': [-1]})
            #                                ], nuc='14N', robust=True, repetitions=int(1200), mixer_deg=-90)
            # elif _I_['readout_on'] == '13c414':
            #     nuclear.analyze_type = 'standard'
            #     sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5]}),
            #                                pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [-.5]})], nuc='13c414', robust=True, repetitions=int(1200), mixer_deg=-90)
            # elif _I_['readout_on'] == '13c90':
            #     nuclear.analyze_type = 'standard'
            #     sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5]}),
            #                                pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [-.5]})], nuc='13c90', robust=True, repetitions=int(1200), mixer_deg=-90)
            # else:
            #     # nuclear.analyze_type = 'standard'
            #     # pi3d.gated_counter.trace.analyze_sequence[2] = ['result', '<', 180, 1200, 1, 1]
            #     # sna.ssr(mcas, frequencies=pi3d.tt.mfl({'14N': [int(_I_['readout_on'][:2])], '13C414': [float("{}0.5".format(_I_['readout_on'][2]))], '13C90': [float("{}0.5".format(_I_['readout_on'][3]))]}), nuc='13c90', robust=True, repetitions=1200, mixer_deg=-90)
            #     nuclear.analyze_type = 'standard'
            #     frequencies_not = pi3d.tt.mfl({'14n': [+1, 0, -1], '13c414': [+.5, -.5], '13c90': [+.5, -.5]})
            #     frequencies = pi3d.tt.mfl({'14N': [int(_I_['readout_on'][:2])], '13C414': [float("{}0.5".format(_I_['readout_on'][2]))], '13C90': [float("{}0.5".format(_I_['readout_on'][3]))]})
            #     frequencies_not = np.delete(frequencies_not, np.argwhere(frequencies_not == frequencies[0])[0, 0])
            #     pi3d._frequencies = frequencies
            #     pi3d._frequencies_not = frequencies_not
            #     sna.ssr(mcas, frequencies=[frequencies, frequencies_not], nuc='13c90', robust=True, repetitions=1200, mixer_deg=-90)
            # with open("{}{}deleteseq.dat".format(_I_['ssr_repetitions'], _I_['readout_on']), "w") as text_file:
            #     print(mcas.dl('2g', 1).ret_info(), file=text_file)
            # with open("{}{}delete{}.dat".format(_I_['ssr_repetitions'], _I_['readout_on'], nuclear.analyze_type), "w") as text_file:
            #     print(pi3d.gated_counter.trace.analyze_sequence.__str__(), file=text_file)

        return mcas

    return ret_mcas


def settings(pdc={}):
    ana_seq = [
        ['init', '<', 55, 450, 1, 2],
        ['init', '>', -1, 1, 1, 1],
        ['result', '<', -1, 1200, 1, 2],
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
    nuclear.maximum_odmr_drift = 0.015
    nuclear.refocus_moving_average_factor = 1

    nuclear.analyze_type = 'none'

    nuclear.parameters = collections.OrderedDict(
        (
            ('sweeps', range(30)),
        )
    )

    nuclear.number_of_simultaneous_measurements = 1


def run_fun(abort, **kwargs):
    # settings()
    # pi3d.gated_counter.points = 4000
    # nuclear.debug_mode = False
    # nuclear.run(abort)
    # nuclear.pld.gui.close_gui()
    nuclear.pld.gui.fig.clear()
    nuclear.pld.gui.ax = nuclear.pld.gui.fig.add_subplot(111)
    reload(dh)
    data = dh.Data(parameter_names=['col', 'index'], observation_names=['value'])
    data.init()
    nuclear.pld.set_data(data=data)



    ana_seq = [
        ['init', '<', -1, 450, 1, 2],
        # ['init', '>', -1, 1, 1, 1],
        # ['result', '<', -1, 1200, 1, 2],
        # ['init', '>', -1, 1, 1, 1],
    ]
    ds = 192
    dt = ds/12e3
    lc0 = 1000
    pi3d.gated_counter.trace.analyze_sequence = ana_seq
    mcas = pym8190a.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2]})
    mcas.start_new_segment('gate0', loop_count=1)
    mcas.asc(length_smpl=ds, gate=True)
    mcas.asc(length_mus=0.2, green=True)
    mcas.asc(length_smpl=ds, memory=True)
    mcas.asc(length_smpl=ds, gate=True)
    mcas.asc(length_mus=10., green=True)
    mcas.asc(length_smpl=ds, memory=True)
    mcas.asc(length_mus=100., green=True)
    # mcas.asc(length_mus=1 * dt, memory=False)
    # mcas.asc(length_mus=1 * dt, memory=True)
    # mcas.asc(length_mus=1 * dt, memory=False)
    # mcas.asc(length_mus=1 * dt, memory=True)
    # mcas.asc(length_mus=1 * dt, memory=False)
    # mcas.asc(length_mus=1 * dt, memory=True)
    # mcas.asc(length_mus=1 * dt, green=False)
    #
    # mcas.asc(length_smpl=ds, memory=True)
    # mcas.asc(length_smpl=ds, memory=False)
    # mcas.asc(length_mus=100 * dt, memory=False)
    # mcas.asc(length_mus=1 * dt, memory=True)
    # mcas.asc(length_mus=1 * dt, memory=False)
    # mcas.asc(length_mus=1 * dt, memory=True)
    # mcas.asc(length_mus=1 * dt, memory=False)
    #
    # mcas.asc(length_mus=1 * dt, memory=True)
    # mcas.asc(length_mus=50000 * dt, green=True)
    # mcas.asc(length_mus=dt, gate=True)
    # mcas.start_new_segment('ct0', loop_count=lc0)
    # # mcas.asc(length_mus=dt, gate=True)
    # mcas.asc(length_mus=1000*dt, green=True)
    # mcas.asc(length_mus=1*dt)
    # mcas.asc(length_mus=1*dt, green=True)
    # mcas.asc(length_mus=1*dt)
    # for i in range(ana_seq[0][-1] - 2):
    #     mcas.asc(length_mus=1*dt, green=True)
    #     mcas.asc(length_mus=1*dt)
    # mcas.start_new_segment('w0')
    # mcas.asc(length_mus=dt, green=True)
    # mcas.asc(length_mus=dt)
    # mcas.asc(length_mus=dt, green=True)
    # mcas.asc(length_mus=dt)
    # mcas.start_new_segment('wait', loop_count=1)
    # mcas.asc(length_mus=.96, green=False)
    # mcas.start_new_segment('count2', loop_count=lc1)
    # mcas.asc(length_mus=dt, gate=True)
    # mcas.asc(length_mus=dt, green=True)
    # mcas.asc(length_mus=dt)
    # mcas.asc(length_mus=10., green=True)
    # mcas.asc(length_mus=dt)
    # mcas.asc(length_mus=10., green=True)
    # mcas.asc(length_mus=dt, green=True)
    # mcas.asc(length_mus=dt)
    # mcas.asc(length_mus=dt, green=True)
    # mcas.asc(length_mus=dt)
    # mcas.asc(length_mus=200., green=True)
    pi3d.md['test_ssr_timetrace'] = mcas
    pi3d.md['test_ssr_timetrace'].initialize()
    # pi3d.gated_counter.points = pi3d.gated_counter.number_of_memories*(n*(lc0+lc1))
    pi3d.gated_counter.points = 20
    pi3d.gated_counter.count(abort, ch_dict=mcas.ch_dict, turn_off_awgs=True)
    # del pi3d.md['test_ssr_timetrace']
    # print(pi3d.timetagger.gated_counter.getData())
    pi3d.d = pi3d.timetagger.gated_counter.getData()
    for col in range(ana_seq[0][-1]):
        wh = np.where(pi3d.d[:, col] > 0)[0]
        df = pd.DataFrame(wh, columns=['value'])
        df = df.reset_index()
        df['col'] = col
        df = df[['col', 'index', 'value']]
        print(df.col.unique(), col, len(df))
        nuclear.data._df = pd.concat([nuclear.data.df, df], ignore_index=True)
    # print(nuclear.data.df)

    nuclear.pld.new_data_arrived()
    # nuclear.pld.gui.ax.plot(wh, label="{}".format(col))
    # nuclear.pld.gui.fig.tight_layout()
    # nuclear.pld.gui.canvas.draw()

