# -*- coding: utf-8 -*-

"""
This file contains a gui for the setupcontroll.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import os
import pyqtgraph as pg
import time

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from interface.simple_laser_interface import ControlMode, ShutterState, LaserState
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class SetupControlWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'setup_control.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class SetupControlGUI(GUIBase):

    ## declare connectors
    setupcontrollogic = Connector(interface='SetupControlLogic')
    #pulsedlogic= Connector(interface='SetupControlLogic')

    # sigA1 = QtCore.Signal(bool)
    # sigA2 = QtCore.Signal(bool)
    # sigRepump = QtCore.Signal(bool)
    # sigGreen = QtCore.Signal(bool)
    # sigMW1ON = QtCore.Signal(bool)
    # sigMW2ON = QtCore.Signal(bool)
    # sigMW3ON = QtCore.Signal(bool)
    # sigSetPower = QtCore.Signal(bool)
    # sigPDzero = QtCore.Signal(bool)
    # sigAutofocus = QtCore.Signal(bool)
    # sigFlipMirror = QtCore.Signal(bool)
    




    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """

        self._setupcontrol_logic = self.setupcontrollogic() 

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = SetupControlWindow()
        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        
        self.updateButtonsEnabled()
        self._mw.A1_Button.clicked.connect(self._setupcontrol_logic.A1_Button_Clicked)
        self._mw.A2_Button.clicked.connect(self._setupcontrol_logic.A2_Button_Clicked)
        self._mw.Repump_Button.clicked.connect(self._setupcontrol_logic.Repump_Button_Clicked)
        self._mw.Green_Button.clicked.connect(self._setupcontrol_logic.Green_Button_Clicked)
        self._mw.MW1_on_Button.clicked.connect(self._setupcontrol_logic.MW1_on_Button_Clicked)
        self._mw.MW1_power_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.MW1_power_DoubleSpinBox_Edited)
        self._mw.MW1_freq_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.MW1_freq_DoubleSpinBox_Edited)
        self._mw.MW2_on_Button.clicked.connect(self._setupcontrol_logic.MW2_on_Button_Clicked)
        self._mw.MW2_freq_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.MW2_freq_DoubleSpinBox_Edited)
        self._mw.MW2_power_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.MW2_power_DoubleSpinBox_Edited)
        self._mw.MW3_on_Button.clicked.connect(self._setupcontrol_logic.MW3_on_Button_Clicked)
        self._mw.MW3_freq_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.MW3_freq_DoubleSpinBox_Edited)
        self._mw.MW3_power_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.MW3_power_DoubleSpinBox_Edited)
        self._mw.Set_A2Power_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.Set_A2Power_DoubleSpinBox_Edited)
        self._mw.Set_A2Power_Button.clicked.connect(self._setupcontrol_logic.Set_A2Power_Button_Clicked)
        self._mw.Set_A1Power_DoubleSpinBox.valueChanged.connect(self._setupcontrol_logic.Set_A1Power_DoubleSpinBox_Edited)
        self._mw.Set_A1Power_Button.clicked.connect(self._setupcontrol_logic.Set_A1Power_Button_Clicked)
        self._mw.Read_A2Power_Button.clicked.connect(self._setupcontrol_logic.Read_A2Power_Button_Clicked)
        self._mw.Read_A1Power_Button.clicked.connect(self._setupcontrol_logic.Read_A1Power_Button_Clicked)
        self._mw.Autofocus_Button.clicked.connect(self._setupcontrol_logic.Autofocus_Button_Clicked)
        self._mw.Flipmirror_Button.clicked.connect(self._setupcontrol_logic.Flipmirror_Button_Clicked)
        self._mw.StartAutoMeas_Button.clicked.connect(self._setupcontrol_logic.StartAutoMeas_Button_Clicked)
        self._mw.StopAutoMeas_Button.clicked.connect(self._setupcontrol_logic.StopAutoMeas_Button_Clicked)
        self._mw.SavePOIs_Button.clicked.connect(self._setupcontrol_logic.SavePOIs_Button_Clicked)
        #self._setupcontrol_logic.SigReadPower.connect(self.update_laserpower, QtCore.Qt.QueuedConnection)
        
        self._mw.MW1_power_DoubleSpinBox.setValue(self._setupcontrol_logic.MW1_power)
        self._mw.MW3_freq_DoubleSpinBox.setValue(self._setupcontrol_logic.MW3_freq)
        self._mw.MW3_power_DoubleSpinBox.setValue(self._setupcontrol_logic.MW3_power)
        self._mw.MW2_power_DoubleSpinBox.setValue(self._setupcontrol_logic.MW2_power)
        self._mw.MW2_freq_DoubleSpinBox.setValue(self._setupcontrol_logic.MW2_freq)
        self._mw.MW1_freq_DoubleSpinBox.setValue(self._setupcontrol_logic.MW1_freq)
        self._mw.Set_A2Power_DoubleSpinBox.setValue(self._setupcontrol_logic.AOM_A2_volt)
        self._mw.Set_A1Power_DoubleSpinBox.setValue(self._setupcontrol_logic.AOM_A1_volt)

        # self._mw.Read_Power_Label.setText(str(self._setupcontrol_logic.read_power))
        
    # def update_laserpower(self):
    #     self._mw.Read_Power_Label.setText(str(self._setupcontrol_logic.read_power))


    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.A1_Button.clicked.disconnect()
        self._mw.A2_Button.clicked.disconnect()
        self._mw.Repump_Button.clicked.disconnect()
        self._mw.Green_Button.clicked.disconnect()
        self._mw.MW1_on_Button.clicked.disconnect()
        self._mw.MW1_power_DoubleSpinBox.valueChanged.disconnect()
        self._mw.MW1_freq_DoubleSpinBox.valueChanged.disconnect()
        self._mw.MW2_on_Button.clicked.disconnect()
        self._mw.MW2_power_DoubleSpinBox.valueChanged.disconnect()
        self._mw.MW2_freq_DoubleSpinBox.valueChanged.disconnect()
        self._mw.MW3_on_Button.clicked.disconnect()
        self._mw.MW3_power_DoubleSpinBox.valueChanged.disconnect()
        self._mw.MW3_freq_DoubleSpinBox.valueChanged.disconnect()
        self._mw.Set_A2Power_DoubleSpinBox.valueChanged.disconnect()
        self._mw.Set_A2Power_Button.clicked.disconnect()
        self._mw.Set_A1Power_DoubleSpinBox.valueChanged.disconnect()
        self._mw.Set_A1Power_Button.clicked.disconnect()
        self._mw.Read_A2Power_Button.clicked.disconnect()
        self._mw.Read_A1Power_Button.clicked.disconnect()
        self._mw.Autofocus_Button.clicked.disconnect()
        self._mw.Flipmirror_Button.clicked.disconnect()
        self._mw.StartAutoMeas_Button.clicked.disconnect()
        self._mw.StopAutoMeas_Button.clicked.disconnect()
        self._mw.SavePOIs_Button.clicked.disconnect()

        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
    
    def restoreDefaultView(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.adjustDockWidget.show()
        self._mw.plotDockWidget.show()

        # re-dock any floating dock widgets
        self._mw.adjustDockWidget.setFloating(False)
        self._mw.plotDockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.adjustDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.plotDockWidget)
    

    @QtCore.Slot()
    def updateButtonsEnabled(self):
        # """ Logic told us to update our button states, so set the buttons accordingly. """
        # self._mw.laserButton.setEnabled(self._laser_logic.laser_can_turn_on)
        # if self._laser_logic.laser_state == LaserState.ON:
        #     self._mw.laserButton.setText('Laser: ON')
        #     self._mw.laserButton.setChecked(True)
        #     self._mw.laserButton.setStyleSheet('')
        # elif self._laser_logic.laser_state == LaserState.OFF:
        #     self._mw.laserButton.setText('Laser: OFF')
        #     self._mw.laserButton.setChecked(False)
        # elif self._laser_logic.laser_state == LaserState.LOCKED:
        #     self._mw.laserButton.setText('INTERLOCK')
        # else:
        #     self._mw.laserButton.setText('Laser: ?')

        # self._mw.shutterButton.setEnabled(self._laser_logic.has_shutter)
        # if self._laser_logic.laser_shutter == ShutterState.OPEN:
        #     self._mw.shutterButton.setText('Shutter: OPEN')
        # elif self._laser_logic.laser_shutter == ShutterState.CLOSED:
        #     self._mw.shutterButton.setText('Shutter: CLOSED')
        # elif self._laser_logic.laser_shutter == ShutterState.NOSHUTTER:
        #     self._mw.shutterButton.setText('No shutter.')
        # else:
        #     self._mw.shutterButton.setText('Shutter: ?')

        # self._mw.currentRadioButton.setEnabled(self._laser_logic.laser_can_current)
        # self._mw.powerRadioButton.setEnabled(self._laser_logic.laser_can_power)
        self._mw.A1_Button.setCheckable(True)
        self._mw.A2_Button.setCheckable(True)
        self._mw.Green_Button.setCheckable(True)
        self._mw.Repump_Button.setCheckable(True)
        self._mw.MW1_on_Button.setCheckable(True)
        self._mw.MW2_on_Button.setCheckable(True)
        self._mw.MW3_on_Button.setCheckable(True)
        self._mw.Set_A2Power_Button.setCheckable(False)
        self._mw.Set_A1Power_Button.setCheckable(False)
        # self._mw.PD_zero_Button.setCheckable(True)
        # self._mw.Flipmirror_Button.setCheckable(True)
        # self._mw.Autofocus_Button.setCheckable(True)

    def A1_time_edited(self,val):
        print(val)
        A1duration=self._mw.A1_time_doubleSpinBox.value()
        self._setupcontrol_logic.A1time=A1duration
        print("oh")


# TODO: Remove POIs button
# "scannerlogic.pois = np.array([])"

# TODO: Start automized measurement
# "automationlogic.start()"