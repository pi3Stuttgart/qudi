from core.meta import InterfaceMetaclass

class LaserPowerInterface(metaclass=InterfaceMetaclass):

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass