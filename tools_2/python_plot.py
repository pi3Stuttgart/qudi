from lmfit import  Model
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


startfolder = os.getcwd()

def sinCosine(x, amp, T, f, shift, offset):
    """Defines a sinusoidal"""
    return amp*np.exp(-(x/T)**2)*np.sin(x * 2*np.pi*f + shift)+offset#amp*np.exp(-x/T)*

def get_file_list(some_path):
    orgin_path=os.getcwd()
    os.chdir(some_path)
    path = os.getcwd()
    file_list = [f for f in os.listdir('.') if os.path.isfile(f)]
    os.chdir(orgin_path)
    return file_list

def get_spin_state(filename):
    """returns spin state and tau, must be in the folder"""
    with open(filename,'rb') as f:
        d=cPickle.load(f)
        #return d['measurement']['spin_state'], d['measurement']['tau']
        return d['spin_state'], d['tau']
  

base= 'D:\\data\\2016\\'
date= '2016-10-19'
#sample='CREE5E17\\'
measurement = 'Rabi'
data_path=base+date+'\\'+measurement+'\\'+'165MHz_-19dBm'+'\\'+'pys'+'\\'
#data_path_off=base+date+'\\'+measurement+'\\'+'pys_off'+'\\'

#file_list = get_file_list(data_path)
#os.chdir(data_path)
#y, x = get_spin_state(file_list[0])

T=200e-9
amp=35000
f=6e6
shift=np.pi/3
offset=0
x=np.arange(0,1200e-9,12e-9)      

y=amp*np.exp(-(x/T)**2)*np.sin(x * 2*np.pi*f + shift)+offset




#file_list_off = get_file_list(data_path_off)
#os.chdir(data_path_off)
#y_off, x_off = get_spin_state(file_list_off[0])
#y=y[0:100]-y[100:200]
#y_onn=y_on/y_on[0]
#y_offn=y_off/y_off[0]

#y=y_offn-y_onn


#pylab.plot(x,fit)
#pylab.show(block=False)

fig, y1=plt.subplots(figsize=(3.1,1.7),dpi=150)    
#y1.plot(afit,lw(afit),lw=2,color='lightcoral')
#y1.plot(x,fit,lw=2,color='lightcoral')
#y1.plot(afit,lws(s),lw=1,color='lightsteelblue')
y1.plot(x,y,'o',markersize=5,mew=0,color='indianred',label='measured')
#y1.plot(x,y,lw=0.5,color='black')

#y1.set_ylim(26,40)
#y1.set_xticklabels([])
y1.set_xlabel('Tau (us)',color='indianred')
y1.set_ylabel('Intensity (a.u.)')
#pl.title('Dependence of linewidth on amplitude')
# pl.legend(loc='upper left', prop={'size':16}, frameon=False)
y1.grid(True,color='sandybrown',lw=0.3,dashes=(1,1.5))
y1.set_axisbelow(True)
y1.tick_params(axis='y', colors='indianred')

y1.yaxis.tick_left()
y1.xaxis.tick_bottom()
#y1.axhline(2*(gamma+gst)*np.sqrt(2.),color='grey',lw=1,ls='dashed')
#y1.axvline(45,color='grey',lw=1,ls='dashed')
pylab.show(block='false')


os.chdir(startfolder)