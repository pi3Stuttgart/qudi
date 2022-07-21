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
from core.util import units
from core.connector import Connector
from gui.colordefs import ColorScaleInferno
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

from gui.laserscanner.connectors_and_set_default_fitting import initialize_connections_and_defaultvalue as ple_default_functions


class VoltScanMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_laserscanner_gui_fitting.ui')

        # Load it
        super(VoltScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class VoltScanGui(GUIBase, ple_default_functions):
   
    # declare connectors
    voltagescannerlogic1 = Connector(interface='LaserScannerLogic')
    
    sigStartScan = QtCore.Signal()
    sigStopScan = QtCore.Signal()
    sigChangeVoltage = QtCore.Signal(float)
    sigChangeRange = QtCore.Signal(list)
    sigChangeResolution = QtCore.Signal(float)
    sigChangeSpeed = QtCore.Signal(float)
    sigChangeLines = QtCore.Signal(int)
    sigSaveMeasurement = QtCore.Signal(str, list, list)

    sigFitChanged = QtCore.Signal(str)
    sigDoFit = QtCore.Signal(str, object, object, int, int)
        

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._voltscan_logic.sigPleFitUpdated.disconnect()
        self.sigDoFit.disconnect()
        self._mw.do_fit_PushButton.clicked.disconnect()
        self._fsd.sigFitsUpdated.disconnect()
        self._mw.fit_range_SpinBox.editingFinished.disconnect()
        self._mw.action_FitSettings.triggered.disconnect()
        
        self._mw.close()
        return 0

    def on_activate(self):

        self._mw = VoltScanMainWindow()
        self._voltscan_logic = self.voltagescannerlogic1()
        
        self.initialize_connections_and_defaultvalues()
        
        # Set up and connect channel combobox
        self.display_channel = 0
        ple_channels = self._voltscan_logic.get_ple_channels()
        for n, ch in enumerate(ple_channels):
            self._mw.ple_channel_ComboBox.addItem(str(ch), n)


        #self._voltscan_logic.SigClock.connect(self.Update_Runtime, QtCore.Qt.QueuedConnection)
  
        # Get the image from the logic
        self.scan_matrix_image = pg.ImageItem(
            self._voltscan_logic.scan_matrix,
            axisOrder='row-major')

        self.scan_matrix_image.setRect(
            QtCore.QRectF(
                self._voltscan_logic.scan_range[0],
                0,
                self._voltscan_logic.scan_range[1] - self._voltscan_logic.scan_range[0],
                self._voltscan_logic.number_of_repeats)
        )

        # self.scan_matrix_image2 = pg.ImageItem(
        #     self._voltscan_logic.scan_matrix2,
        #     axisOrder='row-major')

        # self.scan_matrix_image2.setRect(
        #     QtCore.QRectF(
        #         self._voltscan_logic.scan_range[0],
        #         0,
        #         self._voltscan_logic.scan_range[1] - self._voltscan_logic.scan_range[0],
        #         self._voltscan_logic.number_of_repeats)
        # )

        self.scan_image = pg.PlotDataItem(
            self._voltscan_logic.ple_plot_x,
            self._voltscan_logic.ple_plot_y)

        self.scan_image2 = pg.PlotDataItem(
            self._voltscan_logic.ple_plot_x,
            self._voltscan_logic.ple_plot_y2)

        self.scan_fit_image = pg.PlotDataItem(
            self._voltscan_logic.ple_fit_x,
            self._voltscan_logic.ple_fit_y,
            pen=QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))

        self.ple_fit_image = pg.PlotDataItem(self._voltscan_logic.ple_fit_x,
                                              self._voltscan_logic.ple_fit_y,
                                              pen=pg.mkPen(palette.c2))
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.ple_data_PlotWidget.addItem(self.scan_image)#
        #self._mw.voltscan_ViewWidget.addItem(self.scan_fit_image)
        self._mw.ple_data_PlotWidget.showGrid(x=True, y=True, alpha=0.8) 
        self._mw.ple_matrix_PlotWidget.addItem(self.scan_matrix_image)

        #self._mw.voltscan2_ViewWidget.addItem(self.scan_image2)
        #self._mw.voltscan2_ViewWidget.addItem(self.scan_fit_image)
        #self._mw.voltscan2_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        #self._mw.voltscan_matrix2_ViewWidget.addItem(self.scan_matrix_image2)

        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()

        self.scan_matrix_image.setLookupTable(my_colors.lut)
        #self.scan_matrix_image2.setLookupTable(my_colors.lut)

        # Configuration of the Colorbar
        self.scan_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.voltscan_cb_ViewWidget.addItem(self.scan_cb) 
        self._mw.voltscan_cb_ViewWidget.hideAxis('bottom')
        self._mw.voltscan_cb_ViewWidget.hideAxis('left') 
        self._mw.voltscan_cb_ViewWidget.setLabel('right', 'Fluorescence', units='c/s') 

        # Connect the buttons and inputs for colorbar
        self._mw.voltscan_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.voltscan_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)

        # set initial values


        # Update the input/displayed numbers if the cursor has left the field:


        # fit settings
        self._fsd = FitSettingsDialog(self._voltscan_logic.fc)
        self._fsd.sigFitsUpdated.connect(self._mw.fit_methods_ComboBox.setFitFunctions)
        self._fsd.applySettings()
        self._mw.action_FitSettings.triggered.connect(self._fsd.show)
        # TODO FIGURE OUT what line above actually do
        
        # Connect signals
        self._voltscan_logic.sigUpdatePlots.connect(self.refresh_matrix)
        self._voltscan_logic.sigUpdatePlots.connect(self.refresh_plot)
        self._voltscan_logic.sigUpdatePlots.connect(self.refresh_lines)
        self._voltscan_logic.sigScanFinished.connect(self.scan_stopped)
        self._voltscan_logic.sigScanStarted.connect(self.scan_started)

        #self.sigStartScan.connect(self._voltscan_logic.start_scanning)
        #self.sigStopScan.connect(self._voltscan_logic.stop_scanning)
        self.sigChangeVoltage.connect(self._voltscan_logic.set_voltage)
        self.sigChangeRange.connect(self._voltscan_logic.set_scan_range)
        self.sigChangeSpeed.connect(self._voltscan_logic.set_scan_speed)
        self.sigChangeLines.connect(self._voltscan_logic.set_scan_lines)
        self.sigChangeResolution.connect(self._voltscan_logic.set_resolution)
        self.sigSaveMeasurement.connect(self._voltscan_logic.save_data)

        # Internal trigger signals
        self._mw.do_fit_PushButton.clicked.connect(self.do_fit)
        self._mw.fit_range_SpinBox.editingFinished.connect(self.update_fit_range)
        # Control/values-changed signals to logic
        self.sigDoFit.connect(self._voltscan_logic.do_fit, QtCore.Qt.QueuedConnection)
        # Update signals coming from logic:
        self._voltscan_logic.sigPleFitUpdated.connect(self.update_fit, QtCore.Qt.QueuedConnection)
        
        self._mw.show()

    def add_ranges_gui_elements_clicked(self):
        self._mw.fit_range_SpinBox.setMaximum(self._voltscan_logic.ranges)
        # remove stuff that remained from the old range that might have been in place there
        key = 'channel: {0}, range: {1}'.format(self.display_channel, self._voltscan_logic.ranges - 1)
        if key in self._voltscan_logic.fits_performed:
            self._voltscan_logic.fits_performed.pop(key)
        return
    def remove_ranges_gui_elements_clicked(self):
        if self._voltscan_logic.ranges == 1:
            return
        # in case the removed range is the one selected for fitting right now adjust the value
        self._voltscan_logic.ranges -= 1
        max_val = self._voltscan_logic.ranges - 1
        self._mw.fit_range_SpinBox.setMaximum(max_val)
        if self._voltscan_logic.range_to_fit > max_val:
            self._voltscan_logic.range_to_fit = max_val

        self._mw.fit_range_SpinBox.setMaximum(max_val)
        return


    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def updateButtonsEnabled(self):
        # """ Logic told us to update our button states, so set the buttons accordingly. """
        self._mw.MW1_on_Button.setCheckable(True)
        self._mw.MW2_on_Button.setCheckable(True)
        self._mw.MW3_on_Button.setCheckable(True)
    
    # def run_stop(self, is_checked):
    #     """ Manages what happens if scan is started/stopped """
    #     print('Start scanning')
    #     if is_checked:
    #         self.sigStartScan.emit()
    #         #self._mw.voltscan_ViewWidget.removeItem(self.scan_fit_image) CHANGE
    #         #self._mw.voltscan2_ViewWidget.removeItem(self.scan_fit_image)
    #     else:
    #         self.sigStopScan.emit()

    def scan_started(self):
       pass
    def scan_stopped(self):
        self.refresh_plot()
        self.refresh_matrix()
        self.refresh_lines()

    def refresh_plot(self):
        """ Refresh the xy-plot image """
        self.scan_image.setData(self._voltscan_logic.plot_x, self._voltscan_logic.plot_y)
        #self.scan_image2.setData(self._voltscan_logic.plot_x, self._voltscan_logic.plot_y2)

    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
        self.scan_matrix_image.setImage(self._voltscan_logic.scan_matrix, axisOrder='row-major')
        self.scan_matrix_image.setRect(
            QtCore.QRectF(
                self._voltscan_logic.scan_range[0],
                0,
                self._voltscan_logic.scan_range[1] - self._voltscan_logic.scan_range[0],
                self._voltscan_logic.number_of_repeats)
            )
        self.refresh_scan_colorbar()

        scan_image_data = self._voltscan_logic.scan_matrix

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.voltscan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(scan_image_data, low_centile)
            cb_max = np.percentile(scan_image_data, high_centile)
        else:
            cb_min = self._mw.voltscan_cb_min_InputWidget.value()
            cb_max = self._mw.voltscan_cb_max_InputWidget.value()

        # Now update image with new color scale, and update colorbar
        self.scan_matrix_image.setImage(
            image=scan_image_data,
            levels=(cb_min, cb_max),
            axisOrder='row-major')

        scan_image_data2 = self._voltscan_logic.scan_matrix2
 
        self.refresh_scan_colorbar()

    def refresh_scan_colorbar(self):
        """ Update the colorbar to a new scaling."""

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.voltscan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(self.scan_matrix_image.image, low_centile)
            cb_max = np.percentile(self.scan_matrix_image.image, high_centile)
        else:
            cb_min = self._mw.voltscan_cb_min_InputWidget.value()
            cb_max = self._mw.voltscan_cb_max_InputWidget.value()

        self.scan_cb.refresh_colorbar(cb_min, cb_max)
        # self._mw.voltscan_cb_ViewWidget.update() CHANGE

    def refresh_lines(self):
        self._mw.elapsed_lines_DisplayWidget.display(self._voltscan_logic._scan_counter_up)

    def change_voltage(self,tmp=0):
        self.sigChangeVoltage.emit(self._mw.constDoubleSpinBox.value())

    def change_start_volt(self,tmp=0):
        self.sigChangeRange.emit([
            self._mw.startDoubleSpinBox.value(),
            self._mw.stopDoubleSpinBox.value()
        ])

    def change_speed(self,tmp=0):
        self.sigChangeSpeed.emit(self._mw.speedDoubleSpinBox.value())

    def change_stop_volt(self,tmp=0):
        self.sigChangeRange.emit([
            self._mw.startDoubleSpinBox.value(),
            self._mw.stopDoubleSpinBox.value()
        ])

    def change_lines(self,tmp=0):
        self.sigChangeLines.emit(self._mw.linesSpinBox.value())

    def change_resolution(self,tmp=0):
        self.sigChangeResolution.emit(self._mw.resolutionSpinBox.value())

    def get_matrix_cb_range(self):
        """
        Determines the cb_min and cb_max values for the matrix plot
        """
        matrix_image = self.scan_matrix_image.image

        # If "Manual" is checked or the image is empty (all zeros), then take manual cb range.
        # Otherwise, calculate cb range from percentiles.
        if self._mw.voltscan_cb_manual_RadioButton.isChecked() or np.max(matrix_image) < 0.1:
            cb_min = self._mw.voltscan_cb_min_InputWidget.value()
            cb_max = self._mw.voltscan_cb_max_InputWidget.value()
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            matrix_image_nonzero = matrix_image[np.nonzero(matrix_image)]

            # Read centile range
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(matrix_image_nonzero, low_centile)
            cb_max = np.percentile(matrix_image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]
        return cb_range

    def do_fit(self):
        fit_function = self._mw.fit_methods_ComboBox.getCurrentFit()[0]
        print("Hier fehlt self.sigDoFit.emit")
        self.sigDoFit.emit(fit_function, None, None, self._mw.ple_channel_ComboBox.currentIndex(),
                           self._mw.fit_range_SpinBox.value())
        return

    def update_fit(self, x_data, y_data, result_str_dict, current_fit):
        """ Update the shown fit. """
        if current_fit != 'No Fit':
            # display results as formatted text
            self._mw.ple_fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            print("Hier fehlt ein display widget")
            # self._mw.odm_fit_results_DisplayWidget.setPlainText(formated_results)

        self._mw.fit_methods_ComboBox.blockSignals(True)
        self._mw.fit_methods_ComboBox.setCurrentFit(current_fit)
        self._mw.fit_methods_ComboBox.blockSignals(False)

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if current_fit != 'No Fit':
            self.ple_fit_image.setData(x=x_data, y=y_data)
            print("Hier fehlt ein Plot widget link")
            # if self.ple_fit_image not in self._mw.odmr_PlotWidget.listDataItems():
            #     self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
        else:
            print("Hier fehlt ein Plot widget link")
            pass
            # if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
            #     self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)
        print("Hier fehlt ein Plot widget link")
        # self._mw.odmr_PlotWidget.getViewBox().updateAutoRange()
        return

    def update_fit_range(self):
        self._voltscan_logic.range_to_fit = self._mw.fit_range_SpinBox.value()
        return
    def change_fit_range(self):
        self._voltscan_logic.fit_range = self._mw.fit_range_SpinBox.value()
        return

    def update_channel(self, index):
        self.display_channel = int(
            self._mw.ple_channel_ComboBox.itemData(index, QtCore.Qt.UserRole))
        # self.update_plots(
        #     self._odmr_logic.odmr_plot_x,
        #     self._odmr_logic.odmr_plot_y,
        #     self._odmr_logic.odmr_plot_xy)
