# coding=utf-8
# coding=utf-8
#from pi3diamond import pi3d
import datetime
import numpy as np
import os
import importlib
import notebooks.UserScripts.helpers.sequence_creation_helpers as sch; importlib.reload(sch)
import notebooks.UserScripts.helpers.shared as shared
from hardware.Keysight_AWG_M8190.pym8190a import MultiChSeq
import notebooks.UserScripts.helpers.snippets_awg as sna
importlib.reload(sna)
importlib.reload(shared)
#importlib.reload(MultiChSeq)
import notebooks.UserScripts.helpers.shared as ush;importlib.reload(ush)
from logic.qudip_enhanced import *
#import hardware.Keysight_AWG_M8190.elements as e
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
        sequence_name = 'Electron_t2_red'
        # s = current_iterator_df.transition.iloc[0]
        # freq = pi3d.tt.mfl({'14N': [-1]}, ms_trans=[-1])
        freq = np.array([pi3d.tt.mw_mixing_frequency])
        pi_2_dur = pi3d.tt.rp('e_rabi_ou350deg-90-L', amp=1.0).pi2
        pi_dur = pi3d.tt.rp('e_rabi_ou350deg-90-L', amp=1.0).pi


        mcas = MCAS.MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('start_sequence')
        mcas.asc(length_mus=0.1)  # Starting... histogram 0

        for idx, _I_ in current_iterator_df.iterrows():

            mcas.asc(length_mus=1.0, name = 'initial_delay')
            mcas.asc(length_mus=3.0, green = True, name='Green')
            mcas.asc(length_mus=1.0)
            mcas.asc(aom_A1=True, length_mus=30., name = 'A1_init')  # Init NV with A1 laser (about 1-3 µs). This step can be skipped for the very first tests #as the green laser will also intialise somehow.
            mcas.asc(length_mus=2.0)


            if _I_['nucl_init']:
                sna.electron_rabi(
                    mcas,
                    name = 'init_MW_pi_minus1',
                    new_segment=True,
                    length_mus=1.878/2,
                    amplitudes=[0.23],
                    frequencies=np.array([3345.558]),
                    mixer_deg=[-90]
                )
                mcas.asc(length_mus=0.1, name = 'wait_after_MWinit1')

                sna.electron_rabi(
                    mcas,
                    name = 'init_MW_pi_plus1',
                    new_segment=True,
                    length_mus=1.86/2,
                    amplitudes=[0.23],
                    frequencies=np.array([3349.958]),
                    mixer_deg=[-90]
                )
                mcas.asc(length_mus=0.1, name = 'wait_after_MWinit2')
            if _I_['additional_estate_check']:

                sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False,
                        nuc='ple_Ex', mixer_deg=-90, eom_ampl =0.3,step_idx=1, laser_dur=1.0)
                mcas.asc(length_mus=1.0)




            sna.electron_rabi(
                mcas,
                new_segment=True,
                length_mus=pi_2_dur,
                amplitudes=[1.0],
                frequencies=freq,
                mixer_deg=[-90]
            )
            mcas.asc(length_mus=_I_['tau'])

            sna.electron_rabi(
                mcas,
                new_segment=True,
                length_mus=pi_dur,
                amplitudes=[1.0],
                frequencies=freq,
                mixer_deg=[-90]
            )
            mcas.asc(length_mus=_I_['tau'])

            sna.electron_rabi(
                mcas,
                new_segment=True,
                length_mus=pi_2_dur*_I_['pi_2'],
                amplitudes=[1.0],
                frequencies=freq,
                mixer_deg=[-90]
            )
            mcas.asc(length_mus = 1.0)

            # sna.ssr(mcas, **pd)
            if _I_['resonant']:

                sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False,
                        nuc='ple_Ex', mixer_deg=-90, eom_ampl =0.1,step_idx=0, laser_dur=10.0)

                # sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False,
                #         nuc='Ex_RO', mixer_deg=-90, step_idx=0, laser_dur=5.0)

                mcas.asc(length_mus=1.0)

            else:

                pd = dict(
                    length_mus_mw=0.0,
                    frequencies=[0.0],
                    mixer_deg=-90,
                    repetitions=1,
                    # transition=s,
                    final_wait=False,
                    gate_or_trigger='trigger',
                    number_of_memories=1,
                    step_idx=0,
                    # amplitudes = _I_['amplitudes'],
                    laser_dur=0.3,
                    buffer_time=1.0,
                    cw_mw=False,

                )

                sna.ssr(mcas, **pd)

            if _I_['state_check']:
                # Charge state check as EX + A1 readout
                sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False, nuc='charge_state', mixer_deg=-90,
                        step_idx=1, laser_dur=100.0)


            mcas.asc(length_mus=1.0)
            # sna.ssr(mcas, frequencies=freq, wait_dur=0.0, robust=False, nuc='charge_state', mixer_deg=-90,
            #             step_idx=0, laser_dur= 30.0)

            # mcas.asc(length_mus=20.0)


        pi3d.gated_counter.set_n_values(mcas)

        return mcas
    return ret_mcas

def settings(pdc={}):
    ana_seq=[
        ['result', '>', 1, 1, 0, 1],
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
    nuclear.do_ple_refocusA1 = True
    nuclear.do_ple_refocus = True

    nuclear.do_odmr_refocus = False
    nuclear.do_confocal_red_refocus = True
    nuclear.wavemeter_lock = False

    nuclear.save_smartly = True


    nuclear.ple_refocus_interval = 50
    nuclear.confocal_red_refocus_interval = 50

    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0]
    pi3d.gated_counter.trace.average_results = False

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(1000)),
            #('amp0',np.linspace(0.01,1.0,3)),
            ('amp0', [1.0]),
            ('resonant', [True]),
            ('state_check', [False]),
            ('nucl_init', [False]),
            ('additional_estate_check', [False]),

            ('aom_Ex_power_sweep', [-2.0]),

            ('aom_A1_power_sweep', [-5.0]),
            ('Ex_RO_power_sweep', [-3.0]),

            ('temp', [True]),
            ('delay_ps',[0]), #11110
            # ('tau', E.round_length_mus_full_sample(np.linspace(0, 0.15, 31))),
            ('tau', E.round_length_mus_full_sample(np.linspace(0, .7, 351))),

            ('pi_2', [3.0,1.0]),

        )
    )
    nuclear.number_of_simultaneous_measurements =  1#len(nuclear.parameters['pi_2'])

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