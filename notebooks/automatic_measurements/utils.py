from time import sleep
import json
import os

def delay(delay_msec = 100):
    dieTime = QtCore.QTime.currentTime().addMSecs(delay_msec)
    while (QtCore.QTime.currentTime() < dieTime):
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 100)
def flip_powermirror():
    pulser.set_channel_off(['ch5'])
    pulser.set_channel_on(['ch5'])


def calibrate(steps = [240, 280, 300, 320, 360]):
    calibration = {}
    for step in steps:
        motor_pi3.moveToAbsolutePosition(motor=0, pos=step)
        delay(3000)
#         flip_powermirror()
        delay(2000)
        for i in range(2):
            try:
                pwr = powermeter.get_power() * 1e6
            except:
                pass
            delay(200)
#         flip_powermirror()
        calibration.update({step:pwr})
    return calibration
