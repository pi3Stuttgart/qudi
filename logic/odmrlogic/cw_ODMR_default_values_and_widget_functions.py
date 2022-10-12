import numpy as np
import time

class cw_ODMR_default_values_and_widget_functions:
        F=False
        T=True
        cw_Filename:str="filename"
        cw_MW1:bool=T
        cw_MW2:bool=F
        cw_MW3:bool=F

        cw_MW1_Power:float=-20 #dBm
        cw_MW2_Power:float=-20 #dBm
        cw_MW3_Power:float= -20 #dBm

        cw_StartFreq:float=50 #MHz
        cw_StopFreq:float=90 #MHz
        cw_Stepsize:float=10 #MHz
        cw_MW2_Freq:float=140 #MHz
        cw_MW3_Freq:float=140 #MHz

        cw_A1:bool=F
        cw_A2:bool=T
        cw_PulsedRepump:bool=T
        cw_RepumpDuration:float=5 #µs
        cw_RepumpDecay:float=3 #µs
        cw_CWRepump:bool=F
        cw_Stoptime:float=0 #s
        cw_PeriodicSaving:bool=F
        cw_Interval:float=0 #s

        cw_PerformFit:bool=F
        cw_SelectLorentzianFit:bool=F
        cw_SelectGaussianFit:bool=T
        
        cw_SecondsPerPoint:float=0.02

        cw_Runtime:float=0

        cw_segment_length:float = 100 #length of on-time of a single frequency during cw scan when multiplied by loop_counts in "ODMRLogic.setup_seq()".

        cw_odmr_cb_max:float=100
        cw_odmr_cb_high_percentile:float=100
        cw_odmr_cb_low_percentile:float=0
        cw_odmr_cb_min:float=0
        cw_NumberOfLines:int=20

        cw_update_after_stop:bool=F
        
        def cw_NumberOfLines_LineEdit_textEdited(self,text):
                try:
                        self.cw_NumberOfLines=int(text)
                except:
                        pass

        def cw_Filename_LineEdit_textEdited(self,text):
                try:
                        self.cw_Filename=text
                except:
                        pass

        def cw_StartFreq_LineEdit_textEdited(self,text):
                try:
                        self.cw_StartFreq=float(text)
                except:
                        pass

        def cw_Load_Button_Clicked(self,on):
                print('Loadiing not implemented yet.')

        def cw_A1_CheckBox_StateChanged(self,on):
                self.cw_A1=on==2

        def cw_CWRepump_CheckBox_StateChanged(self,on):
                self.cw_CWRepump=on==2

        def cw_Stoptime_LineEdit_textEdited(self,text):
                try:
                        self.cw_Stoptime=float(text)
                except:
                        pass

        def cw_Interval_LineEdit_textEdited(self,text):
                try:
                        self.cw_Interval=float(text)
                except:
                        pass

        def cw_RepumpDuration_LineEdit_textEdited(self,text):
                try:
                        self.cw_RepumpDuration=float(text)
                except:
                        pass

        def cw_Save_Button_Clicked(self,on):
                self.holder.save_cw_odmr_data()

        def cw_MW3_Power_LineEdit_textEdited(self,text):
                try:
                        self.cw_MW3_Power=float(text)
                except:
                        pass

        def cw_MW3_CheckBox_StateChanged(self,on):
                self.cw_MW3=on==2

        def cw_MW3_Freq_LineEdit_textEdited(self,text):
                try:
                        self.cw_MW3_Freq=float(text)
                except:
                        pass

        def cw_MW2_Power_LineEdit_textEdited(self,text):
                try:
                        self.cw_MW2_Power=float(text)
                except:
                        pass

        def cw_MW1_CheckBox_StateChanged(self,on):
                self.cw_MW1=on==2

        def cw_MaxIterations_LineEdit_textEdited(self,text):
                try:
                        self.cw_MaxIterations=float(text)
                except:
                        pass

        def cw_RepumpDecay_LineEdit_textEdited(self,text):
                try:
                        self.cw_RepumpDecay=float(text)
                except:
                        pass

        def cw_NumberOfPeaks_LineEdit_textEdited(self,text):
                try:
                        self.NumberOfPeaks=float(text)
                except:
                        pass

        def cw_Continue_Button_Clicked(self,on):
                self.continuing=True
                self.setup_seq()
                self.starting_time+=time.time()-self.stoping_time
                self.time_differences = self.holder.setup_time_tagger(n_histograms=self.number_of_points_per_line,
                binwidth=int(self.cw_SecondsPerPoint*1e12),
                n_bins=1
                )
                self.time_differences.start()
                self.measurement_running=True


        def cw_A2_CheckBox_StateChanged(self,on):
                self.cw_A2=on==2

        def cw_MW2_CheckBox_StateChanged(self,on):
                self.cw_MW2=on==2

        def cw_MW2_Freq_LineEdit_textEdited(self,text):
                try:
                        self.cw_MW2_Freq=float(text)
                except:
                        pass

        def cw_PulsedRepump_CheckBox_StateChanged(self,on):
                self.cw_PulsedRepump=on==2

        def cw_MW1_Power_LineEdit_textEdited(self,text):
                try:
                        self.cw_MW1_Power=float(text)
                except:
                        pass

        def cw_PeriodicSaving_CheckBox_StateChanged(self,on):
                self.cw_PeriodicSaving=on==2

        def cw_Stop_Button_Clicked(self,on):
                self.holder.stop_awg()
                self.stoping_time=time.time()
                self.measurement_running=False
                self.time_differences.stop()

        def cw_StopFreq_LineEdit_textEdited(self,text):
                try:
                        self.cw_StopFreq=float(text)
                except:
                        pass

        def cw_SecondsPerPoint_LineEdit_textEdited(self,text):
                try:
                        self.cw_SecondsPerPoint=float(text)
                except:
                        pass

        def cw_Run_Button_Clicked(self,on):
                self.holder.Contrast_Fit = ''
                self.holder.Frequencies_Fit = ''
                self.holder.Linewidth_Fit = ''
                self.setup_seq()
                self.scanmatrix=np.zeros((int(self.cw_NumberOfLines),self.number_of_points_per_line))
                self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
                self.data=0
                self.starting_time=time.time()
                self.time_differences.clear()
                self.time_differences.start()
                self.measurement_running=True

        def cw_PerformFit_CheckBox_StateChanged(self,on):
                self.cw_PerformFit=on==2
                self.cw_update_after_stop=True
                self.holder.sigOdmrPlotsUpdated.emit()

        def cw_Stepsize_LineEdit_textEdited(self,text):
                try:
                        self.cw_Stepsize=float(text)
                except:
                        pass

        def cw_SelectGaussianFit_RadioButton_clicked(self):
                self.cw_SelectGaussianFit=True
                self.cw_SelectLorentzianFit=False
                
        def cw_SelectLorentzianFit_RadioButton_clicked(self):
                self.cw_SelectGaussianFit=False
                self.cw_SelectLorentzianFit=True



