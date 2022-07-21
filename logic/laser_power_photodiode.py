import numpy as np

from traits.api import Float, Bool, Button, Int
#from pyface.image_resource import ImageResource
from core.module import Base
from logic.generic_logic import GenericLogic
#from tools.emod import ManagedJob
#from tools.utility import GetSetItemsMixin
from core.connector import Connector


class LaserPowerHolder(GenericLogic): #Base

    ao_module = Connector(interface='LaserPowerInterface')

    def on_activate(self):
        self._ao_module = self.ao_module()
        self._laser_power = LaserPower(self._ao_module.aom_driver, self._ao_module.photodiode)
        return

    def on_deactivate(self):
        del self._ao_module
        return

class LaserPower:
#class LaserPower(ManagedJob, GetSetItemsMixin):

    # overwrite default priority from ManagedJob (default 0)4
    priority = 0

    Voltage_min = -10

    Voltage_max = -5
    power_target = 5
    # power_target = Float(
    #     default_value=1,
    #     low=0,
    #     high=1e5,
    #     desc='Power targeted [nW]',
    #     label="Power targeted [nW]"
    # )

    tolerances = 0.05

    # tolerances = Float(
    #     default_value=10.,
    #     low=0.,
    #     hight=100.,
    #     desc='Tolerance of precision [%]',
    #     label='Tolerance of precision [%]'
    # )

    points_to_average = Int(
        default_value=100,
        low=1,
        hight=1e5,
        desc='nb of meas to average',
        label='nb of meas to average'
    )
    #print("points to average: ", points_to_average.__dir__(), points_to_average.__dict__)
    power = Float(
        default_value=0.,
        low=0.,
        high=1e5,
        desc='Power  [nW]',
        label="Power  [nW]"
    )
    success = Bool(
        False, label='Success', desc='whether we could go to the power'
    )
    Read_Power_button = Button(label='Read Power', desc='Readout the power')

    def __init__(self, aom_driver, photodiode, **kwargs):
    #def __init__(self, aom_driver, photodiode, pulse_generator, **kwargs):
        super(LaserPower, self).__init__(**kwargs)
        self.aom_driver = aom_driver
        self.photodiode = photodiode
        #self.pulse_generator = pulse_generator
        self.dark_theme = True
        self.Voltage_min = aom_driver.Voltagerange[0]
        self.Voltage_max = aom_driver.Voltagerange[-1]

        # self.aom_driver.goToVoltage(self.Voltage_min)

    def getPower(self):
        return self.photodiode.getMeanPower(int(self.points_to_average.default_value))

    def find_new_interval(
        self, volt_min, volt_max, power_target_min, power_target_max, step
    ):
        self.aom_driver.goToVoltage(volt_min)

        current_power = self.getPower()
        current_voltage = volt_min

        while current_power < power_target_min and current_voltage <= volt_max:
            current_voltage += step
            self.aom_driver.goToVoltage(current_voltage)
            current_power = self.getPower()

        if current_voltage > volt_max:
            self.aom_driver.goToVoltage(volt_min)
            current_power = np.round(self.getPower(), 5)
            print('Power target too high')
            return False, np.round(current_power, 5)

        elif current_power <= power_target_max:
            return True, np.round(current_power, 5)

        else:
            return self.find_new_interval(
                current_voltage - step,
                current_voltage,
                power_target_min,
                power_target_max,
                step / 10.
            )

    def _run(self):
        try:
            self.state = 'run'

            #self.pulse_generator.setContinuous(["aom"])

            volt_min = self.Voltage_min
            volt_max = self.Voltage_max
            self.success = False
            current_voltage = volt_min
            self.aom_driver.goToVoltage(current_voltage)
            current_power = self.getPower()
            power_target_min = self.power_target * (
                1 - self.tolerances / 100. * np.sign(self.power_target)
            )
            power_target_max = self.power_target * (
                1 + self.tolerances / 100. * np.sign(self.power_target)
            )
            if power_target_max < current_power:
                print("power target too small")
                self.power = np.round(current_power, 5)
            else:
                self.success, self.power = self.find_new_interval(
                    volt_min, volt_max, power_target_min, power_target_max, 1
                )

        finally:
            self.state = 'idle'

    def _Read_Power_button_fired(self):
        self.power = np.round(self.getPower(), 5)
        return self.power

