from __future__ import print_function, absolute_import, division
__metaclass__ = type

from .util import ret_property_typecheck, ret_property_list_element, check_type, check_array_like, printexception
from .data_handling import df_drop_duplicate_rows, df_pop, Data

from collections import Counter, OrderedDict

import numpy as np
import pandas as pd
import errno
import shutil
import traceback
import itertools
import datetime
import sys
import os
import time
import logging

from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from core.util import units
from core.util.math import compute_ft
#from logic.generic_logic import GenericLogic
from logic.pulsed.pulse_extractor import PulseExtractor
from logic.pulsed.pulse_analyzer import PulseAnalyzer

class DataGeneration:

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.date_of_creation = datetime.datetime.now()

    current_idx_str = ret_property_typecheck('current_idx_str', str)
    current_parameter_str = ret_property_typecheck('current_parameter_str', str)

    # Save Data:
    file_path = ret_property_typecheck('file_path', str)
    file_name = ret_property_typecheck('file_name', str)
    file_notes = ret_property_typecheck('file_notes', str)
    meas_code = ret_property_typecheck('meas_code', str)
    state = ret_property_list_element('state', ['idle', 'run'])

    @property
    def parameters(self):
        return self._parameters

    @parameters.setter
    @printexception
    def parameters(self, val):
        if type(val) != OrderedDict:
            raise Exception('Error: {}, {}'.format(type(val), val))
        for k, v in val.items():
            _ = check_type(k, 'key', str)
            _ = check_array_like(v, 'value_in_{}'.format(k))
            if len(v) == 0:
                raise Exception("Error: parameter {} has length zero.".format(k))
            items_occuring_more_than_once = [item_val for item_val, number_of_occurences in Counter(v).items() if number_of_occurences > 1]
            if len(items_occuring_more_than_once) > 0:
                raise Exception("Error: parameter {} has duplicate items {}".format(k, items_occuring_more_than_once))
        self._parameters = val

    @property
    def dtypes(self):
        return getattr(self, '_dtypes', None)

    @dtypes.setter
    @printexception
    def dtypes(self, val):
        if isinstance(val, dict):
            for k, v in val.items():
                if not (k in self.parameters.keys() or isinstance(v, str)):
                    raise Exception("Error: {}".format(val))
            self._dtypes = val

    @property
    @printexception
    def observation_names(self):
        return self._observation_names

    @property
    @printexception
    def number_of_simultaneous_measurements(self):
        if hasattr(self, '_number_of_simultaneous_measurements'):
            return self._number_of_simultaneous_measurements
        else:
            return 1

    @number_of_simultaneous_measurements.setter
    @printexception
    def number_of_simultaneous_measurements(self, val):
        if type(val) is int:
            self._number_of_simultaneous_measurements = val
        else:
            raise Exception('Error: {}'.format(val))

    @property
    @printexception
    def data(self):
        return self.pld.data

    @property
    def pld(self):
        return self._pld

    @pld.setter
    def pld(self, val):
        self._pld = val

    def iterator_df_drop_done(self):
        self.iterator_df = df_drop_duplicate_rows(self.iterator_df, self.iterator_df_done)

    def set_iterator_df(self):
        self.iterator_df = pd.DataFrame(
            list(itertools.product(*self.parameters.values())),
            columns=list(self.parameters.keys())
        )
        for cn in self.iterator_df.columns:
            self.iterator_df[cn] = self.iterator_df[cn].astype(type(self.parameters[cn][0]))

    @property
    def progress(self):
        return getattr(self, '_progress', 0)

    def init_data(self, init_from_file=None, iff=None, move_folder=True, drop_nan=True):
        init_from_file = iff if iff is not None else init_from_file
        self.init_from_file = init_from_file
        self.move_folder = move_folder
        self.pld._data = Data(
            parameter_names=list(self.parameters.keys()),
            observation_names=self.observation_names,
            dtypes=self.dtypes,
            init_from_file=init_from_file
        )
        if drop_nan:
            self.data.dropnan(max_expected_rows=self.number_of_simultaneous_measurements)

    def update_current_str(self, separate_parameters_indices=False):
        if hasattr(self, 'current_iterator_df') and len(self.current_iterator_df) > 0:
            if separate_parameters_indices:
                cid = self.current_iterator_df.iloc[-1, :].to_dict()
                cps = ""
                cis = ""
                for key, val in cid.items():
                    if len(self.parameters[key]) > 1:
                        cps += "{}: {}\n".format(key, val)
                        try:
                            cis += "{}: {} ({})\n".format(key, list(self.parameters[key]).index(val), len(self.parameters[key]))
                        except:
                            pass
                self.pld.update_info_text('State: ' + self.state + '\n\n' + 'Current parameters:\n' + cps + '\n\n' + 'Current indices\n' + cis)
            else:
                cid = self.current_iterator_df.iloc[-1, :].to_dict()
                cps = ""
                for key, val in cid.items():
                    if len(self.parameters[key]) > 1:
                        cps += "{}: ".format(key, val)
                        try:
                            cps += "({}/ {})".format(list(self.parameters[key]).index(val), len(self.parameters[key]))
                        except:
                            pass
                        cps += "\n{}\n\n".format(val)
                self.pld.update_info_text('State: ' + self.state + '\n\n' + 'Current parameters:\n' + cps)

    def init_run(self, **kwargs):
        self.state = 'run'
        self.reinit()
        self.init_data(**kwargs)

    def update_progress(self):
        self._progress = len(self.iterator_df_done) / np.prod([len(i) for i in self.parameters.values()])

    def changes_from_previous(self, iterator_df):
        if len(self.data.df) == 0:
            out = iterator_df.iloc[0, :] == iterator_df.iloc[0, :]
            out[:] = True
        elif len(iterator_df) == 0: #required for last iteration, when current_iterator_df is empty
            return iterator_df == iterator_df #should have zero rows (i.e. be empty)
        else:
            out = iterator_df.iloc[0, :] != self.data.df.iloc[-1, :len(self.iterator_df.columns)]
        out = out.to_frame().transpose()
        for idx in range(1, len(iterator_df)):
            out = out.append(iterator_df.iloc[idx-1, :] != iterator_df.iloc[idx, :], ignore_index=True)
        self.current_iterator_df_changes = out

    def iterator(self):
        while True:
            t0 = time.time()
            self.process_remeasure_items()
            #print("qudip_enhanced.data_generationT1=", time.time()-t0)
            t0 = time.time()
            self.iterator_df_done = self.data.df.loc[:, self.data.parameter_names]  # self.iterator_df_done.append(self.current_iterator_df)
            #print("T2=", time.time()-t0)
            t0 = time.time()
            self.set_iterator_df()
            #print("T3=", time.time()-t0)
            t0 = time.time()
            self.iterator_df_drop_done()
            #print("T4=", time.time()-t0)
            t0 = time.time()
            self.update_progress()
            #print("T5=", time.time()-t0)
            t0 = time.time()
            self.iterator_df, self.current_iterator_df = df_pop(self.iterator_df, min(self.number_of_simultaneous_measurements, len(self.iterator_df)))
            #print("T6=", time.time()-t0)
            t0 = time.time()
            self.changes_from_previous(self.current_iterator_df)
            #print("T7=", time.time()-t0)
            t0 = time.time()
            if len(self.current_iterator_df) > 0:
                self.data.append(self.current_iterator_df)
            #print("T8=", time.time()-t0)
            t0 = time.time()
            self.update_current_str()
            #print("T9=", time.time()-t0)
            t0 = time.time()
            if len(self.current_iterator_df) > 0:
                yield self.current_iterator_df, self.current_iterator_df_changes
            else:
                break

    def reinit(self):
        self.start_time = datetime.datetime.now()
        if hasattr(self, 'current_iterator_df'):
            del self.current_iterator_df
        if hasattr(self, '_file_path') and hasattr(self, '_file_name'):
            self.pld.data_path = "{}/data.hdf".format(self.save_dir)

    @property
    def save_dir(self):
        return "{}/{}_{}".format(self.file_path, self.start_time.strftime('%Y%m%d-h%Hm%Ms%S'), self.file_name)

    def make_save_dir(self):
        try:
            os.makedirs(self.save_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        except Exception:
            print(self.save_dir)
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    @property
    def save_dir_tmp(self):
        return "{}/tmp".format(self.save_dir)

    def make_save_dir_tmp(self):
        try:
            os.makedirs(self.save_dir_tmp)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        except Exception:
            print(self.save_dir_tmp)
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    def make_save_location_params(self, script_path, **kwargs):
        script_path = os.path.abspath(script_path)
        self.file_name = str(os.path.splitext(os.path.basename(script_path))[0])
        folder = kwargs['folder'] if 'folder' in kwargs else os.path.dirname(os.path.dirname(script_path)) #os.path.dirname(os.path.dirname(script_path))
        if 'sub_folder_kw' in kwargs:

            # == Windows solutions.
            fnl = script_path.split(os.sep) #This doesnt work on MAC os... :(
            fnl = fnl[fnl.index(kwargs['sub_folder_kw']) + 1:]
            fnl[-1] = fnl[-1].split('.')[0] # extracts the folder name and file name of the script, why so complicated?
            ### Are it needs some folder structure, thats right!
            # == Workaround for MAC

            #fnl = os.path.split(script_path)[1]
            #fnl = fnl.split('.')[0] # Create folder with file name of a py script.
            ## =============

            subfolder = "/".join(fnl)
            self.file_path = str(os.path.join(folder, subfolder))
        else:
            self.file_path = str(folder)

    def save(self, name='', notify=False):
        t0 = time.time()
        t = [t0]
        if not os.path.exists(self.save_dir):
            self.make_save_dir()
        t.append(time.time() - t0)
        if self.init_from_file is not None and self.move_folder:
            new_iff_path = os.path.join(self.save_dir, os.path.basename(os.path.dirname(self.init_from_file)) + '_tbc', os.path.basename(self.init_from_file))
            if not os.path.exists(new_iff_path):
                folder = os.path.dirname(self.init_from_file)
                os.rename(folder, folder + '_tbc')
                shutil.move(folder + '_tbc', self.save_dir)
        t.append(time.time() - t0)
        if len(self.iterator_df_done) >= 0:
            if hasattr(self, 'file_notes'):
                with open("{}/notes.dat".format(self.save_dir), "w") as text_file:
                    text_file.write(self.file_notes)
            if hasattr(self, '_meas_code'):
                with open("{}/meas_code.py".format(self.save_dir), "w") as text_file:
                    text_file.write(self.meas_code)
            t.append(time.time() - t0)
            self.data.save("{}/data.hdf".format(self.save_dir), notify=notify)
            t.append(time.time() - t0)
            self.pld.save_plot("{}/plot.png".format(self.save_dir), notify=notify)
            t.append(time.time() - t0)
            if notify:
                logging.getLogger().info("saved {} to '{} ()".format(name, self.save_dir, " ".join("{:.2f}".format(x) for x in t)))

    def remeasure(self, df):
        indices = self.data.df[self.data.df.loc[:, self.data.parameter_names].isin(df).all(axis=1)].index  # get indices in self.df.data to be replaced
        if len(indices) != len(df):
            raise Exception('Not all rows in df could be found in self.data: (missing: {})'.format(len(df) - len(indices)))
        elif indices[0] % self.number_of_simultaneous_measurements != 0:
            raise Exception('Error: The first index to be remeasured must be an integer multiple of number_of_simultaneous_measurements!\n{} {} {}'.format(df, indices, self.number_of_simultaneous_measurements))
        elif len(indices) % self.number_of_simultaneous_measurements != 0:
            raise Exception('Error: length of indices to be remeasured must be an integer multiple of number_of_simultaneous_measurements!\n{} {} {}'.format(df, indices, self.number_of_simultaneous_measurements))
        elif not ((indices[1:] - indices[:-1]) == 1).all():
            raise Exception("Error: Only connected packets of indices are allowed, i.e. monotonously increasing with stepsize 1".format(indices))
        self.remeasure_df = df

    def process_remeasure_items(self):
        if hasattr(self, 'remeasure_df'):
            self.data._df = df_drop_duplicate_rows(self.data.df, self.remeasure_df)
            del self.remeasure_df
