import os
import time
import datetime
from qtpy import QtCore
import numpy as np
from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from utils import delay, flip_powermirror, calibrate

class Automatedmeasurement(QtCore.QThread):
    """ How to use this thing:
        1. create pois with poimanager (Qudi)
        2. create instance of class
        3. specify steps with "init_steps()"
        4. start with "start()"
            4.1 stop with "stop()"
        If pois have changed since class was initiated, update pois with "init_pois()"
            
        How to add new steps:
        1. write function that starts what you want to do (e.g. take a spectrum)
        2. add it to the func_dict in __init__()
        3. look for the signal that gets emitted once the step is done or create it yourself
        4. connect it to _next_step() in __init__()
    """

    sigNextPoi = QtCore.Signal()
    sigNextStep = QtCore.Signal()
    sigStepDone = QtCore.Signal()
    abort = False
    steps = ['move', 'optimize', 'spectrum', 'time_trace']
    steps_bg = ['move', 'spectrum', 'time_trace']
    def __init__(self, save_folder, calibration):
        super().__init__()
        self.func_dict = {
            'move' : self.move_to_poi,
            'optimize' : self.optimize_on_poi,
            'spectrum' : self.take_spectrum,
            'time_trace' : self.measure_time_trace
        }
        self.save_folder = save_folder
        self.calibration = calibration
        self.on_activate()
    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._spectrumlogic = spectrumlogic
        self._scannerlogic = scannerlogic
        self._optimizerlogic = optimizerlogic
        self.sigNextPoi.connect(self._next_poi, QtCore.Qt.QueuedConnection)
        self.sigNextStep.connect(self._next_step,QtCore.Qt.QueuedConnection )
        self.sigStepDone.connect(self._next_step,QtCore.Qt.QueuedConnection )
        spectrumlogic.sig_specdata_taken.connect(self.save_spectra, QtCore.Qt.QueuedConnection)
        self._optimizerlogic._sigFinishedAllOptimizationSteps.connect(self._next_step, QtCore.Qt.QueuedConnection)
        self.angles_for_pol_dep_spec = np.linspace(0,360,3) # TODO: change num to 100

    def on_deactivate(self):
        pass

    def start(self):
        """Starts the measurements"""
        self.abort = False
        self.init_pois()
        self.sigNextPoi.emit()
        return
    
    
    def stop(self):
        """Stops the program"""
        self.abort = True
        return
    
    
    def init_pois(self,poi_names=None):
        if poi_names==None:
            self.poi_names = list((np.arange(len(self._scannerlogic.pois)) + 1).astype(str))#self._poimanagerlogic.poi_names
        else:
            self.poi_names = poi_names
        self._poi_names = list(self.poi_names).copy() # shallow copy
        pois = self._scannerlogic.pois
        texts = (np.arange(len(self._scannerlogic.pois)) + 1).astype(str)
        self.poi_positions = {t: pos for t, pos in zip(texts, pois)} #self._poimanagerlogic.poi_positions
        
        return
    
    
    def init_steps(self,steps):
        """Stores the steps as class object."""
        keys = self.func_dict.keys()
        if not set(steps).issubset(set(keys)):
            raise Exception('The following steps are not listed in the func_dict: %s'% (list(set(steps) - set(keys))))
        return
    
    @QtCore.Slot()
    def _next_poi(self):
        """Iterates through the pois.
        
        Sets the next poi to be the active one and starts the measurements on this one."""
        
        print('poi')
        # Stop program if finished or user wants to stop
        if self.abort or (len(self._poi_names)==0):
            print('Stopping(poi).')
            print(self.abort,len(self._poi_names))
            return
        # Choose the first poi in the list, set it as the current one and delete it.
        self._current_poi_name = self._poi_names.pop(0)
        print('Current poi %s'%self._current_poi_name)
        # updates the position of the current poi
        self._current_poi_position = self.poi_positions[self._current_poi_name]
        
        # copy the steps into an array that we can modify
        if self._current_poi_name != '1':
            self._steps = self.steps.copy() #shallow copy
        else:
            self._steps = self.steps_bg.copy()
        print(self._steps)
        # start the steps
        self.sigNextStep.emit()
        return
    @QtCore.Slot()
    def _next_step(self):
        """Iterates through the steps."""
        print('step')
        if self.abort:
            print('Stopping (step).')
            return
        if len(self._steps)==0:
            # all steps for the current poi are done, go to next poi
            self.sigNextPoi.emit()
            return
        # choose next step in list as current one and remove it
        self._current_step = self._steps.pop(0)
        print('Current step: %s'%self._current_step)
        print('_steps', self._steps)
        print('steps', self.steps)
        #run the step
        self.func_dict[self._current_step]()
        motor_pi3.moveToAbsolutePosition(motor=0, pos=310)
        delay(1000)
        return
    
    
    def move_to_poi(self,poi_name=None,rs=1000):
        """Moves to the current poi"""
        print('move')
        if poi_name==None:
            poi_name = self._current_poi_name
            poi_position = self._current_poi_position
        else:
            poi_position = self.poi_positions[poi_name]
        if rs == None:
            # get return slowness from confocal logic 
            rs = self._scannerlogic.return_slowness
        print(poi_name)
        # script will move to next line once position is reached

        self._scannerlogic.go_to_position('scanner', x=poi_position[0],y=poi_position[1],z=poi_position[2], rs=rs)
        self.current_poi_position = poi_position
        # no signal is emitted once position is reached. 
        # We need to send one by ourself to keep consistency with the rest of the script.
        
        self.sigStepDone.emit()
        return
    
    
    def optimize_on_poi(self):
        """Tells optimizerlogic to start the refocus.
        
        On completion, a signal is emitted from optimizerlogic
        """
        print('optimize')
        delay(200)
        confocal.refocus_clicked()
        
        return
    
    
    def take_spectrum(self):
        """Tells spectrumlogic to start taking a spectrum.
        
        """
        print('spec')
        delay(2000)
        spectrometer._mw.rec_single_spectrum_Action.trigger()
        return
    @QtCore.Slot()
    def save_spectra(self):
        print("saving spectra")
        self._spectrumlogic.save_spectrum_data(filepath=self.save_folder, name_tag = self._current_poi_name + '_575LP_spectrum_inttime_' + str(5))
        self.sigStepDone.emit()
          
    def measure_time_trace(self):
#         tt_counter.set_up_correlation(bins_width = 200, n_values = 1000)
        for step, power in self.calibration.items():
            motor_pi3.moveToAbsolutePosition(motor=0, pos=int(step))
            delay(2000)
            count_params = {
                "channels":[0, 1],
                "bins_width": bin_width,
                "n_values":n_vals
                }
            corr_params = {
                "channels":[0, 1],
                "bins_width": 500,
                "n_values":1000
                }
            
            timetagger.set_counter(count_params)
            delay(2000)
            counts = timetagger.countrate  * tt_counter._count_frequency
            savelogic.save_array_as_text(counts, filename=self._current_poi_name + '_timetrace_n' + str(n_vals) + '_'+ str(step) + '_' + '.txt',filepath=self.save_folder)
        #get correlation
        motor_pi3.moveToAbsolutePosition(motor=0, pos=int(list(self.calibration.keys())[-2]))
        delay(2000)
        timetagger.set_correlation(corr_params)
        delay(10000)
        dt, corrs = timetagger.corr_data
        corr_data = np.vstack((dt, corrs))
        savelogic.save_array_as_text(corr_data, filename=self._current_poi_name + '_correlation_' + '_'+ str(list(self.calibration.keys())[-2]) + '_' + '.txt',filepath=self.save_folder)
        self.sigStepDone.emit()
        
    def take_pol_dependent_spectrum(self):
        """ Starts a polarization dependent spectrum measurement.

        Tells the ello to rotate (the lambda/2 plate).
        And then tells spectrumlogic to start taking a spectrum.
        """
        print('pol dep spec')

        angles = self.angles_for_pol_dep_spec

        for angle in angles:
            poi_name = self._current_poi_name
            name_tag = poi_name + '_' + str(angle)
            if self._ello_rotor is not None:
                self._ello_rotor.move_abs(to_angle=angle)
            self._spectrumlogic.get_single_spectrum()
            self._spectrumlogic.save_spectrum_data(name_tag=name_tag)
        self.sigStepDone.emit()
        return
# optimizerlogic._max_offset_z