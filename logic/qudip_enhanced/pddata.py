# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import os, sys

from six import string_types

import numpy as np
import pandas as pd
import itertools

import datetime
import collections
import subprocess
import threading

from .util import ret_property_array_like_types
import time
import logging

if sys.version_info.major == 2:
    import __builtin__
else:
    import builtins as __builtin__


def ptrepack(file, folder, tempfile=None, lock=None):
    # C:\Users\yy3\AppData\Local\conda\conda\envs\py27\UserScripts\ptrepack.exe -o --chunkshape=auto --propindexes --complevel=0 --complib=blosc data.hdf data_tmp.hdf

    if lock is not None and not lock.acquire(False):
        print('Trying to run ptrepack on {}'.format(os.path.join(folder, file)))
        print('Waiting for hdf_lock..')
        lock.acquire()
        print('Ok.. hdf_lock acquired.')
    tempfile = 'temp.hdf' if tempfile is None else tempfile
    ptrepack = r"{}\Scripts\ptrepack.exe".format(os.path.dirname(sys.executable)) ##C:\Users\SiC_LT2\anaconda3\Scripts\ptrepack.exe
    #ptrepack = r'C:\Users\SiC_LT2\anaconda3\Scripts\ptrepack.exe'
    command = [ptrepack, "-o", "--chunkshape=auto", "--propindexes", "--complevel=9", "--complib=blosc", file, tempfile]
    _ = subprocess.call(command, cwd=folder)
    if _ != 0:
        print(_, 'ptrepack failed')
    i = 0
    t0 = time.time()
    while i < 1000:
        try:
            os.remove(os.path.join(folder, file))
            break
        except:
            print("Trying to remove {} again. (Try {}, {}s)".format(os.path.join(folder, file), i, time.time() - t0))
            i += 1
    i = 0
    t0 = time.time()
    while i < 1000:
        try:
            os.rename(os.path.join(folder, tempfile), os.path.join(folder, file))
            if i > 0:
                print("Renaming {} to {} was successful after {} tries and a total of {}s)".format(
                    os.path.join(folder, tempfile),
                                                                                                   os.path.join(folder, file), i, time.time() - t0))
            break
        except Exception as e:
            print(e)
            print("Trying to rename {} to {} again. (Try {}, {}s)".format(os.path.join(folder, tempfile),
                                                                          os.path.join(folder, file), i, time.time() - t0))
            i += 1
    if lock is not None: lock.release()


def ptrepack_thread(**kwargs):
    t = threading.Thread(name='run_ptrepack', target=ptrepack, kwargs=kwargs)
    t.start()


def ptrepack_all(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".hdf"):
                ptrepack(file, root)


def weight_mean(w):
    def _weight_mean(d):
        try:
            #             return d.mean()
            return (d * w).sum() / w[d.index].sum()
        except ZeroDivisionError:
            return np.NaN

    return _weight_mean


def df_pop(df, n):
    out = df.head(n)
    return df.iloc[n:, :], out


def l_to_df(l):
    """
    creates DataFrame from list of OrderedDict

    :param l: collections.OrderedDict, dict or list thereof
    :return:
    """
    if type(l) == pd.DataFrame:
        return l
    else:
        if type(l) == dict:
            raise Exception('Error')
        if type(l) in [collections.OrderedDict]:
            l = [l]
        return pd.DataFrame.from_records(l)


def df_access(df, other):
    if type(other) == pd.Series:
        other = pd.DataFrame(other).transpose()
    df_all = df.merge(other.drop_duplicates(), on=list(other.columns), how='left', indicator=True)
    return df_all[df_all._merge == 'both'].iloc[:, :-1].reset_index(drop=True)


def df_delete(df, other):
    if type(other) == pd.Series:
        other = pd.DataFrame(other).transpose()
    df_all = df.merge(other.drop_duplicates(), on=list(other.columns), how='left', indicator=True)
    return df_all[df_all._merge == 'left_only'].iloc[:, :-1].reset_index(drop=True)


def dict_access(df, l):
    return df_access(df=df, other=l_to_df(l))


def dict_delete(df, l):
    return df_delete(df=df, other=l_to_df(l))

def extend_columns(df, other, columns=None):
    """
    Extends df horizontally to include all columns of other
    Necessary workaround due to pandas deficiencies regarding missing data (only float has a realy missing data type)
    Order of columns is important.

    Example:
        df.columns = ['A', 'B', 'C']
        other.columns = ['B', 'C', 'D']
        result: df.columns = ['A', 'B', 'C', 'D']

    :param df: pandas.DataFrame
        DataFrame whose columns should be extended
    :param other: pandas.DataFrame
        DataFrame to take extra columns from
    :return: pandas.DataFrame
    """
    columns = None
    columns = other.columns if columns is None else columns
    if type(columns) != pd.core.indexes.base.Index:
        raise Exception('Error: unexpected behaviour.')
    if not all([i in other.columns for i in df.columns]):
        raise Exception('Error: all columns of other ({}) must be in df ({})'.format(other.columns, df.columns))
    if len(df.columns) == len(columns) and (df.columns == columns).all():
        return df
    else:
        print('This should work but is untested and to my knowledge not used right now. (data_handling.extend_columns)')
        df_missing_columns = pd.Index([i for i in other.columns if i not in df.columns])  # df.columns.append(other.columns).drop_duplicates(keep=False)
        return pd.concat([df, pd.concat([other.loc[:, df_missing_columns].iloc[0:1, :]] * len(df)).reset_index(drop=True)], axis=1).reset_index(drop=True)


def df_take_duplicate_rows(df, other):
    df_columns = df.columns  # here for security reasons, leave it!
    df_dtypes = df.dtypes  # here for security reasons, leave it!
    df_all = df.merge(other.drop_duplicates(), on=list(other.columns), how='left', indicator=True)
    out = df_all[df_all._merge == 'both'].iloc[:, :-1].reset_index(drop=True)
    if not (out.columns == df_columns).all():  # here for security reasons, leave it!
        print(out.columns, df_columns)
    if not (out.dtypes == df_dtypes).all():  # here for security reasons, leave it!
        print(out.columns, df.columns)
    return out


def df_drop_duplicate_rows(df, other):
    """

    :param df: dataframe
    :param other: dataframe
    :param columns: pd.core.indexes.base.Index
        columns to compare
        default: right.columns
    :return:
    """
    df_columns = df.columns  # here for security reasons, leave it!
    df_dtypes = df.dtypes  # here for security reasons, leave it!
    df_all = df.merge(other.drop_duplicates(), on=list(other.columns), how='left', indicator=True)
    out = df_all[df_all._merge == 'left_only'].iloc[:, :-1].reset_index(drop=True)
    if not (out.columns == df_columns).all():  # here for security reasons, leave it!
        print(out.columns, df_columns)
    if not (out.dtypes == df_dtypes).all():  # here for security reasons, leave it!
        print(out.columns, df.columns)
    return out

class Data:
    def __init__(self, parameter_names=None, observation_names=None, dtypes=None, **kwargs):
        if parameter_names is not None:
            self.parameter_names = parameter_names
        if observation_names is not None:
            self.observation_names = observation_names
        if dtypes is not None:
            self.dtypes = dtypes
        if len(kwargs) > 0:
            self.init(**kwargs)
        self.hdf_lock = threading.Lock()

    parameter_names = ret_property_array_like_types('parameter_names', [string_types])
    observation_names = ret_property_array_like_types('observation_names', [string_types])

    @property
    def dtypes(self):
        if not hasattr(self, '_dtypes'):
            self._dtypes = collections.OrderedDict([(key, 'float') for key in self.observation_names])
        return self._dtypes

    @dtypes.setter
    def dtypes(self, val):
        if val is not None:
            for k, v in val.items():
                if k not in self.observation_names or type(v) != str:  # k may not be in parameter_names, as these are inferred correctly from the passed values
                    raise Exception("Error: {}, {}, {}, {}, {}".format(val, k, v, type(v), self.observation_names))
            self._dtypes = val

    def change_column_dtype(self, column_name, new_dtype=None):
        if new_dtype is not None:
            self.df[[column_name]] = self.df[[column_name]].astype(new_dtype)
        if column_name in self.observation_names:
            self.dtypes[column_name] = new_dtype
        self.reinstate_integrity()

    def rename_column(self, column_name, column_name_new):
        if column_name not in self.variables:
            raise Exception('Error: column does not exist.')
        self.parameter_names = [i if i != column_name else column_name_new for i in self.parameter_names]
        self.observation_names = [i if i != column_name else column_name_new for i in self.observation_names]
        self._df = self.df.rename(columns={column_name: column_name_new})
        self.reinstate_integrity()

    def delete_columns(self, column_names):
        not_in = [cn for cn in column_names if not cn in self.variables]
        if len(not_in) > 0:
            raise Exception("Error: column_names {} can not be deleted because they do not exist.".format(not_in))
        nupn = self.non_unary_parameter_names
        non_unary_parameter_names_to_be_deleted = [cn for cn in column_names if cn in self.parameter_names and cn in nupn]
        if len(non_unary_parameter_names_to_be_deleted) != 0:
            raise Exception('Error: column_names {} are in parameter_names but are non_unary. Columns can not be deleted.'.format(non_unary_parameter_names_to_be_deleted))
        self._df = self.df.drop(column_names, axis=1)
        self.reinstate_integrity()

    def delete_nonunary_parameter_names(self):
        self.delete_columns([pn for pn in self.parameter_names if pn not in self.non_unary_parameter_names])

    def append_columns(self, values_dict, no_new_columns_warning=True, **kwargs):
        if len(kwargs) != 1:
            raise Exception('Error: give one dictionary of column_names or observation_names. {}'.format(kwargs))
        od = {'parameter_names': 'observation_names', 'observation_names': 'parameter_names'}
        if type(values_dict) != collections.OrderedDict:
            raise Exception("Error: {}".format(values_dict))
        is_in_other = [cn for cn in list(kwargs.values())[0] if cn in getattr(self, od[list(kwargs.keys())[0]])] #python 3 wrong??
        if len(is_in_other) > 0:
            raise Exception("Error: {} is in od[kwargs.keys()[0]]".format(is_in_other))
        not_in = [cn for cn in list(kwargs.values())[0] if cn not in getattr(self, list(kwargs.keys())[0])] #python 3 wrong??
        if len(not_in) == 0:
            if no_new_columns_warning:
                raise Exception("Error: No new columns given. {}".format(kwargs))
            else:
                return
        if len(values_dict) != len(not_in):
            raise Exception('Error: {}, {}'.format(values_dict, not_in))
        not_in_values_dict = [not_in_i for not_in_i in not_in if not_in_i not in values_dict.keys()]
        if len(not_in_values_dict) > 0:
            raise Exception('Error: {}'.format(not_in_values_dict))
        setattr(self, list(kwargs.keys())[0], list(kwargs.values())[0]) # python 3 wrong??
        for column, value in values_dict.items():
            loc = getattr(self, list(kwargs.keys())[0]).index(column) #python 3 wrong??
            if list(kwargs.keys())[0] == 'observation_names': #python 3 wrong ??
                loc += len(self.parameter_names)
            self.df.insert(loc, column, value, allow_duplicates=False)
        self.reinstate_integrity()

    @property
    def variables(self):
        return self.parameter_names + self.observation_names

    @property
    def number_of_variables(self):
        return len(self.variables)

    def backwards_compatibility_last_parameter(self, cn):
        for n in ['tau', 'point', 'phi', 'x2', 'x1']:  # order of x2, x1, x0.. is important
            if n in cn:
                next_n = cn[cn.index(n) + 1]
                if next_n == 'trace' or '_idx' in next_n:
                    return n
                else:
                    raise Exception('Incompatibility Error: {}'.format(cn))
        else:
            return None

    def get_last_parameter(self, df, last_parameter=None):
        if hasattr(self, '_parameter_names'):
            if last_parameter is not None:
                if last_parameter != self.parameter_names[-1]:
                    raise Exception('Error: {}, {}'.format(self.parameter_names[-1], last_parameter))
            else:
                last_parameter = self.parameter_names[-1]
        elif last_parameter is None:
            cn = list(df.columns)
            bclp = self.backwards_compatibility_last_parameter(cn)
            if bclp is not None:
                last_parameter = bclp
            else:
                l_idx = [cni for cni in cn if cni.endswith('_idx')]
                if len(l_idx) == 0:
                    raise Exception('Error: Could not figure out last_parameter, thus parameter_names and observation_names could not be determined: {}'.format(cn))
                l = [i[:-4] for i in l_idx]
                if all(np.array(cn[:2 * len(l_idx)]) == l + l_idx):
                    last_parameter = l_idx[-1]
                else:
                    raise Exception('Error: Could not figure out last_parameter, thus parameter_names and observation_names could not be determined: {}'.format(cn))
        elif last_parameter not in df.columns:
            raise Exception("last_parameter {} ist not in dataframe columns {}".format(last_parameter, df.columns))
        return last_parameter

    def read_hdf(self, init_from_file):
        store = pd.HDFStore(init_from_file)
        if hasattr(store, '/df'):
            df = store['/df']
            for key in ["parameter_names", 'observation_names', 'dtypes']:
                attr_name = "_{}".format(key)
                if hasattr(store.get_storer('df').attrs, key):
                    setattr(self, attr_name, getattr(store.get_storer('df').attrs, key))
                else:
                    if hasattr(self, attr_name):
                        delattr(self, attr_name)
        else:
            df = store.get('/a')
        store.close()
        return df

    def read_csv(self, init_from_file):
        return pd.read_csv(init_from_file, compression='gzip')

    def init_metadata(self, df, last_parameter):
        if False in [hasattr(self, i) for i in ['_parameter_names', '_observation_names', '_dtypes']]:
            if last_parameter is None:
                last_parameter = self.get_last_parameter(df)
            lpi = list(self.df.columns.values).index(last_parameter) + 1
            if not hasattr(self, '_parameter_names'):
                self.parameter_names = list(self.df.columns[:lpi])
            if not hasattr(self, '_observation_names'):
                self.observation_names = list(self.df.columns[lpi:])
            if not hasattr(self, '_dtypes'):
                self._dtypes = list(self.df.dtypes[lpi:])
        parameter_names_to_delete = ["{}_idx".format(pn) for pn in self.parameter_names if "{}_idx".format(pn) in self.parameter_names]
        self._df = self.df.drop(columns=parameter_names_to_delete)
        self._parameter_names = [pn for pn in self.parameter_names if not pn in parameter_names_to_delete]

    def init(self, last_parameter=None, df=None, init_from_file=None, iff=None, path=None):
        init_from_file = iff if iff is not None else init_from_file
        init_from_file = path if path is not None else init_from_file
        if init_from_file is not None:
            self.filepath = init_from_file
            if init_from_file.endswith('.hdf'):
                df = self.read_hdf(init_from_file)
            elif init_from_file.endswith('.csv'):
                df = self.read_csv(init_from_file)
        if df is None:
            self._df = pd.DataFrame(columns=self.variables)
        else:
            self._df = df[pd.notnull(df)]
        if init_from_file is not None:
            self.init_metadata(df=df, last_parameter=last_parameter)

    def dropnan(self, max_expected_rows=None):
        ldf = len(self.df)
        self.df.dropna(axis=0, how='any', inplace=True)
        if max_expected_rows is not None and ldf - len(self.df) > max_expected_rows:
            raise Exception('Error: A maximum of {} rows with nan values can be expected from unfinished measurements ({}, {}). Whats wrong?'.format(max_expected_rows, ldf, len(self.df)))

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, value):
        self._df = value
        self.reinstate_integrity()

    def seconds_since_last_save(self, filepath):
        return os.stat(filepath).st_mtime - time.time()

    def save(self, filepath, notify=False):
        if filepath.endswith('.csv'):
            t0 = time.time()
            self.df.to_csv(filepath, index=False)
            print("csv data saved ({:.2f}s).\n If speed is an issue, use hdf."
                  " csv format is useful ony for py2-py3-compatibility.".format(time.time() - t0))
        elif filepath.endswith('.hdf'):
            t0 = time.time()
            t = []
            if not self.hdf_lock.acquire(False):
                print('Trying to save data to hdf.')
                print('Waiting for hdf_lock..')
                self.hdf_lock.acquire()
                print('Ok.. hdf_lock acquired.')
            t.append(time.time() - t0)
            store = pd.HDFStore(filepath)
            store.put('df', self.df, table=True)
            for key in ["parameter_names", 'observation_names', 'dtypes']:
                setattr(store.get_storer('df').attrs, key, getattr(self, key))
            store.close()
            t.append(time.time() - t0)
            self.hdf_lock.release()
            t.append(time.time() - t0)
            if getattr(self, 'save_dur_list', [0])[-1] < 5. or self.seconds_since_last_save(filepath) > 3600.:
                ptrepack_thread(file=os.path.split(filepath)[1], folder=os.path.split(filepath)[0], lock=self.hdf_lock)
            else:
                logging.getLogger().info('hdf-file is not repacked. {} {}', self.save_dur_list[-1], self.seconds_since_last_save(filepath))
            t.append(time.time() - t0)
            self.filepath = filepath
            if notify:
                logging.getLogger().info("hdf data saved in ({})".format(" ".join("{:.2f}".format(x) for x in t)))
                if hasattr(self, 'save_dur_list'):
                    self.save_dur_list.append(sum(t))
                else:
                    self.save_dur_list = [sum(t)]

    def get_parameters_df(self, l):
        df_append = l_to_df(l)
        if not (df_append.columns == self.parameter_names).all():
            raise Exception('Error: Dataframe columns dont match: '.format(df_append.columns, self.parameter_names))
        return df_append.reset_index(drop=True)

    def initialize_observations_df(self, n):
        l_obs = []
        for idx in range(n):
            l_obs.append(collections.OrderedDict())
            for k, v in self.dtypes.items():
                if v == 'datetime':
                    l_obs[idx][k] = datetime.datetime(1900, 1, 1)  # datetime.datetime.min is also an option, but leads to OutOfBoundsDatetime: Out of bounds nanosecond timestamp: 1-01-01 00:00:00, when calling data = self.df.iloc[index.row(), index.column()]
                elif v.startswith('numpy'):
                    l_obs[idx][k] = getattr(np, v.split('.')[1])()
                else:
                    l_obs[idx][k] = getattr(__builtin__, v)()
        return pd.DataFrame(columns=self.observation_names, data=l_obs)

    def append(self, l):
        parameters_df = self.get_parameters_df(l)
        df_append = pd.concat([parameters_df, self.initialize_observations_df(len(parameters_df))], axis=1)  # NECESSARY! Reason: sorting issues when appending df with missing columns
        if len(self.df) == 0:
            self._df = df_append
        else:
            self._df = self.df.append(df_append, ignore_index=True)
        self.check_integrity()

    def set_observations(self, l, start_idx=None):
        start_idx = len(self.df) - 1 if start_idx is None else start_idx
        l = l_to_df(l)
        for idx, row in l.iterrows():
            for obs, val in zip(l.columns, row):
                self.df.at[start_idx - len(l) + idx + 1, obs] = val
        self.check_integrity()

    def df_access(self, other):
        return df_access(self.df, other)

    def df_delete(self, other):
        self._df = df_delete(self.df, other)
        self.check_integrity()

    def dict_access(self, l):
        return dict_access(df=self.df, l=l)

    def dict_delete(self, l):
        self._df = dict_delete(df=self.df, l=l)
        self.check_integrity()

    def column_product(self, column_names):
        return itertools.product(*[getattr(self.df, cn).unique() for cn in column_names])

    def sub(self, l):
        ldf = l_to_df(l)
        new_parameter_names = [i for i in self.parameter_names if not (i in ldf.columns and len(ldf[i].unique()) == 1)]
        sub = Data(parameter_names=new_parameter_names, observation_names=self.observation_names, dtypes=self.dtypes)
        sub._df = self.dict_access(ldf)
        return sub

    def iterator(self, column_names, output_data_instance=False):
        for idx, p in enumerate(self.column_product(column_names=column_names)):
            d = collections.OrderedDict(zip(column_names, p))
            d_idx = collections.OrderedDict([(cn, np.argwhere(getattr(self.df, cn).unique() == p)[0, 0]) for cn, p in d.items()])
            sub = self.sub(l=d)
            if not output_data_instance:
                sub = sub.df
            yield d, d_idx, idx, sub

    @property
    def non_unary_parameter_names(self):
        """
        :return: all parameter_names that are indeed varied (with at least two different values in self.df)
        """
        out = []
        for cn in self.parameter_names:
            try:
                if len(self.df[cn].unique()) > 1:
                    out.append(cn)
            except:  # drops for example columns with numpy arrays
                pass
        return out

    def check_integrity(self):
        if len(self.parameter_names) + len(self.observation_names) != len(self.df.columns):
            cnl = [(i, j) for i, j in zip(self.parameter_names + self.observation_names, self.df.columns)]
            raise Exception('Error: Integrity corrupted: {}, {}, {}\n{}'.format(len(self.parameter_names), len(self.observation_names), len(self.df.columns), cnl))
        if not all([i == j for i, j in zip(self.df.columns[:len(self.parameter_names)], self.parameter_names)]):
            raise Exception('Error: Integrity corrupted: {}, {}'.format(self.df.columns, self.parameter_names))
        if not all([i == j for i, j in zip(self.df.columns[-len(self.observation_names):], self.observation_names)]):
            raise Exception('Error: Integrity corrupted: {}, {}'.format(self.df.columns, self.observation_names))
        for cn in self.df.columns:
            if cn in self.parameter_names and cn in self.observation_names:
                raise Exception('Error: Integrity corrupted! {}, {}'.format(self.parameter_names, self.observation_names))

    def reinstate_integrity(self):
        """
        After columns of self.df have been removed, remove these from other variables as well and vice versa
        """
        cnl = [cn for cn in self.df.columns if cn not in self.parameter_names + self.observation_names]
        self._df = self.df.drop(cnl, axis=1)
        self.parameter_names = [i for i in self.parameter_names if i in self.df.columns]
        self.observation_names = [i for i in self.observation_names if i in self.df.columns]
        self.dtypes = collections.OrderedDict([(key, val) for key, val in self.dtypes.items() if not (key in self.dtypes and key not in self.df.columns)])
        # for key in self.dtypes.keys():
        #     if key in self.dtypes and key not in self.df.columns:
        #         del self.dtypes[key]
        # self.check_integrity()

    def update_observation_names_combine(self, observation_names, new_observation_name):
        observation_names = [i for i in self.observation_names if i not in observation_names]
        observation_names.insert(min([self.observation_names.index(i) for i in self.observation_names]), new_observation_name)
        self.observation_names = observation_names

    def observations_to_parameters(self, observation_names, new_parameter_name, new_observation_name='value'):
        df = pd.melt(
            self.df,
            id_vars=[cn for cn in self.df.columns if cn not in observation_names],
            value_vars=observation_names,
            var_name=new_parameter_name,
            value_name=new_observation_name)
        self.parameter_names.append(new_parameter_name)
        self.update_observation_names_combine(observation_names, new_observation_name)
        self.df = df[self.parameter_names + self.observation_names]



    def check_pn_on_helper(self, parameter_name, observation_names):
        if parameter_name not in self.parameter_names:
            raise Exception('Error: chosen parameter_name {} is not in self.parameter_names {}.'.format(parameter_name, self.parameter_names))
        if len(observation_names) == 0:
            raise Exception('Error: Chose at least on observation.')
        if any([i not in self.observation_names for i in observation_names]):
            raise Exception('Error: at least one of the chosen observation_names {} is not in self.observation_names {}'.format(observation_names, self.observation_names))

    def eliminate_parameter(self, parameter_name, observation_names, operations, dropna=False):
        self.check_pn_on_helper(parameter_name, observation_names)
        self.delete_columns([i for i in self.observation_names if i not in observation_names])
        self.parameter_names = [key for key in self.parameter_names if key != parameter_name]
        if len(operations) == 1:
            operations = itertools.repeat(operations[0])
        elif len(operations) != len(observation_names):
            raise Exception('Error: ', operations, observation_names)
        self._df = self.df.groupby(self.parameter_names).agg(collections.OrderedDict([(observation_name, operation) for observation_name, operation in zip(observation_names, operations)])).reset_index()
        self.check_integrity()

    def average_parameter(self, parameter_name, observation_names, observation_name_weight=None):
        if observation_name_weight is None:
            operations = [np.mean]
        else:
            operations = [weight_mean(self.df[observation_name_weight])]
        self.eliminate_parameter(operations=operations, parameter_name=parameter_name, observation_names=observation_names, dropna=False)

    def sum_parameter(self, parameter_name, observation_names):
        self.eliminate_parameter(operations=[np.sum], parameter_name=parameter_name, observation_names=observation_names, dropna=True)

    def subtract_parameter(self, parameter_name, observation_names):
        lnp = len(getattr(self.df, parameter_name).unique())
        if lnp != 2:
            raise Exception('Error: Only parameters with 2 unique items can be subtracted. Parameter {} has {}'.format(parameter_name, lnp))
        self.eliminate_parameter(operations=[np.diff], parameter_name=parameter_name, observation_names=observation_names, dropna=True)

    def subtract_observations(self, observation_names, new_observation_name, dropna=False):
        print('functionality untested')
        if len(observation_names) != 2:
            raise Exception('Error :', observation_names)
        self._df[[observation_names[0]]] = self.df[observation_names[1]] - self.df[observation_names[0]]
        if dropna:
            self.df.dropna(subset=observation_names)
        self.rename_column(observation_names[0], new_observation_name)
        self.delete_columns([self.observation_names[1]])
