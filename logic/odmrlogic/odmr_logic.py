#ODMR-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys
sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved

from core.module import Base
from core.connector import Connector
<<<<<<< Updated upstream
from hardware.swabian_instruments.timetagger import TT as TimeTagger
=======
#from hardware.swabian_instruments.timetagger import TT as TimeTagger
>>>>>>> Stashed changes
from logic.generic_logic import GenericLogic
#import hardware.Keysight_AWG_M8190.pyarbtools_master.pyarbtools as pyarbtools

from qtpy import QtCore
from logic.odmrlogic.cw_ODMR_default_values_and_widget_functions import cw_ODMR_default_values_and_widget_functions as cw_default
from logic.odmrlogic.pulsed_ODMR_default_values_and_widget_functions import pulsed_ODMR_default_values_and_widget_functions as pulsed_default

import inspect
import logging
logger = logging.getLogger(__name__)
import time
<<<<<<< Updated upstream
import pandas as pd
=======
import datetime
from collections import OrderedDict
import matplotlib.pyplot as plt
#import pandas as pd
>>>>>>> Stashed changes

class ODMRLogic_holder(GenericLogic):
    #declare connectors
    counter_device = Connector(interface='TimeTaggerInterface')# Savelogic just for testing purposes
    savelogic = Connector(interface='SaveLogic')
    mcas_holder = Connector(interface='McasDictHolderInterface')

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
    sigOdmrPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    SigClock= QtCore.Signal()
    SigCheckReady_Beacon = QtCore.Signal()

    def on_activate(self):
<<<<<<< Updated upstream
        self.Time_Tagger=self.counter_device()
        self.Time_Tagger.setup_TT()
        self.pulsedODMRLogic = pulsedODMRLogic(self)
        self.ODMRLogic = ODMRLogic(self)
        self.awg = self.mcas_holder()#mcas_dict()
        self.stop_awg = self.awg.mcas_dict.stop_awgs
=======
        """
        Initialisation performed during activation of the module.
        """
        # Get connectors
        self._time_tagger=self.counter_device()
        self._time_tagger.setup_TT()
        self._save_logic = self.savelogic()
        self._awg = self.mcas_holder()#mcas_dict()

        self.stop_awg = self._awg.mcas_dict.stop_awgs
        self.pulsedODMRLogic = pulsedODMRLogic(self)
        self.ODMRLogic = ODMRLogic(self)
>>>>>>> Stashed changes
        self.Timer = RepeatedTimer(1, self.clock) # this clock is not very precise, maybe the solution proposed on https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds can be helpful.
        #self.SigCheckReady_Beacon.connect(self.print_counter)
        self.CheckReady_Beacon = RepeatedTimer(1, self.CheckReady)
        #self.CheckReady_Beacon.start()

        return 

    def on_deactivate(self):
<<<<<<< Updated upstream
        self.Timer.stop()
        self.CheckReady_Beacon.stop()
=======
        """
        Deinitialisation performed during deactivation of the module.
        """
        self.Timer.stop()
        self.CheckReady_Beacon.stop()
        self.stop_awg()
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
        self.Time_Tagger._time_diff.update(**kwargs)
        return self.Time_Tagger.time_differences()


=======
        self._time_tagger._time_diff.update(**kwargs)
        return self._time_tagger.time_differences()

    def save_cw_odmr_data(self, tag=None, colorscale_range=None, percentile_range=None):
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
        # self._save_logic.save_data(data_raw,
        #                             filepath=filepath,
        #                             parameters=parameters,
        #                             filelabel=filelabel_raw,
        #                             fmt='%.6e',
        #                             delimiter='\t',
        #                             timestamp=timestamp)
        fig = self.draw_figure(data_raw['count data (counts)'],data_raw['Frequency (MHz)'],data_matrix['Frequency (MHz) + Scanline'],
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

    def save_pulsed_odmr_data(self, tag=None, colorscale_range=None, percentile_range=None):
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
        '''
        
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
        pulsed_SecondsPerPoint=None,
        pulsed_Binning = None
        '''


        parameters['Enable Microwave1 (bool)'] = self.pulsedODMRLogic.pulsed_MW1
        parameters['Enable Microwave2 (bool)'] = self.pulsedODMRLogic.pulsed_MW2
        parameters['Enable Microwave3 (bool)'] = self.pulsedODMRLogic.pulsed_MW3
        parameters['Microwave1 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW1_Power
        parameters['Microwave2 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW2_Power
        parameters['Microwave3 CW Power (dBm)'] = self.pulsedODMRLogic.pulsed_MW3_Power
        parameters['Microwave1 Start (MHz)'] = self.pulsedODMRLogic.cw_StartFreq
        parameters['Microwave1 Stop (MHz)'] = self.pulsedODMRLogic.cw_StopFreq
        parameters['Microwave1 Stepsize (MHz)'] = self.pulsedODMRLogic.cw_Stepsize
        parameters['Microwave2 CW Power (dBm)'] = self.pulsedODMRLogic.cw_MW2_Freq
        parameters['Microwave3 CW Power (dBm)'] = self.pulsedODMRLogic.cw_MW3_Freq
        parameters['A1 (bool)'] = self.pulsedODMRLogic.cw_A1
        parameters['A2 (bool)'] = self.pulsedODMRLogic.cw_A2
        parameters['Pulsed Repump (bool)'] = self.pulsedODMRLogic.cw_PulsedRepump
        parameters['Pulsed Duration (µs)'] = self.pulsedODMRLogic.cw_RepumpDuration
        parameters['Pulsed Decay (µs)'] = self.pulsedODMRLogic.cw_RepumpDecay
        parameters['CW Repump (bool)'] = self.pulsedODMRLogic.cw_CWRepump
        parameters['Green (bool)'] = self.pulsedODMRLogic.enable_green
        parameters['Seconds per Point (s)'] = self.pulsedODMRLogic.cw_SecondsPerPoint
        # self._save_logic.save_data(data_raw,
        #                             filepath=filepath,
        #                             parameters=parameters,
        #                             filelabel=filelabel_raw,
        #                             fmt='%.6e',
        #                             delimiter='\t',
        #                             timestamp=timestamp)
        fig = self.draw_figure(data_raw['count data (counts)'],data_raw['Frequency (MHz)'],data_matrix['Frequency (MHz) + Scanline'],
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


    def draw_figure(self, data, frequencies, matrix, cbar_range=None, percentile_range=None):
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

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
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
>>>>>>> Stashed changes


class ODMRLogic(cw_default):

    def __init__(self,holder):
        self.measurement_running=False
        self.holder=holder
<<<<<<< Updated upstream
        self.counter=self.holder.Time_Tagger.counter()
        self.time_differences = self.holder.Time_Tagger.time_differences()
        self.number_of_points_per_line=self.holder.Time_Tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.cw_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.holder.SigCheckReady_Beacon.connect(self.check_ready)
=======
        self.counter=self.holder._time_tagger.counter()
        self.time_differences = self.holder._time_tagger.time_differences()
        self.number_of_points_per_line=self.holder._time_tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.cw_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.holder.SigCheckReady_Beacon.connect(self.data_readout)
>>>>>>> Stashed changes
        self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
        self.syncing=False

        self.continuing=False

<<<<<<< Updated upstream
    def check_ready(self):
=======
    def data_readout(self):
>>>>>>> Stashed changes
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running or self.syncing):
            #if not(self.syncing):
                return

        if self.continuing:
            self.ancient_data=self.time_differences.getData()
            self.continuing=False
            
        else:
            data=self.time_differences.getData()-self.ancient_data
<<<<<<< Updated upstream
            print(data)
=======
            #print(data)
>>>>>>> Stashed changes
            data=np.array(data,dtype=object)
            self.ancient_data=data+self.ancient_data
            data=np.sum(data,axis=1)
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
            
            self.holder.sigOdmrPlotsUpdated.emit(self.mw1_freq*1e6,self.data,self.scanmatrix, np.array([]), np.array([]))
                
            


    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / 0.35 #awg_amplitude
        #return V_pp / float(self.awg_device.amp1) #awg_amplitude

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

        sig=inspect.signature(self.setup_seq)
        for parameter in sig.parameters.keys():
            #print(parameter)
            if locals()[parameter]!=None:
                exec(f"self.{parameter}={parameter}")
                #print(parameter)
                #exec(f'print(self.{parameter})')

        #calculate the number of repetitions such that the sequence remains on one frequence for "secondsperpoint". One Segment is 1µs by default (this can be changed).
        #self.loop_count = int(self.cw_SecondsPerPoint/(50e-6))

        self.loop_count = int((self.cw_SecondsPerPoint*1e6)/self.cw_segment_length) #great numbers (~8000) will probably result in too long writing time.
        #print("loop_count= ",self.loop_count)   
        if self.loop_count > 2000:
            error_text=f"Too many loop counts in sequence (N={self.loop_count}). Choose shorter seconds per point, or increase segment_length."
            logger.error(error_text)
            raise Exception(error_text)
        #sequence length can be increased by longer segment duration
        
        # Setup list of all frequencies which the sequence should output.
        self.mw1_freq = np.arange(self.cw_StartFreq,self.cw_StopFreq+self.cw_Stepsize,self.cw_Stepsize)

        #setting up the measurement data
        self.number_of_points_per_line=len(self.mw1_freq)
        
        self.time_differences = self.holder.setup_time_tagger(n_histograms=self.number_of_points_per_line,
            binwidth=int(self.cw_SecondsPerPoint*1e12),
            n_bins=1
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
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
            
        # generate a single MW sequence with the needed mw frequencies and play is continuously until the measurement is stopped,
        # either by the stop button, the runtime, or number of sequence repetitions. 
<<<<<<< Updated upstream
        seq = self.holder.awg.mcas(name="cwODMR", ch_dict={"2g": [1,2],"ps": [1]})
=======
        seq = self.holder._awg.mcas(name="cwODMR", ch_dict={"2g": [1,2],"ps": [1]})
>>>>>>> Stashed changes

        # generate segment of repump which starts at each repetition of the sequence.
        seq.start_new_segment("Start")
        if self.cw_PulsedRepump:
            seq.asc(name='repump1', length_mus=self.cw_RepumpDuration, repump=True)
            seq.asc(name='repump2', length_mus=self.cw_RepumpDecay, repump=False)

        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        seq.asc(name='tt_sync1', length_mus=0.01, tt_sync=True)        
<<<<<<< Updated upstream
        #seq.asc(name='tt_sync2', length_mus=0.01, tt_trigger=True)        
        #seq.asc(name='tt_sync3', length_mus=0.01, tt_trigger=False) 

=======
        seq.asc(name='tt_sync2', length_mus=0.01, tt_trigger=True)        
        seq.asc(name='tt_sync3', length_mus=0.01, tt_trigger=False) 
>>>>>>> Stashed changes


        # generate multiple segments, each containing one of the microwave frequencies. Length of each segment is determined by the loop-count.      
        for freq, self.cw_MW2_Frequency,self.cw_MW3_Frequency  in zip(self.mw1_freq, [self.cw_MW2_Freq]*len(self.mw1_freq), [self.cw_MW3_Freq]*len(self.mw1_freq)):
            frequencies=np.array([freq, self.cw_MW2_Frequency,self.cw_MW3_Frequency])[[self.cw_MW1,self.cw_MW2,self.cw_MW3]]
            seq.start_new_segment("Microwaves"+str(frequencies),loop_count=self.loop_count)
            seq.asc(name="Microvaves"+str(frequencies),pd2g1 = {"type":"sine", "frequencies":frequencies, "amplitudes":self.power},
                A1=self.cw_A1,
                A2=self.cw_A2,
                repump=self.cw_CWRepump,
                green=enable_green,
                tt_trigger = True,
                length_mus=self.cw_segment_length
                )
            #turn off tt_trigger to increment the histogram-index of TimeTagger
            seq.start_new_segment("Microwave_readout"+str(frequencies))
            seq.asc(name="Microvaves_readout"+str(frequencies),pd2g1 = {"type":"sine", "frequencies":frequencies, "amplitudes":self.power},
                A1=self.cw_A1,
                A2=self.cw_A2,
                repump=self.cw_CWRepump,
                green=enable_green,
                tt_trigger = False,
                length_mus=0.01
                )

<<<<<<< Updated upstream
        #self.holder.awg.mcas.status = 1
        self.holder.awg.mcas_dict.stop_awgs()
        self.holder.awg.mcas_dict['cwODMR'] = seq
        self.holder.awg.mcas_dict.print_info()
        self.holder.awg.mcas_dict['cwODMR'].run()
        
=======
        #self.holder._awg.mcas.status = 1
        self.holder._awg.mcas_dict.stop_awgs()
        self.holder._awg.mcas_dict['cwODMR'] = seq
        self.holder._awg.mcas_dict.print_info()
        self.holder._awg.mcas_dict['cwODMR'].run()        
>>>>>>> Stashed changes
        print("running sequence cwODMR")



class pulsedODMRLogic(pulsed_default):
    def __init__(self,holder):
        self.measurement_running=False
        self.holder=holder
<<<<<<< Updated upstream
        self.counter=self.holder.Time_Tagger.counter()
        self.time_differences = self.holder.Time_Tagger.time_differences()
        self.number_of_points_per_line=self.holder.Time_Tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.pulsed_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.data_detect=0
        self.holder.SigCheckReady_Beacon.connect(self.check_ready)
=======
        self.counter=self.holder._time_tagger.counter()
        self.time_differences = self.holder._time_tagger.time_differences()
        self.number_of_points_per_line=self.holder._time_tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.pulsed_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.data_detect=0
        self.holder.SigCheckReady_Beacon.connect(self.data_readout)
>>>>>>> Stashed changes
        self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
        self.syncing=False

        self.repet_list1=[]
        self.cter1=1
        self.c1=0
        self.ancient_index=0
        self.continuing=False # variable to discard first getdata after pressing continue.


<<<<<<< Updated upstream
    def check_ready(self):
=======
    def data_readout(self):
>>>>>>> Stashed changes
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running or self.syncing):
                return


        if self.continuing:
            self.ancient_data=self.time_differences.getData()
            self.continuing=False
            
        else:
            data=self.time_differences.getData()-self.ancient_data
            indexes=np.array(self.time_differences.getIndex())
<<<<<<< Updated upstream
            print(data)
=======
            #print(data)
>>>>>>> Stashed changes
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
            
            self.holder.sigOdmrPlotsUpdated.emit(self.mw1_freq*1e6,self.data,self.scanmatrix,indexes/1e12,self.data_detect)
        #print("ploting matrix")
                

    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / 0.35 #awg_amplitude
        #return V_pp / float(self.awg_device.amp1) #awg_amplitude


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
        pulsed_SecondsPerPoint=None,
        pulsed_Binning = None
        ):

        sig=inspect.signature(self.setup_seq)
        for parameter in sig.parameters.keys():
            #print(parameter)
            if locals()[parameter]!=None:
                exec(f"self.{parameter}={parameter}")
                #print(parameter)
                #exec(f'print(self.{parameter})')

        #calculate the number of repetitions such that the sequence remains on one frequence for "secondsperpoint". One Segment is 1µs by default (this can be changed).
        #self.loop_count = int(self.pulsed_SecondsPerPoint/(50e-6))
        self.loop_count = 30 #great numbers (~8000) will probably result in too long writing time.
        #sequence length can be increased by longer segment duration
        
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
        if self.pulsed_MW1:
            self.power += [self.pulsed_MW1_Power]
        if self.pulsed_MW2:
            self.power += [self.pulsed_MW2_Power]
        if self.pulsed_MW3:
            self.power += [self.pulsed_MW3_Power]
        
        self.power = np.asarray(self.power)
        self.power=self.power_to_amp(self.power)
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
        
<<<<<<< Updated upstream
        seq = self.holder.awg.mcas(name="pulsedODMR", ch_dict={"2g": [1,2],"ps": [1]})
=======
        seq = self.holder._awg.mcas(name="pulsedODMR", ch_dict={"2g": [1,2],"ps": [1]})
>>>>>>> Stashed changes
        # generate segment of repump which starts at each repetition of the sequence.
        if self.pulsed_PulsedRepump:
            seq.start_new_segment("Repump")
            seq.asc(name='repump1', length_mus=self.pulsed_RepumpDuration, repump=True)
            seq.asc(name='repump2', length_mus=self.pulsed_RepumpDecay, repump=False)

        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        seq.asc(name='tt_sync1', length_mus=0.01, tt_sync=True)        
        seq.asc(name='tt_sync2', length_mus=0.01, tt_trigger=True)

        freq_init = np.array([self.pulsed_MW2_Freq, self.pulsed_MW3_Freq])[self.pulsed_MW2, self.pulsed_MW3]
        power_init = self.power_to_amp(np.array([self.pulsed_MW2_Power, self.pulsed_MW3_Power])[self.pulsed_MW2, self.pulsed_MW3])
        for freq in self.mw1_freq:
            seq.start_new_segment("Init")
            if (self.pulsed_A1 or self.pulsed_A2) and (self.pulsed_MW2 or self.pulsed_MW3):
                seq.asc(name="init_sine"+str(freq),pd2g1 = {"type":"sine", "frequencies":freq_init, "amplitudes":power_init},
                        A1=self.pulsed_A1,
                        A2=self.pulsed_A2,
                        length_mus=self.pulsed_InitTime
                        )  
                seq.asc(name='Init_decay'+str(freq), length_mus=self.pulsed_DecayInit, A1=False, A2=False)
            elif self.pulsed_A1 or self.pulsed_A2:
                seq.asc(name='init_no_sine',
                        A1=self.pulsed_A1,
                        A2=self.pulsed_A2,
                        length_mus=self.pulsed_InitTime
                        )  
                seq.asc(name='Init_decay'+str(freq), length_mus=self.pulsed_DecayInit, A1=False, A2=False)
            else:
                logger.warning("No Laser assigned for Init Sequence.")
            seq.start_new_segment("Pi_pulse")
            seq.asc(name="Pi_pulse"+str(freq),pd2g1 = {"type":"sine", "frequencies":[freq], "amplitudes":self.power_to_amp(self.pulsed_MW1_Power)},
                length_mus = self.pulsed_piPulseDuration/1000, #self.pulsed_piPulseDuration is divided by 1000 to be in µs
                )
            seq.asc(name='pi_pulse_decay'+str(freq), length_mus=self.pulsed_PiDecay/1000, A1=False, A2=False) #self.pulsed_PiDecay is divided by 1000 to be in µs

            seq.start_new_segment("Readout")
            seq.asc(name='readout'+str(freq), length_mus=self.pulsed_ReadoutTime, A1=self.pulsed_A1Readout, A2=self.pulsed_A2Readout, tt_trigger=True)
            seq.asc(name='readout_decay'+str(freq), length_mus=self.pulsed_ReadoutDecay, A1=False, A2=False, tt_trigger=True)

        #self.holder.awg.mcas.status = 1
<<<<<<< Updated upstream
        self.holder.awg.mcas_dict.stop_awgs()
        self.holder.awg.mcas_dict['pulsedODMR'] = seq
        self.holder.awg.mcas_dict.print_info()
        self.holder.awg.mcas_dict['pulsedODMR'].run()
=======
        self.holder._awg.mcas_dict.stop_awgs()
        self.holder._awg.mcas_dict['pulsedODMR'] = seq
        self.holder._awg.mcas_dict.print_info()
        self.holder._awg.mcas_dict['pulsedODMR'].run()
>>>>>>> Stashed changes
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