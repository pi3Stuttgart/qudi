#!/usr/bin/python
# -*- coding: utf-8 -*-
import cPickle, pylab, os, platform
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
from collections import deque
from stat import S_ISREG, ST_CTIME, ST_MODE,ST_MTIME
from matplotlib.backends.backend_pdf import PdfPages
from   traits.api   import Instance, Range, Bool, Array, Str, Enum, Button, on_trait_change, Trait, Float, Dict
from   traitsui.api import View, Item, Group, HGroup, VGroup, VSplit, Tabbed, EnumEditor



def getdata(filename):
    """returns wavelength and intensity, must be in the folder"""
    with open(filename,'rb') as f:
        d=cPickle.load(f)
        return d['angle'], d['intensity']  


startfolder = os.getcwd()

#data_path = 'F:/Messdaten/2016-07-06/CREE/Spec_Polar_P70K_Emission_Quater_Waveplate/'
base= 'D:\\Data\\2016\\'
date= '2016-10-10\\'
meas='HWP_Excitation_NO_PBS_Detection\\V1_Line'
meas2='HWP_Excitation_NO_PBS_Detection\\V1p_Line'
data_path=base+date+meas
data_path_2=base+date+meas2

os.chdir(data_path)



angle, intensity = getdata('2016-10-10_CREE5E17_861nm_0.5mW_875LP_900SP_P5.6K_HWP(rotating)_NO_PBS_IN_Detection.pys')

os.chdir(data_path_2)

angle_2, intensity_2 = getdata('2016-10-10_CREE5E17_858nm_0.5mW_875LP_900SP_P5.6K_HWP(rotating)_NO_PBS_IN_Detection.pys')

ax = plt.subplot(111, projection='polar')
ax.plot(angle*np.pi/90.,intensity/np.max(intensity),'o',markersize=5,mew=0,color='lightsteelblue',)
ax.plot(angle_2*np.pi/90.,intensity_2/np.max(intensity_2),'o',markersize=5,mew=0,color='indianred',)



ax.grid(True,color='black',lw=1.5,dashes=(1,2))
ax.set_axisbelow(True)
ax.tick_params(axis='y')#colors='indianred'

ax.yaxis.tick_left()
ax.xaxis.tick_bottom()

#ax.set_title("V1 and V1-Prime ZPL Polarization", va='bottom')
plt.legend()

plt.show()
os.chdir(startfolder)
#plt.savefig('polarplot.png')
#plt.clf()
#plt.close()