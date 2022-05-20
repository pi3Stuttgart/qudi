#ODMR-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys
sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved

from core.module import Base
from core.connector import Connector
from hardware.swabian_instruments.timetagger import TT as TimeTagger
from logic.generic_logic import GenericLogic
#import hardware.Keysight_AWG_M8190.pyarbtools_master.pyarbtools as pyarbtools

from qtpy import QtCore
from logic.odmrlogic.cw_ODMR_default_values_and_widget_functions import cw_ODMR_default_values_and_widget_functions as cw_default
from logic.odmrlogic.pulsed_ODMR_default_values_and_widget_functions import pulsed_ODMR_default_values_and_widget_functions as pulsed_default

import inspect
import logging
logger = logging.getLogger(__name__)
import time
import pandas as pd

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
        self.Time_Tagger=self.counter_device()
        self.Time_Tagger.setup_TT()
        self.pulsedODMRLogic = pulsedODMRLogic(self)
        self.ODMRLogic = ODMRLogic(self)
        self.awg = self.mcas_holder()#mcas_dict()
        self.stop_awg = self.awg.mcas_dict.stop_awgs
        self.Timer = RepeatedTimer(1, self.clock) # this clock is not very precise, maybe the solution proposed on https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds can be helpful.
        #self.SigCheckReady_Beacon.connect(self.print_counter)
        self.CheckReady_Beacon = RepeatedTimer(1, self.CheckReady)
        #self.CheckReady_Beacon.start()

        return 

    def on_deactivate(self):
        self.Timer.stop()
        self.CheckReady_Beacon.stop()
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
        self.Time_Tagger._time_diff.update(**kwargs)
        return self.Time_Tagger.time_differences()




class ODMRLogic(cw_default):

    def __init__(self,holder):
        self.measurement_running=False
        self.holder=holder
        self.counter=self.holder.Time_Tagger.counter()
        self.time_differences = self.holder.Time_Tagger.time_differences()
        self.number_of_points_per_line=self.holder.Time_Tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.cw_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.holder.SigCheckReady_Beacon.connect(self.check_ready)
        self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
        self.syncing=False

        self.continuing=False

    def check_ready(self):
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running or self.syncing):
            #if not(self.syncing):
                return

        if self.continuing:
            self.ancient_data=self.time_differences.getData()
            self.continuing=False
            
        else:
            data=self.time_differences.getData()-self.ancient_data
            print(data)
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
        seq = self.holder.awg.mcas(name="cwODMR", ch_dict={"2g": [1,2],"ps": [1]})

        # generate segment of repump which starts at each repetition of the sequence.
        seq.start_new_segment("Start")
        if self.cw_PulsedRepump:
            seq.asc(name='repump1', length_mus=self.cw_RepumpDuration, repump=True)
            seq.asc(name='repump2', length_mus=self.cw_RepumpDecay, repump=False)

        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        seq.asc(name='tt_sync1', length_mus=0.01, tt_sync=True)        
        #seq.asc(name='tt_sync2', length_mus=0.01, tt_trigger=True)        
        #seq.asc(name='tt_sync3', length_mus=0.01, tt_trigger=False) 



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

        #self.holder.awg.mcas.status = 1
        self.holder.awg.mcas_dict.stop_awgs()
        self.holder.awg.mcas_dict['cwODMR'] = seq
        self.holder.awg.mcas_dict.print_info()
        self.holder.awg.mcas_dict['cwODMR'].run()
        
        print("running sequence cwODMR")



class pulsedODMRLogic(pulsed_default):
    def __init__(self,holder):
        self.measurement_running=False
        self.holder=holder
        self.counter=self.holder.Time_Tagger.counter()
        self.time_differences = self.holder.Time_Tagger.time_differences()
        self.number_of_points_per_line=self.holder.Time_Tagger._time_diff["n_histograms"]
        self.scanmatrix=np.zeros((self.pulsed_NumberOfLines,self.number_of_points_per_line))
        self.data=0
        self.data_detect=0
        self.holder.SigCheckReady_Beacon.connect(self.check_ready)
        self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
        self.syncing=False

        self.repet_list1=[]
        self.cter1=1
        self.c1=0
        self.ancient_index=0
        self.continuing=False # variable to discard first getdata after pressing continue.


    def check_ready(self):
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running or self.syncing):
                return


        if self.continuing:
            self.ancient_data=self.time_differences.getData()
            self.continuing=False
            
        else:
            data=self.time_differences.getData()-self.ancient_data
            indexes=np.array(self.time_differences.getIndex())
            print(data)
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
        
        seq = self.holder.awg.mcas(name="pulsedODMR", ch_dict={"2g": [1,2],"ps": [1]})
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
        self.holder.awg.mcas_dict.stop_awgs()
        self.holder.awg.mcas_dict['pulsedODMR'] = seq
        self.holder.awg.mcas_dict.print_info()
        self.holder.awg.mcas_dict['pulsedODMR'].run()
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