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

import numpy as np
import os
import pyqtgraph as pg

from collections import OrderedDict
from core.connector import Connector
from gui.colordefs import ColorScaleInferno
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic



class TestMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'test_gui.ui')

        # Load it
        super(TestMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class TestGui(GUIBase):
   
    # declare connectors
    testlogic1 = Connector(interface='TestLogic')
    
    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self._mw = TestMainWindow()
        self._test_logic=self.testlogic1()
        self._mw.Start_pushButton.clicked.connect(self.start_measurement,type=QtCore.Qt.QueuedConnection)
        self._mw.Stop_pushButton.clicked.connect(self.stop_measurement,type=QtCore.Qt.QueuedConnection)
        self._test_logic.sigUpdateLabel.connect(self.update_label,type=QtCore.Qt.QueuedConnection)
        self.sigStart.connect(self._test_logic.start,type=QtCore.Qt.QueuedConnection)
        self.sigStop.connect(self._test_logic.stop,type=QtCore.Qt.QueuedConnection)


    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    @QtCore.pyqtSlot()
    def start_measurement(self):
        print("gui start")
        self.sigStart.emit()
        print('MyObject signal thread (gui start):', str(int(QtCore.QThread.currentThreadId())))

    @QtCore.pyqtSlot()
    def stop_measurement(self):
        print("gui stop")
        self.sigStop.emit()
        print('MyObject signal thread (gui stop):', str(int(QtCore.QThread.currentThreadId())))
    
    @QtCore.pyqtSlot()
    def update_label(self):
        self._mw.value_label.setText(str(self._test_logic.value))
        print('MyObject signal thread (label):', str(int(QtCore.QThread.currentThreadId())))
        
