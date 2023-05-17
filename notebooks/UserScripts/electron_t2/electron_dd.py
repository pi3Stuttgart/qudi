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

def init_state_drive(state, freqs): # freqs is list of L12, L23, R12, R34
    '''
    State could be "p(m)3(1)2+(-,n)", example m32+, or p32-, p32n 
    '''
    mw_init32L1 = 0
    mw_init32L2 = 0
    mw_init32C1 = 0
    mw_init32C2 = 0
    mw_init32R1 = 0
    mw_init32R2 = 0
    ## MW drive
    if 'p' in state:
        mw_init32L1 = 0.1
        mw_init32L2 = 0.1
    elif 'm' in state:
        mw_init32R1 = 0.1
        mw_init32R2 = 0.1

    pd2g1 = {
        'type':'sine',
        'phases':[0],
        'amplitudes':[
                    mw_init32L1, 
                    mw_init32L2,
                    mw_init32C1,
                    mw_init32C2,
                    mw_init32R1,
                    mw_init32R2,
                    ],             
        'frequencies':freqs
    }
    print(freqs)
    print(mw_init32L1, mw_init32L2, mw_init32C1,mw_init32C2,mw_init32R1,mw_init32R2,)
    
    return pd2g1

def ret_ret_mcas(pdc):
    def ret_mcas(self, current_iterator_df,sequence_name = None):
        if sequence_name is None:
            sequence_name = 'Electron_test'
        
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1,2], 'ps': [1]})

        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=5.0, repump=True, name='Repump')
        mcas.asc(length_mus=5.0)

        for idx, _I_ in current_iterator_df.iterrows():
            state = {
                'L12':'m',
                'L34':'m',
                'C12':'m',
                'C34':'m',
                'R12':'p',
                'R34':'p',
                }[_I_['trans']]
            state +={
                'L12':'12',
                'L34':'12',
                'C12':'12',
                'C34':'12',
                'R12':'12',
                'R34':'12'
                }[_I_['trans']]
            
            # freqs = [self.queue.tt.mw_mixing_frequency_L-1,
            #          self.queue.tt.mw_mixing_frequency_L+1,
            #          (self.queue.tt.mw_mixing_frequency_L+self.queue.tt.mw_mixing_frequency_R)/2-1,
            #          (self.queue.tt.mw_mixing_frequency_L+self.queue.tt.mw_mixing_frequency_R)/2+1,
            #          self.queue.tt.mw_mixing_frequency_R-1,
            #          self.queue.tt.mw_mixing_frequency_R+1]
            freqs = [2398.85,2400.93,1,1,2538.33,2540.67]
            loops = 100
            mcas.start_new_segment(name='init', loop_count = loops)
            mcas.asc(
                A1= '32' in state,
                A2 = '12' in state,
                length_mus=E.round_length_mus_full_sample(_I_['init_time']/(64*loops))*64, 
                name='resonant_init',
                pd2g1 = init_state_drive(state, freqs)
            )

            mcas.start_new_segment(name='sequence')
            mcas.asc(length_mus=1.0)

            if _I_['trans'] == 'L12':
                pi_2_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=5).pi2
                pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=5).pi
                amp = self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=5).amp
            elif _I_['trans'] == 'R12':
                pi_2_dur = self.queue.tt.rp('e_rabi_ou350deg-90-R', omega=5).pi2
                pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-R', omega=5).pi
                amp = self.queue.tt.rp('e_rabi_ou350deg-90-R', omega=5).amp
            freq = {
                'L12': [(freqs[0]+freqs[1])/2],
                'R12':[(freqs[4]+freqs[5])/2],
                }[_I_['trans']]
            print("pi freq: ", freq)

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

            if _I_['readout'] == 'A2':
                sna.ssr(mcas = mcas, no_new_segment=True, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=0.5)
            mcas.asc(length_mus=0.5, name='sequence wait 2')
           
        self.queue._gated_counter.set_n_values(mcas, self.number_of_simultaneous_measurements) 

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

    nuclear.ple_refocus_interval = 600
    nuclear.confocal_refocus_interval = 600  # seconds
    nuclear.odmr_refocus_interval= 3000

    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(50)),
            ('A2_power', [5]),
            ('init_time', [40]),
            ('readout',['A2']),
            ('tau_2', E.round_length_mus_full_sample(np.linspace(0,3, 600))),
            ('n_pulses', [8]),
            ('trans', ['L12', 'R12']), 
            ('phase_pi2_2', [0,180])
        )
    )
    nuclear.number_of_simultaneous_measurements = 4*25

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 20e6
    nuclear.debug_mode = False
    nuclear.hashed = False
    settings()
    print('run_fun started')
    nuclear.run(abort)