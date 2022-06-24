from __future__ import print_function, absolute_import, division
from imp import reload

from pi3diamond import pi3d
import numpy as np
import os
import UserScripts.helpers.sequence_creation_helpers as sch

reload(sch)
import multi_channel_awg_seq as MCAS

reload(MCAS)
import UserScripts.helpers.snippets_awg as sna

reload(sna)
import AWG_M8190A_Elements as E
import copy
from collections import OrderedDict
from qutip_enhanced import *

seq_name = os.path.basename(__file__).split('.')[0]
nuclear = sch.create_nuclear(__file__)
with open(os.path.abspath(__file__).split('.')[0] + ".py", 'r') as f:
    meas_code = f.read()

######################################################################################################
# init
######################################################################################################
######################################################################################################
# readout
######################################################################################################
_WAVE_FILE_DICT_ = {'14N0': r"D:\Python\pi3diamond\UserScripts\Robust\test_c14nnote_performance\20160717pulses14N\20160719-h17m28s52C10ROT0y0.5T1.5n37e7.5e-06\fields.dat",
                    '14N+1': r"D:\Python\pi3diamond\UserScripts\Robust\test_c14nnote_performance\20160717pulses14N\20160719-h17m28s52C11ROT0y0.5T1.5n37e7.7e-06\fields.dat",
                    }
wfd = dict()
for key, val in _WAVE_FILE_DICT_.items():
    wfd[key] = E.WaveFile(filepath=val,
                          rp=pi3d.tt.rp('e_rabi', mixer_deg=-90))

deltaf = np.diff([pi3d.tt.t(t).current_frequency for t in ['14n+1 ms0', '14n+1 ms-1']])[0]
Azz = {'tau': deltaf, 'small': deltaf, 'big': deltaf}

cnot_phase_dict = {'sbs': 0.0, 'b': 2.76 + 1.9}
Azz_factor = {'tau': .5, 'small': 1, 'big': 1} # As cnot-gate freq is (freq14n+1 + freq14n0)/2., only half hyperfine is active, with resonant pulses the factor is 0
nod = {
    'sbs': {'tau': 1, 'big': 1, 'small': 2},
    'b': {'tau': 1, 'big': 1, 'small': 0}
}

def ret_ret_mcas(pdc):
    def ret_mcas(current_iterator_df):

        mcas = MCAS.MultiChSeq(seq_name=seq_name, ch_dict={'2g': [1, 2], '128m': [1]})
        for idx, _I_ in current_iterator_df.iterrows():
            wait_rf_mw = _I_['wrfmw']

            def wrfmw():
                mcas.asc(length_mus=wait_rf_mw)

            def wrfmw_fix():
                mcas.asc(length_mus=0.5)

        # readout
            def ret_tau4():
                if 'tau_read' in _I_:
                    return E.round_length_mus_full_sample(_I_['tau_read']/4.)
                else:
                    target_Azz = pi3d.tt.get_f('13c{}_hf'.format(_I_['c13_name']))
                    task = _I_['task']
                    max_tau = {'sbs': 200., 'b': 100, 'cbc': 200, 'd': 100.}[_I_['csh_type']]
                    max_tau4 = max_tau/4.
                    periods = {'sensing': 1.0, 'cnot': 0.5}[task]
                    if target_Azz == 0.0:
                        return E.round_length_mus_full_sample(max_tau4)
                    else:
                        return E.round_length_mus_full_sample(min(max_tau4, periods / (4 * np.abs(target_Azz))))

            tau4 = ret_tau4()

            def ret_T():
                T_pi = dict()
                T_eff = dict(tau=4 * tau4)
                for key in ['small', 'big']:
                    if nod[_I_['csh_type']][key] > 0:
                        T_pi[key] = _I_['T_pi_{}'.format(key)]
                        T_eff[key] = 2*wait_rf_mw + T_pi[key]
                return T_pi, T_eff

            T_pi, T_eff = ret_T()

            n14pi2phase = dict()
            n14pi2phase['cnot'] = cnot_phase_dict[_I_['csh_type']]
            for key in ['small', 'big', 'tau']:
                if nod[_I_['csh_type']][key] > 0.0:
                    total_time = T_eff[key] * nod[_I_['csh_type']][key]
                    n14pi2phase[key] = 2 * np.pi * Azz_factor[key] * Azz[key] * total_time
            n14pi2phase['offset'] = {'sensing': 0.0, 'cnot': np.pi / 2.}[_I_['task']] + _I_['n14phaseoffset']
            n14pi2phase = np.rad2deg(sum(n14pi2phase.values()))

            def cnot(nt):
                sna.electron_rabi(mcas,
                                  name='cnot' + nt,
                                  wave_file=wfd[nt],
                                  frequencies=(pi3d.tt.mfl({'14N': [+1]}) + pi3d.tt.mfl({'14N': [0]})) / 2.,
                                  new_segment=False,
                                  mixer_deg=-90,
                                  )

            def nucrabi(type, amplitude_factor=1., phase=0.):
                length_mus_pi = T_pi[type]
                if length_mus_pi == 0.0 or 'tau_read' in _I_:
                    mcas.asc(length_mus=length_mus_pi)
                else:
                    Azz_read = pi3d.tt.get_f('13c{}_hf'.format(_I_['c13_name']))
                    freq = dict(small=pi3d.tt.t('13c ms0').current_frequency - Azz_read,
                                big=pi3d.tt.t('13c ms0').current_frequency - Azz_read - _I_['Azz_read_offset'])[type]
                    sna.nuclear_rabi(mcas,
                                     name='nuclear rabi',
                                     frequencies=np.array([freq]),
                                     amplitudes=[amplitude_factor * pi3d.tt.rp('13c{} ms-1'.format(_I_['c13_name']), period=2 * length_mus_pi).amp],
                                     length_mus=length_mus_pi,
                                     phases=np.array([phase]),
                                     new_segment=False,
                                     )

            def nuclearpi2(phase):
                amplitude = 1.0
                sna.nuclear_rabi(mcas,
                                 name='pi2' + '14N+1 mS0',
                                 frequencies=[pi3d.tt.t('14N+1 mS0').current_frequency],
                                 amplitudes=[amplitude],
                                 length_mus=pi3d.tt.rp('14N+1 mS0', amp=amplitude).pi2,
                                 phases=[phase],
                                 new_segment=False,
                                 )

            def csh_b():
                mcas.start_new_segment('dd_wf')
                wrfmw_fix()
                nuclearpi2(phase=.0)
                wrfmw_fix()
                cnot('14N0')
                mcas.asc(length_mus=2*tau4)
                cnot('14N+1')
                wrfmw()
                nucrabi(type='big')
                wrfmw()
                cnot('14N0')
                mcas.asc(length_mus=2*tau4)
                cnot('14N+1')
                wrfmw_fix()
                nuclearpi2(phase=n14pi2phase)
                wrfmw_fix()

            # sna.init_14N(mcas, new_segment=True)
            # sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14N': [+1]}), pi3d.tt.mfl({'14N': [0, -1]})], nuc='14N+1', robust=True, repetitions=500, mixer_deg=-90, step_idx=0)
            # sna.polarize_green(mcas, length_mus=0.2, new_segment=True)  # to pump back from nv0
            sna.polarize(mcas, new_segment=True)
            {'b': csh_b}[_I_['csh_type']]()
            sna.ssr(mcas, frequencies=[pi3d.tt.mfl({'14N': [+1]}), pi3d.tt.mfl({'14N': [0]}), pi3d.tt.mfl({'14N': [-1]})], nuc='14N+1', robust=True, mixer_deg=-90, step_idx=0)
        return mcas

    return ret_mcas


def settings(pdc={}):
    ana_seq = [
        ['result', '<', 0, 456, 0, 2],
    ]
    sch.settings(
        nuclear=nuclear,
        ret_mcas=ret_ret_mcas(pdc),
        analyze_sequence=ana_seq,
        pdc=pdc,
        meas_code=meas_code
    )
    nuclear.odmr_interval = 30
    nuclear.refocus_interval = 1
    nuclear.maximum_odmr_drift = 0.04
    nuclear.refocus_moving_average_factor = 1

    pi3d.gated_counter.n_values = 1200 * 1500
    pi3d.gated_counter.n_values = pi3d.gated_counter.n_values - pi3d.gated_counter.n_values % pi3d.gated_counter.trace.binning_factor
    pi3d.gated_counter.trace.analyze_type = 'consecutive'
    pi3d.gated_counter.trace.average_results = True
    pi3d.gated_counter.trace.consecutive_valid_result_numbers = [0, 1]

    nuclear.parameters = OrderedDict(
        (
            ('sweeps', range(5)),
            ('wrfmw', [0.5]),
        #readout
            ('task', ['sensing']),
            ('csh_type', ['b']),
            ('c13_name', ['414', '90', '13', '6']),
            # ('c13_name', ['414']),
            # ('tau_read', [0.0]),
            ('Azz_read_offset', np.arange(-0.002, 0.002+1e-8, 0.0001)),
            # ('Azz_read_offset', [0.025]),
            # ('T_pi_small', [300.]),
            ('T_pi_small', [0.]),
            ('T_pi_big', [1000.]),
            # ('T_pi_big', [0.0]),
            # ('T_pi_big', np.arange(0.0, 5000., 25.)),
            ('n14phaseoffset', [0.0, np.pi]),
            # ('n14phaseoffset', np.linspace(0.0, 2*np.pi, 9)),
        )
    )

    nuclear.number_of_simultaneous_measurements = 2
    nuclear.file_path = 'D:/data/nuclearOPs/parameters/nuclear_parameters/nuclear_sweep_csh'
    if len(nuclear.parameters['n14phaseoffset'])<= 2:
        nuclear.pld.custom_model = lmfit_models.SincModel(rabi_frequency=.5/nuclear.parameters['T_pi_big'][0], vary_rabi_frequency=False, negative=False)
    for c in nuclear.parameters['c13_name']:
        nuclear.file_notes += "13c{} ms-1\t{}\n".format(c, pi3d.tt.t("13c{} ms-1".format(c)).current_frequency)

def run_fun(abort, **kwargs):

    nuclear.debug_mode = False
    settings()
    nuclear.run(abort)

    if not nuclear.debug_mode and not abort.is_set():
        fd = dict()
        nuclear.pld.x_axis_parameter_list.update_selected_data(['Azz_read_offset'])
        nuclear.pld.subtract_parameter_list.update_selected_data(['n14phaseoffset'])
        nuclear.pld.update_data_fit_results()
        for idx, _I_ in nuclear.pld.data_fit_results.df.iterrows():
            fd[pi3d.tt.correct_transition_name('13c{} ms-1'.format(_I_['c13_name']))] = pi3d.tt.t('13c{} ms-1'.format(_I_['c13_name'])).current_frequency - _I_['center']
        pi3d.tt.change_transition_frequency(fd, test_mode=False)


# fit_result_list = []
# for d, d_idx, idx, df in data.iterator(column_names=['transition']):
#     print(d)
#     dfagg = df.groupby(['transition', 'x']).agg({'result_0': np.mean}).reset_index()
#     x = np.array(dfagg.x)
#     y = np.array(dfagg.result_0)
#     mod = lmfit_models.SincModel(rabi_frequency=pdc['max_rabi_freq'], negative=True)
#     params = mod.guess(data=y, x=x)
#     fit_result_list.append(mod.fit(y, params=params, x=x))
#     fd[pi3d.tt.correct_transition_name(d['transition'])] = pi3d.tt.t(d['transition']).current_frequency + fit_result_list[-1].params['center'].value
# pi3d.tt.change_transition_frequency(fd, test_mode=False)