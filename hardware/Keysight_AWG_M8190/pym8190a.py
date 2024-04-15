from __future__ import print_function, absolute_import, division

__metaclass__ = type

import numpy as np
import collections
import sys
import itertools
import traceback
import logging
import time
import threading
from core.module import Base #, ConfigOption
from core.configoption import ConfigOption



from . import hardware
from .elements import Sequence, SequenceStep, SequenceStepReuseSegment, WaveStep, __BLM__
from . import util
from . import settings

from interface.mcas_interface import McasDictHolderInterface

class mcas_dict_holder(Base, McasDictHolderInterface):
    def on_activate(self):
        self.mcas_dict = MultiChSeqDict(debug_mode=False)
        self.mcas = MultiChSeq
        self.settings=settings
        return 
    
    def on_deactivate(self):
        del self.mcas_dict
        return 

class MultiChSeqDict(collections.OrderedDict):

    def __init__(self, debug_mode=False, restore_awg_settings=settings.restore_awg_settings):
        super(MultiChSeqDict, self).__init__()
        self.debug_mode = debug_mode  # completely stops interaction with the awg

        self.connect_to_awgs(restore_awg_settings=restore_awg_settings)
        self.set_wait()

    @property
    def debug_mode(self):
        return self._debug_mode

    @debug_mode.setter
    def debug_mode(self, val):
        if not hasattr(self, '_debug_mode') or self._debug_mode != util.check_type(val, 'debug_mode', bool):
            self._debug_mode = val
            if val is True:
                logging.getLogger().info("mcas_dict set to debug_mode {}".format(self.debug_mode))
            written_list = [val.written for val in self.values()]
            if val is True and not all(written_list):
                self.rewrite_keys_awg_memory(keys=[k for k in list(self.keys())[written_list.index(False):]])

    def connect_to_awgs(self, restore_awg_settings, notify=True):
        if not self.debug_mode:
            t0 = time.time()
            def get_awg(awgs, name):
                if 'ps' in name:
                    ch_map = dict()
                    for channels,value in settings.marker_alias.items():
                        if 'ps' in value:
                            ch_map[channels] = int(value[3])

                    out = hardware.PulseStreamerPGProxy(channel_map=ch_map,ip=settings.awg_instrument_adress[name])
                else:
                    out = hardware.AWG(settings.awg_instrument_adress[name], name, channel_numbers=settings.ch_dict_full[name])
                    out.run = False
                    if restore_awg_settings:
                        out.restore_settings_from_file()
                    out.clear_memories()
                awgs[name] = out

            tl = []
            self.awgs = collections.OrderedDict()
            for name in settings.ch_dict_full.keys():
                tl.append(threading.Thread(target=get_awg, args=(self.awgs, name)))
                tl[-1].start()
            for t in tl:
                t.join()
            if notify:
                logging.getLogger().info("Connected to awgs {} in {}s".format(settings.ch_dict_full.keys(), time.time()-t0))
        elif notify:
            logging.getLogger().info("Debug mode! Did not connect to awgs {}".format(settings.ch_dict_full.keys()))

    def stop_awgs(self):
        if not self.debug_mode:
            stop_awgs(self.awgs)

    def set_wait(self):
        mcas = MultiChSeq(name='wait', ch_dict=settings.ch_dict_awgs)
        mcas.start_new_segment('wait')
        mcas.asc(length_smpl=320)
        mcas.status = 1

        self['wait'] = mcas


    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        if not isinstance(key, str):
            raise TypeError("key must be type str but is {} ({})".format(key, type(key)))
        if key != value.name:
            raise TypeError("Not allowed: {}, {}, probably you need to have the same namefor the mcas and the name you try to atibute to the mcas_dict".format(key, MultiChSeq, type(value)))
        if key in self:
            del self[key]
        if value.written:
            raise Exception('Error: Sequence has already been written and can not be added.')

        value.mcas_dict = self
        if value.status == 0 and not self.debug_mode:
            value.finalize()
        if not self.debug_mode:
            value.write_to_awg_memory(notify=True) # longest part
        collections.OrderedDict.__setitem__(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        didx = list(self.keys()).index(key)
        delete_keys = [k for k in list(self.keys())[didx:]]
        self.delete_keys_from_awg_memory(delete_keys)
        del self[key].mcas_dict
        collections.OrderedDict.__delitem__(self, key)
        self.write_keys_to_awg_memory(delete_keys[1:])

    def rewrite_keys_awg_memory(self, keys):
        self.delete_keys_from_awg_memory(keys)
        self.write_keys_to_awg_memory(keys)

    def delete_keys_from_awg_memory(self, keys):
        for key in keys[::-1]:
            if self[key].written:
                self[key].delete_from_awg_memory()

    def write_keys_to_awg_memory(self, keys):
        if not self.debug_mode:
            for key in keys:
                self[key].write_to_awg_memory(notify=True)

    def dl(self, key, *args, **kwargs):
        return self[key].dl(*args, **kwargs)

    @property
    def info(self):
        return "\n".join(["{}, {}".format(key, val.ch_dict) for key, val in self.items()])

    def __repr__(self):
        return self.info

    def __str__(self):
        return self.info

    def print_info(self):
        print(self.info)

class MultiChSeq:
    def __init__(self, ch_dict=None, **kwargs):
        self.name = kwargs.get('name', kwargs.get('seq_name'))
        
        # print('ch_dict in MultiChSeq init: ',ch_dict)
        self.ch_dict = valid_ch_dict(settings.ch_dict_full if ch_dict is None else ch_dict)
        self.init_sequences()
        self.status = 0
        print("MCAS initialized")
        

    name = util.ret_property_typecheck('name', str)

    def init_sequences(self):
        t1 = time.time()
        # TODO: create a PS sequence also, whcih could be assembled later in asc, startnew segment.
        self.sequences = {}

        for awg_str, chl in self.ch_dict.items():
            self.sequences[awg_str] = dict([[ch, Sequence(name=self.name)] for ch in chl])
            if awg_str == 'ps':
                self.sequences[awg_str] = {1:[([],settings.slave_start_delay)]}
        #print("hardware/pym8190; init_sequences", time.time()-t1)

    def dl(self, awg, ch, sequence_step_num=None, wave_step_num=None):
        out = self.sequences[awg][ch]
        if sequence_step_num is not None:
            out = out.dl(sequence_step_num, wave_step_num)
        return out

    @property
    def written(self):
        return getattr(self, '_written', False)

    @written.setter
    def written(self, val):
        self._written = val

    @property
    def length_mus(self):
        try:
            ret = self.sequences.values()[0].values()[0].length_mus
        except Exception as e:
            #print(e)
            ret = self.sequences['2g'][1].length_mus
        return ret

    def asc(self, **kwargs):
        self.add_step_complete(**kwargs)

    def add_step_complete(self, **kwargs):
        pd = {}
        for awg_str, chl in self.ch_dict.items():
            pd[awg_str] = {}
            for ch in chl:
                pd[awg_str][ch] = kwargs.pop('pd' + awg_str + str(ch), {})
        for key in [k for k in kwargs if k in settings.marker_alias]:
            awg_str, ch, marker_name, _ = settings.marker_alias[key]
            pd[awg_str][ch][marker_name + '_marker'] = kwargs.pop(key)
        self.add_step(pd=pd, **kwargs)

    def step_length_mus(self, pd, length_mus):
        lml = []
        if length_mus is not None:
            lml.append(length_mus)
        for awg_str in pd.keys():
            for ch in pd[awg_str].keys():
                if pd[awg_str][ch].get('type', 'wait') in ['robust']:
                    lml.append(WaveStep(**pd[awg_str][ch]).length_mus)
                elif 'length_mus' in pd[awg_str][ch]:
                    lml.append(pd[awg_str][ch]['length_mus'])
        if len(lml) == 0:
            return 0.0
        else:
            for i in lml:
                if abs(i - lml[0]) > 0.1 * (1e-9 * 1e6):
                    raise Exception('The steps for different channels must have same length')
            else:
                return lml[0]

    def add_step(self, pd=None, name='', length_mus=None, ssi=None, wsi=None, **kwargs):
        if self.status != 0:
            raise Exception('Error: MCAS {} is in state {} and can not be changed anmyore.'.format(self.name, self.status))
        if pd is None:
            pd = {}
        length_mus = self.step_length_mus(pd, length_mus=length_mus)
        ## Strange convertion but seems it is only related to optimal pulses.
        for awg_str, chl in self.ch_dict.items():
            if awg_str not in pd:
                pd[awg_str] = {}
            for ch in chl:
                if ch not in pd[awg_str]:
                    pd[awg_str][ch] = {}
                if not pd[awg_str].get('type', 'wait') in ['robust']:
                    pd[awg_str][ch].update(length_mus=length_mus)
                if 'name' not in pd[awg_str][ch]:
                    pd[awg_str][ch].update(name=name)
                pd[awg_str][ch].update(**kwargs)
                if awg_str is not 'ps':
                    if len(self.sequences[awg_str][ch].data_list) == 0:
                        raise Exception('There is no segment to append to. Start a new one first.')
                    elif ssi is None:
                        ssi = len(self.sequences[awg_str][ch].data_list) - 1
                    elif ssi > len(self.sequences[awg_str][ch].data_list) - 1:
                        raise Exception('Error: selected SequenceStep too big ({}, {}). '.format(ssi, len(self.sequences[awg_str][ch].data_list)))
                    wsi = len(self.sequences[awg_str][ch].data_list[ssi].data_list) if wsi is None else wsi
                    if wsi > (len(self.sequences[awg_str][ch].data_list[ssi].data_list)):
                        raise Exception('THIS PROBABLY IS NOT GOOD, PLEASE CHECK!')
                    self.sequences[awg_str][ch].data_list[ssi].data_list.insert(wsi, WaveStep(**pd[awg_str][ch]))
                else: #if awg is ps
                    # print('pd[awg_str][ch].keys() ',pd[awg_str][ch].keys())
                    # print('pd[awg_str][ch] ',pd[awg_str][ch])
                    # print ('next line ',[marker[0:-7] for marker in pd[awg_str][ch].keys() if 'marker' in marker])
                    self.sequences[awg_str][ch].append(([marker[0:-7] for marker in pd[awg_str][ch].keys() if 'marker' in marker and
                                                         pd[awg_str][ch][marker] == True
                                                         ],1000*length_mus))

    def start_new_segment(self, name='', reuse_segment=False, **kwargs):
        for awg_str, chl in self.ch_dict.items():
            for ch in chl:
                if awg_str is 'ps':
                    if 'loop_count' in kwargs.keys():
                        self.sequences[awg_str][ch].append((kwargs['loop_count'],))
                    else:
                        self.sequences[awg_str][ch].append((1,))
                else:
                    if reuse_segment:
                        for idx, step in enumerate(self.sequences[awg_str][ch].data_list):
                            if step.name == name:
                                self.sequences[awg_str][ch].data_list.append(SequenceStepReuseSegment(name=name, reused_sequence_step=step, **kwargs))
                                break
                        else:
                            self.sequences[awg_str][ch].data_list.append(SequenceStep(name=name, **kwargs))
                            print('Warning: reuse_segment was set for {} but no previously defined segment was found. reuse_segment was set to False'.format(name))
                    else:
                        self.sequences[awg_str][ch].data_list.append(SequenceStep(name=name, **kwargs))

    def set_master_trigger_settings(self):
        # print('I am setting master trigger settings settings.master_awg: ',settings.master_awg)
        for awg_str, chl in self.ch_dict.items():
            if awg_str == settings.master_awg:
                for ch in chl:
                    trigger_sync_marker = True if ch == settings.master_trigger_channel else False
                    trigger_step = SequenceStep(name='triggerwait')
                    trigger_step.data_list.append(WaveStep(name='trigger', length_mus=settings.trigger_length_mus, sync_marker=trigger_sync_marker))
                    trigger_step.data_list.append(WaveStep(name='waittrigger', length_mus=settings.trigger_delay_length_mus - settings.trigger_length_mus))
                    w_trig_safety_step = SequenceStep(name='w_trig_safety', data_list=[WaveStep(name='w_trig_safety', length_mus=settings.slave_trigger_safety_length_mus)])
                    self.sequences[awg_str][ch].data_list = [trigger_step] + self.sequences[awg_str][ch].data_list + [w_trig_safety_step]

    def set_slave_trigger_settings(self):
        # print('I am setting slave trigger settings self.ch_dict.items(): ', self.ch_dict.items())
        
        for awg_str, chl in self.ch_dict.items():
            if awg_str != settings.master_awg and 'ps' in awg_str:
                # print('I am setting slave trigger settings awg_str: ', awg_str)
                self.mcas_dict.awgs[awg_str].proxy.setTrigger('HARDWARE_RISING')
                #
                # for ch in chl:
                #     print('ch ', ch)
                #
                #     wait_trigger_step = SequenceStep(data_list=[WaveStep(length_mus=0.0, name='w_trig_step')], advance_mode='SING')
                #     print('wait_trigger_step ', wait_trigger_step)
                #     print('TYPE wait_trigger_step ', type(wait_trigger_step))
                #     print('self.sequences ',self.sequences)
                #     print('self.sequences[awg_str] ',self.sequences[awg_str])
                #     print('self.sequences[awg_str][ch] ',self.sequences[awg_str][ch])
                #     self.sequences[awg_str][ch].data_list = self.sequences[awg_str][ch].data_list + [wait_trigger_step]

    def finalize(self, ignore_max_avg_power=False, notify=True):
        # print('finalize settings.master_awg ',settings.master_awg)
        # print('self.ch_dict ',self.ch_dict)
        if self.status != 0:
            raise Exception('Error: MCAS {} has already been finalized'.format(self.name))
        self.fix_avg_rf_power(ignore_max_avg_power=ignore_max_avg_power)
        # print('finalize 2')
        if settings.master_awg is not None and settings.master_awg in self.ch_dict and len(self.ch_dict) > 1:
            # print('finalize 3')

            self.set_master_trigger_settings()
            # print('finalize 4')

            self.set_slave_trigger_settings()
            # print('finalize 5')

        self.status = 1
        if notify:
            pass#logging.getLogger().info("MCAS '{}' finalized ({} s).".format(self.name, time.time() - t0))

    def fix_avg_rf_power(self, ignore_max_avg_power=False):
        awtd = {}
        for awg_str, l in settings.max_sine_avg_power.items():
            awtd[awg_str] = {}
            for ch, max_avg_power in l.items():
                if max_avg_power is not None and ch in self.ch_dict.get(awg_str, []):
                    awtd[awg_str][ch] = self.additional_wait_time(awg_str, ch, max_avg_power, ignore_max_avg_power=ignore_max_avg_power)

            if all([i == 0 for i in flatten_dict_dict(awtd)]):
                return
            self.start_new_segment(name='rf_power_safety', loop_count=int(np.ceil(max(flatten_dict_dict(awtd)) / __BLM__)))
            self.asc(length_mus=__BLM__)
            for awg_str, l in settings.max_sine_avg_power.items():
                for ch, max_avg_power in l.items():
                    if max_avg_power is not None and ch in self.ch_dict.get(awg_str, []):
                        if settings.amplifier_power[awg_str][ch] * self.sequences[awg_str][ch].normalized_avg_sine_power / max_avg_power > 1.1 and not ignore_max_avg_power:
                            raise Exception(' Additional wait time added, but power still too high on awg {} ch {}! Sequence {} is {} mus long '
                                            'and has an average rf-power of {} W (maximally allowed: {} W) after adding an additional '
                                            'waiting time of {} mus'.format(awg_str, ch, self.name,
                                                                            self.sequences[awg_str][ch].length_mus,
                                                                            settings.amplifier_power[awg_str][ch] * self.sequences[awg_str][ch].normalized_avg_sine_power,
                                                                            self.max_avg_power,
                                                                            awtd[awg_str][ch]))

    def additional_wait_time(self, awg_str, ch, max_avg_power, ignore_max_avg_power=False):
        if ignore_max_avg_power:
            return 0
        else:
            return check_avg_rf_power(self.sequences[awg_str][ch], awg_str=awg_str, ch=ch, max_avg_power=max_avg_power)

    def precompile_samples_waveform(self, notify=True):
        if self.status != 1:
            raise Exception('Error: MCAS {} has already been precompiled'.format(self.name))
        t0 = time.time()
        for awg_str, chl in self.ch_dict.items():
            for ch in chl:
                self.sequences[awg_str][ch].precompile_samples_waveform(0, notify=False)
        self.status = 2
        if notify:
            logging.getLogger().info("MCAS '{}' precompiled ({} s).".format(self.name, time.time() - t0))

    def write_seq(self, notify=True):
        self.finalize(notify=notify)
        self.precompile_samples_waveform(notify=notify)

    def write_to_awg_memory(self, ignore_max_avg_power=False, abort=None, notify=True):
        # check this function
        if not ignore_max_avg_power:
            for awg_str, l in settings.max_sine_avg_power.items():
                for ch, max_avg_power in l.items():
                    if max_avg_power is not None and ch in self.ch_dict.get(awg_str, []):
                        if check_avg_rf_power(self.dl(awg_str, ch), awg_str, ch, max_avg_power, notify=True) != 0:
                            raise Exception('Average rf power too high')
        time_dict = {}
        for awg_str in self.ch_dict.keys():
            if 'ps' not in awg_str:
                for ch, sequence in self.sequences[awg_str].items():
                    if abort is not None and abort.is_set(): break
                    try:
                        t0 = time.time()
                        self.mcas_dict.awgs[awg_str].ch[ch].write_sequence(sequence=sequence, sample_offset=0)
                        time_dict[awg_str + str(ch)] = float("{:.4f}".format(time.time() - t0))
                    except:
                        exc_type, exc_value, exc_tb = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_tb)
                        raise Exception('awg {} ch {} could not write sequence {} to memory.'.format(awg_str, ch, self.name))
        if notify:
            pass
            #logging.getLogger().info('mcas {} has been written: {}'.format(self.name, time_dict))
        self.written = True

    def delete_from_awg_memory(self):
        for awg_str in self.ch_dict.keys():
            if 'ps' not in awg_str:
                for ch, sequence in self.sequences[awg_str].items():
                    self.mcas_dict.awgs[awg_str].ch[ch].delete_sequence(sequence=sequence)
        self.written = False

    def initialize(self):

        for awg_str, chl in settings.ch_dict_full.items():
            for ch in chl:

                if awg_str is 'ps':
                    if awg_str in self.ch_dict: 
                        sequence = self.sequences[awg_str][ch] # In green md there is no awg_str == ps.
                        sequence = self.mcas_dict.awgs[awg_str].unwrap_sequence(sequence)
                        #self.sequence = sequence #UNFUG
                        #print(self.sequence) #UNFUG
                        self.mcas_dict.awgs[awg_str].setSequence(sequence, triggered=True,
                                                                 run=False, loops = 1) ## This have to be implemented now
                else:
                    if ch in self.ch_dict.get(awg_str, []):
                        sequence = self.sequences[awg_str][ch]
                        #self.sequence_awg = sequence #UNFUG
                        #print(awg_str, ch)
                        #print(self.sequence_awg) #UNFUG
                    else:
                        sequence = self.mcas_dict['wait'].sequences[awg_str][ch]
                    self.mcas_dict.awgs[awg_str].ch[ch].initialize_sequence(sequence)

    def start_awgs(self, trigger=True):
        start_awgs(awgs=self.mcas_dict.awgs, ch_dict=self.ch_dict, trigger=trigger)

    def run(self, trigger=True):
        self.initialize()
        self.start_awgs(trigger=trigger)



def valid_ch_dict(ch_dict):
    # print('valid_ch_dict ch_dict',ch_dict)
    if len(ch_dict) > 1:
        if settings.master_awg is None or settings.master_trigger_channel is None:
            raise Exception('No settings.master_awg and settings.master_trigger_channel must be given when multiple awgs are used. If you own the synchronization module, changes to the code need to be made.')
        if not settings.master_awg in ch_dict or not settings.master_trigger_channel in ch_dict[settings.master_awg]:
            raise Exception('No settings.master_awg and settings.master_trigger_channel must be in ch_dict when multiple awgs are used.')
    return ch_dict

def check_avg_rf_power(sequence, awg_str, ch, max_avg_power=None, notify=True):
    avg_power = settings.amplifier_power[awg_str][ch] * sequence.normalized_avg_sine_power
    additional_wait_time = max(0, sequence.length_mus * (avg_power / max_avg_power - 1))
    if notify:
        logging.getLogger().info("avg_power {:.2f} W,max_avg_power: {} W, additional_wait_time: {} mus".format(avg_power, max_avg_power, additional_wait_time))
    return additional_wait_time

def send_trigger(awgs, ch_dict=None):
    ch_dict = settings.ch_dict_full if ch_dict is None else ch_dict
    awg_str = list(ch_dict.keys())[0] if len(ch_dict) == 1 else settings.master_awg
    awgs[awg_str].send_begin()

def set_outputs(awgs, ch_dict=None):
    ch_dict = settings.ch_dict_full if ch_dict is None else ch_dict
    for awg_str, chl in settings.ch_dict_full.items():
        for ch in chl:
            if 'ps' not in awg_str:
                awgs[awg_str].ch[ch].output = 1 if ch in ch_dict.get(awg_str, []) else 0

def start_awgs(awgs, ch_dict=None, trigger=True):
    ch_dict = settings.ch_dict_full if ch_dict is None else ch_dict
    for awg_str, channels in ch_dict.items():
        awgs[awg_str].run = True
    set_outputs(awgs, ch_dict=ch_dict)
    if trigger:
        send_trigger(ch_dict=ch_dict, awgs=awgs)

def stop_awgs(awgs, ch_dict=None):
    ch_dict = settings.ch_dict_full if ch_dict is None else ch_dict
    for awg_str, channels in ch_dict.items():
        awgs[awg_str].run = False

def update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

def flatten_dict_dict(dd):
    return list(itertools.chain(*[i.values() for i in dd.values()]))




if __name__ == '__main__':
    import pym8190a
    md = pym8190a.pym8190a.MultiChSeqDict()
    md.stop_awgs()

    #     s = pym8190a.pym8190a.MultiChSeq(seq_name='test', ch_dict={'128m': [2]})
    #     s.start_new_segment('s1')
    #     s.asc(length_mus=400, pd128m2=dict(type='constant', constant_value=.1))
    #     s.asc(length_mus=400, pd128m2=dict(type='wait', frequencies=[2.5], amplitudes=[.8]))
    #     s.asc(length_mus=400, pd128m2=dict(type='constant', constant_value=-.1))


    s = pym8190a.pym8190a.MultiChSeq(seq_name='test', ch_dict={'2g': [1,2]})
    s.start_new_segment('s1')
    s.asc(length_mus=400, pd128m2=dict(type='constant', constant_value=.1))
    s.asc(length_mus=400, pd128m2=dict(type='wait', frequencies=[2.5], amplitudes=[.8]))
    s.asc(length_mus=400, pd128m2=dict(type='constant', constant_value=-.1))
    md['test'] = s
    md['test'].run()
