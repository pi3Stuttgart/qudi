#PLE-Logic for mcas-module from Javid which combines AWG and ps and uses AWG as master.

import numpy as np
import sys
sys.path.append('C:\src\qudi\hardware\Keysight_AWG_M8190\pyarbtools_master') #quickfix to proceed, should be improved

from hardware.Keysight_AWG_M8190.pym8190a import MultiChSeq as mcas
from hardware.Keysight_AWG_M8190.pym8190a import MultiChSeqDict as mcas_dict
from core.module import Base
#import hardware.Keysight_AWG_M8190.pyarbtools_master.pyarbtools as pyarbtools

class PLELogic(Base):
    # def __init__(
    #     self,
    #     ple_voltage_chan: str,
    #     vbounds: Tuple[float, float],
    #     samp_clk_src: str,
    #     time_tagger,
    #     pulse_streamer,
    #     awg
    # ) -> None:
    #     task = Task()
    #     ao_chan = task.ao_channels.add_ao_voltage_chan(
    #         physical_channel=ple_voltage_chan,
    #         min_val=vbounds[0],
    #         max_val=vbounds[1],
    #         units=VoltageUnits.VOLTS
    #     )

    #     task.timing.cfg_samp_clk_timing(
    #         rate=10e3,
    #         source=samp_clk_src,
    #         active_edge=Edge.RISING,
    #         sample_mode=AcquisitionType.FINITE
    #     )

    #     self.task = task

    #     self.v_range = vbounds

    #     self.count_channel = Combiner(
    #         time_tagger, [self.CHANNEL_APD_0, self.CHANNEL_APD_1]
    #     )

    #     self.time_tagger = time_tagger
    #     self.pulse_streamer = pulse_streamer
    #     self.awg = awg
    #awg_device = pyarbtools.instruments.M8190A(
    #        address='TCPIP0::localhost::inst1::INSTR', timeout=50, reset=True
    #    )
    def on_activate(self):
        return 
    
    def on_deactivate(self):
        return 

    def power_to_amp(self, power_dBm, impedance=50):
        power_dBm = np.atleast_1d(power_dBm)
        P_watts = 10**(power_dBm / 10) * 1e-3
        V_rms = np.sqrt(P_watts * impedance)
        V_pp = V_rms * 2 * np.sqrt(2)
        return V_pp / 0.35 #awg_amplitude
        #return V_pp / float(self.awg_device.amp1) #awg_amplitude


    def setup_mw(
        self,
        enable_microwave=True,
        enable_microwave_2=False,
        enable_microwave_3=False,
        mw1_freq=60,
        mw1_pow=4,
        mw2_freq=70,
        mw2_pow=5,
        mw3_freq=80,
        mw3_pow=6,
    ):
        freq = []
        power = []
        if enable_microwave:
            freq += [mw1_freq]
            power += [mw1_pow]
        if enable_microwave_2:
            freq += [mw2_freq]
            power += [mw2_pow]
        if enable_microwave_3:
            freq += [mw3_freq]
            power += [mw3_pow]

        if len(freq) == 0:
            print("No microwave initialized.")
            return

        power = np.asarray(power)
        # generate a single MW segment with the needed mw frequencies
        # and play is continuously until the measurement is stopped.
        seq = mcas(name="PLE", ch_dict={"2g": [1,2],"ps": [1]})
        seq.start_new_segment("PLE")
        seq.asc(pd2g1 = {"type":"sine", "frequencies":[70], "amplitudes":[0.5]}, length_mus=80)
        #seq.asc(pd2g1 = {"type":"sine", "frequencies":freq, "amplitudes":[0.5]}, length_mus=80)
        mcas.status = 1
        awg = mcas_dict()
        awg['PLE'] = seq
        awg.print_info()
        awg['PLE'].run()
        #stop=mcas_dict_awg.mcas_dict.stop_awgs