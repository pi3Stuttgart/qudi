# -*- coding: utf-8 -*-

"""
This file contains the Qudi counter gui.

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
import random
from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import uic

from gui.powerstabilization.connectors_and_setdefault import powerstab_default_gui as powerstab_default_gui


class PowerControlMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_power_control2.ui')

        # Load it
        super(PowerControlMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PowerStabilizationGui(GUIBase, powerstab_default_gui):
    ''' Config Example
    powerstabilizationgui:
            module.Class: 'powerstabilizationgui.PowerStabilizationGui'
            connect:
                powerstabilizationlogic: 'powerstabilizationlogic'
    '''


    # declare connectors
    powerstabilizationlogic = Connector(interface='PowerStabilizationLogic')
    


    def __init__(self, config, **kwargs):
        print("Init")
        super().__init__(config=config, **kwargs)
        
    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        
        self._mw = PowerControlMainWindow()
        self._power_stabilization = self.powerstabilizationlogic()
        self._power_stabilization.SigUpdatePlots.connect(self.update_plots,type=QtCore.Qt.QueuedConnection)
        self._power_stabilization.SigStabilized.connect(self.set_stabilization_to_off,type=QtCore.Qt.QueuedConnection)

        self.initialize_connections_and_defaultvalues()
        
        self.laserpower_image = pg.PlotDataItem(
            np.arange(20),
            np.zeros(20),
            pen=pg.mkPen(pg.mkColor(255, 255, 255), style=QtCore.Qt.DotLine),
            symbol='o',
            symbolPen=pg.mkColor(255, 255, 255),
            symbolBrush=pg.mkColor(255, 255, 255),
            symbolSize=7)

        # self.laserpower_image.setRect(
        #     QtCore.QRectF(
        #         self._voltscan_logic.scan_range[0],
        #         0,
        #         self._voltscan_logic.scan_range[1] - self._voltscan_logic.scan_range[0],
        #         self._voltscan_logic.number_of_repeats)
        # )

        self._mw.power_trace_PlotWidget.addItem(self.laserpower_image)
        self._mw.power_trace_PlotWidget.setLabel(axis='left', text='Power', units='W')
        self._mw.power_trace_PlotWidget.setLabel(axis='bottom', text='Time', units='s')
        self._mw.power_trace_PlotWidget.showGrid(x=True, y=True, alpha=0.8)


    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self.disconnect_all()
        self._mw.close()
        return
        

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
    
    def set_stabilization_to_off(self):
        self._mw.Off_RadioButton.toggle()

    @QtCore.pyqtSlot()
    def update_plots(self, data_x=None, data_y=None):
        
        #data_x=self._odmr_logic.ODMRLogic.mw1_freq*1e6
        #data_y=self._odmr_logic.ODMRLogic.data
        self._mw.PowerValue_Label.setText(str(round(self._power_stabilization.current_power,2))[:5]+"nW")
        self._mw.VoltageValue_Label.setText(str(round(self._power_stabilization.feedback_voltage-self._power_stabilization.voltage_offset,4))+"V")
        self._mw.AOM_1_Volt_label.setText(str(round(self._power_stabilization._setupcontrol_logic.AOM_A1_volt,2))+"V to AOM A1")
        self._mw.AOM_2_Volt_label.setText(str(round(self._power_stabilization._setupcontrol_logic.AOM_A2_volt,2))+"V to AOM A2")
        data_y = np.asarray(self._power_stabilization.power_list)[-self._power_stabilization.datapoints:]*1e-9
        data_x = np.arange(len(data_y))*self._power_stabilization.sleep_time
        self.laserpower_image.setData(data_x, data_y)