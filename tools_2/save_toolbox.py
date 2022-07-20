import os, cPickle, numpy as np
import logging



def CreateFolder(path):
    
    path_splitted=path.split('\\')
    temp_path=''
    
    for i,path in enumerate(path_splitted):             
        temp_path = temp_path+path_splitted[i]+'\\'
        try:
            os.stat(temp_path)        
        except:
            try:
                os.mkdir(temp_path)
            except:
                print temp_path,' could not be created, please create manually.'
