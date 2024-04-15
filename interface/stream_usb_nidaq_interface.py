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


class StreamUSBNidaqInterface(metaclass=InterfaceMetaclass):
    def on_activate(self):
        pass
    
    def on_deactivate(self):
        pass
   
    def start_acquisition(self):
        pass

    def start_ao_task(self):
        pass

    def cfg_read_task(self, acquisition):
       pass

    def cfg_write_task(self, voltage_out_task):
        pass

    def reading_task_callback(self, task_idx, event_type, num_samples, callback_data):  # bufsize_callback is passed to num_samples
        pass

    def goToVoltage(self, V):
        pass

    def shut_down_streaming(self):
        pass