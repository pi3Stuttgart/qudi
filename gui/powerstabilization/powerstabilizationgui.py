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
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

from gui.powerstabilization.connectors_and_setdefault import powerstab_default_gui as powerstab_default_gui


class PowerControlMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_power_control.ui')

        # Load it
        super().__init__(**kwargs)
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
    
    # sigStartCounter = QtCore.Signal()
    # sigStopCounter = QtCore.Signal()

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
        self._mw.power_trace_PlotWidget.setLabel(axis='left', text='Power', units='nW')
        self._mw.power_trace_PlotWidget.setLabel(axis='bottom', text='Time', units='s')
        self._mw.power_trace_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # self._counting_logic.sigCounterUpdated.connect(self.updateData)
        # self._counting_logic.sigCountingSamplesChanged.connect(self.update_oversampling_SpinBox)
        # self._counting_logic.sigCountLengthChanged.connect(self.update_count_length_SpinBox)
        # self._counting_logic.sigCountFrequencyChanged.connect(self.update_count_freq_SpinBox)
        # self._counting_logic.sigSavingStatusChanged.connect(self.update_saving_Action)
        # self._counting_logic.sigCountingModeChanged.connect(self.update_counting_mode_ComboBox)
        # self._counting_logic.sigCountStatusChanged.connect(self.update_count_status_Action)

        # self.show()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        self.disconnect_all()

        # self.sigStartCounter.disconnect()
        # self.sigStopCounter.disconnect()
        self._mw.close()
        return
        
    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self.disconnect_all()
        
        # self._odmr_logic.sigOdmrPlotsUpdated.disconnect() # TODO: disconnect all used signals

        self._mw.close()

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
    
    def update_plots(self, data_x=None, data_y=None):
        #data_x=self._odmr_logic.ODMRLogic.mw1_freq*1e6
        #data_y=self._odmr_logic.ODMRLogic.data
        data_x = np.arange(20)
        data_y = random.randint(100, size=(20))
        self.laserpower_image.setData(data_x, data_y)