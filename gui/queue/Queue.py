from __future__ import print_function, absolute_import, division

__metaclass__ = type

import sys, os
import misc


import imp
from Queue import Queue

from PyQt5.QtWidgets import QAbstractItemView, QMainWindow, QFileDialog
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
import PyQt5.uic
import PyQt5.QtWidgets
from qutip_enhanced import *
import multi_channel_awg_seq as MCAS; reload(MCAS)


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
import traceback
import TimeTaggerHandler
import numpy as np
import psutil
import collections



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

class queue_gui(QMainWindow):

    update_user_script_folder_text_field_signal = pyqtSignal(str)
    update_selected_user_script_combo_box_signal = pyqtSignal(collections.OrderedDict)
    update_script_queue_table_data_signal = pyqtSignal(collections.OrderedDict)
    update_user_script_params_text_field_signal = pyqtSignal(collections.OrderedDict)


    def __init__(self, title=None, parent=None, no_qt=None, gui=True):
        super(queue_gui, self).__init__(parent=parent)
        self.no_qt = no_qt
        PyQt5.uic.loadUi(os.path.join(self.no_qt.app_dir, 'qtgui/pi3d_main_window.ui'), self)
        self.init_gui()


    def init_gui(self):
        self.setWindowTitle('Pi3Diamond')
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(r"D:\Python\pi3diamond\qtgui\folder_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.user_script_folder_pushButton.setIcon(icon)

        for name in [
            'update_user_script_folder_text_field',
            'update_selected_user_script_combo_box',
            'update_script_queue_table_data',
        ]:
            getattr(getattr(self, "{}_signal".format(name)), 'connect')(getattr(self, "{}_signal_emitted".format(name)))

        self.selected_user_script_combo_box.currentIndexChanged.connect(self.update_selected_user_script_from_combo_box)
        self.remove_next_script_button.clicked.connect(self.no_qt.remove_last_script)
        self.set_stop_request_button.clicked.connect(self.no_qt.set_stop_request)
        self.add_to_queue_button.clicked.connect(self.add_to_queue)
        self.add_rco_button.clicked.connect(self.no_qt.add_rco)
        self.evaluate_button.clicked.connect(self.no_qt.evaluate)
        self.write_standard_awg_sequences_button.clicked.connect(self.no_qt.write_standard_awg_sequences)
        self.user_script_folder_text_field.textChanged.connect(self.user_script_folder_text_field_text_changed)
        self.user_script_folder_pushButton.clicked.connect(self.open_user_script_folder_file_dialog)


    def add_to_queue(self, stupid_argument_emitted_by_qt_signal):
        self.no_qt.add_to_queue()


    def update_selected_user_script_combo_box(self, val):
        self.update_selected_user_script_combo_box_signal.emit(val)


    def update_selected_user_script_combo_box_signal_emitted(self, val):
        self.selected_user_script_combo_box.blockSignals(True)
        if 'user_script_list' in val:
            self.selected_user_script_combo_box.clear()
            self.selected_user_script_combo_box.addItems(
                val['user_script_list'])  # currentIndexChanged is triggered, value is first item (e.g. sweeps)
        self.selected_user_script_combo_box.setCurrentText(val['selected_user_script'])
        self.selected_user_script_combo_box.blockSignals(False)


    def update_selected_user_script_from_combo_box(self):
        self.no_qt.selected_user_script = str(self.selected_user_script_combo_box.currentText())


    def update_script_queue_table_data(self, val):
        self.update_script_queue_table_data_signal.emit(val)


    def update_script_queue_table_data_signal_emitted(self, val):
        self.script_queue_table.blockSignals(True)
        self.script_queue_table.clear_table_contents()
        self.script_queue_table.set_column_names(['name', 'pd'])
        self.script_queue_table.setColumnWidth(0, 400)
        self.script_queue_table.setColumnWidth(1, 100)
        self.script_queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.script_queue_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for cn, cp in val.items():
            self.script_queue_table.set_column(cn, data=cp, )
        self.script_queue_table.blockSignals(False)


    def update_user_script_folder_text_field(self, val):
        self.update_user_script_folder_text_field_signal.emit(val)


    def update_user_script_folder_text_field_signal_emitted(self, val):
        self.user_script_folder_text_field.blockSignals(True)
        self.user_script_folder_text_field.setText(val)
        self.user_script_folder_text_field.blockSignals(False)


    def user_script_folder_text_field_text_changed(self):
        self.user_script_folder = self.user_script_folder_text_field.toPlainText()


    def open_user_script_folder_file_dialog(self):
        self.no_qt.user_script_folder = QFileDialog.getExistingDirectory(
            self,
            'Select user_script_folder',
            r"D:\Python\pi3diamond\UserScripts",
        )