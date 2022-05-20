# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface for TimeTagger.

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
    
    @abstract_interface_method
    def on_activate(self):
        """
        self.setup_TT()
        """
        pass
    @abstract_interface_method    
    def on_deactivate(self):
        pass
    
    @abstract_interface_method
    def setup_TT(self):
        """
        try:
            self.tagger = createTimeTagger()
            # self.tagger.reset()
            print(f"Tagger initialization successful: {self.tagger.getSerial()}")
        except:
            self.log.error(f"\nCheck if the TimeTagger device is being used by another instance.")
            Exception(f"\nCheck if the TimeTagger device is being used by another instance.")

        for i in self._test_channels:
            print(f"RUNNING CHANNEL {i} WITH TEST SIGNAL!")
            self.tagger.setTestSignal(i, True)

        #Create combine channels:

        self._combined_channels = self.combiner(self._combiner["channels"])

        # # set specified in the params.yaml channels params
        # for channel, params in self._channels_params.items():
        #     channel = self.channel_codes[channel]
        #     if 'delay' in params.keys():
        #         self.delay_channel(delay=params['delay'], channel = channel)
        #     if 'triggerLevel' in params.keys():
        #         self.tagger.setTriggerLevel(channel, params['triggerLevel'])
        """
        pass

    @abstract_interface_method
    def histogram(self, **kwargs):  
        """
        The histogram takes default values from the params.yaml

        Besides, it is possible to set values:
        Example:
        channel=1, trigger_channel=5, bins_width=1000, numer_of_bins= 1000

        get data by hist.getData()
        
        for key, value in kwargs.items():
            if key in self._hist.keys():
                self._hist.update({key:int(value)})
        return Histogram(self.tagger,
                            self._hist['channel'],
                            self._hist['trigger_channel'],
                            self._hist['bins_width'],
                            self._hist['number_of_bins'])
        """
        pass

    @abstract_interface_method
    def correlation(self, **kwargs):  
        """
        The correlation takes default values from the params.yaml

        Besides, it is possible to set values:
        Example:
        channel_start=1, channel_stop=2, bins_width=1000, numer_of_bins= 1000

        get data by corr.getData()
        
        for key, value in kwargs.items():
            if key in self._corr.keys():
                self._corr.update({key:value})
        return Correlation(self.tagger,
                            self._corr['channel_start'],
                            self._corr['channel_stop'],
                            self._corr['bins_width'],
                            self._corr['number_of_bins'])
        """
        pass

    @abstract_interface_method
    def delay_channel(self, channel, delay):
        """
        self.tagger.setInputDelay(delay=delay, channel=channel)
        """
        pass

    @abstract_interface_method
    def dump(self, dumpPath, filtered_channels=None): 
        """
        if filtered_channels != None:
            self.tagger.setConditionalFilter(filtered=[filtered_channels], trigger=self.apdChans)
        return Dump(self.tagger, dumpPath, self.maxDumps,\
                                    self.allChans)
        """
        pass

    @abstract_interface_method
    def countrate(self, channels=None):
        """
        The countrate takes default values from the params.yaml
        get data by ctrate.getData()
        if channels == None:
            channels = self._counter['channels']
        
        return Countrate(self.tagger,
                                channels)
        """
        pass

    @abstract_interface_method
    def counter(self, **kwargs):
        """
        refresh_rate - number of samples per second:

        for key, value in kwargs.items():
            if key in self._counter.keys():
                self._counter.update({key:value})
            if key == 'refresh_rate' and value != None:
                self._counter['bins_width'] = int(1e12/value)
        return Counter(self.tagger,
                                self._counter['channels'],
                                self._counter['bins_width'],
                                self._counter['n_values'])
        """
        pass

    @abstract_interface_method
    def time_differences(click_channel, start_channel, next_channel, binwidth, n_bins,n_histograms):
        """
        return TimeDifferences(self.tagger, 
                                click_channel, 
                                start_channel, 
                                next_channel,
                                binwidth, 
                                n_bins,
                                n_histograms)
        """
        pass

    @abstract_interface_method
    def combiner(self, channels):
        """
        return Combiner(self.tagger, channels)
        """
        pass

    @abstract_interface_method
    def count_between_markers(self, click_channel, begin_channel, end_channel, n_values):
        """
        return CountBetweenMarkers(self.tagger,
                                click_channel,
                                begin_channel,
                                end_channel,
                                n_values)     
        """
        pass

    @abstract_interface_method
    def time_differences(self, click_channel, start_channel, next_channel, binwidth,n_bins, n_histograms):
        """
        return TimeDifferences(self.tagger, 
                            click_channel=click_channel,
                            start_channel=start_channel,
                            next_channel=next_channel,
                            binwidth=binwidth,
                            n_bins=n_bins,
                            n_histograms=n_histograms)
        """
        pass
    @abstract_interface_method
    def write_into_file(self, filename, channels):
        """
        return FileWriter(self.tagger,
        filename, channels)
        """
        pass