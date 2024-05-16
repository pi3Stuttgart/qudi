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


class TopticaLaserControlInterface(metaclass=InterfaceMetaclass):
    def on_activate(self):
        pass
    
    def on_deactivate(self):
        pass
   
    def on(self):
        pass

    def off(self):
        pass
    def is_enabled(self):
        pass
    
    def set_power(self, p, ch=2):
        pass
    
    def get_power(self):
        pass

    def get_channel_power(self):
        pass
    
    def get_full_data(self):
        pass
    
    def get_full_info(self):
        pass
    
    def get_full_status(self):
        pass
    
    def get_settings(self):
        pass
    
    def reboot(self):
        pass