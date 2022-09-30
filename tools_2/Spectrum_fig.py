#!/usr/bin/python
# -*- coding: utf-8 -*-
import cPickle, pylab, os
import matplotlib.pyplot as plt
import numpy as np
import re
import matplotlib, pandas, time
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from matplotlib.pylab import *
import matplotlib.pyplot as plt
from tools import save_toolbox
from stat import S_ISREG, ST_CTIME, ST_MODE,ST_MTIME
from matplotlib.backends.backend_pdf import PdfPages

import threading, time
from tools import save_toolbox
from tools.emod import FreeJob
from traits.api import HasTraits, Trait, Instance, Property, Float,Int, Array,Bool, Array, String, Str, Enum, Button
from datetime import datetime, timedelta
from tools.utility import timestamp
import logging
import cPickle


"""HELPFULL METHODS"""
def get_file_list(some_path):
    orgin_path=os.getcwd()
    os.chdir(some_path)
    path = os.getcwd()
    file_list = [f for f in os.listdir('.') if os.path.isfile(f)]
    os.chdir(orgin_path)
    return file_list

def get_file_list_sorted(some_path):
    """sorts a list as a function of data change"""
    #NOTE: use `ST_MTIME` to sort by a modification date
    #NOTE: use `ST_CTIME` to sort by a creation date
    # path to the directory (relative or absolute)
    dirpath = some_path
    orgin_path=os.getcwd()
    date_list=[]
    new_file_list=[]
    
    # get all entries in the directory w/ stats
    entries = (os.path.join(dirpath, fn) for fn in os.listdir(dirpath))
    entries = ((os.stat(path), path) for path in entries)
    
    # leave only regular files, insert creation date
    entries = ((stat[ST_MTIME], path)
               for stat, path in entries if S_ISREG(stat[ST_MODE]))
    #NOTE: on Windows `ST_CTIME` is a creation date 
    #  but on Unix it could be something else
    #NOTE: use `ST_MTIME` to sort by a modification date
    for mdate, path in sorted(entries):
         if path.endswith('.pys'):
            date_list.append(time.ctime(mdate))
            new_file_list.append(os.path.basename(path))
    os.chdir(orgin_path)
    return new_file_list



def getSpectrumData(filename):
    """returns wavelength and intensity, must be in the folder"""
    with open(filename,'rb') as f:
        d=cPickle.load(f)
        return d['wavelength'], d['intensity']  


#----- Folder Specs ------------------------

startfolder = os.getcwd()


base= 'D:\\data\\2016\\'
date= '2016-06-23\\'
sample='CREE\\'
meas = 'Spectrum_Calibrated_Emission_Polarisation_Platform_70_K\\pys\\paper'
#D:\data\2016\2016-07-13\CREE\Spec_Polar_P5.5K_Emission_HWP_rotating\First_Measurement\pys\paper

data_path=base+date+sample+meas
file_list = get_file_list_sorted(data_path)[::-1]

os.chdir(data_path)
#get some basic measurement parameters, as temperature etc

#get spectrum data
os.chdir(data_path)
#g=file_list[i]
wavelength, intensity = getSpectrumData(file_list[0]) 

#start plot
fig, y1=plt.subplots(figsize=(3.1,1.7),dpi=150)    

y1.plot(wavelength[450:800],intensity[450:800]/np.max(intensity),lw=2,color='lightcoral',label='PL Spectrum at 70K')

#y1.plot(wavelength,intensity,'o',markersize=5,mew=0,color='indianred',label='PL Spectrum at 5.5K')



y1.set_xlabel('Wavelength (nm)',color='indianred')
y1.set_ylabel('Intensity (a.u.)')


plt.legend(loc='upper right', prop={'size':16}, frameon=False)
y1.grid(True,color='sandybrown',lw=0.3,dashes=(1,1.5))
y1.set_axisbelow(True)
y1.tick_params(axis='y', colors='indianred')

y1.yaxis.tick_left()
y1.xaxis.tick_bottom()

pylab.show(block='false')


os.chdir(startfolder)
