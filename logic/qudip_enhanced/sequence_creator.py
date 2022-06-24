# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import numpy as np
import itertools
import numbers
import sys
import more_itertools
import lmfit.lineshapes
import collections
import traceback
from .qutip_enhanced import coordinates


class pd(dict):
    def __init__(self):
        super(pd, self).__init__(self)
        self.ddp = dict()
        self.ddp['fid'] = np.array([])
        self.ddp['hahn'] = np.array([0.0])
        self.ddp['xy4'] = np.array([0.0, np.pi / 2., 0.0, np.pi / 2.])
        self.ddp['xy8'] = np.concatenate([self.ddp['xy4'], self.ddp['xy4'][::-1]])
        self.ddp['xy16'] = np.concatenate([self.ddp['xy8'], self.ddp['xy8'] + np.pi])
        self.ddp['knillpi'] = np.array([np.pi / 6., 0, np.pi / 2., 0, np.pi / 6.])
        self.ddp['kdd4'] = np.concatenate([phasexy + self.ddp['knillpi'] for phasexy in self.ddp['xy4']])
        self.ddp['kdd8'] = np.concatenate([phasexy + self.ddp['knillpi'] for phasexy in self.ddp['xy8']])
        self.ddp['kdd16'] = np.concatenate([phasexy + self.ddp['knillpi'] for phasexy in self.ddp['xy16']])

    def parse_ddtype(self, ddtype):
        """

        :param ddtype: str
            full description of used dynamical decoupling sequence, individual parameters separated by "_"
            examples:

                1. kdd4
                    kdd4 sequence, 20 pi-pulses

                2. hahn_90: repeat hahn echo once (as first argument is missing), shift the single done pi-pulse by 90 degrees

                3. 3_kdd4_90: repeat a kdd4 sequence 3 times, shift phase of every pi-pulse by 90 degrees
        :return:
        """
        if type(ddtype) is not str:
            raise Exception('Error:{}, {}'.format(type(ddtype), ddtype))
        pl = ddtype.split("_")
        if len(pl) == 1:
            pl = [1, pl[0], 0]
        elif len(pl) == 2:
            try:
                pl[0] = int(pl[0])
                pl.append(0.0)
            except:
                pl = [1] + pl
                pl[2] = float(pl[2])
        elif len(pl) == 3:
            pl[0] = int(pl[0])
            pl[2] = float(pl[2])
        return pl[0], pl[1], pl[2]

    def __getitem__(self, i):
        n, bs, offset_phase = self.parse_ddtype(i)
        if 'cpmg' in bs:
            if len(bs) == 4:
                raise Exception('Error: {} does not tell how many pi-pulses you want. Valid would be 5_cpmg8'.format(i))
            else:
                bp = np.array(int(bs[4:]) * [0], dtype=np.float64)
        else:
            bp = self.ddp[bs]
        bp = np.tile(bp, n)
        bp += np.deg2rad(offset_phase)
        return bp


__PHASES_DD__ = pd()


class list_repeat(list):
    """
    Allows one wavefile to be used for driving at multiple frequencies without copying it.
    """

    def __getitem__(self, i):
        try:
            return super(list_repeat, self).__getitem__(i)
        except Exception:
            if len(self) != 1:
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)
        return super(list_repeat, self).__getitem__(0)


# def xy2aphi(xy):
#     norm = np.array([np.linalg.norm(xy, axis=1)]).transpose()
#     phi = np.arctan2(xy[:, 1:2], xy[:, 0:1])
#     return np.concatenate([norm, phi], axis=1)

def xy2aphi(xy, out=None):
    import time
    t0 = time.time()
    out = np.empty(xy.shape) if out is None else out
    out[:, 0] = xy[:, 0] ** 2
    out[:, 0] += xy[:, 1] ** 2
    np.sqrt(out[:, 0], out=out[:, 0])
    out[:, 1] = np.arctan2(xy[:, 1], xy[:, 0])
    return out


def round2float(arr, val):
    return np.around(arr / val) * val


class DDParameters:
    def __init__(self, name, rabi_period, time_digitization=None, **kwargs):
        self.name = name
        self.time_digitization = time_digitization
        self.set_total_tau(**kwargs)
        self.rabi_period = rabi_period

    @property
    def phases(self):
        name = self.name
        if name[-6:] == '_uhrig' in name:
            name = name[:-6]
        return __PHASES_DD__[name]

    @property
    def n_tau(self):
        if self.number_of_pi_pulses == 0:
            return 2
        else:
            return 2 * (self.number_of_pi_pulses)

    def set_total_tau(self, **kwargs):
        if self.name[-6:] == '_uhrig':
            if self.time_digitization is not None:
                raise NotImplementedError('time_digitization has no effect for Urig')
            return kwargs['total_tau']
        else:
            if 'tau' in kwargs:
                tau = kwargs['tau']
            else:
                tau = kwargs['total_tau'] / self.n_tau
        if self.time_digitization is not None:
            tau = np.around(tau / self.time_digitization, out=tau)
            tau *= self.time_digitization
        self.total_tau = self.n_tau * tau

    @property
    def number_of_pi_pulses(self):
        return len(self.phases)

    @property
    def number_of_pulses(self):
        return self.number_of_pi_pulses + 2

    @property
    def uhrig_pulse_positions_normalized(self):
        return np.sin(np.pi * np.arange(self.number_of_pulses) / (2 * self.number_of_pulses - 2)) ** 2

    @property
    def uhrig_taus_normalized(self):
        return np.diff(self.uhrig_pulse_positions_normalized)

    @property
    def uhrig_pulse_positions(self):
        return self.total_tau * self.uhrig_pulse_positions_normalized

    @property
    def uhrig_taus(self):
        return self.total_tau * self.uhrig_taus_normalized

    @property
    def tau_list(self):
        name = self.name
        if name[-6:] == '_uhrig' in name:
            return self.uhrig_taus
        else:
            tau = self.total_tau / self.n_tau
            return [tau] + [2 * tau for i in range(self.number_of_pi_pulses - 1)] + [tau]

    @property
    def eff_pulse_dur_waiting_time(self):
        return np.concatenate([[3 / 8. * self.rabi_period], 0.5 * self.rabi_period * np.ones(self.number_of_pi_pulses),
                               [
                                   3 / 8. * self.rabi_period]])  # effective duration of pi pulse for each waiting time. The effective phase evolution time during the pi/2 pulse is taken as half of the pulse duration

    @property
    def minimum_total_tau(self):
        return self.eff_pulse_dur_waiting_time[0] / self.uhrig_taus_normalized[0]

    @property
    def effective_durations_dd(self):
        if self.minimum_total_tau > self.total_tau:
            raise Exception('Waiting times smaller than zero are not allowed. '
                            'Total tau must be at least {} (current: {})'.format(self.minimum_total_tau,
                                                                                 self.total_tau))
        return self.tau_list - self.eff_pulse_dur_waiting_time


class Arbitrary:
    @property
    def controls(self):
        if hasattr(self, '_controls'):
            return self._controls
        elif type(self.column_dict) is not collections.OrderedDict:
            raise Exception("Error: {}, {}".format(self.column_dict, type(self.column_dict)))
        return list(self.column_dict.keys())

    @property
    def n_columns(self):
        """
        n_columns != n_controls, as e.g. 'mw' might have 'x' and 'y' control
        """
        return int(np.sum([len(i) for i in self.column_dict.values()]))

    def locations(self, name):
        return [i for i, val in enumerate(self.sequence) if name in val]

    def l_active(self, name):
        return [True if name in val else False for val in self.sequence]

    @property
    def n_bins(self):
        return len(self.sequence)

    def mask(self, name):
        out = np.zeros((len(self.sequence), self.n_columns), dtype=bool)
        for i in self.locations(name):
            # out[i, self.column_dict[name]] = np.ones(len(self.column_dict[name]), dtype=bool)
            out[i, self.column_dict[name]] += True
        return out

    @property
    def T(self):
        return sum(self.times())

    def times(self, name=None):
        times = self.times_full
        if name is not None:
            return times[self.locations(name)]
        else:
            return times

    def fields(self, name=None):
        fields = self.fields_full
        if name is not None:
            return fields[self.locations(name)][:, self.column_dict[name]]
        else:
            return fields

    def times_fields(self, name):
        return np.concatenate([self.times(name).reshape(-1, 1), self.fields(name)], axis=1)

    def fields_aphi(self, name=None):
        l = []
        for k, v in self.column_dict.items():
            if name is None or k == name:
                l.append(self.fields_full[:, self.column_dict[k]])
                if len(v) == 2:
                    l[-1] = xy2aphi(l[-1])
        out = np.concatenate(l, axis=1)
        if name is not None:
            out = out[self.locations(name)]
        return out

    def split(self, locations, n):
        self._times_full = np.array(
            list(itertools.chain(*[[t / n] * n if idx in locations else [t] for idx, t in enumerate(self.times_full)])))
        self._fields_full = np.repeat(self.fields_full, [n if i in locations else 1 for i in range(self.n_bins)],
                                      axis=0)
        self._sequence = list(
            itertools.chain(*[[item] * n if idx in locations else [item] for idx, item in enumerate(self.sequence)]))

    def split_all_max(self, time_digitization):
        print(
            'This might be slow, rounding and probably also numpy.allclose are veeery slow. making sure in advance that everything is correct and not having to round might be better')
        old_times_full = self.times_full
        old_sequence = self.sequence
        old_fields_full = self.fields_full
        if not np.allclose(old_times_full, round2float(old_times_full, time_digitization), time_digitization * 1e-4):
            raise Exception(
                'length mus {} is not valid for the current sample_frequency {}'.format(old_times_full, 12e3))
        n_split = (old_times_full / time_digitization).astype(int)
        n_rows = int(sum(old_times_full) / time_digitization)
        if not float(n_rows).is_integer():
            raise Exception('Error: {}, {}, {}'.format(self.T, time_digitization, n_rows))
        n_split_cs = np.cumsum(np.hstack([[0], n_split]))
        times_full = np.ones(n_rows)
        times_full *= time_digitization
        fields_full = np.empty([n_rows, self.n_columns])
        sequence = []
        for idx in range(self.n_bins):
            fields_full[n_split_cs[idx]:n_split_cs[idx + 1], :] = old_fields_full[idx, :]
            sequence.append(old_sequence[idx] * n_split[idx])
        self._times_full = times_full
        self._fields_full = fields_full
        self._sequence = sequence

    @property
    def export_names_dict(self):
        return getattr(self, '_export_names_dict', dict([(k, k) for k in self.controls]))

    @export_names_dict.setter
    def export_names_dict(self, val):
        """
        NOTE: Not all controls have to be given, if e.g. only 'mw' should be renamed to 'MW' then val = {'mw': 'MW'} is allowed
        """
        out = {}
        for k, v in val.items():
            if k not in self.controls:
                raise Exception("Error: {}, {}, {}, {}".format(val, out, k, v))
            out[k] = v
        self._export_names_dict = out

    @property
    def export_sequence(self):
        seq = [[] for _ in range(self.n_bins)]
        for name in self.export_names_dict.keys():
            m = self.mask(name)
            for i, row in enumerate(m):
                if np.any(row):
                    seq[i].append(self.export_names_dict[name])
        return [i for i in seq if len(i) > 0]

    @property
    def sequence_steps(self):
        fsn = np.empty((self.n_bins, len(self.export_names_dict)))
        nl_d = dict([(v, 0) for v in self.export_names_dict])
        out = []
        for i, step in enumerate(self.export_sequence):
            osln = []
            for name, export_name in self.export_names_dict.items():
                if export_name in step:
                    nl_d[name] += 1
                    osln.append(nl_d[name])
            fsn[i] = list(nl_d.values())
            out.append([', '.join(step), ', '.join(['{:d}'.format(int(i)) for i in osln])])
        return out

    def save_export_sequence_steps(self, path):
        """
        saves the sequence ['RF, WAIT', 'WAIT', 'MW', ..] along with the line number in the respective file
        :param path:
        :return:
        """
        np.savetxt(path, self.sequence_steps, delimiter="\t", fmt=str("%s"))
        print("Sequence_steps saved.")

    def sequence_steps_for_script(self, sample_frequency=12e3):
        """
        I HAVE NO IDEA HOW THIS BEHAVES WHEN MORE THAN ONE CONTROL IS TURNED ON AT ONCE
        """
        _WAVE_FILE_DICT_ = dict(
            [(self.export_names_dict[key], self.times_fields_aphi(name=key, sample_frequency=sample_frequency)) for key
             in self.export_names_dict])

        sequence_steps = []
        for i in self.sequence_steps:
            sequence_steps.append([[i[0]], [int(i[1])]])
            sequence_steps[-1][1] = dict([(key, val) for key, val in zip(['length_mus', 'omega', 'phases'],
                                                                         _WAVE_FILE_DICT_[sequence_steps[-1][0][0]][
                                                                             sequence_steps[-1][1][0] - 1])])
            sequence_steps[-1][1]['omega'] = [sequence_steps[-1][1]['omega']]
            if sequence_steps[-1][0][0] != 'WAIT':
                sequence_steps[-1][1]['phases'] = np.degrees([sequence_steps[-1][1]['phases']])
        return sequence_steps

    def save_times_fields(self, path, name=None):
        np.savetxt(path, np.around(self.times_fields(name), 9), fmt=str('%+1.14e'))

    def times_fields_aphi(self, name, sample_frequency=12e3):
        t = round2float(self.times(name), 1 / sample_frequency)
        return np.column_stack([t, self.fields_aphi(name)])

    def save_times_fields_aphi(self, name, path=None, sample_frequency=12e3):
        np.savetxt(path, np.around(self.times_fields_aphi(name=name, sample_frequency=sample_frequency), 9),
                   fmt=str('%+1.14e'))

    def save_dynamo_fields(self, directory):
        self.save_times_fields("{}\\fields.dat".format(directory))
        for k, v in self.export_names_dict.items():
            self.save_times_fields_aphi(name=k, path="{}\\{}.dat".format(directory, v))
            print("Fields {} saved.".format(v))

    # def delete_bins(self, l):


    # def dataframe(self):
    #     out = Data()
    #     pn = ['time', 'control_name', ]
    #
    #     parameter_names = ret_property_array_like_typ('parameter_names', str)
    #     parameter_base = ret_property_array_like_typ('ensemble_base', (list, np.ndarray))
    #     observation_names = ret_property_array_like_typ('observation_names', str)

    def print_info(self):
        for s, t in zip(self.sequence, self.times()):
            print(s, t)


class Wait(Arbitrary):
    def __init__(self, t, time_digitization=1 / 12e3, n_bins=1, control='wait'):
        self.column_dict = {control: [0]}
        self.control = control
        self._sequence = getattr(self, '_sequence', [[self.control]] * n_bins)
        self.time_digitization = time_digitization
        self.set_t(t)


    def set_t(self, val):
        self.t = np.around(
            val / (self.n_bins * self.time_digitization)) * self.n_bins * self.time_digitization

    @property
    def sequence(self):
        return self._sequence

    @property
    def fields_full(self):
        return getattr(self, '_fields_full', np.zeros((len(self.sequence), self.n_columns)))

    @property
    def times_full(self):
        return getattr(self, '_times_full', np.array([self.t / float(self.n_bins)] * self.n_bins))


class Rabi(Arbitrary):
    def __init__(self, t_rabi, omega, phase=0.0, control_field='mw', n_bins_rabi=1, time_digitization=None):
        self.n_bins_rabi = n_bins_rabi
        self.t_rabi = t_rabi
        self.phase = phase
        self.omega = omega
        self.control_field = control_field
        self.set_time_digitization(time_digitization)
        self.column_dict = collections.OrderedDict([(self.control_field, [0, 1])])

    @property
    def sequence(self):
        return getattr(self, '_sequence', [[self.control_field]] * self.n_bins_rabi)

    def omega_list(self):
        out = np.ones([self.n_bins_rabi])
        out *= self.omega
        return out

    def set_time_digitization(self, val):
        # if not np.allclose(self.t_rabi, round2float(self.t_rabi, val), val*1e-6):
        #     raise Exception('Error: {}, {}, {}'.format(val, self.t_rabi, float(self.t_rabi/val)))
        self.time_digitization = val

    @property
    def fields_full(self):
        ol = self.omega_list()
        return getattr(self, '_fields_full', np.array([ol * np.cos(self.phase), ol * np.sin(self.phase)]).T)

    @property
    def times_full(self):
        return getattr(self, '_times_full', np.array([self.t_rabi / self.n_bins_rabi] * self.n_bins_rabi))

    # class ShapedPi(Arbitrary):
    #     def __init__(self, t_rabi, omega, phase=0.0, control_field='mw', bin_duration=1/12e3):
    #         self.n_bins_rabi = n_bins_rabi
    #         self.t_rabi = t_rabi
    #         self.phase = phase
    #         self.omega = omega
    #         self.control_field = control_field
    #         self.column_dict = collections.OrderedDict([(self.control_field, [0, 1])])
    #
    #     @property
    #     def sequence(self):
    #         return getattr(self, '_sequence', [[self.control_field]] * self.n_bins_rabi)
    #
    #     def omega_list(self):
    #         return np.ones([self.n_bins_rabi]) * self.omega
    #
    #     @property
    #     def fields_full(self):
    #         ol = self.omega_list()
    #         return getattr(self, '_fields_full', np.array([ol * np.cos(self.phase), ol * np.sin(self.phase)]).T)
    #
    #     @property
    #     def times_full(self):
    #         return getattr(self, '_times_full', np.array([self.t_rabi / self.n_bins_rabi] * self.n_bins_rabi))
    # x = (0:n - 1)*N / n;
    # x = mod(x, 1);
    # x = 1 - tau / tpi * abs(x - 0.5);
    # x = max(x, 0);
    # x = sin(pi * x / 2). ^ 2;


class RabiGaussian(Rabi):
    def __init__(self, gaussian_parameters=None, *args, **kwargs):
        super(RabiGaussian, self).__init__(*args, **kwargs)
        self.gaussian_parameters = gaussian_parameters

    @property
    def gaussian_parameters(self):
        return self._gaussian_parameters

    @gaussian_parameters.setter
    def gaussian_parameters(self, val):
        val['mu'] = float(val.get('mu', self.t_rabi / 2.))
        if val['mu'] < 0. or val['mu'] > self.t_rabi:
            raise Exception('Error: val')
        if val['sigma'] > self.t_rabi:
            raise Exception('Error: val')
        val['area'] = float(val.get('area', self.t_rabi * self.omega))
        val['x_area_range'] = [0.0, self.t_rabi]
        self._gaussian_parameters = val

    def omega_list(self):
        return lmfit.lineshapes.gaussian(self.times_center(self.control_field), **self.gaussian_parameters)


class DDAlpha(Arbitrary):
    def __init__(self, pi_phases=None, spt=None,
                 wait=None, target_t_rf=None, rabi_period=None,
                 target_Azz=None, omega=None,
                 time_digitization=None):
        self.time_digitization = time_digitization
        self.pi_phases = pi_phases
        self.spt = spt
        self.wait = wait
        self.target_t_rf = target_t_rf
        self.rabi_period = rabi_period
        self.target_Azz = target_Azz
        self.omega = omega

    column_dict = collections.OrderedDict([('mw', [0, 1]), ('rf', [2, 3]), ('wait', [4])])

    @property
    def n_pi(self):
        return len(self.pi_phases)

    @property
    def omega(self):
        return self._omega

    @omega.setter
    def omega(self, val):
        if val in [None, 'pi', '2pi'] or isinstance(val, numbers.Number):
            if val in [None, 'pi']:
                o = 0.5 / self.t_rf
            elif val == '2pi':
                o = 1 / self.t_rf
            elif isinstance(val, numbers.Number):
                o = val
            self._omega = o * np.ones(2 * self.n_pi * self.spt)
        elif len(val) == 2 * self.n_pi * self.spt:
            self._omega = val
        else:
            raise Exception('Error: {}'.format(val))

    @property
    def t_rf(self):
        return 2 * self.n_pi * self.spt * self.tau()

    @property
    def sequence(self):
        wait = [['wait']] if self.wait is not None else []
        base = [['rf']] * self.spt + wait + [['mw']] + wait + [['rf']] * self.spt
        return getattr(self, '_sequence', list(itertools.chain(*[base for i in range(self.n_pi)])))

    def alpha(self, n):
        delta_alpha = 2 * np.pi * self.target_Azz * (self.tau() * self.spt + self.wait + 0.25 * self.rabi_period)
        return int(np.ceil(n / 2.)) * (delta_alpha + np.pi) % (2 * np.pi)

    def rf_array_aphi(self):
        u_phi = np.repeat([self.alpha(n) for n in range(2 * self.n_pi)], self.spt)
        return np.array([self.omega, u_phi]).T

    def rf_array_xy(self):
        rho, azim = tuple(np.hsplit(self.rf_array_aphi(), 2))
        x, y, z = coordinates.sph2cart(rho, 0, azim)
        return np.concatenate([x, y], axis=1)

    def mw_array_xy(self):
        return np.array([np.array([np.cos(phi), np.sin(phi)]) / self.rabi_period for phi in self.pi_phases])

    def mw_array_aphi(self):
        x, y = tuple(np.hsplit(self.mw_array_xy(), 2))
        rho, elev, azim = coordinates.cart2sph(x, y, 0)
        return np.concatenate([rho, azim], axis=1)

    @property
    def fields_full(self):
        out = np.zeros((len(self.sequence), self.n_columns))
        mw_array = self.mw_array_xy()
        rf_array_xy = self.rf_array_xy()
        idxmw = 0
        idxrf = 0
        for i, val in enumerate(self.sequence):
            if 'mw' in val:
                out[i, self.column_dict['mw']] = mw_array[idxmw]
                idxmw += 1
            elif 'rf' in val:
                out[i, self.column_dict['rf']] = rf_array_xy[idxrf]
                idxrf += 1
        return getattr(self, '_fields_full', out)

    def tau(self):
        out = self.target_t_rf / (2 * self.n_pi * self.spt)
        if self.time_digitization is not None:
            out = np.around(out / float(self.time_digitization)) * float(self.time_digitization)
        return out

    @property
    def times_full(self):
        td = dict(rf=self.tau(),
                  mw=0.5 * self.rabi_period,
                  wait=self.wait)
        out = np.array([td[i[0]] for i in self.sequence if td[i[0]] is not None])
        out[self.locations('wait')[0]] /= 2
        out[self.locations('wait')[-1]] /= 2
        return getattr(self, '_times_full', out)


class DD(Arbitrary):
    def __init__(self, dd_type=None, rabi_period=None, time_digitization=None, phase=0.0, **kwargs):
        self.dd_type = dd_type
        self.rabi_period = rabi_period
        self.time_digitization = time_digitization
        self.phase = phase
        self.set_total_tau(**kwargs)

    column_dict = collections.OrderedDict([('mw', [0, 1]), ('wait', [2])])

    @property
    def sequence(self):
        if self.number_of_pi_pulses == 0:
            out = ['wait'] + ['wait']
        else:
            out = list(np.insert(['wait'] * self.n_wait, range(1, self.n_wait), [['mw'] * self.number_of_pi_pulses]))

        return getattr(self, '_sequence', [[i] for i in out])

    def mw_array_xy(self):
        rho, azim = tuple(np.hsplit(self.mw_array_aphi(), 2))
        x, y, z = coordinates.sph2cart(rho, 0, azim)
        return np.concatenate([x, y], axis=1)

    def mw_array_aphi(self):
        rho = np.ones([self.number_of_pi_pulses]) / self.rabi_period
        return np.vstack([rho, self.phases]).T

    @property
    def fields_full(self):
        out = np.zeros((len(self.sequence), self.n_columns))
        mw_array = self.mw_array_xy()
        idxmw = 0
        for i, val in enumerate(self.sequence):
            if 'mw' in val:
                out[i, self.column_dict['mw']] = mw_array[idxmw]
                idxmw += 1
        return getattr(self, '_fields_full', out)

    @property
    def times_full(self):
        tl = self.tau_list()
        if self.number_of_pi_pulses == 0:
            out = tl
        else:
            out = np.insert(tl, range(1, len(tl)), [[0.5 * self.rabi_period] * self.number_of_pi_pulses])
        return getattr(self, '_times_full', out)

    @property
    def phases(self):
        name = self.dd_type
        if name[-6:] == '_uhrig' in name:
            name = name[:-6]
        return np.array(__PHASES_DD__[name]) + self.phase

    @property
    def n_wait(self):
        if self.number_of_pi_pulses == 0:
            return 2
        else:
            return self.number_of_pi_pulses + 1

    @property
    def n_tau(self):
        return self.n_wait - 1

    def set_total_tau(self, **kwargs):
        if self.dd_type[-6:] == '_uhrig':
            return kwargs['total_tau']
        else:
            if 'tau' in kwargs and kwargs['tau'] is not None:
                tau = kwargs['tau']
            else:
                tau = kwargs['total_tau'] / self.n_tau
        if self.time_digitization is not None:
            tau = 2 * np.around((tau / 2.) / self.time_digitization) * self.time_digitization
        self.total_tau = self.n_tau * tau

    def tau_list(self):
        name = self.dd_type
        if name[-6:] == '_uhrig' in name:
            return self.uhrig_taus
        else:
            tau = self.total_tau / self.n_tau
            return np.array([tau / 2.] + [tau for _ in range(self.number_of_pi_pulses - 1)] + [tau / 2.])

    @property
    def number_of_pi_pulses(self):
        return len(self.phases)

    @property
    def number_of_pulses(self):
        raise Exception(
            'THIS IS BULLSHIT, THIS SEQUENCE EXCLUDES THE Pi/2 pulses, i.e. number of pulses = number of pi pulses')
        return self.number_of_pi_pulses + 2

    @property
    def uhrig_pulse_positions_normalized(self):
        return np.sin(np.pi * np.arange(self.number_of_pulses) / (2 * self.number_of_pulses - 2)) ** 2

    @property
    def uhrig_taus_normalized(self):
        return np.diff(self.uhrig_pulse_positions_normalized)

    @property
    def uhrig_pulse_positions(self):
        return self.total_tau * self.uhrig_pulse_positions_normalized

    @property
    def uhrig_taus(self):
        out = self.total_tau * self.uhrig_taus_normalized
        if self.time_digitization is not None:
            out = np.around(out / self.time_digitization) * self.time_digitization
        return out

    @property
    def eff_pulse_dur_waiting_time(self):
        return np.concatenate([[3 / 8. * self.rabi_period], 0.5 * self.rabi_period * np.ones(self.number_of_pi_pulses),
                               [
                                   3 / 8. * self.rabi_period]])  # effective duration of pi pulse for each waiting time. The effective phase evolution time during the pi/2 pulse is taken as half of the pulse duration

    @property
    def minimum_total_tau(self):
        return self.eff_pulse_dur_waiting_time[0] / self.uhrig_taus_normalized[0]

    @property
    def effective_durations_dd(self):
        if self.minimum_total_tau > self.total_tau:
            raise Exception('Waiting times smaller than zero are not allowed. '
                            'Total tau must be at least {} (current: {})'.format(self.minimum_total_tau,
                                                                                 self.total_tau))
        return self.tau_list - self.eff_pulse_dur_waiting_time


class Z(Arbitrary):
    def __init__(self, fields_l, times_l):
        self.column_dict = collections.OrderedDict([("z{}".format(i), [i]) for i in range(len(fields_l))])
        self.fields_full = np.diag(fields_l)
        self.times_full = np.array(times_l)
        self.sequence = [[i] for i in self.controls]


class PList(collections.MutableSequence):
    def __init__(self, list_owner):
        self.oktypes = (Arbitrary)
        self.list_owner = list_owner
        self._list = list()

    @property
    def list(self):
        return self._list

    @list.setter
    def list(self, val):
        """
        inefficient, calls script_queue_changed multiple times. In practice not relevant.
        """
        self._list = val
        self.list_owner.p_list_changed()

    def set_parent(self, v):
        v.parent = self.list_owner

    def __len__(self): return len(self.list)

    def __getitem__(self, i): return self.list[i]

    def __delitem__(self, i):
        del self.list[i]
        self.list_owner.p_list_changed()

    def __setitem__(self, i, v):
        raise NotImplementedError

    def insert(self, i, v):  # needed for append
        if i != len(self.list):
            raise Exception('Only appending and popping items allowed')
        self.list.insert(i, v)
        self.list_owner.p_list_changed()

    def __str__(self):
        return str(self.list)

    def __repr__(self):
        return str(self.list)


class Concatenated(Arbitrary):
    def __init__(self, p_list, controls):
        self._controls = controls
        self._p_list = PList(self)
        self._p_list.list = p_list
        self.check_control_length()

    @property
    def p_list(self):
        return self._p_list

    def p_list_changed(self):
        self.set_sequence()
        self.set_column_dict()
        self.set_n_column()
        self.set_fields_full()
        self.set_times_full()

    def set_p_list(self, times_full, fields_full):
        """
        :param times_full: desired representation of times_full of this concatenated instance
                           times are distributed to individual p_list items
        :param fields_full: desired representation of fields_full of this instance of Concatenated
                           fields are distributed to individual p_list items
        """
        nbcs = np.cumsum([0] + [p.n_bins for p in self.p_list])
        cd = self.column_dict
        for idx in range(len(nbcs) - 1):
            self.p_list[idx]._fields_full = fields_full[nbcs[idx]:nbcs[idx + 1],
                                            list(itertools.chain(*[cd[c] for c in self.p_list[idx].controls]))]
            self.p_list[idx]._times_full = times_full[nbcs[idx]:nbcs[idx + 1]]

    def set_sequence(self):
        self._sequence = list(itertools.chain(*[i.sequence for i in self.p_list]))

    @property
    def sequence(self):
        return self._sequence

    def check_control_length(self):
        for c in self.controls:
            if len(set([len(p.column_dict[c]) for p in self.p_list if c in p.column_dict])) != 1:
                raise Exception("Error. column_dict: {}".format(self.column_dict))

    def set_column_dict(self):
        n_cc = {}
        for c in self.controls:
            for p in self.p_list:
                if c in p.column_dict:
                    if c in n_cc and n_cc[c] != len(p.column_dict[c]):
                        raise Exception(
                            'Error: Control {} has different column length on different items of p_list'.format(c))
                    else:
                        n_cc[c] = len(p.column_dict[c])
        out = collections.OrderedDict()
        idx = 0
        for c in self.controls:
            out[c] = list(np.arange(n_cc[c]) + idx)
            idx += n_cc[c]
        self._column_dict = out

    @property
    def column_dict(self):
        return self._column_dict

    def set_n_column(self):
        self._n_columns = len(list(itertools.chain(*self.column_dict.values())))

    @property
    def n_columns(self):
        return self._n_columns

    def extend_fields_full(self, n):
        fields_full = np.zeros([self.p_list[n].n_bins, self.n_columns])
        for c in self.controls:
            if c in self.p_list[n].column_dict:
                fields_full[:, self.column_dict[c]] = self.p_list[n].fields_full[:, self.p_list[n].column_dict[c]]
        return fields_full

    def set_fields_full(self):
        # self._fields_full = np.concatenate(
        out = np.zeros((self.n_bins, self.n_columns))
        nbcs = np.cumsum(([0] + [i.n_bins for i in self.p_list]))
        for i in range(len(self.p_list)):
            for c in self.controls:
                if c in self.p_list[i].column_dict:
                    out[nbcs[i]:nbcs[i + 1], self.column_dict[c]] = self.p_list[i].fields_full[:,
                                                                    self.p_list[i].column_dict[c]]
                    # out[nbcs[i]:nbcs[i+1], :] = self.extend_fields_full(i)
                    # [self.extend_fields_full(i) for i in range(len(self.p_list))]
        # )
        self._fields_full = out

    @property
    def fields_full(self):
        return self._fields_full

    def set_times_full(self):
        self._times_full = np.concatenate([i.times_full for i in self.p_list])

    @property
    def times_full(self):
        return self._times_full


class DDConcatenated(Concatenated):
    """
    THIS IS VERSATILE BUT SLOW
    NOTES:
        1. tau is time between centers of (pi -) pulses
        2. preceeding and following tau/2 not included for better rounding. To
           To include them and have desired time_digitization=t0, here set time_digitization to 2*t0 and append and prepend Wait(tau/2, time_digitization=t0)
        3. fid and hahn echo are not included, for reason see 2.)
    """

    def __init__(self, dd_type, p_list_pulses, tau_list, time_digitization=None):
        self.set_dd_type(dd_type)
        self.time_digitization = time_digitization
        self.set_p_list_pulses(p_list_pulses)
        self.set_tau_list(tau_list)
        super(DDConcatenated, self).__init__(self.generate_p_list(), ['mw'])

    @property
    def dd_type(self):
        return self._dd_type

    @property
    def phases(self):
        return self._phases

    def set_dd_type(self, val):
        if 'uhrig' in val or 'fid' in val or 'hahn' in val:
            raise NotImplementedError
        self._dd_type = val
        self._phases = __PHASES_DD__[self.dd_type]

    @property
    def p_list_pulses(self):
        return self._p_list_pulses

    def set_p_list_pulses(self, val):
        if len(val) != len(__PHASES_DD__[self.dd_type]):
            raise Exception('Error: {}, {}, {}'.format(len(val), val, self.dd_type))
        if len(set(val)) != len(val):
            raise Exception("Error: {}".format(val))
        for idx, pulse in enumerate(val):
            if self.time_digitization is not None and pulse.time_digitization != self.time_digitization:
                raise Exception("Error: {}, {}".format(pulse.time_digitization, self.time_digitization))
            pulse.phase += self.phases[idx]
        self._p_list_pulses = val

    @property
    def tau_list(self):
        return self._tau_list

    def set_tau_list(self, val):
        if len(val) == 1:
            v = np.ones(self.n_tau)
            v *= val
            val = v
        elif len(val) != self.n_tau:
            raise Exception('Error: {}, {}'.format(val, self.n_tau))
        if self.time_digitization is not None:
            val = np.around(val / self.time_digitization, out=val)
            val *= self.time_digitization
        self._tau_list = val

    @property
    def n_tau(self):
        return self.number_of_pi_pulses - 1

    @property
    def number_of_pi_pulses(self):
        return len(self.phases)

    @property
    def pulse_durations(self):
        return np.array([self.p_list_pulses[i].T for i in range(len(self.phases))])

    @property
    def pulse_durations_per_tau(self):
        pulse_durations = self.pulse_durations
        return (pulse_durations[:-1] + pulse_durations[1:]) / 2.

    @property
    def effective_tau_list(self):
        return self.tau_list - self.pulse_durations_per_tau

    @property
    def p_list_tau(self):
        return [Rabi(t_rabi=t_wait,
                     omega=0.0,
                     time_digitization=self.time_digitization,
                     control_field='mw') for t_wait in self.effective_tau_list]

    def generate_p_list(self):
        return list(more_itertools.interleave_longest(self.p_list_pulses, self.p_list_tau))


class DDDegen(Arbitrary):
    def __init__(self, dd_type=None, rabi_period=None, tau=None, sample_frequency=12e3):
        self.dd_type = dd_type
        self.rabi_period = rabi_period
        self.tau = tau
        self.sample_frequency = sample_frequency
        self._sequence = ['mw'] * self.total_length_smpl
        self.set_fields_full()
        self.set_times_full()

    @property
    def sequence(self):
        return getattr(self, '_sequence')

    @property
    def n_pi(self):
        return len(__PHASES_DD__[self.dd_type])

    @property
    def t_pi(self):
        return .5 * self.rabi_period

    @property
    def length_smpl_per_pi(self):
        return int(np.around(self.sample_frequency * self.tau))

    @property
    def total_length_smpl(self):
        out = self.length_smpl_per_pi * self.n_pi
        return int(out)

    def set_times_full(self):
        self._times_full = np.ones(self.total_length_smpl) / self.sample_frequency

    def set_fields_full(self):
        # amplitudes
        x = np.arange(self.total_length_smpl, dtype=float)
        x *= self.n_pi
        x /= self.total_length_smpl
        np.mod(x, 1, out=x)
        x = x - .5
        x = np.abs(x)
        x = x / self.t_pi
        x = x * self.tau
        x = -1 * x
        x = x + 1
        np.maximum(x, 0, out=x)
        x *= np.pi / 2.
        np.sin(x, out=x)
        np.power(x, 2, out=x)

        # phases
        p = __PHASES_DD__[self.dd_type].reshape(-1, 1)
        p = np.repeat(p, 2, axis=1)
        np.cos(p[:, 0], out=p[:, 0])
        np.sin(p[:, 1], out=p[:, 1])
        p = np.repeat(p, self.length_smpl_per_pi, axis=0)

        self._fields_full = 1 / self.rabi_period * (p.T * x).T

    @property
    def times_full(self):
        return self._times_full

    @property
    def fields_full(self):
        return self._fields_full


def unitary_propagator(length_mus, h_mhz, fields, L_Bc):
    return (-1j*length_mus*(2*np.pi*h_mhz + sum(omega*Bc for omega, Bc in zip(fields, L_Bc)))).expm()

def unitary_propagator_list(h_mhz, times, fields, L_Bc):
    u_list = []
    for t, c_l in zip(times, fields):
        u_list.append(
            unitary_propagator(
                length_mus=t,
                h_mhz=h_mhz,
                fields=c_l,
                L_Bc=L_Bc
            )
        )
    return u_list

# def insert_operators_from_dict(u_list, insert_operator_dict):
#     if insert_operator_dict is not None:
#         for idx, kv in enumerate(insert_operator_dict.items()):
#             u_list.insert(kv[0] + idx, kv[1])

def unitary_propagator_list_mult(u_list):
    #HINT: replace argument u_list by "insert_operators_from_dict(unitary_propagator_list(h_mhz, times, fields, L_Bc), insert_operator_dict)", to generate a u_list
    out = []
    for idx in range(len(u_list)):
        try:
            if idx > 0:
                # u_list[idx] = u_list[idx] * u_list[idx-1]
                out.append(u_list[idx] * out[idx-1])
            else:
                out.append(u_list[idx])
        except:
            pass
    return out

# def unitary_propagator_list_sectioned(u_list, section_dict):
#     if type(section_dict) is not collections.OrderedDict:
#         raise Exception('Error: {}, {}'.format(section_dict, type(section_dict)))
#     u_list_reduced = []
#     sdv = section_dict.values()
#     for idx in range(len(sdv)):
#         if idx == 0:
#             ta = unitary_propagator_list_mult(u_list[:sdv[idx]+1])[-1]
#         else:
#             try:
#                 ta = unitary_propagator_list_mult(u_list[sdv[idx-1]+1:sdv[idx]+1])[-1]
#             except:
#                 pass
#         u_list_reduced.append(ta)
#     return u_list_reduced


