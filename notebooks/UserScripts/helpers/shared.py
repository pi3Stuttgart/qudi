from __future__ import print_function, absolute_import, division
from imp import reload

import numpy as np
import threading

__BASE_TAU__ = 2*192/12e3
#
# ddp = dict()
# ddp['fid'] = np.array([])
# ddp['hahn'] =np.array([0.0])
# ddp['xy4'] = np.array([0.0, np.pi / 2., 0.0, np.pi / 2.])
# ddp['xy8'] = np.concatenate([ddp['xy4'], ddp['xy4'][::-1]])
# ddp['xy16'] = np.concatenate([ddp['xy8'], ddp['xy8'] + np.pi])
# ddp['knill_pi'] = np.array([np.pi / 6., 0, np.pi / 2., 0, np.pi / 6.])
# ddp['kdd4'] = np.concatenate([phasexy + ddp['knill_pi'] for phasexy in ddp['xy4']])
# ddp['kdd8'] = np.concatenate([phasexy + ddp['knill_pi'] for phasexy in ddp['xy8']])
# ddp['kdd16'] = np.concatenate([phasexy + ddp['knill_pi'] for phasexy in ddp['xy16']])
# __PHASES_DD__ = ddp
#
# class DDParameters():
#
#     def __init__(self, name, total_tau, rabi_period):
#         self.name = name
#         self.total_tau = total_tau
#         self.rabi_period = rabi_period
#
#     @property
#     def phases(self):
#         name = self.name
#         if name[-6:] == '_uhrig' in name:
#             name = name[:-6]
#         if name[:4] == 'cpmg':
#            return np.zeros(int(name[4:]))
#         elif name in __PHASES_DD__:
#             return __PHASES_DD__[name]
#         else:
#             raise Exception("dynamical decoupling name {} not recognized".format(name))
#     @property
#     def number_of_pi_pulses(self):
#         return len(self.phases)
#
#     @property
#     def number_of_pulses(self):
#         return self.number_of_pi_pulses + 2
#
#     @property
#     def uhrig_pulse_positions_normalized(self):
#         return np.sin(np.pi*np.arange(self.number_of_pulses)/(2*self.number_of_pulses - 2))**2
#
#     @property
#     def uhrig_taus_normalized(self):
#         return np.diff(self.uhrig_pulse_positions_normalized)
#
#     @property
#     def uhrig_pulse_positions(self):
#         return self.total_tau*self.uhrig_pulse_positions_normalized
#
#     @property
#     def uhrig_taus(self):
#       return self.total_tau*self.uhrig_taus_normalized
#
#     @property
#     def tau_list(self):
#         name = self.name
#         if name[-6:] == '_uhrig' in name:
#             return self.uhrig_taus
#         elif name in __PHASES_DD__ or 'cpmg' in name:
#             tau = self.total_tau/(2*self.number_of_pi_pulses)
#             return [tau] + [2*tau for i in range(self.number_of_pi_pulses - 1)] + [tau]
#         else:
#             raise Exception('dynamical decoupling name not recognized')
#
#     @property
#     def eff_pulse_dur_waiting_time(self):
#         return np.concatenate([[3/8.*self.rabi_period], 0.5*self.rabi_period*np.ones(self.number_of_pi_pulses), [3/8.*self.rabi_period]]) #effective duration of pi pulse for each waiting time. The effective phase evolution time during the pi/2 pulse is taken as half of the pulse duration
#
#     @property
#     def minimum_total_tau(self):
#         return self.eff_pulse_dur_waiting_time[0]/self.uhrig_taus_normalized[0]
#
#     @property
#     def effective_durations_dd(self):
#         tau_list = self.tau_list
#         if self.minimum_total_tau > self.total_tau:
#             raise Exception('Waiting times smaller than zero are not allowed. '
#                             'Total tau must be at least {} (current: {})'.format(self.minimum_total_tau, self.total_tau))
# #         return self.tau_list - self.eff_pulse_dur_waiting_time

def round_to(val, base_val):
    return np.around(np.array(val) / base_val)*base_val

def loop_count(tau):
    return int(np.around(tau/__BASE_TAU__))

def x_values_awg_fit(start, stop, nstep, f=np.logspace):
    start = start if start > __BASE_TAU__ else __BASE_TAU__
    if f == np.logspace:
        start = np.log10(start)
        stop = np.log10(stop)
    return round_to(f(start, stop, nstep), __BASE_TAU__)

def dbm2v(Lp):
    P = 10**(Lp/10.-3)
    return np.sqrt(P*50)

def v2dmb(V):
    raise Exception('not implemented')

def complement_arr(arr, direction):
    """
    only points with amp_left + amp_right <= 1.0 can be measured (awg limitation). This results in many zeros in the
    resulting amplitude matrix. These zeros are recognized by the interpolation algorithm as discontinuities.
    This method tries correct for those errors before interpolation.

    :param arr: numpy array
    :param direction: string
    'left' or 'right'
    the direction in which the measured power is increasing. For the measured power of the right frequency, this would be 'right',
    otherwise 'left'.
    :return: numpy array
    """
    for i, line in enumerate(arr):
        for j, item in enumerate(line):
            if item == 0:
                if direction == 'left':
                    arr[i, j] = arr[i, j - 1]
                elif direction == 'right':
                    arr[i, j] = arr[i-1, j]
                else:
                    raise Exception('wrong direction')
    return arr

def tau_full_wavelength(target_tau, frequency):
    return np.around(target_tau*frequency)/frequency

def effective_tau(tau, wait_switch_time, omega_e):
    return tau + 0.25/omega_e + wait_switch_time

def alpha(nu_rf, n, tau, omega_e, wait_switch_time):
    """
    :param nu_rf: radio frequency relative to bare nuclear larmor
    :param n: n = 0..39, number of waiting time
    :param tau: duration of one waiting time
    :param omega_e: electron rabi frequency for pi pulses
    :param wait_switch_time: added to each each waiting time. wait_switch_time = 0.1 --> effectively 0.2 mus before each electron pi pulse done in the experiment
    :return: float. Phase in radiant
    """
    delta_alpha = -2*np.pi*nu_rf*effective_tau(tau, wait_switch_time, omega_e)
    return int(np.ceil(n/2.))*(delta_alpha + np.pi) % (2*np.pi)

def write_rpf_kna(filepath, nu_rf, omega_n, omega_e, tau, wait_switch_time=0.0, steps_per_tau=1):
    """
    :param omega_n: Determines if cnot or detection. omega_n = 0.5/(40*tau) --> cnot 1/(40*tau) --> detection. The last electron pi pulse must have the according phase
    :param filepath: filepath of the generated robust pulse file
    """
    M = 40.*steps_per_tau
    u_t = np.ones(M).reshape(-1, 1)*tau/float(steps_per_tau)
    u_omega = omega_n*np.ones(M).reshape(-1, 1)
    u_phi = np.array([alpha(nu_rf, n, tau, omega_e, wait_switch_time) for n in range(40)])
    u_phi = np.tile([u_phi for i in range(steps_per_tau)], 1).T.reshape(-1, 1)
    u_array_A_phi = np.concatenate([u_t, u_omega, u_phi], axis=1)
    np.savetxt(filepath, u_array_A_phi)

def test_ret_ret_mcas(ret_ret_mcas, pdc_list, nuclear=None, settings=None, write_to_awg=False):

    for pdc in pdc_list:
        print(pdc)
        if settings is not None:
            settings(pdc)
            points = range(len(nuclear.x))
            seq_nums = range(nuclear.number_of_sequences)
        for seq_num in seq_nums:
            for point in points:
                print('writing seq_num: {}, point: {}'.format(seq_num, point))
                mcas = ret_ret_mcas(pdc)(seq_num, point)
                mcas.write_seq()
                if write_to_awg:
                    print('write to awg')
                    mcas.run_sequence()
