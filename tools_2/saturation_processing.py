import cPickle, pylab, os
import matplotlib.pyplot as plt
import numpy as np

startfolder = os.getcwd() # at the end of script we will go back to there
rootfolder = 'D:/data/'
datefolder = 'D:/data/2013-09-23/'
samplefolder = datefolder+'CVD_1E13/'
basefolder= samplefolder+'saturation/'
LaserPowerFolder= datefolder+'Laser Power/'
SignalData= basefolder+'Data'
BGData = basefolder+'BG'
finalfolder= basefolder

"""open  laser power data"""
LaserPowerData='2013-09-23_Laser-Power.pys'
lp=LaserPowerFolder+LaserPowerData
open_lp=open(lp,'rb')
pickeled_lp=cPickle.load(open_lp)
"""prepare the laser power data"""
voltage = pickeled_lp['voltage']
laser_power = pickeled_lp['power']

counts = 'rate' # for saturation
#x-axis = 'voltage'
#counts = counts # for polarization
#x-axis = 'angle'
    
    

"""Open all saturation data and put them into a list"""
os.chdir(SignalData)
path = os.getcwd()
liste = os.listdir(path)

os.chdir(BGData)
pathBG = os.getcwd()
listeBG = os.listdir(pathBG)

"""now create empty arrays, that all data from different spots can be plotted together at the end"""
intensityArray=np.array(())
BGArray=np.array(())
BGcorrectedArray=np.array(())
StoBGArray=np.array(())
targetArray = np.array(())



i=len(liste)-1
while i >= 0:
    os.chdir(SignalData)
    g=liste[i]
    pos = g.find('spot')
    target = g[pos:pos+6]
    gBG=g[:(len(g)-4)]+'_BG'+'.pys'#define the BG label here
    
    try:
        f=open(g,'rb')
        d=cPickle.load(f)
        print 'successfully opened Signal'
        
    except:
        print 'file couldnt be opened or pickled'
        i = i-1
                  
    
    try:
        #y = d['counts']
        intensity= (d[counts])
    except:
        print 'data (intensity) not available in file'+str(g)
    
    
    try:
        iBG=listeBG.index(gBG)
        os.chdir(BGData)
        gBG=listeBG[iBG]
        
    
        try:
            
            fBG=open(gBG,'rb')
            dBG=cPickle.load(fBG)
        except:
            print 'file couldnt be opened or pickled'
            i = i-1
            
        try:
        #y = d['counts']
           #y= x-(dBG[counts]/1000)
            BGcorrected= intensity-(dBG[counts])
            BG = (dBG[counts])
            StoBG = BGcorrected/(dBG[counts])
            RhoSqu=(BGcorrected/intensity)**2
            print 'i :',i
            """now create the arrays where all data is sorted into BGcorrected,BG and StoBG"""
            if i==len(liste)-1:#do this for the first data set to make them stackable
                BGcorrectedArray = BGcorrected
                BGArray = BG
                StoBGArray = StoBG
                targetArray = target
            else:
                
                BGcorrectedArray = np.vstack((BGcorrectedArray,BGcorrected))
                BGArray = np.vstack((BGArray,BG))
                StoBGArray  = np.vstack((StoBGArray,StoBG))
                targetArray= np.vstack((targetArray,target))
        except:
            print 'data (intensity) not available in file'+str(g)
            
    except:
        print 'no BG data found for file:'+g
        
     

        
      
    try:
        os.chdir(finalfolder)
       # np.savetxt(g+'BG+SignaltoBG.txt', np.transpose((BG,StoBG)))
        #print g,gBG
        
        "prepare outputfolder"
        try:
            result_file = open(g+"-all-data.txt", "w")
            result_file.write('voltage power signal BG signal-BG S/B RhoSqu'+"\n")
            result_file.write('degree mW cts cts cts unitless unitless'+"\n")
        except: 
            print 'could not write file'
        for a,phi in enumerate(voltage):
            line=str(phi)+' '+str(laser_power[a])+' '+str(intensity[a])+' '+str(BG[a])+' '+str(BGcorrected[a])+' '+str(StoBG[a])+' '+str(RhoSqu[a])+"\n"
            result_file.write(line)
        result_file.close()
        
        "Create Plot"
        figure = pylab.figure()
        plotty = figure.add_subplot(111)
        pylab.title('Saturation '+str(target), fontsize='x-large')
        pylab.plot(laser_power,intensity, 'black', linewidth=2.0)
        pylab.plot(laser_power,BG, 'r', linewidth=2.0)
        pylab.plot(laser_power,BGcorrected, 'b', linewidth=2.0)
        plotty = figure.add_subplot(111)
        plotty.legend('Saturation ','lower center', bbox_to_anchor=(0.5,-0.5), shadow=True)
        plotty.set_xlabel(u'Opt. Power [mW]')
        plotty.set_ylabel(u'Countrate [cts]')

        pylab.savefig(g[:(len(g)-4)]+'_Plot.png')
        
        figure2 = pylab.figure()
        plotty2 = figure2.add_subplot(111)
        pylab.title('Signal to BG '+str(target), fontsize='x-large')
        pylab.plot(laser_power,StoBG, 'black', linewidth=2.0)
        plotty2 = figure.add_subplot(111)
        plotty2.legend('Signal to BG ','lower center', bbox_to_anchor=(0.5,-0.5), shadow=True)
        plotty2.set_xlabel(u'Opt. Power [mW]')
        plotty2.set_ylabel(u'Signal to BG')

        pylab.savefig(g[:(len(g)-4)]+'_StoBG.png')
        #figure.show()
        i = i-1
        
    except:
        i = i-1
        print 'NO PROCESSED DATA OUTPUT -  CHECK CODE OR RAW FILES'

else:
    
    
    os.chdir(finalfolder)
    targetlist=''
    unitlist=''
    for i,target in enumerate(targetArray):
        targetlist=targetlist+targetArray[i][0]+' '
        unitlist = unitlist+'arb.u. '
   
    """Signal to BG"""
    "prepare outputfolder"
    try:
        result_file = open('StoBG'+"-all-data.txt", "w")
        line = 'voltage power '+str(targetlist)
        result_file.write(line+"\n")
        line = 'Volt mW '+str(unitlist+"\n")
                
        result_file.write(line)
    except: 
        print 'could not write file'
    
    """ PROCESS DATA"""
    entries=np.arange(0,len(StoBGArray),1)
    contents = np.arange(0,len(StoBGArray[len(StoBGArray)-len(entries)]),1)
    
    for index2,content in enumerate(contents):
        line=str(voltage[index2])+' '+str(laser_power[index2])+' '
        
        for index,entry in enumerate(entries):                       
            line = line+str(StoBGArray[entry][index2])+' '     
        line = line + "\n"
        result_file.write(line)
    result_file.close()
    
    """save all BG-Data in one txt.file"""
    "prepare outputfolder"
    try:
        result_file = open('BG'+"-all-data.txt", "w")
        line = 'voltage power '+str(targetlist)
        result_file.write(line+"\n")
        line = 'Volt mW '+str(unitlist+"\n")
                
        result_file.write(line)
    except: 
        print 'could not write file'
    
    """ PROCESS DATA"""
    entries=np.arange(0,len(BGArray),1)
    contents = np.arange(0,len(BGArray[len(BGArray)-len(entries)]),1)
    
    for index2,content in enumerate(contents):
        line=str(voltage[index2])+' '+str(laser_power[index2])+' '
        
        for index,entry in enumerate(entries):                       
            line = line+str(BGArray[entry][index2])+' '     
        line = line + "\n"
        result_file.write(line)
    result_file.close()
    
    """save all BGcorrected-Data in one txt.file"""
    "prepare outputfolder"
    try:
        result_file = open('BGcorrected'+"-all-data.txt", "w")
        line = 'voltage power '+str(targetlist)
        result_file.write(line+"\n")
        line = 'Volt mW '+str(unitlist+"\n")
                
        result_file.write(line)
    except: 
        print 'could not write file'
    
    """ PROCESS DATA"""
    entries=np.arange(0,len(BGcorrectedArray),1)
    contents = np.arange(0,len(BGcorrectedArray[len(BGcorrectedArray)-len(entries)]),1)
    
    for index2,content in enumerate(contents):
        line=str(voltage[index2])+' '+str(laser_power[index2])+' '
        
        for index,entry in enumerate(entries):                       
            line = line+str(BGcorrectedArray[entry][index2])+' '     
        line = line + "\n"
        result_file.write(line)
    result_file.close()

        
    
    os.chdir(startfolder) # so that you can run the script again
    print 'done'  