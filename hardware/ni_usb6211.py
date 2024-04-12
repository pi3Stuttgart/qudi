import numpy as np
import nidaqmx
from nidaqmx import constants
from nidaqmx import stream_readers
from nidaqmx import stream_writers

import matplotlib.pyplot as plt

from nidaqmx import Task
from nidaqmx.constants import TerminalConfiguration
from core.module import Base
from core.connector import Connector
from traits.api import Float
import time
from enum import Enum

from interface.laser_power_interface import LaserPowerInterface

class NI_USB6211(Base, LaserPowerInterface):
    def on_activate(self):
        try:
            self.aom_driver = AOM_Driver(AOChannel='dev3/ao0', Voltagerange=[-10., -2.])
            print('aom driver connected')
        except:
            print('no aom driver connected')
            self.aom_driver = None

        try:
            self.photodiode = Photodiode(
                AIChannel="dev2/ai0", volt_to_power=0.0717, volt_offset=-0.0096, sample_freq=1000, time_acquire=1
            )
            print('photodiode connected')
        except:
            print('no photodiode connected')
            self.photodiode = None
        return

    def on_deactivate(self):
        del self.aom_driver
        del self.photodiode
        return


class AOM_Driver:
    # Class to control an AO of a nidaQ to control an AOM driver

    def __init__(
            self,
            AOChannel,
            Voltagerange
    ):
        self.voltage = 0
        self.voltagerange = Voltagerange
        self.AOChannel = AOChannel
        self.task = Task()
        self.ao_channel = self.task.ao_channels.add_ao_voltage_chan(
            AOChannel, min_val=Voltagerange[0], max_val=Voltagerange[-1]
        )
        self.Voltagerange = Voltagerange

    def goToVoltage(self, V):
        if V > self.Voltagerange[-1] or V < self.Voltagerange[0]:
            pass
        else:
            self.task.write(V)
            time.sleep(0.001)
            self.voltage = V

    def getVoltage(self):
        self.voltage

    def __del__(self):
        self.task.close()

class Photodiode():
    voltage_to_power = Float(
        default_value=0.0717,  # for 0-1000nW     ;   6.63e-3 for 0-50nW
        low=0.,
        hight=100.,
        desc='Qum efficiency [V/nW]',
        label='Qum efficiency [V/nW]'
    )

    voltage_offset = Float(
        default_value=-0.0096,  # for 0-1000nW     ;   .015 for 0-50nW ,
        low=0.,
        hight=10,
        desc='Voltage Offset [mV]',
        label='Voltage Offset [mV]'
    )

    def __init__(self, AIChannel, volt_to_power, volt_offset, sample_freq, time_acquire):
        self.AIChannel = AIChannel
        self.voltage_to_power = volt_to_power  # mV/nW
        self.voltage_offset = volt_offset  # V
        self.sample_freq = sample_freq
        self.time_acquire = time_acquire
        self.num_channels = 1
   
        print("started")
        self.task = Task()
        self.ai_channel = self.task.ai_channels.add_ai_voltage_chan(
            self.AIChannel,
            terminal_config=TerminalConfiguration.RSE,
            min_val=-10,
            max_val=10,
            #current_excit_val=0.002
        )

    #     self.task.timing.cfg_samp_clk_timing(
    #         rate=self.time_acquire,
    #         sample_mode=constants.AcquisitionType.CONTINUOUS,
    #         samps_per_chan=(self.sample_freq * self.time_acquire),
    #     ) # you may not need samps_per_chan

    #     # I set an input_buf_size
    #     self.samples_per_buffer = int(self.sample_freq // 30)  # 30 hz update
    #     # task.in_stream.input_buf_size = samples_per_buffer * 10  # plus some extra space

    #     self.reader = stream_readers.AnalogMultiChannelReader(self.task.in_stream)
    #     self.writer = stream_writers.AnalogMultiChannelWriter(self.task.out_stream)
        
    # def readingTaskCallback(self, task_idx = 1, event_type = 'ACQUIRED_INTO_BUFFER', num_samples = 100, callback_data=None):
    #     print("readingAAAAAAAAAAAAAAAAAAAAAA")
    #     """After data has been read into the NI buffer this callback is called to read in the data from the buffer.

    #     This callback is for working with the task callback register_every_n_samples_acquired_into_buffer_event.

    #     Args:
    #         task_idx (int): Task handle index value
    #         event_type (nidaqmx.constants.EveryNSamplesEventType): ACQUIRED_INTO_BUFFER
    #         num_samples (int): Number of samples that was read into the buffer.
    #         callback_data (object)[None]: No idea. Documentation says: The callback_data parameter contains the value
    #             you passed in the callback_data parameter of this function.
    #     """
    #     buffer = np.zeros((self.num_channels, num_samples), dtype=np.float64)
    #     self.reader.read_many_sample(buffer, num_samples, timeout=20) #timeout=constants.WAIT_INFINITELY)

    #     # Convert the data from channel as a row order to channel as a column
    #     data = buffer.T.astype(np.float32)
    #     print(data)
    #     # Do something with the data
    #     print("task")
    #     self.task.register_every_n_samples_acquired_into_buffer_event(self.samples_per_buffer, self.readingTaskCallback)

    def getMeanVoltage(self, N):
        return np.array(self.task.read(N)).mean()

    def getMeanPower(self, N):
        return (
                       self.getMeanVoltage(N) - self.voltage_offset
               ) / self.voltage_to_power

    def redo_offset(self, N):
        voltage = self.getMeanVoltage(N)
        self.voltage_offset = voltage

    def Changevoltage_to_power(self, R):
        self.voltage_to_power = R

    def __del__(self):
        self.task.close()

class TerminalConfiguration(Enum):
    DEFAULT = -1  #: Default.
    RSE = 10083  #: Referenced Single-Ended.
    NRSE = 10078  #: Non-Referenced Single-Ended.
    DIFFERENTIAL = 10106  #: Differential.
    PSEUDODIFFERENTIAL = 12529  #: Pseudodifferential.

# photokruscht = Photodiode(AIChannel="dev3/ai5",
#     volt_to_power=0.0717,
#     volt_offset=-0.0096,
#     sample_freq=10000,
#     time_acquire=1
#     )
# photokruscht.readingTaskCallback(task_idx=1, event_type='ACQUIRED_INTO_BUFFER', num_samples= 100, callback_data=None)
# time.sleep(10)
# print("done")