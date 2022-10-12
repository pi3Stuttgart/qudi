# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware interface for fast counting devices.

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


class TimeTaggerInterface(metaclass=InterfaceMetaclass):
    """ Interface class to define the controls for fast counting devices.

    A "fast counter" is a hardware device that count events with a "good" time resolution.
    The goal is generally to detect when events happen after an time defining trigger. These events can be photons
    arrival on a detector for example, and the trigger the start of the acquisition.
    This type of hardware regularly records millions of repeated acquisition (ie sweeps) in a few seconds,
    with one or multiple events per trigger (depending on the hardware constrains).
    It can be used in two modes :
    - "Gated" : The result is a 2d array where each line correspond to a single trigger with one or multiple events
                in each line/box
    - "Ungated" : Only the sum of the acquisition is acquired, building an histogram of the events times. This is
                  generally enough for a lot of experiment, where a memory consuming 2d array is not necessary.

    """

    def setup_TT(self):
        pass

    def histogram(self, **kwargs):
        """
        The histogram takes default values from the params.yaml

        Besides, it is possible to set values:
        Example:
        channel=1, trigger_channel=5, bins_width=1000, numer_of_bins= 1000

        get data by hist.getData()
        """
        pass

    def correlation(self, **kwargs):
        """
        The correlation takes default values from the params.yaml

        Besides, it is possible to set values:
        Example:
        channel_start=1, channel_stop=2, bins_width=1000, numer_of_bins= 1000

        get data by corr.getData()
        """
        pass

    def delay_channel(self, channel, delay):
        pass

    def dump(self, dumpPath, filtered_channels=None):
        pass

    def countrate(self, channels=None):
        """
        The countrate takes default values from the params.yaml
        get data by ctrate.getData()
        """
        pass

    def counter(self, **kwargs):
        """
        refresh_rate - number of samples per second:

        """
        pass

    def combiner(self, channels):
        pass

    def count_between_markers(self, n_values, **kwargs):
        pass
    def time_differences(self,
                         **kwargs):  # , click_channel, start_channel, next_channel, binwidth,n_bins, n_histograms):
        pass

    def write_into_file(self, filename, channels):
        pass