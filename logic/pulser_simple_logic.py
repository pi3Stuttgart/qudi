# -*- coding: utf-8 -*
from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
from time import sleep
from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from PyQt5.QtCore import QObject
from core.threadmanager import ThreadManager
# from core.pi3_utils import delay, wavelength_to_freq
import numpy as np

class PulserSimpleLogic(GenericLogic):
    pulser = Connector(interface='DTG')
    sig_update_gui = QtCore.Signal()
    pulse_len = 0
    pulse_sep = 0
    block_length = 0
    filename = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

    def on_activate(self):
        self._pulser = self.pulser()
        self.channels = self._pulser.channels

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
         
    
    def run_pulsed(self, pulse_length, pulse_separation):
        seq, trig = self._pulser.compose_pulsed_sequence(pulse_length, pulse_separation)
        self._pulser.write_sequence(sequence=seq, trigger = trig)
         
    def run_from_file(self, file_name):
        seq, trig = self._pulser.get_from_file_seq(file_name)
        self._pulser.write_sequence(sequence=seq, trigger = trig)
    
    def run_continuous(self):
        seq, trig = self._pulser.compose_pulsed_sequence(100, 0)
        self._pulser.write_sequence(sequence=seq, trigger = trig)

    def start_pulser(self):
        self._pulser.run_dtg()
    def stop_pulser(self):
        self._pulser.stop_dtg()
    
    def update_channel(self, channel_idx):
        self._pulser.channel = self.channels[channel_idx]
        