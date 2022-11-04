#Rabi-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys
sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved

from core.module import Base
from core.connector import Connector
#from hardware.swabian_instruments.timetagger import TT as TimeTagger
from logic.generic_logic import GenericLogic
#import hardware.Keysight_AWG_M8190.pyarbtools_master.pyarbtools as pyarbtools

from logic.rabi_logic.rabi_default_values_and_widget_functions import rabi_default_values_and_widget_functions as rabi_default



from qtpy import QtCore

import inspect
import logging
logger = logging.getLogger(__name__)
import time
#import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
import datetime

class RabiLogic(GenericLogic,rabi_default):
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
    sigRabiPlotsUpdated = QtCore.Signal()
    SigClock= QtCore.Signal()
    SigCheckReady_Beacon = QtCore.Signal()
    sigFitPerformed= QtCore.Signal(np.float)

    starting_time=0

    def on_activate(self):
        self._time_tagger=self.counter_device()
        self._time_tagger.setup_TT()
        self._save_logic = self.savelogic()
        self._awg = self.mcas_holder()#mcas_dict()
        self._fit_logic = self.fitlogic()
        #self._transition_tracker=self.transition_tracker()
        
        self.stop_awg = self._awg.mcas_dict.stop_awgs
        self.Timer = RepeatedTimer(1, self.clock) # this clock is not very precise, maybe the solution proposed on https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds can be helpful.
        #self.SigCheckReady_Beacon.connect(self.print_counter)
        self.CheckReady_Beacon = RepeatedTimer(1, self.get_data)
        #self.CheckReady_Beacon.start()
        self.number_of_points_per_line=self._time_tagger._time_diff["n_histograms"]
        self.measurement_running=False
        self.counter=self._time_tagger.counter()
        self.time_differences = self._time_tagger.time_differences()
        self.scanmatrix=np.zeros(np.array(self.time_differences.getData(),dtype=object).shape)
        self.SigCheckReady_Beacon.connect(self.get_data)
   
        self.syncing=False

        self.continuing=False
        return 

    def on_deactivate(self):
        self.Timer.stop()
        self.CheckReady_Beacon.stop()
        self.stop_awg()
        try: #checkready_beacon may not be launched
            self.checkready.stop()
        except:
            pass
        
        return 
    
    def get_data(self):
        if time.time()-self.starting_time>self.rabi_Stoptime and self.rabi_Stoptime!=0:
            self.rabi_Stop_Button_Clicked(True)

        #print("checkready:",self.measurement_running)
        if not(self.measurement_running):
                return
            
        else:
            indexes=np.array(self.time_differences.getIndex()) #readout binwidth (ps)
            self.scanmatrix=np.array(self.time_differences.getData(),dtype=object) #readout data from timetagger
            self.measured_times_ns=indexes/1e3 #indexes is in ps
            mask=((self.measured_times_ns>=self.rabi_AOMDelay) & (self.measured_times_ns<=self.rabi_IntegrationTime+self.rabi_AOMDelay)) #create mask to filter counts depending on arrival time
            self.data=np.sum(self.scanmatrix[:,mask],axis=1) #sum up the readout-histogram after a single Tau
            self.data_detect=np.sum(self.scanmatrix,axis=0) #sum up the histograms to see the emission decay
            self.measured_times=indexes/1e12 #binwidth in seconds
            self.sigRabiPlotsUpdated.emit()


    def clock(self):
        self.SigClock.emit()

    def CheckReady(self):
        self.SigCheckReady_Beacon.emit()

    def setup_time_tagger(self,**kwargs):
        self._time_tagger._time_diff.update(**kwargs)
        return self._time_tagger.time_differences()

    def save_rabi_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current Rabi data to a file."""
        timestamp = datetime.datetime.now()
        filepath = self._save_logic.get_path_for_module(module_name='Rabi')
        tag = self.rabi_Filename
        if tag is None:
            tag = ''

        if len(tag) > 0:
            filelabel_raw = '{0}_Rabi_raw'.format(tag)
            filelabel_detection = '{0}_Rabi_detection'.format(tag)
            filelabel_matrix = '{0}_Rabi_matrix'.format(tag)
        else:
            filelabel_raw = '_Rabi_raw'
            filelabel_detection = '_Rabi_detection'
            filelabel_matrix = '_Rabi_matrix'

        data_raw = OrderedDict()
        data_detection = OrderedDict()
        data_matrix = OrderedDict()
        data_raw['count data (counts)'] = self.data
        data_raw['Tau (ns)'] = self.tau_duration
        data_detection['Detection Time (ns)'] = self.measured_times*1e9 # save in [ns]
        data_detection['Detection Counts (counts)'] = self.data_detect
        data_matrix['Detection Time + Tau'] = self.scanmatrix

        parameters = OrderedDict()
        parameters['Enable Microwave1 (bool)'] = self.rabi_MW1
        parameters['Enable Microwave2 (bool)'] = self.rabi_MW2
        parameters['Enable Microwave3 (bool)'] = self.rabi_MW3
        parameters['Microwave1 CW Power (dBm)'] = self.rabi_MW1_Power
        parameters['Microwave2 CW Power (dBm)'] = self.rabi_MW2_Power
        parameters['Microwave3 CW Power (dBm)'] = self.rabi_MW3_Power
        parameters['Microwave1 CW Power (dBm)'] = self.rabi_MW1_Freq
        parameters['Microwave2 CW Power (dBm)'] = self.rabi_MW2_Freq
        parameters['Microwave3 CW Power (dBm)'] = self.rabi_MW3_Freq
        parameters['Tau min (ns)'] = self.rabi_Tau_Min
        parameters['Tau max (ns)'] = self.rabi_Tau_Max
        parameters['Tau Step (ns)'] = self.rabi_Tau_Step
        parameters['Tau Decay (ns)'] = self.rabi_Tau_Decay
        parameters['A1 (bool)'] = self.rabi_A1
        parameters['A2 (bool)'] = self.rabi_A2
        parameters['Pulsed Repump (bool)'] = self.rabi_PulsedRepump
        parameters['Pulsed Duration (µs)'] = self.rabi_RepumpDuration
        parameters['Pulsed Decay (µs)'] = self.rabi_RepumpDecay
        parameters['CW Repump (bool)'] = self.rabi_CWRepump
        parameters['Init Time (µs)'] = self.rabi_InitTime
        parameters['Init Decay (µs)'] = self.rabi_DecayInit
        parameters['Readout Time (µs)'] = self.rabi_ReadoutTime
        parameters['Readout Decay (µs)'] = self.rabi_ReadoutDecay
        parameters['Readout via A1 (bool)'] = self.rabi_A1Readout
        parameters['Readout via A2 (bool)'] = self.rabi_A2Readout
        parameters['AOM Delay (ns)'] = self.rabi_AOMDelay
        parameters['Integration Window (ns)'] = self.rabi_IntegrationTime
        parameters['Binning (ns)'] = self.rabi_Binning
        parameters['Amplitude Fit'] = self.Amplitude_Fit
        parameters['Frequency Fit'] = self.Frequency_Fit
        parameters['Phase Fit'] = self.Phase_Fit
        parameters['Pi pulse']= self.pi_pulse


        fig = self.draw_figure(
            data_raw['Tau (ns)'],
            data_raw['count data (counts)'],
            data_matrix['Detection Time + Tau'],
            data_detection['Detection Time (ns)'],
            data_detection['Detection Counts (counts)'],
            self.interplolated_x_data,
            self.fit_data,
            cbar_range=colorscale_range,
            percentile_range=percentile_range
        )

        self._save_logic.save_data(data_matrix,
                                    filepath=filepath,
                                    parameters=parameters,
                                    filelabel=filelabel_matrix,
                                    fmt='%.6e',
                                    delimiter='\t',
                                    timestamp=timestamp)
        
        self._save_logic.save_data(data_detection,
                                    filepath=filepath,
                                    parameters=parameters,
                                    filelabel=filelabel_detection,
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

        self.log.info('Rabi data saved to:\n{0}'.format(filepath))
        return

    def draw_figure(self, time_data, count_data, matrix_data, detection_time, detection_counts, fit_freq_vals, fit_count_vals, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        #key = 'range: {1}'.format(frequencies)
        matrix_data=matrix_data.astype(float)
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

        while np.max(time_data) > 1000:
            time_data = time_data / 1000
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

        ax_mean.plot(time_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')
        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'counts)')
        ax_mean.set_xlim(np.min(time_data), np.max(time_data))
        matrixplot = ax_matrix.imshow(
            matrix_data,
            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
            origin='lower',
            vmin=cbar_range[0],
            vmax=cbar_range[1],
            extent=[np.min(time_data),
                    np.max(time_data),
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

    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / 0.35 #awg_amplitude
        #return V_pp / float(self.awg_device.amp1) #awg_amplitude

    def setup_seq(
        self,
        rabi_Tau_Min=None,
        rabi_Tau_Max=None,
        rabi_Tau_Step=None,
        rabi_Tau_Decay=None,

        rabi_MW1=None,
        rabi_MW1_Freq=None,
        rabi_MW1_Power=None,
        rabi_MW2=None,
        rabi_MW2_Freq=None,
        rabi_MW2_Power=None,
        rabi_MW3=None,
        rabi_MW3_Freq=None,
        rabi_MW3_Power=None,

        rabi_A1=None,
        rabi_A2=None,
        rabi_A1Readout=None,
        rabi_A2Readout=None,
        rabi_InitTime=None,
        rabi_DecayInit=None,
        rabi_RepumpDecay=None,
        rabi_CWRepump=None,
        rabi_PulsedRepump=None,
        rabi_RepumpDuration=None,
        rabi_AOMDelay=None,
        rabi_IntegrationTime=None,
        rabi_Binning=None,
        rabi_Interval=None,
        rabi_PeriodicSaving=None,
        rabi_Stoptime=None,

        rabi_ReadoutTime=None,
        rabi_ReadoutDecay=None
        ):

        ancient_self_variables={}
        sig=inspect.signature(self.setup_seq)
        for parameter in sig.parameters.keys():
            #print(parameter)
            exec(f"ancient_self_variables['{parameter}']=self.{parameter}")
            if locals()[parameter]!=None:
                exec(f"self.{parameter}={parameter}")
                #print(parameter)
                #exec(f'print(self.{parameter})')

        # Setup list of all frequencies which the sequence should output.
        self.tau_duration = np.arange(self.rabi_Tau_Min,self.rabi_Tau_Max+self.rabi_Tau_Step,self.rabi_Tau_Step)
        
        self.time_differences.stop()
        time.sleep(0.02) #maybe the timetagger would get too much commands at the same time

        self.time_differences=self.setup_time_tagger(n_histograms=len(self.tau_duration),
            binwidth=int(self.rabi_Binning*1000), #rabi_Binning input is in ns.
            n_bins=int(self.rabi_ReadoutTime/self.rabi_Binning)
        )

        self.power = []
        if self.rabi_MW2:
            self.power += [self.rabi_MW2_Power]
        if self.rabi_MW3:
            self.power += [self.rabi_MW3_Power]

        self.power = np.asarray(self.power)
        self.power=self.power_to_amp(self.power)
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
        
        seq = self._awg.mcas(name="Rabi", ch_dict={"2g": [1,2],"ps": [1]})
        # generate segment of repump which starts at each repetition of the sequence.
        seq.start_new_segment("Start")
        if self.rabi_PulsedRepump:
            seq.asc(name='repumpOn', length_mus=self.rabi_RepumpDuration, repump=True)
            seq.asc(name='repumpOff', length_mus=self.rabi_RepumpDecay, repump=False)

        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        seq.asc(name='tt_sync1', length_mus=0.01, tt_sync=True) #Set histogram index to 0       
        seq.asc(name='tt_sync2', length_mus=0.01, tt_trigger=True) #increment histogram index

        freq_init = np.array([self.rabi_MW2_Freq, self.rabi_MW3_Freq])[self.rabi_MW2, self.rabi_MW3]
        power_init = self.power_to_amp(np.array([self.rabi_MW2_Power, self.rabi_MW3_Power])[self.rabi_MW2, self.rabi_MW3])
        for duration in self.tau_duration:
            seq.start_new_segment("Init")
            
            if (self.rabi_A1 or self.rabi_A2) and (self.rabi_MW2 or self.rabi_MW3):
                seq.asc(name="init_sine"+str(duration),pd2g1 = {"type":"sine", "frequencies":freq_init, "amplitudes":power_init},
                        A1=self.rabi_A1,
                        A2=self.rabi_A2,
                        length_mus=self.rabi_InitTime
                        )  
                seq.asc(name='Init_decay'+str(duration), length_mus=self.rabi_DecayInit, A1=False, A2=False)
            elif self.rabi_A1 or self.rabi_A2:
                seq.asc(name='init_no_sine',
                        A1=self.rabi_A1,
                        A2=self.rabi_A2,
                        length_mus=self.rabi_InitTime
                        )  
                seq.asc(name='Init_decay'+str(duration), length_mus=self.rabi_DecayInit, A1=False, A2=False)
            else:
                logger.warning("No Laser assigned for Init Sequence.")

            #if duration==self.tau_duration[1]:
            seq.start_new_segment("Tau_pulse")
            seq.asc(name="Tau_pulse"+str(duration),pd2g1 = {"type":"sine", "frequencies":[self.rabi_MW1_Freq], "amplitudes":self.power_to_amp(self.rabi_MW1_Power)},
                length_mus = duration/1000) #self.rabi_piPulseDuration is divided by 1000 to be in µs
            seq.asc(name='Tau_pulse_decay'+str(duration), length_mus=self.rabi_Tau_Decay/1000, A1=False, A2=False) #self.rabi_Tau_Decay is divided by 1000 to be in µs

            seq.start_new_segment("Readout")
            seq.asc(name='readout'+str(duration), length_mus=self.rabi_ReadoutTime/1000, A1=self.rabi_A1Readout, A2=self.rabi_A2Readout, tt_trigger=True)
            seq.asc(name='readout_decay'+str(duration), length_mus=self.rabi_ReadoutDecay/1000, A1=False, A2=False, tt_trigger=True)
        
        #self.awg.mcas.status = 1
        self._awg.mcas_dict.stop_awgs()
        self._awg.mcas_dict['Rabi'] = seq
        self._awg.mcas_dict.print_info()
        self._awg.mcas_dict['Rabi'].run()
        for key,val in ancient_self_variables.items(): # restore the ancient variables
            exec(f"self.{key}={val}")

    def do_fit(self, x_data, y_data, tag):
        
        x_data=x_data.astype(np.float)
        y_data=y_data.astype(np.float)
        self.interplolated_x_data=np.linspace(x_data.min(),x_data.max(),len(x_data)*10) # for the fitting part

        if tag == 'Cosinus':
            print("Doing Cosinus")
            model,params=self._fit_logic.make_sine_model()

            result = self._fit_logic.make_sine_fit(
                                x_axis=x_data,
                                data=y_data,
                                units='Hz',
                                estimator=self._fit_logic.estimate_sine
                                )

            #fit_func=self._fit_logic.sine
            #result=fit_func.fit(x_data,y_data)
            #self.fit_data = fit_func(x=self.interplolated_x_data, *result.x)

        if tag == 'Cosinus+Phase':
            print("Doing Cosinus+Phase")
            model,params=self._fit_logic.make_sine_model()

            result = self._fit_logic.make_sine_fit(
                                x_axis=x_data,
                                data=y_data,
                                units='Hz',
                                estimator=self._fit_logic.estimate_sine
                                )

        
        self.fit_data = model.eval(x=self.interplolated_x_data, params=result.params)
        self.Amplitude_Fit:str=''
        self.Frequency_Fit:str=''
        self.Phase_Fit:str=''
        self.tau_pulse:float=0 #ns

        try:
            self.Amplitude_Fit=str(round(result.params["amplitude"].value,2))
            self.Frequency_Fit=str(round(result.params["frequency"].value*1e3,2))
            self.Phase_Fit=str(round(result.params["phase"].value*180/np.pi,2))
            self.pi_pulse=round(1/(result.params["frequency"].value)/2,2)
        except Exception as e:
            print("an error occured during fitting in Rabi:\n", e)

        self.rabi_FitParams="Amplitude: "+self.Amplitude_Fit+"\n"+"Frequency  (MHz): "+self.Frequency_Fit+"\n"+"Pi pulse (ns): "+str(self.pi_pulse)+"\n"+"Phase: "+self.Phase_Fit
        
        self.sigFitPerformed.emit(1/(result.params["frequency"].value)/2)

        return self.interplolated_x_data,self.fit_data,result

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