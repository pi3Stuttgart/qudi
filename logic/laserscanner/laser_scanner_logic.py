# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for controlling scans of the
fourth analog output channel.  It was originally written for
scanning laser frequency, but it can be used to control any parameter
in the experiment that is voltage controlled.  The hardware
range is typically -10 to +10 V.

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

from cgitb import enable
from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
import numpy as np
import time

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from PyQt5 import QtTest
import logging; logger = logging.getLogger(__name__)

import base64
import hashlib

from scipy.signal import find_peaks
from scipy.interpolate import UnivariateSpline

from logic.laserscanner.ple_default_values_and_widget_functions import ple_default_values_and_widget_functions as ple_default



class LaserScannerLogic(GenericLogic, ple_default):

    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """
    sig_data_updated = QtCore.Signal()

    # declare connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    savelogic = Connector(interface='SaveLogic')
    mcas_holder = Connector(interface='McasDictHolderInterface')
    fitlogic = Connector(interface='FitLogic')
    
    wavemeterlogic= Connector(interface="WavemeterLoggerLogic")
    
    scan_range = StatusVar('scan_range', [-4, 4])
    number_of_repeats = StatusVar(default=10)
    NumberOfPeaks = StatusVar('NumberOfPeaks', default=2)
    resolution = StatusVar('resolution', 100)
    _scan_speed = StatusVar('scan_speed', 0.1)
    _static_v = StatusVar('goto_voltage', 0)
    fc = StatusVar('fits', None)
    enable_A1 = StatusVar('enable_A1', False)
    enable_A2 = StatusVar('enable_A2', True)
    MW1_Freq = StatusVar('MW1_freq', 70)
    MW2_Freq = StatusVar('MW2_freq', 140)
    MW3_Freq = StatusVar('MW3_freq', 210)
    _MW1_Power = StatusVar('MW1_Power', -21)
    MW2_Power = StatusVar('MW2_Power', -21)
    MW3_Power = StatusVar('MW3_Power', -21)
    enable_MW1 = StatusVar('enable_MW1', True)
    enable_MW2 = StatusVar('enable_MW2', True)
    enable_MW3 = StatusVar('enable_MW3', False)





    sigChangeVoltage = QtCore.Signal(float)
    sigVoltageChanged = QtCore.Signal(float)
    sigScanNextLine = QtCore.Signal()
    sigUpdatePlots = QtCore.Signal()
    sigScanFinished = QtCore.Signal()
    sigScanStarted = QtCore.Signal()
    sigFitPerformed =  QtCore.Signal(str)
    SigIonized = QtCore.Signal()

    # to cut the scan line into smaller parts:
    slices=1
    mode=0
    
    def __init__(self, **kwargs):
        """ Create VoltageScanningLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()
        self.stopRequested = False
        self.AbortRequested=False
        # self.repump_on_during_retrace=True
        # self.A2_on_during_retrace=0
        # self.A1_on_during_retrace=0
        self.local_counts=[]
        self.slice_number=0
        self.MW1_Power=-21
        self.volt_list=[] #track PLE
        self.timstap_list=[] #timestamp for PLE track
        self.accepted_list=[]
        self.happy=True
        self.hashed = False
 
        self.fit_x = []
        self.fit_y = []
        self.interpolated_x_data=np.linspace(0,10,10)
        self.fit_data=np.ones(10)
        self.plot_x = []
        self.plot_x_frequency=[]
        self.plot_y = []
        self.plot_y2 = []

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._scanning_device = self.confocalscanner1()
        self._save_logic = self.savelogic()
        self._awg = self.mcas_holder()
        self._wavemeterlogic = self.wavemeterlogic()
        #self.ps=self._awg.mcas_dict.awgs["ps"]
        self._fit_logic = self.fitlogic()
        # Reads in the maximal scanning range. The unit of that scan range is
        # micrometer!
        self.a_range = self._scanning_device.get_position_range()[3]

        # Initialise the current position of all four scanner channels.
        self.current_position = self._scanning_device.get_scanner_position()

        # initialise the range for scanning
        self.set_scan_range(self.scan_range)

        # Keep track of the current static voltage even while a scan may cause the real-time
        # voltage to change.
        self.goto_voltage(self._static_v)

        # Sets connections between signals and functions
        self.sigChangeVoltage.connect(self._change_voltage, QtCore.Qt.QueuedConnection)
        self.sigScanNextLine.connect(self._do_next_line, QtCore.Qt.QueuedConnection)
        self.sigFitPerformed.connect(self.goto_fitted_peak, QtCore.Qt.QueuedConnection)

        # Initialization of internal counter for scanning
        self._scan_counter_up = 0
        self._scan_counter_down = 0
        # Keep track of scan direction
        self.upwards_scan = True

        # calculated number of points in a scan, depends on speed and max step size
        self._num_of_steps = 50  # initialising.  This is calculated for a given ramp.

        #############################

        # TODO: allow configuration with respect to measurement duration
        self.acquire_time = 20  # seconds

        # default values for clock frequency and slowness
        # slowness: steps during retrace line
        self.set_resolution(self.resolution)
        self._goto_speed = 10  # 0.01  # volt / second
        self.set_scan_speed(self._scan_speed)
        self._smoothing_steps = 0  # steps to accelerate between 0 and scan_speed
        self._max_step = 0.01  # volt

        ##############################

        # Initialie data matrix
        self._initialise_data_matrix(100)
        self._wavemeterlogic.start_scanning() #the array of frequencies will be updated
        self.start_stop_timestamps=[]
        self.timestamp_list=[]
        self.f_start_end=[]
        self.xy_data=[] # will contain the frequency and the counts associated with this frequency for each trace measured# ok is not used anymore
        self.range_defined=False

        self.tmp_storage=[]
        self.measured_frequencies=[]
        self.start_list=[]
        self.stop_list=[]

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stopRequested = True
        self.AbortRequested = False

    @QtCore.Slot(float)
    def goto_voltage(self, volts=None):
        """Forwarding the desired output voltage to the scanning device.

        @param float volts: desired voltage (volts)

        @return int: error code (0:OK, -1:error)
        """
        # Changes the respective value
        if volts is not None:
            self._static_v = volts

        # Checks if the scanner is still running
        if (self.module_state() == 'locked'
                or self._scanning_device.module_state() == 'locked'):
            self.log.error('Cannot goto, because scanner is locked!')
            return -1
        else:
            self.sigChangeVoltage.emit(volts)
            return 0

    def _change_voltage(self, new_voltage):
        """ Threaded method to change the hardware voltage for a goto.

        @return int: error code (0:OK, -1:error)
        """
        ramp_scan = self._generate_ramp(self.get_current_voltage(), new_voltage, 0.75)
        if len(ramp_scan[0])==1:
            ramp_scan=np.hstack((ramp_scan,ramp_scan))
        elif len(ramp_scan[0])<1:
            return 0

        self._initialise_scanner()
        ignored_counts = self._scan_line(ramp_scan)
        self._close_scanner()
        self.sigVoltageChanged.emit(new_voltage)
        return 0

    def _goto_during_scan(self, voltage=None):
        if voltage is None:
            return -1

        #if abs(self.get_current_voltage()-voltage)<0.01: #avoid a strange situation where we get an error
        #    goto_ramp = self._generate_ramp(self.get_current_voltage(), voltage+0.05, 0.75)

        #    ignored_counts = self._scan_line(goto_ramp)

        goto_ramp = self._generate_ramp(self.get_current_voltage(), voltage, 0.75)
        if len(goto_ramp[0])==1:
            # this fix works only in this case, it is not meant to work when another channel than the last one (the 4th)
            goto_ramp=np.hstack((goto_ramp,goto_ramp))
            goto_ramp[3,1]=voltage
        
        ignored_counts = self._scan_line(goto_ramp)

        
        return 0

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = float(clock_frequency)
        # checks if scanner is still running
        if self.module_state() == 'locked':
            return -1
        else:
            return 0

    def set_resolution(self, resolution):
        """ Calculate clock rate from scan speed and desired number of pixels """
        self.resolution = resolution
        scan_range = abs(self.scan_range[1] - self.scan_range[0])
        duration = scan_range / self._scan_speed
        new_clock = resolution / duration
        return self.set_clock_frequency(new_clock)

    def set_scan_range(self, scan_range):
        """ Set the scan range """
        r_max = np.clip(scan_range[1], self.a_range[0], self.a_range[1])
        r_min = np.clip(scan_range[0], self.a_range[0], r_max)
        self.scan_range = [r_min, r_max]

    def set_voltage(self, volts):
        """ Set the channel idle voltage """
        self._static_v = np.clip(volts, self.a_range[0], self.a_range[1])
        self.goto_voltage(self._static_v)

    def set_scan_speed(self, scan_speed):
        """ Set scan speed in volt per second """
        self._scan_speed = np.clip(scan_speed, 1e-9, 1e6)
        self._goto_speed = self._scan_speed

    def set_scan_lines(self, scan_lines):
        self.number_of_repeats = int(np.clip(scan_lines, 1, 1e6))

    def _initialise_data_matrix(self, scan_length):
        """ Initializing the ODMR matrix plot. """

        self.scan_matrix = np.zeros((self.number_of_repeats, scan_length))
        self.scan_matrix2 = np.zeros((self.number_of_repeats, scan_length))
        self.plot_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.plot_x_frequency=self.plot_x/0.30 #1000 MHz equals 0.22 V on the PLE x range with FeedForward on # 1000 MHz equals 0.30 V on the PLE x range without FeedForward
        self.plot_y = np.zeros(scan_length)
        self.plot_y2 = np.zeros(scan_length)
        self.fit_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.fit_y = np.zeros(scan_length)
        return

    def get_current_voltage(self):
        """returns current voltage of hardware device(atm NIDAQ 4th output)"""
        return self._scanning_device.get_scanner_position()[3]

    def _initialise_scanner(self):
        """Initialise the clock and locks for a scan"""
        self.module_state.lock()
        self._scanning_device.module_state.lock()

        returnvalue = self._scanning_device.set_up_scanner_clock(
            clock_frequency=self._clock_frequency)
        if returnvalue < 0:
            self._scanning_device.module_state.unlock()
            self.module_state.unlock()
            self.set_position('scanner')
            return -1

        returnvalue = self._scanning_device.set_up_scanner()
        if returnvalue < 0:
            self._scanning_device.module_state.unlock()
            self.module_state.unlock()
            self.set_position('scanner')
            return -1

        return 0

    def start_scanning(self, v_min=None, v_max=None):
        """Setting up the scanner device and starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """
        # print(self._scanning_device.module_state()) #self._scanning_device.module_state() is not the same as _optimizer_logic.module_state.current! So _s_d.module_state is "idle" even when confocal refocus runs.
        # if self._scanning_device.module_state() == 'locked':
        #     logger.error('Nicard is in module state "locked".')
        #     raise Exception    

        print("Start PLE scan...")


        # check if nidaq is not already used
        if not(self._scanning_device._scanner_counter_daq_tasks==[] or self._scanning_device._scanner_clock_daq_task==None):
        #if not(self._scanning_device._scanner_counter_daq_tasks==[] or self._scanning_device._scanner_analog_daq_task==None or self._scanning_device._scanner_clock_daq_task==None or self._scanning_device._clock_daq_task==[] or self._scanning_device._counter_daq_tasks ==None):
            print("another scanner is running. You need to wait. i will continue with current scanner task")
            return

        self.currenttime = time.time()
        self._awg.mcas_dict.stop_awgs()
        self.trace_seq()
        if self.enable_PulsedRepump:
            #self.ps.stream(seq=[[int(self.RepumpDuration*1e3),["repump"],0,0],[int(self.RepumpDecay*1e3),[],0,0]],n_runs=1) #self.RepumpDuration is in µs
            self._awg.mcas_dict['repump'].run()
        self.current_position = self._scanning_device.get_scanner_position() #Never used
        print("PLE Logic current pos", self.current_position)

        if v_min is not None:
            self.scan_range[0] = v_min
        else:
            v_min = self.scan_range[0]
        if v_max is not None:
            self.scan_range[1] = v_max
        else:
            v_max = self.scan_range[1]

        self._scan_counter_up = 0
        self._scan_counter_down = 0
        self.upwards_scan = True

        self.set_resolution(self.resolution)
        
        self._upwards_ramp = self._generate_ramp(v_min, v_max, self._scan_speed)
        self._downwards_ramp = self._generate_ramp(v_max, v_min, self._scan_speed)
        #print("passed time 3", time.time()-self.currenttime)
        
        #this part is used to be able to abort the scanning process more rapidly
        if self.resolution/self.slices<3: #avoid getting empty scan lines

            self.slices=int(self.resolution/3)
        self._upwards_ramp_slices=self.slice_array(self._upwards_ramp)
        self.slice_number=0
        self.local_counts = []
        self.timestamp_list=[]
        self.f_start_end=[]
        self.xy_data=[]
        self.range_defined=False

        self._initialise_data_matrix(len(self._upwards_ramp[3]))
        
        #print("passed time 4", time.time()-self.currenttime)
        
        # Lock and set up scanner
        returnvalue = self._initialise_scanner()
        if returnvalue < 0:
            # TODO: error message
            logging.error('The scanner was not initialised')
            return -1

        self.stopped=False
        self.start_stop_timestamps=[]
        self.start_list=[]
        self.stop_list=[]
        # initialize wavemeter data
        #self._wavemeterlogic._hardware_pull._parentclass._wavelength_data=[]


        self.sigScanNextLine.emit()
        self.sigScanStarted.emit()
        #print("passed time 5", time.time()-self.currenttime)        
        return 0

    def slice_array(self,x):
        arr=np.arange(0,len(x[0]))
        propor=(len(x[0])+1)/self.slices
        parts=[x[:,(i*propor<=arr) & (arr<(i+1)*propor)] for i in range(self.slices)]
        return parts

# DOES THE ERROR, WHICH SHUTS DOWN MEASUREMENT COME FROM HERE???
    def stop_scanning(self):
        """Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        #print("Stopping...")
        with self.threadlock:
            print("threadlock laserscanning")
            if self.module_state() == 'locked':
                print("i'm locked")
                self._close_scanner() # hope this will not destroy something
                self._initialise_scanner()
                self.stopRequested = True
                #self._do_next_line()
        return 0

    def abort_scanning(self):
        #print("Aborting...")
        with self.threadlock:
            if self.module_state() == 'locked':
                self.AbortRequested = True
        return 0


    def _close_scanner(self):
        """Close the scanner and unlock"""
        with self.threadlock:
            self.kill_scanner()
            self.stopRequested = False
            self.AbortRequested = False
            if self.module_state.can('unlock'):
                self.module_state.unlock()

    def _do_next_line(self):
        """ If stopRequested then finish the scan, otherwise perform next repeat of the scan line
        """
        # stops scanning
        if ((self.stopRequested and self.slice_number==0) or self._scan_counter_down >= self.number_of_repeats or self.AbortRequested):
            #QtTest.QTest.qSleep(5000)
            self._goto_during_scan(self._static_v)
            self._close_scanner()
            self.sigScanFinished.emit()
            self.local_counts=[]
            self.slice_number=0
            # self.ps.constant(pulse=(0,[],0,0)) # just for safety
            self._awg.mcas_dict.stop_awgs()
            # self.stopped=True # I put the stopped = True into "goto_fitted_peak", since that is the last called method after scanning

            self.measured_frequencies=self._wavemeterlogic._hardware_pull._parentclass._wavelength_data.copy()
            return

        if self._scan_counter_up == 0 and self.slice_number==0:
            # move from current voltage to start of scan range.
            self._goto_during_scan(self.scan_range[0])
            #QtTest.QTest.qSleep(5000)
            self._wavemeterlogic._hardware_pull._parentclass._wavelength_data=[]
            

        if self.upwards_scan:
            # print("running seq: ", self.curr_sequence_name) # Does it affect the sequence if it is started repeatedly?
            self._awg.mcas_dict.stop_awgs()
            self._awg.mcas_dict[self.curr_sequence_name].run()
            
            fstart=self._wavemeterlogic._wavemeter_device.get_current_wavelength2()
            self.start_list.append(time.time()-self._wavemeterlogic._acqusition_start_time)
            counts = self._scan_line(self._upwards_ramp_slices[self.slice_number])
            fend=self._wavemeterlogic._wavemeter_device.get_current_wavelength2()
            self.f_start_end.append([fstart,fend,len(counts)])

            #get the timestamp from the wavemeter
            self.timestamp_list.append(self._scanning_device.timestamp_list)
            

            #print("PLElogic position during _do_next_line", self._scanning_device.get_scanner_position())
        
            self.local_counts=self.local_counts+list(counts)
            self.slice_number+=1
            if self.slice_number==self.slices:
                if self.mode==0:
                    freqs=np.concatenate([np.linspace(fstart,fend,length) for fstart,fend,length in self.f_start_end])

                else:
                    # calculate the frequencies from the wavelengths measured
                    freq_data=self._wavemeterlogic._hardware_pull._parentclass._wavelength_data.copy()

                    wavelengths=np.array(freq_data)[:,1]
                    times=np.array(freq_data)[:,0]

                    freqs=np.concatenate([np.interp(Ts,xp=times,fp=wavelengths) for Ts in self.timestamp_list])

                cts=self.local_counts
                self.stop_list.append(time.time()-self._wavemeterlogic._acqusition_start_time)
                #TODO get the real fmin,fmax,points
                if not self.range_defined:
                    self.fmin=min(freqs)
                    self.fmax=max(freqs)
                    self.range_defined=True

                self.f_range=np.linspace(self.fmin,self.fmax,len(self.local_counts)) #this will be the x axis for all the scans #do not calculate it here, t least not fmin and fmax

                self.xy_data.append([freqs,cts])


                # because freqs might have a lesser span than fmin->fmax, we artificially create the two extrema data points for the interpolation to work
                if min(freqs)>self.fmin:
                    freqs=np.concatenate(([self.fmin],freqs))
                    cts=np.concatenate(([0],cts))
                    
                if max(freqs)<self.fmax:
                    freqs=np.concatenate((freqs,[self.fmax]))
                    cts=np.concatenate((cts,[0]))


                self.interpolated_cts=np.interp(self.f_range, 
                                                xp=freqs,
                                                fp=cts
                                                )
                
                #self.tmp_storage.append(self.f_start_end.copy())

                self.timestamp_list=[] #reinitialize the timestamp_list
                self.f_start_end=[]

                #old code
                self.scan_matrix[self._scan_counter_up] =self.local_counts # Here occurs an error "cannot copy sequence with size 21 to array axis with dimension 20". This only occured, when variables where changed while the programm is running.
                self.plot_y = self.plot_y + np.array(self.local_counts)

                # # new code
                # self.scan_matrix[self._scan_counter_up] =self.interpolated_cts
                # self.plot_y = self.plot_y + np.array(self.interpolated_cts)

                self.check_if_ionized()
                self.local_counts=[]
                self._scan_counter_up += 1
                self.upwards_scan = False
                self.slice_number=0 

        
        else: #retrace
            #self.measured_frequencies=np.concatenate(self._wavemeterlogic._hardware_pull._parentclass._wavelength_data.copy(), axis=0)[1::2]
            #if len(self.measured_frequencies)!=0:
            #    self.extract_freqlines() #updates plot_x_frequency
            #print("X AXIS:")
            #print(self.plot_x_frequency)
            #print(np.shape(self.plot_x_frequency))
            self.sigUpdatePlots.emit()
            if self.enable_PulsedRepump:
                # self.ps.stream(seq=[[int(self.RepumpDuration*1e3),["repump"],0,0],[int(self.RepumpDecay*1e3),[],0,0]],n_runs=1) #self.RepumpDuration is in µs
                self._awg.mcas_dict.stop_awgs()
                self._awg.mcas_dict['repump'].run()
            counts = self._scan_line(self._downwards_ramp)
            counts = np.ones(self.scan_matrix2[self._scan_counter_down].shape[0])
            self.scan_matrix2[self._scan_counter_down] = counts
            self.plot_y2 += counts
            self._scan_counter_down += 1
            self.upwards_scan = True
            self.start_stop_timestamps=[]


        self.sigScanNextLine.emit()
# Create sequence which runs only once for repump pulse
# Create sequence for upwards scan

    def check_if_ionized(self):
        peak_min_counts=100
        ionized=not(np.sum(np.asarray(self.local_counts)>peak_min_counts))
        if ionized:
            print("Ionized")
            self.SigIonized.emit()

    
    @property
    def MW1_Power(self):
        return self._MW1_Power

    @MW1_Power.setter
    def MW1_Power(self,val):
        self._MW1_Power=val

    def trace_seq(self):
        hash = base64.b64encode(hashlib.sha1(self.convert_seq_params_to_string().encode()).digest())
        #Added self.queue._gated_counter.readout_duration such that the hash recognizes a change in readout duration and will update n_values in the sequence accordingly
        self.curr_sequence_name = "ple_trace_hash_{}".format(hash)
        if self.hashed and not self.curr_sequence_name in self._awg.mcas_dict:
            print("hash in PLE: ", self.curr_sequence_name)
            self._awg.mcas_dict.stop_awgs()
            self.setup_seq(sequence_name=self.curr_sequence_name)

        elif self.hashed == False: 
            self._awg.mcas_dict.stop_awgs()
            self.curr_sequence_name = "ple_trace"
            self.setup_seq(sequence_name=self.curr_sequence_name)
        #else:
            #print("Dont need to set up new RF.")
        return
        
    def setup_seq(self, sequence_name):
        self.power = []
        if self.enable_MW1:
            self.power += [self.MW1_Power]
        if self.enable_MW2:
            self.power += [self.MW2_Power]
        if self.enable_MW3:
            self.power += [self.MW3_Power]
        
        self.power = np.asarray(self.power)
        self.power=self.power_to_amp(self.power)
        if np.sum(self.power)>1:
            logger.error("Combined Microwavepower of all active channels too high! Need value below 1. Value of {} was given.", np.sum(self.power))
            raise Exception
            
        # generate a single MW sequence with the needed mw frequencies and play is continuously until the measurement is stopped,
        # either by the stop button, the runtime, or number of sequence repetitions.
        seq = self._awg.mcas(name=sequence_name, ch_dict={"2g": [1, 2], "ps": [1]})
        frequencies = np.array([self.MW1_Freq, self.MW2_Freq, self.MW3_Freq])[[self.enable_MW1, self.enable_MW2, self.enable_MW3]]
        seq.start_new_segment("Microwaves"+str(frequencies), loop_count=500)
        if len(self.power) == 0:
            seq.asc(name="without MW",
                    A1=self.enable_A1,
                    A2=self.enable_A2,
                    repump=self.enable_Repump,
                    length_mus=10
                    )
        else:
            seq.asc(name="with MW", pd2g1={"type": "sine", "frequencies": frequencies, "amplitudes": self.power},
                    A1=self.enable_A1,
                    A2=self.enable_A2,
                    gateMW=True,
                    repump=self.enable_Repump,
                    length_mus=10
                    )
        
        # if not "PLE_treace" in self._awg.mcas_dict.keys():
        self._awg.mcas_dict.stop_awgs()
        QtTest.QTest.qSleep(200)
        self._awg.mcas_dict[sequence_name] = seq
        #self._awg.mcas_dict.print_info()
        return
        
    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / self._awg.mcas_dict.awgs['2g'].ch[1].output_amplitude
       
    def _generate_ramp(self, voltage1, voltage2, speed):
        """Generate a ramp vrom voltage1 to voltage2 that
        satisfies the speed, step, smoothing_steps parameters.  Smoothing_steps=0 means that the
        ramp is just linear.

        @param float voltage1: voltage at start of ramp.

        @param float voltage2: voltage at end of ramp.
        """

        # It is much easier to calculate the smoothed ramp for just one direction (upwards),
        # and then to reverse it if a downwards ramp is required.

        v_min = min(voltage1, voltage2)
        v_max = max(voltage1, voltage2)

        if v_min == v_max:
            ramp = np.array([v_min, v_max])
        else:
            # These values help simplify some of the mathematical expressions
            linear_v_step = speed / self._clock_frequency
            smoothing_range = self._smoothing_steps + 1

            # Sanity check in case the range is too short

            # The voltage range covered while accelerating in the smoothing steps
            v_range_of_accel = sum(
                n * linear_v_step / smoothing_range for n in range(0, smoothing_range)
                )

            # Obtain voltage bounds for the linear part of the ramp
            v_min_linear = v_min + v_range_of_accel
            v_max_linear = v_max - v_range_of_accel

            if v_min_linear > v_max_linear:
                self.log.warning(
                    'Voltage ramp too short to apply the '
                    'configured smoothing_steps. A simple linear ramp '
                    'was created instead.')
                num_of_linear_steps = int(np.rint((v_max - v_min) / linear_v_step))
                ramp = np.linspace(v_min, v_max, num_of_linear_steps)

            else:
                num_of_linear_steps = int(np.rint((v_max_linear - v_min_linear) / linear_v_step))
                #num_of_linear_steps = int(num_of_linear_steps) # FIXME. This was not needed before 13.10.2022. Should be already handled by np.rint

                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array(
                    [sum(
                        n * linear_v_step / smoothing_range for n in range(1, N)
                        ) for N in range(1, smoothing_range)
                    ])

                accel_part = v_min + smooth_curve
                decel_part = v_max - smooth_curve[::-1]

                linear_part = np.linspace(v_min_linear, v_max_linear, num_of_linear_steps)
                ramp = np.hstack((accel_part, linear_part, decel_part))

        # Reverse if downwards ramp is required
        if voltage2 < voltage1:
            ramp = ramp[::-1]

        # Put the voltage ramp into a scan line for the hardware (4-dimension)
        spatial_pos = self._scanning_device.get_scanner_position()

        scan_line = np.vstack((
            np.ones((len(ramp), )) * spatial_pos[0],
            np.ones((len(ramp), )) * spatial_pos[1],
            np.ones((len(ramp), )) * spatial_pos[2],
            ramp
            ))
        return scan_line

    def _scan_line(self, line_to_scan=None):
        """do a single voltage scan from voltage1 to voltage2

        """
        if line_to_scan is None:
            self.log.error('Voltage scanning logic needs a line to scan!')
            return -1
        try:
            # scan of a single line
            #print("PLE logic: line_to_scan", line_to_scan)
            counts_on_scan_line = self._scanning_device.scan_line(line_to_scan)
            return counts_on_scan_line.transpose()[0]

        except Exception as e:
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_scanning()
            self.sigScanNextLine.emit()
            raise e

    def kill_scanner(self):
        """Closing the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._scanning_device.close_scanner()
            self._scanning_device.close_scanner_clock()
        except Exception as e:
            self.log.exception('Could not even close the scanner, giving up.')
            raise e
        try:
            if self._scanning_device.module_state.can('unlock'):
                self._scanning_device.module_state.unlock()
        except:
            self.log.exception('Could not unlock scanning device.')
        return 0

    def goto_fitted_peak(self):
        if self.Lock_laser:
            #print("PLE going to fitted peak")
            freqs=np.array(self.Frequencies_Fit.split(";")[:-1]).astype(float)
            peak_volt=max(freqs)
            if peak_volt<self.scan_range[1] and peak_volt>self.scan_range[0]:
                self.volt_list.append(peak_volt)
                self.timstap_list.append(time.time())
                self.accepted_list.append(self.happy)
                self._static_v = peak_volt
                self.goto_voltage(self._static_v)
                #self._wavemeterlogic._wavemeter_device.get_reference_course(self.Frequencies_Fit[-1], channel=2)

                # follow the defect PLE line by applying a voltage to the laser chamber
                #Range=self.scan_range[1]-self.scan_range[0]
                Range=0.4

                self.scan_range[0],self.scan_range[1]=peak_volt-0.5*Range,peak_volt+0.5*Range
            else: 
                # emit an error?
                #retry with bigger scan range:
                if self.scan_range[1]>=3 or self.scan_range[0]<=-3:
                    print("No PLE found")
                    return
                    
                #self.scan_range[0],self.scan_range[1]=self.scan_range[0]-1,self.scan_range[1]+1
                #self.scan_range=list(np.clip(self.scan_range,-3,3))
                self.start_scanning()
        self.stopped=True
        return


    def save_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Save the counter trace data and writes it to a file.

        @return int: error code (0:OK, -1:error)
        """
        print("im am the save data of PLE")
        if tag is None:
            tag = ''

        self._saving_stop_time = time.time()

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath2 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath3 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath4 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        timestamp = datetime.datetime.now()

        if len(tag) > 0:
            filelabel = tag + '_PLE_data'
            filelabel2 = tag + '_PLE_data_raw_trace'
            filelabel3 = tag + '_PLE_data_raw freqs vs cts'
            filelabel4 = tag + '_PLE_data_raw freqs'
        else:
            filelabel = 'PLE_data'
            filelabel2 = 'PLE_data_raw_trace'
            filelabel3 = 'PLE_data_raw freqs vs cts'
            filelabel4 = '_PLE_data_raw freqs'
        
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['frequency (Hz)'] = self.plot_x_frequency
        data['trace count data (counts/s)'] = self.plot_y

        data2 = OrderedDict()
        data2['count data (counts/s)'] = self.scan_matrix[:self._scan_counter_up, :]

        data3 =OrderedDict()
        data3["freqs vs cts per scan"]= self.xy_data

        data4 = OrderedDict()
        data4["freqs"] = self.measured_frequencies

        parameters = OrderedDict()
        parameters['Number of frequency sweeps (#)'] = self._scan_counter_up
        parameters['Start Voltage (V)'] = self.scan_range[0]
        parameters['Stop Voltage (V)'] = self.scan_range[1]
        parameters['Scan speed [V/s]'] = self._scan_speed
        parameters['Clock Frequency (Hz)'] = self._clock_frequency
        parameters['ContrastFit'] = self.Contrast_Fit
        parameters['FrequenciesFit'] = self.Frequencies_Fit
        parameters['LinewidthsFit'] = self.Linewidths_Fit
        parameters['MW1 Power (dBm)'] = self.MW1_Power
        parameters['MW2 Power (dBm)'] = self.MW2_Power
        parameters['MW3 Power (dBm)'] = self.MW3_Power
        parameters['MW1 freq (MHz)'] = self.MW1_Freq
        parameters['MW2 freq (MHz)'] = self.MW2_Freq
        parameters['MW3 freq (MHz)'] = self.MW3_Freq


        fig = self.draw_figure(
            self.scan_matrix,
            self.plot_x,
            self.plot_y,
            self.interpolated_x_data,
            self.fit_data,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        self._save_logic.save_data(
            data,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )

        self._save_logic.save_data(
            data2,
            filepath=filepath2,
            parameters=parameters,
            filelabel=filelabel2,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig
        )

        # self._save_logic.save_data(
        #     data3,
        #     filepath=filepath3,
        #     parameters=parameters,
        #     filelabel=filelabel3,
        #     fmt='%.6e',
        #     delimiter='\t',
        #     timestamp=timestamp,
        #     plotfig=fig
        # )

        
        self._save_logic.save_data(
            data4,
            filepath=filepath4,
            parameters=parameters,
            filelabel=filelabel4,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )

        self.log.info('Laser Scan saved to:\n{0}'.format(filepath))
        return 0

    def draw_figure(self, matrix_data, freq_data, count_data, fit_freq_vals, fit_count_vals, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = np.array([np.min(matrix_data), np.max(matrix_data)])
        else:
            cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(
            matrix_data,
            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
            origin='lower',
            vmin=cbar_range[0],
            vmax=cbar_range[1],
            extent=[
                np.min(freq_data),
                np.max(freq_data),
                0,
                self.number_of_repeats
                ],
            aspect='auto',
            interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which='both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig
    
    def do_gaussian_fit(self):
        #print("doing gaussian fit")
        x_data=self.plot_x.astype(np.float)
        #x_data=self.plot_x_frequency.astype(np.float)
        y_data=self.plot_y.astype(np.float)
        if self.NumberOfPeaks==1:
            model,params=self._fit_logic.make_gaussian_model()

            result = self._fit_logic.make_gaussian_fit(
                                x_axis=x_data,
                                data=y_data,
                                units='Hz',
                                estimator=self._fit_logic.estimate_gaussian_peak
                                )

        elif self.NumberOfPeaks==2:
            model,params=self._fit_logic.make_gaussiandouble_model()

            result = self._fit_logic.make_gaussiandouble_fit(
                                x_axis=x_data,
                                data=y_data,
                                units='Hz',
                                estimator=self._fit_logic.estimate_gaussiandouble_peak
                                )
        elif self.NumberOfPeaks==3:
            model,params=self._fit_logic.make_gaussiantriple_model()

            result = self._fit_logic.make_gaussiantriple_fit(
                                x_axis=x_data,
                                data=y_data,
                                units='Hz',
                                estimator=self._fit_logic.estimate_gaussiantriple_peak
                                )


            logger.warning("function 3 gaussian peaks not implemeted")

        self.interpolated_x_data=np.linspace(x_data.min(),x_data.max(),len(x_data)*5)
        self.fit_data = model.eval(x=self.interpolated_x_data, params=result.params)
        
        #using own fitlogic
        # fit_func=self._fit_logic.make_n_gauss_function(self.NumberOfPeaks)
        # result=fit_func.fit(x_data,y_data)
        # self.fit_data=fit_func(interpolated_x_data,*result["result"].x)

        self.Contrast_Fit:str=''
        self.Frequencies_Fit:str=''
        self.Linewidths_Fit:str=''


        for i in range(self.NumberOfPeaks):
            try:
                self.Contrast_Fit=self.Contrast_Fit+str(round(result.params[("g"+str(i)+"_")*(self.NumberOfPeaks!=1)+"amplitude"].value,3))+"; " # because 1 peak and 2 peak gaussian fit dont give the same result keywords, we add the 'gi_' part (missing in the 1 peak case) by multiplying the string by 1 if paeks!=1 and remove it if peaks=1.
                self.Frequencies_Fit=self.Frequencies_Fit+str(round(result.params[("g"+str(i)+"_")*(self.NumberOfPeaks!=1)+"center"].value,7))+"; "
                self.Linewidths_Fit=self.Linewidths_Fit+str(round(result.params[("g"+str(i)+"_")*(self.NumberOfPeaks!=1)+"fwhm"].value,3))+"; " #TODO convert linewidth from V to MHz
            except Exception as e:
                print("an error occured:\n", e)

        self.sigFitPerformed.emit(self.Frequencies_Fit)
        self.happy=True # Grober Unfug
        return self.interpolated_x_data,self.fit_data,result
    
    def convert_seq_params_to_string(self):
        return str(self.MW1_Power)+str(self.MW2_Power)+str(self.MW3_Power)+str(self.MW1_Freq)+str(self.MW2_Freq)+str(self.MW3_Freq)+str(self.enable_MW1)+str(self.enable_MW2)+str(self.enable_MW3)+str(self.enable_A1)+str(self.enable_A2)+str(self.enable_Repump)+str(self.enable_PulsedRepump)+str(self.Lock_laser)+str(self.RepumpDuration)+str(self.RepumpDecay)
    

    ### From here:
    # Take frequency data from wavemeter and extrapolate it
    # Use this extrapolated data as new x-axis for plot and fit

    def find_freq_extrema(self, data, testplot=False):
        ### Getting minima and maxima with peakfinder (for minima the plot has to be mirrored)
        maxima = find_peaks(data - np.mean(data))[0]
        minima = find_peaks(np.mean(data) - data)[0]

        ## Removing the last element of the minima since it is already related to the way back to 0 of the scan:
        #minima = minima[: -1]
        #minima = minima[1:]

        ## Removing first element of maxima since first line is about to be ignored
        maxima = maxima[1:]

        if testplot:
            plt.plot(data)
            plt.plot(maxima, data[maxima], 'o')
            plt.plot(minima, data[minima], 'o')
            plt.show()

        return (maxima, minima)
    
    def interpolate_freqlines(self, data, minima, maxima, samples):
        frequencylist = []
        linelist = []
        for i, max in enumerate(maxima):
            y = data[minima[i]:maxima[i]]
            x = np.arange(0, len(y), 1)
            f = UnivariateSpline(x, y)
            f.set_smoothing_factor(0.35)
            freqline = f(np.linspace(0, maxima[i] - minima[i] - 1, samples))
            frequencylist.append(freqline)

            linelist.append(np.full((samples), i + 1))

        frequencylist = np.array(frequencylist)
        ## Estimating the mean frequency:
        meanfreq = np.mean(frequencylist)
        relativelist = (frequencylist - meanfreq) * 1e3

        #return (relativelist, linelist, meanfreq)
        return (frequencylist*1e3, linelist, meanfreq)
    
    def average_freqlines(self, freqlines):
        frequencymean = np.zeros_like(freqlines)
        for i in freqlines:
            frequencymean += i
        print("FREQLINES SHAPE:")
        print(np.shape(freqlines)[0])
        frequencymean = frequencymean / np.shape(freqlines)[0]
        return (frequencymean[0])
        
    def extract_freqlines(self, extrematest=False):
        maxima, minima = self.find_freq_extrema(self.measured_frequencies, extrematest)
        freqlines, linelist, meanfreq = self.interpolate_freqlines(self.measured_frequencies, minima, maxima, int(self.resolution))
        if np.shape(freqlines)[0] > 0:
            freqmeanline = self.average_freqlines(freqlines)
            self.plot_x_frequency = freqmeanline