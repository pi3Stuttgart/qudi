import time
from . import PID
from core.connector import Connector
from logic.generic_logic import GenericLogic
from PyQt5 import QtCore
from PyQt5 import QtTest
import numpy as np
from core.statusvariable import StatusVar
from scipy.ndimage.interpolation import shift
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
    SigStabilized = QtCore.Signal()
    SigPidProc = QtCore.Signal()
    #SigUpdatePulseStreamer=QtCore.Signal()
    _TargetPower=0

    voltage_offset = StatusVar('voltage_offset', 0.0)
    
    def on_activate(self):
        self._streaming_device = self.streamUSBnidaq() #Insert device for init
        self._setupcontrol_logic= self.setupcontrollogic1() # For turning on lasers and Setting Analog PS Output.
        self.SigStartControl.connect(self.start_control,type=QtCore.Qt.QueuedConnection)
        self.SigPidProc.connect(self.pid_processing,type=QtCore.Qt.QueuedConnection)
        #self.SigUpdatePulseStreamer.connect(self._setupcontrol_logic.write_to_pulsestreamer,type=QtCore.Qt.QueuedConnection)

        self.current_output_voltage=self._setupcontrol_logic.AOM_volt
        
        #self.voltage_list=[]
        self.voltage_list=np.zeros(self.datapoints)
        self.power_list=np.zeros(self.datapoints)
        self.pid1_out_list=[]
        self.setpoint1_list=[]
        #self.time_list=[]
        self.actual_time_list=[]
        self.time_step=0
        
        self.pid1 = PID.PID(float(self.P1_var), float(self.I1_var), float(self.D1_var))
        self.pid1.setSampleTime(0.01)

        self._streaming_device.start_acquisition()
        self.SigPidProc.emit()
        

    def on_deactivate(self):
        self.stabilizing= False
        self.SigStabilized.emit()
        pass
        #TODO: deactivate hardware

    @property
    def TargetPower(self):
        return self._TargetPower

    @TargetPower.setter
    def TargetPower(self,val):
        self._TargetPower=val
        #self.stabilizing=True

    @TargetPower.deleter
    def TargetPower(self,val):
        del self._TargetPower

    @QtCore.pyqtSlot() # What is a pyqtSlot?
    def start_control(self):
        self.pid1 = PID.PID(float(self.P1_var), float(self.I1_var), float(self.D1_var), output = self._setupcontrol_logic.AOM_volt)
        self.pid1.setSampleTime(1) #0.01 #does nothing rn?
        try:  
            # self.voltage_list=[]
            # self.power_list=np.zeros(500)
            # self.pid1_out_list=[]
            # self.setpoint1_list=[]
            # self.time_list=[]
            # self.actual_time_list=[]
            # self.time=0
            self.pid1.setKp(float(self.P1_var))
            self.pid1.setKi(float(self.I1_var))
            self.pid1.setKd(float(self.D1_var))
            print("Start Power Control...")
            self.stabilizing= True
            
        except Exception as error:
            print("An error occured in powerstabilization, aborting... ")
            print("++++++++++++++ error message:   ++++++++++++++++\n")
            print(error)
            print("After aborting set voltage to 0.")
            self.stabilizing= False
            self.SigStabilized.emit()
        # else:
        #     print("Stabilization already running.")
        #     self.stabilizing= True
    
    @QtCore.pyqtSlot()
    def pid_processing(self):
        # measure the voltage and save the trace
        self.feedback_voltage=sum(self._streaming_device.buffer_in[0])/len(self._streaming_device.buffer_in[0]) # average of all measured values
        self.current_power = self.voltage_to_power(self.feedback_voltage)#*1e9 #nW

        if self.stabilizing:
            self.pid1.SetPoint = self.power_to_voltage(self.TargetPower)
            self.pid1.update(self.feedback_voltage)
            self.current_output_voltage = self.pid1.output
            self._setupcontrol_logic.AOM_volt=self.current_output_voltage #TODO: Add two variables for AOM1 and AOM2. Done via "self.controlA1"
            self._setupcontrol_logic.write_to_pulsestreamer()
            #self.SigUpdatePulseStreamer.emit()

        # Update lists for plotting
        self.voltage_list = shift(self.voltage_list,-1, cval=self.feedback_voltage) # nowhere used
        self.power_list = shift(self.power_list,-1, cval=self.current_power)

        self.last_points=25
        self.tolerance=0.03

        power_stability_list=np.asarray(self.power_list[-self.last_points:])
        msk=(power_stability_list> self.TargetPower*(1+self.tolerance)) | (power_stability_list< self.TargetPower*(1-self.tolerance))

        # print(power_stability_list,self.TargetPower)
        # print(msk,np.sum(msk))

        if self.stabilizing and not sum(msk): #all values in power_stability_list are between target +- self.tolerance%
            self.stabilizing=False
            self.SigStabilized.emit()

        #self.setpoint1_list.append(self.pid1.SetPoint)
        #self.pid1_out_list.append(self.current_output_voltage)

        #self.time_list.append(self.time_step)
        #self.actual_time_list.append(time.time())
        #self.time_step=self.time_step+1
        self.SigUpdatePlots.emit()

        QtTest.QTest.qSleep(self.sleep_time) 
        self.SigPidProc.emit() # calling pid_processing again



    def power_to_voltage(self, power):
        voltage = power * self.voltage_to_power_ratio + self.voltage_offset
        return voltage

    def voltage_to_power(self, voltage):
        power = (voltage - self.voltage_offset) / self.voltage_to_power_ratio
        return power

    def set_fix_voltage(self, tag):
        if tag == 'A1':
            self._streaming_device.goToVoltage(self.A1Voltage)
        if tag == 'A2':
            self._setupcontrol_logic.AOM_volt=self.A2Voltage #TODO: Add two variables for AOM1 and AOM2
            
    # not used anymore, since we give voltage directly from PulseStreamer
    def set_fix_voltage(self, tag): # can A2 be set while A1 is controlled via pid_processing?
        if tag == 'A1':
            self._streaming_device.goToVoltage(self.A1Voltage)
        if tag == 'A2':
            
            self._streaming_device.goToVoltage(self.A2Voltage)
        # TODO: Tell hardware file which channel to use