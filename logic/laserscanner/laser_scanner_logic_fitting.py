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
import logging; logger = logging.getLogger(__name__)


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
    
    scan_range = StatusVar('scan_range', [-4, 4])
    number_of_repeats = StatusVar(default=10)
    # resolution = StatusVar(default = 100)
    resolution:int = 100
    _scan_speed = StatusVar('scan_speed', 0.1)
    _static_v = StatusVar('goto_voltage', 0)
    fc = StatusVar('fits', None)
    fit_range = StatusVar('fit_range', 0)

    sigChangeVoltage = QtCore.Signal(float)
    sigVoltageChanged = QtCore.Signal(float)
    sigScanNextLine = QtCore.Signal()
    sigUpdatePlots = QtCore.Signal()
    sigScanFinished = QtCore.Signal()
    sigScanStarted = QtCore.Signal()

    sigPlePlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray)
    sigPleFitUpdated = QtCore.Signal(np.ndarray, np.ndarray, dict, str)

    # to cut the scan line into smaller parts:
    slices=11
    
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

 
        



    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._scanning_device = self.confocalscanner1()
        self._save_logic = self.savelogic()
        self._awg = self.mcas_holder()
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
        # Initalize the ODMR data arrays (mean signal and sweep matrix)
        self._initialize_data_matrix()
        
        self.range_to_fit = 0
        self.fits_performed = {}

        

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
        self._initialise_scanner()
        ignored_counts = self._scan_line(ramp_scan)
        self._close_scanner()
        self.sigVoltageChanged.emit(new_voltage)
        return 0

    def _goto_during_scan(self, voltage=None):
        if voltage is None:
            return -1

        if abs(self.get_current_voltage()-voltage)<0.01: #avoid a strange situation where we get an error
            goto_ramp = self._generate_ramp(self.get_current_voltage(), voltage+0.05, 0.75)
            ignored_counts = self._scan_line(goto_ramp)

        goto_ramp = self._generate_ramp(self.get_current_voltage(), voltage, 0.75)
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

    def _initialize_data_matrix(self, scan_length=resolution):
        """ Initializing the ODMR matrix plot. """
        self.scan_matrix = np.zeros((self.number_of_repeats, scan_length))
        self.scan_matrix2 = np.zeros((self.number_of_repeats, scan_length))
        self.ple_plot_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.ple_plot_y = np.zeros(scan_length)
        self.ple_plot_y2 = np.zeros(scan_length)
        self.ple_fit_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.ple_fit_y = np.zeros(self.ple_fit_x.size)
        
        self.sigPlePlotsUpdated.emit(self.ple_plot_x, self.ple_plot_y, self.scan_matrix)
        current_fit = self.fc.current_fit
        self.sigPleFitUpdated.emit(self.ple_fit_x, self.ple_fit_y, {}, current_fit)
        
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
        self._initialize_data_matrix()
        # Create AWG Sequence which turns on repump during retrace
        print("Start PLE scan...")
        self._awg.mcas_dict.stop_awgs()
        self.retrace_seq()
        self.trace_seq()
        if self.enable_PulsedRepump:
            self._awg.mcas_dict["PLE_retrace"].run()
        
        self.current_position = self._scanning_device.get_scanner_position()

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

        # TODO: Generate Ramps
        self._upwards_ramp = self._generate_ramp(v_min, v_max, self._scan_speed)
        self._downwards_ramp = self._generate_ramp(v_max, v_min, 0.75)

        #this part is used to be able to abort the scanning process more rapidly
        self._upwards_ramp_slices=self.slice_array(self._upwards_ramp)
        self.slice_number=0

        self._initialize_data_matrix(len(self._upwards_ramp[3]))

        # Lock and set up scanner
        returnvalue = self._initialise_scanner()
        if returnvalue < 0:
            # TODO: error message
            return -1

        self.sigScanNextLine.emit()
        self.sigScanStarted.emit()
        return 0

    def slice_array(self,x):
        arr=np.arange(0,len(x[0]))
        propor=(len(x[0])+1)/self.slices
        parts=[x[:,(i*propor<=arr) & (arr<(i+1)*propor)] for i in range(self.slices)]
        return parts

# DOES ERROR, WHICH SHUTS DOWN MEASUREMENT COME FROM HERE???
    def stop_scanning(self):
        """Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        print("Stopping...")
        with self.threadlock:
            if self.module_state() == 'locked':
                #self._close_scanner() # hope this will not destroy something
                #self._initialise_scanner()
                self.stopRequested = True
                #self._do_next_line()
        return 0

    def abort_scanning(self):
        print("Aborting...")
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
            self._goto_during_scan(self._static_v)
            self._close_scanner()
            self.sigScanFinished.emit()
            self.local_counts=[]
            self.slice_number=0
            self._awg.mcas_dict.stop_awgs()
            return

        if self._scan_counter_up == 0 and self.slice_number==0:
            # move from current voltage to start of scan range.
            self._goto_during_scan(self.scan_range[0])

        if self.upwards_scan:
            self._awg.mcas_dict["PLE_trace"].run()
            counts = self._scan_line(self._upwards_ramp_slices[self.slice_number])
            self.local_counts=self.local_counts+list(counts)
            self.slice_number+=1
            if self.slice_number==self.slices:
                self.scan_matrix[self._scan_counter_up] =self.local_counts # Here occurs an error "cannot copy sequence with size 21 to array axis with dimension 20". This only occured, when variables where changed while the programm is running.
                self.plot_y = self.plot_y + np.array(self.local_counts)
                self.local_counts=[]
                self._scan_counter_up += 1
                self.upwards_scan = False
                self.slice_number=0 

        
        else: #retrace

            if self.enable_PulsedRepump:
                self._awg.mcas_dict["PLE_retrace"].run()
            else:
                self._awg.mcas_dict["wait"].run()
            counts = self._scan_line(self._downwards_ramp)
            counts = np.ones(self.scan_matrix2[self._scan_counter_down].shape[0])
            self.scan_matrix2[self._scan_counter_down] = counts
            self.plot_y2 += counts
            self._scan_counter_down += 1
            self.upwards_scan = True



        self.sigUpdatePlots.emit()
        self.sigScanNextLine.emit()
# Create sequence which runs only once for repump pulse
# Create sequence for upwards scan

    def retrace_seq(self):
        seq = self._awg.mcas(name="PLE_retrace", ch_dict={"2g": [1, 2], "ps": [1]})
        seq.start_new_segment("sequence")
        seq.asc(name="without MW",
                repump=True,
                length_mus=self.RepumpDuration
                )
        seq.asc(name="Decay",
                repump=False,
                length_mus=self.RepumpDecay
                )
        self._awg.mcas_dict["PLE_retrace"] = seq

    def trace_seq(self):
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
        seq = self._awg.mcas(name="PLE_trace", ch_dict={"2g": [1, 2], "ps": [1]})
        frequencies = np.array([self.MW1_Freq, self.MW2_Freq, self.MW3_Freq])[[self.enable_MW1, self.enable_MW2, self.enable_MW3]]
        seq.start_new_segment("Microwaves"+str(frequencies), loop_count=100)
        if len(self.power) == 0:
            seq.asc(name="without MW",
                    A1=self.enable_A1,
                    A2=self.enable_A2,
                    repump=self.enable_Repump,
                    length_mus=50
                    )
        else:
            seq.asc(name="with MW", pd2g1={"type": "sine", "frequencies": frequencies, "amplitudes": self.power},
                    A1=self.enable_A1,
                    A2=self.enable_A2,
                    repump=self.enable_Repump,
                    length_mus=50
                    )

        self._awg.mcas_dict["PLE_trace"] = seq
        self._awg.mcas_dict.print_info()
        
    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / 0.35 #awg_amplitude
        #return V_pp / float(self.awg_device.amp1) #awg_amplitude

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
                num_of_linear_steps = np.rint((v_max - v_min) / linear_v_step)
                ramp = np.linspace(v_min, v_max, num_of_linear_steps)

            else:

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / linear_v_step)

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
            counts_on_scan_line = self._scanning_device.scan_line(line_to_scan)
            return counts_on_scan_line.transpose()[0]

        except Exception as e:
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_scanning()
            self.sigScanNextLine.emit()
            raise e

    def get_ple_channels(self):
        return self._scanning_device.get_counter_channels()

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

    def save_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Save the counter trace data and writes it to a file.

        @return int: error code (0:OK, -1:error)
        """
        if tag is None:
            tag = ''

        self._saving_stop_time = time.time()

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath2 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        # filepath3 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        timestamp = datetime.datetime.now()

        if len(tag) > 0:
            filelabel = tag + '_volt_data'
            filelabel2 = tag + '_volt_data_raw_trace'
        #   filelabel3 = tag + '_volt_data_raw_retrace'
        else:
            filelabel = 'volt_data'
            filelabel2 = 'volt_data_raw_trace'
        #   filelabel3 = 'volt_data_raw_retrace'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['frequency (Hz)'] = self.plot_x
        data['trace count data (counts/s)'] = self.plot_y
        #data['retrace count data (counts/s)'] = self.plot_y2

        data2 = OrderedDict()
        data2['count data (counts/s)'] = self.scan_matrix[:self._scan_counter_up, :]

        # data3 = OrderedDict()
        # data3['count data (counts/s)'] = self.scan_matrix2[:self._scan_counter_down, :]

        parameters = OrderedDict()
        parameters['Number of frequency sweeps (#)'] = self._scan_counter_up
        parameters['Start Voltage (V)'] = self.scan_range[0]
        parameters['Stop Voltage (V)'] = self.scan_range[1]
        parameters['Scan speed [V/s]'] = self._scan_speed
        parameters['Clock Frequency (Hz)'] = self._clock_frequency
                
        fig = self.draw_figure(
            self.scan_matrix,
            self.plot_x,
            self.plot_y,
            self.fit_x,
            self.fit_y,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        fig2 = self.draw_figure(
            self.scan_matrix2,
            self.plot_x,
            self.plot_y2,
            self.fit_x,
            self.fit_y,
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
        #     plotfig=fig2
        # )

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
        # key = 'channel: {0}, range: {1}'.format(channel_number, freq_range)
        # fit_freq_vals = self.frequency_lists[freq_range]
        # if key in self.fits_performed:
        #     fit_count_vals = self.fits_performed[key][2].eval()
        # else:
        #     fit_count_vals = 0.0
        
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

    def get_fit_functions(self):
        """ Return the hardware constraints/limits
        @return list(str): list of fit function names
        """
        return list(self.fc.fit_list)    

    def do_fit(self, fit_function=None, x_data=None, y_data=None, channel_index=0, fit_range=0):
        """
        Execute the currently configured fit on the measurement data. Optionally on passed data
        """
        if (x_data is None) or (y_data is None):
            if fit_range >= 0:
                x_data = self.frequency_lists[fit_range]
                x_data_full_length = np.zeros(len(self.final_freq_list))
                # how to insert the data at the right position?
                start_pos = np.where(np.isclose(self.final_freq_list, self.mw_starts[fit_range]))[0][0]
                x_data_full_length[start_pos:(start_pos + len(x_data))] = x_data
                y_args = np.array([ind_list[0] for ind_list in np.argwhere(x_data_full_length)])
                y_data = self.odmr_plot_y[channel_index][y_args]
            else:
                x_data = self.final_freq_list
                y_data = self.odmr_plot_y[channel_index]
        if fit_function is not None and isinstance(fit_function, str):
            if fit_function in self.get_fit_functions():
                self.fc.set_current_fit(fit_function)
            else:
                self.fc.set_current_fit('No Fit')
                if fit_function != 'No Fit':
                    self.log.warning('Fit function "{0}" not available in ODMRLogic fit container.'
                                     ''.format(fit_function))

        self.odmr_fit_x, self.odmr_fit_y, result = self.fc.do_fit(x_data, y_data)
        key = 'channel: {0}, range: {1}'.format(channel_index, fit_range)
        if fit_function != 'No Fit':
            self.fits_performed[key] = (self.odmr_fit_x, self.odmr_fit_y, result, self.fc.current_fit)
        else:
            if key in self.fits_performed:
                self.fits_performed.pop(key)

        if result is None:
            result_str_dict = {}
        else:
            result_str_dict = result.result_str_dict
        self.sigOdmrFitUpdated.emit(
            self.odmr_fit_x, self.odmr_fit_y, result_str_dict, self.fc.current_fit)
        return


    @fc.constructor
    def sv_set_fits(self, val):
        # Setup fit container
        fc = self.fitlogic().make_fit_container('PLE sum', '1d')
        fc.set_units(['Hz', 'c/s'])
        if isinstance(val, dict) and len(val) > 0:
            fc.load_from_dict(val)
        else:
            d1 = OrderedDict()
            d1['Lorentzian dip'] = {
                'fit_function': 'lorentzian',
                'estimator': 'dip'
            }
            d1['Two Lorentzian dips'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'dip'
            }
            d1['N14'] = {
                'fit_function': 'lorentziantriple',
                'estimator': 'N14'
            }
            d1['N15'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'N15'
            }
            d1['Two Gaussian dips'] = {
                'fit_function': 'gaussiandouble',
                'estimator': 'dip'
            }
            default_fits = OrderedDict()
            default_fits['1d'] = d1
            fc.load_from_dict(default_fits)
        return fc

    @fc.representer
    def sv_get_fits(self, val):
        """ save configured fits """
        if len(val.fit_list) > 0:
            return val.save_to_dict()
        else:
            return None

