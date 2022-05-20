import time
import numpy as np
from qtpy import QtCore

from core.connector import Connector
from logic.generic_logic import GenericLogic
import sys
import inspect
import logging; logger = logging.getLogger(__name__)


sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved


#PulseStreamer is tured on in "pulsed_measurement_logic.pulse_generator_on"
#In order to be able to stream anything, a sequence has to be uploaded beforehand.


class SetupControlLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    # waiting time between queries im milliseconds
    ###CONNECT TO PULSEDMEASUREMENTLOGIC oder so

    sigUpdate = QtCore.Signal()
    #declare connectors

    #microwave1 = Connector(interface='MicrowaveInterface') #UNComment
    pulsegenerator = Connector(interface='PulserInterface')
    mcas_holder = Connector(interface='McasDictHolderInterface')

    MW1_power:float=-21
    MW3_freq:float=210
    MW3_power:float=-21
    MW2_power:float=-21
    MW2_freq:float=140
    MW1_freq:float=70
    set_power:float=10
    enable_MW1:bool=False
    enable_MW2:bool=False
    enable_MW3:bool=False
    enable_A1:bool=False
    enable_A2:bool=False
    enable_Repump:bool=False
    enable_Green:bool=False

    def on_activate(self):
        """ Prepare logic module for work.
        """
        #create the pulser object
        self.pulser=self.pulsegenerator()
        #create a pulsegenerator sequence
        self.pulser._seq=self.pulser.pulse_streamer.createSequence()
        self.awg = self.mcas_holder()#mcas_dict()
        self.stop_awg = self.awg.mcas_dict.stop_awgs
        self.settings_list=[]

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.pulser.pulser_off()
        
    @QtCore.Slot()
    def check_laser_loop(self):
        """ Get power, current, shutter state and temperatures from laser. """
    
    
    @QtCore.Slot(bool)
    def set_laser_state(self, state):
        """ Turn laser on or off. """
        if state and self.laser_state == LaserState.OFF:
            self._laser.on()
        if not state and self.laser_state == LaserState.ON:
            self._laser.off()
        self.sigUpdate.emit()

    
    @QtCore.Slot(float)
    def set_MW_power(self, power):
        """ Set laser output power. """
        self._laser.set_power(power)

    def activate_pulser_channel(self, channel, state, duration=100000):
        self.pulser._seq.setDigital(channel,[[duration, state]])
        self.pulser.pulser_on() #find a way to switch this off
        #print("pulser on")

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

        sig=inspect.signature(self.setup_seq)
        self.string=""
        ancient_self_variables={} # store the self. variables in this dict to be unpacked later
        
        for parameter in sig.parameters.keys():
            #print(parameter)
            # print(locals()[parameter])
            #exec(f"print(self.{parameter})")
            exec(f"ancient_self_variables['{parameter}']=self.{parameter}")
            if locals()[parameter]!=None:
                exec(f"self.{parameter}={parameter}")

            # maybe add that we only take the power and freq of MW when they are used
            exec(f"self.string=self.string+str(float(self.{parameter}))")

        self.power = []
        if self.enable_MW1:
            self.power += [self.MW1_power]
        if self.enable_MW2:
            self.power += [self.MW2_power]
        if self.enable_MW3:
            self.power += [self.MW3_power]

        self.awg.mcas_dict.stop_awgs()

        
        if len(self.power)==0 and (self.enable_A1 == False and self.enable_A2 == False and self.enable_Repump == False and self.enable_Green == False):
            print("Stoping awg")
            return

        if 1:#not(self.string in self.settings_list): # generate sequence if it doesn't exist
            print("\ngenerated new sequence")
            self.settings_list.append(self.string)
            index=self.settings_list.index(self.string)
            name='Setupcontrol_'+str(index)

            self.power = np.asarray(self.power)
            self.power=self.power_to_amp(self.power)
            if np.sum(self.power)>1:
                logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
                raise Exception
                
            # generate a single MW sequence with the needed mw frequencies and play is continuously until the measurement is stopped,
            # either by the stop button, the runtime, or number of sequence repetitions.
            seq = self.awg.mcas(name=name, ch_dict={"2g": [1,2], "ps":[1]})
            frequencies=np.array([self.MW1_freq, self.MW2_freq,self.MW3_freq])[[self.enable_MW1,self.enable_MW2,self.enable_MW3]]
            #print(frequencies)
            seq.start_new_segment("Microwaves"+str(frequencies))
            #print(self.enable_A1,self.enable_A2,self.enable_Repump,self.enable_Green)
            if len(self.power)==0:
                seq.asc(name="without MW",
                        A1=self.enable_A1,
                        A2=self.enable_A2,
                        repump=self.enable_Repump,
                        green=self.enable_Green,
                        length_mus=5
                        )
            else:
                seq.asc(name="with MW", pd2g1 = {"type":"sine", "frequencies":frequencies, "amplitudes":self.power},
                        A1=self.enable_A1,
                        A2=self.enable_A2,
                        repump=self.enable_Repump,
                        green=self.enable_Green,
                        length_mus=5
                        )

            #self.awg.mcas.status = 1
            self.awg.mcas_dict[name] = seq

        #always run this part
        index=self.settings_list.index(self.string)
        name='Setupcontrol_'+str(index)
        #self.awg.mcas_dict.print_info()
        self.awg.mcas_dict[name].run()
        print("running sequence Setupcontrol"+str(index)) # store the settings in a dict so we do not generate a lot of sequences that o the same
        
        for key,val in ancient_self_variables.items(): # restore the ancient variables
            exec(f"self.{key}={val}")

    def MW1_power_DoubleSpinBox_Edited(self,value):
        #print('done something with MW1_power_DoubleSpinBox. Value=',value)
        self.MW1_power=value

    def Repump_Button_Clicked(self,on):
            #print('done something with Repump_Button')
            self.enable_Repump=on
            self.setup_seq()

    def MW3_freq_DoubleSpinBox_Edited(self,value):
            #print('done something with MW3_freq_DoubleSpinBox. Value=',value)
            self.MW3_freq=value


    def A1_Button_Clicked(self,on):
            #print('done something with A1_Button')
            self.enable_A1=on
            self.setup_seq()

    def MW1_on_Button_Clicked(self,on):
            #print('done something with MW1_on_Button')
            self.enable_MW1=on
            self.setup_seq()

    def MW2_on_Button_Clicked(self,on):
            #print('done something with MW2_on_Button')
            self.enable_MW2=on
            self.setup_seq()

    def MW3_on_Button_Clicked(self,on):
            #print('done something with MW3_on_Button')
            self.enable_MW3=on
            self.setup_seq()

    def MW3_power_DoubleSpinBox_Edited(self,value):
            #print('done something with MW3_power_DoubleSpinBox. Value=',value)
            self.MW3_power=value

    def Flipmirror_Button_Clicked(self,on):
            print('done something with Flipmirror_Button')

    def MW2_power_DoubleSpinBox_Edited(self,value):
            #print('done something with MW2_power_DoubleSpinBox. Value=',value)
            self.MW2_power=value

    def A2_Button_Clicked(self,on):
            #print('done something with A2_Button')
            self.enable_A2=on
            self.setup_seq()

    def Green_Button_Clicked(self,on):
            #print('done something with Green_Button')
            self.enable_Green=on
            self.setup_seq()

    def PD_zero_Button_Clicked(self,on):
            print('done something with PD_zero_Button')

    def MW2_freq_DoubleSpinBox_Edited(self,value):
            #print('done something with MW2_freq_DoubleSpinBox. Value=',value)
            self.MW2_freq=value

    def MW1_freq_DoubleSpinBox_Edited(self,value):
            #print('done something with MW1_freq_DoubleSpinBox. Value=',value)
            self.MW1_freq=value

    def Autofocus_Button_Clicked(self,on):
            print('done something with Autofocus_Button')

    def Set_Power_Button_Clicked(self,on):
            print('done something with Set_Power_Button')

    def set_power_DoubleSpinBox_Edited(self,value):
            #print('done something with set_power_DoubleSpinBox. Value=',value)
            self.set_power=value