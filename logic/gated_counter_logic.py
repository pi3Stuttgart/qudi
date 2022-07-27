from __future__ import print_function, absolute_import, division
__metaclass__ = type

import misc
import traceback
import time
import sys
import os
import threading
#import multi_channel_awg_seq as MCAS
import Analysis
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
#import pyqtgraph as pg
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import PyQt5.QtCore
import numpy as np
import logging
import zmq

# from qutip_enhanced import *
import logic.qudip_enhanced.qtgui.gui_helpers
from numbers import Number
#from pi3diamond import pi3d

class GatedCounter(logic.qudip_enhanced.qtgui.gui_helpers.WithQt):

    def __init__(self, title='Gated Counter', parent=None, gui=True, **kwargs):
        super(GatedCounter, self).__init__(title=title, parent=parent, gui=gui, QtGuiClass=GatedCounterQt)
        self.readout_interval = 1e6 # DO NOT SET BELOW 0.2, plotting runs in main loop, and takes around 0.15, which then makes the console annoying to work with.
        self.readout_duration = 10e6
        self.trace = Analysis.Trace()
        self.analyze_trace_during_experiment = True
        if title is not None:
            self.update_window_title(title)
        self.tim
        self.raw_clicks_processing = False
        self.raw_clicks_processing_function = None


    readout_interval = misc.ret_property_typecheck('readout_interval', Number)

    progress = misc.ret_property_typecheck('progress', int)

    @property
    def points(self):
        if hasattr(self, 'n_values'):
            return self.n_values/sum([step[3] for step in self.trace.analyze_sequence])
        return self._points

    @points.setter
    def points(self, val):
        self._points = misc.check_type(val, 'points', int)

    @property
    def n_values(self):
        return self._n_values

    @n_values.setter
    def n_values(self, val):
        self._n_values = val


    def set_n_values(self, mcas, analyze_sequence=None):

        # print('gated counter readout_duration set_n_values', self.readout_duration)
        analyze_sequence = self.trace.analyze_sequence if analyze_sequence is None else analyze_sequence
        # print('analyze sequence: ',analyze_sequence)
        self.n_values = int(self.readout_duration / mcas.length_mus * sum([step[3] for step in analyze_sequence]))
        # print('self.n_values ',self.n_values)




    def read_trace(self):
        import time
        t0 = time.time()
        self.gated_counter_data = self.timetagger.gated_counter_countbetweenmarkers.getData()
        # print('1 tt:',time.time()-t0)

        if self.ZPL_counter:
            if self.raw_clicks_processing:
                counter_name = 'raw_zpl'
                # print('init raw clicks processing name: ', counter_name)
                data = pi3d.timetagger.get_stream_data(counter_name=counter_name, kwargs=[])
                #data = datadict['data']

                #send_time = datadict['time_before']
                #print("Send time was: {}".format(send_time))
                #print("Time now: {}".format(time.time()))
                # print('11 tt:', time.time() - t0)

                if self.raw_clicks_processing_function is not None:
                    self.raw_clicks_processing_function(data,
                                                        delays = self.start_trigger_delay_ps_list,
                                                        windows = self.window_ps_list
                                                        )
                    # print('12 tt:', time.time() - t0)

                else:
                    raise Exception('self.raw_clicks_processing_function is None')

                # print('21 tt:', time.time() - t0)

                # if self.two_zpl_apd:
                #     # trace_name = 'zpl_2_counter_data_{i}_{j}'.format(i=i, j=j)
                #     counter_name = 'raw_2_zpl'
                #     data = pi3d.timetagger.get_stream_data(counter_name=counter_name, kwargs=[])
                #     if self.raw_clicks_processing_function is not None:
                #         self.raw_clicks_processing_function(data,
                #                                             delays=self.start_trigger_delay_ps_list,
                #                                             windows=self.window_ps_list
                #                                             )
                #
                #     else:
                #         raise Exception('self.raw_clicks_processing_function is None')

                # print('22 tt:', time.time() - t0)

            else:
                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        trace_name = 'zpl_counter_data_{i}_{j}'.format(i=i,j=j)
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)

                        # pi3d.timetagger.gated_counter_countbetweenmarkers.sync()
                        zpl_counter_data = getattr(pi3d.timetagger,counter_name).getData()#.astype(np.int64)
                        # getattr(pi3d.timetagger, counter_name).sync()
                        setattr(self, trace_name,zpl_counter_data)
                        # print('21 tt:', time.time() - t0)
                        if self.two_zpl_apd:
                            trace_name = 'zpl_2_counter_data_{i}_{j}'.format(i=i, j=j)
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            pi3d.timetagger.gated_counter_countbetweenmarkers.sync()
                            zpl_counter_data = getattr(pi3d.timetagger,counter_name).getData()#.astype(np.int64)
                            # getattr(pi3d.timetagger, counter_name).sync()
                            setattr(self, trace_name,zpl_counter_data)

                        # print('22 tt:',time.time()-t0)


        # print('tt3:',time.time()-t0)

        self.set_progress()
        # print('tt4:',time.time()-t0)
        if self.analyze_trace_during_experiment:
            self.trace_rep = Analysis.TraceRep(trace=self.gated_counter_data[:self.progress],
                                               analyze_sequence=self.trace.analyze_sequence,
                                               number_of_simultaneous_measurements=self.trace.number_of_simultaneous_measurements)
            self.trace.trace = np.array(self.trace_rep.df.groupby(['run', 'sm', 'step', 'memory']).agg({'n': np.sum}).reset_index().n)
            self.update_plot_data()
        # print('clear TT start')
        # self.clear_timetaggers()
        # print('clear TT finished')
        t1 = time.time()
        # print('tt5:',t1-t0)

    def clear_timetaggers(self):
        pi3d.timetagger.gated_counter_countbetweenmarkers.clear()
        if self.ZPL_counter:
            if self.raw_clicks_processing:
                counter_name = 'raw_zpl'
                # getattr(pi3d.timetagger, counter_name).clear()
                pi3d.timetagger.kill_stream(counter_name=counter_name, kwargs=[])
                # if self.two_zpl_apd:
                #     counter_name = 'raw_2_zpl'
                #     pi3d.timetagger.kill_stream(counter_name=counter_name, kwargs=[])

            else:
                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                        getattr(pi3d.timetagger, counter_name).clear()

                        if self.two_zpl_apd:
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            getattr(pi3d.timetagger, counter_name).clear()


    def stop_timetaggers(self):

        pi3d.timetagger.gated_counter_countbetweenmarkers.stop()
        if self.ZPL_counter:
            # print('Gated counter stop TT ZPL_counter')

            if self.raw_clicks_processing:
                # print('Gated counter stop TT raw_clicks_processing')

                counter_name = 'raw_zpl'
                pi3d.timetagger.stop_stream(counter_name=counter_name, kwargs=[])
                # if self.two_zpl_apd:
                #     # print('Gated counter stop TT two_zpl_apd')
                #
                #     counter_name = 'raw_2_zpl'
                #     pi3d.timetagger.stop_stream(counter_name=counter_name, kwargs=[])
            else:
                # print('Gated counter stop TT NOT== raw_clicks_processing')

                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                        getattr(pi3d.timetagger, counter_name).stop()

                        if self.two_zpl_apd:
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            getattr(pi3d.timetagger, counter_name).stop()

    def start_timetaggers(self):
        pi3d.timetagger.gated_counter_countbetweenmarkers.start()
        if self.ZPL_counter:
            if self.raw_clicks_processing:

                counter_name = 'raw_zpl'
                pi3d.timetagger.start_stream(counter_name=counter_name, kwargs=[])
                # if self.two_zpl_apd:
                #     counter_name = 'raw_2_zpl'
                #     pi3d.timetagger.start_stream(counter_name=counter_name, kwargs=[])
            else:
                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                        getattr(pi3d.timetagger, counter_name).start()

                        if self.two_zpl_apd:
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            getattr(pi3d.timetagger, counter_name).start()

    def count(self, abort, ch_dict, turn_off_awgs=True,
              start_trigger_delay_ps_list = None,window_ps_list=None,
              raw_clicks_processing=False, two_zpl_apd = False,raw_clicks_processing_channels = [0,1,2,3,4,5,6,7]):

        # self.start_timetaggers()
        self.start_trigger_delay_ps_list = start_trigger_delay_ps_list
        self.window_ps_list = window_ps_list
        self.two_zpl_apd = two_zpl_apd
        self.raw_clicks_processing = raw_clicks_processing
        self.raw_clicks_processing_channels = raw_clicks_processing_channels


        if hasattr(self, '_gui'):
            self.gui.clear_plot(len(self.trace.analyze_sequence))
        try:
            self.set_counter()
            MCAS.start_awgs(pi3d.awgs, ch_dict=ch_dict)
            self.progress = 0
            while True:
                if abort.is_set():
                    break
                # print('Gated counter is falling asleep for ',int(self.readout_duration / 1e6))
                time.sleep(int(self.readout_duration / 1e6))
                break;
                # ready = pi3d.timetagger.gated_counter_countbetweenmarkers.ready()
                # if ready:
                #     break
                # else:
                #     # time.sleep(self.readout_interval / 1e6)
                #     time.sleep(1)

            self.read_trace()
            self.update_plot()

        except Exception as e:
            abort.set()
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            if turn_off_awgs:
                pi3d.mcas_dict.stop_awgs()

            self.stop_timetaggers()

            # begin2 = time.time()
            # self.clear_timetaggers()

            # pi3d.timetagger.gated_counter_countbetweenmarkers.stop()
            self.state = 'idle'

    def set_counter(self):
        self.ZPL_counter = False

        def f():
            nlp_per_point = sum([step[3] for step in self.trace.analyze_sequence])

            pi3d.timetagger.init_counter(
                'gated_counter_countbetweenmarkers',
                n_values=self.n_values - self.n_values % nlp_per_point if hasattr(self, '_n_values') else nlp_per_point * self.points,
            )

            if self.raw_clicks_processing:
                name = 'raw_zpl'
                n_bins = self.n_values - self.n_values % nlp_per_point if hasattr(self,
                                                                                  '_n_values') else nlp_per_point * self.points,

                # print('n_bins ',n_bins)
                kwargs = dict(n_bins = n_bins[0]*len(self.raw_clicks_processing_channels),
                              channels=self.raw_clicks_processing_channels)
                # print('kwargs["n_bins"] ',kwargs["n_bins"])

                pi3d.timetagger.create_stream(counter_name=name, kwargs=kwargs)

                # if self.two_zpl_apd:
                #     name = 'raw_2_zpl'
                #     pi3d.timetagger.create_stream(counter_name=name, kwargs=kwargs)


                self.ZPL_counter = True

            else:
                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        if (start_trigger_delay_ps is not None) and (window_ps is not None):

                            name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                            pi3d.timetagger.init_counter(
                                name,
                                n_values=self.n_values - self.n_values % nlp_per_point if hasattr(self,
                                                                                                  '_n_values') else nlp_per_point * self.points,
                                delay_ps=start_trigger_delay_ps,
                                window_ps=window_ps
                            )

                            if self.two_zpl_apd:
                                name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                                pi3d.timetagger.init_counter(
                                    name,
                                    n_values=self.n_values - self.n_values % nlp_per_point if hasattr(self,
                                                                                                      '_n_values') else nlp_per_point * self.points,
                                    delay_ps=start_trigger_delay_ps,
                                    window_ps=window_ps
                                )

                            self.ZPL_counter = True

        for i in range(2):
            t = threading.Thread(target=f)
            t.start()
            t.join(5)
            if t.is_alive():
                logging.getLogger().info('Setting up counter failed!')
                logging.getLogger().info('Trying to restart timetagger..')
                pi3d.restart_timetagger()
            else:
                break
        else:
            raise Exception('Error: timeout.')

    def set_progress(self):
        if pi3d.timetagger.gated_counter_countbetweenmarkers.ready():
            self.progress = int(len(self.gated_counter_data))
        else:
            self.progress = int(len(self.gated_counter_data) - np.argmax(self.gated_counter_data[::-1] != 0) - 1)

    def init_plot(self):
        if hasattr(self, '_gui'):
            self.gui.init_plot()

    def update_plot_data(self):
        self.effective_subtrace_list = []
        self.hist_list = []
        df = self.trace.df_extended()
        for idx, step in enumerate(self.trace.analyze_sequence):
            try:
                self.effective_subtrace_list.append(df.loc[df.step == idx, range(step[5])].astype(int).values)
                self.hist_list.append([])
                estl = self.effective_subtrace_list[-1].T
                if estl.shape[0] == 2:
                    self.hist_list[-1].append(self.trace.hist(estl[0, :] - estl[1, :]))
                else:
                    for t in estl:
                        self.hist_list[-1].append(self.trace.hist(t))
            except:
                pass

    def update_plot(self):
        if hasattr(self, '_gui'):
            self.update_plot_data()
            self.gui.update_plot(self.effective_subtrace_list, self.hist_list)

class GatedCounterQt(logic.qudip_enhanced.qtgui.gui_helpers.QtGuiClass):
    def __init__(self, parent=None, no_qt=None):
        super(GatedCounterQt, self).__init__(parent=parent, no_qt=no_qt, ui_filepath=os.path.join(pi3d.app_dir, 'qtgui/gated_counter.ui'))

    clear_plot_signal = PyQt5.QtCore.pyqtSignal(int)
    update_plot_signal = PyQt5.QtCore.pyqtSignal(list, list)

    def clear_plot(self, number_of_subtraces):
        self.clear_plot_signal.emit(number_of_subtraces)

    def clear_plot_signal_emitted(self, number_of_subtraces):
        try:
            self.fig.clear()
            self.axes = self.fig.subplots(number_of_subtraces, 2, squeeze=False)
            self.canvas.draw()
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    def clear_signal_emitted(self):
        pass

    def init_gui(self):
        super(GatedCounterQt, self).init_gui()
        for name in [
            'clear_plot',
            'update_plot',
        ]:
            getattr(getattr(self, "{}_signal".format(name)), 'connect')(getattr(self, "{}_signal_emitted".format(name)))

        # Figure
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.ax = self.fig.add_subplot(111)
        self.canvas.draw()
        self.plot_layout.addWidget(self.canvas, 1, 1, 20, 20)
        self.toolbar_layout.addWidget(self.toolbar, 21, 1, 1, 20)

    def update_plot(self, effective_subtrace_list, hist_list):
        self.update_plot_signal.emit(effective_subtrace_list, hist_list)

    def update_plot_signal_emitted(self, effective_subtrace_list, hist_list):
        try:
            t0 = time.time()
            for nst, st in enumerate(effective_subtrace_list):
                self.axes[nst, 0].cla()
                self.axes[nst, 0].plot(st)
                self.axes[nst, 1].cla()
                if len(hist_list[nst]) > 0:
                    for h in hist_list[nst]:
                        self.axes[nst, 1].plot(h['bin_edges'], h['hist'])
                else:
                    self.axes[nst, 1].text(
                        0.5,
                        0.5,
                        'HISTOGRAM FAILED',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.axes[nst, 1].transAxes,
                        color='r',
                        fontsize=30
                    )
                self.fig.tight_layout()
                self.fig.canvas.draw_idle()
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)


class GatedCounterQtGraph(logic.qudip_enhanced.qtgui.gui_helpers.QtGuiClass):
    """
    The same as GatedCounterQt but with Pyqtgraph'''
    """
    def __init__(self, parent=None, no_qt=None):
        super(GatedCounterQt, self).__init__(parent=parent, no_qt=no_qt, ui_filepath=os.path.join(pi3d.app_dir, 'qtgui/gated_counter.ui'))

    clear_plot_signal = PyQt5.QtCore.pyqtSignal(int)
    update_plot_signal = PyQt5.QtCore.pyqtSignal(list, list)

    def clear_plot(self, number_of_subtraces):
        self.clear_plot_signal.emit(number_of_subtraces)

    def clear_plot_signal_emitted(self, number_of_subtraces):
        try:
            self.fig.clear()
            self.axes = self.fig.subplots(number_of_subtraces, 2, squeeze=False)
            self.canvas.draw()
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)

    def clear_signal_emitted(self):
        pass

    def init_gui(self):
        super(GatedCounterQt, self).init_gui()
        for name in [
            'clear_plot',
            'update_plot',
        ]:
            getattr(getattr(self, "{}_signal".format(name)), 'connect')(getattr(self, "{}_signal_emitted".format(name)))

        # Figure




        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)




        self.ax = self.fig.add_subplot(111)
        self.canvas.draw()



        self.plot_layout.addWidget(self.canvas, 1, 1, 20, 20)
        self.toolbar_layout.addWidget(self.toolbar, 21, 1, 1, 20)

    def update_plot(self, effective_subtrace_list, hist_list):
        self.update_plot_signal.emit(effective_subtrace_list, hist_list)

    def update_plot_signal_emitted(self, effective_subtrace_list, hist_list):
        try:
            t0 = time.time()
            for nst, st in enumerate(effective_subtrace_list):
                self.axes[nst, 0].cla()
                self.axes[nst, 0].plot(st)
                self.axes[nst, 1].cla()
                if len(hist_list[nst]) > 0:
                    for h in hist_list[nst]:
                        self.axes[nst, 1].plot(h['bin_edges'], h['hist'])
                else:
                    self.axes[nst, 1].text(
                        0.5,
                        0.5,
                        'HISTOGRAM FAILED',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.axes[nst, 1].transAxes,
                        color='r',
                        fontsize=30
                    )
                self.fig.tight_layout()
                self.fig.canvas.draw_idle()
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)