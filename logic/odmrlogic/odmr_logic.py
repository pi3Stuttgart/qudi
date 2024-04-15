#ODMR-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys
sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved

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
from core.statusvariable import StatusVar
import hardware.Keysight_AWG_M8190.elements as E
#import pandas as pd

class ODMRLogic_holder(GenericLogic):
    #declare connectors
    counter_device = Connector(interface='TimeTaggerInterface')# Savelogic just for testing purposes
    savelogic = Connector(interface='SaveLogic')
    mcas_holder = Connector(interface='McasDictHolderInterface')
    fitlogic = Connector(interface='FitLogic')
    #transition_tracker = Connector(interface="TransitionTracker")
    CHANNEL_APD0 = 0
    CHANNEL_APD1 = 1
    CHANNEL_DETECT = 2
    CHANNEL_SEQUENCE = 3
    

    # time_tagger = counter_device().createTimeTagger()

    # print('time_tagger created')
    # print(time_tagger)
    # time_tagger.setTriggerLevel(0, 1)  #Supra
    # time_tagger.setTriggerLevel(1, 1)  #Supra
    # time_tagger.setTriggerLevel(2, 1)
    # time_tagger.setTriggerLevel(3, 1)
    # time_tagger.setTriggerLevel(4, 1)
    # time_tagger.setTriggerLevel(5, 1)
    # time_tagger.setTriggerLevel(6, 1)
    # time_tagger.setTriggerLevel(7, 1)

    #create the signals:
    sigOdmrPlotsUpdated = QtCore.Signal()
    SigClock= QtCore.Signal()
    SigCheckReady_Beacon = QtCore.Signal()
    sigFitPerformed =  QtCore.Signal(str, str)

    SelectLorentzianFit:bool=False
    SelectGaussianFit:bool=True
    align_mode=False # set to true if we want to align the B field

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Get connectors
        self._time_tagger=self.counter_device()
        self._time_tagger.setup_TT()
        self._save_logic = self.savelogic()
        self._awg = self.mcas_holder()#mcas_dict()
        self._fit_logic = self.fitlogic()
        #self._transition_tracker=self.transition_tracker()
        
        self.stop_awg = self._awg.mcas_dict.stop_awgs
        self.pulsedODMRLogic = pulsedODMRLogic(self)
        self.ODMRLogic = ODMRLogic(self)
        self.Timer = RepeatedTimer(1, self.clock) # this clock is not very precise, maybe the solution proposed on https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds can be helpful.
        #self.SigCheckReady_Beacon.connect(self.print_counter)
        self.CheckReady_Beacon = RepeatedTimer(1, self.CheckReady)
        #self.CheckReady_Beacon.start()

        self.Contrast_Fit: str = ''
        self.Frequencies_Fit: str = ''
        self.Linewidths_Fit: str = ''
        self.NumberOfPeaks: int=1

        self.update_TT: bool = False

        self.x_fit = np.arange(20)
        self.y_fit = np.arange(20)

        return 


    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.
        """
        self.Timer.stop()
        self.CheckReady_Beacon.stop()
        self.stop_awg()
        try: #checkready_beacon may not be launched
            self.checkready.stop()
        except:
            pass
        
        del self.ODMRLogic
        del self.pulsedODMRLogic
        return 
    
    def clock(self):
        self.SigClock.emit()

    def CheckReady(self):
        self.SigCheckReady_Beacon.emit()

    def setup_time_tagger(self,**kwargs):
        self._time_tagger._time_diff.update(**kwargs)
        return self._time_tagger.time_differences()

    def save_cw_odmr_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""

        if tag is None:
            tag = ''

        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        timestamp = datetime.datetime.now()
        

        if len(tag) > 0:
            filelabel_raw = '{0}_cw_ODMR_raw'.format(tag)
            filelabel_matrix = '{0}_cw_ODMR_matrix'.format(tag)
        else:
            filelabel_raw = '_cw_ODMR_raw'
            filelabel_matrix = '_cw_ODMR_matrix'
        
        # prepare the data in a dict or in an OrderedDict:
        data_raw = OrderedDict()
        data_matrix = OrderedDict()
        data_raw['count data (counts)'] = self.ODMRLogic.data
        data_raw['Frequency (MHz)'] = self.ODMRLogic.mw1_freq
        data_matrix['Frequency (MHz) + Scanline'] = self.ODMRLogic.scanmatrix
        
        parameters = OrderedDict()
        parameters['runtime (s)'] = self.ODMRLogic.current_runtime
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
        parameters['Contrast'] = self.Contrast_Fit
        parameters['Frequencies (MHz)'] = self.Frequencies_Fit
        parameters['Linewidths (kHz)'] = self.Linewidths_Fit

        fig = self.draw_cw_figure(
            data_raw['count data (counts)'],
            data_raw['Frequency (MHz)'],
            data_matrix['Frequency (MHz) + Scanline'],
            self.ODMRLogic.x_fit,
            self.ODMRLogic.y_fit,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        self._save_logic.save_data(
            data_matrix,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel_matrix,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )
        
        self._save_logic.save_data(
            data_raw,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel_raw,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig
        )
        self.log.info('ODMR data saved to:\n{0}'.format(filepath))
        return 0

    def save_pulsed_odmr_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')

        if tag is None:
            tag = ''

        if len(tag) > 0:
            filelabel_raw = '{0}_pulsed_ODMR_raw'.format(tag)
            filelabel_detection = '{0}_pulsed_ODMR_detection'.format(tag)
            filelabel_matrix = '{0}_pulsed_ODMR_matrix'.format(tag)
        else:
            filelabel_raw = '_pulsed_ODMR_raw'
            filelabel_detection = '_pulsed_ODMR_detection'
            filelabel_matrix = '_pulsed_ODMR_matrix'
            
        data_raw = OrderedDict()
        data_detection = OrderedDict()
        data_matrix = OrderedDict()
        data_raw['count data (counts)'] = self.pulsedODMRLogic.data
        data_raw['Frequency (MHz)'] = self.pulsedODMRLogic.mw1_freq
        data_detection['Detection Time (ns)'] = self.pulsedODMRLogic.indexes/1e3 #save data in [ns]
        data_detection['Detection Counts (counts)'] = self.pulsedODMRLogic.data_detect
        data_matrix['Frequency (MHz) + Scanline'] = self.pulsedODMRLogic.scanmatrix

        parameters = OrderedDict()
        parameters['runtime (s)'] = self.pulsedODMRLogic.current_runtime
        parameters['Enable Microwave1 (bool)'] = self.pulsedODMRLogic.pulsed_MW1
        parameters['Enable Microwave2 (bool)'] = self.pulsedODMRLogic.pulsed_MW2
        parameters['Enable Microwave3 (bool)'] = self.pulsedODMRLogic.pulsed_MW3
        parameters['Microwave1 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW1_Power
        parameters['Microwave2 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW2_Power
        parameters['Microwave3 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW3_Power
        parameters['Microwave1 Start (MHz)'] = self.pulsedODMRLogic.pulsed_StartFreq
        parameters['Microwave1 Stop (MHz)'] = self.pulsedODMRLogic.pulsed_StopFreq
        parameters['Microwave1 Stepsize (MHz)'] = self.pulsedODMRLogic.pulsed_Stepsize
        parameters['Microwave2 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW2_Freq
        parameters['Microwave3 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW3_Freq
        parameters['Pi Pulse Duration (ns)'] = self.pulsedODMRLogic.pulsed_piPulseDuration
        parameters['Pi Pulse Decay (ns)'] = self.pulsedODMRLogic.pulsed_PiDecay
        parameters['A1 (bool)'] = self.pulsedODMRLogic.pulsed_A1
        parameters['A2 (bool)'] = self.pulsedODMRLogic.pulsed_A2
        parameters['Pulsed Repump (bool)'] = self.pulsedODMRLogic.pulsed_PulsedRepump
        parameters['Pulsed Duration (µs)'] = self.pulsedODMRLogic.pulsed_RepumpDuration
        parameters['Pulsed Decay (µs)'] = self.pulsedODMRLogic.pulsed_RepumpDecay
        parameters['CW Repump (bool)'] = self.pulsedODMRLogic.pulsed_CWRepump
        parameters['Init Time (µs)'] = self.pulsedODMRLogic.pulsed_InitTime
        parameters['Init Decay (µs)'] = self.pulsedODMRLogic.pulsed_DecayInit
        parameters['Readout Time (µs)'] = self.pulsedODMRLogic.pulsed_ReadoutTime
        parameters['Readout Decay (µs)'] = self.pulsedODMRLogic.pulsed_ReadoutDecay
        parameters['Readout via A1 (bool)'] = self.pulsedODMRLogic.pulsed_A1Readout
        parameters['Readout via A2 (bool)'] = self.pulsedODMRLogic.pulsed_A2Readout
        parameters['AOM Delay (ns)'] = self.pulsedODMRLogic.pulsed_AOMDelay
        parameters['Binning (s)'] = self.pulsedODMRLogic.pulsed_Binning
        parameters['Contrast'] = self.Contrast_Fit
        parameters['Frequencies (MHz)'] = self.Frequencies_Fit
        parameters['Linewidths (kHz)'] = self.Linewidths_Fit
        
        fig = self.draw_pulsed_figure(
            data_raw['Frequency (MHz)'],
            data_raw['count data (counts)'],
            data_matrix['Frequency (MHz) + Scanline'],
            data_detection['Detection Time (ns)'],
            data_detection['Detection Counts (counts)'],
            self.pulsedODMRLogic.x_fit,
            self.pulsedODMRLogic.y_fit,
            cbar_range=colorscale_range,
            percentile_range=percentile_range
        )

        self._save_logic.save_data(
            data_matrix,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel_matrix,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )
        
        self._save_logic.save_data(
            data_detection,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel_detection,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )
        
        self._save_logic.save_data(
            data_raw,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel_raw,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig
        )

        self.log.info('ODMR data saved to:\n{0}'.format(filepath))
        return

    def draw_cw_figure(self, count_data, freq_data, matrix_data, fit_freq_vals, fit_count_vals,cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        fit_freq_vals = fit_freq_vals/1e6
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
            fit_count_vals = fit_count_vals / 1000
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
        self.fig, (self.ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)
        self.ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            self.ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')
            # self.ax_mean.plot(fit_freq_vals/10**(3*prefix_index), fit_count_vals, marker='None')
            
    
        self.ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'counts)')
        self.ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

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
        self.fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = self.fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = self.fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'counts)')

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

        return self.fig

    def draw_pulsed_figure(self, freq_data, count_data, matrix_data, detection_time, detection_counts, fit_freq_vals, fit_count_vals, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        #key = 'range: {1}'.format(frequencies)
        fit_freq_vals = fit_freq_vals/1e6
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
            fit_count_vals = fit_count_vals / 1000
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
        fig, (ax_mean, ax_matrix, ax_detection) = plt.subplots(nrows=3, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            #ax_mean.plot(fit_freq_vals/10**(3*prefix_index), fit_count_vals, marker='None')
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')
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

        ax_detection.plot(detection_time, detection_counts, linestyle=':', linewidth=0.5)
        ax_detection.set_ylabel('Fluorescence (' + counts_prefix + 'counts)')
        ax_detection.set_xlim(np.min(detection_time), np.max(detection_time))

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


##############################################################
# Stuff for Fitting
#         
    def do_fit(self,x_data, y_data):
        self.interplolated_x_data=np.linspace(x_data.min(),x_data.max(),len(x_data)*5)

        if self.pulsedODMRLogic.measurement_running and self.NumberOfPeaks > 2:
            error_text=f"Too many peaks to fit. Wait until measurement has finished to fit more than two peaks."
            logger.error(error_text)
            self.NumberOfPeaks = 2
            raise Warning(error_text)
        if self.SelectGaussianFit:
            self.fit_func=self._fit_logic.make_n_gauss_function_with_offset(self.NumberOfPeaks)
        elif self.SelectLorentzianFit:
            self.fit_func=self._fit_logic.make_n_lorentz_function_with_offset(self.NumberOfPeaks)
        # x_data=x_data.astype(np.float)
        # y_data=y_data.astype(np.float)
        # if self.NumberOfPeaks==1:
        #     model,params=self._fit_logic.make_gaussian_model()

        #     result = self._fit_logic.make_gaussian_fit(
        #                         x_axis=x_data,
        #                         data=y_data,
        #                         units='Hz',
        #                         estimator=self._fit_logic.estimate_gaussian_peak
        #                         )

        # elif self.NumberOfPeaks==2:
        #     model,params=self._fit_logic.make_gaussiandouble_model()

        #     result = self._fit_logic.make_gaussiandouble_fit(
        #                         x_axis=x_data,
        #                         data=y_data,
        #                         units='Hz',
        #                         estimator=self._fit_logic.estimate_gaussiandouble_peak
        #                         )
                                
        # elif self.NumberOfPeaks==3:
        #     model,params=self._fit_logic.make_gaussiantriple_model()

        #     result = self._fit_logic.make_gaussiantriple_fit(
        #                         x_axis=x_data,
        #                         data=y_data,
        #                         units='Hz',
        #                         estimator=self._fit_logic.estimate_gaussiantriple_peak
        #                         )


        #     logger.warning("function 3 gaussian peaks not implemeted")


        # #print(x_data.min(),x_data.max(),len(x_data)*10)
            
            # self.fit_data = model.eval(x=self.interplolated_x_data, params=result.params)


            #using own fitlogic
            
        self.fit_result=self.fit_func.fit(x_data,y_data)
        self.fit_data=self.fit_func(self.interplolated_x_data,*self.fit_result["result"].x)
        
        self.Contrast_Fit: str=''
        self.Frequencies_Fit: str=''
        self.Linewidths_Fit: str=''

        # for i in range(self.NumberOfPeaks):
        #     try:
        #         self.Contrast_Fit=self.Contrast_Fit+str(round(result.params[("g"+str(i)+"_")*(self.NumberOfPeaks!=1)+"amplitude"].value,2))+"; " # because 1 peak and 2 peak gaussian fit dont give the same result keywords, we add the 'gi_' part (missing in the 1 peak case) by multiplying the string by 1 if paeks!=1 and remove it if peaks=1.
        #         self.Frequencies_Fit=self.Frequencies_Fit+str(round(result.params[("g"+str(i)+"_")*(self.NumberOfPeaks!=1)+"center"].value/1e6,2))+"; "
        #         self.Linewidths_Fit=self.Linewidths_Fit+str(round(result.params[("g"+str(i)+"_")*(self.NumberOfPeaks!=1)+"fwhm"].value/1e3,2))+"; " #TODO convert linewidth from V to MHz
        #     except Exception as e:
        #         print("an error occured:\n", e)

        for i in range(self.NumberOfPeaks):
            try:
                self.Contrast_Fit=self.Contrast_Fit+str(round(self.fit_result[("ampl_"+str(i))],2))+"; " # because 1 peak and 2 peak gaussian fit dont give the same self.fit_result keywords, we add the 'gi_' part (missing in the 1 peak case) by multiplying the string by 1 if paeks!=1 and remove it if peaks=1.
                self.Frequencies_Fit=self.Frequencies_Fit+str(round(self.fit_result[("mu_"+str(i))],2))+"; "
                self.Linewidths_Fit=self.Linewidths_Fit+str(round(self.fit_result[("gam_"+str(i))],2))+"; " 
            except Exception as e:
                print("an error occured:\n", e)
        if self.update_TT:
            print("emit to TT")
            self.sigFitPerformed.emit(self.Frequencies_Fit, self.pulsedODMRLogic.CallerTag)
        return self.interplolated_x_data,self.fit_data,self.fit_result
  

class ODMRLogic(cw_default):
    def __init__(self,holder):
        self.now = time.time()
        self.measurement_running=False
        self.holder=holder
        #self.counter=self.holder._time_tagger.counter()
        self.time_differences = self.holder._time_tagger.time_differences()
        self.number_of_points_per_line=self.holder._time_tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.cw_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.holder.SigCheckReady_Beacon.connect(self.data_readout,type=QtCore.Qt.QueuedConnection)
        self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
        self.syncing=False
        self.cw_odmr_refocus_running=False

        self.continuing=False

        self.x_fit = np.arange(20)
        self.y_fit = np.arange(20)

        self.starting_time=0

        # Counter that counts how often the histogram indef of the Time Differences measurement was reset to 0. It should correlate with the number of scanned lines 
        # and is reset at the beginning of a scan
        self.histogram_rollover = 0

    def data_readout(self):
        #print("dur ", time.time()-self.now)
        self.current_runtime = time.time()-self.starting_time
        if (self.current_runtime>self.cw_Stoptime and self.cw_Stoptime!=0) and self.measurement_running:
            self.cw_Stop_Button_Clicked(True)
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running or self.syncing):
            #if not(self.syncing):
                return

        if self.continuing:
            self.ancient_data=self.time_differences_cw.getData()
            self.continuing=False
            
        # else:
        #     data=self.time_differences.getData().flatten()
        #     self.ancient_data=data+self.ancient_data

        #     self.scanmatrix = np.vstack(
        #         (data, self.scanmatrix[:-1, :])
        #     )
        #     self.data += data

        #     self.holder.sigOdmrPlotsUpdated.emit()

        else:
            ## Checks if the histogram index was reset (i.e. if a full ODMR line was measured in the time tagger)
            rollover_recent = self.time_differences.getCounts()
            if rollover_recent == self.histogram_rollover:
                return
            
            #print(self.time_differences.getCounts())  ## Test print of the read out rollover number: If printed it should go up in steps of one
            
            self.histogram_rollover +=1
            data=self.time_differences.getData()-self.ancient_data
            data=np.array(data,dtype=object)           
            self.ancient_data += data          # update already recorded data
            data=np.sum(data,axis=1)           # because data initially is a list of lists. something like [[432],[444],[123],[432],[542]]
            
            try:
                if self.scanmatrix.shape[0]< self.cw_NumberOfLines:
                    add=np.zeros((int(self.cw_NumberOfLines-self.scanmatrix.shape[0]),self.scanmatrix.shape[1]))
                    self.scanmatrix=np.vstack((self.scanmatrix,add))
                elif self.scanmatrix.shape[0]> self.cw_NumberOfLines and self.cw_NumberOfLines!=0:
                    self.scanmatrix=self.scanmatrix[:int(self.cw_NumberOfLines)]
            except:
                print("Wrong input :(, try again.")

            self.scanmatrix[1:]=self.scanmatrix[0:-1]
            self.scanmatrix[0]=data
            self.data=self.data+data
            self.holder.sigOdmrPlotsUpdated.emit()
           
                
            


    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / self.holder._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude
    
    def setup_seq(
        self,
        cw_MW1=None,
        cw_MW2=None,
        cw_MW3=None,
        cw_StartFreq=None,
        cw_StopFreq=None,
        cw_Stepsize=None,
        cw_MW2_Freq=None,
        cw_MW3_Freq=None,
        cw_MW1_Power=None,
        cw_MW2_Power=None,
        cw_MW3_Power=None,

        cw_A1=None,
        cw_A2=None,
        cw_PulsedRepump=None,
        cw_RepumpDuration = None, 
        cw_RepumpDecay = None, 
        cw_CWRepump=None,
        enable_green=False,
        cw_SecondsPerPoint=None,
        cw_segment_length = None
        ):
        print("ODMR CW SETUP SEQ STARTED")

        sig=inspect.signature(self.setup_seq)
        for parameter in sig.parameters.keys():
            #print(parameter)
            if locals()[parameter]!=None:
                exec(f"self.{parameter}={parameter}")
                #print(parameter)
                #exec(f'print(self.{parameter})')

        #calculate the number of repetitions such that the sequence remains on one frequence for "secondsperpoint". One Segment is 1µs by default (this can be changed).
        #self.loop_count = int(self.cw_SecondsPerPoint/(50e-6))

        # Rollover index has to be reset to 1 at beginnign of the scan
        self.histogram_rollover = 0

        self.loop_count = int((self.cw_SecondsPerPoint*1e6)/self.cw_segment_length) #great numbers (~8000) will probably result in too long writing time.
        #print("loop_count= ",self.loop_count)   
        if self.loop_count > 2000:
            error_text=f"Too many loop counts in sequence (N={self.loop_count}). Choose shorter seconds per point, or increase segment_length."
            logger.error(error_text)
            raise Exception(error_text)
        #sequence length can be increased by longer segment duration
        
        # Setup list of all frequencies which the sequence should output.
        self.mw1_freq = np.arange(self.cw_StartFreq,self.cw_StopFreq+self.cw_Stepsize,self.cw_Stepsize)

        if len(self.mw1_freq)>400:
            error_text=f"More than 400 freqs to upload, if you want to continue please uncomment me in ODMR_logic. Otherwise MCAS will be killed because the sequence is too long."
            logger.error(error_text)
            raise Warning(error_text)
            
        #setting up the measurement data
        self.number_of_points_per_line=len(self.mw1_freq)


        self.time_differences = self.holder.setup_time_tagger(
            #tagger = self.holder._time_tagger,
            click_channel=1,
            start_channel=12, #negative slope of channel 4
            next_channel=4, 
            sync_channel=7,
            #binwidth=int(self.cw_SecondsPerPoint*1e12),
            binwidth=int(self.cw_SecondsPerPoint*1e12),
            n_bins=1,
            n_histograms=self.number_of_points_per_line,
        )

        # Setup list which contains the mw-powers of all the active microwaves
        self.power = []
        if self.cw_MW1:
            self.power += [self.cw_MW1_Power]
        if self.cw_MW2:
            self.power += [self.cw_MW2_Power]
        if self.cw_MW3:
            self.power += [self.cw_MW3_Power]

        self.power = np.asarray(self.power)
        self.power=self.power_to_amp(self.power)
        print(self.power)
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
            
        # generate a single MW sequence with the needed mw frequencies and play is continuously until the measurement is stopped,
        # either by the stop button, the runtime, or number of sequence repetitions. 

        seq = self.holder._awg.mcas(name="cwODMR", ch_dict={"2g": [1,2],"ps": [1]})

        # generate segment of repump which starts at each repetition of the sequence.
        seq.start_new_segment("Start")
        if self.cw_PulsedRepump:
            seq.asc(name='repump1', length_mus=E.round_length_mus_to_x_multiple_ps(self.cw_RepumpDuration), repump=True)
            seq.asc(name='repump2', length_mus=E.round_length_mus_to_x_multiple_ps(self.cw_RepumpDecay), repump=False)


        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        #seq.asc(name='tt_sync1', length_mus=E.round_length_mus_to_x_multiple_ps(0.064), memory=True)        
        #seq.asc(name='tt_sync3', length_mus=E.round_length_mus_to_x_multiple_ps(0.064)) 
        #seq.asc(name='tt_sync2', length_mus=E.round_length_mus_to_x_multiple_ps(0.064), gate=True)        
        #seq.asc(name='tt_sync3', length_mus=E.round_length_mus_to_x_multiple_ps(0.064), gate=False) 
        # generate multiple segments, each containing one of the microwave frequencies. Length of each segment is determined by the loop-count.      
        #seq.start_new_segment("Microwaves")


        for freq, self.cw_MW2_Frequency,self.cw_MW3_Frequency  in zip(self.mw1_freq, [self.cw_MW2_Freq]*len(self.mw1_freq), [self.cw_MW3_Freq]*len(self.mw1_freq)):
            frequencies=np.array([freq, self.cw_MW2_Frequency,self.cw_MW3_Frequency])[[self.cw_MW1,self.cw_MW2,self.cw_MW3]]
            #print([freq, self.cw_MW2_Frequency,self.cw_MW3_Frequency])
            #print([self.cw_MW1,self.cw_MW2,self.cw_MW3])
            #seq.start_new_segment("Microwaves"+str(frequencies))
            #turn off tt_trigger to increment the histogram-index of TimeTagger
            #seq.start_new_segment("MW_readout"+str(frequencies))
            seq.start_new_segment("Next click"+str(frequencies),loop_count=1)
            seq.asc(name="MW_readout"+str(frequencies)[:32],pd2g1 = {"type":"sine", "frequencies":frequencies, "amplitudes":self.power},
                gate = True,
                length_mus=E.round_length_mus_to_x_multiple_ps(0.064)
                ) 
            seq.start_new_segment("Start Click"+str(frequencies),loop_count=int(self.cw_SecondsPerPoint*1e6/50))
            seq.asc(name="MW_readout"+str(frequencies)[:32],pd2g1 = {"type":"sine", "frequencies":frequencies, "amplitudes":self.power},
                A1=self.cw_A1,
                A2=self.cw_A2,
                gateMW=True,
                repump=self.cw_CWRepump,
                green=enable_green,
                gate = False,
                length_mus=E.round_length_mus_to_x_multiple_ps(50)
                )  
            

        seq.start_new_segment("Sequence call",loop_count=1)
        seq.asc(name='tt_sync1', length_mus=E.round_length_mus_to_x_multiple_ps(0.064), 
                A1=self.cw_A1,
                A2=self.cw_A2,
                gateMW=True,
                repump=self.cw_CWRepump,
                green=enable_green,
                gate = False,
                memory=True,
                )  

        seq.start_new_segment("Waiting for Readout, rollover",loop_count=int(self.cw_SecondsPerPoint*1e6*(self.number_of_points_per_line/2)/50))
        seq.asc(name="MW_readout"+str(frequencies)[:32],pd2g1 = {"type":"sine", "frequencies":frequencies, "amplitudes":self.power},
            A1=self.cw_A1,
            A2=self.cw_A2,
            gateMW=True,
            repump=self.cw_CWRepump,
            green=enable_green,
            gate = False,
            memory = False,
            length_mus=E.round_length_mus_to_x_multiple_ps(50)
            ) 

          

        #self.holder._awg.mcas.status = 1
        self.holder._awg.mcas_dict.stop_awgs()
        self.holder._awg.mcas_dict['cwODMR'] = seq
        #self.holder._awg.mcas_dict.print_info()
        self.holder._awg.mcas_dict['cwODMR'].run()        
        print("running sequence cwODMR")

        self.holder.CheckReady_Beacon = RepeatedTimer(0.01, self.holder.CheckReady)
                

class pulsedODMRLogic(pulsed_default):
    def __init__(self,holder):
        self.measurement_running=False
        self.holder=holder
        #self.counter=self.holder._time_tagger.counter()
        self.time_differences = self.holder._time_tagger.time_differences()
        self.number_of_points_per_line=self.holder._time_tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.pulsed_NumberOfLines,self.number_of_points_per_line))
        self.holder.SigCheckReady_Beacon.connect(self.data_readout, type=QtCore.Qt.QueuedConnection)
        self.data=0
        self.data_detect=0
        self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
        self.syncing=False

        self.repet_list1=[]
        self.cter1=1
        self.c1=0
        self.ancient_index=0
        self.continuing=False # variable to discard first getdata after pressing continue.
        self.pulsed_odmr_refocus_running=False


        self.x_fit = np.arange(20)
        self.y_fit = np.arange(20)
        self.starting_time=0

    def data_readout(self):
        self.current_runtime = time.time()-self.starting_time
        if (self.current_runtime>self.pulsed_Stoptime and self.pulsed_Stoptime!=0) and self.measurement_running:
            self.holder.update_TT = True
            self.holder.sigOdmrPlotsUpdated.emit()
            self.pulsed_Stop_Button_Clicked(True)
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running or self.syncing):
                return


        if self.continuing:
            self.ancient_data=self.time_differences.getData()
            self.continuing=False
            
        else:
            data=self.time_differences.getData()-self.ancient_data
            self.indexes=np.array(self.time_differences.getIndex())
            #print(data)
            data=np.array(data,dtype=object)
            self.ancient_data=data+self.ancient_data
            data_detect=np.sum(data,axis=0)
            data=np.sum(data,axis=1)
            # if the number of lines has changed
            try:
                if self.scanmatrix.shape[0]< self.pulsed_NumberOfLines:
                    add=np.zeros((int(self.pulsed_NumberOfLines-self.scanmatrix.shape[0]),self.scanmatrix.shape[1]))
                    self.scanmatrix=np.vstack((self.scanmatrix,add))
                elif self.scanmatrix.shape[0]> self.pulsed_NumberOfLines and self.pulsed_NumberOfLines!=0:
                    self.scanmatrix=self.scanmatrix[:int(self.pulsed_NumberOfLines)]
            except:
                print("Wrong input :(, try again.")

            self.scanmatrix[1:]=self.scanmatrix[0:-1]
            self.scanmatrix[0]=data
            self.data=self.data+data
            self.data_detect=self.data_detect+data_detect
        
        self.holder.sigOdmrPlotsUpdated.emit()
            
       
    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / self.holder._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude
        


    def setup_seq(
        self,
        pulsed_MW1=None,
        pulsed_MW2=None,
        pulsed_MW3=None,
        pulsed_StartFreq=None,
        pulsed_StopFreq=None,
        pulsed_Stepsize=None,
        pulsed_MW2_Freq=None,
        pulsed_MW3_Freq=None,
        pulsed_MW1_Power=None,
        pulsed_MW2_Power=None,
        pulsed_MW3_Power=None,
        pulsed_piPulseDuration=None,
        pulsed_PiDecay=None,
        pulsed_A1=None,
        pulsed_A2=None,
        pulsed_PulsedRepump=None,
        pulsed_RepumpDuration = None, 
        pulsed_RepumpDecay = None, 
        pulsed_CWRepump=None,
        enable_green=False,
        pulsed_AOMDelay = None,
        pulsed_InitTime = None,
        pulsed_DecayInit = None,
        pulsed_ReadoutTime = None,
        pulsed_ReadoutDecay = None,
        pulsed_A1Readout = None,
        pulsed_A2Readout = None,
        pulsed_Binning = None
        ):
        gateMW_dur = 0.256
        self.round_to = 16
        sig=inspect.signature(self.setup_seq)
        for parameter in sig.parameters.keys():
            #print(parameter)
            if locals()[parameter]!=None:
                exec(f"self.{parameter}={parameter}")
                #print(parameter)
                #exec(f'print(self.{parameter})')

        # Setup list of all frequencies which the sequence should output.
        self.mw1_freq = np.arange(self.pulsed_StartFreq,self.pulsed_StopFreq+self.pulsed_Stepsize,self.pulsed_Stepsize)

        #setting up the measurement data
        self.number_of_points_per_line=len(self.mw1_freq)

        self.time_differences.stop()
        time.sleep(0.02) #maybe the timetagger would get too much commands at the same time

        self.time_differences=self.holder.setup_time_tagger(n_histograms=self.number_of_points_per_line,
            binwidth=int(self.pulsed_Binning*1000), #pulsed_Binning input is in ns.
            n_bins=int(self.pulsed_ReadoutTime*1e6/(self.pulsed_Binning*1000))
        )

        self.power = []
        if self.pulsed_MW2:
            self.power += [self.pulsed_MW2_Power]
        if self.pulsed_MW3:
            self.power += [self.pulsed_MW3_Power]
        
        self.power = np.asarray(self.power)
        self.power=self.power_to_amp(self.power)
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
        
        seq = self.holder._awg.mcas(name="pulsedODMR", ch_dict={"2g": [1,2],"ps": [1]})
        # generate segment of repump which starts at each repetition of the sequence.
        # if self.pulsed_PulsedRepump:
        #     seq.start_new_segment("Repump")
        #     seq.asc(name='repump1', length_mus=self.pulsed_RepumpDuration, repump=True)
        #     seq.asc(name='repump2', length_mus=self.pulsed_RepumpDecay, repump=False)

        
        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        seq.start_new_segment("SYNCING")
        seq.asc(name='tt_sync1', length_mus=E.round_length_mus_to_x_multiple_ps(0.016, self.round_to), memory=True)        
        seq.asc(name='tt_sync2', length_mus=E.round_length_mus_to_x_multiple_ps(0.016, self.round_to), gate=True)

        freq_init = np.array([self.pulsed_MW2_Freq, self.pulsed_MW3_Freq])[[self.pulsed_MW2, self.pulsed_MW3]]
        power_init = self.power_to_amp(np.array([self.pulsed_MW2_Power, self.pulsed_MW3_Power])[[self.pulsed_MW2, self.pulsed_MW3]])
        
        for freq in self.mw1_freq:
            if self.pulsed_PulsedRepump:
                seq.start_new_segment("Repump")
                seq.asc(name='repump1', length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_RepumpDuration, self.round_to), repump=True)
                seq.start_new_segment("Repump_decay")
                if (self.pulsed_RepumpDecay - gateMW_dur)> 0: pulsed_RepumpDecay = self.pulsed_RepumpDecay - gateMW_dur
                else: pulsed_RepumpDecay = self.pulsed_RepumpDecay
                seq.asc(name='repump2', length_mus=E.round_length_mus_to_x_multiple_ps(pulsed_RepumpDecay, self.round_to), repump=False)
            
            seq.start_new_segment("Init")
            if (self.pulsed_DecayInit - gateMW_dur)> 0: pulsed_DecayInit = self.pulsed_DecayInit - gateMW_dur
            else: pulsed_DecayInit = self.pulsed_DecayInit
                
            if self.pulsed_CWRepump and (self.pulsed_MW2 or self.pulsed_MW3) and not (self.pulsed_A1 or self.pulsed_A2):
                seq.asc(name='gateMW', length_mus=gateMW_dur, gateMW=True)
                seq.asc(name="init_sine"+str(freq),pd2g1 = {"type":"sine", "frequencies":freq_init, "amplitudes":power_init},
                        gateMW = True,
                        repump = self.pulsed_CWRepump,
                        A1=self.pulsed_A1,
                        A2=self.pulsed_A2,
                        length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_InitTime, self.round_to)
                        )  
                seq.asc(name='Init_decay'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(pulsed_DecayInit,self.round_to), A1=False, A2=False)
            
            elif self.pulsed_CWRepump and not (self.pulsed_A1 or self.pulsed_A2):
                seq.asc(name='init_no_sine',
                        repump = self.pulsed_CWRepump,
                        A1=self.pulsed_A1,
                        A2=self.pulsed_A2,
                        length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_InitTime, self.round_to)
                        )  
                seq.asc(name='Init_decay'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(pulsed_DecayInit,self.round_to), A1=False, A2=False)
            
            elif (self.pulsed_A1 or self.pulsed_A2) and (self.pulsed_MW2 or self.pulsed_MW3):
                seq.asc(name='gateMW', length_mus=E.round_length_mus_to_x_multiple_ps(gateMW_dur, self.round_to), gateMW=True)
                seq.asc(name="init_sine"+str(freq),pd2g1 = {"type":"sine", "frequencies":freq_init, "amplitudes":power_init},
                        gateMW = True,
                        repump = self.pulsed_CWRepump,
                        A1=self.pulsed_A1,
                        A2=self.pulsed_A2,
                        length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_InitTime, self.round_to)
                        )  
                seq.asc(name='Init_decay'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(pulsed_DecayInit, self.round_to), A1=False, A2=False)
            elif self.pulsed_A1 or self.pulsed_A2:
                seq.asc(name='init_no_sine',
                        repump = self.pulsed_CWRepump,
                        A1=self.pulsed_A1,
                        A2=self.pulsed_A2,
                        length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_InitTime, self.round_to)
                        )  
                seq.asc(name='Init_decay'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(pulsed_DecayInit, self.round_to), A1=False, A2=False)
            else:
                logger.warning("No Laser assigned for Init Sequence.")
            seq.start_new_segment("Pi_pulse")
            seq.asc(name='gateMW', length_mus=E.round_length_mus_to_x_multiple_ps(gateMW_dur,self.round_to), gateMW=True)
            seq.asc(name="Pi_pulse"+str(freq),pd2g1 = {"type":"sine", "frequencies":[freq], "amplitudes":self.power_to_amp(self.pulsed_MW1_Power)},gateMW = True,
                length_mus = E.round_length_mus_to_x_multiple_ps(self.pulsed_piPulseDuration/1000, self.round_to), #self.pulsed_piPulseDuration is divided by 1000 to be in µs
                )
            
            if self.pulsed_MW4 or self.pulsed_MW5:
                freqs=np.asarray([self.pulsed_MW4_Freq,self.pulsed_MW5_Freq])[[self.pulsed_MW4 , self.pulsed_MW5]]
                powers=self.power_to_amp([self.pulsed_MW4_Power,self.pulsed_MW5_Power])[[self.pulsed_MW4 , self.pulsed_MW5]]

                seq.asc(name="flip",pd2g1 = {"type":"sine", "frequencies":freqs, "amplitudes":powers}, gateMW=True,
                        length_mus=E.round_length_mus_to_x_multiple_ps(min(self.pulsed_MW4_piPulseDuration,self.pulsed_MW5_piPulseDuration)/1000, self.round_to)
                        )
                if self.pulsed_MW4_piPulseDuration!=self.pulsed_MW5_piPulseDuration:
                    freqs=np.asarray([self.pulsed_MW4_Freq,self.pulsed_MW5_Freq])[[self.pulsed_MW4 and self.pulsed_MW4_piPulseDuration>self.pulsed_MW5_piPulseDuration, self.pulsed_MW5 and self.pulsed_MW4_piPulseDuration<self.pulsed_MW5_piPulseDuration]]
                    powers=self.power_to_amp([self.pulsed_MW4_Power,self.pulsed_MW5_Power])[[self.pulsed_MW4 and self.pulsed_MW4_piPulseDuration>self.pulsed_MW5_piPulseDuration, self.pulsed_MW5 and self.pulsed_MW4_piPulseDuration<self.pulsed_MW5_piPulseDuration]]

                    seq.asc(name="flip",pd2g1 = {"type":"sine", "frequencies":freqs,"amplitudes":powers}, gateMW=True,
                            length_mus=E.round_length_mus_to_x_multiple_ps(abs(self.pulsed_MW4_piPulseDuration-self.pulsed_MW5_piPulseDuration)/1000, self.round_to)
                            ) 
                    
            seq.asc(name='pi_pulse_decay'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_PiDecay/1000, self.round_to), A1=False, A2=False) #self.pulsed_PiDecay is divided by 1000 to be in µs

            seq.start_new_segment("Readout")
            seq.asc(name='readout'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_ReadoutTime, self.round_to), A1=self.pulsed_A1Readout, A2=self.pulsed_A2Readout, repump = self.pulsed_CWRepump, gate=True)
            seq.asc(name='readout_decay'+str(freq), length_mus=E.round_length_mus_to_x_multiple_ps(self.pulsed_ReadoutDecay, self.round_to), A1=False, A2=False, gate=True)

        #self.holder.awg.mcas.status = 1
        self.holder._awg.mcas_dict.stop_awgs()
        self.holder._awg.mcas_dict['pulsedODMR'] = seq
        self.holder._awg.mcas_dict.print_info()
        self.holder._awg.mcas_dict['pulsedODMR'].run()
        print("running sequence pulsedODMR")



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