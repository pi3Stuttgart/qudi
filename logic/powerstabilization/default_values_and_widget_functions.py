import threading
from PyQt5 import QtCore
class powerstabilization_default():

        TargetPower: float = 10
        Wavelength: int = 920
        TargetVoltage: float = 1
        A1Voltage: float = 0
        A2Voltage: float = 0
        current_power: float = 0
        current_voltage: float = 0
        voltage_offset_dict: dict = {
                880: -0.101129,
                890: 0.132278,
                900: 0.123411,
                910: 0.083189,
                920: 0.085577,
                930: -0.206446,
                940: -0.043606,
                950: 0.078632,
                }
        voltage_to_power_ratio_dict: dict = {
                880: 5.23e-4, 
                890: 4.2e-4,
                900: 4.3e-4,
                910: 4.55e-4,
                920: 4.16e-4,
                930: 5.95e-4,
                940: 5.18e-4,
                950: 5.31e-4,
                } 
        voltage_offset: float = voltage_offset_dict[Wavelength]
        voltage_to_power_ratio: float = voltage_to_power_ratio_dict[Wavelength] #V/nW
        voltage_offset_A1A2: float = 0.0
        voltage_to_power_ratio_A1A2: float = 0.1402 #V/nW
        voltage_offset_730: float = 0.041678
        voltage_to_power_ratio_730: float = 1.409e-6 #V/nW
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

        @QtCore.pyqtSlot(str)
        def Wavelength_LineEdit_textEdited(self, input):
                print("Done something with Wavelength_LineEdit_textEdited. Text=", input)
                try:    
                        if input == "0917":
                                pass
                                self.Wavelength = float(input)
                                print("Wavelength: ", self.Wavelength)
                                self.voltage_offset = self.voltage_offset_A1A2
                                self.voltage_to_power_ratio = self.voltage_to_power_ratio_A1A2
                                print("voltage_offset changed to A1/A2 values: ", self.voltage_offset)
                                print("voltage_to_power_ratio changed to A1/A2 values: ", self.voltage_to_power_ratio)
                        elif input == "0730":
                                pass
                                self.Wavelength = float(input)
                                print("Wavelength: ", self.Wavelength)
                                self.voltage_offset = self.voltage_offset_730
                                self.voltage_to_power_ratio = self.voltage_to_power_ratio_730
                                print("voltage_offset changed to 730 values: ", self.voltage_offset)
                                print("voltage_to_power_ratio changed to 730 values: ", self.voltage_to_power_ratio)
                        else:
                                self.Wavelength = float(input)
                                print("Wavelength: ", self.Wavelength)
                                self.voltage_offset = self.voltage_offset_dict[min(self.voltage_offset_dict,key=lambda x:abs(x-self.Wavelength))]
                                self.voltage_to_power_ratio = self.voltage_to_power_ratio_dict[min(self.voltage_to_power_ratio_dict,key=lambda x:abs(x-self.Wavelength))]
                                print("voltage_offset changed to: ", self.voltage_offset)
                                print("voltage_to_power_ratio changed to: ", self.voltage_to_power_ratio)
                        self.load_calibration()
                except:
                        print("Input not a float")
                        print("voltage_offset like before: ", self.voltage_offset)
                        print("voltage_to_power_ratio like before: ", self.voltage_to_power_ratio)

        @QtCore.pyqtSlot(bool)
        def A1_PushButton_Clicked(self, state):
                self.set_power_A1(self.TargetPower)

        @QtCore.pyqtSlot(bool)
        def A2_PushButton_Clicked(self, state):
                self.set_power_A2(self.TargetPower)

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

        def load_calibration(self):#
                pass