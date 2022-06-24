# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type

from qutip import tensor, ket2dm, expect, jmat, Qobj
from .data_generation import DataGeneration
from .data_handling import PlotData
from qutip_enhanced import sequence_creator
from .qutip_enhanced import dim2spin, sort_eigenvalues_standard_basis
import qutip_enhanced.nv_hamilton
from collections import OrderedDict
import collections
from itertools import chain, combinations, product
import numpy as np
import numbers

import traceback
import sys


class NVHamFit14nParams():

    def __init__(self, diag=True):
        """

        :param diag: bool
            diagonalize hamiltonian or just take diagonal used for testing or algorithm speedup
        """
        self.diag = diag
        self.spin_name_list = ['e', '14n']
        self.transition_name_list = [['+1', '0', '-1'], ['+1', '0', '-1']]
        self.states_list = [range(len(i)) for i in self.transition_name_list]
        self.set_ntd()

    def nuclear_transition_name(self, transition):
        ms = self.transition_name_list[0][transition[0][0]]
        fsn = flipped_spin_numbers(transition)[0]
        nuc = self.spin_name_list[fsn]
        if ms == '0' and '13c' in nuc:
            return '13c ms0'
        else:
            if fsn == 1:
                if transition[0][1] == 0:  # initial transition is '+1'
                    mn = '+1'
                elif transition[1][1] == 2:  # initial transition is '0'
                    mn = '-1'
                nuc += mn
            return "{} ms{}".format(nuc, ms)

    def set_ntd(self):
        ntd = {}
        c13ms0_added = False
        for t in single_quantum_transitions_non_hf_spins(self.states_list, hf_spin_list=[0]):
            name = self.nuclear_transition_name(t)
            if name == '13c ms0':
                if c13ms0_added:
                    continue
                else:
                    c13ms0_added = True
            ntd[name] = t
        self.ntd = OrderedDict(ntd)

    def set_frequency_dict(self, fd):
        if type(fd) != OrderedDict:
            raise Exception('ERROR!')
        self.frequency_dict = fd
        self.transitions = [self.ntd[key] for key in self.frequency_dict]

    def nvham(self, magnetic_field, gamma, qp, hf_para_n, hf_perp_n):
        return qutip_enhanced.nv_hamilton.NVHam(
            magnet_field={'z': magnetic_field},
            electron_levels=[0, 1, 2],
            nitrogen_levels=[0, 1, 2],
            n_type='14n',
            gamma=gamma,
            qp=qp,
            hf_para_n=hf_para_n,
            hf_perp_n=hf_perp_n
        )

    def transition_frequencies(self, magnetic_field, transition_numbers, gamma, qp, hf_para_n, hf_perp_n):
        nvham = self.nvham(magnetic_field=magnetic_field, gamma=gamma, qp=qp, hf_para_n=hf_para_n, hf_perp_n=hf_perp_n)
        if self.diag:
            h_diag = sort_eigenvalues_standard_basis(nvham.dims, *nvham.h_nv.eigenstates()[::-1])
        else:
            print('Not diagonalizing, just taking diagonal.')
            h_diag = np.diag(nvham.h_nv.data.todense())
        f = []
        for i in transition_numbers:
            f.append(-get_transition_frequency(h_diag=h_diag, dims=nvham.dims, transition=self.transitions[i]))
        return f


def purity(dm):
    """should work for qudits also"""
    s = range(len(dm.dims[0]))
    comb = list(chain.from_iterable(combinations(s, r) for r in range(len(s) + 1)))[1:]
    return dict((i, ((dm.ptrace(i)) ** 2).tr()) for i in comb)


def measurement_result(dm, operator):
    return np.abs((operator.dag() * operator * dm).tr())


def test_states_single(dim, pure=False):
    m = (dim - 1.) / 2.
    out = dict()
    for axis in ['x', 'y', 'z']:
        out["s{}".format(axis)] = []
        for idx, state in enumerate(jmat(m, axis).eigenstates()[1][::-1]):
            if not pure:
                state = ket2dm(state)
            out["{}{}".format(axis, idx)] = state
            out["s{}".format(axis)].append(state)
        out["s{}".format(axis)] = sum(out["s{}".format(axis)])
        out["s{}".format(axis)] = out["s{}".format(axis)] / out["s{}".format(axis)].norm()
    return out


__TEST_STATES_SINGLE_PURE__ = dict([(dim, test_states_single(dim=dim, pure=True)) for dim in [2, 3]])
__TEST_STATES_SINGLE__ = dict([(dim, test_states_single(dim=dim, pure=False)) for dim in [2, 3]])


def chunk(s, size=2):
    return list(map(''.join, zip(*[iter(s)] * size)))


def test_states(dims=None, pure=False, **kwargs):
    """

    :param dims: e.g. [2,3]
    :param pure: boolean
    :param kwargs: either variable names_multi_list or names_multi_list_str must be given
        names_multi_list: e.g. [['z0', 'z1], ['x0', 'y2']], this will produce two teststates, each with total dim 2x3 (as given in dim=[2,3])
    :return:
    """
    if 'names_multi_list' in kwargs:
        names_multi_list = kwargs.get('names_multi_list')
        l_ok_list = [len(i) == len(dims) for i in names_multi_list]
        if not all(l_ok_list):  #:for i in names_multi_list:
            raise Exception('Error: {}, {}, {}, {}, {}'.format(len(dims), dims, names_multi_list, l_ok_list, [[len(i), i, len(dims)] for i in names_multi_list]))
    elif 'names_multi_list_str' in kwargs:
        nmls = kwargs.get('names_multi_list_str')
        names_multi_list = []
        for i in nmls:
            if type(i) != str:
                raise Exception('Error: each item of names_multi_list_str must be {} (is {})'.format(str, type(i)))
            if len(i) != 2 * len(dims):
                raise Exception("Error: {}, {}, {}, {}".format(dims, 2 * len(dims), i, len(i)))
            names_multi_list.append(chunk(i))
    else:
        raise Exception('Error: {}'.format(kwargs))
    out = collections.OrderedDict()
    for idx, names_multi in enumerate(names_multi_list):
        name_multi = "".join(names_multi)
        out[name_multi] = tensor(*[__TEST_STATES_SINGLE_PURE__[dim][name] for name, dim in zip(names_multi, dims)]).unit()
        if not pure:
            out[name_multi] = ket2dm(out[name_multi]).unit()
    return out


def propagate_test_states(gates, test_states):
    out = {}
    if type(test_states) is dict:
        for key, val in test_states.items():
            out[key] = gates * val * gates.dag()
    elif type(gates) is list:
        for key, val in enumerate(gates):
            out[key] = val * test_states * val.dag()
    return out


# def single_quantum_transition(states):
#     """
#     list of single quantum transitions. higher quantum number is always first item
#     """
#     out = []
#     for s in itertools.product(itertools.product(*states), itertools.product(*states)):
#         delta = np.array(s[0]) - np.array(s[1])
#         if sum(np.abs(delta) == 1) == 1 and sum(delta) == 1:
#             out.append([s[0], s[1]])
#     return out

def single_quantum_transition_hf_spins(states_list, hf_spin_list='all'):
    """
    :param states_list:
        example; states_list = [[0,1], [0,1], [0,1]] for e.g. two electron states [+1,0], two 14n states [+1,0], 13c
    :param hf_spin_list:
        example: hf_spin_list = [0]
        Gives all spins, that have a hyperfine coupling to multiple other spins and thus change their hyperfine frequencies
    :return:
        example: NOTE: only the electron transitions are listed, as only spin[0] is a hf_spin
        [[(0, 0, 0), (1, 0, 0)],
         [(0, 0, 1), (1, 0, 1)],
         [(0, 1, 0), (1, 1, 0)],
         [(0, 1, 1), (1, 1, 1)]]
    """
    if hf_spin_list is 'all':
        hf_spin_list = range(len(states_list))
    non_hf_spins = [i for i in range(len(states_list)) if i not in hf_spin_list]
    states_list_non_hf_spins = [state for idx, state in enumerate(states_list) if idx not in hf_spin_list]

    out = []
    for nhfl in product(*states_list_non_hf_spins):
        state_list_sub = states_list[:]
        for idx, state in zip(non_hf_spins, nhfl):
            state_list_sub[idx] = [state]
        for s in product(*state_list_sub):
            for sn in hf_spin_list:
                if s[sn] + 1 in state_list_sub[sn]:
                    ts = list(s)
                    ts[sn] += 1
                    out.append([s, tuple(ts)])
    return out


def single_quantum_transitions_non_hf_spins(states_list, hf_spin_list='all'):
    """
    :param states_list:
        example; states_list = [[0,1], [0,1], [0,1]] for e.g. two electron states [+1,0], two 14n states [+1,0], 13c
    :param hf_spin_list:
        example: hf_spin_list = [0]
        Gives all spins, that have a hyperfine coupling to multiple other spins and thus change their hyperfine frequencies
    :return:
        example: NOTE: only the electron transitions are listed, as only spin[0] is a hf_spin
    [[(0, 0, 0), (0, 1, 0)],
     [(0, 0, 0), (0, 0, 1)],
     [(1, 0, 0), (1, 1, 0)],
     [(1, 0, 0), (1, 0, 1)]]
    """
    if hf_spin_list is 'all':
        hf_spin_list = range(len(states_list))
    non_hf_spins = [i for i in range(len(states_list)) if i not in hf_spin_list]
    states_list_hf_spins = [states_list[i] for i in hf_spin_list]
    out = []
    for nhfl in product(*states_list_hf_spins):
        state_list_sub = states_list[:]
        for hf_spin, state in zip(hf_spin_list, nhfl):
            state_list_sub[hf_spin] = [state]
        for sn in non_hf_spins:
            for i in [k for k in non_hf_spins if k != sn]:
                state_list_sub[i] = [state_list_sub[i][0]]
            for s in product(*state_list_sub):
                if s[sn] + 1 in states_list[sn]:
                    ts = list(s)
                    ts[sn] += 1
                    out.append([s, tuple(ts)])
    return out


def flipped_spin_numbers(transition):
    """
    :param transition: example [(0, 0, 0), (0, 1, 0)]
    :return: int
        for above example, 1 is returned
    """
    l = []
    for i in range(len(transition[0])):
        if (transition[1][i] - transition[0][i]) == 1:
            l.append(i)
    return l


def single_quantum_transition(states_list, hf_spin_list='all'):
    return single_quantum_transition_hf_spins(states_list=states_list, hf_spin_list=hf_spin_list) + \
           single_quantum_transitions_non_hf_spins(states_list=states_list, hf_spin_list=hf_spin_list)


def state_num2name(state, name_list):
    return tuple([name_list[i][val] for i, val in enumerate(state)])


def state_name2num(state, name_list):
    return tuple([name_list[i].index(val) for i, val in enumerate(state)])


def state_num_name(state, name_list):
    if type(state) is list:
        st = type(state[0][0])
    else:
        st = type(state[0])
    if st == str:
        f = state_name2num
    else:
        f = state_num2name
    if type(state) is list:
        return [f(s, name_list) for s in state]
    else:
        return f(state, name_list)


def get_transition_frequency(**kwargs):
    if 'h' in kwargs:
        dims = kwargs['h'].dims[0]
        h_diag = kwargs['h'].diag()
    else:
        dims = kwargs['dims']
        h_diag = kwargs['h_diag']
    m_list = list(product(*[range(i) for i in dims]))

    def t(s0, s1):
        return h_diag[m_list.index(s1)] - h_diag[m_list.index(s0)]

    if 'transition' in kwargs:
        return t(*kwargs['transition'])
    if 's0' in kwargs and 's1' in kwargs:
        return t(kwargs['s0'], kwargs['s1'])
    else:
        if 'name_list' in kwargs:
            states_list_string = [(state_num_name(s[0], kwargs['name_list']), state_num_name(s[1], kwargs['name_list'])) for s in
                                  kwargs['states_list']]
        else:
            states_list_string = kwargs['states_list']
        return dict([(str(sstr), t(s[0], s[1])) for sstr, s in zip(states_list_string, kwargs.get('states_list'))])


class Simulate(DataGeneration):

    def __init__(self, gui=False, progress_bar=None, **kwargs):
        super(DataGeneration, self).__init__()
        self.parameters = kwargs.pop('parameters')
        self.times_fields_dict = self.get_times_fields_dict(kwargs.pop('times_fields_list'))
        self.section_dict = self.get_section_dict(self.times_fields_dict)
        self.ret_h_mhz = kwargs.pop('ret_h_mhz')
        self.dims = kwargs.pop('dims')
        self.L_Bc = [Qobj(i, dims=[self.dims, self.dims]) for i in kwargs.pop('L_Bc')]
        self.gui = gui
        self.pld = PlotData('analyze_pulse', gui=self.gui)
        self.pld.x_axis_parameter = 'to_bin'
        self.progress_bar = progress_bar
        self.number_of_simultaneous_measurements = self.calc_number_of_simultaneous_measurements()

    @staticmethod
    def get_times_fields_dict(times_fields_list):
        l = [i[0] for i in times_fields_list]
        if len(l) != len(set(l)):
            raise Exception('Duplicate keys!')
        else:
            return collections.OrderedDict(times_fields_list)

    @property
    def section_dict(self):
        return self._section_dict

    @section_dict.setter
    def section_dict(self, val):
        """

        :param val: collections.OrderedDict([(sectionname1, section1), (sectionname2, section2), ...])
            sectionname can be Qobj operator, integer (then it hast to be
        :return:
        """
        if any([i not in val.values() for i in self.parameters['to_bin']]):
            raise Exception("Some value in to_bin is not in section_dict")
        if len(val.keys()) != len(set(val.keys())):
            raise Exception('ERROR: {}'.format(val.keys()))
        self._section_dict = val

    @staticmethod
    def get_section_dict(times_fields_dict):
        section_length_list = []
        fields_list = []
        insert_operator_dict = collections.OrderedDict()
        for key, val in times_fields_dict.items():
            iodidx = np.cumsum(section_length_list)[-1] if len(section_length_list) > 0 else 0
            if isinstance(val, numbers.Number):
                insert_operator_dict[iodidx] = 'tba'
                section_length_list.append(val)
            elif isinstance(val, Qobj):
                insert_operator_dict[iodidx] = val
                section_length_list.append(1)
            else:
                section_length_list.append(len(val))
                fields_list.append(val)

        return collections.OrderedDict([(key, val) for key, val in zip(times_fields_dict.keys(), np.cumsum(section_length_list) - 1)])

    def calc_number_of_simultaneous_measurements(self):
        if 'initial_state' in self.parameters:
            f_initial_state = len(self.parameters['initial_state'])
        else:
            l = list()
            for key, val in self.parameters.items():
                if key.startswith('initial_state'):
                    l.append(len(val))
            f_initial_state = int(np.prod(l))
        if 'observation_type' in self.parameters:
            return int(np.product([len(i) for i in list(self.parameters.values())[list(self.parameters.keys()).index('observation_type'):]]) * f_initial_state)
        else:
            return len(self.parameters['to_bin']) * len(self.parameters['spin_num']) * len(self.parameters['axis']) * f_initial_state

    @property
    def observation_names(self):
        return ["value"]

    def update_progress(self):
        super(Simulate, self).update_progress()
        if self.progress_bar is None:
            print(self.progress)
        else:
            self.progress_bar.value = self.progress

    def detunings(self, iterator_df_row):
        return dict([(key, val) for key, val in iterator_df_row.items() if 'detuning' in key])

    def h_mhz_changed(self, iterator_df_changed_idx):
        changed = False
        if self.current_iterator_df_changes.loc[iterator_df_changed_idx, [cn for cn in self.data.parameter_names if '_detuning' in cn]].any():
            changed = True
        return changed

    def initial_state(self, _I_):
        if 'initial_state' in _I_:
            return _I_['initial_state']
        else:
            d = collections.OrderedDict()
            for key, val in _I_.items():
                if key.startswith('initial_state'):
                    d[int(key.replace('initial_state', ''))] = val
            return "".join(collections.OrderedDict(sorted(d.items())).values())

    def expect(self, _I_, pts):
        op = jmat(dim2spin(self.dims[_I_['spin_num']]), _I_['axis'])
        state = pts[0].ptrace(_I_['spin_num'])
        return expect(op, state)

    def probability(self, _I_, pts):
        id = [idx for idx, val in enumerate(chunk(_I_['measurement_operator'])) if val != 'nn']
        dim_sub = [self.dims[i] for i in id]
        mos_sub = [i for i in chunk(_I_['measurement_operator'])[id[0]:id[-1] + 1]]
        op = list(test_states(dims=dim_sub, pure=False, names_multi_list=[mos_sub]).values())[0]
        dm = pts[0].ptrace(id)
        return measurement_result(dm, op)

    def run(self, abort=None):
        self.init_run(init_from_file=None, iff=None)
        try:
            for idxo, _ in enumerate(self.iterator()):
                if abort is not None and abort.is_set(): break
                observation_dict_list = []
                for idx, _I_ in self.current_iterator_df.iterrows():
                    if self.h_mhz_changed(idx):
                        u_list_reduced, u_list_mult = self.generate_u_list_mult()
                    u_list_reduced, u_list_mult = self.f(u_list_reduced=u_list_reduced, u_list_mult=u_list_mult, idxo=idxo, idx=idx, _I_=_I_, abort=abort)
                    if abort is not None and abort.is_set(): break
                    ts = list(test_states(dims=self.dims, pure=False, names_multi_list_str=[self.initial_state(_I_)]).values())[0]
                    to_bin = list(self.section_dict.values()).index(_I_['to_bin'])
                    pts = propagate_test_states([u_list_mult[to_bin]], ts)
                    if _I_.get('observation_type', 'expect') == 'expect':
                        value = self.expect(_I_, pts)
                    elif _I_['observation_type'] == 'probability':
                        value = self.probability(_I_, pts)
                    elif _I_['observation_type'] == 'purity':
                        value = purity(pts[0])[tuple([int(i) for i in _I_['spin_nums']])]
                    else:
                        raise Exception('Error!')
                    observation_dict_list.append(collections.OrderedDict([('value', value)]))
                self.data.set_observations(observation_dict_list)
                if self.gui:
                    self.pld.new_data_arrived()
            self.pld.new_data_arrived()
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            self.state = 'idle'
            self.update_current_str()

    def generate_u_list_mult(self):
        h_mhz = self.ret_h_mhz(**self.detunings(self.current_iterator_df.iloc[0, :].to_dict()))
        u_list_reduced = []
        for key, val in self.times_fields_dict.items():
            if isinstance(val, numbers.Number):
                u_list_reduced.append('tba')
            elif isinstance(val, Qobj):
                u_list_reduced.append(val)
            else:
                u_list_reduced.append(
                    sequence_creator.unitary_propagator_list_mult(
                        sequence_creator.unitary_propagator_list(
                            h_mhz=h_mhz,
                            times=val[:, 0],
                            fields=val[:, 1:],
                            L_Bc=self.L_Bc
                        )
                    )[-1]
                )
        u_list_mult = sequence_creator.unitary_propagator_list_mult(u_list_reduced)
        return u_list_reduced, u_list_mult

    def f(self, u_list_reduced, u_list_mult, idxo, idx, _I_, abort):
        """
        :return: updated versions of u_list_reduced, u_list_mult
        """
        raise NotImplementedError
