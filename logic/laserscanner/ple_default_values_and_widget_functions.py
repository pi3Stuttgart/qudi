import numpy as np
import time

class ple_default_values_and_widget_functions:
        lock_laser:bool=False
        RepumpDuration:float = 10
        RepumpDecay:float = 1000

        Filename:str = ''
        stoptime:float = 0
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

        def ple_PulsedRepump_CheckBox_StateChanged(self,value):
                self.enable_PulsedRepump=value==2

        def ple_RepumpWhenIonized_CheckBox_StateChanged(self,value):
                self.RepumpWhenIonized=value==2

        def ple_MW2_CheckBox_StateChanged(self,value):
                self.enable_MW2=value==2

        def ple_Continue_Button_Clicked(self,on):
                print('done something with ple_Continue_Button')

        def ple_MW1_CheckBox_StateChanged(self,value):
                self.enable_MW1=value==2

        def ple_Save_Button_Clicked(self,on):
                self.save_data(tag=self.Filename)

        def ple_MW1_Power_LineEdit_textEdited(self,text):
                try:
                        self.MW1_Power=float(text.replace(",","."))
                except:
                        pass

        def ple_MW3_Power_LineEdit_textEdited(self,text):
                try:
                        self.MW3_Power=float(text.replace(",","."))
                except:
                        pass

        def ple_RepumpDuration_LineEdit_textEdited(self,text):
                try:
                        self.RepumpDuration=float(text.replace(",","."))
                except:
                        pass
        
        def ple_NumberOfPeaks_LineEdit_textEdited(self,text):
                try:
                        self.NumberOfPeaks=int(text)
                except:
                        pass

        def ple_A1_CheckBox_StateChanged(self,value):
                self.enable_A1=value==2

        def ple_A2_CheckBox_StateChanged(self,value):
                self.enable_A2=value==2

        def ple_Lock_Laser_CheckBox_StateChanged(self,value):
                self.lock_laser=value==2

        # def ple_RepumpDecay_LineEdit_textEdited(self,text):
        #         try:
        #                 self.RepumpDecay=float(text.replace(",","."))
        #         except:
        #                 pass

        def ple_MW1_Freq_LineEdit_textEdited(self,text):
                try:
                        self.MW1_Freq=float(text.replace(",","."))
                except:
                        pass

        def ple_MW2_Freq_LineEdit_textEdited(self,text):
                try:
                        self.MW2_Freq=float(text.replace(",","."))
                except:
                        pass

        def ple_Run_Button_Clicked(self,on):
                self.start_scanning()

        def ple_MW3_CheckBox_StateChanged(self,value):
                self.enable_MW3=value==2

        def ple_MW2_Power_LineEdit_textEdited(self,text):
                try:
                        self.MW2_Power=float(text.replace(",","."))
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
                        self.MW3_Freq=float(text.replace(",","."))
                except:
                        pass

        def ple_CWrepump_CheckBox_StateChanged(self,value):
                self.enable_Repump=value==2

        def ple_PerformFit_CheckBox_StateChanged(self,value):
                self.PerformFit=value==2
                if self.PerformFit:
                        self.sigUpdatePlots.emit()
   
        def ple_MaxIterations_LineEdit_textEdited(self,text):
                try:
                        self.MaxIterations=float(text.replace(",","."))
                except:
                        pass

        def ple_Stoptime_LineEdit_textEdited(self,text):
                try:
                        self.stoptime=float(text.replace(",","."))
                except:
                        pass

        def fit_methods_ComboBox_StateChanged(self):
                print("Selected new Fitmethod Need to connect the data via ,,initialize_connections_and_defaultvalues,, of the gui. In line 61 or so.")

        def select_scan_range(self, index):
                print(index)
                print("Selected new Fitmethod Need to connect the data via ,,initialize_connections_and_defaultvalues,, of the gui. In line 61 or so.")