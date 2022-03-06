from qtpy import QtCore


from core.module import Base
from core.configoption import ConfigOption
from core.pi3_utils import delay
from logic.generic_logic import GenericLogic


import socket
import numpy as np
try:
    import cPickle as pickle
except:
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

    
class TimeTaggerClient(Base):
    _corr = ConfigOption('corr', False, missing='warn')
    _counter = ConfigOption('counter', False, missing='warn')
    _combiner = ConfigOption('combiner', False, missing='warn')
    _channels_params = ConfigOption('channels_params', False, missing='warn')
    _maxDumps =  ConfigOption('maxDumps', 1000000000, missing='warn')

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
            received = self.tcp_client.recv(10000) #TODO add length header and listen only to the specified bits!
        except EOFError as e:
            raise e
        # response = pickle.loads(, encoding='bytes')
        # out_s = StringIO()
        response = pickle.loads(received[1:])#, 'latin-1'))
 
        flag = received[:1].decode()
        if flag == 'c':
            #get wavelength
            self.wlm_time = np.vstack((self.wlm_time, response))
            return response[0]
        elif flag == 'k':
            if action != None:
                msg = pickle.dumps(action, protocol=pickle.HIGHEST_PROTOCOL)
                self.tcp_client.sendall(msg)
            else:
                print("Set action! ")
        elif flag == 'u':
            return response
    
    def on_deactivate(self):
        self.tcp_client.close()
    # setExposure(self, exposureTime):
        # return self.send_request("set_exposure_time", action=str(exposureTime* 1000))
    def set_counter(self):
        return self.send_request("set_counter", action=self._counter)

    def get_counter(self):
        return self.send_request("get_counter")
        
    def get_server_time(self):
        return self.send_request("get_server_time")

    def sync_clocks(self):
        # to sync time stamps and wavelengths add delta t to the current time of the client
        times = np.array([])
        for t in range(1000):
            times = np.append(times, time.time() - self.get_server_time())
            delay(0.25)
        return times.mean()