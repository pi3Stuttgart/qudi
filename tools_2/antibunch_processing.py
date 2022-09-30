import cPickle, pylab, os
import matplotlib.pyplot as plt
import numpy as np
startfolder = os.getcwd() # at the end of script we will go back to there
basefolder= 'F:/Messdaten/2013-06-07/Autocorrelation/'
os.chdir(basefolder)
g='2013-06-07_CVD_1E16_2mW_660nm_675-60BP_800SP_after-fiber_808LP-before-APD_spot02-14.5kcts-Autocorrelation.pys'
pos = g.find('spot')
target = g[pos:pos+6]
f=open(g,'rb')
d=cPickle.load(f)
r = 0.00518
x = d['time_bins']
y = d['counts']
y1 = d['counts']*d['norm_factor']
y2 = (y1-(1-r))/r
"prepare outputfolder"
os.chdir(basefolder)
result_file = open(g+"-all-data.txt", "w")
result_file.write('timedelay counts normalized signal'+"\n")
result_file.write('ns cts unitless unitless'+"\n")

for a,phi in enumerate(x):
	line=str(phi)+' '+str(y[a])+' '+str(y1[a])+' '+str(y2[a])+"\n"
	result_file.write(line)
result_file.close()
    
figure = pylab.figure()
plotty = figure.add_subplot(111)
pylab.title('Autocorrelation '+str(target), fontsize='x-large')
pylab.plot(x,y2, 'bo', linewidth=2.0)
plotty = figure.add_subplot(111)
plotty.legend('Autocorrelation ','lower center', bbox_to_anchor=(0.5,-0.5), shadow=True)
plotty.set_xlabel(u'time delay [ns]')
plotty.set_ylabel(u'second order correlation')

pylab.savefig(g[:(len(g)-4)]+'_BG-corrected.png')
figure.show()
os.chdir(startfolder)