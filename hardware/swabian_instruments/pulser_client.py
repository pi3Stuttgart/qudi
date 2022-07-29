from qtpy import QtCore


from core.module import Base
from core.configoption import ConfigOption
#from core.pi3_utils import delay
from logic.generic_logic import GenericLogic


import socket
import numpy as np
# try:
#     import cPickle as pickle
# except:
import pickle
import time

def connect(func):
    def wrapper(self, *arg, **kw):
        try:
            # Establish connection to TCP server and exchange data
            self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_client.connect((self.host_ip, self.server_port))
            res = func(self, *arg, **kw)
        finally:
            self.tcp_client.close()
        return res
    return wrapper
    
class PulserClient(Base):
    sig_send_request = QtCore.Signal(str, str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
        pass

    def on_activate(self):
        self.host_ip, self.server_port = "localhost", 1243
        self.sig_send_request.connect(self.send_request, QtCore.Qt.QueuedConnection)

    @connect
    @QtCore.Slot(str, str)
    def send_request(self, request, action=None):
        action = None if action == '' else action
        self.tcp_client.sendall(request.encode())
        try:
            received = self.tcp_client.recv(1024) #TODO add length header and listen only to the specified bits!
        except EOFError as e:
            raise e

        flag = received[:1].decode()
        response = pickle.loads(received[1:], encoding='latin1')
        
        if flag == 'c':
            #get wavelength
            self.wlm_time = np.vstack((self.wlm_time, response))
            return response[0]
        elif flag == 'k':
            if action != None:
                msg = pickle.dumps(action, protocol=2)
                self.tcp_client.sendall(msg)
            else:
                print("Set action! ")
        elif flag == 'u':
            return response
    
    def on_deactivate(self):
        pass
        # self.tcp_client.close()

    def laser_on(self):
        return self.send_request('laser_on')
    def laser_off(self):
        return self.send_request('laser_off')

    def set_channel_on(self, channels=['ch2', 'ch3']):
        return self.send_request("set_channel_on", action=channels)

    def set_channel_off(self, channels=['ch2', 'ch3']):
        return self.send_request("set_channel_off", action=channels)