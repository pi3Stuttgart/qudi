from traits.api         import HasTraits, Instance, SingletonHasTraits, Range, on_trait_change
from traitsui.api       import View, Item, Group, HGroup, VGroup
from traits.api         import Button



import hardware.pulse_generator
import hardware.TimeTagger as time_tagger
import hardware.microwave_sources
import hardware.nidaq
import hardware.laser
import hardware.hameg
import hardware.flip_mirror
import hardware.spectrometer_trigger
import hardware.apt_stage
import hardware.power_meter
import hardware.laser


import measurements.odmr
import measurements.autocorrelation
import measurements.laser_power
import measurements.saturation
import measurements.rabi
import measurements.zeeman
import analysis.pulsed
import measurements.polarization
#from measurements.pulsed_with_aom_delay import T1pi



class MeasurementPanel( HasTraits ):
    
    
    autocorrelation_button = Button(label='start autocorrelation', desc='Opens autocorrelation measurement')
    odmr_button = Button(label='start ODMR', desc='Opens ODMR measurement')
    laser_power_button = Button(label='start laserpower', desc='Opens laser power measurement')
    saturation_button = Button(label='start saturation', desc='Opens saturation measurement')
    rabi_button = Button(label='start rabi', desc='Opens rabi measurement')
    zeeman_button = Button(label='start zeeman', desc='Opens zeeman measurement')
    pulsed_button = Button(label='start pulsed', desc='Opens pulsed measurement')
    polarization_button =  Button(label='start polarization', desc='Opens pulsed measurement')
   # t1pi_button =  Button(label='start T1pi with AOM delay', desc='Opens pulsed T1pi measurement')
    


    
    #odmr = measurements.odmr.ODMR(microwave, odmr_counter, pulse_generator)

#polarization = measurements.polarization.Polarization(time_tagger, rotation_stage)
#rabi_measurement = measurements.rabi.Rabi(pulse_generator,time_tagger,microwave) 
#pulsed_tool_tau = analysis.pulsed.PulsedToolTau(measurement=rabi_measurement) 
    
    @on_trait_change('autocorrelation_button')
    def autocorrelation_button_fired(self):    
        autocorrelation = measurements.autocorrelation.Autocorrelation(time_tagger)
        autocorrelation.edit_traits()
        
    @on_trait_change('odmr_button')
    def odmr_button_fired(self):    
        odmr = measurements.odmr.ODMR(microwave, counter)
        odmr.edit_traits() 
    
    @on_trait_change('laser_power_button')
    def laser_power_button_fired(self):    
        laserpower = measurements.laser_power.LaserPower(time_tagger, laser, power_meter)
        laserpower.edit_traits() 
    
    @on_trait_change('saturation_button')
    def saturation_button_fired(self):    
        saturation = measurements.saturation.Saturation(time_tagger, laser, power_meter)
        saturation.edit_traits()
    
    @on_trait_change('rabi_button')
    def rabi_button_fired(self):    
        rabi_measurement = measurements.rabi.Rabi(pulse_generator,time_tagger,microwave)
        rabi_measurement.edit_traits()
    
    @on_trait_change('pulsed_button')
    def pulsed_button_fired(self):    
        pulsed_tool_tau = analysis.pulsed.PulsedToolTau(measurement=rabi_measurement)
        pulsed_tool_tau.edit_traits()
    
    @on_trait_change('pulsed_button')
    def zeeman_button_fired(self):    
        zeeman = measurements.zeeman.Zeeman()
        zeeman.edit_traits()
        
    @on_trait_change('polarization_button')
    def polarization_button_fired(self):       
        polarization = measurements.polarization.Polarization(time_tagger, rotation_stage)
        polarization.edit_traits()
    
   # @on_trait_change('polarization_button')
    #def t1pi_button_fired(self):
    #    t1pi.measurements=T1pi()
    #    t1pi.edit_traits()




    traits_view = View(HGroup(VGroup(Item('autocorrelation_button', style='custom', show_label=False),
                                     Item('odmr_button', style='custom', show_label=False),
                                     Item('laser_power_button', style='custom', show_label=False),
                                     Item('saturation_button', style='custom', show_label=False),
                                     ),
                              VGroup(Item('rabi_button', style='custom', show_label=False),
                                     Item('pulsed_button', style='custom', show_label=False),
                                     Item('zeeman_button', style='custom', show_label=False),
                                     Item('polarization_button', style='custom', show_label=False),
                                     )
                             
                             ),
                       title='Measurements Panel', resizable=True, x=650, y= -50
                       )



        
    

