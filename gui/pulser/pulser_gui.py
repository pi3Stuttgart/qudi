import numpy as np
import os
import pyqtgraph as pg

from collections import OrderedDict
from core.connector import Connector
from gui.colordefs import ColorScaleInferno
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

class PulserMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'pulser.ui')

        # Load it
        super(PulserMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class PulserGui(GUIBase):
    # declare connectors
    pulse_sequence_files = os.listdir('pulse_sequences')
    simple_pulser_logic = Connector(interface='PulserSimpleLogic')    
    def on_activate(self):
        self._pulser_logic = self.simple_pulser_logic()
        self._is_running_from_file = False 
        self._run_continuous = False
        self.channel = ['A', 1]
        self.channelTrig = ['A', 2]
        self._mw = PulserMainWindow()
        self.set_up_ui()

    def set_up_ui(self):
        self._mw.checkBox_run.clicked.connect(self.run_pulser)
        self._mw.comboBox_load.currentIndexChanged.connect(self.update_sequences_list)
        #! TODO rewrite with 3.9 python -> using := assignment
        self._mw.pushButton_load.clicked.connect(self.load_sequence_from_file)
        self._mw.checkBox_from_file.clicked.connect(lambda x: [None for self._is_running_from_file in [not self._is_running_from_file]])
        self._mw.checkBox_continuous.clicked.connect(lambda x: [None for self._run_continuous in [not self._run_continuous]])
        self._mw.pushButton_write.clicked.connect(self.write_sequence)
        self._mw.comboBox_channel.currentIndexChanged.connect(self.change_channel)
        self.filename = 'ramsey.csv'
        self.pulse_len = int(self._mw.doubleSpinBox_pulselen.value())
        self.pulse_sep = int(self._mw.doubleSpinBox_pulsesep.value())

        
        for channel in self._pulser_logic.channels[::-1]:
            print(channel)
            self._mw.comboBox_channel.insertItem(0, str(channel))
            self._mw.comboBox_channel.setCurrentIndex(0)
        self.change_channel()

        for name in self.pulse_sequence_files:  
            self._mw.comboBox_load.insertItem(0, name)
            self._mw.comboBox_load.setCurrentIndex(0)

    def change_channel(self):
        channel_idx = self._mw.comboBox_channel.currentIndex()
        self._pulser_logic.update_channel(channel_idx)

    def run_pulser(self):
        if self._mw.checkBox_run.isChecked():
            self._pulser_logic.start_pulser()
        else:
            self._pulser_logic.stop_pulser()

    def update_sequences_list(self):
        self.filename = self._mw.comboBox_load.currentText()
        print('load', self.filename)

    def write_sequence(self):
        if self._is_running_from_file:
            seq_file = self._mw.comboBox_load.currentText()
            self._pulser_logic.run_from_file(seq_file)
        elif self._run_continuous:
            self._pulser_logic.run_continuous()
        else:
            self.pulse_len = int(self._mw.doubleSpinBox_pulselen.value())
            self.pulse_sep = int(self._mw.doubleSpinBox_pulsesep.value())
            self._pulser_logic.run_pulsed(self.pulse_len, self.pulse_sep)

    def load_sequence_from_file(self):
        os.chdir('pulse_sequences')
        file_dialog = QtWidgets.QFileDialog(self._mw)
        name = file_dialog.getOpenFileName(self._mw, 'Open File')
        print(name)
        
        if os.path.basename(name[0])[:-4] in [self._mw.comboBox_load.itemText(j) for j in range(self._mw.comboBox_load.count())]:
            print('Name already exists!!!')
            return
        if 'seq.csv' in name[0]:
            self.filename = name[0]
            name_txt = os.path.basename(name[0])
            self._mw.comboBox_load.insertItem(0, name_txt)
            self._mw.comboBox_load.setCurrentIndex(0)
        else:
            print('wrong file?')
        file_dialog.close()
        os.chdir('..')
        return self.filename

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0
