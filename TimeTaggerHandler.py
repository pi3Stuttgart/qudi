# coding=utf-8
__metaclass__ = type
import sys
import ctypes
sys.path.append(r"C:\Program Files (x86)\SwabianInstruments\TimeTagger\win64\python27")
import TimeTagger
import zmq
import multiprocessing
import cPickle as pickle
import tblib.pickling_support
tblib.pickling_support.install()
import traceback
import collections
import psutil
import socket

TimeTagger_channel_map = dict(apd0=0,
                              apd_ZPL=4,
                              ssr_trigger=3,
                              freq_swap_trigger=2)


__SERVER_PORT__ = "5560"
__DEVICE_PORT__ = "5559"

class TimeTaggerProxy():
    def __init__(self):
        context = zmq.Context()
        print("Connecting to server...")
        self.socket = context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:%s" % __DEVICE_PORT__)

    def communicate(self, inc):
        if inc == 'killme':
            self.socket.send(pickle.dumps({'killme':True}))
            return

        if not 'args' in inc:
            inc['args'] = []
        if not 'kwargs' in inc:
            inc['kwargs'] = {}
        self.socket.send(pickle.dumps(inc))
        out = pickle.loads(self.socket.recv())
        if type(out) is dict and 'exc_tb' in out:
            traceback.print_exception(out['exc_type'], out['exc_value'], out['exc_tb'])
        else:
            return out

    def init_counter(self, counter_name, **kwargs):
        self.communicate(
            dict(
                counter_name=counter_name,
                method='init_counter',
                kwargs=kwargs,
            )
        )


    def sync(self, counter_name, **kwargs):
        if self.communicate(
            dict(
                counter_name=counter_name,
                method='sync',
                kwargs=kwargs,
            )
        ) == "synced":
            return
        else:
            raise RuntimeError("Sync of timetagger failed!")

    def __getattr__(self, name):
        class CT:
            def __init__(self, outer):
                self.outer = outer
            def __getattr__(self, name2):
                if name2 in ['_ipython_canary_method_should_not_exist_', '_repr_mimebundle_', '__members__', '__methods__']: # neither IPython nor Pycharm will be able to get any information, as class is just a proxy
                    return None
                return lambda: self.outer.communicate(dict(counter_name=name, method=name2))
        return CT(self)


delayed_channel_start = None
delayed_channel_stop = None
delayed_channel_APD = None
gated_channel_APD = None



delayed_channel_start_list = {}
delayed_channel_stop_list = {}

def init_counter(kind, tagger, **kwargs):
    global delayed_channel_start
    global delayed_channel_stop
    global delayed_channel_APD
    global gated_channel_APD
    global delayed_channel_start_list
    global delayed_channel_stop_list
    # global delayed_channel_starts_list
    delayed_channel_start = None
    delayed_channel_stop = None
    delayed_channel_APD = None
    gated_channel_APD = None
    tagger.setConditionalFilter([], [])

    if kind == 'gated_counter':
        return TimeTagger.SSRTimeTrace(
            tagger,
            TimeTagger_channel_map['apd0'],
            TimeTagger_channel_map['apd_ZPL'],
            TimeTagger_channel_map['ssr_trigger'],
            TimeTagger_channel_map['freq_swap_trigger'],
            kwargs['nrows'],
            kwargs['number_of_memories'])

    if 'gated_cbm_zpl' in kind:
        if 'delay_ps' in kwargs.keys():
            # print('TimeTager delay_ps ', kwargs['delay_ps'])
            delay = int(kwargs['delay_ps'])
        else:
            delay = 0

        if 'window_ps' in kwargs.keys():
            # print('TimeTager window_ps ', kwargs['window_ps'])
            window = int(kwargs['window_ps'])
        else:
            window = 40000 #40 ns

        start_channel_name = str(delay)
        if start_channel_name in delayed_channel_start_list:
            delayed_channel_start = delayed_channel_start_list[start_channel_name]
        else:
            delayed_channel_start = TimeTagger.DelayedChannel(
                tagger=tagger,
                input_channel=TimeTagger_channel_map['ssr_trigger'],
                delay=delay
            )
            delayed_channel_start_list.update({start_channel_name:delayed_channel_start})

        vch_start = delayed_channel_start.getChannel()

        stop_channel_name = str(delay)+'_'+str(window)
        if stop_channel_name in delayed_channel_stop_list:
            delayed_channel_stop = delayed_channel_stop_list[stop_channel_name]
        else:
            delayed_channel_stop = TimeTagger.DelayedChannel(
                tagger=tagger,
                input_channel=TimeTagger_channel_map['ssr_trigger'],
                delay=delay+window
            )
            delayed_channel_stop_list.update({stop_channel_name:delayed_channel_stop})


        vch_stop = delayed_channel_stop.getChannel()


        # print('delayed_channel_stop_list ',delayed_channel_stop_list)
        # print('kind ',kind)

        return TimeTagger.CountBetweenMarkers(
            tagger,
            click_channel=TimeTagger_channel_map['apd_ZPL'],
            begin_channel=vch_start,
            end_channel=vch_stop,
            n_values=kwargs['n_values'],
        )


    if kind == 'gated_counter_countbetweenmarkers':
        # if 'delay_ps' in kwargs.keys():
        #     delay = kwargs['delay_ps'].values[0]
        # else:
        #     delay = 0
        #
        return TimeTagger.CountBetweenMarkers(
            tagger,
            click_channel=TimeTagger_channel_map['apd0'],
            begin_channel=TimeTagger_channel_map['ssr_trigger'],
            end_channel=TimeTagger_channel_map['freq_swap_trigger'],
            n_values=kwargs['n_values'],
        )

        # tagger.setTriggerLevel(2, 0.3)
        # tagger.setTriggerLevel(7, 0.3)
        # tagger.setTriggerLevel(3, 0.3)
        #tagger.setTriggerLevel(1, 0.3)
        # tagger.setConditionalFilter([TimeTagger_channel_map['apd0']],[TimeTagger_channel_map['ssr_trigger']])

        # delayed_channel_start_400 = TimeTagger.DelayedChannel(
        #     tagger=tagger,
        #     input_channel=TimeTagger_channel_map['ssr_trigger'],
        #     delay=delay
        # )
        #
        # vch1 = delayed_channel_start_400.getChannel()
        #
        # return TimeTagger.CountBetweenMarkers(
        #     tagger,
        #     click_channel=TimeTagger_channel_map['apd0'],
        #     begin_channel=vch1,
        #     end_channel=TimeTagger_channel_map['freq_swap_trigger'],
        #     n_values=kwargs['n_values'],
        # )
    elif kind == 'odmr':
        return TimeTagger.ODMR(
            tagger,
            TimeTagger_channel_map['apd0'],
            TimeTagger_channel_map['apd_ZPL'],
            TimeTagger_channel_map['ssr_trigger'],
            TimeTagger_channel_map['freq_swap_trigger'],
            kwargs['number_of_memories'])
    elif kind == 'orabi_timedifferences':
        print('orabi_timedifferences init_counter()')
        if kwargs['delay'] == 0:
            # print('kwargs[delay] ', kwargs['delay'])
            return TimeTagger.TimeDifferences(
                tagger,
                click_channel=TimeTagger_channel_map['apd0'],
                start_channel=TimeTagger_channel_map['ssr_trigger'],
                next_channel=TimeTagger_channel_map['freq_swap_trigger'],
                sync_channel=7,
                n_bins=1000,#kwargs['n_bins'],
                # binwidth=int(500), # 200 ns full length
                binwidth=int(1000), #
                n_histograms=kwargs['number_of_memories']
            )

        # tagger.setConditionalFilter([TimeTagger_channel_map['apd0']],[TimeTagger_channel_map['ssr_trigger']])

        delayed_channel_start = TimeTagger.DelayedChannel(
            tagger=tagger,
            input_channel=TimeTagger_channel_map['ssr_trigger'],
            delay=kwargs['delay']
        )

        vch1 = delayed_channel_start.getChannel()
        return TimeTagger.TimeDifferences(
            tagger,
            click_channel= TimeTagger_channel_map['apd0'],
            start_channel= vch1,
            next_channel = TimeTagger_channel_map['freq_swap_trigger'] ,
            sync_channel =7,
            n_bins=1000,#kwargs['n_bins'],
            binwidth=int(500), # 200 ns full length
            n_histograms=kwargs['number_of_memories']
        )
    elif kind == 'orabi_countbetweenmarkers':

        tagger.setTriggerLevel(2, 0.3)
        tagger.setTriggerLevel(7, 0.3)
        tagger.setTriggerLevel(3, 0.3)

        tagger.setConditionalFilter([TimeTagger_channel_map['apd0']],[TimeTagger_channel_map['ssr_trigger']])

        delayed_channel_start = TimeTagger.DelayedChannel(
            tagger=tagger,
            input_channel=TimeTagger_channel_map['ssr_trigger'],
            delay=kwargs['delay']
        )
        vch1 = delayed_channel_start.getChannel()

        return TimeTagger.CountBetweenMarkers(
            tagger,
            click_channel=TimeTagger_channel_map['apd0'],
            #click_channel=gated_clicks.getChannel(),
            begin_channel=TimeTagger_channel_map['ssr_trigger'],
            end_channel=TimeTagger_channel_map['freq_swap_trigger'],
            n_values=kwargs['n_values'],
        )
    elif kind == 'odmr_timedifferences':

        tagger.setTriggerLevel(2, 0.3)
        tagger.setTriggerLevel(7, 0.3)
        tagger.setTriggerLevel(3, 0.3)

        return TimeTagger.TimeDifferences(
            tagger,
            click_channel=TimeTagger_channel_map['apd0'],
            next_channel=TimeTagger_channel_map['freq_swap_trigger'],
            sync_channel=7,
            n_bins=1,
            binwidth=int(3*1e6), # no odmr will be accumulated for more than 100mus per step
            n_histograms=kwargs['number_of_memories'])


    elif kind == 'counter_ZPL':
        print('Initializing the ZPL counter...')
        return TimeTagger.Counter(
            tagger,
            [TimeTagger_channel_map['apd_ZPL']],
            kwargs['interval_ps'],
            kwargs['trace_length']
        )


    elif kind == 'counter':

        print('Initializing the counter...')

        tagger.setTriggerLevel(2, 0.3)
        tagger.setTriggerLevel(7, 0.3)
        tagger.setTriggerLevel(3, 0.3)
        # g_start_ch = TimeTagger.DelayedChannel(tagger, TimeTagger_channel_map['apd0'], int(0))
        # g_stop_ch = TimeTagger.DelayedChannel(tagger,
        #                                       TimeTagger_channel_map['ssr_trigger'],
        #                                       int(1e6) #1 us aka 1 MHz
        #                                       )

        gated_clicks = TimeTagger.GatedChannel(tagger=tagger,
                                               input_channel=TimeTagger_channel_map['apd0'],
                                               gate_start_channel=TimeTagger_channel_map['ssr_trigger'],
                                               gate_stop_channel= TimeTagger.CHANNEL_INVALID
        # TimeTagger_channel_map['freq_swap_trigger'],
                                               )
        # print('gated_clicks ',gated_clicks)
        # print('input_channel= ',TimeTagger_channel_map['apd0'])
        # print('gate_start_channel= ',TimeTagger_channel_map['ssr_trigger'])
        # print('gate_stop_channel= ',TimeTagger_channel_map['freq_swap_trigger'])
        # print('gated_clicks.getChannel() ',gated_clicks.getChannel())


        return TimeTagger.Counter(
            tagger,
            # [gated_clicks.getChannel()],
            [TimeTagger_channel_map['apd0']],
            #[g_start_ch.getChannel()],
            kwargs['interval_ps'],
            kwargs['trace_length']
        )
    elif kind == 'pulsed':
        return TimeTagger.TimeDifferences(
            tagger,
            click_channel=TimeTagger_channel_map['apd0'],
            start_channel=TimeTagger_channel_map['freq_swap_trigger'],
            next_channel=TimeTagger_channel_map['freq_swap_trigger'],
            sync_channel=TimeTagger_channel_map['ssr_trigger'],
            binwidth=kwargs['bw'],
            n_bins=kwargs['n_bins'],
            n_histograms=kwargs['n_histos'],
            )
    elif kind == 'correlation':

        if 'delay_ps' in kwargs.keys():
            # print('TimeTager delay_ps ', kwargs['delay_ps'])
            delay = int(kwargs['delay_ps'])
        else:
            delay = None

        if 'window_ps' in kwargs.keys():
            # print('TimeTager window_ps ', kwargs['window_ps'])
            window = int(kwargs['window_ps'])
        else:
            window = None #40 ns

        # print('window: {window}\ndelay: {delay}'.format(delay = delay,window = window))

        if delay!=None and window!=None:
            delayed_channel_start = TimeTagger.DelayedChannel(
                tagger=tagger,
                input_channel=TimeTagger_channel_map['ssr_trigger'],
                delay=delay
            )
            vch_start = delayed_channel_start.getChannel()


            delayed_channel_stop = TimeTagger.DelayedChannel(
                tagger=tagger,
                input_channel=TimeTagger_channel_map['ssr_trigger'],
                delay=delay+window
            )
            vch_stop = delayed_channel_stop.getChannel()

            gated_channel_APD = TimeTagger.GatedChannel(
                tagger = tagger,
                input_channel= TimeTagger_channel_map['apd_ZPL'],
                gate_start_channel=vch_start,
                gate_stop_channel=vch_stop
            )

            vch_gated = gated_channel_APD.getChannel()

            return TimeTagger.Correlation(
                tagger,
                channel_1 = vch_gated,
                channel_2=TimeTagger_channel_map['ssr_trigger'],
                binwidth=kwargs['bw'],
                n_bins=kwargs['n_bins'],
                )
        else:
            return TimeTagger.Correlation(
                tagger,
                channel_1=TimeTagger_channel_map['apd_ZPL'],
                channel_2=TimeTagger_channel_map['ssr_trigger'],
                binwidth=kwargs['bw'],
                n_bins=kwargs['n_bins'],
            )
    else:
        raise NotImplementedError(kind)

def device():
    frontend=None
    backend=None
    context=None
    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.XREP)
        frontend.bind("tcp://127.0.0.1:{}".format(__DEVICE_PORT__))
        # Socket facing services
        backend = context.socket(zmq.XREQ)
        backend.bind("tcp://127.0.0.1:{}".format(__SERVER_PORT__))
        zmq.device(zmq.QUEUE, frontend, backend)

    except Exception as e:
        print(e)
        print("bringing down zmq device")
    finally:
        frontend.close()
        backend.close()
        context.term()


def server():
    # if len(lists_processes(__SERVER_PORT__)) == 0:
    #     sys.exit()
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.connect("tcp://localhost:%s" % __SERVER_PORT__)
    counter_dict = dict()
    tagger = TimeTagger.createTimeTagger()
    while True:
        #  Wait for next request from client
        try:
            inc = pickle.loads(socket.recv())
            if 'killme' in inc and inc['killme'] is True:
                sys.exit()
            else:
                if len(inc) != 4:
                    raise Exception('Error: Need 4 arguments, passed {}.'.format(len(inc)))
                if type(inc) not in [dict, collections.OrderedDict] or not ('counter_name' in inc and 'method' in inc and 'args' in inc and 'kwargs' in inc):
                    raise Exception('Error: passed type must be in [dict, collections.OrderedDict] with keys [counter_name, method, args, kwargs]')
                available_counters = ['gated_cbm_zpl','gated_counter', 'counter', 'counter_ZPL','odmr', 'pulsed', 'odmr_timedifferences', 'gated_counter_countbetweenmarkers','correlation','orabi_countbetweenmarkers']
                if hasattr(inc,'counter_name'):
                    if inc['counter_name'] not in available_counters:
                        raise NotImplementedError('Error: counter {} is not in {}'.format(inc['counter'], available_counters))

                # print('method', inc['method'])
                # print('inc ', inc)
                if inc['method'] == 'init_counter':

                        counter_dict[inc['counter_name']] = init_counter(
                            kind=inc['counter_name'],
                            tagger=tagger,
                            **inc['kwargs']
                        )
                        socket.send(pickle.dumps(None))
                elif inc['method'] == 'sync':
                    # print("Sync method called")
                    try:
                        tagger.sync()
                        # print("Synced.")
                        socket.send(pickle.dumps("synced"))
                    except Exception as err:
                        socket.send(pickle.dumps("sync failed"))
                else:
                    if inc['counter_name'] not in counter_dict:
                        # print('inc',inc)
                        # print('counter_dict',counter_dict)
                        raise Exception('Error: {}, {}'.format(inc['counter_name'], counter_dict))
                    msg = getattr(counter_dict[inc['counter_name']], inc['method'])(*inc['args'], **inc['kwargs'])
                    socket.send(pickle.dumps(msg))
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            socket.send(pickle.dumps(dict(exc_type=exc_type, exc_value=exc_value, exc_tb=exc_tb)))

def start_process(f, name):
    p = multiprocessing.Process(target=f, name=name)
    p.start()

def start_device():

    start_process(device, name='timetagger_device')

def start_server():
    start_process(server, name='timetagger_server')

def stop_server():
    dp = get_device_port()
    if dp is not None:
        TimeTaggerProxy().communicate('killme')

def stop_device():
    dp = get_device_port()
    if dp is not None:
        psutil.Process(dp).terminate()

def lists_processes(port, ip=None):
    ip = '127.0.0.1' if ip is None else ip
    lc = psutil.net_connections('inet')
    pid_l = []
    for c in lc:
        (cip, cport) = c.laddr
        if cip == ip:
            pid_s = str(c.pid) if c.pid else '(unknown)'
            if cport == port:
                pid_l.append(int(pid_s))
    return list(set(pid_l))

def get_device_port():
    pid_l = lists_processes(int(__SERVER_PORT__)) + lists_processes(int(__DEVICE_PORT__))
    if len(pid_l) == 0:
        return None
    elif len(pid_l) == 2:
        return int(pid_l[0])
    else:
        raise Exception('Error. Unexpected behaviour.')

def init_timetagger():
    import time
    try:
        stop_server()
        stop_device()
        time.sleep(2)
    except:
        pass
    print('now starting')
    start_device()
    start_server()
    time.sleep(2)
    return TimeTaggerProxy()

if __name__ == '__main__':
    t = init_timetagger()
    t.init_counter('gated_counter', nrows=10, number_of_memories=2)
    a = t.gated_counter.getData()