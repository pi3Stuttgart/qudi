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


class ODMRWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_ODMR_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class ODMRGUI(GUIBase):

    ## declare connectors
    odmrlogic = Connector(interface='ODMRLogic_holder')
    exec("from gui.odmr.connectors_and_setdefault import *") # loads the variables and function of the specified module as part of the class

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

        #self._setupcontrol_logic = self.setupcontrollogic() 
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = ODMRWindow()
        self._odmr_logic= self.odmrlogic()
        self.initialize_connections_and_defaultvalues()

        #connect the signals:
        self._odmr_logic.sigOdmrPlotsUpdated.connect(self.update_plots, QtCore.Qt.QueuedConnection)
        self._odmr_logic.SigClock.connect(self.Update_Runtime, QtCore.Qt.QueuedConnection)
        
        #get the number of points the Timetagger counter will return:
        self.number_of_points_per_line=self._odmr_logic._time_tagger._counter["n_values"]

        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()

        #################### setup graphics for cw ODMR
        self.cw_odmr_matrix_image = pg.ImageItem(
            #self._odmr_logic.odmr_plot_xy[:, self.display_channel],
            np.random.rand(40, 20),
            axisOrder='row-major')

        self.cw_odmr_matrix_image.setRect(QtCore.QRectF(
            70,
            0,
            40,
            20
        ))

        self.cw_odmr_image = pg.PlotDataItem(
                                          np.arange(20),
                                          np.arange(20),
                                          pen=pg.mkPen(pg.mkColor(255, 255, 255), style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=pg.mkColor(255, 255, 255),
                                          symbolBrush=pg.mkColor(255, 255, 255),
                                          symbolSize=7)

        self.cw_odmr_image_fit = pg.PlotDataItem(
                                            np.arange(20),
                                            np.arange(20),
                                            pen=pg.mkPen(pg.mkColor(255, 0, 0), style=QtCore.Qt.SolidLine)
                                            )

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.cw_odmr_PlotWidget.addItem(self.cw_odmr_image)
        self._mw.cw_odmr_PlotWidget.addItem(self.cw_odmr_image_fit)
        self._mw.cw_odmr_PlotWidget.setLabel(axis='left', text='Counts', units='Counts')
        self._mw.cw_odmr_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.cw_odmr_PlotWidget.showGrid(x=True, y=True, alpha=0.8)



        self._mw.cw_odmr_matrix_PlotWidget.addItem(self.cw_odmr_matrix_image)
        self._mw.cw_odmr_matrix_PlotWidget.setLabel(axis='left', text='Matrix Lines', units='#')
        self._mw.cw_odmr_matrix_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')

        self.cw_odmr_matrix_image.setLookupTable(my_colors.lut)

        # Configuration of the Colorbar
        self.cw_odmr_scan_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.cw_odmr_cb_PlotWidget.addItem(self.cw_odmr_scan_cb)
        self._mw.cw_odmr_cb_PlotWidget.hideAxis('bottom')
        self._mw.cw_odmr_cb_PlotWidget.hideAxis('left')
        self._mw.cw_odmr_cb_PlotWidget.setLabel('right', 'Counts', units='c')

        # Connect the buttons and inputs for colorbar
        self._mw.cw_odmr_cb_manual_RadioButton.clicked.connect(self.update_cw_colorbar)
        self._mw.cw_odmr_cb_centiles_RadioButton.clicked.connect(self.update_cw_colorbar)
        self._mw.cw_odmr_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        self._mw.cw_odmr_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        self._mw.cw_odmr_cb_min_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        self._mw.cw_odmr_cb_max_DoubleSpinBox.valueChanged.connect(self.update_cw_colorbar)
        self.cw_cb_min = self._odmr_logic.ODMRLogic.cw_odmr_cb_low_percentile
        self.cw_cb_max = self._odmr_logic.ODMRLogic.cw_odmr_cb_high_percentile


        #################### setup graphics for pulsed ODMR  ####################
        self.pulsed_odmr_matrix_image = pg.ImageItem(
                    np.random.rand(40, 20),
                    axisOrder='row-major')

        self.pulsed_odmr_matrix_image.setRect(QtCore.QRectF(
            70,
            0,
            40,
            20
        ))
        self.pulsed_odmr_data_image = pg.PlotDataItem(
                                        np.arange(20),
                                        np.arange(20),
                                        pen=pg.mkPen(pg.mkColor(255, 255, 255), style=QtCore.Qt.DotLine),
                                        symbol='o',
                                        symbolPen=pg.mkColor(255, 255, 255),
                                        symbolBrush=pg.mkColor(255, 255, 255),
                                        symbolSize=7)

        self.pulsed_odmr_data_image_fit = pg.PlotDataItem(
                                            #self._odmr_logic.odmr_fit_x,
                                            np.arange(20),
                                            #self._odmr_logic.odmr_fit_y,
                                            np.arange(20),
                                            pen=pg.mkPen(palette.c2))

        self.pulsed_odmr_detect_image = pg.PlotDataItem(
                                        #self._odmr_logic.odmr_plot_x,
                                        np.arange(20),
                                        #self._odmr_logic.odmr_plot_y[self.display_channel],
                                        np.arange(20),
                                        pen=pg.mkPen(pg.mkColor(255, 255, 255), style=QtCore.Qt.DotLine),
                                        symbol='o',
                                        symbolPen=pg.mkColor(255, 255, 255),
                                        symbolBrush=pg.mkColor(255, 255, 255),
                                        symbolSize=7)

        self.odmr_detect_fit_image = pg.PlotDataItem(
                                            #self._odmr_logic.odmr_fit_x,
                                            np.arange(20),
                                            #self._odmr_logic.odmr_fit_y,
                                            np.arange(20),
                                            pen=pg.mkPen(palette.c2))

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.pulsed_odmr_data_PlotWidget.addItem(self.pulsed_odmr_data_image)
        self._mw.pulsed_odmr_data_PlotWidget.addItem(self.pulsed_odmr_data_image_fit)
        self._mw.pulsed_odmr_data_PlotWidget.setLabel(axis='left', text='Counts', units='Counts')
        self._mw.pulsed_odmr_data_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.pulsed_odmr_data_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.pulsed_odmr_detect_PlotWidget.addItem(self.pulsed_odmr_detect_image)
        self._mw.pulsed_odmr_detect_PlotWidget.setLabel(axis='left', text='Counts', units='Counts')
        self._mw.pulsed_odmr_detect_PlotWidget.setLabel(axis='bottom', text='time', units='s')
        self._mw.pulsed_odmr_detect_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.pulsed_odmr_matrix_PlotWidget.addItem(self.pulsed_odmr_matrix_image)
        self._mw.pulsed_odmr_matrix_PlotWidget.setLabel(axis='left', text='Matrix Lines', units='#')
        self._mw.pulsed_odmr_matrix_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')

        self.pulsed_odmr_matrix_image.setLookupTable(my_colors.lut)

        self.pulsed_odmr_scan_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.pulsed_odmr_cb_PlotWidget.addItem(self.pulsed_odmr_scan_cb)
        self._mw.pulsed_odmr_cb_PlotWidget.hideAxis('bottom')
        self._mw.pulsed_odmr_cb_PlotWidget.hideAxis('left')
        self._mw.pulsed_odmr_cb_PlotWidget.setLabel('right', 'Counts', units='c')

        # Connect the buttons and inputs for colorbar
        self._mw.pulsed_odmr_cb_manual_RadioButton.clicked.connect(self.update_pulsed_colorbar)
        self._mw.pulsed_odmr_cb_centiles_RadioButton.clicked.connect(self.update_pulsed_colorbar)
        self._mw.pulsed_odmr_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.update_pulsed_colorbar)
        self._mw.pulsed_odmr_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.update_pulsed_colorbar)
        self._mw.pulsed_odmr_cb_min_DoubleSpinBox.valueChanged.connect(self.update_pulsed_colorbar)
        self._mw.pulsed_odmr_cb_max_DoubleSpinBox.valueChanged.connect(self.update_pulsed_colorbar)
        self.pulsed_cb_min = self._odmr_logic.pulsedODMRLogic.pulsed_odmr_cb_low_percentile
        self.pulsed_cb_max = self._odmr_logic.pulsedODMRLogic.pulsed_odmr_cb_high_percentile



    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self.disconnect_all()
        
        self._odmr_logic.sigOdmrPlotsUpdated.disconnect()
        self._odmr_logic.SigClock.disconnect()
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
        if self._mw.cw_odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.cw_odmr_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.cw_odmr_cb_high_percentile_DoubleSpinBox.value()

            self.cw_cb_min = np.percentile(self._odmr_logic.ODMRLogic.scanmatrix, low_centile)
            self.cw_cb_max = np.percentile(self._odmr_logic.ODMRLogic.scanmatrix, high_centile)
        else:
            self.cw_cb_min = self._mw.cw_odmr_cb_min_DoubleSpinBox.value()
            self.cw_cb_max = self._mw.cw_odmr_cb_max_DoubleSpinBox.value()

        self.cw_odmr_scan_cb.refresh_colorbar(self.cw_cb_min, self.cw_cb_max)
        self._mw.cw_odmr_cb_PlotWidget.update()
        self.cw_odmr_matrix_image.setImage(
                image=self._odmr_logic.ODMRLogic.scanmatrix,
                axisOrder='row-major',
                levels=(self.cw_cb_min, self.cw_cb_max)
            )

    def update_pulsed_colorbar(self):
        if self._mw.pulsed_odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.pulsed_odmr_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.pulsed_odmr_cb_high_percentile_DoubleSpinBox.value()

            self.pulsed_cb_min = np.percentile(self._odmr_logic.pulsedODMRLogic.scanmatrix, low_centile)
            self.pulsed_cb_max = np.percentile(self._odmr_logic.pulsedODMRLogic.scanmatrix, high_centile)
        else:
            self.pulsed_cb_min = self._mw.pulsed_odmr_cb_min_DoubleSpinBox.value()
            self.pulsed_cb_max = self._mw.pulsed_odmr_cb_max_DoubleSpinBox.value()

        self.pulsed_odmr_scan_cb.refresh_colorbar(self.pulsed_cb_min, self.pulsed_cb_max)
        self._mw.pulsed_odmr_cb_PlotWidget.update()
        
        self.pulsed_odmr_matrix_image.setImage(
                image=self._odmr_logic.pulsedODMRLogic.scanmatrix,
                axisOrder='row-major',
                levels=(self.pulsed_cb_min, self.pulsed_cb_max)
            )


    def update_plots(self,odmr_data_x=None, odmr_data_y=None, odmr_matrix=None, odmr_detect_x=None, odmr_detect_y=None):
        if self._odmr_logic.ODMRLogic.measurement_running or self._odmr_logic.ODMRLogic.cw_update_after_stop:
            odmr_data_x=self._odmr_logic.ODMRLogic.mw1_freq*1e6
            odmr_data_y=self._odmr_logic.ODMRLogic.data
            odmr_matrix=self._odmr_logic.ODMRLogic.scanmatrix
            #print(odmr_data_x, odmr_data_y, odmr_matrix)
            self.cw_odmr_image.setData(odmr_data_x, odmr_data_y)
            self._mw.cw_odmr_PlotWidget.removeItem(self.cw_odmr_image_fit)
            self._odmr_logic.ODMRLogic.cw_update_after_stop=False
            if self._odmr_logic.ODMRLogic.cw_PerformFit:
                self._mw.cw_odmr_PlotWidget.addItem(self.cw_odmr_image_fit)

                self._odmr_logic.ODMRLogic.x_fit,self._odmr_logic.ODMRLogic.y_fit,self._odmr_logic.ODMRLogic.fit_result=self._odmr_logic.do_fit(self._odmr_logic.ODMRLogic.mw1_freq*1e6,self._odmr_logic.ODMRLogic.data)

                self.cw_odmr_image_fit.setData(self._odmr_logic.ODMRLogic.x_fit, self._odmr_logic.ODMRLogic.y_fit)
                self._mw.cw_Contrast_Fit_Label.setText(str(self._odmr_logic.Contrast_Fit))
                self._mw.cw_Linewidths_Fit_Label.setText(str(self._odmr_logic.Linewidths_Fit))
                self._mw.cw_Frequencies_Fit_Label.setText(str(self._odmr_logic.Frequencies_Fit))



            self.cw_odmr_matrix_image.setRect(
                QtCore.QRectF(
                    odmr_data_x[0],
                    0,
                    #np.abs(selected_odmr_data_x[-1] - selected_odmr_data_x[0]),
                    odmr_data_x[-1]-odmr_data_x[0],
                    odmr_matrix.shape[0]
                    )
            )

            self.update_cw_colorbar()


        elif self._odmr_logic.pulsedODMRLogic.measurement_running or self._odmr_logic.pulsedODMRLogic.pulsed_update_after_stop:
            odmr_data_x=self._odmr_logic.pulsedODMRLogic.mw1_freq*1e6
            odmr_data_y=self._odmr_logic.pulsedODMRLogic.data
            odmr_matrix=self._odmr_logic.pulsedODMRLogic.scanmatrix
            odmr_detect_x=self._odmr_logic.pulsedODMRLogic.indexes/1e12
            odmr_detect_y= self._odmr_logic.pulsedODMRLogic.data_detect

            #print(odmr_data_x, odmr_data_y, odmr_matrix)
            self.pulsed_odmr_data_image.setData(odmr_data_x, odmr_data_y)
            self._mw.pulsed_odmr_data_PlotWidget.removeItem(self.pulsed_odmr_data_image_fit)
            self._odmr_logic.pulsedODMRLogic.pulsed_update_after_stop=False

            self.pulsed_odmr_detect_image.setData(odmr_detect_x, odmr_detect_y)
            if self._odmr_logic.pulsedODMRLogic.pulsed_PerformFit: #TODO Only when checkbox
                self._mw.pulsed_odmr_data_PlotWidget.addItem(self.pulsed_odmr_data_image_fit)

                self._odmr_logic.pulsedODMRLogic.x_fit,self._odmr_logic.pulsedODMRLogic.y_fit,self._odmr_logic.pulsedODMRLogic.fit_result=self._odmr_logic.do_fit(self._odmr_logic.pulsedODMRLogic.mw1_freq,self._odmr_logic.pulsedODMRLogic.data)

                self.pulsed_odmr_data_image_fit.setData(self._odmr_logic.pulsedODMRLogic.x_fit*1e6, self._odmr_logic.pulsedODMRLogic.y_fit)
                self._mw.pulsed_Contrast_Fit_Label.setText(str(self._odmr_logic.Contrast_Fit))
                self._mw.pulsed_Linewidths_Fit_Label.setText(str(self._odmr_logic.Linewidths_Fit))
                self._mw.pulsed_Frequencies_Fit_Label.setText(str(self._odmr_logic.Frequencies_Fit))

            self.pulsed_odmr_matrix_image.setRect(
                QtCore.QRectF(
                    odmr_data_x[0],
                    0,
                    #np.abs(selected_odmr_data_x[-1] - selected_odmr_data_x[0]),
                    odmr_data_x[-1]-odmr_data_x[0],
                    odmr_matrix.shape[0]
                    )
            )
            self.update_pulsed_colorbar()


    def Update_Runtime(self):
        if self._odmr_logic.ODMRLogic.measurement_running:
            runtime=time.time()-self._odmr_logic.ODMRLogic.starting_time
            hours=int(runtime//3600)
            minutes=int((runtime//60)%60)
            secs=int(runtime%60)
            #time_str=str(runtime).split(".")
            self._mw.cw_Runtime_Label.setText(f"{hours} h {minutes} m {secs} s")

        elif self._odmr_logic.pulsedODMRLogic.measurement_running:
            runtime=time.time()-self._odmr_logic.pulsedODMRLogic.starting_time
            hours=int(runtime//3600)
            minutes=int((runtime//60)%60)
            secs=int(runtime%60)
            #time_str=str(runtime).split(".")
            self._mw.pulsed_Runtime_Label.setText(f"{hours} h {minutes} m {secs} s") 