# coding=utf-8
from __future__ import print_function, absolute_import, division
from imp import reload
__metaclass__ = type

from qutip_enhanced import *
import numpy as np
import itertools
import os
import datetime

"""
calculate 2d density matrix of two spins 
-input file must be a text file that contains the measurement outcome for 
all four states (for the given caluclation it was 414 and 13c90kHz (-,+): [++, +-, -+, --] or [1,2,3,4])
the result is given as the expectation value of being in that state [0..1,0..1,0..1,0..1].
for the tomography result however it is necessary to have the expectation value
-measurement directions: ['zz','zx','zy','yz','xz','yy','yx','xy','xx']
"""


class TomoToDM:
    def __init__(self, source_format='state_pop', **kwargs):
        """Processes tomography measurement data.

            Parameters
            ----------
            source_format : string
                gives the type of tomography data outputted by the measurement
                allowed values are 
                    'state_pop' : population of the whole state vector 
                    'qubit_pop' : populations of each single qubit
                    'qubit_expt' : expectation value of each qubit
                
            kwargs: 
                meas_basis_list : list of strings
                    optional to 'pulse_dir_list' 
                    the basis of each tomography measurement in the right order. 
                    e.g. meas_basis_list = ['zz','zx','zy','yz','xz','yy','yx','xy','xx']
                
                pulse_dir_list : list of strings
                    optional to 'meas_basis_list'
                    the pulses done for each tomography measurement in the right order
                    e.g. pulse_basis_list = ['zz','zy','zx','xz','yz','xx','xy','yx','yy']
                
                filename : string
                    filename of the text file containing the tomography data. 
                    
                    Example : 
                    -------
                    for source_format = 'state_pop' and two qubits
                        
                    tomography	result 1	result 2	result 3	result 4	events 1	events 2	events 3	events 4
                    0	0.283088235294	0.191176470588	0.257352941176	0.268382352941	272	272	272	272
                    1	0.370786516854	0.498127340824	0.063670411985	0.0674157303371	267	267	267	267
                    2	0.338028169014	0.19014084507	0.242957746479	0.228873239437	284	284	284	284
                    3	0.449511400651	0.0228013029316	0.514657980456	0.0130293159609	307	307	307	307
                    4	0.25468164794	0.224719101124	0.2734082397	0.247191011236	267	267	267	267
                    5	0.838383838384	0.016835016835	0.127946127946	0.016835016835	297	297	297	297
                    6	0.410358565737	0.486055776892	0.0756972111554	0.0278884462151	251	251	251	251
                    7	0.528138528139	0.0519480519481	0.398268398268	0.021645021645	231	231	231	231
                    8	0.253846153846	0.234615384615	0.261538461538	0.25	260	260	260	260                       
                        
            Usable Class Attributes
            --------
            
            UNFINISHED
            
        
            """

        if kwargs.has_key('meas_basis_list'):
            self.meas_basis_list = kwargs['meas_basis_list']
        elif kwargs.has_key('pulse_dir_list'):
            self.meas_basis_list = self.pdl2mbl(kwargs['pulse_dir_list'])
        else:
            raise Exception('No pulse_dir_list or meas_basis_list given.')
        self.num_qubits = int(np.sqrt((len(self.meas_basis_list) - 1) / 2.0))
        if kwargs.has_key('filename'):
            self.meas_data = self.read_file(kwargs['filename'])
        elif kwargs.has_key('meas_data'):
            self.meas_data = self.format_data(kwargs['meas_data'])
        else:
            raise Exception("Neither 'filename' nor 'meas_data' have been given.")
        if not len(self.meas_data) == len(self.meas_basis_list):
            raise Exception('Given data does not match given meas_basis_list.')
        if kwargs.has_key('param_string') and kwargs.has_key('param_names'):
            self.add_pd(param_names, param_string)
        self.get_ob()
        self.get_ev()
        self.calc_rho()

    def pdl2mbl(self, pdl):
        """
        takes list of strings and replaces 'x' by 'y' and 'y' by '-x'
        
        Parameters
        ----------
        
        xy_list : list of strings
            e.g. ['x', 'xyz', 'abc']Bei Dr. House kannst noch was lernen:

        Returns
        -------
        yx_list : list of strings
            any 'x' of each string in xy_list will be replaced by an 'y', any 'y' in xy_list will be replaces by an 'x'
            e.g. ['y', 'yxz', 'abc']
        """
        pdl = [i.replace('x', '2').replace('y', '-1').replace('-x', '-2').replace('-y', '1') for i in pdl]
        return [i.replace('1', 'x').replace('2', 'y') for i in pdl]

    def read_file(self, filename):
        """
        returns a variable with the relevant content of a text file with filename 'filename'
        
        Parameters
        ----------        
        
        filename : string
            file must contain one head line plus one line for every item in self.meas_basis_list. 
            The first row is the number of the measurement, the following 2**self.num_qubits rows are the actual data
        
        Returns
        -------
        
        meas_data : dict
            key : string
                measurement directions according to self.meas_basis_list
            val : ndarray.float
                populations, i.e. density matrix diagonals, i.e. 2**self.num_qubits values
        
        """
        f = open(filename, 'r')
        data = f.read().split('\n')[1:]
        f.close()
        meas_data = dict([[self.meas_basis_list[i], np.array(dat.split('\t')[1:2 ** self.num_qubits + 1]).astype(float)] for i, dat in enumerate(data)])
        return meas_data

    def format_data(self, data):
        meas_data = dict([[md, data[i]] for i, md in enumerate(self.meas_basis_list)])
        return meas_data

    def get_ob(self):
        """
        sets the class variable 'ob', a multi qubit operator basis'
        
        Usable Class Attributes
        --------
        ob : dict
            key : string
                names for the operator basis elements, e.g.  '1x', 'zz', ...
            val : qubit operator
                elements of the operator basis, e.g. tensor(qeye(2), sigmax()), tensor(sigmaz(),sigmaz()), ...
    
        """
        sqob = {'1': qeye(2), 'x': sigmax(), '-x': -sigmax(), 'y': sigmay(), '-y': -sigmay(), 'z': sigmaz()}  # single qubit operator basis
        mqob_str = itertools.product(*[sqob.keys() for i in range(self.num_qubits)])
        mqob = dict([[''.join(j), tensor([sqob[i] for i in j])] for j in mqob_str])
        self.ob = mqob

    def get_ev(self):
        """
        extracts the measured expectation values for the 
        basis states (given in self.ob) from self.meas_data
        
        Usable Class Attributes
        --------
        ev : dict
            key : string
                names for the operator basis elements, e.g.  '1x', 'zz', ...
            val : float
                measured expectation values for the basis states in self.ob, 
    
        """
        self.ev = {}
        for key in self.ob:
            ob_key = key.replace('-x', 'z').replace('-y', 'z').replace('x', 'z').replace('y', 'z')
            a = self.ob[ob_key].diag()
            meas_data_key = key.replace('1', 'z')
            b = self.meas_data.get(meas_data_key, 0)
            self.ev[key] = sum(a * b)

    def calc_rho(self):
        """Calculates density matrix of compound system from expectation values of single qubits

        Paramters
        ---------
        UNFINISHED
        """
        self.rho = 1. / (2 ** self.num_qubits) * qsum([self.ob[key] * self.ev[key] for key in self.ob])

    def add_pd(self, param_names, param_string):
        """
        Extracts parameters given in param_names from param_string

        Paramters
        ---------
        param_names : list of strings
            e.g. ['number', 'tau']
        
        param_string : string
            multiple parameters must be sparated by '_'
            e.g. 'number15_tau3.8'
        
        Usable Class Attributes
        --------
        pd : dict
            key : string
                name of the parameter
            val : string
                value of the parameter
            e.g. {'number': '15', 'tau': '3.8'} 
        """
        tmp = [x for x in param_string.split('_')]
        self.pd = {}
        for i, vn in enumerate(param_names):
            for part in tmp:
                if vn in part:
                    self.pd[vn] = part.replace(vn, '')


def mp2c(mag, phase):
    mag = np.array(mag) / np.linalg.norm(mag)
    return [m * np.exp(1j * phase[i]) for i, m in enumerate(mag)]


def aqpsi(**kwargs):
    """
    Takes a 2**n dimensional complex coefficient vector and returns a QM state vector psi.
    
    Parameters
    ----------
    
    c : list of complex values or numpy array
        List of 2**n(natural number) complex coefficients

    x : dictionary
        keys : str
            'mag', 'phase
        values : list of float
            mag : 0..1
            phase : 0..2*pi
        
    Returns
    -------
    
    psi : Qobj
        A quantum mechanical state vector.
    """
    if kwargs.has_key('x'):
        x = kwargs['x']
        c = mp2c(x['mag'], x['phase'])
    elif kwargs.has_key('c'):
        c = np.array(kwargs['c']) / np.linalg.norm(kwargs['c'])
    nq = int(np.round(np.log2(len(c)), 0))
    bl = list(itertools.product(*[[0, 1] for i in range(nq)]))
    b = [tensor([basis(2, bwi) for bwi in bwi_tuple]) for bwi_tuple in bl]
    psi = qsum([c[i] * b[i] for i in range(len(c))])
    return psi


def aqrho(**kwargs):
    """
    Takes a 2**n dimensional complex coefficient vector and returns a density matrix rho.
    
    Parameters
    ----------
    b 
    c : list of complex values or numpy array
        List of 2**n(natural number) complex coefficients
    
    Returns
    -------
    
    rho : Qobj
        Density matrix.
    """
    return ket2dm(aqpsi(**kwargs))


def target_state(tau, tau_cnot=0.0):
    """
    this one should be right for interaction entangle
    """
    tau_eff = tau + tau_cnot
    #    print tau_eff
    phi = -0.0887 / 2 * tau_eff
    p0 = 0.5 + phi
    p1 = 0.75 - phi
    p2 = 0.25
    p3 = 0.5
    phase = 2 * np.pi * np.array([p0, p1, p2, p3]) - p0
    mag = [.5, .5, .5, .5]
    c = mp2c(mag, phase)
    return {'c': [mag, phase], 'rho': aqrho(c=c)}


if __name__ == '__main__':
    meas_type = 'ie_nm1c1390'
    if True:
        target_folder = 'D:/data/NuclearOps/%s' % meas_type
    elif True:
        target_folder = os.getcwd() + '/interaction_entangle2'

    time_bounds = [datetime.datetime.strptime(strtime, '%Y%m%d-h%Hm%Ms%S') for
                   strtime in ['20140508-h11m24s39', '20140512-h21m04s32']]
    if meas_type == 'one_qubit_tomo':
        param_names = ['nuc', 'amp', 'pi2', 'phase', 'atp']
        pdl = ['z', 'x', 'y']
    elif meas_type == 'ie_nm1c1390':
        param_names = ['pi214n', 'pi213c90', 'cnot1', 'tau', 'cnot2']
        pdl = ['zz', 'xz', 'yz', 'zx', 'zy', 'xx', 'xy', 'yx', 'yy']
    elif meas_type == 'entangle_2_13c':
        param_names = 000
        pdl = ['zz', 'xz', 'yz', 'zx', 'zy', 'xx', 'xy', 'yx', 'yy']

    data_l = []
    fidelities = []

    for offset in [0.5 / 1.192]:
        sum_fid = []
        for i, directory in enumerate(os.listdir(target_folder)):
            param_string = directory[18 + 1 + len(meas_type):]
            fil = '%s/%s/%s_result.dat' % (target_folder, directory, directory)
            date = datetime.datetime.strptime(directory[:18], '%Y%m%d-h%Hm%Ms%S')
            if date < time_bounds[0] or date > time_bounds[1]:
                continue
            data = TomoToDM(source_format='state_pop', filename=fil, pulse_dir_list=pdl, param_names=param_names, param_string=param_string)
            # select desired parameters
            p = data.pd
            print(p)
            if p['pi214n'] == '0' and p['pi213c90'] == '0' and p['cnot1'] == '0' and p['cnot2'] == '0':
                f = fidelity(data.rho, ket2dm(tensor(basis(2, 0), basis(2, 0))))
            elif p['pi214n'] == '1' and p['pi213c90'] == '1' and p['cnot1'] == '1' and p['cnot2'] == '1':
                f = fidelity(data.rho, target_state(float(data.pd['tau']), offset)['rho'])
            elif p['pi214n'] == '1' and p['pi213c90'] == '1' and p['cnot1'] == '0' and p['cnot2'] == '0':
                phase = 2 * np.pi * np.array([0, 0.25, 0.25, 0.5])
                mag = [.5, .5, .5, .5]
                c = mp2c(mag, phase)
                print(aqpsi(c=c))
                print(aqrho(c=c))
            #            print ts.data.todense()
            #            print data.rho
            #            f = fidelity(data.rho, ts)
            print(f)
            #            data.f = f
            #            data_l.append(data)
            #            sum_fid.append(f)
            #        fidelities.append([offset, sum(sum_fid)/8.0])

            #    fidelities = np.array(fidelities)
            #    import matplotlib.pyplot as plt
            #
            #    x = fidelities[:,0]
            #    y = fidelities[:,1]
            #    plt.plot(x, y)
            #    plt.show()







            # def find_state_optimize(method, x0 = None, **kwargs):
            #
            #    def fun(x, opt = True):
            #
            #        mag = x[0:len(x)/2]/np.linalg.norm(x[0:len(x)/2])
            #        if mag[0] < 0:
            #            mag = np.array(mag)*-1
            #        phase = np.fmod(np.array([2*np.pi if i==0 else i for i in x[len(x)/2:]]), 2*np.pi)
            #        phase = phase - phase[0]
            #        c =  mp2c(mag, phase)
            #        fid = fidelity(self.rho, self.aqrho(c))
            #        if opt == True:
            #            return 1 - fid
            #        else:
            #            return {'fid': fid, 'x': [mag, phase], 'c': c}
            #    nip =  2*2**self.num_qubits#number of independent parameters, including global phase and normalization
            #    if method == 'trymp':
            #        mag_list = itertools.product(*[[1] for i in range(nip/2)])
            #        phase_list = itertools.product(*[np.arange(0,2,0.1)*np.pi for i in range(nip/2)])
            #        coeff_list = list(itertools.product(*[mag_list,phase_list]))
            #        coeff_list = [x for x in coeff_list if x[1][0] == 0]
            #        coeff_list = [x for x in coeff_list if not x[0] == tuple([0 for i in range(nip/2)])]
            #        coeff_list = [x for x in coeff_list if all([x[0][j]==0 and x[1][j]==0 or x[0][j]!=0for j in range(0,len(x[0]))])]
            #        ret = {'fid':0}
            #        for i,x in enumerate(coeff_list):
            #            x = x[0] + x[1]
            #            if 1 - fun(x) > ret['fid']:
            #                ret = fun(x, opt = False)
            #        return ret
            #    if method == 'nelder-mead':
            #        res = minimize(fun, x0, method='Nelder-Mead')
            #        return fun(res['x'], opt = False)
            #            data.trymp = data.find_state_optimize('trymp')
            #
            #            print data.trymp['c']
            #            print data.trymp['fid']
            #            fidelity(data.rho, rho_dest)
            #            data_l.append(data)

            #            barchart([0,1,2,3], [0,1,2,3], data.rho.data.todense())
            #            x = target_state(float(p['tau']), dur_cnot_mus = (float(p['cnot1']) + float(p['cnot2']))*1/1.192)
            #            rho_target = data.aqrho(data.mp2c(x[0], x[1]))
            #            print fidelity(data.rho, rho_target)
            #            data.trymp = data.find_state_optimize('trymp') #optimize
            #            print
            #            data.neldermead = data.find_state_optimize('nelder-mead', x0 = np.concatenate([data.trymp['x'][0], data.trymp['x'][1]])) #optimize
            #            data.p = p
            #
            #    fil = open('2014-02-13_14n90trynealdermead', 'w')
            #    pickle.dump(data_l, fil)
            #    fil.close()

            #        meas_data = []
            #        for b in pdl:
            #            rhob = rho
            #            for j,d in enumerate(b):
            #                if d == 'z':
            #                    axis = {'z':1}
            #                    angle = 0
            #                elif d == 'x':
            #                    axis = {'x':+1}
            #                    angle = np.pi/2.
            #                elif d == 'y':
            #                    axis = {'y':-1}
            #                    angle = np.pi/2.
            #                rhob = qte.rotate(rhob, rotation_axis = axis, angle = angle, rotated_spin = j)
            #            meas_data.append(rhob.diag())
            #        data = TomoToDM(source_format = 'state_pop', meas_data = meas_data, pulse_dir_list = pdl)
            #        data.calc_rho()
            #        print fidelity(data.rho_yawang(), rho)
            #        print fidelity(data.rho,rho)

            #        print fidelity(data.rho_yawang(), rho)


            #    var_names = ['pi214n', 'pi213c90','cnot1','tau','cnot2',]
            ##    var_names = ['nuc','pi2','phase','atp']
            #    max_fid_minimize = []
            #    max_fid = []
            #    max_fid_pure = []
            #    max_fid_coeff2 = []
            #    max_fid_brute = []
            #
            #    for i, directory in enumerate(os.listdir(target_folder)):
            #        fil = target_folder+'\\' +directory+'\\'+directory + '_result.dat'
            #        p = get_param_dict(var_names, directory[44:])
            #        if p['pi214n'] == '1' and p['pi213c90'] == '1'and p['cnot1'] == '0' and p['cnot2'] == '0' and p['tau'] == '0':
            #            print fil
            #            print pdl
            #            data = TomoToDM(source_format = 'state_pop', filename = fil, pulse_dir_list = pdl)
            #            data.calc_rho()
            #            ryw = data.rho_yawang()
            #            print fidelity(data.rho, ryw)
            #            ret = data.fs_try(at = 'coeff')
            #            print data.rho
            #            tmp = data.find_state_brute()
            #            tmp['params'] = p
            #            max_fid_brute.append(tmp)


            # BASINHOPPING





            #            tmp['params'] = p
            #            print data.rho
            #            print tmp
            #            print data.aqrho(tmp['c'])
            #        if p['pi214n'] == '1' and p['pi213c90'] == '1' and p['cnot1'] == '0' and p['cnot2'] == '0' and p['tau'] == '0':
            #            data = TomoToDM(source_format = 'state_pop', filename = fil, pulse_dir_list = pdl)
            #            data.calc_rho()
            #            tmp = data.find_state_coeff2()

            #            max_fid_coeff2.append(tmp)
            #            tmp = data.find_pure_state()
            #            tmp['params'] = data.get_param_dict(var_names, param_string)
            #            print data.rho.diag()
            #            max_fid_pure.append(tmp)
            #    pickle.dump(max_fid_pure, open('var_max_fid_pure', 'w'))
            #        max_fid_minimize.append(tmp)
            #        tmp = data.find_state_coeff()
            #        tmp['params'] = data.get_param_dict(var_names, param_string)
            #        print tmp
            #        max_fid.append(tmp)
            #    pickle.dump(max_fid_minimize, open('var_max_fid_minimize_ext', 'w'))
            #        for c in coeff_list:
            #            fid.append(fidelity(self.rho, self.aqrho(c)))
            #        return {'c': coeff_list[np.argmax(fid)], 'fid': max(fid)}
            #
            #
            #
            #    def find_pure_state2(self):
            #        def fun(x, opt = True):
            #            c =  self.mp2c(x[0:len(x)/2], x[len(x)/2:])
            #            test_rho = self.aqrho()
            #
            #            f = 1 - fidelity(self.rho, self.aqrho(c))
            #            td = tracedist(test_rho,self.rho)
            #            #diff_sum
            #            difference_sum = 0
            #            sq_op_b = {'x': sigmax(), 'y': sigmay(), 'z': sigmaz()} #single qubit operator basis
            #            for bs in self.meas_basis_list:
            #                dl = list(bs)
            #                for i, string in enumerate(dl):
            #                    difference_sum += abs(self.qe[bs][i] - expect(sq_op_b[string], self.rho.ptrace(i)))**2
            #
            #            if opt == True:
            #                return f
            #            else:
            #                return {'fid': 1-f, 'c': c}
            #
            #        nip = 2*2**self.num_qubits - 2 #number of independent parameters
            #        bnds = [(0,1) for i in range(nip/2)] + [(0,2*np.pi) for i in range(nip/2,nip)]
            #
            #        opt_dict = minimize(fun, [0,0,0,0,0,0], method='Anneal', bounds=bnds, constraints = const)
            #        return fun(opt_dict['x'], opt = False)
            #
            #
            #    def find_state_coeff_minimize(self):
            #        def fun(x):
            #            c = [x[0]] + [x[i]*np.exp(1j*x[i+1]) for i in range(1,len(x),2)]
            #            return 1 - fidelity(self.aqrho(c), self.rho)
            #        num_params = 2*2**self.num_qubits - 1 #num_qubits magnitudes, num_qubits - 1 phases
            #
            #        res_dict = minimize(fun, [-1,0,0,0,0,0,0], method='Anneal')
            #        mag = res_dict['x'][0:num_params:2]
            #        mag = mag/np.linalg.norm(mag)
            #        phase = res_dict['x'][1:num_params:2]
            #        phase = np.mod(phase, 2*np.pi)
            #        return {'mag': np.around(mag, 2), 'phase': np.around(phase, 2), 'fid': 1-res_dict['fun']}
            #            #diff_sum
            #            difference_sum = 0
            #            sq_op_b = {'x': sigmax(), 'y': sigmay(), 'z': sigmaz()} #single qubit operator basis
            #            for bs in self.meas_basis_list:
            #                dl = list(bs)
            #                for i, string in enumerate(dl):
            #                    difference_sum += abs(self.qe[bs][i] - expect(sq_op_b[string], self.rho.ptrace(i)))**2
            #
            #    def find_pure_state(self):
            #        def fun(x, minimize = True):
            #            c = [1-np.linalg.norm(x[0:len(x)/2])] + [x[i]* np.exp(1j*x[i+1]) for i in range(0,len(x),2)]
            #            test_rho = self.aqrho(c)
            #
            #            #diff_sum
            #            difference_sum = 0
            #            sq_op_b = {'x': sigmax(), 'y': sigmay(), 'z': sigmaz()} #single qubit operator basis
            #            for bs in self.meas_basis_list:
            #                dl = list(bs)
            #                for i, string in enumerate(dl):
            #                    difference_sum += abs(self.qe[bs][i] - expect(sq_op_b[string], self.rho.ptrace(i)))**2
            #
            #            f = 1 - fidelity(test_rho, self.rho)
            #            td = tracedist(test_rho,self.rho)
            #
            #            if minimize == True:
            #                return f
            #            else:
            #                return {'c': c, 'fidelity': fidelity(test_rho, self.rho)}
            #
            #        nump = 2*2**self.num_qubits - 2 #num_qubits magnitudes, num_qubits - 1 phases
            #        bnds = [(0,1) for i in range(nump/2)] + [(0,2*np.pi) for i in range(nump/2,nump)]
            #        const = ({'type': 'ineq', 'fun' : lambda x: np.linalg.norm(x[0:nump/2]) <= 1})
            #        opt_dict = minimize(fun, [-1,0,0,0,0,0], method='SLSQP ', bounds=bnds, constraints = const)
            #        import pdb; pdb.set_trace()
            #        return fun(opt_dict['x'], minimize = False)
