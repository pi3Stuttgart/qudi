#from pi3diamond import pi3d, CloseHandler
import numpy as np
import collections
from .AWG_M8190A_Elements import Sequence, SequenceStep, WaveStep
import time


__HARDCODED_MAX_AVG_POWER__ = 5
_BLM_ = 192./12e3


class MultiChSeq(object):
    def __init__(self, seq_name, ch_dict=None, trigger_delay=54*_BLM_, trigger_length_mus=54*_BLM_,
                 w_trig_safety=10*_BLM_, max_avg_power=5):
        super(MultiChSeq, self).__init__()
        self.trigger_length_mus = trigger_length_mus
        self.trigger_delay = trigger_delay  # the awg has a fixed trigger delay (sample clock dependent) of ~< 1mus
        self.max_avg_power = max_avg_power  # maximum rf power on average
        self.w_trig_safety = w_trig_safety  # after awg2g finishes its sequence, it waits this time until it sends a new trigger
        self.seq_name = seq_name  #
        self.ch_dict = {'awg': [1, 2]} if ch_dict is None else ch_dict
        self.sequences = {}
        for awg_str in self.ch_dict.keys():
            self.sequences[awg_str] = dict([[ch, Sequence(name=self.seq_name)] for ch in self.ch_dict[awg_str]])
        self.awg = None

    def asc(self, **kwargs):
        if self.reusing:
            return
        self.add_step_complete(**kwargs)

    def add_step_complete(self, pdawg1=None, pdawg2=None,
                          green=False,timetagger=False,orange=False,   **kwargs):

        pd = {}
            
        for awg_str in self.ch_dict.keys():
            pd[awg_str] = {}
            for ch in self.ch_dict[awg_str]:
                ps = 'pd' + awg_str + str(ch)
                update(pd, {awg_str: {ch: locals()[ps]}})
                if pd[awg_str][ch] is None:
                    pd[awg_str][ch] = {}

        # set mw smpl_maker on
        if green:
            pd['awg'][1].update(smpl_marker=green)
            #pd['awg'][2].update(smpl_marker=green)
        if timetagger:
            pd['awg'][1].update(sync_marker=timetagger)
        if orange:
            pd['awg'][2].update(smpl_marker=orange)
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

    def add_step(self,pd=None, name='', length_mus=None, **kwargs):
        if pd is None:
            pd = {}
        length_mus = self.step_length_mus(pd, length_mus=length_mus)
        for awg_str in self.ch_dict.keys():
            if awg_str not in pd:
                pd[awg_str] = {}
            for ch in self.ch_dict[awg_str]:
                if ch not in pd[awg_str]:
                    pd[awg_str][ch] = {}
                pdch = pd[awg_str][ch]
                if 'loop_count' in pdch or 'advance_mode' in pdch:
                    raise Exception("Parameter dict for an individual channel must not have any of keys ['loop_count', 'advance_mode'], as those are set for the step")
                if not pd[awg_str].get('type', 'wait') in ['robust']:
                    pd[awg_str][ch].update(length_mus=length_mus)
                if 'name' not in pd[awg_str][ch]:
                    pd[awg_str][ch].update(name=name)
                pd[awg_str][ch].update(**kwargs)
                if len(self.sequences[awg_str][ch].data_list) == 0:
                    raise Exception('There is no segment to append to. Start a new one first.')
                self.sequences[awg_str][ch].data_list[-1].data_list.append(WaveStep(**pd[awg_str][ch]))

    def start_new_segment(self, name='', loop_count=1, advance_mode='AUTO', reuse_segment=False):
        self.reusing=False
        if reuse_segment:
            reused_sequence_step=None
            for awg_str in self.ch_dict.keys():
                for ch in self.ch_dict[awg_str]:
                    for step in self.sequences[awg_str][ch].data_list:
                        if step.name==name and not step.reuse_segment:
                            self.reusing=True
                            reused_sequence_step = step
                            break
#                    reused_sequence_step_l = [i for i in self.sequences[awg_str][ch].data_list if i.name == name]
                    if reused_sequence_step is None:
                        reuse_segment = False
                        self.sequences[awg_str][ch].data_list.append(SequenceStep(name=name, advance_mode=advance_mode, loop_count=loop_count, reuse_segment=reuse_segment))
                    else:
                        self.sequences[awg_str][ch].data_list.append(SequenceStep(name=name, advance_mode=advance_mode, loop_count=loop_count, reused_sequence_step=reused_sequence_step,reuse_segment=reuse_segment))
        else:
            for awg_str in self.ch_dict.keys():
                for ch in self.ch_dict[awg_str]:
                    self.sequences[awg_str][ch].data_list.append(SequenceStep(name=name, advance_mode=advance_mode, loop_count=loop_count))


    def comb_all_steps(self, fd, **kwargs):
        """
        Combs through all steps in a given sequence and performs 'fun' on each step.
        fun must be a function of an integer i out of range(len(self.x))
        """
        for awg_str in fd:
            for ch in fd[awg_str]:
                for f in fd[awg_str][ch]:
                    for step in self.sequences[awg_str][ch].step_list:
                        f(step, **kwargs)

    # def remove_step(self, name):
    #     for awg_str in self.ch_dict.keys():
    #         for ch in self.ch_dict[awg_str]:
    #             for step_seq in self.sequences[awg_str][ch].sequence_data:
    #                 if step_seq.type == 'waveform':
    #                     for step_w in step_seq.waveform_data:
    #                         if step_w.name == name:
    #                             step_seq.remove(step_w)
    #                 else:
    #                     if step_seq.name == name:
    #                         self.sequences[awg_str][ch].sequence_data.remove(step_seq)

    def write_seq(self, ignore_max_avg_power=False):
        #self.fix_avg_rf_power(ignore_max_avg_power=ignore_max_avg_power)
        for awg_str in self.ch_dict.keys():
            for ch in self.ch_dict[awg_str]:
                self.awg.ch[ch].save_sequence(self.sequences[awg_str][ch], notify=False) #FIXME
                #awg(self,awg_str).ch[ch].save_sequence(self.sequences[awg_str][ch], notify=False) #FIXME
        print("MCAS '{}' has been generated.".format(self.seq_name))

    def run_sequence(self, ignore_max_avg_power=False):
        self._run_sequence(seq_name=self.seq_name,
                     ch_dict=self.ch_dict,
                     max_avg_power=self.max_avg_power,
                     ignore_max_avg_power=ignore_max_avg_power,
                     )

    def avg_rf_power(self):
        if 2 in self.ch_dict.get('awg', []):
            return avg_rf_power(self.sequences['awg'][2])
        else:
            return 0

    def additional_wait_time(self, ignore_max_avg_power=False):
        if ignore_max_avg_power:
            return 0
        else:
            return check_avg_rf_power(self.sequences['awg'][2], max_avg_power=self.max_avg_power)

    def fix_avg_rf_power(self, ignore_max_avg_power=False):
        if 2 in self.ch_dict.get('awg', []):
            awt = self.additional_wait_time(ignore_max_avg_power=ignore_max_avg_power)
            if awt == 0:
                return
            length_mus = awt
            loop_count = 1
            if awt > 100.0:
                length_mus = 100.0
                loop_count = int(np.ceil(awt/100.0))
            self.start_new_segment(name='rf_power_safety', loop_count=loop_count)
            self.asc(length_mus=length_mus)
            if check_avg_rf_power(self.sequences['awg'][2], max_avg_power=self.max_avg_power) > 0.1 and not ignore_max_avg_power:
                raise Exception('Additional wait time added, but RF-power still too high!')
                
            
    def AddWait(self,time,orange=False):
        if time<0.:
            for i in range(100): print('Negative time for sequence in AWG!!!')
        av_prev=self.sequences['awg'][1].data_list[-1].advance_mode
        if av_prev=='SING' or av_prev=='AUTO':
            for ch in self.ch_dict['awg']:
                self.sequences['awg'][ch].data_list[-1].advance_mode='AUTO'
            if int(time/(32/12.))>=1:
                self.start_new_segment('wait',advance_mode='AUTO',loop_count=int(time/(32/12.)))
                self.asc(length_smpl=32000,orange=orange)
            self.start_new_segment('ncste',advance_mode=av_prev)
            self.asc(length_mus=time%(32/12.),orange=orange)
        else:
            self.asc(length_mus=time,orange=orange)

    def _run_sequence(self,seq_name=None, ch_dict=None, trigger=False,
                      turn_off_compl=True, max_avg_power=1,
                      ignore_max_avg_power=True):
        ch_dict = {'awg': [1, 2]} if ch_dict is None else ch_dict
        ccd = complementary_ch_dict(ch_dict)
        if turn_off_compl:
            for awg_str in ccd.keys():
                for ch in ccd[awg_str]:
                    self._awg(awg_str=awg_str).ch[ch].selected_sequence_name = 'wait'
        #    if not ignore_max_avg_power:
        #        if 2 in ch_dict.get('awg', []):
        #            if check_avg_rf_power(pi3d.awg.ch[1].ret_sequence(seq_name), max_avg_power, notify=True) != 0:
        #                raise Exception('Average rf power too high')
        for awg_str in ch_dict.keys():
            for ch in ch_dict[awg_str]:
                self._awg(awg_str).ch[ch].selected_sequence_name = seq_name
            self._awg(awg_str).run()
        self.set_outputs()
        if trigger:
            self.send_trigger(ch_dict=ch_dict)

    def send_trigger(self,ch_dict=None):
        ch_dict = {'awg': [1, 2]} if ch_dict is None else ch_dict
        if len(ch_dict) == 1:
            self._awg(ch_dict.keys()[0]).awg.send_begin()
        else:
            pass
            # pi3d.awg.awg.send_begin()

    # def awg_pi3d(aws):
    #     try:
    #         return getattr(pi3d, 'awg') #FIXME TO QUDI
    #     except:
    #         return a

    def _awg(self, awg_str):
        try:
            return getattr(self, awg_str)  # FIXME TO QUDI
        except:
            print('Error, can not find any AWG!')

    def set_outputs(self, ch_dict=None):
        ch_dict = {'awg': [1, 2]} if ch_dict is None else ch_dict
        for awg_str in ch_dict.keys():
            for ch in ch_dict[awg_str]:
                self._awg(awg_str).ch[ch].output = 1

    #            if awg_str == 'awg2g':
    #                awg(awg_str).ch[ch].complementary_output = 1

    def stop_awgs(self, ch_dict=None):
        ch_dict = {'awg': [1, 2]} if ch_dict is None else ch_dict
        for awg_str in ch_dict.keys():
            self._awg(awg_str).abort()
            for ch in ch_dict[awg_str]:
                self._awg(awg_str).ch[ch].selected_sequence_name = 'wait'



def set_global_sample_offset(awg, delay_length_mus):
    gso = int(round(delay_length_mus * 1e-6 * 12e9))
    if not gso % 64 == 0:
        raise Exception('trigger_delay not allowed')
    else:
        for chn in [1, 2]:
            awg.ch[chn].global_sample_offset = gso

def avg_rf_power(awg128m_sequence):
    rf_energy = 0
    for seq_step in awg128m_sequence.data_list:
        if seq_step.advance_mode == 'AUTO':
            for w_step in seq_step.data_list:
                    rf_energy += 500.0 * sum(
                        np.array(w_step.amplitudes, dtype='float') ** 2) * w_step.length_mus * seq_step.loop_count
    if rf_energy == 0.0:
        return 0
    else:
        return rf_energy / awg128m_sequence.length_mus

def check_avg_rf_power(awg128m_sequence, max_avg_power, notify=True):
    if max_avg_power > __HARDCODED_MAX_AVG_POWER__:
        raise Exception("This value of 'max_avg_power' is forbidden!")
    avg_power = avg_rf_power(awg128m_sequence)
    additional_wait_time = max(0, int(awg128m_sequence.length_mus * (avg_power/max_avg_power - 1)))
    if additional_wait_time > 0:
        new_avg_power = avg_power/(1 + additional_wait_time/awg128m_sequence.length_mus)
        print("Old avg_power {:.2f} W, additional_wait_time: {:d}, new avg_power: {:.2f}".format(avg_power, additional_wait_time, new_avg_power))
    elif notify:
        print("The average rf power is {:.2f} W".format(avg_power))
    return additional_wait_time
    
def complementary_ch_dict(ch_dict):
    fcd = {'awg': [1, 2]}
    ccd = dict()
    for key, value in fcd.items():
        if not key in ch_dict:
            ccd[key] = [1, 2]
        else:
            l = [i for i in value if i not in ch_dict[key]]
            if len(l) > 0:
                ccd[key] = l
    return ccd





def update(d, u):
    for k, v in u.items(): #FIXME  changed here (was iteritems)
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def comb_awg_seq(data_list, fun, **kwargs):
    """
    Combs through all steps in a given sequence and performs 'fun' on each step.
    fun must be a function of an integer i out of range(len(self.x))
    """
    for step_seq in data_list:
        if step_seq.type == 'waveform':
            for step_w in step_seq.data_list:
                fun(step_w, **kwargs)
        else:
            fun(step_seq, **kwargs)

if __name__ == '__main__':
    mcas = MultiChSeq(seq_name='asdf')
    # mcas.start_new_segment('rfsmplmarker')
    # mcas.asc(length_smpl=12800, pd128m1=dict(smpl_marker=True))
    mcas.start_new_segment('sinesine')
    sd = dict(type='sine', frequencies=[1000.], amplitudes=[0.01])
    mcas.asc(length_mus=1e3, pdawg1=sd)
    mcas.write_seq()
    mcas.run_sequence()