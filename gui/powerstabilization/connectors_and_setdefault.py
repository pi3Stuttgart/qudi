from PyQt5 import QtCore
class powerstab_default_gui():
        def initialize_connections_and_defaultvalues(self):
                #set the default values to the text line
                self._mw.TargetPower_LineEdit.setText(str(self._power_stabilization.TargetPower))
                self._mw.Data_Points_LineEdit.setText(str(self._power_stabilization.datapoints))
                
                self._mw.PowerValue_Label.setText(str(self._power_stabilization.current_power))
                self._mw.VoltageValue_Label.setText(str(self._power_stabilization.current_voltage))
                self._mw.AOM_Volt_label.setText(str(self._power_stabilization.current_voltage))

                # connect all the changeable widgets
                self._mw.TargetPower_LineEdit.textEdited.connect(self._power_stabilization.TargetPower_LineEdit_textEdited,type=QtCore.Qt.QueuedConnection)
                self._mw.Data_Points_LineEdit.textEdited.connect(self._power_stabilization.Data_Points_LineEdit_textEdited,type=QtCore.Qt.QueuedConnection)


                self._mw.A1_PushButton.clicked.connect(self._power_stabilization.A1_PushButton_Clicked,type=QtCore.Qt.QueuedConnection)
                self._mw.A2_PushButton.clicked.connect(self._power_stabilization.A2_PushButton_Clicked,type=QtCore.Qt.QueuedConnection)
                self._mw.Calibrate_PushButton.clicked.connect(self._power_stabilization.Calibrate_PushButton_Clicked,type=QtCore.Qt.QueuedConnection)
                self._mw.Offset_PushButton.clicked.connect(self._power_stabilization.Offset_PushButton_Clicked,type=QtCore.Qt.QueuedConnection)
                self._mw.SaveTrace_PushButton.clicked.connect(self._power_stabilization.SaveTrace_PushButton_Clicked,type=QtCore.Qt.QueuedConnection)

        def disconnect_all(self):
                self._mw.TargetPower_LineEdit.textEdited.disconnect()
                self._mw.A1_PushButton.clicked.disconnect()
                self._mw.A2_PushButton.clicked.disconnect()
                self._mw.Offset_PushButton.clicked.disconnect()
                self._mw.Calibrate_PushButton.clicked.disconnect()
                self._mw.SaveTrace_PushButton.clicked.disconnect()