import cPickle, pylab, os
import matplotlib.pyplot as plt
import numpy as np
import matplotlib, pandas, time
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

#-----------------------------------------------
#----- Folder Specs ------------------------

startfolder = os.getcwd()
data_path = 'D:/data/2016/2016-07-13/CREE/Spec_Polar_P5.5K_Emission_HWP_S3_0/First_Measurement/pys'

file_list = get_file_list_sorted(data_path)[::-1]


#get wavelength from first file
g=file_list[1]
os.chdir(data_path)
f=open(g,'rb')
d=cPickle.load(f)
wavelength=d['wavelength']
mydict={'wavelength':wavelength}

intensity_array=[]
angle_array=[]
v1_array=[]
v1prime_array=[]
v2_array=[]
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
    v1 = np.max(intensity[475:490])
    v1prime = np.max(intensity[460:470])
    v2 = np.max(intensity[740:760])
    angle = return_value(g,'_degree')
    #-----Data stacking
    if i==len(file_list)-1:#do this for first dataset to make it stackable
    	intensity_array = intensity
    	angle_array=angle
    	v1_array = v1
    	v1prime_array = v1prime
    	v2_array = v2
    else:
    	intensity_array = np.vstack((intensity_array,intensity))
    	angle_array=np.append(angle_array,angle)
    	v1_array = np.append(v1_array,v1)
    	v1prime_array = np.append(v1prime_array,v1prime)
    	v2_array = np.append(v2_array,v2)
    mydict[angle] = intensity#you can also save the dictonary right away
    i -=1
#-----------------------------------------------
#-----V1 S Paramter------------------------l
v1_max =  np.max(v1_array)
v1_min =  np.min(v1_array)


#-----V1 Prime S Paramter------------------------
v1p_max =  np.max(v1prime_array)
v1p_min = np.min(v1prime_array)


#-----creating ouputfile------------------------
df=pandas.DataFrame(np.transpose(intensity_array),index=wavelength,columns=angle_array)
df.to_excel('Measurement Emission HWP 70K.xlsx',sheet_name='book1')
#dictToCsv(mydict,'First Measurement 5.5K.xlsx')#we dont use this because it is unsorted

#-----------------------------------------------
#-----Polar Plot------------------------
ax = plt.subplot(111, projection='polar')
ax.plot(angle_array*np.pi/90.,v1_array, color='r', linewidth=3,label='v1')
ax.plot(angle_array*np.pi/90.,v1prime_array, color='b', linewidth=3,label='v1_prime')
ax.grid(True)
ax.set_title("V1 lines (maximum taken)", va='bottom')
plt.legend()

plt.savefig('polarplot.png')
plt.clf()
#plt.show()
#-----Polar Plot Normalized ------------------------
ax2 = plt.subplot(111, projection='polar')
ax2.plot(angle_array*np.pi/90.,v1_array/np.max(v1_array), color='r', linewidth=3, label='v1')
ax2.plot(angle_array*np.pi/90.,v1prime_array/np.max(v1prime_array), color='b', linewidth=3,label='v1_prime')
ax2.grid(True)
ax2.set_title("V1 lines (maximum taken, Normalized)", va='bottom')
plt.legend()
plt.savefig('polarplot_normalized.png')
plt.clf()
#plt.show()

#-----Linear Plot v1 and v1' ------------------------
ax3 = plt.subplot(111)
ax3.plot(angle_array,v1_array, color='r', linewidth=3,label='v1')
ax3.plot(angle_array,v1prime_array, color='b', linewidth=3,label='v1_prime')
#ax3.plot(angle_array,2*(v1prime_array/v1_array), color='g', linewidth=3,label='v1p/v1')
ax3.grid(True)
#Contrast1=np.round(1-np.min(v1_array)/np.max(v1_array),2)
#Contrast2=np.round(1-np.min(v1prime_array)/np.max(v1prime_array),2)
#Contrast3=np.round(np.max(v1prime_array)/np.max(v1_array),2)
S0 =  np.min(v1_array)+np.max(v1_array)
S1 = np.max(v1_array)- np.min(v1_array)
Iy = np.min(v1prime_array)
Ix = np.max(v1prime_array)
title1="For V S0="+str(S0)+'  S1='+str(S1)+' Ix='+str(Ix)+' Iy='+str(Iy)
#title2="V1p="+str(Contrast2)
#title3="1-V1p/V1"+str(Contrast3)
ax3.set_title(title1, va='bottom')
plt.legend()
plt.savefig('Lineplot.png')
plt.clf()

#-----Linear Plot v2 ------------------------
ax4 = plt.subplot(111)
ax4.plot(angle_array, v2_array/np.max(v2_array), color='b', linewidth=3,label='v2')
ax4.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax3.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Lineplot.png')
plt.clf()

#-----Polar Plot------------------------
ax5 = plt.subplot(111, projection='polar')
ax5.plot(angle_array*np.pi/90., v2_array, color='b', linewidth=3,label='v2')
ax5.grid(True)
Contrast=np.round(1-np.min(v2_array)/np.max(v2_array))
title1="Contrast V2 ="+str(Contrast)
ax3.set_title(title1, va='bottom')
plt.legend()
plt.savefig('V2 Polarplot.png')
plt.clf()
#
print 'V1 and V1p'
print 'v1_max = '+str(v1_max)
print 'v1_min = '+str(v1_min)
print 'v1p_max = '+str(v1p_max)
print 'v1p_min =' +str(v1p_min) 


os.chdir(startfolder) 