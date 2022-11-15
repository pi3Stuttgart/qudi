# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Python\pi3diamond/qtgui/transition_tracker.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!
import datetime
import numpy as np
import os
import pyqtgraph as pg
import pyqtgraph.exporters

from core.connector import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem
from qtpy import QtCore
from qtpy import uic
from PyQt5 import QtCore, QtGui, QtWidgets

class window(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        super().__init__()
        # Load it
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'transition_tracker.ui')

        # Load it

        uic.loadUi(ui_file, self)
        self.show()

class TransitionTrackerGui(GUIBase):
    transition_tracker_logic = Connector(interface="TransitionTracker") #class name

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        #self.show()

    def on_activate(self):
        self._mw = window()
        self._transition_tracker = self.transition_tracker_logic()

        self._mw.setObjectName("window")
        self._mw.resize(760, 793)
        self._mw.setWindowOpacity(1.0)
        self._mw.setAutoFillBackground(False)
        #self.button = QtWidgets.QPushButton('start')
        #self._mw.addItem(self.button)
        self.remove_next_script_button = QtWidgets.QPushButton(self._mw)
        self.remove_next_script_button.setGeometry(QtCore.QRect(680, 970, 761, 31))
        self.remove_next_script_button.setObjectName("remove_next_script_button")
        # self.script_queue_table = QTableWidgetEnhancedDrop(self._mw)
        # self.script_queue_table.setEnabled(True)
        # self.script_queue_table.setGeometry(QtCore.QRect(10, 220, 731, 561))
        # self.script_queue_table.setAutoFillBackground(False)
        # self.script_queue_table.setFrameShape(QtWidgets.QFrame.Panel)
        # self.script_queue_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        # self.script_queue_table.setObjectName("script_queue_table")
        # self.script_queue_table.setColumnCount(0)
        # self.script_queue_table.setRowCount(0)
        # self.set_stop_request_button = QtWidgets.QPushButton(self._mw)
        # self.set_stop_request_button.setGeometry(QtCore.QRect(680, 1010, 761, 41))
        # self.set_stop_request_button.setObjectName("set_stop_request_button")
        # self.current_local_oscillator_freq_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.current_local_oscillator_freq_text_field.setEnabled(True)
        # self.current_local_oscillator_freq_text_field.setGeometry(QtCore.QRect(10, 40, 161, 31))
        # self.current_local_oscillator_freq_text_field.setReadOnly(False)
        # self.current_local_oscillator_freq_text_field.setObjectName("current_local_oscillator_freq_text_field")
        # self.current_local_oscillator_freq_label = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label.setEnabled(True)
        # self.current_local_oscillator_freq_label.setGeometry(QtCore.QRect(10, 20, 151, 16))
        # self.current_local_oscillator_freq_label.setObjectName("current_local_oscillator_freq_label")
        # self.current_local_oscillator_freq_label_2 = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label_2.setEnabled(True)
        # self.current_local_oscillator_freq_label_2.setGeometry(QtCore.QRect(10, 80, 161, 16))
        # self.current_local_oscillator_freq_label_2.setObjectName("current_local_oscillator_freq_label_2")
        # self.current_local_oscillator_freq_p1_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.current_local_oscillator_freq_p1_text_field.setEnabled(True)
        # self.current_local_oscillator_freq_p1_text_field.setGeometry(QtCore.QRect(10, 100, 161, 31))
        # self.current_local_oscillator_freq_p1_text_field.setReadOnly(False)
        # self.current_local_oscillator_freq_p1_text_field.setObjectName("current_local_oscillator_freq_p1_text_field")
        # self.current_local_oscillator_freq_label_3 = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label_3.setEnabled(True)
        # self.current_local_oscillator_freq_label_3.setGeometry(QtCore.QRect(190, 20, 161, 16))
        # self.current_local_oscillator_freq_label_3.setObjectName("current_local_oscillator_freq_label_3")
        # self.current_local_oscillator_freq_label_4 = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label_4.setEnabled(True)
        # self.current_local_oscillator_freq_label_4.setGeometry(QtCore.QRect(190, 80, 161, 16))
        # self.current_local_oscillator_freq_label_4.setObjectName("current_local_oscillator_freq_label_4")
        # self.current_local_oscillator_freq_label_5 = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label_5.setEnabled(True)
        # self.current_local_oscillator_freq_label_5.setGeometry(QtCore.QRect(370, 20, 161, 16))
        # self.current_local_oscillator_freq_label_5.setObjectName("current_local_oscillator_freq_label_5")
        # self.current_local_oscillator_freq_label_6 = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label_6.setEnabled(True)
        # self.current_local_oscillator_freq_label_6.setGeometry(QtCore.QRect(370, 80, 161, 16))
        # self.current_local_oscillator_freq_label_6.setObjectName("current_local_oscillator_freq_label_6")
        # self.mw_mixing_frequency_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.mw_mixing_frequency_text_field.setEnabled(True)
        # self.mw_mixing_frequency_text_field.setGeometry(QtCore.QRect(190, 40, 161, 31))
        # self.mw_mixing_frequency_text_field.setReadOnly(False)
        # self.mw_mixing_frequency_text_field.setObjectName("mw_mixing_frequency_text_field")
        # self.mw_mixing_frequency_p1_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.mw_mixing_frequency_p1_text_field.setEnabled(True)
        # self.mw_mixing_frequency_p1_text_field.setGeometry(QtCore.QRect(190, 100, 161, 31))
        # self.mw_mixing_frequency_p1_text_field.setReadOnly(False)
        # self.mw_mixing_frequency_p1_text_field.setObjectName("mw_mixing_frequency_p1_text_field")
        # self.mw_transition_frequency_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.mw_transition_frequency_text_field.setEnabled(True)
        # self.mw_transition_frequency_text_field.setGeometry(QtCore.QRect(370, 40, 161, 31))
        # self.mw_transition_frequency_text_field.setReadOnly(False)
        # self.mw_transition_frequency_text_field.setObjectName("mw_transition_frequency_text_field")
        # self.mw_transition_frequency_p1_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.mw_transition_frequency_p1_text_field.setEnabled(True)
        # self.mw_transition_frequency_p1_text_field.setGeometry(QtCore.QRect(370, 100, 161, 31))
        # self.mw_transition_frequency_p1_text_field.setReadOnly(False)
        # self.mw_transition_frequency_p1_text_field.setObjectName("mw_transition_frequency_p1_text_field")
        # self.current_local_oscillator_freq_label_7 = QtWidgets.QLabel(self._mw)
        # self.current_local_oscillator_freq_label_7.setEnabled(True)
        # self.current_local_oscillator_freq_label_7.setGeometry(QtCore.QRect(570, 50, 161, 16))
        # self.current_local_oscillator_freq_label_7.setObjectName("current_local_oscillator_freq_label_7")
        # self.zero_field_splitting_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.zero_field_splitting_text_field.setEnabled(True)
        # self.zero_field_splitting_text_field.setGeometry(QtCore.QRect(570, 70, 161, 31))
        # self.zero_field_splitting_text_field.setReadOnly(False)
        # self.zero_field_splitting_text_field.setObjectName("zero_field_splitting_text_field")
        # self.ple_Ex_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.ple_Ex_text_field.setEnabled(True)
        # self.ple_Ex_text_field.setGeometry(QtCore.QRect(10, 160, 161, 31))
        # self.ple_Ex_text_field.setReadOnly(False)
        # self.ple_Ex_text_field.setObjectName("ple_Ex_text_field")
        # self.ple_A1_text_field = QtWidgets.QTextBrowser(self._mw)
        # self.ple_A1_text_field.setEnabled(True)
        # self.ple_A1_text_field.setGeometry(QtCore.QRect(190, 160, 161, 31))
        # self.ple_A1_text_field.setReadOnly(False)
        # self.ple_A1_text_field.setObjectName("ple_A1_text_field")
        # self.ple_Ex_label = QtWidgets.QLabel(self._mw)
        # self.ple_Ex_label.setEnabled(True)
        # self.ple_Ex_label.setGeometry(QtCore.QRect(10, 140, 161, 16))
        # self.ple_Ex_label.setObjectName("ple_Ex_label")
        # self.ple_A1_label = QtWidgets.QLabel(self._mw)
        # self.ple_A1_label.setEnabled(True)
        # self.ple_A1_label.setGeometry(QtCore.QRect(190, 140, 161, 16))
        # self.ple_A1_label.setObjectName("ple_A1_label")
        self._transition_tracker.update_tt_nuclear_gui.connect(self.update_gui_nuclear)
        self._transition_tracker.update_tt_electron_gui.connect(self.update_gui_electron)

        #self.retranslateUi(self._mw)
        #QtCore.QMetaObject.connectSlotsByName(self._mw)

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def on_deactivate(self):
        self._mw.close()

    def update_gui_electron(self):
        self._mw.current_local_oscillator_freq_text_field.setText("{:.10f}".format(self._transition_tracker.current_local_oscillator_freq))
        self._mw.current_local_oscillator_freq_p1_text_field.setText("{:.10f}".format(self._transition_tracker.current_local_oscillator_freq_p1))
        self._mw.mw_mixing_frequency_text_field.setText("{:.10f}".format(self._transition_tracker.mw_mixing_frequency))
        self._mw.mw_mixing_frequency_p1_text_field.setText("{:.10f}".format(self._transition_tracker.mw_mixing_frequency_p1))
        self._mw.mw_transition_frequency_text_field.setText("{:.10f}".format(self._transition_tracker.mw_transition_frequency))
        self._mw.mw_transition_frequency_p1_text_field.setText("{:.10f}".format(self._transition_tracker.mw_transition_frequency_p1))
        self._mw.zero_field_splitting_text_field.setText("{:.10f}".format(self._transition_tracker.zero_field_splitting))
        self._mw.ple_A2_text_field.setText("{:.10f}".format(self._transition_tracker.ple_A2))
        self._mw.ple_A1_text_field.setText("{:.10f}".format(self._transition_tracker.ple_A1))
        # self.ple_repump_text_field.setText("{:.10f}".format(self.ple_A1))




    def update_gui_nuclear(self):
        column_names = ['name', 'current_frequency', 'ms_state', 'spin_type', 'start_level', 'end_level']
        print('update gui nulcear Transition Tracker')
        self._mw.script_queue_table.setColumnCount(len(column_names))
        self._mw.script_queue_table.clearSelection()
        self._mw.script_queue_table.clear()
        self._mw.script_queue_table.setHorizontalHeaderLabels(column_names)
        self._mw.script_queue_table.setEnabled(True)
        self._mw.script_queue_table.setRowCount(len(self._transition_tracker.transitions))
        for ridx, t in enumerate(self._transition_tracker.transitions):
            for cidx, attr_name in enumerate(column_names):
                new_item = QTableWidgetItem(str(getattr(t, attr_name)))
                self._mw.script_queue_table.setItem(ridx, cidx, new_item)

    def retranslateUi(self, window):
        _translate = QtCore.QCoreApplication.translate
        window.setWindowTitle(_translate("window", "Form"))
        self.remove_next_script_button.setText(_translate("window", "Remove next script"))
        self.set_stop_request_button.setText(_translate("window", "Set stop_request"))
        self.current_local_oscillator_freq_label.setText(_translate("window", "current_local_oscillator_freq"))
        self.current_local_oscillator_freq_label_2.setText(_translate("window", "current_local_oscillator_freq_p1"))
        self.current_local_oscillator_freq_label_3.setText(_translate("window", "mw_mixing_frequency"))
        self.current_local_oscillator_freq_label_4.setText(_translate("window", "mw_mixing_frequency_p1"))
        self.current_local_oscillator_freq_label_5.setText(_translate("window", "mw_transition_frequency"))
        self.current_local_oscillator_freq_label_6.setText(_translate("window", "mw_transition_frequency_p1"))
        self.current_local_oscillator_freq_label_7.setText(_translate("window", "zero_field_splitting"))
        self.ple_A2_label.setText(_translate("window", "PLE A2"))
        self.ple_A1_label.setText(_translate("window", "PLE A1"))


from qutip_enhanced.qtgui.custom_widgets import QTableWidgetEnhancedDrop
