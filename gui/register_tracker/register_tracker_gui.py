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


class RegisterTrackerWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'register.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class RegisterTrackerGUI(GUIBase):

    ## declare connectors
    transition_tracker_logic = Connector(interface='TransitionTracker')
    
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """

        self._tt = self.transition_tracker_logic() 

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = RegisterTrackerWindow()
        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        
        self.updateButtonsEnabled()
        self._mw.A1_Button.clicked.connect(self._setupcontrol_logic.A1_Button_Clicked)
        self._mw.A2_Button.clicked.connect(self._setupcontrol_logic.A2_Button_Clicked)

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
        self._mw.Set_Power_DoubleSpinBox.valueChanged.disconnect()
        self._mw.repump_power_doubleSpinBox.valueChanged.disconnect()

        self._mw.Set_Power_Button.clicked.disconnect()
        self._mw.Read_Power_Button.clicked.disconnect()
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
        self._mw.Set_Power_Button.setCheckable(False)
        # self._mw.PD_zero_Button.setCheckable(True)
        # self._mw.Flipmirror_Button.setCheckable(True)
        # self._mw.Autofocus_Button.setCheckable(True)