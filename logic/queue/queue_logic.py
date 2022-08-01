# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type

import sys, os
import logic.misc
import imp
from gui.queue.Queue import queue_gui

from queue import Queue

from PyQt5.QtWidgets import QAbstractItemView, QMainWindow, QFileDialog
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
import PyQt5.uic
import PyQt5.QtWidgets
from logic.qudip_enhanced import *
# FIXME

# import multi_channel_awg_seq as MCAS; reload(MCAS)
import logic.misc as misc
import datetime
import logging.handlers
import os
import pickle
import sys
import threading
import time
import traceback
from logic.generic_logic import GenericLogic
from core.connector import Connector
import multiprocess
import numpy as np
import logging

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

    # declare connections
    # MCAS
    mcas_holder = Connector(interface='McasDictHolderInterface')
    # Transition tracker
    transition_tracker = Connector(interface = 'TransitionTracker') # Should be a name of the class
    #confocal = Connector('ConfocalLogic')
    # Gated counter.
    gated_counter = Connector('GatedCounter') # Should be name of the class.
    update_selected_user_script_combo_box_signal = pyqtSignal(collections.OrderedDict)
    user_script_list = misc.ret_property_array_like_typ('user_script_list', str)
    guis = []  # stores names of all open guis (later on used to dump them periodically)
    _StopTimeout = 60.

    __TIME_FORMAT_STR__ = '%Y%m%d-h%Hm%Ms%S'

    # smiq_visa_device = 'GPIB0::28::INSTR'
    # app_dir = r'D:/Python/pi3diamond'
    # log_dir = '{}/log/'.format(app_dir)
    # log_archive_dir = '{}/log/archive/'.format(app_dir)
    # log_single_val_dir = '{}/log/single_values/'.format(app_dir)
    # log_tmp = '{}/log/temp/'.format(app_dir)

    def __init__(self, config , **kwargs):
        super(queue_logic, self).__init__(config=config, **kwargs)

        self.script_history = []

    def on_activate(self):

        self._awg = self.mcas_holder()  #self._mcas_dict = self.mcas_holder()#float(9)#self.mcas_holder()  # mcas_dict()
        self._transition_tracker = self.transition_tracker()#float(10)#self.transition_tracker()
        self._gated_counter = self.gated_counter() # connection to the GC.
        self.init_run() #
        self.write_standard_awg_sequences()
        # TODO we are adding confocal later.
        #self._confocal = self.confocal()

    def on_deactivate(self):
        pass
        #FIXME destroy me gently

    @property
    def md(self):
        return self._mcas_dict#

    @property
    def gui(self):
        return self._gui

    # def restart_timetagger(self):
    #     import TimeTaggerHandler
    #     reload(TimeTaggerHandler)
    #     self._timetagger = TimeTaggerHandler.init_timetagger()

    def init_run(self):
        self.user_script_folder = r"/Users/vvv/Documents/GitHub/qudi/notebooks/UserScripts/electron_t2"
        self._script_queue = ScriptQueueList(oktypes=(ScriptQueueStep), list_owner=self)
        self.q = Queue() # use connector
        self.run_thread()
        # self.track_memory_usage_thread()

    @property
    def script_queue(self):
        return self._script_queue
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
    #
    def restore(self, model, fp=None):
        filename = self.persistent_file_name(model) if fp is None else fp

        if os.access(filename, os.F_OK):

            self.log.info('Restoring state of ' + model.__str__() + '\nfrom ' + filename + '..')

            try:
                a = pickle.load(open(filename, 'rb'))
                a = a if type(a) is dict else a.__getstate__()
                model.set_items(a)
                self.log.info('[DONE1]')

            except Exception as inst:
                self.log.exception(str(inst))
                self.log.warning('[FAILED]')
                raise inst

    def dump(self, model):
        filename = self.persistent_file_name(model)
        self.log.info('attempting to save state of ' + model.__str__() + '\nto ' + filename + '..', )
        try:
            fil = open(filename, 'wb')
            pickle.dump(model.__getstate__(), fil)
            fil.close()
            self.log.info('[DONE]')
        except Exception:
            self.log.exception(str(Exception))
            self.log.warning('[FAILED]')

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


        ## Why this is needed??????

        #from tools_2 import emod
        #emod.JobManager().start()

        # start the CronDaemon
        #from tools_2 import cron
        #cron.CronDaemon().start()
        self.dummy_test_variable = 123

        while True:
            if self.thread.stop_request.is_set():
                self.q.queue.clear()
                self.script_queue.list = []
                self.thread.stop_request.clear()
            try: ### runs the measurement!
                self.current_script = self.q.get()
                self.thread.stop_request.clear() # this is necessary although it shouldn't be.
                self.log.info("Starting Userscript {}...{}".format(
                    self.current_script['module_name'][10:],
                   self.thread.stop_request.is_set()))
                sys.modules[self.current_script['module_name']].run_fun(
                    self.thread.stop_request, queue = self, **self.current_script['pd']) ## Creates a nuclear and runs it.!!!

                self.script_history.append(self.current_script)
                self.script_queue.pop(0)
                self.log.info("Userscript {} has finished...".format(self.current_script['module_name'][10:]))
                del self.current_script
                self.q.task_done()
            except Exception: #Not running the measurement.
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
            #if hasattr(self, '_gui'):
            val = collections.OrderedDict([('user_script_list', self.user_script_list), ('selected_user_script', self.selected_user_script)])

            #self.update_selected_user_script_combo_box(val)
            #Instead emit a signal which will updates it.
            self.update_selected_user_script_combo_box_signal.emit(val)

    @property
    def selected_user_script(self):
        return self._selected_user_script

    @selected_user_script.setter
    def selected_user_script(self, val):
        if val != '':
            if val not in self.user_script_list:
                raise Exception('Script {} not in {}'.format(val, self.user_script_list))
            self._selected_user_script = val
            #if hasattr(self, '_gui'):
            val = collections.OrderedDict([('selected_user_script', self.selected_user_script)])
            self.update_selected_user_script_combo_box_signal.emit(val)
            #self.gui.update_selected_user_script_combo_box(val)

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
            #This now is done in gui automatically.
            #if hasattr(self, '_gui'):
                #self.gui.update_user_script_folder_text_field(val)

    def add_to_queue(self, name=None, pd=None, folder=None):
        #self.confocal.counter_state = 'idle'
        #self.md.stop_awgs()
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
        folder = r"/Users/vvv/Documents/GitHub/qudi/notebooks/UserScripts"
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
        self.add_to_queue('standard_awg_sequences', folder=r'/Users/vvv/Documents/GitHub/qudi/notebooks/UserScripts/helpers')

    def dl(self, key, *args, **kwargs):
        return self._mcas_dict[key].dl(*args, **kwargs)

    def save_pi3diamond(self, destination_dir):
        src = os.getcwd()
        f = '{}/qudi.zip'.format(destination_dir)
        if not os.path.isfile(f):
            zf = zipfile.ZipFile(f, 'a')
            for root, dirs, files in os.walk(src):
                if (not any([i in root for i in ['__pycache__',
                                                 'awg_settings',
                                                 'currently_unused',
                                                 ".idea",
                                                 ".hg",
                                                 'UserScripts',
                                                 'log'
                                                 ]
                             ]
                            )
                ) or root.endswith('transition_tracker_log') or root.endswith('helpers'):
                    for file in files:
                        if any([file.endswith(i) for i in ['.py', '.dat', '.ui']]):
                            zf.write(os.path.join(root, file), os.path.join(root.replace(os.path.commonprefix([root, src]), ""), file))
            zf.close()