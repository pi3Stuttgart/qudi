
from qtpy import QtCore
from numpy import divide, zeros_like, ones, array
from datetime import datetime


def delay(delay_msec = 100):
    dieTime = QtCore.QTime.currentTime().addMSecs(delay_msec)
    while (QtCore.QTime.currentTime() < dieTime):
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 100)

def wavelength_to_freq(wavelength):
    wavelength = array(wavelength)
    aa = 299792458.0 * 1e9 * ones(wavelength.shape[0])
    freqs = divide(aa, wavelength, out=zeros_like(aa), where=wavelength!=0)
    return freqs

def freq_to_wavelength(freq):
    freq = array(freq)
    aa = 299792458.0 * 1e9 * ones(freq.shape[0])
    wavelength = divide(aa, freq, out=zeros_like(aa), where=freq!=0)
    return wavelength

def printdebug(debug,text):
        """
        Prints time and text to console if debug is set to True.

        @param bool debug: Outputs something if set to true
        @param str text: String to be printed
        """
        if debug:
            text = f'{datetime.now().strftime("%H:%M:%S")} ' + text
            print(text)
        return