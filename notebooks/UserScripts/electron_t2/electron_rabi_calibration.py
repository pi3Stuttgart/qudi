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
freqs_all = {'R2':177.7,'R1':169.7, 'C1':107,'C2':116,'L1':30.5,'L2':38.5,'RFp12':3.4,'RFm12':6.47}
ael = 1.0

def ret_ret_mcas(pdc):
    def ret_mcas(self, current_iterator_df, sequence_name = None):
        sequence_name = 'Electron_rabi_test' if sequence_name is None else sequence_name
        #print(self, current_iterator_df)
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=5.0, repump=True, name='Repump')
        mcas.asc(length_mus=10.0)  #Decay from metastables.
        freq = [30]
        
        for idx, _I_ in current_iterator_df.iterrows():
            
            ## Preliminary....
            
            def init_state_drive(state):
                '''
                State could be "p(m)3(1)2+(-,n)", example m32+, or p32-, p32n 
                '''
                mw_init32R2 = 0
                mw_init32R1 = 0
                mw_init32m = 0
                RF_init12p = 0
                RF_init12m = 0
                ## MW drive
                if 'p' in state:
                    if '+' in state:
                        RF_init12m = 0.1
                        mw_init32R2 = 0.08
                        mw_init32m = 0.4
                    elif '-' in state:
                        RF_init12m = 0.0
                        mw_init32R1 = 0.08
                        mw_init32m = 0.0
                elif 'm' in state:
                    mw_init32R2 = 0.04
                    mw_init32R1 = 0.04

                pd2g1 = {
                    'type':'sine',
                    'phases':[0],
                    'amplitudes':[
                                mw_init32R2,
                                mw_init32R1,
                                mw_init32m,
                                mw_init32m, 
                                RF_init12p,
                                RF_init12m],                    
                    #'frequencies':[30.5,38.5],
                    'frequencies':[177.78,168.4,30.5,38.5,3.4,6.47]
                }
                
                return pd2g1
            ## Decide on init state for rabi calibration.

            state = {'L1':'m','L2':'m', 'C1':'m','C2':'m','R1':'p','R2':'p'}[_I_['trans']]
            state +={'L1':'32-','L2':'m12+', 'C1':'12+','C2':'12-','R1':'32+','R2':'12-'}[_I_['trans']]
            # print('Initialising to',state)

            ###
            ## Sequence after repump
            ###

            mcas.asc(
                A1= '32' in state,
                A2 = '12' in state, 
                length_mus=_I_['init_time'], 
                name='resonant_init',
                pd2g1 = init_state_drive(state)
            ) 

            mcas.asc(length_mus=2.0, name='sequence wait 1')
            freqs = {'L1':30.5,'L2':38.52,'C1':108.,'C2':116,'R1':168.4,'R2':177.78}[_I_['trans']]
            pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-C1', amp=_I_['amp']).pi
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=pi_dur,
                amplitudes=[_I_['amp']],
                frequencies=[_I_['mw_freq']], #Later also debug the transition frequency.
                mixer_deg=[-90]
            )

            mcas.asc(length_mus=0.5)
            pi_dur = 0.5
            ampR1 = self.queue.tt.rp('e_rabi_ou350deg-90-R1', omega=1.0).amp
            ampR2 = self.queue.tt.rp('e_rabi_ou350deg-90-R2', omega=1.0).amp

            if _I_['trans'].startswith('C'): #Used later for calibration of the C
                sna.electron_rabi(
                    mcas,
                    new_segment=False,
                    length_mus= pi_dur,
                    amplitudes=[ampR1,ampR2],
                    frequencies=[168.4, 177.78],
                    mixer_deg=[-90,-90] ##Here is not perfect., sin it needs various calibrations. 
                )
            # sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
            #         nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=3.0)
            if _I_['readout'] == 'A2':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=1.5)
            elif _I_['readout'] == 'A1':
               sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                   nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=1.5)
            mcas.asc(length_mus=0.5, name='sequence wait 2')

        self.queue._gated_counter.set_n_values(mcas, self.number_of_simultaneous_measurements) #how to get here the queue? readout duration/sequence length.

        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '>', 1, 1, 0, 1],
        # ['init', '>', 1, 1, 0, 1],
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

    nuclear.x_axis_title = 'tau [mus]'
    #nuclear.analyze_type = 'consecutive'
    nuclear.analyze_type = 'average'

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

    nuclear.ple_refocus_interval = 600
    nuclear.confocal_refocus_interval = 600  # seconds
    nuclear.odmr_refocus_interval= 600

    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict( # WHAT DOES ALL THIS MEAN ??? WHICH UNITS ??
        (
            ('sweeps', range(15)),
            ('init_time', [150.0]),
            ('mw_init12',[0.0]),
            ('mw_init32',[0.0]),
            ('mw_init32R1',[0.0]),
            ('mw_init32R2',[0.04]),
            ('RF_init12p',[0.0]),
            ('RF_init12m',[0.0]),
            ('mw_init32m',[0.04]),
            ('init', ['A2']),
            ('t_read',[1.0]),
            ('A2_power',[5]),
            ('173pi', [False]),
            ('amp', np.array([0.01])),  #at 0.2 pi pulse is 0.1, at 0.4, 0.05 ns, 0.05*50 = 2.5
            ('trans',['C1']),  # at 0.05 pi pulse is 0.4, so 1.25 oscillation with 1.0 us
            ('mw_duration', [0]),  #E.round_length_mus_full_sample(np.linspace(0,0.8,40))),
            ('mw_freq', np.linspace(104,112,151)),  # E.round_length_mus_full_sample(np.linspace(0,0.8,40))),
            ('readout', ['A2','A1']),
        )
    )
    nuclear.number_of_simultaneous_measurements =  2#*len(nuclear.parameters['mw_freq'])#len(nuclear.parameters['phase_pi2_2'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 20*1e6
    nuclear.hashed = False
    nuclear.debug_mode = False
    settings()
    print('run_fun started')
    nuclear.run(abort)