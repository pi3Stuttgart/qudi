# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module to operate the voltage (laser) scanner.
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

#TODO carefull disconnection
from email.policy import default
import os
from tkinter import Y
import numpy as np
import copy as cp
from typing import Union, Tuple
from functools import partial
from PySide2 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

import qudi.util.uic as uic
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.core.module import GuiBase
from qudi.gui.ple.ple_ui_window import PLEScanMainWindow
from qudi.util.widgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox

class PulsedPlottingMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_plotting.ui')

        # Load it
        super().__init__()

        uic.loadUi(ui_file, self)

class PulsedPlotting(GuiBase):

    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)
    _save_display_view = StatusVar(name='save_display_view', default=None)
    _plotting_logic = Connector(name='plotter', interface= 'PulsedPlottingLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_deactivate(self):
        """ Reverse steps of activation
        @return int: error code (0:OK, -1:error)
        """
        self._save_window_geometry(self._mw)
        self.save_view()
        self._mw.close()
        return 0

    def on_activate(self):
        self._mw = PulsedPlottingMainWindow()
        self._mw.show()
        self.plotting_logic = self._plotting_logic()

        self.plotting_logic.sigPulsedPlotUpdated.connect(self.update_plot, QtCore.Qt.QueuedConnection)

        self._pw = self._mw.TimingDiagramGraphicsView
        self.color = []
        self.color.append(pg.mkColor(17,95,154))
        self.color.append(pg.mkColor(153,31,23))
        self.color.append(pg.mkColor(118,198,143))
        self.color.append(pg.mkColor(255,180,0))
        self.color.append(pg.mkColor(226, 124, 124))
        self.color.append(pg.mkColor(144, 128, 255))

        self.curves = {}
        self.label = {}
        # self.legend1 = pg.LegendItem()
        for i, ch in enumerate(self.plotting_logic.pulsed.digital_channels):
            self.curves[ch] = pg.PlotCurveItem(pen=pg.mkPen(self.color[i], cosmetic=True),
                                                clipToView=True,
                                                downsampleMethod='subsample',
                                                autoDownsample=True,
                                                antialias=True)

            self._pw.addItem(self.curves[ch])
            self.label[ch] = pg.TextItem(text=f'{ch}', color=self.color[i], anchor=(0+i*-1, 0))
            self.label[ch].setPos(0,0)
                        
            # self.legend1.addItem(self.curves[ch], ch)
            
        # self.legend1.setParentItem(self.curves[ch])
        self._pw.setLabel('bottom', 'Time', units='s')
        self._pw.setLabel('left', 'Level', units='arb.')
        
        # self._pw.setMouseEnabled(x=False, y=False)
        # self._pw.setMouseTracking(False)
        # self._pw.setMenuEnabled(False)
        # self._pw.hideButtons()
        
    
    def show(self):
        """Make window visible and put it above all other windows.
        """
        self._mw.show()
        self._mw.raise_()
        self._mw.activateWindow()
    
    def update_plot(self, data):
        r = 0
        items = self._pw.items()
        
        for i, ch in enumerate(self.plotting_logic.pulsed.digital_channels):
            x_arr, y_arr = data[ch]
            zero = y_arr.any()
            
            if not zero and self.curves[ch] in items:
                self._pw.removeItem(self.curves[ch])
            elif zero and not self.curves[ch] in items:
                self._pw.addItem(self.curves[ch])
            
            if not zero and self.label[ch] in items:
                self._pw.removeItem(self.label[ch])
            elif zero and not self.label[ch] in items:
                self._pw.addItem(self.label[ch])

            if y_arr.any():
                self.curves[ch].setData(y=y_arr+0.31*r, x=x_arr, fillLevel=0+0.31*r, brush=self.color[i])
                r += 1
    
    def save_view(self):
        """Saves the current GUI state as a QbyteArray.
           The .data() function will transform it to a bytearray, 
           which can be saved as a StatusVar and read by the load_view method. 
        """
        self._save_display_view = self._mw.saveState().data() 
        
    def load_view(self):
        """Loads the saved state from the GUI and can read a QbyteArray
            or a simple byteArray aswell.
        """
        if self._save_display_view is None:
            pass
        else:
            self._mw.restoreState(self._save_display_view)
        