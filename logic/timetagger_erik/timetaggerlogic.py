#ODMR-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys

from core.module import Base
from core.connector import Connector
#from hardware.swabian_instruments.timetagger import TT as TimeTagger
from logic.generic_logic import GenericLogic
#import hardware.Keysight_AWG_M8190.pyarbtools_master.pyarbtools as pyarbtools

from qtpy import QtCore
from logic.odmrlogic.cw_ODMR_default_values_and_widget_functions import cw_ODMR_default_values_and_widget_functions as cw_default
from logic.odmrlogic.pulsed_ODMR_default_values_and_widget_functions import pulsed_ODMR_default_values_and_widget_functions as pulsed_default

import inspect
import logging
logger = logging.getLogger(__name__)
import time
import datetime
from collections import OrderedDict
import matplotlib.pyplot as plt
#import pandas as pd

class TimeTaggerLogic(GenericLogic):
    #declare connectors
    counter_device = Connector(interface='TimeTaggerInterface')# Savelogic just for testing purposes
    savelogic = Connector(interface='SaveLogic')
    
    #create the signals:
    sigTimeTaggerPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray)

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Get connectors
        self._time_tagger=self.counter_device()
        self._time_tagger.setup_TT()
        self._save_logic = self.savelogic()
        
        self.filename = ""
        self.stoptime = ""
        self.periodicsaving = False
        self.runtime = 0

        self.measurement_state = 'Stopped'
        
        self.counter_params = self._time_tagger._counter
        self.time_diff_params = self._time_tagger._time_diff
        self.hist_params = self._time_tagger._hist

    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.
        """
        del self._time_tagger
        return 

    def start_counter(self):
        self.measurement_state= 'Counter'
        self.counter = self.init_counter(channels = self.counter_params['channels'],
            bins_width = self.counter_params['bins_width'],
            n_values = self.counter_params['n_values']
        )
        self.data = np.zeros(self.counter_params['n_values'])
        i = 0
        while i < 5:
            self.counter_data_readout()
            time.sleep(1)
            i +=1
  
    def start_time_differences(self):
        self.measurement_state= 'TimeDiff'
        self.time_differences = self.init_time_differences(click_channel = self.time_diff_params['click_channel'],
            start_channel = self.time_diff_params['start_channel'],
            next_channel = self.time_diff_params['next_channel'],
            sync_channel = self.time_diff_params['sync_channel'],
            binwidth = self.time_diff_params['binwidth'],
            n_bins = self.time_diff_params['n_bins'],
            n_histograms = self.time_diff_params['n_histograms']
        )
        i = 0
        while i < 5:
            self.time_differences_data_readout()
            time.sleep(1)
            i +=1

    def start_histogram(self):
        self.measurement_state= 'Histogram'
        self.histogram = self.init_histogram(click_channel = self.hist_params['click_channel'],
            start_channel = self.hist_params['start_channel'],
            binwidth = self.hist_params['binwidth'],
            number_of_bins = self.hist_params['number_of_bins'])
        i = 0
        while i < 5:
            self.histogram_data_readout()
            time.sleep(1)
            i +=1


    def init_counter(self,**kwargs):
        #kwargs: channels, bins_width, n_values
        self._time_tagger._counter.update(**kwargs)
        return self._time_tagger.counter()

    def init_time_differences(self,**kwargs):
        #kwargs: click_channel, start_channel, next_channel, sync_channel, binwidth, n_bins, n_histograms
        self._time_tagger._time_diff.update(**kwargs)
        return self._time_tagger.time_differences()
    
    def init_histogram(self,**kwargs):
        #kwargs: click_channel, ,start_channel, binwidth, number_of_bins
        self._time_tagger._hist.update(**kwargs)
        return self._time_tagger.histogram()

    def counter_data_readout(self):
        self.data = self.data[1:-1]
        self.data = np.hstack(self.data, np.sum(self.data,axis=1))
        print(self.data)
        self.counter_times = np.linspace(0,self.counter_params['n_values']*self.counter_params['bins_width'], self.counter_params['n_values'])
        self.sigTimeTaggerPlotsUpdated.emit(self.counter_times,self.data)              
    
    def time_differences_data_readout(self):
        self.data=self.time_differences.getData()
        # self.data=np.sum(self.data,axis=1)
        #self.data=np.array(self.data,dtype=object)
        self.time_diff_times = np.linspace(0,self.time_diff_params['n_bins']*self.time_diff_params['binwidth']/1000, self.time_diff_params['n_bins'])
        print(self.data[0])
        print(len(self.data[0]))
        print(self.time_diff_times)
        print(len(self.time_diff_times))
        self.sigTimeTaggerPlotsUpdated.emit(self.time_diff_times,self.data[0])   

    def histogram_data_readout(self):
        self.data=self.histogram.getData()
        self.hist_times = np.linspace(0,self.hist_params['number_of_bins']*self.hist_params['binwidth']/1000, self.hist_params['number_of_bins'])
        self.sigTimeTaggerPlotsUpdated.emit(self.hist_times,self.data)   
    
    def save_histogram_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')

        if tag is None:
            tag = ''

        if len(tag) > 0:
            filelabel_raw = '{0}_cw_ODMR_data_raw'.format(tag)
            filelabel_matrix = '{0}_cw_ODMR_data_matrix'.format(tag)
        else:
            filelabel_raw = '_cw_ODMR_data_raw'
            filelabel_matrix = '_cw_ODMR_data_matrix'
        
        data_raw = OrderedDict()
        data_matrix = OrderedDict()
        data_raw['count data (counts)'] = self.ODMRLogic.data
        data_raw['Frequency (MHz)'] = self.ODMRLogic.mw1_freq
        data_matrix['Frequency (MHz) + Scanline'] = self.ODMRLogic.scanmatrix
        
        parameters = OrderedDict()
        parameters['Enable Microwave1 (bool)'] = self.ODMRLogic.cw_MW1
        parameters['Enable Microwave2 (bool)'] = self.ODMRLogic.cw_MW2
        parameters['Enable Microwave3 (bool)'] = self.ODMRLogic.cw_MW3
        parameters['Microwave1 CW Power (dBm)'] = self.ODMRLogic.cw_MW1_Power
        parameters['Microwave2 CW Power (dBm)'] = self.ODMRLogic.cw_MW2_Power
        parameters['Microwave3 CW Power (dBm)'] = self.ODMRLogic.cw_MW3_Power
        parameters['Microwave1 Start (MHz)'] = self.ODMRLogic.cw_StartFreq
        parameters['Microwave1 Stop (MHz)'] = self.ODMRLogic.cw_StopFreq
        parameters['Microwave1 Stepsize (MHz)'] = self.ODMRLogic.cw_Stepsize
        parameters['Microwave2 CW Power (dBm)'] = self.ODMRLogic.cw_MW2_Freq
        parameters['Microwave3 CW Power (dBm)'] = self.ODMRLogic.cw_MW3_Freq
        parameters['A1 (bool)'] = self.ODMRLogic.cw_A1
        parameters['A2 (bool)'] = self.ODMRLogic.cw_A2
        parameters['Pulsed Repump (bool)'] = self.ODMRLogic.cw_PulsedRepump
        parameters['Pulsed Duration (µs)'] = self.ODMRLogic.cw_RepumpDuration
        parameters['Pulsed Decay (µs)'] = self.ODMRLogic.cw_RepumpDecay
        parameters['CW Repump (bool)'] = self.ODMRLogic.cw_CWRepump
        parameters['Green (bool)'] = self.ODMRLogic.enable_green
        parameters['Seconds per Point (s)'] = self.ODMRLogic.cw_SecondsPerPoint

        fig = self.draw_cw_figure(data_raw['count data (counts)'],data_raw['Frequency (MHz)'],data_matrix['Frequency (MHz) + Scanline'],
                                cbar_range=colorscale_range,
                                percentile_range=percentile_range)

        self._save_logic.save_data(data_matrix,
                                    filepath=filepath,
                                    parameters=parameters,
                                    filelabel=filelabel_matrix,
                                    fmt='%.6e',
                                    delimiter='\t',
                                    timestamp=timestamp)
        
        self._save_logic.save_data(data_raw,
                                    filepath=filepath,
                                    parameters=parameters,
                                    filelabel=filelabel_raw,
                                    fmt='%.6e',
                                    delimiter='\t',
                                    timestamp=timestamp,
                                    plotfig=fig)

        self.log.info('ODMR data saved to:\n{0}'.format(filepath))
        return

    def draw_cw_figure(self, data, frequencies, matrix, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        #key = 'range: {1}'.format(frequencies)
        count_data = data
        freq_data = frequencies
        matrix_data = matrix
        
        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = np.array([np.min(matrix_data), np.max(matrix_data)])
        else:
            cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            #fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'counts)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))
        matrixplot = ax_matrix.imshow(
            matrix_data,
            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
            origin='lower',
            vmin=cbar_range[0],
            vmax=cbar_range[1],
            extent=[np.min(freq_data),
                    np.max(freq_data),
                    0,
                    np.shape(matrix_data)[0]
                    ],
            aspect='auto',
            interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig
           

    def Counter_Button_Clicked(self,on):
        print('done something with cw_Run_Button')
        self.start_counter()
       
    def Histogram_Button_Clicked(self,on):
        print('done something with cw_Run_Button')
        self.start_histogram()
       
    def TimeDiff_Button_Clicked(self,on):
        print('done something with cw_Run_Button')
        self.start_time_differences()()
       
       
    def Stop_Button_Clicked(self,on):
        print('done something with cw_Stop_Button')
        self.start_counter()
        # self.holder.stop_awg()
        # #self.holder.awg.mcas.status = 0
        # self.stoping_time=time.time()
        # self.measurement_running=False
        # self.time_differences.stop()

    def Continue_Button_Clicked(self,on):
        print('done something with cw_Continue_Button')
        self.start_time_differences()
        # self.continuing=True
        # #self.holder.awg.mcas_dict['cwODMR'].run()
        # self.setup_seq()
        # self.starting_time+=time.time()-self.stoping_time
        # self.time_differences = self.holder.setup_time_tagger(n_histograms=self.number_of_points_per_line,
        # binwidth=self.cw_SecondsPerPoint*1e12,
        # n_bins=1
        # )
        # self.time_differences.start()
        # self.measurement_running=True

    def Save_Button_Clicked(self,on):
        # self.holder.save_cw_odmr_data()
        print('done something with cw_Save_Button')

    def Load_Button_Clicked(self,on):
            print('done something with cw_Load_Button')

    def Filename_lineEdit_textEdited(self,text):
        print('done something with cw_Filename_LineEdit. Text=',text)
        try:
                self.Filename=text
        except:
                pass

    def Stoptime_lineEdit_textEdited(self,text):
            print('done something with cw_Stoptime_LineEdit. Text=',text)
            try:
                    self.Stoptime=float(text)
            except:
                    pass

    def Interval_lineEdit_textEdited(self,text):
            print('done something with cw_Interval_LineEdit. Text=',text)
            try:
                    self.Interval=float(text)
            except:
                pass

    def PeriodicSaving_CheckBox_StateChanged(self,on):
        print('done something with cw_PeriodicSaving_CheckBox')
        self.PeriodicSaving=on==2

    def ClickChannel_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.hist_params['click_channel'] = int(text)
            self.time_diff_params['click_channel'] = int(text)
        except:
            print("Could not convert to integer.")
    
    def CounterClickChannel_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.counter_params['click_channel'] = int(text)
        except:
            print("Could not convert to integer.")

    def StartChannel_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.hist_params['start_channel'] = int(text)
        except:
            print("Could not convert to integer.")
    
    def NextChannel_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.time_diff_params['next_channel'] = int(text)
        except:
            print("Could not convert to integer.")
    
    def SyncChannel_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.time_diff_params['sync_channel'] = int(text)
        except:
            print("Could not convert to integer.")

    def Binwidth_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.hist_params['binwidth'] = int(text)
            self.time_diff_params['binwidth'] = int(text)
        except:
            print("Could not convert to integer.")
    
    def CounterBinwidth_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.counter_params['bins_width'] = int(text)
        except:
            print("Could not convert to integer.")

    def Datapoints_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.counter_params['n_values'] = int(text)
        except:
            print("Could not convert to integer.")

    def NumberOfBins_lineEdit_textEdited(self,text):
        print(text)
        try:
            self.hist_params['number_of_bins'] = int(text)
        except:
            print("Could not convert to integer.")

    

from threading import Timer
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False