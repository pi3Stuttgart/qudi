# coding=utf-8
from __future__ import print_function, absolute_import, division

__metaclass__ = type

from .pddata import *
from .pdplotddata import *

def cpd():
    hdfl = [fn for fn in os.listdir(os.getcwd()) if fn.endswith('.hdf')]
    if not 'data.hdf' in hdfl and len(hdfl) != 1:
        raise Exception('Error: No hdf file found in files {}'.format(os.listdir(os.getcwd())))
    data = Data(iff=os.path.join(os.getcwd(), hdfl[0]))
    if 'prepare_data.py' in os.listdir(os.getcwd()):
        from prepare_data import prepare_data
        data = prepare_data(data)
    out = PlotData(data=data)
    if 'sweeps' in data.parameter_names:
        out.x_axis_parameter_list.update_selected_indices(out.x_axis_parameter_list.selected_indices_default(exclude_names=['sweeps']))
        out.average_parameter_list.update_selected_data(['sweeps'])
    if any(['result_' in out.observation_list.data]):
        out.observation_list.update_selected_data([i for i in out.observation_list.data if i.startswith('result_')])
    else:
        out.observation_list.update_selected_indices([0])
    out.update_plot()
    out.gui.show_gui()
    return out


def cpd_thread():
    import threading
    out = PlotData()

    def run():

        for fn in os.listdir(os.getcwd()):
            if fn.endswith('.hdf'):
                out.set_data_from_path(fn)

        out.gui.show_gui()

    t = threading.Thread(target=run)
    t.start()


def subfolders_with_hdf(folder):
    l = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".hdf"):
                l.append(root)
    return l


def number_of_points_of_hdf_files_in_subfolders(folder, endswith='data.hdf'):
    l = subfolders_with_hdf(folder)
    out_openable = []
    out_failed = []
    for subdir in l:
        for root, dirs, files in os.walk(subdir):
            for file in files:
                if file.endswith(endswith):
                    try:
                        d = Data(iff=os.path.join(root, file))
                        out_openable.append({'root': root, 'file': file, 'points': len(d.df)})
                    except:
                        out_failed.append({'root': root, 'file': file})
    return out_openable, out_failed


def hdf_files_in_subfolders_with_less_than_n_points(folder, n):
    out_openable, out_failed = number_of_points_of_hdf_files_in_subfolders(folder)
    out_smaller = [i for i in out_openable if i['points'] < n]
    out_larger_equal = [i for i in out_openable if i['points'] >= n]
    return out_smaller, out_larger_equal, out_failed


def move_folder(folder_list_dict=None, destination_folder=None):
    import shutil
    failed = 0
    for i in folder_list_dict:
        try:
            src = i['root']
            dst = os.path.join(destination_folder, os.path.basename(i['root']))
            shutil.move(src, dst)
        except:
            failed += 1
            print("Folder {} could not be moved. Lets hope it has tbc in its name".format(i['root']))
    print("Successfully moved: {}. Failed: {}".format(len(folder_list_dict) - failed, failed))