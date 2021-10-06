import numpy as np
import pyvisa
from collections import OrderedDict
from core.configoption import ConfigOption
from core.module import Base
import os  
class DTG(Base):
    visa_address = ConfigOption('visa_address', missing='error')
    channels = ConfigOption('channels', missing='error')
    #ConfigOption('channel', missing='error')
    trigger_channel = ConfigOption('trigger_channel', missing='error')
    
    def on_activate(self):
        self.channel = self.channels[0]
        rm = pyvisa.ResourceManager()
        self.dtg = rm.open_resource(self.visa_address)
        self.current_block = 'Block1'
        self.current_sequence = []
        self.outputs_ON()

    def on_deactivate(self):
        self.outputs_OFF()

    def outputs_ON(self):
        self.dtg.write('OUTP:STAT:ALL ON;*WAI')
        # return self.dtg.query('is OK?')
    def outputs_OFF(self):
        self.dtg.write('OUTP:STAT:ALL OFF;*WAI')
        # return self.dtg.query('is OK?')
    def run_dtg(self):
        # self.dtg.write('OUTP:STAT:ALL ON;*WAI')
        self.dtg.write('TBAS:RUN ON')
        state = 0 if int(self.dtg.query('TBAS:RUN?')) == 1 else -1
        return state

    def stop_dtg(self):
        # self.dtg.write('OUTP:STAT:ALL OFF;*WAI')
        self.dtg.write('TBAS:RUN OFF')
        state = 0 if int(self.dtg.query('TBAS:RUN?')) == 0 else -1
        return state

    def new_block(self, length, nameBlock='Block1'):
        self.stop_dtg()
        block_length = int(self.dtg.query('BLOC:LENG? "{0}"'.format(nameBlock)))
        if nameBlock=='Block1':
            self.dtg.write('BLOC:DEL "{0}"'.format(nameBlock))
            print('Deleted', self.dtg.query('*OPC?'))

        self.dtg.write('BLOC:NEW "{0}", {1}'.format(nameBlock, length))
        self.dtg.query('*OPC?')
        self.dtg.write('BLOC:SEL "{0}"'.format(nameBlock))
        self.dtg.query('*OPC?')
        return self.dtg.query('*OPC?')

    def select_block(self, nameBlock):
        self.dtg.write('BLOC:SEL "{0}"'.format(nameBlock))
        self.dtg.query('*OPC?')
        return self.dtg.query('*OPC?')

    def get_frequency(self):
        return float(self.dtg.query('TBAS:FREQ?'))

    def set_frequency(self, sample_rate):
        self.dtg.write('TBAS:FREQ {0:e}'.format(sample_rate))
        return self.get_sample_rate()

    def set_channel_binary(self, channel, data):
        c = channel
        max_blocksize = 8 * 800
        dlen = len(data)
        written = 0
        start = 0

        # when there is more than 1MB of data to transfer, split it up
        while dlen >= max_blocksize - 8:
            end = start + max_blocksize
            bytestr = np.packbits(np.fliplr(np.reshape(data[start:end], (-1, 8))))
            # print(channel, '->', c, 'start', start, 'end', end, 'len', dlen, 'packed', len(bytestr))
            #print(bytestr)
            self.dtg.write_binary_values(
                'PGEN{0}:CH{1}:BDATA {2},{3},'.format(c[0], c[1], start, end - start),
                bytestr,
                datatype='B'
            )
            written += end - start
            dlen -= end - start
            start = end

        end = start + dlen
        if dlen > 0:
            to_pad = 8 - dlen % 8 if dlen % 8 != 0 else 0

            padded_bytes = np.packbits(
                np.fliplr(
                    np.reshape(
                        np.pad(data[start:end], (0, to_pad), 'constant'),
                        (-1, 8)
                    )
                )
            )
            #print(padded_bytes)
            # print(channel, '-->', c, 'start', start, 'end', end,
            #       'len', dlen, 'padded', len(padded_bytes))
            self.dtg.write_binary_values(
                'PGEN{0}:CH{1}:BDATA {2},{3},'.format(c[0], c[1], start, end - start),
                padded_bytes,
                datatype='B'
            )
            written += end - start
        return written

    def set_channel_with_trig(self, sequence, channel=['A', 1], trigger = ['A', 2]):
        self.set_channel_binary(sequence, channel)
        self.set_channel_binary(sequence, trigger)


        #!DTG commands:
    def get_short_pulse_seq(self, pulse_len, pulse_sep):
        block_len = pulse_len + pulse_sep
        if block_len < 1000:
            pad = 0
            r = 1000//block_len
            block = block_len*r
            while block % 100 != 0:
                pad += 1
                block = (r*(block_len + pad))
        sequence = list(np.concatenate((np.ones(pulse_len, dtype=int), np.zeros(pulse_sep + pad, dtype=int))))
        reprate = block//(len(sequence))
        trigZeros = np.zeros(len(sequence), dtype=int)
        trigZeros[0:5] = np.ones(5)
        trigSeq = list(list(trigZeros) * reprate)
        sequence = sequence*reprate #MAKE SEQUENCE LONGER THAN 1000 to be read by DTG
        return sequence, trigSeq


    def get_from_file_seq(self, filename, returnTrigForAll=False):
        """
        File format:
        csv with ',' as a delimeter
        pulse length     ->     10
        pulse separation ->     -10
        So the file looks like this:
        10, -10, 10, -10
        This would give a block of two pulses 10 ns with 10 ns waiting time in between the pulses
        """
        print(filename)
        os.chdir('pulse_sequences')
        if 'seq.csv' in filename:
            file_data = np.genfromtxt(filename, delimiter=',')
            os.chdir('..')
            sequence = np.zeros(np.sum(np.abs(file_data).astype(int)))
            trig_all = np.zeros(len(sequence))
            start=0
            for i in file_data:
                seq = np.ones(abs(int(i))) if i>0 else np.zeros(abs(int(i)))
                sequence[start:int(np.abs(i) + start)] = seq
                trig_all[start] = 1 if i>0 else 0
                start = int(np.abs(i)) + start
                
            
            block_len = len(sequence)
            if block_len < 1000:
                pad = 0
                r = 1000//block_len
                block = block_len*r
                while block % 100 != 0:
                    pad += 1
                    block = (r*(block_len + pad))
                sequence = list(np.concatenate((sequence, np.zeros(pad, dtype=int))).astype(int))
                reprate = block//(len(sequence))
                trigZeros = np.zeros(len(sequence), dtype=int)
                trigZeros[0:5] = np.ones(5)
                trigSeq = list(list(trigZeros) * reprate)
                sequence = sequence*reprate #MAKE SEQUENCE LONGER THAN 1000 to be read by DTG
            else:
                r = len(sequence)//100
                pad = 100 * (r + 1) - len(sequence)
                sequence = list(np.concatenate((sequence, np.zeros(pad, dtype=int))).astype(int))
                trigSeq = list(np.zeros(len(sequence), dtype=int))
                trigSeq[0:5] = np.ones(5)
            if returnTrigForAll:
                return sequence, trigSeq, trig_all
            else:
                return sequence, trigSeq
        else:
            print('UPSIE the sequence file has to end on seq.csv !!!')
        

    def write_sequence(self, sequence, trigger = None):
        self.new_block(len(sequence))
        self.block_length = int(self.dtg.query('BLOC:LENG? "{0}"'.format('Block1')))
        self.set_channel_binary(self.channel, sequence)
        if trigger is not None:
            self.set_channel_binary(self.trigger_channel, trigger)
    
    def compose_pulsed_sequence(self, pulse_length, pulse_separation):
        sequence, trig = self.get_short_pulse_seq(pulse_length, pulse_separation)
        return sequence, trig