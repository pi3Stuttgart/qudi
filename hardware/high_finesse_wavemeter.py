# -*- coding: utf-8 -*-

"""
This module contains a POI Manager core class which gives capability to mark
points of interest, re-optimise their position, and keep track of sample drift
over time.

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

from qtpy import QtCore
import ctypes   # is a foreign function library for Python. It provides C
                # compatible data types, and allows calling functions in DLLs
                # or shared libraries. It can be used to wrap these libraries
                # in pure Python.

from interface.wavemeter_interface import WavemeterInterface
from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import Mutex

from ctypes import*
from math import *

#from hardware.wavemeter.wavemeter import WaveMeter, PIDParams

#WAVEMETER_PID = PIDParams(1.1, 0.38, 0.82, 1.05, .155, 9.99)


class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the wavelength to the parent class
    sig_wavelength = QtCore.Signal(float, float)

    def __init__(self, parentclass):
        super().__init__()

        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass


    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start the timer.

        @param bool state: (True) starts timer, (False) stops it.
        """

        if state_change:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(self._parentclass._measurement_timing)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _measure_thread(self):
        """ The threaded method querying the data from the wavemeter.
        """

        # update as long as the state is busy
        if self._parentclass.module_state() == 'running':
            # get the current wavelength from the wavemeter
            temp1=float(self._parentclass._wavemeterdll.GetWavelength(0))
            temp2=float(self._parentclass._wavemeterdll.GetWavelength(0))

            # send the data to the parent via a signal
            self.sig_wavelength.emit(temp1, temp2)



class HighFinesseWavemeter(Base,WavemeterInterface):
    """ Hardware class to controls a High Finesse Wavemeter.

    Example config for copy-paste:

    high_finesse_wavemeter:
        module.Class: 'high_finesse_wavemeter.HighFinesseWavemeter'
        measurement_timing: 10.0 # in seconds

    """

    # config options
    _measurement_timing = ConfigOption('measurement_timing', default=10.)
    dll_path = ConfigOption('dll_path', default='C:\Windows\System32\wlmData.dll')
    channel1 = ConfigOption('default_channel', default=1)
    
    # signals
    sig_handle_timer = QtCore.Signal(bool)

    #############################################
    # Flags for the external DLL
    #############################################

    # define constants as flags for the wavemeter
    _cCtrlStop                   = ctypes.c_uint16(0x00)
    # this following flag is modified to override every existing file
    _cCtrlStartMeasurment        = ctypes.c_uint16(0x1002)
    _cReturnWavelangthAir        = ctypes.c_long(0x0001)
    _cReturnWavelangthVac        = ctypes.c_long(0x0000) #0: vac, 1 air, 2: freq, 3: wavenumber, 4: energy ?


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        # the current wavelength read by the wavemeter in nm (vac)
        self._current_wavelength = 0.0
        self._current_wavelength2 = 0.0
        self._dll_path = self.dll_path

    def on_activate(self):
        #############################################
        # Initialisation to access external DLL
        #############################################
        try:
            # imports the spectrometer specific function from dll
            self._wavemeterdll = ctypes.windll.LoadLibrary(self._dll_path)
            
        except:
            self.log.critical('There is no Wavemeter installed on this '
                    'Computer.\nPlease install a High Finesse Wavemeter and '
                    'try again.')

        # define the use of the GetWavelength function of the wavemeter
#        self._GetWavelength2 = self._wavemeterdll.GetWavelength2
        # return data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength2.restype = ctypes.c_double
        # parameter data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength2.argtypes = [ctypes.c_double]

        # define the use of the GetWavelength function of the wavemeter
#        self._GetWavelength = self._wavemeterdll.GetWavelength
        # return data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength.restype = ctypes.c_double
        # parameter data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength.argtypes = [ctypes.c_double]

        # define the use of the ConvertUnit function of the wavemeter
#        self._ConvertUnit = self._wavemeterdll.ConvertUnit
        # return data type of the ConvertUnit function of the wavemeter
        self._wavemeterdll.ConvertUnit.restype = ctypes.c_double
        # parameter data type of the ConvertUnit function of the wavemeter
        self._wavemeterdll.ConvertUnit.argtypes = [ctypes.c_double, ctypes.c_long, ctypes.c_long]

        # manipulate perdefined operations with simple flags
#        self._Operation = self._wavemeterdll.Operation
        # return data type of the Operation function of the wavemeter
        self._wavemeterdll.Operation.restype = ctypes.c_long
        # parameter data type of the Operation function of the wavemeter
        self._wavemeterdll.Operation.argtypes = [ctypes.c_ushort]

        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        self._hardware_pull.sig_wavelength.connect(self.handle_wavelength)

        # start the event loop for the hardware
        self.hardware_thread.start()


    def on_deactivate(self):
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_acqusition()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()
        self._hardware_pull.sig_wavelength.disconnect()

        try:
            # clean up by removing reference to the ctypes library object
            del self._wavemeterdll
            return 0
        except:
            self.log.error('Could not unload the wlmData.dll of the '
                    'wavemeter.')


    #############################################
    # Methods of the main class
    #############################################

    def handle_wavelength(self, wavelength1, wavelength2):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        self._current_wavelength = wavelength1
        self._current_wavelength2 = wavelength2

    def start_acqusition(self):
        """ Method to start the wavemeter software.

        @return int: error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter reading is started.
        """

        # first check its status
        if self.module_state() == 'running':
            self.log.error('Wavemeter busy')
            return -1


        self.module_state.run()
        # actually start the wavemeter
        self._wavemeterdll.Operation(self._cCtrlStartMeasurment) #starts measurement

        # start the measuring thread
        self.sig_handle_timer.emit(True)

        return 0

    def stop_acqusition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return int: error code (0:OK, -1:error)
        """
        # check status just for a sanity check
        if self.module_state() == 'idle':
            self.log.warning('Wavemeter was already stopped, stopping it '
                    'anyway!')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(True)
            # set status to idle again
            self.module_state.stop()

        # Stop the actual wavemeter measurement
        self._wavemeterdll.Operation(self._cCtrlStop)

        return 0

    def get_current_wavelength(self, kind="air",ch=channel1):
        """ This method returns the current wavelength.

        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

        @return float: wavelength (or negative value for errors)
        """
        factor = {"vac": 0, "air": 1, "freq": 2, "wavenumber": 3, "energy": 4}[kind]
        self._wavemeterdll.GetWavelengthNum.restype = ctypes.c_double
        self._current_wavelength = self._wavemeterdll.GetWavelengthNum(ctypes.c_int(ch), ctypes.c_double(0))
        return float(self._wavemeterdll.ConvertUnit(self._current_wavelength,0,ctypes.c_int(factor)))
        
    def get_timing(self):
        """ Get the timing of the internal measurement thread.

        @return float: clock length in second
        """
        return self._measurement_timing

    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.

        @param float timing: clock length in second

        @return int: error code (0:OK, -1:error)
        """
        self._measurement_timing=float(timing)
        return 0

    #Start of the PID Loop
    def startPIDLoop(self):
        self._wavemeterdll.SetDeviationChannel(ctypes.c_bool(2),ctypes.c_bool(1))
        return 'True'

    #Stop of the PID Loop
    def stopPIDLoop(self):
        self._wavemeterdll.SetDeviationChannel(ctypes.c_bool(2), ctypes.c_bool(0))
        return 'False'
    #Sets the desired Frequency

    def setPIDFrequency(self,value):
        self._wavemeterdll.SetDeviationReference(ctypes.c_double(value))

    # #Start of the PID Loop # Setzt Häckchen auf 1
    # def startPIDLoop(self):
    #     self._wavemeterdll.SetDeviationMode(ctypes.c_bool(1))
    #     return 'True'

    # #Stop of the PID Loop # Setzt Häckchen auf 0
    # def stopPIDLoop(self): #shouldn't be touched, because it also turns of PID lock for all other connected lasers
    #     self._wavemeterdll.SetDeviationMode(ctypes.c_bool(0))
    #     return 'False'

    #Status of the PID LOOP (Häckchen an (1) oder aus (0))
    def statusPIDLoop(self):
        self._wavemeterdll.GetDeviationMode.restype = ctypes.c_bool
        state = self._wavemeterdll.GetDeviationMode(ctypes.c_bool())
        return state
    
    #Get PID reference course, channel num for multi switches, in case of SiC-LT 2 its channel 2
    def get_reference_course(self,channel=channel1): # Reads current aimed frequency
        """
        Arguments: channel
        Returns: the string corresponing to the reference set on the WLM.
        For example, constant reference: '619.1234'
        Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
        """
        #first create a string buffer
        string_buffer = ctypes.create_string_buffer(1024)
        xp = ctypes.cast(string_buffer, ctypes.POINTER(ctypes.c_char))
        self._wavemeterdll.GetPIDCourseNum.restype = ctypes.c_long
        self._wavemeterdll.GetPIDCourseNum.argtypes = [ctypes.c_long, xp]
        self._wavemeterdll.GetPIDCourseNum(channel, string_buffer)
        return string_buffer.value


	#Sets the desired PID lock Frequency
    def set_reference_course(self,function, channel=channel1):
        """
        Arguments: the string corresponing to the reference set on the WLM.
        For example, constant reference: '619.1234'
        Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
        Returns: None

        Code: 
        set_reference_course('327.10200')
        set_reference_course('327.10200 + 0.001 * triangle(t/10)') for scanning
        """ 
        string_buffer = ctypes.create_string_buffer(1024)
        xp = ctypes.cast(string_buffer, ctypes.POINTER(ctypes.c_char))
        self._wavemeterdll.SetPIDCourseNum.restype = ctypes.c_long
        self._wavemeterdll.SetPIDCourseNum.argtypes = [ctypes.c_long, xp]
        string_buffer.value = "{}".format(function).encode()
        self._wavemeterdll.SetPIDCourseNum(channel, string_buffer)

    def stop_control(port = 2, signal = 0):
        print("FIXME") #FIXME
        WaveMeter.set_deviation_channel(port, signal)
    
    def start_control(port = 2, signal = 2):
        print("FIXME") #FIXME
        WaveMeter.set_deviation_channel(port, signal)
