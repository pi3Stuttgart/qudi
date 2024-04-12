import numpy as np
import time

class arb_seq_default_values_and_widget_functions:
        F=False
        T=True

        

        arbseq_MW1:bool=F
        arbseq_MW1_Freq:float=333
        arbseq_MW1_Power:float=-99
        arbseq_MW2:bool=F
        arbseq_MW2_Freq:float=70
        arbseq_MW2_Power:float=-10
        arbseq_MW3:bool=F
        arbseq_MW3_Freq:float=333
        arbseq_MW3_Power:float=-99
        arbseq_MW4:bool=F
        arbseq_MW4_Freq:float=333
        arbseq_MW4_Power:float=-99
        arbseq_MW4_Duration:float=333
        arbseq_MW5:bool=F
        arbseq_MW5_Freq:float=333
        arbseq_MW5_Power:float=-99
        arbseq_MW5_Duration:float=333

        arbseq_A1:bool=T
        arbseq_A2:bool=T
        arbseq_A1Readout:bool=T
        arbseq_A2Readout:bool=T
        arbseq_CWRepump:bool=T
        arbseq_PulsedRepump:bool=F
        
        arbseq_IntegrationTime:float= 333 #ns
        

        arbseq_Interval:float=0
        arbseq_PeriodicSaving:bool=F
        arbseq_Stoptime:float=300 #ns

        

        arbseq_MaxIterations:float=20
        arbseq_PerformFit:bool=F
        arbseq_NumberOfPeaks:float=0

        arbseq_cb_max:float=100
        arbseq_cb_high_percentile:float=100
        arbseq_cb_low_percentile:float=0
        arbseq_cb_min:float=0

        arbseq_Runtime:float=0
        arbseq_Frequencies_Fit:float=70
        arbseq_Linewidths_Fit:float=1

        arbseq_FitFunction:str='Cosinus'
        arbseq_FitParams:str=""
        update_after_stop:bool=F

        pi_pulse:float=100 #ns

        def arbseq_Stop_Button_Clicked(self,on):
                #print('done something with arbseq_Stop_Button')
                self.stop_awg()
                #self.holder.awg.mcas.status = 0
                self.stoping_time=time.time()
                self.measurement_running=False
                self.time_differences.stop()
                #del self._awg.mcas_dict['ArbSeq']

        def arbseq_Continue_Button_Clicked(self,on):
                #print('done something with arbseq_Continue_Button')
                self.continuing=True
                self.setup_seq()
                self.starting_time+=time.time()-self.stoping_time
                self.time_differences=self.setup_time_tagger(n_histograms=self.number_of_points_per_line,
                        binwidth=self.arbseq_Binning*1000, #pulsed_Binning input is in ns.
                        n_bins=int(self.arbseq_ReadoutTime/(self.arbseq_Binning))
                        )       
                self.time_differences.start()
                self.measurement_running=True

        def arbseq_Run_Button_Clicked(self,on):
                #print('done something with arbseq_Run_Button')
                self.setup_seq()
                self.scanmatrix=np.zeros(np.array(self.time_differences.getData(),dtype=object).shape)
                self.starting_time=time.time()
                self.time_differences.clear()
                self.time_differences.start()
                self.measurement_running=True

        def arbseq_InitTime_LineEdit_textEdited(self,text):
                #print('done something with arbseq_InitTime_LineEdit. Text=',text)
                try:
                        self.arbseq_InitTime=float(text.replace(",","."))
                except:
                        pass

        def arbseq_Load_Button_Clicked(self,on):
                print('done something with arbseq_Load_Button')
                

        def arbseq_RepumpDecay_LineEdit_textEdited(self,text):
                #print('done something with arbseq_RepumpDecay_LineEdit. Text=',text)
                try:
                        self.arbseq_RepumpDecay=float(text.replace(",","."))
                except:
                        pass

        def arbseq_Stoptime_LineEdit_textEdited(self,text):
                #print('done something with arbseq_Stoptime_LineEdit. Text=',text)
                try:
                        self.arbseq_Stoptime=float(text.replace(",","."))
                except:
                        pass

        def arbseq_CWRepump_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_CWRepump_CheckBox')
                self.arbseq_CWRepump=on==2

        def arbseq_Tau_Decay_lineEdit_textEdited(self,text):
                #print('done something with arbseq_Tau_Decay_lineEdit. Text=',text)
                try:
                        self.arbseq_Tau_Decay=float(text.replace(",","."))
                except:
                        pass

        def arbseq_Tau_Max_lineEdit_textEdited(self,text):
                #print('done something with arbseq_Tau_Max_lineEdit. Text=',text)
                try:
                        self.arbseq_Tau_Max=float(text.replace(",","."))
                except:
                        pass

        def arbseq_A1_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_A1_CheckBox')
                self.arbseq_A1=on==2

        def arbseq_RepumpDuration_LineEdit_textEdited(self,text):
                #print('done something with arbseq_RepumpDuration_LineEdit. Text=',text)
                try:
                        self.arbseq_RepumpDuration=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MW1_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_MW1_CheckBox')
                self.arbseq_MW1=on==2

        def arbseq_A1Readout_checkBox_StateChanged(self,on):
                #print('done something with arbseq_A1Readout_checkBox')
                self.arbseq_A1Readout=on==2

        def arbseq_Interval_LineEdit_textEdited(self,text):
                #print('done something with arbseq_Interval_LineEdit. Text=',text)
                try:
                        self.arbseq_Interval=float(text.replace(",","."))
                except:
                        pass

        def arbseq_PeriodicSaving_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_PeriodicSaving_CheckBox')
                self.arbseq_PeriodicSaving=on==2

        def arbseq_MW2_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_MW2_CheckBox')
                self.arbseq_MW2=on==2
                
        def arbseq_MW2_Freq_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Freq_LineEdit. Text=',text)
                try:
                        self.arbseq_MW2_Freq=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MW2_Power_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW2_Power=float(text.replace(",","."))
                except:
                        pass
        
        def arbseq_MW4_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_MW2_CheckBox')
                self.arbseq_MW4=on==2

        def arbseq_MW4_Freq_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Freq_LineEdit. Text=',text)
                try:
                        self.arbseq_MW4_Freq=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MW4_Power_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW4_Power=float(text.replace(",","."))
                except:
                        pass
        
        def arbseq_MW4_Duration_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW4_Duration=float(text.replace(",","."))
                except:
                        pass
        
        def arbseq_MW5_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_MW2_CheckBox')
                self.arbseq_MW5=on==2

        def arbseq_MW5_Freq_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Freq_LineEdit. Text=',text)
                try:
                        self.arbseq_MW5_Freq=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MW5_Power_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW5_Power=float(text.replace(",","."))
                except:
                        pass
        
        def arbseq_MW5_Duration_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW2_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW5_Duration=float(text.replace(",","."))
                except:
                        pass

        def arbseq_DecayInit_LineEdit_textEdited(self,text):
                #print('done something with arbseq_DecayInit_LineEdit. Text=',text)
                try:
                        self.arbseq_DecayInit=float(text.replace(",","."))
                except:
                        pass

        def arbseq_A2Readout_checkBox_StateChanged(self,on):
                #print('done something with arbseq_A2Readout_checkBox')
                self.arbseq_A2Readout=on==2

        def arbseq_cb_max_DoubleSpinBox_Edited(self,value):
                #print('done something with arbseq_cb_max_DoubleSpinBox. Value=',value)
                self.arbseq_cb_max=value

        def arbseq_cb_high_percentile_DoubleSpinBox_Edited(self,value):
                #print('done something with arbseq_cb_high_percentile_DoubleSpinBox. Value=',value)
                self.arbseq_cb_high_percentile=value

        def arbseq_cb_low_percentile_DoubleSpinBox_Edited(self,value):
                #print('done something with arbseq_cb_low_percentile_DoubleSpinBox. Value=',value)
                self.arbseq_cb_low_percentile=value

        def arbseq_cb_min_DoubleSpinBox_Edited(self,value):
                #print('done something with arbseq_cb_min_DoubleSpinBox. Value=',value)
                self.arbseq_cb_min=value

        def arbseq_Save_Button_Clicked(self,on):
                self.save_arbseq_data(self.arbseq_Filename)
                print('done something with arbseq_Save_Button')

        def arbseq_MW1_Freq_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW1_Freq_LineEdit. Text=',text)
                try:
                        self.arbseq_MW1_Freq=float(text.replace(",","."))
                except:
                        pass

        def arbseq_Tau_Min_lineEdit_textEdited(self,text):
                #print('done something with arbseq_Tau_Min_lineEdit. Text=',text)
                try:
                        self.arbseq_Tau_Min=float(text.replace(",","."))
                except:
                        pass


        def arbseq_ReadoutTime_LineEdit_textEdited(self,text):
                #print('done something with arbseq_ReadoutTime_LineEdit. Text=',text)
                try:
                        self.arbseq_ReadoutTime=float(text.replace(",","."))
                except:
                        pass

        def arbseq_PulsedRepump_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_PulsedRepump_CheckBox')
                self.arbseq_PulsedRepump=on==2

        def arbseq_MW3_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_MW3_CheckBox')
                self.arbseq_MW3=on==2

        def arbseq_Tau_Step_lineEdit_textEdited(self,text):
                #print('done something with arbseq_Tau_Step_lineEdit. Text=',text)
                try:
                        self.arbseq_Tau_Step=float(text.replace(",","."))
                except:
                        pass

        def arbseq_A2_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_A2_CheckBox')
                self.arbseq_A2=on==2

        def arbseq_MW3_Freq_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW3_Freq_LineEdit. Text=',text)
                try:
                        self.arbseq_MW3_Freq=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MW3_Power_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW3_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW3_Power=float(text.replace(",","."))
                except:
                        pass

        def arbseq_AOMDelay_LineEdit_textEdited(self,text):
                #print('done something with arbseq_AOMDelay_LineEdit. Text=',text)
                try:
                        self.arbseq_AOMDelay=float(text.replace(",","."))
                except:
                        pass

        def arbseq_Filename_LineEdit_textEdited(self,text):
                #print('done something with arbseq_Filename_LineEdit. Text=',text)
                try:
                        self.arbseq_Filename=text
                except:
                        pass

        def arbseq_ReadoutDecay_LineEdit_textEdited(self,text):
                #print('done something with arbseq_ReadoutDecay_LineEdit. Text=',text)
                try:
                        self.arbseq_ReadoutDecay=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MW1_Power_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MW1_Power_LineEdit. Text=',text)
                try:
                        self.arbseq_MW1_Power=float(text.replace(",","."))
                except:
                        pass

        def arbseq_MaxIterations_LineEdit_textEdited(self,text):
                #print('done something with arbseq_MaxIterations_LineEdit. Text=',text)
                try:
                        self.arbseq_MaxIterations=float(text.replace(",","."))
                except:
                        pass

        def arbseq_PerformFit_CheckBox_StateChanged(self,on):
                #print('done something with arbseq_PerformFit_CheckBox')
                self.arbseq_PerformFit=on==2
                self.update_after_stop=True #sorry magnificient programmer going throug this,      
                self.sigArbSeqPlotsUpdated.emit()

        def arbseq_NumberOfPeaks_LineEdit_textEdited(self,text):
                #print('done something with arbseq_NumberOfPeaks_LineEdit. Text=',text)
                try:
                        self.arbseq_NumberOfPeaks=int(text.replace(",","."))
                except:
                        pass

        def arbseq_Binning_LineEdit_textEdited(self,text):
                #print('done something with arbseq_Binning_LineEdit. Text=',text)
                try:
                        self.arbseq_Binning=float(text.replace(",","."))
                except:
                        pass

        def arbseq_IntegrationTime_lineEdit_textEdited(self,text):
                #print('done something with arbseq_IntegrationTime_lineEdit. Text=',text)
                try:
                        arbseq_IntegrationTime=float(text.replace(",","."))
                        if arbseq_IntegrationTime>=2*self.arbseq_Binning:
                                self.arbseq_IntegrationTime=arbseq_IntegrationTime

                except:
                        pass

        def arbseq_SelectFit_ComboBox_currentTextChanged(self, text):
                print("combo box sagt: ", text)
                self.arbseq_FitFunction = text