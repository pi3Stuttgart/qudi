import threading
from PyQt5 import QtCore
class powerstabilization_default():

        TargetPower: float = 10
        TargetVoltage: float = 1
        A1Voltage: float = 0
        A2Voltage: float = 0
        current_power: float = 0
        current_voltage: float = 0
        voltage_offset: float = 0.0000
        voltage_to_power_ratio: float = 0.1402 #V/nW
        stabilizing: bool = False
        datapoints : int = 500
        sleep_time: int = 200
                
        @QtCore.pyqtSlot(str)
        def TargetPower_LineEdit_textEdited(self, input):
                print("Done something with TargetPower_LineEdit_textEdited. Text=", input)
                try:
                        self.TargetPower = float(input)
                        self.TargetVoltage = self.power_to_voltage(self.TargetPower)#/1e9
                        print("Target Voltage: ", self.TargetVoltage)
                except:
                        print("Input not a float")

        @QtCore.pyqtSlot(bool)
        def A1_PushButton_Clicked(self, state):
                #self.set_power(self.TargetPower)
                print("Not yet implemented")

        @QtCore.pyqtSlot(bool)
        def A2_PushButton_Clicked(self, state):
                self.set_power(self.TargetPower)

        @QtCore.pyqtSlot(bool)
        def Offset_PushButton_Clicked(self, state):
                print("Not yet implemented")
                # TODO: Turn off lasers
                #self.voltage_offset = self.pid1.output

        @QtCore.pyqtSlot(bool)
        def Calibrate_PushButton_Clicked(self, state):
                print("Done something with Calibrate_PushButton_Clicked")
                self.calibrate_power()
        

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