import time
import ctypes
import numpy as np
from pipython import GCSDevice, pitools

MAX_SAMPLES = 8192
NUMCYLES = 3  # number of cycles for wave generator output
TABLERATE = 100  # duration of a wave table point in multiples of servo cycle times as integer

class PiScanner():
    
    def __init__(self, serialnum = '0111144145', model='E-517'):
        self.pidevice = GCSDevice(model)
        self.serialnum = serialnum
        self.model=model
        self.seconds_per_point = None
        self.connect()
        self.getAxes()
        
        self.x_range, self.y_range, self.z_range = self.getLimits()
        
        self.setTiming()
        self.associate_tables()
        self.clear_triggers()
        self.setCycles()
        self.setOffsets()

        self.setServo((True,True,True))
        
        self.getPosition()

    def __del__(self):
        self.disconnect()

    def generate_stairs(from_=0, to_=10, min_=0, max_=10, step_width=0.5, samples=1000):
        total = np.linspace(0, to_, samples)
        step_samples = int(samples * step_width/to_)
        step = np.zeros(step_samples)#np.linspace(0, step_width, int(samples * step_width/tot))
        num_steps = int((to_ - from_) / step_width)
        ladder = np.array([step + a_stp * ((max_ - min_)/num_steps) for a_stp in range(num_steps)]).flatten()
        return np.pad(ladder, (0, np.abs(samples - len(ladder))), mode='constant', constant_values=(0, max_))

    def scan_line(self):
        wavedata = np.array([stairs(samples=int(MAX_SAMPLES/10)), stairs(samples=int(MAX_SAMPLES/10))])
        self.sweep_arbitrary_wave(wavedata)
    

    def sweep_arbitrary_wave(self, wavedata, axes=['A','B'], wavetables = [1,2], wavegens = [1,2], bunchsize=10):
        # clear wave tables
        pidevice.WCL(wavetables)

        for i, wavetable in enumerate(wavetables):
            #write wave points of wave table
            pitools.writewavepoints(pidevice, [wavetable], list(wavedata[i]), bunchsize=bunchsize)

        #connect wave tables to wave generators
        pidevice.WSL(wavegens, wavetables)

        #set wave generators {} to run for {} cycles
        pidevice.WGC(wavegens, [NUMCYLES] * len(wavegens))

        #set wave table rate to {} for wave generators {}
        pidevice.WTR(wavegens, [TABLERATE] * len(wavegens), interpol=[0] * len(wavegens))

        #move axes {} to start positions {}
        startpos = [wavedata[i][0] for i in range(len(wavedata))]
        pidevice.MOV(axes, startpos)
        pitools.waitontarget(pidevice, axes)

        #start wave generators {}
        pidevice.WGO(wavegens, mode=[1] * len(wavegens))

        #reset wave generators
        pidevice.WGO(wavegens, mode=[0] * len(wavegens))
        


    def associate_tables(self, tables=[1,2,3]):
        # associate generators and wave tables
        generators = [1,2,3]
        ret = self.pidevice.WSL(generators, tables)

    def stop(self):
        axes = [1,2,3]
        modes = np.array((0,0,0,))      #1: start immediately
        ret = self.pidevice.WGO(
                                axes, # const int* piWaveGeneratorIdsArray
                                modes, # const int* piStartModArray
                                )

    def clear_triggers(self):
        # clear trigger points
        self.pidevice.TWC()

        
    def setCycles(self, cycles=[1,1,1]):
        # set the number of cycles for the wave generator output to 1
        axes = [1,2,3]
        cycles = cycles
        ret = self.pidevice.WGC(axes, cycles)

        
    def setOffsets(self, offsets=[0.,0.,0.]):
        # set the offsets to 0.0
        axes =[1,2,3]
        offsets = offsets
        ret = self.pidevice.WOS(axes, offsets)
                    
    def CheckError(self):
        iError = self.pidevice.GetError()
        
        return self.pidevice.TranslateError()
    
    def connect(self, interface="USB"):
        #getting the description string of the controller 
        self.pidevice.ConnectUSB(serialnum=self.serialnum)
        self.ID = self.pidevice.GetID()
        if (self.ID<0):
            print( self.CheckError())
        print('connected: {}'.format(self.pidevice.qIDN().strip()))

        #TODO: ethernet, rs232

    def disconnect(self):
        self.pidevice.CloseConnection()
    
    def reconnect(self):
        self.disconnect()
        self.connect()

    def getAxes(self):
        self.szAxes = self.pidevice.axes
        servos_on = self.getServo()
        self.szAxes = [s for s in self.pidevice.axes if servos_on[s] is True]
        return self.szAxes
        
    def setServo(self, switch):
        #TODO
        pass

    def enable_servo(self,enable=True):
        pass #self.setServo((enable,enable,enable))

    def disable_servo(self,disable=True):
        pass #self.enable_servo(enable=not disable)

    def getServo(self):
        state = dict(self.pidevice.qSVO())
        return state

    
    def getServoTime(self):
        param_hex = '0xe000200' #CODE OF THE PARAMETER
        param = int(param_hex, 16)
        servo_update__time = self.pidevice.qSPA()['1'][param]
        return servo_update__time
        
    def getLimits(self):
        pdValueArraymin= list(self.pidevice.qTMN().values())
        pdValueArraymax= list(self.pidevice.qTMX().values())
        
        return (pdValueArraymin[0],pdValueArraymax[0]), (pdValueArraymin[1],pdValueArraymax[1]), (pdValueArraymin[2],pdValueArraymax[2])
    
    def getXRange(self):
        return self.x_range
        
    def getYRange(self):
        return self.y_range

    def getZRange(self):
        return self.z_range
        
    def set_x(self, x):
        self.setPosition( x, self.y, self.z )
        
    def set_y(self, y):
        self.setPosition( self.x, y, self.z )
        
    def set_z(self, z):
        self.setPosition( self.x, self.y, z)
    
    def getPosition(self):
        pos = self.pidevice.qPOS()
        pos = list(pos.values())
        self.x, self.y, self.z = pos[0],pos[1],pos[2]
        return self.x, self.y, self.z
    
    def setPosition(self, x,y,z):
        new_pos = []
        if 'A' in self.szAxes:
            new_pos.append(x)
        if 'B' in self.szAxes:
            new_pos.append(y)
        if 'C' in self.szAxes:
            new_pos.append(z)

        self.pidevice.MOV(self.szAxes, new_pos)
          

    def setTiming(self, seconds_per_point=0.01, duty_cycle=0.5):
        if seconds_per_point != self.seconds_per_point:
            #cycles = int(seconds_per_point / self.getServoTime()) 
            print( self.getServoTime())
            cycles = int(seconds_per_point / self.getServoTime()) 
            generators = [1,2,3]
            rates = [cycles, cycles,cycles]
            interpolations = [0, 0, 0]
            self.pidevice.WTR(generators,rates,interpolations)
            self.seconds_per_point = seconds_per_point
        
    def getTiming(self):
        return self.seconds_per_point

    def setWaveTable(self, Line ):
        for i, line_i in enumerate(Line):
            self.__line_i = line_i
            """
            <SegStartPoint> <WaveLength> {<WavePoint>}
            <SegStartPoint> The index of the segment starting
            point in the wave table. Must be 1.
            <WaveLength> The length of the user-defined
            curve in points. The segment length, i.e. the
            number of points written to the wave table, is
            identical to the <WaveLength> value.

            

            """
            wavetables = [1,2]
            wavegens =[1,2]
            pidevice.WCL(wavetables) # clear tables
            for i, wavetable in enumerate(wavetables):
                print('write wave points of wave table {} and axis {}'.format(wavetable, i))
                pitools.writewavepoints(pidevice, wavetable, line_i, bunchsize=10)
                print('connect wave tables {} to wave generators {}'.format(wavetables, wavegens))
                pidevice.WSL(wavegens, wavetables)
                print('set wave generators {} to run for {} cycles'.format(wavegens, NUMCYLES))
                pidevice.WGC(wavegens, [NUMCYLES] * len(wavegens))
                print('set wave table rate to {} for wave generators {}'.format(TABLERATE, wavegens))
                pidevice.WTR(wavegens, [TABLERATE] * len(wavegens), interpol=[0] * len(wavegens))
            startpos = [wavedata[i][0] for i in range(len(wavedata))]
            print('move axes {} to start positions {}'.format(axes, startpos))
            pidevice.MOV(axes, startpos)
            pitools.waitontarget(pidevice, axes)
            print('start wave generators {}'.format(wavegens))
            pidevice.WGO(wavegens, mode=[1] * len(wavegens))
            while any(list(pidevice.IsGeneratorRunning(wavegens).values())):
                print('.', end='')
                sleep(1.0)
            print('\nreset wave generators {}'.format(wavegens))
            pidevice.WGO(wavegens, mode=[0] * len(wavegens))
            print('done')
            # scanner.pidevice.WAV_POL(append='X', table=i+1, firstpoint=1, numpoints = len(line_i), x0=1, a0=1, an=0)
            # self.pidevice.WAV_PNT(i+1, # int iWaveTableId
            #                     0, # int iOffsetOfFirstPointInWaveTable
            #                     len(line_i), # int iNumberOfWavePoints
            #                     0)
    def clearTriggers(self): 
        self.pidevice.TWC()

    def enableMultipleWGTriggerOut(self, Line):

        self.clearTriggers()
    
        for i in range(len(Line[0])/100):
            wavepoints = np.arange(i*100+1, (i+1)*100+10,10)  # np.array(range(i+1,len(Line[0])/10+i*10+1))*10
            switch = np.array([ 1 for point in wavepoints])
            outputs = np.array([1 for point in wavepoints])
            print( "wavepoints:", wavepoints)
            print(  "switch:", switch)


            self.pidevice.TWS(
                                   outputs, # const int* piTriggerChannelIdsArray
                                   wavepoints, # const int* piPointNumberArray
                                   switch, # const double* piSwitchArray
                                   ) 


    def enableSingleWGTriggerOut(self, Line):

        self.clearTriggers()
        wavepoints = np.array([1])  # np.array(range(i+1,len(Line[0])/10+i*10+1))*10
        switch = np.array([ 1])
        outputs = np.array([1])

        self.pidevice.TWS(outputs, # const int* piTriggerChannelIdsArray
                                   wavepoints, # const int* piPointNumberArray
                                   switch, # const double* piSwitchArray
                                   ) 
 
 

    def connectTriggerOut(self, channel=1):

        outputs = np.array([channel])
        CTOParam = np.array([3])
        pdValueArray = 4
        self.pidevice.CTO(outputs, CTOParam, pdValueArray) 



    def startWaveTriggerOut(self):
        axes = [1,2,3]
        modes = [1,1,1]      #1: start immediately
        self.pidevice.WGO(axes, modes)
       

    def startWaveTriggerIn(self):
        axes = [1,2,3]
        modes = [2,2,2][:len(axes)]      #1: start immediately
        self.pidevice.WGO(axes, # const piWaveGeneratorIdsArray
                          modes, # const piStartModArray
                          )
           

    def waitFinished(self):     
        #TODO       
        self.pidevice.IsGeneratorRunning()
        # OrderedDict([(1, False)])
        #if 'pbValueArray[0]' = TRUE corresponding wavegenerator is running False: is not running
        # pbValueArray[0]=True
        # sleeptime= self.getTiming() * len(self.__line_i)/10 #/10: because of duty cycle
        # time.sleep(sleeptime)
        # while(pbValueArray[0]):
        #     time.sleep(0.001)
        #     if ( not self.pidevice.IsGeneratorRunning()):
        #         print( self.CheckError())
                #self.pidevice.CloseConnection(self.ID)


    def scanLine(self, Line, SecondsPerPoint, return_speed=None, trigger_mode='output single'):
        """Move the scanner along a line in 3D space."""
        self.trigger_mode = trigger_mode
        
        try:
            if self.trigger_mode == 'input':
                self.setTiming(SecondsPerPoint)
                self.setWaveTable(Line) 
                # self.startWaveTriggerIn()  
            elif self.trigger_mode == 'output single':  
                #outputs on every single point
                Line = np.repeat(Line, repeats=10, axis=1)      
                # self.enableWGTriggers(Line) 
                self.connectTriggerOut()
                self.setTiming(SecondsPerPoint/10)  #/10: so we have 90-10% duty cycle for triggering
                self.setWaveTable(Line)
                self.startWaveTriggerOut()
            elif self.trigger_mode == "output":
                raise NotImplemented
                return False
                # self.enableWGTriggers(Line)
                self.connectTriggerOut()
                self.setTiming(SecondsPerPoint)
                self.setWaveTable(Line)
                self.startWaveTriggerOut() 
          

            #TODO
            #self.waitFinished()


        except Exception as e:
            print( "Failed:", e)
            return False
        finally:
            #self.clearWaveTable()
            return True

    def create_line(res=100):
        x_line = np.linspace(0,100,res)
        y_line = 2.*np.ones_like(x_line)*10
        z_line = 3.*np.ones_like(x_line)*10
        return np.vstack((x_line, y_line, z_line, ))
    
    # scanner = PiScanner()
   
    # line = create_line()
    # scanner.scanLine(line,SecondsPerPoint=0.01)
    