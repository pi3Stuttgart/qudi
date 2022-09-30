#rev 1.2

import pickle #works better than cPickle
import cPickle
import pyfits
_file_mode_map = {'asc':'', 'bin':'b'}
_pickle_mode_map = {'asc':0, 'bin':1}

def writeDictToFile(dict, filename):
    if filename.find('.txt')!=-1 or filename.find('.asc')!=-1:
        d=dictToAscii(dict)
        stringToFile(d,filename)
    elif filename.find('.pys')!=-1: 
        mode='bin'
        fil = open(filename,'w'+_file_mode_map[mode])
        cPickle.dump(dict, fil, _pickle_mode_map[mode])
        fil.close()
    elif filename.find('.pyd')!=-1:
        mode='asc'
        fil = open(filename,'w'+_file_mode_map[mode])
        cPickle.dump(dict, fil, _pickle_mode_map[mode])
        fil.close()
    elif filename.find('.fits')!=-1:
 
        tbhdu = dictToFits(dict)
        tbhdu.writeto(filename)
    else:
        filename=filename+'.pys'
        mode='bin'
        fil = open(filename,'w'+_file_mode_map[mode])
        cPickle.dump(dict, fil, _pickle_mode_map[mode])
        fil.close()
            #interacts with __get_state__
def dictToFits(dict, keys=None):
    columns={}
    for key, value in dict.items():
        columns[keys]=pyfits.Column(name=key, format='E', array=value)
    cols=pyfits.ColDefs(columns)
    tbhdu=pyfits.new_table(cols)
    return tbhdu
  


def keysFromDict(dict, keys=None):
    """extract any number of keys from a dictionary"""
    d={}
    if keys==None:                     # return entire dict
        return dict
    else:
        if not hasattr(keys,'__iter__'): # only one key
            d[keys]=dict[keys]
        else:                           # tuple of keys 
            for key in keys:
                d[key]=dict[key]                 
    return d

def pickleFileToDict(path, keys=None):
    """(path, [(keys)]) Extracts the whole or a key of a dictionary from a pickled file"""
    dict={}
    try:
        fileh=open(path,'rU')
        try:
            dict=pickle.load(fileh)
        finally:
            fileh.close()
    except IOError:
        print 'Error importing data'
    d=KeysFromDict(dict,keys)
    return d

def blub(value):
    if hasattr(value,'__iter__'):
        blub(value.subitem)

def dictToAscii(dict, keys=None):
    """Converts a dictionary or parts of it to a string"""
    try:        # if there is a doc string put it up front
      datastring= '#__doc__\n'+dict['__doc__']+'\n'
      del dict['__doc__']
    except:
      datastring=''
    for key, value in dict.items():
        datastring+= '#'+key+'\n' # header for each key
        #blub(value)
        if hasattr(value,'__iter__'): # array? 
            if value!=[]:
                if hasattr(value[0],'__iter__'): # 2d array?
      
                       #2d array
                       for i in range(value.shape[0]):
                           for j in range(value.shape[1]):
                               datastring+=(str(value[i,j])+', ')
                               if j==value.shape[1]-1:
                                   datastring+='\n'
          
                else: 
                    #1d array
                    try:
                        n=value.shape[0]
                    except:
                        n=len(value)
                    for i in range(n):
                        datastring+=(str(value[i])+'\n')
            else:
                datastring=datastring+' '+'/n'
    
        else:
            # value no array
            datastring=datastring+str(value)+'\n'
    return datastring


#def write(item, string):
#    if hasattr(value,'__iter__'): # array?
#        for subitem in item:
#            write(subitem, string)
#    else: 
#        string=string+str(value)+'\n'
#    return string

def stringToFile(datastring, path):
    """writes datastring to file"""
    try:
        f=open(path,'w')
        try:
            f.write(datastring)
        finally:
            f.close()
    except IOError:
        print 'Error exporting data'
        return False
    return True

def pickleFileToAscFile(sourcefile, targetfile=None, keys=None):
  """dump pickle from pickled file to ascii file (source, [target], [(keys)])"""
  dict={}
  dict=PickleFile2Dict(sourcefile, keys)
  datastring=Dict2Ascii(dict, keys)
  if targetfile==None:
      String2File(datastring, sourcefile+'.asc')
  else:
      String2File(datastring, targetfile)

