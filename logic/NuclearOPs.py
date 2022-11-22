from __future__ import print_function, absolute_import, division
__metaclass__ = type

import sys
if sys.version_info.major == 2:
    from imp import reload
else:
    from importlib import reload

#TODO connect the objects, e.g. gated counter.
#from self.queueiamond import self.queue

import importlib
import zipfile
import time
import logic.misc as misc
importlib.reload(misc)
import traceback
import datetime
import threading
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
from logic.qudip_enhanced.util import ret_property_list_element
from logic.qudip_enhanced import save_qutip_enhanced
import logic.qudip_enhanced.data_handling as data_handling
import base64
import hashlib

#import qutip_enhanced.pddata
from collections import OrderedDict

class NuclearOPs(DataGeneration):

    # TODO use the qudi state machine instead maybe?
    state = ret_property_list_element('state', ['idle', 'run', 'sequence_testing', 'sequence_debug_interrupted', 'sequence_ok'])
    #
    # # Tracking stuff:
    refocus_interval = misc.ret_property_typecheck('refocus_interval', int)
    odmr_interval = misc.ret_property_typecheck('odmr_interval', Number)
    additional_recalibration_interval = misc.ret_property_typecheck('additional_recalibration_interval', int)

    __TITLE_DATE_FORMAT__ = '%Y%m%dh%Hm%Ms%S'


    def __init__(self):#TODO - revert back here from the self.queue.

        super().__init__()
        ## TODO give all the handles for the interfaces from queue here...
        # TODO for future ODMR refocus parameters.
        self.odmr_pd = dict(
            n=0,
            freq=None,
            size={'left': '1', 'right': ''},
            repeat=False,
        )
        self.odmr_pd_refocus = dict(
            n=1,
            freq=None,
            size={'left': '1', 'right': ''},
            repeat=False,
        )
        self.hashed = False
        self.do_ple_refocusA2 = False
        self.do_ple_refocusA1 = False
        self.do_ple_refocus = False
        self.do_confocal_repump_refocus = False
        self.do_confocal_A1A2_refocus = False
        self.do_confocal_A2MW_refocus = False
        #
        self.refocus_cw_odmr =False
        self.refocus_pulsed_odmr =False
        #
        self.do_interferometerPhase_locking = False
        self.wavemeter_lock = False
        #
        self.yellow_repump_compensation = False
        #
        self.last_red_confocal_refocus = - 10000
        self.last_odmr_refocus = -10000
        self.last_ple_refocus = - 10000
        self.confocal_refocus_interval = 0
        self.ple_refocus_interval = 0
        self.odmr_refocus_interval=0
        self.last_interferometer_refocus = - 10000
        self.interferometer_refocus_interval = 0
        #
        self.save_smartly = False
        self.delay_ps_list = []
        self.window_ps_list = []
        #
        self.two_zpl_apd = False
        self.raw_clicks_processing = False
        self.raw_clicks_processing_channels = [0,1,2,3,4,5,6,7]

        self.performedRefocus = False


        #self._confocal = self.confocal()
        #self._tt = self.transition_tracker()
        #self._mcas_dict = self.mcas_dict()
        #self._gated_counter = self.gated_counter()

        #activate connectors..

    @property
    def ana_trace(self):
        #return np.array([0]) #FIXME

        return self.queue._gated_counter.trace#self.queue.gated_counter.trace

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
                            'ple_A2', 'ple_A1',
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
                            'ple_A2', 'ple_A1',
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
        self._md = self.queue._awg.mcas_dict
        if getattr(self, 'debug_mode', False):
            #self.run_debug_sequence(*args, **kwargs)

            self.thread = threading.Thread(target=self.run_debug_sequence,args = args, kwargs = kwargs)
            self.thread.start()
            



        else:
            self.thread = threading.Thread(target=self.run_measurement,args = args, kwargs = kwargs)
            self.thread.start()
            #self.run_measurement(*args, **kwargs)

    #def mainloop():

    #    Qtimer.timeout.connect(run_iteration)

    #def run_iteration(self, current_iterator):

    def run_measurement(self, abort, **kwargs):
        t0 = time.time()
        print('NuclearOps run_measurement')

        self.init_run(**kwargs)
        #logging.info('passed the init')
        #When the confocal connected #TODO 1
        confocal = self.queue._confocal
        x = confocal._current_x
        y = confocal._current_y
        z = confocal._current_z
        #logging.info('got the confocal position')
        self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[x],confocal_y = [y], confocal_z = [z]))
        #[self._confocal.x], confocal_y=[self._confocal.y], confocal_z=[self._confocal.z]))
        print("t 1=", time.time()-t0)
        t0 = time.time()
        try:
            #if hasattr(self.queue,'microwave'):
            #   self.queue.microwave.On()

            # TODO uncomment when on the setup
            #self.queue._gated_counter.set_counter()#
            #start_trigger_delay_ps_list = self.delay_ps_list ,window_ps_list = self.window_ps_list)

            #enumerator=enumerate(self.iterator())
            #iterator_list=list(self.iterator()) # seems to laag imensely
            for idx, _ in enumerate(self.iterator()):#range(len(iterator_list)):
                if abort.is_set(): break
                while True:
                    if abort.is_set(): break
                    # Uncomment when on the setup #TODO
                    #if self.wavemeter_lock and self.queue.wavemeter.wm_id != 0:
                     #    freq = self.queue.wavemeter.get_current_frequency()
                     #    self.queue.wavemeter.set_lock_frequency(freq)
                      #   self.queue.wavemeter.lock_frequency()
                    #     time.sleep(0.1)

                    if self.do_confocal_repump_refocus:
                        self.do_refocus_repump()

                    if self.do_confocal_A1A2_refocus or self.do_confocal_A2MW_refocus:
                        self.do_refocus_zpl()

                    if self.do_ple_refocusA2 or self.do_ple_refocusA1:
                        self.do_refocus_ple(abort)
                        # if 'delta_ple_A2' in self.current_iterator_df.keys():
                        #     self.queue.ple_A2.delta_ple = self.current_iterator_df['delta_ple_A2'].unique()[0]
                        #     logging.getLogger().info(
                        #         'I set delta_ple_A2: {}'.format(self.current_iterator_df['delta_ple_A2'].unique()[0]))

                    if self.refocus_cw_odmr or self.refocus_pulsed_odmr:
                         self.do_refocusodmr(abort, check_odmr_frequency_drift_ok=False, initial_odmr=False)

                    #if self.set_laser_power:
                        # set laser power to wanted value
                    #Here put EOM!
                    #TODO uncomment
                    #self.check_eom() #if it still locked.



                    #if 'aom_Ex_power_sweep' in self.current_iterator_df.keys():
                    #     current_Ex_voltage = self.queue.power_calibration.aom_list['aom_Ex_power'].voltage
                    #
                    #     if self.current_iterator_df['aom_Ex_power_sweep'].unique()!= current_Ex_voltage:
                    #         logging.getLogger().info('I set voltage Ex: {}'.format(self.current_iterator_df['aom_Ex_power_sweep'].unique()))
                    #         self.queue.power_calibration.aom_list['aom_Ex_power'].set_voltage(
                    #             self.current_iterator_df['aom_Ex_power_sweep'].unique())
                    #         time.sleep(0.1)

                    # if 'Ex_RO_power_sweep' in self.current_iterator_df.keys():
                    #     current_Ex_RO_voltage = self.queue.power_calibration.aom_list['Ex_RO_aom_power'].voltage
                    #
                    #     if self.current_iterator_df['Ex_RO_power_sweep'].unique()!= current_Ex_RO_voltage:
                    #         logging.getLogger().info(
                    #             'I set voltage RO Ex: {}'.format(self.current_iterator_df['Ex_RO_power_sweep'].unique()))
                    #         self.queue.power_calibration.aom_list['Ex_RO_aom_power'].set_voltage(
                    #                 self.current_iterator_df['Ex_RO_power_sweep'].unique())
                    #         time.sleep(0.1)

                    # if 'aom_A1_power_sweep' in self.current_iterator_df.keys():
                    #     current_A1_voltage = self.queue.power_calibration.aom_list['aom_A1_power'].voltage
                    #
                    #     if self.current_iterator_df['aom_A1_power_sweep'].unique()!= current_A1_voltage:
                    #         logging.getLogger().info(
                    #             'I set voltage A1: {}'.format(self.current_iterator_df['aom_A1_power_sweep'].unique()))
                    #         self.queue.power_calibration.aom_list['aom_A1_power'].set_voltage(
                    #             self.current_iterator_df['aom_A1_power_sweep'].unique())
                    #         time.sleep(0.1)


                    # if 'repump_power_sweep' in self.current_iterator_df.keys():
                    #     current_repump_voltage = self.queue.power_calibration.aom_list['aom_repump_power'].voltage
                    #
                    #     # if self.current_iterator_df['repump_power_sweep'].unique()!= current_repump_voltage:
                    #     #     logging.getLogger().info(
                    #     #         'I set voltage repump: {}'.format(self.current_iterator_df['repump_power_sweep'].unique()))
                    #     #     #self.queue.power_calibration.aom_list['aom_repump_power'].set_voltage(
                    #     #             self.current_iterator_df['repump_power_sweep'].unique())
                    #     #     time.sleep(0.1)


                    #if self.do_interferometerPhase_locking:
                     #   interferometer_phase = None

                      #  if 'interferometer_phase' in self.current_iterator_df.keys():
                       #     interferometer_phase = self.current_iterator_df['interferometer_phase'].unique()[0]
                        #pass
                        #self.do_interf_phase_lock(interferometer_phase)

                    #if self.yellow_repump_compensation:
                        # add here the ability to sweep desired frequency
                        #if 'yellow_desired_freq' in self.current_iterator_df.keys():
                         #   yellow_desired_freq = self.current_iterator_df['yellow_desired_freq'].unique()[0]
                          #  # print('yellow_desired_freq ', yellow_desired_freq)
                            #self.queue.ple_repump.desired_freq = yellow_desired_freq

                        #self.queue.ple_repump.compensate_drift()
                    
                    self.setup_rf(self.current_iterator_df, hashed = self.hashed) #MCAS is ready
                    
                    if abort.is_set(): break
                    
                    print("Save Smartly in NucOps: ",self.save_smartly)
                    start = time.time()
                    if self.raw_clicks_processing:
                        self.data.set_observations(pd.concat([self.df_refocus_pos.iloc[-1:, :]]*self.number_of_simultaneous_measurements).reset_index(drop=True))
                        self.data.set_observations([OrderedDict(ple_A1=self.queue._transition_tracker.ple_A1)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(ple_A2=self.queue._transition_tracker.ple_A2)]*self.number_of_simultaneous_measurements)
                    elif not self.save_smartly:
                        self.data.set_observations([OrderedDict(mw_mixing_frequency=self.queue._transition_tracker.mw_mixing_frequency)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(local_oscillator_freq=self.queue._transition_tracker.current_local_oscillator_freq)]*self.number_of_simultaneous_measurements)
                        self.data.set_observations([OrderedDict(ple_A2=self.queue._transition_tracker.ple_A2)]*self.number_of_simultaneous_measurements) # already inlcuded in raw_clicks_processing
                        self.data.set_observations([OrderedDict(ple_A1=self.queue._transition_tracker.ple_A1)]*self.number_of_simultaneous_measurements) # already inlcuded in raw_clicks_processing
                        self.data.set_observations(pd.concat([self.df_refocus_pos.iloc[-1:, :]]*self.number_of_simultaneous_measurements).reset_index(drop=True))#already inlcuded in raw_clicks_processing
                        
                    self.data.set_observations([OrderedDict(start_time=datetime.datetime.now())]*self.number_of_simultaneous_measurements)
                    print("Time for Saving 1:", time.time()-start)
                    # TODO
                    #Measure powers and record them!!!!
                    ##
                    # self.data.set_observations([OrderedDict(EOM_Ex_integrator_voltage=self.queue.power_calibration.pd_list[
                    #     'pd_Ex_integrator_voltage'].get_data())] * self.number_of_simultaneous_measurements)


                    if False:#not self._md.debug_mode: Laser power calibration #Fixme
                        self._md['red_Ex'].run()
                        #self.data.set_observations([OrderedDict(aom_Ex_power_measured=self.queue.power_calibration.pd_list['pd_A1_power'].get_data())]*self.number_of_simultaneous_measurements)
                        time.sleep(0.1)
                        self._md.stop_awgs()


                        self._md['Ex_RO'].run()
                        #self.data.set_observations([OrderedDict(Ex_RO_power_measured=self.queue.power_calibration.pd_list['pd_A1_power'].get_data())]*self.number_of_simultaneous_measurements)
                        time.sleep(0.1)
                        self._md.stop_awgs()

                        self._md['red_A1'].run()
                        #self.data.set_observations([OrderedDict(aom_A1_power_measured=self.queue.power_calibration.pd_list['pd_A1_power'].get_data())]*self.number_of_simultaneous_measurements)
                        time.sleep(0.1)
                        self._md.stop_awgs()

                    #TODO add laser power meters to the df
                    #if self.yellow_repump_compensation:
                        #self.data.set_observations([OrderedDict(yellow_freq_measured=self.queue.wavemeter.dll.GetFrequencyNum(3, 0))] * self.number_of_simultaneous_measurements)
                    #t1 = time.time()
                    # print(t1)
                    # Thread1=threading.Thread(target=self.get_trace, args=(abort), kwargs={'delay_ps_list': self.delay_ps_list ,'window_ps_list' : self.window_ps_list})
                    # Thread1.start()
                    self.get_trace(abort,delay_ps_list = self.delay_ps_list ,window_ps_list = self.window_ps_list) #Start AWGs...
                    # print(time.time()-t1,'after get trace')
                    if abort.is_set(): break
                    
                    self.data.set_observations([OrderedDict(end_time=datetime.datetime.now())]*self.number_of_simultaneous_measurements)

                    if self.save_smartly:
                        t0 = time.time()
                        #pass
                        # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                        dd = self.ana_trace.trace
                        idx = np.nonzero(dd)
                        ddd = dd[idx]
                        self.data.set_observations([
                                                       OrderedDict({'trace': (idx, ddd)})
                                                   ] * self.number_of_simultaneous_measurements)
                        print("t_2=", time.time()-t0)
                        t0 = time.time()
                    elif self.raw_clicks_processing:
                        pass
                    else:
                        self.data.set_observations([OrderedDict(trace=self.ana_trace.trace)]*self.number_of_simultaneous_measurements)
                    # # print('type(self.ana_trace.trace) ', type(self.ana_trace.trace))
                    # # print('self.ana_trace.trace.dtype ', self.ana_trace.trace.dtype)

                    # TEMP SOLUTION FIXME LATER, Only for HOM , just uncomment this code
                    #self.data.set_observations([OrderedDict(delays_ps=self.delay_ps_list)]*self.number_of_simultaneous_measurements)
                    #self.data.set_observations([OrderedDict(windows_ps=self.window_ps_list)]*self.number_of_simultaneous_measurements)
                    print("t_3=", time.time()-t0)
                    t0 = time.time()

                    if False:# self.queue._gated_counter.ZPL_counter:
                        for i, delay_ps in enumerate(self.delay_ps_list):
                            for j, window_ps in enumerate(self.window_ps_list):
                                name = 'zpl_counter_data_{i}_{j}'.format(i=i, j=j)
                                dd = getattr(self.queue._gated_counter,name)
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
                                    dd = getattr(self.queue._gated_counter,name)
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

                    print("t_4=", time.time()-t0)
                    t0 = time.time()
                    if abort.is_set(): break
                    repeat_measurement = self.analyze() ##TODO here we make only non zeros., and do the average. 
                    if abort.is_set(): break
                    print("t_5=", time.time()-t0)

                    
                    if self.do_confocal_repump_refocus:
                        self.do_refocus_repump()
                    
                    if self.do_confocal_A1A2_refocus or self.do_confocal_A2MW_refocus:
                        self.do_refocus_zpl()
                    
                    
                    if self.do_ple_refocus or self.do_ple_refocusA1 or self.do_ple_refocusA2:
                            self.do_refocus_ple(abort)


                    t0 = time.time()
                    if self.refocus_cw_odmr or self.refocus_pulsed_odmr:
                        self.do_refocusodmr(abort=abort)
                        odmr_frequency_drift_ok = self.do_refocusodmr(abort=abort)
                    else:
                        odmr_frequency_drift_ok = True

                    if repeat_measurement:
                        print('repeat_measurement ')
                    if odmr_frequency_drift_ok and not repeat_measurement:
                        break

                    print("t_6=", time.time()-t0)
                    t0 = time.time()
                    # end of while
                    # print("end of while")

                if hasattr(self, '_pld'):
                    self.pld.new_data_arrived()
                if abort.is_set(): break
                print("t_7=", time.time()-t0)
                t0 = time.time()
                print("START SAVING:")
                self.save()
                print("SAVING COMPLETED.", time.time()-t0)
                #end of for
                # print("end of for")
                
        except Exception as e:
            print('ERROR: Nuclear op failed in run measuremt',e)
            abort.set()
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            t0 = time.time()
            self.data._df = data_handling.df_take_duplicate_rows(self.data.df, self.iterator_df_done) #drops unfinished measurements,
            print("t_9=", time.time()-t0)
            t0 = time.time()
            self.pld.new_data_arrived()
            print("t_10=", time.time()-t0)
            t0 = time.time()
            #self.queue.multi_channel_awg_sequence.stop_awgs(self.queue.awgs)
            self.state = 'idle'
            self.update_current_str()

            print("t_11=", time.time()-t0)
            t0 = time.time()
            if self.session_meas_count == 0:
                self.pld.gui.close_gui()
                if hasattr(self.data, 'init_from_file') and self.data.init_from_file is not None:
                    self.move_init_from_file_folder_back()

            print("t_12=", time.time()-t0)
            t0 = time.time()
            if os.path.exists(self.save_dir) and not os.listdir(self.save_dir):
                os.rmdir(self.save_dir)


            # if self.wavemeter_lock and self.queue.wavemeter.wm_id != 0:
            #     self.queue.wavemeter.unlock_frequency()
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
            self._md.debug_mode = True
            for idx, _ in enumerate(self.iterator()):
                if abort.is_set(): break
                self.data.set_observations([OrderedDict(start_time=datetime.datetime.now())] * self.number_of_simultaneous_measurements)
                
                #self.dowork()
                self.setup_rf(self.current_iterator_df) ##Is this guy stops the main loop?
                
                self.data.set_observations([OrderedDict(end_time=datetime.datetime.now())] * self.number_of_simultaneous_measurements)
            if not abort.is_set():
                self.state = 'sequence_ok'
        except Exception:
            self.state = 'sequence_debug_interrupted'
            abort.set()
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            #TODO do this
            #self._md.debug_mode = False
            self._md.stop_awgs() ##FIXME
            self.update_current_str()
            if os.path.exists(self.save_dir) and not os.listdir(self.save_dir):
                os.rmdir(self.save_dir)

    def dowork(self,):
        time.sleep(1)

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


    def do_refocus_ple(self,abort):
        delta_t = time.time() - self.last_ple_refocus

        if (delta_t>= self.ple_refocus_interval):


            if self.do_ple_refocusA1:
                self.do_refocus_pleA1(abort)

            if self.do_ple_refocusA2:
                self.do_refocus_pleA2(abort)

            self.last_ple_refocus = time.time()
            time.sleep(1)
            self.performedRefocus = True

            if self.checkA1LaserPower:
                self.queue._awg.mcas_dict.awgs["ps"].constant(pulse=(0,["A1"],0,0))
                self.queue._powerstabilization_logic.controlA1 = True
                self.queue._powerstabilization_logic.controlA2 = False
                self.queue._powerstabilization_logic.TargetPower = self.A1LaserPower
                self.queue._powerstabilization_logic.start_control
                start_time = time.time()
                while self.queue._powerstabilization_logic.stabilize:
                    time.sleep(0.1)
                    if start_time - time.time() > 30:
                        logging.getLogger().info('Could not reach desired A1-laserpower in reasonable time. Set analog voltage to 0.5V.')
                        self.queue._powerstabilization_logic.A1Voltage = 0.5
                        self.queue._powerstabilization_logic.set_fix_voltage(tag="A1")
                self.queue._awg.mcas_dict.awgs["ps"].Night()
            if self.checkA2LaserPower:
                self.queue._awg.mcas_dict.awgs["ps"].constant(pulse=(0,["A2"],0,0))
                self.queue._powerstabilization_logic.controlA2 = True
                self.queue._powerstabilization_logic.controlA1 = False
                self.queue._powerstabilization_logic.TargetPower = self.A2LaserPower
                self.queue._powerstabilization_logic.start_control
                start_time = time.time()
                while self.queue._powerstabilization_logic.stabilize:
                    time.sleep(0.1)
                    if start_time - time.time() > 30:
                        logging.getLogger().info('Could not reach desired A2-laserpower in reasonable time. Set analog voltage to 0.5V.')
                        self.queue._powerstabilization_logic.A2Voltage = 0.5
                        self.queue._powerstabilization_logic.set_fix_voltage(tag="A2")                
                self.queue._awg.mcas_dict.awgs["ps"].Night()

    def do_refocus_pleA2(self, abort): #CHANGED! commented what belonged to wavemeter
        #if self.wavemeter_lock and self.queue.wavemeter.wm_id!=0:
        #    self.queue.wavemeter.unlock_frequency()
        #    time.sleep(0.1)
        
        self.queue._PLE_logic.Lock_laser=True
        self.queue._PLE_logic.start_scanning()
        while not self.queue._PLE_logic.stopped:
            time.sleep(0.5)

        # self.queue.ple_A2.syncFlag = False
        # self.queue.ple_A2.state = 'refocus PLE'

        # while(self.queue.ple_A2.syncFlag == False):
        #     time.sleep(0.1)
        # time.sleep(0.5)

        #if self.wavemeter_lock and self.queue.wavemeter.wm_id != 0:
        #    freq = self.queue.wavemeter.get_current_frequency()
        #    self.queue.wavemeter.set_lock_frequency(freq)
        #    self.queue.wavemeter.lock_frequency()
        #    time.sleep(0.1)


    def do_refocus_pleA1(self, abort):
        self.queue.ple_A1.syncFlag = False
        self.queue.ple_A1.state = 'refocus PLE'

        while(self.queue.ple_A1.syncFlag == False):
            time.sleep(0.1)
        time.sleep(1.0)


    def do_refocus_repump(self):
        delta_t = time.time() - self.last_red_confocal_refocus
        print("doing_refocus_repump")
        if (delta_t >= self.confocal_refocus_interval):

            self.queue._awg.mcas_dict.awgs["ps"].constant(pulse=(0,["repump"],0,0))

            self.queue._optimizer.start_refocus(initial_pos = np.array(self.df_refocus_pos.iloc[0]))
            while not self.queue._optimizer.refocus_finished:
                time.sleep(0.25)
            self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[self.queue._optimizer.optim_pos_x], confocal_y=[self.queue._optimizer.optim_pos_y], confocal_z=[self.queue._optimizer.optim_pos_z]))
            
            
            #TODO connect to optimized and return when done
            # self.queue.optimizer.syncFlag=False
            # self.queue.optimizer.state = 'refocus_red'

            # while self.queue.confocal.syncFlag == False:
            #     time.sleep(0.1)

            # time.sleep(0.5)
            # self.last_red_confocal_refocus = time.time()


            # self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[self.queue.confocal.x], confocal_y=[self.queue.confocal.y], confocal_z=[self.queue.confocal.z]))

            self.performedRefocus = True



    def do_refocus_zpl(self):
        
        delta_t = time.time() - self.last_red_confocal_refocus

        if (delta_t >= self.confocal_refocus_interval):
            print("doing confocal refocus with resonant laser")

            sequence_name="A2MW_confocal_refocus"
            if self.do_confocal_A1A2_refocus:
                self.queue._awg.mcas_dict.awgs["ps"].constant(pulse=(0,["A1", "A2", "repump"],0,0)) # last 2 digits are analog output: these are set in the awg_hardware. These parameters are not used


            elif self.do_confocal_A2MW_refocus:
                MW1_freq = 33.6
                MW2_freq = 173.6
                MW3_freq = 173.6
                enable_MW1 = True
                enable_MW2 = True
                enable_MW3 = False

                enable_Repump =True

                self.power = [0.25,0.25,0.25]
                # if self.enable_MW1:
                #     self.power += [self.MW1_power]
                # if self.enable_MW2:
                #     self.power += [self.MW2_power]
                # if self.enable_MW3:
                #     self.power += [self.MW3_power]

                #self.power = np.asarray(self.power)
                #self.power=self.power_to_amp(self.power)

                if not sequence_name in self.queue._awg.mcas_dict:

                    seq = self.queue._awg.mcas(name=sequence_name, ch_dict={"2g": [1, 2], "ps": [1]})
                    frequencies = np.array([MW1_freq, MW2_freq, MW3_freq])[[enable_MW1, enable_MW2, enable_MW3]]
                    seq.start_new_segment("Microwaves"+str(frequencies), loop_count=200)
                    seq.asc(name="with MW", pd2g1={"type": "sine", "frequencies": frequencies, "amplitudes": self.power},
                            A2=True,
                            repump=enable_Repump,
                            length_mus=50
                            )

                    self.queue._awg.mcas_dict[sequence_name] = seq

                    while self.mcas=='':
                        #process_events() #TODO gui process events.
                        time.sleep(0.01)
            

            self.queue._awg.mcas_dict[sequence_name].run()
        
            self.queue._optimizer.start_refocus(initial_pos = self.queue._confocal.get_position(), caller_tag = 'NuclearOps')
            while not self.queue._optimizer.refocus_finished:
                time.sleep(0.25)

            self.last_red_confocal_refocus = time.time()

            self.df_refocus_pos = pd.DataFrame(OrderedDict(confocal_x=[self.queue._optimizer.optim_pos_x], confocal_y=[self.queue._optimizer.optim_pos_y], confocal_z=[self.queue._optimizer.optim_pos_z]))
            self.queue._awg.mcas_dict.stop_awgs()
            time.sleep(1)
            self.performedRefocus = True
    def check_eom(self):

        logging.getLogger().info('checking the eom')
        for i in range(3):
            current_voltage = self.queue.power_calibration.pd_list['pd_Ex_integrator_voltage'].get_data()
            if current_voltage > 1.5 or current_voltage <-1.5:
                logging.getLogger().info('V_c = {}: relocking...'.format(current_voltage))
                for rel in range(3):
                    self.queue.interferometer.relock_eom()
            else:
                return
        raise Exception('After 3 trials EOM is not locked!')







    # # ----------------
    # # Should not refocus every time, should refocus only if time>last_interferometer_refocus
    # # ----------------
    #
    # def do_interf_phase_lock(self, interferometer_phase = None):
    #     interferometer = self.queue.interferometer
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
    #     #     interferometer = self.queue.interferometer
    #     #     if interferometer_phase is not None:
    #     #         interferometer.desired_phase = interferometer_phase
    #     #     interferometer.do_calibration_scan()
    #     #     while interferometer.syncFlag == False:
    #     #         time.sleep(0.1)




    def run_refocus(self):
        pass
        # print('NUCLEAROPS RUN REFOCUS')
        # self.queue.confocal.run_refocus()
        # self.df_refocus_pos = self.df_refocus_pos.append(pd.DataFrame(OrderedDict(confocal_x=[self.queue.confocal.x], 
        #                                                                           confocal_y=[self.queue.confocal.y], 
        #                                                                           confocal_z=[self.queue.confocal.z]))).reset_index(drop=True)
        # if self.refocus_moving_average_num > 1:
        #     ma = self.confocal_pos_moving_average(min(len(self.df_refocus_pos), self.refocus_moving_average_num))
        #     for axis in ['x', 'y', 'z']:
        #         setattr(self.queue.confocal, axis, getattr(ma, 'confocal_{}'.format(axis)).iloc[-1])
        #     logging.getLogger().info("Refocus ma_deviation [nm]: {}, {}, {}".format(*[(getattr(self.queue.confocal, axis) - self.df_refocus_pos.iloc[-1, :]['confocal_{}'.format(axis)])*1000 for axis in ['x', 'y', 'z']]))

    def add_odmr_script_to_queue(self, abort, pd):
        sys.modules[self.queue.init_task(name='refocus_confocal_odmr', folder='C:/src/qudi/notebooks')].run_fun(self, abort=abort, **pd)

    def do_refocusodmr(self, abort=None, check_odmr_frequency_drift_ok=True, initial_odmr=False):
        if abort.is_set():
            pass
            #logging.getLogger().info('do_refocusodmr stopped here0')

        #Range of ODMR?


        delta_t = time.time() - self.last_odmr_refocus
        if (delta_t >= self.odmr_refocus_interval):
            print("starting ODMR refocus")
            if self.refocus_cw_odmr:
                self.queue._ODMR_logic.ODMRLogic.cw_PerformFit=True
                self.queue._ODMR_logic.ODMRLogic.cw_Stoptime=15 #sec
                self.queue._ODMR_logic.ODMRLogic.cw_Run_Button_Clicked(True)

                while self.queue._ODMR_logic.ODMRLogic.cw_odmr_refocus_running:
                    time.sleep(0.5)

            elif self.refocus_pulsed_odmr:
                self.queue._ODMR_logic.pulsedODMRLogic.pulsed_PerformFit=True
                self.queue._ODMR_logic.pulsedODMRLogic.pulsed_Stoptime=15 #sec
                self.queue._ODMR_logic.pulsedODMRLogic.pulsed_Run_Button_Clicked(True)

                while self.queue._ODMR_logic.pulsedODMRLogic.pulsed_odmr_refocus_running:
                    time.sleep(0.5)
            self.performedRefocus = True
        #self.queue._awg.mcas_dict.stop_awgs()
        self.last_odmr_refocus=time.time()
        self.queue._gated_counter.set_counter()

        self.odmr_frequency_drift_ok = True # just to test, if sequence is running
        return self.odmr_frequency_drift_ok # just to test, if sequence is running
        # self.queue.odmr.file_name = self.file_name
        # delta_t = time.time() - self.last_odmr
        # if self.odmr_interval != 0 and (delta_t >= self.odmr_interval) or len(self.data.df) == 0 or initial_odmr:
        #     if check_odmr_frequency_drift_ok and hasattr(self, 'maximum_odmr_drift'):
        #         self.add_odmr_script_to_queue(abort, self.odmr_pd)
        #         current_drift = np.abs(self.queue.tt.current_local_oscillator_freq - self.data.df.iloc[-1, :].local_oscillator_freq)
        #         if current_drift > self.maximum_odmr_drift:
        #             #logging.getLogger().info("Too much drift ({} > {}), trying again!".format(current_drift, self.maximum_odmr_drift))
        #             print("Too much drift ({} > {}), trying again!".format(current_drift, self.maximum_odmr_drift))
        #             odmr_frequency_drift_ok = False
        #         else:
        #             #logging.getLogger().info("Drift is ok  ({} < {})".format(current_drift, self.maximum_odmr_drift))
        #             print("Drift is ok  ({} < {})".format(current_drift, self.maximum_odmr_drift))
        #             odmr_frequency_drift_ok = True
        #         if self.refocus_interval != 0 and self.odmr_count % self.refocus_interval == 0:
        #             self.add_odmr_script_to_queue(abort, self.odmr_pd_refocus)
        #     else:
        #         if self.refocus_interval != 0 and self.odmr_count % self.refocus_interval == 0:
        #             self.add_odmr_script_to_queue(abort, self.odmr_pd_refocus)
        #         else:
        #             self.add_odmr_script_to_queue(abort, self.odmr_pd)
        #         odmr_frequency_drift_ok = True
        #     self.odmr_count += 1
        #     self.last_odmr = time.time()
        #     if abort.is_set():
        #         #logging.getLogger().info('do_refocusodmr stopped here1')
        #         print('do_refocusodmr stopped here1')
        #     return odmr_frequency_drift_ok
        # elif check_odmr_frequency_drift_ok:
        #     if abort.is_set():
        #         #logging.getLogger().info('do_refocusodmr stopped here2')
        #         print('do_refocusodmr stopped here2')
        #     return True

    # def odmr_frequency_drift_ok(self):
    #     if not hasattr(self, 'maximum_odmr_drift'):
    #         return True
    #     if len(self.data.df) > 0:
    #         current_drift = np.abs(self.queue.tt.current_local_oscillator_freq - self.data.df.iloc[-1,:].local_oscillator_freq)
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
        if not self._md.debug_mode:
            print("INITIALIZING")
            t1 = time.time()
            self.mcas.initialize()
            print("time needed for init: ", time.time() - t1)
           
        self.queue._gated_counter.count(abort,
                                 ch_dict=self.mcas.ch_dict,
                                 start_trigger_delay_ps_list = delay_ps_list,
                                 window_ps_list = window_ps_list,
                                 two_zpl_apd = self.two_zpl_apd,
                                 raw_clicks_processing = self.raw_clicks_processing,
                                 raw_clicks_processing_channels = self.raw_clicks_processing_channels)

    # def setup_rf(self, current_iterator_df):
    #     t1 = time.time()
    #     #logging.info('setting up the rf')
    #     self.mcas = ''
    #     print("t 1", time.time()-t1)
    #     t1 = time.time()
    #     self.mcas = self.ret_mcas(self,current_iterator_df)
    #     while self.mcas=='':
    #         #process_events() #TODO gui process events.
    #         time.sleep(0.01)
    #     print("t 2", time.time()-t1)
    #     t1 = time.time()
    #     self.queue._awg.mcas_dict[self.mcas.name] = self.mcas
    #     print("t 3", time.time()-t1)
    #     #logging.info('finished setting up the sequence')

    def setup_rf(self, current_iterator_df, hashed = True):
        #print("current_iterator_df ", current_iterator_df)
        if "sweeps" in current_iterator_df.columns:
            current_iterator_df = current_iterator_df.drop(["sweeps"], axis=1)

        hash = base64.b64encode(hashlib.sha1((str(current_iterator_df)+"\n"+str(self.queue._gated_counter.readout_duration)).encode()).digest()) ##REmove the sweep from the current_iterator_df.
        #Added self.queue._gated_counter.readout_duration such that the hash recognizes a change in readout duration and will update n_values in the sequence accordingly
        sequence_name = "nuclear_op_hash_{}".format(hash)
        if hashed and not sequence_name in self.queue._awg.mcas_dict or self.performedRefocus:
            self.queue._awg.mcas_dict.stop_awgs()
            self.mcas = ''
            
            self.mcas = self.ret_mcas(self,current_iterator_df, sequence_name)
            while self.mcas=='':
                time.sleep(0.01)
    
            self.queue._awg.mcas_dict[sequence_name] = self.mcas
   
        elif hashed and self.mcas==None and sequence_name in self.queue._awg.mcas_dict:
            self.mcas = self.queue._awg.mcas_dict[sequence_name]
   
        elif hashed and self.mcas.name != sequence_name:
            self.queue._awg.mcas_dict.stop_awgs()
            self.mcas = self.queue._awg.mcas_dict[sequence_name]
   
        elif hashed == False: 
            self.queue._awg.mcas_dict.stop_awgs()
            self.mcas = ''
            self.mcas = self.ret_mcas(self,current_iterator_df)
            while self.mcas=='':
                #process_events() #TODO gui process events.
                time.sleep(0.01)
            sequence_name = self.mcas.name
            self.queue._awg.mcas_dict[sequence_name] = self.mcas
        else:
            print("Dont need to set up new RF.")
        self.performedRefocus = False
            
         #pi3d.mcas_dict[sequence_name].initialize()
        # pi3d.mcas_dict[sequence_name].start_awgs()

    def analyze(self, data=None, ana_trace=None, start_idx=None, ):
        if ana_trace is None:
            ana_trace = self.ana_trace
            if self.analyze_type != ana_trace.analyze_type:
                raise Exception('This was supposed to be a sanity check. The programmer made shit.')
        data = self.data if data is None else data
        if ana_trace.analyze_type is not None:
            t_ana_t0 = time.time()
            #df = ana_trace.analyze_fast().df
            df = ana_trace.analyze().df
            print('time of Analysis.ana_trace.analyze_fast = ', time.time() - t_ana_t0)
            # print("df in NucOps: ", df.at)
            # print("df in NucOps: ", df.at[0, 'events'])
            if (df.events == 0).any() and not self.analyze_type == 'consecutive' and df.at[0, 'events'] != 0:
                return True #Means that data is good? 
            if 'result_num' in df.columns: #if there are multiple readouts of type "result", here step index is important
                obs_r = df.pivot_table(values='result', columns='result_num', index='sm').rename(
                    columns=collections.OrderedDict([(i, 'result_{}'.format(i)) for i in df.result_num.unique()]))
            else:
                obs_r = df.rename(columns={'result': 'result_0'}).drop(columns=['step', 'events', 'sm'])
            if not self.save_smartly and not self.raw_clicks_processing:
                data.set_observations(obs_r, start_idx=start_idx)
                #data.set_observations(df.groupby(['sm']).agg({'thresholds': lambda x: [i for i in x]}), start_idx=start_idx)

            data.set_observations(df.groupby(['sm']).agg({'events': np.sum}), start_idx=start_idx)
            data.set_observations(df.groupby(['sm']).agg({'average_counts': np.mean}), start_idx=start_idx)

            #logging.getLogger().info(df)
            #logging.getLogger().info(ana_trace.analyze_type)
            return False

    def reanalyze(self, do_while_run=False, **kwargs):
        if self.state == 'run' and not do_while_run:
            print('Measurement is running.\nReanalyzation will write to data.df and may interfere with the running measurement doing the same.\nIf you want to reanalyze anyway, pass argument do_while_run=True')
            return
        import Analysis
        ana_trace = Analysis.Trace()
        for key in ['analyze_type', 'number_of_simultaneous_measurements', 'analyze_sequence', 'binning_factor', 'average_results', 'consecutive_valid_result_numbers']:
            setattr(ana_trace, key, kwargs.get(key, getattr(self.ana_trace, key)))
        for idx, _I_ in self.data.df.iterrows():
            if (idx-1)%ana_trace.number_of_simultaneous_measurements:
                continue ## What is it for? (seems that it doing nothings.
            if type(_I_['trace']) != np.ndarray:
                print('Interrupted reanalyzation at dataframe index {}, as trace is not a numpy array.\nMaybe, this is trace has just not been measured yet?\nTotal length of dataframe is {}'.format(idx, len(self.data.df)))
                break
            ana_trace.trace = _I_['trace']
            self.analyze(ana_trace=ana_trace, start_idx=idx)

    def save(self):
        pass
        if len(self.iterator_df_done) > 0 and not(hasattr(self, 'do_save') and not self.do_save):
            t0 = time.time()
            Thread1= threading.Thread(target= super(NuclearOPs, self).save, kwargs={"notify":False})
            Thread1.start()
            #super(NuclearOPs, self).save(notify=False) #### IMPORTANT
            Thread1.join()
            print("Waiting to join threads=", time.time()-t0)
            t0 = time.time()
            self.save_sequence_file()
            print("t2=", time.time()-t0)
            t0 = time.time()
            self.queue.save_pi3diamond(destination_dir=self.save_dir)
            print("t3=", time.time()-t0)
            t0 = time.time()
            save_qutip_enhanced(destination_dir=self.save_dir)
            print("t4=", time.time()-t0)
            t0 = time.time()
            #TODO
            # has to switch to qudi log. logging.getLogger().info("saved nuclear to '{} ({:.3f})".format(self.save_dir, time.time() - t0))

    def save_sequence_file(self):
        pass
        seq_message = []
        for k in self._md[self.mcas.name].sequences.keys():
            for ch in [1,2]:
                try:
                    
                    seq_message.append(self._md[self.mcas.name].sequences[k][ch].ret_info()) ##TODO why is it also printing in the consolse??
                    seq_message.append("\n") ##TODO why is it also printing in the consolse??
                except:
                    
                    pass
        #seq_message.append("\n") ##TODO why is it also printing in the consolse??
        seq_message.append(str(self._md[self.mcas.name].sequences['ps'][1])) ##TODO why is it also printing in the consolse??
        #seq_message.append("\n") ##TODO why is it also printing in the consolse??
        awg_file_name = 'awg-file.txt'
        awg_fp = os.path.join(self.save_dir, awg_file_name)

        if not os.path.exists(awg_fp):
            with open(awg_fp, 'w') as fp:
                for page in seq_message:
                    fp.write(page)
                    #fp.write("\n") ##TODO why is it also printing in the consolse??
                    fp.write('\n-------------------------------------------------------------------\n')

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