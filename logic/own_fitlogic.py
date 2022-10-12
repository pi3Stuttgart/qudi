"""
This file contains the Qudi FitLogic class, which provides all
fitting methods imported from the files in logic/fitmethods.

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

from ast import Raise
from cmath import isnan
import importlib
import inspect
from tkinter import X
import lmfit
from qtpy import QtCore
import numpy as np
import os
import sys
from collections import OrderedDict
from distutils.version import LooseVersion

from logic.generic_logic import GenericLogic
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from core.config import load, save
from core.configoption import ConfigOption
from scipy import optimize
from scipy import signal
from scipy.fftpack import fft, ifft, rfft
import time

import logging
logger = logging.getLogger(__name__)

import inspect

class FitLogic(GenericLogic):
    """
    This is the fitting class where fit functions are defined and methods are
    implemented to process the data.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speedup=True # determine if we have want to get a fit as fast as possible
        self.optimize_time=1 # seconds to get optimization done
        self.init_guess=np.array([])
        #self.make_example_data()
        #self.fit(soothayer,self.x,self.y)
        self.analyse_kwargs={"height":None, "threshold":None, "distance":None, "prominence":0.2, "width":2, "wlen":None, "rel_height":0.5}

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ """
        pass
    
    def initialize(self):
        self.init_guess=np.array([])

    def least_square(self,y_data,y_fit):
        y_data=np.asarray(y_data)
        y_fit=np.asarray(y_fit)
        if len(y_fit)!=len(y_data):
            logger.error("The two lists given to least square do not have the same length")
            return -1
        else:
            return np.sum((y_data-y_fit)**2)

    def function_to_optimize(self,args):
        self.y_test=self.estimation_function(self.x_data,*args)
        least_square=self.least_square(self.y_data,self.y_test)
        if least_square==-1:
            return 1e40
        return least_square

        
    def fit(self,function,x_data,y_data,init_guess=None,peak_pos_arguments=[],dip_pos_arguments=[],sine_freq_arguments=[]): # the peak_pos_arguments=[],dip_pos_arguments=[],sine_freq_arguments=[] give the position in the function argument array of peaks,dips and the sine frequencies
        fit_time=time.time()
        self.estimation_function=function
        self.x_data=x_data
        self.y_data=y_data

        sig=inspect.signature(function)
        params=list(sig.parameters.keys())

        #until the definition of the mehtods, this code is just there to get better initial guesses

        # using the signature of the function
        if not ("args" in sig.parameters.keys() or "kwargs" in sig.parameters.keys()): # get a x0 guiess from the function default values
            args=[]
            kwargs={}
            x0=np.array([1.3]*(len(params)-1)) # the initial guess for the optimizer function, I expect 1.3 not to land on any singularity of the fit function
            for j,i in enumerate(sig.parameters):
                #print(sig.parameters[i])
                if "=" in str(sig.parameters[i]):
                    equal_pos=str(sig.parameters[i]).find("=")
                    kwargs[i]=str(sig.parameters[i])[equal_pos+1:]
                    if j>0: #do not take the first parameter into account
                        x0[j-1]=kwargs[i]

        elif type(function) == type(multifunction()):
            x0=np.array([1.3]*(function.arg_length))
        else:
            logger.error("Fit function contains *args or **kwargs in its signature, the fit cannot be done!")
            return x_data*0

        # using the additional information the user may feed into the fit function 
        #!!!! be aware that giving no peak, dip or freq information will lead to the progrm using  the same init guess as the best result from the previous fit: so omiting eak, dip or freq information can lead to a significant increase in fit speed
        if len(peak_pos_arguments)>0 or len(dip_pos_arguments)>0 or len(sine_freq_arguments)>0: #analyse data if peak,dip or frequency argument positions are specified
            anylysis_time=time.time()
            peaks,dips,freqs=self.analyse_data(y_data,**self.analyse_kwargs)
            logger.info(f"annalysing data took {time.time()-anylysis_time} s")
            #the frequencies given by fft are symetric around the middle of the freqs list, we remove them
            freqs=freqs[0][:int(len(freqs[0])/2)]



            #logger.info(peak_pos_arguments)
            #logger.info(dip_pos_arguments)
            #logger.info(sine_freq_arguments)
            #logger.info(peaks)
            #logger.info(dips)
            #logger.info(freqs)

            # set the initial guesses arguments at their calculated position
            if len(peaks[0])>len(peak_pos_arguments):
                for i,peak_pos in enumerate(peak_pos_arguments):
                    x0[peak_pos]=self.x_data[peaks[0][i]]
            else:
                for i,peak in enumerate(peaks[0]):
                    x0[peak_pos_arguments[i]]=self.x_data[peak]

            if len(dips[0])>len(dip_pos_arguments):
                for i,dip_pos in enumerate(dip_pos_arguments):
                    x0[dip_pos]=self.x_data[dips[0][i]]
            else:
                for i,dip in enumerate(dips[0]):
                    x0[dip_pos_arguments[i]]=self.x_data[dip]

            factor=(self.x_data[10]-self.x_data[0])/10 #get the conversion factor for the reciprocal space
            sr=1/factor
            N = len(self.x_data)
            n = np.arange(N)*np.pi
            T = N/sr
            freq_domain = n/T

            if len(freqs)>len(sine_freq_arguments):
                for i,sine_freq in enumerate(sine_freq_arguments):
                    x0[sine_freq]=freq_domain[freqs[i]]
            else:
                for i,freq in enumerate(freqs):
                    x0[sine_freq_arguments[i]]=freq_domain[freq]

        # I expect we will often try to fit the same data with the same function many times. This is why I take the previous result as the initial guess
        elif len(x0)==len(self.init_guess): 
            x0=self.init_guess

        # use the provided init guess, None means the value in x0 is not changed, else it overwrites the x0 from before
        if init_guess!= None: 
            init_guess=np.asarray(init_guess)
            x0[init_guess!=None]=init_guess[init_guess!=None]

        logger.info(f"x0={x0}")

        logger.info(f"setting x0 took {time.time()-fit_time} s")
        opt_time=time.time()
        methods=["Nelder-Mead","Powell","CG","BFGS","L-BFGS-B","TNC","COBYLA","SLSQP"]
        holded_res=optimize.minimize(self.function_to_optimize,x0=x0)
        if not self.speedup: # use the given time to get the best optimization 
            start_time=time.time()
            res_list=[]
            mini=np.inf
            for method in methods:
                logger.info("trying with "+method+" method.")
                if not np.isnan(holded_res.fun):
                    x0=holded_res.x
                if time.time()-start_time>self.optimize_time: # do not exceed the given time
                    break
                res=optimize.minimize(self.function_to_optimize,x0=x0,method=method)
                res_list.append(res)
                if res.fun!=np.nan:
                    if np.min([mini,res.fun]) < mini:
                        mini=res.fun
                        holded_res=res
                        retained_method=method

            logger.info("retained_method: "+retained_method)

        if not holded_res.success:
            logger.warning("Fit was not successful, consider setting speedup to false")
                
        self.init_guess=holded_res.x
        self.res=holded_res
        logger.info(f"optimizing took {time.time()-opt_time} s")
        return self.res

    def use_curve_fit(self):
        logger.warning(("curve fit not implemented"))
    
    def analyse_data(self,x,**kwargs): #kwars: height=None, threshold=None, distance=None, prominence=None, width=None, wlen=None, rel_height=0.5, plateau_size=None
        x=signal.savgol_filter(x,int(0.1*len(x)/2)*2+1,3) # for better peak finding we smooth the data. The window size (2nd argumant) must be odd, the filter window is 10% of the data length
        x_peaks=signal.find_peaks(x,**kwargs)
        x_dips=signal.find_peaks(-x,**kwargs)
        FT_x=abs(rfft(x)) # we are only interested in the frequencies
        FT_x=signal.savgol_filter(FT_x,int(0.01*len(x)/2)*2+1,3) # the window size is 1% as peaks are expected to be sharp
        FT_peaks=signal.find_peaks(FT_x,**kwargs)
        return x_peaks,x_dips,FT_peaks

    def gaussian(self,x, mu, sig):
        return np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))

    def lorentzian(self, x, x0, a, gam ):
        return a * gam**2 / ( gam**2 + ( x - x0 )**2)

    def make_example_data(self):
        self.x=np.linspace(-10,10,1000)
        self.y=self.quadratic(self.x,1,3,5)+np.random.random(len(self.x))*self.x

    
    def quadratic(self,x,a=1,b=0,c=0):
        #print(x)
        return a*x**2+b*x+c


class multifunction():
    import inspect
    def __init__(self,function=None): # the function list will be 2d, firstz index will be the functions that will be added, second argument will be functions that will be multiplied
        self.function=function
        if function==None:
            self.function_list=[]
            self.arg_length=0
        else:
            self.function_list=[function]
            self.arg_lenth=len(self.inspect.signature(function).parameters)-1 #-1 because x is assumed to part of the arguments
        
        
        
    def __call__(self,*args,**kwargs):
        if len(kwargs.keys())!=0:
            logger.warning("kwargs are not taken into account in this function")
        x=args[0]
            
        used=1 # the used params in args
        y=0
        for function in self.function_list:
            sig=self.inspect.signature(function)
            params_number=len(sig.parameters)-1 #we assume x is always part of the arguments
            func_args=args[used:used+params_number]
            print(func_args)
            used+=params_number
            y=y+function(x,*func_args)
        return y
        
    
    def __add__(self,other):
        added=multifunction()
        if str(type(other))=="<class 'function'>":
            other=multifunction(other)
        added.arg_lenth=self.arg_length+other.arg_length
        added.function_list=self.function_list+other.function_list
        return added

    def __radd__(self,other):
        added=multifunction()
        if str(type(other))=="<class 'function'>":
            other=multifunction(other)
        added.arg_lenth=self.arg_length+other.arg_length
        added.function_list=self.function_list+other.function_list
        return added

    





# def multi_lorentz(self, x, params ):
#     off = params[0]
#     paramsRest = params[1:]
#     assert not ( len( paramsRest ) % 3 )
#     return off + sum( [ self.lorentzian( x, *paramsRest[ i : i+3 ] ) for i in range( 0, len( paramsRest ), 3 ) ] )

# def res_multi_lorentz(self, params, xData, yData ):
#     diff = [ self.multi_lorentz( x, params ) - y for x, y in zip( xData, yData ) ]
#     return diff

# xData, yData = np.loadtxt('HEMAT_1.dat', unpack=True )
# yData = yData / max(yData)
# generalWidth = 1
# yDataLoc = yData
# startValues = [ max( yData ) ]
# counter = 0

# while max( yDataLoc ) - min( yDataLoc ) > .1:
#     counter += 1
#     if counter > 20: ### max 20 peak...emergency break to avoid infinite loop
#         break
#     minP = np.argmin( yDataLoc )
#     minY = yData[ minP ]
#     x0 = xData[ minP ]
#     startValues += [ x0, minY - max( yDataLoc ), generalWidth ]
#     popt, ier = leastsq( res_multi_lorentz, startValues, args=( xData, yData ) )
#     yDataLoc = [ y - multi_lorentz( x, popt ) for x,y in zip( xData, yData ) ]

# print(popt)
# testData = [ multi_lorentz(x, popt ) for x in xData ]   