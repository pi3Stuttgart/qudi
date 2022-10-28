import numpy as np
import time

class rabi_default_values_and_widget_functions:
        F=False
        T=True
        rabi_Filename:str="Filename"

        rabi_Tau_Min:float=10 #ns
        rabi_Tau_Max:float=100 #ns
        rabi_Tau_Step:float=10 #ns
        rabi_Tau_Decay:float= 500 #ns

        rabi_MW1:bool=T
        rabi_MW1_Freq:float=70
        rabi_MW1_Power:float=-20
        rabi_MW2:bool=F
        rabi_MW2_Freq:float=140
        rabi_MW2_Power:float=-20
        rabi_MW3:bool=F
        rabi_MW3_Freq:float=210
        rabi_MW3_Power:float=-20

        rabi_A1:bool=F
        rabi_A2:bool=T
        rabi_A1Readout:bool=F
        rabi_A2Readout:bool=T
        rabi_InitTime:float= 30 #µs
        rabi_DecayInit:float= 1 #µs
        rabi_RepumpDecay:float =1 #µs
        rabi_CWRepump:bool=F
        rabi_PulsedRepump:bool=T
        rabi_RepumpDuration:float=5 #µs
        rabi_AOMDelay:float=450 #ns
        rabi_IntegrationTime:float= 1000 #ns
        rabi_Binning:float=10 #ns

        rabi_Interval:float=0
        rabi_PeriodicSaving:bool=F
        rabi_Stoptime:float=0 #ns

        rabi_ReadoutTime:float=3000 #ns
        rabi_ReadoutDecay:float=500 #ns

        rabi_MaxIterations:float=20
        rabi_PerformFit:bool=F
        rabi_NumberOfPeaks:float=0

        rabi_cb_max:float=100
        rabi_cb_high_percentile:float=100
        rabi_cb_low_percentile:float=0
        rabi_cb_min:float=0

        rabi_Runtime:float=0
        rabi_Frequencies_Fit:float=70
        rabi_Linewidths_Fit:float=1

        rabi_FitFunction:str='Cosinus'
        rabi_FitParams:str=""
        update_after_stop:bool=F

        pi_pulse:float=100 #ns

        def rabi_Stop_Button_Clicked(self,on):
                #print('done something with rabi_Stop_Button')
                self.stop_awg()
                #self.holder.awg.mcas.status = 0
                self.stoping_time=time.time()
                self.measurement_running=False
                self.time_differences.stop()

        def rabi_Continue_Button_Clicked(self,on):
                #print('done something with rabi_Continue_Button')
                self.continuing=True
                self.setup_seq()
                self.starting_time+=time.time()-self.stoping_time
                self.time_differences=self.setup_time_tagger(n_histograms=self.number_of_points_per_line,
                        binwidth=self.rabi_Binning*1000, #pulsed_Binning input is in ns.
                        n_bins=int(self.rabi_ReadoutTime/(self.rabi_Binning))
                        )       
                self.time_differences.start()
                self.measurement_running=True

        def rabi_Run_Button_Clicked(self,on):
                #print('done something with rabi_Run_Button')
                self.setup_seq()
                self.scanmatrix=np.zeros(np.array(self.time_differences.getData(),dtype=object).shape)
                self.starting_time=time.time()
                self.time_differences.clear()
                self.time_differences.start()
                self.measurement_running=True

        def rabi_InitTime_LineEdit_textEdited(self,text):
                #print('done something with rabi_InitTime_LineEdit. Text=',text)
                try:
                        self.rabi_InitTime=float(text.replace(",","."))
                except:
                        pass

        def rabi_Load_Button_Clicked(self,on):
                print('done something with rabi_Load_Button')
                
        def rabi_MW2_Freq_LineEdit_textEdited(self,text):
                #print('done something with rabi_MW2_Freq_LineEdit. Text=',text)
                try:
                        self.rabi_MW2_Freq=float(text.replace(",","."))
                except:
                        pass

        def rabi_RepumpDecay_LineEdit_textEdited(self,text):
                #print('done something with rabi_RepumpDecay_LineEdit. Text=',text)
                try:
                        self.rabi_RepumpDecay=float(text.replace(",","."))
                except:
                        pass

        def rabi_Stoptime_LineEdit_textEdited(self,text):
                #print('done something with rabi_Stoptime_LineEdit. Text=',text)
                try:
                        self.rabi_Stoptime=float(text.replace(",","."))
                except:
                        pass

        def rabi_CWRepump_CheckBox_StateChanged(self,on):
                #print('done something with rabi_CWRepump_CheckBox')
                self.rabi_CWRepump=on==2

        def rabi_Tau_Decay_lineEdit_textEdited(self,text):
                #print('done something with rabi_Tau_Decay_lineEdit. Text=',text)
                try:
                        self.rabi_Tau_Decay=float(text.replace(",","."))
                except:
                        pass

        def rabi_Tau_Max_lineEdit_textEdited(self,text):
                #print('done something with rabi_Tau_Max_lineEdit. Text=',text)
                try:
                        self.rabi_Tau_Max=float(text.replace(",","."))
                except:
                        pass

        def rabi_A1_CheckBox_StateChanged(self,on):
                #print('done something with rabi_A1_CheckBox')
                self.rabi_A1=on==2

        def rabi_RepumpDuration_LineEdit_textEdited(self,text):
                #print('done something with rabi_RepumpDuration_LineEdit. Text=',text)
                try:
                        self.rabi_RepumpDuration=float(text.replace(",","."))
                except:
                        pass

        def rabi_MW1_CheckBox_StateChanged(self,on):
                #print('done something with rabi_MW1_CheckBox')
                self.rabi_MW1=on==2

        def rabi_A1Readout_checkBox_StateChanged(self,on):
                #print('done something with rabi_A1Readout_checkBox')
                self.rabi_A1Readout=on==2

        def rabi_Interval_LineEdit_textEdited(self,text):
                #print('done something with rabi_Interval_LineEdit. Text=',text)
                try:
                        self.rabi_Interval=float(text.replace(",","."))
                except:
                        pass

        def rabi_PeriodicSaving_CheckBox_StateChanged(self,on):
                #print('done something with rabi_PeriodicSaving_CheckBox')
                self.rabi_PeriodicSaving=on==2

        def rabi_MW2_Power_LineEdit_textEdited(self,text):
                #print('done something with rabi_MW2_Power_LineEdit. Text=',text)
                try:
                        self.rabi_MW2_Power=float(text.replace(",","."))
                except:
                        pass

        def rabi_DecayInit_LineEdit_textEdited(self,text):
                #print('done something with rabi_DecayInit_LineEdit. Text=',text)
                try:
                        self.rabi_DecayInit=float(text.replace(",","."))
                except:
                        pass

        def rabi_A2Readout_checkBox_StateChanged(self,on):
                #print('done something with rabi_A2Readout_checkBox')
                self.rabi_A2Readout=on==2

        def rabi_cb_max_DoubleSpinBox_Edited(self,value):
                #print('done something with rabi_cb_max_DoubleSpinBox. Value=',value)
                self.rabi_cb_max=value

        def rabi_cb_high_percentile_DoubleSpinBox_Edited(self,value):
                #print('done something with rabi_cb_high_percentile_DoubleSpinBox. Value=',value)
                self.rabi_cb_high_percentile=value

        def rabi_cb_low_percentile_DoubleSpinBox_Edited(self,value):
                #print('done something with rabi_cb_low_percentile_DoubleSpinBox. Value=',value)
                self.rabi_cb_low_percentile=value

        def rabi_cb_min_DoubleSpinBox_Edited(self,value):
                #print('done something with rabi_cb_min_DoubleSpinBox. Value=',value)
                self.rabi_cb_min=value

        def rabi_Save_Button_Clicked(self,on):
                self.save_rabi_data()
                print('done something with rabi_Save_Button')

        def rabi_MW1_Freq_LineEdit_textEdited(self,text):
                #print('done something with rabi_MW1_Freq_LineEdit. Text=',text)
                try:
                        self.rabi_MW1_Freq=float(text.replace(",","."))
                except:
                        pass

        def rabi_Tau_Min_lineEdit_textEdited(self,text):
                #print('done something with rabi_Tau_Min_lineEdit. Text=',text)
                try:
                        self.rabi_Tau_Min=float(text.replace(",","."))
                except:
                        pass

        def rabi_MW2_CheckBox_StateChanged(self,on):
                #print('done something with rabi_MW2_CheckBox')
                self.rabi_MW2=on==2

        def rabi_ReadoutTime_LineEdit_textEdited(self,text):
                #print('done something with rabi_ReadoutTime_LineEdit. Text=',text)
                try:
                        self.rabi_ReadoutTime=float(text.replace(",","."))
                except:
                        pass

        def rabi_PulsedRepump_CheckBox_StateChanged(self,on):
                #print('done something with rabi_PulsedRepump_CheckBox')
                self.rabi_PulsedRepump=on==2

        def rabi_MW3_CheckBox_StateChanged(self,on):
                #print('done something with rabi_MW3_CheckBox')
                self.rabi_MW3=on==2

        def rabi_Tau_Step_lineEdit_textEdited(self,text):
                #print('done something with rabi_Tau_Step_lineEdit. Text=',text)
                try:
                        self.rabi_Tau_Step=float(text.replace(",","."))
                except:
                        pass

        def rabi_A2_CheckBox_StateChanged(self,on):
                #print('done something with rabi_A2_CheckBox')
                self.rabi_A2=on==2

        def rabi_MW3_Freq_LineEdit_textEdited(self,text):
                #print('done something with rabi_MW3_Freq_LineEdit. Text=',text)
                try:
                        self.rabi_MW3_Freq=float(text.replace(",","."))
                except:
                        pass

        def rabi_MW3_Power_LineEdit_textEdited(self,text):
                #print('done something with rabi_MW3_Power_LineEdit. Text=',text)
                try:
                        self.rabi_MW3_Power=float(text.replace(",","."))
                except:
                        pass

        def rabi_AOMDelay_LineEdit_textEdited(self,text):
                #print('done something with rabi_AOMDelay_LineEdit. Text=',text)
                try:
                        self.rabi_AOMDelay=float(text.replace(",","."))
                except:
                        pass

        def rabi_Filename_LineEdit_textEdited(self,text):
                #print('done something with rabi_Filename_LineEdit. Text=',text)
                try:
                        self.rabi_Filename=text
                except:
                        pass

        def rabi_ReadoutDecay_LineEdit_textEdited(self,text):
                #print('done something with rabi_ReadoutDecay_LineEdit. Text=',text)
                try:
                        self.rabi_ReadoutDecay=float(text.replace(",","."))
                except:
                        pass

        def rabi_MW1_Power_LineEdit_textEdited(self,text):
                #print('done something with rabi_MW1_Power_LineEdit. Text=',text)
                try:
                        self.rabi_MW1_Power=float(text.replace(",","."))
                except:
                        pass

        def rabi_MaxIterations_LineEdit_textEdited(self,text):
                #print('done something with rabi_MaxIterations_LineEdit. Text=',text)
                try:
                        self.rabi_MaxIterations=float(text.replace(",","."))
                except:
                        pass

        def rabi_PerformFit_CheckBox_StateChanged(self,on):
                #print('done something with rabi_PerformFit_CheckBox')
                self.rabi_PerformFit=on==2
                self.update_after_stop=True #sorry magnificient programmer going throug this,      
                self.sigRabiPlotsUpdated.emit()

        def rabi_NumberOfPeaks_LineEdit_textEdited(self,text):
                #print('done something with rabi_NumberOfPeaks_LineEdit. Text=',text)
                try:
                        self.rabi_NumberOfPeaks=float(text.replace(",","."))
                except:
                        pass

        def rabi_Binning_LineEdit_textEdited(self,text):
                #print('done something with rabi_Binning_LineEdit. Text=',text)
                try:
                        self.rabi_Binning=float(text.replace(",","."))
                except:
                        pass

        def rabi_IntegrationTime_lineEdit_textEdited(self,text):
                #print('done something with rabi_IntegrationTime_lineEdit. Text=',text)
                try:
                        rabi_IntegrationTime=float(text.replace(",","."))
                        if rabi_IntegrationTime>=2*self.rabi_Binning:
                                self.rabi_IntegrationTime=rabi_IntegrationTime

                except:
                        pass

        def rabi_SelectFit_ComboBox_currentTextChanged(self, text):
                print("combo box sagt: ", text)
                self.rabi_FitFunction = text