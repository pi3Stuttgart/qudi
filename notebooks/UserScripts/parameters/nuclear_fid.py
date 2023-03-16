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
    def ret_mcas(self, current_iterator_df, sequence_name = None):
        sequence_name = 'Electron_rabi_test' if sequence_name is None else sequence_name
        #print(self, current_iterator_df)
        
        #mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        #mcas.start_new_segment('start_sequence')
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=5.0, repump=True, name='Repump')
        mcas.asc(length_mus=20.0)  # Starting... histogram 0
        for idx, _I_ in current_iterator_df.iterrows():
            
            
        
            amp_R1 = self.queue.tt.rp('e_rabi_ou350deg-90-R1', omega=_I_['omega']).amp
            amp_R2 = self.queue.tt.rp('e_rabi_ou350deg-90-R2', omega=_I_['omega']).amp
            mcas.asc(
                A1 = _I_['init']=='A1',
                A2 = _I_['init']=='A2', 
                length_mus=_I_['init_time'], 
                name='resonant_init',
                pd2g1 = {
                    'type':'sine',
                    'phases':[0],
                    'amplitudes':[_I_['mw_init']],#0.02
                    'frequencies':[177.8,168.4]
                })  # Init system with A2 laser - into -1/2.
            
            mcas.asc(length_mus=10.0, name='sequence wait 1')
            
            ## swap to plus - a pi pulse for Center transitions
            
            amp_c = self.queue.tt.rp('e_rabi_ou350deg-90-C2', period = 1.0).amp
            
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus= 0.5,
                amplitudes=[amp_c],
                frequencies=[107.8], #mfl --> gives the frequency , (12-12m, 29Si8+)
                mixer_deg=[-90]) # Rabi 1/2-1/2 pi pulse. 


            mcas.asc(length_mus=0.1)

            # nuc pi/2
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=_I_['mw_duration']/4,
                amplitudes=[_I_['RF_amp']],
                frequencies=[_I_['RF_freq']],
                mixer_deg=[-90]
            )
            mcas.asc(length_mus=_I_['tau_FID'])
            
            # nuc pi/2
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=_I_['mw_duration']/4,
                amplitudes=[_I_['RF_amp']],
                frequencies=[_I_['RF_freq']],
                mixer_deg=[-90]
            )
            
            if _I_['cnot_freq'] ==168.4:
                sna.electron_rabi(
                    mcas,
                    new_segment=False,
                    length_mus= 0.25,
                    #length_mus= _I_['mw_dur_R1'],
                    amplitudes=[amp_R1],
                    frequencies=[_I_['cnot_freq']],
                    mixer_deg=[-90]
                ) # ODMR 
            else:
                sna.electron_rabi(
                    mcas,
                    new_segment=False,
                    length_mus= 0.5,
                    #length_mus= _I_['mw_dur_R1'],
                    amplitudes=[amp_R2],
                    frequencies=[_I_['cnot_freq']],
                    mixer_deg=[-90]
                ) # ODMR 


            mcas.asc(length_mus=0.5, name='sequence wait 1')
            freq = [30.0]
            if _I_['init'] == 'A2':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=3.0)
            elif _I_['init'] == 'A1':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=3.0)
            mcas.asc(length_mus=0.5, name='sequence wait 2')

            # if _I_['readout'] == 'A2':
            #     sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
            #         nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=1, laser_dur=100.3)
            # elif _I_['readout'] == 'A1':
            #     sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
            #         nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=1, laser_dur=100.3)

            # if _I_['readout'] == 'A2':
            #     sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
            #         nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=2, laser_dur=100.3)
            # elif _I_['readout'] == 'A1':
            #     sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
            #         nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=2, laser_dur=100.3)

        self.queue._gated_counter.set_n_values(mcas, self.number_of_simultaneous_measurements) #how to get here the queue? readout duration/sequence length.

        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '>', 0, 1, 0, 1],
        #['result', '>', -1, 1, 0, 1],
        #['init', '>', -1, 1, 0, 1],
        # ['init', '>', 5, 1, 0, 1],
    ]
        #what does each entry do?
        # ana_seq[0]: ? 'result' or 'init', init - for postselection
        # ana_seq[1]: ? > or <
        # ana_seq[2]: "threshold"
        # ana_seq[3]: "nlp_per_point", number of laser pulses per point. N of repetitions. 
        # ana_seq[4]: set to 100 --> no counts measured; set to 7 --> counts can be measured; --> delta - exclusion zone. n > threshold +delta, or n< threhold - delta. 
        # ana_seq[5]: "number of results" --> ssr = cnot1 + laser1 + cnot2 + laser2, -> n=2, etc.. laser2-laser1,  histograms are centered around 0, 
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
    nuclear.do_ple_refocusA2 = True

    # ODMR refocus
    nuclear.refocus_cw_odmr = False
    nuclear.refocus_pulsed_odmr = False

    #confocal refocus
    nuclear.do_confocal_repump_refocus = False
    nuclear.do_confocal_A1A2_refocus = True
    nuclear.do_confocal_A2MW_refocus = False

    # Resonant Laser power
    nuclear.checkA1LaserPower = False # Not yet implemented in powerstablogic
    nuclear.checkA2LaserPower = False
    nuclear.A1LaserPower = 1 #nW
    nuclear.A2LaserPower = 3 #nW

    nuclear.ple_refocus_interval = 600
    nuclear.confocal_refocus_interval = 600  # seconds
    nuclear.odmr_refocus_interval= 600

    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict( # WHAT DOES ALL THIS MEAN ??? WHICH UNITS ??
        (
            ('A2_power',[3]),
            ('omega', [1.0]), #for odmr probing 
            ('readout', ['A2']),
            ('init', ['A2']),
            ('mw_init',[0.02]),
            ('sweeps', range(30)),
            ('RF_amp',[0.2]),
            ('RF_freq',[3.263]),
            ('mw_duration',[4.496]), # 2pi
            ('init_time', [100]),
            #('cnot_freq',[177.8]),#np.linspace(90,130,40)), 
            ('tau_FID',E.round_length_mus_full_sample(np.linspace(0.0, 200, 101))),
            ('cnot_freq',[168.4,177.8])
        )
    )

    nuclear.number_of_simultaneous_measurements =  2

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 3*1e6 # --> nvalues.
    nuclear.hashed = False
    nuclear.debug_mode = False
    settings()
    print('run_fun started')
    nuclear.run(abort)