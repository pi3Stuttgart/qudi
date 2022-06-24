# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

from qutip import *


import scipy.linalg

import numpy as np
import os
import collections
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
import itertools
import zipfile
import copy
from . import coordinates
np.set_printoptions(suppress=True, linewidth=100000)

def save_qutip_enhanced(destination_dir):
    src = os.path.dirname(os.path.dirname(__file__))
    f = '{}/qutip_enhanced.zip'.format(destination_dir)
    if not os.path.isfile(f):
        zf = zipfile.ZipFile(f, 'a')
        for root, dirs, files in os.walk(src):
            # if (not any([i in root for i in ['__pycache__', 'awg_settings', 'currently_unused', ".idea", ".hg", 'UserScripts', 'log']])) or root.endswith('transition_tracker_log') or root.endswith('helpers'):
            if (not any([i in root for i in ['build']])):
                for file in files:
                    if any([file.endswith(i) for i in ['.py', '.dat', '.ui']]) and not file == 'setup.py':
                        zf.write(os.path.join(root, file), os.path.join(root.replace(os.path.commonprefix([root, src]), ""), file))
        zf.close()

class Eigenvector:
    def __init__(self, dims):
        """
        Eigenvalues are not sorted in any way which makes plotting or
        following special level at anticrossings difficult. This class follows energy levels
        according to their eigenvectors.
        For every newly calculated eigenvectors and eigenvalues the sort function must be called.
        -dims must be numpy array of system dimensions, e.g. np.array([3,3]) for electron + 14N

        """
        self.dims = np.array(dims)
        self.evecs_old = make_vector_basis(dims)
        self.idx = np.array(range(self.dims.prod()))
        self.evals_sorted_list = None

    def sort(self, evecs_new, evals_new):
        """
        keep order of eigenvalues by comparing the
        eigenvectors from former and current run
        -evecs_new is a numpy array of qutip eigenvectors in arbitrary order like given by evals, evec = Qobj.eigenstates()
        -evals_new is numpy array of eigenvalues like given by evals, evec = Qobj.eigenstates()
        """
        self.idx_new = copy.deepcopy(self.idx)
        for i in range(self.dims.prod()):
            for j in range(self.dims.prod()):
                if (self.evecs_old[i].trans() * evecs_new[j]).norm() >= 0.5 and (
                            self.evecs_old[1].trans() * evecs_new[j]).norm() <= 1.5:
                    self.idx_new[i] = j
                    break
                elif j == self.dims.prod() - 1:
                    raise Exception("No two orthonormal EV have been found. Try to make more steps. {}".format((self.evecs_old[i].trans() * evecs_new[j]).norm() ))
        self.evals_sorted = np.take(evals_new, self.idx_new)
        self.evecs_old = np.take(evecs_new, self.idx_new)
        if self.evals_sorted_list is None:
            self.evals_sorted_list = np.array([self.evals_sorted])
        else:
            self.evals_sorted_list = np.append(self.evals_sorted_list, np.array([self.evals_sorted]), axis=0)



# class Eigenvector:
#     def __init__(self, dims, track_evals=False):
#         """
#         Eigenvalues are not sorted in any way which makes plotting or
#         following special level at anticrossings difficult. This class follows energy levels
#         according to their eigenvectors.
#         For every newly calculated eigenvectors and eigenvalues the sort function must be called.
#         -dims must be numpy array of system dimensions, e.g. np.array([3,3]) for electron + 14N
#
#         """
#         self.dims = np.array(dims)
#         self.evecs_old = np.eye(self.dims.prod())
#         self.idx = np.arange(self.dims.prod())
#         self.track_evals = track_evals
#
#     def update_evals_sorted_list(self):
#         if self.track_evals:
#             if not hasattr(self, 'evals_sorted_list'):
#                 self.evals_sorted_list = np.array([self.evals_sorted])
#             else:
#                 self.evals_sorted_list = np.append(self.evals_sorted_list, np.array([self.evals_sorted]), axis=0)
#
#     def sort(self, evec_matrix_new, evals_new):
#         """
#         keep order of eigenvalues by comparing the
#         eigenvectors from former and current run
#         -evecs_new is a numpy array of qutip eigenvectors in arbitrary order like given by evals, evec = Qobj.eigenstates()
#         -evals_new is numpy array of eigenvalues like given by evals, evec = Qobj.eigenstates()
#         """
#         idx = []
#         for vold in self.evecs_old.T:
#             l = []
#             for vnew in evec_matrix_new.T:
#                 l.append(np.vdot(vold, vnew))
#             idx.append(np.array(l).argmax())
#         print(idx)
#         self.idx = idx
#         # self.idx = np.array(np.real(np.dot(self.evecs_old.conjugate().transpose(), evec_matrix_new)).argmax(axis=0))
#         self.evecs_old = evec_matrix_new[:, self.idx]
#         np.set_printoptions(precision=2)
#         self.evals_sorted = evals_new[self.idx]
#         self.update_evals_sorted_list()


def sort_eigenvalues_standard_basis(dims, evec, evals):
    ev = Eigenvector(dims=dims)
    ev.sort(evec, evals)
    return np.real(ev.evals_sorted)

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def draw(self, renderer):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        FancyArrowPatch.draw(self, renderer)


class Bloch(Bloch):

    def draw_arrow(self, rho, elev, azim, length=0.1, shorten_line_factor=0.98, n=100, arrowstyle="-|>", **kwargs):
        if not self.axes:
            raise Exception('For this functionality axes must be given to Bloch() upon instantiation')
        x, y, z = coordinates.sph2cart(rho, elev, azim)
        ahs = int(np.ceil(n * shorten_line_factor))
        self.axes.plot(x[:ahs], y[:ahs], z[:ahs], label='parametric curve', **kwargs)
        self.axes.add_artist(self.arrowhead(x, y, z, length=length, arrowstyle=arrowstyle, **kwargs))

    def arrowhead(self, x, y, z, length=0.1, arrowstyle="-|>", **kwargs):
        if not self.axes:
            raise Exception('For this functionality axes must be given to Bloch() upon instantiation')
        xyz = np.gradient(np.column_stack([x, y, z]))[0]
        iii = -1
        x1 = xyz[iii, 0]
        y1 = xyz[iii, 1]
        z1 = xyz[iii, 2]
        l = length
        a = Arrow3D([x[iii] - x1 * l, x[iii] + x1 * l], [y[iii] - y1 * l, y[iii] + y1 * l],
                    [z[iii] - z1 * l, z[iii] + z1 * l],
                    mutation_scale=20,
                    lw=3, arrowstyle=arrowstyle, **kwargs)
        return a


def make_vector_basis(dims):
    """

    :param dims: np.array
        e.g. [2,3] for system of two spins: spin 1/2. and spin 1
    :return: list of dims.prod() many Qobj vectors
        returns the standard basis for the system given by dims
    """
    return [state_number_qobj(dims, i) for i in state_number_enumerate(dims)]


def dim2spin(dims):
    """
    always returns numpy matrix
    """
    if type(dims) is list:
        raise Exception("Insert numpy array, not list!")
    spins = None
    if isinstance(dims, np.ndarray):
        if dims.ndim > 0:
            spins = (dims - 1) / 2.0
    else:
        spins = (dims - 1) / 2.0
    return spins


def spin2dim(spins):
    """
    always returns numpy matrix
    """
    if type(spins) is list:
        raise Exception("Insert numpy array, not list!")
    dims = None
    if isinstance(spins, np.ndarray):
        if spins.ndim > 0:
            dims = (2 * spins + 1).astype(np.int32, copy=False)
    else:
        dims = int(2 * spins + 1)
    return dims


def qsum(ql):
    """

    :param ql: list of Qobj
        all list elements must have same dimensions e.g [sigmax(), sigma(y)]
    :return: Qobj
        ql[0] + ql[1] + .. + ql[-1]
    """
    sum_ql = 0 * ql[0]
    for qobj in ql:
        sum_ql += qobj
    return sum_ql


def qmul(ql):
    sum_ql = ql[0]
    for qobj in ql[1:]:
        sum_ql *= qobj
    return sum_ql


def do_zero(h):
    dims = h.dims
    h = h.data.todense()
    d = np.diag(h) - h[0, 0]
    np.fill_diagonal(h, d)
    return Qobj(h, dims=dims)


# def get_sub_matrix(op, levels):
#     return op.eliminate_states([i for i in range(op.dims[0][0]) if i not in levels])

def get_rot_matrix(dim, rotation_axis=None, **kwargs):
    """
    :param dim: int
        dimensionality of rotated qubit
        example: 2
    :param rotation_axis: dict
        example: {'x': 1, 'y': 1}
    :param kwargs:
        a) transition, list/np.array
        b) rotated_levels, list/np.array
        example: rotated_levels = [0, 2]
    list/np.array
    :return:
    """
    ## generate rotation matrix for sublevels
    rotation_axis = coordinates.Coord().coord_unit(rotation_axis, 'cart')
    rotated_levels = kwargs.get('transition', kwargs.get('rotated_levels', range(dim)))
    dim_rot = len(rotated_levels)
    rot_mat = qsum([rotation_axis[axis_name] * jmat(dim2spin(dim_rot), axis_name) for axis_name in coordinates.Coord().cart_coord])
    ## expand rotation matrix to full size 'dim' of single qubit
    out = np.zeros([dim, dim], dtype=np.complex128)
    for idxrm0, idxe0 in zip(range(dim_rot), rotated_levels):
        for idxrm1, idxe1 in zip(range(dim_rot), rotated_levels):
            out[idxe0, idxe1] = rot_mat[idxrm0, idxrm1]
    return Qobj(out)

def get_rot_operator(dim, angle=np.pi / 2.0, **kwargs):
    rot_mat = get_rot_matrix(dim, **kwargs)
    U = (-1j * angle * rot_mat).expm()
    return U

def gate_expand_1toN_qudit(U, dims, target):
    return tensor([identity(dim0) for dim0 in dims[:target]] + [U] +
                  [identity(dim1) for dim1 in dims[target+1:]])

def extend_operator(dims, target_spin, operator, control_dict=None):

    control_dict = collections.OrderedDict() if control_dict is None else copy.deepcopy(control_dict)
    for idx, dim in enumerate(dims):
        if idx not in control_dict and idx != target_spin:
            control_dict[idx] = list(range(dim))
    control_dict = dict(sorted(control_dict.items()))
    if target_spin in control_dict:
        raise Exception('Error: rotated_spin must not be in control_dict!!\n{}, {}'.format(dims, control_dict))
    sl = ["".join(str(j) for j in i) for i in itertools.product(*control_dict.values())]
    slc = [i for i in ["".join(str(j) for j in i) for i in itertools.product(*[range(k) for idx, k in enumerate(dims) if idx != target_spin])] if i not in sl]
    out = []
    for l, operation in zip([sl, slc], [operator, qeye([dims[target_spin]])]):
        for sublevel in l:
            a = list(sublevel)
            a.insert(target_spin, 'c')
            sublevel = "".join(a)
            ol = []
            for idx, item in enumerate(sublevel):
                if item == 'c':
                    ol.append(operation)
                else:
                    ol.append(fock_dm(dims[idx], int(item)))
            out.append(tensor(ol))
    return qsum(out)

# def extend_operator(dims, target_spin, operator, control_dict=None):
#     """
#     - selective_to[0] names a list of spins. selective_to[1] gives the levels of spin i that the rotation should be selective on,
#     if a spin is omitted here in this dictionary, rotated_spin will be rotated in all spin states
#     example: given a system with three spins, spin 1, 1, 1/2.0, transition = [0,1], rotated spin = 1 and selective_to = {0:[1,2],2:[1]} will rotate the second spins transition 1 < - > 0,
#     if spin 0 is in spin states 1 or 2 but not if it is in spin state 0 and if spin 2 is in spin state 1 but not if it is in spin state 0
#     """
#     control_dict = {} if control_dict is None else copy.deepcopy(control_dict)
#     for idx, dim in enumerate(dims):
#         if idx not in control_dict and idx != target_spin:
#             control_dict[idx] = range(dim)
#     if target_spin in control_dict:
#         raise Exception('Error: rotated_spin must not be in control_dict!!\n{}, {}'.format(dims, control_dict))
#     control_dict_compl = {}
#     control_dict_all_levels = 0
#     for idx, val in control_dict.items():
#         if len(val) == 0 or len(val) > dims[idx]:
#             raise Exception('Error: {}, {}'.format(dims, control_dict))
#         if len(val) == dims[idx]:
#             control_dict_compl[idx] = range(dims[idx])
#             control_dict_all_levels += 1
#         else:
#             control_dict_compl[idx] = [k for k in range(dims[idx]) if k not in val]
#     out = []
#     for d, operation in zip([control_dict, control_dict_compl], [operator, qeye([dims[target_spin]])]):
#         for key in d:
#             for idx, item in enumerate(d[key]):
#                 d[key][idx] = fock_dm(dims[key], item)
#         d[target_spin] = [operation]  # rotate for the selective_to, perform qeye for selective_to_compl
#         d = collections.OrderedDict(sorted(d.items()))
#         out.append(qsum([tensor(*items) for items in itertools.product(*d.values())]))
#         if control_dict_all_levels == len(dims) - 1:
#             break
#     return qsum(out)


def get_rot_operator_all_spins(**kwargs):
    """
    - selective_to[0] names a list of spins. selective_to[1] gives the levels of spin i that the rotation should be selective on,
    if a spin is omitted here in this dictionary, rotated_spin will be rotated in all spin states
    example: given a system with three spins, spin 1, 1, 1/2.0, transition = [0,1], rotated spin = 1 and selective_to = {0:[1,2],2:[1]} will rotate the second spins transition 1 < - > 0,
    if spin 0 is in spin states 1 or 2 but not if it is in spin state 0 and if spin 2 is in spin state 1 but not if it is in spin state 0
    """
    if 'dims' in kwargs:
        dims = kwargs.pop('dims')
    elif 'dim' in kwargs:
        if 'selective_to' in kwargs:
            raise Exception('Error: {}'.format(kwargs))
        dims = [kwargs.pop('dim')]
    rotated_spin = kwargs.pop('rotated_spin', None)
    selective_to = kwargs.pop('selective_to', None)
    if rotated_spin is None:
        if len(dims) == 1:
            rotated_spin = 0
        else:
            raise Exception('If the total dimensionality is greater than 1 (dims={}), rotated_spin must be given.'.format(dims))
    if 'rot_op' in kwargs:
        operator = kwargs['rot_op']
    else:
        operator = get_rot_operator(dim=dims[rotated_spin], **kwargs)
    return extend_operator(dims=dims, target_spin=rotated_spin, control_dict=selective_to, operator=operator)


def get_rot_matrix_all_spins(*args, **kwargs):
    o = get_rot_operator_all_spins(*args, **kwargs)
    dims = o.dims
    return Qobj(scipy.linalg.logm(o.data.todense()), dims=dims) / np.pi * 1.j


def rotate(op, **kwargs):
    U = get_rot_operator_all_spins(op.dims[0], **kwargs)
    operator = U * op * U.dag()
    return operator

def hadamard_walsh(d):
    l = []
    for n in range(d):
        for m in range(d):
            l.append(np.exp(1j*2*np.pi*m*n/float(d))*(basis(d, m) * basis(d, n).dag()))
    return qsum(l)/np.sqrt(d)

chrestenson_gate = hadamard_walsh(3)

if __name__ == '__main__':
    import matplotlib.pyplot as plt

    rho0 = ket2dm(tensor(basis(2, 0), basis(2, 0)))


    # print qte.get_rot_operator_all_spins(dims=[2], rotation_axis={'y':1}, angle=np.pi/2.)

    def r(phi):
        rho = rotate(rho0, rotation_axis={'y': 1.}, rotated_spin=0, angle=np.pi / 2.)
        rho = rotate(rho, rotation_axis={'y': 1}, rotated_spin=1, angle=np.pi / 2.)
        rho = rotate(rho, rotation_axis={'z': 1}, rotated_spin=0, angle=phi)
        rho = rotate(rho, rotation_axis={'z': 1}, rotated_spin=1, angle=2 * phi)
        rho = rotate(rho, rotation_axis={'y': 1}, rotated_spin=1, angle=-np.pi / 2)
        rho = rotate(rho, rotation_axis={'z': 1}, rotated_spin=0, angle=-np.pi / 2., selective_to={1: [1]})
        rho = rotate(rho, rotation_axis={'y': 1}, rotated_spin=0, angle=-np.pi / 2)
        return rho


    cphase0 = get_rot_operator_all_spins(dims=[2, 2], rotation_axis={'z': 1}, rotated_spin=0, angle=np.pi / 2., selective_to={1: [0]})
    cphase1 = get_rot_operator_all_spins(dims=[2, 2], rotation_axis={'z': 1}, rotated_spin=0, angle=- np.pi / 2., selective_to={1: [1]})
    rotx = get_rot_operator_all_spins(dims=[2, 2], rotation_axis={'y': 1}, rotated_spin=1, angle=np.pi / 2.)
    print(rotx * cphase0 * cphase1 * rotx.dag())

    a = np.array([[0. - 1.j, 0. + 0.j, 0. + 0.j, 0. + 0.j],
                  [0. + 0.j, 0. - 1.j, 0. + 0.j, 0. + 0.j],
                  [0. + 0.j, 0. + 0.j, 0. + 1.j, 0. + 0.j],
                  [0. + 0., 0. + 0.j, 0. + 0.j, 0. + 1.j]])


# """
# ============
# Pgf Preamble
# ============
#
# """
# # -*- coding: utf-8 -*-
# from __future__ import (absolute_import, division, print_function,
#                         unicode_literals)
#
# import six
#
# import matplotlib as mpl
# mpl.use("pgf")
# pgf_with_custom_preamble = {
#     "pgf.rcfonts": False,    # don't setup fonts from rc parameters
# }
# mpl.rcParams.update(pgf_with_custom_preamble)
#
# import matplotlib.pyplot as plt
# plt.figure(figsize=(4.5, 2.5))
# plt.plot(range(5))
# # plt.xlabel("unicode text: я, ψ, €, ü, \\unitfrac[10]{°}{µm}")
# # plt.ylabel("\\XeLaTeX")
# # plt.legend([r"unicode math: $\lambda = \sum_0^{N}{p(i)$"])
# plt.tight_layout(.5)
#
# plt.savefig(r"D:\Dropbox\Dokumente\PI3\Thesis\phd-thesis\fig\nv_hybrid\pgf_preamble.pgf")
# plt.savefig(r"D:\Dropbox\Dokumente\PI3\Thesis\phd-thesis\fig\nv_hybrid\pgf_preamble.png")

# import matplotlib as mpl
# import matplotlib.pyplot as plt
# import numpy as np
#
# fig_size = (4.5, 2.5)
# params = {'backend': 'pgf',
#           'axes.labelsize': 12,
#           'text.fontsize': 12,
#           'legend.fontsize': 12,
#           'xtick.labelsize': 12,
#           'ytick.labelsize': 12,
#           'text.usetex': True,
#           'figure.figsize': fig_size}
# mpl.rcParams.update(params)
#
# x = np.linspace(0, 1)
# y = np.sin(4 * np.pi * x) * np.exp(-5 * x)
# plt.fill(x, y, 'r', label=r"$y=e^{-5x} \sin 4 \pi x$")
# plt.legend(loc='upper right')
# plt.grid(True)
# #plt.show()
# plt.savefig(r"D:\Dropbox\Dokumente\PI3\Thesis\phd-thesis\fig\nv_hybrid\pgf_preamble.pgf", bbox_inches='tight',pad_inches=0)

