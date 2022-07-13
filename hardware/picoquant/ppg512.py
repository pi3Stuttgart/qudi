import serial
import csv
import numpy as np
from hardware.picoquant.crc import get_chck_summ # file supplied by picoquant
import time
import matplotlib.pyplot as plt
import os

from core.module import Base
from core.configoption import ConfigOption


class waveform_generation:
    def __init__(self):
        self.path_to_folder = os.path.dirname(os.path.abspath(__file__))

    # Make sure to only send integers to the device. Otherwise it won't work.
    def create_a_waveform_file(self, voltages, fname='waveform.txt'):
        fname = os.path.join(self.path_to_folder,fname)
        line = ''
        for v in voltages:
            line += str(format(int(v), '#04x'))
            line += ';'
        with open(fname, 'w') as fp:
            fp.write(line[:-1])
        print(f'Stored waveform in {fname}')


    def get_waveform_from_file(self,fname='waveform.txt'):
        fname = os.path.join(self.path_to_folder,fname)
        with open(fname, 'r') as fp:
            inpt = fp.read()
        waveform_hex = inpt.split(';')
        waveform_int = np.zeros(len(waveform_hex))
        for i in range(len(waveform_hex)):
            waveform_int[i] = int(waveform_hex[i],16)
        return waveform_int


    def plot_waveform_from_file(self,fname='waveform.txt'):
        fname = os.path.join(self.path_to_folder,fname)
        waveform = self.get_waveform_from_file(fname)
        plt.plot(waveform)
        plt.xlabel('bit')
        plt.ylabel('amp')
        plt.ylim([0,255])
        plt.show()


    def create_gauss(self, width,amp=255):
        if amp > 255:
            raise Exception('amp needs to be 255 or less.')
        voltages = np.zeros((512,))

        offset_index = 256
        gauss = lambda i, : amp*np.exp(-(i-offset_index)**2.0 / width**2.0)

        for index in range(512):
            voltages[index] = gauss(index)
        voltages = np.around(voltages)
        return voltages


    def create_ramp(self, len, amp=255):
        if len > 512:
            raise Exception('len needs to be 512 or less.')
        if amp > 255:
            raise Exception('amp needs to be 255 or less.')
        voltages = np.zeros((512,))
        ramp = np.linspace(0,amp,len) 
        for index in range(len):
            voltages[index] = ramp[index]
        voltages = np.around(voltages)
        return voltages


    def create_triangle(self, amp=255):
        if amp > 255:
            raise Exception('amp needs to be 255 or less.')
        voltages = np.zeros((512,))
        len = 256
        ramp = np.linspace(0,amp,len) 
        for index in range(len):
            voltages[index] = ramp[index]
        for index in range(len):
            voltages[index+len] = np.flip(ramp)[index]
        voltages = np.around(voltages)
        return voltages

    
    def create_square(self,len, amp=255):
        if len > 512:
            raise Exception('len needs to be 512 or less.')
        if amp > 255:
            raise Exception('amp needs to be 255 or less.')
        voltages = np.zeros((512,))
        voltages[:len]=np.ones(len)*amp
        return voltages
            
    
    def create_zero(self):
        voltages = np.zeros((512,))
        return voltages


    def create_sine(self,amp):
        if amp > 255:
            raise Exception('amp needs to be 255 or less.')
        voltages = np.zeros((512,))
        for i in range(512):
            voltages[i] = round(amp* (1 + np.sin(2*np.pi*i/512))/2)
        return voltages


class ppg512(Base):
    # How to write a waveform:
        # # instances so you know what they refer to
        # wg = waveform_generation()
        # ppg = ppg512()
        # # create the waveform and save them in a file, can be omitted it waveform is already in file
        # wg.create_a_waveform_file(wg.create_square(50,amp=255), 'waveform.txt')
        # # plot the waveform (not necessary but nice to see what is going on)
        # wg.plot_waveform_from_file('waveform.txt')
        # # take the wavform from the file and send it to the device
        # ans = ppg.write_waveform(fname='waveform.txt')
    
    _port = ConfigOption(name='port', missing='warn')
    _vccrf = ConfigOption(name='vccrf', missing='warn')
    _vref = ConfigOption(name='vref', missing='warn')

    def __init__(self, port=None,**kwargs):
        if port:
            self._port = port
        self.wg = waveform_generation()
        self.path_to_folder = os.path.dirname(os.path.abspath(__file__))
        super().__init__(**kwargs)

    def on_activate(self):
        self.connect()
        print(self._query('*IDN?'))
        time.sleep(1)
        # set voltages to values specified in config
        self.set_vccrf(self._vccrf)
        time.sleep(1)
        self.set_vref(self._vref)
        time.sleep(1)
        print(self.get_vccrf())
        time.sleep(1)
        print(self.get_vref())
        return


    def on_deactivate(self):
        # set amplifier voltage to min to reduce heating
        self.set_vccrf(12000)
        # also minimise reference voltage to acieve minimal output voltage
        self.set_vref(0)
        # set output to zero (aka. minimal possible voltage)
        self.constant_output()
        self.ser.close()
    

    def connect(self):
        _port = self._port #'COM10'
        self.ser = serial.Serial(port=_port, baudrate=115200, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, timeout=2)
        return

    
    def _write(self, cmd, eol='\r'):
        cmd += eol # end of line marker
        cmd = bytes(cmd,'UTF-8') # turn into bytes
        a = self.ser.write(cmd)
        return


    def _query(self, cmd, eol='\r', delay=0.1):
        """Sends a command to the decive and returns the response.
        
        System responses are:
            BUSY system is busy and can therefore not handle command
            ACK response for every correct set command (ends with '!')
            NACK response for commands with wrong parameter
            COMMAND UNKNOWN wrong or misspelled command
        """
        time.sleep(delay)
        self._write(cmd, eol)
        time.sleep(delay) #if you read right after sending a command, you get an empty string
        ans = self.ser.read_all()
        return ans


    def reset(self):
        """Reset System
        
        System restarts with stored values.
        """
        ans = self._query('SYS:RES!', delay=3)
        return ans


    def set_vref(self,vref):
        """ Sets VREF to vref in mV. Max 2V.

        VREF is stored DAC reference voltage. 
        This is the max voltage that device will give out (when 256 is given as value in waveform).
        """
        ans = self._query(f'SOUR:VOLT:VREF {vref}!')
        return ans


    def get_vref(self):
        """Returns VREF in mV.
        """
        ans = self._query('SOUR:VOLT:VREF?')
        return ans


    def set_vccrf(self,vccrf):
        """ Sets VCCRF to vccrf in mV. Possible values are 12V to 24V

        VCCRF is supply voltage for RF amplifier.
        Set it as low as possible to minimize heating.
        """
        ans = self._query(f'SOUR:VOLT:VCCRF {vccrf}!')
        return ans

    
    def get_vccrf(self):
        """Returns VCCRF in mV.
        """
        ans = self._query('SOUR:VOLT:VCCRF?')
        return ans


    def write_waveform(self, fname = 'waveform.txt'):
        value = []
        fname = os.path.join(self.path_to_folder,fname)
        with open(fname) as fp:
            data = csv.reader(fp, delimiter=';')
            for row in data:
                for column in row:
                    # print(row)
                    value.append(column)

        check_sum = get_chck_summ(fname)
        value.append('0x'+str(check_sum)[2:4])
        value.append('0x'+str(check_sum)[4:6])
        to_write = ''
        for v in value:
            to_write += v
            to_write += ';'

        to_write = to_write[:-1]

        # It is important to read out the memory after sending 'SYS:DATA!' --> use _query
        # If you don't do this, the device will not change the waveform.
        self._query('SYS:DATA!')
        ans = self._query(to_write,eol='')
        print(f'Wrote waveform from {fname} to device.')
        return ans


    def constant_output(self):
        self.wg.create_a_waveform_file(self.wg.create_zero(),fname='temp.txt')
        ans = self.write_waveform(fname='temp.txt')
        return ans
