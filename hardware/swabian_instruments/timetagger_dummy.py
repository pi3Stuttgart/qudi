
from os.path import join, getsize, isfile
import numpy as np
#from TimeTagger import createTimeTagger, Dump, Correlation, Histogram, Counter, CountBetweenMarkers, FileWriter, Countrate, Combiner, TimeDifferences
#from TimeTagger import createTimeTagger, Dump, Correlation, Histogram, Counter, CountBetweenMarkers, Countrate, Combiner, TimeDifferences
from core.configoption import ConfigOption
from core.module import Base

from interface.test_interface import TimeTaggerInterface
#from interface.pulser_interface import PulserInterface

class TT_dummy(Base, TimeTaggerInterface):
    #_hist = ConfigOption('hist', False, missing='warn')
    #_time_diff = ConfigOption('time_diff', False, missing='warn')
    #_corr = ConfigOption('corr', False, missing='warn')
    #_combiner = ConfigOption('combiner', False, missing='warn')
    #_counter = ConfigOption('counter', False, missing='warn')
    #_test_channels = ConfigOption('test_channels', False, missing='warn')
    #_channels_params = ConfigOption('channels_params', False, missing='warn')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sample_rate = 50
        chan_alphabet = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight']
        self.channel_codes = dict(zip(chan_alphabet, list(range(1, 9, 1))))

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

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

        pass

    def counter(self, **kwargs):
        """
        refresh_rate - number of samples per second:

        """
        pass

    def combiner(self, channels):
        pass

    def count_between_markers(self, click_channel, begin_channel, end_channel, n_values):
        pass

    def time_differences(self,
                         **kwargs):  # , click_channel, start_channel, next_channel, binwidth,n_bins, n_histograms):
        pass

    def write_into_file(self, filename, channels):
        pass

    def init_counter(self, counter_type, *args, **kwargs):
        """this one is from pi3diamond of Javid/Sebastian, etc..."""

        pass

    def create_stream(self, *args, **kwargs):
        pass

    def get_stream_data(self, *args, **kwargs):
        pass
