# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import numpy as np
import pandas as pd

import operator
from functools import partial
import itertools

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMenu, QAction
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtGui, QtWidgets, QtCore

class QTableWidgetEnhanced(QTableWidget):

    def __init__(self, parent=None):
        super(QTableWidgetEnhanced, self).__init__(parent)

    def cell_empty(self, ridx, cidx):
        return self.item(ridx, cidx).text() != ''

    def column_data_indices(self, column_name):
        """
        :return: all rows whose text is not an empty string, as this is considered a cell not containing data
        """
        cidx = self.column_index(column_name)
        return [ridx for ridx in range(self.rowCount()) if self.cell_empty(ridx, cidx)]

    def column_data(self, column_name):
        """
        :return: data of all rows, whose text is not an empty string, as this is considered a cell not containing data
        """
        cidx = self.column_index(column_name)
        return [self.item(ridx, cidx).data(0x0100) for ridx in self.column_data_indices(column_name)]

    def row_data_indices(self, ridx):
        return [cidx for cidx in range(self.columnCount()) if self.cell_empty(ridx, cidx)]

    def row_data(self, ridx):
        return [self.item(ridx, cidx).data(0x0100) for cidx in self.row_data_indices(ridx)]

    def set_cell(self, ridx, cidx, val=None, flag=None):
        item = self.item(ridx, cidx)
        if item is None:
            item = QTableWidgetItem()
            self.setItem(ridx, cidx, item)
            if flag is None:
                item.setFlags(Qt.NoItemFlags)
        if val is not None:
            item.setText(str(val))
            item.setData(0x0100, val)
        if flag is not None:
            item.setFlags(flag)

    def parse_data_flags(self, data=None, flags=None):
        if data is not None and flags is not None and len(data) != len(flags):
            raise Exception('Error: {}, {}'.format(data, flags))
        data = itertools.repeat(None) if data is None else data
        flags = itertools.repeat(None) if flags is None else flags
        return data, flags

    def set_column(self, column_name, data=None, flags=None):
        nd = len(data) if hasattr(data, '__len__') else 0
        nf = len(flags) if hasattr(flags, '__len__') else 0
        self.set_n_rows(max(nd, nf, self.rowCount()))
        data, flags = self.parse_data_flags(data=data, flags=flags)
        cidx = self.column_index(column_name=column_name)
        for ridx, val, flag in zip(range(self.rowCount()), data, flags):
            self.set_cell(ridx, cidx, val, flag)

    def set_row(self, ridx, data=None, flags=None):
        nd = len(data) if hasattr(data, '__len__') else 0
        nf = len(flags) if hasattr(flags, '__len__') else 0
        if max(nd, nf) > self.columnCount():
            raise Exception("Error: Can not set row {}.\nEither data or flags has more items than the table has columns.\n{}, {}".format(ridx, data, flags))
        data, flags = self.parse_data_flags(data=data, flags=flags)
        for cidx, val, flag in zip(range(self.columnCount()), data, flags):
            self.set_cell(ridx, cidx, val, flag)

    @property
    def column_names(self):
        return [self.horizontalHeaderItem(i).text() for i in range(self.columnCount())]

    def set_column_names(self, header):
        self.clear_table_contents()
        self.setColumnCount(len(header))
        self.setHorizontalHeaderLabels(header)

    def column_index(self, column_name):
        return self.column_names.index(column_name)

    def column_name(self, column_index):
        return self.column_names[column_index]

    def set_n_rows(self, n_rows):
        n_new = n_rows - self.rowCount()
        if n_new > 0:
            n_old = self.rowCount()
            self.setRowCount(n_old+n_new)
            for ridx in range(n_old, n_old+n_new):
                self.set_row(ridx)

    def selected_column_items(self, column_name):
        out = []
        for item in self.selectedItems():
            if item.column() == self.column_index(column_name=column_name):
                out.append(item.data(0x0100))
        return out

    def selected_row_items(self, ridx):
        out = []
        for item in self.selectedItems():
            if item.row() == ridx:
                out.append(item.data(0x0100))
        return out

    def selected_items_unique_row_indices(self):
        return list(set([i.row() for i in self.selectedItems()]))

    def clear_column_data(self, column_name):
        cidx = self.column_index(column_name=column_name)
        for ridx in range(self.columnCount()):
            self.set_cell(ridx, cidx, val="")

    def clear_column_flags(self, column_name):
        cidx = self.column_index(column_name=column_name)
        for ridx in range(self.columnCount()):
            self.set_cell(ridx, cidx, flag=Qt.NoItemFlags)

    def clear_table_contents(self):
        for column_name in self.column_names:
            self.clear_column_data(column_name)
            self.clear_column_flags(column_name)
        super(QTableWidgetEnhanced, self).clear()
        # self.clear()
        self.setRowCount(0)
        self.setColumnCount(0)

class QTableWidgetEnhancedDrop(QTableWidgetEnhanced):

    def __init__(self, parent=None):
        super(QTableWidgetEnhancedDrop, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    hdf_file_dropped = pyqtSignal(str)

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            if len(links) != 1:
                print('Warning: {}, {}'.format(links, len(links)))
                event.ignore()
            elif not links[0].endswith(".hdf"):
                print('Warning: {}, {}'.format(links, links[0][:-4]))
                event.ignore()
            else:
                self.hdf_file_dropped.emit(links[0])
        else:
            event.ignore()

class QTableWidgetEnhancedContextMenu(QTableWidgetEnhanced):

    def contextMenuEvent(self, event):
        self.menu = QMenu(self)
        remove_script_action = QAction('Remove row', self)
        self.menu.addAction(remove_script_action)
        self.menu.popup(QCursor.pos())