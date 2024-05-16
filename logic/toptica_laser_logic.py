"""author: Erik and Jonathan"""

import json
import os

import time
import datetime
from qtpy import QtCore
import numpy as np
from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from core.pi3_utils import delay
from PyQt5 import QtTest
import csv

class TopticaLaserLogic(GenericLogic):
    # declare connectors
    laser = Connector(interface='TopticaLaserControlInterface')
    
    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # self._awg = self.mcas_holder()
        self._laser = self.laser() 

    def on_deactivate(self):
        pass