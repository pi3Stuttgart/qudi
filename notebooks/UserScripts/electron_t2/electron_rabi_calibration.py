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
#freqs_all 8 mhz = {'R2':177.7,'R1':169.7, 'C1':107,'C2':116,'L1':30.5,'L2':38.5,'RFp12':3.4,'RFm12':6.47}
#freqs_all 2 mhz = {'R2':177.7,'R1':169.7, 'C1':107,'C2':116,'L1':30.5,'L2':38.5,'RFp12':3.4,'RFm12':6.47}
ael = 1.0


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
            RF_init12m = 0.3
            mw_init32R1 = 0.3
        elif '-' in state:
            RF_init12m = 0.0
            mw_init32R2 = 0.3
        mw_init32m = 0.3
    elif 'm' in state:
        mw_init32R2 = 0.3
        mw_init32R1 = 0.3

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
        'frequencies':[2543.8, 2535, 2395.5, 2403.2, 3.4, 1.026]
    }
    
    return pd2g1


def ret_ret_mcas(pdc):
    def ret_mcas(self, current_iterator_df, sequence_name = None):
        sequence_name = 'Electron_rabi_test' if sequence_name is None else sequence_name
        #print(self, current_iterator_df)
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        freq = [30]
        
        for idx, _I_ in current_iterator_df.iterrows():
            mcas.asc(length_mus=5.0, repump=True, name='Repump')
            mcas.asc(length_mus=10.0)  #Decay from metastables.
            ## Preliminary....
            
            
            ## Decide on init state for rabi calibration.
            state = {
                'L12':'m',
                'L34':'m',
                'L':'m',
                'C1':'m',
                'C2':'m',
                'R12':'p',
                'R34':'p',
                'R':'p'
                }[_I_['trans']]
            state +={
                'L12':'12',
                'L34':'12',
                'L':'12',
                'C1':'12',
                'C2':'12',
                'R12':'12',
                'R34':'12',
                'R':'12'
                }[_I_['trans']]
            
            print('Initialising to',state)

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

            mcas.asc(length_mus=1.0, name='sequence wait 1')
            freqs = {
                'L12': [2395.5],
                'L34': [2403.2],
                'L': [2395.5, 2403.2],
                'R12': [2535],
                'R34': [2543.8],
                'R': [2535, 2543.8],
                }[_I_['trans']]
            if _I_['trans'] == 'L12' or _I_['trans'] == 'R12':
                amp = [_I_['amp']]
                mix_deg = [-90]
            else:
                amp = [_I_['amp']/2, _I_['amp']/2]
                mix_deg = [-90, -90]
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=_I_['mw_duration'],
                amplitudes=amp,
                frequencies=freqs, #Later also debug the transition frequency. 
                mixer_deg=mix_deg
            )

            if _I_['trans'].startswith('C'): #Used later for calibration of the C
                mcas.asc(length_mus=0.01)
                sna.electron_rabi(
                    mcas,
                    new_segment=False,
                    length_mus= 1.0,
                    amplitudes=[0.2, 0.2],
                    frequencies=[107.8,115.8],
                    mixer_deg=[-90,-90]
                )
            
            
            mcas.asc(length_mus=0.1)
            if _I_['readout'] == 'A2':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=_I_['t_read'])
            elif _I_['readout'] == 'A1':
               sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                   nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=_I_['t_read'])

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
    #nuclear.analyze_type = 'standard'
    nuclear.analyze_type = 'average'
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

    nuclear.ple_refocus_interval = 900
    nuclear.confocal_refocus_interval = 900  # seconds
    nuclear.odmr_refocus_interval= 600

    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict(
        (
           ('sweeps', range(5)),
            ('init_time', [30.0]),
            ('t_read', [1.0]),
            ('A2_power', [5]),
            ('amp', np.linspace(0.1,0.7,7)), #at 0.2 pi pulse is 0.1, at 0.4, 0.05 ns, 0.05*50 = 2.5
            ('mw_duration', E.round_length_mus_full_sample(np.linspace(0,2.0,131))),
            ('trans',['L12', 'R12', 'L', 'R']),
            ('readout', ['A2','A1']),
        )
    )
    nuclear.number_of_simultaneous_measurements =  len(nuclear.parameters['readout'])*len(nuclear.parameters['trans'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 5*1e6
    nuclear.hashed = False
    nuclear.debug_mode = False
    settings()
    print('run_fun started')
    nuclear.run(abort)