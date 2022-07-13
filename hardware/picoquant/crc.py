import csv
from PyCRC.CRCCCITT import CRCCCITT
# CRC-CCITT
# polynom: 0x1021
# seed: 0xFFFF

def get_chck_summ(filename="waveform.csv"):

    f = open(filename)
    data = csv.reader(f, delimiter=';')
    amplitude = bytearray()
    for row in data:
        for column in row:
         #print(row)
            #print str(column)
            amplitude.append(int(str(column),0))
            amplitude.append(0)
    f.close()
    return hex(CRCCCITT(version="FFFF").calculate(bytes(amplitude)))