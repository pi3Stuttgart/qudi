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


class TransitionTrackerInterface(metaclass=InterfaceMetaclass):
        def __init__(self,config, **kwargs):
                pass

        def on_activate(self):
                pass

        def on_deactivate(self):
                pass

        def connect_signals(self):
                pass
        #self.update_tt_nuclear_gui.connect(self.update_gui_nuclear)
        #self.update_tt_electron_gui.connect(self.update_gui_electron)

        def nuclear_transition_name(self, transition):
                pass

        def set_ntd(self):
                pass

        def reload_nuclear_parameters(self):
                pass

        def set_h_diag(self):
                pass

        def load_transitions(self):
                pass

        def update_current_frequencies(self):
                pass

        def load_rabi_parameters(self):
                pass

        def plot_rabi_parameters(self):
                pass


        def update_stuff(self):
                pass

        def transition(self, name):
                pass

        def change_transition_frequency(self, fd, current_magnetic_field=None, test_mode=False):
                pass

        def update_nuclear_parameter(self, typ, val, old_val, transition_list, nuc, filename, test_mode=False):
                pass

        # @staticmethod
        # def frequency_fid(assumed_frequency, frequency_offset, measured_period, max_diff_factor=.2):
        #         pass
    
        # @staticmethod
        # def correct_transition_name(name):
        #         pass

        def update_zero_field_splitting(self, freq):
                pass

        def get_rabi_parameter(self, name, **kwargs):
                pass

        def rp(self, name, **kwargs):
                pass


        def get_f(self, typ):
                pass

        def mfl(self, td, mw_mixing_frequency=None, ms_trans='-1'):
                pass