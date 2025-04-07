import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableView, QPushButton, 
    QVBoxLayout, QWidget, QInputDialog
)
import numpy as np
from PyQt5.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel, QModelIndex
import numpy as np

from core.connector import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy import uic


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return self._data.shape[0]

    def columnCount(self, parent=QModelIndex()):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role in (Qt.DisplayRole, Qt.EditRole):
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            elif orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """Update DataFrame when a cell is edited. If editing a value (except state), update all rows with the same name."""
        if role == Qt.EditRole:
            col_name = self._data.columns[index.column()]
            row = index.row()

            if col_name != "name" and col_name != "state":
                name = self._data.at[row, "name"]

                # Find rows with the same name
                rows_to_update = self._data[self._data["name"] == name].index.tolist()

                if len(rows_to_update) > 1:  
                    # Only block signals when multiple rows exist to avoid infinite loops
                    self.blockSignals(True)

                # Update all rows with the name
                self._data.loc[self._data["name"] == name, col_name] = value

                if len(rows_to_update) > 1:
                    self.blockSignals(False)  # Unblock signals only if we blocked them before

                self.layoutChanged.emit()  # Refresh table view
            else:
                self._data.iloc[row, index.column()] = value

            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        return False

    def flags(self, index):
        """Make all cells editable"""
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def insertRow(self, row_data):
        """Inserts a new row at the end of the DataFrame"""
        row_position = self.rowCount()
        self.beginInsertRows(QModelIndex(), row_position, row_position)
        
        new_row = pd.DataFrame([row_data], columns=self._data.columns)
        self._data = pd.concat([self._data, new_row], ignore_index=True)
        
        self.endInsertRows()
        self.layoutChanged.emit()  # Refresh the table view

class RegisterTrackerWindow(QMainWindow):
    def __init__(self, df):
        super().__init__()
        self.setWindowTitle("Nuclear Register")
        self.resize(900, 600)

        self.model = PandasModel(df)
        print(self.model._data.name)

        # Sorting Proxy Model
        self.sort_proxy_model = QSortFilterProxyModel()
        self.sort_proxy_model.setSourceModel(self.model)
        self.sort_proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        self.table = QTableView()
        self.table.setModel(self.sort_proxy_model)
        self.table.setSortingEnabled(True)

        # Add Button
        self.add_button = QPushButton("Add Row")
        self.add_button.clicked.connect(self.add_row)
        # Add Button
        self.save_button = QPushButton("Save Register")
        self.save_button.clicked.connect(self.save)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.add_button)
        layout.addWidget(self.save_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def add_row(self):
        """Prompts user name and state, then assigns dependent values for other columns"""

        # Step 1: Select name
        name, ok = QInputDialog.getText(self, "Enter Name", "Enter a name for the new row:")
        if not ok or not name.strip():  # Check if user canceled or entered an empty string
            return  # Cancel row addition if user cancels or enters nothing
        
        # Step 2: Select state (depends on name)
        state_options = list(["-1.5", "-0.5", "0.5", "1.5"])
        state, ok = QInputDialog.getItem(self, "Select state", f"Choose state for {name}:", state_options, editable=False)
        if not ok:
            return
        
        atom = 'C' if 'C' in name else 'Si'
        # check if name is already in df. if yes, take same azz and azx
        print(name)
        print(list(self.model._data.name))
        if name in list(self.model._data.name):
            print("Name is in list.")
            print("_____")
            print(state)
            print(list(self.model._data.loc[self.model._data.name==name].state))
            if state in list(self.model._data.loc[self.model._data.name==name].state):
                print("state is in list.")
                # check if same name and state already in self.model._data. then return error
                print("Entry with same name and state already exists.")
                return
            azz = self.model._data.loc[self.model._data.name==name].azz.iloc[0]
            azx = self.model._data.loc[self.model._data.name==name].azx.iloc[0]
        else:
            azz = np.nan
            azx = np.nan
        
        trans_freq = np.nan
        bath_detuning = np.nan
        rf_phase_offset = np.nan
        rf_amp_dd = np.nan
        pi = np.nan
        pi2 = np.nan
        
        # Insert new row with selected name and state, shared atom and hyperfine values and mapped values
        self.model.insertRow([name, atom, azz, azx, state, trans_freq, bath_detuning, rf_phase_offset, rf_amp_dd, pi, pi2])

    def save(self):
        self.model._data.to_hdf('register.hdf', key = 'df')

class RegisterTrackerGUI(GUIBase):
    ## declare connectors
    transition_tracker_logic = Connector(interface='TransitionTracker')
    
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._tt = self.transition_tracker_logic() 

        register  = pd.read_hdf('register.hdf', 'df')
        self._mw = RegisterTrackerWindow(register)
        self._mw.show()

    
        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        
    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        
        self._mw.close()
    
    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
    

    
