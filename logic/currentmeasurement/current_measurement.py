import time
from . import PID
from core.connector import Connector
from logic.generic_logic import GenericLogic
from PyQt5 import QtCore
from PyQt5 import QtTest
import numpy as np

from collections import OrderedDict
from core.statusvariable import StatusVar
from scipy.ndimage.interpolation import shift
from scipy.interpolate import InterpolatedUnivariateSpline
from logic.currentmeasurement.default_values_and_widget_functions import currentmeasurement_default as currentmeasurement_default
import datetime

class CurrentMeasurementLogic(GenericLogic, currentmeasurement_default):
    
    ''' Config Example
    currentmeasurementlogic:
            module.Class: 'currentmeasurementlogic.CurrentMeasurementLogic'
            connect:
                streamUSBnidaq: 'streamusbnidaq'
            voltage_offset: 0.01651
            voltage_to_power_ratio: 6.7485e-3
    '''
    # Implement Config options for voltage_offset and voltage_to_power_ratio

    # streamUSBnidaq = Connector(interface='StreamUSBNidaqInterface')
    # setupcontrollogic1 = Connector(interface='SetupControlLogic')
    # #transition_tracker = Connector(interface='TransitionTracker')

    # Declare signals
    SigStabilized=QtCore.Signal()
    SigUpdatePlots=QtCore.Signal()
    SigStartPowerCalibration=QtCore.Signal()
    SigPidProc = QtCore.Signal()
    SigUpdateVoltageLabels = QtCore.Signal()
    SigPowerCalibrationFinished=QtCore.Signal(list, list) # [voltage], [power]
    _TargetPower=0
    sleep_time=200
    scanning=False

    voltage_offset = StatusVar('voltage_offset', 0.0)
    
    offset = StatusVar('current_measurement_offset', 0)
    Multiplier =StatusVar('current_measurement_Multiplier', 10)

    scan_stop_V:float = StatusVar('scan_stop_V',0)
    stabilization_wait_time:float= StatusVar('stabilization_wait_time',5000) #ms 
    scan_start_V:float= StatusVar('scan_start_V',0)
    save_after_scan:bool= StatusVar('save_after_scan',0)
    applied_voltage:float= StatusVar('applied_voltage',0)
    step:float= StatusVar('step',0.1)
    name:str= StatusVar('name',"")

    Safe_Limits=[-30,10] #V

    # Implement Config options for voltage_offset and voltage_to_power_ratio
    USBnidaq = Connector(interface='StreamUSBNidaqInterface')
    laserscannerlogic = Connector(interface='LaserScannerLogic')
    savelogic = Connector(interface='SaveLogic')

    def on_activate(self):
        self._streaming_device = self.USBnidaq()
        self._laser_scanner_logic = self.laserscannerlogic()
        self._savelogic=self.savelogic()
        
        self._streaming_device.start_ao_task()

        self.stabilization_wait_time=self.stabilization_wait_time/1000
        
        self._laser_scanner_logic.sigScanNextLine.connect(self.change_voltage)

        self.voltages = [0,0]# [0,0.1,0.2,0.3,0.4,0.5,0.4,.3, 2., .1, 0, -.1, -.2, -.3, -.4]
        self.step_line = 1

        self.SigPidProc.connect(self.pid_processing,type=QtCore.Qt.QueuedConnection)

        self.current_list=np.zeros(self.Data_Points)
        self.voltage_list=np.zeros(self.Data_Points)
        self.timestamp_list=np.zeros(self.Data_Points)
        
        self.t0=time.time()
        self._streaming_device.start_acquisition()
        self.SigPidProc.emit()

        self.set_voltage(0)
        print("Started")

    def on_deactivate(self):
        self.set_voltage(0)
        self._streaming_device.on_deactivate()
    
    def set_voltage(self, volt):
        self._streaming_device.goToVoltage(volt)

    def change_voltage(self):
        current_scan_line = self._laser_scanner_logic._scan_counter_up
        while current_scan_line >= len(self.voltages):
            current_scan_line = current_scan_line-len(self.voltages)
        self.set_voltage(self.voltages[int(current_scan_line/self.step_line)])

    def set_voltages(self, start, stop, step):
        v_list = []
        v_list.extend(np.round(np.arange(start,stop+step,step),3))
        v_list.extend(np.round(np.arange(start,stop,step)[::-1][:-1],3))
        self.voltages = v_list

    
    def scan_voltages(self):
        voltages=np.arange(self.scan_start_V,self.scan_stop_V,self.step)
        for V in voltages:
            self.applied_voltage_doubleSpinBox_Edited(V)
            QtTest.QTest.qSleep(self.stabilization_wait_time)

        if self.save_after_scan:
            self.save_trace(self.name)

        self.scnning=False

    def save_trace(self,tag=""):
        print("im am the save data of current measurement")
        if tag is None:
            tag = ''

        self._saving_stop_time = time.time()

        filepath = self._save_logic.get_path_for_module(module_name='Current_Measurement')
        timestamp = datetime.datetime.now()

        if len(tag) > 0:
            filelabel = tag + '_current_measurement_data'
        else:
            filelabel = 'currentmeasurement_data'
        
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['Voltage (V)'] = self.plot_x_frequency
        data['current data (A)'] = self.plot_y
        data['time']= self.timestamp_list

        parameters = OrderedDict()

        self._save_logic.save_data(
            data,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )

        self.log.info('Laser Scan saved to:\n{0}'.format(filepath))
        return 0
    
    # def on_activate(self):
    #     self._streaming_device = self.streamUSBnidaq() #Insert device for init
    #     self._setupcontrol_logic= self.setupcontrollogic1() # For turning on lasers and Setting Analog PS Output.
    #     #self._transition_tracker= self.transition_tracker() # For turning on lasers and Setting Analog PS Output.
    #     self.SigPidProc.connect(self.pid_processing,type=QtCore.Qt.QueuedConnection)
        
    #     self.SigStartPowerCalibration.connect(self.calibrate_power,type=QtCore.Qt.QueuedConnection)
        
    #     self.current_output_voltage=self._setupcontrol_logic.AOM_volt
        
    #     self.voltage_min = 0
    #     self.voltage_max = 1
    #     self.number_steps = 51

    #     self.power_list=np.zeros(self.Data_Points)
    #     self.voltage_list=np.zeros(self.Data_Points)
        
    #     self._streaming_device.start_acquisition()
    #     self.SigPidProc.emit()

    #     self.load_calibration()

    # def on_deactivate(self):
    #     self.stabilizing= False

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

    def pid_processing(self):
        # measure the voltage and save the trace
        self.feedback_voltage=sum(self._streaming_device.buffer_in[0])/len(self._streaming_device.buffer_in[0]) # average of all measured values
        self.current_current =self.feedback_voltage#*1e9 #nW

        # Update lists for plotting
        self.voltage_list = shift(self.voltage_list,-1, cval=self.applied_voltage) 
        self.current_list = shift(self.current_list,-1, cval=self.current_current)
        self.timestamp_list= shift(self.timestamp_list,-1, cval= time.time()-self.t0)

        #self.current_list = np.array(list(self.current_list))

        #self.setpoint1_list.append(self.pid1.SetPoint)
        #self.pid1_out_list.append(self.current_output_voltage)

        #self.time_list.append(self.time_step)
        #self.actual_time_list.append(time.time())
        #self.time_step=self.time_step+1
        self.SigUpdatePlots.emit()

        QtTest.QTest.qSleep(self.sleep_time) 
        self.SigPidProc.emit() # calling pid_processing again

    def update_voltages(self):
        self.set_voltage(self.nidaq_voltage)
        self.SigUpdateVoltageLabels.emit()
