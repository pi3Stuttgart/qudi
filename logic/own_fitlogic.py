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

from ast import Raise, Sub
from cmath import exp, isnan
import importlib
import inspect
from mimetypes import init
from tkinter import X, Y

from matplotlib.style import use
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

class multifunction():
    import inspect
    def __init__(self,function=None): # the function list will be 2d, firstz index will be the functions that will be added, second argument will be functions that will be multiplied
        self.peak_pos=[]
        self.freq_pos=[]
        #logger.info("hi")
        if function==None:
            self.function_list=[]
            self.arg_length=0
        else:
            self.function_list=[function]
            sig=self.inspect.signature(function).parameters
            #print(sig)
            #logger.info(sig)
            sub=0
            for i,param in enumerate(sig.keys()):
                param=param.lower()
                if param=="self": # take into account that the function may silently pass self to itself
                    sub=1
                #logger.info(f"{param}, {i}")

                if "mean" == param or "mu" == param or "x0" == param:
                    self.peak_pos.append(i-1-sub)
                elif "freq" == param or "omega" == param:
                    self.freq_pos.append(i-1-sub)
            #print("i=",i)
            #logger.info(self.)
            self.arg_length=i # len(args)-1 because x is assumed to part of the arguments
        
        
        
    def __call__(self,*args,**kwargs): # a possible speedup would be to vectorize with np the function evaluation
        if len(kwargs.keys())!=0:
            logger.warning("kwargs are not taken into account in this function")
        self.x=args[0] # will be passed to each function
        self.args=args[1:]
        return self.parse(self.function_list.copy())

    def parse(self,tokens): #calculate with the Polish notation # works because the arguments are passed by reference
        token=tokens.pop(0)
        #print("got token:",token, end="\n")
        #print("tokens",tokens, end="\n")
        if token=='+':
            return self.parse(tokens)+self.parse(tokens)
        elif token=='-':
            return self.parse(tokens)-self.parse(tokens)
        elif token=='*':
            return self.parse(tokens)*self.parse(tokens)
        elif token=='/':
            return self.parse(tokens)/self.parse(tokens)
        else:
                # must be just a function
                #print(self.args)
                #print("token executed:",token, end="\n")
                func=token
                arg_len=len(self.inspect.signature(func).parameters)-1
                arguments=self.args[:arg_len]
                self.args=self.args[arg_len:]
                return func(self.x,*arguments)
        
    def _add(self,other,op): #add to the polish notation
        added=multifunction()
        if str(type(other))=="<class 'function'>" or str(type(other))=="<class 'method'>" :
            other=multifunction(other)
        added.arg_length=self.arg_length+other.arg_length
        added.function_list=[op]+self.function_list+other.function_list
        added.peak_pos=self.peak_pos+list(np.array(other.peak_pos)+self.arg_length)
        added.freq_pos=self.freq_pos+list(np.array(other.freq_pos)+self.arg_length)
        return added

    def __add__(self,other):
        return self._add(other,"+")

    def __radd__(self,other):
        return self._add(other,"+")

    def __sub__(self,other):
        return self._add(other, "-")

    def __rsub__(self,other):
        return self._add(other, "-")

    def __mul__(self,other):
        return self._add(other,"*")

    def __rmul__(self,other):
        return self._add(other,"*")

    def __truediv__(self,other):
        return self._add(other,"/")

    def __rtruediv__(self,other):
        return self._add(other,"/")


class FitLogic(GenericLogic):
    """
    This is the fitting class where fit functions are defined and methods are
    implemented to process the data.
    """
    mf=multifunction
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speedup=True # determine if we have want to get a fit as fast as possible
        self.optimize_time=1 # seconds to get optimization done
        self.use_multifunction_hints=False # multifunction might find some peak or frequencies in its arguments, so this can be used to get better fitting
        self.next_init_guess=np.array([])
        #self.make_example_data()
        #self.fit(soothayer,self.x,self.y)
        self.analyse_kwargs={"height":None, "threshold":None, "distance":None, "prominence":0.4, "width":2, "wlen":None, "rel_height":0.5}

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ """
        pass
    
    def initialize(self):
        self.next_init_guess=np.array([])

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

    def sort_by_prominence(self,find_peaks_result):
        peaks=find_peaks_result
        prom=peaks[1]["prominences"]
        indexes=prom.argsort()[::-1]
        sorted_peaks=peaks[0][indexes]
        return sorted_peaks
        
    def fit(self,function,x_data,y_data,init_guess=None,peak_pos_arguments=[],dip_pos_arguments=[],sine_freq_arguments=[],use_multifunction_hints=False): # the peak_pos_arguments=[],dip_pos_arguments=[],sine_freq_arguments=[] give the position in the function argument array of peaks,dips and the sine frequencies
        # to get faster fitting, one can also order the peak argument position so that the highest peaks correspond to the first peak arguments listed
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

        
        # I expect we will often try to fit the same data with the same function many times. This is why I take the previous result as the initial guess
        if len(x0)==len(self.next_init_guess): 
            x0=self.next_init_guess

        # using the additional information the user may feed into the fit function 
        #!!!! be aware that giving no peak, dip or freq information will lead to the progrm using  the same init guess as the best result from the previous fit: 
        # so omiting peak, dip or freq information can lead to a significant increase in fit speed and success !!!!
        if use_multifunction_hints or len(peak_pos_arguments)>0 or len(dip_pos_arguments)>0 or len(sine_freq_arguments)>0: #analyse data if peak,dip or frequency argument positions are specified
            if use_multifunction_hints and type(function)==type(self.mf()):
                peak_pos_arguments=list(set(function.peak_pos+peak_pos_arguments)) # set removes all duplicates but the list is now also sorted
                sine_freq_arguments=list(set(function.freq_pos+sine_freq_arguments))

            anylysis_time=time.time()
            peaks,dips,freqs=self.analyse_data(y_data,**self.analyse_kwargs)
            logger.info(f"annalysing data took {time.time()-anylysis_time} s")

            Peaks=self.sort_by_prominence(peaks)
            Dips=self.sort_by_prominence(dips)
            Freqs=self.sort_by_prominence(freqs)

            logger.info(f"peaks:{len(Peaks)}, dips:{len(Dips)},freqs:{len(Freqs)}")

            #the frequencies given by fft are symetric around the middle of the freqs list, we remove them
            #Freqs=Freqs[:int(len(Freqs)/2)]


            #logger.info(peak_pos_arguments)
            #logger.info(dip_pos_arguments)
            #logger.info(sine_freq_arguments)
            #logger.info(peaks)
            #logger.info(dips)
            #logger.info(freqs)
            #logger.info(self.x_data)
            #logger.info(x0)

            # set the initial guesses arguments at their calculated position
            filtered=0
            if len(peak_pos_arguments)>0:
                y=signal.savgol_filter(y_data,int(0.1*len(y_data)/2)*2+1,3) # for better peak finding we smooth the data. The window size (2nd argumant) must be odd, the filter window is 10% of the data length
                y_peaks=signal.find_peaks(y,**self.analyse_kwargs)
                Peaks=self.sort_by_prominence(y_peaks)
                filtered=1

                if len(Peaks)>len(peak_pos_arguments):
                    for i,peak_pos in enumerate(peak_pos_arguments):
                        x0[peak_pos]=self.x_data[Peaks[i]]
                else:
                    for i,peak in enumerate(Peaks):
                        x0[peak_pos_arguments[i]]=self.x_data[peak]

            if len(dip_pos_arguments)>0:
                if not filtered:
                    y=signal.savgol_filter(y_data,int(0.1*len(y_data)/2)*2+1,3)
                y_dips=signal.find_peaks(y,**self.analyse_kwargs)
                Dips=self.sort_by_prominence(y_dips)

                if len(Dips)>len(dip_pos_arguments):
                    for i,dip_pos in enumerate(dip_pos_arguments):
                        x0[dip_pos]=self.x_data[Dips[i]]
                else:
                    for i,dip in enumerate(Dips):
                        x0[dip_pos_arguments[i]]=self.x_data[dip]

            if len(sine_freq_arguments)>0:
                FT_x=abs(rfft(y_data)) # we are only interested in the frequencies
                FT_x=signal.savgol_filter(FT_x,int(0.01*len(y_data)/2)*2+1,3) # the window size is 1% as peaks are expected to be sharp
                freqs=signal.find_peaks(FT_x,**self.analyse_kwargs)

                Freqs=self.sort_by_prominence(freqs)

                factor=(self.x_data[10]-self.x_data[0])/10 #get the conversion factor for the reciprocal space
                sr=1/factor
                N = len(self.x_data)
                n = np.arange(N)*np.pi
                T = N/sr
                freq_domain = n/T

                if len(Freqs)>len(sine_freq_arguments):
                    for i,sine_freq in enumerate(sine_freq_arguments):
                        x0[sine_freq]=freq_domain[Freqs[i]]
                else:
                    for i,freq in enumerate(Freqs):
                        x0[sine_freq_arguments[i]]=freq_domain[freq]

            

            
        # use the provided init guess, None means the value in x0 is not changed, else it overwrites the x0 from before
        if init_guess!= None: 
            init_guess=np.asarray(init_guess)
            x0[init_guess!=None]=init_guess[init_guess!=None]

        logger.info(f"x0={x0}")

        logger.info(f"setting x0 took {time.time()-fit_time} s")
        
        opt_time=time.time()
        mini=self.function_to_optimize(tuple(x0)) # as initial minimum value we take the function result for x0
        methods=["Nelder-Mead","Powell","CG","BFGS","L-BFGS-B","TNC","COBYLA","SLSQP"]
        holded_res=optimize.minimize(self.function_to_optimize,x0=x0)
        if holded_res.fun>2*mini: # the fit did destroy something
            holded_res.x=np.array(x0)
            holded_res.fun=mini
        x0=holded_res.x
        if not self.speedup: # use the given time to get the best optimization 
            start_time=time.time()
            res_list=[]
            mini=self.function_to_optimize(tuple(x0)) # as initial minimum value we take the function result for x0
            for method in methods:
                logger.info("trying with "+method+" method.")
                if time.time()-start_time>self.optimize_time: # do not exceed the given time
                    break
                res=optimize.minimize(self.function_to_optimize,x0=x0,method=method)
                res_list.append(res)
                if res.fun!=np.nan:
                    if np.min([mini,res.fun]) < mini:
                        if res.fun/mini>0.9: # take the better result init params
                            x0=res.x
                        mini=res.fun
                        holded_res=res
                        retained_method=method

            logger.info("retained_method: "+retained_method)

        if not holded_res.success:
            logger.warning("Fit was not successful, consider setting speedup to false")
                
        self.next_init_guess=holded_res.x
        self.res=holded_res
        logger.info(f"optimizing took {time.time()-opt_time} s")
        logger.info(f"total fit time was: {time.time()-fit_time}")
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

    ############ basic functions

    def gaussian(self,x, ampl, mu, sig):
        return ampl*np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))

    def lorentzian(self, x, ampl, x0, gam ):
        return ampl * gam**2 / ( gam**2 + ( x - x0 )**2)

    def sine(self,x,ampl,omega,phase):
        return ampl*np.sin(x*omega+phase)

    def constant(self,x,offset):
        return np.ones(len(x))*offset

    def linear(self,x,a,b):
        return a*x+b

    def quadratic(self,x,a=1,b=0,c=0):
        return a*x**2+b*x+c

    def exp_decay(self,x,ampl,x0,decay):
        return ampl*np.exp((x-x0)/decay)

    def stretched_exponential(self,x,ampl, decay, offset, N):
        return ampl*np.exp(-(x/decay)**N)+offset

    ############ Now make composed functions

    def make_n_gauss_function(self,n_gauss):
        ngauss=self.mf(self.gaussian)
        for i in range(n_gauss-1):
            ngauss=ngauss+self.gaussian
        return ngauss

    def make_n_lorentz_function(self,n_lor):
        nlorentz=self.mf(self.lorentzian)
        for i in range(n_lor-1):
            nlorentz=nlorentz+self.lorentzian
        return nlorentz

    def make_n_gauss_function_with_offset(self,n_gauss):
        return self.make_n_gauss_function(n_gauss)+self.constant

    def make_n_lorentz_function_with_offset(self,n_lorentz):
        return self.make_n_lorentz_function(n_lorentz)+self.constant

    def make_n_gauss_function_with_linear_offset(self,n_gauss):
        return self.make_n_gauss_function(n_gauss)+self.linear()

    def make_n_lorentz_function_with_linear_offset(self,n_lorentz):
        return self.make_n_lorentz_function(n_lorentz)+self.linear

    def make_oscilating_exponential_decay_function(self):
        return self.sine*self.mf(self.exp_decay)

    def make_oscilating_exponential_decay_with_offset_function(self):
        return self.sine*self.mf(self.exp_decay)+self.constant

    def make_oscilating_exponential_decay_with_linear_offset_function(self):
        return self.sine*self.mf(self.exp_decay)+self.linear

    ############ and the fitting part

    def make_n_gauss_fit(self,n_gauss,x_data,y_data,init_guess=None):
        func=self.make_n_gauss_function(n_gauss)
        res=self.fit(func,x_data,y_data,use_multifunction_hints=True,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        for i in range(0,3*n_gauss,3):
            ampl,mu,gam=params[i:i+3]
            res_dict["ampl_"+str(i//3)]=ampl
            res_dict["mu_"+str(i//3)]=mu
            res_dict["gam_"+str(i//3)]=gam
        return res_dict

    def make_n_lorentz_fit(self,n_lor,x_data,y_data,init_guess=None):
        func=self.make_n_lorentz_function(n_lor)
        res=self.fit(func,x_data,y_data,use_multifunction_hints=True,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        for i in range(0,3*n_lor,3):
            ampl,mu,gam=params[i:i+3]
            res_dict["ampl_"+str(i//3)]=ampl
            res_dict["mu_"+str(i//3)]=mu
            res_dict["gam_"+str(i//3)]=gam
        return res_dict

    def make_n_gauss_with_offset_fit(self,n_gauss,x_data,y_data,init_guess=None):
        func=self.make_n_gauss_function_with_offset(n_gauss)
        res=self.fit(func,x_data,y_data,use_multifunction_hints=True,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        for i in range(0,3*n_gauss,3):
            ampl,mu,gam=params[i:i+3]
            res_dict["ampl_"+str(i//3)]=ampl
            res_dict["mu_"+str(i//3)]=mu
            res_dict["gam_"+str(i//3)]=gam
        res_dict["offset"]=params[-1]
        return res_dict
    
    def make_n_lorentz_with_offset_fit(self,n_lor,x_data,y_data,init_guess=None):
        func=self.make_n_lorentz_function_with_offset(n_lor)
        res=self.fit(func,x_data,y_data,use_multifunction_hints=True,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        for i in range(0,3*n_lor,3):
            ampl,mu,gam=params[i:i+3]
            res_dict["ampl_"+str(i//3)]=ampl
            res_dict["mu_"+str(i//3)]=mu
            res_dict["gam_"+str(i//3)]=gam
        res_dict["offset"]=params[-1]
        return res_dict

    def make_n_gauss_with_linear_offset_fit(self,n_gauss,x_data,y_data,init_guess=None):
        func=self.make_n_gauss_function_with_linear_offset(n_gauss)
        res=self.fit(func,x_data,y_data,use_multifunction_hints=True,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        for i in range(0,3*n_gauss,3):
            ampl,mu,gam=params[i:i+3]
            res_dict["ampl_"+str(i//3)]=ampl
            res_dict["mu_"+str(i//3)]=mu
            res_dict["gam_"+str(i//3)]=gam
        res_dict["a"]=params[-2]
        res_dict["b"]=params[-1]
        return res_dict

    def make_n_lorentz_with_linear_offset_fit(self,n_lor,x_data,y_data,init_guess=None):
        func=self.make_n_lorentz_function_with_linear_offset(n_lor)
        res=self.fit(func,x_data,y_data,use_multifunction_hints=True,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        for i in range(0,3*n_lor,3):
            ampl,mu,gam=params[i:i+3]
            res_dict["ampl_"+str(i//3)]=ampl
            res_dict["mu_"+str(i//3)]=mu
            res_dict["gam_"+str(i//3)]=gam
        res_dict["a"]=params[-2]
        res_dict["b"]=params[-1]
        return res_dict

    def make_oscilating_exponential_decay_fit(self,x_data,y_data,init_guess=None):
        func=self.make_oscilating_exponential_decay_function()
        res=self.fit(func,x_data,y_data,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        res_dict["amplitude"]=params[0]*params[3]
        res_dict["frequency"]=params[1]
        res_dict["phase"]=params[2]
        res_dict["x0"]=params[4]
        res_dict["decay"]=params[5]
        return res_dict
        
    def make_oscilating_exponential_decay_with_offset_fit(self,x_data,y_data,init_guess=None):
        func=self.make_oscilating_exponential_decay_with_offset_function()
        res=self.fit(func,x_data,y_data,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        res_dict["amplitude"]=params[0]*params[3]
        res_dict["frequency"]=params[1]
        res_dict["phase"]=params[2]
        res_dict["x0"]=params[4]
        res_dict["decay"]=params[5]
        res_dict["offset"]=params[6]
        return res_dict

    def make_oscilating_exponential_decay_with_offset_fit(self,x_data,y_data,init_guess=None):
        func=self.make_oscilating_exponential_decay_with_offset_function()
        res=self.fit(func,x_data,y_data,init_guess=init_guess)
        params=res.x
        res_dict={}
        res_dict["result"]=res
        res_dict["params"]=params
        res_dict["amplitude"]=params[0]*params[3]
        res_dict["frequency"]=params[1]
        res_dict["phase"]=params[2]
        res_dict["x0"]=params[4]
        res_dict["decay"]=params[5]
        res_dict["a"]=params[6]
        res_dict["b"]=params[7]
        return res_dict

    def make_example_data(self):
        self.x=np.linspace(-10,10,1000)
        self.y=self.quadratic(self.x,1,3,5)+np.random.random(len(self.x))*self.x
 