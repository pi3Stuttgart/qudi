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

"""HELPFULL METHODS"""
def get_file_list(some_path):
    orgin_path=os.getcwd()
    os.chdir(some_path)
    path = os.getcwd()
    file_list = [f for f in os.listdir('.') if os.path.isfile(f)]
    os.chdir(orgin_path)
    return file_list

def find_string_in_array(f,seq):
  """Return items containing f in sequence """
  regex=re.compile(".*"+f+".*")#using regulary expressions for finding part of string in a list
  item=[m.group(0) for l in seq for m in [regex.search(l)] if m]
  return item[0] #item itself is a 1d-array so [0] has to be added

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

def return_value(k, string):
    """Returns a wanted number in front of a string as an integer found in a given string k, output limited to 10 digits"""
    v_idx = k.find(string)
    #print 'string ',string,' found at position: ',v_idx
    returnvalue = 0
    for i in range(1,10):        
        try:
            returnvalue = float(k[v_idx-i:v_idx])
        except:
            pass
    return returnvalue

def dictToCsv(dictionary, filename):
    df=pandas.DataFrame(dict([ (k,pandas.Series(v)) for k,v in dictionary.iteritems() ]))        
    df.to_excel(filename,sheet_name='book1')

def getSpectrum(filename):
    """returns wavelength and intensity, must be in the folder"""
    with open(filename,'rb') as f:
        d=cPickle.load(f)
        return d['wavelength'], d['intensity']  

def getCalibration(folder):
    laserlist=get_file_list_sorted(folder)[::-1]
    i=len(laserlist)-1
    laser_array=[]
    angle_array=[]

    while i >= 0:
        filename=laserlist[i]
        os.chdir(folder)    
        wavelength, intensity = getSpectrum(filename)
        #wavelength = wavelength-np.mean(wavelength[500:])#substract BG
        intensity = intensity - np.mean(intensity[500:])#substract BG
        mymax = np.max(intensity[0:200])
        angle = return_value(filename,'_degree_')

        if i==len(laserlist)-1:#do this for first dataset to make it stackable
            laser_array = mymax
            angle_array = angle
        else:
            laser_array = np.append(laser_array,mymax)
            angle_array = np.append(angle_array,angle)
        i -=1
    return laser_array,angle_array



def sine(phi):
    return np.sin(2*phi)
def sinesq(phi):
    return np.square(np.sin(2*phi))
def cos(phi):
    return np.cos(2*phi)
def cossq(phi):
    return np.square(np.cos(2*phi))
def sined(delta):
    return np.sin(delta)
def cosd(delta):
    return np.cos(delta)


def a22(phi,delta): 
    return cossq(phi)+cosd(delta)*sinesq(phi)
def a32(phi,delta): 
    return cos(phi)*sine(phi)-cos(phi)*cos(phi)*sine(phi)
def a42(phi,delta): 
    return sine(phi)*sined(delta)
def a23(phi,delta): 
    return cos(phi)*sine(phi)-cos(phi)*cosd(delta)*sine(phi)
def a33(phi,delta): 
    return cosd(delta)*cossq(phi)+sinesq(phi)
def a43(phi,delta): 
    return -cos(phi)*sined(delta)
def a24(phi,delta): 
    return -sine(phi)*sined(delta)
def a34(phi,delta): 
    return cos(phi)*sined(delta)
def a44(phi,delta): 
    return cosd(delta)

def LinearPolarizer(phi2):
    """General linear polarizer, phi is the angle of the polarizer."""
    return map(lambda phi: np.array(
        [[1, np.cos(2*phi), np.sin(2*phi),  0],
        [np.cos(2*phi)   , np.square(np.cos(2*phi)), np.sin(2*phi)*np.cos(2*phi),  0],
        [np.sin(2*phi)   , np.sin(2*phi)*np.cos(2*phi), np.square(np.sin(2*phi)),  0],
        [0, 0, 0, 0]]
        ),phi2)

def LinearRetarder(phi2, delta,shift=0):
    """ General linear retarder, phi is the angle of the retarder
        calculates waveplates.
    """
    phi2 = phi2-shift
    #print 'shift: ',shift
    return map(lambda phi: np.array(
        [[1,               0,              0,               0],
         [0 , a22(phi,delta), a32(phi,delta),  a42(phi,delta)],
         [0 , a23(phi,delta), a33(phi,delta),  a43(phi,delta)],
         [0 , a24(phi,delta), a34(phi,delta),  a44(phi,delta)]]
         ),phi2)

def QuarterWP (phi, shift=0):
    """defines a quarter waveplate"""
    delta = np.pi/2
    return LinearRetarder(phi,delta,shift)
def HalfWP (phi, shift=0):
    """defines a half waveplate"""
    delta = np.pi
    return LinearRetarder(phi,delta,shift)
def StokesVector(s0,s1,s2,s3):
    return np.array([s0,s1,s2,s3])
def StokesPolarization(x,stokesvector=np.array([1,0,0,1]),waveplate='qwp', shift=np.pi/9.):
    """Returns Stokes vector after passing through a waveplate"""
    s   = stokesvector
    if waveplate =='qwp' or waveplate == 1:
        wp = QuarterWP(x, shift)
    else:
        wp = HalfWP(x,shift)
    p   = np.einsum('...j,j',wp ,s)
    result = np.square(np.absolute(p))
    s0 =np.transpose(result)[0]
    s1 =np.transpose(result)[1]
    s2 =np.transpose(result)[2]
    s3 =np.transpose(result)[3]
    return s0,s1,s2,s3

def StokesMixture(x,stokesvector=np.array([1,1,1,1]),waveplate=0, shift=np.pi/9., linear=1, circular=0):
    """Defines a mixture of polarized light, with a and b components"""
    s0,s1,s2,s3 = StokesPolarization(x,stokesvector, waveplate, shift)    
    return linear*s1+circular*s3
def StokesMixture2(x,waveplate=0, shift=np.pi/9., linear=1, circular=0):
    """Defines a mixture of polarized light, with a and b components"""
    stokesvector=np.array([1,linear,0,circular])
    s0,s1,s2,s3 = StokesPolarization(x,stokesvector, waveplate, shift)    
    #iy=(np.sqrt(np.square(s1)+np.square(s2)+np.square(s3))-s1)/2
    return s1+s3#s1+s3
def StokesMixture3(x,waveplate=0, shift=np.pi/9., linear=1, circular=0, lin2=0):
    """defines a mixture of polarized light, with a and b components"""
    stokesvector=np.array([1,linear,lin2,circular])
    s0,s1,s2,s3 = StokesPolarization(x,stokesvector, waveplate, shift)    

    return s1+s2+s3
def TestStokes(stokesvector=np.array([1,0,0,1]), waveplate='qwp'):
    """Stokes Demonstration, calculation takes 8.41ms  on a Win7 i5"""
    x=np.arange(0,np.pi/2,0.01)# create a si           nusoidal
    s0,s1,s2,s3 = StokesPolarization(x,stokesvector,waveplate)
    ax=plt.subplot(111,projection='polar')
    ax.plot(x*4,s0, color='r',linewidth=3,label='S0')
    ax.plot(x*4,s1, color='g',linewidth=3,label='S1')
    ax.plot(x*4,s2, color='b',linewidth=3,label='S2')
    ax.plot(x*4,s3, color='y',linewidth=3,label='S3')
    ax.grid(True)
    ax.legend(bbox_to_anchor=(0, 0, 1, 0.15), bbox_transform=gcf().transFigure)
    ax.set_title('Stokes', va='bottom')
    plt.show(block=False)

def FitStokes(x,y,q=True, start_angle=0,units='degree', title='', cross=True, plotcolor='bo', label=''):
    
    from lmfit import  Model
    norm = np.max(y)
    y = y/norm #normalize it
    if q:
        waveplate=1# if quarter wave
    else:
        waveplate=0# if half wave plate
    # Fit Model
    if units == 'degree':
        x = x*np.pi/90.
        start_angle = start_angle*np.pi/90.
    polmodel=Model(StokesMixture2)
    pars = polmodel.make_params()
    pars['shift'].set(value = 1, min=-4*np.pi,max=3*np.pi)
    pars['linear'].set(value = 1,min=0, max=1.5)
    pars['circular'].set(value = 0.2,min=0, max=1.5)
    if q:
        pars['linear'].set(value = 0.0,min=0, max=1.5)
        pars['circular'].set(value = 1.2,min=0, max=1.5)
    pars['waveplate'].set(value=waveplate, vary=False)
    result = polmodel.fit(y,pars,x=x/4.,waveplate=waveplate)
    #some parameters
    sh=8*(result.best_values['shift']-start_angle) %np.pi#modulo pi
    print 'shift ', sh
    rcp= np.round(result.best_values['circular'],2)
    lvp= np.round(result.best_values['linear'],2)
    s0 = np.sqrt(np.sqrt(rcp)+np.sqrt(lvp))
    s0, s1, s3 = np.round(s0/s0,2),np.round(lvp/s0,2), np.round(rcp/s0,2)
    s2=0
    s0a,s1a,s2a,s3a=StokesPolarization(x,stokesvector=np.array([s0,s1,s2,s3]),waveplate='hwp', shift=sh)
    pol_degree = np.round((np.sqrt(np.square(s1)+np.square(s2)+np.square(s3)))/s0,2)
    fitlabel = 'fit ('+'s0= '+str(s0)+', s1='+str(s1)+', s2=0'+', s3= '+str(s3)+') , '+r'$ \Pi$= '+str(pol_degree)
    return x,y,sh,result, fitlabel,s0a,s1a,s2a,s3a
def PlotStokes(x,y,result,sh,fitlabel, plotcolor, title,cross=True, alpha=1, line_label=''):
    degree_sign= u'\N{DEGREE SIGN}'# to have the degree sign
    plt.subplots_adjust(bottom=0.35)
    ax=plt.subplot(111,projection='polar')
    ax.plot(x,y, plotcolor+'o',linewidth=3,label=line_label+' raw data')
    ax.plot(x,result.best_fit, color=plotcolor,label = fitlabel)
    # create lines to illustrate shift
    if cross:
        crossX,crossY = createCross(sh)# for shift
        crossXp,crossYp = createCross(sh+np.pi)# for shift
        ax.plot(crossX,crossY, color=plotcolor)
        ax.plot(crossXp,crossYp, color=plotcolor)
        ax.text(sh*4, 0.5*max(crossY), 'shift='+str(np.round(sh*90/np.pi,2))+degree_sign, rotation=sh/2, color=plotcolor )
        ax.patch.set_alpha(alpha)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(0, 0, 0.8, 0.3), bbox_transform=gcf().transFigure)
    ax.set_title(title, va='bottom')
    plt.show(block=False)
    return ax
def Plot4plots(axarr,aplot, i):
    if i == 0:
        axarr[0,0]=aplot
    if i == 1:
        axarr[0,1]=aplot
    if i == 2:
        axarr[1,0]=aplot
    if i == 3:
        axarr[1,1]=aplot
def FitStokesDictionary(laserdict,PLdict,q=True ,plottitle=''):

    i=0
    for key, value in PLdict.iteritems() :
        if not key == 'angle':
            x,y,sh,result, fitlabel,s0a,s1a,s2a,s3a= FitStokes(laserdict['laser_angle'],laserdict['laser'],q=q, start_angle=0,units='degree', title=plottitle, cross=True, plotcolor='go', label='laser')
            PlotStokes(x,y,result,sh,fitlabel, plotcolor='y',title=plottitle, alpha=0.5, line_label='785nm laser')
            color=returnPlotcolor(key)#to have different colors
            #print 'color', color
            x,y,sh,result, fitlabel,s0a,s1a,s2a,s3a= FitStokes(PLdict['angle'],value,q=q, start_angle=0,units='degree', title=plottitle+key, cross=True, plotcolor='go', label='laser')
            aplot=PlotStokes(x,y,result,sh,fitlabel, plotcolor=color,title=key+plottitle,line_label=key)

            #axarr
            plt.savefig(key+'fit.png')
            pp = PdfPages(key+'fit.pdf')
            pp.savefig()
            pp.close()
            plt.clf()
            plt.close()

            i+=1
    return s0a,s1a,s2a,s3a
    #f.savefig('all_lines_fit.png')
def returnPlotcolor(key):
    if key == 'v1prime':
        color='b'
    if key == 'v1':
        color='r'
    if key == 'v2prime':
        color='g'
    if key == 'v2':
        color='m'
    return color

def createCross(shift):
    # creates a cross, reuturn values are x1, x2=x1+90degree, y
    x0=np.full(100,shift/2.)
    x1=np.full(100,shift/2.+np.pi)
    x= np.append(x1,x0)
    y=np.arange(0,1,1/200.)
    #print len(x)
    #print len(y)
    return x,y
#-----------------------------------------------
#----- Folder Specs ------------------------

startfolder = os.getcwd()

#data_path = 'F:/Messdaten/2016-07-06/CREE/Spec_Polar_P70K_Emission_Quater_Waveplate/'
base= 'D:\\data\\2016\\'
date= '2016-08-08\\'
date_laser='2016-08-11\\'
sample='CREE\\'
#meas = 'P70K_Excitation_HWP_13d_Parallel_C_Emission_HWP(rotating)/'
#meas = 'P5.5K_Excitation_HWP_13d_Paral_C_Emission_HWP(rotating)'
#meas ='P5.5K_Excitation_HWP_35.5d_C_Emission_HWP(rotating)'
#meas = 'P70K_Excitation_HWP_35.5d_Perp_C_Emission_HWP(rotating)'
#meas = 'P70K_Excitation_HWP_35.5d_Perp_C_Emission_QWP(rotating)'
#meas ='P50K_Exci_HWP_10d_HWP(rot)B MW(-19_350_178_248)'
meas = 'P5.5K_Excitation_QWP_0d_HWP(rotating) HR B MW(-19dBm 350MHz OR)'
data_path=base+date+sample+meas+'\\First_Measurement\\pys\\'
#data_path = 'F:/Messdaten/2016-07-22/CREE/P70K_Excitation_HWP_13d_Parallel_C_Emission_HWP(rotating)/First_Measurement/pys'
file_list = get_file_list_sorted(data_path)[::-1]
#cal ='laser_calibration HWP_360 13_degree Parallel to C'
#cal='laser_calibration 5.5K HWP_360 13_degree to C'
#cal='laser_calibration 5.5K HWP_360 35.5_degree to C'
#cal='laser_calibration 5.5K HWP_360 35.5_degree to C'
#cal='laser_calibration QWP_360 35.5_degree to C'
cal='laser_calibration 5.5K excitation_HWP 10d_degree BP_Filter'
calibration_path= base+date_laser+sample+cal+'/First_Measurement/pys'
laser,angle_laser = getCalibration(calibration_path)# our laser polarization
os.chdir(data_path)
wavelength,intensity = getSpectrum(file_list[1])
mydict={'wavelength':wavelength}

#get some basic measurement parameters, as temperature etc
temperature = return_value(file_list[1],'K_')
start_angle = return_value(file_list[1],'d_')
#create empty array first
intensity_array=[]
angle_array=[]
v1_array=[]
v1prime_array=[]
v2_array=[]
v2prime_array=[]
#--------Loop over all files-----------
i=len(file_list)-1
while i >= 0:
    os.chdir(data_path)
    g=file_list[i]
    wavelength, intensity = getSpectrum(g)    
    #-----Normalization     
    intensity = intensity-np.mean(intensity[20:60])
    v1_max_sideband = intensity[494]
    v1_min_sideband = intensity[475]
    v1_sideband = (v1_max_sideband - v1_min_sideband)/2.
    v1 = np.max(intensity[475:494]) - (v1_min_sideband + 1.3*v1_sideband)
    v1p_max_sideband = intensity[475]
    v1p_min_sideband = intensity[460]
    v1p_sideband = (v1p_max_sideband - v1p_min_sideband)/2.
    v1prime = np.max(intensity[460:475])-(v1p_min_sideband + 1.3*v1p_sideband)
    v2 = np.max(intensity[740:760])
    v2prime = np.max(intensity[530:550])
    angle = return_value(g,'_degree')
    #-----Data stacking
    if i==len(file_list)-1:#do this for first dataset to make it stackable
        intensity_array = intensity
        angle_array=angle
        v1_array = v1
        v1prime_array = v1prime
        v2_array = v2
        v2prime_array = v2prime
    else:
        intensity_array = np.vstack((intensity_array,intensity))
        angle_array=np.append(angle_array,angle)
        v1_array = np.append(v1_array,v1)
        v1prime_array = np.append(v1prime_array,v1prime)
        v2_array = np.append(v2_array,v2)
        v2prime_array = np.append(v2prime_array,v2prime)
    mydict[angle] = intensity#you can also save the dictonary right away
    i -=1


#-----------------------------------------------
#-----creating ouputfile------------------------
df=pandas.DataFrame(np.transpose(intensity_array),index=wavelength,columns=angle_array)
df.to_excel('Measurement Excitation 70K.xlsx',sheet_name='book1')
#dictToCsv(mydict,'First Measurement 5.5K.xlsx')#we dont use this because it is unsorted

#-----------------------------------------------
#-----Polar Plot------------------------
ax = plt.subplot(111, projection='polar')
ax.plot(angle_array*np.pi/90.,v1_array, color='r', linewidth=3,label='v1')
ax.plot(angle_array*np.pi/90.,v1prime_array, color='b', linewidth=3,label='v1_prime')
#ax.plot(angle_laser*np.pi/90.,laser, color='g', linewidth=1,label='785nm laser')
ax.grid(True)
ax.set_title("V1 lines (maximum taken)", va='bottom')
plt.legend()

plt.savefig('polarplot.png')
plt.clf()
plt.close()

#-----------------------------------------------
#-----Polar Plot------------------------
axt = plt.subplot(111, projection='polar')
axt.plot(angle_array*np.pi/90.,v1prime_array, color='b', linewidth=3,label='v1_prime')
#axt.plot(angle_array*np.pi/90.,laser, color='g', linewidth=1,label='785nm laser')
axt.grid(True)
axt.set_title("V1' lines (maximum taken)", va='bottom')
plt.legend()

plt.savefig('polarplot V1.png')
plt.clf()
plt.close()

#plt.show()
#-----Polar Plot Normalized ------------------------
ax2 = plt.subplot(111, projection='polar')
ax2.plot(angle_array*np.pi/90.,v1_array/np.max(v1_array), color='r', linewidth=3, label='v1')
ax2.plot(angle_array*np.pi/90.,v1prime_array/np.max(v1prime_array), color='b', linewidth=3,label='v1_prime')
#ax2.plot(angle_laser*np.pi/90.,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
ax2.grid(True)
ax2.set_title("V1 lines (maximum taken, Normalized)", va='bottom')
plt.legend()
plt.savefig('polarplot_normalized.png')
plt.clf()
plt.close()
#plt.show()

#-----Linear Plot v1 and v1' ------------------------
ax3 = plt.subplot(111)
ax3.plot(angle_array,v1_array/np.max(v1_array), color='r', linewidth=3,label='v1')
ax3.plot(angle_array,v1prime_array/np.max(v1prime_array), color='b', linewidth=3,label='v1_prime')
ax3.plot(angle_laser,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
#ax3.plot(angle_array,2*(v1prime_array/v1_array), color='g', linewidth=3,label='v1p/v1')
ax3.grid(True)
Contrast1=np.round(1-np.min(v1_array)/np.max(v1_array),2)
Contrast2=np.round(1-np.min(v1prime_array)/np.max(v1prime_array),2)
#Contrast3=np.round(np.max(v1prime_array)/np.max(v1_array),2)
title1="Contrast V1="+str(Contrast1)
title2="V1p="+str(Contrast2)
#title3="1-V1p/V1"+str(Contrast3)
ax3.set_title(title1+title2, va='bottom')
plt.legend()
plt.savefig('Lineplot.png')
plt.clf()
plt.close()

#-----Linear Plot v2 ------------------------
ax4 = plt.subplot(111)
ax4.plot(angle_array, v2_array/np.max(v2_array), color='b', linewidth=3,label='v2')
ax4.plot(angle_laser,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
ax4.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax4.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Lineplot Normalized.png')
plt.clf()
plt.close()

#-----Linear Plot v2 ------------------------
ax7 = plt.subplot(111)
ax7.plot(angle_array, v2_array, color='b', linewidth=3,label='v2')
ax7.plot(angle_laser,laser, color='g', linewidth=1,label='785nm laser')
ax7.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax7.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Lineplot.png')
plt.clf()
plt.close()

#-----Polar Plot V2------------------------
ax5 = plt.subplot(111, projection='polar')
ax5.plot(angle_array*np.pi/90., v2_array/np.max(v2_array), color='b', linewidth=3,label='v2')
ax5.plot(angle_laser*np.pi/90.,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
ax5.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax5.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Polarplot Normalized.png')
plt.clf()
plt.close()
#
#-----Polar Plot V2------------------------
ax6 = plt.subplot(111, projection='polar')
ax6.plot(angle_array*np.pi/90., v2_array, color='b', linewidth=3,label='v2')
ax6.plot(angle_laser*np.pi/90.,laser, color='g', linewidth=1,label='785nm laser')
ax6.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax6.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Polarplot.png')
plt.clf()
plt.close()
print 'Excel File Created'
print 'Plots Created'

#-----Density Plot------------------------
fig = plt.figure()
ax = fig.gca(projection='3d')
X,Y=np.meshgrid(wavelength,angle_array[0])
surf=ax.plot_surface(X,Y,intensity_array, cmap=cm.coolwarm, linewidth=1, antialiased=False)

ax.zaxis.set_major_locator(LinearLocator(10))
ax.zaxis.set_major_formatter(FormatStrFormatter('%.02f'))
fig.colorbar(surf, shrink=0.5, aspect=5)
#plt.show(block=False)


mytitle='Spec_Polar_P5.5K_Emission_Polarisation'
#-normalizing data
v1primenorm=(v1prime_array-min(v1prime_array))/max(v1prime_array-min(v1prime_array))
v1norm=(v1_array-min(v1_array))/max(v1_array-min(v1_array))
v2norm=(v2_array-min(v2_array))/max(v2_array-min(v2_array))
v2primenorm=(v2prime_array-min(v2prime_array))/max(v2prime_array-min(v2prime_array))

#-----Density Plot with pylab------------------------
fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, figsize=(6,10))
#fig, ax4 = plt.subplots(nrows=1, figsize=(6,10),projection='polar')
ax1.imshow(intensity_array, extent=[wavelength[0],wavelength[len(wavelength)-1],angle_array[0],np.pi],aspect='auto')
ax1.set_title(mytitle)
start,stop=425,760
cut_intensity=np.transpose(np.transpose(intensity_array)[start:stop])
ax2.imshow(cut_intensity, extent=[wavelength[start],wavelength[stop],0,np.pi], aspect='auto')
ax2.set_title('zoom in')
ax3.plot(angle_array*np.pi/180.,v1prime_array,  color='b', linewidth=3,label='v1\'(858.7)')
ax3.plot(angle_array*np.pi/180.,v1_array,       color='r', linewidth=3,label='v1 (861.4 nm)')
ax3.plot(angle_array*np.pi/180.,v2prime_array,  color='g', linewidth=3,label='v2\' (873.6 nm)')
ax3.plot(angle_array*np.pi/180.,v2_array,       color='m', linewidth=3,label='v2 (916.6 nm)')
ax4.plot(angle_array*np.pi/180.,v1primenorm, color='b', linewidth=3,label='v1\'(858.7)')
ax4.plot(angle_array*np.pi/180.,v1norm, color='r', linewidth=3,label='v1 (861.4 nm)')
ax4.plot(angle_array*np.pi/180.,v2primenorm, color='g', linewidth=3,label='v2\' (873.6 nm)')
ax4.plot(angle_array*np.pi/180.,v2norm, color='m', linewidth=3,label='v2 (916.6 nm)')
ax4.plot(angle_laser*np.pi/180.,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')


ax3.grid(True)
ax3.set_title("V1 lines (maximum taken)", va='bottom')
plt.legend()
plt.tight_layout()
#plt.show(block=False)
plt.savefig(mytitle+'.png')
plt.clf()
plt.close()
#----all in polarplot
ax5 = plt.subplot(111, projection='polar')
ax5.plot(angle_array*np.pi/90.,v1prime_array,  color='b', linewidth=3,label='v1\'(858.7)')
ax5.plot(angle_array*np.pi/90.,v1_array,       color='r', linewidth=3,label='v1 (861.4 nm)')
ax5.plot(angle_array*np.pi/90.,v2prime_array,  color='g', linewidth=3,label='v2\' (873.6 nm)')
ax5.plot(angle_array*np.pi/90.,v2_array,       color='m', linewidth=3,label='v2 (916.6 nm)')
ax5.plot(angle_laser*np.pi/90.,laser, color='y', linewidth=1,label='785nm laser')
ax5.grid(True)
ax5.set_title("All lines (maximum taken)", va='bottom')
plt.legend(bbox_to_anchor=(.05, -0.2), loc=2, borderaxespad=0)

plt.savefig('polarplot_all.png')
plt.close()
#-----------------------------
# save plots seperately
fig, ax = plt.subplots(nrows=1, figsize=(6,10))
ax.imshow(intensity_array, extent=[wavelength[0],wavelength[len(wavelength)-1],angle_array[0],np.pi],aspect='auto')
ax.grid(True)
ax.set_title('Intensity Plot')
plt.savefig(mytitle+'1.png')
plt.clf()
plt.close()
# --------------------
fig, ax = plt.subplots(nrows=1, figsize=(6,10))
start,stop=425,760
cut_intensity=np.transpose(np.transpose(intensity_array)[start:stop])
ax.imshow(cut_intensity, extent=[wavelength[start],wavelength[stop],0,np.pi], aspect='auto')
ax.set_title('zoom in')
ax.grid(True)
plt.savefig(mytitle+'2.png')
plt.clf()
# --------------------
plt.close()
# FitPolarization(angle_array,v2_array,start_angle=45,title='V2, 70K,exc: HWP, E parallel c, em:HWP',q=False)
# FitPolarization(angle_array,v2prime_array,q=False, start_angle=0, title='V2, 70K,exc: HWP, E parallel c, em:HWP',cross=False)
# FitPolarization(angle_array,v1prime_array,q=True, start_angle=0, title='V1prime, 70K,exc: HWP, E parallel c, em:HWP',cross=False)

#--------------------
#--- FITTING---------
perpendsign = unichr(0x27C2)
parsign     = unichr(0x2225)
plottitle = ' E '+'unknown to'+' c '#first it is not known
g=meas
temperature = return_value(g,'K_')
perpendicular = r' $\vec{E}$ '+r'$\bot$'+r' $\vec{c}$ @ '
parallel = r' $\vec{E}$ '+r'$\parallel$'+r' $\vec{c}$ @ '
#temperature = str(70)+'K_'
if g.find('Perp')>0:
    plottitle = perpendicular
    print 'Perpendicular to C'

if g.find('Para')>0:
    plottitle = parallel
    print 'Parallel to C'

if g.find('13')>0:    
    plottitle = parallel
    print 'Parallel to C'

if g.find('58')>0: 
    plottitle = perpendicular
    print 'Perpendicular to C'

if g.find('35.5')>0: 
    plottitle = r' $\vec{E}$ '+'45'+r' $\vec{c}$ '
    print '45 degree to C'

    
plottitle+= ' '+str(temperature)+'K - '
if g.find('Excitation_HWP')>0:
    plottitle+='Excitation: HWP -'

if g.find('Excitation_QWP')>0:
    plottitle+='Excitation: QWP -'
if g.find('Emission_HWP')>0:
    q=False#no qwp
    plottitle+=' Detection: HWP'
if g.find('Emission_QWP')>0:
    q=True
    print 'QWP in detection'
    plottitle+='Detection: QWP'


q=False


laserdict={'laser':laser}#first dict entry
laserdict['laser_angle']=angle_laser
PLdict={'angle':angle_array}#first dict entry
PLdict['v1']=v1_array
PLdict['v1prime']=v1prime_array
PLdict['v2']=v2_array
PLdict['v2prime']=v2prime_array

s0a,s1a,s2a,s3a=FitStokesDictionary(laserdict,PLdict,q=q ,plottitle=plottitle)

# combine the plots into one
import shutil
import pdfkit #download it here:  http://wkhtmltopdf.org/downloads.html

def convertAllToPdf(startfolder):
    b = startfolder+'/tools/'
    config = pdfkit.configuration(wkhtmltopdf='C:/Program Files (x86)/wkhtmltopdf/bin/wkhtmltopdf.exe')
    shutil.copy('v1primefit.png', b)
    shutil.copy('v2primefit.png', b)
    shutil.copy('v1fit.png', b)
    shutil.copy('v2fit.png', b)
    shutil.copy('Spec_Polar_P5.5K_Emission_Polarisation.png',b)
    pdfkit.from_file(startfolder+'/tools/template.html', g+'all.pdf',configuration=config)
    os.remove(b+'v1primefit.png')
    os.remove(b+'v1fit.png')
    os.remove(b+'v2primefit.png')
    os.remove(b+'v2fit.png')
    os.remove(b+'Spec_Polar_P5.5K_Emission_Polarisation.png')

try:
    convertAllToPdf(startfolder)
except:
    print 'no combined pdf created'

import subprocess

subprocess.Popen('explorer "{0}"'.format(data_path))

os.chdir(startfolder) 
