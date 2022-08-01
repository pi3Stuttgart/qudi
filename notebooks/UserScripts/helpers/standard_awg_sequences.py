from __future__ import print_function, absolute_import, division
from imp import reload
from importlib import reload as reload
import hardware.Keysight_AWG_M8190.pym8190a as MCAS; reload(MCAS)
import notebooks.UserScripts.helpers.sequence_creation_helpers as sch; reload(sch)


from hardware.Keysight_AWG_M8190.elements import WaveFile, WaveStep, SequenceStep, Sequence
#import from hardware.Keysight_AWG_M8190.elements
import hardware.Keysight_AWG_M8190.elements as E
import notebooks.UserScripts.helpers.snippets_awg as sna
import numpy as np
reload(sna)


def ret_awg_seq(name, pd={}, **kwargs):
    if name == 'green':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2], 'ps': [1]})
        mcas.start_new_segment('green')
        mcas.asc(name='green', length_mus=12e4/12e3, green=True, gate=True)
        mcas.asc(name='green', length_mus=12e2/12e3, green=True, gate=False) #Tried to increase here the duty cycle of the
        #gating interval.

    if name == 'red':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1]})
        mcas.start_new_segment('red')
        mcas.asc(name='red', length_mus=320/12e3, green=True)
    if name == 'repump':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2],'ps':[1]})
        mcas.start_new_segment('repump')
        mcas.asc(name='repump', length_mus=1200e3 / 12e3, repump=True)

    if name == 'red_Ex':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2],'ps':[1]})
        mcas.start_new_segment('red_Ex')
        mcas.asc(pd2g2=dict(type='sine',
                            frequencies=[10],
                            amplitudes=[0.3],
                            phase_offset_type='absolute',
                            phase=[0]),
                 aom_Ex=True, length_mus=100)

    if name == 'Ex_RO':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2],'ps':[1]})
        mcas.start_new_segment('Ex_RO')
        mcas.asc(name='Ex_RO', length_mus=120e3 / 12e3, Ex_RO=True)

    if name == 'red_A1':
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2],'ps':[1]})#So far only makes green
        mcas.start_new_segment('red_A1')
        mcas.asc(name='red_A1', length_mus=120e3/12e3, aom_A1=True)



    if name == 'pulsed':
        if 'length_mus_mw' in pd:
            name += '%.2f' % pd['length_mus_mw']
        if 'name' in kwargs:
            name = kwargs['name']
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2]})
        sna.ssr(mcas, **pd)
    # if name == 'test_sine':
    #     pi3d.mcas_dict.stop_awgs()
    #     name = 'test_sine'
    #     import multi_channel_awg_seq as MCAS
    #     mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2]})
    #     mcas.start_new_segment('asdf', loop_count=1000000)
    #     pd2g1 = dict(type='sine', amplitudes=[1.0], frequencies=[3.0], length_mus=1.)
    #     pd2g2 = dict(type='sine', amplitudes=[1.0], frequencies=[3.0], length_mus=1., phases=[90])
    #     # mcas.asc(name=name, )
    #     mcas.asc(name=name, pd2g2=pd2g2, pd2g1=pd2g1)
    #     pi3d.mcas_dict['test_sine'] = mcas
    #     pi3d.mcas_dict['test_sine'].run()


    # if name == '13C90_pi':
    #     sc1 = Sequence(name=name)
    #     sc1.data_list.append(SequenceStep(data_list=[WaveStep(type='wait', length_smpl=0)], name='dontremove', advance_mode='AUTO'))
    #     amp = min(MCAS.__MAX_RF_AMPLITUDE__, 1.0)
    #     sc1.data_list.append(
    #         SequenceStep(data_list=[
    #             WaveStep(type='sine',
    #                      amplitudes=[amp],
    #                      length_mus=pi3d.tt.rp(name='13C mS0', amp=amp).pi,
    #                      frequencies=[pi3d.tt.t('13C mS0').current_frequency])
    #         ],
    #             name='13C mS0', advance_mode='AUTO'))
    #     sc1.data_list.append(SequenceStep(data_list=[WaveStep(length_smpl=320)], name='waitstop', advance_mode='SING'))
    #     pi3d.awg128m.ch[1].save_sequence(sc1)
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
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2], 'ps': [1]})
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
                          iq_mixer = False,
                          mixer_deg=kwargs['mixer_deg'])
            mcas.asc(name='compensate', length_mus=m - i*step)
            mcas.asc(name='green', length_mus=0.01, green=True, memory=True)
            mcas.asc(name='green', length_mus=2.99, green=True)
            mcas.asc(name='wait', length_mus=30.9)

        # l = np.around(np.linspace(0.0, m, num_step)*(64*12e3))/(64*12e3)
        # l = np.array([i for i in l if i == 0.0 or i == m or (i >=320/12e3 and (m - i) > 320/12e3)])
        # print('m', m)
        # print(l)
        # mcas.start_new_segment(name='_pulsed_tau_', segment_end_offset_mus=l[0])
        # sna.electron_rabi(mcas, length_mus=l[-1],
        #                   transition=kwargs['transition'],
        #                   name='_pulsed_tau_',
        #                   wait_switch=True,
        #                   frequencies=frequencies,
        #                   amplitudes=amplitudes,
        #                   mixer_deg=kwargs['mixer_deg'])
        # mcas.start_new_segment(name='compensate', segment_end_offset_mus=l[-1]-l[0])
        # mcas.asc(name='compensate', length_mus=l[-1])
        # mcas.start_new_segment(name='green')
        # mcas.asc(name='green', length_mus=3.0, green=True)
        # mcas.start_new_segment(name='wait')
        # mcas.asc(name='wait', length_mus=0.9)
        # for li in l:
        #     mcas.start_new_segment(name='_pulsed_tau_', segment_end_offset_mus=li, reuse_segment=True)
        #     mcas.asc(name='compensate', segment_end_offset_mus=l[-1] - li, reuse_segment=True)
        #     mcas.start_new_segment(name='green', reuse_segment=True)
        #     mcas.start_new_segment(name='wait', reuse_segment=True)
    if name == 'fid':
        m = kwargs['length_mus']
        num_step = kwargs.get('num_step', 50)
        step = m/num_step
        name = 'fid%.1f' % kwargs['length_mus']
        name = kwargs.get('name', name)
        frequencies = kwargs['frequencies']
        # mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2], '128m':[1]})
        mcas = MCAS.MultiChSeq(name=name, ch_dict={'2g': [1, 2]})
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

def write_awg_seq(queue,**kwargs):
    queue._awg.mcas_dict[kwargs['name']] = ret_awg_seq(**kwargs)

def write_awg_standards(queue):
    write_awg_seq(queue, name='green')
    write_awg_seq(queue,name='repump')
    write_awg_seq(queue,name='red_Ex')
    write_awg_seq(queue,name='red_A1')
    write_awg_seq(queue,name='Ex_RO')

    #write_awg_seq(name='red')
    #write_awg_seq(name='orange')
    # write_awg_seq('pulsed_green')
    # write_awg_seq('13C90_pi')
    # for s in ['left']:
    #     sign = {'left': +1, 'right': -1}
    #     a = dict(repetitions=1, transition=s, final_wait=False)
    #     write_awg_seq('pulsed',
    #                   pd=dict(
    #                       length_mus_mw=0.8,
    #                       frequencies=sign[s]*pi3d.tt.mfl({'14N': [0]}, ms_trans='left'),
    #                       mixer_deg=75,
    #                       **a
    #                   ),
    #                   name='pulsed0.80_'+s
    #                   )
    #     write_awg_seq('pulsed',
    #                   pd=dict(
    #                       length_mus_mw=3.,
    #                       frequencies=sign[s]*pi3d.tt.mfl({'14N': [-1, 0, 1], '13C414': [-0.5, 0.5]}, ms_trans='left'),
    #                       mixer_deg=75,
    #                       **a
    #                   ),
    #                   name='pulsed3.00_'+s
    #                   )
    #     write_awg_seq(
    #         'pulsed',
    #         pd=dict(length_mus_mw=20.,
    #                 frequencies=sign[s] * pi3d.tt.mfl({'14N': [-1, 0, 1], '13C414': [-0.5, 0.5], '13C90': [-0.5, 0.5]}, ms_trans='left'),
    #                 mixer_deg=75,
    #                 amplitudes=pi3d.tt.rp('e_rabi', mixer_deg=75).amplitude(tni={'left': [0], 'right': [1]}[s], period=[2 * 20.]),
    #                 **a
    #                 ), name='pulsed20.00_'+s)
    # write_awg_seq('red')
    # write_awg_seq('infrared')
    # write_awg_seq(name='test_sine', amplitudes=[1.0], frequencies=[10.0], phases=[0.0], ch_dict={'2g':[1]}, length_smpl=12032)

def run_fun(abort, queue, **kwargs):
    write_awg_standards(queue)

# if False:
#     mcas = MCAS.MultiChSeq(name='asdf', ch_dict={'2g': [1, 2], '128m': [1]})
#     mcas.start_new_segment('hi')
#     mcas.asc(
#              pd128m1=dict(length_mus=12., amplitudes=[.01], frequencies=[1.0], type='sine'),
#              # pd128m2=dict(length_mus=12., amplitudes=[1.0], frequencies=[1.0], type='sine'),
#              )
#     # sna.nuclear_rabi(mcas,
#     #              name='13c90 ms-1',
#     #              amplitudes=[1.0],
#     #              frequencies=[1.0],
#     #              length_mus=10.0
#     #              )
#     mcas.asc(length_mus =4)
#     mcas.write_seq()
#     mcas.run_sequence()
#
#
#     MCAS.stop_awgs()
