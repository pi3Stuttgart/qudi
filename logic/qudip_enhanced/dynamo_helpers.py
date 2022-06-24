# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

import sys, os
if sys.version_info.major == 2:
    from StringIO import StringIO
else:
    from io import StringIO

try:
	import matlab.engine
except:
	print('matlab.engine could not be loaded')

from qutip_enhanced import *
import shutil
import itertools
import datetime
import time
import threading

import lmfit.lineshapes
from .qutip_enhanced import *
from . import sequence_creator

SDx = jmat(.5, 'x')  # np.array([[0.0, 1.0], [1.0, 0.0]], dtype='complex_') / 2.
SDy = jmat(.5, 'y')  # np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype='complex_') / 2.
SDz = jmat(.5, 'z')  # np.array([[1.0, 0.0], [0.0, -1.0]], dtype='complex_') / 2.
STx = jmat(1., 'x')  # np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype='complex_') / np.sqrt(2)
STy = jmat(1., 'y')  # np.array([[0.0, -1.0j, 0.0], [1.0j, 0.0, -1.0j], [0.0, 1.0j, 0.0]], dtype='complex_') / np.sqrt(2)
STz = jmat(1., 'z')  # np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, -1.0]], dtype='complex_')


def f_drift(x, fwhm, center=0.0, drift_width=0.0, f='gaussian'):
    if f == 'lorentzian':
        sigma = fwhm / 2.
    elif f == 'gaussian':
        sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    fun = getattr(lmfit.lineshapes, f)
    out = []
    for xi in x:
        if -drift_width / 2. <= xi <= drift_width / 2.:
            x = 0.0
        elif xi < drift_width / 2.:
            x = xi + drift_width / 2.
        elif xi > drift_width / 2.:
            x = xi - drift_width / 2.
        out.append(fun(x=x, sigma=sigma, center=center))
    return out


def ensemble(base, weight_base=None):
    """
    NOTE: For documentation see qutip_enhanced examples

        :param base: dict with keys ['det', 'ps']

        - base['det'] = [nparr_0, nparr_1, nparr_2, ...] for controls 0,1,2.. Each numpy array arr_i includes the detunings for one class of controls and has len(shape) = 1, e.g. mw on a specific transition or nuclear spin driving of a specific nuclear transition (e.g. 13C90 mS-1)
            Examples: 
                - [0.0]
                - [-0.2, -0.1, 0.0, 0.1, 0.2]

        base['ps'] = [nparr_a, nparr_b, nparr_c, ...], for controls 0, 1, 2 where nparr_i.shape = (number_of_powerscalings, number_of_connected_controls)
            Examples:
                - base['ps'] = [np.array([[1.]])] for a z-control, no powerscaling
                - base['ps'] = [np.array([[1., 1.]])] for x,y controls, no powerscaling
                - base['ps'] = [np.array([[.9, .9], [1., 1.], [1.1,1.1]])] for +- 10% powerscaling

    :param weight_base: dict with keys ['det', 'ps'] or None

        - weight_base['det'] 

            exactly the same form as base['det']

            Examples: 
                - base['det'] = [[0.0], [-0.1, 0.0, 0.1]] --> weight_base['det'] = [[1.0], [0.5, 1.0, 0.5]]

        - weight_base['ps']

            - len(weight_base['ps']) = len(base['ps'])
            - weight_base['ps'][i].shape = base['ps'].shape[0]

            Examples:
                - base['ps'] = [np.array([[1.]])] -> weight['ps'] = [np.array([[1.]])]
                - base['det']  = np.array([[1., 1.]]) -> weight['ps'] = [np.array([[1.]])]
                - base['det']  = np.array([[.9, .9], [1., 1.], [1.1,1.1]]) -> weight['ps'] = [np.array([[0.5, 1.0, 0.5]])]

    """
    for key, val in base.items():
        if type(val) != list:
            raise Exception(key, type(val), val)
    if not all(len(i.shape) == 1 for i in base['det']):
        raise Exception(base['det'])
    if not all([len(i.shape) == 2 for i in base['ps']]):
        raise Exception(base['ps'])
    if weight_base is None:
        weight_base = {}
        for key in base:
            weight_base[key] = []
            for idx, item in enumerate(base[key]):
                weight_base[key].append(np.ones(base[key][idx].shape[0]))

    # What this loop does:
    #   - extend weights that are [] by equal weighting
    #   - extends the weights of powerscalings to shape (n,2) such that form of base and weight_base are equal and can then be processed more easily
    #   - normalizes the weights such, that among each subweight (e.g. for electron detunings [-0.1, 0.0, 0.1] the weights are [.123, 1.0, .123])
    for key, val in weight_base.items():
        for i, item in enumerate(val):
            if key == 'det':
                if len(item) == 0:
                    weight_base[key][i] = np.ones(len(base[key][i]))
                elif len(item) != len(base[key][i]):
                    raise Exception("Error: {}, {}".format(base[key], weight_base[key]))
            elif key == 'ps':
                if len(item) == 0:
                    weight_base[key][i] = np.ones(base[key][i].shape[0])
                elif len(item) != len(base[key][i]):
                    raise Exception("Error: {}, {}".format(base[key], weight_base[key]))
                    # weight_base[key][i] = np.repeat(np.array(weight_base[key][i]).reshape(-1, 1), base[key][i].shape[1], axis=1)

        weight_base[key] = [np.array(i) / np.max(i) for i in weight_base[key]]

    ps_base = [np.hstack(i) for i in list(itertools.product(*base['ps']))]
    det_base = list(itertools.product(*base['det']))
    det = np.array(list(itertools.chain(*[(i,) * len(ps_base) for i in det_base])))
    ps = np.tile(ps_base, (len(det_base), 1))

    weight_ps_base = [np.hstack(i) for i in list(itertools.product(*weight_base['ps']))]
    weight_det_base = np.array(list(itertools.product(*weight_base['det'])))
    weight_det = np.array(list(itertools.chain(*[(i,) * len(weight_ps_base) for i in weight_det_base])))
    weight_ps = np.tile(weight_ps_base, (len(weight_det_base), 1))
    weight = np.prod(np.concatenate([weight_det, weight_ps], axis=1), axis=1)
    weight = weight / np.sum(weight)

    return det, ps, weight


class DynPython(sequence_creator.Arbitrary):

    def __init__(self, dynamo_path, initial, final, dims=None, print_flag=True, **kwargs):
        self.dims = dims
        self.eng = self.get_eng(**kwargs)
        self.dynamo_path = dynamo_path
        self.out = StringIO()
        self.err = StringIO()
        self.already_printed = ''
        self.initial = initial
        self.final = final
        self.print_flag = print_flag

    def get_eng(self, use_engine=None, desktop=False):
        if type(use_engine) == matlab.engine.matlabengine.MatlabEngine:
            print('using existing engine {}'.format(use_engine.eval('matlab.engine.engineName')))
            return use_engine
        m = matlab.engine.find_matlab()
        if use_engine is not None and use_engine in m:
            eng = matlab.engine.connect_matlab(use_engine)
            print('connected to {}'.format(use_engine))
            return eng
        mdp = [int(i[3:]) for i in m if 'dpe' in i]
        il = itertools.count()
        while True:
            n = next(il)
            if not n in mdp:
                break
        name = "dpe{}".format(n) if use_engine is None else use_engine
        print('Starting matlab engine {}..'.format(name))
        eng = matlab.engine.start_matlab("-desktop") if desktop else matlab.engine.start_matlab()
        eng.eval("matlab.engine.shareEngine('{}')".format(name), nargout=0)
        print('Done.')

        return eng

    @property
    def dims(self):
        return self._dims

    @dims.setter
    def dims(self, val):
        if not(type(val) is list or (type(val) is np.ndarray and len(val.shape) == 1)):
            raise Exception("Error: {}".format(val))
        self._dims = val

    def print_out(self):
        if self.print_flag:
            to_print = self.out.getvalue()
            print(to_print.replace(self.already_printed, '')) #dont use strip())
            self.already_printed = to_print

    @property
    def dyn(self):
        return self.eng.workspace[str("dyn")]

    def set_dyn(self, task, H_drift_list, H_ctrl_list, weight):
        self.eng.addpath(self.eng.genpath(self.dynamo_path))
        initial = matlab.double(self.initial.data.todense().tolist(), is_complex=True)
        final = matlab.double(self.final.data.todense().tolist(), is_complex=True)
        weight = matlab.double(weight.tolist())
        self._dyn = self.eng.dynamo(task, initial, final, H_drift_list, H_ctrl_list, weight, stdout=self.out, stderr=self.err)
        self.eng.workspace[str("dyn")] = self._dyn
        self.print_out()

    @property
    def n_ensemble(self):
        return int(self.eng.eval("dyn.system.n_ensemble"))

    def set_labels(self, title, c_labels):
        self.eng.eval(str("dyn.system.set_labels('{}', {}, {{{}}})").format(title, self.dims, ", ".join("'{}'".format(i) for i in c_labels)), stdout=self.out, stderr=self.err, nargout=0)

    def get_mask(self, optimize_times=False):
        return np.array(self.eng.full_mask(self.dyn, int(optimize_times)))

    def seq_init(self, TL, control_type, control_par):
        self.eng.seq_init(self.dyn, len(self.sequence), matlab.double(TL.tolist()), control_type, control_par, stdout=self.out, stderr=self.err, nargout=0)
        self.print_out()

    def set_fields(self, fields):
        fields = matlab.double(np.array(fields, dtype=np.complex64).tolist(), is_complex=True)
        self.eng.set_controls(self.dyn, fields, stdout=self.out, stderr=self.err, nargout=0)
        self.print_out()

    def set_projector(self, bin, P=None, n_ens=None, clear_workspace=True):
        self.eng.workspace["Projector_from_python"] = matlab.double(np.array(P, dtype=np.complex64).tolist(), is_complex=True)
        n_ens_list = range(1, self.n_ensemble+1) if n_ens is None else [n_ens+1]
        for n_ens in n_ens_list:
            self.eng.eval("dyn.cache.set_P({}, {}, Projector_from_python)".format(bin+1, n_ens), nargout=0)
        # if clear_workspace:
        #     self.eng.eval("clear({Projector_from_python})", nargout=0)


    def open_ui(self):
        self.eng.ui_open(self.dyn, nargout=0)

    def search_thread(self, mask, options=None, dt=2., dt_walltime=120., stop_too_bad_fun=None, abort=None, kill=None):
        options = {} if options is None else options
        mask = matlab.logical(mask.tolist())

        def run():
            if 'max_walltime' in options:
                n = range(int(options['max_walltime'] / dt))
                options['max_walltime'] = dt
                t0 = time.time()
                for _ in n:
                    if abort is not None and abort.is_set(): break
                    if kill is not None and kill.is_set(): break
                    self.eng.search(self.dyn, mask, options, stdout=self.out, stderr=self.err, nargout=0)
                    frob_norm = np.sqrt(2 * self.eng.compute_error(self.dyn) * self.eng.eval("dyn.system.norm2"))
                    print(self.eng.eval('dyn.stats{end}.term_reason'))
                    elapsed_time = time.time() - t0
                    if stop_too_bad_fun is not None and elapsed_time > dt_walltime:
                        if frob_norm > stop_too_bad_fun(elapsed_time):
                            s1 = 'Final'
                        else:
                            s1 = 'Current'
                    else:
                        s1 = 'Current'
                    print("{} Frobenius norm: {} ({}), t={}s".format(s1, frob_norm, stop_too_bad_fun(elapsed_time), elapsed_time))
                    if s1 == 'Final' or self.eng.eval('dyn.stats{end}.term_reason') != "Wall time limit reached": break

        t = threading.Thread(target=run)
        t.start()
        return t

    def search(self, mask, options=None):
        options = {} if options is None else options
        mask = matlab.logical(mask.tolist())
        self.eng.search(self.dyn, mask, options, nargout=0)

    def X(self, n_ens, include_initial=True, include_final=True):
        out = []
        for i in range(1, n_ens + 1):
            out.append([])
            if include_initial:
                out[-1].append(Qobj(self.initial))
                if out[-1][-1].isket:
                    out[-1][-1] = ket2dm(out[-1][-1])
                out[-1][-1].dims = [self.dims, self.dims]
            for j in range(1, self.n_bins + 1):
                out[-1].append(Qobj(np.array(self.eng.eval('dyn.X({}, {})'.format(j, i)))))
                if out[-1][-1].isket:
                    out[-1][-1] = ket2dm(out[-1][-1])
                out[-1][-1].dims = [self.dims, self.dims]
            if include_final:
                out[-1].append(Qobj(self.final))
                if out[-1][-1].isket:
                    out[-1][-1] = ket2dm(out[-1][-1])
                out[-1][-1].dims = [self.dims, self.dims]
        return out

    @property
    def times_full(self):
        return np.array(self.eng.eval("dyn.export"))[:, 0]

    @property
    def fields_full(self):
        return 2 * np.pi*np.array(self.eng.eval("dyn.export"))[:, 1:]

    def save_matlab_output(self, path):
        with open(path, "w") as f:
            f.write(self.out.getvalue())
        print("matlab_output saved.")

    def save_script_code(self, path, script_code):
        if script_code != None:
            with open(path, "w") as text_file:
                text_file.write(script_code)
            print("script_code saved.")

    def save_notebook(self, path, script_path):
        sp, file_extension = os.path.splitext(script_path)
        dp = path# + os.path.splitext(os.path.basename(script_path))[0]
        if file_extension == '.ipynb':
            shutil.copy(sp + '.ipynb', dp + '.ipynb')
            shutil.move(sp + '.html', dp + '.html')
            shutil.move(sp + '.py', dp + '.py')

    def save_matlab_workspace(self, path):
        self.eng.save(path, nargout=0)

    def save_gates(self, path):

        gates = [Qobj(np.array(self.eng.eval('dyn.X({}, 1)'.format(i))), dims=[self.dims]*2) for i in range(1, self.n_bins + 1)]
        qsave(gates, path)
        print("gates saved as *.qu -file.")

    def save(self, script_path=None, dns=None, script_code=None, substr=None, save_notebook=False):
        if dns is None:
            filename, file_extension = os.path.splitext(script_path)
            if file_extension == '.ipynb':
                script_path = script_path.split('.')[0] + '.ipynb'
            else:
                script_path = script_path.split('.')[0] + '.py'
            dn = os.path.dirname(script_path)
            dns = dn + '\\' + datetime.datetime.now().strftime('%Y%m%d-h%Hm%Ms%S') + substr
        if not os.path.isdir(dns):
            os.makedirs(dns)
        self.save_script_code(dns + '\\' + os.path.basename(script_path), script_code)
        if save_notebook:
            self.save_notebook(dns, script_path)
        self.save_matlab_workspace(dns + "\\workspace.mat")
        self.save_matlab_output(path=dns+"\\matlab_output.dat")
        self.save_gates(path=dns+"\\gates")
        save_qutip_enhanced(os.path.join(dns))
        # import qutip_enhanced
        # shutil.copytree(os.path.dirname(qutip_enhanced.__file__), dns + '\\qutip_enhanced')
        # print("qutip_enhanced saved.")
        self.save_dynamo_fields(directory=dns)
        # self.save_export_mask(path=dns+"\\export_mask.dat")
        self.save_export_sequence_steps(path=dns + "\\sequence_steps.dat")
        return dns

def rotop(*args, **kwargs):
    return 2*np.pi*get_rot_matrix_all_spins(*args, **kwargs).data.todense()

def load(eng, directory):
    """
    :param directory: directory in which mat file and script and so on lies
    :return:
    """
    eng.addpath(eng.genpath(directory))