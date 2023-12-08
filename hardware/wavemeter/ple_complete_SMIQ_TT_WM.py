import numpy as np

from traits.api import Trait, Instance, Property, String, Range, Float, Int, Bool, Array, Enum, Button, Any, List, Str
from traits.has_traits import on_trait_change

from traitsui.api import View, Item, HGroup, VGroup, VSplit, Tabbed, EnumEditor, TextEditor, Group, Spring, StatusItem
from traitsui.qt4.extra.qt_view import QtView
from enable.api import Component, ComponentEditor
from chaco.api import ArrayPlotData, Plot, PlotLabel, RdBu, Spectral, gray, reverse, viridis
from chaco.tools.api import LineInspector
from chaco.tools import simple_zoom
from chaco.tools.api import PanTool
from logic.ple_logic_SMIQ_TT_WM import PLELogic

from tools.chaco_addons import SavePlot as Plot, SaveTool, SaveHPlotContainer as HPlotContainer

import time
import threading
import logging

from tools.emod import ManagedJob

from tools.utility import GetSetItemsMixin
from analysis.fit_analysis import fit_n_lorentzian, n_lorentzian

from pathlib import Path
from WAVEMETER import WAVEMETER, PLE_VOLT_TO_FREQ_RATIO
if WAVEMETER:
    from wavemeter import WaveMeter, PIDParams

# from hardware.TimeTagger import CountBetweenMarkers
RdBu_r = reverse(RdBu)

WAVEMETER_CHANNEL = 1
WAVEMETER_CHANNEL_OFF = 0
if WAVEMETER:
    WAVEMETER_PID = PIDParams(1.1, 0.38, 0.82, 1.05, .155, 9.99)
else:
    WAVEMETER_PID = None
DLC_PRO_VOLTAGE_MULTIPLIER = 10

def format_arrays(array):
    with np.printoptions(formatter={'float': lambda x: f"{x:0.3f}"}):
        return str(array)


class PLE(ManagedJob, GetSetItemsMixin):
    """Provides PLE measurements."""

    sweeper = Any()

    # starting and stopping
    keep_data = Bool(
        False
    )  # helper variable to decide whether to keep existing data
    resubmit_button = Button(
        label='resubmit',
        desc=
        'Submits the measurement to the job manager. Tries to keep previously acquired data. Behaves like a normal submit if sequence or time bins have changed since previous run.'
    )

    # measurement parameters
    central_frequency = Float(
        default_value=327.1,
        low=327.,
        hight=328.,
        desc='Central Frequency [THz]',
        label='Central Freq. [THz]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%f'
        )
    )
    frequency_range = Float(
        default_value=20,
        low=.1,
        hight=24.,
        desc='frequency range [GHz]',
        label='Freq. range [GHz]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%f'
        )
    )
    resolution = Float(
        default_value=0.01,
        desc='resolution [GHz]',
        label='resolution [GHz]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%f'
        )
    )
    
    # if no wavemeter one can do a voltage scan
    central_volt = Float(
        default_value=0.,
        low=-3.,
        hight=3.,
        desc='Central Voltage [V]',
        label='Central Volt. [V]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%f'
        )
    )
    volt_range = Float(
        default_value=3.,
        low=0.,
        hight=6.,
        desc='Voltage range [V]',
        label='Volt. range [V]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%f'
        )
    )
    volt_resolution = Float(
        default_value=0.01,
        desc='resolution [V]',
        label='resolution [V]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%f'
        )
    )

    MW_power = Float(
        default_value=-25,
        low=-150,
        high=40,
        desc='Microwave Power [dBm]',
        label='MW Power [dBm]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float
        )
    )

    MW_freq = Float(
        default_value=70,
        desc='Microwave Frequency [MHz]',
        label='MW Freq [MHz]',
        editor=TextEditor(
            auto_set=False,
            enter_set=True,
            evaluate=float,
        )
    )

    MW_power_2 = Range(
        low=-150,
        high=40,
        value=-25,
        desc='Microwave 2 Power [dBm]',
        label='MW 2 Power [dBm]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%e'
        )
    )

    MW_freq_2 = Float(
        default_value=172,
        desc='Microwave 2 Frequency [MHz]',
        label='MW 2 Freq [MHz]',
        editor=TextEditor(auto_set=False, enter_set=True, evaluate=float)
    )

    MW_power_3 = Range(
        low=-100,
        high=-15,
        value=-25,
        desc='Microwave 3 Power [dBm]',
        label='Mw 3 Power [dBm]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%e'
        )
    )

    MW_freq_3 = Float(
        default_value=172,
        desc='Microwave 3 Frequency [MHz]',
        label='MW 3 Freq [MHz]',
        editor=TextEditor(auto_set=False, enter_set=True, evaluate=float)
    )

    seconds_per_point = Float(
        default_value=0.01,
        label='seconds_per_point [s]',
        editor=TextEditor(
            auto_set=False, enter_set=True, evaluate=float, format_str='%e'
        )
    )

    n_lines = Range(
        low=1,
        high=10000,
        value=10,
        desc='Number of lines in Matrix',
        label='Matrix lines',
        mode='text',
        auto_set=False,
        enter_set=True
    )

    #time estimation
    no_sweeps = Int(0)
    average_counts = Float(0)

    # measurement data
    frequency = Array()
    voltage = Array()

    counts = Array()
    counts_matrix = Array()
    volt_wavelen_array = {}

    stop_time = Range(
        low=1.,
        value=np.inf,
        desc='Time after which the experiment stops by itself [s]',
        label='Stop time [s]',
        mode='text',
        auto_set=False,
        enter_set=True
    )
    run_time = Float(value=0.0, desc='Run time [s]', label='Run time [s]')
    colormap = Enum("viridis", 'RdBu_r', 'Spectral', 'gray')

    # plotting
    line_label = Instance(PlotLabel)

    line_data = Instance(ArrayPlotData)
    line_plot = Instance(Plot, editor=ComponentEditor())
    line_figure = Instance(HPlotContainer, editor=ComponentEditor())

    # line_plot2 = Instance(Plot, editor = ComponentEditor())
    matrix_data = Instance(ArrayPlotData)
    matrix_plot = Instance(Plot, editor=ComponentEditor())
    matrix_figure = Instance(HPlotContainer, editor=ComponentEditor())
    
    status_string_left = Str('')
    status_string_right = Str('')
    cursordata = Instance(ArrayPlotData)

    # enables
    enable_repump_730 = Bool(True, label='Repump 730')
    enable_repump_780 = Bool(False, label='Repump 780')
    repump_pulsed = Bool(True, label='Pulsed repump')
    repump_length = Int(100000000, label="Repump length [ns]")
    repump_delay = Int(1200, label="Repump delay [ns]")
    enable_microwave = Bool(True, label="Enable Microwave")
    enable_AOM_A1 = Bool(False, label="Enable AOM A1")
    enable_AOM_A2 = Bool(True, label="Enable AOM A2")
    enable_wavemeter = Bool(True, label="Enable Wavemeter")
    switch_volt_to_GHz = Bool(False, label="Switch to GHz",desc="Calculates the detuning in GHz with a predefined correction factor.")
    
    AWG_SMIQ_switch_button = Button(label="Switch AWG/SMIQ")
    AWG_SMIQ_label = Str("SMIQ")

    # enable second microwave source
    enable_microwave_2 = Bool(False, label='Enable Microwave 2')
    enable_microwave_3 = Bool(False, label='Enable Microwave 3')
    enable_Spin_polarized_PLE = Bool(False, label='Spin Polarized PLE')

    # control data fitting
    perform_fit = Bool(False, label='perform fit')
    number_of_resonances = Int(
        default_value=2,
        desc='Number of Lorentzians used in fit',
        label='N',
        auto_set=False,
        enter_set=True
    )

    # fit result
    fit_parameters = Array(value=np.array((np.nan, np.nan, np.nan, np.nan)))
    fit_frequencies = Array(value=np.array((np.nan,)), label='Frequency [GHz]')
    fit_frequencies_v = Array(value=np.array((np.nan,)), label='Frequency [V]')
    fit_freq_err = Array(value=np.array((np.nan,)), label='freq err [GHz]')
    fit_freq_err_v = Array(value=np.array((np.nan,)), label='freq err [V]')
    fit_amplitudes = Array(value=np.array((np.nan,)), label='Amplitudes [cts]')
    fit_line_width = Array(value=np.array((np.nan,)), label='FWHM [MHz]')
    fit_line_width_v = Array(value=np.array((np.nan,)), label='FWHM [mV]')
    fit_linewidth_err = Array(value=np.array((np.nan,)), label='lw err [MHz]')
    fit_linewidth_err_v = Array(value=np.array((np.nan,)), label='lw err [mV]')
    fit_contrast = Array(value=np.array((np.nan,)), label='contrast [%]')

    def __init__(self, logic: PLELogic, **kwargs):
        super(PLE, self).__init__(**kwargs)

        self.dark_theme = True
        self.logic = logic
        if not WAVEMETER:
            self.enable_wavemeter = False

        self._create_line_plot()
        # self._create_line_plot2()
        self._create_matrix_plot()
        self.on_trait_change(
            self._update_line_data_index, 'frequency, switch_volt_to_GHz', dispatch='ui'
        )
        self.on_trait_change(
            self._update_line_data_value, 'counts', dispatch='ui'
        )
        # self.on_trait_change(self._update_line_data_inde, 'frequency', dispatch = 'ui')
        # self.on_trait_change(self._update_line_data_value2, 'laser_power', dispatch = 'ui')
        self.on_trait_change(
            self._update_line_data_fit, 'fit_parameters,switch_volt_to_GHz', dispatch='ui'
        )
        self.on_trait_change(
            self._update_matrix_data_value, 'counts_matrix', dispatch='ui'
        )
        self.on_trait_change(
            self._update_matrix_data_index, 'n_lines,frequency,switch_volt_to_GHz', dispatch='ui'
        )
        self.on_trait_change(
            self._update_fit,
            'counts,perform_fit,number_of_resonances,threshold,switch_volt_to_GHz',
            dispatch='ui'
        )
        

    def _counts_matrix_default(self):
        return np.zeros((self.n_lines, len(self.frequency)))

    def _frequency_default(self):
        if self.enable_wavemeter:
            return np.arange(
                self.central_frequency*1e3 - self.frequency_range / 2,
                self.central_frequency*1e3 + self.frequency_range / 2 + self.resolution,
                self.resolution
            )
        else: 
            return np.arange(
                self.central_volt - self.volt_range / 2,
                self.central_volt + self.volt_range / 2 + self.volt_resolution,
                self.volt_resolution
            )

    def _counts_default(self):
        return np.zeros(self.frequency.shape)

    # def configure_nidaq(self):
    #     self.create_nidq_tasks()
    #     self.configure_nidaq_timing()

    # def configure_nidaq_timing(self):
    #     pass

    # def create_nidaq_tasks(self):
    #     self.create_analog_in()
    #     self.create_analog_out()
    #     self.create_counter()

    # def create_counter(self):
    #     pass

    # def create_analog_in(self):
    #     pass

    # def create_analog_out(self):
    #     pass

    def _run(self):

        try:
            self.state = 'run'
            self.old_counts = self.counts.copy()
            self.old_counts_matrix = self.counts_matrix.copy()

            # add static PS signals if not pulsed
            ps_channels = []
            if self.enable_AOM_A1:
                ps_channels += ["A1"]
            if self.enable_AOM_A2:
                ps_channels += ["A2"]
            if self.enable_repump_730 and not self.repump_pulsed:
                ps_channels += ["730"]
            if self.enable_repump_780 and not self.repump_pulsed:
                ps_channels += ["780"]
            if self.enable_microwave:
                ps_channels += ['MW']
            if self.enable_microwave_2:
                ps_channels += ['MW2']
            

            if (not self.keep_data) or (np.any(self._frequency_default() != self.frequency) ):
                # reset
                self. frequency = self._frequency_default()
                self.counts_matrix = self._counts_matrix_default()
                self.counts = np.zeros_like(self.frequency)
                self.old_counts = np.zeros_like(self.frequency)
                self.old_counts_matrix = self.counts_matrix
                self.run_time = 0.0
                self.no_sweeps = 0
                
            self.frequency = self.logic.setup(
                self.AWG_SMIQ_label,
                self.central_frequency*1e3,
                self.frequency_range,
                self.resolution,
                self.central_volt,
                self.volt_range,
                self.volt_resolution,
                self.seconds_per_point,
                self.enable_wavemeter,
                self.enable_microwave,
                self.enable_microwave_2,
                self.MW_freq,
                self.MW_power,
                self.MW_freq_2,
                self.MW_power_2,
                self.enable_repump_730,
                self.enable_repump_780,
                self.repump_pulsed,
                self.repump_length,
                self.repump_delay,
                ps_channels
            )
            
                

            if self.run_time >= self.stop_time:
                self.state = 'done'
                return
            volt_wavelen_array = {}
            
            start_time = time.time()
            self.counts = self.old_counts
            self.counts_matrix = self.old_counts_matrix
            while self.run_time < self.stop_time:
                if threading.currentThread().stop_request.isSet():
                    break

                counts, volt_wavelen_array = self.logic.scan_line(volt_wavelen_array)
                
                self.counts += counts
                self.counts_matrix = np.vstack(
                    (counts, self.counts_matrix[:-1, :])
                )
                self.trait_property_changed('counts', self.counts)
                self.volt_wavelen_array = volt_wavelen_array
                
                self.run_time = time.time() - start_time
                self.no_sweeps += 1

            self.logic.cleanup()
            
        except:
            logging.getLogger().exception('Error in PLE.')
            self.state = 'error'
        else:
            if self.run_time < self.stop_time:
                self.state = 'idle'
            else:
                try:
                    self.save(self.filename)
                except:
                    logging.getLogger(
                    ).exception('Failed to save the data to file.')
                self.state = 'done'
        finally:
            self.logic.cleanup()

    # plotting
    def laser_length_pulsed(self):
        sequence = [(["aom"], self.laser_length)]
        sequence.append
        if self.enable_microwave2:
            sequence = [(["aom", 'microwave'], self.laser_length)]
        self.pulse_generator.Sequence(sequence)
        
    def _enable_wavemeter_changed(self,new):
        if new:
            self.switch_volt_to_GHz = True

    def _create_line_plot(self):
        line_data = ArrayPlotData(
            frequency=np.array((0., 1.)),
            counts=np.array((0., 0.)),
            freq_fit=np.array((0., 1.)),
            fit=np.array((0., 0.))
        )
        line_plot = Plot(
            line_data, padding=8, padding_left=64, padding_bottom=32
        )
        renderer = line_plot.plot(
            ('frequency', 'counts'), style='line', color='blue'
        )
        if self.enable_wavemeter or self.switch_volt_to_GHz:
            line_plot.index_axis.title = 'Detuning [GHz]'
        else:
            line_plot.index_axis.title = 'Detuning [V]'
        line_plot.value_axis.title = 'Fluorescence counts'
        line_label = PlotLabel(
            text='', hjustify='left', vjustify='bottom', position=[64, 128]
        )
        line_plot.overlays.append(line_label)
        line_plot.tools.append(SaveTool(line_plot))
        
        #add cursor to show data at mouse position
        cursordata = ArrayPlotData(
            cursor_index=np.array([]), cursor_value=np.array([])
        )
        renderer[0].overlays.append(
            LineInspector(
                component=renderer[0],
                axis='index',
                inspect_mode="space",
                write_metadata=True,
                is_listener=True,
                color="black",
                line_style='solid',
                line_width=1,
            )
        )
        renderer[0].overlays.append(
            LineInspector(
                component=renderer[0],
                axis='value',
                inspect_mode="space",
                write_metadata=True,
                is_listener=True,
                color="black",
                line_style='solid',
                line_width=1,
            )
        )
        
        self.line_label = line_label
        self.line_data = line_data
        self.line_plot = line_plot

        if self.dark_theme:
            text_color = 0xbbbbbb
            bg_color = 0x3c3f41
            line_plot.index_axis.tick_label_color = text_color
            line_plot.value_axis.tick_label_color = text_color
            line_plot.index_axis.title_color = text_color
            line_plot.value_axis.title_color = text_color
        else:
            text_color = "grey"
            bg_color = "white"
            
        # now we can zoom in with mouse wheel
        zoom = simple_zoom.SimpleZoom(line_plot)
        line_plot.overlays.append(zoom)
        
        # now we can pan with the mouse
        pan = PanTool(line_plot)
        line_plot.tools.append(pan)
        
        self.cursordata = cursordata
        self.line_renderer = renderer[0]
        self.line_renderer.index.on_trait_change(
            self._metadata_changed, "metadata_changed"
        )
        self.line_renderer.value.on_trait_change(
            self._metadata_changed, "metadata_changed"
        )

        container = HPlotContainer(bgcolor=bg_color)
        container.add(line_plot)
        self.line_figure = container
        
    @on_trait_change("enable_wavemeter, switch_volt_to_GHz")    
    def _change_line_plot_xlabel(self):
        if self.enable_wavemeter or self.switch_volt_to_GHz:
            line_plot = self.line_plot
            line_plot.index_axis.title = 'Detuning [GHz]'
            line_plot.request_redraw()
            matrix_plot = self.matrix_plot
            matrix_plot.index_axis.title = 'Detuning [GHz]'
            matrix_plot.request_redraw()
        else:
            line_plot = self.line_plot
            line_plot.index_axis.title = 'Detuning [V]'
            line_plot.request_redraw()
            matrix_plot = self.matrix_plot
            matrix_plot.index_axis.title = 'Detuning [V]'
            matrix_plot.request_redraw()

    def _metadata_changed(self):
        if "selections" in self.line_renderer.index.metadata and "selections" in self.line_renderer.value.metadata:
            x_ndx, y_ndx = self.line_renderer.index.metadata[
                "selections"], self.line_renderer.value.metadata["selections"]
            if y_ndx and x_ndx:

                self.cursordata.set_data('cursor_index', np.array(x_ndx))
                self.cursordata.set_data('cursor_value', np.array(y_ndx))
                xval = '{:.3f}'.format(
                    float(self.cursordata.arrays['cursor_index'])
                )
                yval = '{:.3f}'.format(
                    float(self.cursordata.arrays['cursor_value']) / 1000.
                )
                self.status_string_right = "(" + xval + "MHz," + yval + "kCnt)"
                return
        self.cursordata.set_data('cursor_index', np.array([]))
        self.cursordata.set_data('cursor_value', np.array([]))
        self.status_string_right = ''
        
    def _create_matrix_plot(self):
        matrix_data = ArrayPlotData(image=np.zeros((2, 2)))
        matrix_plot = Plot(
            matrix_data, padding=8, padding_left=64, padding_bottom=32
        )
        if self.enable_wavemeter or self.switch_volt_to_GHz:
            matrix_plot.index_axis.title = 'Detuning [GHz]'
        else:
            matrix_plot.index_axis.title = 'Detuning [V]'
        matrix_plot.value_axis.title = 'line #'
        matrix_plot.img_plot(
            'image',
            xbounds=(self.frequency[0], self.frequency[-1]),
            ybounds=(0, self.n_lines),
            cmap='viridis',
            colormap=viridis
        )
        matrix_plot.tools.append(SaveTool(matrix_plot))
        self.matrix_data = matrix_data
        self.matrix_plot = matrix_plot

        if self.dark_theme:
            text_color = 0xbbbbbb
            bg_color = 0x3c3f41
            matrix_plot.index_axis.tick_label_color = text_color
            matrix_plot.value_axis.tick_label_color = text_color
            matrix_plot.index_axis.title_color = text_color
            matrix_plot.value_axis.title_color = text_color
        else:
            text_color = "grey"
            bg_color = "white"

        container = HPlotContainer(bgcolor=bg_color)
        container.add(matrix_plot)
        self.matrix_figure = container

    def _perform_fit_changed(self, new):
        plot = self.line_plot
        if new:
            plot.plot(
                ('freq_fit', 'fit'), style='line', color='red', name='fit'
            )
            self.line_label.visible = True
        else:
            try:
                plot.delplot('fit')
                self.line_label.visible = False
            except:
                pass
        plot.request_redraw()

    @on_trait_change('no_sweeps')
    def _no_sweeps_changed(self):
        try:
            self.average_counts = self.counts.mean() / self.no_sweeps
        except:
            self.average_counts = 0
        self.status_string_left = 'Counts per sweep:' + '{:.2f}'.format(
            self.average_counts
        ) + ", No. Sweeps:" + str(self.no_sweeps)


    def _update_line_data_index(self):
        freq = self.frequency.copy()
        if self.switch_volt_to_GHz and not self.enable_wavemeter:
            freq *= PLE_VOLT_TO_FREQ_RATIO
        self.line_data.set_data('frequency', freq)
        self.line_data.set_data(
            'freq_fit',
            np.linspace(np.min(freq), np.max(freq), 500)
        )
        # self.counts_matrix = self._counts_matrix_default()

    def _update_line_data_value(self):
        self.line_data.set_data('counts', self.counts)

    # def _update_line_data_value3(self):
    #     self.line_data.set_data('counts1', self.counts1)

    def _update_line_data_fit(self):
        freq = self.frequency.copy()
        if self.switch_volt_to_GHz and not self.enable_wavemeter:
            freq *= PLE_VOLT_TO_FREQ_RATIO
        if not np.any(np.isnan(self.fit_parameters)):
            x = np.linspace(np.min(freq), np.max(freq), 500)
            N = (self.fit_parameters.size - 1) // 3

            self.line_data.set_data(
                'fit', n_lorentzian(N, x, *self.fit_parameters)
            )
        else:
            try:
                self.line_plot.delplot('fit')
                self.line_data.del_data('fit')
                self.line_label.visible = False
            except:
                pass

    def _update_matrix_data_value(self):
        self.matrix_data.set_data('image', self.counts_matrix)

    def _update_matrix_data_index(self):
        freq = self.frequency.copy()
        if self.switch_volt_to_GHz and not self.enable_wavemeter:
            freq *= PLE_VOLT_TO_FREQ_RATIO
        if self.n_lines > self.counts_matrix.shape[0]:
            self.counts_matrix = np.vstack(
                (
                    self.counts_matrix,
                    np.zeros(
                        (
                            self.n_lines - self.counts_matrix.shape[0],
                            self.counts_matrix.shape[1]
                        )
                    )
                )
            )
        else:
            self.counts_matrix = self.counts_matrix[:self.n_lines]
        self.matrix_plot.components[0].index.set_data(
            (freq.min(), freq.max()),
            (0.0, float(self.n_lines))
        )

    def _update_fit(self):
        # when fit not enabled or fit no finished, skip
        if not self.perform_fit:
            return
        freq = self.frequency.copy()
        if self.switch_volt_to_GHz and not self.enable_wavemeter:
            freq *= PLE_VOLT_TO_FREQ_RATIO

        xdata = freq
        ydata = self.counts
        N = self.number_of_resonances

        bounds = [
            (xdata.min(), xdata.max()),  # x0
            (.01, 10),  # HWHM
            (1, ydata.max())  # amplitude
        ] * N  # N times
        bounds += [
            (ydata.min(), ydata.min() + (ydata.max() - ydata.min()) / 3)
        ]  # background

        res, err = fit_n_lorentzian(N, xdata, ydata, bounds)

        self.fit_amplitudes = res.x[2:-1:3]
        self.fit_frequencies = res.x[:-1:3]  # GHz
        self.fit_frequencies_v = res.x[:-1:3]  # V
        self.fit_freq_err = err[:-1:3]
        self.fit_freq_err_v = err[:-1:3]
        self.fit_line_width = res.x[1:-1:3] * 1e3 * 2  # MHz (FWHM)
        self.fit_line_width_v = res.x[1:-1:3] * 1e3 * 2  # mV (FWHM)
        self.fit_linewidth_err = err[1:-1:3] * 1e3 * 2
        self.fit_linewidth_err_v = err[1:-1:3] * 1e3 * 2
        self.fit_contrast = 100 * res.x[2:-1:3] / (res.x[2:-1:3] + res.x[-1])

        if not res.success:
            logging.getLogger().debug('PLE fit failed.', exc_info=True)
            self.fit_parameters = np.array([np.nan])
            self.fit_amplitudes = np.array([np.nan])
            self.fit_frequencies = np.array([np.nan])
            self.fit_frequencies_v = np.array([np.nan])
            self.fit_line_width = np.array([np.nan])
            self.fit_line_width_v = np.array([np.nan])
            self.fit_freq_err = np.array([np.nan])
            self.fit_freq_err_v = np.array([np.nan])
            self.fit_linewidth_err = np.array([np.nan])
            self.fit_linewidth_err_v = np.array([np.nan])
            return

        self.fit_parameters = res.x

    # saving data
    def save(self, filename):
        super().save(filename)
        path = Path(filename)
        self.matrix_plot.save(f'{path.with_name(path.stem + "-matrix_plot.png")}')
        self.line_plot.save(f'{path.with_name(path.stem + "-line_plot.png")}')

    def save_all(self, filename):
        self.line_plot.save(filename + '_PLE_Line_Plot.png')
        self.matrix_plot.save(filename + '_PLE_Matrix_Plot.png')
        self.save(filename + '_PLE.pys')

    # react to GUI events

    def _colormap_changed(self, new):
        if new == "RdBu_r":
            func = RdBu_r
        elif new == "viridis":
            func = viridis
        elif new == "Spectral":
            func = Spectral
        elif new == "gray":
            func = gray
        else:
            raise NameError(f"colormap {new} not found")
        self.matrix_plot.color_mapper = func(
            self.matrix_plot.color_mapper.range
        )
        self.matrix_figure.request_redraw()

    def _AWG_SMIQ_switch_button_fired(self):
        if str(self.AWG_SMIQ_label) == "SMIQ":
            self.AWG_SMIQ_label = "AWG"
        elif str(self.AWG_SMIQ_label) == "AWG":
            self.AWG_SMIQ_label = "SMIQ"

    def submit(self):
        """Submit the job to the JobManager."""
        self.keep_data = False
        ManagedJob.submit(self)

    def resubmit(self):
        """ReSubmit the job to the JobManager."""
        self.keep_data = True
        ManagedJob.submit(self)

    def _resubmit_button_fired(self):
        """React to start button. Submit the Job."""
        self.resubmit()

    def default_traits_view(self):
        if self.dark_theme:
            with open("dracula.qss", "r") as f:
                stylesheet = f.read()
        else:
            stylesheet = ""

        return QtView(
            VGroup(
                HGroup(
                    Item('submit_button', show_label=False),
                    Item('remove_button', show_label=False),
                    Item('resubmit_button', show_label=False),
                    Item('priority', enabled_when='state != "run"'),
                    Item('state', style='readonly'),
                    Item('run_time', style='readonly', format_str='%.f'),
                    Item('stop_time'),
                ),
                HGroup(
                    Item('filename', springy=True),
                    Item('save_button', show_label=False),
                    Item('load_button', show_label=False)
                ),
                HGroup(
                      Item("AWG_SMIQ_switch_button",show_label=False),
                      Item("AWG_SMIQ_label",show_label=False,style="readonly")  
                    ),
                HGroup(
                    Item('enable_repump_730', enabled_when='state != "run"'),
                    Item('enable_repump_780', enabled_when='state != "run"'),
                    Item(
                        'repump_pulsed',
                        enabled_when='state != "run" and (enable_repump_730 or enable_repump_780)'
                    ),
                    Item(
                        'repump_length',
                        enabled_when=
                        'state != "run" and (enable_repump_730 or enable_repump_780) and repump_pulsed'
                    ),
                    Item(
                        'repump_delay',
                        enabled_when=
                        'state != "run" and (enable_repump_730 or enable_repump_780) and repump_pulsed'
                    ),
                    Item(
                        'enable_AOM_A1',
                        width=-80,
                        enabled_when='state != "run"'
                    ),
                    Item(
                        'enable_AOM_A2',
                        width=-80,
                        enabled_when='state != "run"'
                    ),
                    Item(
                        'enable_wavemeter',
                        width=-80,
                        enabled_when='state != "run"'
                    ),
                    Spring(),
                ),
                HGroup(
                    Item(
                        'enable_microwave',
                        width=-80,
                        enabled_when='state != "run"'
                    ),
                    Item('MW_freq', enabled_when='state != "run"'),
                    Item('MW_power', enabled_when='state != "run"'),
                    Item('enable_microwave_2', enabled_when='state != "run"'),
                    Item('MW_freq_2', enabled_when='state != "run"'),
                    Item(
                        'MW_power_2', width=-80, enabled_when='state != "run"'
                    ),
                    # Item('enable_microwave_3', enabled_when='state != "run"'),
                    # Item('MW_freq_3', enabled_when='state != "run"'),
                    # Item(
                    #     'MW_power_3', width=-80, enabled_when='state != "run"'
                    # ),
                    Spring(),
                ),
                VGroup(
                    HGroup(
                        Item(
                            'central_frequency',
                            width=-80,
                            enabled_when='state != "run"',
                            visible_when="enable_wavemeter",
                        ),
                        Item(
                            'frequency_range',
                            width=-80,
                            enabled_when='state != "run"',
                            visible_when="enable_wavemeter",
                        ),
                        Item(
                            'resolution',
                            width=-80,
                            enabled_when='state != "run"',
                            visible_when="enable_wavemeter",
                        ),
                        Item(
                            'central_volt',
                            width=-80,
                            enabled_when='state != "run"',
                            visible_when="not enable_wavemeter",
                        ),
                        Item(
                            'volt_range',
                            width=-80,
                            enabled_when='state != "run"',
                            visible_when="not enable_wavemeter",
                        ),
                        Item(
                            'volt_resolution',
                            width=-80,
                            enabled_when='state != "run"',
                            visible_when="not enable_wavemeter",
                        ),
                        Item(
                            'switch_volt_to_GHz',
                            visible_when="not enable_wavemeter",  
                        ),
                        Item(
                            'seconds_per_point',
                            width=-80,
                            enabled_when='state != "run"'
                        ),
                        Spring(),
                    ),
                ),
                VGroup(
                    HGroup(
                        Item('perform_fit'),
                        Item('number_of_resonances', width=-60),
                        Item('n_lines', width=-60),
                        Item('colormap', width=-100),
                        Spring(),
                    ),
                    HGroup(
                        Item('fit_frequencies', style='readonly', springy=True,visible_when='switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_frequencies_v', style='readonly', springy=True,visible_when='not switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_freq_err', style='readonly', springy=True,visible_when='switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_freq_err_v', style='readonly', springy=True,visible_when='not switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_line_width', style='readonly', springy=True,visible_when='switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_line_width_v', style='readonly', springy=True,visible_when='not switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_linewidth_err', style='readonly', springy=True,visible_when='switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_linewidth_err_v', style='readonly', springy=True,visible_when='not switch_volt_to_GHz',format_func=format_arrays,),
                        Item('fit_contrast', style='readonly', springy=True,format_func=format_arrays,),
                        Item('fit_amplitudes', style='readonly', springy=True,format_func=format_arrays,),
                    ),
                ),
                VSplit(
                    Item('matrix_figure', show_label=False, resizable=True),
                    Item('line_figure', show_label=False, resizable=True),
                ),
            ),
            title='PLE',
            width=1300,
            height=800,
            style_sheet=stylesheet,
            buttons=[],
            resizable=True,
            statusbar=[
            StatusItem(name='status_string_left', width=0.67),
            StatusItem(name='status_string_right', width=0.33)
        ],
        )

    get_set_items = [
        'central_frequency',
        'resolution',
        'frequency_range',
        'central_volt',
        'volt_range',
        'volt_resolution',
        'frequency',
        'counts',
        'counts_matrix',
        'old_counts',
        'old_counts_matrix',
        'voltage',
        'fit_parameters',
        'fit_contrast',
        'fit_line_width',
        'fit_line_width_v',
        'fit_linewidth_err',
        'fit_linewidth_err_v',
        'fit_frequencies',
        'fit_frequencies_v',
        'fit_freq_err',
        'fit_freq_err_v',
        'perform_fit',
        'run_time',
        'enable_repump_730',
        'enable_repump_780',
        'repump_pulsed',
        'repump_length',
        'repump_delay',
        'seconds_per_point',
        'stop_time',
        'n_lines',
        'number_of_resonances',
        'enable_AOM_A1',
        'enable_AOM_A2',
        'enable_wavemeter',
        'switch_volt_to_GHz',
        'enable_microwave',
        'enable_microwave_2',
        'enable_microwave_3',
        'MW_freq',
        'MW_power',
        'MW_freq_2',
        'MW_power_2',
        'MW_freq_3',
        'MW_power_3',
        'no_sweeps',
        '__doc__'
    ]