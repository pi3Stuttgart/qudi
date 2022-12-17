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
    def ret_mcas(self, current_iterator_df,sequence_name = None):
        if sequence_name is None:
            sequence_name = 'Electron_test'
        
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1,2], 'ps': [1]})

        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=0.1)  # Starting... histogram 0
        mcas.asc(length_mus=5.0, repump=True, name='Repump')
        mcas.asc(length_mus=30.0)
        mcas.asc(A2=True, length_mus=10., name='A2_init')  # Longer first init.
        mcas.asc(length_mus=1.0)

        freq = [177.7]#np.array([self.queue.tt.mw_mixing_frequency])
        amp = 1.0
        pi_2_dur = self.queue.tt.rp('e_rabi_ou350deg-90-R', amp=amp).pi2
        pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-R', amp=amp).pi

        for idx, _I_ in current_iterator_df.iterrows():
            mcas.asc(A2=True, length_mus=10.,
                     name='A2_init')  # Init NV with A1 laser (about 1-3 µs). This step can be skipped for the very first tests #as the green laser will also intialise somehow.
            mcas.asc(length_mus=10.0)

            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=pi_2_dur,
                amplitudes=[amp],
                frequencies=freq,
                phases = [0],
                mixer_deg=[-90]
            )

            for i in range(_I_['n_pulses']):
                mcas.asc(length_mus=_I_['tau_2'])

                sna.electron_rabi(
                    mcas,
                    new_segment=False,
                    length_mus=pi_dur,
                    amplitudes=[amp],
                    frequencies=freq,
                    phases = [90],
                    mixer_deg=[-90]
                )
                
                mcas.asc(length_mus=_I_['tau_2']*2)

                sna.electron_rabi(
                    mcas,
                    new_segment=False,
                    length_mus=pi_dur,
                    amplitudes=[amp],
                    frequencies=freq,
                    phases = [0],
                    mixer_deg=[-90]
                )
                mcas.asc(length_mus=_I_['tau_2'])

            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=pi_2_dur,
                amplitudes=[amp],
                frequencies=freq,
                phases = [_I_['phase_pi2_2']],
                mixer_deg=[-90]
            )

            
            mcas.asc(length_mus=1.0)

            #freq = [30.0]
            
            if _I_['readout'] == 'A2':
                sna.ssr(mcas = mcas, no_new_segment=True, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=3.)
            mcas.asc(length_mus=0.5, name='sequence wait 2')
            #mcas.asc(length_mus=_I_['n_pulses']*(20-_I_['tau_2'])*4, name='sequence wait 2')

        self.queue._gated_counter.set_n_values(mcas,
        self.number_of_simultaneous_measurements) #how to get here the queue? readout duration/sequence length) #how to get here the queue?

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

    nuclear.x_axis_title = 'Index'
    #nuclear.analyze_type = 'consecutive'
    # nuclear.analyze_type = 'standard'
    nuclear.analyze_type = 'average' #experimental feature for the fast 
    #nuclear.analyze_type = None
    nuclear.save_smartly = True

    #PLE refocus
    nuclear.do_ple_refocusA1 = False #not used 
    nuclear.do_ple_refocusA2 = False

    # ODMR refocus
    nuclear.refocus_cw_odmr = False
    nuclear.refocus_pulsed_odmr = False

    #confocal refocus
    nuclear.do_confocal_repump_refocus = False
    nuclear.do_confocal_A1A2_refocus = False
    nuclear.do_confocal_A2MW_refocus = False

    # Resonant Laser power
    nuclear.checkA1LaserPower = False # Not yet implemented in powerstablogic
    nuclear.checkA2LaserPower = False
    nuclear.A1LaserPower = 1 #nW
    nuclear.A2LaserPower = 3 #nW

    nuclear.ple_refocus_interval = 300
    nuclear.confocal_refocus_interval = 300  # seconds
    nuclear.odmr_refocus_interval= 600

    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict(
        (
            ('n_pulses', [11]),
            ('sweeps', range(50)),
            ('readout',['A2']),
            ('tau_2', E.round_length_mus_full_sample(np.linspace(0.0,0.05, 600))),
            ('phase_pi2_2', [0,180])
        )
    )
    nuclear.number_of_simultaneous_measurements =2*len(nuclear.parameters['tau_2'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 5e6 #For long measurement
    nuclear.debug_mode = False
    nuclear.hashed = True
    settings()
    print('run_fun started')
    nuclear.run(abort)