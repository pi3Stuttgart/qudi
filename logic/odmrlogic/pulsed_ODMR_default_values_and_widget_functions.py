import numpy as np
import time

class pulsed_ODMR_default_values_and_widget_functions:
        F=False
        T=True
        pulsed_Filename:str="filename"
        pulsed_MW1:bool=T
        pulsed_MW2:bool=F
        pulsed_MW3:bool=F

        pulsed_MW1_Power:float=-41 #dBm
        pulsed_MW2_Power:float=-20 #dBm
        pulsed_MW3_Power:float=-20 #dBm

        pulsed_StartFreq:float=30 #MHz
        pulsed_StopFreq:float=38 #MHz
        pulsed_Stepsize:float=0.2 #MHz
        pulsed_MW2_Freq:float=173 #MHz
        pulsed_MW3_Freq:float=140 #MHz

        pulsed_A1:bool=F
        pulsed_A2:bool=T
        pulsed_A1Readout:bool=F
        pulsed_A2Readout:bool=T
        pulsed_PulsedRepump:bool=T
        pulsed_RepumpDuration:float=5
        pulsed_RepumpDecay:float=3
        pulsed_CWRepump:bool=F

        pulsed_PiDecay:float =500#ns
        pulsed_piPulseDuration:float= 1088#ns

        pulsed_Stoptime:float=0
        pulsed_PeriodicSaving:bool=F
        pulsed_Interval:float=0

        pulsed_AOMDelay:float=450#ns
        pulsed_InitTime:float=10 #µs
        pulsed_DecayInit:float= 1 #µs
        pulsed_ReadoutTime:float= 2 #µs
        pulsed_ReadoutDecay:float= 0.5 #µs

        pulsed_PerformFit:bool=F
        
        pulsed_SecondsPerPoint:float=0.02

        pulsed_Runtime=0
        pulsed_Binning = 100

        pulsed_odmr_cb_max:float=100
        pulsed_odmr_cb_high_percentile:float=100
        pulsed_odmr_cb_low_percentile:float=0
        pulsed_odmr_cb_min:float=0

        pulsed_NumberOfLines:int=20
        pulsed_update_after_stop:bool=F

        def pulsed_NumberOfLines_LineEdit_textEdited(self,text):
                #print('done something with pulsed_NumberOfLines_LineEdit. Text=',text)
                try:
                        self.pulsed_NumberOfLines=int(text)
                except:
                        pass


        def pulsed_PeriodicSaving_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_PeriodicSaving_CheckBox')
                self.pulsed_PeriodicSaving=on==2

        def pulsed_MW3_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_MW3_CheckBox')
                self.pulsed_MW3=on==2

        def pulsed_Interval_LineEdit_textEdited(self,text):
                #print('done something with pulsed_Interval_LineEdit. Text=',text)
                try:
                        self.pulsed_Interval=float(text.replace(",","."))
                except:
                        pass

        def pulsed_StartFreq_LineEdit_textEdited(self,text):
                #print('done something with pulsed_StartFreq_LineEdit. Text=',text)
                try:
                        self.pulsed_StartFreq=float(text.replace(",","."))
                except:
                        pass

        def pulsed_A2_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_A2_CheckBox')
                self.pulsed_A2=on==2

        def pulsed_MW2_Freq_LineEdit_textEdited(self,text):
                #print('done something with pulsed_MW2_Freq_LineEdit. Text=',text)
                try:
                        self.pulsed_MW2_Freq=float(text.replace(",","."))
                except:
                        pass

        def pulsed_A2Readout_checkBox_StateChanged(self,on):
                #print('done something with pulsed_A2Readout_checkBox')
                self.pulsed_A2Readout=on==2

        def pulsed_A1_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_A1_CheckBox')
                self.pulsed_A1=on==2

        def pulsed_MW1_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_MW1_CheckBox')
                self.pulsed_MW1=on==2

        def pulsed_PerformFit_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_PerformFit_CheckBox')
                self.pulsed_PerformFit=on==2
                self.pulsed_update_after_stop=True
                self.holder.sigOdmrPlotsUpdated.emit()

        def pulsed_MW1_Power_LineEdit_textEdited(self,text):
                #print('done something with pulsed_MW1_Power_LineEdit. Text=',text)
                try:
                        self.pulsed_MW1_Power=float(text.replace(",","."))
                except:
                        pass

        def pulsed_StopFreq_LineEdit_textEdited(self,text):
                #print('done something with pulsed_StopFreq_LineEdit. Text=',text)
                try:
                        self.pulsed_StopFreq=float(text.replace(",","."))
                except:
                        pass

        def pulsed_Filename_LineEdit_textEdited(self,text):
                #print('done something with pulsed_Filename_LineEdit. Text=',text)
                try:
                        self.pulsed_Filename=text
                except:
                        pass

        def pulsed_PulsedRepump_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_PulsedRepump_CheckBox')
                self.pulsed_PulsedRepump=on==2

        def pulsed_Stop_Button_Clicked(self,on):
                #print('done something with pulsed_Stop_Button')
                #self.holder.SigCheckReady_Beacon.disconnect()
                self.holder.stop_awg()
                #self.holder.awg.mcas.status = 0
                self.stoping_time=time.time()
                self.time_differences.stop()
                self.measurement_running=False
                self.pulsed_odmr_refocus_running=False
                

        def pulsed_MW2_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_MW2_CheckBox')
                self.pulsed_MW2=on==2

        def pulsed_MW3_Power_LineEdit_textEdited(self,text):
                #print('done something with pulsed_MW3_Power_LineEdit. Text=',text)
                try:
                        self.pulsed_MW3_Power=float(text.replace(",","."))
                except:
                        pass

        def pulsed_MaxIterations_LineEdit_textEdited(self,text):
                #print('done something with pulsed_MaxIterations_LineEdit. Text=',text)
                try:
                        self.pulsed_MaxIterations=float(text.replace(",","."))
                except:
                        pass

        def pulsed_MW2_Power_LineEdit_textEdited(self,text):
                #print('done something with pulsed_MW2_Power_LineEdit. Text=',text)
                try:
                        self.pulsed_MW2_Power=float(text.replace(",","."))
                except:
                        pass

        def pulsed_SecondsPerPoint_LineEdit_textEdited(self,text):
                #print('done something with pulsed_SecondsPerPoint_LineEdit. Text=',text)
                try:
                        self.pulsed_SecondsPerPoint=float(text.replace(",","."))
                except:
                        pass

        def pulsed_CWRepump_CheckBox_StateChanged(self,on):
                #print('done something with pulsed_CWRepump_CheckBox')
                self.pulsed_CWRepump=on==2

        def pulsed_Load_Button_Clicked(self,on):
                print('Loading not implemented yet.')

        def pulsed_Continue_Button_Clicked(self,on):
                self.continuing=True
                self.setup_seq()
                self.starting_time+=time.time()-self.stoping_time
                self.time_differences=self.holder.setup_time_tagger(n_histograms=self.number_of_points_per_line,
                binwidth=self.pulsed_Binning*1000, #pulsed_Binning input is in ns.
                n_bins=int(self.pulsed_ReadoutTime*1e6/(self.pulsed_Binning*1000))
                )
                self.time_differences.start()
                self.measurement_running=True


        def pulsed_Stepsize_LineEdit_textEdited(self,text):
                #print('done something with pulsed_Stepsize_LineEdit. Text=',text)
                try:
                        self.pulsed_Stepsize=float(text.replace(",","."))
                except:
                        pass

        def pulsed_MW3_Freq_LineEdit_textEdited(self,text):
                #print('done something with pulsed_MW3_Freq_LineEdit. Text=',text)
                try:
                        self.pulsed_MW3_Freq=float(text.replace(",","."))
                except:
                        pass

        def pulsed_NumberOfPeaks_LineEdit_textEdited(self,text):
                #print('done something with pulsed_NumberOfPeaks_LineEdit. Text=',text)
                try:
                        self.NumberOfPeaks=int(text.replace(",","."))
                        self.holder.NumberOfPeaks=self.NumberOfPeaks
                except:
                        pass

        def pulsed_odmr_cb_max_DoubleSpinBox_Edited(self,value):
                #print('done something with pulsed_odmr_cb_max_DoubleSpinBox. Value=',value)
                self.pulsed_odmr_cb_max=value

        def pulsed_odmr_cb_high_percentile_DoubleSpinBox_Edited(self,value):
                #print('done something with pulsed_odmr_cb_high_percentile_DoubleSpinBox. Value=',value)
                self.pulsed_odmr_cb_high_percentile=value

        def pulsed_odmr_cb_low_percentile_DoubleSpinBox_Edited(self,value):
                #print('done something with pulsed_odmr_cb_low_percentile_DoubleSpinBox. Value=',value)
                self.pulsed_odmr_cb_low_percentile=value

        def pulsed_odmr_cb_min_DoubleSpinBox_Edited(self,value):
                #print('done something with pulsed_odmr_cb_min_DoubleSpinBox. Value=',value)
                self.pulsed_odmr_cb_min=value

        def pulsed_Stoptime_LineEdit_textEdited(self,text):
                #print('done something with pulsed_Stoptime_LineEdit. Text=',text)
                try:
                        self.pulsed_Stoptime=float(text.replace(",","."))
                except:
                        pass

        def pulsed_Save_Button_Clicked(self,on):
                self.holder.save_pulsed_odmr_data(tag=self.pulsed_Filename)

        def pulsed_Run_Button_Clicked(self,on):
                self.pulsed_odmr_refocus_running=True
                self.holder.Contrast_Fit = ''
                self.holder.Frequencies_Fit = ''
                self.holder.Linewidth_Fit = ''
                self.setup_seq()
                self.data_detect=0
                self.data=0
                #self.holder.SigCheckReady_Beacon.connect(self.data_readout)
                self.time_differences.clear()
                self.time_differences.start()
                self.scanmatrix=np.zeros((self.pulsed_NumberOfLines,self.number_of_points_per_line))
                self.ancient_data=np.array(self.time_differences.getData(),dtype=object)
                self.starting_time=time.time()
                self.measurement_running=True

        def pulsed_RepumpDecay_LineEdit_textEdited(self,text):
                #print('done something with pulsed_RepumpDecay_LineEdit. Text=',text)
                try:
                        self.pulsed_RepumpDecay=float(text.replace(",","."))
                except:
                        pass

        def pulsed_RepumpDuration_LineEdit_textEdited(self,text):
                #print('done something with pulsed_RepumpDuration_LineEdit. Text=',text)
                try:
                        self.pulsed_RepumpDuration=float(text.replace(",","."))
                except:
                        pass

        def pulsed_A1Readout_checkBox_StateChanged(self,on):
                #print('done something with pulsed_A1Readout_checkBox')
                self.pulsed_A1Readout=on==2


        def pulsed_AOMDelay_LineEdit_textEdited(self,text):
                #print('done something with pulsed_AOMDelay_LineEdit. Text=',text)
                try:
                        self.pulsed_AOMDelay=float(text.replace(",","."))
                except:
                        pass

        def pulsed_InitTime_LineEdit_textEdited(self,text):
                #print('done something with pulsed_InitTime_LineEdit. Text=',text)
                try:
                        self.pulsed_InitTime=float(text.replace(",","."))
                except:
                        pass

        def pulsed_DecayInit_LineEdit_textEdited(self,text):
                #print('done something with pulsed_DecayInit_LineEdit. Text=',text)
                try:
                        self.pulsed_DecayInit=float(text.replace(",","."))
                except:
                        pass

        def pulsed_ReadoutTime_LineEdit_textEdited(self,text):
                #print('done something with pulsed_ReadoutTime_LineEdit. Text=',text)
                try:
                        self.pulsed_ReadoutTime=float(text.replace(",","."))
                except:
                        pass

        def pulsed_ReadoutDecay_LineEdit_textEdited(self,text):
                #print('done something with pulsed_ReadoutDecay_LineEdit. Text=',text)
                try:
                        self.pulsed_ReadoutDecay=float(text.replace(",","."))
                except:
                        pass

        def pulsed_PiDecay_lineEdit_textEdited(self,text):
                #print('done something with pulsed_PiDecay_lineEdit. Text=',text)
                try:
                        self.pulsed_PiDecay=float(text.replace(",","."))
                except:
                        pass

        def pulsed_piPulseDuration_lineEdit_textEdited(self,text):
                #print('done something with pulsed_piPulseDuration_lineEdit. Text=',text)
                try:
                        self.pulsed_piPulseDuration=float(text.replace(",","."))
                except:
                        pass

        def pulsed_Binning_LineEdit_textEdited(self,text):
                #print('done something with pulsed_Binning_LineEdit. Text=',text)
                try:
                        self.pulsed_Binning=float(text.replace(",","."))
                except:
                        pass

        def pulsed_SelectGaussianFit_RadioButton_clicked(self):
                self.holder.SelectGaussianFit=True
                self.holder.SelectLorentzianFit=False
                
        def pulsed_SelectLorentzianFit_RadioButton_clicked(self):
                self.holder.SelectGaussianFit=False
                self.holder.SelectLorentzianFit=True

        # F=False
        # T=True
        # pulsed_Filename=StatusVar("pulsed_Filename","filename")
        # pulsed_MW1=StatusVar("pulsed_MW1",T)
        # pulsed_MW2=StatusVar("pulsed_MW2",F)
        # pulsed_MW3=StatusVar("pulsed_MW3", F)

        # pulsed_MW1_Power=StatusVar("pulsed_MW1_Power",-20 )#dBm
        # pulsed_MW2_Power=StatusVar("pulsed_MW2_Power",-20 )#dBm
        # pulsed_MW3_Power=StatusVar("pulsed_MW3_Power",-20)
        
        # pulsed_StartFreq=StatusVar("pulsed_StartFreq",10) #MHz
        # pulsed_StopFreq=StatusVar("pulsed_StopFreq",50) #MHz
        # pulsed_Stepsize=StatusVar("pulsed_Stepsize",10) #MHz
        # pulsed_MW2_Freq=StatusVar("pulsed_MW2_Freq",140) #MHz
        # pulsed_MW3_Freq=StatusVar("pulsed_MW3_Freq", 100)
        
        # pulsed_A1=StatusVar("pulsed_A1",T)
        # pulsed_A2=StatusVar("pulsed_A2",F)
        # pulsed_A1Readout=StatusVar("pulsed_A1Readout",F)
        # pulsed_A2Readout=StatusVar("pulsed_A2Readout",T)
        # pulsed_PulsedRepump=StatusVar("pulsed_PulsedRepump",T)
        # pulsed_RepumpDuration=StatusVar("pulsed_RepumpDuration",3)
        # pulsed_RepumpDecay=StatusVar("pulsed_RepumpDecay",1) #µs
        # pulsed_CWRepump=StatusVar("pulsed_CWRepump",F) 
        
        # pulsed_PiDecay=StatusVar("pulsed_PiDecay", 1000) #ns
        # pulsed_piPulseDuration=StatusVar("pulsed_piPulseDuration", 68)
        
        # pulsed_Stoptime=StatusVar("pulsed_Stoptime",0)
        # pulsed_PeriodicSaving=StatusVar("pulsed_PeriodicSaving",F)
        # pulsed_Interval=StatusVar("pulsed_Interval",0) 
        
        # pulsed_AOMDelay=StatusVar("pulsed_AOMDelay",450) #µs
        # pulsed_InitTime=StatusVar("pulsed_InitTime", 10) #µs
        # pulsed_DecayInit=StatusVar("pulsed_DecayInit", 500) #µs
        # pulsed_ReadoutTime=StatusVar("pulsed_ReadoutTime", 3) #µs
        # pulsed_ReadoutDecay=StatusVar("pulsed_ReadoutDecay", 1) #µs
        
        # pulsed_PerformFit=StatusVar("pulsed_PerformFit",F)
        # pulsed_SelectLorentzianFit=StatusVar("pulsed_SelectLorentzianFit",T)
        # pulsed_SelectGaussianFit=StatusVar("pulsed_SelectGaussianFit",F)
        
        # pulsed_SecondsPerPoint=StatusVar("pulsed_SecondsPerPoint", 0.02)
        
        # pulsed_Runtime=StatusVar("pulsed_Runtime",0)
        # pulsed_Binning=StatusVar("pulsed_Binning", 100)
        
        # pulsed_odmr_cb_max=StatusVar("pulsed_odmr_cb_max",100)
        # pulsed_odmr_cb_high_percentile=StatusVar("pulsed_odmr_cb_high_percentile",100)
        # pulsed_odmr_cb_low_percentile=StatusVar("pulsed_odmr_cb_low_percentile",0)
        # pulsed_odmr_cb_min=StatusVar("pulsed_odmr_cb_min", 0)
        
        # pulsed_NumberOfLines=StatusVar("pulsed_NumberOfLines",20)
        # pulsed_update_after_stop=StatusVar("pulsed_update_after_stop",F)