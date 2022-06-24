from pi3diamond import pi3d
import numpy as np
import time, datetime, os, itertools
import errno

import UserScripts.helpers.sequence_creation_helpers as sch
reload(sch)
import multi_channel_awg_seq as MCAS
reload(MCAS)
import UserScripts.helpers.snippets_awg as sna
reload(sna)

nuclear = pi3d.nuclear
tt = pi3d.tt
seq_name = os.path.basename(__file__).split('.')[0]
gated_counter = pi3d.gated_counter
confocal = pi3d.confocal

__USE_POWERMETER__ = False

def run_fun(abort, **kwargs):
    try:
        confocal.XYSize = 1.2
        confocal.XYStep = 0.1
        aom_voltage0 = confocal.aom_voltage
        counter_state0 = confocal.counter_state
        confocal.CountTImeMonitor = 0.002
        confocal.ReadoutDelayMonitor = 0.002
        confocal.TraceLength = 200
        confocal.counter_state = 'count'
        use_powermeter = __USE_POWERMETER__
        if use_powermeter:
            powermeter = pi3d.powermeter
        pms = {True: "Power\t", False: ''}[use_powermeter]
        try:
            folder = "D:/data/{}".format(sch.sub_folder_structure(os.path.abspath(__file__)))
            os.makedirs(folder)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        nts = datetime.datetime.now().strftime('%Y%m%d-h%Hm%Ms%S')
        fn = "{}/{}_saturation_curve.dat".format(folder, nts)
        for i in range(2):
            confocal.run_refocus()
        with open(fn, 'w') as f:
            f.write("Voltage\t{}kCounts\tBackground\tDiff\n".format(pms))
            for voltage in np.linspace(-8, -6, 20):
                if abort.is_set(): break
                confocal.aom_voltage = voltage
                if use_powermeter:
                    pass #ps = "{:.2f}\t".format(power)
                else:
                    ps = ''
                for i in range(2):
                    confocal.run_refocus()
                time.sleep(confocal.CountInterval * confocal.TraceLength + 0.5)
                counts = np.mean(confocal.C)/1000.
                confocal.x += 2
                time.sleep(confocal.CountInterval * confocal.TraceLength + 0.5)
                counts_bg = np.mean(confocal.C)/1000.
                confocal.x -= 2
                print "voltage: {}, nv-counts: {}".format(voltage, counts - counts_bg)
                f.write("{:3f}\t{}{:.1f}\t{:.1f}\t{:.1f}\n".format(voltage, ps, counts, counts_bg, counts-counts_bg))
    finally:
        confocal.XYSize = 0.56
        confocal.XYStep = 0.08
        confocal.aom_voltage = aom_voltage0


#    def saturation_curve(self, filename, aom_voltages = numpy.linspace(-10,10,200)):
#        """Creates a new run function.
#        The defintion of the run function may include parameter, but may not be arguement of run function"""#
#        confocal = pi3d.confocal
#        powermeter = pi3d.powermeter
#        gc = pi3d.get_counter()
#
#        power_params = {'duration': 3, 'steps': 20}
#
#        folder = 'D:/data/saturation_curve/'
#
#        def run():
#            #os.mkdir(folder + filename)
#            fil = open(folder + filename, 'w')
#            fil.write('Power\t Counts\t Background\t Diff\n')
#            for i in aom_voltages:
#                confocal.aom_voltage = i
#                powers = []
#                for j in range(1,power_params['steps']):
#                    time.sleep(power_params['duration']*1./power_params['steps'])
#                    powers.append(powermeter.get_power())
#                power = numpy.mean(powers)
#
#                confocal.aom_voltage = 10
#                self.run_refocus()
#                confocal.aom_voltage = i
#                time.sleep(confocal.CountInterval * confocal.TraceLength + 0.5)
#                counts = numpy.mean(confocal.C)
#                confocal.x += 2
#                time.sleep(confocal.CountInterval * confocal.TraceLength + 0.5)
#                counts_bg = numpy.mean(confocal.C)
#                confocal.x -= 2
#                fil.write('%.2f \t %.1f\t %.1f\t %.1f\n' %(power, counts, counts_bg, counts-counts_bg))
#                if self.abort.is_set(): break
#            fil.close()
#
#
#        return run