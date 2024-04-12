from core.connector import Connector
from logic.generic_logic import GenericLogic
from PyQt5 import QtCore
from PyQt5 import QtTest
import numpy as np
from core.statusvariable import StatusVar

from interface.CTL_interface import CTLInterface
from hardware.laser.Toptica.toptica_CTL_laser import TopticaCTL

class CTLLogic(GenericLogic,CTLInterface):
    
    ''' Config Example
    ctllogic:
            module.Class: 'CTLLogic.CTLLogic'
            connect:
                TopticaCTL: 'TopticaCTL'
    '''
    # Implement Config options for voltage_offset and voltage_to_power_ratio
    TopticaCTL = Connector(interface='TopticaCTL')

    def on_activate(self):
        self._CTL:TopticaCTL = self.TopticaCTL()
        self._CTL.dlc.open()

    def on_deactivate(self):
        self._CTL.on_deactivate()

    def wavelength(self,val: float=None):
        if val:
            print("Setting CTL wavelength to ", val,"nm.")
            self._CTL.wavelength_setpoint = val
        else:
            return self._CTL.wavelength_setpoint

    def current(self,val: float=None):
        if val:
            self._CTL.current_setpoint = val
        else:
            return self._CTL.current_setpoint

    def emission(self,val: bool=None):
        if val == True:
            self._CTL.current_enabled = val
        elif val == False:
            self._CTL.current_enabled = val
        else:
            return self._CTL.current_enabled

    def ON(self):
        self._CTL.current_enabled = True

    def OFF(self):
        self._CTL.current_enabled = False
