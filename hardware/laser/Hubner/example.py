import cwave
import time

# create device handle
cw = cwave.CWave()
# connect to device
cw.connect('192.168.202.22')
# The C-WAVE laser only accepts one connection at a time, but you can
# connect to 'localhost' while beeing connected via C-WAVE Control
# to use both your python program and C-WAVE Control in parallel
# via C-WAVE Control's connection multiplexing feature:
#cw.connect('localhost')

# dial IR wavelength 1100nm but also request SHG for 550nm
cw.dial(1100, True)
# give device some time to update its status bits
time.sleep(3)
# poll until both OPO_LOCK and SHG_LOCK are green
while not cw.get_dial_done():
    time.sleep(1)

###############################################
# DEVICE HAS NOW REACHED DESTINATION WAVELENGTH
###############################################

#
# Using the integrated signal generator to scan:
#
# configure settings (100ms Period, Triangle, 20% to 70%):
cw.set_opo_extramp_settings(100, cwave.ExtRampMode.Triangle, 20, 70)
# use signal generator on opo
cw.set_piezo_mode(cwave.PiezoChannel.Opo, cwave.PiezoMode.ExtRamp)

# sleep 10s
time.sleep(10)

#
# Moving the opo piezo manually via loop with wait time::
#
cw.set_piezo_manual_output(cwave.PiezoChannel.Opo, 0)
cw.set_piezo_mode(cwave.PiezoChannel.Opo, cwave.PiezoMode.Manual)
for value in range(0, 65535+1, 100):
    # valid output values are: 0 - 65535
    cw.set_piezo_manual_output(cwave.PiezoChannel.Opo, value)
    print('Manual Output Value: {} / {}%'.format(value, int(value/65535*100)))
    time.sleep(0.1)