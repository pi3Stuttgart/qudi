import numpy as numpy
import matplotlib.pyplot as plt
import time
import numpy as np

from hardware.pulse_generator import PulseGenerator
from measurements.pulsed import sequence_union, sequence_remove_zeros, sequence_length



def generate_lockin_sequence():
    start_time=time.time()
    sequence=[]

    sequence.append((['aom',"microwave",'SMIQtrigger'],996))
    no_loops = np.round(0.06/(np.round( np.array(1./200*1e9, dtype=float)/12 )*12*1e-9) )

    for i in range(int(no_loops)):
        sequence.append( (['aom','microwave','detect','SMIQtrigger'], np.round( np.array(1./200*1e9, dtype=float)/24 )*12 ) )
        sequence.append( (['aom','detect','SMIQtrigger'],  np.round( np.array(1./200*1e9, dtype=float)/24 )*12 ) ) 
    sequence.append((["aom"],(10*1e9+8)))
    return sequence, pulse_generator.convertSequenceToBinary(sequence, loop=5)

aom_delay = 0
decay_init = 999
decay_read = 999
enable_eldor = False
eldor_pulselength = 200
eldor_delay = 100
eldor_second_swap = True
laser = 300
base_direction = []

def generate_laser_pulse(tau):
    return [ ([], decay_init+tau+decay_read+int(enable_eldor)*(eldor_pulselength+eldor_delay)+int(enable_eldor and eldor_second_swap)*(eldor_pulselength+eldor_delay)), (['aom'], laser ) ]

def generate_detect_pulse( tau):
    single_sequence_length =  decay_init+tau+decay_read+int(enable_eldor)*(eldor_pulselength+eldor_delay)+int(enable_eldor and eldor_second_swap)*(eldor_pulselength+eldor_delay) + laser
    return [( ['detect'], int(single_sequence_length) )]

def generate_mw_pulse(tau):
    #get the base direction of the pulse
   
 
    if eldor_second_swap and eldor_second_swap:
        return [ ([], decay_init+aom_delay), (['eldor'],eldor_pulselength), ([]+base_direction,eldor_delay), (['microwave']+base_direction,tau),([]+base_direction,eldor_delay), (['eldor'],eldor_pulselength), ([],decay_read-aom_delay) ]
    elif eldor_second_swap and not eldor_second_swap:
        return [ ([], decay_init+aom_delay), (['eldor'],eldor_pulselength), ([]+base_direction,eldor_delay), (['microwave']+base_direction,tau), ([]+base_direction,decay_read-aom_delay)]                    
    else:
        return [ ([] + base_direction, decay_init+aom_delay), (['microwave']+base_direction,tau), ([]+base_direction, decay_read-aom_delay) ] 



def generate_rabi_sequence():
    taus = np.arange(1,1251,50)
    initialization_pulse =[(['aom'],laser)]
    pulses = []

    for i, tau in enumerate(taus):
        laser_pulse =generate_laser_pulse(tau)
        detect_pulse = generate_detect_pulse(tau)
        mw_pulse = generate_mw_pulse(tau)

        tmp_unified = sequence_union( laser_pulse, detect_pulse)
        pulse = sequence_union( tmp_unified, mw_pulse)

        pulses.extend(sequence_remove_zeros(pulse))

    stop_pulse = [([],0.5e9)]

    sequence = initialization_pulse
    sequence.extend(pulses)
    sequence.extend(stop_pulse)
    return (sequence, pulse_generator.convertSequenceToBinary(sequence, loop=0))



def performance_test(sequence, loop=0):

	pulse_generator.pack = pulse_generator.pack_numpy
	start_numpy = time.time()
	bits_numpy = pulse_generator.convertSequenceToBinary(sequence, loop)
	end_numpy = time.time()
	pulse_generator.pack = pulse_generator.pack_original
	start_std = time.time()
	bits_std  = pulse_generator.convertSequenceToBinary(sequence, loop)
	end_std  = time.time()
	if bits_numpy == bits_std:
		print 'both packing sequences have the same result.'
		print 'std took',end_std-start_std,'s'
		print 'npy took',end_numpy-start_numpy,'s'
	else:
		print 'packing functions defer in result...'





def check_sequence_creation(pulse_generator, sequence, loop=0):
	print 'creating with loop=', loop
	bit = pulse_generator.convertSequenceToBinary(sequence,loop)
	bit_decoded = pulse_generator.unpack_sequence(bit)
	if sequence == bit_decoded:
		print 'decoding and encoding works correctly.'
	else:
		print 'decoding or encoding doesn\'t work correctly'
	return bit_decoded



def sequence_to_file(sequence, filename):
	with open(filename,'w') as f:
		for i, pattern in enumerate(sequence):
			total_time = sequence_length(sequence[:i+1])
			channels, time = pattern[0], pattern[1]
			f.write( '{:50s}; {:9d}; {:9d}'.format(str(channels), int(time), int(total_time)) + '\n' )

class SequencePlotter(object):


	channel_map = {'ch0':0,'ch1':1,'ch2':2,'ch3':3,'ch4':4,'ch5':5,'ch6':6,'ch7':7,'ch8':8,'ch9':9,'ch10':10,'ch11':11}

	def __init__(self, pulse_generator=None):
		if pulse_generator != None:
			self.pulse_generator = pulse_generator
			self.channel_map =  self.pulse_generator.channel_map


	def plot_sequence(self, sequence, label='Sequence'):
		plt.figure()		
		self.channels_seen = set()
		self.times = [0 ]
		self.active_channels = []
		self._total_time = 0
		self.title=label
		for channel, time in sequence:
			self.channels_seen.update( channel )
			self.times.append(self._total_time + time)
			self.active_channels.append(channel)

			self._total_time += time

		self.N = len(self.channels_seen)
		self._ordered_channels = []

		for channel in self.channels_seen:
			self._ordered_channels.append(self.channel_map[channel])
		self._ordered_channels = sorted(self._ordered_channels)

		i=1
		for channel_no in self._ordered_channels:

			for key, value in self.channel_map.items():
				if value==channel_no:
					ch_name = key

			t_lenghts = []
			t = 0
			line_points = []
			status = 0
			x = []
			y = []
			for j,(time_start, time_end) in enumerate(zip(self.times, self.times[1:])):
				diff = time_end-time_start
				if ch_name in self.active_channels[j]:

					if j>0:
						if status != 0.5:
							#we have a rising edge						
							x.append( t )
							y.append( i )
							x.append( t )
							y.append( i+0.5 )
						else:
							x.append( t )
							y.append( i+0.5 )
							x.append( t )
							y.append( i+0.5 )					

					elif j==0:
						print 'ch', ch_name,': starting high'
						x.append( t )
						y.append( i+0.5 )
					status = 0.5
				else:
					if j==0:
						print 'ch', ch_name,': starting low'
						x.append( t )
						y.append(  i )
					if j>0:
						if status != 0:
							#we have a falling edge
							x.append( t )
							y.append( i+0.5 )
							x.append( t )
							y.append( i )							
						else:
							x.append( t )
							y.append( i )
							x.append( t )
							y.append( i )								
					status = 0
				t+=diff
			x.append(t+self.times[-1])
			y.append(i+status)

			plt.plot(x,y,linestyle='-',label='')
			i+=1

		plt.title(self.title)
		plt.xlim(0, self._total_time)
		plt.ylim(0, i)
		
		plt.show(blocking=False)



if __name__ == '__main__':

	lockin_seq_file = "C:\\data\\lockin_seq.txt"
	rabi_seq_file   = "C:\\data\\rabi_seq.txt"

	lockin_sequence, lockin_seq_cached = generate_lockin_sequence()
	#rabi_sequence, rabi_seq_cached = generate_rabi_sequence()

	#performance_test(lockin_sequence)
	#performance_test(rabi_sequence)
	pulse_generator = PulseGenerator(serial='XpoJYaysTt', channel_map={'aom':0, 'detect':1, 'sequence':2, 'microwave':3, 'SMIQtrigger':4,'stagetrigger':5,'Iswitch':6,'Qswitch':7,"eldor":8,'ch9':9,'ch10':10,'ch11':11})

	sequence_to_file(check_sequence_creation(lockin_sequence, loop=5), lockin_seq_file )
	#sequence_to_file(check_sequence_creation(rabi_sequence, loop=0), rabi_seq_file )

