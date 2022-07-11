from __future__ import print_function, absolute_import, division
__metaclass__ = type

import sys
if sys.version_info.major == 2:
    from imp import reload
else:
    from importlib import reload

#TODO connect the objects, e.g. gated counter.
#from pi3diamond import pi3d

import importlib
import zipfile
import time
import logic.misc as misc
importlib.reload(misc)
import traceback
import datetime
import os
import numpy as np
import pandas as pd
import logging
import collections

from numbers import Number
from logic.generic_logic import GenericLogic
from core.connector import Connector
#TODO replace import with a connector to that
from logic.qudip_enhanced.data_generation import DataGeneration
#from qudip_enhanced.util import ret_property_list_element
#from qudip_enhanced import save_qutip_enhanced
import logic.qudip_enhanced.data_handling as data_handling

#import qutip_enhanced.pddata
from collections import OrderedDict

class NuclearOPs(DataGeneration):

    # instead of connectors it will be given from queue module.
    # confocal = Connector('ConfocalLogic')
    # transition_tracker = Connector('TransitionTracker')
    # mcas_dict = Connector('McasDictHolderInterface')
    #gated_counter = Connector()

    # TODO use the qudi state machine instead maybe?
    # state = ret_property_list_element('state', ['idle', 'run', 'sequence_testing', 'sequence_debug_interrupted', 'sequence_ok'])
    #
    # # Tracking stuff:
    # refocus_interval = misc.ret_property_typecheck('refocus_interval', int)
    # odmr_interval = misc.ret_property_typecheck('odmr_interval', Number)
    # additional_recalibration_interval = misc.ret_property_typecheck('additional_recalibration_interval', int)

    __TITLE_DATE_FORMAT__ = '%Y%m%dh%Hm%Ms%S'


    def __init__(self, config, **kwargs):

        super().__init__(config=config, **kwargs)
        ## TODO give all the handles for the interfaces from queue here...
        # TODO for future ODMR refocus parameters.
        # self.odmr_pd = dict(
        #     n=0,
        #     freq=None,
        #     size={'left': '1', 'right': ''},
        #     repeat=False,
        # )
        # self.odmr_pd_refocus = dict(
        #     n=1,
        #     freq=None,
        #     size={'left': '1', 'right': ''},
        #     repeat=False,
        # )

        # self.do_ple_refocusEx = False
        # self.do_ple_refocusA1 = False
        # self.do_ple_refocus = False
        # self.do_confocal_red_refocus = False
        # self.do_confocal_zpl_refocus = False
        #
        # self.do_odmr_refocus = False
        #
        # self.do_interferometerPhase_locking = False
        # self.wavemeter_lock = False
        #
        # self.yellow_repump_compensation = False
        #
        # self.last_red_confocal_refocus = - 10000
        # self.confocal_red_refocus_interval = 0
        # self.last_ple_refocus = - 10000
        # self.ple_refocus_interval = 0
        # self.last_interferometer_refocus = - 10000
        # self.interferometer_refocus_interval = 0
        #
        # self.save_smartly = False
        # self.delay_ps_list = []
        # self.window_ps_list = []
        #
        # self.two_zpl_apd = False
        # self.raw_clicks_processing = False
        # self.raw_clicks_processing_channels = [0,1,2,3,4,5,6,7]

    def on_activate(self):
        pass
        #self._confocal = self.confocal()
        #self._tt = self.transition_tracker()
        #self._mcas_dict = self.mcas_dict()
        #self._gated_counter = self.gated_counter()

        #activate connectors..

    def on_deactivate(self):
        pass

    @property
    def ana_trace(self):
        return np.array([0]) #FIXME
        #return pi3d.gated_counter.trace

    @property
    def analyze_type(self):
        try:
            return self.ana_trace.analyze_type
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    @analyze_type.setter
    def analyze_type(self, val):
        self.ana_trace.analyze_type = val

    @property
    def number_of_simultaneous_measurements(self):
        return self.ana_trace.number_of_simultaneous_measurements

    @number_of_simultaneous_measurements.setter
    def number_of_simultaneous_measurements(self, val):
        self.ana_trace.number_of_simultaneous_measurements = val

    @property #this comes form data generation.
    def observation_names(self):
        try:
            if hasattr(self, '_observation_names'):
                return self._observation_names
            else:
                zpl_counters = []

                for i, delay_ps in enumerate(self.delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        name = 'zpl_counter_data_{i}_{j}'.format(i=i, j=j)
                        zpl_counters.append(name)
                        if self.two_zpl_apd:
                            name = 'zpl_2_counter_data_{i}_{j}'.format(i=i, j=j)
                            zpl_counters.append(name)

                if self.save_smartly:



                    # return zpl_counters + \
                    #        [
                    #            # 'trace',
                    #         'average_counts',
                    #         'start_time', 'end_time','events',
                    #         'aom_Ex_power_measured', 'aom_A1_power_measured',
                    #         'Ex_RO_power_measured', 'EOM_Ex_integrator_voltage',
                    #         ]

                    # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code

                    if self.yellow_repump_compensation:
                        yell = ['yellow_freq_measured']
                    else:
                        yell = []

                    return zpl_counters + \
                           ['trace',
                            'average_counts',
                            'start_time', 'end_time','events',
                            'aom_Ex_power_measured', 'aom_A1_power_measured',
                            'Ex_RO_power_measured', 'EOM_Ex_integrator_voltage',
                            'windows_ps', 'delays_ps']+yell

                if self.raw_clicks_processing:
                    if self.yellow_repump_compensation:
                        yell = ['yellow_freq_measured']
                    else:
                        yell = []

                    return zpl_counters + \
                           ['average_counts','events',
                            'start_time', 'end_time',
                            'ple_Ex', 'ple_A1',
                            'confocal_x', 'confocal_y', 'confocal_z',
                            'aom_Ex_power_measured', 'aom_A1_power_measured',
                            'Ex_RO_power_measured', 'EOM_Ex_integrator_voltage',
                            'windows_ps', 'delays_ps']+yell

                else:
                    if self.yellow_repump_compensation:
                        yell = ['yellow_freq_measured']
                    else:
                        yell = []

                    return ['result_{}'.format(i) for i in range(self.number_of_results)] + zpl_counters + \
                           ['trace',
                            'ple_Ex', 'ple_A1',
                            'average_counts', 'events', 'thresholds',
                            'start_time', 'end_time',
                            'mw_mixing_frequency', 'local_oscillator_freq',
                            'confocal_x', 'confocal_y', 'confocal_z',
                            'aom_Ex_power_measured', 'aom_A1_power_measured', 'Ex_RO_power_measured',
                            'EOM_Ex_integrator_voltage',
                            'windows_ps', 'delays_ps']+yell
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    @property
    def dtypes(self):
        if not hasattr(self, '_dtypes'):
            if self.save_smartly:

                # self._dtypes = dict(events='int',
                #                     # windows_ps='object',
                #                     # delays_ps='object',
                #                     # trace='object',
                #                     start_time='datetime', end_time='datetime',
                #                     average_counts='float')


                # # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                self._dtypes = dict(delays_ps='object',
                                    events='int',
                                    windows_ps='object', trace='object',
                                    start_time='datetime', end_time='datetime',
                                    average_counts='float')

            elif self.raw_clicks_processing:
                self._dtypes = dict(delays_ps='object',windows_ps='object',
                                    start_time='datetime', end_time='datetime',
                                    events='int',
                                    confocal_x='float', confocal_y='float', confocal_z='float',
                                    average_counts='float')



            else:
                self._dtypes = dict(delays_ps='object',
                                    windows_ps='object', trace='object',
                                    events='int', start_time='datetime', end_time='datetime',
                                    local_oscillator_freq='float', thresholds='object',
                                    confocal_x='float', confocal_y='float', confocal_z='float',
                                    average_counts='float')

            for i, delay_ps in enumerate(self.delay_ps_list):
                for j, window_ps in enumerate(self.window_ps_list):
                    name = 'zpl_counter_data_{i}_{j}'.format(i=i, j=j)
                    self._dtypes.update({name:'object'})

                    if self.two_zpl_apd:
                        name = 'zpl_2_counter_data_{i}_{j}'.format(i=i, j=j)
                        self._dtypes.update({name: 'object'})

        return self._dtypes

    @property
    def number_of_results(self):
        return self.ana_trace.number_of_results

    def run(self, *args, **kwargs):
        if getattr(self, 'debug_mode', False):
            self.run_debug_sequence(*args, **kwargs)
        else:
            self.run_measurement(*args, **kwargs)

    def run_measurement(self, abort, **kwargs):
        pi3d = None
        self.init_run(**kwargs)
        self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[self._confocal.x], confocal_y=[self._confocal.y], confocal_z=[self._confocal.z]))
        try:
            if hasattr(pi3d,'microwave'):
                pi3d.microwave.On()
            # pi3d.gated_counter.set_counter(start_trigger_delay_ps_list = self.delay_ps_list ,window_ps_list = self.window_ps_list)


            for idx, _ in enumerate(self.iterator()):
                if abort.is_set(): break
                while True:
                    if abort.is_set(): break

                    # if self.wavemeter_lock and pi3d.wavemeter.wm_id != 0:
                    #     freq = pi3d.wavemeter.get_current_frequency()
                    #     pi3d.wavemeter.set_lock_frequency(freq)
                    #     pi3d.wavemeter.lock_frequency()
                    #     time.sleep(0.1)

                    if self.do_confocal_red_refocus:
                        self.do_refocus_red()

                    if self.do_confocal_zpl_refocus:
                        self.do_refocus_zpl()

                    if self.do_ple_refocus or self.do_ple_refocusA1 or self.do_ple_refocusEx:
                        # if 'delta_ple_Ex' in self.current_iterator_df.keys():
                        #     pi3d.ple_Ex.delta_ple = self.current_iterator_df['delta_ple_Ex'].unique()[0]
                        #     logging.getLogger().info(
                        #         'I set delta_ple_Ex: {}'.format(self.current_iterator_df['delta_ple_Ex'].unique()[0]))
                        self.do_refocus_ple(abort)

                    # if self.do_odmr_refocus:
                    #     self.do_refocusodmr(abort, check_odmr_frequency_drift_ok=False, initial_odmr=False)

                    #Here put EOM!
                    self.check_eom()



                    # if 'aom_Ex_power_sweep' in self.current_iterator_df.keys():
                    #     current_Ex_voltage = pi3d.power_calibration.aom_list['aom_Ex_power'].voltage
                    #
                    #     if self.current_iterator_df['aom_Ex_power_sweep'].unique()!= current_Ex_voltage:
                    #         logging.getLogger().info('I set voltage Ex: {}'.format(self.current_iterator_df['aom_Ex_power_sweep'].unique()))
                    #         pi3d.power_calibration.aom_list['aom_Ex_power'].set_voltage(
                    #             self.current_iterator_df['aom_Ex_power_sweep'].unique())
                    #         time.sleep(0.1)

                    # if 'Ex_RO_power_sweep' in self.current_iterator_df.keys():
                    #     current_Ex_RO_voltage = pi3d.power_calibration.aom_list['Ex_RO_aom_power'].voltage
                    #
                    #     if self.current_iterator_df['Ex_RO_power_sweep'].unique()!= current_Ex_RO_voltage:
                    #         logging.getLogger().info(
                    #             'I set voltage RO Ex: {}'.format(self.current_iterator_df['Ex_RO_power_sweep'].unique()))
                    #         pi3d.power_calibration.aom_list['Ex_RO_aom_power'].set_voltage(
                    #                 self.current_iterator_df['Ex_RO_power_sweep'].unique())
                    #         time.sleep(0.1)

                    # if 'aom_A1_power_sweep' in self.current_iterator_df.keys():
                    #     current_A1_voltage = pi3d.power_calibration.aom_list['aom_A1_power'].voltage
                    #
                    #     if self.current_iterator_df['aom_A1_power_sweep'].unique()!= current_A1_voltage:
                    #         logging.getLogger().info(
                    #             'I set voltage A1: {}'.format(self.current_iterator_df['aom_A1_power_sweep'].unique()))
                    #         pi3d.power_calibration.aom_list['aom_A1_power'].set_voltage(
                    #             self.current_iterator_df['aom_A1_power_sweep'].unique())
                    #         time.sleep(0.1)


                    # if 'repump_power_sweep' in self.current_iterator_df.keys():
                    #     current_repump_voltage = pi3d.power_calibration.aom_list['aom_repump_power'].voltage
                    #
                    #     # if self.current_iterator_df['repump_power_sweep'].unique()!= current_repump_voltage:
                    #     #     logging.getLogger().info(
                    #     #         'I set voltage repump: {}'.format(self.current_iterator_df['repump_power_sweep'].unique()))
                    #     #     #pi3d.power_calibration.aom_list['aom_repump_power'].set_voltage(
                    #     #             self.current_iterator_df['repump_power_sweep'].unique())
                    #     #     time.sleep(0.1)


                    if self.do_interferometerPhase_locking:
                        interferometer_phase = None

                        if 'interferometer_phase' in self.current_iterator_df.keys():
                            interferometer_phase = self.current_iterator_df['interferometer_phase'].unique()[0]
                        self.do_interf_phase_lock(interferometer_phase)

                    if self.yellow_repump_compensation:

                        # add here the ability to sweep desired frequency
                        if 'yellow_desired_freq' in self.current_iterator_df.keys():
                            yellow_desired_freq = self.current_iterator_df['yellow_desired_freq'].unique()[0]
                            # print('yellow_desired_freq ', yellow_desired_freq)
                            #pi3d.ple_repump.desired_freq = yellow_desired_freq

                        #pi3d.ple_repump.compensate_drift()


                    self.setup_rf(self.current_iterator_df) #MCAS is ready


                    if abort.is_set(): break
                    self.data.set_observations([OrderedDict(start_time=datetime.datetime.now())]*self.number_of_simultaneous_measurements)

                    if self.raw_clicks_processing:
                        self.data.set_observations(pd.concat([self.df_refocus_pos.iloc[-1:, :]]*self.number_of_simultaneous_measurements).reset_index(drop=True))
                        self.data.set_observations([OrderedDict(ple_A1=self._tt.ple_A1)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(ple_Ex=self._tt.ple_Ex)]*self.number_of_simultaneous_measurements)

                    elif not self.save_smartly:
                        self.data.set_observations([OrderedDict(mw_mixing_frequency=self._tt.mw_mixing_frequency)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(ple_Ex=self._tt.ple_Ex)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(ple_A1=self._tt.ple_A1)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(local_oscillator_freq=self._tt.current_local_oscillator_freq)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations(pd.concat([self.df_refocus_pos.iloc[-1:, :]]*self.number_of_simultaneous_measurements).reset_index(drop=True))

                    self.data.set_observations([OrderedDict(start_time=datetime.datetime.now())]*self.number_of_simultaneous_measurements)
                    #self.data.set_observations([OrderedDict(EOM_Ex_integrator_voltage=pi3d.power_calibration.pd_list[
                      #  'pd_Ex_integrator_voltage'].get_data())] * self.number_of_simultaneous_measurements)
                    self._md['red_Ex'].run()
                    #self.data.set_observations([OrderedDict(aom_Ex_power_measured=pi3d.power_calibration.pd_list['pd_A1_power'].get_data())]*self.number_of_simultaneous_measurements)
                    time.sleep(0.1)
                    self._md.stop_awgs()

                    self._md['Ex_RO'].run()
                    #self.data.set_observations([OrderedDict(Ex_RO_power_measured=pi3d.power_calibration.pd_list['pd_A1_power'].get_data())]*self.number_of_simultaneous_measurements)
                    time.sleep(0.1)
                    self._md.stop_awgs()

                    self._md['red_A1'].run()
                    #self.data.set_observations([OrderedDict(aom_A1_power_measured=pi3d.power_calibration.pd_list['pd_A1_power'].get_data())]*self.number_of_simultaneous_measurements)
                    time.sleep(0.1)
                    self._md.stop_awgs()
                    #TODO add laser power meters to the df
                    #if self.yellow_repump_compensation:
                        #self.data.set_observations([OrderedDict(yellow_freq_measured=pi3d.wavemeter.dll.GetFrequencyNum(3, 0))] * self.number_of_simultaneous_measurements)

                    self.get_trace(abort,delay_ps_list = self.delay_ps_list ,window_ps_list = self.window_ps_list) #Start AWGs...
                    if abort.is_set(): break
                    self.data.set_observations([OrderedDict(end_time=datetime.datetime.now())]*self.number_of_simultaneous_measurements)

                    if self.save_smartly:
                        pass
                        # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                        dd = self.ana_trace.trace
                        idx = np.nonzero(dd)
                        ddd = dd[idx]
                        self.data.set_observations([
                                                       OrderedDict({'trace': (idx, ddd)})
                                                   ] * self.number_of_simultaneous_measurements)
                    if self.raw_clicks_processing:
                        pass
                    else:
                        self.data.set_observations([OrderedDict(trace=self.ana_trace.trace)]*self.number_of_simultaneous_measurements)
                    # print('type(self.ana_trace.trace) ', type(self.ana_trace.trace))
                    # print('self.ana_trace.trace.dtype ', self.ana_trace.trace.dtype)

                    # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                    self.data.set_observations([OrderedDict(delays_ps=self.delay_ps_list)]*self.number_of_simultaneous_measurements)
                    self.data.set_observations([OrderedDict(windows_ps=self.window_ps_list)]*self.number_of_simultaneous_measurements)

                    if self._gated_counter.ZPL_counter:
                        for i, delay_ps in enumerate(self.delay_ps_list):
                            for j, window_ps in enumerate(self.window_ps_list):
                                name = 'zpl_counter_data_{i}_{j}'.format(i=i, j=j)
                                dd = getattr(self._gated_counter,name)
                                if self.save_smartly:

                                    self.data.set_observations([
                                                               OrderedDict({name: dd})
                                                           ] * self.number_of_simultaneous_measurements)

                                    # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                                    # idx = np.nonzero(dd)
                                    # ddd = dd[idx]
                                    idx = np.nonzero(dd)
                                    ddd = dd[idx]
                                    self.data.set_observations([
                                                               OrderedDict({name: (idx,ddd)})
                                                           ] * self.number_of_simultaneous_measurements)
                                else:
                                    self.data.set_observations([
                                                               OrderedDict({name: dd})
                                                           ] * self.number_of_simultaneous_measurements)

                                if self.two_zpl_apd:
                                    name = 'zpl_2_counter_data_{i}_{j}'.format(i=i, j=j)
                                    dd = getattr(pi3d.gated_counter,name)
                                    if self.save_smartly:
                                        self.data.set_observations([
                                                                   OrderedDict({name: dd})
                                                               ] * self.number_of_simultaneous_measurements)

                                        # # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                                        idx = np.nonzero(dd)
                                        ddd = dd[idx]
                                        self.data.set_observations([
                                                                   OrderedDict({name: (idx,ddd)})
                                                               ] * self.number_of_simultaneous_measurements)
                                    else:
                                        self.data.set_observations([
                                                                   OrderedDict({name: dd})
                                                               ] * self.number_of_simultaneous_measurements)


                    if abort.is_set(): break
                    repeat_measurement = self.analyze()
                    if abort.is_set(): break

                    #
                    # if self.do_confocal_red_refocus:
                    #     self.do_refocus_red()
                    #
                    # if self.do_confocal_zpl_refocus:
                    #     self.do_refocus_zpl()
                    #
                    #
                    # if self.do_ple_refocus or self.do_ple_refocusA1 or self.do_ple_refocusEx:
                    #         self.do_refocus_ple(abort)

                    if self.do_odmr_refocus:
                        odmr_frequency_drift_ok = self.do_refocusodmr(abort=abort)
                    else:
                        odmr_frequency_drift_ok = True

                    if repeat_measurement:
                        print('repeat_measurement ')
                    if odmr_frequency_drift_ok and not repeat_measurement:
                        break

                if hasattr(self, '_pld'):
                    self.pld.new_data_arrived()
                if abort.is_set(): break
                self.save()
        except Exception as e:
            print('ERROR: Nuclear op failed in run measuremt',e)
            abort.set()
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            self.data._df = data_handling.df_take_duplicate_rows(self.data.df, self.iterator_df_done) #drops unfinished measurements,
            self.pld.new_data_arrived()
            pi3d.multi_channel_awg_sequence.stop_awgs(pi3d.awgs)
            self.state = 'idle'
            self.update_current_str()


            if self.session_meas_count == 0:
                self.pld.gui.close_gui()
                if hasattr(self.data, 'init_from_file') and self.data.init_from_file is not None:
                    self.move_init_from_file_folder_back()
            if os.path.exists(self.save_dir) and not os.listdir(self.save_dir):
                os.rmdir(self.save_dir)


            # if self.wavemeter_lock and pi3d.wavemeter.wm_id != 0:
            #     pi3d.wavemeter.unlock_frequency()
            #     time.sleep(0.1)

    @property
    def session_meas_count(self):
        if len(self.data.df) == 0 or len(self.iterator_df_done) == 0:
            return 0
        else:
            return len(self.iterator_df_done) - len(self.data.df[(self.data.df.start_time < self.start_time) & (self.data.df.start_time > datetime.datetime(1900, 1, 1))])


    def run_debug_sequence(self, abort, **kwargs):
        if any([key in kwargs for key in ['iff', 'init_from_file']]):
            raise Exception('Error: Data initialization from file (.hdf or .csv) not allwoed in sequence debug mode.')
        if len(self.parameters['sweeps']) != 1:
            print('Debug mode, number of sweeps set to one.')
            self.parameters['sweeps'] = [0]
        self.init_run(**kwargs)
        self.state = 'sequence_testing'
        try:
            self._mcas_dict.debug_mode = True
            for idx, _ in enumerate(self.iterator()):
                if abort.is_set(): break
                self.data.set_observations([OrderedDict(start_time=datetime.datetime.now())] * self.number_of_simultaneous_measurements)
                self.setup_rf(self.current_iterator_df)
                self.data.set_observations([OrderedDict(end_time=datetime.datetime.now())] * self.number_of_simultaneous_measurements)
            if not abort.is_set():
                self.state = 'sequence_ok'
        except Exception:
            self.state = 'sequence_debug_interrupted'
            abort.set()
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            self._mcas_dict.debug_mode = False
            self.multi_channel_awg_sequence.stop_awgs(self._awgs) ##FIXME
            self.update_current_str()
            if os.path.exists(self.save_dir) and not os.listdir(self.save_dir):
                os.rmdir(self.save_dir)

    def confocal_pos_moving_average(self, n):
        #FIXME ?
        return self.df_refocus_pos[['confocal_x', 'confocal_y', 'confocal_z']].rolling(n, win_type='boxcar', center=True).sum().dropna()/n

    @property
    def refocus_moving_average_num(self):
        return getattr(self, '_refocus_moving_average_num', 10)

    @refocus_moving_average_num.setter
    def refocus_moving_average_num(self, val):
        self._refocus_moving_average_num = val

    @property
    def sweeps(self):
        return self.parameters['sweeps']
    #
    #
    # def do_refocus_ple(self,abort):
    #     delta_t = time.time() - self.last_ple_refocus
    #
    #     if (delta_t>= self.ple_refocus_interval):
    #
    #
    #         if self.do_ple_refocusA1:
    #             self.do_refocus_pleA1(abort)
    #
    #         if self.do_ple_refocusEx:
    #             self.do_refocus_pleEx(abort)
    #
    #         self.last_ple_refocus = time.time()

    #
    # def do_refocus_pleEx(self, abort):
    #     if self.wavemeter_lock and pi3d.wavemeter.wm_id!=0:
    #         pi3d.wavemeter.unlock_frequency()
    #         time.sleep(0.1)
    #
    #
    #     pi3d.ple_Ex.syncFlag = False
    #     pi3d.ple_Ex.state = 'refocus PLE'
    #
    #     while(pi3d.ple_Ex.syncFlag == False):
    #         time.sleep(0.1)
    #     time.sleep(0.5)
    #
    #     if self.wavemeter_lock and pi3d.wavemeter.wm_id != 0:
    #         freq = pi3d.wavemeter.get_current_frequency()
    #         pi3d.wavemeter.set_lock_frequency(freq)
    #         pi3d.wavemeter.lock_frequency()
    #         time.sleep(0.1)
    #
    #
    # def do_refocus_pleA1(self, abort):
    #     pi3d.ple_A1.syncFlag = False
    #     pi3d.ple_A1.state = 'refocus PLE'
    #
    #     while(pi3d.ple_A1.syncFlag == False):
    #         time.sleep(0.1)
    #     time.sleep(1.1)
    #
    #
    #
    # def do_refocus_red(self):
    #
    #     delta_t = time.time() - self.last_red_confocal_refocus
    #
    #     if (delta_t >= self.confocal_red_refocus_interval):
    #
    #         pi3d.confocal.syncFlag=False
    #         pi3d.confocal.state = 'refocus_red'
    #
    #         while pi3d.confocal.syncFlag == False:
    #             time.sleep(0.1)
    #
    #         time.sleep(0.5)
    #         self.last_red_confocal_refocus = time.time()
    #
    #
    #         self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[pi3d.confocal.x], confocal_y=[pi3d.confocal.y], confocal_z=[pi3d.confocal.z]))
    #
    #
    #
    #
    # def do_refocus_zpl(self):
    #
    #     delta_t = time.time() - self.last_red_confocal_refocus
    #
    #     if (delta_t >= self.confocal_red_refocus_interval):
    #
    #         pi3d.confocal.syncFlag=False
    #         pi3d.confocal.state = 'refocus_zpl'
    #
    #         while pi3d.confocal.syncFlag == False:
    #             time.sleep(0.1)
    #
    #         time.sleep(0.5)
    #         self.last_red_confocal_refocus = time.time()
    #
    #
    #         self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[pi3d.confocal.x], confocal_y=[pi3d.confocal.y], confocal_z=[pi3d.confocal.z]))
    #
    #
    #
    #
    #
    # def check_eom(self):
    #
    #     logging.getLogger().info('checking the eom')
    #     for i in range(3):
    #         current_voltage = pi3d.power_calibration.pd_list['pd_Ex_integrator_voltage'].get_data()
    #         if current_voltage > 1.5 or current_voltage <-1.5:
    #             logging.getLogger().info('V_c = {}: relocking...'.format(current_voltage))
    #             for rel in range(3):
    #                 pi3d.interferometer.relock_eom()
    #         else:
    #             return
    #     raise Exception('After 3 trials EOM is not locked!')
    #
    #
    #
    #
    #
    #
    #
    # # ----------------
    # # Should not refocus every time, should refocus only if time>last_interferometer_refocus
    # # ----------------
    #
    # def do_interf_phase_lock(self, interferometer_phase = None):
    #     interferometer = pi3d.interferometer
    #     delta_t = time.time() - self.last_interferometer_refocus
    #     if (delta_t >= self.interferometer_refocus_interval):
    #         interferometer.do_calibration_scan()
    #
    #     while interferometer.syncFlag == False:
    #         time.sleep(0.1)
    #
    #     if (interferometer_phase is not None) and (interferometer._desired_voltage!=interferometer_phase):
    #         print('I am setting interferometer phase {} pi'.format(interferometer_phase/np.pi))
    #         interferometer.desired_phase = interferometer_phase
    #         interferometer.set_desired_voltage(interferometer.phase2voltage(interferometer.desired_phase))
    #         interferometer.go_to_position(interferometer._desired_voltage)
    #
    #     while interferometer.syncFlag == False:
    #         time.sleep(0.1)
    #
    #
    #     time.sleep(0.2)
    #     self.last_interferometer_refocus = time.time()
    #
    #
    #     # def do_interf_phase_lock(self, interferometer_phase=None):
    #     #     interferometer = pi3d.interferometer
    #     #     if interferometer_phase is not None:
    #     #         interferometer.desired_phase = interferometer_phase
    #     #     interferometer.do_calibration_scan()
    #     #     while interferometer.syncFlag == False:
    #     #         time.sleep(0.1)




    def run_refocus(self):
        pass
        # print('NUCLEAROPS RUN REFOCUS')
        # pi3d.confocal.run_refocus()
        # self.df_refocus_pos = self.df_refocus_pos.append(pd.DataFrame(OrderedDict(confocal_x=[pi3d.confocal.x], confocal_y=[pi3d.confocal.y], confocal_z=[pi3d.confocal.z]))).reset_index(drop=True)
        # if self.refocus_moving_average_num > 1:
        #     ma = self.confocal_pos_moving_average(min(len(self.df_refocus_pos), self.refocus_moving_average_num))
        #     for axis in ['x', 'y', 'z']:
        #         setattr(pi3d.confocal, axis, getattr(ma, 'confocal_{}'.format(axis)).iloc[-1])
        #     logging.getLogger().info("Refocus ma_deviation [nm]: {}, {}, {}".format(*[(getattr(pi3d.confocal, axis) - self.df_refocus_pos.iloc[-1, :]['confocal_{}'.format(axis)])*1000 for axis in ['x', 'y', 'z']]))

    def add_odmr_script_to_queue(self, abort, pd):
        pass
        #sys.modules[pi3d.init_task(name='refocus_confocal_odmr', folder='D:/Python/pi3diamond/UserScripts/')].run_fun(abort=abort, **pd)

    # def do_refocusodmr(self, abort=None, check_odmr_frequency_drift_ok=True, initial_odmr=False):
    #     if abort.is_set():
    #         logging.getLogger().info('do_refocusodmr stopped here0')
    #     pi3d.odmr.file_name = self.file_name
    #     delta_t = time.time() - self.last_odmr
    #     if self.odmr_interval != 0 and (delta_t >= self.odmr_interval) or len(self.data.df) == 0 or initial_odmr:
    #         if check_odmr_frequency_drift_ok and hasattr(self, 'maximum_odmr_drift'):
    #             self.add_odmr_script_to_queue(abort, self.odmr_pd)
    #             current_drift = np.abs(pi3d.tt.current_local_oscillator_freq - self.data.df.iloc[-1, :].local_oscillator_freq)
    #             if current_drift > self.maximum_odmr_drift:
    #                 logging.getLogger().info("Too much drift ({} > {}), trying again!".format(current_drift, self.maximum_odmr_drift))
    #                 odmr_frequency_drift_ok = False
    #             else:
    #                 logging.getLogger().info("Drift is ok  ({} < {})".format(current_drift, self.maximum_odmr_drift))
    #                 odmr_frequency_drift_ok = True
    #             if self.refocus_interval != 0 and self.odmr_count % self.refocus_interval == 0:
    #                 self.add_odmr_script_to_queue(abort, self.odmr_pd_refocus)
    #         else:
    #             if self.refocus_interval != 0 and self.odmr_count % self.refocus_interval == 0:
    #                 self.add_odmr_script_to_queue(abort, self.odmr_pd_refocus)
    #             else:
    #                 self.add_odmr_script_to_queue(abort, self.odmr_pd)
    #             odmr_frequency_drift_ok = True
    #         self.odmr_count += 1
    #         self.last_odmr = time.time()
    #         if abort.is_set():
    #             logging.getLogger().info('do_refocusodmr stopped here1')
    #         return odmr_frequency_drift_ok
    #     elif check_odmr_frequency_drift_ok:
    #         if abort.is_set():
    #             logging.getLogger().info('do_refocusodmr stopped here2')
    #         return True

    # def odmr_frequency_drift_ok(self):
    #     if not hasattr(self, 'maximum_odmr_drift'):
    #         return True
    #     if len(self.data.df) > 0:
    #         current_drift = np.abs(pi3d.tt.current_local_oscillator_freq - self.data.df.iloc[-1,:].local_oscillator_freq)
    #         if current_drift > self.maximum_odmr_drift:
    #             logging.getLogger().info("Too much drift ({} > {}), trying again!".format(current_drift, self.maximum_odmr_drift))
    #             return False
    #         else:
    #             logging.getLogger().info("Drift is ok  ({} > {})".format(current_drift, self.maximum_odmr_drift))
    #             return True

    def reinit(self):
        super(NuclearOPs, self).reinit()
        self.odmr_count = 0
        self.additional_recalibration_interval_count = 0
        self.last_odmr = time.time()
        self.last_rabi_refocus = time.time()


    def get_trace(self, abort, delay_ps_list = None,window_ps_list = None):
        # print('get_trace NuclearOps delay', delay_ps_list)
        # print('get_trace NuclearOps window_ps', window_ps_list)
        self.mcas.initialize()
        self._gated_counter.count(abort, #FIXme get connector.
                                 ch_dict=self.mcas.ch_dict,
                                 start_trigger_delay_ps_list = delay_ps_list,
                                 window_ps_list = window_ps_list,
                                 two_zpl_apd = self.two_zpl_apd,
                                 raw_clicks_processing = self.raw_clicks_processing,
                                 raw_clicks_processing_channels = self.raw_clicks_processing_channels)

    def setup_rf(self, current_iterator_df):
        self.mcas = ''
        self.mcas = self.ret_mcas(current_iterator_df)
        while self.mcas=='':
            time.sleep(0.1)

        time.sleep(0.1)
        self._mcas_dict[self.mcas.name] = self.mcas

    def analyze(self, data=None, ana_trace=None, start_idx=None):
        if ana_trace is None:
            ana_trace = self.ana_trace
            if self.analyze_type != ana_trace.analyze_type:
                raise Exception('This was supposed to be a sanity check. The programmer made shit.')
        data = self.data if data is None else data
        if ana_trace.analyze_type is not None:
            df = ana_trace.analyze().df
            if (df.events == 0).any() and not self.analyze_type == 'consecutive' and df.at[0, 'events'] != 0:
                return True
            if 'result_num' in df.columns: #if results are not averaged
                obs_r = df.pivot_table(values='result', columns='result_num', index='sm').rename(
                    columns=collections.OrderedDict([(i, 'result_{}'.format(i)) for i in df.result_num.unique()]))
            else:
                obs_r = df.rename(columns={'result': 'result_0'}).drop(columns=['step', 'events', 'sm'])
            if not self.save_smartly and not self.raw_clicks_processing:
                data.set_observations(obs_r, start_idx=start_idx)
                data.set_observations(df.groupby(['sm']).agg({'thresholds': lambda x: [i for i in x]}), start_idx=start_idx)

            data.set_observations(df.groupby(['sm']).agg({'events': np.sum}), start_idx=start_idx)
            data.set_observations(df.groupby(['sm']).agg({'average_counts': np.mean}), start_idx=start_idx)

            logging.getLogger().info(df)
            logging.getLogger().info(ana_trace.analyze_type)
            return False

    # def reanalyze(self, do_while_run=False, **kwargs):
    #     if self.state == 'run' and not do_while_run:
    #         print('Measurement is running.\nReanalyzation will write to data.df and may interfere with the running measurement doing the same.\nIf you want to reanalyze anyway, pass argument do_while_run=True')
    #         return
    #     import Analysis
    #     ana_trace = Analysis.Trace()
    #     for key in ['analyze_type', 'number_of_simultaneous_measurements', 'analyze_sequence', 'binning_factor', 'average_results', 'consecutive_valid_result_numbers']:
    #         setattr(ana_trace, key, kwargs.get(key, getattr(self.ana_trace, key)))
    #     for idx, _I_ in self.data.df.iterrows():
    #         if (idx-1)%ana_trace.number_of_simultaneous_measurements:
    #             continue ## What is it for? (seems that it doing nothings.
    #         if type(_I_['trace']) != np.ndarray:
    #             print('Interrupted reanalyzation at dataframe index {}, as trace is not a numpy array.\nMaybe, this is trace has just not been measured yet?\nTotal length of dataframe is {}'.format(idx, len(self.data.df)))
    #             break
    #         ana_trace.trace = _I_['trace']
    #         self.analyze(ana_trace=ana_trace, start_idx=idx)

    def save(self):
        pass
        # if len(self.iterator_df_done) > 0 and not(hasattr(self, 'do_save') and not self.do_save):
        #     t0 = time.time()
        #     super(NuclearOPs, self).save(notify=True) #### IMPORTANT
        #     self.save_sequence_file()
        #     pi3d.save_pi3diamond(destination_dir=self.save_dir)
        #     save_qutip_enhanced(destination_dir=self.save_dir)
        #     logging.getLogger().info("saved nuclear to '{} ({:.3f})".format(self.save_dir, time.time() - t0))

    def save_sequence_file(self):
        pass
        seq_message = []
        for k in self._md[self.mcas.name].sequences.keys():
            for ch in [1,2]:
                try:
                    seq_message.append(self._md[self.mcas.name].sequences[k][ch].ret_info())
                except:
                    pass

        awg_file_name = 'awg-file.txt'
        awg_fp = os.path.join(self.save_dir, awg_file_name)

        if not os.path.exists(awg_fp):
            with open(awg_fp, 'w') as fp:
                for page in seq_message:
                    fp.write(page)
                    fp.write('-------\n')

    def reset_settings(self):
        """
        Here only settings are changed that are not automatically changed during run()
        :return:
        """
        self.additional_recalibration_interval = 0
        self.ret_mcas = None
        self.mcas = None
        self.refocus_interval = 2
        self.odmr_interval = 15
        self.file_notes = ''
        self.thread = None