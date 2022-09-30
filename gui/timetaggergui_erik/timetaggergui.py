# -*- coding: utf-8 -*-

"""
This file contains a gui for the ODMR.

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
from gui.colordefs import ColorScaleInferno
from gui.guiutils import ColorBar
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class TimeTaggerWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_TT_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class TimeTaggerGUI(GUIBase):

    ## declare connectors
    timetaggerlogic = Connector(interface='TimeTaggerLogic')
    

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
    
    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """

        #self._setupcontrol_logic = self.setupcontrollogic() 
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = TimeTaggerWindow()
        self._timetagger_logic= self.timetaggerlogic()
        
        self._mw.Filename_lineEdit.setText(str(self._timetagger_logic.filename))
        self._mw.Stoptime_lineEdit.setText(str(self._timetagger_logic.stoptime))
        self._mw.PeriodicSaving_CheckBox.setChecked(self._timetagger_logic.periodicsaving)
        self._mw.Runtime_Label.setText(str(self._timetagger_logic.runtime))


        
        self._mw.Filename_lineEdit.textEdited.connect(self._timetagger_logic.Filename_lineEdit_textEdited)
        self._mw.Stoptime_lineEdit.textEdited.connect(self._timetagger_logic.Stoptime_lineEdit_textEdited)
        self._mw.Interval_lineEdit.textEdited.connect(self._timetagger_logic.Interval_lineEdit_textEdited)
        self._mw.CounterClickChannel_lineEdit.textEdited.connect(self._timetagger_logic.CounterClickChannel_lineEdit_textEdited)
        self._mw.ClickChannel_lineEdit.textEdited.connect(self._timetagger_logic.ClickChannel_lineEdit_textEdited)
        self._mw.StartChannel_lineEdit.textEdited.connect(self._timetagger_logic.StartChannel_lineEdit_textEdited)
        self._mw.NextChannel_lineEdit.textEdited.connect(self._timetagger_logic.NextChannel_lineEdit_textEdited)
        self._mw.SyncChannel_lineEdit.textEdited.connect(self._timetagger_logic.SyncChannel_lineEdit_textEdited)
        self._mw.CounterBinwidth_lineEdit.textEdited.connect(self._timetagger_logic.CounterBinwidth_lineEdit_textEdited)
        self._mw.Binwidth_lineEdit.textEdited.connect(self._timetagger_logic.Binwidth_lineEdit_textEdited)
        self._mw.NumberOfBins_lineEdit.textEdited.connect(self._timetagger_logic.NumberOfBins_lineEdit_textEdited)
        self._mw.Datapoints_lineEdit.textEdited.connect(self._timetagger_logic.Datapoints_lineEdit_textEdited)
        
        self._mw.PeriodicSaving_CheckBox.stateChanged.connect(self._timetagger_logic.PeriodicSaving_CheckBox_StateChanged)
                
        self._mw.Counter_Button.clicked.connect(self._timetagger_logic.Counter_Button_Clicked)
        self._mw.Histogram_Button.clicked.connect(self._timetagger_logic.Histogram_Button_Clicked)
        self._mw.TimeDiff_Button.clicked.connect(self._timetagger_logic.TimeDiff_Button_Clicked)
        self._mw.Stop_Button.clicked.connect(self._timetagger_logic.Stop_Button_Clicked)
        self._mw.Continue_Button.clicked.connect(self._timetagger_logic.Continue_Button_Clicked)
        self._mw.Save_Button.clicked.connect(self._timetagger_logic.Save_Button_Clicked)
        self._mw.Load_Button.clicked.connect(self._timetagger_logic.Load_Button_Clicked)
        
        #connect the signals:
        self._timetagger_logic.sigTimeTaggerPlotsUpdated.connect(self.update_plots, QtCore.Qt.QueuedConnection)
        #self._timetagger_logic.SigClock.connect(self.Update_Runtime, QtCore.Qt.QueuedConnection)
        
        #get the number of points the Timetagger counter will return:
        self.number_of_points_per_line=self._timetagger_logic._time_tagger._counter["n_values"]

        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()

        #################### setup graphics for cw ODMR
        # self.Histogram_matrix_image = pg.ImageItem(
        #     #self.__timetagger_logic.odmr_plot_xy[:, self.display_channel],
        #     np.random.rand(40, 20),
        #     axisOrder='row-major')

        # self.Histogram_matrix_image.setRect(QtCore.QRectF(
        #     70,
        #     0,
        #     40,
        #     20
        # ))

        self.Histogram_image = pg.PlotDataItem(
                                          np.arange(20),
                                          np.arange(20),
                                          pen=pg.mkPen(pg.mkColor(255, 255, 255), style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=pg.mkColor(255, 255, 255),
                                          symbolBrush=pg.mkColor(255, 255, 255),
                                          symbolSize=7)

        # self.odmr_fit_image = pg.PlotDataItem(
        #                                      np.arange(20),
        #                                      np.arange(20),
        #                                      pen=pg.mkPen(palette.c2))

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.Histogram_PlotWidget.addItem(self.Histogram_image)
        self._mw.Histogram_PlotWidget.setLabel(axis='left', text='Counts', units='Counts')
        self._mw.Histogram_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.Histogram_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Configuration of the Colorbar
        # self.Histogram_scan_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        # self._mw.Histogram_cb_PlotWidget.addItem(self.Histogram_scan_cb)
        # self._mw.Histogram_cb_PlotWidget.hideAxis('bottom')
        # self._mw.Histogram_cb_PlotWidget.hideAxis('left')
        # self._mw.Histogram_cb_PlotWidget.setLabel('right', 'Counts', units='c')

        # Connect the buttons and inputs for colorbar
        # self._mw.Histogram_cb_manual_RadioButton.clicked.connect(self.update_cw_colorbar)
        # self._mw.Histogram_cb_centiles_RadioButton.clicked.connect(self.update_cw_colorbar)
        # self._mw.Histogram_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        # self._mw.Histogram_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        # self._mw.Histogram_cb_min_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        # self._mw.Histogram_cb_max_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        # self.cw_cb_min = self._timetagger_logic.Histogram_cb_low_percentile
        # self.cw_cb_max = self._timetagger_logic.Histogram_cb_high_percentile

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        
        self._mw.Counter_Button.clicked.disconnect()
        self._mw.Histogram_Button.clicked.disconnect()
        self._mw.TimeDiff_Button.clicked.disconnect()
        self._mw.Stop_Button.clicked.disconnect()
        self._mw.Continue_Button.clicked.disconnect()
        self._mw.Save_Button.clicked.disconnect()
        self._mw.Load_Button.clicked.disconnect()
        self._mw.Filename_LineEdit.textEdited.disconnect()
        self._mw.Stoptime_LineEdit.textEdited.disconnect()
        self._mw.Interval_LineEdit.textEdited.disconnect()
        self._mw.PeriodicSaving_CheckBox.stateChanged.disconnect()
        self._mw.ClickChannel_lineEdit.textEdited.disconnect()
        self._mw.StartChannel_lineEdit.textEdited.disconnect()
        self._mw.NextChannel_lineEdit.textEdited.disconnect()
        self._mw.SyncChannel_lineEdit.textEdited.disconnect()
        self._mw.Binwdith_lineEdit.textEdited.disconnect()
        self._mw.CounterBinwdith_lineEdit.textEdited.disconnect()
        self._mw.Datapoints_lineEdit.textEdited.disconnect()
        self._mw.NumberOfBins_lineEdit.textEdited.disconnect()

        
        self._timetagger_logic.sigTimeTaggerPlotsUpdated.disconnect()
        self._timetagger_logic.SigClock.disconnect()
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


    def update_cw_colorbar(self):
        if self._mw.Histogram_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.Histogram_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.Histogram_cb_high_percentile_DoubleSpinBox.value()

            self.cw_cb_min = np.percentile(self._timetagger_logic.scanmatrix, low_centile)
            self.cw_cb_max = np.percentile(self._timetagger_logic.scanmatrix, high_centile)
        else:
            self.cw_cb_min = self._mw.Histogram_cb_min_DoubleSpinBox.value()
            self.cw_cb_max = self._mw.Histogram_cb_max_DoubleSpinBox.value()

        self.Histogram_scan_cb.refresh_colorbar(self.cw_cb_min, self.cw_cb_max)
        self._mw.Histogram_cb_PlotWidget.update()
        self.Histogram_matrix_image.setImage(
                image=self._timetagger_logic.scanmatrix,
                axisOrder='row-major',
                levels=(self.cw_cb_min, self.cw_cb_max)
            )

  
    def update_plots(self,Histogram_data_x=None, Histogram_data_y=None):
        
        if self._timetagger_logic.measurement_state == "Counter":
            self.Histogram_image.setData(Histogram_data_x, Histogram_data_y)
        elif self._timetagger_logic.measurement_state == "Histogram":
            self.Histogram_image.setData(Histogram_data_x, Histogram_data_y)
        elif self._timetagger_logic.measurement_state == "TimeDiff":
            self.Histogram_image.setData(Histogram_data_x, Histogram_data_y)

    def Update_Runtime(self):
        pass
        # self._timetagger_logic.measurement_running:
        # runtime=time.time()-self._timetagger_logic.starting_time
        # hours=int(runtime//3600)
        # minutes=int((runtime//60)%60)
        # secs=int(runtime%60)
        # #time_str=str(runtime).split(".")
        # self._mw.cw_Runtime_Label.setText(f"{hours} h {minutes} m {secs} s")