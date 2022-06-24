# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import sys, os
import misc
import imp
from Queue import Queue

from PyQt5.QtWidgets import QAbstractItemView, QMainWindow, QFileDialog
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
import PyQt5.uic
import PyQt5.QtWidgets
from logic.qudip_enhanced import *

# FIXME
# import multi_channel_awg_seq as MCAS; reload(MCAS)

import datetime
import logging.handlers
import os
import pickle
import sys
import threading
import time
import traceback
from logic.generic_logic import GenericLogic

import multiprocess
import numpy as np

import collections


class ScriptQueueStep:
    def __init__(self, name, pd):
        self.name = name
        self.pd = pd


class ScriptQueueList(collections.MutableSequence):
    def __init__(self, oktypes, list_owner, *args):
        self.oktypes = oktypes
        self.list_owner = list_owner
        self._list = list()
        self.extend(list(args))

    @property
    def list(self):
        return self._list

    @list.setter
    def list(self, val):
        """
        inefficient, calls script_queue_changed multiple times. In practice not relevant.
        """
        self._list = []
        if len(val) == 0:
            self.list_owner.script_queue_changed()
        else:
            try:
                for i in val:
                    self.append(i)
            except Exception:
                self._list = []
                self.list_owner.script_queue_changed()
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)

    def check(self, val):
        if not isinstance(val, self.oktypes):
            raise TypeError("list item {} is not allowed, as it can not be found in {}".format(val, self.oktypes))

    # def check_duplicate(self, v):
    #     duplicates = [item.name for item in self.list if item.name == v.name]
    #     if len(duplicates) > 0:
    #         raise Exception('Error: {}, {}, {}'.format(duplicates, self.list, v))

    def set_parent(self, v):
        v.parent = self.list_owner

    def __len__(self):
        return len(self.list)

    def __getitem__(self, i):
        return self.list[i]

    def __delitem__(self, i):
        del self.list[i]
        self.list_owner.script_queue_changed()

    def __setitem__(self, i, v):
        raise NotImplementedError
        # self.check(v)
        # self.check_duplicate(v)
        # self.list[i] = v
        # self.list_owner.script_queue_changed(i, v)

    def insert(self, i, v):
        if i != len(self.list):
            raise Exception('Only appending and popping items allowed')
        self.check(v)
        # self.check_duplicate(v)
        self.list.insert(i, v)
        self.list_owner.script_queue_changed()

    def __str__(self):
        return str(self.list)

    def __repr__(self):
        return str(self.list)


class queue_logic(GenericLogic):
    def __init__(self, config , **kwargs):
        super(queue_logic, self).__init__(config,**kwargs)
        # for property_name in ['confocal', 'nidaq', 'fast_counter', 'odmr', 'timetagger', 'pp',
        #                       'gated_counter', 'nuclear', 'magnet', 'tt', 'pulsed', 'powermeter', 'oxxius_laser',
        #                       'rf_amp', 'misc', 'Fit', 'Analysis', 'multi_channel_awg_sequence', 'magnet_stage_micos',
        #                       'microwave', 'mcas_dict']:

        # setattr(self.__class__, property_name, property(attrgetter(property_name)))


        self.script_history = []
        # self.init_run()




        # if os.path.exists(self.log_single_val_dir + 'single_values.hdf'):
        #     dh.ptrepack('single_values.hdf', self.log_single_val_dir)

    @property
    def md(self):
        return self._mcas_dict

    @property
    def gui(self):
        return self._gui

    # def restart_timetagger(self):
    #     import TimeTaggerHandler
    #     reload(TimeTaggerHandler)
    #     self._timetagger = TimeTaggerHandler.init_timetagger()

    def init_run(self):
        self.user_script_folder = r'D:/Python/pi3diamond/UserScripts/'
        self._script_queue = ScriptQueueList(oktypes=(ScriptQueueStep), list_owner=self)
        self.q = Queue()
        self.run_thread()
        # self.track_memory_usage_thread()

    # app_dir = r'D:/Python/pi3diamond'
    # log_dir = '{}/log/'.format(app_dir)
    # log_archive_dir = '{}/log/archive/'.format(app_dir)
    # log_single_val_dir = '{}/log/single_values/'.format(app_dir)
    # log_tmp = '{}/log/temp/'.format(app_dir)

    guis = []  # stores names of all open guis (later on used to dump them periodically)

    _StopTimeout = 60.

    log_level = logging.INFO

    workspace_dir = 'log/'

    __TIME_FORMAT_STR__ = '%Y%m%d-h%Hm%Ms%S'

    scanner_xrange = (0.0, 30.0)
    scanner_yrange = (0.0, 30.0)
    scanner_zrange = (-25, 25.0)

    #colormaps = {'default': Spectral, 'confocal': jet}
    #smiq_visa_device = 'GPIB0::28::INSTR'

    @property
    def script_queue(self):
        return self._script_queue

    user_script_list = misc.ret_property_array_like_typ('user_script_list', str)

    @property
    def nowstr(self):
        return datetime.datetime.now().strftime('%Y%m%d-h%Hm%Ms%S')

    @property
    def nowstr_colon(self):
        return datetime.datetime.now().strftime('%Y/%m/%d-%H:%M:%S')

    @property
    def nowstr_pd(self):
        return datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')

    @property
    def awgs(self):
        return self._mcas_dict.awgs



    ####################################################################################################################
    # dump and restore
    ####################################################################################################################

    def persistent_file_name(self, model):
        if hasattr(model, 'pi3d_dump_filename'):
            return self.log_dir + model.pi3d_dump_filename
        return self.log_dir + str(model.__class__).replace('>', '').replace('<',

                                                                            '') + '.pyd'  # windows does not allow '>' and '<' in filenames

    def restore(self, model, fp=None):
        filename = self.persistent_file_name(model) if fp is None else fp

        if os.access(filename, os.F_OK):

            self.logger.info('Restoring state of ' + model.__str__() + '\nfrom ' + filename + '..')

            try:
                a = pickle.load(open(filename, 'rb'))
                a = a if type(a) is dict else a.__getstate__()
                model.set_items(a)
                self.logger.info('[DONE1]')

            except Exception as inst:
                self.logger.exception(str(inst))
                self.logger.warning('[FAILED]')
                raise inst


    def dump(self, model):
        filename = self.persistent_file_name(model)
        self.logger.info('attempting to save state of ' + model.__str__() + '\nto ' + filename + '..', )
        try:
            fil = open(filename, 'wb')
            pickle.dump(model.__getstate__(), fil)
            fil.close()
            self.logger.info('[DONE]')
        except Exception:
            self.logger.exception(str(Exception))
            self.logger.warning('[FAILED]')

    # @property
    # def current_nuclear(self):
    #     l = [i for i in self.__dict__ if 'Nuclear' in i]
    #     df = pd.DataFrame({'attr_name': l, 'date': [datetime.datetime.strptime(i[-17:], '%Y%m%dh%Hm%Ms%S') for i in l]})
    #     return getattr(self, df[df['date'] == df['date'].max()].iloc[0, 0])

    @property
    def script_module_names(self):
        return [i for i in sys.modules if '__script__' in i]

    @property
    def last_running_script_name(self):
        sm = self.script_module_names
        if hasattr(self, 'current_script'):
            if not self.current_script['module_name'] in sm:
                raise Exception('Error: {}, {}'.format(sm, self.current_script))
            else:
                return self.current_script['module_name']
        else:
            return sm[-1]
    @property
    def cun_modules(self):
        lrs = self.last_running_script_name
        if hasattr(sys.modules[lrs], 'nuclear'):
            return sys.modules[lrs]
        else:
            for smi in self.script_module_names[::-1]:
                if hasattr(sys.modules[smi], 'nuclear'):
                    return sys.modules[smi]

    @property
    def cun(self):
        return self.cun_modules.nuclear

    # ####################################################################################################################
    # # single values
    # ####################################################################################################################
    # def latest_file_fn(self, fn_no_date, folder):
    #     file_list = sorted(os.listdir((folder)))
    #     return [s for s in file_list if fn_no_date in s][-1]
    #
    # def get_path_for_save_value_to_file(self, filename):
    #     now = datetime.datetime.now()
    #     full_path = self.log_single_val_dir + os.path.splitext(filename)[0] + '/' + now.strftime('%Y%m') + filename + '.dat'
    #     return full_path
    #
    # def date_str_in(self, date_str, start_date_str=None, end_date_str=None):
    #     date = datetime.datetime.strptime(date_str, self.__TIME_FORMAT_STR__)
    #     start_date = datetime.datetime.min if start_date_str is None else datetime.datetime.strptime(start_date_str, self.__TIME_FORMAT_STR__)
    #     end_date = datetime.datetime.now() if end_date_str is None else datetime.datetime.strptime(end_date_str, self.__TIME_FORMAT_STR__)
    #     return start_date <= date <= end_date
    #
    # def save_value_to_file(self, val, filename):
    #     """Appends a given value 'val' to a text file with filename 'yymmdd_filename' (e.g. 130101_temperature.dat) and adds the current date and time (format'yymmdd hhmmss) separated by a tab. '
    #     """
    #     full_path = self.get_path_for_save_value_to_file(filename)
    #     folder = os.path.dirname(full_path)
    #     if not os.path.isdir(self.log_single_val_dir):
    #         os.mkdir(self.log_single_val_dir)
    #     if not os.path.isdir(folder):
    #         os.mkdir(folder)
    #     now = datetime.datetime.now()
    #     fil = open(full_path, 'a')
    #     fil.write(now.strftime('%Y%m%d-h%Hm%Ms%S') + '\t' + str(val) + '\n')
    #     fil.close()
    #
    # def save_values_to_file(self, val, filename, full_path=None):
    #     full_path = self.get_path_for_save_value_to_file(filename) if full_path is None else full_path
    #     folder = os.path.dirname(full_path)
    #     if not os.path.isdir(self.log_single_val_dir):
    #         os.mkdir(self.log_single_val_dir)
    #     if not os.path.isdir(folder):
    #         os.mkdir(folder)
    #     now = datetime.datetime.now()
    #     fil = open(full_path, 'a')
    #     fil.write(now.strftime('%Y%m%d-h%Hm%Ms%S') + '\t' + '\t'.join(str(v) for v in val) + '\n')
    #     fil.close()
    #
    # def get_last_value_from_file(self, filename, flg_out_date=False):
    #     folder = os.path.dirname(self.get_path_for_save_value_to_file(filename))
    #     file_list = sorted(os.listdir((folder)))
    #     last_file_name = [s for s in file_list if filename in s][-1]
    #     fil = open(folder + '\\' + last_file_name, 'r')
    #     line_str_list = fil.readlines()[-1].split('\t')
    #     fil.close()
    #
    #     if 'fit_params' in filename or 'history' in filename:
    #         val = np.array(line_str_list[-1].rstrip('\n'))
    #     else:
    #         val = float(line_str_list[-1].rstrip('\n'))
    #     if flg_out_date == True:
    #         date = datetime.datetime.strptime(line_str_list[0], '%Y%m%d-h%Hm%Ms%S')
    #         return val, date
    #     return val
    #
    # def get_last_values_from_file(self, filename, flg_out_date=False, full_path=None):
    #     if full_path is None:
    #         folder = os.path.dirname(self.get_path_for_save_value_to_file(filename))
    #         file_list = sorted(os.listdir((folder)))
    #         last_file_name = [s for s in file_list if filename in s][-1]
    #         full_path = folder + '\\' + last_file_name
    #     else:
    #         full_path = self.get_path_for_save_value_to_file(filename) if full_path is None else full_path
    #     fil = open(full_path, 'r')
    #
    #     line_str_list = fil.readlines()[-1].split('\t')
    #     line_str_list[-1].rstrip('\n')
    #     fil.close()
    #     val = []
    #     for i in line_str_list[1:]:
    #         try:
    #             val.append(float(i))
    #         except:
    #             val.append(i.rstrip('\n'))
    #     if flg_out_date is True:
    #         date = datetime.datetime.strptime(line_str_list[0], '%Y%m%d-h%Hm%Ms%S')
    #         return val, date
    #     return val
    #
    # def get_values_time_span(self, filename, start_date_str, end_date_str=None):
    #     folder = os.path.dirname(self.get_path_for_save_value_to_file(filename))
    #     file_list = sorted(os.listdir(folder))
    #     result = {'dates': [], 'data': []}
    #     for fn in file_list:
    #         try:
    #             file_date_str = datetime.datetime.strptime(fn[0:6], '%Y%m').strftime(self.__TIME_FORMAT_STR__)
    #         except:
    #             file_list.remove(fn)
    #             continue
    #         with open("{}/{}".format(folder, fn), 'r') as f:
    #             for l in f:
    #                 l = l.rstrip('\n').split('\t')
    #
    #                 if self.date_str_in(l[0], start_date_str, end_date_str):
    #                     result['dates'].append(datetime.datetime.strptime(l[0], self.__TIME_FORMAT_STR__))
    #                     result['data'].append(l[1:])
    #     result['data'] = np.array(result['data'])
    #     return result

    # def plot_single_values(self, filename, start_date_str, end_date_str=None, grating='m'):
    #     values = self.get_values_time_span(filename=filename, start_date_str=start_date_str, end_date_str=end_date_str)
    #     if end_date_str is None:
    #         end_date_str = datetime.datetime.now()
    #     else:
    #         end_date_str = datetime.datetime.strptime(end_date_str, self.__TIME_FORMAT_STR__)
    #     grating_dict = {'h': 1. / 60. / 60., 'm': 1. / 60., 's': 1.}
    #     labeldict = {'magnet_gradients': ['x', 'y'], 'confocal_pos': ['x', 'y', 'z'], 'magnet_pos': ['x', 'y', 'z', 'phi'], 'current_local_oscillator_freq': 'local oscillator'}
    #     legenddict = {'magnet_gradients': 'MHz/mu m', 'confocal_pos': 'mu m', 'magnet_pos': 'mu m', 'current_local_oscillator_freq': 'MHz'}
    #     precisiondict = {'magnet_gradients': 6, 'confocal_pos': 4, 'magnet_pos': 4, 'current_local_oscillator_freq': 3}
    #     tdelta = np.array([(values['dates'][i] - end_date_str).total_seconds() for i in range(len(values['dates']))]) * grating_dict['{}'.format(grating)]
    #     num_single_values = len(values['data'][0])
    #     num_dp = len(tdelta)
    #     data = dict()
    #     for num in range(num_single_values):
    #         data[num] = np.array([values['data'][i][num] for i in range(num_dp)]).astype(float)
    #     import matplotlib.pyplot as plt
    #     import matplotlib.ticker
    #     fig, axes = plt.subplots(num_single_values)
    #     fig.suptitle(filename + ' since ' + '{}'.format(values['dates'][0].strftime('%Y%m%d-h%Hm%Ms%S')))
    #     if num_single_values != 1:
    #         for sv in range(num_single_values):
    #             axes[sv].plot(tdelta, data[sv], 'o-', label=labeldict[filename][sv])
    #             axes[sv].yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.{}f'.format(precisiondict[filename])))
    #             axes[sv].legend()
    #             axes[sv].set_ylabel(legenddict[filename])
    #             axes[sv].set_xlabel('time [{}]'.format(grating))
    #     else:
    #         axes.plot(tdelta, data[0], 'o-', label=labeldict[filename])
    #         axes.legend()
    #         axes.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.{}f'.format(precisiondict[filename])))
    #         axes.set_ylabel(legenddict[filename])
    #         axes.set_xlabel('time [s]')
    #     plt.show()

    # def save_values_hdf(self, classifier, vd, dt=None, full_path=None):
    #     # classifier='concal_pos'
    #     # vd=dict(x=11, y=12)
    #     # dt=None
    #     # full_path=None
    #     # import time
    #     # t0 = time.time()
    #     # import datetime
    #     # self = pi3d
    #     # import pandas as pd
    #     # import subprocess
    #     #
    #     #
    #     # for i in range(1000):
    #     dt = datetime.datetime.now() if dt is None else dt
    #     full_path = "{}/single_values.hdf".format(self.log_single_val_dir) if full_path is None else full_path
    #     folder = os.path.dirname(full_path)
    #     if not os.path.isdir(self.log_single_val_dir):
    #         os.mkdir(self.log_single_val_dir)
    #     if not os.path.isdir(folder):
    #         os.mkdir(folder)
    #     sdt = pd.Series([dt]*len(vd), name='datetime')
    #     cdt = pd.Series([classifier]*len(vd), name='classifier')
    #     dfd = pd.DataFrame(vd.items(), columns=['subclassifier', 'value'])
    #     df = pd.concat([sdt, cdt, dfd], axis=1)
    #     store = pd.HDFStore(full_path)
    #     store.append(key='df', value=df, table=True, append=True, index=False, mode='w')
    #     store.close()

    def track_memory_usage(self):
        while True:
            self.save_value_to_file(self.current_memory_usage(), 'memory_mb')
            # CAREFUL WITH THREADING AND WRITING TO SAME HDF FILE self.save_values_hdf(classifier='memory_mb', vd=dict(none=self.current_memory_usage()))
            # possible solution: https://stackoverflow.com/questions/22522551/pandas-hdf5-as-a-database
            time.sleep(5)

    # def current_memory_usage(self):
    #     print(os.getpid())
    #     p = psutil.Process(os.getpid())
    #     return p.memory_info()[0] / 1024.
    #
    # def track_memory_usage_thread(self):
    #     self.tmu_thread = threading.Thread(target=self.track_memory_usage)
    #     self.tmu_thread.stop_request = multiprocess.Event()
    #     self.tmu_thread.start()

    def script_queue_changed(self):
        self.update_script_queue_table_data()

    @property
    def script_queue_table_data(self):
        return self._script_queue_table_data

    def update_script_queue_table_data(self):
        out = collections.OrderedDict([('name', []), ('pd', [])])
        for ridx, i in enumerate(self.script_queue):
            for cidx, attr_name in enumerate(['name', 'pd']):
                out[attr_name].append(getattr(i, attr_name))
        self._script_queue_table_data = out
        if hasattr(self, '_gui'):
            self.gui.update_script_queue_table_data(self.script_queue_table_data)

    ####################################################################################################################
    # script queue
    ####################################################################################################################
    def run(self):

        from tools import emod
        emod.JobManager().start()

        # start the CronDaemon
        from tools import cron
        cron.CronDaemon().start()


        while True:
            if self.thread.stop_request.is_set():
                self.q.queue.clear()
                self.script_queue.list = []
                self.thread.stop_request.clear()
            try:
                self.current_script = self.q.get()
                self.thread.stop_request.clear() # this is necessary although it shouldnt be.
                self.logger.info("Starting Userscript {}...{}".format(self.current_script['module_name'][10:], pi3d.thread.stop_request.is_set()))
                sys.modules[self.current_script['module_name']].run_fun(self.thread.stop_request, **self.current_script['pd'])
                self.script_history.append(self.current_script)
                self.script_queue.pop(0)
                self.logger.info("Userscript {} has finished...".format(self.current_script['module_name'][10:]))
                del self.current_script
                self.q.task_done()
            except Exception:
                self.q.queue.clear()
                self.script_queue.list = []
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)

    def run_thread(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.stop_request = multiprocess.Event()
        self.thread.start()

    def set_user_script_list(self):
        file_list = []
        unwanted_files = ['__init__.py', 'refocus_confocal_odmr.py']
        for files in os.listdir(self.user_script_folder):
            if files.endswith(".py") and not files in unwanted_files:
                file_list.append(str(files.split('.')[0]))
        self._user_script_list = file_list
        if len(self.user_script_list) > 0:
            self._selected_user_script = self.user_script_list[0]
            if hasattr(self, '_gui'):
                val = collections.OrderedDict([('user_script_list', self.user_script_list), ('selected_user_script', self.selected_user_script)])
                self.gui.update_selected_user_script_combo_box(val)

    @property
    def selected_user_script(self):
        return self._selected_user_script

    @selected_user_script.setter
    def selected_user_script(self, val):
        if val != '':
            if val not in self.user_script_list:
                raise Exception('Script {} not in {}'.format(val, self.user_script_list))
            self._selected_user_script = val
            if hasattr(self, '_gui'):
                val = collections.OrderedDict([('selected_user_script', self.selected_user_script)])
                self.gui.update_selected_user_script_combo_box(val)

    @property
    def user_script_params(self):
        return getattr(self, '_user_script_params', {})

    @user_script_params.setter
    def user_script_params(self, val):
        self.user_script_params = misc.check_type(val, 'user_script_params', dict)

    @property
    def user_script_folder(self):
        return self._user_script_folder

    @user_script_folder.setter
    def user_script_folder(self, val):
        if os.path.isdir(val):
            self._user_script_folder = val
            self.set_user_script_list()
            if hasattr(self, '_gui'):
                self.gui.update_user_script_folder_text_field(val)

    def add_to_queue(self, name=None, pd=None, folder=None):
        self.confocal.counter_state = 'idle'
        self.md.stop_awgs()
        folder = self.user_script_folder if folder is None else folder
        name = self.selected_user_script if name is None else name
        pd = self.user_script_params if pd is None else pd
        if name == '':
            return
        try:
            module_name = self.init_task(name, folder)
            self.q.put({'module_name': module_name, 'pd': pd})
            self.script_queue.append(ScriptQueueStep(module_name[10:], self.user_script_params))
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    def add_rco(self):
        folder = 'D:/Python/pi3diamond/UserScripts/'
        name = 'refocus_confocal_odmr'
        pd = self.user_script_params
        self.add_to_queue(name, pd, folder)

    def in_script_queue(self, name):
        for step in self.script_queue:
            if step.name == name:
                return True
        else:
            return False

    def evaluate(self):
        raise NotImplementedError
        # name = self.selected_user_script
        # pd = self.user_script_params
        # if self.in_script_queue(name):
        #     raise Exception("Running the 'evaluate' function of a script is only possible when its 'run_fun' is not running.")
        # else:
        #     self.get_user_script(name).evaluate(**pd)

    def remove_last_script(self):
        if self.q.qsize() > 0:
            del self.script_queue[-1]
            self.q.get()

    def init_task(self, name, folder=None):
        folder = self.user_script_folder if folder is None else folder
        funa = "{}/{}.py".format(folder, name)
        task_name = "__script__{}_{}".format(self.nowstr, name)
        _ = imp.load_source(task_name, funa)
        return task_name

    def set_stop_request(self):
        self.thread.stop_request.set()

    def write_standard_awg_sequences(self):
        self.add_to_queue('standard_awg_sequences', folder='D:/Python/pi3diamond/UserScripts/helpers')

    def dl(self, key, *args, **kwargs):
        return self._mcas_dict[key].dl(*args, **kwargs)




    ####################################################################################################################
    # GUI
    ####################################################################################################################
    # def show_gui(self, module_names):
    #     for module_name in module_names:
    #         self.show_subgui(module_name)

    # def get_odmr(self):
    #     if not hasattr(self, 'odmr'):
    #         # from ODMR_3T import ODMR
    #         from ODMR import ODMR
    #         self.odmr = ODMR()
    #     return self.odmr


    # def show_subgui(self, name):
    #     if name == 'confocal':
    #         getattr(self, 'confocal').edit_traits(view='MainView')
    #         getattr(self, 'confocal').edit_traits(view='TrackerView')
    #         getattr(self, 'confocal').edit_traits(view='TraceView')
    #         self.restore(model=getattr(self, name))
    #         self.confocal.reset_settings()
    #         self.guis.append(name)
    #     elif name == 'oxxius_laser':
    #         print('no gui available for oxxius_laser')
    #
    #     elif name == 'ple_Ex':
    #         # print('name == ple should show gui')
    #         getattr(self, name).edit_traits()
    #     elif name == 'ple_repump':
    #         # print('name == ple should show gui')
    #         getattr(self, name).edit_traits()
    #
    #     elif name == 'ple_A1':
    #         # print('name == ple should show gui')
    #         getattr(self, name).edit_traits()
    #     elif name == 'gated_counter':
    #         pi3d.gated_counter.gui.show()
    #     elif name == 'corr_meas':
    #         pi3d.corr_meas.gui.show()
    #     elif name == 'interferometer':
    #         pi3d.interferometer.gui.show()
    #
    #
    #     elif name == 'tt':
    #         pi3d.tt.show()
    #     elif name == 'odmr':
    #         # self.show_odmr()
    #
    #         if hasattr(pi3d.odmr.pld, '_gui'):
    #             pi3d.odmr.pld.gui.show()
    #     elif name == 'orabi':
    #         # self.show_odmr()
    #
    #         if hasattr(pi3d.orabi.pld, '_gui'):
    #             pi3d.orabi.pld.gui.show()
    #     elif 'mcas_dict' in name:
    #         return
    #     else:
    #         getattr(self, name).edit_traits()
    #         if name not in ['tt', 'nuclear', 'gated_counter']:
    #             self.restore(model=getattr(self, name))
    #         if name not in self.guis:
    #             self.guis.append(name)

    def save_pi3diamond(self, destination_dir):
        src = os.getcwd()
        f = '{}/qudi.zip'.format(destination_dir)
        if not os.path.isfile(f):
            zf = zipfile.ZipFile(f, 'a')
            for root, dirs, files in os.walk(src):
                if (not any([i in root for i in ['__pycache__', 'awg_settings', 'currently_unused', ".idea", ".hg", 'UserScripts', 'log']])) or root.endswith('transition_tracker_log') or root.endswith('helpers'):
                    for file in files:
                        if any([file.endswith(i) for i in ['.py', '.dat', '.ui']]):
                            zf.write(os.path.join(root, file), os.path.join(root.replace(os.path.commonprefix([root, src]), ""), file))
            zf.close()