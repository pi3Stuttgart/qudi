# -*- coding: utf-8 -*-
"""
Interface for a spectrometer.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass



class CWaveInterface(metaclass=InterfaceMetaclass):

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def set_wavelength(self):
        pass

    def get_wavelength_set(self):
        pass

    def set_pump_laser(self,enable):
        pass

    def get_pump_laser(self):
        pass

    def get_shutter(self, shutter):
        pass

    def set_shutter(self, shutter, open_shutter: bool):
        pass

    # def get_power(self):
    #     pass

    # def get_power_setpoint(self):
    #     pass

    # def modulation_mode(self, power=None):
    #     pass

    # def digital_modulation(self, enable):
    #     pass

    # def analog_modulation(self, enable):
    #     pass

    # def on_off_modulation(self, enable):
    #     pass

    # def get_modulation_state(self):
    #     pass

    # def set_modulation_power(self, power):
    #     pass

    # def get_modulation_power(self):
    #     pass

    # # def set_analog_impedance(self, arg):
    # #     pass

    # def get_analog_impedance(self):
    #     pass

    # # logic:
    # def power(self):
    #     pass
    
    # def current(self):
    #     pass