from __future__ import print_function, absolute_import, division
__metaclass__ = type

import os
from .elements import __BLM__
#: PXI0::13-0.0::INSTR
#	SCPI Access (HiSLIP): TCPIP0::localhost::hislip0::INSTR
#	SCPI Access (VXI-11): TCPIP0::localhost::inst0::INSTR
#	SCPI Access (Socket): TCPIP0::localhost::5025::SOCKET
settings_folder = os.path.join(os.path.dirname(__file__), 'hardware_settings')
ch_dict_full = {'2g': [1, 2],'ps':[1]}
ch_dict_awgs = {'2g': [1, 2]}
awg_instrument_adress = {'2g': 'TCPIP0::localhost::inst0::INSTR',
                         # 'ps':'http://169.254.8.2:8050/json-rpc'}
                          'ps':'129.69.46.36'}
master_awg = '2g'
master_trigger_channel = 1
restore_awg_settings = True

# optional settings
#marker_alias = {'memory': ['2g', 1, 'smpl'], 'green': ['2g', 2, 'smpl'], 'gate': ['2g', 2, 'sync'], 'red': ['128m', 1, 'sync'], 'infrared': ['128m', 1, 'smpl']}
# marker_alias = {'memory': ['2g', 1, 'smpl',None],
#                 'green': ['2g', 2, 'smpl',None],
#                 'gate': ['2g', 2, 'sync',None],
#                 'ple_trigger':['ps',1,'ple_trigger','0'],
#                 'aom_Ex': ['ps',1,'aom_Ex','3'],
#                 'aom_A1': ['ps',1,'aom_A1','6'],
#                 'repump': ['ps',1,'repump','7'],
#                 'sync_tt': ['ps',1,'sync_tt','5']
#                 }

# marker_alias = {'memory': ['2g', 2, 'sync',None],
#                 'green': ['2g', 2, 'smpl',None],
#                 'gate': ['2g', 1, 'smpl',None],
#                 'ple_trigger':['ps',1,'ple_trigger','0'],
#                 'aom_Ex': ['ps',1,'aom_Ex','3'],
#                 'aom_A1': ['ps',1,'aom_A1','6'],
#                 'repump': ['ps',1,'repump','7'],
#                 'sync_tt': ['ps',1,'sync_tt','5']
#                 }

marker_alias = {
                # 'memory': ['2g', 2, 'sync',None],
                # 'aom_Ex': ['2g', 2, 'smpl',None],
                # 'gate': ['2g', 1, 'smpl',None],
                'FlipMirror':['ps',1,'FlipMirror','0'],
                'A2':['ps',1,'A2','1'],
                'repump': ['ps',1,'repump','2'],
                'green': ['ps',1,'green','3'],
                #ch4 is clock to AWG
                'A1':['ps',1,'A1','5'],
                'gate': ['ps',1,'tt_sync','7'],
                'memory': ['ps',1,'tt_trigger','6'],
                'tt_sync': ['ps',1,'tt_sync','6'],
                'tt_trigger': ['ps',1,'tt_trigger','7']
                }



max_sine_avg_power = {'2g': {1: None, 2: None}}
amplifier_power = {'2g': {1: 5., 2: 5.}}
# TODO: WHAT IS THIS?

####################################################################################################################################
# internal settings
####################################################################################################################################
trigger_delay_length_mus = 27 * __BLM__ # the awg has a fixed trigger delay (sample clock dependent) of ~< 1mus
trigger_length_mus = 27 * __BLM__ # duration of trigger sent to the slave awgs. Must not be longer __TRIGGER_DELAY_LENGTH_MUS__
slave_trigger_safety_length_mus = 32 * __BLM__ # after __MASTER_AWG__ finishes its sequence, it waits this time until it starts over and sends a new trigger
slave_start_delay = trigger_length_mus *1000 - 54 # delay for the PulseStreamer slave to be synchronized with a master

