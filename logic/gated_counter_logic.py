from __future__ import print_function, absolute_import, division
__metaclass__ = type

import logic.misc as misc
import traceback
import time
import sys
import os
import threading
from PyQt5.QtCore import pyqtSignal
import logic.Analysis as Analysis
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import PyQt5.QtCore
import numpy as np
import logging
from hardware.Keysight_AWG_M8190.pym8190a import MultiChSeq as MCAS
from hardware.Keysight_AWG_M8190.pym8190a import start_awgs as start_awgs
import zmq
import logic.qudip_enhanced.qtgui.gui_helpers
from numbers import Number
import copy
import datetime
import os
import pylab as pb
import time

from collections import OrderedDict
from core.connector import Connector
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from qtpy import QtCore

class GatedCounter(GenericLogic):

    ##declare connections
    # Timetagger
    # fastcounter = Connector(interface='TimeTaggerInterface')
    # add possible signals here
    # Needed a connection to the queue as well... connection to mcas?
    fastcounter = Connector(interface='TimeTaggerInterface')
    mcas_holder = Connector(interface='McasDictHolderInterface')
    sigHistogramUpdated = QtCore.Signal()
    sigMeasurementFinished = QtCore.Signal()
    sigTraceUpdated = pyqtSignal(list, list)
    readout_interval = misc.ret_property_typecheck('readout_interval', Number)
    progress = misc.ret_property_typecheck('progress', int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.debug('The following configuration was found.')
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))
        self.readout_interval = 1e6 # DO NOT SET BELOW 0.2, plotting runs in main loop, and takes around 0.15, which then makes the console annoying to work with.
        self.readout_duration = 10e6
        self.trace = Analysis.Trace()
        self.analyze_trace_during_experiment = True #TODO make it False compatible.
        self.title = 'Gated_counter'

        #if title is not None:
        #    self.update_window_title(title)
        #self.tim
        self.raw_clicks_processing = False
        self.raw_clicks_processing_function = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._fast_counter_device = self.fastcounter()#FIXME
        self._mcas_dict = self.mcas_holder()
        #self._pulse_generator_device = self.pulsegenerator()
        # Maybe replace with the mcas holder?
        #self._save_logic = self.savelogic() #This is done in nuclear ops.
        #self._fit_logic = self.fitlogic() #-This is nice, we can keep it
        #self._traceanalysis_logic = self.traceanalysislogic1() # Done with Analysis class.
        #self.hist_data = None
        #self.trace = None
        #self.sigMeasurementFinished.connect(self.ssr_measurement_analysis)# is it?

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        return

    # =========================================================================
    #                           Raw Data Analysis
    # =========================================================================

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
        self.gated_counter_data = self._fast_counter_device.gated_counter_countbetweenmarkers.getData()

        #print('1 tt:',time.time()-t0)
        if False:#self.ZPL_counter: do later #Fixme
            if self.raw_clicks_processing:
                counter_name = 'raw_zpl'
                #print('init raw clicks processing name: ', counter_name)
                data = self._fast_counter_device.get_stream_data(counter_name=counter_name, kwargs=[])
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
                #     data = self._fast_counter_device.get_stream_data(counter_name=counter_name, kwargs=[])
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

                        # self._fast_counter_device.gated_counter_countbetweenmarkers.sync()
                        zpl_counter_data = getattr(self._fast_counter_device,counter_name).getData()#.astype(np.int64)
                        # getattr(self._fast_counter_device, counter_name).sync()
                        setattr(self, trace_name,zpl_counter_data)
                        # print('21 tt:', time.time() - t0)
                        if self.two_zpl_apd:
                            trace_name = 'zpl_2_counter_data_{i}_{j}'.format(i=i, j=j)
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            #self._fast_counter_device.gated_counter_countbetweenmarkers.sync()
                            zpl_counter_data = getattr(self._fast_counter_device,counter_name).getData()#.astype(np.int64)
                            # getattr(self._fast_counter_device, counter_name).sync()
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
        #self._fast_counter_device.gated_counter_countbetweenmarkers.clear()
        if self.ZPL_counter:
            if self.raw_clicks_processing:
                counter_name = 'raw_zpl'
                # getattr(self._fast_counter_device, counter_name).clear()
                #self._fast_counter_device.kill_stream(counter_name=counter_name, kwargs=[])
                # if self.two_zpl_apd:
                #     counter_name = 'raw_2_zpl'
                #     self._fast_counter_device.kill_stream(counter_name=counter_name, kwargs=[])

            else:
                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                        #getattr(self._fast_counter_device, counter_name).clear()

                        if self.two_zpl_apd:
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            #getattr(self._fast_counter_device, counter_name).clear()


    def stop_timetaggers(self):

        if hasattr(self._fast_counter_device, 'gated_counter_countbetweenmarkers'):
            self._fast_counter_device.gated_counter_countbetweenmarkers.stop()
        if self.ZPL_counter:
            # print('Gated counter stop TT ZPL_counter')

            if self.raw_clicks_processing:
                # print('Gated counter stop TT raw_clicks_processing')

                counter_name = 'raw_zpl'
                #self._fast_counter_device.stop_stream(counter_name=counter_name, kwargs=[])
                # if self.two_zpl_apd:
                #     # print('Gated counter stop TT two_zpl_apd')
                #
                #     counter_name = 'raw_2_zpl'
                #     self._fast_counter_device.stop_stream(counter_name=counter_name, kwargs=[])
            else:
                # print('Gated counter stop TT NOT== raw_clicks_processing')

                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                        getattr(self._fast_counter_device, counter_name).stop()

                        if self.two_zpl_apd:
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            getattr(self._fast_counter_device, counter_name).stop()

    def start_timetaggers(self):
        self._fast_counter_device.gated_counter_countbetweenmarkers.start()
        if self.ZPL_counter:
            if self.raw_clicks_processing:

                counter_name = 'raw_zpl'
                self._fast_counter_device.start_stream(counter_name=counter_name, kwargs=[])
                # if self.two_zpl_apd:
                #     counter_name = 'raw_2_zpl'
                #     self._fast_counter_device.start_stream(counter_name=counter_name, kwargs=[])
            else:
                for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
                    for j, window_ps in enumerate(self.window_ps_list):
                        counter_name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
                        getattr(self._fast_counter_device, counter_name).start()

                        if self.two_zpl_apd:
                            counter_name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
                            getattr(self._fast_counter_device, counter_name).start()

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

            if not self._mcas_dict.mcas_dict.debug_mode:
                start_awgs(self._mcas_dict.mcas_dict.awgs, ch_dict=ch_dict)

            self.progress = 0
            while True:
                if abort.is_set():
                    break
                # print('Gated counter is falling asleep for ',int(self.readout_duration / 1e6))
                time.sleep(int(self.readout_duration / 1e6))
                break
                # ready = self._fast_counter_device.gated_counter_countbetweenmarkers.ready()
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
                self._mcas_dict.mcas_dict.stop_awgs()

            self.stop_timetaggers()

            # begin2 = time.time()
            # self.clear_timetaggers()

            # self._fast_counter_device.gated_counter_countbetweenmarkers.stop()
            self.state = 'idle'

    def set_counter(self):
        self.ZPL_counter = False
        ## Needs to be adjusted to the qudi gated counter #TODO
        def f():
            nlp_per_point = sum([step[3] for step in self.trace.analyze_sequence])

            #TODO redo the interfaces . Init counter to gated counter now, or make it inside the TT class?
            self._fast_counter_device.count_between_markers(
                n_values=self.n_values - self.n_values % nlp_per_point if hasattr(self, '_n_values') else nlp_per_point * self.points
            )

            #ZPL STUF
            # if False: # self.raw_clicks_processing:
            #     name = 'raw_zpl'
            #     n_bins = self.n_values - self.n_values % nlp_per_point if hasattr(self,
            #                                                                       '_n_values') else nlp_per_point * self.points,
            #
            #     # print('n_bins ',n_bins)
            #     kwargs = dict(n_bins = n_bins[0]*len(self.raw_clicks_processing_channels),
            #                   channels=self.raw_clicks_processing_channels)
            #     # print('kwargs["n_bins"] ',kwargs["n_bins"])
            #
            #     self._fast_counter_device.create_stream(counter_name=name, kwargs=kwargs)
            #
            #     # if self.two_zpl_apd:
            #     #     name = 'raw_2_zpl'
            #     #     self._fast_counter_device.create_stream(counter_name=name, kwargs=kwargs)
            #
            #
            #     self.ZPL_counter = True

            # else:
            #     for i, start_trigger_delay_ps in enumerate(self.start_trigger_delay_ps_list):
            #         for j, window_ps in enumerate(self.window_ps_list):
            #             if (start_trigger_delay_ps is not None) and (window_ps is not None):
            #
            #                 name = 'gated_cbm_zpl_{i}_{j}'.format(i=i, j=j)
            #                 self._fast_counter_device.init_counter(
            #                     name,
            #                     n_values=self.n_values - self.n_values % nlp_per_point if hasattr(self,
            #                                                                                       '_n_values') else nlp_per_point * self.points,
            #                     delay_ps=start_trigger_delay_ps,
            #                     window_ps=window_ps
            #                 )
            #
            #                 if self.two_zpl_apd:
            #                     name = 'gated_cbm_2_zpl_{i}_{j}'.format(i=i, j=j)
            #                     self._fast_counter_device.init_counter(
            #                         name,
            #                         n_values=self.n_values - self.n_values % nlp_per_point if hasattr(self,
            #                                                                                           '_n_values') else nlp_per_point * self.points,
            #                         delay_ps=start_trigger_delay_ps,
            #                         window_ps=window_ps
            #                     )
            #
            #                 self.ZPL_counter = True

        for i in range(2):
            t = threading.Thread(target=f)
            t.start()
            t.join(5)
            if t.is_alive():
                logging.getLogger().info('Setting up counter failed!')
                logging.getLogger().info('Trying to restart timetagger..')
                self._fast_counter_device.restart_timetagger() #FIXME
            else:
                break
        else:
            raise Exception('Error: timeout.')

    def set_progress(self):
        if self._fast_counter_device.gated_counter_countbetweenmarkers.ready():
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

            #Instead send a signal
            #self.gui.update_plot(self.effective_subtrace_list, self.hist_list)
            self.sigTraceUpdated.emit(self.effective_subtrace_list, self.hist_list)

    def clear_plot(self, number_of_subtraces):
        self.clear_plot_signal.emit(number_of_subtraces)

### This is now replaced by the gated_counter_gui.py from qudi.
class GatedCounterQt(logic.qudip_enhanced.qtgui.gui_helpers.QtGuiClass):
    def __init__(self, parent=None, no_qt=None):
        super(GatedCounterQt, self).__init__(parent=parent, no_qt=no_qt, ui_filepath=os.path.join('C:\src\qudi\gui',
                                                                                                  r'qtgui\gated_counter.ui'))

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




