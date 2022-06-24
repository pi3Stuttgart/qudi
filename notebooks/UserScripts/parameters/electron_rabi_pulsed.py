# coding=utf-8
from __future__ import print_function, absolute_import, division
from imp import reload
__metaclass__ = type

from pi3diamond import pi3d
import pym8190a
#
from collections import OrderedDict

from qutip_enhanced import *
import time, datetime
import sys, traceback
import logging

# import UserScripts.helpers.sequence_creation_helpers as sch;reload(sch)
import multi_channel_awg_seq as MCAS; reload(MCAS)
import UserScripts.helpers.standard_awg_sequences as sas; reload(sas)
import UserScripts.helpers.snippets_awg as sna; reload(sna)

seq_name = os.path.basename(__file__).split('.')[0]

def write_sequence(pdc):
    n_amp =len([key for key in pdc if 'amp' in key])
    t = {1: ['left'], 2:['left', 'right']}[n_amp]
    freq_list = np.array([pi3d.tt.mfl('14N0', ms_trans='left')[0]])
    freq_list_p1 = np.array([pi3d.tt.mfl('14N0', ms_trans='right')[0]])
    nstep = 100
    n_perdiods = 5.0
    amp = pym8190a.elements.round_to_amplitude_granularity(float(pdc['amp{}'.format(pdc['transition'])]))
    total_dur = n_perdiods * pi3d.tt.rp("e_rabi_ou{:.0f}deg{}".format(1000*pi3d.awgs['2g'].ch[1].output_amplitude, pdc['mixer_deg']), amp=amp).period
    kk = 1
    while np.isnan(total_dur):
        total_dur = n_perdiods * pi3d.tt.rp(
            "e_rabi_ou{:.0f}deg{}".format(1000 * pi3d.awgs['2g'].ch[1].output_amplitude, pdc['mixer_deg']),
            amp=amp-kk*0.01).period
        kk+=1
    print('total duration, ', total_dur)
    total_dur = nstep*np.around(np.array(total_dur/nstep)*12e3)/12e3
    pi3d.pulsed.mcas = sas.ret_awg_seq(
        name='rabi',
        length_mus=total_dur,
        amplitudes=[float(pdc[key]) for key in pdc if 'amp' in key],
        transition=t,
        frequencies=freq_list[:n_amp],
        num_step=nstep,
        mixer_deg=pdc['mixer_deg']
    )


def settings(pdc):
    write_sequence(pdc)
    pi3d.pulsed.refocus_interval = 1
    pi3d.pulsed.odmr_interval = 600
    pi3d.pulsed.mw_power = 16.
    pi3d.pulsed.sequence_name = seq_name
    pi3d.pulsed.planned_sweeps = 1e5
    pi3d.pulsed.fit_function = 'CosineMultiDet'

class DataGeneration(dg.DataGeneration):

    def run(self, abort, **kwargs):
        self.init_run(**kwargs)
        try:
            for idxo, _ in enumerate(self.iterator()):
                if abort.is_set(): break
                for idx, _I_ in self.current_iterator_df.iterrows():
                    if _I_["amp{}".format(_I_['transition'])] == '0.000000':
                        self.data.set_observations([
                            dict(
                                omega='0.000000',
                                date=pd.to_datetime('now').__str__())
                        ])
                        continue
                    settings(_I_.to_dict())
                    pi3d.pulsed.run(abort)
                    pi3d.pulsed._do_fit_changed()
                    self.data.set_observations([OrderedDict(omega="{:.6f}".format(1000. / np.abs(pi3d.pulsed.rabi_period)))])
                    self.data.set_observations([OrderedDict(date=pd.to_datetime('now').__str__())])


                    self.data.set_observations([OrderedDict(tau=np.array(pi3d.pulsed.tau))])
                    self.data.set_observations([OrderedDict(results=[pi3d.pulsed.results_all])])

                if hasattr(self, '_pld'):
                    self.pld.new_data_arrived()
                if abort.is_set(): break
                self.save()
        except Exception:
            abort.set()
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            self.data._df = data_handling.df_take_duplicate_rows(self.data.df, self.iterator_df_done)  # drops unfinished measurements,
            pi3d.multi_channel_awg_sequence.stop_awgs(pi3d.awgs)
            self.state = 'idle'
            self.update_current_str()
            if len(self.data.df) <= 1:
                self.pld.gui.close_gui()
                if hasattr(self.data, 'init_from_file') and self.data.init_from_file is not None:
                    self.move_init_from_file_folder_back()
            if os.path.exists(self.save_dir) and not os.listdir(self.save_dir):
                os.rmdir(self.save_dir)

meas = DataGeneration()


pi3d.electron_rabi = meas
meas.parameters = collections.OrderedDict([
    ('mixer_deg', [-90]),
    # ('amp0', ["{:.6f}".format(i) for i in E.round_to_amplitude_granularity([0.0, 1.0])]),
    # ('amp0', ["{:.6f}".format(i) for i in pym8190a.elements.round_to_amplitude_granularity(np.arange(0.0, 1.0001, 0.05))]),
    ('amp0', ["{:.6f}".format(i) for i in pym8190a.elements.round_to_amplitude_granularity([
        0.0,0.2,0.4,0.6,0.8,1.0
        #0.0,0.1,0.3,1.0
        #0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0
        # 0.0, 0.7, 1.0
    ])]),
    ('transition', [0,1]),
    amp.append(["{:.6f}".format(i) for i in E.round_to_amplitude_granularity([i for i in np.linspace(0.0, 1.0, 20) if i > 0.05 or i == 0.0])])
    #amp.append(["{:.6f}".format(i) for i in E.round_to_amplitude_granularity(np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]))])
])
meas._observation_names = ['omega', 'date', 'tau', 'results']
meas.dtypes = dict(omega='float', date='str', tau = 'object', results = 'object')

for cn, val in meas.parameters.items():
    if cn.startswith('amp') and val[0] != '0.000000':
        raise Exception('Error: {}, {}'.format(cn, val))

meas.pld = dh.PlotData(title='electron_rabi', gui=True)
meas.file_path = r"D:/data/NuclearOPs/parameters/electron_rabi"
meas.file_name = 'electron_rabi'

def run_fun(abort, **kwargs):

    meas.run(abort)
    #pi3d.pulsed.edit_traits()

    for d, d_idx, idx, sub in meas.data.iterator(['mixer_deg']):
        sub = sub.drop('mixer_deg', axis=1)
        sub= sub[['amp0', 'transition', 'omega', 'date']]

        if len(sub) == len(meas.data.df.amp0.unique()) and len(sub) > 3:
            f = "e_rabi_ou{:.0f}deg{}".format(1000 * pi3d.awgs['2g'].ch[1].output_amplitude, d['mixer_deg'])
            logging.getLogger().info('Updating rabi file {}..'.format(f))
            pi3d.tt.rabi_parameters[f].update_file(sub)
            logging.getLogger().info("Done!")