import numpy as np
from datetime import datetime
import time

from core.configoption import ConfigOption
from core.module import Base

import hardware.laser.Hubner.cwave as cwave

from typing import Union, Tuple, List, Any
from PyQt5 import QtTest

from interface.cwave_interface import CWaveInterface



class HubnerCWave(Base,CWaveInterface):#, Interface): #?
   
    ''' Config Example
    HubnerCWave:
            module.Class: 'laser.Hubner.cwave_laser'
            IP: '129.69.46.217'
    '''
    IP = ConfigOption('IP', "129.69.46.217", missing='warn') 

    def on_activate(self):
        self._cwave = cwave.CWave()
        self._cwave.connect(self.IP)

    def on_deactivate(self):
        self._cwave.disconnect()

    def set_wavelength(self,wavelength,request_shg=True):
        '''Sets a new wavelength (OPO) to dial'''
        self._cwave.dial(wavelength, request_shg)

    def get_wavelength_set(self):
        '''Gets whether the dial operation is complete'''
        return self._cwave.get_dial_done()

    def set_pump_laser(self,enable):
        '''Sets enabled state of internal pump laser'''
        self._cwave.set_laser(enable)

    def get_pump_laser(self):
        '''Gets enabled state of internal pump laser'''
        return self._cwave.get_laser()

    def get_shutter(self, shutter):
        '''Gets whether current state of a shutter is open or closed'''
        return self._cwave.get_shutter(shutter)

    def set_shutter(self, shutter, open_shutter: bool):
        '''Sets a shutter open or closed'''
        self._cwave.set_shutter(shutter, open_shutter)

    # def get_mode(self):
    #     self.mode = self._cobolt.get_mode()
    #     return self.mode

    # def get_state(self):
    #     self.state = self._cobolt.get_state()
    #     return self.state

    # def set_current(self,val):
    #     """Set constant laser current in mA"""
    #     self._cobolt.set_current(val)

    # def get_current(self):
    #     """Get constant laser current in mA"""
    #     self.current = self._cobolt.get_current()
    #     return self.current

    # def get_current_setpoint(self):
    #     """Get constant laser current setpoint in mA"""
    #     return self._cobolt.get_current_setpoint()

    # def set_power(self, power):
    #     """Set constant laser power in mW"""
    #     self._cobolt.set_power(power)

    # def get_power(self):
    #     """Get constant laser power in mW"""
    #     self.power = self._cobolt.get_power()
    #     return self.power

    # def get_power_setpoint(self):
    #     """Get constant laser power setpoint in mW"""
    #     return self._cobolt.get_power_setpoint()

    # # 06MLD specific:

    # def modulation_mode(self, power=None):
    #     """Enter modulation mode.

    #     Args:
    #         power: modulation power (mW)
    #     """
    #     return self._cobolt.modulation_mode(power)

    # def digital_modulation(self, enable):
    #     """Enable digital modulation mode by enable=1, turn off by enable=0"""
    #     return self._cobolt.digital_modulation(enable)

    # def analog_modulation(self, enable):
    #     """Enable analog modulation mode by enable=1, turn off by enable=0"""
    #     return self._cobolt.analog_modulation(enable)

    # def on_off_modulation(self, enable):
    #     """Enable On/Off modulation mode by enable=1, turn off by enable=0"""
    #     return self._cobolt.on_off_modulation(enable)

    # def get_modulation_state(self):
    #     """Get the laser modulation settings as [analog, digital]"""
    #     return self._cobolt.get_modulation_state()

    # def set_modulation_power(self, power):
    #     """Set the modulation power in mW"""
    #     return self._cobolt.set_modulation_power(power)

    # def get_modulation_power(self):
    #     """Get the modulation power setpoint in mW"""
    #     return self._cobolt.get_modulation_power()

    # # def set_analog_impedance(self, arg):
    # #     """Set the impedance of the analog modulation.

    # #     Args:
    # #         arg: 0 for HighZ, 1 for 50 Ohm.
    # #     """
    #     # return self._cobolt.set_analog_impedance(arg)

    # def get_analog_impedance(self):
    #     """Get the impedance of the analog modulation \n
    #     return: 0 for HighZ and 1 for 50 Ohm"""
    #     return self._cobolt.get_analog_impedance()
