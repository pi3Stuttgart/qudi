from __future__ import print_function, absolute_import, division
__metaclass__ = type

import sys
if sys.version_info.major == 2:
    from imp import reload
else:
    from importlib import reload

#from pi3diamond import pi3d
from logic.qudip_enhanced import *
from logic.qudip_enhanced.util import printexception
import time, datetime
import logic.misc as misc; reload(misc)
import traceback
import numpy as np
import logging
import types
import hashlib
import base64


import lmfit
from collections import OrderedDict
from numbers import Number

import ast
import importlib
from hardware.Keysight_AWG_M8190 import pym8190a
import notebooks.UserScripts.helpers.snippets_awg as sna; importlib.reload(sna)
from logic.qudip_enhanced.data_generation import DataGeneration
__COUNTER_NAME__ = 'odmr_timedifferences'
# __COUNTER_NAME__  = 'gated_counter_countbetweenmarkers'
run_val_fun_name = {'odmr_timedifferences': 'getCounts',
                    'odmr': 'getODMRRun',
                    'gated_counter_countbetweenmarkers':'getData',}[__COUNTER_NAME__]

#TODO fix it to work similar to normal Nops. (regarding TT for example)
class ODMR(DataGeneration):
    #shouldnt it be a based class of logic?

    def __init__(self,queue):
        super(ODMR, self).__init__()
        self.pld = data_handling.PlotData(title='ODMR', gui=False)
        self.q = queue

        @printexception
        def custom_default_settings_pld(self):
            self.x_axis_parameter_list.update_selected_value('center_frequency')
            self.average_parameter_list.update_selected_data(['sweeps'])
            self.observation_list.update_selected_data(['counts_per_lp'])

        self.pld._custom_default_settings = types.MethodType(custom_default_settings_pld, self.pld)
        self.save_after_run = True
        self.file_path = r"D:\data\ODMR"
        self.file_name = 'odmr'
        self.set_ret_mcas()

    # Tracking stuff:

    odmr_runs = misc.ret_property_typecheck('odmr_runs', int)
    # runtime = misc.ret_property_typecheck('runtime', Number)
    readout_interval = misc.ret_property_typecheck('readout_interval', Number)
    progress = misc.ret_property_typecheck('progress', int)
    f_mhz = misc.ret_property_typecheck('f_mhz', float)
    power = misc.ret_property_typecheck('power', float)
    refocus_interval = misc.ret_property_typecheck('refocus_interval', Number)
    track_file = misc.ret_property_typecheck('track_file', dict)
    update_tt = misc.ret_property_typecheck('update_tt', bool)
    custom_model = misc.ret_property_typecheck('custom_model', lmfit.Model)
    save_after_run = misc.ret_property_typecheck('save_after_run', bool)

    __TITLE_DATE_FORMAT__ = '%Y%m%dh%Hm%Ms%S'

    @property
    def observation_names(self):
        try:
            return ['counts_per_lp', 'counts', 'odmr_runs']
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    @property
    def dtypes(self):
        try:
            if not hasattr(self, '_dtypes'):
                self._dtypes = dict(counts_per_lp='float', odmr_runs='int', counts='int')
            return self._dtypes
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    @dtypes.setter
    def dtypes(self, val):
        try:
            if isinstance(val, dict):
                for k, v in val.items():
                    if not (k in self.parameters.keys() or isinstance(v, str)):
                        raise Exception("Error: {}".format(val))
                self._dtypes = val
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    @data_generation.DataGeneration.number_of_simultaneous_measurements.setter
    def number_of_simultaneous_measurements(self):
        raise NotImplementedError

    def run(self, abort, **kwargs):
        self.parameters['sweeps'] = [0]
        self.parameters['mw_mixing_freq_L'] = [self.q._transition_tracker.mw_mixing_frequency_L]
        self.parameters['mw_mixing_freq_C'] = [self.q._transition_tracker.mw_mixing_frequency_C]
        self.parameters['mw_mixing_freq_R'] = [self.q._transition_tracker.mw_mixing_frequency_R]
        self.init_run(**kwargs)
        try:
            logging.getLogger().info('ODMR..')
            if len(self.parameters['transition']) != 1:
                raise Exception('Error: {}'.format(self.parameters))
            else:
                transition = self.parameters['transition'][0]
            if transition == 'left':
                self.f_mhz = self.q._transition_tracker.mw_mixing_frequency_L
            elif transition == 'right':
                self.f_mhz = self.q._transition_tracker.mw_mixing_frequency_R
            #pi3d.microwave.CW(f=self.f_mhz*1e6, power=self.power)
            for idx, _ in enumerate(self.iterator()):
                if idx == 0:
                    t0 = time.time()
                    self.q._awg.mcas_dict.stop_awgs()
                    self.setup_counter()
                    self.setup_rf(self.current_iterator_df)
                    self.setup_time = time.time() - t0
                if abort.is_set():
                    break
                self.data.set_observations(self.get_counts())
                if abort.is_set():
                    break
                #self.pld.new_data_arrived() # plotting and plot the pld!
                if getattr(getattr(self.q._fast_counter_device, __COUNTER_NAME__), run_val_fun_name)() < self.odmr_runs:
                    self.parameters['sweeps'] = range(self.parameters['sweeps'][-1]+2) #range(len(self.parameters['sweeps'])+1)
            getattr(self.q._fast_counter_device, __COUNTER_NAME__).stop()
            self.q._awg.mcas_dict.stop_awgs()
            logging.getLogger().info(
                'ODMR duration {}s ({} runs)'.format((datetime.datetime.now() - self.start_time).seconds,
                                                     getattr(getattr(self.q._fast_counter_device, __COUNTER_NAME__),
                                                             run_val_fun_name)()))
            fit_start_time = datetime.datetime.now()
            self.fit_and_update(abort)
            logging.getLogger().info(
                'ODMR fitting {}s ({} runs)'.format((datetime.datetime.now() - fit_start_time).seconds,
                                                     getattr(getattr(self.q._fast_counter_device, __COUNTER_NAME__),
                                                             run_val_fun_name)()))
            if self.save_after_run:
                self.save()
        except Exception:
            abort.set()
            logging.getLogger().info('ODMR.. Failed/Aborted!')
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            self.q._awg.mcas_dict.stop_awgs()
            self.state = 'idle'

    def fit_and_update(self, abort):

        self.pld.set_custom_default_settings()
        data_selected = self.pld.data_selected
        self.chisqr_l = []
        self.result_l = []

        #cf_guess_list = np.array(pi3d.odmr.data.df.center_frequency.unique()) if getattr(self, 'sweep_fit_guess', True) else [None]
        freq_list = np.array(self.data.df.center_frequency.unique())
        indexs = np.argmin(np.array(data_selected.df.counts_per_lp))
        cf_guess_list = [freq_list[indexs],freq_list[indexs]+2.0,freq_list[indexs]-2.0]
        ###
        for cf_guess in cf_guess_list:
            if cf_guess is not None:
                self.pld.custom_params = lmfit.Parameters()
                self.pld.custom_params.add('center', cf_guess)
            self.pld.update_data_fit_results(data_selected)
            self.result_l.append(self.pld.data_fit_results.df.fit_result.iloc[0])
            self.chisqr_l.append(self.result_l[-1].chisqr)
            self.pld.data_fit_results.df.at[0, 'fit_result'] = result = self.result_l[np.array(self.chisqr_l).argmin()]
            if abort.is_set(): return
        ###


        self.pld.update_plot_fit(data_fit_results=self.pld.data_fit_results)

        offset = result.params['center'].value
        if 'a' in result.params: # LorentzModel
            self.odmr_line_width = 2 * result.params['g']
            self.odmr_contrast = -100 * result.params['a'] / (np.pi * result.params['g'] * result.params['c'])
        elif 'a1' in result.params and 'a2' in result.params and 'a3' in result.params:
            self.odmr_line_width = 2*result.params['g']
            self.odmr_contrast = sum([(-100 * result.params['a{}'.format(i)] / (np.pi * result.params['c'])) for i in range(1,4)]) #result.params['c1'] + result.params['c2'] + result.params['c3']
        self.f_mhz += offset
        #pi3d.microwave.CW(f=self.f_mhz * 1e6, power=self.power)
        t = self.parameters['transition'][0]
        if self.update_tt:
            if t == 'left':
                self.q.tt.mw_mixing_frequency_L = self.f_mhz

                # also update mw freqs in both PLE
                #pi3d.ple_Ex.mw_frequency = self.f_mhz
                #pi3d.ple_A1.mw_frequency = self.f_mhz



                logging.getLogger().info('current_mw_mixing_frequency was corrected by {} MHz'.format(offset))
            elif t == 'right':
                print('right ',self.f_mhz)
                self.q.tt.mw_mixing_frequency_R = self.f_mhz # TODO, we need to do a setter for the mw_mixing_frquency_p1
                #pi3d.ple_Ex.mw_frequency2 = self.f_mhz
                #pi3d.ple_A1.mw_frequency2 = self.f_mhz

                # Such that it calculates B_z and B_perp using full hamiltonian.
                self.f_mhz = self.q.tt.mw_mixing_frequency_L

                logging.getLogger().info('current_mw_mixing_frequency_p1 frequency was corrected by {} MHz'.format(offset))
        if self.track_file[t] is not None:
            if t == 'left':
                self.q.save_value_to_file(self.q.tt.mw_mixing_frequency, self.track_file[t])
                # pi3d.save_values_hdf(self.track_file[t], vd={'none': pi3d.tt.current_local_oscillator_freq})
            elif t == 'right':
                # pi3d.save_values_hdf(self.track_file[t], vd={'none': pi3d.tt.zero_field_splitting})
                self.q.save_value_to_file(self.q.tt.zero_field_splitting, self.track_file[t])
                pass


    def get_counts(self):
        # time.sleep(self.readout_interval)
        aggdf = self.data.df.groupby(['center_frequency']).agg({'counts': np.sum, 'odmr_runs': np.sum}).reset_index()
        # cts = np.array(getattr(pi3d.timetagger, __COUNTER_NAME__).getData()[0,:-1], dtype=np.int32) # last data value takes photons during possible RF pi pulse (13c90)
        # cts = np.array(getattr(pi3d.timetagger, __COUNTER_NAME__).getData()[:-1, 0], dtype=np.int32) if __COUNTER_NAME__ == 'odmr_timedifferences' \
        time.sleep(self.readout_interval)

        getattr(self.q._fast_counter_device, __COUNTER_NAME__).sync()
        cts = np.array(getattr(self.q._fast_counter_device, __COUNTER_NAME__).getData()[0:,0], dtype=np.int32) if __COUNTER_NAME__ == 'odmr_timedifferences' \
            else np.array(getattr(self.q._fast_counter_device, __COUNTER_NAME__).getData()[0, :-1], dtype=np.int32) # last data value takes photons during possible RF pi pulse (13c90)
        cts2 = cts
        # time.sleep(self.readout_interval)
        odmr_runs = getattr(getattr(self.q._fast_counter_device, __COUNTER_NAME__), run_val_fun_name)()
        # time.sleep(self.readout_interval)
        odmr_runs2 = odmr_runs
        if len(self.iterator_df_done) > 0:
            cts = cts - aggdf['counts']
            odmr_runs = odmr_runs - aggdf['odmr_runs'].iloc[-1]
        counts_per_lp = cts.astype(np.float)/odmr_runs
        for _ in counts_per_lp:
            pass
            #if any(counts_per_lp == np.inf):
                #pi3d.cts2 = cts2
                #pi3d.odmr_runs2 = odmr_runs2
                #pi3d.cts = cts
                #pi3d.odmr_runs = odmr_runs
                #pi3d.counts_per_lp = counts_per_lp
                #raise Exception('Error: {}'.format(counts_per_lp))
        return [OrderedDict([('counts_per_lp', cplp), ('counts', cts), ('odmr_runs', odmr_runs)]) for cplp, cts in zip(counts_per_lp, cts)]

    def setup_counter(self): ## TODO here is the beast.
        print('SETUP Counter')
        if __COUNTER_NAME__ == 'gated_counter_countbetweenmarkers':

            self.q._fast_counter_device.init_counter(__COUNTER_NAME__,
                                         n_values=len(self.parameters['center_frequency']),
                                         delay_ps = pd.DataFrame.from_dict({'delay_ps':[0]}))
                                         # number_of_memories=len(self.parameters['center_frequency']))

            self.cts = np.zeros(len(self.parameters['center_frequency']))
            self.counts_per_lp = np.zeros(len(self.parameters['center_frequency']))
        else:
            self.q._fast_counter_device.init_counter(__COUNTER_NAME__,
                                         number_of_memories=len(self.parameters['center_frequency']))

        getattr(self.q._fast_counter_device, __COUNTER_NAME__).clear()

    # def do_refocus(self, l):
    #     if self.refocus_interval > 0 and time.time() - self.last_refocus > self.refocus_interval:
    #         pi3d.confocal.run_refocus()
    #         self.last_refocus = time.time()
    #         self.setup_rf(l)

    def reinit(self):
        super(ODMR, self).reinit()
        self.pld.custom_model = self.custom_model
        self._number_of_simultaneous_measurements = len(self.parameters['center_frequency'])
        if len(self.parameters['center_frequency']) != self.number_of_simultaneous_measurements:
            raise Exception('Error: {}, {}'.format(self.parameters['center_frequency'], self.number_of_simultaneous_measurements))



    @property
    def ret_mcas(self):
        return self._ret_mcas

    def set_ret_mcas(self, val=None):
        def ret_mcas(current_iterator_df, sequence_name):
            s = current_iterator_df.transition.iloc[0]
            #flip_13c90 = getattr(current_iterator_df, 'flip_13c90').iloc[0]
            mcas = pym8190a.MultiChSeq(name=sequence_name, ch_dict={'2g': [1, 2], 'ps': [1]})

            mcas.start_new_segment('start_sequence')
            mcas.asc(length_mus=0.1, sync_tt=True, name='Sync TT')  # Starting... histogram 0
            mcas.asc(length_mus=1.0, name='delay')
            mcas.asc(length_mus=0.1, name='initial_delay')
            # mcas.asc(length_mus=0.1, memory=True, name='memory')
            mcas.asc(length_mus=0.08, name='delay')

            for idx, _I_ in current_iterator_df.iterrows():
                frequencies = _I_['center_frequency'] + self.q.tt.mfl(ast.literal_eval(_I_['td']), ms_trans=s)
                if idx%2 ==0:
                    factor = 0
                else:
                    factor = 5
                factor = 1
                pd = dict(
                    length_mus_mw=_I_['pi_duration'],
                    frequencies=[frequencies],
                    mixer_deg=_I_['mixer_deg'],
                    repetitions=1,
                    transition=s,
                    final_wait=False,
                    gate_or_trigger='none',
                    number_of_memories=1,
                    step_idx=None,
                    #amplitudes = _I_['amplitudes'],
                    laser_dur=_I_['laser_dur']*factor,
                    buffer_time = _I_['buffer_time'],
                    cw_mw = _I_['cw_mw'],

                )
                if 'amplitudes' in _I_.keys():
                    pd['amplitudes'] = _I_['amplitudes']
                if 'pi_pulse_factor' in _I_.keys():
                    pd['pi_pulse_factor'] = _I_['pi_pulse_factor']
                sna.ssr(mcas, **pd)

            mcas.start_new_segment('Final')

            mcas.asc(length_mus=0.128)
            # mcas.asc(length_mus=0.1, memory=True, name='memory')
            # mcas.asc(length_mus=0.1)

            return mcas


        if hasattr(self, 'mcas'):
            del self.mcas
        if val is None:
            self._ret_mcas = ret_mcas
        elif hasattr(val, '__call__'):
            self._ret_mcas = val

    def setup_rf(self, ls):
        #hash = base64.b64encode(hashlib.sha1(str(ls)).digest())
        sequence_name = "odmr"#_{}".format(hash)
        if True:#not sequence_name in pi3d.mcas_dict:
            self.q._awg.mcas_dict[sequence_name] = self.ret_mcas(ls, sequence_name=sequence_name)
        self.q._awg.mcas_dict[sequence_name].initialize()
        self.q._awg.mcas_dict[sequence_name].start_awgs()