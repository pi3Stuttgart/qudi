class powerstabilization_default():

        TargetPower: float = 0
        TargetVoltage: float = 1
        A1Voltage: float = 0
        A2Voltage: float = 0
        current_power: float = 0
        current_voltage: float = 0
        controlA1: bool =False
        controlA2: bool =True
        voltage_offset: float = 0.01651
        voltage_to_power_ratio: float = 6.7485e-3 #V to nW
        running: bool = False
        P1_var: float = 1
        I1_var: float = 0.1
        D1_var: float = 0.1
                

        def TargetPower_LineEdit_textEdited(self, input):
                print("Done something with TargetPower_LineEdit_textEdited. Text=", input)
                try:
                        self.TargetPower = float(input)
                        self.TargetVoltage = self.power_to_voltage(self.TargetPower)
                        print("Target Voltage: ", self.TargetVoltage)
                except:
                        print("Input not a float")

        def A1Voltage_LineEdit_textEdited(self, input):
                print("Done something with A1Voltage_LineEdit_textEdited. Text=", input)
                try:
                        self.A1Voltage = float(input)
                except:
                        print("Input not a float")
        def A2Voltage_LineEdit_textEdited(self, input):
                print("Done something with A2Voltage_LineEdit_textEdited. Text=", input)
                try:
                        self.A2Voltage = float(input)
                except:
                        print("Input not a float")


        def A1Voltage_PushButton_Clicked(self, state):
                print("Done something with A1Voltage_PushButton_Clicked")
                self.set_fix_voltage("A1")

        def A2Voltage_PushButton_Clicked(self, state):
                print("Done something with A2Voltage_PushButton_Clicked")
                self.set_fix_voltage("A2")

        def Offset_PushButton_Clicked(self, state):
                print("Done something with Offset_PushButton_Clicked")
                print("Not yet implemented")

        def SaveTrace_PushButton_Clicked(self, state):
                print("Done something with SaveTrace_PushButton_Clicked")
                print("Not yet implemented")



        def On_RadioButton_clicked(self):
                print("Done something with On_RadioButton_clicked.")
                self.start_control()

        def Off_RadioButton_clicked(self):
                print("Done something with Off_RadioButton_clicked.")
                self.stop_control()

        def A1_RadioButton_clicked(self):
                print("Done something with A1_RadioButton_clicked")
                self.controlA1 = True
                self.controlA2 = False

        def A2_RadioButton_clicked(self):
                print("Done something with A2_RadioButton_clicked")
                self.controlA1 = False
                self.controlA2 = True