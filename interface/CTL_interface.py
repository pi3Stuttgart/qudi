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


class CTLInterface(metaclass=InterfaceMetaclass):
    def on_activate(self):
        pass
    
    def on_deactivate(self):
        pass

    def wavelength(self,val):
        pass

    def current(self,val):
        pass

    @property
    def wavelength_act(self):
        pass

    @property
    def wavelength_setpoint(self) -> float:
        pass

    @wavelength_setpoint.setter
    def wavelength_setpoint(self, val):
        pass

    @property
    def current_act(self):
        pass

    @property
    def current_setpoint(self) -> float:
        pass

    @current_setpoint.setter
    def current_setpoint(self, val):
        pass

    @property
    def emission(self) -> bool:
        pass

    @property
    def emission_button(self) -> bool:
        pass

    @property
    def current_enabled(self) -> bool:
        pass

    @current_enabled.setter
    def current_enabled(self, val):
        pass

    def get_limits_from_dlc(self, verbose) -> dict:
        pass

    @property
    def _vrange(self):
        pass

    @property
    def _crange(self):
        pass

    @property
    def _trange(self):
        pass

    @property
    def _wlrange(self):
        pass

    def _check_value(val, parameter_name, permitted_range):
        pass

    def ON(self):
        pass

    def OFF(self):
        pass