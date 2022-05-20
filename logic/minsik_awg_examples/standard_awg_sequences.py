from __future__ import print_function, absolute_import, division
from imp import reload
import hardware.Keysight_AWG_M8190.pym8190a.MultiChSeq as MCAS; reload(MCAS)
import logic.minsik_awg_examples.sequence_creation_helpers as sch; reload(sch)

#from pi3diamond import pi3d
from hardware.Keysight_AWG_M8190.elements import WaveFile, WaveStep, SequenceStep, Sequence
import hardware.Keysight_AWG_M8190.elements as E
import logic.minsik_awg_examples.snippets_awg as sna
import numpy as np
reload(sna)


def ret_awg_seq(name, pd={}, **kwargs):
    if name == 'A1':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'ps': [1]})
        mcas.start_new_segment('A1')
        mcas.asc(name='A1', length_mus=320/12e3, A1=True)
    if name == 'A2':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'ps': [1]})
        mcas.start_new_segment('A2')
        mcas.asc(name='A2', length_mus=320/12e3, A2=True)
    if name == 'repump':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'ps': [1]})
        mcas.start_new_segment('repump')
        mcas.asc(name='repump', length_mus=320/12e3, repump=True)
    if name == 'green':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'128m': [1]})
        mcas.start_new_segment('red')
        mcas.asc(name='green', length_mus=320/12e3, green=True)
    if name == 'orange':
        #mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1], '128m': [1]})
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'128m': [1]})
        #mcas.start_new_segment('infrared', loop_count=1000000)
        mcas.start_new_segment('orange')
        mcas.asc(name='orange', length_mus=320 / 12e3, orange=True)

    if name == 'pulsed':
        if 'length_mus_mw' in pd:
            name += '%.2f' % pd['length_mus_mw']
        if 'name' in kwargs:
            name = kwargs['name']
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2]})
        sna.ssr(mcas, **pd)
   
    if name == 'rabi':
        name = 'rabi%.1f' % kwargs['length_mus']
        if not (('amplitudes' in kwargs) ^ ('periods' in kwargs)):
            raise Exception("Either 'amplitudes' or 'periods' must be given as argument")
        elif 'amplitudes' in kwargs:
            amplitudes = kwargs['amplitudes']
            name += "a"+"_".join(["{:.4f}".format(i) for i in kwargs['amplitudes']])
        elif 'period' in kwargs:
            amplitudes = [pi3d.tt.rp('e_rabi_deg{}_{}'.format(kwargs['mixer_deg'], kwargs['transition']), period=p).amp for p in kwargs['periods']]
            name += "p"+"_".join(["{:.2f}".format(i) for i in kwargs['periods']])
        else:
            raise Exception('Nope!')
        name += "_".join(kwargs['transition'])
        name = kwargs.get('name', name)
        frequencies = kwargs['frequencies']
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2]})
        mcas.start_new_segment('sync_timetagger')
        mcas.asc(name='sync', length_mus=0.01, gate=True) #Changed when timetagger was going to be used
        m = kwargs['length_mus']
        num_step = kwargs.get('num_step', 50)

        step = np.around((m/num_step)*(64*12e3))/(64*12e3)
        mcas.start_new_segment('rabi')
        for i in range(num_step):
            sna.electron_rabi(mcas, length_mus=step*i,
                          new_segment=False,
                          transition=kwargs['transition'],
                          name='_pulsed_tau_',
                          wait_switch=True,
                          frequencies=frequencies,
                          amplitudes=amplitudes,
                          mixer_deg=kwargs['mixer_deg'])
            mcas.asc(name='compensate', length_mus=m - i*step)
            mcas.asc(name='green', length_mus=0.01, green=True, memory=True)
            mcas.asc(name='green', length_mus=2.99, green=True)
            mcas.asc(name='wait', length_mus=0.9)

    if name == 'fid':
        m = kwargs['length_mus']
        num_step = kwargs.get('num_step', 50)
        step = m/num_step
        name = 'fid%.1f' % kwargs['length_mus']
        name = kwargs.get('name', name)
        frequencies = kwargs['frequencies']
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2], '128m':[1]})
        mcas.start_new_segment('sync_timetagger')
        mcas.asc(name='sync', length_mus=0.01, gate=True) #Changed when timetagger was going to be used
        mcas.start_new_segment('fid')
        def pi2():
            sna.electron_rabi(mcas,
                              length_mus=E.round_length_mus_full_sample(pi3d.tt.rp('e_rabi', mixer_deg=-90, amp=1.0).pi2),
                              new_segment=False,
                              name='pi2',
                              wait_switch=True,
                              frequencies=frequencies,
                              amplitudes=[1.0],
                              mixer_deg=-90)

        for i in range(num_step):
            pi2()
            mcas.asc(length_mus=step*i, name='_pulsed_tau_')
            pi2()
            mcas.asc(name='compensate', length_mus=m - i*step)
            mcas.asc(name='green', length_mus=0.01, green=True)
            mcas.asc(name='green', length_mus=2.99, green=True)
            mcas.asc(name='wait', length_mus=0.9)
        sna.nuclear_rabi(mcas,
                         name='flip_13c90',
                         frequencies=[pi3d.tt.t('13C mS0').current_frequency],
                         amplitudes=[min(MCAS.__MAX_RF_AMPLITUDE__, 1.0)],
                         length_mus=2.5,
                         new_segment=True,
                         )
    return mcas

def write_awg_seq(**kwargs):
    pi3d.mcas_dict[kwargs['name']] = ret_awg_seq(**kwargs)

def write_awg_standards():
    write_awg_seq(name='green')
    write_awg_seq(name='red')
    write_awg_seq(name='orange')
 
def run_fun(abort, **kwargs):
    write_awg_standards()
