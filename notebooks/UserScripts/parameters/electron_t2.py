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

def ret_ret_mcas(pdc):
    def ret_mcas(self, current_iterator_df, sequence_name = None):
        sequence_name = 'Electron T2' if sequence_name is None else sequence_name
        #print(self, current_iterator_df)
        
        #freq = [30.42]#np.array([self.queue.tt.mw_mixing_frequency])
        #amp = 0.5#self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=2.0).amp #2 MHz
        #pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', amp=amp).pi
        #amp = amp #FIXME still? just quickfix because rabi is not well calibrated
        # Sequence starts
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})

        for idx, _I_ in current_iterator_df.iterrows():
                # init
            def erabi(freq, length, amp, phase=0.0):
                sna.electron_rabi(mcas,
                                  name='electron rabi',
                                  length_mus=length,
                                  amplitudes=[amp],
                                  frequencies=freq,
                                  phases=np.rad2deg(phase),
                                  new_segment=False,
                                  mixer_deg=-90,
                                  )

            def waveform(seq):
                mcas.start_new_segment('waveform')
                sna.polarize(mcas, new_segment=False)
                mw = seq.times_fields_aphi('mw')
                wait = seq.times_fields_aphi('wait')
                for step in seq.sequence_steps:
                    idx = int(step[1]) - 1
                    if step[0] == 'mw':
                        erabi(freq=freq, 
                        length=mw[idx, 0], 
                        amp=self.queue.tt.rp('e_rabi', period=1 / mw[idx, 1], mixer_deg=-90).amp, 
                        phase=mw[idx, 2])
                    elif step[0] == 'wait':
                        mcas.asc(length_mus=wait[idx, 0])


            rabi_period = _I_['rabi_period']
            def dd():
                pi2x = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1 / rabi_period, phase=0.0, control_field='mw')
                pi2_2 = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1 / rabi_period, phase=_I_['phase_pi2_2'], control_field='mw')
                dd = sc.DD(dd_type='{}_{}'.format(_I_['n_rep_dd'], _I_['ddt']), rabi_period=_I_['rabi_period'], total_tau=_I_['total_tau'])
                seq = sc.Concatenated([pi2x, dd, pi2_2], controls=['mw', 'wait'])
                waveform(seq)

            freq = [0.5*(30.5+38.5)]#pi3d.tt.mfl({'14N': [+1]}, ms_trans=_I_['ms'])
            #freqs = [freq]*2#[pi3d.tt.mfl({'14N': [+1]}, ms_trans=_I_['ms']),
                     #pi3d.tt.mfl({'14N': [0]}, ms_trans=_I_['ms'])]
            dd()
            mcas.asc(length_mus=0.5)
            
            if _I_['readout'] == 'A2':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=1.5)
            elif _I_['readout'] == 'A1':
               sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                   nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=1.5)
            mcas.asc(length_mus=0.5, name='sequence wait 2')

        self.queue._gated_counter.set_n_values(mcas, self.number_of_simultaneous_measurements) #how to get here the queue? readout duration/sequence length.

            
            #sna.nuclear_rabi(mcas,
            #                 name=trf,
            ##                 frequencies=[pi3d.tt.t(trf).current_frequency],
            #                 amplitudes=[arf],
            #                 length_mus=pi3d.tt.rp(trf, amp=arf).pi)
            #sna.ssr(mcas, frequencies=freq, nuc='14N+1', robust=True, mixer_deg=-90, step_idx=0)
            #sna.ssr(mcas, frequencies=freqs, nuc='14N+1', robust=True, mixer_deg=-90, step_idx=0)
            #pi3d.gated_counter.set_n_values(mcas)
        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '>', 1, 1, 0, 1]
        #['result', '<', 'auto', 123123, 1, 1],
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
    #nuclear.x_axis_title = 'Index'
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
    nuclear.do_confocal_A1A2_refocus = False
    nuclear.do_confocal_A2MW_refocus = True

    # Set Laser Power; Is always done after PLE refocus
    nuclear.checkA2LaserPower = False 
    nuclear.A2LaserPower = 3 #nW

    nuclear.checkA1LaserPower = False #To be implemented
    nuclear.A1LaserPower = 3 #nW ; To be implemented
    nuclear.checkRepumpPower = False #To be implemented

    # Refocus Timings
    nuclear.ple_refocus_interval = 600
    nuclear.confocal_refocus_interval = 600  # seconds
    nuclear.odmr_refocus_interval= 600


    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    #pi3d.gated_counter.trace.analyze_type = 'consecutive'
    #pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0]
    #pi3d.gated_counter.trace.average_results = True

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(100)),
            ('rabi_period', [0.1]),
            ('ms', [-1]),
            ('ddt', ['fid','hahn', 'xy4', 'xy16', 'kdd4', 'kdd16']),
            ('n_rep_dd', [1]),
            ('readout',['A2']),
            ('total_tau', np.hstack([[0.0], np.linspace(0.03, 100, 100)])),
            ('phase_pi2_2', [0.0, np.pi]),
        )
    )
    nuclear.number_of_simultaneous_measurements = len(nuclear.parameters['phase_pi2_2'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 5*1e6 # --> nvalues.
    nuclear.hashed = False
    nuclear.debug_mode = False
    settings()
    print('run_fun started')
    nuclear.run(abort)
    #nuclear.thread.join()
