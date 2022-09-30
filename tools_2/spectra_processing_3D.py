import cPickle, pylab, os
import matplotlib.pyplot as plt
import numpy as np
import matplotlib, pandas, time
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
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

def get_folder_list(some_path):
    orgin_path=os.getcwd()
    os.chdir(some_path)
    path = os.getcwd()
    file_list = [f for f in os.listdir('.')]
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

def get_arrays(file_list,data_path):
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
    return intensity_array,angle_array,v1_array,v1prime_array,v2_array

#-----------------------------------------------
#----- Folder Specs ------------------------

startfolder = os.getcwd()
data_path = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_0.0_Degree/pys'
data_path1 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_9.0_Degree/pys'
data_path2 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_18.0_Degree/pys'
data_path3 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_27.0_Degree/pys'
data_path4 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_36.0_Degree/pys'
data_path5 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_45.0_Degree/pys'
data_path6 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_54.0_Degree/pys'
data_path7 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_63.0_Degree/pys'
data_path8 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_72.0_Degree/pys'
data_path9 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_81.0_Degree/pys'
data_path10 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_90.0_Degree/pys'
data_path11 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_99.0_Degree/pys'
data_path12 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_108.0_Degree/pys'
data_path13 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_117.0_Degree/pys'
data_path14 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_126.0_Degree/pys'
data_path15 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_135.0_Degree/pys'
data_path16 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_144.0_Degree/pys'
data_path17 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_153.0_Degree/pys'
data_path18 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_162.0_Degree/pys'
data_path19 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_171.0_Degree/pys'
data_path20 = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/Excitation_180.0_Degree/pys'

data_path_Ex = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM'


file_list = get_file_list_sorted(data_path)[::-1]
file_list1 = get_file_list_sorted(data_path1)[::-1]
file_list2 = get_file_list_sorted(data_path2)[::-1]
file_list3 = get_file_list_sorted(data_path3)[::-1]
file_list4 = get_file_list_sorted(data_path4)[::-1]
file_list5 = get_file_list_sorted(data_path5)[::-1]
file_list6 = get_file_list_sorted(data_path6)[::-1]
file_list7 = get_file_list_sorted(data_path7)[::-1]
file_list8 = get_file_list_sorted(data_path8)[::-1]
file_list9 = get_file_list_sorted(data_path9)[::-1]
file_list10 = get_file_list_sorted(data_path10)[::-1]
file_list11 = get_file_list_sorted(data_path11)[::-1]
file_list12 = get_file_list_sorted(data_path12)[::-1]
file_list13 = get_file_list_sorted(data_path13)[::-1]
file_list14 = get_file_list_sorted(data_path14)[::-1]
file_list15 = get_file_list_sorted(data_path15)[::-1]
file_list16 = get_file_list_sorted(data_path16)[::-1]
file_list17 = get_file_list_sorted(data_path17)[::-1]
file_list18 = get_file_list_sorted(data_path18)[::-1]
file_list19 = get_file_list_sorted(data_path19)[::-1]
file_list20 = get_file_list_sorted(data_path20)[::-1]

file_list_EX = get_folder_list(data_path_Ex)[::-1]


basefolder = 'D:/data/2016/2016-07-04/CREE/Spec_Polar_P70K_Emission_Polarisation_RM/'


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
Ex_Pol_array=[]

i=len(file_list_EX)-1
while i >= 0:
    Ex_Pol=return_value
    os.chdir(data_path)
    g=file_list_EX[i]
    
    
    ##-----get angle names
    angle_Ex = return_value(g,'_Degree')
    Ex_Pol_array=np.append(Ex_Pol_array,angle_Ex)

    data_path =basefolder+g+'/pys'        
    file_list=get_file_list_sorted(data_path)
    if i==len(file_list_EX)-1:#do this for first dataset to make it stackable
        intensity_array,angle_array,v1_array,v1prime_array,v2_array=get_arrays(file_list,data_path)
    else:
        intensity_array1,angle_array1,v1_array1,v1prime_array1,v2_array1=get_arrays(file_list,data_path)
        intensity_array = np.vstack((intensity_array,intensity_array1))
        print 'current folder:',g
        print 'len angle:',len(angle_array), 'len angle1:',len(angle_array1)
        angle_array     = np.vstack((angle_array,angle_array1))
        v1_array        = np.vstack((v1_array,v1_array1))
        v1prime_array   = np.vstack((v1prime_array,v1prime_array1))
        v2_array        = np.vstack((v2_array,v2_array1))
        
    #------------------------

    i -=1


#--------Loop over first files-----------

    
#-----------------------------
#------Iterate over folders---


#-----------------------------------------------
#-----creating ouputfile------------------------
#df=pandas.DataFrame(np.transpose(intensity_array),index=wavelength,columns=angle_array)
#df.to_excel('Measurement Excitation 171 Degree 70K.xlsx',sheet_name='book1')
#dictToCsv(mydict,'First Measurement 5.5K.xlsx')#we dont use this because it is unsorted

#-----------------------------------------------
#-----Polar Plot------------------------
fig = plt.figure()
ax = fig.gca(projection='3d')
X,Y=np.meshgrid(angle_array, Ex_Pol_array)
surf=ax.plot_surface(X,Y,v1prime_array, cmap=cm.coolwarm, linewidth=1, antialiased=False)

ax.zaxis.set_major_locator(LinearLocator(10))
ax.zaxis.set_major_formatter(FormatStrFormatter('%.02f'))
fig.colorbar(surf, shrink=0.5, aspect=5)
plt.show(block=False)

#ax.grid(True)
#ax.set_title("V1 lines (maximum taken)", va='bottom')
#plt.legend()

#plt.savefig('test.png')
#plt.clf()

# plt.savefig('polarplot.png')
# plt.clf()
# #plt.show()
# #-----Polar Plot Normalized ------------------------
# ax2 = plt.subplot(111, projection='polar')
# ax2.plot(angle_array*np.pi/90.,v1_array/np.max(v1_array), color='r', linewidth=3, label='v1')
# ax2.plot(angle_array*np.pi/90.,v1prime_array/np.max(v1_array), color='b', linewidth=3,label='v1_prime')
# ax2.grid(True)
# ax2.set_title("V1 lines (maximum taken, Normalized)", va='bottom')
# plt.legend()
# plt.savefig('polarplot_normalized.png')
# plt.clf()
#plt.show()

#
print 'Excel File Created'
print 'Plots Created'
os.chdir(startfolder) 