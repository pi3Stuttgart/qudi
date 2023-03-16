# coding=utf-8
from __future__ import print_function, absolute_import, division
import pyqtgraph as pg
__metaclass__ = type

import traceback
from PyQt5.QtWidgets import QListWidgetItem
import PyQt5.QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
#TODO add pyqtgraph.
from .util import printexception
from . import pddata
try:
    import logic.qudip_enhanced.qtgui.gui_helpers
    from logic import qudip_enhanced as qudip_enhanced
except Exception as e:
    print(e)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib
import matplotlib.pyplot as plt
import lmfit
import numpy as np
import pandas as pd
import collections
import os
import itertools
import sys
import time
import logging
from six import string_types
import subprocess


class Base:

    @printexception
    def __init__(self, delete_names=None):
        self.delete_names = [] if delete_names is None else delete_names

    @printexception
    def delete_attributes(self):
        for attr_name in self.delete_names:
            if hasattr(self, attr_name):
                delattr(self, attr_name)
        if hasattr(self, '_gui'):
            getattr(self.parent.gui, self.name).clear()

    @property
    @printexception
    def data(self):
        return getattr(self, '_data')

    @printexception
    def update_data(self):
        self._data = self.get_data()
        if hasattr(self.parent, '_gui'):
            getattr(self.parent.gui, self.name).update_data(self.data)
        self.update_selected_indices()

    @property
    @printexception
    def selected_indices(self):
        return self._selected_indices


class SelectableList(Base):

    @printexception
    def __init__(self, name='noname', parent=None, **kwargs):  # kwargs =dict(delete_names=['_data','_selected_indices',])
        super(SelectableList, self).__init__(**kwargs)
        self.parent = parent
        self.name = name

    @property
    @printexception
    def selected_index(self):
        if len(self._selected_indices) != 1:
            raise Exception("Error: No single index selected.")
        return self._selected_indices[0]

    @printexception
    def update_selected_indices(self, val=None):
        if val is not None:
            self._selected_indices = val
        elif not hasattr(self, '_selected_indices') or (any([i not in self.data for i in self.selected_data]) and len(self.data) > 0):
            self._selected_indices = self.selected_indices_default()
        if hasattr(self.parent, '_gui'):
            getattr(getattr(self.parent.gui, self.name), "update_selected_indices")(self.selected_indices)

    @printexception
    def update_selected_data(self, val=None):
        selected_indices = val if val is None else [self.data.index(i) for i in val]
        self.update_selected_indices(selected_indices)

    @property
    @printexception
    def selected_data(self):
        return [self.data[i] for i in self.selected_indices]

    @property
    @printexception
    def selected_value(self):
        return self.data[self.selected_index]

    @printexception
    def update_selected_value(self, val=None):
        selected_data = val if val is None else [val]
        self.update_selected_data(selected_data)


class XAxisParameterComboBox(SelectableList):

    @printexception
    def __init__(self, **kwargs):
        super(XAxisParameterComboBox, self).__init__(name='x_axis_parameter_list', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        return [cn for cn in self.parent.parameter_names_reduced()]

    @printexception
    def selected_indices_default(self, selected_indices=None, exclude_names=None):
        exclude_names = [] if exclude_names is None else exclude_names
        arr = np.array([[idx, len(getattr(self.parent.data.df, p).unique())] for idx, p in enumerate(self.data) if p not in exclude_names])
        return [arr[:, 0][np.argmax(arr[:, 1])]]


class ColAxParameterComboBox(SelectableList):

    @printexception
    def __init__(self, **kwargs):
        super(ColAxParameterComboBox, self).__init__(name='col_ax_parameter_list', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        return ['__none__'] + [cn for cn in self.parent.parameter_names_reduced()]

    @printexception
    def selected_indices_default(self, selected_indices=None):
        return [0]


class RowAxParameterComboBox(SelectableList):

    @printexception
    def __init__(self, **kwargs):
        super(RowAxParameterComboBox, self).__init__(name='row_ax_parameter_list', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        return ['__none__'] + [cn for cn in self.parent.parameter_names_reduced()]

    @printexception
    def selected_indices_default(self, selected_indices=None):
        return [0]


class SubtractParameterComboBox(SelectableList):

    @printexception
    def __init__(self, **kwargs):
        super(SubtractParameterComboBox, self).__init__(name='subtract_parameter_list', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        return ['__none__'] + [cn for cn in self.parent.parameter_names_reduced()]

    @printexception
    def selected_indices_default(self, selected_indices=None):
        return [0]


class ObservationList(SelectableList):

    @printexception
    def __init__(self, **kwargs):
        super(ObservationList, self).__init__(name='observation_list', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        return [i for i in self.parent.data.observation_names if not i in ['trace', 'start_time', 'end_time', 'thresholds']]

    @printexception
    def selected_indices_default(self, selected_indices=None):
        return []


class AverageParameterList(SelectableList):

    @printexception
    def __init__(self, **kwargs):
        super(AverageParameterList, self).__init__(name='average_parameter_list', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        return self.parent.data.parameter_names

    @printexception
    def selected_indices_default(self, selected_indices=None):
        return []


class DataTable(Base):

    @printexception
    def __init__(self, name='noname', parent=None, **kwargs):
        super(DataTable, self).__init__(**kwargs)
        self.parent = parent
        self.name = name

    @printexception
    def update_selected_indices(self, selected_indices=None):
        if isinstance(selected_indices, collections.OrderedDict) or selected_indices is None:
            self._selected_indices = self.selected_indices_default(selected_indices)
        else:
            raise Exception(type(selected_indices), selected_indices)
        if hasattr(self.parent, '_gui'):
            getattr(getattr(self.parent.gui, self.name), "update_selected_indices")(self.selected_indices)

    @property
    @printexception
    def selected_data(self):
        out = collections.OrderedDict()
        for cn, val in self.selected_indices.items():
            data_full = getattr(self.parent.data.df, cn).unique()
            out[cn] = [data_full[i] for i in val]
        return out

    @printexception
    def update_selected_data(self, selected_data):
        out = collections.OrderedDict()
        for cn, val in selected_data.items():
            indices = []
            for i in val:
                indices.append(np.where(self.data[cn] == i)[0][0])
            out[cn] = indices
        self.update_selected_indices(out)


class ParameterTable(DataTable):

    @printexception
    def __init__(self, **kwargs):
        super(ParameterTable, self).__init__(name='parameter_table', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        out = collections.OrderedDict()
        for cn in self.parent.parameter_names_reduced():
            out[cn] = getattr(self.parent.data.df, cn).unique()
        return out

    @printexception
    def selected_indices_default(self, selected_indices=None):
        out = collections.OrderedDict()
        if hasattr(self, '_data'):
            for key, val in self._data.items():
                if selected_indices is not None and key in selected_indices:
                    out[key] = selected_indices[key]
                else:
                    out[key] = range(len(val))
        return out


class FitResultTable(DataTable):
    def __init__(self, **kwargs):
        super(FitResultTable, self).__init__(name='fit_result_table', delete_names=['_data', '_selected_indices'], **kwargs)

    @printexception
    def get_data(self):
        if not hasattr(self.parent, '_data_fit_results') or len(self.parent.data_fit_results.df) == 0:
            out = collections.OrderedDict()
        else:
            header = list(self.parent.data_fit_results.parameter_names) + list(self.parent.data_fit_results.df.fit_result[0].params.keys())
            out = self.parent.data_fit_results.df[header].to_dict('list', into=collections.OrderedDict)
        return out

    @printexception
    def selected_indices_default(self, selected_indices=None):
        return collections.OrderedDict()

from logic.qudip_enhanced import qtgui #fixme - is it used?

class PlotData(qudip_enhanced.qtgui.gui_helpers.WithQt):

    @printexception
    def __init__(self, title=None, parent=None, gui=True, **kwargs):
        """

        :param title:
        :param parent:
        :param gui:
        :param kwargs:
            path: path to hdf file
            data: Data instance or
        """

        super(PlotData, self).__init__(parent=parent, gui=gui, QtGuiClass=PlotDataQt)
        self.observation_list = ObservationList(parent=self)
        self.average_parameter_list = AverageParameterList(parent=self)
        self.x_axis_parameter_list = XAxisParameterComboBox(parent=self)
        self.col_ax_parameter_list = ColAxParameterComboBox(parent=self)
        self.row_ax_parameter_list = RowAxParameterComboBox(parent=self)
        self.subtract_parameter_list = SubtractParameterComboBox(parent=self)
        self.parameter_table = ParameterTable(parent=self)
        self.fit_result_table = FitResultTable(parent=self)
        self.set_data(**kwargs)
        if title is not None:
            self.update_window_title(title)

    fit_function = 'cosine'
    show_legend = False

    @printexception
    def set_data(self, **kwargs):
        if 'path' in kwargs:
            self.data = pddata.Data(iff=kwargs['path'])
        elif 'data' in kwargs:
            self.data = kwargs['data']
        if hasattr(self.data, 'filepath'):
            self.update_window_title(self.data.filepath)
            matplotlib.rcParams["savefig.directory"] = os.path.dirname(self.data.filepath)

    @printexception
    def set_data_from_path(self, path):
        self.set_data(path=path)

    @property
    @printexception
    def data(self):
        if hasattr(self, '_data'):
            return self._data

    @data.setter
    @printexception
    def data(self, val):
        self.delete_attributes()
        self._data = val
        self.new_data_arrived()

    @printexception
    def new_data_arrived(self):
        if hasattr(self.data, 'filepath') and matplotlib.rcParams["savefig.directory"] != os.path.dirname(self.data.filepath):
            matplotlib.rcParams["savefig.directory"] = os.path.dirname(self.data.filepath)
        self.x_axis_parameter_list.update_data()
        self.col_ax_parameter_list.update_data()
        self.row_ax_parameter_list.update_data()
        self.subtract_parameter_list.update_data()
        self.parameter_table.update_data()
        self.observation_list.update_data()
        self.average_parameter_list.update_data()
        self.set_custom_default_settings()
        self.update_plot()

    @printexception
    def set_custom_default_settings(self):
        if hasattr(self, '_custom_default_settings'):
            self._custom_default_settings()

    @printexception
    def delete_attributes(self):
        for attr_name in [
            '_data',
        ]:
            if hasattr(self, attr_name):
                delattr(self, attr_name)
        for attr_name in [
            'observation_list',
            'average_parameter_list',
            'x_axis_parameter_list',
            'col_ax_parameter_list',
            'row_ax_parameter_list',
            'subtract_parameter_list',
            'parameter_table',
            'fit_result_table',
        ]:
            getattr(self, attr_name).delete_attributes()

    @printexception
    def parameter_names_reduced(self, data=None):
        data = self.data if data is None else data
        return [i for i in data.parameter_names if not '_idx' in i]

    @property
    @printexception
    def data_selected(self):
        if len(self.data.df) == 0:
            return
        other = pd.DataFrame(list(itertools.product(*self.parameter_table.selected_data.values())))
        other.rename(columns=collections.OrderedDict([(key, val) for key, val in enumerate(self.parameter_table.selected_data.keys())]), inplace=True)
        data = pddata.Data(parameter_names=self.data.parameter_names, observation_names=self.observation_list.selected_data)
        data._df = pddata.df_access(self.data.df[self.data.parameter_names + self.observation_list.selected_data], other)
        if self.subtract_parameter_list.selected_value != '__none__':
            data.subtract_parameter(self.subtract_parameter_list.selected_value, observation_names=self.observation_list.selected_data)
        for pn in self.average_parameter_list.selected_data:
            data.average_parameter(pn, observation_names=self.observation_list.selected_data)
        return data

    @property
    @printexception
    def data_fit_results(self):
        return self._data_fit_results

    def update_data_fit_results(self, data_selected=None):
        data_selected = self.data_selected if data_selected is None else data_selected
        x_axis_parameter = self.x_axis_parameter_list.selected_value
        if not x_axis_parameter in data_selected.parameter_names:
            print('Can not fit!\nx_axis_parameter {} is not in data_selected'.format(x_axis_parameter))
            return
        if hasattr(self, 'custom_model'):
            mod = self.custom_model
        elif self.fit_function == 'cosine':
            from . import lmfit_custom_models
            mod = lmfit_custom_models.CosineModel()
        elif self.fit_function == 'exp':
            pass
        elif self.fit_function == 'lorentz':
            from . import lmfit_custom_models
            mod = lmfit_custom_models.LorentzianModel()
        try:
            pnl = [pn for pn in data_selected.parameter_names if pn != x_axis_parameter]
            for d, d_idx, idx, sub in data_selected.iterator(column_names=pnl, output_data_instance=True):
                for idx_obs, obs in enumerate(sub.observation_names):
                    x = np.array(sub.df[x_axis_parameter])
                    y = np.array(sub.df[obs])
                    params = mod.guess(data=y, x=x)
                    for key, val in getattr(self, 'custom_params', {}).items():
                        if key not in params:
                            raise Exception('Error: invalid custom_params {} for fit. Key {} not found'.format(self.custom_params, key))
                        params[key] = val
                    if idx == 0 and idx_obs == 0:
                        data_fit_results = pddata.Data(parameter_names=pnl + ['observation_name'],
                                                       observation_names=['fit_result'],
                                                       dtypes={'fit_result': 'object'})
                        data_fit_results.init()
                    data_fit_results.append(
                        collections.OrderedDict([
                        (key, val) for key, val in zip(
                            list(d.keys()) + ['observation_name'], 
                            list(d.values()) + [obs]
                                                    )
                    ])
                    )
                    data_fit_results.set_observations(collections.OrderedDict([('fit_result', mod.fit(y, params, x=x))]))
            self._data_fit_results = data_fit_results
            self.extend_data_fit_results_by_parameters()
            self.fit_result_table.update_data()
        except ValueError:
            print("Can not fit, maybe input contains nan values")
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    def extend_data_fit_results_by_parameters(self):
        new_observation_names = self._data_fit_results.df.loc[0, 'fit_result'].params.keys()
        values_dict = collections.OrderedDict([(key, np.nan) for key in new_observation_names])
        observation_names = list(self._data_fit_results.observation_names[:-1]) + list(new_observation_names) + [str(self._data_fit_results.observation_names[-1])]
        self._data_fit_results.append_columns(values_dict=values_dict, observation_names=observation_names)
        for idx, _I_ in self._data_fit_results.df.iterrows():
            for pn, pv in _I_['fit_result'].params.items():
                self._data_fit_results.df.loc[idx, pn] = pv

    def plot_label(self, condition_dict_reduced, obs):
        label = ""
        for key in self.data.non_unary_parameter_names:
            if key in condition_dict_reduced:
                val = condition_dict_reduced[key]
                if type(val) is str:
                    label += "{}:{}, ".format(key, val)
                else:
                    label += "{}:{:g}, ".format(key, val)
        return label[:-2] + obs

    @staticmethod
    @printexception
    def get_subplot_grid_location_parameters(nx_tot, ny_tot, n_tot, **kwargs):
        """
        NOTE: index numbers (e.g. n, nx, ny start from 0 as is common in python, not from 1 as is common in matlab and partially in matplotlib
        :param nx_tot: int
            number of axes from left to right
        :param ny_tot: int
            number of axes from bottom to top
        :param n_tot: int
            total number of plots
        :param kwargs: either give (nx, ny) or n
            'nx': int
                x (horizontal) position in grid
            'ny': int
                y position in grid
            'n' : int
                position in flattened grid
        :return: dict
        """
        if nx_tot * ny_tot < n_tot:
            raise Exception('Error: {}, {}, {}'.format(nx_tot, ny_tot, n_tot))
        if 'n' in kwargs:
            n = kwargs['n']
            nx = n % nx_tot
            ny = int(np.floor(n / float(nx_tot)))
        elif 'nx' in kwargs and 'ny' in kwargs:
            nx = kwargs['nx']
            ny = kwargs['ny']
            n = nx_tot * ny + nx
        else:
            raise Exception('Error: {}'.format(kwargs))
        if n > n_tot - 1:
            raise Exception('Error: given n (or (nx, ny)) does not index an axis within the grid')
        most_bottom_axis = True if n + nx_tot > n_tot - 1 else False
        most_left_axis = True if nx == 0 else False
        return n, nx, ny, most_bottom_axis, most_left_axis

    @printexception
    def number_of_lines(self, data_selected=None):
        data_selected = self.data_selected if data_selected is None else data_selected
        return len(data_selected.df[[i for i in data_selected.parameter_names if i != self.x_axis_parameter_list.selected_value]].drop_duplicates())

    @printexception
    def update_plot_new(self, fig, data_selected=None):
        data_selected = self.data_selected if data_selected is None else data_selected
        if data_selected is None or len(data_selected.df) == 0:
            print('Nothing to plot. You may select something.')
            return
        x_axis_parameter = self.x_axis_parameter_list.selected_value
        col_ax_parameter = self.col_ax_parameter_list.selected_value
        row_ax_parameter = self.row_ax_parameter_list.selected_value
        for name in ['x_axis_parameter', 'col_ax_parameter', 'row_ax_parameter']:
            val = locals()[name]
            if val != '__none__' and not val in data_selected.parameter_names:
                print('Can not plot!\n{} {} is not in data_selected'.format(name, val))
                return
        fig.clear()
        if col_ax_parameter != '__none__' and row_ax_parameter == '__none__':
            ax_p_list = self.parameter_table.selected_data[col_ax_parameter]
            n_tot = len(ax_p_list)
            nx_tot = int(np.ceil(np.sqrt(n_tot)))
            ny_tot = n_tot / float(nx_tot)
            ny_tot = int(ny_tot + 1) if int(ny_tot) == ny_tot else int(np.ceil(ny_tot))
        elif col_ax_parameter != '__none__' and row_ax_parameter != '__none__':
            ax_p_list = list(itertools.product(self.parameter_table.selected_data[row_ax_parameter], self.parameter_table.selected_data[col_ax_parameter]))
            n_tot = len(ax_p_list)
            nx_tot = len(self.parameter_table.selected_data[col_ax_parameter])
            ny_tot = len(self.parameter_table.selected_data[row_ax_parameter])
            if n_tot == nx_tot * ny_tot:  # self.number_of_lines:# +1 is for legend, I DONT THINK THIS DID WHAT IT SHOULD, SO I CHANGED IT
                ny_tot += 1
        else:
            ax_p_list = []
            nx_tot = ny_tot = n_tot = 1
        axes = []
        for ni in range(1, n_tot + 1):
            pd = {} if len(axes) == 0 else {'sharex': axes[0], 'sharey': axes[0]}
            axes.append(fig.add_subplot(ny_tot, nx_tot, ni, **pd))
        cn = [pn for pn in data_selected.parameter_names if pn != self.x_axis_parameter_list.selected_value]
        if len(list(data_selected.column_product(column_names=cn))) > getattr(self, 'max_plots', 100):
            return
        for d, d_idx, idx, sub in data_selected.iterator(column_names=cn):
            if len(ax_p_list) == 0 or row_ax_parameter == '__none__':  # len(ax_p_list[0]) == 1:
                n = np.argwhere(np.array(ax_p_list) == (d[col_ax_parameter]))[0, 0] if col_ax_parameter != '__none__' else 0
            else:
                for n, cr in enumerate(ax_p_list):
                    if cr[1] == d[col_ax_parameter] and cr[0] == d[row_ax_parameter]:
                        break
                else:
                    continue
            abcdefg = collections.OrderedDict([(key, val) for key, val in d.items() if key not in [self.subtract_parameter_list.selected_value, col_ax_parameter, row_ax_parameter]])
            for obs in self.observation_list.selected_data:
                axes[n].plot(sub.loc[:, self.x_axis_parameter_list.selected_data[0]], sub[obs], '-o', markersize=3, label=self.plot_label(abcdefg, obs))
            if len(ax_p_list) != 0:
                title_list = []
                for column_name in [col_ax_parameter, row_ax_parameter]:
                    if column_name != '__none__' and len(self.data.df[col_ax_parameter].unique()) > 1:
                        title_list.append("{}: {}".format(column_name, d[column_name]))
                if len(title_list) > 0:
                    axes[n].set_title(", ".join(title_list))

        for n in range(n_tot):
            n, nx, ny, most_bottom_axis, most_left_axis = self.get_subplot_grid_location_parameters(nx_tot, ny_tot, n_tot, n=n)
            axes[n].set_xlabel(self.x_axis_parameter_list.selected_value)
            if not most_left_axis:
                plt.setp(axes[n].get_yticklabels(), visible=False)
            else:
                if len(self.observation_list.selected_data) == 1:
                    axes[n].set_ylabel(self.observation_list.selected_data[0])
        if 1 < len(axes[0].lines):  # <= 12:  # NOT PYTHON 3 SAFE
            if len(ax_p_list) != 0:
                axes.append(fig.add_subplot(ny_tot, nx_tot, ny_tot * nx_tot))
                plt.setp(axes[-1].get_xticklabels(), visible=False)
                plt.setp(axes[-1].get_yticklabels(), visible=False)
                axes[-1].xaxis.set_ticks_position('none')
                axes[-1].yaxis.set_ticks_position('none')
                axes[-1].axis('off')
                axes[-1].legend(
                    axes[0].lines,
                    [l.get_label() for l in axes[0].lines],
                    borderaxespad=0.1,  # Small spacing around legend box
                    loc='upper left',
                    fontsize=25 / len(axes[0].lines),
                )
            else:
                axes[0].legend(fontsize=25 / len(axes[0].lines), )
        fig.tight_layout()
        return axes

    @printexception
    def update_plot(self, *args, **kwargs):
        if hasattr(self, '_data') and hasattr(self, '_gui'):
            self.gui.axes = self.update_plot_new(fig=self.gui.fig)
            self.gui.canvas.draw()

    @printexception
    def update_plot_fit(self, data_fit_results=None):
        if data_fit_results is None:
            self.update_data_fit_results()
        else:
            self._data_fit_results = data_fit_results
        if hasattr(self, '_gui'):
            self.gui.fig_fit.clear()
            self.gui.ax_fit = self.gui.fig_fit.add_subplot(111)
            for r in self.data_fit_results.df.fit_result:
                color = self.gui.ax_fit._get_lines.get_next_color()
                x = r.userkws['x']
                y = r.eval(params=r.params, x=x)
                self.gui.ax_fit.plot(x, y, '-', color=color)
                self.gui.ax_fit.plot(x, r.data, 'o', color=color, markersize=3.5)
                self.gui.fig_fit.tight_layout()
                self.gui.canvas_fit.draw()

    @printexception
    def save_plot(self, filepath, notify=False):
        t0 = time.time()
        plt.ioff()
        fig = plt.figure()
        axes = self.update_plot_new(fig=fig)
        fig.savefig(filepath)
        plt.close(fig)
        plt.ion()
        if notify:
            pass#logging.getLogger().info('Plot saved to {} in ({:.3f}s)'.format(filepath, time.time() - t0))

    @property
    @printexception
    def info_text(self):
        return self._info_text

    @printexception
    def update_info_text(self, info_text):
        self._info_text = info_text
        if hasattr(self, '_gui'):
            self.gui.update_info_text(info_text)


class BaseQt(PyQt5.QtWidgets.QWidget):

    def __init__(self, name, widget_name, parent, *args, **kwargs):
        super(BaseQt, self).__init__(*args, **kwargs)
        self.name = name
        self.widget_name = widget_name
        self.parent = parent

    @printexception
    def update_data(self, data):
        self.update_data_signal.emit(data)

    @printexception
    def update_selected_indices(self, selected_indices):
        getattr(self, "update_selected_indices_signal").emit(selected_indices)

    @printexception
    def connect_signals(self):
        for name in [
            'data'.format(self.name),
            'selected_indices'.format(self.name),
        ]:
            getattr(getattr(self, "update_{}_signal".format(name)), 'connect')(getattr(self, "update_{}_signal_emitted".format(name)))

    @printexception
    def clear(self):
        widget = getattr(self.parent, self.widget_name)
        try:
            widget.blockSignals(True)
            widget.clear()
        except:
            raise
        finally:
            widget.blockSignals(False)


class SelectableListQt(BaseQt):
    update_data_signal = pyqtSignal(list)
    update_selected_indices_signal = pyqtSignal(list)

    @printexception
    def update_data_signal_emitted(self, data):
        widget = getattr(self.parent, self.widget_name)
        widget.blockSignals(True)
        try:
            if widget.count() != 0:
                getattr(self.parent, self.widget_name).clear()
            for val in data:
                widget.addItem(QListWidgetItem(val))
        except:
            raise
        finally:
            widget.blockSignals(False)

    @printexception
    def update_selected_indices_signal_emitted(self, selected_indices):
        widget = getattr(self.parent, self.widget_name)
        try:
            widget.blockSignals(True)
            for i in selected_indices:
                widget.item(i).setSelected(True)
        except:
            raise
        finally:
            widget.blockSignals(False)

    @printexception
    def update_selected_indices_from_gui(self, *args, **kwargs):
        print('Item selection has been changed.')
        getattr(self.parent.no_qt, self.name).update_selected_indices([i.row() for i in getattr(self.parent, self.widget_name).selectedIndexes()])


class ParameterCombobox(BaseQt):
    update_data_signal = pyqtSignal(list)
    update_selected_indices_signal = pyqtSignal(list)

    @printexception
    def update_data_signal_emitted(self, data):
        widget = getattr(self.parent, self.widget_name)
        widget.blockSignals(True)
        try:
            if widget.count() != 0:
                getattr(self.parent, self.widget_name).clear()
            widget.addItems(data)
        except:
            raise
        finally:
            widget.blockSignals(False)
        if hasattr(getattr(self.parent.no_qt, self.name), '_selected_indices'):
            getattr(self.parent.parameter_table, 'update_item_flags')()

    @printexception
    def update_selected_indices_signal_emitted(self, selected_indices):
        getattr(self.parent, self.widget_name).blockSignals(True)
        getattr(self.parent, self.widget_name).setCurrentText(getattr(self.parent.no_qt, self.name).data[selected_indices[0]])
        getattr(self.parent, self.widget_name).blockSignals(False)

    @printexception
    def update_selected_indices_from_gui(self, *args, **kwargs):
        idx = getattr(self.parent.no_qt, self.name).data.index(str(getattr(self.parent, self.widget_name).currentText()))
        getattr(self.parent.no_qt, self.name).update_selected_indices([idx])


class TableQt(BaseQt):
    update_data_signal = pyqtSignal(collections.OrderedDict)
    update_selected_indices_signal = pyqtSignal(collections.OrderedDict)

    @printexception
    def update_data_signal_emitted(self, data):
        widget = getattr(self.parent, self.widget_name)
        widget.blockSignals(True)
        try:
            if widget.columnCount() != 0:
                getattr(self.parent, self.widget_name).clear_table_contents()
            if widget.columnCount() == 0:
                widget.set_column_names(data.keys())
            for column_name, val in data.items():
                widget.set_column(column_name, val)
            self.update_item_flags()
        except:
            raise
        finally:
            widget.blockSignals(False)

    @printexception
    def update_selected_indices_signal_emitted(self, selected_indices):
        widget = getattr(self.parent, self.widget_name)
        widget.blockSignals(True)
        try:
            for cn, val in selected_indices.items():
                cidx = widget.column_index(cn)
                for ridx in widget.column_data_indices(cn):
                    if val == '__all__' or (not isinstance(val, string_types) and ridx in val):
                        widget.item(ridx, cidx).setSelected(True)
                    else:
                        widget.item(ridx, cidx).setSelected(False)
        except:
            raise
        finally:
            widget.blockSignals(False)

    @printexception
    def update_selected_indices_from_gui(self):
        widget = getattr(self.parent, self.widget_name)
        out = collections.OrderedDict()
        column_names = widget.column_names
        for item in widget.selectedItems():
            cn = column_names[item.column()]
            if not cn in out:
                out[cn] = []
            out[cn].append(item.row())
        getattr(self.parent.no_qt, self.name).update_selected_indices(out)


class ParameterTableQt(TableQt):

    @printexception
    def update_item_flags(self):
        widget = getattr(self.parent, self.widget_name)
        widget.blockSignals(True)
        try:
            for cidx in range(widget.columnCount()):
                cn = widget.column_name(cidx)
                if cn == self.parent.no_qt.subtract_parameter_list.selected_value:
                    flag = Qt.NoItemFlags
                else:
                    flag = Qt.ItemIsSelectable | Qt.ItemIsEnabled
                for ridx in widget.column_data_indices(cn):
                    widget.set_cell(ridx, cidx, flag=flag)
        except:
            raise
        finally:
            widget.blockSignals(False)


class FitResultTableQt(TableQt):

    @printexception
    def update_item_flags(self):
        widget = getattr(self.parent, self.widget_name)
        widget.blockSignals(True)
        try:
            for cidx in range(widget.columnCount()):
                for ridx in widget.column_data_indices(widget.column_name(cidx)):
                    widget.set_cell(ridx, cidx, flag=Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        except:
            raise
        finally:
            widget.blockSignals(False)


class PlotDataQt(qudip_enhanced.qtgui.gui_helpers.QtGuiClass):
    def __init__(self, parent=None, no_qt=None):
        self.observation_list = SelectableListQt(name='observation_list', widget_name='observation_widget', parent=self)
        self.average_parameter_list = SelectableListQt(name='average_parameter_list', widget_name='average_parameter_widget', parent=self)
        self.x_axis_parameter_list = ParameterCombobox(name='x_axis_parameter_list', widget_name='x_axis_parameter_comboBox', parent=self)
        self.col_ax_parameter_list = ParameterCombobox(name='col_ax_parameter_list', widget_name='col_ax_parameter_comboBox', parent=self)
        self.row_ax_parameter_list = ParameterCombobox(name='row_ax_parameter_list', widget_name='row_ax_parameter_comboBox', parent=self)
        self.subtract_parameter_list = ParameterCombobox(name='subtract_parameter_list', widget_name='subtract_parameter_comboBox', parent=self)
        self.parameter_table = ParameterTableQt(name='parameter_table', widget_name='parameter_table_widget', parent=self)
        self.fit_result_table = FitResultTableQt(name='fit_result_table', widget_name='fit_result_table_widget', parent=self)
        #print(self.layout())
        super(PlotDataQt, self).__init__(parent=parent, no_qt=no_qt, ui_filepath=os.path.join(os.path.dirname(__file__), 'qtgui/plot_data_vv3.ui'))
        self.setCentralWidget(self.parameter_tab)
        #print(self.layout())


    update_info_text_signal = pyqtSignal(str)

    @printexception
    def clear_signal_emitted(self):
        for name in [
            'x_axis_parameter_comboBox',
            'col_ax_parameter_comboBox',
            'row_ax_parameter_comboBox',
            'subtract_parameter_comboBox',
            'parameter_table_widget',
            'observation_widget',
            'average_parameter_widget',
            'fit_result_table_widget',
        ]:
            getattr(self, name).clear()  # self.clear_widget(name)
        try:
            self.fig.clf()
            self.canvas.draw()
        except:
            pass
        try:
            self.fig_fit.clf()
            self.canvas_fit.draw()
        except:
            pass

    @printexception
    def update_info_text(self, info_text):
        self.update_info_text_signal.emit(info_text)

    @printexception
    def update_info_text_signal_emitted(self, info_text):
        self.info.setPlainText(info_text)

    @printexception
    def redraw_plot(self):
        self.fig.tight_layout()
        self.canvas.draw()

    @printexception
    def redraw_plot_fit(self):
        self.fig_fit.tight_layout()
        self.canvas_fit.draw()

    @printexception
    def init_gui(self):
        super(PlotDataQt, self).init_gui()
        for name in [
            'update_info_text'
        ]:
            getattr(getattr(self, "{}_signal".format(name)), 'connect')(getattr(self, "{}_signal_emitted".format(name)))
        for name in [
            'observation_list',
            'average_parameter_list',
            'x_axis_parameter_list',
            'row_ax_parameter_list',
            'col_ax_parameter_list',
            'subtract_parameter_list',
            'parameter_table',
            'fit_result_table'

        ]:
            getattr(self, name).connect_signals()

        # # Figure
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.ax = self.fig.add_subplot(111)
        self.canvas.draw()
        self.plot_layout.addWidget(self.canvas, 1, 1, 20, 20)
        self.toolbar_layout.addWidget(self.toolbar, 21, 1, 1, 20)

        if False:## PyQTGRaph addon....
            self.pg_layout = pg.GraphicsLayoutWidget()
            x = np.random.normal(size=1000)
            y = np.random.normal(size=1000)
            self.pg_layout.addPlot(x=x, y=y, pen=None, symbol='x', row=0, col=0, title="Plot @ row 1, column 1")
            self.plot_layout.addWidget(self.pg_layout)

        # Figure fit
        self.fig_fit = Figure()
        self.canvas_fit = FigureCanvas(self.fig_fit)
        self.toolbar_fit = NavigationToolbar(self.canvas_fit, self)

        self.ax_fit = self.fig_fit.add_subplot(111)
        self.canvas_fit.draw()
        self.plot_fit_layout.addWidget(self.canvas_fit, 1, 1, 20, 20)
        self.toolbar_fit_layout.addWidget(self.toolbar_fit, 21, 1, 1, 20)

        self.update_plot_button.clicked.connect(self.no_qt.update_plot)
        self.update_fit_result_button.clicked.connect(lambda: self.no_qt.update_plot_fit(None))
        self.update_plot_button.setAcceptDrops(True)

        self.parameter_table_widget.hdf_file_dropped.connect(self.no_qt.set_data_from_path)
        self.parameter_table_widget.itemSelectionChanged.connect(self.parameter_table.update_selected_indices_from_gui)
        self.observation_widget.itemSelectionChanged.connect(self.observation_list.update_selected_indices_from_gui)
        self.average_parameter_widget.itemSelectionChanged.connect(self.average_parameter_list.update_selected_indices_from_gui)
        self.open_code_button.clicked.connect(self.open_measurement_code)
        self.open_explorer_button.clicked.connect(self.open_explorer)

        self.x_axis_parameter_comboBox.currentIndexChanged.connect(self.x_axis_parameter_list.update_selected_indices_from_gui)
        self.col_ax_parameter_comboBox.currentIndexChanged.connect(self.col_ax_parameter_list.update_selected_indices_from_gui)
        self.row_ax_parameter_comboBox.currentIndexChanged.connect(self.row_ax_parameter_list.update_selected_indices_from_gui)
        self.subtract_parameter_comboBox.currentIndexChanged.connect(self.subtract_parameter_list.update_selected_indices_from_gui)

    @printexception
    def open_measurement_code(self, *args, **kwargs):
        if hasattr(self.no_qt.data, 'filepath'):
            subprocess.Popen(r"start {}/meas_code.py".format(os.path.dirname(self.no_qt.data.filepath)), shell=True)
        else:
            print('No filepath.')

    @printexception
    def open_explorer(self, *args, **kwargs):
        if hasattr(self.no_qt.data, 'filepath'):
            subprocess.Popen("explorer {}".format(os.path.abspath(os.path.dirname(self.no_qt.data.filepath))), shell=True)
        else:
            print('No filepath.')
