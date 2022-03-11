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

    
class TimeTaggerClient(Base):
    _corr = ConfigOption('corr', False, missing='warn')
    _counter = ConfigOption('counter', False, missing='warn')
    _combiner = ConfigOption('combiner', False, missing='warn')
    _channels_params = ConfigOption('channels_params', False, missing='warn')
    _maxDumps =  ConfigOption('maxDumps', 1000000000, missing='warn')

    sig_send_request = QtCore.Signal(str, str)

    queryInterval = ConfigOption('query_interval', 50)
    sigUpdate = QtCore.Signal()


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
        self.countrate = np.array([1])
        

    def on_activate(self):
        self.host_ip, self.server_port = "localhost", 1244
        self.sig_send_request.connect(self.send_request, QtCore.Qt.QueuedConnection)
        self.stopRequest = False
        
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.query_loop, QtCore.Qt.QueuedConnection)
        self.set_counter()
        self.start_query_loop()

    @QtCore.Slot()
    def query_loop(self):
        """ Get power, current, shutter state and temperatures from laser. """
        if self.stopRequest:
            if self.module_state.can('stop'):
                self.module_state.stop()
            self.stopRequest = False
            return
        qi = self.queryInterval
        try:
            
            if self._counter is not None:
                
                self.countrate = self._get_counter()
        except:
            qi = 3000
            self.log.exception("Exception in laser status loop, throttling refresh rate.")

        self.queryTimer.start(qi)
        self.sigUpdate.emit()

    @QtCore.Slot()
    def start_query_loop(self):
        """ Start the readout loop. """
        self.module_state.run()
        self.queryTimer.start(self.queryInterval)

    @QtCore.Slot()
    def stop_query_loop(self):
        """ Stop the readout loop. """
        self.stopRequest = True
        for i in range(10):
            if not self.stopRequest:
                return
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.queryInterval/1000)


    @connect
    @QtCore.Slot(str, str)
    def send_request(self, request, action=None):
        action = None if action == '' else action
        
        self.tcp_client.sendall(request.encode())
        try:
            received = self.tcp_client.recv(50000) #TODO add length header and listen only to the specified bits!
        except EOFError as e:
            raise e
        # response = pickle.loads(, encoding='bytes')
        # out_s = StringIO()
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
        self.tcp_client.close()
        self.stop_query_loop()
        for i in range(5):
            time.sleep(self.queryInterval / 1000)
            QtCore.QCoreApplication.processEvents()
    # setExposure(self, exposureTime):
        # return self.send_request("set_exposure_time", action=str(exposureTime* 1000))
    def set_counter(self, counter_params=None):
        if counter_params is None:
            counter_params = self._counter
        counter_params['n_vals'] = 1000 #bigg buffer
        return self.send_request("set_counter", action=counter_params)

    def set_correlation(self, corr_params=None):
        if corr_params is None:
            corr_params = self._corr
        return self.send_request("set_correlation", action=corr_params)

    def get_correlation(self):
        return self.send_request("get_correlation")

    def _get_counter(self):
        return self.send_request("get_counter")
    def get_counter(self):
        return np.array([[cc[-1]] for cc in self.countrate])
        
    def get_server_time(self):
        return self.send_request("get_server_time")

    def get_combined_channels(self):
        return self.send_request("get_combined_channels")

    def set_combined_channels(self, channels = [0,1]):
        return self.send_request("set_combined_channels", action=channels)

    def reset_time_tagger(self):
        return self.send_request("reset_time_tagger")

    def set_count_between_markers(self, params=None):
        if params is None:
            print("SET THE PARAMS")
            return 
        self.send_request("set_count_between_markers", action = params)

    def get_count_between_markers(self):
        return self.send_request("get_count_between_markers")

    def sync_clocks(self):
        # to sync time stamps and wavelengths add delta t to the current time of the client
        times = np.array([])
        for t in range(1000):
            times = np.append(times, time.time() - self.get_server_time())
            delay(0.25)
        return times.mean()