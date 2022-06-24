# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type

import subprocess
import shutil
import os
import time


old = r"C:\Users\Basti\AppData\Local\Swiss Academic Software\Citavi"
new = "D:\Sonstiges"

def unlock(path):
    subprocess.call(["C:\Program Files\LockHunter\LockHunter.exe",  "/silent", "/unlock", "/kill", path], shell=True)
    time.sleep(3)

unlock(old)
nf = os.path.join(new, os.path.basename(old))
src_exists = os.path.exists(old)
dst_exists = os.path.exists(nf)
if not (src_exists ^ dst_exists):
    raise Exception('Error: Source XOR target directory must exist. ')
if src_exists:
    shutil.move(old, nf)
subprocess.call(['mklink',  "/J", old, nf], shell=True)

