import numpy as np






def logistic(x, g=1., k=1., f0=0.5):
	return float(g)/(1+np.exp(-1.*k*g*x)*(float(g)/float(f0)-1))

def logistic_k_smooth(g):
	return 4./np.power(g,2)

def logistic_max_speed(k=1, g=1):
	return float(k)*np.power(g,2)/4.


def logistic_k_from_speed(v, g=1):
	return 4.*v/np.power(g,2)