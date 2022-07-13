# -*- coding: utf-8 -*-

"""
This file contains the general logic for magnet control.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from hashlib import blake2b
import numpy as np
import time
import datetime

from qtpy import QtCore
from collections import OrderedDict
from core.connector import Connector
from core.pi3_utils import delay
from logic.generic_logic import GenericLogic


class MagnetLogic(GenericLogic):

    # declare connectors
    magnet_3d = Connector(interface='vectormagnet')
    timetagger = Connector(interface='TT')
    savelogic = Connector(interface='SaveLogic')
    optimizerlogic = Connector(interface='OptimizerLogic')
    confocallogic = Connector(interface='ConfocalLogic')


    # create signals internal
    sigScanFinished = QtCore.Signal()
    sigScanLoopBody = QtCore.Signal()

    # create signal to hardware
    sigRampMagnet = QtCore.Signal(list,list,bool)
    sigSetPswStatus = QtCore.Signal(int)
    sigRampToZero = QtCore.Signal()
    sigPauseRamp = QtCore.Signal()
    sigContinueRamp = QtCore.Signal()

    # create signals to gui
    sigUpdatePswStatusLabel = QtCore.Signal(str)
    sigRampFinished = QtCore.Signal()
    sigUpdateTwoDGraphData = QtCore.Signal()
    sigGotPos = QtCore.Signal(list,list) # B field in spherical coordinated and carthesian coordinates



    def __init__(self, config, **kwargs):

        # initialize variables with standard values
        # the GUI takes these as initial values as well
        self.phi_min = 0
        self.phi_max = 360
        self.n_phi = 10
        self.phis = np.linspace(self.phi_min, self.phi_max, self.n_phi)
        self.phi = 0
        self.theta_min = 0
        self.theta_max = 180
        self.n_theta = 10
        self.thetas = np.linspace(self.theta_min, self.theta_max, self.n_theta)
        self.theta = 0
        self.B = 0.01
        self.int_time = 1
        self.reps = 1

        # booleans for the scan
        self.abort_scan = False
        self.scanning_finished = False

        # other booleans
        self.refocusInitiatedByLogic = True

        # set up the image array for the plot
        self.thetaPhiImage = np.zeros((self.n_theta,self.n_phi))
        # matrix for testing
        self.thetaPhiImage = np.random.rand(self.n_theta,self.n_phi)
        for i in range(self.n_theta):
            for j in range(self.n_phi):
                self.thetaPhiImage[i,j] = 10*i+j

        super().__init__(config=config, **kwargs)


    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        #initialize hardware
        self._magnet_3d = self.magnet_3d()
        self._timetagger = self.timetagger()
        self._savelogic = self.savelogic()

        # initialize other logic
        self._scanninglogic = self.confocallogic()
        
        # connect signals from hardware
        self._magnet_3d.sigRampFinished.connect(self._magnet_ramp_finished)

        # connect signals to hardware
        self.sigRampMagnet.connect(self._magnet_3d.ramp)
        self.sigSetPswStatus.connect(self._magnet_3d.set_psw_status)
        self.sigRampToZero.connect(self._magnet_3d.ramp_to_zero)
        self.sigPauseRamp.connect(self._magnet_3d.pause_ramp)
        self.sigContinueRamp.connect(self._magnet_3d.continue_ramp)

        # connect internal signal
        self.sigScanLoopBody.connect(self._scan_loop_body)

        self.updatePswStatusInterval = 10000
        self.scanning = False

        self.pswStatusInterval = 10000
        self.magnetStatusInterval = 10000

        # start loop that updates psw status in gui
        self._update_psw_status_string_loop_body()
        return
        

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        # deactivates 3d magnet, rmaps it back to zero
        self._magnet_3d.on_deactivate()
        return


    #--------------------------------------------
    #functions to store values as class objects
    def set_phi_min(self,phi_min):
        self.phi_min = phi_min

    def set_phi_max(self,phi_max):
        self.phi_max = phi_max
    
    def set_n_phi(self,n_phi):
        self.n_phi = n_phi

    def set_phi(self,phi):
        self.phi = phi

    def set_theta_min(self,theta_min):
        self.theta_min = theta_min

    def set_theta_max(self,theta_max):
        self.theta_max = theta_max
    
    def set_n_theta(self,n_theta):
        self.n_theta = n_theta

    def set_theta(self,theta):
        self.theta = theta

    def set_B(self,B):
        self.B = B

    def set_int_time(self,int_time):
        self.int_time = int_time

    def set_reps(self,reps):
        self.reps = reps
    #--------------------------------------------


    def calc_xyz_from_angle(self,B,theta,phi):
        """ Calculates x,y,z from spherical coordinates.

        Returns list with values.
        """
        x = B * np.sin(np.deg2rad(theta)) * np.cos(np.deg2rad(phi))
        y = B * np.sin(np.deg2rad(theta)) * np.sin(np.deg2rad(phi))
        z = B * np.cos(np.deg2rad(theta))
        return [x,y,z]


    def save_2d_data(self, tag=None, timestamp=None):
        """Saves the data of the 2d magnet scan"""

        # create file and retun path to it
        filepath = self._savelogic.get_path_for_module(module_name='Magnet')

        if timestamp is None:
            timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_magnet_alignment_data'
        else:
            filelabel = 'magnet_alignment_data'

        # prepare the data in a dict or in an OrderedDict:
        matrix_data = OrderedDict()
        matrix_data['Alignment Matrix'] = self.thetaPhiImage

        parameters = OrderedDict()
        parameters['Time at Data save'] = timestamp
        parameters['absolute B field'] = self.B
        parameters['B field units'] = 'Tesla'
        parameters['theta_min (°)'] = self.theta_min
        parameters['theta_max (°)'] = self.theta_max
        parameters['n_theta'] = self.n_theta
        parameters['phi_min (°)'] = self.phi_min
        parameters['phi_max (°)'] = self.phi_max
        parameters['n_phi'] = self.n_phi
        parameters['thetas (°)'] = self.thetas
        parameters['phis (°)'] = self.phis


        self._savelogic.save_data(matrix_data, filepath=filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp)

        # not absolutely necessary, kill it if it breaks anything
        self.log.debug('Magnet 2D data saved to:\n{0}'.format(filepath))
        return


    def start_scan(self,params):
        """params need to be list with the following structure:
        [B,theta_min,theta_max,n_theta,phi_min,phi_max,n_phi,int_time]
        """
        [B,theta_min,theta_max,n_theta,phi_min,phi_max,n_phi,int_time] = params
        # store params as class objects
        self.B = B
        self.theta_min = theta_min
        self.theta_max= theta_max
        self.n_theta = n_theta
        self.phi_min = phi_min
        self.phi_max = phi_max
        self.n_phi = n_phi
        self.int_time = int_time
        # initialize image
        self.thetaPhiImage = np.zeros((self.n_theta,self.n_phi))
        # scanning params
        self.scanning = True
        self.thetas = np.linspace(self.theta_min,self.theta_max,self.n_theta)
        self.phis = np.linspace(self.phi_min,self.phi_max,self.n_phi)
        self._thetas = self.thetas.copy()
        self._thetas = list(self._thetas)
        self._theta = self._thetas.pop(0)
        self._phis = self.phis.copy()
        self._phis = list(self._phis)
        # start first pixel
        self.sigScanLoopBody.emit()
        return


    def _scan_loop_body(self):
        if len(self._phis) == 0:
            if len(self._thetas) == 0:
                self.scanning = False
                self.sigScanFinished.emit()
                return
            else:
                self._phis = self.phis.copy()
                self._phis = list(self._phis)
                self._phi = self._phis.pop(0)
                self._theta = self._thetas.pop(0)
        else:
            self._phi = self._phis.pop(0)
        self.ramp(field_spherical = [self.B,self._theta,self._phi])
        return
       
    def _magnet_ramp_finished(self):
        if not self.scanning:
            # do nothing if ramp was not initiated by magnet scan
            # only pass signal through to gui
            self.sigRampFinished.emit()
            return
        else:
            ## take data
            # initialize counter
            ctr = self._timetagger.counter(refresh_rate=1/self.int_time,n_values=1) #channels=[1,2] to specify APD channels
            # after counter is set up, we need to wait until the time bin has passed. (+10% just to be sure.)
            delay(1100*self.int_time)
            cts = ctr.getData()[-1][0]/self.int_time # [-1]: last entry is sum of both APDs, [0] is entry
            ## write counts into image
            # get posi in grid from theta and phi
            index_theta = np.where(self.thetas==self._theta)[0][0]
            index_phi = np.where(self.phis==self._phi)[0][0]
            self.thetaPhiImage[index_theta,index_phi] = cts
            # update picture in gui
            self.sigUpdateTwoDGraphData.emit()
            # call loop body again
            self.sigScanLoopBody.emit()
            return

    def get_psw_status_string(self):
        state = self.get_ramping_state()
        heater = self.get_psw_status()
        if 9 in state:
            ret_str = 'PSW heating.'
        elif 10 in state:
            ret_str = 'PSW cooling'
        else:
            if heater == [1,1,1]:
                ret_str = 'PSW warm'
            elif 1 in heater and heater != [1,1,1]:
                ret_str = f'PSW in {str(heater)}'
            elif heater == [0,0,0]:
                ret_str = 'PSW cold'
            else:
                ret_str = 'unknown state'
        return ret_str


    def get_ramping_state(self):
        # TODO: would be nicer with signals
        state = self._magnet_3d.get_ramping_state()
        return state

    
    def get_psw_status(self):
        # TODO: would be nicer with signals
        heater = self._magnet_3d.get_psw_status()
        return heater

    
    def _update_psw_status_string_loop_body(self):
        status_string = self.get_psw_status_string()
        
        self.pswStatusTimer = QtCore.QTimer()
        self.pswStatusTimer.setSingleShot(True)
        self.pswStatusTimer.timeout.connect(self._update_psw_status_string_loop_body, QtCore.Qt.QueuedConnection)
        self.pswStatusTimer.start(self.pswStatusInterval)

        self.sigUpdatePswStatusLabel.emit(status_string)
        return


    def cool_psw(self):
        self.sigSetPswStatus.emit(0)
        return

    
    def heat_psw(self):
        self.sigSetPswStatus.emit(1)
        return


    def ramp_to_zero(self):
        """Tells magnet to ramp to zero"""
        self.sigRampToZero.emit()
        return


    def ramp(self,field_spherical=None, field_carthesian=None):
        field_carthesian = None if field_carthesian==[None] else field_carthesian
        if (field_spherical == None) and (field_carthesian != None):
            field_target = field_carthesian
        elif (field_spherical != None) and (field_carthesian == None):
            field_target = self.calc_xyz_from_angle(field_spherical[0],field_spherical[1],field_spherical[2])
        else:
            raise Exception('Field needs to specified either in spherical or carthesian coordinates')
        self.sigRampMagnet.emit(field_target, [None,None,None], False)
        return


    def pause_ramp(self):
        self.sigPauseRamp.emit()
        return

    def continue_ramp(self):
        self.sigContinueRamp.emit()
        return


    def get_magnet_field(self):
        field_mag = self._magnet_3d.get_field()
        return field_mag


    def get_field_spherical(self):
        """Returns the magnetic field in spherical coordinates.
        
        @return list: spherical coordinates as [B,theta,phi]
        """
        [x,y,z] = self.get_magnet_field()
        
        B = np.sqrt(x**2 + y**2 + z**2)
        if np.isclose(B, 0.0):
            theta = 0
            phi = 0
        else:
            theta = np.arccos(z/B)
            theta = np.rad2deg(theta)
            phi = np.arctan2(y,x)
            phi = np.rad2deg(phi)

        return [B,theta,phi]


    def mag_field_requested(self):

        [Bx,By,Bz] = self.get_magnet_field()
        [B,theta,phi] = self.get_field_spherical()

        self.sigGotPos.emit([B,theta,phi],[Bx,By,Bz])
        return