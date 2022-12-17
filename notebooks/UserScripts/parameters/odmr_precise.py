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
        
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        
        for idx, _I_ in current_iterator_df.iterrows():
            mcas.asc(length_mus=5.0, repump=True, name='Repump')
            mcas.asc(length_mus=20.0)  # Starting... histogram 0
        
            #pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=_I_['omega']).pi
            #amp = self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=_I_['omega']).amp
            mcas.asc(A1=_I_['init']=='A1',A2 =_I_['init']=='A2', length_mus=_I_['init_time'], name='resonant_init')  # Init system with A2 laser
            mcas.asc(length_mus=0.5, name='sequence wait 1')
            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus= 0.48,
                amplitudes=[0.18],
                frequencies=[_I_['mw_freq']],
                mixer_deg=[-90]
            )
            mcas.asc(length_mus=0.5, name='sequence wait 1')
            freq = [30.0]
            if _I_['init'] == 'A2':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A2', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=30.0)
            elif _I_['init'] == 'A1':
                sna.ssr(mcas = mcas, queue=self.queue, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_A1', mixer_deg=-90, eom_ampl=0.0, step_idx=0, laser_dur=30.0)
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

    nuclear.parameters = OrderedDict( # WHAT DOES ALL THIS MEAN ??? WHICH UNITS ??
        (
            ('omega', [0.5]),  
            ('readout', ['A1']),
            ('init_time', [50]),
            ('sweeps', range(10)),
            ('mw_freq', np.linspace(12,17,100)), 
            ('init', ['A1']),
        )
    )
    nuclear.number_of_simultaneous_measurements =  1*len(nuclear.parameters['mw_freq'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 75*1e6 # --> nvalues.
    nuclear.hashed = True
    nuclear.debug_mode = False
    settings()
    print('run_fun started')
    nuclear.run(abort)
    #nuclear.thread.join() #experimental...
    # # ------------------------------------------------------
    #df = nuclear.data.df
    # pld = nuclear.pld.data_fit_results.df
    #df = df[['sweeps', 'average_counts', 'amp', 'mw_duration']]
    
    # temp_df = pd.DataFrame(columns=['amp0', 'omega', 'average_counts', 'mw_duration'])
    #temp_df = pd.DataFrame(columns=['amp', 'omega', 'transition','date'])
    # for amp in df['amp0'].unique():
    #     print('Ampl ', amp)
    #     sub_df = df[(df['amp0'] == amp)]
    
    
    
    #     # sub_pld = pld[(pld['amp0'] == amp)]
    #     x = sub_df['mw_duration'].unique()
    #     y = sub_df.groupby(by=['mw_duration']).agg({'average_counts': np.mean}).values.ravel()
    
    #     m = lmfit_models.CosineModel()
    #     p = m.guess(data=y, x=x)
    #     r = m.fit(data=y, params=p, x=x)
    
    
    #     temp_df = pd.concat([temp_df, pd.DataFrame({
    #         'amp0': [amp],
    #         # 'omega': 1.0 / sub_pld['T'].mean(),
    #         'transition': [0],
    
    #         'omega': [1.0 / r.params['T'].value],
    #         # 'average_counts': [y],
    #         # 'mw_duration': [x],
    
    #         'date': [str(datetime.datetime.now())]
    #     })])
    
    # f = 'e_rabi_ou350deg-90'
    # temp_df = temp_df[['amp0', 'transition', 'omega', 'date']]
    
    # print(temp_df)
    # pi3d.tt.rabi_parameters[f].update_file(temp_df)
    # ------------------------------------------------------

    # x = nuclear.data.df['mw_duration'].unique()
    # y = nuclear.data.df.groupby(by = ['mw_duration']).agg({'average_counts': np.mean}).values
    
    # T = nuclear.pld.fit_result_table.data['T'] #RabiPeriod
    # pi3d.tt.rabi_parameters[f].update_file(sub)  ## where sub is dataframe
    # nuclear.pld.data_fit_results.df
    # data_dict={
    #     'mw_durations' : x,
    #     'average_counts':y,
    #     'omega' : 1.0/T,
    #     # amp0    transition    omega    date
    
    # }
    # print('-----------')
    # print('x: ')
    # print(x)
    # print('y: ')
    # print(y)
    # print('-----------')

        # df = nuclear.data.df
    # pld = nuclear.pld.data_fit_results.df
    #df = df[['sweeps', 'average_counts', 'amp', 'mw_duration']]

    # temp_df = pd.DataFrame(columns=['amp0', 'omega', 'average_counts', 'mw_duration'])
    #temp_df = pd.DataFrame(columns=['amp', 'omega', 'transition','date'])
    #for amp in df['amp'].unique():
    #    print('Ampl ', amp)
    #    sub_df = df[(df['amp'] == amp)]
    #    # sub_pld = pld[(pld['amp0'] == amp)]
    #    x = sub_df['mw_duration'].unique()
     #   y = sub_df.groupby(by=['mw_duration']).agg({'average_counts': np.mean}).values.ravel()
    #    m = lmfit_models.CosineModel()
    #    p = m.guess(data=y, x=x)
     #   r = m.fit(data=y, params=p, x=x)
    #    temp_df = pd.concat([temp_df, pd.DataFrame({
    #        'amp0': [amp],
            # 'omega': 1.0 / sub_pld['T'].mean(),
     #       'transition': [0],
     #       'omega': [1.0 / r.params['T'].value],
            # 'average_counts': [y],
            # 'mw_duration': [x],
    #        'date': [str(datetime.datetime.now())]
    #    })])

    #f = 'e_rabi_ou350deg-90'
    #temp_df = temp_df[['amp0', 'transition', 'omega', 'date']]

    #print(temp_df)
    #nuclear.queue.tt.rabi_parameters[f].update_file(temp_df)
    #------------------------------------------------------

    #x = df['mw_duration'].unique()
    #y = df.groupby(by = ['mw_duration']).agg({'average_counts': np.mean}).values
