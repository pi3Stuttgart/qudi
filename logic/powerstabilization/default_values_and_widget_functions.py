import threading
from PyQt5 import QtCore
class powerstabilization_default():

        TargetPower: float = 10
        TargetVoltage: float = 1
        A1Voltage: float = 0
        A2Voltage: float = 0
        current_power: float = 0
        current_voltage: float = 0
        controlA1: bool = False
        controlA2: bool = True
        voltage_offset: float = 0.0000
        voltage_to_power_ratio: float = 0.1402 #V/nW
        stabilizing: bool = False
        P1_var: float = 0.05
        I1_var: float = 0.1
        D1_var: float = 0.0001
        datapoints : int = 500
        sleep_time: int = 100
                
        @QtCore.pyqtSlot(str)
        def TargetPower_LineEdit_textEdited(self, input):
                print("Done something with TargetPower_LineEdit_textEdited. Text=", input)
                try:
                        self.TargetPower = float(input)
                        self.TargetVoltage = self.power_to_voltage(self.TargetPower)#/1e9
                        print("Target Voltage: ", self.TargetVoltage)
                except:
                        print("Input not a float")

        @QtCore.pyqtSlot(str)
        def A1Voltage_LineEdit_textEdited(self, input):
                print("Done something with A1Voltage_LineEdit_textEdited. Text=", input)
                try:
                        self.A1Voltage = float(input)
                except:
                        print("Input not a float")

        @QtCore.pyqtSlot(str)
        def A2Voltage_LineEdit_textEdited(self, input):
                print("Done something with A2Voltage_LineEdit_textEdited. Text=", input)
                try:
                        self.A2Voltage = float(input)
                except:
                        print("Input not a float")

        @QtCore.pyqtSlot(bool)
        def A1Voltage_PushButton_Clicked(self, state):
                print("Done something with A1Voltage_PushButton_Clicked")
                self.set_fix_voltage("A1")

        @QtCore.pyqtSlot(bool)
        def A2Voltage_PushButton_Clicked(self, state):
                print("Done something with A2Voltage_PushButton_Clicked")
                self.set_fix_voltage("A2")

        @QtCore.pyqtSlot(bool)
        def Offset_PushButton_Clicked(self, state):
                print("Done something with Offset_PushButton_Clicked")
                # TODO: Turn off lasers
                self.voltage_offset = self.pid1.output
        

        @QtCore.pyqtSlot(bool)
        def SaveTrace_PushButton_Clicked(self, state):
                print("Done something with SaveTrace_PushButton_Clicked")
                print("Not yet implemented")

        @QtCore.pyqtSlot(str)
        def Data_Points_LineEdit_textEdited(self,input):
                print("Done something with Data_Points_LineEdit_textEdited. Text=", input)
                try:
                        self.datapoints = int(input)
                except:
                        print("Input not an int")

        @QtCore.pyqtSlot(bool)
        def On_RadioButton_clicked(self,on):
                print("Done something with On_RadioButton_clicked.")
                self.SigStartControl.emit()

        @QtCore.pyqtSlot(bool)
        def Off_RadioButton_clicked(self,on):
                print("Done something with Off_RadioButton_clicked.")
                self.SigStopControl.emit()

        @QtCore.pyqtSlot(bool)
        def A1_RadioButton_clicked(self,on):
                print("Done something with A1_RadioButton_clicked")
                self.controlA1 = True
                self.controlA2 = False

        @QtCore.pyqtSlot(bool)
        def A2_RadioButton_clicked(self,on):
                print("Done something with A2_RadioButton_clicked")
                self.controlA1 = False
                self.controlA2 = True