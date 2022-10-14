import numpy as np
from datetime import datetime
import time

from core.configoption import ConfigOption
from core.module import Base

import nidaqmx
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx import constants

from interface.stream_usb_nidaq_interface import StreamUSBNidaqInterface

class streamUSBnidaq(Base, StreamUSBNidaqInterface): #Hardware file
   
    ''' Config Example
    streamusbnidaq:
            module.Class: 'USBNidaq6211.streamUSBnidaq'
            chan_in: 'dev3/ai0'
            chan_A1: 'dev3/ao0'
            chan_A2: 'dev3/ao1'
    '''
    chan_in = ConfigOption('chan_in', False, missing='warn') #test if readout from config file works
    chan_A1 = ConfigOption('chan_A1', False, missing='warn') #test if readout from config file works
    chan_A2 = ConfigOption('chan_A2', False, missing='warn') #test if readout from config file works
    voltagerange = ConfigOption('voltagerange', False, missing='warn') #test if readout from config file works

    def on_activate(self):
        # Parameters
        print("Init USB Nidaq...")
        self.sampling_freq_in = 10  # in Hz
        self.buffer_in_size = 10
        self.bufsize_callback = self.buffer_in_size
        self.buffer_in_size_cfg = round(self.buffer_in_size * 1)  # clock configuration
        self.refresh_rate_plot = 10  # in Hz
        self.crop = 10  # number of seconds to drop at acquisition start before saving
        self.my_filename = 'test_3_opms'  # with full path if target folder different from current folder (do not leave trailing /)
        
        # Initialize data placeholders
        self.buffer_in = np.zeros((len(self.chan_in), self.buffer_in_size))
        self.data = np.zeros((len(self.chan_in), 1))  # will contain a first column with zeros but that's fine
        return

    def on_deactivate(self):
        self.shut_down_streaming()

    def start_acquisition(self):
        # Configure and setup the tasks
        self.task_in = nidaqmx.Task()
        self.cfg_read_task(self.task_in)
        self.stream_in = AnalogMultiChannelReader(self.task_in.in_stream)
        self.task_in.register_every_n_samples_acquired_into_buffer_event(self.bufsize_callback, self.reading_task_callback) 
        # Registers a callback function to receive an event when the specified number of samples is written from the device to the buffer.
        # But afaik it is not necessary for readout in general. One can just access self.buffer_in at all times. #https://nidaqmx-python.readthedocs.io/en/latest/task.html
        self.task_in.start()

        self.task_out = nidaqmx.Task()
        self.cfg_write_task(self.task_out)
        #self.task_out.start()

    def cfg_read_task(self, acquisition):
        acquisition.ai_channels.add_ai_voltage_chan(self.chan_in)
        acquisition.timing.cfg_samp_clk_timing(rate=self.sampling_freq_in, sample_mode=constants.AcquisitionType.CONTINUOUS,
                                            samps_per_chan=self.buffer_in_size_cfg)
        # print("Connected read task.")
    
    def cfg_write_task(self, voltage_out_task):
        self.numberOfUsedChannels = 0
        if self.chan_A1 is not None:
            voltage_out_task.ao_channels.add_ao_voltage_chan(self.chan_A1, min_val=self.voltagerange[0], max_val=self.voltagerange[-1])
            self.numberOfUsedChannels +=1
        if self.chan_A2 is not None:
            voltage_out_task.ao_channels.add_ao_voltage_chan(self.chan_A2, min_val=self.voltagerange[0], max_val=self.voltagerange[-1])
            self.numberOfUsedChannels +=1      
        print("Connected write task.")

    def reading_task_callback(self, task_idx, event_type, num_samples, callback_data):
        self.stream_in.read_many_sample(self.buffer_in, num_samples, timeout=constants.WAIT_INFINITELY)
        return 0  # Absolutely needed for this callback to be well defined (see nidaqmx doc).
    
    def goToVoltage(self, V):
        if V > self.voltagerange[-1] or V < self.voltagerange[0]:
            print("Target voltage does not in voltage range.")
        else:
            print("Setting Outputvoltage to", V, "V.")
            self.task_out.write(V)
            time.sleep(0.001) #UNFUG
            self.current_voltage = V
    
    def MultiplegoToVoltage(self, V):
        if len(V) == self.numberOfUsedChannels and len(V) == 2: #check if there are two voltage input and two output channels are used.
            if V[0] > self.voltagerange[-1] or V[0] < self.voltagerange[0] or V[1] > self.voltagerange[-1] or V[1] < self.voltagerange[0]:
                print("Target voltage is not in voltage range.")
            else:
                print("Setting Outputvoltage to", V, "V.")
                self.task_out.write(V)
                time.sleep(0.001) #UNFUG
                self.current_voltage = V
        elif len(V) == self.numberOfUsedChannels and len(V) == 1: #check if there is only voltage input when only one output channel is used.
            if V[0] > self.voltagerange[-1] or V[0] < self.voltagerange[0]:
                print("Target voltage is not in voltage range.")
            else:
                print("Setting Outputvoltage to", V, "V.")
                self.task_out.write(V)
                time.sleep(0.001) #UNFUG
                self.current_voltage = V
        
        elif len(V) != self.numberOfUsedChannels:
            print("Need ",self.numberOfUsedChannels, " input arguments for output voltage. -USBNidaq6211")
        
        else:
            print("Invalid voltages passed to USBNidaq6211")

    def shut_down_streaming(self):
        # Close task to clear connection
        # self.goToVoltage(0)
        self.task_in.close()
        self.task_out.close()