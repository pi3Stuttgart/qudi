# import matplotlib
# matplotlib.use('Qt5Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, itertools, collections, lmfit

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

from .qutip_enhanced import *
from . import analyze
from . import coordinates
#from . import nv_hamilton
from . import sequence_creator
from . import sequence_creator as sc
#from . import dynamo_helpers
from . import qtgui
from . import data_handling
from . import data_handling as dh
from . import data_generation
from . import data_generation as dg
from . import qutrit_sensing
from . import lmfit_models
from . import pddata
from . import pdplotddata
