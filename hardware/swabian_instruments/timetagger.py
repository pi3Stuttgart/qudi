
from os.path import join, getsize, isfile
import numpy as np
#from TimeTagger import createTimeTagger, Dump, Correlation, Histogram, Counter, CountBetweenMarkers, FileWriter, Countrate, Combiner, TimeDifferences
from TimeTagger import createTimeTagger, Dump, Correlation, Histogram, Counter, CountBetweenMarkers, Countrate, Combiner, TimeDifferences

from core.configoption import ConfigOption
from core.module import Base

from interface.test_interface import TimeTaggerInterface
#from interface.pulser_interface import PulserInterface

class TT(Base, TimeTaggerInterface):
    _hist = ConfigOption('hist', False, missing='warn')
    _time_diff = ConfigOption('time_diff', False, missing='warn')
    _corr = ConfigOption('corr', False, missing='warn')
    _combiner = ConfigOption('combiner', False, missing='warn')
    _counter = ConfigOption('counter', False, missing='warn')
    _test_channels = ConfigOption('test_channels', False, missing='warn')
    _channels_params = ConfigOption('channels_params', False, missing='warn')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sample_rate = 50
        chan_alphabet = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight']
        self.channel_codes = dict(zip(chan_alphabet, list(range(1,9,1))))

    def on_activate(self):
        self.setup_TT()
        self.tagger.setTriggerLevel(1,0.7)
        self.tagger.setTriggerLevel(2,0.7)

    def on_deactivate(self):
        pass

    def setup_TT(self):
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

    def histogram(self, **kwargs):  
        """
        The histogram takes default values from the params.yaml

        Besides, it is possible to set values:
        Example:
        channel=1, trigger_channel=5, bins_width=1000, numer_of_bins= 1000

        get data by hist.getData()
        """
        for key, value in kwargs.items():
            if key in self._hist.keys():
                self._hist.update({key:int(value)})
        # return Histogram(self.tagger,
        #                     self._hist['click_channel'],
        #                     self._hist['start_channel'],
        #                     self._hist['next_channel'],
        #                     self._hist['sync_channel'],
        #                     self._hist['binwidth'],
        #                     self._hist['n_bins'],
        #                     self._hist['n_histograms'])
        return Histogram(self.tagger,
                            1,
                            4,
                            -4,
                            7,
                            10000000,
                            123,
                            20)
    
    def correlation(self, **kwargs):  
        """
        The correlation takes default values from the params.yaml

        Besides, it is possible to set values:
        Example:
        channel_start=1, channel_stop=2, bins_width=1000, numer_of_bins= 1000

        get data by corr.getData()
        """
        for key, value in kwargs.items():
            if key in self._corr.keys():
                self._corr.update({key:value})
        return Correlation(self.tagger,
                            self._corr['channel_start'],
                            self._corr['channel_stop'],
                            self._corr['bins_width'],
                            self._corr['number_of_bins'])


    def delay_channel(self, channel, delay):
        self.tagger.setInputDelay(delay=delay, channel=channel)


    def dump(self, dumpPath, filtered_channels=None): 
        if filtered_channels != None:
            self.tagger.setConditionalFilter(filtered=[filtered_channels], trigger=self.apdChans)
        return Dump(self.tagger, dumpPath, self.maxDumps,\
                                    self.allChans)
        
    def countrate(self, channels=None):
        """
        The countrate takes default values from the params.yaml
        get data by ctrate.getData()
        """
        if channels == None:
            channels = self._counter['channels']
        
        return Countrate(self.tagger, channels)

    def counter(self, **kwargs):
        """
        refresh_rate - number of samples per second:

        """
        self.tagger.setTriggerLevel(1,0.5)
        self.tagger.setTriggerLevel(2,0.5)
        for key, value in kwargs.items():
            if key in self._counter.keys():
                self._counter.update({key:value})
            if key == 'refresh_rate' and value != None:
                self._counter['bins_width'] = int(1e12/value)
        return Counter(self.tagger,
                                self._counter['channels'],
                                self._counter['bins_width'],
                                self._counter['n_values'])

    def combiner(self, channels):
        return Combiner(self.tagger, channels)

    def count_between_markers(self, click_channel, begin_channel, end_channel, n_values):
        return CountBetweenMarkers(self.tagger,
                                click_channel,
                                begin_channel,
                                end_channel,
                                n_values)     

    def time_differences(self,**kwargs): #, click_channel, start_channel, next_channel, binwidth,n_bins, n_histograms):
        return TimeDifferences(self.tagger, 
                            click_channel=self._time_diff['click_channel'],
                            start_channel=self._time_diff['start_channel'],
                            next_channel=self._time_diff['next_channel'],
                            sync_channel=self._time_diff['sync_channel'],
                            binwidth=self._time_diff['binwidth'],
                            n_bins=self._time_diff['n_bins'],
                            n_histograms=self._time_diff['n_histograms']
                            )

    def write_into_file(self, filename, channels):
        return FileWriter(self.tagger,
        filename, channels)

    