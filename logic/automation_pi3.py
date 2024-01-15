"""author: Erik and Jonathan"""

import json
import os

import time
import datetime
from qtpy import QtCore
import numpy as np
from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from core.pi3_utils import delay
from PyQt5 import QtTest
import csv

class AutomatedMeasurementLogic(GenericLogic):
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
    # declare connectors
    poimanagerlogic = Connector(interface='PoiManagerLogic')
    savelogic = Connector(interface='SaveLogic')
    scannerlogic = Connector(interface='ConfocalLogic')
    spectrumlogic = Connector(interface='SpectrumLogic')
    optimizerlogic = Connector(interface = 'OptimizerLogic')
    setupcontrollogic = Connector(interface = 'SetupControlLogic')
    # mcas_holder = Connector(interface='McasDictHolderInterface')
    counterlogic = Connector(interface='CounterLogic')
    laserscannerlogic = Connector(interface = 'LaserScannerLogic')
    powerstabilizationlogic= Connector(interface='PowerStabilizationLogic')
    
    # internal signals
    sigNextPoi = QtCore.Signal()
    sigNextStep = QtCore.Signal()
    sigStepDone = QtCore.Signal()
    sigAutomizedRefocus = QtCore.Signal() # connected to confocal gui
    SigLoop = QtCore.Signal()

    abort = False
    steps_bg = ['move', 'spectrum', 'spectrum']
    #steps = ['move', 'optimize', 'ple']
    #steps_bg = []

    
    _laser_power_list=[0.5,1,1.5,2,3,4,5,7.5,10,15,20,25,30,35]

    _MW_power_list=list(np.arange(-30,-16,1))*len(_laser_power_list)
    
    #steps= ['resonant_optimize', 'next_laser_power', 'ple']*len(_laser_power_list)
    steps= ['move', 'optimize', 'spectrum', 'spectrum']
    #steps= (['next laser power']+['next MW power','ple']*len(_MW_power_list))*len(_laser_power_list)

    #scan ranges for PLE
    scan_range=[[-3,0],[-2,2],[0,3]] #should_work without jumps
    secure_scan_range=np.array([np.arange(-3,2,1),np.arange(-1,4,1)]).T #this scan range really should work if the previous should fail

    # Secure_scan_range={tuple(secure_scan_range[i-1]):secure_scan_range[i] for i in range(len(secure_scan_range))}
    # Scan_range={tuple(scan_range[i-1]):scan_range[i] for i in range(len(scan_range))}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.func_dict = {
            'move' : self.move_to_poi,
            'optimize' : self.optimize_on_poi,
            'resonant_optimize' : self.resonant_optimize_on_poi,
            'spectrum' : self.take_spectrum,
            'ple' : self.take_PLE,
            'next MW power': self.next_MW_power,
            'next_laser_power': self.next_laser_power,
            "measure_PLE": self.measure_ple
        }
       
    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # self._awg = self.mcas_holder()
        self._save_logic = self.savelogic() 
        self._poimanager_logic = self.poimanagerlogic() 
        self._spectrum_logic = self.spectrumlogic() 
        self._scanner_logic = self.scannerlogic()
        self._optimizer_logic = self.optimizerlogic()
        self._counter_logic = self.counterlogic()
        self._laser_scanner_logic = self.laserscannerlogic()
        self._setupcontrol_logic = self.setupcontrollogic()
        self._powerstabilization_logic = self.powerstabilizationlogic()

        # self._poimanagerlogic = self.poimanagerlogic() # is already included in confocal gui
     
        self.save_folder = "C:/Data/2023/AutomizedSpectra/" # save_folder0
        
        ## signals
        # connect internal signals
        self.sigNextPoi.connect(self._next_poi, QtCore.Qt.QueuedConnection)
        self.sigNextStep.connect(self._next_step,QtCore.Qt.QueuedConnection )
        
        # connect signals that mark the completion of one step
        self.sigStepDone.connect(self._next_step,QtCore.Qt.QueuedConnection )
        self._spectrum_logic.sig_specdata_taken.connect(self.save_spectrum, QtCore.Qt.QueuedConnection)
        self._laser_scanner_logic.sigScanFinished.connect(self.save_ple, QtCore.Qt.QueuedConnection)
        #spectrumlogic.sig_specdata_updated.connect(self._next_step)
        #self._optimizer_logic.sigRefocusFinished.connect(self._next_step, QtCore.Qt.QueuedConnection)
        self._powerstabilization_logic.SigStabilized.connect(self.laser_power_stabilized, QtCore.Qt.QueuedConnection)
        self.SigLoop.connect(self.loop, QtCore.Qt.QueuedConnection)
        

        ## initialisation of variables
        self.angles_for_pol_dep_spec = np.linspace(0,360,3) # TODO: change num to 100
        # self.create_flipmirror_sequence()
        # self.create_repump_sequence()
        
        self.bin_width = int(1e12/50)
        self.n_vals = 300
        self.tag_for_saving = '' # mark the file name if the autofocus was not successfully found
        
        self._spectrum_logic.update_integration_time(20)
        self.measurementStarted = False
        self.Laserpower_stabilized=False
        self.Laserpower_stabilized_fail=False

    def on_deactivate(self):
        self.stop()
        
    # def create_flipmirror_sequence(self):
    #     seq = self._awg.mcas(name="FlippyFloppy", ch_dict={"2g": [1,2],"ps": [1]})
    #     seq.start_new_segment("Start", loop_count=100)
    #     seq.asc(name='Flip', length_mus=500, FlipMirror=True)
    #     self._awg.mcas_dict.stop_awgs()
    #     self._awg.mcas_dict['FlippyFloppy'] = seq
    #     self._awg.mcas_dict.print_info()

    def run_repump(self):
        self._setupcontrol_logic.enable_A1 = False
        self._setupcontrol_logic.enable_A2 = False
        self._setupcontrol_logic.enable_Green = False
        self._setupcontrol_logic.enable_Repump = True
        self._setupcontrol_logic.run()

    def run_repumpA1A2(self):
        self._setupcontrol_logic._awg.mcas_dict['RepumpAndA1AndA2'].run()
        # self._setupcontrol_logic.enable_A1 = True
        # self._setupcontrol_logic.enable_A2 = True
        # self._setupcontrol_logic.enable_Green = False
        # self._setupcontrol_logic.enable_Repump = True
        # self._setupcontrol_logic.run()
    def run_A1(self):
        self._setupcontrol_logic._awg.mcas_dict['A1'].run()
        # self._setupcontrol_logic.enable_A1 = True
        # self._setupcontrol_logic.enable_A2 = False
        # self._setupcontrol_logic.enable_Green = False
        # self._setupcontrol_logic.enable_Repump = False
        # self._setupcontrol_logic.run()
    def run_A2(self):
        self._setupcontrol_logic._awg.mcas_dict['A2'].run()
        # self._setupcontrol_logic.enable_A1 = False
        # self._setupcontrol_logic.enable_A2 = True
        # self._setupcontrol_logic.enable_Green = False
        # self._setupcontrol_logic.enable_Repump = False
        # self._setupcontrol_logic.run()


    def measure_ple(self):
        for Range in self.scan_range:
            #measure PLE with range
            #stich parts toguether

            pass
        #save PLE

    def next_MW_power(self):
        print("setting MW Power")
        if len(self.MW_power_list)>0:
            new_power=self.MW_power_list.pop(0)
            print("new power",new_power)
            # self._setupcontrol_logic.MW1_power=new_power
            # self._setupcontrol_logic.MW2_power=new_power
            # self._setupcontrol_logic.MW3_power=new_power
            self._laser_scanner_logic.MW1_Power=new_power
            self._laser_scanner_logic.MW2_Power=new_power
            self._laser_scanner_logic.MW3_Power=new_power
            print(self._laser_scanner_logic.MW1_Power)

        self.sigNextStep.emit()

    @QtCore.Slot()
    def laser_power_stabilized(self):
        self.Laserpower_stabilized=True

    def next_laser_power(self):
        print("setting laserpower")
        if len(self.laser_power_list)>0:
            self._setupcontrol_logic._awg.mcas_dict.stop_awgs()
            self.run_A2()

            new_power=self.laser_power_list.pop(0)
            self.Laserpower_stabilized=False
            self._powerstabilization_logic.TargetPower=new_power
            self._powerstabilization_logic.SigStartControl.emit()
            self.Laserpower_stabilized_fail=False
            self.start_time=time.time()
            self.loop() #wait until power is stabilized


    @QtCore.Slot()     
    def loop(self):
        #print("looping")
        if not(self.Laserpower_stabilized):
            QtTest.QTest.qSleep(250)
            if time.time()-self.start_time<100: #do not try to sabilize over an infinite time period
                self.SigLoop.emit()
            else:
                print("Stabilization not successful")
                self.Laserpower_stabilized_fail=True
                self._setupcontrol_logic.AOM_volt=1
                self.end_looping()
        else:
            self.end_looping()

    def end_looping(self):
        #self._powerstabilization_logic.SigStopControl.emit()
        QtTest.QTest.qSleep(200)
        self._setupcontrol_logic._awg.mcas_dict.stop_awgs()
        self.sigNextStep.emit()


    def flip_spectrometermirror(self):
        # define how you want to flip your mirror. probably just via pulsestreamer or with a separate qudi-module
        self._setupcontrol_logic.Flipmirror_Button_Clicked(True) #simulate a click
        # #delay(20)
        # time.sleep(0.02)
        # #self._awg.mcas_dict['Repump'].run()
        # self._awg.mcas_dict["setupcontrol"].run()
        # #delay(1000)
        QtTest.QTest.qSleep(500)

    def start(self):
        """Starts the measurements"""
        try:
            self._spectrum_logic._spectrometer_device.on_activate()
            # save  current save options
            self.get_save_pdf = self._spectrum_logic._save_logic.save_pdf
            self.get_save_png = self._spectrum_logic._save_logic.save_png

            # overwrite save options. Only txt should be saved.
            self._spectrum_logic._save_logic.save_pdf = False
            self._spectrum_logic._save_logic.save_png = False
        except:
            print("No unopended device found.")

        
        self.abort = False
        self.measurementStarted = True
            
        self.laser_power_list= self._laser_power_list.copy()
        self.MW_power_list=self._MW_power_list.copy()
        self.init_pois()
        self.sigNextPoi.emit()
        return
    
    
    def stop(self):
        """Stops the program"""
        self.abort = True
        self.measurementStarted = False
        #TODO : disconnect all the signals which were connoected!!!!!!!!!!
        return
    
    
    def init_pois(self,poi_names=None):
        if poi_names==None:
            self.poi_names = list((np.arange(len(self._scanner_logic.pois)) + 1).astype(str))#self._poimanagerlogic.poi_names
        else:
            self.poi_names = poi_names
        # copy the names into an array that we can modify
        self._poi_names = list(self.poi_names).copy() # shallow copy
        pois = self._scanner_logic.pois
        texts = (np.arange(len(self._scanner_logic.pois)) + 1).astype(str)
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
        # Stop program if finished or user wants to stop
        if self.abort or (len(self._poi_names)==0):
            print('Stopping(poi).')
            print(self.abort,len(self._poi_names))
            self._setupcontrol_logic._awg.mcas_dict.stop_awgs()
        
            # Restore save options to previous state
            self._spectrum_logic._save_logic.save_pdf = self._spectrum_logic.get_save_pdf
            self._spectrum_logic._save_logic.save_png = self._spectrum_logic.get_save_png
            return

        # Choose the first poi in the list, set it as the current one and delete it.
        self._current_poi_name = self._poi_names.pop(0)
        print('Current poi %s'%self._current_poi_name)
        # updates the position of the current poi
        self._current_poi_position = self.poi_positions[self._current_poi_name]
        print("_next_poi: _current_poi_position", self._current_poi_position)
        # copy the steps into an array that we can modify
        if self._current_poi_name != '1':
            self.record_background = False
            self._steps = self.steps.copy() #shallow copy
        else:
            self.record_background = True
            self._steps = self.steps_bg.copy()
        print(self._steps)
        # start the steps
        self.sigNextStep.emit()
        return

        # AttributeError: 'Automatedmeasurement' object has no attribute '_steps'
        # Traceback (most recent call last):

        #   File "C:\src\qudi\logic\automation_pi3.py", line 206, in _next_step (now line 213)
        #     if len(self._steps)==0:

    @QtCore.Slot()
    def _next_step(self):
        """Iterates through the steps."""
        if not self.measurementStarted:
            return
        elif self.abort:
            print('Stopping (step).')
            # Restore save options to previous state
            self._spectrum_logic._save_logic.save_pdf = self.get_save_pdf
            self._spectrum_logic._save_logic.save_png = self.get_save_png
            self._setupcontrol_logic._awg.mcas_dict.stop_awgs()
            return
        elif len(self._steps)==0:
            # all steps for the current poi are done, go to next poi
            self.sigNextPoi.emit()
            return
        else:
            # choose next step in list as current one and remove it
            self._current_step = self._steps.pop(0)
            print('Current step: %s'%self._current_step)
            self.func_dict[self._current_step]()
            return
    
    def move_to_poi(self,poi_name=None,rs=1000):
        """Moves to the current poi"""
        if poi_name==None:
            poi_name = self._current_poi_name
            poi_position = self._current_poi_position
        else:
            poi_position = self.poi_positions[poi_name]
        if rs == None:
            # get return slowness from confocal logic 
            rs = self._scanner_logic.return_slowness
        print("POI name: ", poi_name)
        # script will move to next line once position is reached

        self._scanner_logic.go_to_position('scanner', x=poi_position[0],y=poi_position[1],z=poi_position[2], rs=rs)
        self.current_poi_position = poi_position
        # no signal is emitted once position is reached. 
        # We need to send one by ourself to keep consistency with the rest of the script.
        
        self.sigStepDone.emit()
        return
    
    def move_to_poi_failed_autofocus(self,poi_name=None,rs=1000):
        """Moves to the current poi"""
        if poi_name==None:
            poi_name = self._current_poi_name
            poi_position = self._current_poi_position
        else:
            poi_position = self.poi_positions[poi_name]
        if rs == None:
            # get return slowness from confocal logic 
            rs = self._scanner_logic.return_slowness
        print("POI name: ", poi_name)
        # script will move to next line once position is reached

        self._scanner_logic.go_to_position('scanner', x=poi_position[0],y=poi_position[1],z=poi_position[2], rs=rs)
        self.current_poi_position = poi_position
        # no signal is emitted once position is reached. 
        # We need to send one by ourself to keep consistency with the rest of the script.
        
        return
    
    
    def optimize_on_poi(self):
        """Tells optimizerlogic to start the refocus.
        
        On completion, a signal is emitted from optimizerlogic
        """
        self.tag_for_saving = ''
        QtTest.QTest.qSleep(200)
        self.run_repump()
        self.check_countrate(tag = 'mirror_up')
        crosshair_pos = self._scanner_logic.get_position()
        self._optimizer_logic.start_refocus(crosshair_pos, caller_tag = 'confocalgui') # TODO: fix me; What happens when caller tag is gui? Is crosshair
        while not self._optimizer_logic.refocus_finished:
            QtTest.QTest.qSleep(250)
        self._next_step()
        # self._optimizer_logic.start_refocus(initial_pos = [self._scanner_logic._current_x,self._scanner_logic._current_y,self._scanner_logic._current_z], caller_tag = 'automation_logic')
    
    def resonant_optimize_on_poi(self): # TODO: combine with other optimize
        """Tells optimizerlogic to start the refocus.
        
        On completion, a signal is emitted from optimizerlogic
        """
        print("automationlogic x,y,z,a position before refocus:", self._optimizer_logic._scanning_device.get_scanner_position())
        self.tag_for_saving = ''
        QtTest.QTest.qSleep(200)
        self.run_repumpA1A2()
        self.check_countrate(tag = 'mirror_up')
        self._optimizer_logic.start_refocus(initial_pos = [self._scanner_logic._current_x,self._scanner_logic._current_y,self._scanner_logic._current_z], caller_tag = 'automation_logic')
        return
    
    
    def take_spectrum(self):
        """Tells spectrumlogic to start taking a spectrum.
        
        """
        self.check_autofocus_close_to_poi()
        self.flip_spectrometermirror()
        QtTest.QTest.qSleep(1000)
        self.check_countrate(tag = 'mirror_down')
        QtTest.QTest.qSleep(1000)
        print("STARTED TAKING SPECTRUM")
        now = time.time()
        self._spectrum_logic.get_single_spectrum()
        later = time.time()-now
        print("ENDED TAKING SPECTRUM")
        print(later)
        self.flip_spectrometermirror()
        return

    def take_PLE(self):
        self.check_countrate(tag = 'mirror_up')
        self._setupcontrol_logic._awg.mcas_dict.stop_awgs()
        print("start scanning the laser")
        self._laser_scanner_logic.start_scanning()
        #After PLE scan is finished, a signal is emitted by _laser_scanner_logic which saves the collected data
        return

   

    def check_countrate(self, tag = ''):
        print("Checking Mirror Position...")
        self.run_repump()
        QtTest.QTest.qSleep(2000)
        countrate_limit = 400
        iteration = 0
        avg_counts = np.mean(self._counter_logic.countdata[0][-5:-1]) # average over 10 data points aquired
        if tag == 'mirror_up':
            while (avg_counts < countrate_limit) and (iteration < 5):
                print('avg_counts: ', avg_counts)
                iteration +=1
                self.flip_spectrometermirror()
                QtTest.QTest.qSleep(1000)
                self.run_repump()
                QtTest.QTest.qSleep(2000)
                # self.move_to_poi_failed_autofocus(self._current_poi_name) 
                avg_counts = np.mean(self._counter_logic.countdata[0][-5:-1]) # average over 10 data points aquired
                QtTest.QTest.qSleep(1000)
                if iteration >= 2:
                    self.tag_for_saving = '_autofocus_not_sucessful'
            print("mirror should be up")
        elif tag == 'mirror_down':
            while (avg_counts > countrate_limit) and (iteration < 5):
                print('avg_counts: ', avg_counts)
                iteration +=1
                self.flip_spectrometermirror()
                QtTest.QTest.qSleep(1000)
                self.run_repump()
                QtTest.QTest.qSleep(2000)
                avg_counts = np.mean(self._counter_logic.countdata[0][-5:-1]) # average over 10 data points aquired
                QtTest.QTest.qSleep(1000)
            print("mirror should be down")
        return

    
    def check_autofocus_close_to_poi(self):
        # TODO: CHECK SIGNAL TO NOISE IN REFOCUS
        # Check if optimized position is within reach of poi. otherwise mark it in file.
        x_offset = np.abs(self._optimizer_logic.optim_pos_x-self.current_poi_position[0]) # difference between poi and gaussian fit
        y_offset = np.abs(self._optimizer_logic.optim_pos_y-self.current_poi_position[1]) # difference between poi and gaussian fit
        x_width = self._optimizer_logic.optim_sigma_x # width of gaussian fit
        y_width = self._optimizer_logic.optim_sigma_y # width of gaussian fit
        
        scan_window = self._optimizer_logic.refocus_XY_size

        if (x_offset > 0.5*scan_window) or (y_offset > 0.5*scan_window) or (x_width < 0.1e-6) or (y_width < 0.1e-6) or (x_width > 1.2e-6) or (y_width > 1.2e-6):
            self.tag_for_saving = '_autofocus_not_matching_POI'
        if self._current_poi_name == '1':
            self.tag_for_saving = '_background'

    def check_for_V2_in_spectrum(self):
        current_spectrum = self._spectrum_logic._spectrum_data[1, :]-self.spectrum_background
        # TODO: Check which index corresponds to 917.2nm


    @QtCore.Slot()
    def save_spectrum(self):
        
        # save data
        self._spectrum_logic.save_spectrum_data(filepath=self.save_folder, name_tag = self._current_poi_name + '_850LP_inttime_' + str(self._spectrum_logic.integration_time) + self.tag_for_saving)

        if self._current_poi_name == '1':
            # only takes the signal of first recorded POI (background), not the wavelength. Will be substracted from other spectra to determine if V2 is present
            self.spectrum_background = self._spectrum_logic._spectrum_data[1, :]

        
        self.sigStepDone.emit()

    @QtCore.Slot() #what is this?   
    def save_ple(self):
        QtTest.QTest.qSleep(1000) # give the logic the time to make a fit
        filename = self._laser_scanner_logic.Filename
        print("Filename:", filename)
        #filename += str(new_power)
        #print("Filename:", filename)
        self._laser_scanner_logic.save_data(tag=filename)
        self.sigStepDone.emit()

    def StartAutoMeas_Button(self,on):
        self._save_logic.save_array_as_text(data = self._scanner_logic.pois, filename = 'POIs.txt', filepath = self.save_folder)
        self.start()

    def StopAutoMeas_Button(self,on):
        self.stop()

    def SavePOIs_Button(self,on):
        print(self._scanner_logic.pois)
        self._save_logic.save_array_as_text(data = self._scanner_logic.pois, filename = 'POIs.txt', filepath = self.save_folder)

        
        
    def DeletePOIs_Button(self,on):
        self._scanner_logic.pois = np.array([]) 

    def SetSequence_Button(self,on):
        self.steps = self.steps_preliminary  
        
    def SetBackgroundSeq_Button(self,on):
        self.steps_bg = self.steps_bg_preliminary 
        
    def Sequence_lineEdit(self,value):
        self.steps = str(value)
        
    def Background_lineEdit(self,value):
        self.steps_bg_preliminary = str(value)

    def SaveFolder_lineEdit(self,value):
        self.save_folder = str(value)
        

    def copy_pois_from_poilogic(self):
        newpois = []
        for entry in self._poimanager_logic.poi_positions:
            newpois.append(self._poimanager_logic.poi_positions[entry].tolist())
        self._scanner_logic.pois = np.array(newpois)