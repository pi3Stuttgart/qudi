from typing import Tuple
from nidaqmx.task import Task
from nidaqmx.constants import AcquisitionType, Edge, SampleTimingType, VoltageUnits, TaskMode
from nidaqmx.system.device import Device
from TimeTagger import TimeDifferences, Combiner
import TimeTagger
from hardware.pulse_streamer import PulseStreamerPGProxy
from hardware.microwave_sources import SMIQ, SMIQSLM01
from pym8190a.pym8190a import MultiChSeqDict, MultiChSeq
from pym8190a.hardware import AWG
import threading

import numpy as np
import time
from WAVEMETER import WAVEMETER
if WAVEMETER:
    from wavemeter import WaveMeter, PIDParams


class PLELogic:
    """ This logic use still the NI card for scanning the laser and readout/calibrate the scan with the wavemeter as the scanning from the wavemeter
    it self it quite slow. Before a measurement the NI voltage range is calibrated on the total frequency range entered and extracted from the Wavemeter"""

    # set TimeTagger Channels
    CHANNEL_TT_0 = 1
    CHANNEL_TT_1 = 2
    CHANNEL_SEQUENCE = 3
    CHANNEL_DETECT = 4

    # set Wavemeter Channels
    WAVEMETER_CHANNEL = 4
    WAVEMETER_CHANNEL_OFF = 0
    # WAVEMETER_PID = PIDParams(0, 1, 0, .155, .155, 1.13) # old
    # PID values: P | I | D | dt | t_a | V/Hz
    if WAVEMETER:
        WAVEMETER_PID = PIDParams(1.1, 0.38, 0.82, 1.05, .155, 9.99)
    else:
        WAVEMETER_PID = None
    DLC_PRO_VOLTAGE_MULTIPLIER = 10
    
    volt_wavelen_array = {}

    def __init__(
        self,
        ple_voltage_chan: str,
        vbounds: Tuple[float, float],
        samp_clk_src: str,
        time_tagger: TimeTagger,
        pulse_streamer: PulseStreamerPGProxy,
        microwave: SMIQSLM01,
        microwave_2: SMIQSLM01,
        wavemeter,
        awg: MultiChSeqDict = None,
    ) -> None:
        
        self.dev = Device("dev1")
        self.dev2 = Device("dev2")
        self.awg = awg
        self.awg_device:AWG = awg.awgs["2g"]
        #self.dev.reset_device()
        #self.dev2.reset_device()
        
        task = Task(new_task_name="PLE AO task")
        ao_chan = task.ao_channels.add_ao_voltage_chan(
            physical_channel=ple_voltage_chan,
            min_val=vbounds[0],
            max_val=vbounds[1],
            units=VoltageUnits.VOLTS
        )
        # Set to the NI.task that it will be triggered with external signal from PS --> "NI_trigger"
        task.timing.cfg_samp_clk_timing(
            rate=10e3,
            source=samp_clk_src,
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.FINITE
        )
        self.task = task
        
        # read_task = Task(new_task_name="PLE read AO task")
        # read_task.ai_channels.add_ai_voltage_chan("/Dev1/_ao10_vs_aognd")
        # self.read_task = read_task

        self.v_range = vbounds

        # Combine both TT input Channles
        self.count_channel = Combiner(
            time_tagger, [self.CHANNEL_TT_0, self.CHANNEL_TT_1]
        )

        self.time_tagger = time_tagger
        self.pulse_streamer = pulse_streamer
        self.microwave = microwave
        self.microwave_2 = microwave_2
        self.wavemeter = wavemeter

    def set_voltage(self, v: float):
        self.task.stop()
        self.task.timing.samp_timing_type = SampleTimingType.ON_DEMAND
        self.task.write(v, auto_start=True)

    def setup(
        self,
        AWG_SMIQ_label: str,
        central_freq,
        frequency_range,
        resolution,
        central_volt,
        volt_range,
        volt_resolution,
        seconds_per_point,
        use_wavemeter,
        enable_microwave,
        enable_microwave_2,
        mw1_freq,
        mw1_pow,
        mw2_freq,
        mw2_pow,
        enable_repump_730,
        enable_repump_780,
        enable_pulsed_repump,
        repump_length,
        decay_repump,
        ps_channels,
    ):
        # self.dev.reset_device()
        # self.dev2.reset_device()
        if WAVEMETER:
            self.use_wavemeter = use_wavemeter
        else:
            self.use_wavemeter = False
        self.set_voltage(0)

        
        if self.use_wavemeter:
            # determine frequency range, f-df/2...f+df/2
            freq = np.arange(
                central_freq - frequency_range / 2,
                central_freq + frequency_range / 2 + resolution,
                resolution
            )
            if WAVEMETER:
                WaveMeter.set_pid_settings(self.WAVEMETER_CHANNEL, self.WAVEMETER_PID)
                # Turns Wavemeter stabilisation off for channel WAVEMETER_CHANNEL by cutting connection between port and signal
                WaveMeter.set_deviation_channel(self.WAVEMETER_CHANNEL, self.WAVEMETER_CHANNEL_OFF)

                # set wavemeter to the minimum frequency
                WaveMeter.set_pid_course(self.WAVEMETER_CHANNEL, str(freq[0] / 1000))
                # start regulation of the Channel again
                WaveMeter.set_deviation_channel(
                    self.WAVEMETER_CHANNEL, self.WAVEMETER_CHANNEL
                )
                meas_freq = 0
                desired_freq = np.round(freq[0]/1000,5)
                while meas_freq != desired_freq:
                    threading.currentThread().stop_request.wait(0.5)
                    if threading.currentThread().stop_request.isSet():
                            break
                    meas_freq = np.round(self.wavemeter.getFrequencyNum(4),5)
                    
                # function returns voltage at controller in mV
                voltage_offset_min = WaveMeter.get_deviation_signal(
                    self.WAVEMETER_CHANNEL
                ) / 1000

                # regulate wavemeter to the maximum frequency and extract the offset voltage
                WaveMeter.set_pid_course(self.WAVEMETER_CHANNEL, str(freq[-1] / 1000))
                
                meas_freq = 0
                desired_freq = np.round(freq[-1]/1000,5)
                while meas_freq != desired_freq:
                    threading.currentThread().stop_request.wait(0.5)
                    if threading.currentThread().stop_request.isSet():
                            break
                    meas_freq = np.round(self.wavemeter.getFrequencyNum(4),5)
                
                voltage_offset_max = WaveMeter.get_deviation_signal(
                    self.WAVEMETER_CHANNEL
                ) / 1000
                WaveMeter.set_deviation_channel(self.WAVEMETER_CHANNEL, self.WAVEMETER_CHANNEL_OFF)

                # calculate the voltage range for the external analog voltage control (nidaq), if the MULTIPLIER is set devide by it
                voltage_range = (
                    voltage_offset_max - voltage_offset_min
                ) / self.DLC_PRO_VOLTAGE_MULTIPLIER
            else:
                voltage_range = 0.0
                
            # check voltage bounds, the controller only takes an input of +-3V
            if voltage_range > 6.0:
                raise Exception("PLE frequency window too big")

            # generate voltage array for nidaq
            self.voltage = np.linspace(
                -voltage_range / 2, voltage_range / 2, freq.size
            )
        
        else:
            self.voltage = np.arange(
                central_volt - volt_range / 2,
                central_volt + volt_range / 2 + volt_resolution,
                volt_resolution
            )
            if self.voltage[0] < -3.0 or self.voltage[-1] > 3.0:
                raise Exception("PLE voltage window too big")

        

        # create TT TimeDifference class (Start, Click, Next measurement)
        self.time_differences = TimeDifferences(            # Class
            self.time_tagger,                               # TimeTagger
            self.count_channel.getChannel(),                # Combined Counting Channels
            self.CHANNEL_DETECT,                            # Channel detect from PS for Start
            self.CHANNEL_DETECT,                            # Channel detect from PS for next bin
            self.CHANNEL_SEQUENCE,                          # Channel detect from PS for next Hist
            int(seconds_per_point * 1e12),                  # Detectionlength
            1,                                              # # of Bins
            self.voltage.size                               # # of Hists
        )
        # self.time_differences.setMaxCounts(1)

        if str(AWG_SMIQ_label) == "SMIQ":
            self.setup_mw(
                enable_microwave,
                enable_microwave_2,
                mw1_freq,
                mw1_pow,
                mw2_freq,
                mw2_pow,
            )
        elif str(AWG_SMIQ_label) == "AWG":
            if mw1_pow + mw2_pow > 1.0:
                print("Sum of MW Power too high (> 1)! No output given!")
                print("MW power:",mw1_pow)
                print("MW 2 power:",mw2_pow)
                pass
            else:
                if self.old_mw_settings != [self.mw_freq,self.mw2_freq,self.mw_power,self.mw2_power]:
                    seq = MultiChSeq(name="Setup_control", ch_dict={"2g": [1]})
                    seq.start_new_segment("MW")
                    seq.asc(name="MW", pd2g1={"type": "sine", "frequencies": [self.mw_freq/1e6,self.mw2_freq/1e6], "amplitudes": list(self.awg_device.power_to_amp1([self.mw_power, self.mw2_power]))}, length_mus=50)
                    self.awg["Setup_control"] = seq
                self.awg["Setup_control"].run()
                self.Cont_mw_enable = True
                self.old_mw_settings = [self.mw_freq,self.mw2_freq,self.mw_power,self.mw2_power]
        
        seq = self.setup_ps(
            enable_repump_730,
            enable_repump_780,
            enable_pulsed_repump,
            repump_length,
            decay_repump,
            seconds_per_point,
            ps_channels
        )
        if self.use_wavemeter:
            self.frequency = freq
        else:
            self.frequency = self.voltage
        self.sequence = seq
        return self.frequency

    # setup microwave SMIQs
    def setup_mw(
        self,
        enable_microwave,
        enable_microwave_2,
        mw1_freq,
        mw1_pow,
        mw2_freq,
        mw2_pow,
    ):
        self.enable_microwave = enable_microwave
        self.enable_microwave_2 = enable_microwave_2
        if enable_microwave:
                mw = self.microwave
                mw.setPower(mw1_pow)
                mw.setFrequency(mw1_freq)
        if enable_microwave_2:
                mw2 = self.microwave_2
                mw2.setPower(mw2_pow)
                mw2.setFrequency(mw2_freq)

    # create PS sequence
    def setup_ps(
        self,
        enable_repump_730,
        enable_repump_780,
        enable_pulsed_repump,
        repump_length,
        decay_repump,
        seconds_per_point,
        ps_channels
    ):
        seq = []

        seq += [(["sequence"], 100)]                                                    # at the beginning to start counting at all
        if enable_pulsed_repump and enable_repump_730:
            seq += [(["730"], repump_length)]
            seq += [([], decay_repump)]
        elif enable_pulsed_repump and enable_repump_780:
            seq += [(["780"], repump_length)]
            seq += [([], decay_repump)]

        for _ in self.voltage:
            seq += [(ps_channels + ["NI_trigger"], 500)]                                    # writes new voltage and then measure after 500ns
            seq += [(ps_channels + ["detect"], int(seconds_per_point * 1e9 - 500))]

        self.ps_seq = seq

    def scan_line(self,volt_wavelen_array):
        self.pulse_streamer.Night()
        self.time_differences.clear()
        time.sleep(0.1)

        # if Wavemeter is connected
        self.volt_wavelen_array = volt_wavelen_array
        if self.use_wavemeter:
            if WAVEMETER:
                self.set_voltage(self.voltage[0])                                               # set first voltage
                WaveMeter.set_pid_course(
                    self.WAVEMETER_CHANNEL, str(self.frequency[0] / 1000)                       # fine tune the toptica on the first Frequency using the wavemeter: Set target freq
                )
                WaveMeter.set_deviation_channel(
                    self.WAVEMETER_CHANNEL, self.WAVEMETER_CHANNEL                              # Turn on Port-Signal connection
                )
            
                meas_freq = 0
                desired_freq = np.round(self.frequency[0]/1000,5)
                while meas_freq != desired_freq:
                    threading.currentThread().stop_request.wait(0.5)
                    if threading.currentThread().stop_request.isSet():
                            break
                    meas_freq = np.round(self.wavemeter.getFrequencyNum(4),5)
                
                WaveMeter.set_deviation_channel(
                    self.WAVEMETER_CHANNEL, self.WAVEMETER_CHANNEL_OFF                          # Turn off Port-Signal connection after 500ms
                )
                # self.read_task.stop()
                # self.volt_wavelen_array[self.read_task.read()] = WaveMeter.get_frequency(4)

        self.task.stop()
        # setup NI task with # of voltage values and voltage steps
        self.task.timing.samp_timing_type = SampleTimingType.SAMPLE_CLOCK
        self.task.timing.samp_quant_samp_per_chan = self.voltage.size
        self.task.write(self.voltage, auto_start=True)

        self.pulse_streamer.setSequence(self.ps_seq, 1)                                     # start PS to write sequence and trigger NI and TT
        while not self.pulse_streamer.hasFinished():
            # self.volt_wavelen_array[self.read_task.read()] = WaveMeter.get_frequency(4)
            time.sleep(.1)                                                                  # wait until this has finished
        data = self.time_differences.getData()                                              # then readout data
        self.time_differences.clear()

        self.task.stop()
        self.task.control(TaskMode.TASK_UNRESERVE)
        # self.task.close()
        return data.flatten(), self.volt_wavelen_array

    
        

    def cleanup(self):
        self.pulse_streamer.Night()
        self.set_voltage(0)
        self.task.stop()
        self.task.control(TaskMode.TASK_UNRESERVE)
        # self.task.close()
        if WAVEMETER:
            WaveMeter.set_deviation_channel(
                self.WAVEMETER_CHANNEL, self.WAVEMETER_CHANNEL_OFF
            )
        try:
            self.microwave.setPower(-99)
        except:
            pass
        try:
            self.microwave_2.setPower(-99)
        except:
            pass