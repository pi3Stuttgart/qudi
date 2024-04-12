import numpy as np
from datetime import datetime
import time

from core.configoption import ConfigOption
from core.module import Base

#import toptica.lasersdk as lasersdk
import toptica.lasersdk.dlcpro.v2_4_0 as dlcsdk
#from toptica.lasersdk import decop, client

from typing import Union, Tuple, List, Any
from PyQt5 import QtTest

from interface.CTL_interface import CTLInterface

class OutOfRangeError(ValueError):
    """Custom out of range errors for when a parameter is outside the permitted
    range"""

    def __init__(self, value: Any, parameter_name: str, permitted_range: List[Any]):
        self.value = value
        self.parameter_name = parameter_name
        self.range = permitted_range
        self.message = (
            f"{value} is not within the permitted "
            f"{parameter_name} range {permitted_range}"
        )
        super().__init__(self.message)


def _check_value(val: float, parameter_name: str, permitted_range: List[float]):
    """Check that a value is within a given range, raise error if not

    Raises
    ------
    OutOfRangeError
        If ``val`` is not within the two values of the ``permitted_range``
        list
    """
    if not permitted_range[0] <= val <= permitted_range[1]:
        raise OutOfRangeError(val, parameter_name, permitted_range)


def _print_dict(the_dict: dict, indent: int = 0, header: str = ""):
    """Recursive dictionary printing"""
    longest_key_len = len(max(the_dict.keys(), key=len))
    line = "-" * max(len(header), longest_key_len, 50)
    indent_spaces = " | " * indent
    if not indent:
        print("")
        if header:
            print(header)
        print(line)
    for key, val in the_dict.items():
        if isinstance(val, dict):
            print(f"{indent_spaces}{key}:")
            _print_dict(val, indent=(indent + 1))
        else:
            print(indent_spaces, end="")
            print(f"{key:<{longest_key_len}}: {val}")
    if not indent:
        print(line)

class TopticaCTL(Base,CTLInterface):#, Interface): #?
   
    ''' Config Example
    TopticaCTL:
            module.Class: 'laser.Toptica.TopticaCTL'
            IP: '129.69.46.175'
    '''
    IP = ConfigOption('IP', "129.69.46.175", missing='warn') 

    def on_activate(self):
        self.connection = dlcsdk.NetworkConnection(self.IP)
        self.dlc = dlcsdk.DLCpro(self.connection)
        self.dlc.open()
        self.wl_control_available = True
        self.temp_control_available = False
        self._lims = None
        self.get_limits_from_dlc()

    def on_deactivate(self):
        self.dlc.close()


    # Wavelength properties ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

    @property
    def wavelength_act(self):
        """The actual wavelength of the laser (read only)"""
        if not self.wl_control_available:
            return None
        return self.dlc.laser1.ctl.wavelength_act.get()

    @property
    def wavelength_setpoint(self) -> float:
        """The setpont of the laser wavelength"""
        if not self.wl_control_available:
            return None
        return self.dlc.laser1.ctl.wavelength_set.get()

    @wavelength_setpoint.setter
    def wavelength_setpoint(self, val: float):
        if not self.wl_control_available:
            raise RuntimeError(
                "Cannot set wavelength when `wl_control_available` is False"
            )
        if val is None:
            return
        val = float(val)
        if self._wlrange[0] is None:
            self.get_limits_from_dlc()
        _check_value(val, "wavelength setpoint", self._wlrange)
        self.dlc.laser1.ctl.wavelength_set.set(val)


    # Current properties ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

    @property
    def current_act(self):
        """The actual current of the laser diode (read only)"""
        return self.dlc.laser1.dl.cc.current_act.get()

    @property
    def current_setpoint(self) -> float:
        """The setpont of the laser current"""
        return self.dlc.laser1.dl.cc.current_set.get()

    @current_setpoint.setter
    def current_setpoint(self, val: float):
        if val is None:
            return
        val = float(val)
        if self._crange[0] is None:
            self.get_limits_from_dlc()
        _check_value(val, "current setpoint", self._crange)
        self.dlc.laser1.dl.cc.current_set.set(val)


    # Emission properties ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ##

    @property
    def emission(self) -> bool:
        """Emission status of the DLC (read only)"""
        return self.dlc.emission.get()

    @property
    def emission_button(self) -> bool:
        """Status of the emission button of the DLC (read only)"""
        return self.dlc.emission_button_enabled.get()

    @property
    def current_enabled(self) -> bool:
        """Status of the current to the laser"""
        return self.dlc.laser1.dl.cc.enabled.get()

    @current_enabled.setter
    def current_enabled(self, val: bool):
        """Sneaky way to control emission on/off provided the button on the
        DLC is enabled"""
        if val and not self.emission_button:
            print("(!) Emission button on DLC not enabled, so cannot enable emission")
        self.dlc.laser1.dl.cc.enabled.set(val)



    def get_limits_from_dlc(self, verbose: bool = False) -> dict:
        """Query the laser for the wavelength, piezo voltage, current and
        scan frequency limits, and populate the ``_lims`` dict attribute

        Returns
        -------
        self._lims : dict
            The limits
        """
        self._lims = {
            "vmin": self.dlc.laser1.dl.pc.voltage_min.get(),
            "vmax": self.dlc.laser1.dl.pc.voltage_max.get(),
            "cmin": 0.0,
            "cmax": self.dlc.laser1.dl.cc.current_clip.get(),
            "fmin": 0.02,
            "fmax": 400,  # cannot find max in manual
            "tmin": None,
            "tmax": None,
            "wlmin": None,
            "wlmax": None,
        }
        if self.wl_control_available:
            self._lims.update(
                {
                    "wlmin": self.dlc.laser1.ctl.wavelength_min.get(),
                    "wlmax": self.dlc.laser1.ctl.wavelength_max.get(),
                }
            )
        if self.temp_control_available:
            self._lims.update(
                {
                    "tmin": self.dlc.laser1.dl.tc.temp_set_min.get(),
                    "tmax": self.dlc.laser1.dl.tc.temp_set_max.get(),
                }
            )
        if verbose:
            _print_dict(self._lims)
        return self._lims
    
    @property
    def _vrange(self):
        return self._lims["vmin"], self._lims["vmax"]

    @property
    def _crange(self):
        return self._lims["cmin"], self._lims["cmax"]

    @property
    def _trange(self):
        return self._lims["tmin"], self._lims["tmax"]

    @property
    def _wlrange(self):
        return self._lims["wlmin"], self._lims["wlmax"]

    def _check_value(val: float, parameter_name: str, permitted_range: List[float]):
        """Check that a value is within a given range, raise error if not

        Raises
        ------
        OutOfRangeError
            If ``val`` is not within the two values of the ``permitted_range``
            list
        """
        if not permitted_range[0] <= val <= permitted_range[1]:
            raise OutOfRangeError(val, parameter_name, permitted_range)

    
