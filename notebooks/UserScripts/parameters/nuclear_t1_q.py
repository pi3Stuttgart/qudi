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
        
        #freq = [30.42]#np.array([self.queue.tt.mw_mixing_frequency])
        amp = self.queue.tt.rp('e_rabi_ou350deg-90-L', omega=2.0).amp #2 MHz
        pi_dur = self.queue.tt.rp('e_rabi_ou350deg-90-L', amp=amp).pi
        #amp = amp #FIXME still? just quickfix because rabi is not well calibrated
        # Sequence starts
        mcas = MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        
        for idx, _I_ in current_iterator_df.iterrows():
            mcas.start_new_segment('start_sequence')
            mcas.asc(length_mus=3.0, repump=True, name='Repump')
            mcas.asc(length_mus=1.0)  # Starting... 
            mcas.asc(A1=True, length_mus=100., name='A1_init')  # Longer init for nuclear polarization
            mcas.asc(length_mus=1.0)  # Starting... 

            sna.electron_rabi(
                mcas,
                new_segment=False,
                length_mus=pi_dur,
                amplitudes=[amp],
                frequencies=[_I_['freqs']],
                mixer_deg=[-90]
            )
            mcas.asc(length_mus=0.5)
            freq = [30]
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

    nuclear.x_axis_title = 'Index'
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

    nuclear.ple_refocus_interval = 600
    nuclear.confocal_refocus_interval = 600  # seconds
    nuclear.odmr_refocus_interval= 600

    #rabi refocus ?

    nuclear.queue._gated_counter.trace.consecutive_valid_result_numbers = [0]
    nuclear.queue._gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict( # WHAT DOES ALL THIS MEAN ??? WHICH UNITS ??
        (
            #('mw_duration', E.round_length_mus_full_sample(np.linspace(0.0, 0.3, 31))), 
            #('rabi_period', [0.087]),
            # ('resonant', [True]),
            # ('ms', [-1]),
            # ('state_check', [False]),
            # ('nucl_init', [False]),
            # ('additional_estate_check', [False]),
            #('ddt', ['fid', 'hahn', 'xy4', 'xy16', 'kdd','kdd4', 'kdd16']),
            #('ddt', ['xy4']),
            #('n_rep_dd', range(1,4)),
            # ('delay_ps',[0.45]), #11110 # actually which delay ?
            #('amp', np.array([0.25])),
            # ('phase_pi2_2', [0]),
            ('sweeps', range(60)),
            ('readout', ['A2']),
            ('index', range(20)), 
            ('freqs', np.linspace(25,40,50)),
            
        )
    )
    nuclear.number_of_simultaneous_measurements =  1*len(nuclear.parameters['freqs'])

def run_fun(abort, **kwargs):
    print(1,' Nuclear started!!!')
    nuclear.queue = kwargs['queue']
    nuclear.queue._gated_counter.readout_duration = 4*1e6 # --> nvalues.
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
