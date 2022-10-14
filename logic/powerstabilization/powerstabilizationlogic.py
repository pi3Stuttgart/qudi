import time
from . import PID
from core.module import Base
from core.connector import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore

from logic.powerstabilization.default_values_and_widget_functions import powerstabilization_default as powerstabilization_default


class PowerStabilizationLogic(GenericLogic, powerstabilization_default):
    
    ''' Config Example
    powerstabilizationlogic:
            module.Class: 'powerstabilizationlogic.PowerStabilizationLogic'
            connect:
                streamUSBnidaq: 'streamusbnidaq'
            voltage_offset: 0.01651
            voltage_to_power_ratio: 6.7485e-3
    '''
    # Implement Config options for voltage_offset and voltage_to_power_ratio

    streamUSBnidaq = Connector(interface='StreamUSBNidaqInterface')

    # Declare signals

    def on_activate(self): #TODO this method should be on_activate
        self._streaming_device = self.streamUSBnidaq() #Insert device for init
        
        self.voltage_list=[]
        self.pid1_out_list=[]
        self.setpoint1_list=[]
        self.time_list=[]
        self.actual_time_list=[]

    def on_deactivate(self):
        self.stop_control()

    def start_control(self):
        self.sleep_time = 0.5 #FIXME do we really need a sleep? Does this affect performance?
        self.pid1 = PID.PID(float(self.P1_var), float(self.I1_var), float(self.D1_var))
        self.pid1.setSampleTime(0.5)
        if self.running!=True:
            try:  
                self.voltage_list=[]
                self.power_list=[]
                self.pid1_out_list=[]
                self.setpoint1_list=[]
                self.time_list=[]
                self.actual_time_list=[]
                self.time=0
                self._streaming_device.start_acquisition()
                self.running=True
                self.pid_processing()
            except Exception as error:
                print("An error occured, aborting. ")
                print("++++++++++++++ error message:   ++++++++++++++++\n")
                print(error)
                print("After aborting set voltage to 0.")
                self.stop_control()
        else:
            print("Stabilization already running.")
    
    def stop_control(self): 
        self.running=False
        print("Stopping stabilization.")
        self._streaming_device.shut_down_streaming() # is also done when shutting down _streaming_device. Does it need to be executed twice?

    def pid_processing(self):
        print("Start Power Control...")
        while self.running:
            #update the values of the variables according to the value in the GUI
            self.pid1.setKp(float(self.P1_var))
            self.pid1.setKi(float(self.I1_var))
            self.pid1.setKd(float(self.D1_var))
            
            # measure the voltage and save the trace
            time.sleep(self.sleep_time) # UNFUG! DONT USE LONG SLEEPS IN QUDI LATER
            self.feedback_voltage=sum(self._streaming_device.buffer_in[0])/len(self._streaming_device.buffer_in[0]) # average of all measured values
            print("current voltage:", self.feedback_voltage)
            self.current_power = self.voltage_to_power(self.feedback_voltage)
            print("current power: ", self.current_power)
            
            self.pid1.SetPoint = self.TargetVoltage
            self.pid1.update(self.feedback_voltage)
            self.current_voltage = self.pid1.output

            self.voltage_list.append(self.feedback_voltage)
            self.power_list.append(self.current_power)
            self.setpoint1_list.append(self.pid1.SetPoint)
            self.pid1_out_list.append(self.current_voltage)

            self.time_list.append(self.time)
            self.actual_time_list.append(time.time())
            self.time=self.time+1

            self._streaming_device.goToVoltage([self.current_voltage]) # TODO: Tell hardware file which channel to use
                                                        # Should include two values if two channels are used in hardware file.
                                                        # At which level should the not controlled channel stay?

    def power_to_voltage(self, power):
        voltage = power * self.voltage_to_power_ratio + self.voltage_offset
        return voltage

    def voltage_to_power(self, voltage):
        power = (voltage - self.voltage_offset) / self.voltage_to_power_ratio
        return power

    def set_fix_voltage(self, tag): # can A2 be set while A1 is controlled via pid_processing?
        if tag == 'A1':
            self._streaming_device.goToVoltage(self.A1Voltage)
        if tag == 'A2':
            self._streaming_device.goToVoltage(self.A2Voltage)
        # TODO: Tell hardware file which channel to use