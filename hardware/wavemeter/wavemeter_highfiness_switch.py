"""
the setPIDfrequency() in the xxx.backup.py did not work!
Instead: using get/set_reference_course function, which is also
compatible for wavemeter with multi-switches
Added by Di on 2021-09-02
multiple ports using getFrequencyNum and getWavelengthNum (2021-09-27)
"""

from ctypes import*
from math import *


class Wavemeter():

	#Import Wavemeter DLL
	# data_dll = windll.wlmData
	data_dll = windll.LoadLibrary('C:\Windows\System32\wlmData.dll')
	# get the right wlmData.dll's from "C:\Program Files (x86)\HighFinesse\Wavelength Meter WS7 4660\Projects\NetworkAccess\NetworkAccess_0006.zip\NetworkAccess\Client_Windows"

	#Function for the Wavelength Meter Angstrom WS7/30

	#Start the Wavemeter
	#Start wavemeter software in hidden server mode
	#ControlWLMEx(18,0,0,-1,0)
	# 18 = hidden and wait for software start
	# -1 = wait infinitely for software start / set time here in milliseconds
	# def startWavemeter():
	# 	out = data_dll.ControlWLMEx(18,0,0,-1,0)
	# 	return out


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