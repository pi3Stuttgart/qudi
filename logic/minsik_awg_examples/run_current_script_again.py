from __future__ import print_function, absolute_import, division

from pi3diamond import pi3d
import copy

s = copy.deepcopy(pi3d.current_script)

def run_fun(abort, **kwargs):
    pi3d.add_to_queue(s['name'], pd=s['pd'], folder=s['folder'])