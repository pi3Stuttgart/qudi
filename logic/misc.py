# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type

import sys, os

import numpy as np
import pandas as pd
from numbers import Number
import collections
import subprocess
#import __builtin__

class TC:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

def getter_setter_gen(name, type_):
    def getter(self):
        return getattr(self, "_" + name)

    def setter(self, value):
        if not isinstance(value, type_):
            raise TypeError("{} attribute must be set to an instance of {} but was set to {}".format(name, type_, value))
        setattr(self, "_" + name, value)

    return property(getter, setter)

def getter_setter_gen_tc(name, tc):
    k = tc.kwargs

    def getter(self):
        return getattr(self, "_" + name)

    getter = k.get('getter', getter)
    if 'setter' in k:
        return property(getter, k['setter'])
    elif 'start' in k and 'stop' in k:
        def setter(self, val):
            setattr(self, '_' + name, check_range(check_type(val, name, k['typ']), name, k['start'], k['stop']))
    elif 'list_type' in k:
        def setter(self, val):
            setattr(self, '_' + name, check_array_like_typ(val, name, k['list_type']))
    elif 'list_element' in k:
        def setter(self, val):
            setattr(self, '_' + name, check_list_element(val, name, k['list_element']))
    else:
        raise ValueError('Error. {}'.format(k))
    return property(getter, setter)


def auto_attr_check(cls):
    new_dct = {}
    for key, val in cls.__dict__.items():
        if isinstance(val, type):
            val = getter_setter_gen(key, val)
        elif type(val) == TC:
            val = getter_setter_gen_tc(key, val)
        new_dct[key] = val
    # Creates a new class, using the modified dictionary as the class dict:
    return type(cls)(cls.__name__, cls.__bases__, new_dct)


def check_type(val, name, typ):
    if issubclass(type(val), typ):
        return val
    else:
        raise Exception("Property {} must be {} but is {} ({})".format(name, typ, type(val), val))


def check_range(val, name, start, stop):
    if start <= val <= stop:
        return val
    else:
        raise Exception("Property {} must be in range ({}, {}) but has a value of {}".format(name, start, stop, val))


def check_range_type(val, name, typ, start, stop):
    return check_range(check_type(val, name, typ), name, start, stop)


def check_array_like(val, name):
    at = [list, np.ndarray]
    if type(val) in at:
        return val
    else:
        raise Exception("Type of property {} must be in list {}. Tried to assign val {} of type {}.".format(name, at, val, type(val)))


def check_array_like_typ(val, name, typ):
    val = [check_type(i, name + '_i', typ) for i in check_array_like(val, name)]
    if typ in [float, int, Number]:
        val = np.array(val)
    return val


def check_list_element(val, name, l):
    if val in l:
        return val
    else:
        raise Exception("Property {} must be in list {} but has a value of {}".format(name, l, val))


def ret_getter(name):
    def getter(self):
        return getattr(self, '_' + name)

    return getter


def ret_property_typecheck(name, typ):
    def setter(self, val):
        setattr(self, '_' + name, check_type(val, name, typ))

    return property(ret_getter(name), setter)


def ret_property_range(name, typ, start, stop):
    def setter(self, val):
        setattr(self, '_' + name, check_range(check_type(val, name, typ), name, start, stop))

    return property(ret_getter(name), setter)


def ret_property_list_element(name, l):
    def setter(self, val):
        setattr(self, '_' + name, check_list_element(val, name, l))

    return property(ret_getter(name), setter)

def ret_property_array_like(name):
    def setter(self, val):
        setattr(self, '_' + name, check_array_like(val, name))

    return property(ret_getter(name), setter)

def ret_property_array_like_typ(name, typ):
    def setter(self, val):
        setattr(self, '_' + name, check_array_like_typ(val, name, typ))

    return property(ret_getter(name), setter)


def round_to_float(x, tr, rf=None):
    rf = np.around if rf is None else rf
    return rf(x / tr) * tr


def del_files_keep_subfolders(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                # elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)


def round_to(val, base_val):
    return np.around(np.array(val) / base_val)*base_val

def remove_empty_folders(path):
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                remove_empty_folders(fullpath)

    # if folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0:
        print("Removing empty folder:", path)
        os.rmdir(path)


def strictly_increasing(l):
    # x_i >= x_(i+1)
    return all(x < y for x, y in zip(l, l[1:]))


def strictly_decreasing(l):
    # x_i <= x_(i+1)
    return all(x > y for x, y in zip(l, l[1:]))


def non_increasing(l):
    # x_i > x_(i+1)
    return all(x >= y for x, y in zip(l, l[1:]))


def non_decreasing(l):
    # x_i < x_(i+1)
    return all(x <= y for x, y in zip(l, l[1:]))


def sort_lists(baselist, l):
    """Sorts baselist and applies the same index-mapping to all other lists. Probably slow"""
    if len(baselist) != len(l):
        print("unequal list lengths to sort")
        return
    d = {}
    for key, val in enumerate(l):
        d[baselist[key]] = val
    baselist_sorted = sorted(d)
    list_sorted = []
    for key in baselist_sorted:
        list_sorted.append(d[key])
    return baselist_sorted, list_sorted


def prime_factors(n):
    """ Return the prime factors of the given number. """
    factors = []
    lastresult = n
    # 1 is a special case
    if n == 1:
        return [1]
    while 1:
        if lastresult == 1:
            break
        c = 2
        while 1:
            if lastresult % c == 0:
                break
            c += 1
        factors.append(c)
        lastresult /= c
    return factors


def change_binning(binning, y, x=None, averaged=True):
    """Change binning of y data, and possibly additional x data.
    averaged means resulting value is average of binned values.
    averaged can be [False, 'y', 'x', True], 'x' / 'y' means average only for respective array."""
    y2 = []
    for i in range(int(len(y) / binning)):
        if averaged or averaged == 'y':
            y2.append(np.mean(y[i * binning:(i + 1) * binning]))
        else:
            y2.append(sum(y[i * binning:(i + 1) * binning]))
    if x is not None:
        x2 = []
        for i in range(int(len(x) / binning)):
            if averaged or averaged == 'x':
                x2.append(np.mean(x[i * binning:(i + 1) * binning]))
            else:
                x2.append(sum(x[i * binning:(i + 1) * binning]))
        return x2, y2
    return y2


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d
