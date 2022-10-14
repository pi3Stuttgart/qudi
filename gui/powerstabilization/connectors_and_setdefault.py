class powerstab_default_gui():
        def initialize_connections_and_defaultvalues(self):
                #set the default values to the text line
                self._mw.TargetPower_LineEdit.setText(str(self._power_stabilization.TargetPower))
                self._mw.A1Voltage_LineEdit.setText(str(self._power_stabilization.A1Voltage))
                self._mw.A2Voltage_LineEdit.setText(str(self._power_stabilization.A2Voltage))

                # self._mw.On_RadioButton.setChecked(self._power_stabilization.On_rb)
                # self._mw.Off_RadioButton.setChecked(self._power_stabilization.Off_rb)
                # self._mw.A1_RadioButton.setChecked(self._power_stabilization.A1_rb)
                # self._mw.A2_RadioButton.setChecked(self._power_stabilization.A2_rb)

                self._mw.PowerValue_Label.setText(str(self._power_stabilization.current_power))
                self._mw.VoltageValue_Label.setText(str(self._power_stabilization.current_voltage))

                # connect all the changeable widgets
                self._mw.TargetPower_LineEdit.textEdited.connect(self._power_stabilization.TargetPower_LineEdit_textEdited)
                self._mw.A1Voltage_LineEdit.textEdited.connect(self._power_stabilization.A1Voltage_LineEdit_textEdited)
                self._mw.A2Voltage_LineEdit.textEdited.connect(self._power_stabilization.A2Voltage_LineEdit_textEdited)

                self._mw.A1Voltage_PushButton.clicked.connect(self._power_stabilization.A1Voltage_PushButton_Clicked)
                self._mw.A2Voltage_PushButton.clicked.connect(self._power_stabilization.A2Voltage_PushButton_Clicked)
                self._mw.Offset_PushButton.clicked.connect(self._power_stabilization.Offset_PushButton_Clicked)
                self._mw.SaveTrace_PushButton.clicked.connect(self._power_stabilization.SaveTrace_PushButton_Clicked)

                self._mw.On_RadioButton.clicked.connect(self._power_stabilization.On_RadioButton_clicked)
                self._mw.Off_RadioButton.clicked.connect(self._power_stabilization.Off_RadioButton_clicked)
                self._mw.A1_RadioButton.clicked.connect(self._power_stabilization.A1_RadioButton_clicked)
                self._mw.A2_RadioButton.clicked.connect(self._power_stabilization.A2_RadioButton_clicked)

        def disconnect_all(self):
                self._mw.TargetPower_LineEdit.textEdited.disconnect()
                self._mw.A1Voltage_LineEdit.textEdited.disconnect()
                self._mw.A2Voltage_LineEdit.textEdited.disconnect()
                self._mw.A1Voltage_PushButton.clicked.disconnect()
                self._mw.A2Voltage_PushButton.clicked.disconnect()
                self._mw.Offset_PushButton.clicked.disconnect()
                self._mw.SaveTrace_PushButton.clicked.disconnect()
                self._mw.On_RadioButton.clicked.disconnect()
                self._mw.Off_RadioButton.clicked.disconnect()
                self._mw.A1_RadioButton.clicked.disconnect()
                self._mw.A2_RadioButton.clicked.disconnect()
