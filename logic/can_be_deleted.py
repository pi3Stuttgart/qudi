from cmath import exp
from scipy.fft import fft, ifft,rfft
from scipy import signal
import numpy as np
from matplotlib.pylab import plt


def exp_sine(x,omega,phase,decay):
    return np.sin(omega*x+phase)*np.exp(-x/decay)
"""
x=np.linspace(-20,20,10000)
#x_FT=np.linspace(0,max(x)-min(x),len(x))

factor=(x[10]-x[0])/10
pos=200
print(factor)
x0=pos*factor
#FT_pos=30
#freq=FT_pos/factor
print(x0,x[pos])
f=exp_sine
params=(2,1,14)
y=f(x,*params)+(np.random.random(len(x))-0.5)*1

#y=np.sin(2*x)+np.sin(3*x)+np.sin(10*x)+np.sin(30*x)

sr=1/factor
X = fft(x)
N = len(X)
n = np.arange(N)
T = N/sr
freq = n/T
x_FT=freq

FTy=fft(y)
FTx=fft(x)

plt.plot(x,y)
plt.plot(x_FT/(factor*np.pi),FTy)
#plt.plot(FTx,FTy)

plt.show()
fty=signal.savgol_filter(FTy,int(0.1*len(FTy)/2)*2+1,3)
kwargs={"height":None, "threshold":None, "distance":None, "prominence":5, "width":5, "wlen":None, "rel_height":0.5, "plateau_size":None}
peaks=signal.find_peaks(fty,**kwargs)
print(peaks)
for peak in peaks[0][:20]:
    #print(peak)
    print(x_FT[peak]/factor/np.pi)

"""
# sampling rate
sr = 2000
# sampling interval
ts = 1.0/sr
t = np.arange(0,20,ts)

x=np.linspace(-20,20,10000)
factor=(x[10]-x[0])/10
sr=1/factor

f=exp_sine
params=(6,1,14)
y=f(x,*params)+(np.random.random(len(x))-0.5)*1

X = abs(rfft(y))
N = len(X)
n = np.arange(N)*np.pi
T = N/sr
freq = n/T
fty=signal.savgol_filter(X,51,3)
kwargs={"height":None, "threshold":None, "distance":None, "prominence":20, "width":1, "wlen":None, "rel_height":0.5, "plateau_size":None}
peaks=signal.find_peaks(fty,**kwargs)
print(peaks)
for peak in peaks[0][:20]:
    #print(peak)
    print(freq[peak])

plt.figure(figsize = (8, 6))
plt.plot(freq, X, 'r')
plt.plot(freq, fty, 'b')
plt.ylabel('Amplitude')

plt.show()
