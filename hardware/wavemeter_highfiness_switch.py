"""
the setPIDfrequency() in the xxx.backup.py did not work!
Instead: using get/set_reference_course function, which is also
compatible for wavemeter with multi-switches
Added by Di on 2021-09-02
multiple ports using getFrequencyNum and getWavelengthNum (2021-09-27)
"""

from ctypes import*
from math import *

from qtpy import QtCore

from interface.wavemeter_interface import WavemeterInterface
from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import Mutex


class HighFinesseWavemeter(Base,WavemeterInterface):
	""" Hardware class to controls a High Finesse Wavemeter.

	Example config for copy-paste:

	high_finesse_wavemeter:
		module.Class: 'high_finesse_wavemeter.HighFinesseWavemeter'
		measurement_timing: 10.0 # in seconds

	"""

	# config options
	_measurement_timing = ConfigOption('measurement_timing', default=10.)

	# signals
	sig_handle_timer = QtCore.Signal(bool)

	#############################################
	# Flags for the external DLL
	#############################################

	# define constants as flags for the wavemeter
	_cCtrlStop				   = c_uint16(0x00)
	# this following flag is modified to override every existing file
	_cCtrlStartMeasurment		= c_uint16(0x1002)
	_cReturnWavelangthAir		= c_long(0x0001)
	_cReturnWavelangthVac		= c_long(0x0000)


	def __init__(self, config, **kwargs):
		super().__init__(config=config, **kwargs)

		#locking for thread safety
		self.threadlock = Mutex()

		# the current wavelength read by the wavemeter in nm (vac)
		self._current_wavelength = 0.0
		self._current_wavelength2 = 0.0


	def on_activate(self):
		#############################################
		# Initialisation to access external DLL
		#############################################
		try:
			# imports the spectrometer specific function from dll
			self._wavemeterdll = windll.LoadLibrary(r'C:\Windows\System32\wlmData_backup.dll')
			self.data_dll = windll.LoadLibrary(r'C:\Windows\System32\wlmData_backup.dll')

		except:
			self.log.critical('There is no Wavemeter installed on this '
					'Computer.\nPlease install a High Finesse Wavemeter and '
					'try again.')

		# define the use of the GetWavelength function of the wavemeter
#		self._GetWavelength2 = self._wavemeterdll.GetWavelength2
		# return data type of the GetWavelength function of the wavemeter
		self._wavemeterdll.GetWavelength2.restype = c_double
		# parameter data type of the GetWavelength function of the wavemeter
		self._wavemeterdll.GetWavelength2.argtypes = [c_double]

		# define the use of the GetWavelength function of the wavemeter
#		self._GetWavelength = self._wavemeterdll.GetWavelength
		# return data type of the GetWavelength function of the wavemeter
		self._wavemeterdll.GetWavelength.restype = c_double
		# parameter data type of the GetWavelength function of the wavemeter
		self._wavemeterdll.GetWavelength.argtypes = [c_double]	

		# define the use of the ConvertUnit function of the wavemeter
#		self._ConvertUnit = self._wavemeterdll.ConvertUnit
		# return data type of the ConvertUnit function of the wavemeter
		self._wavemeterdll.ConvertUnit.restype = c_double
		# parameter data type of the ConvertUnit function of the wavemeter
		self._wavemeterdll.ConvertUnit.argtypes = [c_double, c_long, c_long]

		# manipulate perdefined operations with simple flags
#		self._Operation = self._wavemeterdll.Operation
		# return data type of the Operation function of the wavemeter
		self._wavemeterdll.Operation.restype = c_long
		# parameter data type of the Operation function of the wavemeter
		self._wavemeterdll.Operation.argtypes = [c_ushort]

		# create an indepentent thread for the hardware communication
		self.hardware_thread = QtCore.QThread()

		# create an object for the hardware communication and let it live on the new thread
		#self._hardware_pull = HardwarePull(self)
		#self._hardware_pull.moveToThread(self.hardware_thread)

		# connect the signals in and out of the threaded object
		#self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
		#self._hardware_pull.sig_wavelength.connect(self.handle_wavelength)

		# start the event loop for the hardware
		self.hardware_thread.start()


	def on_deactivate(self):
		if self.module_state() != 'idle' and self.module_state() != 'deactivated':
			self.stop_acqusition()
		self.hardware_thread.quit()
		self.sig_handle_timer.disconnect()
		#self._hardware_pull.sig_wavelength.disconnect()

		# try:
		# 	 # clean up by removing reference to the ctypes library object
		# 	del self._wavemeterdll
		# 	return 0
		# except:
		# 	self.log.error('Could not unload the wlmData.dll of the wavemeter.')


	#Start a measurement.
	def startMeasurement(self):
		out = self.data_dll.Operation(2)
		return out

	#Stop a measurement.
	def stopMeasurement(self):
		out = self.data_dll.Operation(0)
		return out

	#Ask for the measured wavelength
	def getWavelength(self):
		self.data_dll.GetWavelength.restype = c_double
		wave = self.data_dll.GetWavelength(c_double(0))
		return wave

	#Ask for the measured wavelength with the number of the port
	def getWavelengthNum(self,num_port):
		self.data_dll.GetWavelengthNum.restype = c_double
		wavelength = self.data_dll.GetWavelengthNum(num_port, c_double(0))
		return wavelength

	#Ask for the measured frequncy
	def getFrequency(self):
		self.data_dll.GetFrequency.restype = c_double
		freq = self.data_dll.GetFrequency(c_double(0))
		return freq

	#Ask for the measured frequency with the number of the port
	def getFrequencyNum(self,num_port):
		self.data_dll.GetFrequencyNum.restype = c_double
		freq = self.data_dll.GetFrequencyNum(num_port, c_double(0))
		return freq

	#Wait for an event and read out afterwards
	def getWLMEvent(self):
		self.data_dll.Instantiate.restype = c_long
		ret=self.data_dll.Instantiate(1,5,1500,0)
		#variable:
		i= 0.
		yValues = []
		iVer=c_long() 
		iMode=c_long() 
		iVal=c_long() 
		dVal=c_double()
		iRes=c_long() 


		while i<10.:
			self.data_dll.WaitForWLMEvent.restype = c_long
			ret=self.data_dll.WaitForWLMEventEx(byref(iVer),byref(iMode),byref(iVal),byref(dVal),byref(iRes))
			# if ret 1,2,5,6 and if imode=42
			# if iMode==42 there is a valid value for wavelength on Channel 1
			if (ret == 1 or ret == 2 or ret == 5 or ret == 6):
				if (iMode.value == 42) and (dVal.value > 0):
					yValues.append(dVal.value)
					print('dVal is '+str(dVal.value))
					return dVal.value
			i = i +1.

	#Start of the PID Loop
	def startPIDLoop(self):
		self.data_dll.SetDeviationMode(c_bool(1))
		return 'True'

	#Stop of the PID Loop
	def stopPIDLoop(self):
		self.data_dll.SetDeviationMode(c_bool(0))
		return 'False'

	#Status of the PID LOOP
	def statusPIDLoop(self):
		self.data_dll.GetDeviationMode.restype = c_bool
		state = self.data_dll.GetDeviationMode(c_bool())
		return state

	#Get PID reference course, channel num for multi switches, in my case no switch so it is 1
	def get_reference_course(self,channel=1):
		"""
		Arguments: channel
		Returns: the string corresponing to the reference set on the WLM.
		For example, constant reference: '619.1234'
		Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
		"""
		#first create a string buffer
		string_buffer = create_string_buffer(1024)
		xp = cast(string_buffer, POINTER(c_char))
		self.data_dll.GetPIDCourseNum.restype = c_long
		self.data_dll.GetPIDCourseNum.argtypes = [c_long, xp]
		self.data_dll.GetPIDCourseNum(channel, string_buffer)
		return string_buffer.value


	#Sets the desired PID lock Frequency
	def set_reference_course(self,function, channel=1):
		"""
		Arguments: the string corresponing to the reference set on the WLM.
		For example, constant reference: '619.1234'
		Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
		Returns: None

		Code: 
		set_reference_course('327.10200')
		set_reference_course('327.10200 + 0.001 * triangle(t/10)') for scanning
		""" 
		string_buffer = create_string_buffer(1024)
		xp = cast(string_buffer, POINTER(c_char))
		self.data_dll.SetPIDCourseNum.restype = c_long
		self.data_dll.SetPIDCourseNum.argtypes = [c_long, xp]
		string_buffer.value = "{}".format(function).encode()
		self.data_dll.SetPIDCourseNum(channel, string_buffer)


	#Confert Unit
	def ConvertUnit(self,value,unit,target_unit):
		#0 = wavelength in vac
		#1 = walength in air
		#2 = frequency
		#3 = wavenumber
		#4 = photonengery
		self.data_dll.ConvertUnit.restype = c_double
		value = self.data_dll.ConvertUnit(c_double(value),unit,target_unit)
		return value
	
	def start_acqusition(self):
		""" Method to start the wavemeter software.

		@return (int): error code (0:OK, -1:error)

		Also the actual threaded method for getting the current wavemeter
		reading is started.
		"""
		pass


	def stop_acqusition(self):
		""" Stops the Wavemeter from measuring and kills the thread that queries the data.

		@return (int): error code (0:OK, -1:error)
		"""
		pass


	def get_current_wavelength(self, kind="air"):
		""" This method returns the current wavelength.

		@param (str) kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

		@return (float): wavelength (or negative value for errors)
		"""
		pass


	def get_current_wavelength2(self, kind="air"):
		""" This method returns the current wavelength of the second input channel.

		@param (str) kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

		@return float: wavelength (or negative value for errors)
		"""
		pass


	def get_timing(self):
		""" Get the timing of the internal measurement thread.

		@return (float): clock length in second
		"""
		pass


	def set_timing(self, timing):
		""" Set the timing of the internal measurement thread.

		@param (float) timing: clock length in second

		@return (int): error code (0:OK, -1:error)
		"""
		pass