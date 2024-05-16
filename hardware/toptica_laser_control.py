import numpy as np
from datetime import datetime
import time

from core.configoption import ConfigOption
from core.module import Base

from PyQt5 import QtTest

from pylablib.devices import Toptica

from interface.toptica_laser_control_interface import TopticaLaserControlInterface

class TopticaLaserControl(Base, TopticaLaserControlInterface): #Hardware file
   
    ''' Config Example
    streamusbnidaq:
            module.Class: 'USBNidaq6211.streamUSBnidaq'
            chan_in: 'dev3/ai0'
            chan_A1: 'dev3/ao0'
            chan_A2: 'dev3/ao1'
    '''
    laser_com_port = ConfigOption('laser_com_port', 'COM1', missing='warn') #test if readout from config file works
    
    def on_activate(self):
        # Parameters
        print("Connect to toptica lasers...")
        
        self.iBeamSmart = Toptica.TopticaIBeam((self.laser_com_port, 115200))
#        DLCPro = Toptica.LaserName(("COM10",38400))  # in case of 38400 baud connection
        return

    def on_deactivate(self):
        self.iBeamSmart.close()

       
    def on(self):
        print("turn laser on")
        self.iBeamSmart.enable()
    
    def off(self):
        print("turn laser off")
        self.iBeamSmart.enable(enabled = False)
    
    def is_enabled(self):
        self.iBeamSmart.is_enabled()
    
    def set_power(self, p, ch=2):
        """
        Set power p in W
        """
        print("Set channel ", ch, " output to ", p,"W.")
        self.iBeamSmart.set_channel_power(ch, p)
    
    def get_power(self):
        return self.iBeamSmart.get_output_power()

    def get_channel_power(self):
        return self.iBeamSmart.get_channel_power(channel='all')
    
    def get_full_data(self):
        print(self.iBeamSmart.get_full_data())
    
    def get_full_info(self):
        print(self.iBeamSmart.get_full_info())
    
    def get_full_status(self):
        print( self.iBeamSmart.get_full_status())
    
    def get_settings(self):
        print(self.iBeamSmart.get_settings())

    def set_device_variable(self, key, value):
        print("Setting ", key, value)
        self.iBeamSmart.set_device_variable(key,value)
    
    def reboot(self):
        self.iBeamSmart.reboot()