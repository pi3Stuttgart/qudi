import time
from . import PID
from core.connector import Connector
from logic.generic_logic import GenericLogic
from PyQt5 import QtCore
from PyQt5 import QtTest
import numpy as np
import matplotlib.pyplot as plt
from core.statusvariable import StatusVar
from scipy.ndimage.interpolation import shift
from scipy.interpolate import InterpolatedUnivariateSpline
from logic.powerstabilization.default_values_and_widget_functions import powerstabilization_default as powerstabilization_default
import glob
import pathlib as Path

#import connector files for easy coding and fast file finding
from logic.save_logic import SaveLogic
from logic.setup_control_logic import SetupControlLogic
from hardware.USBNidaq6211 import streamUSBnidaq

class PowerStabilizationLogic(GenericLogic, powerstabilization_default):
    
    ''' Config Example
    powerstabilizationlogic:
            module.Class: 'powerstabilizationlogic.PowerStabilizationLogic'
            connect:
                streamUSBnidaq: 'USBNIDAQ6001'
                setupcontrollogic1: 'setupcontrollogic'
                savelogic: 'savelogic'
            voltage_offset: 0.01651
            voltage_to_power_ratio: 6.7485e-3
    '''
    # Implement Config options for voltage_offset and voltage_to_power_ratio

    # streamUSBnidaq = Connector(interface='StreamUSBNidaqInterface')
    streamUSBnidaq = Connector(interface='streamUSBnidaq')
    setupcontrollogic1 = Connector(interface='SetupControlLogic')
    savelogic = Connector(interface='SaveLogic')
    #transition_tracker = Connector(interface='TransitionTracker')

    # Declare signals
    SigStabilized=QtCore.Signal()
    SigUpdatePlots=QtCore.Signal()
    SigStartPowerCalibration=QtCore.Signal()
    SigPidProc = QtCore.Signal()
    SigPowerCalibrationFinished=QtCore.Signal(list, list) # [voltage], [power]
    _TargetPower=0
    _Wavelength=917

    voltage_offset = StatusVar('voltage_offset', 0.0)
    
    def on_activate(self):
        self._streaming_device:streamUSBnidaq = self.streamUSBnidaq() #Insert device for init
        self._setupcontrol_logic:SetupControlLogic = self.setupcontrollogic1() # For turning on lasers and Setting Analog PS Output.
        self._save_logic:SaveLogic = self.savelogic()
        #self._transition_tracker= self.transition_tracker() # For turning on lasers and Setting Analog PS Output.
        self.SigPidProc.connect(self.pid_processing,type=QtCore.Qt.QueuedConnection)
        
        self.SigStartPowerCalibration.connect(self.calibrate_power,type=QtCore.Qt.QueuedConnection)
        
        self.current_output_voltage=self._setupcontrol_logic.AOM_A2_volt
        
        self.voltage_min = 0
        self.voltage_max = 1
        self.number_steps = 51

        self.power_list=np.zeros(self.datapoints)
        self.voltage_list=np.zeros(self.datapoints)
        
        self._streaming_device.start_acquisition()
        self.SigPidProc.emit()

        self.load_calibration()

    def on_deactivate(self):
        self.stabilizing= False
        self._streaming_device.on_deactivate()

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
        
    @property
    def Wavelength(self):
        return self._Wavelength

    @Wavelength.setter
    def Wavelength(self,val):
        self._Wavelength=val
        #self.stabilizing=True

    @Wavelength.deleter
    def Wavelength(self,val):
        del self._Wavelength

    @QtCore.pyqtSlot()
    def calibrate_power(self):
        self._setupcontrol_logic._awg.mcas_dict.stop_awgs()
        QtTest.QTest.qSleep(1000)
        # self._setupcontrol_logic._awg.mcas_dict["A2"].run() # TODO: doesnt turn on laser yet. Why?
        self._setupcontrol_logic.enable_Green = True
        self._setupcontrol_logic.run() 
        QtTest.QTest.qSleep(1000)

        self.scan_voltage = np.linspace(self.voltage_min, self.voltage_max, self.number_steps)
        self.scan_power = []
        print("Started calibration")
        for volt in self.scan_voltage:
            print("Current voltage:", volt)
            self._setupcontrol_logic.AOM_A1_volt=volt #TODO: Add two variables for AOM1 and AOM2. Done via "self.controlA1"
            self._setupcontrol_logic.write_to_pulsestreamer()
            QtTest.QTest.qSleep(1000)
            feedback_voltage=sum(self._streaming_device.buffer_in[0])/len(self._streaming_device.buffer_in[0]) # average of all measured values
            self.scan_power.append(self.voltage_to_power(np.mean(feedback_voltage)))
        self.scan_voltage = np.array(self.scan_voltage)
        self.scan_power = np.array(self.scan_power)
        save = [self.scan_voltage,self.scan_power]
        np.savetxt(f"power_calibration\\power_calibration_{int(self._Wavelength)}.csv",save)
        self.fity = np.linspace(np.min(self.scan_power),np.max(self.scan_power),5000)
        self.fitx = np.zeros_like(self.fity)
        try:
            self.fitx = np.array([InterpolatedUnivariateSpline(self.scan_voltage, self.scan_power-float(i), k=3).roots()[0] for i in self.fity])
            np.savetxt(f"power_calibration\\power_calibration_{int(self._Wavelength)}_interpolated.csv",[self.fitx,self.fity])
        except:
            print("Didn't find roots")

        fig = self.draw_figure(self.scan_voltage,self.scan_power,self.fitx,self.fity)
        fig.savefig(f"power_calibration\\power_calibration_{int(self._Wavelength)}_interpolated.png")
        plt.close(fig)

    def set_power_A1(self, wanted_power):
        extrapolator = InterpolatedUnivariateSpline(self.scan_voltage, self.scan_power-float(wanted_power), k=3)
        print("Roots of Interpolation:", extrapolator.roots())
        try:
            self._setupcontrol_logic.AOM_A1_volt=min(extrapolator.roots())
            self._setupcontrol_logic.write_to_pulsestreamer()
        except:
            print("ERROR MESSAGE HERE. Wanted laserpower cannot be reached.")
            self._setupcontrol_logic.AOM_A1_volt=.8
            
    def set_power_A2(self, wanted_power):
        extrapolator = InterpolatedUnivariateSpline(self.scan_voltage, self.scan_power-float(wanted_power), k=3)
        print("Roots of Interpolation:", extrapolator.roots())
        try:
            self._setupcontrol_logic.AOM_A2_volt=min(extrapolator.roots())
            self._setupcontrol_logic.write_to_pulsestreamer()
        except:
            print("ERROR MESSAGE HERE. Wanted laserpower cannot be reached.")
            self._setupcontrol_logic.AOM_A2_volt=.8

    def power_to_voltage(self, power):
        voltage = power * self.voltage_to_power_ratio + self.voltage_offset
        return voltage

    def voltage_to_power(self, voltage):
        power = (voltage - self.voltage_offset) / self.voltage_to_power_ratio
        return power

    def load_calibration(self):#
        files = np.array(glob.glob(str(Path.Path.cwd())+"\\power_calibration\\power_calibration_???.csv"))
        if len(files) != 0:
            L = len(str(Path.Path.cwd())+"\\power_calibration\\power_calibration_")
            values = np.array([int(i[L:L+3]) for i in files]) 
            closest_WL = values[np.argmin(np.abs(values-self._Wavelength))]
            # self.scan_voltage = np.array([0.  , 0.02, 0.04, 0.06, 0.08, 0.1 , 0.12, 0.14, 0.16, 0.18, 0.2 , 0.22, 0.24, 0.26, 0.28, 0.3 , 0.32, 0.34, 0.36, 0.38, 0.4 , 0.42, 0.44, 0.46, 0.48, 0.5 , 0.52, 0.54, 0.56, 0.58, 0.6 , 0.62, 0.64, 0.66, 0.68, 0.7 , 0.72, 0.74, 0.76, 0.78, 0.8 , 0.82, 0.84, 0.86, 0.88, 0.9 , 0.92, 0.94, 0.96, 0.98, 1.  ])
            # self.scan_power = np.array([ 0.1238836 ,  0.12599493,  0.22159166,  0.68937049,  1.54317239,  2.78440493,  4.25741556,  5.93053428,  7.6515102 ,  9.36321997, 11.040093  , 12.60412704, 14.31536895, 15.89324504, 17.36590648, 18.69018796, 19.92368213, 21.08022998, 21.99455996, 22.78220943, 23.62451957, 24.30050268, 25.23735482, 25.50397125, 26.02136908, 26.40258496, 26.75647065, 26.99083052, 27.24407526, 27.1358099 , 27.37357142, 27.56629082, 27.6788962 , 27.97683129, 28.00275399, 28.0284421 , 28.28110047,
            # 28.34713886, 28.45129887, 28.45681184, 28.43346968, 28.67029297, 28.7260092 , 28.5505324 , 28.47112212, 28.48613617, 28.26315399, 28.23863885, 28.44942211, 28.27781615, 28.20028263])
            self.scan_voltage,self.scan_power = np.loadtxt(f"power_calibration\\power_calibration_{closest_WL}.csv")
            print(f"Calibration loaded for {closest_WL}nm!")
        else:
            print("No calibration file found!")

    def pid_processing(self):
        # measure the voltage and save the trace
        self.feedback_voltage=sum(self._streaming_device.buffer_in[0])/len(self._streaming_device.buffer_in[0]) # average of all measured values
        self.current_power = self.voltage_to_power(self.feedback_voltage)#*1e9 #nW

        # Update lists for plotting
        self.voltage_list = shift(self.voltage_list,-1, cval=self.feedback_voltage) # nowhere used
        self.power_list = shift(self.power_list,-1, cval=self.current_power)

        self.last_points=25
        self.tolerance=0.03

        power_stability_list = np.asarray(self.power_list[-self.last_points:])

        #print("power_stability_list:", power_stability_list)
        #print("self.TargetPower*(1+self.tolerance)):", self.TargetPower*(1+self.tolerance))
        #print("self.TargetPower*(1-self.tolerance)):", self.TargetPower*(1-self.tolerance))
        #print("self.TargetPower*(1-self.tolerance)):", self.TargetPower*(1-self.tolerance))
        #print("Bool1:", (power_stability_list > self.TargetPower*(1+self.tolerance)))
        #print("Bool2:", (power_stability_list < self.TargetPower * (1 - self.tolerance)))
        msk = (power_stability_list > self.TargetPower*(1+self.tolerance)) | (power_stability_list < self.TargetPower*(1 - self.tolerance))

        # print(power_stability_list,self.TargetPower)
        # print(msk,np.sum(msk))

        if self.stabilizing and not sum(msk): #all values in power_stability_list are between target +- self.tolerance%
            self.stabilizing = False
            self.SigStabilized.emit()

        #self.setpoint1_list.append(self.pid1.SetPoint)
        #self.pid1_out_list.append(self.current_output_voltage)

        #self.time_list.append(self.time_step)
        #self.actual_time_list.append(time.time())
        #self.time_step=self.time_step+1
        self.SigUpdatePlots.emit()

        QtTest.QTest.qSleep(self.sleep_time) 
        self.SigPidProc.emit() # calling pid_processing again

    def draw_figure(self, scan_voltage, scan_power, fitx, fity):
        """ Draw the calibration figure to save with the data.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots(nrows=1, ncols=1)

        ax.plot(scan_voltage, scan_power, linestyle=':', linewidth=0.5)
        ax.plot(fitx, fity, linestyle=':', linewidth=0.5)
        ax.set_xlabel("AOM Voltage (V)")
        ax.set_ylabel("Power (nW)")


        return fig