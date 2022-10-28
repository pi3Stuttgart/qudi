import time
from core.connector import Connector
from logic.generic_logic import GenericLogic
from PyQt5 import QtCore

import numpy as np

class TestLogic(GenericLogic):

    sigUpdateLabel = QtCore.Signal()
    sigRunAgain=QtCore.Signal()

    def __init__(self, config,**kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self): #TODO this method should be on_activate
        self.value=1
        self.sigRunAgain.connect(self.run,type=QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        self.running=False
        pass

    @QtCore.pyqtSlot()
    def start(self):
        print("starting in logic")
        self.cter=0
        self.running=True
        self.sigRunAgain.emit()
        print('MyObject signal thread (logic start):', str(int(QtCore.QThread.currentThreadId())))
        

    @QtCore.pyqtSlot()
    def run(self):
        if self.running:
            self.cter+=1
            time.sleep(0.5)
            print("running")
            self.value=np.random.random()
            self.sigUpdateLabel.emit()
            print('MyObject signal thread (before emit) (running '+str(self.cter)+'):', str(int(QtCore.QThread.currentThreadId())))
            self.sigRunAgain.emit()
            print('MyObject signal thread (after emit) (running '+str(self.cter)+'):', str(int(QtCore.QThread.currentThreadId())))

    @QtCore.pyqtSlot()
    def stop(self):
        print("stoping in logic")
        self.running=False
        print('MyObject signal thread (logic stop):', str(int(QtCore.QThread.currentThreadId())))
