from __future__ import print_function, absolute_import, division

__metaclass__ = type

import sys, os
import logic.misc

from PyQt5.QtWidgets import QAbstractItemView, QMainWindow, QFileDialog
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
import PyQt5.uic
import PyQt5.QtWidgets
from logic.qudip_enhanced import *
import importlib
setup = False
#import multi_channel_awg_seq as MCAS; importlib.reload(MCAS)
import sip

try:
    sip.setapi('QDate', 2)
    sip.setapi('QDateTime', 2)
    sip.setapi('QString', 2)
    sip.setapi('QtextStream', 2)
    sip.setapi('Qtime', 2)
    sip.setapi('QUrl', 2)
    sip.setapi('QVariant', 2)
except ValueError as e:
    raise RuntimeError('Could not set API version (%s): did you import PyQt4 directly?' % e)

import datetime
import logging
import logging.handlers
import os
import pickle
import shutil
import sys
import threading
import time
from core.connector import Connector
from gui.guibase import GUIBase
import traceback
#import TimeTaggerHandler
import numpy as np
import psutil
import collections
from PyQt5 import QtCore, QtWidgets

class ScriptQueueStep:
    def __init__(self, name, pd):
        self.name = name
        self.pd = pd


class ScriptQueueList(collections.MutableSequence):
    def __init__(self, oktypes, list_owner, *args):
        self.oktypes = oktypes
        self.list_owner = list_owner
        self._list = list()
        self.extend(list(args))

    @property
    def list(self):
        return self._list

    @list.setter
    def list(self, val):
        """
        inefficient, calls script_queue_changed multiple times. In practice not relevant.
        """
        self._list = []
        if len(val) == 0:
            self.list_owner.script_queue_changed()
        else:
            try:
                for i in val:
                    self.append(i)
            except Exception:
                self._list = []
                self.list_owner.script_queue_changed()
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)

    def check(self, val):
        if not isinstance(val, self.oktypes):
            raise TypeError("list item {} is not allowed, as it can not be found in {}".format(val, self.oktypes))

    # def check_duplicate(self, v):
    #     duplicates = [item.name for item in self.list if item.name == v.name]
    #     if len(duplicates) > 0:
    #         raise Exception('Error: {}, {}, {}'.format(duplicates, self.list, v))

    def set_parent(self, v):
        v.parent = self.list_owner

    def __len__(self):
        return len(self.list)

    def __getitem__(self, i):
        return self.list[i]

    def __delitem__(self, i):
        del self.list[i]
        self.list_owner.script_queue_changed()

    def __setitem__(self, i, v):
        raise NotImplementedError
        # self.check(v)
        # self.check_duplicate(v)
        # self.list[i] = v
        # self.list_owner.script_queue_changed(i, v)

    def insert(self, i, v):
        if i != len(self.list):
            raise Exception('Only appending and popping items allowed')
        self.check(v)
        # self.check_duplicate(v)
        self.list.insert(i, v)
        self.list_owner.script_queue_changed()

    def __str__(self):
        return str(self.list)

    def __repr__(self):
        return str(self.list)

class window(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        super().__init__()
        # Load it
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir,'pi3d_main_window.ui')
        # Load ui
        PyQt5.uic.loadUi(ui_file, self)
        self.show()


class queue_gui(GUIBase):

    update_user_script_folder_text_field_signal = pyqtSignal(str)
    update_selected_user_script_combo_box_signal = pyqtSignal(collections.OrderedDict)
    update_script_queue_table_data_signal = pyqtSignal(collections.OrderedDict)
    update_user_script_params_text_field_signal = pyqtSignal(collections.OrderedDict)

    #Connect to the Queue.
    queue_logic = Connector(interface="queue_logic")  # class name

    def __init__(self, config, title=None, parent=None, no_qt=None, gui=True, **kwargs):
        super(queue_gui, self).__init__(config = config, **kwargs)

    def init_gui(self):
        self._mw.setWindowTitle('nuclear ops queue')
        # icon = QtGui.QIcon()
        # icon.addPixmap(QtGui.QPixmap(r"D:\Python\pi3diamond\qtgui\folder_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        # self.user_script_folder_pushButton.setIcon(icon)

        for name in [
            'update_user_script_folder_text_field',
            'update_selected_user_script_combo_box',
            'update_script_queue_table_data',
        ]:
            getattr(getattr(self, "{}_signal".format(name)), 'connect')(
                getattr(self, "{}_signal_emitted".format(name)))
        self._mw.selected_user_script_combo_box.currentIndexChanged.connect(
            self.update_selected_user_script_from_combo_box)
        self._mw.remove_next_script_button.clicked.connect(self.no_qt.remove_last_script)
        self._mw.set_stop_request_button.clicked.connect(self.no_qt.set_stop_request)
        self._mw.add_to_queue_button.clicked.connect(self.add_to_queue)
        self._mw.add_rco_button.clicked.connect(self.no_qt.add_rco)
        self._mw.evaluate_button.clicked.connect(self.no_qt.evaluate)
        self._mw.write_standard_awg_sequences_button.clicked.connect(self.no_qt.write_standard_awg_sequences)
        #self._mw.user_script_folder_text_field.textChanged.connect(self.user_script_folder_text_field_text_changed)
        self._mw.user_script_folder_pushButton.clicked.connect(self.open_user_script_folder_file_dialog)
        #self.show()
        self.no_qt.update_selected_user_script_combo_box_signal.connect(self.update_selected_user_script_combo_box)

    def on_activate(self):
        self._mw = window()
        self.no_qt = self.queue_logic()
        self.init_gui()

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def on_deactivate(self):
        self._mw.close()


    def add_to_queue(self, stupid_argument_emitted_by_qt_signal):
        self.no_qt.add_to_queue()


    def update_selected_user_script_combo_box(self,val):
        self.update_selected_user_script_combo_box_signal.emit(val)


    def update_selected_user_script_combo_box_signal_emitted(self, val):
        self._mw.selected_user_script_combo_box.blockSignals(True)
        if 'user_script_list' in val:
            self._mw.selected_user_script_combo_box.clear()
            self._mw.selected_user_script_combo_box.addItems(
                val['user_script_list'])  # currentIndexChanged is triggered, value is first item (e.g. sweeps)
        self._mw.selected_user_script_combo_box.setCurrentText(val['selected_user_script'])
        self._mw.selected_user_script_combo_box.blockSignals(False)


    def update_selected_user_script_from_combo_box(self):
        self.no_qt.selected_user_script = str(self._mw.selected_user_script_combo_box.currentText())


    def update_script_queue_table_data(self, val):
        self.update_script_queue_table_data_signal.emit(val)


    def update_script_queue_table_data_signal_emitted(self, val):
        self._mw.script_queue_table.blockSignals(True)
        self._mw.script_queue_table.clear_table_contents()
        self._mw.script_queue_table.set_column_names(['name', 'pd'])
        self._mw.script_queue_table.setColumnWidth(0, 400)
        self._mw.script_queue_table.setColumnWidth(1, 100)
        self._mw.script_queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._mw.script_queue_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for cn, cp in val.items():
            self._mw.script_queue_table.set_column(cn, data=cp, )
        self._mw.script_queue_table.blockSignals(False)


    def update_user_script_folder_text_field(self, val):
        self.update_user_script_folder_text_field_signal.emit(val)


    def update_user_script_folder_text_field_signal_emitted(self, val):
        self._mw.user_script_folder_text_field.blockSignals(True)
        self._mw.user_script_folder_text_field.setText(val)
        self._mw.user_script_folder_text_field.blockSignals(False)


    #def user_script_folder_text_field_text_changed(self):
        #self.user_script_folder = self._mw.user_script_folder_text_field.toPlainText()
        # needs to be cleaned up, and separated from logic# TODO

    def open_user_script_folder_file_dialog(self):
        self.user_script_folder = QFileDialog.getExistingDirectory(
            self._mw,
            'Select user_script_folder',
            r"/Users/vvv/Documents/GitHub/qudi/notebooks/UserScripts",
        )
        self.no_qt.user_script_folder = self.user_script_folder
        #this is working - need to do now the gui, no?
        #it calls a setter which then updates the text, why not update it here?
        self.update_user_script_folder_text_field(self.user_script_folder)