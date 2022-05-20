#Rabi-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys
sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved

from core.module import Base
from core.connector import Connector
from hardware.swabian_instruments.timetagger import TT as TimeTagger
from logic.generic_logic import GenericLogic
#import hardware.Keysight_AWG_M8190.pyarbtools_master.pyarbtools as pyarbtools

from logic.rabi_logic.rabi_default_values_and_widget_functions import rabi_default_values_and_widget_functions as rabi_default



from qtpy import QtCore

import inspect
import logging
logger = logging.getLogger(__name__)
import time
import pandas as pd

class RabiLogic(GenericLogic,rabi_default):
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
    sigRabiPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    SigClock= QtCore.Signal()
    SigCheckReady_Beacon = QtCore.Signal()


    def on_activate(self):
        self.Time_Tagger=self.counter_device()
        self.Time_Tagger.setup_TT()
        self.awg = self.mcas_holder()#mcas_dict()
        self.stop_awg = self.awg.mcas_dict.stop_awgs
        self.Timer = RepeatedTimer(1, self.clock) # this clock is not very precise, maybe the solution proposed on https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds can be helpful.
        #self.SigCheckReady_Beacon.connect(self.print_counter)
        self.CheckReady_Beacon = RepeatedTimer(1, self.get_data)
        #self.CheckReady_Beacon.start()
        self.number_of_points_per_line=self.Time_Tagger._time_diff["n_histograms"]
        self.measurement_running=False
        self.counter=self.Time_Tagger.counter()
        self.time_differences = self.Time_Tagger.time_differences()
        self.scanmatrix=np.zeros(np.array(self.time_differences.getData(),dtype=object).shape)
        self.SigCheckReady_Beacon.connect(self.get_data)
   
        self.syncing=False

        self.continuing=False
        return 

    def on_deactivate(self):
        self.Timer.stop()
        self.CheckReady_Beacon.stop()
        try: #checkready_beacon may not be launched
            self.checkready.stop()
        except:
            pass
        
        return 
    
    def get_data(self):
        #print("checkready:",self.measurement_running)
        if not(self.measurement_running):
                return
            
        else:
            indexes=np.array(self.time_differences.getIndex()) #readout binwidth (ps)
            self.scanmatrix=np.array(self.time_differences.getData(),dtype=object) #readout data from timetagger
            measured_times_ns=indexes/1e3 #indexes is in ps
            mask=((measured_times_ns>=self.rabi_AOMDelay) & (measured_times_ns<=self.rabi_IntegrationTime+self.rabi_AOMDelay)) #create mask to filter counts depending on arrival time
            data_sine=np.sum(self.scanmatrix[:,mask],axis=1) #sum up the readout-histogram after a single Tau
            data_detect=np.sum(self.scanmatrix,axis=0) #sum up the histograms to see the emission decay
            print(np.shape(self.scanmatrix))
            measured_times=indexes/1e12 #binwidth in seconds
            self.sigRabiPlotsUpdated.emit(self.tau_duration*1e-9,data_sine,self.scanmatrix, measured_times, data_detect)


    def clock(self):
        self.SigClock.emit()

    def CheckReady(self):
        self.SigCheckReady_Beacon.emit()

    def setup_time_tagger(self,**kwargs):
        self.Time_Tagger._time_diff.update(**kwargs)
        return self.Time_Tagger.time_differences()


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
        
        seq = self.awg.mcas(name="Rabi", ch_dict={"2g": [1,2],"ps": [1]})
        # generate segment of repump which starts at each repetition of the sequence.
        seq.start_new_segment("Start")
        if self.rabi_PulsedRepump:
            seq.asc(name='repumpOn', length_mus=self.rabi_RepumpDuration, repump=True)
            seq.asc(name='repumpOff', length_mus=self.rabi_RepumpDecay, repump=False)

        # short pulses to SYNC and TRIGGER the timedifferences module of TimeTagger.
        seq.asc(name='tt_sync1', length_mus=0.01, tt_sync=True) #Set histogram index to 0       
        seq.asc(name='tt_sync2', length_mus=0.01, tt_trigger=True)

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
            seq.asc(name='readout_decay'+str(duration), length_mus=self.rabi_ReadoutDecay/1000, A1=False, A2=False, tt_trigger=False)
        
        #self.awg.mcas.status = 1
        self.awg.mcas_dict.stop_awgs()
        self.awg.mcas_dict['Rabi'] = seq
        self.awg.mcas_dict.print_info()
        self.awg.mcas_dict['Rabi'].run()
        for key,val in ancient_self_variables.items(): # restore the ancient variables
            exec(f"self.{key}={val}")



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