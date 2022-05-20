from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass

class ODMRLogic_interface(metaclass=InterfaceMetaclass):

    @abstract_interface_method
    def on_activate(self):
        pass

    @abstract_interface_method
    def on_deactivate(self):
       pass

    @abstract_interface_method  
    def setup_time_differences_counting(self,bin_width=10,**mw_params):
        pass

    @abstract_interface_method
    def run(self,**params):
        pass

    @abstract_interface_method
    def collect_data(self):
        pass