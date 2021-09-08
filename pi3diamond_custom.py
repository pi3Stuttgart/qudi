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
from qutip_enhanced import *
import multi_channel_awg_seq as MCAS; reload(MCAS)


import sip

try:
    sip.setapi('QDate', 2)
    sip.setapi('QDateTime', 2)
    sip.setapi('QString', 2)
    sip.setapi('QtextStream', 2)
    sip.setapi('Qtime', 2)
    sip.setapi('QUrl', 2)
    sip.setapi('QVariant', 2)
except ValueError as e:
    raise RuntimeError('Could not set API version (%s): did you import PyQt4 directly?' % e)

import datetime
import logging
import logging.handlers
import os
import pickle
import shutil
import sys
import threading
import time
import traceback
import TimeTaggerHandler

import multiprocess
import numpy as np
import psutil
import collections
from chaco.api import Spectral,jet


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

def attrgetter(name):
    def get_any(self):
        nname = '_' + name
        if not hasattr(self, nname):
            if name == 'confocal':
                from Confocal import Confocal
                val = Confocal()
                val.x, val.y, val.z = self.get_last_values_from_file('confocal_pos')
            # if name == 'microwave':
            #     from Anritsu import Anritsu
            #     val = Anritsu()
            #
            if name == 'microwave':
                from SMIQ import SMIQ
                val = SMIQ()

            if name == 'nidaq':
                from NIDAQ import NIDAQ
                val = NIDAQ(
                    photon_source=str('/Dev4/PFI12'),
                    function_counter_in=str('/Dev4/Ctr2'),
                    # counter 2 und 3 werden fuer scanning, odmr etc benutzt
                    function_counter_out=str('/Dev4/Ctr3'),
                    # dieser counter macht die trigger fuers odmr
                    scanner_ao_channels=str('/Dev4/ao0:2'),
                    scanner_ai_channels=str('/Dev4/ai0:2'),
                    scanner_xrange=self.scanner_xrange,
                    scanner_yrange=self.scanner_yrange,
                    scanner_zrange=self.scanner_zrange,
                    odmr_trig_channel=str('/Dev4/PFI7'),
                )
            if name == 'fast_counter':
                import Pyro.core
                val = Pyro.core.getProxyForURI('PYROLOC://192.168.137.201:2000/FastComTec')
            # if name == 'odmr':
            #     from ODMR import ODMR
            #     val = ODMR()
            if name == 'odmr':
                # from ODMR_3T import ODMR
                from ODMR import ODMR
                val = ODMR()
            if name == 'orabi':
                from ORABI import ORABI
                val = ORABI()
            if name == 'ple_A1':
                from NIDAQ import PLESweeper
                from ple_complete_A1 import PLE_A1 as PLE

                from pulse_streamer_ import PulseStreamerPGProxy

                plesweeper_A1 = PLESweeper(
                    CounterIn='/Dev4/Ctr0',  # was /Dev4/Ctr2
                    CounterOut='/Dev4/Ctr1',  # was /Dev4/Ctr3
                    TickSource=str('/Dev4/PFI12'),  # was 12
                    TriggerIn="/Dev4/PFI0",
                    AOChannels='/Dev3/AO0',
                    AIChannels="/Dev4/AI0",
                    v_range=(-3, 3))

                pulse_generator = PulseStreamerPGProxy(
                    channel_map={'ple_trigger': 0, 'detect': 1, 'sequence': 2, 'aom_Ex': 3, 'odmrgate': 4,
                                 'microwave_2': 5,
                                 'aom_A1': 6, 'repump': 7})
                # channel_map = {'aom': 0, 'detect': 1, 'sequence': 2, 'microwave': 3, 'odmrgate': 4, 'microwave_2': 5,
                #                'ple_trigger': 6, 'repump': 7})

                val = PLE(sweeper=plesweeper_A1, pulse_generator=pulse_generator,microwave= self.awgs['2g'])

            if name == 'wavemeter':
                from wavemeter import Wavemeter
                val = Wavemeter()

            if name == 'interferometer':
                from NIDAQ import PLESweeper
                from Interferometer_Stabilization import Interferometer_Stabilization

                # sweeper_interferometer = PLESweeper(
                #     CounterIn='/Dev4/Ctr0',  # was /Dev4/Ctr2
                #     CounterOut='/Dev4/Ctr1',  # was /Dev4/Ctr3
                #     TickSource=str('/Dev4/PFI12'),  # was 12
                #     TriggerIn="/Dev4/PFI0",
                #     AOChannels='/Dev3/AO4',
                #     AIChannels=None,
                #     v_range=(0, 5))
                sweeper_interferometer = PLESweeper(
                    CounterIn='/Dev4/Ctr1',  # was /Dev4/Ctr2
                    CounterOut='/Dev4/Ctr2',  # was /Dev4/Ctr3
                    TickSource=str('/Dev4/PFI13'),  # was 12
                    TriggerIn="/Dev4/PFI0",
                    AOChannels='/Dev3/AO4',
                    AIChannels=None,
                    v_range=(0, 10))



                val = Interferometer_Stabilization(sweeper=sweeper_interferometer)

            if name == 'ple_Ex':
                from NIDAQ import PLESweeper
                from ple_complete_Ex import PLE
                from pulse_streamer_ import PulseStreamerPGProxy

                plesweeper_Ex = PLESweeper(
                    CounterIn='/Dev4/Ctr0',  # was /Dev4/Ctr2
                    CounterOut='/Dev4/Ctr1',  # was /Dev4/Ctr3
                    TickSource=str('/Dev4/PFI12'),  # was 12
                    TriggerIn="/Dev4/PFI0",
                    AOChannels='/Dev3/AO1',
                    AIChannels="/Dev4/AI1",
                    v_range=(-2, 2))

                pulse_generator = PulseStreamerPGProxy(
                    channel_map={'ple_trigger': 0, 'detect': 1, 'sequence': 2, 'aom_Ex': 3, 'odmrgate': 4,
                                 'microwave_2': 5,
                                 'aom_A1': 6, 'repump': 7})
                # channel_map = {'aom': 0, 'detect': 1, 'sequence': 2, 'microwave': 3, 'odmrgate': 4, 'microwave_2': 5,
                #                'ple_trigger': 6, 'repump': 7})

                val = PLE(sweeper=plesweeper_Ex, pulse_generator=pulse_generator)

            if name == 'power_calibration':

                # AOM power output versus applied voltage
                import power_calibration_measurement as pc

                # pd = dict(
                #     pd_Ex_power=dict(channel="Dev4/ai0", samples_to_read=10, sampling_rate=1000.0),
                #     aom_Ex_power=dict(channel="Dev3/ao3", voltage=-7.5, name='aom_Ex_power'),  # -8 to +2 working range
                #     aom_green_power=dict(channel="Dev4/ao3", voltage=-3.0, name='aom_green_power')
                #     # -10 to -2 working range
                # )

                pd = dict(
                    pd_Ex_power=dict(channel="Dev4/ai0", samples_to_read=10, sampling_rate=1000.0),
                    pd_A1_power=dict(channel="Dev4/ai1", samples_to_read=10, sampling_rate=1000.0),
                    pd_Ex_integrator_voltage=dict(channel="Dev4/ai2", samples_to_read=10, sampling_rate=1000.0),
                    aom_Ex_power=dict(channel="Dev3/ao3", voltage=self.confocal.aom_voltage_Ex, name='aom_Ex_power'),  # -8 to +2 working range
                    aom_A1_power =dict(channel="Dev3/ao5", voltage=self.confocal.aom_voltage_A1, name='aom_A1_power'),  # -8 to +2 working range
                    aom_green_power=dict(channel="Dev4/ao3", voltage=self.confocal.aom_voltage_green, name='aom_green_power')
                    # -10 to -2 working range
                )



                val = pc.Power_calibration_measurement(pd)


            if name == 'timetagger':
                import TimeTaggerHandler
                val = TimeTaggerHandler.init_timetagger()
            if name == 'gated_counter':
                # try:
                from GatedCounter import GatedCounter
                val = GatedCounter(gui=True)
                # except Exception as inst:
                #     print(inst)
                #     print("Gated Counter could not be started, return None instead")
                #     return None

            if name == 'corr_meas':
                # try:
                from CorrMeas import CorrMeas
                val = CorrMeas(gui=True)

            if name == 'magnet':
                from Magnet import Magnet
                val = Magnet()
            if name == 'tt':
                from TransitionTracker import TransitionTracker
                val = TransitionTracker()
            if name == 'pulsed':
                import pulsed
                val = pulsed.Pulsed()
            if name == 'powermeter':
                from powermeter_thorlabs_PM100D import Powermeter
                val = Powermeter()
            if name == 'oxxius_laser':
                from oxxius_laser import Laser
                val = Laser()
            if name == 'rf_amp':
                from rf_amplifier_500A250A import Amp
                val = Amp()
            if name == 'misc':
                val = misc
            if name == 'Fit':
                import Fit
                val = Fit
            if name == 'Analysis':
                import Analysis
                val = Analysis
            if name == 'multi_channel_awg_sequence':
                import multi_channel_awg_seq
                val = multi_channel_awg_seq
            if name == 'magnet_stage_micos':
                import magnet_stage_micos
                val = magnet_stage_micos.Micos()
            if name == 'mcas_dict':
                import multi_channel_awg_seq
                val = multi_channel_awg_seq.MultiChSeqDict()
            setattr(self, nname, val)
        return getattr(self, nname)
    return get_any



class Pi3DiamondCustom:
    def __init__(self, *args, **kwargs):
        super(Pi3DiamondCustom, self).__init__()
        # for property_name in ['confocal', 'nidaq', 'fast_counter', 'odmr', 'timetagger', 'pp',
        #                       'gated_counter', 'nuclear', 'magnet', 'tt', 'pulsed', 'powermeter', 'oxxius_laser',
        #                       'rf_amp', 'misc', 'Fit', 'Analysis', 'multi_channel_awg_sequence', 'magnet_stage_micos',
        #                       'microwave', 'mcas_dict']:
        for property_name in ['confocal',
                              'nidaq',
                              'fast_counter',
                              'interferometer',
                              'wavemeter',
                              'ple_Ex',
                              'ple_A1',
                              'timetagger',
                              'pp',
                              'odmr',
                              'orabi',
                              'gated_counter',
                              'corr_meas',
                              'nuclear',
                              'magnet',
                              'tt',
                              'pulsed',
                              'misc',
                              'Fit',
                              'Analysis',
                              'multi_channel_awg_sequence',
                              'power_calibration',
                              'magnet_stage_micos',
                              'mcas_dict']:
            setattr(self.__class__, property_name, property(attrgetter(property_name)))
        if kwargs.get('gui', True):
            if 'gui' in kwargs:
                del kwargs['gui']
            self._gui = Pi3DiamondCustomQt(no_qt=self, *args, **kwargs)
        self.script_history = []
        self.init_run()




        # if os.path.exists(self.log_single_val_dir + 'single_values.hdf'):
        #     dh.ptrepack('single_values.hdf', self.log_single_val_dir)

    @property
    def md(self):
        return self.mcas_dict

    @property
    def gui(self):
        return self._gui

    def restart_timetagger(self):
        import TimeTaggerHandler
        reload(TimeTaggerHandler)
        self._timetagger = TimeTaggerHandler.init_timetagger()

    def init_run(self):
        self.user_script_folder = r'D:/Python/pi3diamond/UserScripts/'
        self._script_queue = ScriptQueueList(oktypes=(ScriptQueueStep), list_owner=self)
        self.q = Queue()
        self.run_thread()
        # self.track_memory_usage_thread()

    app_dir = r'D:/Python/pi3diamond'
    log_dir = '{}/log/'.format(app_dir)
    log_archive_dir = '{}/log/archive/'.format(app_dir)
    log_single_val_dir = '{}/log/single_values/'.format(app_dir)
    log_tmp = '{}/log/temp/'.format(app_dir)

    guis = []  # stores names of all open guis (later on used to dump them periodically)

    _StopTimeout = 60.

    log_level = logging.INFO

    workspace_dir = 'log/'

    __TIME_FORMAT_STR__ = '%Y%m%d-h%Hm%Ms%S'

    scanner_xrange = (0.0, 30.0)
    scanner_yrange = (0.0, 30.0)
    scanner_zrange = (-25, 25.0)

    colormaps = {'default': Spectral, 'confocal': jet}
    smiq_visa_device = 'GPIB0::28::INSTR'

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
        return self.mcas_dict.awgs

    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            # def handleError(self, *args, **kwargs):
            #     print("loggler_handleerror", args, kwargs)
            #     traceback.print_stack()

            # logging.Handler.handleError = handleError
            self._logger = logging.getLogger()
            ftrf = logging.Formatter("%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s")
            fh = logging.handlers.RotatingFileHandler(self.log_dir + 'diamond_log.txt', maxBytes=int(8*50e6), backupCount=100)
            # fh = logging.handlers.TimedRotatingFileHandler(self.log_dir + 'diamond_log.txt', 'W6')
            fh.setFormatter(ftrf)
            # fh.handleError = handleError
            for handler in self.logger.handlers:
                if type(handler) == logging.StreamHandler:
                    fhh = handler
                    break
            else:

                fhh = logging.StreamHandler()
                self._logger.addHandler(fhh)
            # fhh.handleError = handleError
            self._logger.addHandler(fh)
            self._logger.setLevel(self.log_level)
        return self._logger

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

    ####################################################################################################################
    # single values
    ####################################################################################################################
    def latest_file_fn(self, fn_no_date, folder):
        file_list = sorted(os.listdir((folder)))
        return [s for s in file_list if fn_no_date in s][-1]

    def get_path_for_save_value_to_file(self, filename):
        now = datetime.datetime.now()
        full_path = self.log_single_val_dir + os.path.splitext(filename)[0] + '/' + now.strftime('%Y%m') + filename + '.dat'
        return full_path

    def date_str_in(self, date_str, start_date_str=None, end_date_str=None):
        date = datetime.datetime.strptime(date_str, self.__TIME_FORMAT_STR__)
        start_date = datetime.datetime.min if start_date_str is None else datetime.datetime.strptime(start_date_str, self.__TIME_FORMAT_STR__)
        end_date = datetime.datetime.now() if end_date_str is None else datetime.datetime.strptime(end_date_str, self.__TIME_FORMAT_STR__)
        return start_date <= date <= end_date

    def save_value_to_file(self, val, filename):
        """Appends a given value 'val' to a text file with filename 'yymmdd_filename' (e.g. 130101_temperature.dat) and adds the current date and time (format'yymmdd hhmmss) separated by a tab. '
        """
        full_path = self.get_path_for_save_value_to_file(filename)
        folder = os.path.dirname(full_path)
        if not os.path.isdir(self.log_single_val_dir):
            os.mkdir(self.log_single_val_dir)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        now = datetime.datetime.now()
        fil = open(full_path, 'a')
        fil.write(now.strftime('%Y%m%d-h%Hm%Ms%S') + '\t' + str(val) + '\n')
        fil.close()

    def save_values_to_file(self, val, filename, full_path=None):
        full_path = self.get_path_for_save_value_to_file(filename) if full_path is None else full_path
        folder = os.path.dirname(full_path)
        if not os.path.isdir(self.log_single_val_dir):
            os.mkdir(self.log_single_val_dir)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        now = datetime.datetime.now()
        fil = open(full_path, 'a')
        fil.write(now.strftime('%Y%m%d-h%Hm%Ms%S') + '\t' + '\t'.join(str(v) for v in val) + '\n')
        fil.close()

    def get_last_value_from_file(self, filename, flg_out_date=False):
        folder = os.path.dirname(self.get_path_for_save_value_to_file(filename))
        file_list = sorted(os.listdir((folder)))
        last_file_name = [s for s in file_list if filename in s][-1]
        fil = open(folder + '\\' + last_file_name, 'r')
        line_str_list = fil.readlines()[-1].split('\t')
        fil.close()
        val = float(line_str_list[-1].rstrip('\n'))
        if flg_out_date == True:
            date = datetime.datetime.strptime(line_str_list[0], '%Y%m%d-h%Hm%Ms%S')
            return val, date
        return val

    def get_last_values_from_file(self, filename, flg_out_date=False, full_path=None):
        if full_path is None:
            folder = os.path.dirname(self.get_path_for_save_value_to_file(filename))
            file_list = sorted(os.listdir((folder)))
            last_file_name = [s for s in file_list if filename in s][-1]
            full_path = folder + '\\' + last_file_name
        else:
            full_path = self.get_path_for_save_value_to_file(filename) if full_path is None else full_path
        fil = open(full_path, 'r')

        line_str_list = fil.readlines()[-1].split('\t')
        line_str_list[-1].rstrip('\n')
        fil.close()
        val = []
        for i in line_str_list[1:]:
            try:
                val.append(float(i))
            except:
                val.append(i.rstrip('\n'))
        if flg_out_date is True:
            date = datetime.datetime.strptime(line_str_list[0], '%Y%m%d-h%Hm%Ms%S')
            return val, date
        return val

    def get_values_time_span(self, filename, start_date_str, end_date_str=None):
        folder = os.path.dirname(self.get_path_for_save_value_to_file(filename))
        file_list = sorted(os.listdir(folder))
        result = {'dates': [], 'data': []}
        for fn in file_list:
            try:
                file_date_str = datetime.datetime.strptime(fn[0:6], '%Y%m').strftime(self.__TIME_FORMAT_STR__)
            except:
                file_list.remove(fn)
                continue
            with open("{}/{}".format(folder, fn), 'r') as f:
                for l in f:
                    l = l.rstrip('\n').split('\t')

                    if self.date_str_in(l[0], start_date_str, end_date_str):
                        result['dates'].append(datetime.datetime.strptime(l[0], self.__TIME_FORMAT_STR__))
                        result['data'].append(l[1:])
        result['data'] = np.array(result['data'])
        return result

    def plot_single_values(self, filename, start_date_str, end_date_str=None, grating='m'):
        values = self.get_values_time_span(filename=filename, start_date_str=start_date_str, end_date_str=end_date_str)
        if end_date_str is None:
            end_date_str = datetime.datetime.now()
        else:
            end_date_str = datetime.datetime.strptime(end_date_str, self.__TIME_FORMAT_STR__)
        grating_dict = {'h': 1. / 60. / 60., 'm': 1. / 60., 's': 1.}
        labeldict = {'magnet_gradients': ['x', 'y'], 'confocal_pos': ['x', 'y', 'z'], 'magnet_pos': ['x', 'y', 'z', 'phi'], 'current_local_oscillator_freq': 'local oscillator'}
        legenddict = {'magnet_gradients': 'MHz/mu m', 'confocal_pos': 'mu m', 'magnet_pos': 'mu m', 'current_local_oscillator_freq': 'MHz'}
        precisiondict = {'magnet_gradients': 6, 'confocal_pos': 4, 'magnet_pos': 4, 'current_local_oscillator_freq': 3}
        tdelta = np.array([(values['dates'][i] - end_date_str).total_seconds() for i in range(len(values['dates']))]) * grating_dict['{}'.format(grating)]
        num_single_values = len(values['data'][0])
        num_dp = len(tdelta)
        data = dict()
        for num in range(num_single_values):
            data[num] = np.array([values['data'][i][num] for i in range(num_dp)]).astype(float)
        import matplotlib.pyplot as plt
        import matplotlib.ticker
        fig, axes = plt.subplots(num_single_values)
        fig.suptitle(filename + ' since ' + '{}'.format(values['dates'][0].strftime('%Y%m%d-h%Hm%Ms%S')))
        if num_single_values != 1:
            for sv in range(num_single_values):
                axes[sv].plot(tdelta, data[sv], 'o-', label=labeldict[filename][sv])
                axes[sv].yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.{}f'.format(precisiondict[filename])))
                axes[sv].legend()
                axes[sv].set_ylabel(legenddict[filename])
                axes[sv].set_xlabel('time [{}]'.format(grating))
        else:
            axes.plot(tdelta, data[0], 'o-', label=labeldict[filename])
            axes.legend()
            axes.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.{}f'.format(precisiondict[filename])))
            axes.set_ylabel(legenddict[filename])
            axes.set_xlabel('time [s]')
        plt.show()

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
        return self.mcas_dict[key].dl(*args, **kwargs)


    # Javid added:
    def get_microwave(self):
        """provide SMIQ instead of dummy device as microwave synthesizer.
        """
        import SMIQ
        return SMIQ.SMIQ()

    def get_TimeTagger(self, reload = True):
        if reload:
            reload
        if not hasattr(self,'_timetagger'):
            self._timetagger = TimeTaggerHandler.init_timetagger()
        return self._timetagger

    def get_awg(self):
        return self.awgs['2g']

    ####################################################################################################################
    # GUI
    ####################################################################################################################
    def show_gui(self, module_names):
        for module_name in module_names:
            self.show_subgui(module_name)

    def get_odmr(self):
        if not hasattr(self, 'odmr'):
            # from ODMR_3T import ODMR
            from ODMR import ODMR
            self.odmr = ODMR()
        return self.odmr

    def show_odmr(self):
        self.get_odmr()
        self.restore(model=self.odmr)
        self.odmr.edit_traits()



    def show_subgui(self, name):
        if name == 'confocal':
            getattr(self, 'confocal').edit_traits(view='MainView')
            getattr(self, 'confocal').edit_traits(view='TrackerView')
            getattr(self, 'confocal').edit_traits(view='TraceView')
            self.restore(model=getattr(self, name))
            self.confocal.reset_settings()
            self.guis.append(name)
        elif name == 'oxxius_laser':
            print('no gui available for oxxius_laser')

        elif name == 'ple_Ex':
            # print('name == ple should show gui')
            getattr(self, name).edit_traits()
        elif name == 'ple_A1':
            # print('name == ple should show gui')
            getattr(self, name).edit_traits()
        elif name == 'gated_counter':
            pi3d.gated_counter.gui.show()
        elif name == 'corr_meas':
            pi3d.corr_meas.gui.show()
        elif name == 'interferometer':
            pi3d.interferometer.gui.show()


        elif name == 'tt':
            pi3d.tt.show()
        elif name == 'odmr':
            # self.show_odmr()

            if hasattr(pi3d.odmr.pld, '_gui'):
                pi3d.odmr.pld.gui.show()
        elif name == 'orabi':
            # self.show_odmr()

            if hasattr(pi3d.orabi.pld, '_gui'):
                pi3d.orabi.pld.gui.show()
        elif 'mcas_dict' in name:
            return
        else:
            getattr(self, name).edit_traits()
            if name not in ['tt', 'nuclear', 'gated_counter']:
                self.restore(model=getattr(self, name))
            if name not in self.guis:
                self.guis.append(name)

    def save_pi3diamond(self, destination_dir):
        src = os.getcwd()
        f = '{}/pi3diamond.zip'.format(destination_dir)
        if not os.path.isfile(f):
            zf = zipfile.ZipFile(f, 'a')
            for root, dirs, files in os.walk(src):
                if (not any([i in root for i in ['__pycache__', 'awg_settings', 'currently_unused', ".idea", ".hg", 'UserScripts', 'log']])) or root.endswith('transition_tracker_log') or root.endswith('helpers'):
                    for file in files:
                        if any([file.endswith(i) for i in ['.py', '.dat', '.ui']]):
                            zf.write(os.path.join(root, file), os.path.join(root.replace(os.path.commonprefix([root, src]), ""), file))
            zf.close()

class Pi3DiamondCustomQt(QMainWindow):

    update_user_script_folder_text_field_signal = pyqtSignal(str)
    update_selected_user_script_combo_box_signal = pyqtSignal(collections.OrderedDict)
    update_script_queue_table_data_signal = pyqtSignal(collections.OrderedDict)
    update_user_script_params_text_field_signal = pyqtSignal(collections.OrderedDict)

    def __init__(self, title=None, parent=None, no_qt=None, gui=True):
        super(Pi3DiamondCustomQt, self).__init__(parent=parent)
        self.no_qt = no_qt
        PyQt5.uic.loadUi(os.path.join(self.no_qt.app_dir, 'qtgui/pi3d_main_window.ui'), self)
        self.init_gui()

    def init_gui(self):
        self.setWindowTitle('Pi3Diamond')
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(r"D:\Python\pi3diamond\qtgui\folder_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.user_script_folder_pushButton.setIcon(icon)

        for name in [
            'update_user_script_folder_text_field',
            'update_selected_user_script_combo_box',
            'update_script_queue_table_data',
        ]:
            getattr(getattr(self, "{}_signal".format(name)), 'connect')(getattr(self, "{}_signal_emitted".format(name)))


        self.selected_user_script_combo_box.currentIndexChanged.connect(self.update_selected_user_script_from_combo_box)
        self.remove_next_script_button.clicked.connect(self.no_qt.remove_last_script)
        self.set_stop_request_button.clicked.connect(self.no_qt.set_stop_request)
        self.add_to_queue_button.clicked.connect(self.add_to_queue)
        self.add_rco_button.clicked.connect(self.no_qt.add_rco)
        self.evaluate_button.clicked.connect(self.no_qt.evaluate)
        self.write_standard_awg_sequences_button.clicked.connect(self.no_qt.write_standard_awg_sequences)
        self.user_script_folder_text_field.textChanged.connect(self.user_script_folder_text_field_text_changed)
        self.user_script_folder_pushButton.clicked.connect(self.open_user_script_folder_file_dialog)

    def add_to_queue(self, stupid_argument_emitted_by_qt_signal):
        self.no_qt.add_to_queue()

    def update_selected_user_script_combo_box(self, val):
        self.update_selected_user_script_combo_box_signal.emit(val)

    def update_selected_user_script_combo_box_signal_emitted(self, val):
        self.selected_user_script_combo_box.blockSignals(True)
        if 'user_script_list' in val:
            self.selected_user_script_combo_box.clear()
            self.selected_user_script_combo_box.addItems(val['user_script_list'])  # currentIndexChanged is triggered, value is first item (e.g. sweeps)
        self.selected_user_script_combo_box.setCurrentText(val['selected_user_script'])
        self.selected_user_script_combo_box.blockSignals(False)

    def update_selected_user_script_from_combo_box(self):
        self.no_qt.selected_user_script = str(self.selected_user_script_combo_box.currentText())

    def update_script_queue_table_data(self, val):
        self.update_script_queue_table_data_signal.emit(val)

    def update_script_queue_table_data_signal_emitted(self, val):
        self.script_queue_table.blockSignals(True)
        self.script_queue_table.clear_table_contents()
        self.script_queue_table.set_column_names(['name', 'pd'])
        self.script_queue_table.setColumnWidth(0, 400)
        self.script_queue_table.setColumnWidth(1, 100)
        self.script_queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.script_queue_table.setSelectionMode(QAbstractItemView.SingleSelection)
        for cn, cp in val.items():
            self.script_queue_table.set_column(cn, data=cp, )
        self.script_queue_table.blockSignals(False)

    def update_user_script_folder_text_field(self, val):
        self.update_user_script_folder_text_field_signal.emit(val)

    def update_user_script_folder_text_field_signal_emitted(self, val):
        self.user_script_folder_text_field.blockSignals(True)
        self.user_script_folder_text_field.setText(val)
        self.user_script_folder_text_field.blockSignals(False)

    def user_script_folder_text_field_text_changed(self):
        self.user_script_folder = self.user_script_folder_text_field.toPlainText()

    def open_user_script_folder_file_dialog(self):
        self.no_qt.user_script_folder = QFileDialog.getExistingDirectory(
            self,
            'Select user_script_folder',
            r"D:\Python\pi3diamond\UserScripts",
        )

pi3d = Pi3DiamondCustom()

