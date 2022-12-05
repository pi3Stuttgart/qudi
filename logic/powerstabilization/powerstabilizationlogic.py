import time
from . import PID
from core.connector import Connector
from logic.generic_logic import GenericLogic
from PyQt5 import QtCore

import numpy as np

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
    setupcontrollogic1 = Connector(interface='SetupControlLogic')

    # Declare signals
    SigUpdatePlots=QtCore.Signal()
    SigStartControl = QtCore.Signal()
    SigStopControl = QtCore.Signal()
    SigPidProc = QtCore.Signal()
    SigUpdatePulseStreamer=QtCore.Signal()
    SigStabilized = QtCore.Signal()
    _TargetPower=0

    def on_activate(self): #TODO this method should be on_activate
        self._streaming_device = self.streamUSBnidaq() #Insert device for init
        self._setupcontrol_logic= self.setupcontrollogic1()
        
        self.SigStartControl.connect(self.start_control,type=QtCore.Qt.QueuedConnection)
        self.SigStopControl.connect(self.stop_control,type=QtCore.Qt.QueuedConnection)
        self.SigPidProc.connect(self.pid_processing,type=QtCore.Qt.QueuedConnection)
        self.SigUpdatePulseStreamer.connect(self._setupcontrol_logic.write_to_pulsestreamer,type=QtCore.Qt.QueuedConnection)

        self.voltage_list=[]
        self.pid1_out_list=[]
        self.setpoint1_list=[]
        self.time_list=[]
        self.actual_time_list=[]

        self.power_list_length=100 #not yet implemented

        self.current_output_voltage=self._setupcontrol_logic.AOM_volt
        self.running=False
        self.sleep_time = 0.5 #FIXME do we really need a sleep? Does this affect performance?

    def on_deactivate(self):
        if self.running:
            self.stop_control()

    @property
    def TargetPower(self):
        return self._TargetPower

    @TargetPower.setter
    def TargetPower(self,val):
        self._TargetPower=val
        self.stabilize=True

    @TargetPower.deleter
    def TargetPower(self,val):
        del self._TargetPower

    @QtCore.pyqtSlot()
    def start_control(self):
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
                self.pid1.setKp(float(self.P1_var))
                self.pid1.setKi(float(self.I1_var))
                self.pid1.setKd(float(self.D1_var))
                print("Start Power Control...")
                self.stabilize= True
                self.SigPidProc.emit()
            except Exception as error:
                print("An error occured, aborting. ")
                print("++++++++++++++ error message:   ++++++++++++++++\n")
                print(error)
                print("After aborting set voltage to 0.")
                self.stop_control()
        else:
            print("Stabilization already running.")
            self.stabilize= True
    
    @QtCore.pyqtSlot()
    def stop_control(self):
        self.running=False
        print("Stopping stabilization.")
        #self.SigNotPidProc.emit()
        self._streaming_device.shut_down_streaming() # is also done when shutting down _streaming_device. Does it need to be executed twice?

    @QtCore.pyqtSlot()
    def pid_processing(self):
        if self.running:
            # measure the voltage and save the trace
            if self.stabilize:
                self._setupcontrol_logic.AOM_volt=self.current_output_voltage
                self.SigUpdatePulseStreamer.emit()

            time.sleep(self.sleep_time) # UNFUG! DONT USE LONG SLEEPS IN QUDI LATER
            self.feedback_voltage=sum(self._streaming_device.buffer_in[0])/len(self._streaming_device.buffer_in[0]) # average of all measured values
            self.current_power = self.voltage_to_power(self.feedback_voltage)#*1e9 #nW
            
            self.pid1.SetPoint = self.power_to_voltage(self.TargetPower)
            self.pid1.update(self.feedback_voltage)
            self.current_output_voltage = self.pid1.output

            self.voltage_list.append(self.feedback_voltage)
            self.power_list.append(self.current_power)

            last_points=5
            tolerance=0.03

            power_stability_list=np.asarray(self.power_list[-last_points:])
            msk=(power_stability_list> self.TargetPower*(1+tolerance)) | (power_stability_list< self.TargetPower*(1-tolerance))

            # print(power_stability_list,self.TargetPower)
            # print(msk,np.sum(msk))

            if self.stabilize and not sum(msk): #all values in power_stability_list are between target +- tolerance%
                self.stabilize=False
                self.SigStabilized.emit()

            self.setpoint1_list.append(self.pid1.SetPoint)
            self.pid1_out_list.append(self.current_output_voltage)

            self.time_list.append(self.time)
            self.actual_time_list.append(time.time())
            self.time=self.time+1

            self.SigPidProc.emit()

        else:
            pass
            #self.stop_control()
        self.SigUpdatePlots.emit()



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