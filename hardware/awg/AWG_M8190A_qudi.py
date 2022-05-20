"""
author: Vadim Vorobyov

This module provides a GUI for the agilent M8190a AWG.
It can possibly be adopted to other AWGs as well.

The class definitions for basic elements of the AWG are defined in AWG_M8190A_Elements
(like Waveforms, Sequences etc). If you want a new Waveform type, look there.
"""

import os
import copy
import threading
import time
from . import agilent_m8190a as agilent_m8190a
from . import AWG_M8190A_Elements as AWG_M8190A_Elements
import collections
import traceback
import sys
import visa
import time
import numpy as np
from core.module import Base#, ConfigOption
from core.configoption import ConfigOption

from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
from interface.pulser_interface import PulserInterface, PulserConstraints

class SequencesList(collections.MutableSequence):

    def __init__(self, oktypes, list_owner, *args):
        self.oktypes = oktypes
        self.list_owner = list_owner
        self.list = list()
        self.extend(list(args))

    def check(self, val):
        if not isinstance(val, self.oktypes):
            raise TypeError("list item {} is not allowed, as it can not be found in {}".format(val, self.oktypes))

    def check_duplicate(self, v):
        self.list = [item for item in self.list if item.name != v.name]

    def set_parent(self, v):
        v.parent = self.list_owner

    def __len__(self): return len(self.list)

    def __getitem__(self, i): return self.list[i]

    def __delitem__(self, i):
        del self.list[i]
        self.list_owner.update_sequence_name_list()

    def __setitem__(self, i, v):
        self.check(v)
        self.check_duplicate(v)
        self.set_parent(v)
        self.list[i] = v
        self.list_owner.update_sequence_name_list()

    def insert(self, i, v):
        self.check(v)
        self.check_duplicate(v)
        self.set_parent(v)
        self.list.insert(i, v)
        self.list_owner.update_sequence_name_list()

    def __str__(self):
        return str(self.list)

# class AWGGUIHandler(Handler):
#     # def close(self, info, is_ok):
#     #     info.object.state = 'stop'
#     #     info.object.output_1 = 'Off'
#     #     info.object.output_2 = 'Off'
#     #     info.object.running_sequence_1 = ''
#     #     info.object.running_sequence_2 = ''
#     #     os.chdir('D:\\Python\\pi3diamond')
#     #     pi3d.dump(info.object)
#     #     for editor in info.ui._editors:
#     #         if hasattr(editor, 'grid'):
#     #             editor.grid.control.HideCellEditControl()
#     #     return Handler.close(self, info, is_ok)
#
#     def object_title_changed(self, info):
#         info.ui.title = info.object.title

class Channel(object):

    selected_sequence_id = -1  # Int(-1)
    selected_sequence_name_gui = ''  # Str()
    sequence_name_list_gui = ['']  # List(Str)
    fine_delay = 0  # Float()
    fine_delay_limits = {0, 1}  # Dict()
    fine_delay_limits_str = ''  # Str()
    coarse_delay = 0.0  # Float()
    coarse_delay_limits = {0, 1}  # Dict()
    coarse_delay_limits_str = ''  # Str()
    arm_mode = ['SELF', 'ARM']  # Enum('SELF', 'ARM')
    trigger_mode = ['triggered', 'gated', 'continuous']  # Enum('triggered', 'gated', 'continuous')
    output = [0, 1]  # Enum([0, 1])
    complement_output = [0, 1]  # Enum([0, 1])
    differential_offset = 0.0  # Float()
    sample_clock_source = ['EXT', 'INT']  # Enum('EXT', 'INT')
    output_amplitude = 0.5  # Range(value=0.70, low=0.35, high=0.7)
    output_offset = 0.0  # Range(value=0.0, low=0.0, high=0.01) # I do not know the ranges
    sample_marker_amplitude = 0.5  # Range(low=0.0, high=2.25)
    sample_marker_offset = 0.0  # Range(low=-0.5, high=1.75)
    sample_marker_low = 0.0  # Range(low=-0.5, high=1.75)
    sample_marker_high = 0.0  # Range(low=-0.5, high=1.75)
    sync_marker_amplitude = 0.0  # Range(low=0.0, high=2.25)
    sync_marker_offset = 0.0  # Range(low=-0.5, high=1.75)
    sync_marker_low = 0.0  # Range(low=-0.5, high=1.75)
    sync_marker_high = 0.0  # Range(low=-0.5, high=1.75)
    sequencer_mode = 'ARB'  # Enum('ARB', 'STS', 'STSC')
    dynamic_mode = 0  # Enum(0, 1)
    global_sample_offset = 0  # Int(0, label = 'Offset in samples')

    def __init__(self, channel_number, awggui):
        super(Channel, self).__init__()
        self.channel_number = channel_number
        self.awggui = awggui
        self.sequences = []
        self.get_current_settings()

    state = 'abort' #Enum(['abort', 'run'], label='State')
    #run_button = Button(label='Run')
    #abort_button = Button(label='Abort')


    @property
    def sequences(self):
        return self._sequences

    @sequences.setter
    def sequences(self, val):
        typ = AWG_M8190A_Elements.Sequence
        for i in AWG_M8190A_Elements.check_array_like(val, 'sequences'):
            if isinstance(i, typ):
                i.parent = self
            else:
                raise Exception("Elements of property sequences of a {} - instance must "
                                "be of type {} but is of type {}".format(type(self), typ, type(i)))
        self._sequences = SequencesList(typ, self, *val)
        self.update_sequence_name_list()

    def update_sequence_name_list(self):
        if hasattr(self, '_sequences'):
            self.sequence_name_list = [seq.name for seq in self.sequences]

    def _run_button_fired(self):
        self.run()

    def _abort_button_fired(self):
        self.abort()

    def run(self):
        if self.awggui.awg.channels_coupled:
            raise Exception('Channels are coupled. Use the abort method of the AWG Module.')
        if len(self.sequences) == 0:
            raise Exception('No sequences available (i.e. sequences is an empty list).')
        if self.selected_sequence_name == '':
            raise Exception('No sequence selected. This should not have been possible, something is wrong.')
        self.awgch.run = True
        self.state = 'run'
        self.awggui.state = 'run'

    def abort(self):
        if self.awggui.awg.channels_coupled:
            self.awggui.abort()
        else:
            self.awgch.run = False
            self.state = 'abort'
            if self.complementary_awggui_ch.state == 'abort':
                self.awggui.state = 'abort'

    def _sample_clock_source_changed(self):
        if self.sample_clock_source == 'INT':
            self.awggui.internal_sample_frequency = self.awggui.sample_frequency

    @property
    def awgch(self):
        return self.awggui.awg.ch[self.channel_number]

    @property
    def complementary_awggui_ch(self):
        return self.awggui.ch[(self.channel_number)%2 + 1]

    @property
    def sample_frequency(self):
        return self.awggui.sample_frequency

    def get_current_settings(self):
        """Get current settings of AWG. Important if save file is lost, then AWG and GUI will be out of sync."""
        attr_list = ['fine_delay', 'fine_delay_limits', 'coarse_delay', 'coarse_delay_limits', 'arm_mode', 'trigger_mode', 'output', 'complement_output',
                     'differential_offset', 'sample_clock_source', 'output_amplitude', 'output_offset',
                     'sample_marker_amplitude', 'sample_marker_offset', 'sample_marker_low', 'sample_marker_high',
                     'sync_marker_amplitude', 'sync_marker_offset', 'sync_marker_low', 'sync_marker_high',
                     'sequencer_mode', 'dynamic_mode']
        for name in attr_list:
            setattr(self, name, getattr(self.awgch, name))

    def _selected_sequence_id_changed(self, name, old, new):
        raise Exception('selected_sequence_id is readonly right now. When more than one sequence can be written to awg, it will become meaningful.')

    def write_sequence_to_awg_memory(self, name=None, notify=True, return_time=False):
        t0 = time.time()
        name = self.selected_sequence_name if name is None else name
        if name != '':
            self.abort()
            sids = self.awgch.write_sequence_stable(sequence=self.ret_sequence(name), sample_offset=self.global_sample_offset)
            self.sequencer_mode = self.awgch.sequencer_mode
            self.trigger_mode = self.awgch.trigger_mode
            dt = time.time() - t0
            if notify:
                print('writing sequence {} on {} ch {} took {:.4f} seconds'.format(name, self.awggui.title, self.channel_number, dt))
            if return_time:
                return dt

    @property
    def selected_sequence_name(self):
        return self._selected_sequence_name

    @selected_sequence_name.setter
    def selected_sequence_name(self, val):
        if val not in self.sequence_name_list:
            raise Exception('Sequence does not exist')
        if val == getattr(self, '_selected_sequence_name', None):
            return
        try:
            self.write_sequence_to_awg_memory(val)
            self._selected_sequence_name = val
        except:
            self.selected_sequence_name = 'wait'
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
            raise Exception('selected_sequence_name of {} ch {} could not be changed to {}'.format(self.awggui.title, self.channel_number, val))
        finally:
            self.selected_sequence_name_gui = self.selected_sequence_name

    @property
    def sequence_name_list(self):
        return self._sequence_name_list

    @sequence_name_list.setter
    def sequence_name_list(self, val):
        self._sequence_name_list = AWG_M8190A_Elements.check_array_like_typ(val, 'sequence_name_list', str)
        self.sequence_name_list_gui = self.sequence_name_list

    def _sequence_name_list_gui_changed(self):
        self.sequence_name_list = list(self.sequence_name_list_gui) #no idea why this list() is necessary, but it is.

    def _selected_sequence_name_gui_changed(self):
        self.selected_sequence_name = self.selected_sequence_name_gui

    def _send_enable_event_button_fired(self):
        self.awgch.send_enable_event()

    def _send_advancement_event_button_fired(self):
        self.awgch.send_advancement_event()

    def save_sequence(self, sequence, notify=True):
        self.sequences.append(sequence)
        if notify:
            print("Sequence {} added to sequences.".format(sequence.name))
        if sequence.name == self.selected_sequence_name:
            self.selected_sequence_name = 'wait'

    def ret_sequence(self, name):
        for sequence in self.sequences:
            if sequence.name == name:
                return sequence
        else:
            raise Exception('This sequence does not exist.')

    def sequence_exists(self, name):
        try:
            s = self.ret_sequence(name)
            return True
        except:
            return False

class AWGGUI(Base):
    """
    This is a liberary for usage of Keysight AWG with QUDI
    Example config:
    ----- TBW
    """

    _modclass = 'AWGKeysight'
    _modtype = 'hardware'
    _lan_address = ConfigOption('LAN_adress', missing='error')
    _name = ConfigOption('name', missing='error')

    # PI3Diamond Legacy for traits. Leave it here for now

    title = 'No Title'
    state = 'abort'  # Enum(['abort', 'run'], label='State')
    internal_sample_frequency_limits = {}  # ,Dict()
    internal_sample_frequency_limits_str = ''  # Str()
    internal_sample_frequency = 1  # [0-12]#Range(value=12., low=0, high=12.0, label='Sample rate [GS/s]', auto_set=False, enter_set=True)
    external_sample_frequency_limits = {}  # Dict()
    external_sample_frequency_limits_str = ''  # Str()
    external_sample_frequency = 0.0  # Float()
    sample_frequency_limits = {}  # Dict()
    sample_frequency_limits_str = ''  # Str()
    sample_frequency = 12.0  # Range(value=12., low=0, high=12.0, label='Sample rate [GS/s]', auto_set=False, enter_set=True)
    sample_clock_source = 'INT'  # Enum('EXT', 'INT')
    sample_clock_output_source = 'INT'  # Enum('EXT', 'INT')
    reference_clock_source = 'INT'  # Enum('EXT', 'INT', 'AXI')
    trigger_input_threshold_level = 0.0  # Float()
    trigger_input_threshold_level_limits = {}  # Dict()
    trigger_input_threshold_level_limits_str = ''  # Str()
    trigger_input_impedance = 'LOW'  # Enum('LOW', 'HIGH')
    trigger_input_slope = 'POS'  # Enum('POS', 'NEG', 'EITH')
    trigger_source = 'EXT'  # Enum('EXT', 'INT')
    internal_trigger_frequency = 0.0  # Float()
    internal_trigger_frequency_limits = {}  # Dict()
    internal_trigger_frequency_limits_str = ''  # Str()
    event_input_threshold_level = 0.0  # Float()
    event_input_threshold_level_limits = {}  # Dict()
    event_input_threshold_level_limits_str = ''  # Str()
    enable_event_source = 'TRIG'  # Enum('TRIG', 'EVENT')
    advancement_event_source = 'TRIG'  # Enum('TRIG', 'EVEN', 'INT')
    # send_enable_event_button = Button()
    gate_open = 0  # Enum(0, 1) #visible_when="channels_coupled == 1"
    # send_advancement_event_button = Button()
    # send_begin_button = Button()
    channels_coupled = 0  # Enum(0, 1)

    # ch1 = Channel() #Instance(Channel, factory=Channel)
    # ch2 = Channel() #Instance(Channel, factory=Channel)


    # Indicate how fast frequencies within a list or sweep mode can be changed:
    # _FREQ_SWITCH_SPEED = 0.009  # Frequency switching speed in s (acc. to specs)
    def on_activate(self):

        self.title = self._name
        self.awg = agilent_m8190a.AWG(self._lan_address,self._name)
        self.awg.restore_settings_from_file() # FIXME - AWG sample frequency not in the file 'AWG settings'!!
        self.get_current_settings()
        self.ch1 = Channel(channel_number=1, awggui=self)  # Instance(Channel, factory=Channel)
        self.ch2 = Channel(channel_number=2, awggui=self)
        self.write_wait()
        # self.start_monitor_status_thread()

    def on_deactivate(self):

        self.awg.awg_visa_device.close()
        del(self.awg)
        # TODO what should be here: think about what if rm also should be closed...

    def get_current_settings(self):
        attr_list = ['internal_sample_frequency', 'internal_sample_frequency_limits',
                     'external_sample_frequency', 'external_sample_frequency_limits',
                     'sample_clock_output_source', 'reference_clock_source',
                     'trigger_input_threshold_level', 'trigger_input_threshold_level_limits',
                     'trigger_input_impedance', 'trigger_input_slope','trigger_source',
                     'internal_trigger_frequency', 'internal_trigger_frequency_limits',
                     'event_input_threshold_level', 'event_input_threshold_level_limits',
                     'enable_event_source', 'advancement_event_source', 'gate_open',
                     'channels_coupled']
        for name in attr_list:
            if name in ['gate_open'] and not self.awg.channels_coupled:
                return
            setattr(self, name, getattr(self.awg, name))
        self.sample_frequency_limits = self.internal_sample_frequency_limits

    def write_wait(self):
        wait = AWG_M8190A_Elements.Sequence(name='wait',
                                            data_list=[
                                                AWG_M8190A_Elements.SequenceStep(
                                                    data_list=[AWG_M8190A_Elements.WaveStep(length_smpl=320)],
                                                    advance_mode='AUTO',
                                                    name='wait')
                                            ]
                                            )
        for i in [1, 2]:
            self.ch[i].sequences.append(wait)
            self.ch[i].selected_sequence_name = 'wait'

    def _send_enable_event_button_fired(self):
        self.awg.send_enable_event()

    def _send_advancement_event_button_fired(self):
        self.awg.send_advancement_event()

    def _send_begin_button_fired(self):
        self.awg.send_begin()

    def _channels_coupled_changed(self):
        if self.channels_coupled == 0:
            self.channels_coupled = 1
            print('Uncoupling channels is possible, but suppressed for sake of simplicity. Remove this message, if you need to.')

    def _ch1_default(self):
        return Channel(channel_number=1, awggui=self)

    def _ch2_default(self):
        return Channel(channel_number=2, awggui=self)

    @property
    def ch(self):
        return {1: self.ch1, 2: self.ch2}

    def start_monitor_status_thread(self):
        def ms():
            while True:
                time.sleep(2)
                if self.awg.run:
                    self.state = 'run'
                    for i in [1, 2]:
                        self.ch[i].state = {True: 'run', False: 'abort'}[self.awg.ch[i].run]
                else:
                    self.state = 'abort'
                    self.ch[1].state = 'abort'
                    self.ch[2].state = 'abort'

        self.monitor_status_thread = threading.Thread(target=ms)
        self.monitor_status_thread.start()

    ######################################################################################################################################
    # start/stop
    ######################################################################################################################################

    def _run_button_fired(self):
        self.run()

    def _abort_button_fired(self):
        self.abort()

    def run(self):
        for i in [1, 2]:
            c = self.ch[i]
            if len(c.sequences) == 0 or c.selected_sequence_name == '':
                raise Exception('AWG can not be started, if no sequence is selected.')
        self.awg.run = True
        self.ch[1].state = 'run'
        self.ch[2].state = 'run'
        self.state = 'run'

    def abort(self):
        self.awg.run = False
        self.state = 'abort'
        self.ch[1].state = 'abort'
        self.ch[2].state = 'abort'

if __name__ == '__main__':
    a = AWGGUI(name='awg2g')
    #from AWG_M8190A_Elements import *
    wait = AWG_M8190A_Elements.Sequence(name='wait', data_list=[AWG_M8190A_Elements.SequenceStep(data_list=[AWG_M8190A_Elements.WaveStep(length_smpl=320)], advance_mode='AUTO', name='wait')])
    print(wait.data_list[0].number_of_steps)
    # import AWG_M8190A_GUI as G
    #a = AWGGUI('awg2g')
    #a.ch[1].sequences.append(wait)
    #print(1)