import numpy as np
from datetime import datetime
import time

from core.configoption import ConfigOption
from core.module import Base

import nidaqmx
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx import constants

from PyQt5 import QtTest

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
        self.sampling_freq_in = 42  # in Hz
        self.buffer_in_size = 10
        self.bufsize_callback = self.buffer_in_size
        self.buffer_in_size_cfg = round(self.buffer_in_size * 1)  # clock configuration
        self.crop = 10  # number of seconds to drop at acquisition start before saving #What does this do?
        self.my_filename = 'test_3_opms'  # with full path if target folder different from current folder (do not leave trailing /)
        
        # Initialize data placeholders
        self.buffer_in = np.zeros((1, self.buffer_in_size))
        self.data = np.zeros((1, 1))  # will contain a first column with zeros but that's fine
        #self.start_acquisition()
        return

    def on_deactivate(self):
        try: #please look away :)
            self.task_in.is_task_done()
            self.shut_down_streaming()
        except:
            pass

       
    def start_acquisition(self):
        # Configure and setup the tasks
        self.task_in = nidaqmx.Task()
        self.cfg_read_task(self.task_in)
        self.stream_in = AnalogMultiChannelReader(self.task_in.in_stream)
        self.task_in.register_every_n_samples_acquired_into_buffer_event(self.bufsize_callback, self.reading_task_callback) 
        # Registers a callback function to receive an event when the specified number of samples is written from the device to the buffer.
        # But afaik it is not necessary for readout in general. One can just access self.buffer_in at all times. #https://nidaqmx-python.readthedocs.io/en/latest/task.html
        #self.reading_task_callback()
        self.task_in.start()

        self.task_out = nidaqmx.Task()
        self.cfg_write_task(self.task_out)
        self.task_out.start()

    def cfg_read_task(self, acquisition):
        acquisition.ai_channels.add_ai_voltage_chan(self.chan_in)
        acquisition.timing.cfg_samp_clk_timing(rate=self.sampling_freq_in, sample_mode=constants.AcquisitionType.CONTINUOUS,
                                            samps_per_chan=self.buffer_in_size_cfg)
        # print("Connected read task.")
    
    def cfg_write_task(self, voltage_out_task):
        self.numberOfUsedChannels = 0
        print("Channels:")
        print(self.chan_A2)
        print(self.chan_A1)
        if self.chan_A1 != 'None':
            print("1")
            voltage_out_task.ao_channels.add_ao_voltage_chan(self.chan_A1, min_val=self.voltagerange[0], max_val=self.voltagerange[-1])
            self.numberOfUsedChannels +=1
        if self.chan_A2 != 'None':
            print("1")
            voltage_out_task.ao_channels.add_ao_voltage_chan(self.chan_A2, min_val=self.voltagerange[0], max_val=self.voltagerange[-1])
            self.numberOfUsedChannels +=1      
        print("Connected write task.")

    def reading_task_callback(self, task_idx, event_type, num_samples, callback_data):
        #print("buffer in", self.buffer_in)
        #print("num samples", num_samples)
        self.stream_in.read_many_sample(self.buffer_in, num_samples, timeout=constants.WAIT_INFINITELY)

        return 0  # Absolutely needed for this callback to be well defined (see nidaqmx doc).
    
    def goToVoltage(self, V):
        if V > self.voltagerange[-1] or V < self.voltagerange[0]:
            print("Target voltage does not in voltage range.")
        else:
            print("Setting Outputvoltage to", V, "V.")
            self.task_out.write(V)
            QtTest.QTest.qSleep(10) # needed at all?
            self.current_voltage = V
    
    def MultiplegoToVoltage(self, V):
        if len(V) == self.numberOfUsedChannels and len(V) == 2: #check if there are two voltage input and two output channels are used.
            if V[0] > self.voltagerange[-1] or V[0] < self.voltagerange[0] or V[1] > self.voltagerange[-1] or V[1] < self.voltagerange[0]:
                print("Target voltage is not in voltage range.")
            else:
                print("Setting Outputvoltage to", V, "V.")
                self.task_out.write(V)
                QtTest.QTest.qSleep(1) # needed at all?
                self.current_voltage = V
        elif len(V) == self.numberOfUsedChannels and len(V) == 1: #check if there is only voltage input when only one output channel is used.
            if V[0] > self.voltagerange[-1] or V[0] < self.voltagerange[0]:
                print("Target voltage is not in voltage range.")
            else:
                print("Setting Outputvoltage to", V, "V.")
                self.task_out.write(V)
                QtTest.QTest.qSleep(1) # needed at all?
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