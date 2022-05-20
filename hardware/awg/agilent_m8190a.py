import visa
import numpy as np
import os
import datetime
import time
import sys
import traceback

#TODO:  -make it possible to write segments and sequences to awg and play them repeatedly. This saves time needed for writing stuff again and again and saves the
#TODO:   awg memory
#TODO:  - See section 7.7 in the manual.
#TODO:    read out messages of the STATus subsystem.
#TODO:    This allows for example to detect linear playtime requirement errors while playing

class SequenceStep(object):
    def __init__(self, awg, channel_number, step_id, sequence_steps):
        self.awg = awg
        self.channel_number = channel_number
        self.step_id = step_id
        self.sequence_steps = sequence_steps

    @property
    def data(self):
        """
        :return: int, int, str, marker-enable, start-addr, end-addr
            segment_id, loop-count, advance-mode, marker-enable, start-addr, end-addr.
        Manual 4.20.2
        """
        uc = self.awg.query("SEQ{}:DATA? {},{},{}".format(self.channel_number, self.sequence_steps.sequence.sid, self.step_id, 1))
        return np.array(uc.split(','), dtype=np.int32)

    @data.setter
    def data(self, value):
        """
        :param value: 6 32-bit words
        for meaning see Manual 4.20.2
        """
        if type(value) == np.ndarray and value.dtype == np.uint32:
            data = ','.join(str(i) for i in value)
        else:
            raise ValueError('Data must be provided as np.int32 array. Binary data is not implemented yet.')
        self.awg.write("SEQ{}:DATA {},{},{}".format(self.channel_number, self.sequence_steps.sequence.sid, self.step_id, data))


class SequenceSteps(dict):
    def __init__(self, awg, channel_number, sequence):
        super(SequenceSteps, self).__init__(self)
        self.awg = awg
        self.channel_number = channel_number
        self.sequence = sequence

    @property
    def step_ids(self):
        return range(self.sequence.length)

    def __getitem__(self, step_id):
        if self.valid_step_id(step_id):
            return SequenceStep(awg=self.awg, channel_number=self.channel_number, step_id=step_id, sequence_steps=self)
        else:
            raise ValueError('The step_id {} is not allowed.'.format(step_id))

    def __repr__(self):
        return self.step_ids

    def valid_step_id(self, step_id):
        if 0 <= step_id <= self.sequence.length - 1 and type(step_id) is int and type(step_id) is int:
            return True
        else:
            return False


class Sequence(object):
    def __init__(self, awg, channel_number, sid, sequences):
        self.awg = awg
        self.channel_number = channel_number
        self.sid = sid
        self.sequences = sequences
        self.steps = SequenceSteps(awg=self.awg, channel_number=self.channel_number, sequence=self)

    @property
    def length(self):
        return [item for item in self.sequences.catalogue if item[0] == self.sid][0][1]

    def delete(self):
        """
        Deletes this sequence.
        """
        self.awg.write("SEQ{}:DEL {}".format(self.channel_number, self.sid))

    @property
    def name(self):
        value = self.awg.query("SEQ{}:NAME? {}".format(self.channel_number, self.sid)).lstrip('"').rstrip('"')
        if value == '':
            value = 'noname'
        return value

    @name.setter
    def name(self, value):
        if value == '':
            value = 'noname'
        self.awg.write("SEQ{}:NAME {},\"{}\"".format(self.channel_number, self.sid, value))

    @property
    def comment(self):
        """
        :return:
        """
        value = self.awg.query("SEQ{}:COMM? {}".format(self.channel_number, self.sid)).lstrip('"').rstrip('"')
        if value == '':
            value = 'noname'
        return value

    @comment.setter
    def comment(self, value):
        """
        :param value:
        :return:
        """
        if value == '':
            value = 'noname'
        self.awg.write("SEQ{}:COMM {},'{}'".format(self.channel_number, self.sid, value))

    @property
    def advance_mode(self):
        """
        :return:
        """
        return self.awg.query("SEQ{}:ADV? {}".format(self.channel_number, self.sid))

    @advance_mode.setter
    def advance_mode(self, value):
        """
        :param value:
        :return:
        """
        self.awg.write("SEQ{}:ADV {},{}".format(self.channel_number, self.sid, value))

    @property
    def loop_count(self):
        """

        :return:
        """
        return int(self.awg.query("SEQ{}:COUN? {}".format(self.channel_number, self.sid)))

    @loop_count.setter
    def loop_count(self, value):
        """
        :param value: int
         possible values 1..4G-1
        :return:
        """
        self.awg.write("SEQ{}:COUN {},{}".format(self.channel_number, self.sid, value))

    def select(self):
        self.awg.write("STAB{}:SEQ:SEL {}".format(self.channel_number, self.sid))


class Sequences(dict):
    def __init__(self, awg, channel_number):
        super(Sequences, self).__init__(self)
        self.awg = awg
        self.channel_number = channel_number

    @property
    def items(self):
        return [(int(i), self.__getitem__(i)) for i in self.sids]

    @property
    def sids(self):
        return sorted([int(i[0]) for i in self.catalogue])

    @property
    def sequences(self):
        return [self.__getitem__(sid) for sid in self.sids]

    def __getitem__(self, sid):
        if self.valid_id(sid):
            # when the sequencer memory is empty, the catalogue is not [] but [[0,0]] for whatever reasons.
            # Nonetheless waveform sid 0 is never assigned.
            return Sequence(awg=self.awg, channel_number=self.channel_number, sid=sid, sequences=self)
        else:
            raise ValueError('The sequence_id {} is not allowed.'.format(sid))

    @property
    def catalogue(self):
        c = self.awg.query("SEQ{}:CAT?".format(self.channel_number)).split(',')
        catalogue = [[int(i), int(l)] for i, l in zip(c[::2], c[1::2])]
        if catalogue == [[0, 0]]:
            return []
        else:
            return catalogue

    def __repr__(self):
        return self.catalogue

    def delete_all(self):
        """

            :return:
            """
        self.awg.write("SEQ{}:DEL:ALL".format(self.channel_number))

    def memory_usage(self):
        """

        :return:
        """
        kl = ['bytes available', 'bytes in use', 'contiguous bytes available']
        vsl = [int(i) for i in self.awg.query("SEQ{}:FREE?".format(self.channel_number)).split(',')]
        return dict((k, int(v)) for k, v in zip(kl, vsl))

    @staticmethod
    def valid_id(sid):
        if 0 <= sid <= 2 ** 19 - 2 and type(sid) is int:
            return True
        else:
            return False

    @staticmethod
    def valid_length(length):
        if 1 <= length <= 2 ** 19 and type(length) is int:
            return True
        else:
            return False

    @property
    def length(self):
        return len(self.sids)

    def define_new(self, length):
        """
        Defines a new segment and returns its segment_id

        :param length: int
            size of the segment in number of samples
            5*64 .. 2G, in sample vector granularity, i.e. multiples of 64
        :return:
        """
        if not self.valid_length(length):  # awg does not throw an error itself (which it does in define_segment())
            raise ValueError('Invalid sequence length {}'.format(length))
        sid = int(self.awg.query("SEQ{}:DEF:NEW? {}".format(self.channel_number, length)))
        return Sequence(self.awg, self.channel_number, sid, sequences=self)

    @property
    def selected(self):
        """
        Select where in the sequence table the sequence starts in STSequence mode.
        In dynamic sequence selection mode select the sequence that is played before the first sequence
        is dynamically selected.
        possible values: 0..512k-1
        Manual 4.21.7
        """
        ssid = int(self.awg.query("STAB{}:SEQ:SEL?".format(self.channel_number)))
        if ssid not in self.sids:
            return None
        else:
            return ssid

    @selected.setter
    def selected(self, value):
        if value not in self.sids:
            raise Exception('While technically possible, selecting sids pointing to the start of a sequence in the sequencer memory are not allowed here.')
        self.awg.write("STAB{}:SEQ:SEL {}".format(self.channel_number, value))

    @property
    def dynamic_mode_selected(self):
        """
        When the dynamic mode for segments or sequences is active, set or query the selected sequence table entry.
        possible values: 0..512k-1
        Manual 4.21.9
        """
        return self.awg.query("STAB{}:DYN:SEL?".format(self.channel_number))

    @dynamic_mode_selected.setter
    def dynamic_mode_selected(self, value):
        self.awg.write("STAB{}:DYN:SEL {}".format(self.channel_number, value))


class Segment(object):
    def __init__(self, awg, channel_number, sid, segments):
        self.awg = awg
        self.channel_number = channel_number
        self.sid = sid
        self.segments = segments

    @property
    def length(self):
        return [item for item in self.segments.catalogue if item[0] == self.sid][0][1]

    @property
    def data(self):
        offset = 0
        uc = self.awg.query("TRAC{}:DATA? {},{},{}".format(self.channel_number, self.sid, offset, self.length))
        return np.array(uc.split(','), dtype=np.int16)

    @data.setter
    def data(self, value):
        offset = 0
        if type(value) == np.ndarray and value.dtype == np.int16:
            data = ','.join(str(i) for i in value)
            self.awg.write("TRAC{}:DATA {},{},{}".format(self.channel_number, self.sid, offset, data))
        else:
            self.awg.write_raw(value)

    def select(self):
        """
        """
        self.awg.write("TRAC{}:SEL {}".format(self.channel_number, self.sid))

    @property
    def name(self):
        value = self.awg.query("TRAC{}:NAME? {}".format(self.channel_number, self.sid)).lstrip('"').rstrip('"')
        if value == '':
            value = 'noname'
        return value

    @name.setter
    def name(self, value):
        if value == '':
            value = 'noname'
        self.awg.write("TRAC{}:NAME {},\"{}\"".format(self.channel_number, self.sid, value))

    @property
    def comment(self):
        """
        :return:
        """
        value = self.awg.query("TRAC{}:COMM? {}".format(self.channel_number, self.sid)).lstrip('"').rstrip('"')
        if value == '':
            value = 'noname'
        return value

    @comment.setter
    def comment(self, value):
        """
        :param value:
        :return:
        """
        if value == '':
            value = 'noname'
        self.awg.write("TRAC{}:COMM {},'{}'".format(self.channel_number, self.sid, value))

    def delete(self):
        """
        :return:
        """
        self.awg.write("TRAC{}:DEL {}".format(self.channel_number, self.sid))


class SelectedSegment(Segment):
    """
    This represents the segment selected wia segments[i].select in sequencer_mode 'ARB'
    """

    def __init__(self, awg, channel_number, segments):
        object.__init__(self)
        self.awg = awg
        self.channel_number = channel_number
        self.segments = segments

    @property
    def advance_mode(self):
        """
        :return:
        """
        return self.awg.query("TRAC{}:ADV?".format(self.channel_number))

    @advance_mode.setter
    def advance_mode(self, value):
        """
        :param value:
        :return:
        """
        self.awg.write("TRAC{}:ADV {}".format(self.channel_number, value))

    @property
    def loop_count(self):
        """
        :return:
        """
        return int(self.awg.query("TRAC{}:COUN?".format(self.channel_number)))

    @loop_count.setter
    def loop_count(self, value):
        """
        :param value:
        :return:
        """
        self.awg.write("TRAC{}:COUN {}".format(self.channel_number, value))

    @property
    def marker_state(self):
        """
        Marker state of the selected segment. (selected via :TRACe[1|2]:SELect[?] <segment_id>)
        possible values: '0', '1'
        :return:
        """
        return int(self.awg.query("TRAC{}:MARK?".format(self.channel_number)))

    @marker_state.setter
    def marker_state(self, value):
        if not value in [0, 1]:
            raise ValueError('Marker state {} not allowed'.format(value))
        self.awg.write("TRAC{}:MARK {}".format(self.channel_number, value))

    @property
    def sid(self):
        return int(self.awg.query("TRAC{}:SEL?".format(self.channel_number)))

class Segments(dict):
    def __init__(self, awg, channel_number):
        super(Segments, self).__init__()
        self.awg = awg
        self.channel_number = channel_number

    @property
    def items(self):
        return [(int(i), self.__getitem__(i)) for i in self.sids]

    @property
    def sids(self):
        c = self.awg.query("trac{}:CAT?".format(self.channel_number)).split(',')
        if c == [[0, 0]]:
            return []
        return [int(i) for i in c[::2]]

    @property
    def segments(self):
        return [self.__getitem__(sid) for sid in self.sids]

    def __getitem__(self, sid):
        if not sid == 0 and self.valid_id(sid):
            # when the waveform memory is empty, the catalogue is not [] but [[0,0]] for whatever reasons.
            # Nonetheless waveform sid 0 is never assigned.
            return Segment(awg=self.awg, channel_number=self.channel_number, sid=sid, segments=self)
        else:
            raise ValueError('The segment_id {} is not allowed.'.format(sid))

    @property
    def catalogue(self):
        c = self.awg.query("trac{}:CAT?".format(self.channel_number)).split(',')
        catalogue = [[int(i), int(l)] for i, l in zip(c[::2], c[1::2])]
        if catalogue == [[0, 0]]:
            return []
        else:
            return catalogue

    def __repr__(self):
        return self.catalogue

    def delete_all(self):
        """

            :return:
            """
        self.awg.write("TRAC{}:DEL:ALL".format(self.channel_number))

    def memory_usage(self):
        """

        :return:
        """
        kl = ['bytes available', 'bytes in use', 'contiguous bytes available']
        vsl = [int(i) for i in self.awg.query("TRAC{}:FREE?".format(self.channel_number)).split(',')]
        return dict((k, int(v)) for k, v in zip(kl, vsl))

    @staticmethod
    def valid_id(sid):
        if 1 <= sid <= 2 ** 19 and type(sid) is int:
            return True
        else:
            return False

    @staticmethod
    def valid_length(length):
        if 320 <= length <= 2 * 1024 ** 3 and length % 64 == 0 and type(length) is int:
            return True
        else:
            return False

    def define_new(self, length):
        """
        Defines a new segment and returns its segment_id

        :param length: int
            size of the segment in number of samples
            5*64 .. 2G, in sample vector granularity, i.e. multiples of 64
        :return:
        """
        if not self.valid_length(
                length):  # awg does not throw an error itself (which it does in define_segment())
            raise ValueError('Invalid segment length {}'.format(length))
        sid = int(self.awg.query("TRAC{}:DEF:NEW? {}".format(self.channel_number, length))) # creates new segment and return it's id (SID)
        return Segment(self.awg, self.channel_number, sid, segments=self)

    def define(self, sid, length):
        """
        Defines a new segment with given segment_id. If segment_id is already taken, an error is thrown.

        :param length: int
            size of the segment in number of samples
            5*64 .. 2G, in sample vector granularity, i.e. multiples of 64, tested by awg
        :return:
        """
        if sid in self.sids:
            raise Exception('Segment already exists.')
        if not self.valid_length(length):  # as the awg does not throw an error itself
            raise ValueError('Invalid segment length {}'.format(length))
        self.awg.write("TRAC{}:DEF {},{}".format(self.channel_number, sid, length))
        return Segment(self.awg, self.channel_number, sid, segments=self)

    @property
    def selected(self):
        return SelectedSegment(awg=self.awg, channel_number=self.channel_number, segments=self)


class Channel(object):
    def __init__(self, channel_number, awg):
        super(Channel, self).__init__()
        self.channel_number = channel_number
        self.awg = awg
        self.segments = Segments(awg=self.awg, channel_number=self.channel_number)
        self.sequences = Sequences(awg=self.awg, channel_number=self.channel_number)

    ####################################################################################################################
    # ARM/TRIGger Subsystem
    ####################################################################################################################

    @property
    def run(self):
        rs = [bool(int(i)) for i in format(int(bin(int(self.awg.query('STAT:OPER:RUN:COND?')))[2:]), '02d')[::-1]]
        return rs[self.channel_number - 1]

    @run.setter
    def run(self, val):
        if val is True:
            self.awg.write("INIT:IMM{}".format(self.channel_number))
        elif val is False:
            self.awg.write("ABOR{}".format(self.channel_number))
        dt = 0.1
        to = 0
        while val is not self.run:
            to += dt
            time.sleep(dt)
            if to > 5:
                raise Exception('What is taking so long? This is not normal behaviour.')

    @property
    def fine_delay_limits(self):
        return {'min': float(self.awg.query('ARM:DEL{}? MIN'.format(self.channel_number)))*1e6, 'max': float(self.awg.query('ARM:DEL{}? MAX'.format(
            self.channel_number)))*1e6}

    @property
    def fine_delay(self):
        return float(self.awg.query("ARM:DEL{}?".format(self.channel_number)))

    @fine_delay.setter
    def fine_delay(self, value):
        self.awg.write("ARM:DEL{} {}".format(self.channel_number, value*1e-6))

    @property
    def coarse_delay_limits(self):
        """
        given in microseconds
        :return:
        """
        return {'min': float(self.awg.query('ARM:CDEL{}? MIN'.format(self.channel_number)))*1e6, 'max': float(self.awg.query('ARM:CDEL{}? MAX'.format(
            self.channel_number)))*1e6}

    @property
    def coarse_delay(self):
        return float(self.awg.query("ARM:CDEL{}?".format(self.channel_number)))*1e6

    @coarse_delay.setter
    def coarse_delay(self, value):
        self.awg.write("ARM:CDEL{} {}".format(self.channel_number, value*1e-6))

    @property
    def arm_mode(self):
        """
        Arm mode
        possible values: 'SELF' or 'ARMED'
        """
        return self.awg.query("INIT:CONT{}:ENAB?".format(self.channel_number))

    @arm_mode.setter
    def arm_mode(self, value):
        if value not in ['SELF', 'ARMED']:
            raise ValueError('Not allowed.')
        self.awg.write("INIT:CONT{}:ENAB {}".format(self.channel_number, value))

    @property
    def continuous_mode(self):
        """
        continuous mode.
        possible values: 0 or 1
        0:
            gate mode off: trigger mode is 'triggered'
            gate mode on: trigger mode is 'gated'
        1:
            gate mode off: trigger mode is 'automatic'
            gate mode on: trigger mode is 'automatic'
        """
        return int(self.awg.query("INIT:CONT{}?".format(self.channel_number)))

    @continuous_mode.setter
    def continuous_mode(self, value):
        if value not in [0, 1]:
            raise ValueError('Not allowed')
        self.awg.write("INIT:CONT{} {}".format(self.channel_number, value))

    @property
    def gate_mode(self):
        """
        gate mode
        possible values 0 or 1
        0: gate mode is off.
            continuous mode off: trigger mode is 'triggered'
            continuous_mode on: trigger mode is 'automatic'
        1: gate mode is on.
            continuous mode off: trigger mode is 'gated'
            continuous mode on: trigger mode is 'automatic'
        """
        return int(self.awg.query("INIT:GATE{}?".format(self.channel_number)))

    @gate_mode.setter
    def gate_mode(self, value):
        if value not in [0, 1]:
            raise ValueError('Not allowed')
        self.awg.write("INIT:GATE{} {}".format(self.channel_number, value))

    __TRIGGER_MODE_MAP__ = {'00': 'triggered', '01': 'gated', '10': 'continuous', '11': 'continuous'}

    @property
    def trigger_mode(self):
        return self.__TRIGGER_MODE_MAP__["{}{}".format(self.continuous_mode, self.gate_mode)]

    @trigger_mode.setter
    def trigger_mode(self, value):
        if not value in self.__TRIGGER_MODE_MAP__.values():
            raise ValueError('Trigger mode not allowed')
        m = {v: k for k, v in self.__TRIGGER_MODE_MAP__.items()}[value]
        self.continuous_mode = int(m[0])
        self.gate_mode = int(m[1])

    def send_enable_event(self):
        self.awg.write('TRIG:ENAB{}'.format(self.channel_number))

    @property
    def gate_open(self):
        return self.awg.query('TRIG:BEG{}:GATE?'.format(self.channel_number))

    @gate_open.setter
    def gate_open(self, value):
        self.awg.write('TRIG:BEG{}:GATE {}'.format(self.channel_number, value))

    def send_advancement_event(self):
        self.awg.write('TRIG:ADV{}'.format(self.channel_number))

    def send_begin(self):
        self.awg.write('TRIG:BEG{}:IMM'.format(self.channel_number))

    ####################################################################################################################
    # MMEMory Subsystem
    ####################################################################################################################

    ####################################################################################################################
    # OUTPut Subsystem
    ####################################################################################################################
    @property
    def output(self):
        """
        arbitrary waveform output
        possible values: 0, 1
        """
        return int(self.awg.query("OUTP{}?".format(self.channel_number)))

    @output.setter
    def output(self, value):
        if value not in [0, 1]:
            raise ValueError('Not allowed')
        self.awg.write("OUTP{} {}".format(self.channel_number, value))

    @property
    def complement_output(self):
        """
        complement arbitrary waveform output
        possible values: '0', '1'
        """
        return int(self.awg.query("OUTP{}:COMP?".format(self.channel_number)))

    @complement_output.setter
    def complement_output(self, value):
        self.awg.write("OUTP{}:COMP {}".format(self.channel_number, value))

    @property
    def differential_offset(self):
        return float(self.awg.query('OUTP:DIOF?'))

    @differential_offset.setter
    def differential_offset(self, value):
        self.awg.write('OUTP{}:DIOF {}'.format(self.channel_number, value))

    @property
    def sample_clock_source(self):
        return self.awg.query('FREQ:RAST:SOUR{}?'.format(self.channel_number))

    @sample_clock_source.setter
    def sample_clock_source(self, value):
        self.awg.write('FREQ:RAST:SOUR{} {}'.format(self.channel_number, value))

    ####################################################################################################################
    # DAC|DC|AC Subsystem
    ####################################################################################################################

    ####################################################################################################################
    # VOLTage Subsystem
    # Set the voltages for the currently selected output path (DAC, DC, or AC). I guess this usually will be DAC.
    ####################################################################################################################

    @property
    def output_amplitude(self):
        return float(self.awg.query("VOLT{}?".format(self.channel_number)))

    @output_amplitude.setter
    def output_amplitude(self, value):
        self.awg.write("VOLT{} {}".format(self.channel_number, value))

    @property
    def output_offset(self):
        return float(self.awg.query("VOLT{}:OFFS?".format(self.channel_number)))

    @output_offset.setter
    def output_offset(self, value):
        self.awg.write("VOLT{}:OFFS {}".format(self.channel_number, value))

    ####################################################################################################################
    # MARKer Subsystem
    ####################################################################################################################
    @property
    def sample_marker_amplitude(self):
        """
        output amplitude for sample marker.
        """
        return float(self.awg.query("MARK{}:SAMP:VOLT:AMPL?".format(self.channel_number)))

    @sample_marker_amplitude.setter
    def sample_marker_amplitude(self, value):
        self.awg.write("MARK{}:SAMP:VOLT:AMPL {}".format(self.channel_number, value))

    @property
    def sample_marker_offset(self):
        """
        output offset for sample marker.
        possible values -0.5..1.75 [Volt]
        """
        return float(self.awg.query("MARK{}:SAMP:VOLT:OFFS?".format(self.channel_number)))

    @sample_marker_offset.setter
    def sample_marker_offset(self, value):
        self.awg.write("MARK{}:SAMP:VOLT:OFFS {}".format(self.channel_number, value))

    @property
    def sample_marker_low(self):
        """
        output low level for sample marker.
        possible values -0.5..1.75 [Volt]
        """
        return float(self.awg.query("MARK{}:SAMP:VOLT:LOW?".format(self.channel_number)))

    @sample_marker_low.setter
    def sample_marker_low(self, value):
        self.awg.write("MARK{}:SAMP:VOLT:LOW {}".format(self.channel_number, value))

    @property
    def sample_marker_high(self):
        """
        output high level for sample marker.
        possible values +0.5..1.75 [Volt]
        """
        return float(self.awg.query("MARK{}:SAMP:VOLT:HIGH?".format(self.channel_number)))

    @sample_marker_high.setter
    def sample_marker_high(self, value):
        self.awg.write("MARK{}:SAMP:VOLT:HIGH {}".format(self.channel_number, value))

    @property
    def sync_marker_amplitude(self):
        """
        output amplitude for sample marker.
        possible values: 0.0.. +2.25 [Volt]
        """
        return float(self.awg.query("MARK{}:SYNC:VOLT:AMPL?".format(self.channel_number)))

    @sync_marker_amplitude.setter
    def sync_marker_amplitude(self, value):
        self.awg.write("MARK{}:SYNC:VOLT:AMPL {}".format(self.channel_number, value))

    @property
    def sync_marker_offset(self):
        """
        output offset for sample marker.
        possible values -0.5..1.75 [Volt]
        """
        return float(self.awg.query("MARK{}:SYNC:VOLT:OFFS?".format(self.channel_number)))

    @sync_marker_offset.setter
    def sync_marker_offset(self, value):
        self.awg.write("MARK{}:SYNC:VOLT:OFFS {}".format(self.channel_number, value))

    @property
    def sync_marker_low(self):
        """
        output low level for sample marker.
        possible values -0.5..1.75 [Volt]
        """
        return float(self.awg.query("MARK{}:SYNC:VOLT:LOW?".format(self.channel_number)))

    @sync_marker_low.setter
    def sync_marker_low(self, value):
        self.awg.write("MARK{}:SYNC:VOLT:LOW {}".format(self.channel_number, value))

    @property
    def sync_marker_high(self):
        """
        output high level for sample marker.
        possible values +0.5..1.75 [Volt]
        """
        return float(self.awg.query("MARK{}:SYNC:VOLT:HIGH?".format(self.channel_number)))

    @sync_marker_high.setter
    def sync_marker_high(self, value):
        self.awg.write("MARK{}:SYNC:VOLT:HIGH {}".format(self.channel_number, value))
    ####################################################################################################################
    # FUNCtion
    ####################################################################################################################

    @property
    def sequencer_mode(self):
        """
        Use this command to set or query the type of waveform that will be generated.
        possible values 'ARB', 'STS', 'STSC'
        'ARB': a single arbitrary waveform segment is played
        'STS: play a sequence
        'STSC': play a scenario
        """
        return self.awg.query("FUNC{}:MODE?".format(self.channel_number))

    @sequencer_mode.setter
    def sequencer_mode(self, value):
        self.awg.write("FUNC{}:MODE {}".format(self.channel_number, value))

    ####################################################################################################################
    # STABle Subsystem
    # Unlike the sequencer subsystem, the STABle subsystem provides full functionality.
    ####################################################################################################################
    @property
    def sequencer_table_data(self):
        """
        PLEASE NOTE: THIS PROPERTY AFFECTS THE COMPLETE SEQUENCER TABLE.

        The command form writes directly into the sequencer memory. The query form reads the data from the sequencer
        memory, if all segments are read-write. The query returns an error, if at least one write-only segment in the
        waveform memory exists. This command affects the complete sequencer table!
        Manual 4.21.6
        """
#        return self.awg.query("STAB{}:DATA?".format(self.channel_number))
        number_of_sequence_table_entries = 524287
        length = 6*number_of_sequence_table_entries
        return self.awg.query("STAB{}:DATA 0, {}?".format(self.channel_number, length))

    @sequencer_table_data.setter
    def sequencer_table_data(self, value):

        # self.awg.write_raw("STAB{}:DATA {}".format(self.channel_number, value))
        self.awg.write_raw("STAB{}:DATA ".format(self.channel_number).encode() + value)

    def reset_sequencer_table(self):
        self.awg.write("STAB{}:RES".format(self.channel_number))

    @property
    def dynamic_mode(self):
        """
        Enable or disable dynamic mode.
        Manual 4.21.8
        """
        return int(self.awg.query("STAB{}:DYN?".format(self.channel_number)))

    @dynamic_mode.setter
    def dynamic_mode(self, value):
        self.awg.write("STAB{}:DYN {}".format(self.channel_number, value))


    @property
    def scenario_mode_sequence_start_index(self):
        """
        Select where in the sequence table the scenario starts in STSCenario mode.
        possible values: 0..512k-1
        Manual 4.21.10
        """
        return self.awg.query("STAB{}:SCEN:SEL?".format(self.channel_number))

    @scenario_mode_sequence_start_index.setter
    def scenario_mode_sequence_start_index(self, value):
        self.awg.write("STAB{}:SCEN:SEL {}".format(self.channel_number, value))

    @property
    def scenario_advance_mode(self):
        """
        advancement mode for scenarios.
        possible values 'AUTO', 'COND', 'REP', 'SING'
        Manual 4.21.11
        """
        return self.awg.query("STAB{}:SCEN:ADV?".format(self.channel_number))

    @scenario_advance_mode.setter
    def scenario_advance_mode(self, value):
        self.awg.write("STAB{}:SCEN:ADV {}".format(self.channel_number, value))

    @property
    def scenario_loop_count(self):
        """
        Set or query the loop count for scenarios.
        possible values: 1..4G-1: number of times the scenario is repeated.
        Manual 4.21.12
        """
        return self.awg.query("STAB{}:SCEN:COUN?".format(self.channel_number))

    @scenario_loop_count.setter
    def scenario_loop_count(self, value):
        self.awg.write("STAB{}:SCEN:COUN {}".format(self.channel_number, value))

    ####################################################################################################################
    # TEST Subsystem
    ####################################################################################################################

    # def write_sequence(self, sequence, sample_offset):
    #     """
    #     CAREFUL1: This method just writes and writes to sequencer and waveform memory. It does not delete ANYTHING.
    #         Call the respective methods from the STAB and TRAC subsystem sections from time to time.
    #
    #     CAREFUL2: If somehow segments are written such, that 'holes' are created in the waveform memory, this method
    #         might or might not write segments in empty spaces into the waveform memory and the
    #         linear playtime requirement might or might not be fulfilled anymore.
    #
    #     Write a AWG_M8190A_Elements.Sequence object into the AWG memory
    #
    #     As is, this method does not allow for:
    #         - Scenarios (this requires use of the STABle subsystem)
    #         - Reusing segments
    #
    #     :param sequence: AWG_M8190A_Elements.Sequence
    #     """
    #     t0 = time.time()
    #     self.sequences.delete_all()
    #     self.segments.delete_all()
    #     segment_ids = []
    #     if sequence.number_of_steps == 0:
    #         raise ('An empty sequence can not be written.')
    #     elif sequence.number_of_steps > 1:
    #         sm_sequence = self.sequences.define_new(length=sequence.number_of_steps)
    #     for i, step in enumerate(sequence.data_list):
    #         wm_segment = self.segments.define_new(length=step.length_smpl)
    #
    #         cmd = 'TRAC%i %i,0,' %(self.channel_number, wm_segment.sid)
    #         length = step.length_smpl*2
    #         cmd += '#' + str(len(str(length)))+str(length)
    #         cmd += buffer(step.segment_block_data(coherent_offset=sample_offset)).__str__()
    #         wm_segment.data = cmd
    #
    #         wm_segment.name = step.name
    #         wm_segment.comment = step.comment
    #         segment_ids.append(wm_segment.sid)
    #         sample_offset += step.loop_count * step.length_smpl
    #         if sequence.number_of_steps > 1:
    #             sm_sequence.steps[i].data = step.sequence_block_data(wm_segment.sid)
    #     if sequence.number_of_steps > 1:
    #         sm_sequence.name = sequence.name
    #         sm_sequence.comment = sequence.comment
    #         sm_sequence.advance_mode = sequence.advance_mode
    #         sm_sequence.loop_count = sequence.loop_count
    #     if sequence.number_of_steps == 1:
    #         self.sequencer_mode = 'ARB'
    #         self.segments[1].select()  #this is only useful, if the sequencer memory is not used properly.
    #     else:
    #         self.sequencer_mode = 'STS'
    #     print "t: {}, n: {}, a: {}, : chn: {}".format(time.time() - t0, sequence.name, self.awg.address, self.channel_number)
    #     return segment_ids

    def write_sequence_stable(self, sequence, sample_offset):
        """
        CAREFUL1: This method just writes and writes to sequencer and waveform memory. It does not delete ANYTHING.
            Call the respective methods from the STAB and TRAC subsystem sections from time to time.

        CAREFUL2: If somehow segments are written such, that 'holes' are created in the waveform memory, this method
            might or might not write segments in empty spaces into the waveform memory and the
            linear playtime requirement might or might not be fulfilled anymore.

        Write a AWG_M8190A_Elements.Sequence object into the AWG memory

        As is, this method does not allow for:
            - Scenarios (this requires use of the STABle subsystem)
            - Reusing segments

        :param sequence: AWG_M8190A_Elements.Sequence
        """
        if sequence.number_of_steps == 1 and sequence.data_list[0].advance_mode != 'AUTO':
            raise Exception('A single Segment right now can only be played, when advance_mode is AUTO. Then trigger mode is set to continuous and the segment is played infinitely.')
        if sequence.number_of_steps == 0:
            raise ('An empty sequence can not be written.')
        self.reset_sequencer_table()
        self.segments.delete_all()
        segment_ids = []
        segmentid_length_dict=dict()
        try:
            for i, step in enumerate(sequence.data_list):
                if not step.reuse_segment:
                    wm_segment = self.segments.define_new(length=step.length_smpl)
                    cmd = bytes('TRAC%i %i,0,' %(self.channel_number, wm_segment.sid), encoding='utf8')
                    length = step.length_smpl*2
                    cmd += bytes('#' + str(len(str(length)))+str(length),encoding='utf8')
                    cmd += bytes(step.segment_block_data(coherent_offset=sample_offset).tostring())
                    wm_segment.data = cmd
                    wm_segment.name = step.name
                    wm_segment.comment = step.comment
                    segment_ids.append(wm_segment.sid)
                    step._sequencer_table_sid = wm_segment.sid
                    length=step.length_smpl
                    sample_offset += step.loop_count * length
                    segmentid_length_dict[wm_segment.sid]=length
                else:
                    sid=step.sequencer_table_sid
                    segment_ids.append(sid)
                    sample_offset += step.loop_count * segmentid_length_dict[sid]
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
            raise Exception('An error occured while writing sequence {}, sequencestep ({},{})'.format(sequence.name, step.name, i))
        if sequence.number_of_steps == 1: #in this case, play single waveform, therefore trigger_mode and advance_mode are slightly different.
            if sequence.data_list[0].advance_mode == 'AUTO':
                self.trigger_mode = 'continuous'
                self.sequencer_mode = 'ARB'
                self.segments[segment_ids[0]].select()  #this is only useful, if the sequencer memory is not used properly.
        else:
            stable=sequence.sequence_table_data_block(segment_ids)
            self.sequencer_table_data = stable
            self.trigger_mode = 'continuous'
            self.sequencer_mode = 'STS'

class AWG(object):
    def __init__(self, address, name):
        self._address = address
        self._name = name
        rm = visa.ResourceManager()
        self.awg_visa_device = rm.open_resource(self.address, timeout=50000, read_termination='\n', write_termination='\n')  #
#        self.awg_visa_device = visa.instrument(self.address, timeout=50000, read_termination='\n', write_termination='\n')
        self._ch = dict([[i, Channel(channel_number=i, awg=self)] for i in range(1, 3)])

    @property
    def address(self):
        return self._address

    @property
    def name(self):
        return self._name

    @property
    def ch(self):
        return self._ch

    @property
    def errors(self):
        """
        :rtype : object
        :return:
        """
        check = True
        err = ''
        while check:
            res = self.awg_visa_device.query('SYST:ERR?')
            if res[0] == '-':
                err += res + '\n'
            else:
                check = False
        return err

    # Communication
    def write(self, cmd):
        """ Submit a SCPI command.
            See Agilent AWG M8190A User's Guide for documentation.
        """
        self.awg_visa_device.write(cmd)
        errors = self.errors
        if errors != '':
            raise Exception('Errors occurred while writing to AWG:\n' + errors)

    # Communication
    def write_raw(self, cmd):
        """ Submit a SCPI command.
            See Agilent AWG M8190A User's Guide for documentation.
        """
        self.awg_visa_device.write_raw(cmd)
        errors = self.errors
        if errors != '':
            raise Exception('Errors occurred while writing to AWG:\n' + errors)

    def query(self, cmd):
        """ Submit a SCPI query and return response.
            See Agilent AWG M8190A User's Guide for documentation.
        :type self: object
        :param cmd:
        """
        try:
            res = self.awg_visa_device.query(cmd)
            errors = self.errors  # this part is weird but necessary, because 'TRAC[1|2]:DATA? ..' returns '' if length is no multiple of 64. The try clause succeeds, still there is an error in the awg error memory.
            if errors != '':
                raise Exception('Errors occurred while querying AWG:\n' + errors)
            else:
                return res
        except Exception as inst:
            errors = self.errors
            if errors != '':
                raise Exception('Errors occurred while querying AWG:\n' + errors)
            else:
                raise inst

    ####################################################################################################################
    # ARM/TRIGger Subsystem
    ####################################################################################################################
    @property
    def run(self):
        return False if int(self.query('STAT:OPER:RUN:COND?')) == 0 else True

    @run.setter
    def run(self, val):
        self.ch[1].run = val
        if not self.channels_coupled:
            self.ch[2].run = val

    @property
    def trigger_input_threshold_level_limits(self):
        return {'min': float(self.query('ARM:TRIG:LEV? MIN')), 'max': float(self.query('ARM:TRIG:LEV? MAX'))}

    @property
    def trigger_input_threshold_level(self):
        return float(self.query("ARM:TRIG:LEV?"))

    @trigger_input_threshold_level.setter
    def trigger_input_threshold_level(self, value):
        self.write("ARM:TRIG:LEV {}".format(value))

    @property
    def trigger_input_impedance(self):
        return self.query('ARM:TRIG:IMP?')

    @trigger_input_impedance.setter
    def trigger_input_impedance(self, value):
        self.write('ARM:TRIG:IMP {}'.format(value))

    @property
    def trigger_input_slope(self):
        """
        Set or query the trigger input slope.
        POSitive - rising edge
        NEGative - falling edge
        EITHer - both
        :return:
        """
        return self.query('ARM:TRIG:SLOP?')

    @trigger_input_slope.setter
    def trigger_input_slope(self, value):
        self.write('ARM:TRIG:SLOP {}'.format(value))

    @property
    def trigger_source(self):
        """
        'EXT' or 'INT'
        :return:
        """
        return self.query('ARM:TRIG:SOUR?')

    @trigger_source.setter
    def trigger_source(self, value):
        self.write('ARM:TRIG:SOUR {}'.format(value))

    @property
    def internal_trigger_frequency_limits(self):
        return {'min': float(self.query('ARM:TRIG:FREQ? MIN')), 'max': float(self.query('ARM:TRIG:FREQ? MAX'))}
    @property
    def internal_trigger_frequency(self):
        return float(self.query('ARM:TRIG:FREQ?'))

    @internal_trigger_frequency.setter
    def internal_trigger_frequency(self, value):
        self.write('ARM:TRIG:FREQ {}'.format(value))

    @property
    def event_input_threshold_level_limits(self):
        return {'min': float(self.query('ARM:EVEN:LEV? MIN')), 'max': float(self.query('ARM:TRIG:LEV? MAX'))}

    @property
    def event_input_threshold_level(self):
        return float(self.query("ARM:EVEN:LEV?"))

    @event_input_threshold_level.setter
    def event_input_threshold_level(self, value):
        self.write("ARM:EVEN:LEV {}".format(value))

    @property
    def event_input_impedance(self):
        return float(self.query('ARM:EVEN:IMP?'))

    @event_input_impedance.setter
    def event_input_impedance(self, value):
        self.write('ARM:EVEN:IMP {}'.format(value))

    @property
    def event_input_slope(self):
        """
        Set or query the trigger input slope.
        POSitive - rising edge
        NEGative - falling edge
        EITHer - both
        :return:
        """
        return self.query('ARM:EVEN:SLOP?')

    @event_input_slope.setter
    def event_input_slope(self, value):
        self.write('ARM:EVEN:SLOP {}'.format(value))

    @property
    def enable_event_source(self):
        """
        'TRIG' or 'EVEN'
        :return:
        """
        return self.query('TRIG:SOUR:ENAB?')

    @enable_event_source.setter
    def enable_event_source(self, value):
        self.write('TRIG:SOUR:ENAB {}'.format(value))

    @property
    def advancement_event_source(self):
        """
        'TRIG', 'EVEN', 'INT'
        :return:
        """
        return self.query('TRIG:SOUR:ADV?')

    @advancement_event_source.setter
    def advancement_event_source(self, value):
        self.write('TRIG:SOUR:ADV {}'.format(value))

    @property
    def external_sample_frequency_limits(self):
        """sample frequency [GHz]. """
        return {'min': float(self.query('FREQ:RAST:EXT? MIN')) / 1e9, 'max': float(self.query('FREQ:RAST:EXT? MAX')) / 1e9}

    @property
    def external_sample_frequency(self):
        """sample frequency [GHz]. """
        return float(self.query('FREQ:RAST:EXT?')) / 1e9

    @external_sample_frequency.setter
    def external_sample_frequency(self, value):
        self.write('FREQ:RAST:EXT {}'.format(value*1e9))

    @property
    def internal_sample_frequency_limits(self):
        """sample frequency [GHz]. """
        return {'min': float(self.query('FREQ:RAST? MIN')) / 1e9, 'max': float(self.query('FREQ:RAST? MAX')) / 1e9}

    @property
    def internal_sample_frequency(self):
        """sample frequency [GHz]. """
        return float(self.query('FREQ:RAST?')) / 1e9

    @internal_sample_frequency.setter
    def internal_sample_frequency(self, value):
        self.write('FREQ:RAST {}'.format(value*1e9))

    @property
    def sample_clock_output_source(self):
        return self.query('OUTP:SCLK:SOUR?')

    @sample_clock_output_source.setter
    def sample_clock_output_source(self, value):
        self.write('OUTP:SCLK:SOUR {}'.format(value))

    @property
    def reference_clock_source(self):
        return self.query('ROSC:SOUR?')

    @reference_clock_source.setter
    def reference_clock_source(self, value):
        self.write('ROSC:SOUR {}'.format(value))

    def send_enable_event(self):
        if not self.channels_coupled:
            raise Exception('Invalid command when channels not coupled')
        else:
            self.ch[1].send_enable_event()

    @property
    def gate_open(self):
        if not self.channels_coupled:
            raise Exception('Invalid command when channels not coupled')
        else:
            return int(self.ch[1].gate_open)

    @gate_open.setter
    def gate_open(self, value):
        if not self.channels_coupled:
            raise Exception('Invalid command when channels not coupled')
        else:
            self.ch[1].gate_open = value

    def send_advancement_event(self):
        if not self.channels_coupled:
            raise Exception('Invalid command when channels not coupled')
        else:
            self.ch[1].send_advancement_event()

    def send_begin(self):
        if not self.channels_coupled:
            raise Exception('Invalid command when channels not coupled')
        else:
            self.ch[1].send_begin()

    @property
    def current_settings(self):
        return self.query('SYST:SET?')

    @current_settings.setter
    def current_settings(self, val):
        self.write_raw('SYST:SET {}'.format(val))

    __SETTINGS_FOLDER__ = 'C:\\src\\qudi\\hardware\\awg\\awg_settings'

    def dump_settings_to_file(self, settings):

        if not os.path.isdir(self.__SETTINGS_FOLDER__):
            os.mkdir(self.__SETTINGS_FOLDER__)
        fp = '{}/{}_current_{}_settings'.format(self.__SETTINGS_FOLDER__, datetime.datetime.now().strftime('%Y%m%d-h%Hm%Ms%S'), self.name)
        with open(fp, "w") as f:
            f.write(self.current_settings)

    def dump_current_settings_to_file(self):
        self.dump_settings_to_file(self.current_settings)

    def load_settings_from_file(self, filepath=None):
        if filepath is None:
            file_list = sorted(os.listdir((self.__SETTINGS_FOLDER__)))
            for fn in file_list:
                if self.name not in fn:
                    file_list.remove(fn)
                    continue
                try:
                    file_date = datetime.datetime.strptime(fn[0:8], '%Y%m%d')
                except:
                    file_list.remove(fn)
                    continue
            filepath = '{}/{}'.format(self.__SETTINGS_FOLDER__, file_list[-1])
        with open(filepath, "r") as f:
            return f.read()

    def restore_settings_from_file(self, filepath=None):
        self.current_settings = self.load_settings_from_file(filepath)

    ####################################################################################################################
    # FORMat Subsystem
    ####################################################################################################################

    @property
    def byte_order(self):
        """
        Controls whether binary data is transferred in normal ("big endian") or swapped ("little endian") byte order.
        possible values: 'NORM', 'SWAP'
        'NORM': Big-endian
        'SWAP': little endian (windows standard)

        """
        return self.query("FORM:BORD?")

    @byte_order.setter
    def byte_order(self, value):
        self.write("FORM:BORD {}".format(value))

    ####################################################################################################################
    # INSTrument Subsystem
    ###################################################################################################################

    @property
    def channels_coupled(self):
        return int(self.query('INST:COUP:STAT?'))

    @channels_coupled.setter
    def channels_coupled(self, value):
        self.write('INST:COUP:STAT {}'.format(value))

    # Miscellaneous
    def rst(self):
        """
        reset the device to factory defaults
        """
        self.write('*RST')

    @property
    def is_ready(self):
        return int( self.query('*OPC?'))

    ######################################################################################################################
    # STATus Subsystem
    #####################################################################################################################
    @property
    def status_byte(self):
        stb = [bool(int(i)) for i in format(int(bin(int(self.query('*STB?')))[2:]), '08d')[::-1]]
        return dict(error_queue = stb[2], questionable_data = stb[3], message_available = stb[4], standard_event=stb[5], master_summary=stb[6], operational_data =stb[7])

if __name__ == '__main__':

    a = AWG(address='TCPIP0::192.168.0.2::hislip0::INSTR', name = 'awg')
    #a = AWG(address='TCPIP0::localhost::inst1::INSTR')
    print('Hello!')