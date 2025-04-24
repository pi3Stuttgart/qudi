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


import sys
import pandas as pd

try:
    NA = pd.NA
except AttributeError:
    # pandas < 1.0
    NA = np.nan

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

# class DataFrameTableWidget(QtWidgets.QWidget):
#     def __init__(self, df):
#         super().__init__()
#         self.df = df.copy()

#         # Each unique spin (group) defines a separate section.
#         self.unique_spins = self.df['spin name'].unique().tolist()

#         # Define choices with the special option '_none_'.
#         self.subspace_choices = ["_none_"] + sorted(self.df['subspace'].unique().tolist())
#         self.dd_method_choices = ["_none_"] + sorted(self.df['dd_method'].unique().tolist())

#         # All additional columns.
#         self.extra_columns = [c for c in self.df.columns if c not in ['spin name', 'subspace', 'dd_method']]

#         # Store current filter choices for each spin.
#         # By default, we set both to '_none_'.
#         self.spin_filters = {spin: (self.subspace_choices[0], self.dd_method_choices[0])
#                              for spin in self.unique_spins}

#         self.init_ui()
#         # Build the table at startup.
#         self.rebuild_table()

#     def init_ui(self):
#         layout = QtWidgets.QVBoxLayout(self)

#         # Global filter controls.
#         global_controls = QtWidgets.QHBoxLayout()
#         global_controls.addWidget(QtWidgets.QLabel("Global Subspace:"))
#         self.global_subspace = QtWidgets.QComboBox()
#         self.global_subspace.addItems(self.subspace_choices)
#         global_controls.addWidget(self.global_subspace)

#         global_controls.addWidget(QtWidgets.QLabel("Global dd_method:"))
#         self.global_dd_method = QtWidgets.QComboBox()
#         self.global_dd_method.addItems(self.dd_method_choices)
#         global_controls.addWidget(self.global_dd_method)

#         self.apply_global_button = QtWidgets.QPushButton("Apply Global Settings")
#         self.apply_global_button.clicked.connect(self.apply_global_settings)
#         global_controls.addWidget(self.apply_global_button)

#         layout.addLayout(global_controls)

#         # Create table widget.
#         self.table = QtWidgets.QTableWidget()
#         ncols = 2 + len(self.extra_columns) + 1  # Two for filtering controls, extra columns, plus copy button.
#         self.table.setColumnCount(ncols)
#         headers = ['Subspace', 'dd_method'] + self.extra_columns + ['Copy']
#         self.table.setHorizontalHeaderLabels(headers)
#         self.table.verticalHeader().setVisible(True)

#         layout.addWidget(self.table)
#         self.setLayout(layout)
#         self.setWindowTitle("Spin register")
#         self.resize(800, 600)

#     def rebuild_table(self):
#         """
#         Rebuilds the table by first inserting a control row for each spin (with comboboxes)
#         and then inserting one or more data rows immediately below to display all the matching records.
#         """
#         # Clear the table.
#         self.table.setRowCount(0)

#         for spin in self.unique_spins:
#             # Get the current filter selections for this spin.
#             curr_subspace, curr_dd_method = self.spin_filters.get(
#                 spin, (self.subspace_choices[0], self.dd_method_choices[0])
#             )

#             # Create a header (control) row for the spin.
#             control_row = self.table.rowCount()
#             self.table.insertRow(control_row)
#             # Display the spin name in the row header.
#             self.table.setVerticalHeaderItem(control_row, QtWidgets.QTableWidgetItem(spin))

#             # Add comboboxes as filtering controls.
#             subspace_cb = QtWidgets.QComboBox()
#             subspace_cb.addItems(self.subspace_choices)
#             subspace_cb.setCurrentText(curr_subspace)
#             subspace_cb.currentIndexChanged.connect(
#                 lambda _, spin=spin, cb=subspace_cb: self.on_control_changed(spin, cb.currentText(), None)
#             )
#             self.table.setCellWidget(control_row, 0, subspace_cb)

#             dd_method_cb = QtWidgets.QComboBox()
#             dd_method_cb.addItems(self.dd_method_choices)
#             dd_method_cb.setCurrentText(curr_dd_method)
#             dd_method_cb.currentIndexChanged.connect(
#                 lambda _, spin=spin, cb=dd_method_cb: self.on_control_changed(spin, None, cb.currentText())
#             )
#             self.table.setCellWidget(control_row, 1, dd_method_cb)

#             # In the control row, we leave the extra columns empty.
#             for col_idx in range(len(self.extra_columns)):
#                 item = QtWidgets.QTableWidgetItem("")
#                 item.setFlags(Qt.ItemIsEnabled)
#                 self.table.setItem(control_row, 2 + col_idx, item)

#             # Optionally, you could add a copy button here that copies the current filter settings.
#             copy_ctrl = QtWidgets.QPushButton("Copy")
#             copy_ctrl.clicked.connect(lambda _, row=control_row, spin=spin: self.copy_row(row))
#             self.table.setCellWidget(control_row, 2 + len(self.extra_columns), copy_ctrl)

#             # Now, query the DataFrame for matching records for this spin.
#             df_spin = self.df[self.df['spin name'] == spin]
#             mask = pd.Series([True] * len(df_spin), index=df_spin.index)
#             if curr_subspace != "_none_":
#                 mask &= (df_spin['subspace'] == curr_subspace)
#             if curr_dd_method != "_none_":
#                 mask &= (df_spin['dd_method'] == curr_dd_method)
#             df_match = df_spin[mask]

#             # Insert a data row for each matching record.
#             for i, (_, record) in enumerate(df_match.iterrows()):
#                 data_row = self.table.rowCount()
#                 self.table.insertRow(data_row)
#                 # Data rows do not have a spin name in their vertical header.
#                 self.table.setVerticalHeaderItem(data_row, QtWidgets.QTableWidgetItem(""))

#                 # Instead of comboboxes, show the record's values for subspace and dd_method.
#                 subspace_item = QtWidgets.QTableWidgetItem(str(record['subspace']))
#                 subspace_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
#                 self.table.setItem(data_row, 0, subspace_item)

#                 dd_method_item = QtWidgets.QTableWidgetItem(str(record['dd_method']))
#                 dd_method_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
#                 self.table.setItem(data_row, 1, dd_method_item)

#                 # Set extra columns.
#                 for col_idx, extra_col in enumerate(self.extra_columns):
#                     item = QtWidgets.QTableWidgetItem(str(record[extra_col]))
#                     item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
#                     self.table.setItem(data_row, 2 + col_idx, item)

#                 # Copy button for this data row.
#                 copy_button = QtWidgets.QPushButton("Copy")
#                 copy_button.clicked.connect(lambda _, row=data_row: self.copy_row(row))
#                 self.table.setCellWidget(data_row, 2 + len(self.extra_columns), copy_button)

#     def on_control_changed(self, spin, new_subspace, new_dd_method):
#         """
#         Triggered when one of the filtering comboboxes in the control row changes.
#         Updates the stored filter for the spin and rebuilds the table.
#         Either new_subspace or new_dd_method may be None to indicate no change.
#         """
#         curr_subspace, curr_dd_method = self.spin_filters.get(
#             spin, (self.subspace_choices[0], self.dd_method_choices[0])
#         )
#         if new_subspace is not None:
#             curr_subspace = new_subspace
#         if new_dd_method is not None:
#             curr_dd_method = new_dd_method
#         self.spin_filters[spin] = (curr_subspace, curr_dd_method)
#         self.rebuild_table()

#     def copy_row(self, row_idx):
#         """
#         Copies the contents of the given row to the clipboard.
#         The text is formatted as:
#           subspace:[value]
#           dd_method:[value]
#           [extra column]:[value] ...
#         """
#         subspace_val = ""
#         dd_method_val = ""

#         # Try to get text from a combobox first.
#         widget_sub = self.table.cellWidget(row_idx, 0)
#         if widget_sub is not None and isinstance(widget_sub, QtWidgets.QComboBox):
#             subspace_val = widget_sub.currentText()
#         else:
#             item = self.table.item(row_idx, 0)
#             subspace_val = item.text() if item else ""

#         widget_dd = self.table.cellWidget(row_idx, 1)
#         if widget_dd is not None and isinstance(widget_dd, QtWidgets.QComboBox):
#             dd_method_val = widget_dd.currentText()
#         else:
#             item = self.table.item(row_idx, 1)
#             dd_method_val = item.text() if item else ""

#         # Gather extra column values.
#         lines = [
#             f"subspace:{subspace_val}",
#             f"dd_method:{dd_method_val}"
#         ]
#         for col_idx, extra_col in enumerate(self.extra_columns):
#             item = self.table.item(row_idx, 2 + col_idx)
#             value = item.text() if item is not None else ""
#             lines.append(f"{extra_col}: {value}")
#         text_to_copy = "\n".join(lines)

#         clipboard = QtWidgets.QApplication.clipboard()
#         clipboard.setText(text_to_copy)
#         QtWidgets.QMessageBox.information(self, "Copied", f"Row data copied to clipboard:\n\n{text_to_copy}")

#     def get_spin(self, spin_name, subspace, dd_method):
#         """
#         Returns the DataFrame filtered by spin name, subspace, and dd_method.
#         If subspace or dd_method is '_none_', that criterion is ignored.
#         """
#         filtered = self.df[self.df['spin name'] == spin_name]
#         if subspace != "_none_":
#             filtered = filtered[filtered['subspace'] == subspace]
#         if dd_method != "_none_":
#             filtered = filtered[filtered['dd_method'] == dd_method]
#         return filtered

#     def apply_global_settings(self):
#         """
#         Updates the filter choices for all spins with the global selections,
#         then rebuilds the table.
#         """
#         global_sub = self.global_subspace.currentText()
#         global_dd = self.global_dd_method.currentText()
#         for spin in self.unique_spins:
#             self.spin_filters[spin] = (global_sub, global_dd)
#         self.rebuild_table()

class DataFrameTableWidget(QtWidgets.QWidget):
    def __init__(self, df):
        super().__init__()
        # Copy DataFrame and enforce pandas nullable dtypes
        self.df = df.copy()
        # Ensure key columns are pandas StringDtype
        for c in ['spin name', 'subspace', 'dd_method']:
            self.df[c] = self.df[c].astype('str')

        # Identify extra columns and convert to nullable dtypes
        self.extra_columns = [c for c in self.df.columns if c not in ['spin name','subspace','dd_method']]
        for col in self.extra_columns:
            if pd.api.types.is_integer_dtype(self.df[col].dtype):
                self.df[col] = self.df[col].astype('Int64')
            elif pd.api.types.is_float_dtype(self.df[col].dtype):
                self.df[col] = self.df[col].astype('Float64')
            else:
                self.df[col] = self.df[col].astype('str')

        self.unique_spins = self.df['spin name'].dropna().unique().tolist()
        self.subspace_choices = ['_none_'] + sorted(self.df['subspace'].dropna().unique().tolist())
        self.dd_method_choices = ['_none_'] + sorted(self.df['dd_method'].dropna().unique().tolist())
        self.spin_filters = {s: (self.subspace_choices[0], self.dd_method_choices[0]) for s in self.unique_spins}

        # Row metadata and guard
        self.row_infos = []
        self.updating = False

        self.init_ui()
        self.rebuild_table()

    def init_ui(self):
        vlay = QtWidgets.QVBoxLayout(self)

        # Global filters
        hlay = QtWidgets.QHBoxLayout()
        hlay.addWidget(QtWidgets.QLabel('Global Subspace:'))
        self.global_sub = QtWidgets.QComboBox(); self.global_sub.addItems(self.subspace_choices)
        hlay.addWidget(self.global_sub)
        hlay.addWidget(QtWidgets.QLabel('Global dd_method:'))
        self.global_dd = QtWidgets.QComboBox(); self.global_dd.addItems(self.dd_method_choices)
        hlay.addWidget(self.global_dd)
        btn = QtWidgets.QPushButton('Apply Global'); btn.clicked.connect(self.apply_global_settings)
        hlay.addWidget(btn)
        vlay.addLayout(hlay)

        # Table
        self.table = QtWidgets.QTableWidget()
        ncols = 2 + len(self.extra_columns) + 1
        self.table.setColumnCount(ncols)
        self.table.setHorizontalHeaderLabels(['Subspace','dd_method'] + self.extra_columns + ['Copy/Add'])
        self.table.itemChanged.connect(self.on_item_changed)
        vlay.addWidget(self.table)

        self.setLayout(vlay)
        self.setWindowTitle('Live‑editable DataFrame with Nullable Dtypes')
        self.resize(900, 600)

    def save_to_hdf(self):
        # Convert extension dtypes to numpy-compatible for PyTables table format
        df_save = self.df.copy()
        for col in df_save.columns:
            if pd.api.types.is_integer_dtype(df_save[col].dtype) or pd.api.types.is_float_dtype(df_save[col].dtype):
                df_save[col] = df_save[col].astype('float64')
            elif pd.api.types.is_string_dtype(df_save[col].dtype):
                df_save[col] = df_save[col].astype('object')
        df_save.to_hdf(path_or_buf=r"C:\src\qudi\register_df_live.hdf", key='data', mode='w', format='table')

    def save_backup_hdf(self):
        # Convert extension dtypes to numpy-compatible for PyTables table format
        df_save = self.df.copy()
        for col in df_save.columns:
            if pd.api.types.is_integer_dtype(df_save[col].dtype) or pd.api.types.is_float_dtype(df_save[col].dtype):
                df_save[col] = df_save[col].astype('float64')
            elif pd.api.types.is_string_dtype(df_save[col].dtype):
                df_save[col] = df_save[col].astype('object')
        df_save.to_hdf(path_or_buf=r"C:\src\qudi\register_df_backup.hdf", key='data', mode='w', format='table')

    def rebuild_table(self):
        self.updating = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.row_infos.clear()

        for spin in self.unique_spins:
            subf, ddf = self.spin_filters[spin]
            # Control row
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setVerticalHeaderItem(r, QtWidgets.QTableWidgetItem(spin))
            cb1 = QtWidgets.QComboBox(); cb1.addItems(self.subspace_choices); cb1.setCurrentText(subf)
            cb1.currentIndexChanged.connect(lambda _, s=spin, cb=cb1: self.on_control(s, cb.currentText(), None))
            self.table.setCellWidget(r,0,cb1)
            cb2 = QtWidgets.QComboBox(); cb2.addItems(self.dd_method_choices); cb2.setCurrentText(ddf)
            cb2.currentIndexChanged.connect(lambda _, s=spin, cb=cb2: self.on_control(s, None, cb.currentText()))
            self.table.setCellWidget(r,1,cb2)
            for ci in range(len(self.extra_columns)):
                itm = QtWidgets.QTableWidgetItem(''); itm.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(r,2+ci,itm)
            btn = QtWidgets.QPushButton('Copy'); btn.clicked.connect(lambda _, row=r: self.copy_row(row))
            self.table.setCellWidget(r,2+len(self.extra_columns),btn)
            self.row_infos.append({'type':'control','spin':spin})

            # Data rows
            df_spin = self.df[self.df['spin name']==spin]
            mask = pd.Series(True, index=df_spin.index)
            if subf!='_none_': mask &= df_spin['subspace']==subf
            if ddf!='_none_': mask &= df_spin['dd_method']==ddf
            df_match = df_spin[mask]
            for idx,rec in df_match.iterrows():
                r2 = self.table.rowCount(); self.table.insertRow(r2)
                self.table.setVerticalHeaderItem(r2,QtWidgets.QTableWidgetItem(''))
                # subspace, dd_method
                for ci, key in enumerate(['subspace','dd_method']):
                    val = rec[key]
                    txt = '' if pd.isna(val) else str(val)
                    it = QtWidgets.QTableWidgetItem(txt)
                    it.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
                    self.table.setItem(r2,ci,it)
                # extra cols editable
                for ci,col in enumerate(self.extra_columns):
                    v = rec[col]; txt = '' if pd.isna(v) else str(v)
                    it = QtWidgets.QTableWidgetItem(txt)
                    it.setFlags(it.flags()|Qt.ItemIsEditable)
                    self.table.setItem(r2,2+ci,it)
                b2 = QtWidgets.QPushButton('Copy'); b2.clicked.connect(lambda _, row=r2: self.copy_row(row))
                self.table.setCellWidget(r2,2+len(self.extra_columns),b2)
                self.row_infos.append({'type':'data','df_idx':idx})

            # New-entry row
            rn = self.table.rowCount(); self.table.insertRow(rn)
            self.table.setVerticalHeaderItem(rn,QtWidgets.QTableWidgetItem(''))
            in_sub = QtWidgets.QLineEdit(); self.table.setCellWidget(rn,0,in_sub)
            in_dd  = QtWidgets.QLineEdit(); self.table.setCellWidget(rn,1,in_dd)
            for ci in range(len(self.extra_columns)):
                it = QtWidgets.QTableWidgetItem(''); it.setFlags(it.flags()|Qt.ItemIsEditable)
                self.table.setItem(rn,2+ci,it)
            b3 = QtWidgets.QPushButton('Add'); b3.clicked.connect(lambda _,row=rn,s=spin: self.add_new(row,s))
            self.table.setCellWidget(rn,2+len(self.extra_columns),b3)
            self.row_infos.append({'type':'new','spin':spin})

        self.table.blockSignals(False)
        self.updating = False

    def on_control(self, spin, sub, dd):
        a,b = self.spin_filters[spin];
        if sub is not None: a=sub
        if dd  is not None: b=dd
        self.spin_filters[spin] = (a,b)
        self.rebuild_table()

    def on_item_changed(self, item):
        if self.updating: return
        info = self.row_infos[item.row()]
        if info['type']!='data': return
        col = item.column()
        if 2 <= col < 2+len(self.extra_columns):
            field = self.extra_columns[col-2]; idx = info['df_idx']; txt = item.text().strip()
            self.df.at[idx,field] = NA if txt=='' else type(self.df.at[idx,field])(txt)
            self.save_to_hdf()

    def copy_row(self, row):
        def get_text(col):
            w = self.table.cellWidget(row,col)
            if isinstance(w,QtWidgets.QLineEdit): return w.text().strip()
            if isinstance(w,QtWidgets.QComboBox): return w.currentText()
            it = self.table.item(row,col)
            return it.text().strip() if it else ''
        sub,dd = get_text(0),get_text(1)
        lines = [f'subspace:{sub}',f'dd_method:{dd}']
        for i,col in enumerate(self.extra_columns):
            txt = self.table.item(row,2+i).text().strip() if self.table.item(row,2+i) else ''
            lines.append(f'{col}:{txt}')
        txt = '\n'.join(lines)
        cb = QtWidgets.QApplication.clipboard(); cb.setText(txt)
        QtWidgets.QMessageBox.information(self,'Copied',txt)

    def add_new(self, row, spin):
        sub = self.table.cellWidget(row,0).text().strip()
        dd  = self.table.cellWidget(row,1).text().strip()
        if not sub or not dd:
            QtWidgets.QMessageBox.warning(self,'Missing','Enter both Subspace & dd_method')
            return
        rec = {'spin name':spin,'subspace':sub,'dd_method':dd}
        for i,col in enumerate(self.extra_columns):
            txt = self.table.item(row,2+i).text().strip() if self.table.item(row,2+i) else ''
            rec[col] = NA if txt=='' else type(self.df[col].iloc[0])(txt)
        self.df = pd.concat([self.df,pd.DataFrame([rec])],ignore_index=True)
        self.save_to_hdf()
        # refresh choices
        subs = sorted(self.df['subspace'].dropna().unique().tolist())
        dds  = sorted(self.df['dd_method'].dropna().unique().tolist())
        self.subspace_choices = ['_none_']+subs
        self.dd_method_choices = ['_none_']+dds
        cur_s,cur_d = self.global_sub.currentText(),self.global_dd.currentText()
        self.global_sub.blockSignals(True); self.global_sub.clear(); self.global_sub.addItems(self.subspace_choices)
        if cur_s in self.subspace_choices: self.global_sub.setCurrentText(cur_s)
        self.global_sub.blockSignals(False)
        self.global_dd.blockSignals(True); self.global_dd.clear(); self.global_dd.addItems(self.dd_method_choices)
        if cur_d in self.dd_method_choices: self.global_dd.setCurrentText(cur_d)
        self.global_dd.blockSignals(False)
        self.rebuild_table()

    def get_spin(self, spin_name, subspace, dd_method):
        df2 = self.df[self.df['spin name']==spin_name]
        if subspace!='_none_': df2 = df2[df2['subspace']==subspace]
        if dd_method!='_none_': df2 = df2[df2['dd_method']==dd_method]
        return df2

    def apply_global_settings(self):
        gsub,gdd = self.global_sub.currentText(),self.global_dd.currentText()
        for s in self.unique_spins: self.spin_filters[s]=(gsub,gdd)
        self.rebuild_table()


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
        self._mw = window()
        #self.show()

    def on_activate(self):
        
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


        target_tab = self._mw.tabWidget.widget(1)
        self.register_table=DataFrameTableWidget(self._transition_tracker.Register.df)
        # Set a layout for the tab if it doesn't already have one
        if not target_tab.layout():
            layout = QtWidgets.QVBoxLayout(target_tab)
            target_tab.setLayout(layout)
        else:
            layout = target_tab.layout()

        layout.addWidget(self.register_table)

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
        self.register_table.save_backup_hdf()
        self._mw.close()
        #TODO - clean the memory

    def update_gui_electron(self):
        self._mw.current_local_oscillator_freq_text_field.setText("{:.3f}".format(self._transition_tracker.current_local_oscillator_freq))
        self._mw.mw_mixing_frequency_L_text_field.setText("{:.3f}".format(self._transition_tracker.mw_mixing_frequency_L))
        self._mw.mw_mixing_frequency_C_text_field.setText("{:.3f}".format(self._transition_tracker.mw_mixing_frequency_C))
        self._mw.mw_mixing_frequency_R_text_field.setText("{:.3f}".format(self._transition_tracker.mw_mixing_frequency_R))
        self._mw.zero_field_splitting_text_field.setText("{:.2f}".format(self._transition_tracker.zero_field_splitting))
        self._mw.Bfield_text_field.setText("{:.9f}".format(self._transition_tracker.current_magnetic_field_vector[0]))
        #self._mw.mw_transition_frequency_p1_text_field.setText("{:.10f}".format(self._transition_tracker.mw_transition_frequency_C))
        self._mw.off_axis_B_field_text_field.setText("{:.9f}".format(self._transition_tracker.current_magnetic_field_vector[1]))
        self._mw.ple_A2_text_field.setText("{:.9f}".format(self._transition_tracker.ple_A2))
        self._mw.ple_A1_text_field.setText("{:.9f}".format(self._transition_tracker.ple_A1))
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


#from logic.qudip_enhanced.qutip_enhanced.qtgui.custom_widgets import QTableWidgetEnhancedDrop
