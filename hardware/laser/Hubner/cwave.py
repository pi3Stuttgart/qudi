'''This module allows control of the Hubner C-WAVE 2.0 Laser.'''

# pylint: disable=R0904

import typing
import enum
import socket

class Log(typing.NamedTuple):
    '''Contains all status data of the device'''
    tempOpo: float
    tempShg1: float
    tempShg2: float
    tempRef: float
    tempBase: float
    tempFpga: float
    pdPump: float
    pdSignal: float
    pdShg: float
    pdReserve: float
    statusBits: int

class ShutterChannel(enum.Enum):
    '''Enumeration of shutter channels'''
    Laser = 'las'
    LaserOut = 'las_out'
    OpoOut = 'opo_out'
    Shg = 'shg'
    ShgOut = 'shg_out'

class StepperChannel(enum.Enum):
    '''Enumeration of stepper channels'''
    Opo = 'opo'
    Shg = 'shg'

class MappingChannel(enum.Enum):
    '''Enumeration of mapping channels'''
    Opo = 'opo'
    Shg = 'shg'

class TemperatureChannel(enum.Enum):
    '''Enumeration of temperature channels'''
    Opo = 'opo'
    Shg = 'shg'
    Ref = 'ref'

class PiezoChannel(enum.Enum):
    '''Enumeration of piezo channels'''
    Opo = 'opo'
    Shg = 'shg'
    Etalon = 'eta'
    Ref = 'ref'

class PiezoMode(enum.IntEnum):
    '''Enumeration of piezo modes'''
    Hold = 0
    Scan = 1
    Control = 2
    ExtRamp = 3
    Manual = 4

class ExtRampMode(enum.IntEnum):
    '''Enumeration of ExtRamp modes'''
    Sawtooth = 0
    Triangle = 1

class StatusBit(enum.IntEnum):
    '''Enumeration of status bits'''
    OpoStepper = 0
    OpoTemp = 1
    ShgStepper = 2
    ShgTemp = 3
    EtalonCoarse = 4
    OpoLock = 5
    ShgLock = 6
    EtalonLock = 7
    LaserEmission = 8
    RefTemp = 9
    OpoStable = 10

class CWave:
    '''Represents a handle to the C-WAVE device.'''

    def __init__(self):
        self.__socket = None
        self.__connected = False

    def connect(self, address: str, port: int = 10001):
        '''Connect to device'''
        assert isinstance(address, str)
        assert isinstance(port, int)
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.connect((address, port))
        self.__connected = True
        # sanity check if there is really a C-WAVE behind this connection
        if not self.get_firmware_version().startswith('CWave '):
            self.disconnect()
            raise ConnectionAbortedError('Invalid device')

    def disconnect(self):
        '''Disconnects from device'''
        if not self.__socket is None:
            self.__socket.close()
        self.__socket = None
        self.__connected = False

    def dial(self, wavelength: float, request_shg: bool) -> None:
        '''Sets a new wavelength (OPO) to dial'''
        assert isinstance(wavelength, (float, int))
        assert isinstance(request_shg, bool)
        wavelength = wavelength/2 if request_shg else wavelength
        self.__query_value('opo_lambda', int(wavelength*100))

    def get_dial_done(self) -> bool:
        '''Gets whether the dial operation is complete'''
        return self.test_status_bits([
            StatusBit.OpoLock,
            StatusBit.ShgLock,
        ])

    def get_firmware_version(self) -> str:
        '''Gets firmware version'''
        return self.__query('info?')

    def get_fpga_version(self) -> str:
        '''Gets FPGA version'''
        return int(self.__query('info_fpga?'))

    def get_serialnumber(self) -> int:
        '''Gets serial number'''
        return int(self.__query('uniqueid?'))

    def optimize_stop(self) -> None:
        '''Stops all optimizations'''
        self.__query('opt_stop')

    def optimize_etalon(self) -> None:
        '''Optimizes etalon'''
        self.__query('regeta_catch')

    def etalon_move(self, delta_wavelength: float) -> None:
        '''Moves etalon wavelength wise'''
        assert isinstance(delta_wavelength, (float, int))
        self.__query_value('thicketa_rel_hr', int(delta_wavelength*1000))

    def elements_move(self, delta_wavelength: float) -> None:
        '''Moves all elements wavelength wise'''
        assert isinstance(delta_wavelength, (float, int))
        self.__query_value('opo_rlambda', int(delta_wavelength*100))

    def set_stepper_period(self, channel: StepperChannel, period: (int)) -> None:
        '''Sets stepper period'''
        assert isinstance(channel, StepperChannel)
        assert isinstance(period, int)
        self.__query_value('{}_pos_i'.format(channel.value), period)

    def set_piezo_mode(self, channel: PiezoChannel, mode: PiezoMode) -> None:
        '''Sets piezo operation mode'''
        assert isinstance(channel, PiezoChannel)
        assert isinstance(mode, PiezoMode)
        if mode == PiezoMode.Manual and not (channel in [PiezoChannel.Opo, PiezoChannel.Shg]):
            raise Exception('Manual Mode only allowed OPO und SHG Channels')
        if mode == PiezoMode.ExtRamp and channel != PiezoChannel.Opo:
            raise Exception('ExtRamp Mode only allowed OPO Channel')
        self.__query_value('reg{}_on'.format(channel.value), mode.value)

    def get_piezo_mode(self, channel: PiezoChannel) -> PiezoMode:
        '''Gets piezo operation mode'''
        assert isinstance(channel, PiezoChannel)
        return PiezoMode(int(self.__query('reg{}_on?'.format(channel.value))))

    def set_piezo_manual_output(self, channel: PiezoChannel, value: int) -> None:
        '''Sets piezo output when in manual mode'''
        assert isinstance(channel, PiezoChannel)
        assert isinstance(value, int)
        if channel == PiezoChannel.Etalon:
            raise Exception(
                'Operation not allowed for etalon channel.\n' +
                'Use set_etalon_offset() instead while in \'off\' mode'
            )
        self.__query_value('reg{}_out'.format(channel.value), value)

    def get_piezo_manual_output(self, channel: PiezoChannel) -> int:
        '''Sets piezo output when in manual mode'''
        assert isinstance(channel, PiezoChannel)
        if channel == PiezoChannel.Etalon:
            raise Exception(
                'Operation not allowed for etalon channel.\n' +
                'Use get_etalon_offset() instead while in \'off\' mode'
            )
        return int(self.__query('reg{}_out?'.format(channel.value)))

    def set_etalon_offset(self, value: int) -> None:
        '''Sets etalon control offset'''
        assert isinstance(value, int)
        self.__query_value('regeta_off', value)

    def get_etalon_offset(self) -> int:
        '''Gets etalon control offset'''
        return int(self.__query('regeta_off?'))

    def set_galvo_position(self, value: int) -> None:
        '''Sets thick etalon position'''
        assert isinstance(value, int)
        self.__query_value('galvo', value)

    def get_galvo_position(self) -> None:
        '''Gets thick etalon position'''
        return int(self.__query('galvo?'))

    def set_laser(self, enable: bool) -> None:
        '''Sets enabled state of internal pump laser'''
        assert isinstance(enable, bool)
        self.__query_value('laser_en', int(enable))

    def get_laser(self) -> bool:
        '''Gets enabled state of internal pump laser'''
        return bool(self.__query('laser_en?'))

    def set_shutter(self, shutter: ShutterChannel, open_shutter: bool) -> None:
        '''Sets a shutter open or closed'''
        assert isinstance(open_shutter, bool)
        self.__query_value('shtter_{}'.format(shutter.value), int(open_shutter))

    def get_shutter(self, shutter: ShutterChannel) -> bool:
        '''Gets whether current state of a shutter is open or closed'''
        return bool(int(self.__query('shtter_{}?'.format(shutter.value))))

    def set_mirror(self, position: bool) -> None:
        '''Sets mirror to either 0 or 1 position'''
        assert isinstance(position, bool)
        self.__query_value('mirror', int(position))

    def get_mirror(self) -> bool:
        '''Gets current state of mirror'''
        return bool(int(self.__query('mirror?')))

    def get_status_bits(self) -> int:
        '''Gets raw representation of status bits'''
        return self.get_log().statusBits

    def get_external_pump(self) -> bool:
        '''Gets whether device has an external pump'''
        return int(self.__query('laser_exist?')) == 0

    def set_temperature_setpoint(self, channel: TemperatureChannel, setpoint: float) -> None:
        '''Sets temperature setpoint'''
        assert isinstance(channel, TemperatureChannel)
        assert isinstance(setpoint, (float, int))
        self.__query_value('t{}_set'.format(channel.value), int(setpoint*1000))

    def get_temperature_setpoint(self, channel: TemperatureChannel) -> float:
        '''Gets temperature setpoint'''
        assert isinstance(channel, TemperatureChannel)
        return float(self.__query('t{}_set?'.format(channel.value)))/1000

    def get_mapping_temperature(self, channel: MappingChannel, wavelength: float) -> float:
        '''Gets corresponding temperature of a wavelength according to mapping'''
        assert isinstance(wavelength, (int, float))
        return float(
            self.__query('mapping_{}?{}'.format(channel.value, int(wavelength*100))).split(':')[1]
        )/1000

    def set_opo_extramp_settings(self,
                                 period_milliseconds: int,
                                 mode: ExtRampMode,
                                 lower_limit_percent: int,
                                 upper_limit_percent: int):
        '''Sets ExtRamp OPO mode parameters'''
        assert isinstance(period_milliseconds, int)
        assert isinstance(mode, ExtRampMode)
        assert isinstance(lower_limit_percent, int)
        assert isinstance(upper_limit_percent, int)
        self.__query_value('regopo_extramp', [
            period_milliseconds,
            mode.value,
            lower_limit_percent,
            upper_limit_percent,
        ])

    def get_log(self) -> Log:
        '''Gets latest device status summary'''
        ret = self.__query('get_log?')
        split = ret.split(':')
        return Log(
            int(split[0])/1000,  # tempOpo
            int(split[1])/1000,  # tempShg1
            int(split[2])/1000,  # tempShg1
            int(split[3])/1000,  # tempRef
            int(split[4])/1000,  # tempBase
            int(split[5])/1000,  # tempFpga
            int(split[6]),       # pdPump
            int(split[7]),       # pdSignal
            int(split[8]),       # pdShg
            int(split[9]),       # pdReserve
            int(split[10]),      # statusBits
        )

    def test_status_bits(self, bits) -> bool:
        '''Test whether a list list of status bits are all true'''
        status_bits = self.get_status_bits()
        for bit in bits:
            assert isinstance(bit, StatusBit)
            # bits are "inverted": 0 -> OK, 1 -> FAIL
            if status_bits & (1 << bit.value) > 0:
                return False
        return True

    def __query(self, cmd: str) -> str:
        assert isinstance(cmd, str)
        if not self.__connected:
            raise ConnectionError('Not connected to device.')
        # flush input
        self.__socket.settimeout(0.001)
        while True:
            try:
                self.__socket.recv(1000)
            # pylint: disable=W0702
            except:
                break
        # send query
        self.__socket.send((cmd + '\r').encode('ASCII'))
        # flush output
        self.__socket.makefile().flush()
        # wait for response
        # use long timeout because in multiplexing operation
        # via C-WAVE control, responses might take longer
        self.__socket.settimeout(10)
        response = ''
        # read response until line break
        while True:
            char = self.__socket.recv(1).decode('ASCII')
            if char in ['\r', '\n']:
                break
            response += char
        if len(response) > 0 and response[0] != '?':
            split = response.replace('?', ':').split(':', 1)
            if len(split) > 1:
                return split[1]
            return ''
        raise ConnectionError('Command Failed: ' + cmd)

    def __query_value(self, cmd: str, val: any) -> str:
        assert isinstance(cmd, str)
        if not self.__connected:
            raise ConnectionError('Not connected to device.')
        cmd += ':' if cmd[-1] != '?' else ''
        if not isinstance(val, typing.Iterable):
            val = [val]
        cmd += ':'.join(map(str, val))
        ret = self.__query(cmd)
        return ret
