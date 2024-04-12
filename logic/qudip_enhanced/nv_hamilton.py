# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import numpy as np
from scipy.constants import mu_0, hbar
import sys
np.set_printoptions(suppress=True, linewidth=500, threshold=sys.maxsize)#np.nan)
from logic.qudip_enhanced.qutip_enhanced import *
print('I am here)')
gamma = {'e': -2.0028 * 1.6021766208e-19 / (4 * np.pi * 9.10938356e-31) * 1e-6,
         '13c': 10.705, '29si':-8.465,
         '14n': +3.0766,
         '15n': -4.3156}


def hft_13c_dd(location, gamman=None):
    """
    Calculates 13C hyperfine tensor for pure dipolar coupling at position location.
    location must be inserted according to module coordinates.
    For very close nuclei this gets wrong as contact interaction then plays a role.

    :param location: dic
    example: {'rho': 1e-9, 'elev': np.pi / 2, 'azim': 0}
    :return: hyperfine tensor in amtrix notation
    """
    gamman = gamma['13c'] if gamman is None else gamman
    loc_cart = coordinates.Coord().coord_unit(location, 'cart')
    rho = coordinates.Coord().coord(location, 'sph')['rho']
    x, y, z = [loc_cart[i] for i in ['x', 'y', 'z']]
    prefactor = mu_0 / (2.0) * hbar * gamma['e'] * 1e6 * gamman * 1e6 / rho ** 3  # given in Hertz
    prefactor_mhz = prefactor * 1e-6  # given in MHz
    mat = np.matrix([[1 - 3 * x * x, -3 * x * y, -3 * x * z],
                     [-3 * x * y, 1 - 3 * y * y, -3 * y * z],
                     [-3 * x * z, -3 * y * z, 1 - 3 * z * z]])
    return prefactor_mhz * mat


class NVHam:
    """
    Hamiltonian describing a single NV + nuclear spins.

    ALWAYS USE NUMPY ARRAYS, DONT USE LISTS.
    
    All frequencies are in [MHz]. Magnetic field in [Tesla].

    Example: NV with N14, one 13C at location x = 1e-9 meters; Magnetic field is 0.5 Tesla in z, 1 gauss in y, only electron spin states ms = 0 and ms = -1 are considered
        ham = NVHam(magnet_field = {'z':0.5, 'y':0.0001}, n_type = 'n14', electron_levels = [0,1]) #create base nv hamiltonian
        ham.add_spin(ham.hft_13c_dd(location = {'x': 1e-9}), ham.h_13c()) #add 13C nuclear spin with pure dipolar coupling
        evals, evecs = ham.h_nv.eigenstates() #calculate eigenvalues and eigenstates
    """

    def __init__(self, magnet_field=None, n_type=None, electron_levels=None, nitrogen_levels=None, **kwargs):
        """

        :param magnet_field: dict
            The applied external magnetic field in [Tesla] must be given as dictionary like described in module coordinates. Cartesian and Spherical coordinates possible.
            example: magnet_field={'z': 0.1}
        :param n_type: str
            The type of nitrogen atom : '14n', '15n', None
        :param electron_levels: list
            Order of states is ms = +1, 0, -1
            The sublevels of the electron spins are chosen with electron_levels, which can be e.g. [1,2], [0,1,2]
            but not [0], [1] or [2].
        :param nitrogen_levels: list
            Order of states is mn = +1, 0, -1
            Same as electron_levels but for the nitrogen spin.
        :param D: float
            Zero field splitting, default 2870 MHz.
        """
        self.j = {'14n': 1, '15n': .5, 'e': 1.5, '13c': .5, '29si':0.5}
        self._gamma = gamma  # gyromagnetic ratios given in 1/2pi MHz/T, i.e. f = gamma*B
        self._qp = {'14n': -4.945745, '15n': 0.0, '13c': 0, '29si':0}
        self._hf_para_n = {'14n': -2.165, '15n': +3.03}
        self._hf_perp_n = {'14n': -2.7, '15n': +3.65}
        self.D = 34.95
        self.dims = [4]# 3 for NV was
        self.magnet_field_cart = coordinates.Coord().coord(magnet_field, 'cart')  # magnet field in cartesian coordinates
        self.n_type = n_type #'14n', '15n', None
        self.nitrogen_levels = nitrogen_levels
        self.electron_levels = [0,1,2,3] if electron_levels is None else electron_levels
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.set_h_nv()

    @property
    def n_type(self):
        return self._n_type

    @n_type.setter
    def n_type(self, val):
        if val in ['14n', '15n', None]:
            self._n_type = val
        else:
            raise Exception("Chosen 'n_type' is not allowed.")

    @property
    def nitrogen_dim(self):
        if self.n_type == '14n':
            return 3
        elif self.n_type == '15n':
            return 2

    @property
    def gamma(self):
        return self._gamma

    @gamma.setter
    def gamma(self, val):
        if type(val) is dict:
            self._gamma.update(val)
        else:
            raise Exception('Error: {}'.format(val))

    @property
    def qp(self):
        return self._qp

    @qp.setter
    def qp(self, val):
        if type(val) is dict:
            self._qp.update(val)
        else:
            raise Exception('Error: {}'.format(val))

    @property
    def hf_para_n(self):
        return self._hf_para_n

    @hf_para_n.setter
    def hf_para_n(self, val):
        if type(val) is dict:
            self._hf_para_n.update(val)
        else:
            raise Exception('Error: {}'.format(val))

    @property
    def hf_perp_n(self):
        return self._hf_perp_n

    @hf_perp_n.setter
    def hf_perp_n(self, val):
        if type(val) is dict:
            self._hf_perp_n.update(val)
        else:
            raise Exception('Error: {}'.format(val))

    @property
    def nitrogen_levels(self):
        return self._nitrogen_levels

    @nitrogen_levels.setter
    def nitrogen_levels(self, val):
        if self.n_type is not None:
            fl = range(int(2 * self.j[self.n_type] + 1))
            if val is None:
                self._nitrogen_levels = fl
            elif set(fl).issuperset(set(val)):
                self._nitrogen_levels = val
            else:
                raise Exception("Chosen 'nitrogen_levels must be a list, e.g. nitrogen_levels = [1,2] for n_type='14n'.")

    def calc_zeeman(self, gamma, j):
        """

        :param gamma: float
            gyromagnetic ratio of the subject spin
        :param j: float
            total spin quantum number, i.e. 1/2, 1, 3/2, ..
        :return: zeeman splitting. However be careful with gyromagnetic ratios of electron spin. Use their negative
        """
        return  qsum([gamma * self.magnet_field_cart[axis] * jmat(j, axis) for axis in coordinates.Coord().cart_coord])

    def h_electron(self):
        """
        calculate electron hamilton matrix with zerofield and zeeman splitting. 
        Final size of h_electron depends on self.electron_levels. 
        """
        self.h_ezfs = self.D * jmat(self.j['e'], 'z') ** 2
        self.h_eze = self.calc_zeeman(gamma=self.gamma['e'], j=self.j['e'])
        self.h_e = self.h_ezfs + self.h_eze
        return self.h_e

    def h_nitrogen(self):
        """
        calculate nitrogen hamilton operator with quadrupol, hyperfine and zeeman. 
        Final size of h_nitrogen depends on self.nitrogen_levels
        """
        self.h_nqp = self.qp[self.n_type] * jmat(self.j[self.n_type], 'z') ** 2
        self.h_nze = self.calc_zeeman(self.gamma['14n'], self.j[self.n_type])
        self.h_n = self.h_nqp + self.h_nze
        return self.h_n

    def hft_nitrogen(self):
        """
        Gives the nitrogen hyperfine tensor according to self.get_nitrogen_params()
        """
        return np.diag([self.hf_perp_n[self.n_type], self.hf_perp_n[self.n_type], self.hf_para_n[self.n_type]])

    def h_13c(self):
        """
        calculate 13C hamilton matrix with with zeeman splitting. This 
        Final size of h_electron depends on self.electron_levels. 
        """
        return self.calc_zeeman(self.gamma['13c'], 1 / 2.0)
    def h_29si(self):
        """
        calculate 13C hamilton matrix with with zeeman splitting. This
        Final size of h_electron depends on self.electron_levels.
        """
        return self.calc_zeeman(self.gamma['29si'], 1 / 2.0)

    @staticmethod
    def hft_13c_dd(*args, **kwargs):
        return hft_13c_dd(*args, **kwargs)

    def h_hf(self, hft, nsd, nslvl_l):
        """
        Calculates the hyperfine hamiltonian between electron spin and a spin 'nsq'.
        'hft' is the hyperfine tensor for the interaction, e.g. calculated from hft_nitrogen or hft_13c or inserted freely
        'nsq' is the spin that is added, i.e. nsq = 1/2.0 for a 13c
        'nslvl_l' nuclear_spin_lvl_list (i guess that's what this variable name means)
        """
        h_hf = 0 * qeye(list(np.append(self.h_nv.dims[0], len(nslvl_l))))
        eye_mat = None if self.h_nv.dims[0][1:] == [] else qeye(self.h_nv.dims[0][1:])  # unity matrix for spinsnot involved in HF
        for i in range(3): #why is here 3?
            electron = jmat(self.spins[0], coordinates.Coord().cart_coord[i]).extract_states(self.spin_levels[0])
            for j in range(3): #why is here 3?
                new = jmat(dim2spin(nsd), coordinates.Coord().cart_coord[j]).extract_states(nslvl_l)
                tmp = tensor(electron, eye_mat, new) if eye_mat is not None else tensor(electron, new)
                h_hf = h_hf + hft[i, j] * tmp
        return h_hf

    def set_h_nv(self):
        """
        calculates the base hamiltonian with parameters specified at instantiation
        """
        self.spins = np.array([1.5])
        self.spin_levels = [self.electron_levels]
        self.h_nv = self.h_electron().extract_states(self.electron_levels)
        if self.n_type is not None:
            self.add_spin(hft=self.hft_nitrogen(), h_ns=self.h_nitrogen(), nslvl_l=self.nitrogen_levels)

    def add_spin(self, hft, h_ns, nslvl_l):
        """

        :param hft: np.array
            hyperfine tensor for the interaction between electron spin and the spin that should be added. might be taken
            from self.hft_nitrogen() or self.hft_13c_dd()
        :param h_ns: Qobj operator
            hamilton operator of the spin that should be added. ns stands for 'nsq' might be taken from
            self.h_nitrogen() or self.h_13c()
        :param nslvl_l: list
            spin levels of 'h_ns' that should be considered. For a 13C this will usually be [0,1].
        :return:
        """

        nsd = h_ns.shape[0]  # multiplicity of new spin
        nsq = dim2spin(nsd)  # quantum number of new spin
        self.dims.append(int(h_ns.shape[0]))
        h_nv_ext = tensor(self.h_nv,
                          qeye(len(nslvl_l)))  # nv hamilton operator extended with qeye of dimension of new spin
        h_ns_ext = tensor(qeye(self.h_nv.dims[0]), h_ns.extract_states(nslvl_l))  # extended hamilton operator of the new spin
        h_hf = self.h_hf(hft, nsd, nslvl_l)  # new spin - electron hyperfine interaction tensor
        self.h_nv = h_nv_ext + h_ns_ext + h_hf
        self.spins = np.append(self.spins, nsq)
        self.spin_levels.append(nslvl_l)
        return self.h_nv


if __name__ == '__main__':
    e = Eigenvector(dims=[2, 3])
    B_list = np.linspace(0.1, 0.105, 50)
    h_nv = NVHam(magnet_field={'z': 0.0}, n_type='14n', nitrogen_levels=[0, 1, 2], electron_levels=[1, 2])
    for i in B_list:
        h_nv = NVHam(magnet_field={'z': i}, n_type='14n', nitrogen_levels=[0, 1, 2], electron_levels=[1, 2]).h_nv
        e.sort(h_nv.eigenstates()[1], h_nv.eigenenergies())
    import matplotlib.pyplot as plt
    plt.plot(B_list, e.evals_sorted_list)

    # def h_nv_rotating_frame(self, rotation_operator):
    #     U = (1j * rotation_operator * 2 * pi * t).expm()
    #     Ht = (1j*rotation_operator)
    #     return

    # C13_hyperfine_tensor = nvham.hft_13c_dd(location={'rho': 0.155e-9, 'elev': np.pi/2.})
    # C13414_ht = np.matrix([[0, 0, 0],
    #                           [0, 0, 0],
    #                           [0, 0, 0.414]])
    # C1390_ht = np.matrix([[0, 0, 0],
    #                       [0, 0, 0],
    #                       [0, 0, 0.089]])
    # nvham.add_spin(C13414_ht, nvham.h_13c(), [0, 1])
    # nvham.add_spin(C1390_ht, nvham.h_13c(), [0, 1])
    # print nvham.h_nv
    # nvham = NVHam(magnet_field={'z': 0.55}, n_type='14n', nitrogen_levels=[0, 1, 2], electron_levels=[0, 1, 2])
    # C13_hyperfine_tensor = nvham.hft_13c_dd(location={'rho': 0.155e-9, 'elev': np.pi/2.})
    # print C13_hyperfine_tensor
    # nvham.add_spin(C13_hyperfine_tensor, nvham.h_13c(), [0, 1])
    # print nvham.h_nv
    # a = nvham.h_hf(nvham.hft_nitrogen(), nvham.h_nitrogen().shape[0], nvham.nitrogen_levels)
    # C13_hyperfine_tensor = ham.hft_13c_dd(location={'rho': 0.458e-9, 'elev': pi/ 2., 'azim': 0.0})
    # ham.add_spin(C13_hyperfine_tensor, ham.h_13c(), [0, 1])
    # print ham.h_nv[0,0] - ham.h_nv[1,1]
    # print C13_hyperfine_tensor
    # C13_hamilton = ham.h_13c()
    # ham.add_spin(C13_hyperfine_tensor, C13_hamilton, nslvl_l=[0, 1])

    # print ham.hft_13c_dd(location={'rho': 1e-9, 'elev': np.pi / 2.})
    # # print ham.h_nv
    # print abs(ham.h_nv[0, 0] - ham.h_nv[1, 1]) - abs(ham.h_nv[2, 2] - ham.h_nv[3, 3])
    # print abs(ham.h_nv[4, 4] - ham.h_nv[5, 5]) - abs(ham.h_nv[2, 2] - ham.h_nv[3, 3])

    # ham = NVHam(magnet_field={'z': 0.52373915}, electron_levels=[0, 1, 2], n_type='14n', nitrogen_levels=[0, 1, 2])
    # print ham.h_nv
    # print ham.h_nv[7, 7] - ham.h_nv[6, 6]
    # print ham.h_nv[1, 1] - ham.h_nv[0, 0]
    # ham.add_spin(ham.hft_13c_dd(location = {'x': 1e-9}), ham.h_13c())
    # evals, evecs = ham.h_nv.eigenstates()
    #     print evals
    # ev = Eigenvector(dims=np.array([4,3]))
    # mag_z_l = np.linspace(0, 0.1028, 30)
    # ham = NVHam(magnet_field = {'z':0.55}, n_type='14', electron_levels=[0,1,2])
    # print ham.h_nv
    #    for mag_z in mag_z_l:
    #        ham = NVHam(magnet_field = {'rho': mag_z, 'elev': np.pi/2.}, n_type = '14n', electron_levels=[1,2], nitrogen_levels=[0, 1, 2])
    # #        ham.add_spin(ham.h_13c(), ham.hft_13c_dd())
    #        evals, evecs = ham.h_nv.eigenstates()
    #        ev.sort(evecs, evals)
    #    figure(1)
    #    colors = ['b', 'r', 'g']  # list of colors for plotting
    #    for n in range(prod(ev.dims)):
    #        plot(mag_z_l, (ev.evals_sorted_list[:, n]), lw=2)
    #    show()
