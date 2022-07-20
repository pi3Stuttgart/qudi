import cPickle, pylab, os
import matplotlib.pyplot as plt
import numpy as np
import matplotlib, pandas, time
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from matplotlib.pylab import *
import matplotlib.pyplot as plt
from tools import save_toolbox
from stat import S_ISREG, ST_CTIME, ST_MODE,ST_MTIME

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

def getCalibration(folder):
    laserlist=get_file_list_sorted(folder)[::-1]
    i=len(laserlist)-1
    laser_array=[]
    while i >= 0:
        filename=laserlist[i]
        os.chdir(folder)    
        f=open(filename,'rb')
        d=cPickle.load(f)
        wavelength=d['wavelength']
        intensity = d['intensity']
        mymax = np.max(intensity)
        if i==len(laserlist)-1:#do this for first dataset to make it stackable
            laser_array = mymax
        else:
            laser_array = np.append(laser_array,mymax)
        i -=1
    return laser_array
    

#-----------------------------------------------
#----- Folder Specs ------------------------

startfolder = os.getcwd()

#data_path = 'F:/Messdaten/2016-07-06/CREE/Spec_Polar_P70K_Emission_Quater_Waveplate/'
data_path = 'D:/data/2016/2016-08-04/CREE/P5.5K_Excitation_HWP_13d_Paral_C_Emission_HWP(rotating) 2/First_Measurement/pys'
file_list = get_file_list_sorted(data_path)[::-1]
#calibration_path= 'D:/data/2016/2016-07-19/CREE/laser_calibration/First_Measurement/pys'
#calibration_path= 'D:/data/2016/2016-07-19/CREE/laser_calibration 360/First_Measurement/pys'
#calibration_path= 'D:/data/2016/2016-07-19/CREE/laser_calibration 360/First_Measurement/pys'
calibration_path= 'D:/data/2016/2016-07-29/CREE/laser_calibration 5.5K HWP_360 13_degree to C/First_Measurement/pys'
laser = getCalibration(calibration_path)# our laser polarization

#get wavelength from first file
g=file_list[1]
os.chdir(data_path)
f=open(g,'rb')
d=cPickle.load(f)
wavelength=d['wavelength']
mydict={'wavelength':wavelength}

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
    f=open(g,'rb')
    d=cPickle.load(f)
    #-----Normalization
    intensity = d['intensity'] 
    intensity = intensity-np.mean(intensity[20:100])
    v1 = np.max(intensity[475:494])
    v1prime = np.max(intensity[460:475])
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
ax.plot(angle_array*np.pi/90.,laser, color='g', linewidth=1,label='785nm laser')
ax.grid(True)
ax.set_title("V1 lines (maximum taken)", va='bottom')
plt.legend()

plt.savefig('polarplot.png')
plt.clf()

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

#plt.show()
#-----Polar Plot Normalized ------------------------
ax2 = plt.subplot(111, projection='polar')
ax2.plot(angle_array*np.pi/90.,v1_array/np.max(v1_array), color='r', linewidth=3, label='v1')
ax2.plot(angle_array*np.pi/90.,v1prime_array/np.max(v1prime_array), color='b', linewidth=3,label='v1_prime')
ax2.plot(angle_array*np.pi/90.,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
ax2.grid(True)
ax2.set_title("V1 lines (maximum taken, Normalized)", va='bottom')
plt.legend()
plt.savefig('polarplot_normalized.png')
plt.clf()
#plt.show()

#-----Linear Plot v1 and v1' ------------------------
ax3 = plt.subplot(111)
ax3.plot(angle_array,v1_array/np.max(v1_array), color='r', linewidth=3,label='v1')
ax3.plot(angle_array,v1prime_array/np.max(v1prime_array), color='b', linewidth=3,label='v1_prime')
ax3.plot(angle_array,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
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

#-----Linear Plot v2 ------------------------
ax4 = plt.subplot(111)
ax4.plot(angle_array, v2_array/np.max(v2_array), color='b', linewidth=3,label='v2')
ax4.plot(angle_array,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
ax4.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax4.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Lineplot.png')
plt.clf()

#-----Polar Plot------------------------
ax5 = plt.subplot(111, projection='polar')
ax5.plot(angle_array*np.pi/90., v2_array/np.max(v2_array), color='b', linewidth=3,label='v2')
ax5.plot(angle_array*np.pi/90.,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')
ax5.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax5.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Polarplot.png')
plt.clf()
#
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
ax4.plot(angle_array*np.pi/180.,laser/np.max(laser), color='g', linewidth=1,label='785nm laser')


ax3.grid(True)
ax3.set_title("V1 lines (maximum taken)", va='bottom')
plt.legend()
plt.tight_layout()
#plt.show(block=False)
plt.savefig(mytitle+'.png')
plt.clf()
#----all in polarplot
ax5 = plt.subplot(111, projection='polar')
ax5.plot(angle_array*np.pi/90.,v1prime_array,  color='b', linewidth=3,label='v1\'(858.7)')
ax5.plot(angle_array*np.pi/90.,v1_array,       color='r', linewidth=3,label='v1 (861.4 nm)')
ax5.plot(angle_array*np.pi/90.,v2prime_array,  color='g', linewidth=3,label='v2\' (873.6 nm)')
ax5.plot(angle_array*np.pi/90.,v2_array,       color='m', linewidth=3,label='v2 (916.6 nm)')
ax5.plot(angle_array*np.pi/90.,laser, color='y', linewidth=1,label='785nm laser')
ax5.grid(True)
ax5.set_title("All lines (maximum taken)", va='bottom')
plt.legend(bbox_to_anchor=(.05, -0.2), loc=2, borderaxespad=0)

plt.savefig('polarplot_all.png')

#-----------------------------
# save plots seperately
fig, ax = plt.subplots(nrows=1, figsize=(6,10))
ax.imshow(intensity_array, extent=[wavelength[0],wavelength[len(wavelength)-1],angle_array[0],np.pi],aspect='auto')
ax.grid(True)
ax.set_title('Intensity Plot')
plt.savefig(mytitle+'1.png')
plt.clf()
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


os.chdir(startfolder) 