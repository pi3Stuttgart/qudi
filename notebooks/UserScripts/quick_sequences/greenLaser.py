# coding=utf-8
import datetime
import numpy as np
import os
import importlib
import notebooks.UserScripts.helpers.sequence_creation_helpers as sch; importlib.reload(sch)
import notebooks.UserScripts.helpers.shared as shared
from hardware.Keysight_AWG_M8190.pym8190a import MultiChSeq as MultiChSeq
import notebooks.UserScripts.helpers.snippets_awg as sna
importlib.reload(sna)
importlib.reload(shared)
#importlib.reload(MultiChSeq)
import notebooks.UserScripts.helpers.shared as ush;importlib.reload(ush)
from logic.qudip_enhanced import *
import hardware.Keysight_AWG_M8190.elements as E
from collections import OrderedDict


seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

__TAU_HALF__ = 2*192/12e3
__SAMPLE_FREQUENCY__ = 12e3#e.__SAMPLE_FREQUENCY__

ael = 1.0

def ret_ret_mcas(pdc):
    def ret_mcas(self, current_iterator_df):
        sequence_name = 'green_laser'
        #print(self, current_iterator_df)
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=0.1)  # Starting... histogram 0
        mcas.asc(length_mus=3.0, green=True, name='Green')
        mcas.asc(length_mus=3.1)
        # freq = [70.0]#np.array([self.queue.tt.mw_mixing_frequency])
        # pi_2_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', amp=1.0).pi2
        # pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', amp=1.0).pi
        # for idx, _I_ in current_iterator_df.iterrows():
        #     mcas.asc(length_mus=1.0, name='initial_delay')
        #     mcas.asc(length_mus=3.0, green=True, name='Green')
        #     mcas.asc(length_mus=1.0)
        #     mcas.asc(A1=True, length_mus=30.,
        #              name='A1_init')  # Init NV with A1 laser (about 1-3 µs). This step can be skipped for the very first tests #as the green laser will also intialise somehow.
        #     mcas.asc(length_mus=2.0)

        #     sna.electron_rabi(
        #         mcas,
        #         new_segment=False,
        #         length_mus=pi_2_dur,
        #         amplitudes=[1.0],
        #         frequencies=freq,
        #         mixer_deg=[-90]
        #     )
        #     mcas.asc(length_mus=_I_['tau'])

        #     sna.electron_rabi(
        #         mcas,
        #         new_segment=False,
        #         length_mus=pi_dur,
        #         amplitudes=[1.0],
        #         frequencies=freq,
        #         mixer_deg=[-90]
        #     )
        #     mcas.asc(length_mus=_I_['tau'])

        #     sna.electron_rabi(
        #         mcas,
        #         new_segment=False,
        #         length_mus=pi_2_dur,
        #         amplitudes=[1.0],
        #         frequencies=freq,
        #         mixer_deg=[-90]
        #     )
        #     mcas.asc(length_mus=1.0)

        #     sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
        #             nuc='ple_Ex', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=3.0)

        #     mcas.asc(length_mus=1.0)
        #     mcas.asc(length_mus=1.0)

        self.queue._gated_counter.set_n_values(mcas) #how to get here the queue?

        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '>', 1, 1, 0, 1],
        # ['init', '>', 1, 1, 0, 1],
        # ['init', '>', 5, 1, 0, 1],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )

    nuclear.x_axis_title = 'tau_half [mus]'
    #nuclear.analyze_type = 'consecutive'
    #nuclear.analyze_type = 'standard'

    nuclear.do_ple_refocusEx = False
    nuclear.do_ple_refocusA1 = False
    nuclear.do_ple_refocus = False
    nuclear.do_odmr_refocus = False
    nuclear.do_confocal_red_refocus = False

    nuclear.ple_refocus_interval = 100
    nuclear.confocal_red_refocus_interval = 100  # 240

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('rabi_period', [0.07]),
            ('resonant', [True]),
            ('ms', [-1]),
            ('state_check', [False]),
            ('nucl_init', [False]),
            ('additional_estate_check', [False]),
            #('ddt', ['fid', 'hahn', 'xy4', 'xy16', 'kdd','kdd4', 'kdd16']),
            #('ddt', ['xy4']),
            ('n_rep_dd', range(1,10)),
            ('delay_ps',[0]), #11110
            ('tau', [1.0,2.0,3.0]),#E.round_length_mus_full_sample(np.linspace(0.0, 10.0, 100))),
            ('phase_pi2_2', [0]),

        )
    )
    nuclear.number_of_simultaneous_measurements =  len(nuclear.parameters['phase_pi2_2'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 1e6
    nuclear.debug_mode = False
    settings()
    print('run_fun started')
    nuclear.run(abort)