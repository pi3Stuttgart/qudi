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


class AutomizedMeasurementWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'automized_measurement.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class AutomizedMeasurementGUI(GUIBase):

    ## declare connectors
    automizedmeasurementlogic = Connector(interface='AutomizedMeasurementLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """

        self.automized_measurement_logic = self.automizedmeasurementlogic() 

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = AutomizedMeasurementWindow()
        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        
        self.updateButtonsEnabled()
        
        
        self._mw.StartAutoMeas_Button.clicked.connect(self.automized_measurement_logic.StartAutoMeas_Button)
        self._mw.StopAutoMeas_Button.clicked.connect(self.automized_measurement_logic.StartAutoMeas_Button)
        self._mw.SavePOIs_Button.clicked.connect(self.automized_measurement_logic.StartAutoMeas_Button)
        self._mw.DeletePOIs_Button.clicked.connect(self.automized_measurement_logic.StartAutoMeas_Button)
        self._mw.SetSequence_Button.clicked.connect(self.automized_measurement_logic.StartAutoMeas_Button)
        self._mw.SetBackgroundSeq_Button.clicked.connect(self.automized_measurement_logic.StartAutoMeas_Button)
        
        self._mw.Sequence_lineEdit.textChanged.connect(self.automized_measurement_logic.Sequence_lineEdit)
        self._mw.Background_lineEdit.textChanged.connect(self.automized_measurement_logic.Background_lineEdit)
        self._mw.SaveFolder_lineEdit.textChanged.connect(self.automized_measurement_logic.SaveFolder_lineEdit)
        

        # self._setupcontrol_logic.SigReadPower.connect(self.update_laserpower, QtCore.Qt.QueuedConnection)
        
        # self._mw.Read_Power_Label.setText(str(self._setupcontrol_logic.read_power))
        
    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.StartAutoMeas_Button.clicked.disconnect()
        self._mw.StopAutoMeas_Button.clicked.disconnect()
        self._mw.SavePOIs_Button.clicked.disconnect()
        self._mw.DeletePOIs_Button.clicked.disconnect()
        self._mw.SetSequence_Button.clicked.disconnect()
        self._mw.SetBackgroundSeq_Button.clicked.disconnect()
        self._mw.SaveFolder_Button.clicked.disconnect()

        self._mw.Sequence_lineEdit.textChanged.disconnect()
        self._mw.Background_lineEdit.textChanged.disconnect()
        self._mw.SaveFolder_lineEdit.textChanged.disconnect()
       
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
       
        self._mw.StartAutoMeas_Button.setCheckable(True)
        self._mw.StopAutoMeas_Button.setCheckable(True)
        self._mw.SavePOIs_Button.setCheckable(True)
        self._mw.DeletePOIs_Button.setCheckable(True)
        self._mw.SetSequence_Button.setCheckable(True)
        self._mw.SetBackgroundSeq_Button.setCheckable(True)



# TODO: Remove POIs button
# "scannerlogic.pois = np.array([])"

# TODO: Start automized measurement
# "automationlogic.start()"