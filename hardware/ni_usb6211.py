import numpy as np
from nidaqmx import Task
from nidaqmx.constants import TerminalConfiguration
from core.module import Base
from core.connector import Connector
from traits.api import Float
import time
from enum import Enum

class NI_USB6211(Base):
    def on_activate(self):
        try:
            self.aom_driver = AOM_Driver(AOChannel='dev3/ao0', Voltagerange=[-10., 10.])
            print('aom driver connected')
        except:
            print('no aom driver connected')
            self.aom_driver = None
        
        try:
            self.photodiode = Photodiode(
                AIChannel="dev3/ai5", volt_to_power=0.0547, volt_offset=-0.0174
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
    #Class to control an AO of a nidaQ to control an AOM driver

    def __init__(
        self,
        AOChannel,
        Voltagerange,
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
        default_value=6.7485e-3,  #for 0-1000nW     ;   6.63e-3 for 0-50nW
        low=0.,
        hight=100.,
        desc='Qum efficiency [V/nW]',
        label='Qum efficiency [V/nW]'
    )

    voltage_offset = Float(
        default_value=.01651,  #for 0-1000nW     ;   .015 for 0-50nW , 
        low=0.,
        hight=10,
        desc='Voltage Offset [mV]',
        label='Voltage Offset [mV]'
    )

    def __init__(self, AIChannel, volt_to_power, volt_offset):
        self.AIChannel = AIChannel
        self.task = Task()
        self.ai_channel = self.task.ai_channels.add_ai_voltage_chan(
            AIChannel,
            terminal_config=TerminalConfiguration.RSE,
            min_val=-10,
            max_val=10
        )
        self.voltage_to_power = volt_to_power  #mV/nW
        self.voltage_offset = volt_offset  #V

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