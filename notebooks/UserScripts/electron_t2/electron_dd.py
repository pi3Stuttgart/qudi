# coding=utf-8
#from pi3diamond import pi3d
import datetime
import numpy as np
import os
import importlib
import notebooks.UserScripts.helpers.sequence_creation_helpers as sch; importlib.reload(sch)
import notebooks.UserScripts.helpers.shared as shared
#import hardware.multi_channel_awg_seq as MCAS
#import notebooks.UserScripts.helpers.snippets_awg as sna

#importlib.reload(sna)
importlib.reload(shared)
#importlib.reload(MCAS)
import notebooks.UserScripts.helpers.shared as ush;importlib.reload(ush)
from logic.qudip_enhanced import *
#import hardware.pym8190a.elements as e
from collections import OrderedDict


seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

__TAU_HALF__ = 2*192/12e3
__SAMPLE_FREQUENCY__ = e.__SAMPLE_FREQUENCY__

ael = 1.0

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):
        sequence_name = 'Electron_t2_red_Tst'

        #mcas = MCAS.MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        #mcas.start_new_segment('start_sequence')
        #mcas.asc(length_mus=0.1)  # Starting... histogram 0




        #def erabi(freq, length, amp, phase=0.0):
        #    sna.electron_rabi(mcas,
        #                      name='electron rabi',
        #                      length_mus=length,
         #                     amplitudes=[amp],
        #                      frequencies=freq,
        #                      phases=np.rad2deg(phase),
        #                      new_segment=False,
        #                      mixer_deg=-90,
        #                      )

        #def waveform(seq):
         #   mcas.start_new_segment('waveform')
         #   sna.polarize(mcas, new_segment=False)
         #   mw = seq.times_fields_aphi('mw')
        #    wait = seq.times_fields_aphi('wait')
         #   for step in seq.sequence_steps:
         #       idx = int(step[1]) - 1
         #       if step[0] == 'mw':
         #           erabi(freq=freq, length=mw[idx, 0],
         #                 amp=pi3d.tt.rp('e_rabi', period=1 / mw[idx, 1], mixer_deg=-90).amp, phase=mw[idx, 2])
         #       elif step[0] == 'wait':
          #          mcas.asc(length_mus=wait[idx, 0])

        def dd():
            pi2x = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1.0 / rabi_period, phase=0.0, control_field='mw')
            pi2_2 = sc.Rabi(t_rabi=0.25 * rabi_period, omega=1.0 / rabi_period, phase=_I_['phase_pi2_2'],
                            control_field='mw')
            dd = sc.DD(dd_type='{}_{}'.format(_I_['ddt'],_I_['n_rep_dd']), rabi_period=_I_['rabi_period'],
                       tau = _I_['tau'])#total_tau=_I_['total_tau'])
            print(_I_["ddt"])
            seq = sc.Concatenated([pi2x, dd, pi2_2], controls=['mw', 'wait'])
            print([steps[0] for steps in seq.sequence_steps])
            #waveform(seq)



        for idx, _I_ in current_iterator_df.iterrows():
            freq = pi3d.tt.mfl({'14N': [0]}, ms_trans=_I_['ms'])
            rabi_period = _I_['rabi_period']
            mcas.asc(length_mus=1.0, name = 'initial_delay')
            mcas.asc(length_mus=0.2, green = True, name='Green')
            mcas.asc(length_mus=1.0)
            #mcas.asc(aom_A1=True, length_mus=100, name = 'A1_init')  # Init NV with A1 laser (about 1-3 µs). This step can be skipped for the very first tests #as the green laser will also intialise somehow.
            mcas.asc(length_mus=2.0)

            dd()
            mcas.asc(length_mus=1.0)

            sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False,
                    nuc='ple_Ex', mixer_deg=-90, eom_ampl =0.3,step_idx=0, laser_dur= 1.0)
            mcas.asc(length_mus=1.0)

            if _I_['state_check']:
                # Charge state check as EX + A1 readout
                sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False, nuc='charge_state', mixer_deg=-90,
                        step_idx=1, laser_dur=100.0)


            mcas.asc(length_mus=1.0)
            mcas.asc(length_mus=10.0)


        pi3d.gated_counter.set_n_values(mcas)

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
    nuclear.analyze_type = 'standard'

    nuclear.do_ple_refocusEx = True
    nuclear.do_ple_refocusA1 = False
    nuclear.do_ple_refocus = True
    nuclear.do_odmr_refocus = False
    nuclear.do_confocal_red_refocus = True

    nuclear.ple_refocus_interval = 100
    nuclear.confocal_red_refocus_interval = 100  # 240

    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0]
    pi3d.gated_counter.trace.average_results = False

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
            ('ddt', ['xy4']),
            ('n_rep_dd', range(1)),
            ('delay_ps',[0]), #11110
            ('tau', [1.0]),#E.round_length_mus_full_sample(np.linspace(0.0, 10.0, 100))),
            ('phase_pi2_2', [np.pi*0.5]),

        )
    )
    nuclear.number_of_simultaneous_measurements =  1# len(nuclear.parameters['phase_pi2_2'])

def run_fun(abort, **kwargs):
    pi3d.readout_duration = 1e6*100
    # pi3d.gated_counter.readout_duration = 5e6
    pi3d.gated_counter.readout_duration = 1e6*10

    nuclear.debug_mode = True
    settings()
    print('run_fun started')

    nuclear.run(abort)


    # # ------------------------------------------------------
    # df = nuclear.data.df
    # # pld = nuclear.pld.data_fit_results.df
    # df = df[['sweeps', 'average_counts', 'amp0', 'mw_duration']]
    #
    # # temp_df = pd.DataFrame(columns=['amp0', 'omega', 'average_counts', 'mw_duration'])
    # temp_df = pd.DataFrame(columns=['amp0', 'omega', 'transition','date'])
    # for amp in df['amp0'].unique():
    #     print('Ampl ', amp)
    #     sub_df = df[(df['amp0'] == amp)]
    #
    #
    #
    #     # sub_pld = pld[(pld['amp0'] == amp)]
    #     x = sub_df['mw_duration'].unique()
    #     y = sub_df.groupby(by=['mw_duration']).agg({'average_counts': np.mean}).values.ravel()
    #
    #     m = lmfit_models.CosineModel()
    #     p = m.guess(data=y, x=x)
    #     r = m.fit(data=y, params=p, x=x)
    #
    #
    #     temp_df = pd.concat([temp_df, pd.DataFrame({
    #         'amp0': [amp],
    #         # 'omega': 1.0 / sub_pld['T'].mean(),
    #         'transition': [0],
    #
    #         'omega': [1.0 / r.params['T'].value],
    #         # 'average_counts': [y],
    #         # 'mw_duration': [x],
    #
    #         'date': [str(datetime.datetime.now())]
    #     })])
    #
    # f = 'e_rabi_ou350deg-90'
    # temp_df = temp_df[['amp0', 'transition', 'omega', 'date']]
    #
    # print(temp_df)
    # pi3d.tt.rabi_parameters[f].update_file(temp_df)
    # ------------------------------------------------------




    # x = nuclear.data.df['mw_duration'].unique()
    # y = nuclear.data.df.groupby(by = ['mw_duration']).agg({'average_counts': np.mean}).values
    #
    # T = nuclear.pld.fit_result_table.data['T'] #RabiPeriod
    # pi3d.tt.rabi_parameters[f].update_file(sub)  ## where sub is dataframe
    # nuclear.pld.data_fit_results.df
    # data_dict={
    #     'mw_durations' : x,
    #     'average_counts':y,
    #     'omega' : 1.0/T,
    #     # amp0    transition    omega    date
    #
    # }
    # print('-----------')
    # print('x: ')
    # print(x)
    # print('y: ')
    # print(y)
    # print('-----------')