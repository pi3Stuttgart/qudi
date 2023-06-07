import numpy as np
from qtpy import QtCore

from core.connector import Connector
from logic.generic_logic import GenericLogic
import sys
import logging; logger = logging.getLogger(__name__)
from core.pi3_utils import delay
import time
from core.statusvariable import StatusVar

sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved


#PulseStreamer is tured on in "pulsed_measurement_logic.pulse_generator_on"
#In order to be able to stream anything, a sequence has to be uploaded beforehand.


class SetupControlLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    sigUpdate = QtCore.Signal()

    mcas_holder = Connector(interface='McasDictHolderInterface')
    #powercontrol = Connector(interface='LaserPowerHolder')
    #automizedmeasurementlogic = Connector(interface = 'Automatedmeasurement')
    savelogic = Connector(interface = 'SaveLogic')

    _AOM_volt:float=1
    read_power:str='-'

    MW1_freq = StatusVar('MW1_freq', 70)
    MW2_freq = StatusVar('MW2_freq', 140)
    MW3_freq = StatusVar('MW3_freq', 210)
    MW1_power = StatusVar('MW1_Power', -21)
    MW2_power = StatusVar('MW2_Power', -21)
    MW3_power = StatusVar('MW3_Power', -21)
    enable_MW1: bool = False
    enable_MW2: bool = False
    enable_MW3: bool = False

    enable_A1: bool = False
    enable_A2: bool = False
    enable_Repump: bool = False
    enable_Green: bool = False

    active_chanels=[] # used to talk to the pulsestreamer directly
    flip_mirror=False

    SigReadPower= QtCore.Signal()

    def __init__(self, config, **kwargs):   
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        """ Prepare logic module for work.
        """

        self._awg = self.mcas_holder()
        #self._powercontrol = self.powercontrol()
        #self._automized_measurement_logic = self.automizedmeasurementlogic()
        self._save_logic = self.savelogic()
        self.flipmirror_sequence_created = False
        self.ps=self._awg.mcas_dict.awgs["ps"]

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.enable_MW1:bool=False
        self.enable_MW2:bool=False
        self.enable_MW3:bool=False
        self.enable_A1:bool=False
        self.enable_A2:bool=False
        self.enable_Repump:bool=False
        self.enable_Green:bool=False
        self.AOM_volt=0
        self._awg.mcas_dict.stop_awgs()
        self.write_to_pulsestreamer()
        
        del self._awg
        #del self._powercontrol
        return

    @property
    def AOM_volt(self):
        #print("getting AOM Volt")
        return self._AOM_volt

    @AOM_volt.setter
    def AOM_volt(self,val):
        #print("setting AOM Volt", val)
        if val>1:
            val=1
            print("Correcting AOM analog Amplitude to 1")
        elif val<0:
            val=0
            print("Correcting AOM analog Amplitude to 0")
        self._AOM_volt=val
        self.ps.analog_volt=self._AOM_volt
        #self.write_to_pulsestreamer()

    @AOM_volt.deleter
    def AOM_volt(self):
        #print("deleting OAM Volt")
        del self._AOM_volt

    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / 0.35 #awg_amplitude
        #return V_pp / float(self.awg_device.amp1) #awg_amplitude

    def setup_seq(
        self,
        enable_A1:bool=None,
        enable_A2:bool=None,
        enable_Repump:bool=None,
        enable_Green:bool=None,

        enable_MW1:bool=None,
        MW1_power:float=None,
        MW1_freq:float=None,

        enable_MW2:bool=None,
        MW2_power:float=None,
        MW2_freq:float=None,

        enable_MW3:bool=None,
        MW3_freq:float=None,
        MW3_power:float=None,
        ):

        self.power = []
        if self.enable_MW1:
            self.power += [self.MW1_power]
        if self.enable_MW2:
            self.power += [self.MW2_power]
        if self.enable_MW3:
            self.power += [self.MW3_power]

        self._awg.mcas_dict.stop_awgs()

        
        if len(self.power)==0 and (self.enable_A1 == False and self.enable_A2 == False and self.enable_Repump == False and self.enable_Green == False):
            print("Setupcontrollogic: Stopping awg")
            return
        
        if len(self.power)==0 and (self.enable_A1 == False and self.enable_A2 == False and self.enable_Repump == True and self.enable_Green == False):
            self._awg.mcas_dict['repump'].run()
            return
        if len(self.power)==0 and (self.enable_A1 == True and self.enable_A2 == False and self.enable_Repump == False and self.enable_Green == False):
            self._awg.mcas_dict['A1'].run()
            return
        if len(self.power)==0 and (self.enable_A1 == False and self.enable_A2 == True and self.enable_Repump == False and self.enable_Green == False):
            self._awg.mcas_dict['A2'].run()
            return
        if len(self.power)==0 and (self.enable_A1 == False and self.enable_A2 == False and self.enable_Repump == False and self.enable_Green == True):
            self._awg.mcas_dict['green'].run()
            return
        if len(self.power)==0 and (self.enable_A1 == True and self.enable_A2 == True and self.enable_Repump == True and self.enable_Green == False):
            self._awg.mcas_dict['RepumpAndA1AndA2'].run()
            return
        

        self.power = np.asarray(self.power)
        self.power=self.power_to_amp(self.power)
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
            
        # generate a single MW sequence with the needed mw frequencies and play is continuously until the measurement is stopped,
        # either by the stop button, the runtime, or number of sequence repetitions.
        seq = self._awg.mcas(name="setupcontrol", ch_dict={"2g": [1, 2], "ps": [1]})
        frequencies = np.array([self.MW1_freq, self.MW2_freq, self.MW3_freq])[[self.enable_MW1, self.enable_MW2, self.enable_MW3]]
        seq.start_new_segment("Microwaves"+str(frequencies), loop_count=200)
        if len(self.power) == 0:
            seq.asc(name="without MW",
                    A1=self.enable_A1,
                    A2=self.enable_A2,
                    repump=self.enable_Repump,
                    green=self.enable_Green,
                    length_mus=50
                    )
        else:
            seq.asc(name="with MW", pd2g1={"type": "sine", "frequencies": frequencies, "amplitudes": self.power},
                    A1=self.enable_A1,
                    A2=self.enable_A2,
                    repump=self.enable_Repump,
                    green=self.enable_Green,
                    length_mus=50
                    )

        self._awg.mcas_dict["setupcontrol"] = seq
        #self._awg.mcas_dict.print_info()
        self._awg.mcas_dict["setupcontrol"].run()
        return
    
    def write_to_pulsestreamer(self):
        #self.active_chanels=list(filter(("").__ne__, ["A1"*self.enable_A1,"A2"*self.enable_A2,"green"*self.enable_Green,"repump"*self.enable_Repump,'FlipMirror'*self.flip_mirror]))
        self.active_chanels=list(filter(("").__ne__, []))
        self.ps.constant(pulse=(0,self.active_chanels,self.AOM_volt,0)) #Ok this is actually not the power we set but the analog input on the A2 AOM

    def MW_on(self):
        return self.enable_MW1 or self.enable_MW2 or self.enable_MW3

    def run(self):
        # if self.MW_on():
        #     self.setup_seq()
        # else:
        #     self._awg.mcas_dict.stop_awgs()
        #     self.write_to_pulsestreamer()
        self.setup_seq()
        
    def A1_Button_Clicked(self,on):
        #print('done something with A1_Button')
        self.enable_A1=on
        self.run()

    def A2_Button_Clicked(self,on):
        #print('done something with A2_Button')
        self.enable_A2=on
        self.run()

    def Repump_Button_Clicked(self,on):
        #print('done something with Repump_Button')
        self.enable_Repump=on
        self.run()

    def Green_Button_Clicked(self,on):
        #print('done something with Green_Button')
        self.enable_Green=on
        self.run()

    def MW1_on_Button_Clicked(self,on):
        #print('done something with MW1_on_Button')
        self.enable_MW1=on
        self.run()

    def MW2_on_Button_Clicked(self,on):
        #print('done something with MW2_on_Button')
        self.enable_MW2=on
        self.run()

    def MW3_on_Button_Clicked(self,on):
        #print('done something with MW3_on_Button')
        self.enable_MW3=on
        self.run()
        
    def MW1_power_DoubleSpinBox_Edited(self,value):
        #print('done something with MW1_power_DoubleSpinBox. Value=',value)
        self.MW1_power=value

    def MW2_power_DoubleSpinBox_Edited(self,value):
        #print('done something with MW2_power_DoubleSpinBox. Value=',value)
        self.MW2_power=value

    def MW3_power_DoubleSpinBox_Edited(self,value):
        #print('done something with MW3_power_DoubleSpinBox. Value=',value)
        self.MW3_power=value

    def MW1_freq_DoubleSpinBox_Edited(self,value):
        #print('done something with MW1_freq_DoubleSpinBox. Value=',value)
        self.MW1_freq=value

    def MW2_freq_DoubleSpinBox_Edited(self,value):
        #print('done something with MW2_freq_DoubleSpinBox. Value=',value)
        self.MW2_freq=value

    def MW3_freq_DoubleSpinBox_Edited(self,value):
        #print('done something with MW3_freq_DoubleSpinBox. Value=',value)
        self.MW3_freq=value

    def Flipmirror_Button_Clicked(self,on):
        awg_running_seq="" #TODO get the active running sequence
        self._awg.mcas_dict.stop_awgs()
        self.flip_mirror=True
        self.write_to_pulsestreamer()
        time.sleep(0.01)
        self.flip_mirror=False
        if self.MW_on():
            self._awg.mcas_dict["setupcontrol"].run()
        else:
            self.write_to_pulsestreamer()


    def create_flipmirror_sequence(self):
        seq = self._awg.mcas(name="FlippyFloppy", ch_dict={"2g": [1,2],"ps": [1]})
        seq.start_new_segment("Start", loop_count=100)
        seq.asc(name='Flip', length_mus=500, FlipMirror=True)
        self._awg.mcas_dict.stop_awgs()
        self._awg.mcas_dict['FlippyFloppy'] = seq
        self._awg.mcas_dict.print_info()
        self.flipmirror_sequence_created = True
    
    def Autofocus_Button_Clicked(self,on):
        print('done something with Autofocus_Button')

    def Read_Power_Button_Clicked(self,on):
        #self.read_power = str(self._powercontrol._laser_power._Read_Power_button_fired()) + " nW"
        self.SigReadPower.emit()

    def Set_Power_Button_Clicked(self,on):
        #self._powercontrol._laser_power.power_target = self.set_power
        #self._powercontrol._laser_power._run()
        #self.read_power = str(self._powercontrol._laser_power._Read_Power_button_fired()) + " nW"
        #print('Set power to: ', self.read_power)
        self.SigReadPower.emit()
        self.write_to_pulsestreamer()

    def Set_Power_DoubleSpinBox_Edited(self,value):
        #print('done something with set_power_DoubleSpinBox. Value=',value)
        self.AOM_volt=value
        
    def StartAutoMeas_Button_Clicked(self,on):
        # save current POIs
        self._save_logic.save_array_as_text(data = self._automized_measurement_logic._scanner_logic.pois, filename = 'POIs.txt', filepath = self._automized_measurement_logic.save_folder)

        # start automized measurement
        self._automized_measurement_logic.start()

    def StopAutoMeas_Button_Clicked(self,on):
        self._automized_measurement_logic.stop()

    def SavePOIs_Button_Clicked(self,on):
        print("Nothing happend")  