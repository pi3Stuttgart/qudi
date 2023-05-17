import numpy as np
import os
import sys 
import own_fitlogic as fit
import matplotlib.pylab as plt

fitter=fit.FitLogic()
fitter.optimize_time=3
fitter.speedup=False

mod=fitter.make_n_gauss_function_with_offset(2)

direct=r"C:\Data\2023\05\20230509\ODMR"

files=os.listdir(direct)
data=[]
for fi in files:
    #print(fi)
    if "raw.dat" in fi:
        data.append(fi)


X=[]
Rs=[]
Ls=[]

dic={"tilt":1,"rot":3}
active="rot"# "rot" #"tilt" #

for i,fi in enumerate(data):
    dat=fi.split("_")
    if dat[1]=="-0.4":
        tr=dat[-4]
        variable=dat[dic[active]]
        if tr=="L": X.append(float(variable))
        Data=np.loadtxt(direct+"\\"+fi,delimiter="\t")
        init_guess=[[20,2530.5,1,20,2528.5,1,None],[20,2388.8,1,20,2391.2,1,None]][tr=="L"]
        #init_guess=[[20,2530,1,20,2528,1,None],[20,2389,1,20,2391,1,None]][tr=="L"]
        print(init_guess,tr)
        x=Data[:,1]
        y=Data[:,0]
        res=mod.fit(x,y,init_guess=init_guess)
        print(res)
        print(fi,i)
        [Rs,Ls][tr=="L"].append((res["params"][4]+res["params"][1])/2)
        #plt.figure(i)
        #plt.plot(x,y,x,mod(x,*res["params"]))

#plt.show()
Rs=np.asarray(Rs)
Ls=np.asarray(Ls)

def squared(x,a,b,c):
    return x**2*a+b*x+c

#x=np.arange(4,-5,-1)
x=np.array(X)[1:]
y=abs(Ls-Rs)[1:]
print(x,y)
res=fitter.fit(x_data=x,y_data=y,function=squared)
print(res)
print(-res.x[1]/2/res.x[0])
plt.plot(x,y,x,squared(x,*res.x))

plt.savefig('Bfield_alignment.png')
plt.show()
