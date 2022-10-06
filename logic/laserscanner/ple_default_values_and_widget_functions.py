import numpy as np
import time

class ple_default_values_and_widget_functions:
        MW1_Power:float=-21
        MW2_Power:float=-21
        MW3_Power:float=-21
        MW1_Freq:float=70
        MW2_Freq:float=140
        MW3_Freq:float=210
        enable_MW1:bool=True
        enable_MW2:bool=False
        enable_MW3:bool=False
        enable_A1:bool=False
        enable_A2:bool=True
        enable_Repump:bool=False
        enable_PulsedRepump:bool=True
        RepumpDuration:float = 10
        RepumpDecay:float = 1000

        Filename:str = ''
        PeriodicSaving:bool = False
        PerformFit:bool = False
        NumberOfPeaks:int = 2
        Stoptime:float = 3600
        Interval:float = 180
        PerformFit:bool = False

        Contrast_Fit:str=''
        Frequencies_Fit:str=''
        Linewidths_Fit:str=''

        #NumberOfLines: int = 10
        #ValuesPerScan: int = 200
        #Start: float = -3
        #Stop: float = 3
        #Speed: float = 0.3
        #constVoltage: float = 0


        def ple_Load_Button_Clicked(self,on):
                print('done something with ple_Load_Button')

        def ple_PulsedRepump_CheckBox_StateChanged(self,on):
                self.enable_PulsedRepump=on==2

        def ple_MW2_CheckBox_StateChanged(self,on):
                self.enable_MW2=on==2

        def ple_Continue_Button_Clicked(self,on):
                print('done something with ple_Continue_Button')

        def ple_MW1_CheckBox_StateChanged(self,on):
                self.enable_MW1=on==2

        def ple_Save_Button_Clicked(self,on):
                self.save_data(tag=self.Filename)

        def ple_MW1_Power_LineEdit_textEdited(self,text):
                try:
                        self.MW1_Power=float(text)
                except:
                        pass

        def ple_Abort_Button_Clicked(self,on):
                self.AbortRequested = True
        def ple_MW3_Power_LineEdit_textEdited(self,text):
                try:
                        self.MW3_Power=float(text)
                except:
                        pass

        def ple_RepumpDuration_LineEdit_textEdited(self,text):
                try:
                        self.RepumpDuration=float(text)
                except:
                        pass
        
        def ple_NumberOfPeaks_LineEdit_textEdited(self,text):
                try:
                        self.NumberOfPeaks=int(text)
                except:
                        pass

        def ple_A1_CheckBox_StateChanged(self,on):
                self.enable_A1=on==2

        def ple_A2_CheckBox_StateChanged(self,on):
                self.enable_A2=on==2

        def ple_RepumpDecay_LineEdit_textEdited(self,text):
                try:
                        self.RepumpDecay=float(text)
                except:
                        pass

        def ple_MW1_Freq_LineEdit_textEdited(self,text):
                try:
                        self.MW1_Freq=float(text)
                except:
                        pass

        def ple_MW2_Freq_LineEdit_textEdited(self,text):
                try:
                        self.MW2_Freq=float(text)
                except:
                        pass

        def ple_Run_Button_Clicked(self,on):
                self.start_scanning()

        def ple_MW3_CheckBox_StateChanged(self,on):
                self.enable_MW3=on==2

        def ple_MW2_Power_LineEdit_textEdited(self,text):
                try:
                        self.MW2_Power=float(text)
                except:
                        pass

        def ple_Stop_Button_Clicked(self,on):
                self.stopRequested = True

        def ple_Filename_LineEdit_textEdited(self,text):
                try:
                        self.Filename=text
                except:
                        pass

        def ple_MW3_Freq_LineEdit_textEdited(self,text):
                try:
                        self.MW3_Freq=float(text)
                except:
                        pass

        def ple_CWrepump_CheckBox_StateChanged(self,on):
                self.enable_Repump=on==2

        def ple_PerformFit_CheckBox_StateChanged(self,on):
                self.PerformFit=on==2
                if self.PerformFit:
                        self.sigUpdatePlots.emit()

        def ple_PeriodicSaving_CheckBox_StateChanged(self,on):
                self.PeriodicSaving=on==2

        def ple_Interval_LineEdit_textEdited(self,text):
                try:
                        self.Interval=float(text)
                except:
                        pass

        def ple_MaxIterations_LineEdit_textEdited(self,text):
                try:
                        self.MaxIterations=float(text)
                except:
                        pass

        def ple_Stoptime_LineEdit_textEdited(self,text):
                try:
                        self.Stoptime=float(text)
                except:
                        pass

        def fit_methods_ComboBox_StateChanged(self):
                print("Selected new Fitmethod Need to connect the data via ,,initialize_connections_and_defaultvalues,, of the gui. In line 61 or so.")