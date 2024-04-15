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
def sort_by_prominence(find_peaks_result):
    peaks=find_peaks_result
    prom=peaks[1]["prominences"]
    indexes=prom.argsort()[::-1]
    sorted_peaks=peaks[0][indexes]
    return sorted_peaks


def parse(tokens):
    global i
    global args
    token=tokens.pop(0)
    print(token)
    print(tokens)
    if token=='+':
            return parse(tokens)+parse(tokens)
    elif token=='-':
            return parse(tokens)-parse(tokens)
    elif token=='*':
            return parse(tokens)*parse(tokens)
    elif token=='/':
            return parse(tokens)/parse(tokens)
    else:
            # must be just a function
            print(args)
            arguments=args[:i]
            args=args[i:]
            i+=1
            return token(*arguments)

def f(x):
    return x

def g(x,y):
    return x+y

def h(x,y,z):
    return x+y+z

i=1
args=(1,1,3,1,3,1,1,2)

expression=["*", "+", f,g, "*", h,g]
res=parse(expression)
print(res)

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
y=f(x,*params)+(np.random.random(len(x))-0.5)*1 + 4*np.sin(20*x)

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

s_peaks=sort_by_prominence(peaks)
print(s_peaks)

for peak in s_peaks[:20]:
    #print(peak)
    print(freq[peak])


plt.figure(figsize = (8, 6))
plt.plot(freq, X, 'r')
plt.plot(freq, fty, 'b')
plt.ylabel('Amplitude')

plt.show()"""
