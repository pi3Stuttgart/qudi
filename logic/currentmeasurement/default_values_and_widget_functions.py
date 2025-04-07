import threading
from PyQt5 import QtCore
from core.statusvariable import StatusVar
import threading

class currentmeasurement_default():
        Data_Points:float = 500
        _applied_voltage:float = 0
        safe_limits:int = 1 #True of 1 if we use safe limits
        nidaq_voltage=0

        @property
        def applied_voltage(self):
                return self._applied_voltage

        @applied_voltage.setter
        def applied_voltage(self,value):
                if self.safe_limits:
                        if (value < self.Safe_Limits[0]) | (value > self.Safe_Limits[1]):
                                print(f"Given value exceded safe limits, turn off safe limits to allow to get to {value} V")
                                return
                        
                self._applied_voltage=value
                return

        @applied_voltage.deleter
        def applied_voltage(self):
                del self._applied_voltage

        @QtCore.pyqtSlot(str)
        def Data_Points_LineEdit_textEdited(self,text):
                #print('done something with Data_Points_LineEdit. Text=',text)
                try:
                        self.Data_Points=int(text)
                except:
                        pass

        @QtCore.pyqtSlot(float)
        def applied_voltage_doubleSpinBox_Edited(self,value):
                #print('done something with applied_voltage_doubleSpinBox. Value=',value)
                if self.safe_limits:
                        if (value < self.Safe_Limits[0]) | (value > self.Safe_Limits[1]):
                                print(f"Given value exceded safe limits, turn off safe limits to allow to get to {value} V")
                                return
                        
                self.applied_voltage=value
                self.nidaq_voltage=value/self.Multiplier
                self.update_voltages()


        @QtCore.pyqtSlot(float)
        def offset_doubleSpinBox_Edited(self,value):
                #print('done something with offset_doubleSpinBox. Value=',value)
                self.offset=value
        
        @QtCore.pyqtSlot(float)
        def Multiplier_doubleSpinBox_Edited(self,value):
                #print('done something with Multiplier_doubleSpinBox. Value=',value)
                self.Multiplier=value
                self.nidaq_voltage=self.applied_voltage/value
                self.update_voltages()

        @QtCore.pyqtSlot(bool)
        def SaveTrace_PushButton_Clicked(self,on):
                #print('done something with SaveTrace_PushButton')
                self.save_trace()


        @QtCore.pyqtSlot(float)
        def scan_stop_V_doubleSpinBox_Edited(self,value):
                #print('done something with scan_stop_V_doubleSpinBox. Value=',value)
                if self.safe_limits:
                        if (value < self.Safe_Limits[0]) | (value > self.Safe_Limits[1]):
                                print(f"Given value exceded safe limits, turn off safe limits to allow to get to {value} V")
                                return

                self.scan_stop_V=value

        @QtCore.pyqtSlot(float)
        def stabilization_wait_time_doubleSpinBox_Edited(self,value):
                #print('done something with stabilization_wait_time_doubleSpinBox. Value=',value)
                self.stabilization_wait_time=value*1000

        @QtCore.pyqtSlot(float)
        def scan_start_V_doubleSpinBox_Edited(self,value):
                #print('done something with scan_start_V_doubleSpinBox. Value=',value)
                if self.safe_limits:
                        if (value < self.Safe_Limits[0]) | (value > self.Safe_Limits[1]):
                                print(f"Given value exceded safe limits, turn off safe limits to allow to get to {value} V")
                                return
                self.scan_start_V=value

        @QtCore.pyqtSlot(int)
        def save_after_scan_checkBox_StateChanged(self,on):
                #print('done something with save_after_scan_checkBox')
                self.save_after_scan=on==2


        @QtCore.pyqtSlot(float)
        def step_doubleSpinBox_Edited(self,value):
                #print('done something with step_doubleSpinBox. Value=',value)
                if self.safe_limits:
                        if (value < self.Safe_Limits[0]) | (value > self.Safe_Limits[1]):
                                print(f"Given value exceded safe limits, turn off safe limits to allow to get to {value} V")
                                return
                self.step=value

        @QtCore.pyqtSlot(str)
        def name_lineEdit_textEdited(self,text):
                #print('done something with name_lineEdit. Text=',text)
                try:
                        self.name=text
                except:
                        pass

        @QtCore.pyqtSlot(bool)
        def start_scan_pushButton_Clicked(self,on):
                #print('done something with start_scan_pushButton')
                if not self.scanning:
                        process=threading.Thread(target=self.scan_voltages)
                        process.start()
                        self.scanning=True
                #self.scan_voltages()

        @QtCore.pyqtSlot(int)
        def safe_limits_checkBox_StateChanged(self,on):
                #print('done something with safe_limits_checkBox')
                self.safe_limits=on==2
                if self.safe_limits:
                        if (self.applied_voltage < self.Safe_Limits[0]):
                                self.applied_voltage_doubleSpinBox_Edited(self.Safe_Limits[0])
                                
                        elif (self.applied_voltage > self.Safe_Limits[1]):
                                self.applied_voltage_doubleSpinBox_Edited(self.Safe_Limits[1])