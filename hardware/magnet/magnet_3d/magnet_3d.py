# -*- coding: utf-8 -*-

"""
This module controls a 3D magnet.

The 3D magnet consists of three 1D magnets, to which it needs to be connected to.

Config for copy paste:
    magnet_3d:
        module.Class: 'magnet.3dmagnet.magnet_3d'
        connect:
            magnet_x: 'magnet_x'
            magnet_y: 'magnet_y'
            magnet_z: 'magnet_z'


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
from qtpy import QtCore
from datetime import datetime

from core.module import Base
from core.connector import Connector




class vectormagnet(Base):

    # declare connector
    # Note: you must create the interface file and give it to the class in the hardware file.
    magnet_x = Connector(interface='Magnet1DInterface')
    magnet_y = Connector(interface='Magnet1DInterface')
    magnet_z = Connector(interface='Magnet1DInterface')

    # create internal signals
    sigInternalRampFinished = QtCore.Signal()
    sigRamp = QtCore.Signal()
    sigRampToZero = QtCore.Signal()

    # create other signals
    sigRampFinished = QtCore.Signal()


    def on_activate(self):
        self._magnet_x = self.magnet_x()
        self._magnet_y = self.magnet_y()
        self._magnet_z = self.magnet_z()

        # connect internal signals
        self.sigInternalRampFinished.connect(self._ramp_loop)
        self.sigRamp.connect(self._ramp_loop)
        self.sigRampToZero.connect(self._ramp_to_zero_loop)

        self.debug = True#False # triggers print statements

        self._abortRampLoop = False
        self.rampTimerInterval = 10000
        self.fastRampTimerInterval = 10000
        self.safeRampTimerInterval = 10000
        self._abortRampToZeroLoop = False
        self.rampToZeroTimerInterval = 10000
        return 0


    def on_deactivate(self):
        self._magnet_x.on_deactivate()
        self._magnet_y.on_deactivate()
        self._magnet_z.on_deactivate()
        return 0


    def get_coil_constants(self):
        const_x = self._magnet_x.get_coil_constant()
        const_y = self._magnet_y.get_coil_constant()
        const_z = self._magnet_z.get_coil_constant()
        return [const_x, const_y, const_z]


    def get_magnet_currents(self):
        curr_x = self._magnet_x.get_magnet_current()
        curr_y = self._magnet_y.get_magnet_current()
        curr_z = self._magnet_z.get_magnet_current()
        return [curr_x,curr_y,curr_z]


    def get_supply_currents(self):
        curr_x = self._magnet_x.get_supply_current()
        curr_y = self._magnet_y.get_supply_current()
        curr_z = self._magnet_z.get_supply_current()
        return [curr_x,curr_y,curr_z]


    def get_target_currents(self):
        target_x = self._magnet_x.get_target_current()
        target_y = self._magnet_y.get_target_current()
        target_z = self._magnet_z.get_target_current()
        return [target_x,target_y,target_z]
    

    def set_target_currents(self,target):
        self._magnet_x.set_target_current(target[0])
        self._magnet_y.set_target_current(target[1])
        self._magnet_z.set_target_current(target[2])
        return 0


    def get_target_fields(self):
        target_x = self._magnet_x.get_target_field()
        target_y = self._magnet_y.get_target_field()
        target_z = self._magnet_z.get_target_field()
        return [target_x,target_y,target_z]


    def set_target_fields(self,target):
        self._magnet_x.set_target_field(target[0])
        self._magnet_y.set_target_field(target[1])
        self._magnet_z.set_target_field(target[2])
        return 0


    def get_field(self):
        """Returns field in x,y,z direction."""
        field_x = self._magnet_x.get_field()
        field_y = self._magnet_y.get_field()
        field_z = self._magnet_z.get_field()
        return[field_x,field_y,field_z]

    def get_field_units(self):
        unit_x = self._magnet_x.get_field_units()
        unit_y = self._magnet_y.get_field_units()
        unit_z = self._magnet_z.get_field_units()
        return[unit_x,unit_y,unit_z]


    def get_ramping_state(self):
        """Returns the ramping state of all three 1D magnets.
        
        integers mean the following:
            1:  RAMPING to target field/current
            2:  HOLDING at the target field/current
            3:  PAUSED
            4:  Ramping in MANUAL UP mode
            5:  Ramping in MANUAL DOWN mode
            6:  ZEROING CURRENT (in progress)
            7:  Quench detected
            8:  At ZERO current
            9:  Heating persistent switch
            10: Cooling persistent switch

        @return: list of ints with ramping status [status_x,status_y,status_z].
        """
        status_x = self._magnet_x.get_ramping_state()
        status_y = self._magnet_y.get_ramping_state()
        status_z = self._magnet_z.get_ramping_state()
        status = [status_x,status_y,status_z]
        return status


    def continue_ramp(self):
        """Resumes ramping.
        
        Puts the power supply in automatic ramping mode. Ramping resumes until target field/current is reached.
        """
        self._magnet_x.continue_ramp()
        self._magnet_y.continue_ramp()
        self._magnet_z.continue_ramp()
        return


    def pause_ramp(self):
        """Pauses the ramping process.
        
        The current/field will stay at the level it has now.
        """
        self.abort_ramp_loop()
        self._magnet_x.pause_ramp()
        self._magnet_y.pause_ramp()
        self._magnet_z.pause_ramp()
        return


    def abort_ramp_loop(self):
        self._abortRampLoop = True
        return


    def fire_ramp_timer_once(self, interval=1000):
        """fires the ramp timer once after interval ms."""
        self.rampTimer = QtCore.QTimer()
        self.rampTimer.setSingleShot(True)
        self.rampTimer.timeout.connect(self.send_sig_ramp, QtCore.Qt.QueuedConnection)
        self.rampTimer.start(interval)
        return


    def send_sig_ramp(self):
        self.sigRamp.emit()
        return


    def ramp(self, field_target=[None,None,None], current_target=[None,None,None], enter_persistent=False):
        """Ramps the magnet."""
        self._abortRampLoop = False
        self._abortRampToZeroLoop = True
        self._ramp_loop(field_target=field_target, current_target=current_target,enter_persistent=enter_persistent,first_time=True)
        return


    def _ramp_loop(self, field_target=[None,None,None], current_target=[None,None,None], enter_persistent=False, first_time=False):
        print('_ramp_loop')

        if self._abortRampLoop:
            # puts magnet in pause mode and stops the loop.
            print('Stopping ramp loop.')
            self.pause_ramp()
            return

        # turn into lists because script works with lists
        field_target = list(field_target)
        current_target = list(current_target)
        
        #make sure that only one parameter is specified
        if field_target==[None,None,None] and not current_target==[None,None,None]:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} current given')
            #check if field exceeds specs
            coil_constants = self.get_coil_constants()
            _field_target = np.multiply(coil_constants,current_target)
            self.check_field(_field_target)
            # store args as class objects to reference them later
            self.field_target = field_target
            self.current_target = current_target
            self.enter_persistent = enter_persistent
            # store if field or current was given
            self.given = 'current'
        elif current_target==[None,None,None] and not field_target==[None,None,None]:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} field given')
            _field_target = field_target
            self.check_field(field_target)
            # store args as class objects to reference them later
            self.field_target = field_target
            self.current_target = current_target
            self.enter_persistent = enter_persistent
            # store if field or current was given
            self.given = 'field'
        elif current_target==[None,None,None] and field_target==[None,None,None]:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} No target given, using saved one.')
            # if no targets are given (e.g. because ramp is called in the ramp loop), use the ones stores as class objects.
            try:
                field_target = self.field_target
                current_target = self.current_target
                enter_persistent = self.enter_persistent
            except:
                raise RuntimeError('Targets were not given and also not stored as class objects.')
        else:
            raise RuntimeError('You cannot give field and current target at the same time.')

        #check if persistence is boolean
        if not type(enter_persistent)==bool:
            raise RuntimeError('enter_persistent needs to be boolean.')

        # If the loop is called for the first time, the targets in the magnet controller needs to be set to the current value.
        # If this is not done, we run into a problem when we stop a ramp.
        # e.g. we wanted to ramp to 0.3T but stopped at 0.2T. Stopping means we paused the ramp.
        # If we now decide to ramp to 0.1T and call teh ramp() function, it would unpause the ramp. 
        # Since the old target is still there, the magnet would first ramp to 0.3T and then be in HOLDING mode.
        # From this point on, our script functions normal again.
        # To stop the magnet from ramping too much, we set the targets to the current field/current in the first round.
        # This would then (almost) immediately place the magnet in HOLDING mode and our script can go on as usual.
        if first_time:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} first time')
            if self.given == 'current':
                target = self.get_target_currents()
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} current target was {target}, setting to {self.current_target}')
                self.set_target_currents(self.current_target)
            elif self.given == 'field':
                target = self.get_target_fields()
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} field target was {target}, setting to {self.field_target}')
                self.set_target_fields(self.field_target)
            else:
                raise RuntimeError(f'cannot deal with {self.given} as given.')

        # get magnet mode (persistent od driven)
        # mode = self.get_persistent()
        mode = self.get_pseudo_persistent()
        # get ramping state
        state = self.get_ramping_state()
        # get heater status
        heater = self.get_psw_status()
        # get field inside magnet
        field_mag = self.get_field()
        # get current inside magnet
        curr_mag = self.get_magnet_currents()
        # get current inside power supply
        curr_sup = self.get_supply_currents()
        if self.debug:
            print(f'{datetime.now().strftime("%H:%M:%S")} mode {mode}\nstate {state}\nheater {heater}\nmagnet field {field_mag}\nmagnet current {curr_mag}\nsupply current {curr_sup}')
        
        ## The following block of code prepares the magnet for ramping.
        # is magnet in HOLDING or ZERO state?
        if state == [2,2,2] or state == [8,8,8]:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet in state {state}')
            # is the current/field at target?
            if (self.given == 'field' and np.allclose(field_target, field_mag, atol=0.0001)) or (self.given == 'current' and np.allclose(current_target, curr_mag,atol=0.01)):
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} Current at target')
                # is heater status correct?
                if heater == [int(not enter_persistent),int(not enter_persistent),int(not enter_persistent)]:
                    if self.debug:
                        print(f'{datetime.now().strftime("%H:%M:%S")} Heater status correct')
                    # is magnet mode correct?
                    if mode == [int(enter_persistent),int(enter_persistent),int(enter_persistent)]:
                        # everything is on target, ramp is done
                        print('\nRamp done.\n\n')
                        self._abortRampLoop = True
                        self.sigRampFinished.emit()
                        return
                    # magnet mode not correct
                    else:
                        if self.debug:
                            print(f'{datetime.now().strftime("%H:%M:%S")} Magnet mode wrong {mode}')
                        # since heaters are in desired state, PSW is cooling/heating and mode will soon follow.
                        self.fire_ramp_timer_once(interval = self.rampTimerInterval)
                        return
                # heater status not correct
                else:
                    if self.debug:
                        print(f'{datetime.now().strftime("%H:%M:%S")} Heater status wrong {heater}')
                    # do current in power supply and magnet match?
                    if np.allclose(curr_mag, curr_sup, atol=0.01):
                        if self.debug:
                            print(f'{datetime.now().strftime("%H:%M:%S")} Sup and mag current match')
                        # switch on/off heater and wait
                        self.set_psw_status(int(not enter_persistent))
                        self.fire_ramp_timer_once(interval = self.rampTimerInterval)
                        return
                    # current in suply difers from current in magnet
                    else:
                        if self.debug:
                            print(f'{datetime.now().strftime("%H:%M:%S")} Sup and mag current differ {curr_sup} {curr_mag}')
                        # ramp power supply to current inside magnet
                        self._ramp_supply(current_target=curr_mag)
                        self.fire_ramp_timer_once(interval = self.rampTimerInterval)
                        return
            # current/field not at target
            else:
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} {self.given} not at target, current {curr_mag}, target {current_target}, field {field_mag}, target {field_target}')
                # do current in power supply and magnet match?
                if np.allclose(curr_mag, curr_sup, atol=0.01):
                    if self.debug:
                        print(f'{datetime.now().strftime("%H:%M:%S")} Sup and mag curr match')
                    # is heater on?
                    if heater == [1,1,1]:
                        if self.debug:
                            print(f'{datetime.now().strftime("%H:%M:%S")} Heater is already on')
                        # is magnet in driven mode?
                        if mode == [0,0,0]:
                            if self.debug:
                                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet in driven mode')
                            self._ramp(field_target=field_target, current_target=current_target)
                            return
                        # magnet is (on at least one axis) in persistent mode
                        else:
                            if self.debug:
                                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet (partially) in driven mode')
                            # since heaters are on, PSW is heating and mode will soon follow.
                            self.fire_ramp_timer_once(interval = self.rampTimerInterval)
                            return
                    # (at least one) heater is turned off
                    else:
                        if self.debug:
                            print(f'{datetime.now().strftime("%H:%M:%S")} (At least one) heater is turned off')
                        # turn heaters on
                        self.set_psw_status(1)
                        self.fire_ramp_timer_once(interval = self.rampTimerInterval)
                        return
                # current in suply difers from current in magnet
                else:
                    if self.debug:
                        print(f'{datetime.now().strftime("%H:%M:%S")} Sup and mag curr differ')
                    # ramp power supply to current inside magnet
                    self._ramp_supply(current_target=curr_mag)
                    self.fire_ramp_timer_once(interval = self.rampTimerInterval)
                    return
        # is (at least one) magnet in cooling state
        elif 10 in state:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} cooling')
            # check again in 60s. We wait that long because cooling takes 10 min
            self.fire_ramp_timer_once(interval = 60000)
            return
        # is (at least one) magnet in heating state?
        elif 9 in state:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} heating')
            self.fire_ramp_timer_once(interval = self.rampTimerInterval)
            return
        # is (at least one) magnet paused?
        elif 3 in state:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} upausing ramp')
            #continue ramp
            self.continue_ramp()
            self.fire_ramp_timer_once(interval = self.rampTimerInterval)
            return
        # magnet is neither holding, at zero, heating or cooling
        else:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet is in some other state {state}')
            self.fire_ramp_timer_once(interval = self.rampTimerInterval)
            return
    

    def _ramp_supply(self, current_target):
        """This function is used to ramp the power supply and only the power supply.
        
        That means that the magnet needs to be in persistent mode.
        It is used to adjust the supply current to the magnet current before turning on hte PSW heaters.
        """
        magnet_in_persistent = (self.get_persistent()==[0,0,0])
        psws_off = (self.get_psw_status()==[0,0,0])
        if magnet_in_persistent and psws_off:
            self._ramp(current_target=current_target)
            return
        else:
            print('Magnet is not in persisient mode.')
            return


    def _ramp(self, field_target=[None,None,None], current_target=[None,None,None]):
        """
        """
        # print('_ramp')
        #make sure that only one parameter is specified
        if field_target==[None,None,None] and not current_target==[None,None,None]:
            #check if field exceeds specs
            coil_constants = self.get_coil_constants()
            _field_target = np.multiply(coil_constants,current_target)
            self.check_field(_field_target)
        elif current_target==[None,None,None] and not field_target==[None,None,None]:
            _field_target = field_target
            self.check_field(field_target)
        else:
            raise RuntimeError('You need to give either field or current target.')


        # check for danger of exceeding max vectorial field 
        worst_case_field = [0,0,0]
        current_field = self.get_field()
        for i in range(len(_field_target)):
            t = _field_target[i]
            c = current_field[i]
            w =  max(abs(t),abs(c))
            worst_case_field[i] = w
        worst_case_amplitude = np.linalg.norm(worst_case_field)

        # ramp fast or slow
        if worst_case_amplitude < 1:
            self._fast_ramp(field_target=field_target, current_target=current_target)
        else:
            self._safe_ramp(field_target=field_target, current_target=current_target)
        return 0


    def check_field(self,target_field):
        """Checks if the given field exceeds the constraints.
        
        Returns 0 if everything is okay.
        """

        target_amplitude = np.linalg.norm(target_field)
        if target_amplitude > 1 and target_field[0] !=0 and target_field[1] != 0:
            raise RuntimeError('Max vector field 1T exceeded')
        elif abs(target_field[2]) > 6:
            raise RuntimeError('Max z-field 6T exceeded')
        else:
            return 0


    def _fast_ramp(self, field_target=[None,None,None], current_target=[None,None,None]):
        """Ramps all three axes at once."""
        print('_fast_ramp')
        #ramp
        self._magnet_x.ramp(field_target=field_target[0], current_target=current_target[0])
        self._magnet_y.ramp(field_target=field_target[1], current_target=current_target[1])
        self._magnet_z.ramp(field_target=field_target[2], current_target=current_target[2])

        # Start timer: this function starts a timer that calls the function once
        self._fast_ramp_loop()
        return


    def _fast_ramp_loop(self):

        if self._abortRampLoop:
            # puts magnet in pause mode and stops the loop.
            print('Stopping fast ramp loop.')
            self.pause_ramp()
            return

        state = self.get_ramping_state()
        if state == [2,2,2]:
            self.sigInternalRampFinished.emit()
            return
        else:
            # calls the function again after 1s
            self.fastRampTimer = QtCore.QTimer()
            self.fastRampTimer.setSingleShot(True)
            self.fastRampTimer.timeout.connect(self._fast_ramp_loop, QtCore.Qt.QueuedConnection)
            self.fastRampTimer.start(self.fastRampTimerInterval)
            return
        

    def _safe_ramp(self, field_target=[None,None,None], current_target=[None,None,None]):
        """Ramps to the target field in a safe way.
        
        Calculations are done for field units in Tesla. 
        If you want to use kG, change factor.
        """

        if self._abortRampLoop:
            # puts magnet in pause mode and stops the loop.
            print('Stopping safe ramp loop.')
            self.pause_ramp()
            return

        if field_target:
            target = field_target
            current_target = [None, None, None]
        else:
            target = current_target
            field_target = [None, None, None]

         # define the order of the axes for the magnetic field
        indices = np.argsort(target)
        self.order_axes = []
        self.order_field_targets = []
        self.order_current_targets = []
        for i in indices:
            if i == 0:
                self.order_axes.append('x')
            elif i == 1:
                self.order_axes.append('y')
            elif i == 2:
                self.order_axes.append('z')
            self.order_field_targets.append(field_target[i])
            self.order_current_targets.append(current_target[i])

        
        self.topical_axis = self.order_axes.pop(0)
        self.topical_field_target = self.order_field_targets.pop(0)
        self.topical_current_target = self.order_current_targets.pop(0)
        eval('self._magnet_' + self.topical_axis + '.ramp(field_target=' + self.topical_field_target + ', current_target=' + self.topical_current_target + ')')

        # Start timer: this function starts a timer that calls the function once
        self._safe_ramp_loop()


    def _safe_ramp_loop(self):
        """ Internal function to ramp in a save way
        """
        status = eval('self._magnet_' + self.topical_axis + '.get_ramping_state()')
        if status == 2: #HOLDING at the target field/current
            
            try:
                #go to next axis
                self.topical_axis = self.order_axes.pop(0)
                self.topical_field_target = self.order_field_targets.pop(0)
                self.topical_current_target = self.order_current_targets.pop(0)

            except:
                # no more axes available --> ramp finished
                self.sigInternalRampFinished.emit()
                return
            # start ramp on next axis
            eval('self._magnet_' + self.topical_axis + '.ramp(field_target=' + self.topical_field_target + ', current_target=' + self.topical_current_target + ')')
        # calls the function again after 1000 ms
        self.safeRampTimer = QtCore.QTimer()
        self.safeRampTimer.setSingleShot(True)
        self.safeRampTimer.timeout.connect(self._safe_ramp_loop, QtCore.Qt.QueuedConnection)
        self.safeRampTimer.start(self.safeRampTimerInterval)
        return


    def get_psw_status(self):
        """Returns the status of the psw heaters as array. 

        [status heater x, status heater y, status heater z]
        
        0 means heater is switched off.
        1 means heateris switched on.
        """

        status_x = self._magnet_x.get_psw_status()
        status_y = self._magnet_y.get_psw_status()
        status_z = self._magnet_z.get_psw_status()

        return [status_x, status_y, status_z]


    def set_psw_status(self, status):
        """Turns the PSWs of all 3 magnets on (1) or off(0).

        If you change the current in one coil, all PSWs should be turned on to ensure the other coils are not affected.

        Before PSW is heated and superconducting state is broken, the current inside the magnet and the current that is applied by the powersupply need to match.
        Also, device needs to be in HOLDING mode (ramp has finished).
        Otherwise the magnet might quench.
        """

        # check ramp state
        ramping_state = self.get_ramping_state()
        if not (ramping_state == [2,2,2] or ramping_state == [8,8,8]):
            raise Exception(f'All magnets need to be in HOLDING or ZERO mode.\nRamping state is {ramping_state}')

        # check if currents inside and outside magnet match
        curr_mag = self.get_magnet_currents()
        curr_sup = self.get_supply_currents()
        if not np.allclose(curr_mag, curr_sup, atol=0.01):
            raise Exception(f'Current on power supply does not match current inside magnet.\nSupply: {curr_sup}\nMagnet: {curr_mag}')

        if type(status) == int:
            if status == 0 or status == 1:
                self._magnet_x.set_psw_status(status)
                self._magnet_y.set_psw_status(status)
                self._magnet_z.set_psw_status(status)
            else:
                raise Exception('Status needs to be either 0 or 1.')
        else:
            raise TypeError('Status needs to be integer.')
        return

    
    def get_persistent(self):
        """ Returns mode of the magnets as array.

        [mode x, mode y, mode z]

        0 if in driven mode,
        1 if in persistent mode.

        Note: If current in magnet is less than 100 mA, AMI will not say that the magnet is in persistent mode, eventhough PSWs are cold.
        """

        mode_x = self._magnet_x.get_persistent()
        mode_y = self._magnet_y.get_persistent()
        mode_z = self._magnet_z.get_persistent()

        return [mode_x, mode_y, mode_z]


    def get_pseudo_persistent(self):
        """Returns mode of the magnets as array.

        [mode x, mode y, mode z]

        0 if in driven mode,
        1 if in persistent mode.

        Note: If current in magnet is less than 100 mA, AMI will not say that magnet is in persistent mode, eventhough PSWs are cold.
        This function fixes that issue.
        If the heater is turned off and the magnet is in HOLDING or ZERO mode, the PSW should be cool and the magnet should be in persisent mode.
        If the current inside the magnet is less than 100 mA, the AMI will not return 1, eventhough the magnet loop is superconducting.
        This means that the function should return 1.
        So if the above requirements are met (magnet in HOLDING or ZERO, PSW heater off, current less than 100 mA), this function will return 1.
        """

        mode_x = self._magnet_x.get_pseudo_persistent()
        mode_y = self._magnet_y.get_pseudo_persistent()
        mode_z = self._magnet_z.get_pseudo_persistent()

        return [mode_x, mode_y, mode_z]


    def ramp_to_zero(self):
        """Ramps the magnet to zero field and turns of the PSW heaters."""
        self._abortRampLoop = True
        self._abortRampToZeroLoop = False
        self._ramp_to_zero_loop(first_time=True)
        return


    def _ramp_to_zero_loop(self, first_time=False):
        """Loop body that controls the ramp to zero.
        """
        print('_ramp_to_zero_loop')
        if self._abortRampToZeroLoop:
            # puts magnet in pause mode and stops the loop.
            print('Stopping ramp to zero loop.')
            self.pause_ramp()
            return

        if first_time:
            self.pause_ramp()

        state = self.get_ramping_state()
        heater = self.get_psw_status()
        curr_mag = self.get_magnet_currents()
        curr_sup = self.get_supply_currents()
        if self.debug:
            print(f'{datetime.now().strftime("%H:%M:%S")} state {state}\nheater {heater}\nmagnet current {curr_mag}\nsupply current {curr_sup}')

        if state == [8,8,8]:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet in ZERO state')
            if heater == [0,0,0]:
                print('\nmagnet at zero.\n\n')
                self._abortRampToZeroLoop = True
                return
            else:
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} At least one Heater is on')
                self.set_psw_status(0)
                self.rampToZeroTimer = QtCore.QTimer()
                self.rampToZeroTimer.setSingleShot(True)
                self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
                self.rampToZeroTimer.start(self.rampToZeroTimerInterval)
                return
        
        # The code block above might not catch zero current. This one should do so.
        if (state == [3,3,3]) and np.allclose(curr_mag,[0,0,0],atol=0.02) and heater == [0,0,0]:
            print('\nmagnet at zero.\n\n')
            self._abortRampToZeroLoop = True
            return

        if state == ([2,2,2] or [3,3,3]):
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet at HOLDING or PAUSED')
            if heater == [1,1,1]:
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} All heaters on')
                self._magnet_x.ramp_to_zero()
                self._magnet_y.ramp_to_zero()
                self._magnet_z.ramp_to_zero()
                self.rampToZeroTimer = QtCore.QTimer()
                self.rampToZeroTimer.setSingleShot(True)
                self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
                self.rampToZeroTimer.start(self.rampToZeroTimerInterval)
                return
            if np.allclose(curr_mag,curr_sup,atol=0.01):
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} Currents in supply and magnet match')
                self.set_psw_status(1)
                self.rampToZeroTimer = QtCore.QTimer()
                self.rampToZeroTimer.setSingleShot(True)
                self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
                self.rampToZeroTimer.start(self.rampToZeroTimerInterval)
                return
            else:
                if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} Currents in supply and magnet do not match. Ramping power supply.')
                self._ramp_supply(current_target=curr_mag)
                self.rampToZeroTimer = QtCore.QTimer()
                self.rampToZeroTimer.setSingleShot(True)
                self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
                self.rampToZeroTimer.start(self.rampToZeroTimerInterval)
                return
        elif 3 in state:
            if self.debug:
                    print(f'{datetime.now().strftime("%H:%M:%S")} Magnet paused. Continuing ramp.')
            self.continue_ramp()
            self.rampToZeroTimer = QtCore.QTimer()
            self.rampToZeroTimer.setSingleShot(True)
            self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
            self.rampToZeroTimer.start(self.rampToZeroTimerInterval)
            return
        elif 10 in state:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet cooling.')
                self.rampToZeroTimer = QtCore.QTimer()
                self.rampToZeroTimer.setSingleShot(True)
                self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
                self.rampToZeroTimer.start(60000)
                return
        else:
            if self.debug:
                print(f'{datetime.now().strftime("%H:%M:%S")} Magnet in state {state}, waiting and checking again.')
            self.rampToZeroTimer = QtCore.QTimer()
            self.rampToZeroTimer.setSingleShot(True)
            self.rampToZeroTimer.timeout.connect(self._send_signal_ramp_to_zero_loop, QtCore.Qt.QueuedConnection)
            self.rampToZeroTimer.start(self.rampToZeroTimerInterval)
            return


    def _send_signal_ramp_to_zero_loop(self):
        self.sigRampToZero.emit()
        return


    def abort_ramp_to_zero_loop(self):
            self._abortRampToZeroLoop = True
            return