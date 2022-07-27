from __future__ import print_function, absolute_import, division
__metaclass__ = type

import operator
import os

import numpy as np
import pylab
import scipy.optimize
import scipy.stats

from qutip_enhanced import *
from collections import OrderedDict

def reanalyze_dataframe(data, analyze_sequence, analyze_type, number_of_simultaneous_measurements):
    trace = Trace(analyze_sequence=analyze_sequence)
    data_new = data_handling.Data(parameter_names=data.parameter_names, observation_names=data.observation_names, dtypes=data.dtypes)
    data_new.init()
    for row in data.df.iterrows():
        data_new._df = data_new.df.append(row[1])
        try:
            trace.raw_trace = row[1]['trace']
            analysis = trace.analyze(analyze_type=analyze_type, number_of_simultaneous_measurements=number_of_simultaneous_measurements)
            thresholds = trace.thresholds
            data_new.set_observations([OrderedDict(('result_{}'.format(i), result) for i, result in enumerate(results)) for results in analysis['results']])
            data_new.set_observations([OrderedDict(events=events) for events in analysis['events']])
            data_new.set_observations([OrderedDict(thresholds=thresholds)] * number_of_simultaneous_measurements)
        except:
            print('Nope')

    return data_new

class BaseTrace:
    def __init__(self, trace=None, analyze_sequence=None, analyze_type='standard', binning_factor=1, number_of_simultaneous_measurements=1, average_results=False, consecutive_valid_result_numbers=None):
        self.analyze_sequence = analyze_sequence
        self.trace = trace
        self.analyze_type = analyze_type
        self.binning_factor = binning_factor
        self.average_results = average_results
        self.number_of_simultaneous_measurements = number_of_simultaneous_measurements
        self.consecutive_valid_result_numbers = [0] if consecutive_valid_result_numbers is None else consecutive_valid_result_numbers

    @property
    def analyze_type(self):
        return self._analyze_type

    @analyze_type.setter
    def analyze_type(self, val):
        if val == 'consecutive_b':
            raise Exception("Error: outdated anlyze_type 'consecutive_b'. Chose 'consecutive' and probably you want to chose 'consecutive_valid_result_numbers = [0,1]'")
        else:
            self._analyze_type = val

    @property
    def analyze_sequence(self):
        return self._analyze_sequence

    @analyze_sequence.setter
    def analyze_sequence(self, value):
        if isinstance(value, list):
            if len(value) == 0:
                raise Exception("'analyze_sequence' can not be of length zero.")
            for idx, step in enumerate(value):
                if len(step) != 6:
                    raise Exception('Error: {}, {}'.format(idx, value))
                if not isinstance(step, list):
                    raise Exception('Error: {}, {}'.format(idx, value))
                if not step[0] in ['init', 'result']:
                    raise Exception('Error: {}, {}'.format(idx, value))
                if not step[1] in ['<', '>']:
                    raise Exception('Error: {}, {}'.format(idx, value))
                if not (step[2] == 'auto' or isinstance(step[2], int)):
                    raise Exception('Error: {}, {}'.format(idx, value))
                if step[2] == 'auto' and step[5] != 1:
                    raise Exception('Error: {}, {}'.format(idx, value))
                if not isinstance(step[3], int) or step[3] < 0:
                    raise Exception('Error: {}, {}'.format(idx, value))
                if not type(step[4]) in [int, float]:
                    raise Exception('Error: {}, {}'.format(idx, value))

                if not isinstance(step[5], int) and step[5] >= 1:
                    raise Exception('When given, the last (6th) entry in an analyze_sequence step must be of type int. It represents the alternating_repetitions also used in snippets_awg.SSR()')
            self._analyze_sequence = value
        elif value is None:
            self._analyze_sequence = value
        else:
            raise TypeError("Trace.analyze_sequence must be a list.")

    @property
    def number_of_results(self):
        return sum([step[-1] for step in self.analyze_sequence if step[0] == 'result'])

    @property
    def period_run(self):
        return self.period_measurement*self.number_of_simultaneous_measurements

    @property
    def trace(self):
        return self.__trace

    @trace.setter
    def trace(self, value):
        if not (value is None or isinstance(value, np.ndarray) or isinstance(value, list)):
            raise Exception("'trace' must be None or of type list or np.ndarray")
        if value is None:
            self.__trace = value
        else:
            self.__trace = np.array(value, dtype=np.int16)

    @property
    def number_of_runs(self):
        return int(self.trace_length_cut / self.period_run)

    def period_measurement(self):
        raise NotImplementedError

    @property
    def trace_length_cut(self):
        return len(self.trace) - len(self.trace) % self.period_run

    @property
    def trace_cut(self):
        return self.trace[:self.trace_length_cut]

    def append_column(self, df, column_name, l):
        n = (len(df) / len(l))
        if n != int(n):
            raise Exception('Error: {}, {}'.format(len(df), len(l), l))
        df[column_name] = np.tile(l, int(n))
        return df

    def df_memory_column(self, df=None):
        df = self.df if df is None else df
        df = pd.pivot_table(df, values='n', index=['run', 'sm', 'step'], columns=['memory']).reset_index()
        return df

    @property
    def number_of_runs_rebinned(self):
        return int(np.floor(self.number_of_runs/float(self.binning_factor)))

    def df_rebin(self, df=None):
        df = self.df_memory_column() if df is None else df
        run_rebin = np.repeat(np.repeat(range(self.number_of_runs_rebinned), len(self.analyze_sequence) * self.number_of_simultaneous_measurements), self.binning_factor)
        df = df.iloc[:len(run_rebin)]
        if len(df) == 0:
            return df
        df.is_copy = False
        df['run_rebin'] = run_rebin
        idx = df.columns.tolist().index(0)
        out = df.groupby(['run_rebin'] + df.columns[1:idx].tolist()).agg(collections.OrderedDict([(key, np.sum) for key in df.columns[idx:-1]])).reset_index()
        out = out.rename(columns={'run_rebin': 'run'})
        return out

    def df_extended(self, df=None):
        df = self.df_memory_column() if df is None else df
        df = self.df_rebin(df)
        for idx, cn in enumerate(['st', 'op', 'thr', 'rep', 'thr_diff', 'n_mem']):
            self.append_column(df, cn, [step[idx] for step in self.analyze_sequence])
        df['thr'] = df['thr'].astype('object')
        return df

    def df_consecutive(self, df):
        df2 = df.copy()
        df2.step = 1
        df['st'] = 'init'
        idx_result_0 = list(df2.columns).index('step')+1
        df.iloc[-1, idx_result_0:idx_result_0 + self.analyze_sequence[0][5]] = np.int16(0)
        df.at[df.index[-1], 'reliable'] = False
        df.iloc[:, idx_result_0:] = df.reindex(index=np.roll(df.index, 1)).reset_index()
        df = pd.concat([df, df2]).sort_values(['run', 'sm', 'step', 'st']).reset_index(drop=True)
        return df

class TraceRep(BaseTrace):

    @property
    def period_measurement(self):
        return sum([step[3] for step in self.analyze_sequence])

    @property
    def df(self):
        analyze_sequence = self.analyze_sequence

        len_step_l = [step[3] for step in analyze_sequence]
        number_of_steps = len(len_step_l)
        len_k_l = [int(step[3] / step[5]) for step in analyze_sequence]
        len_memory_l = [step[5] for step in analyze_sequence]

        d = collections.OrderedDict([
            ('run', np.repeat(range(self.number_of_runs), self.period_run)),
            ('sm', np.tile(np.repeat(range(self.number_of_simultaneous_measurements), self.period_measurement), self.number_of_runs)),
            ('step', np.tile(np.repeat(range(number_of_steps), len_step_l), self.number_of_runs*self.number_of_simultaneous_measurements)),
            ('k', np.tile(np.concatenate([np.repeat(range(len_k), len_memory) for len_k, len_memory in zip(len_k_l, len_memory_l)]), self.number_of_runs*self.number_of_simultaneous_measurements)),
            ('memory', np.tile(np.concatenate([np.tile(range(len_memory), len_k) for len_k, len_memory in zip(len_k_l, len_memory_l)]), self.number_of_runs*self.number_of_simultaneous_measurements)),
            ('n', self.trace_cut)
        ])
        return pd.DataFrame.from_dict(d)

class Trace(BaseTrace):

    def hist(self, trace):
        hist, bins_temp = np.histogram(trace, bins=max(trace) - min(trace))
        bins = np.array(bins_temp[1:], dtype='int32')
        return {'hist': hist, 'bin_edges': bins}

    def guess_threshold(self, trace):
        return np.percentile(trace, 30)
        bin_edges = np.linspace(min(trace), max(trace), max(trace) - min(trace) + 1)
        hist = np.histogram(trace, bin_edges, normed=True)[0]
        hist_binary = np.array(hist) > max(hist[1:]) * 0.1 # this [:1] think because we dont want to consider zero counts)
        list = pylab.find(hist_binary)
        threshold = bin_edges[int((list[-1] + list[0]) / 2)]
        np.percentile(trace, 30)
        return threshold

    def fit_poissonian(self, trace):
        "Fit two Poissonians to the histogram, return (Amplitude1, Mean1, Amp2, Mean2)"
        # estimate peaks and relevant x-range based on given threshold
        threshold_guess = self.guess_threshold(trace)
        A1 = 0.5
        y1 = int(threshold_guess * (1 - 0.15))
        y2 = int(threshold_guess * (1 + 0.15))
        bin_edge_low = int(y1 - 4 * y1 ** 0.5)
        if bin_edge_low<0:
            bin_edge_low = 0
        bin_edge_high = int(y2 + 4 * y2 ** 0.5)
        # get histogram
        bin_edges = np.linspace(bin_edge_low, bin_edge_high, bin_edge_high - bin_edge_low + 1)
        bin_edges = np.append(bin_edges, bin_edges[-1] + bin_edges[-1] - bin_edges[-2])
        hist = np.histogram(trace, bins=bin_edges, normed=True)[0]
        # calculate fit
        prmtr_guess = (A1, y1, y2)
        if bin_edges[-1] < 600:  # use poisson
            model = self.poissonian
            A1, y1, y2 = scipy.optimize.leastsq(self.poiss_error, prmtr_guess, args=(hist, bin_edges))[0]
        else:  # use gauss
            model = self.gauss
            A1, y1, y2 = scipy.optimize.leastsq(self.gauss_error, prmtr_guess, args=(hist, bin_edges))[0]
        fit = (A1, y1, 1. - A1, y2)
        return {'fit': fit, 'hist': hist, 'bin_edges': bin_edges, 'model': model}

    def calc_threshold(self, trace, plot=False):
        fp = self.fit_poissonian(trace=trace)
        model = fp['model']
        bin_edges = fp['bin_edges'][fp['bin_edges'] >= 0]
        fit = fp['fit']
        # search Threshold
        poiss1_normed = np.array(model(bin_edges, 1e4, fit[1]))
        poiss2_normed = np.array(model(bin_edges, 1e4, fit[3]))
        function = poiss1_normed - poiss2_normed
        # [poiss1_normed[0] - (1 - poiss2_normed[0])]
        # for i in range(len(self.hist_bins)-1):
        #    function.append(function[i] + poiss1_normed[i+1] + poiss2_normed[i+1])
        for i in range(len(function) - 1):
            if function[i] < 0 and function[i + 1] >= 0:
                root_index = i + 1
                break
            elif function[i] > 0 and function[i + 1] <= 0:
                root_index = i + 1
                break
        threshold = bin_edges[root_index]
        # Calc readout fidelity
        area1_low = np.sum(model(bin_edges[0:root_index], 1., fit[1]))
        area1_high = np.sum(model(bin_edges[root_index:], 1., fit[1]))
        area2_low = np.sum(model(bin_edges[0:root_index], 1., fit[3]))
        area2_high = np.sum(model(bin_edges[root_index:], 1., fit[3]))
        # self.fidelity = 1 - (area2_low / area1_low + area1_high / area2_high) / 2
        # print "Threshold = %s, fidelity = %s" % (self.Threshold_fit, round(self.fidelity, 2))
        return threshold

    def poissonian(self, x, amplitude, mean):
        """Returns a Poissonian distribution (array) on x"""
        # x must be integers
        x_int = []
        for i in range(len(x)):
            x_int.append(int(x[i]))
        # Use Decimals (otherwise e**(-740++) = 0)
        # e = Decimal("%s" % np.math.e)
        # A = Decimal("%s" % amplitude)
        # y = Decimal("%s" % mean)
        e = np.math.e
        A = amplitude
        y = mean
        poisson = []
        poisson.append(A * e ** (-y / 4.))
        for i in range(1, x_int[-1] + 1):
            poisson.append(poisson[i - 1] * y / i)
        result = []
        for i in range(x_int[0], x_int[-1] + 1):
            result.append(float(poisson[i]))
        result = np.array(result)
        result = result * e ** (-y / 4.) * e ** (-y / 4.) * e ** (-y / 4.)
        return list(result)

    def poiss_error(self, prmtr, data, x):
        "Needed for scipy.optimize.leastsq"
        A1, y1, y2 = prmtr
        A2 = 1. - A1
        function = np.add(self.poissonian(x, A1, y1), self.poissonian(x, A2, y2))
        error = []
        for i in range(len(data)):
            error.append(data[i] - function[i])
        return error

    def gauss(self, x, amplitude, mean):
        """Returns a Gaussian distribution (array) on x"""
        result = amplitude * 1. / (mean * 2 * np.pi) ** 0.5 * np.exp(-(x - mean) ** 2 * 1. / mean)
        return list(result)

    def gauss_error(self, prmtr, data, x):
        "Needed for scipy.optimize.leastsq"
        A1, y1, y2 = prmtr
        A2 = 1. - A1
        function = np.add(self.gauss(x, A1, y1), self.gauss(x, A2, y2))
        error = []
        for i in range(len(data)):
            error.append(data[i] - function[i])
        return error

    @property
    def period_measurement(self):
        return sum([step[5] for step in self.analyze_sequence])

    @property
    def df(self):
        d = collections.OrderedDict([
            ('run', np.repeat(range(self.number_of_runs), self.period_run)),
            ('sm', np.tile(np.repeat(range(self.number_of_simultaneous_measurements), self.period_measurement), self.number_of_runs)),
            ('step', np.tile(np.concatenate([np.tile([i], step[-1]) for i, step in enumerate(self.analyze_sequence)]), self.number_of_runs*self.number_of_simultaneous_measurements)),
            ('memory', np.tile(np.concatenate([range(step[-1]) for step in self.analyze_sequence]), self.number_of_runs*self.number_of_simultaneous_measurements)),
            ('n', self.trace_cut)
        ])
        return pd.DataFrame.from_dict(d)

    def append_thr_a_eff(self, df):
        df['thr_a'] = -2
        column_names = [cn for cn in df.columns if type(cn) == long]
        for idx, step in enumerate(self.analyze_sequence):
            if step[2] == 'auto':
                df.loc[df['step'] == idx, 'thr_a'] = self.calc_threshold(df.loc[df['step'] == idx, column_names[0]])
            else:
                df.loc[df['step'] == idx, 'thr_a'] = df.loc[df['step'] == idx, 'thr']

    def append_digital(self, df):
        df['digital'] = -2
        df['reliable'] = True
        for idx, step in enumerate(self.analyze_sequence):
            results = df.loc[df['step'] == idx, range(step[5])].values
            if step[5] == 1:
                results = np.concatenate([results, df.loc[df['step'] == idx, 'thr_a'].astype(int).values.reshape(-1, 1)], axis=1)
            results_arg_sort = np.argsort(results, axis=1)
            df.loc[df['step'] == idx, 'digital'] = results_arg_sort[:, 0] if step[1] == '<' else results_arg_sort[:, -1]
            results_sort = np.sort(results, axis=1)
            diff = np.diff(results_sort[:, [0, 1]], axis=1) if step[1] == '<' else np.diff(results_sort[:, [-1, -2]], axis=1)
            df.loc[df['step'] == idx, 'reliable'] = np.abs(diff).reshape(-1) > df.loc[df['step'] == idx, 'thr_diff'] #more or less than value by threshold difference

    def append_valid_measurement(self, df):
        if self.analyze_type == 'consecutive':
            df = self.df_consecutive(df)
            nstep = 2
        else:
            nstep = len(self.analyze_sequence)
        reliable_run = df.groupby(['run', 'sm']).agg({'reliable': np.sum}) == nstep
        if len(df.loc[df['st'] == 'init']) == 0:
            valid_measurement = reliable_run.reliable
        elif self.analyze_type == 'consecutive':
            initialized_run = df[df['st'] == 'init'].groupby(['run', 'sm']).agg({'digital': np.sum}).isin(self.consecutive_valid_result_numbers)
            valid_measurement = initialized_run.digital & reliable_run.reliable
        else:
            initialized_run = df[df['st'] == 'init'].groupby(['run', 'sm']).agg({'digital': np.sum}) == 0
            valid_measurement = initialized_run.digital & reliable_run.reliable
        df['vm'] = valid_measurement.repeat(nstep).values
        return df


    def append_valid_inits(self, df):
        if self.analyze_type == 'consecutive':
            df = self.df_consecutive(df)
            nstep = 2
        else:
            nstep = len(self.analyze_sequence)

        if len(df.loc[df['st'] == 'init']) == 0:
            initialized_run = df.groupby(['run', 'sm']).agg({'digital': np.sum}) > -10  # Always true
        else:
            initialized_run = df[df['st'] == 'init'].groupby(['run', 'sm']).agg({'digital': np.sum}) == 0
        df['valid_inits'] = initialized_run.digital.repeat(nstep).values
        return df





    def df_complete(self):
        df = self.df_extended()
        self.append_thr_a_eff(df)
        self.append_digital(df)
        df = self.append_valid_measurement(df)
        df = self.append_valid_inits(df)
        return df

    def analyze(self):
        df = self.df_complete()
        data_result = dh.Data(parameter_names=['sm', 'step', 'result_num'], observation_names=['result', 'events', 'thresholds','average_counts'],
                              dtypes=collections.OrderedDict([('result', 'float'), ('events', 'int'), ('thresholds', 'int'),('average_counts', 'float')]))
        data_result.init()
        for sm in range(self.number_of_simultaneous_measurements):
            df_step = df.loc[(df['run'] == df['run'].unique()[0]) & (df['sm'] == sm) & (df['st'] == 'result')]
            for _, df_step_i in df_step.iterrows():
                result_numbers = self.consecutive_valid_result_numbers if self.analyze_type == 'consecutive' else range(df_step_i.n_mem)
                data_result.append([collections.OrderedDict([('sm', sm), ('step', df_step_i['step']), ('result_num', rn)]) for rn in result_numbers])
                data_result.set_observations([collections.OrderedDict([('thresholds', df_step_i.thr_a)])]*len(result_numbers))
                if self.analyze_type == 'consecutive':
                    df_sub = df.loc[(df['vm'] == True) & (df['sm'] == sm)]
                    r = df_sub.loc[df_sub['st'] == 'init', 'digital'].reset_index() == df_sub.loc[df_sub['st'] == 'result', 'digital'].reset_index()
                    r['index'] = df_sub.loc[df_sub['st'] == 'init', 'digital'].values
                    r = r.groupby(['index']).agg(['count', 'mean'])
                    r.columns = r.columns.droplevel(0)
                    for result_num, row in r.iterrows():
                        data_result.df.loc[(data_result.df.sm==sm) &
                                           (data_result.df.step==df_step_i['step']) &
                                           (data_result.df.result_num==result_num), ['result', 'events']] = r.loc[result_num, ['mean', 'count']].values
                    for k, v in data_result.dtypes.items():
                        data_result.change_column_dtype(k, new_dtype=v)
                else:
                    df_sub = df.loc[(df['vm'] == True) & (df['sm'] == sm) & (df['st'] == 'result')]
                    if df_sub.run.nunique() > 0:
                        data_result.df.events = df_sub.run.nunique()
                        bins = np.arange(-.5, df_sub.n_mem.iloc[0] + .5)
                        data_result.set_observations([collections.OrderedDict([('result', result)]) for result in df_sub['digital'].value_counts(normalize=True, bins=bins, sort=False).values])


                        # Add here average number of photons for another df_sub
                        # np.mean(df[(df['st'] == 'result') & (df['sm'] == sm)][0])
                        # if we have init or
                        # np.mean(df[(df['sm'] == sm)][0])
                        # if we dont have init
                        # np.mean(df[(df['st'] == 'result') & (df['sm'] == sm)][0])
                        # df_sub1 = df[(df['sm'] == sm)]

                        df_sub1 = df.loc[(df['valid_inits'] == True) & (df['sm'] == sm) & (df['st'] == 'result')]
                        data_result.set_observations([collections.OrderedDict([('average_counts', np.mean(df_sub1[0]))])])

        if self.average_results:
            data_result.eliminate_parameter(parameter_name='result_num', observation_names=['result', 'events', 'thresholds'],
                                            operations=[dh.weight_mean(data_result.df['events']), np.sum, np.mean])
        return data_result

    def analyze_hmm(self, tau_d=1, tau_b=0.1, low=None, high=None, dt=1, f_print=True, f_plot=False, filename=None):
        from . import HMM
        A = [[np.exp(-dt / tau_d), 1 - np.exp(-dt / tau_d)],
             [1 - np.exp(-dt / tau_b), np.exp(-dt / tau_b)]]
        result = HMM.run_prog(self.trace, dt, A=A, low=low, high=high, f_print=f_print, f_plot=f_plot)
        if filename is not None and filename != '':
            HMM.save_all(result, None, os.path.splitext(filename)[0])
        return result

    def parameter_info(self):
        for pn in ['analyze_type', 'analyze_sequence', 'average_results', 'number_of_simultaneous_measurements', 'binning_factor', 'consecutive_valid_result_numbers']:
            print("{}: {}".format(pn, getattr(self, pn)))

#class Trace_charge(Trace):

#    def fit_switching_poissonian(self, tr):

        #TODO: put here your switching fit code.

#    if __name__ == '__main__':
#      trp = TraceRep(trace=a, analyze_sequence=pi3d.gated_counter.trace.analyze_sequence, analyze_type=pi3d.gated_counter.trace.analyze_type, number_of_simultaneous_measurements=1)
#      trace = np.array(trp.df.groupby(['run', 'sm', 'step', 'memory']).agg({'n': np.sum}).reset_index().n)
#      tr = Trace(trace=trace, analyze_sequence=trp.analyze_sequence, analyze_type = trp.analyze_type, number_of_simultaneous_measurements=trp.number_of_simultaneous_measurements)
#      self = tr
 #     self.analyze()