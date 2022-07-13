# -*- coding: utf-8 -*-

"""
This file contains the GUI for magnet control.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import datetime
import numpy as np
import os
import pyqtgraph as pg
import pyqtgraph.exporters
from qtpy import uic

from core.connector import Connector
from core.statusvariable import StatusVar
from gui.colordefs import ColorScaleViridis
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from qtpy import QtCore
from qtpy import QtWidgets
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtwidgets.scan_plotwidget import ScanImageItem


class CrossLine(pg.InfiniteLine):

    """ Construct one line for the Crosshair in the plot.

    @param float pos: optional parameter to set the position
    @param float angle: optional parameter to set the angle of the line
    @param dict pen: Configure the pen.

    For additional options consider the documentation of pyqtgraph.InfiniteLine
    """

    def __init__(self, **args):
        pg.InfiniteLine.__init__(self, **args)

    def adjust(self, extroi):
        """
        Run this function to adjust the position of the Crosshair-Line

        @param object extroi: external roi object from pyqtgraph
        """
        if self.angle == 0:
            self.setValue(extroi.pos()[1] + extroi.size()[1] * 0.5)
        if self.angle == 90:
            self.setValue(extroi.pos()[0] + extroi.size()[0] * 0.5)


class MagnetMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_magnet_gui.ui')

        # Load it
        super(MagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()




class MagnetGui(GUIBase):
    """ Main GUI for the magnet. """

    # Stuff that needs to happen:
    # get_crosshair_posi --> set values
    # ramp --> get values from spinbox, send to logic, start ramp
    # ZERO--> ramp to zero
    # STOP --> pause ramp
    # HEAT --> turn on heater
    # COOL --> turn off heater
    # GET POS --> get field in magnet
    # SCAN --> start scan
    # RESUME --> dunno
    # SAVE --> save data


    # declare connectors
    magnetlogic = Connector(interface='MagnetLogic')
    savelogic = Connector(interface='SaveLogic')

    # create signals to logic
    sigChangeB = QtCore.Signal(list,list) # list: [B,theta,phi], list [Bx,By,Bz]
    sigStopRamp = QtCore.Signal()
    sigRampZero = QtCore.Signal()
    sigStartScan = QtCore.Signal(list)
    sigHeatPsw = QtCore.Signal()
    sigCoolPsw = QtCore.Signal()
    sigUpdatePswStatusLabel = QtCore.Signal()
    sigGetPos = QtCore.Signal()

    # status var
    _alignment_2d_cb_label = StatusVar('alignment_2d_cb_GraphicsView_text', 'Fluorescence')
    _alignment_2d_cb_units = StatusVar('alignment_2d_cb_GraphicsView_units', 'counts/s')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._continue_2d_fluorescence_alignment = False

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._magnetlogic = self.magnetlogic()
        self._savelogic = self.savelogic()

        self._mw = MagnetMainWindow()

        # connect button presses
        self._mw.get_crosshair_posi_PushButton.clicked.connect(self.get_crosshair_posi_clicked)
        self._mw.rotate_abs_PushButton.clicked.connect(self.change_abs_B_field)
        self._mw.stop_ramp_PushButton.clicked.connect(self.stop_ramp_clicked)
        self._mw.ramp_to_zero_PushButton.clicked.connect(self.ramp_to_zero_clicked)
        self._mw.curr_pos_get_pos_PushButton.clicked.connect(self.get_pos_clicked)
        self._mw.cool_PSW_pushButton.clicked.connect(self.cool_PSW_clicked)
        self._mw.heat_PSW_pushButton.clicked.connect(self.heat_PSW_clicked)

        # changes to scaling of colorbar and image
        self._mw.alignment_2d_cb_min_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_cb_max_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_cb_low_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)
        self._mw.alignment_2d_cb_high_centiles_DSpinBox.valueChanged.connect(self._update_2d_graph_data)

        # connect signals to logic
        self.sigChangeB.connect(self._magnetlogic.ramp)
        self.sigStopRamp.connect(self._magnetlogic.pause_ramp)
        self.sigRampZero.connect(self._magnetlogic.ramp_to_zero)
        self.sigStartScan.connect(self._magnetlogic.start_scan)
        self.sigHeatPsw.connect(self._magnetlogic.heat_psw)
        self.sigCoolPsw.connect(self._magnetlogic.cool_psw)
        self.sigGetPos.connect(self._magnetlogic.mag_field_requested)

        # connect signals from logic
        self._magnetlogic.sigUpdatePswStatusLabel.connect(self.update_psw_status_label)
        self._magnetlogic.sigRampFinished.connect(self.reactivate_control_buttons)
        self._magnetlogic.sigRampFinished.connect(self.change_magnet_status_label)
        self._magnetlogic.sigUpdateTwoDGraphData.connect(self._update_2d_graph_data)

        # connect signals from logic
        # self._magnetlogic.sigAngleChanged.connect()
        self._magnetlogic.sigGotPos.connect(self.update_current_pos_display)
        # self._magnetlogic.sigPixelFinished.connect(self._update_2d_graph_data)
        self._magnetlogic.sigScanFinished.connect(self._scan_finished)

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

        # display default values
        params = ['theta_min','theta_max', 'n_theta', 'phi_min', 'phi_max', 'n_phi', 'int_time']
        for param in params:
            eval('self._mw.' + param + '_doubleSpinBox.setValue(self._magnetlogic.' + param + ')')
        # B is named a bit differently
        self._mw.scan_B_doubleSpinBox.setValue(self._magnetlogic.B)

        # connect the actions of the toolbar:
        self._mw.default_view_Action.triggered.connect(self.set_default_view_main_window)

        # get current magnet field
        curr_pos_spherical = self._magnetlogic.get_field_spherical()

        # display current B field
        self._mw.curr_pos_B_DoubleSpinBox.setValue(curr_pos_spherical[0])
        self._mw.curr_pos_theta_DoubleSpinBox.setValue(curr_pos_spherical[1])
        self._mw.curr_pos_phi_DoubleSpinBox.setValue(curr_pos_spherical[2])

        # update the values also of the absolute rotation display:
        self._mw.rotate_abs_B_DoubleSpinBox.setValue(curr_pos_spherical[0])
        self._mw.rotate_abs_theta_DoubleSpinBox.setValue(curr_pos_spherical[1])
        self._mw.rotate_abs_phi_DoubleSpinBox.setValue(curr_pos_spherical[2])

        # I copied this from the ulm version and just replaces axis0 and axis1
        self._2d_alignment_ImageItem = ScanImageItem(image=self._magnetlogic.thetaPhiImage)
        self._mw.alignment_2d_GraphicsView.addItem(self._2d_alignment_ImageItem)
        axis0 = self._magnetlogic.phis
        axis1 = self._magnetlogic.thetas
        step0 = axis0[1] - axis0[0]
        step1 = axis1[1] - axis1[0]
        self._2d_alignment_ImageItem.set_image_extent([[axis0[0]-step0/2, axis0[-1]+step0/2],
                                                       [axis1[0]-step1/2, axis1[-1]+step1/2]])
        # Get the colorscales at set LUT
        my_colors = ColorScaleViridis()
        self._2d_alignment_ImageItem.setLookupTable(my_colors.lut)
        
        # Set initial position for the crosshair, default is current magnet position
        ini_pos_x_crosshair = curr_pos_spherical[2] # phi
        ini_pos_y_crosshair = curr_pos_spherical[1] # theta

        # make crosshair one pixel wide
        ini_width_crosshair = [
            (self._magnetlogic.phis[-1] - self._magnetlogic.phis[0]) / len(self._magnetlogic.phis),
            (self._magnetlogic.thetas[-1] - self._magnetlogic.thetas[0]) / len(self._magnetlogic.thetas)]
        self._mw.alignment_2d_GraphicsView.toggle_crosshair(True, movable=True)
        self._mw.alignment_2d_GraphicsView.set_crosshair_pos((ini_pos_x_crosshair, ini_pos_y_crosshair))
        self._mw.alignment_2d_GraphicsView.set_crosshair_size(ini_width_crosshair)

        self._mw.alignment_2d_GraphicsView.sigCrosshairDraggedPosChanged.connect(
            self.update_from_roi_magnet)

        # Configuration of Colorbar:
        self._2d_alignment_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        self._mw.alignment_2d_cb_GraphicsView.addItem(self._2d_alignment_cb)
        self._mw.alignment_2d_cb_GraphicsView.hideAxis('bottom')
        self._mw.alignment_2d_cb_GraphicsView.hideAxis('left')

        self._mw.alignment_2d_cb_GraphicsView.addItem(self._2d_alignment_cb)

        self._mw.alignment_2d_cb_GraphicsView.setLabel('right',
            self._alignment_2d_cb_label,
            units=self._alignment_2d_cb_units)

        # Add save file tag input box
        # This can not be done in designer, therefore we do it via code
        self._mw.alignment_2d_nametag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.alignment_2d_nametag_LineEdit.setMaximumWidth(200)
        self._mw.alignment_2d_nametag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                                          'added to the filename.')

        self._mw.save_ToolBar.addWidget(self._mw.alignment_2d_nametag_LineEdit)
        self._mw.save_Action.triggered.connect(self.save_2d_plots_and_data)

        # trigger actions for 2d alignment
        self._mw.run_stop_2d_alignment_Action.triggered.connect(self.run_stop_2d_alignment)
        #self._mw.continue_2d_alignment_Action.triggered.connect(self.continue_stop_2d_alignment)

        # initialize label for PSW status
        self._psw_status_label = 'PSW status: --'

        return 0


    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._magnetlogic.on_deactivate()
        self._mw.close()


    def show(self):
        """Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def update_from_roi_magnet(self, pos):
        """The user manually moved the XY ROI, position label accordingly

        @params object roi: PyQtGraph ROI object
        """

        # No indea what this is doing, just keeping it
        x_pos = pos.x()
        y_pos = pos.y()

        self._mw.pos_show.setText('({0:.6f}, {1:.6f})'.format(x_pos, y_pos))


    def set_default_view_main_window(self):
        """ Establish the default dock Widget configuration. 
        
        DOES NOT DO ANYTHING ATM, DON'T KNOW WHY
        """

        # connect all widgets to the main Window
        self._mw.curr_pos_DockWidget.setFloating(False)
        self._mw.rotate_abs_DockWidget.setFloating(False)
        self._mw.alignment_DockWidget.setFloating(False)

        

        # align the widget
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.curr_pos_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.rotate_abs_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2),
                               self._mw.alignment_DockWidget)


    def change_abs_B_field(self):
        """Tells the logic to change the B field."""
        self.deactivate_control_buttons()

        # get vlaues from spinboxes
        self.B = self._mw.rotate_abs_B_DoubleSpinBox.value()
        self.theta = self._mw.rotate_abs_theta_DoubleSpinBox.value()
        self.phi = self._mw.rotate_abs_phi_DoubleSpinBox.value()

        self._mw.ramp_status_label.setText('Ramping')

        self.sigChangeB.emit([self.B,self.theta,self.phi],[None])
        return


    def stop_ramp_clicked(self):
        """Tells the logic to stop the ramping."""
        self.reactivate_control_buttons()
        self.sigStopRamp.emit()


    def ramp_to_zero_clicked(self):
        """Tells the logic to ramp the magnetic field to zero"""
        # deactivates buttons
        self.deactivate_control_buttons()
        self.sigRampZero.emit()
        return


    def get_pos_clicked(self):
        """Gets B field (xyz) inside magnet, transforms into spherical coords and displays
        """
        self.sigGetPos.emit()

        # send signal to logic (mag_field_requested), locig fetches values and sends signal back to update_current_pos_display

        # scrap all of this here and work with signals
        # [Bx,By,Bz] = self._magnetlogic.get_magnet_field()

        # B = (Bx**2 + By**2 + Bz**2)**0.5

        # if np.isclose(Bz, 0.0):
        #     theta = 90
        # else:
        #     theta = np.rad2deg(np.arctan((Bx**2 + By**2)**0.5/Bz))

        # if np.isclose(Bx, 0.0):
        #     if By >= 0:
        #         phi = 90
        #     else:
        #         phi = 270
        # else:
        #     phi = np.rad2deg(np.arctan(By/Bx))

        # # display current B field
        # self._mw.curr_pos_B_DoubleSpinBox.setValue(B)
        # self._mw.curr_pos_theta_DoubleSpinBox.setValue(theta)
        # self._mw.curr_pos_phi_DoubleSpinBox.setValue(phi)
        # self._mw.curr_pos_Bx_DoubleSpinBox.setValue(Bx)
        # self._mw.curr_pos_By_DoubleSpinBox.setValue(By)
        # self._mw.curr_pos_Bz_DoubleSpinBox.setValue(Bz)
        return


    def update_current_pos_display(self,curr_pos_spherical,curr_pos_cartesian):
        """Updates the current pos in the gui."""
        B = curr_pos_spherical[0]
        theta = curr_pos_spherical[1]
        phi = curr_pos_spherical[2]
        Bx = curr_pos_cartesian[0]
        By = curr_pos_cartesian[1]
        Bz = curr_pos_cartesian[2]

        self._mw.curr_pos_B_DoubleSpinBox.setValue(B)
        self._mw.curr_pos_theta_DoubleSpinBox.setValue(theta)
        self._mw.curr_pos_phi_DoubleSpinBox.setValue(phi)
        self._mw.curr_pos_Bx_DoubleSpinBox.setValue(Bx)
        self._mw.curr_pos_By_DoubleSpinBox.setValue(By)
        self._mw.curr_pos_Bz_DoubleSpinBox.setValue(Bz)


    def reactivate_control_buttons(self):
        """Reactivates the buttons in the gui that control the B field.
        """
        status = True
        self._mw.rotate_abs_PushButton.setEnabled(status)
        self._mw.heat_PSW_pushButton.setEnabled(status)
        self._mw.cool_PSW_pushButton.setEnabled(status)
        return


    def deactivate_control_buttons(self):
        """Deactivates the buttons in the gui that control the B field.
        """
        status = False
        self._mw.rotate_abs_PushButton.setEnabled(status)
        self._mw.heat_PSW_pushButton.setEnabled(status)
        self._mw.cool_PSW_pushButton.setEnabled(status)
        return


    def run_stop_2d_alignment(self, is_checked):
        """ Manage what happens if 2d magnet scan is started/stopped

        @param bool is_checked: state if the current scan, True = started,
                                False = stopped
        """

        # param 'is_checked' probably is emitted by the QAction
        if is_checked:
            self.start_2d_alignment_clicked()

        else:
            self.abort_2d_alignment_clicked()



    def start_2d_alignment_clicked(self):
        """Sends the params for the 2d scan to the logic and tells it to start a scan.
        """
        # deactivate magnet field control buttons
        self.deactivate_control_buttons()
        # deactivate the SpinBoxes for scanning parameters
        self.deactivate_scan_spinboxes()

        B = self._mw.scan_B_doubleSpinBox.value()
        theta_min = self._mw.theta_min_doubleSpinBox.value()
        theta_max = self._mw.theta_max_doubleSpinBox.value()
        n_theta = int(self._mw.n_theta_doubleSpinBox.value())
        phi_min = self._mw.phi_min_doubleSpinBox.value()
        phi_max = self._mw.phi_max_doubleSpinBox.value()
        n_phi = int(self._mw.n_phi_doubleSpinBox.value())
        int_time = self._mw.int_time_doubleSpinBox.value()

        # start scan
        self.sigStartScan.emit([B,theta_min,theta_max,n_theta,phi_min,phi_max,n_phi,int_time])


    def abort_2d_alignment_clicked(self):
        """ """
        # reactivate magnet field control buttons
        self.reactivate_control_buttons()
        # reactivate the SpinBoxes for scanning parameters
        self.reactivate_scan_spinboxes()

        # This variable is checked before every pixel.
        # Pixel is only scanned if variable is True.
        self._magnetlogic.abort_scan = True


    def _scan_finished(self):
        """Sets the gui to the state before the start of the measurement."""
        # reactivate spin boxes for input
        self.reactivate_scan_spinboxes()
        # reactivate buttons 
        self.reactivate_control_buttons()
        # change icon of QAction
        self._mw.run_stop_2d_alignment_Action.setChecked(False)


    def reactivate_scan_spinboxes(self):
        """reactivates the SpinBoxes for scanning parameters"""
        boxes = ['scan_B', 'theta_min', 'theta_max', 'n_theta', 
                'phi_min', 'phi_max', 'n_phi', 'int_time']
        for box in boxes:
            eval('self._mw.' + box + '_doubleSpinBox.setDisabled(False)')


    def deactivate_scan_spinboxes(self):
        """deactivates the SpinBoxes for scanning parameters"""
        boxes = ['scan_B', 'theta_min', 'theta_max', 'n_theta', 
                'phi_min', 'phi_max', 'n_phi', 'int_time']
        for box in boxes:
            eval('self._mw.' + box + '_doubleSpinBox.setDisabled(True)')    


    def _update_2d_graph_data(self):
        """ Refresh the 2D-matrix image. """
        matrix_data = self._magnetlogic.thetaPhiImage

        if self._mw.alignment_2d_centiles_RadioButton.isChecked():

            low_centile = self._mw.alignment_2d_cb_low_centiles_DSpinBox.value()
            high_centile = self._mw.alignment_2d_cb_high_centiles_DSpinBox.value()

            if np.isclose(low_centile, 0.0):
                low_centile = 0.0

            # mask the array in order to mark the values which are zeros with
            # True, the rest with False:
            masked_image = np.ma.masked_equal(matrix_data, 0.0)

            # compress the 2D masked array to a 1D array where the zero values
            # are excluded:
            if len(masked_image.compressed()) == 0:
                cb_min = np.percentile(self._2d_alignment_ImageItem.image, low_centile)
                cb_max = np.percentile(self._2d_alignment_ImageItem.image, high_centile)
            else:
                cb_min = np.percentile(masked_image.compressed(), low_centile)
                cb_max = np.percentile(masked_image.compressed(), high_centile)
        else:
            cb_min = self._mw.alignment_2d_cb_min_centiles_DSpinBox.value()
            cb_max = self._mw.alignment_2d_cb_max_centiles_DSpinBox.value()


        self._2d_alignment_ImageItem.setImage(image=matrix_data, levels=(cb_min, cb_max))
        self._update_2d_graph_axis()

        self._update_2d_graph_cb()


    def _update_2d_graph_axis(self):
        
        axis0_name = 'phi'
        axis0_unit = '°'
        axis1_name = 'theta'
        axis1_unit = '°'

        axis0_array = self._magnetlogic.phis
        axis1_array = self._magnetlogic.thetas

        step0 = axis0_array[1] - axis0_array[0]
        step1 = axis1_array[1] - axis1_array[0]

        self._2d_alignment_ImageItem.set_image_extent([[axis0_array[0]-step0/2, axis0_array[-1]+step0/2],
                                                       [axis1_array[0]-step1/2, axis1_array[-1]+step1/2]])

        self._mw.alignment_2d_GraphicsView.setLabel('bottom', 'Absolute Position, Axis0: ' + axis0_name, units=axis0_unit)
        self._mw.alignment_2d_GraphicsView.setLabel('left', 'Absolute Position, Axis1: '+ axis1_name, units=axis1_unit)


    def _update_2d_graph_cb(self):
        """ Update the colorbar to a new scaling.

        That function alters the color scaling of the colorbar next to the main
        picture.
        """

        # If "Centiles" is checked, adjust colour scaling automatically to
        # centiles. Otherwise, take user-defined values.

        if self._mw.alignment_2d_centiles_RadioButton.isChecked():

            low_centile = self._mw.alignment_2d_cb_low_centiles_DSpinBox.value()
            high_centile = self._mw.alignment_2d_cb_high_centiles_DSpinBox.value()

            if np.isclose(low_centile, 0.0):
                low_centile = 0.0

            # mask the array such that the arrays will be
            masked_image = np.ma.masked_equal(self._2d_alignment_ImageItem.image, 0.0)

            if len(masked_image.compressed()) == 0:
                cb_min = np.percentile(self._2d_alignment_ImageItem.image, low_centile)
                cb_max = np.percentile(self._2d_alignment_ImageItem.image, high_centile)
            else:
                cb_min = np.percentile(masked_image.compressed(), low_centile)
                cb_max = np.percentile(masked_image.compressed(), high_centile)

        else:
            cb_min = self._mw.alignment_2d_cb_min_centiles_DSpinBox.value()
            cb_max = self._mw.alignment_2d_cb_max_centiles_DSpinBox.value()

        self._2d_alignment_cb.refresh_colorbar(cb_min, cb_max)
        self._mw.alignment_2d_cb_GraphicsView.update()


    def save_2d_plots_and_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        timestamp = datetime.datetime.now()
        filetag = self._mw.alignment_2d_nametag_LineEdit.text()
        filepath = self._savelogic.get_path_for_module(module_name='Magnet')

        if len(filetag) > 0:
            filename = os.path.join(filepath, '{0}_{1}_Magnet'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
        else:
            filename = os.path.join(filepath, '{0}_Magnet'.format(timestamp.strftime('%Y%m%d-%H%M-%S'),))

        exporter_graph = pyqtgraph.exporters.SVGExporter(self._mw.alignment_2d_GraphicsView.plotItem.scene())
        exporter_graph.export(filename  + '.svg')

        self._magnetlogic.save_2d_data(filetag, timestamp)


    def cool_PSW_clicked(self):
        """ Emits signal to logic that PSW needs to be cooled.
        """
        status = self._magnetlogic.get_ramping_state()
        if not status == ([2,2,2] or [8,8,8]):
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle('Error!')
            msg.setText('Device is not in holding mode!')
            x = msg.exec_()
            return

        self.deactivate_control_buttons()
        self._psw_status_label = "Cooling PSwitch."
        self.sigCoolPsw.emit()
        return


    def heat_PSW_clicked(self):
        """ Emits signal to logic that PSW needs to be heated.
        """
        self.deactivate_control_buttons()
        self._psw_status_label = "Heating PSwitch."
        self.sigHeatPsw.emit()
        return

    def get_psw_status(self):
        """Asks logic for the status of the psw heaters as array. 

        [status heater x, status heater y, status heater z]
        
        0 means heater is switched off.
        1 means heateris switched on.
        """
        status = self._magnetlogic
        return status

    def get_persistent(self):
        """Asks logic for the mode of the magnets as array.
        
        [mode x, mode y, mode z]

        0 if in driven mode,
        1 if in persistent mode.
        """
        persistent = self._magnetlogic.get_persistent()
        return persistent

    def update_psw_status_label(self, label):
        # reactivate buttons if PSWs are hot/cold
        # not a nice way to do it
        if (label == 'PSW warm') or (label == 'PSW cold'):
            self.reactivate_control_buttons()
        self._mw.status_PSW_label.setText(label)
        return


    def change_magnet_status_label(self):
        self._mw.ramp_status_label.setText('Ramp done.')
        return


    def get_crosshair_posi_clicked(self):
        """Gets the position of the crosshair and changes the value in the spin boxes accordingly.
        """
        [theta, phi] = self.get_crosshair_posi()
        self._mw.rotate_abs_theta_DoubleSpinBox.setValue(theta)
        self._mw.rotate_abs_phi_DoubleSpinBox.setValue(phi)
        return

    def get_crosshair_posi(self):
        """Return the position of the crossshair in terms of theta, phi"""
        # get position of crosshair
        # you can get the posi of the crosshair in confocal by using
        # confocal._mw.xy_refocus_ViewWidget_2.crosshair_position
        # this will return tuple, e.g. (1.676e-05, 1.749e-05)
        (x,y) = self._mw.alignment_2d_GraphicsView.crosshair_position
        # maybe I need to process them to turn them into the angels
        theta = x
        phi = y
        return [theta, phi]