import numpy as np
from datetime import datetime
import time

from core.configoption import ConfigOption
from core.module import Base

from pycobolt import Cobolt06MLD

from typing import Union, Tuple, List, Any
from PyQt5 import QtTest

from interface.cobolt_interface import CoboltInterface



class HubnerCobolt(Base,CoboltInterface):#, Interface): #?
   
    ''' Config Example
    HubnerCobolt:
            module.Class: 'laser.cobolt_laser'
            COM_Port: 'COM4'
    '''
    COM_Port = ConfigOption('COM', "COM4", missing='warn') 
    serialnumber = ConfigOption('SN', 23393, missing='nothing') 

    def on_activate(self):
        self._cobolt = Cobolt06MLD(port=self.COM_Port)
        if self._cobolt.is_connected():
            # print(self._cobolt.__class__," connected")
            self._cobolt.turn_on()
        # self.connection = dlcsdk.NetworkConnection(self.IP)
        # self.dlc = dlcsdk.DLCpro(self.connection)
        # self.dlc.open()
        # self.wl_control_available = True
        # self.temp_control_available = False
        # self._lims = None
        # self.get_limits_from_dlc()

    def on_deactivate(self):
        self._cobolt.turn_off()

    def get_mode(self):
        self.mode = self._cobolt.get_mode()
        return self.mode

    def get_state(self):
        self.state = self._cobolt.get_state()
        return self.state

    def set_current(self,val):
        """Set constant laser current in mA"""
        self._cobolt.set_current(val)

    def get_current(self):
        """Get constant laser current in mA"""
        self.current = self._cobolt.get_current()
        return self.current

    def get_current_setpoint(self):
        """Get constant laser current setpoint in mA"""
        return self._cobolt.get_current_setpoint()

    def set_power(self, power):
        """Set constant laser power in mW"""
        self._cobolt.set_power(power)

    def get_power(self):
        """Get constant laser power in mW"""
        self.power = self._cobolt.get_power()
        return self.power

    def get_power_setpoint(self):
        """Get constant laser power setpoint in mW"""
        return self._cobolt.get_power_setpoint()

    # 06MLD specific:

    def modulation_mode(self, power=None):
        """Enter modulation mode.

        Args:
            power: modulation power (mW)
        """
        return self._cobolt.modulation_mode(power)

    def digital_modulation(self, enable):
        """Enable digital modulation mode by enable=1, turn off by enable=0"""
        return self._cobolt.digital_modulation(enable)

    def analog_modulation(self, enable):
        """Enable analog modulation mode by enable=1, turn off by enable=0"""
        return self._cobolt.analog_modulation(enable)

    def on_off_modulation(self, enable):
        """Enable On/Off modulation mode by enable=1, turn off by enable=0"""
        return self._cobolt.on_off_modulation(enable)

    def get_modulation_state(self):
        """Get the laser modulation settings as [analog, digital]"""
        return self._cobolt.get_modulation_state()

    def set_modulation_power(self, power):
        """Set the modulation power in mW"""
        return self._cobolt.set_modulation_power(power)

    def get_modulation_power(self):
        """Get the modulation power setpoint in mW"""
        return self._cobolt.get_modulation_power()

    # def set_analog_impedance(self, arg):
    #     """Set the impedance of the analog modulation.

    #     Args:
    #         arg: 0 for HighZ, 1 for 50 Ohm.
    #     """
        # return self._cobolt.set_analog_impedance(arg)

    def get_analog_impedance(self):
        """Get the impedance of the analog modulation \n
        return: 0 for HighZ and 1 for 50 Ohm"""
        return self._cobolt.get_analog_impedance()
