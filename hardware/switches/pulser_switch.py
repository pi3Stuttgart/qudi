import time
import re
from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import RecursiveMutex
from interface.switch_interface import SwitchInterface
from hardware.swabian_instruments import pulser_client
from core.statusvariable import StatusVar
from core.connector import Connector

class DigitalSwitchPulser(Base, SwitchInterface):
    """ This class enables to control a switch via Swabian Instruments Pulser ().
    Control external hardware by the output of the digital channels of a SI Pulser.

    Example config for copy-paste:

    digital_switch_pulser:
        module.Class: 'switches.digital_switch_pulser.DigitalSwitchDigitalSwitchPulser'
        channels: ['ch5', 'ch6']  # optional
        name: 'My Switch Hardware Name'  # optional
        switch_time: 0.1
        remember_states: False
        switches:                       # optional
            One: ['Low', 'High']
            Two: ['Off', 'On']
    """
    # Channels of the NI Card to be used for switching.
    # Can either be a single channel or multiple lines.

    _channels = ConfigOption(name='channels', missing='error')
    # switch_time to wait after setting the states for the connected hardware to react
    _switch_time = ConfigOption(name='switch_time', default=0.1, missing='nothing')
    # optionally customize all switches in config. Each switch needs a tuple of 2 state names.
    # If used, you must specify as many switches as you have specified channels
    _switches = ConfigOption(name='switches', default=None, missing='nothing')
    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=True, missing='nothing')
    # if inverted is True, first entry in switches is "high" and second is "low"
    _inverted_states = ConfigOption(name='inverted_states', default=False, missing='nothing')

    _states = StatusVar(name='states', default=None)
    states = StatusVar(name='states', default=None)
    pulser = Connector(interface='PulserClient')

    def __init__(self, *args, **kwargs):
        """ Create the digital switch output control module
        """
        super().__init__(*args, **kwargs)
        self.lock = RecursiveMutex()

        # self._channels = tuple()

    def on_activate(self):
        """ Prepare module, connect to hardware.
        The number of switches is automatically determined from the ConfigOption channel:
        """
        # Determine DO lines to use. This defines the number of switches for this module.
       
        # Determine available switches and states
        self.pulser = self.pulser()
        if self._switches is None:
            self._switches = {str(ii): ('Off', 'On') for ii in range(1, len(self._channels) + 1)}
        self._switches = self._chk_refine_available_switches(self._switches)

        if self._hardware_name is None:
            self._hardware_name = 'pulser'

        # reset states if requested, otherwise use the saved states
        if self._remember_states and isinstance(self._states, dict) and \
                set(self._states) == set(self._switches):
            self._states = {switch: self._states[switch] for switch in self._switches}
            self.states = self._states
        else:
            self._states = dict()
            self.states = {switch: states[0] for switch, states in self._switches.items()}

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        pass

    @property
    def name(self):
        """ Name of the hardware as string.

        The name can either be defined as ConfigOption (name) or it defaults to the name of the hardware module.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        return self._switches.copy()

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        return self._states.copy()

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        avail_states = self.available_states
        assert isinstance(state_dict,
                          dict), f'Property "state" must be dict type. Received: {type(state_dict)}'
        assert all(switch in avail_states for switch in
                   state_dict), f'Invalid switch name(s) encountered: {tuple(state_dict)}'
        assert all(isinstance(state, str) for state in
                   state_dict.values()), f'Invalid switch state(s) encountered: {tuple(state_dict.values())}'

        if state_dict:
            with self.lock:
                new_states = self._states.copy()
                new_states.update(state_dict)
                for channel_index, (switch, state) in enumerate(self.states.items()):
                    if switch == 'laser':
                        if state == 'on':
                            self.pulser.laser_on()
                        elif state == 'off':
                            self.pulser.laser_off()
                    elif switch == 'spectrometer':
                        if state == 'on':
                            self.pulser.set_channel_on(channels = [self._channels[channel_index]])
                        elif state == 'off':
                            self.pulser.set_channel_off(channels = [self._channels[channel_index]])
                    elif switch == 'powermeter':
                        self.pulser.set_channel_on(channels = [self._channels[channel_index]])
                        self.pulser.set_channel_off(channels = [self._channels[channel_index]])
                        
                    # if self._inverted_states:
                    #     binary.append(avail_states[switch][0] == state)
                    # else:
                    #     binary.append(avail_states[switch][0] != state
                time.sleep(self._switch_time)
                self._states = new_states

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self._states, f'Invalid switch name: "{switch}"'
        return self.states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        self.states = {switch: state}
        for channel_index, (switch, state) in enumerate(self.states.items()):
                    if switch == 'laser':
                        if state == 'on':
                            self.pulser.laser_on()
                        elif state == 'off':
                            self.pulser.laser_off()
                    elif switch == 'spectrometer':
                        if state == 'on':
                            self.pulser.set_channel_on(channels = [self._channels[channel_index]])
                        elif state == 'off':
                            self.pulser.set_channel_off(channels = [self._channels[channel_index]])
                    elif switch == 'powermeter':
                        self.pulser.set_channel_on(channels = [self._channels[channel_index]])
                        self.pulser.set_channel_off(channels = [self._channels[channel_index]])
                        

    def _chk_refine_available_switches(self, switch_dict):
        """ See SwitchInterface class for details

        @param dict switch_dict:
        @return dict:
        """
        refined = super()._chk_refine_available_switches(switch_dict)
        num = len(self._channels)
        assert len(refined) == num, f'Exactly {num} switches or None must be specified in config'
        assert all(len(s) == 2 for s in refined.values()), 'Switches can only take exactly 2 states'
        return refined
