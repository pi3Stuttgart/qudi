// *****************************************************************************
// * wlmData.h                                                                 *
// *   (header file for wlmData.dll)                                           *
// *                                                                2021-04-23 *
// *****************************************************************************

#ifndef WLMDATA_H_
	// Avoid reentrance
	#define WLMDATA_H_

	// WLMDATA_EXPORTS must not be defined for any project using this dll.
	#ifdef WLMDATA_EXPORTS 
		#define DLL_IM_EXPORT dllexport 
	#else
		#define DLL_IM_EXPORT dllimport 
	#endif

	#ifdef __cplusplus
		#define NOT_MANGLED extern "C"
		typedef long &      lref;
		typedef __int64 &   l64ref;
		typedef double &    dref;
		typedef char &      sref;
	#else
		#define NOT_MANGLED
		typedef long *      lref;
		typedef __int64 *   l64ref;
		typedef double *    dref;
		typedef char *      sref;
	#endif

	#define Data_API(ret) NOT_MANGLED __declspec(DLL_IM_EXPORT) ret __stdcall

	#ifndef DWORD 
		typedef unsigned long   DWORD;
	#endif

	#ifndef LONG_PTR 
		#ifdef _WIN64
			typedef __int64 LONG_PTR;
			typedef unsigned __int64 ULONG_PTR;
			#define __int3264   __int64
		#else
		    typedef long LONG_PTR;
			typedef unsigned long ULONG_PTR;
			#define __int3264   __int32
		#endif
	#endif

	#ifndef __cplusplus
		#ifndef bool
			typedef unsigned char bool;
			#ifndef true 
				#define true  1
			#endif
			#ifndef false 
				#define false 0
			#endif
		#endif
	#endif


// ***********  Functions for general usage  ****************************
	Data_API(LONG_PTR)       Instantiate(long RFC, long Mode, LONG_PTR P1, long P2) ;

//	void __stdcall           CallbackProc(long Mode, long IntVal, double DblVal) ;
//	void __stdcall           CallbackProcEx(long Ver, long Mode, long IntVal, double DblVal, long Res1) ;
	Data_API(long)           WaitForWLMEvent(lref Mode, lref IntVal, dref DblVal) ;
	Data_API(long)           WaitForWLMEventEx(lref Ver, lref Mode, lref IntVal, dref DblVal, lref Res1) ;
	Data_API(long)           WaitForNextWLMEvent(lref Mode, lref IntVal, dref DblVal) ;
	Data_API(long)           WaitForNextWLMEventEx(lref Ver, lref Mode, lref IntVal, dref DblVal, lref Res1) ;
	Data_API(void)           ClearWLMEvents(void) ;

	Data_API(long)           ControlWLM(long Action, LONG_PTR App, long Ver) ;
	Data_API(long)           ControlWLMEx(long Action, LONG_PTR App, long Ver, long Delay, long Res) ;
	Data_API(__int64)        SynchroniseWLM(long Mode, __int64 TS) ;
	Data_API(long)           SetMeasurementDelayMethod(long Mode, long Delay) ;
	Data_API(long)           SetWLMPriority(long PPC, long Res1, long Res2) ;
	Data_API(long)           PresetWLMIndex(long Ver) ;

	Data_API(long)           GetWLMVersion(long Ver) ;
	Data_API(long)           GetWLMIndex(long Ver) ;
	Data_API(long)           GetWLMCount(long V) ;


// ***********  General Get... & Set...-functions  **********************
	Data_API(double)         GetWavelength(double WL) ;
	Data_API(double)         GetWavelength2(double WL2) ;
	Data_API(double)         GetWavelengthNum(long num, double WL) ;
	Data_API(double)         GetCalWavelength(long ba, double WL) ;
	Data_API(double)         GetCalibrationEffect(double CE) ;
	Data_API(double)         GetFrequency(double F) ;
	Data_API(double)         GetFrequency2(double F2) ;
	Data_API(double)         GetFrequencyNum(long num, double F) ;
	Data_API(double)         GetLinewidth(long Index, double LW) ;
	Data_API(double)         GetLinewidthNum(long num, double LW) ;
	Data_API(double)         GetDistance(double D) ;
	Data_API(double)         GetAnalogIn(double AI) ;
	Data_API(double)         GetMultimodeInfo(long num, long type, long mode, dref Val) ;
	Data_API(double)         GetTemperature(double T) ;
	Data_API(long)           SetTemperature(double T) ;
	Data_API(double)         GetPressure(double P) ;
	Data_API(long)           SetPressure(long Mode, double P) ;
	Data_API(long)           GetAirParameters(long Mode, lref State, dref Val) ;
	Data_API(long)           SetAirParameters(long Mode, long State, double Val) ;
	Data_API(double)         GetExternalInput(long Index, double I) ;
	Data_API(long)           SetExternalInput(long Index, double I) ;
	Data_API(long)           GetExtraSetting(long Index, lref lGet, dref dGet, sref sGet) ;
	Data_API(long)           SetExtraSetting(long Index, long lSet, double dSet, sref sSet) ;

	Data_API(unsigned short) GetExposure(unsigned short E) ;
	Data_API(long)           SetExposure(unsigned short E) ;
	Data_API(unsigned short) GetExposure2(unsigned short E2) ;
	Data_API(long)           SetExposure2(unsigned short E2) ;
	Data_API(long)           GetExposureNum(long num, long arr, long E) ;
	Data_API(long)           SetExposureNum(long num, long arr, long E) ;
	Data_API(double)         GetExposureNumEx(long num, long arr, double E) ;
	Data_API(long)           SetExposureNumEx(long num, long arr, double E) ;
	Data_API(bool)           GetExposureMode(bool EM) ;
	Data_API(long)           SetExposureMode(bool EM) ;
	Data_API(long)           GetExposureModeNum(long num, bool EM) ;
	Data_API(long)           SetExposureModeNum(long num, bool EM) ;
	Data_API(long)           GetExposureRange(long ER) ;
	Data_API(double)         GetExposureRangeEx(long ER) ;
	Data_API(long)           GetAutoExposureSetting(long num, long AES, lref iVal, dref dVal) ;
	Data_API(long)           SetAutoExposureSetting(long num, long AES, long iVal, double dVal) ;

	Data_API(unsigned short) GetResultMode(unsigned short RM) ;
	Data_API(long)           SetResultMode(unsigned short RM) ;
	Data_API(unsigned short) GetRange(unsigned short R) ;
	Data_API(long)           SetRange(unsigned short R) ;
	Data_API(unsigned short) GetPulseMode(unsigned short PM) ;
	Data_API(long)           SetPulseMode(unsigned short PM) ;
	Data_API(long)           GetPulseDelay(long PD) ;
	Data_API(long)           SetPulseDelay(long PD) ;
	Data_API(long)           GetPulseIntegration(long PI) ;
	Data_API(long)           SetPulseIntegration(long PI) ;
	Data_API(unsigned short) GetWideMode(unsigned short WM) ;
	Data_API(long)           SetWideMode(unsigned short WM) ;

	Data_API(long)           GetDisplayMode(long DM) ;
	Data_API(long)           SetDisplayMode(long DM) ;
	Data_API(bool)           GetFastMode(bool FM) ;
	Data_API(long)           SetFastMode(bool FM) ;

	Data_API(bool)           GetLinewidthMode(bool LM) ;
	Data_API(long)           SetLinewidthMode(bool LM) ;

	Data_API(bool)           GetDistanceMode(bool DM) ;
	Data_API(long)           SetDistanceMode(bool DM) ;

	Data_API(long)           GetSwitcherMode(long SM) ;
	Data_API(long)           SetSwitcherMode(long SM) ;
	Data_API(long)           GetSwitcherChannel(long CH) ;
	Data_API(long)           SetSwitcherChannel(long CH) ;
	Data_API(long)           GetSwitcherSignalStates(long Signal, lref Use, lref Show) ;
	Data_API(long)           SetSwitcherSignalStates(long Signal, long Use, long Show) ;
	Data_API(long)           SetSwitcherSignal(long Signal, long Use, long Show) ;

	Data_API(long)           GetAutoCalMode(long ACM) ;
	Data_API(long)           SetAutoCalMode(long ACM) ;
	Data_API(long)           GetAutoCalSetting(long ACS, lref val, long Res1, lref Res2) ;
	Data_API(long)           SetAutoCalSetting(long ACS, long val, long Res1, long Res2) ;

	Data_API(long)           GetActiveChannel(long Mode, lref Port, long Res1) ;
	Data_API(long)           SetActiveChannel(long Mode, long Port, long CH, long Res1) ;
	Data_API(long)           GetChannelsCount(long C) ;

	Data_API(unsigned short) GetOperationState(unsigned short OS) ;
	Data_API(long)           Operation(unsigned short Op) ;
	Data_API(long)           SetOperationFile(sref lpFile) ;
	Data_API(long)           Calibration(long Type, long Unit, double Value, long Channel) ;
	Data_API(long)           PowerCalibration(long Unit, double Value, long Channel, long Options, long Res) ;
	Data_API(long)           RaiseMeasurementEvent(long Mode) ;
	Data_API(long)           TriggerMeasurement(long Action) ;
	Data_API(long)           GetTriggerState(long TS) ;
	Data_API(long)           GetInterval(long I) ;
	Data_API(long)           SetInterval(long I) ;
	Data_API(bool)           GetIntervalMode(bool IM) ;
	Data_API(long)           SetIntervalMode(bool IM) ;
	Data_API(double)         GetInternalTriggerRate(double TR) ;
	Data_API(long)           SetInternalTriggerRate(double TR) ;
	Data_API(long)           GetBackground(long BG) ;
	Data_API(long)           SetBackground(long BG) ;
	Data_API(long)           GetAveragingSettingNum(long num, long AS, long Value) ;
	Data_API(long)           SetAveragingSettingNum(long num, long AS, long Value) ;

	Data_API(bool)           GetLinkState(bool LS) ;
	Data_API(long)           SetLinkState(bool LS) ;
	Data_API(void)           LinkSettingsDlg(void) ;

	Data_API(long)           GetPatternItemSize(long Index) ;
	Data_API(long)           GetPatternItemCount(long Index) ;
	Data_API(ULONG_PTR)      GetPattern(long Index) ;
	Data_API(ULONG_PTR)      GetPatternNum(long Chn, long Index) ;
	Data_API(long)           GetPatternData(long Index, ULONG_PTR PArray) ;
	Data_API(long)           GetPatternDataNum(long Chn, long Index, ULONG_PTR PArray) ;
	Data_API(long)           SetPattern(long Index, long iEnable) ;
	Data_API(long)           SetPatternData(long Index, ULONG_PTR PArray) ;

	Data_API(bool)           GetAnalysisMode(bool AM) ;
	Data_API(long)           SetAnalysisMode(bool AM) ;
	Data_API(long)           GetAnalysisItemSize(long Index) ;
	Data_API(long)           GetAnalysisItemCount(long Index) ;
	Data_API(ULONG_PTR)      GetAnalysis(long Index) ;
	Data_API(long)           GetAnalysisData(long Index, ULONG_PTR PArray) ;
	Data_API(long)           SetAnalysis(long Index, long iEnable) ;

	Data_API(long)           GetMinPeak(long M1) ;
	Data_API(long)           GetMinPeak2(long M2) ;
	Data_API(long)           GetMaxPeak(long X1) ;
	Data_API(long)           GetMaxPeak2(long X2) ;
	Data_API(long)           GetAvgPeak(long A1) ;
	Data_API(long)           GetAvgPeak2(long A2) ;
	Data_API(long)           SetAvgPeak(long PA) ;

	Data_API(long)           GetAmplitudeNum(long num, long Index, long A) ;
	Data_API(double)         GetIntensityNum(long num, double I) ;
	Data_API(double)         GetPowerNum(long num, double P) ;

	Data_API(unsigned short) GetDelay(unsigned short D) ;
	Data_API(long)           SetDelay(unsigned short D) ;
	Data_API(unsigned short) GetShift(unsigned short S) ;
	Data_API(long)           SetShift(unsigned short S) ;
	Data_API(unsigned short) GetShift2(unsigned short S2) ;
	Data_API(long)           SetShift2(unsigned short S2) ;
	Data_API(double)         GetGain(long num, long index, long mode, dref Gain) ;
	Data_API(long)           SetGain(long num, long index, long mode, double Gain) ;


// ***********  Deviation (Laser Control) and PID-functions  ************
	Data_API(bool)           GetDeviationMode(bool DM) ;
	Data_API(long)           SetDeviationMode(bool DM) ;
	Data_API(double)         GetDeviationReference(double DR) ;
	Data_API(long)           SetDeviationReference(double DR) ;
	Data_API(long)           GetDeviationSensitivity(long DS) ;
	Data_API(long)           SetDeviationSensitivity(long DS) ;
	Data_API(double)         GetDeviationSignal(double DS) ;
	Data_API(double)         GetDeviationSignalNum(long Port, double DS) ;
	Data_API(long)           SetDeviationSignal(double DS) ;
	Data_API(long)           SetDeviationSignalNum(long Port, double DS) ;
	Data_API(double)         RaiseDeviationSignal(long iType, double dSignal) ;

	Data_API(long)           GetPIDCourse(sref PIDC) ;
	Data_API(long)           SetPIDCourse(sref PIDC) ;
	Data_API(long)           GetPIDCourseNum(long Port, sref PIDC) ;
	Data_API(long)           SetPIDCourseNum(long Port, sref PIDC) ;
	Data_API(long)           GetPIDSetting(long PS, long Port, lref iSet, dref dSet) ;
	Data_API(long)           SetPIDSetting(long PS, long Port, long iSet, double dSet) ;
	Data_API(long)           GetLaserControlSetting(long PS, long Port, lref iSet, dref dSet, sref sSet) ;
	Data_API(long)           SetLaserControlSetting(long PS, long Port, long iSet, double dSet, sref sSet) ;
	Data_API(long)           ClearPIDHistory(long Port) ;


// ***********  Other...-functions  *************************************
	Data_API(double)         ConvertUnit(double Val, long uFrom, long uTo) ;
	Data_API(double)         ConvertDeltaUnit(double Base, double Delta, long uBase, long uFrom, long uTo) ;


// ***********  Obsolete...-functions  **********************************
	Data_API(bool)           GetReduced(bool R) ;
	Data_API(long)           SetReduced(bool R) ;
	Data_API(unsigned short) GetScale(unsigned short S) ;
	Data_API(long)           SetScale(unsigned short S) ;


// ***********  Constants  **********************************************

// Instantiating Constants for 'RFC' parameter
	const int	cInstCheckForWLM = -1;
	const int	cInstResetCalc = 0;
	const int	cInstReturnMode = cInstResetCalc;
	const int	cInstNotification = 1;
	const int	cInstCopyPattern = 2;
	const int	cInstCopyAnalysis = cInstCopyPattern;
	const int	cInstControlWLM = 3;
	const int	cInstControlDelay = 4;
	const int	cInstControlPriority = 5;

// Notification Constants for 'Mode' parameter
	const int	cNotifyInstallCallback = 0;
	const int	cNotifyRemoveCallback = 1;
	const int	cNotifyInstallWaitEvent = 2;
	const int	cNotifyRemoveWaitEvent = 3;
	const int	cNotifyInstallCallbackEx = 4;
	const int	cNotifyInstallWaitEventEx = 5;

// ResultError Constants of Set...-functions
	const int	ResERR_NoErr = 0;
	const int	ResERR_WlmMissing = -1;
	const int	ResERR_CouldNotSet = -2;
	const int	ResERR_ParmOutOfRange = -3;
	const int	ResERR_WlmOutOfResources = -4;
	const int	ResERR_WlmInternalError = -5;
	const int	ResERR_NotAvailable = -6;
	const int	ResERR_WlmBusy = -7;
	const int	ResERR_NotInMeasurementMode = -8;
	const int	ResERR_OnlyInMeasurementMode = -9;
	const int	ResERR_ChannelNotAvailable = -10;
	const int	ResERR_ChannelTemporarilyNotAvailable = -11;
	const int	ResERR_CalOptionNotAvailable = -12;
	const int	ResERR_CalWavelengthOutOfRange = -13;
	const int	ResERR_BadCalibrationSignal = -14;
	const int	ResERR_UnitNotAvailable = -15;
	const int	ResERR_FileNotFound = -16;
	const int	ResERR_FileCreation = -17;
	const int	ResERR_TriggerPending = -18;
	const int	ResERR_TriggerWaiting = -19;
	const int	ResERR_NoLegitimation = -20;
	const int	ResERR_NoTCPLegitimation = -21;
	const int	ResERR_NotInPulseMode = -22;
	const int	ResERR_OnlyInPulseMode = -23;
	const int	ResERR_NotInSwitchMode = -24;
	const int	ResERR_OnlyInSwitchMode = -25;
	const int	ResERR_TCPErr = -26;
	const int	ResERR_StringTooLong = -29;
	const int	ResERR_InterruptedByUser = -30;

// Mode Constants for Callback-Export and WaitForWLMEvent-function
	const int	cmiResultMode = 1;
	const int	cmiRange = 2;
	const int	cmiPulse = 3;
	const int	cmiPulseMode = cmiPulse;
	const int	cmiWideLine = 4;
	const int	cmiWideMode = cmiWideLine;
	const int	cmiFast = 5;
	const int	cmiFastMode = cmiFast;
	const int	cmiExposureMode = 6;
	const int	cmiExposureValue1 = 7;
	const int	cmiExposureValue2 = 8;
	const int	cmiDelay = 9;
	const int	cmiShift = 10;
	const int	cmiShift2 = 11;
	const int	cmiReduce = 12;
	const int	cmiReduced = cmiReduce;
	const int	cmiScale = 13;
	const int	cmiTemperature = 14;
	const int	cmiLink = 15;
	const int	cmiOperation = 16;
	const int	cmiDisplayMode = 17;
	const int	cmiPattern1a = 18;
	const int	cmiPattern1b = 19;
	const int	cmiPattern2a = 20;
	const int	cmiPattern2b = 21;
	const int	cmiMin1 = 22;
	const int	cmiMax1 = 23;
	const int	cmiMin2 = 24;
	const int	cmiMax2 = 25;
	const int	cmiNowTick = 26;
	const int	cmiCallback = 27;
	const int	cmiFrequency1 = 28;
	const int	cmiFrequency2 = 29;
	const int	cmiDLLDetach = 30;
	const int	cmiVersion = 31;
	const int	cmiAnalysisMode = 32;
	const int	cmiDeviationMode = 33;
	const int	cmiDeviationReference = 34;
	const int	cmiDeviationSensitivity = 35;
	const int	cmiAppearance = 36;
	const int	cmiAutoCalMode = 37;
	const int	cmiWavelength1 = 42;
	const int	cmiWavelength2 = 43;
	const int	cmiLinewidth = 44;
	const int	cmiLinewidthMode = 45;
	const int	cmiLinkDlg = 56;
	const int	cmiAnalysis = 57;
	const int	cmiAnalogIn = 66;
	const int	cmiAnalogOut = 67;
	const int	cmiDistance = 69;
	const int	cmiWavelength3 = 90;
	const int	cmiWavelength4 = 91;
	const int	cmiWavelength5 = 92;
	const int	cmiWavelength6 = 93;
	const int	cmiWavelength7 = 94;
	const int	cmiWavelength8 = 95;
	const int	cmiVersion0 = cmiVersion;
	const int	cmiVersion1 = 96;
	const int	cmiPulseDelay = 99;
	const int   cmiPulseIntegration = cmiPulseDelay;
	const int	cmiDLLAttach = 121;
	const int	cmiSwitcherSignal = 123;
	const int	cmiSwitcherMode = 124;
	const int	cmiExposureValue11 = cmiExposureValue1;
	const int	cmiExposureValue12 = 125;
	const int	cmiExposureValue13 = 126;
	const int	cmiExposureValue14 = 127;
	const int	cmiExposureValue15 = 128;
	const int	cmiExposureValue16 = 129;
	const int	cmiExposureValue17 = 130;
	const int	cmiExposureValue18 = 131;
	const int	cmiExposureValue21 = cmiExposureValue2;
	const int	cmiExposureValue22 = 132;
	const int	cmiExposureValue23 = 133;
	const int	cmiExposureValue24 = 134;
	const int	cmiExposureValue25 = 135;
	const int	cmiExposureValue26 = 136;
	const int	cmiExposureValue27 = 137;
	const int	cmiExposureValue28 = 138;
	const int	cmiPatternAverage = 139;
	const int	cmiPatternAvg1 = 140;
	const int	cmiPatternAvg2 = 141;
	const int	cmiAnalogOut1 = cmiAnalogOut;
	const int	cmiAnalogOut2 = 142;
	const int	cmiMin11 = cmiMin1;
	const int	cmiMin12 = 146;
	const int	cmiMin13 = 147;
	const int	cmiMin14 = 148;
	const int	cmiMin15 = 149;
	const int	cmiMin16 = 150;
	const int	cmiMin17 = 151;
	const int	cmiMin18 = 152;
	const int	cmiMin21 = cmiMin2;
	const int	cmiMin22 = 153;
	const int	cmiMin23 = 154;
	const int	cmiMin24 = 155;
	const int	cmiMin25 = 156;
	const int	cmiMin26 = 157;
	const int	cmiMin27 = 158;
	const int	cmiMin28 = 159;
	const int	cmiMax11 = cmiMax1;
	const int	cmiMax12 = 160;
	const int	cmiMax13 = 161;
	const int	cmiMax14 = 162;
	const int	cmiMax15 = 163;
	const int	cmiMax16 = 164;
	const int	cmiMax17 = 165;
	const int	cmiMax18 = 166;
	const int	cmiMax21 = cmiMax2;
	const int	cmiMax22 = 167;
	const int	cmiMax23 = 168;
	const int	cmiMax24 = 169;
	const int	cmiMax25 = 170;
	const int	cmiMax26 = 171;
	const int	cmiMax27 = 172;
	const int	cmiMax28 = 173;
	const int	cmiAvg11 = cmiPatternAvg1;
	const int	cmiAvg12 = 174;
	const int	cmiAvg13 = 175;
	const int	cmiAvg14 = 176;
	const int	cmiAvg15 = 177;
	const int	cmiAvg16 = 178;
	const int	cmiAvg17 = 179;
	const int	cmiAvg18 = 180;
	const int	cmiAvg21 = cmiPatternAvg2;
	const int	cmiAvg22 = 181;
	const int	cmiAvg23 = 182;
	const int	cmiAvg24 = 183;
	const int	cmiAvg25 = 184;
	const int	cmiAvg26 = 185;
	const int	cmiAvg27 = 186;
	const int	cmiAvg28 = 187;
	const int	cmiPatternAnalysisWritten = 202;
	const int	cmiSwitcherChannel = 203;
	const int	cmiStartCalibration = 235;
	const int	cmiEndCalibration = 236;
	const int	cmiAnalogOut3 = 237;
	const int	cmiAnalogOut4 = 238;
	const int	cmiAnalogOut5 = 239;
	const int	cmiAnalogOut6 = 240;
	const int	cmiAnalogOut7 = 241;
	const int	cmiAnalogOut8 = 242;
	const int	cmiIntensity = 251;
	const int	cmiPower = 267;
	const int	cmiActiveChannel = 300;
	const int	cmiPIDCourse = 1030;
	const int	cmiPIDUseTa = 1031;
	const int	cmiPIDUseT = cmiPIDUseTa;
	const int	cmiPID_T = 1033;
	const int	cmiPID_P = 1034;
	const int	cmiPID_I = 1035;
	const int	cmiPID_D = 1036;
	const int	cmiDeviationSensitivityDim = 1040;
	const int	cmiDeviationSensitivityFactor = 1037;
	const int	cmiDeviationPolarity = 1038;
	const int	cmiDeviationSensitivityEx = 1039;
	const int	cmiDeviationUnit = 1041;
	const int	cmiDeviationBoundsMin = 1042;
	const int	cmiDeviationBoundsMax = 1043;
	const int	cmiDeviationRefMid = 1044;
	const int	cmiDeviationRefAt = 1045;
	const int	cmiPIDConstdt = 1059;
	const int	cmiPID_dt = 1060;
	const int	cmiPID_AutoClearHistory = 1061;
	const int	cmiDeviationChannel = 1063;
	const int	cmiPID_ClearHistoryOnRangeExceed = 1069;
	const int	cmiAutoCalPeriod = 1120;
	const int	cmiAutoCalUnit = 1121;
	const int	cmiAutoCalChannel = 1122;
	const int	cmiServerInitialized = 1124;
	const int	cmiWavelength9 = 1130;
	const int	cmiExposureValue19 = 1155;
	const int	cmiExposureValue29 = 1180;
	const int	cmiMin19 = 1205;
	const int	cmiMin29 = 1230;
	const int	cmiMax19 = 1255;
	const int	cmiMax29 = 1280;
	const int	cmiAvg19 = 1305;
	const int	cmiAvg29 = 1330;
	const int	cmiWavelength10 = 1355;
	const int	cmiWavelength11 = 1356;
	const int	cmiWavelength12 = 1357;
	const int	cmiWavelength13 = 1358;
	const int	cmiWavelength14 = 1359;
	const int	cmiWavelength15 = 1360;
	const int	cmiWavelength16 = 1361;
	const int	cmiWavelength17 = 1362;
	const int	cmiExternalInput = 1400;
	const int	cmiPressure = 1465;
	const int	cmiBackground = 1475;
	const int	cmiDistanceMode = 1476;
	const int	cmiInterval = 1477;
	const int	cmiIntervalMode = 1478;
	const int	cmiCalibrationEffect = 1480;
	const int	cmiLinewidth1 = cmiLinewidth;
	const int	cmiLinewidth2 = 1481;
	const int	cmiLinewidth3 = 1482;
	const int	cmiLinewidth4 = 1483;
	const int	cmiLinewidth5 = 1484;
	const int	cmiLinewidth6 = 1485;
	const int	cmiLinewidth7 = 1486;
	const int	cmiLinewidth8 = 1487;
	const int	cmiLinewidth9 = 1488;
	const int	cmiLinewidth10 = 1489;
	const int	cmiLinewidth11 = 1490;
	const int	cmiLinewidth12 = 1491;
	const int	cmiLinewidth13 = 1492;
	const int	cmiLinewidth14 = 1493;
	const int	cmiLinewidth15 = 1494;
	const int	cmiLinewidth16 = 1495;
	const int	cmiLinewidth17 = 1496;
	const int	cmiTriggerState = 1497;
	const int	cmiDeviceAttach = 1501;
	const int	cmiDeviceDetach = 1502;
	const int	cmiTimePerMeasurement = 1514;
	const int	cmiAutoExpoMin = 1517;
	const int	cmiAutoExpoMax = 1518;
	const int	cmiAutoExpoStepUp = 1519;
	const int	cmiAutoExpoStepDown = 1520;
	const int	cmiAutoExpoAtSaturation = 1521;
	const int	cmiAutoExpoAtLowSignal = 1522;
	const int	cmiAutoExpoFeedback = 1523;
	const int	cmiAveragingCount = 1524;
	const int	cmiAveragingMode = 1525;
	const int	cmiAveragingType = 1526;
	const int	cmiAirMode = 1532;
	const int	cmiAirTemperature = 1534;
	const int	cmiAirPressure = 1535;
	const int	cmiAirHumidity = 1536;
	const int	cmiAirCO2 = 1651;
	const int	cmiSubSnapshotID = 1539;
	const int	cmiInternalTriggerRate = 1540;
	const int	cmiGain11 = 1541;
	const int	cmiGain12 = 1542;
	const int	cmiGain13 = 1543;
	const int	cmiGain14 = 1544;
	const int	cmiGain15 = 1545;
	const int	cmiGain16 = 1546;
	const int	cmiGain17 = 1547;
	const int	cmiGain18 = 1548;
	const int	cmiGain19 = 1549;
	const int	cmiGain21 = 1558;
	const int	cmiGain22 = 1559;
	const int	cmiGain23 = 1560;
	const int	cmiGain24 = 1561;
	const int	cmiGain25 = 1562;
	const int	cmiGain26 = 1563;
	const int	cmiGain27 = 1564;
	const int	cmiGain28 = 1565;
	const int	cmiGain29 = 1566;
	const int	cmiMultimodeLevel1 = 1609;
	const int	cmiMultimodeLevel2 = 1610;
	const int	cmiMultimodeLevel3 = 1611;
	const int	cmiMultimodeLevel4 = 1612;
	const int	cmiMultimodeLevel5 = 1613;
	const int	cmiMultimodeLevel6 = 1614;
	const int	cmiMultimodeLevel7 = 1615;
	const int	cmiMultimodeLevel8 = 1616;
	const int	cmiMultimodeLevel9 = 1617;
	const int	cmiFastBasedLinewidthAnalysis = 1630;
	const int	cmiMultimodeCount1 = 1633;
	const int	cmiMultimodeCount2 = 1634;
	const int	cmiMultimodeCount3 = 1635;
	const int	cmiMultimodeCount4 = 1636;
	const int	cmiMultimodeCount5 = 1637;
	const int	cmiMultimodeCount6 = 1638;
	const int	cmiMultimodeCount7 = 1639;
	const int	cmiMultimodeCount8 = 1640;
	const int	cmiMultimodeCount9 = 1641;
	const int	cmiPowerCalibration = 1652;
	const int	cmiStartPowerCalibration = 1653;
	const int	cmiEndPowerCalibration = 1654;

// Index constants for Get- and SetExtraSetting
	const int	cesCalculateLive = 4501;

// WLM Control Mode Constants
	const int	cCtrlWLMShow = 1;
	const int	cCtrlWLMHide = 2;
	const int	cCtrlWLMExit = 3;
	const int	cCtrlWLMStore = 4;
	const int	cCtrlWLMCompare = 5;
	const int	cCtrlWLMWait        = 0x0010;
	const int	cCtrlWLMStartSilent = 0x0020;
	const int	cCtrlWLMSilent      = 0x0040;
	const int	cCtrlWLMStartDelay  = 0x0080;

// Operation Mode Constants (for "Operation" and "GetOperationState" functions)
	const int	cStop = 0;
	const int	cAdjustment = 1;
	const int	cMeasurement = 2;

// Base Operation Constants (To be used exclusively, only one of this list at a time,
// but still can be combined with "Measurement Action Addition Constants". See below.)
	const int	cCtrlStopAll = cStop;
	const int	cCtrlStartAdjustment = cAdjustment;
	const int	cCtrlStartMeasurement = cMeasurement;
	const int	cCtrlStartRecord = 0x0004;
	const int	cCtrlStartReplay = 0x0008;
	const int	cCtrlStoreArray  = 0x0010;
	const int	cCtrlLoadArray   = 0x0020;

// Additional Operation Flag Constants (combine with "Base Operation Constants" above.)
	const int	cCtrlDontOverwrite = 0x0000;
	const int	cCtrlOverwrite     = 0x1000; // don't combine with cCtrlFileDialog
	const int	cCtrlFileGiven     = 0x0000;
	const int	cCtrlFileDialog    = 0x2000; // don't combine with cCtrlOverwrite and cCtrlFileASCII
	const int	cCtrlFileBinary    = 0x0000; // *.smr, *.ltr
	const int	cCtrlFileASCII     = 0x4000; // *.smx, *.ltx, don't combine with cCtrlFileDialog

// Measurement Control Mode Constants
	const int	cCtrlMeasDelayRemove = 0;
	const int	cCtrlMeasDelayGenerally = 1;
	const int	cCtrlMeasDelayOnce = 2;
	const int	cCtrlMeasDelayDenyUntil = 3;
	const int	cCtrlMeasDelayIdleOnce = 4;
	const int	cCtrlMeasDelayIdleEach = 5;
	const int	cCtrlMeasDelayDefault = 6;

// Measurement Triggering Action Constants
	const int	cCtrlMeasurementContinue = 0;
	const int	cCtrlMeasurementInterrupt = 1;
	const int	cCtrlMeasurementTriggerPoll = 2;
	const int	cCtrlMeasurementTriggerSuccess = 3;
	const int	cCtrlMeasurementEx = 0x0100;

// ExposureRange Constants
	const int	cExpoMin = 0;
	const int	cExpoMax = 1;
	const int	cExpo2Min = 2;
	const int	cExpo2Max = 3;

// Amplitude Constants
	const int	cMin1 = 0;
	const int	cMin2 = 1;
	const int	cMax1 = 2;
	const int	cMax2 = 3;
	const int	cAvg1 = 4;
	const int	cAvg2 = 5;

// Measurement Range Constants
	const int	cRange_250_410 = 4;
	const int	cRange_250_425 = 0;
	const int	cRange_300_410 = 3;
	const int	cRange_350_500 = 5;
	const int	cRange_400_725 = 1;
	const int	cRange_700_1100 = 2;
	const int	cRange_800_1300 = 6;
	const int	cRange_900_1500 = cRange_800_1300;
	const int	cRange_1100_1700 = 7;
	const int	cRange_1100_1800 = cRange_1100_1700;

// Measurement Range Model Constants
	const int	cRangeModelOld = 65535;
	const int	cRangeModelByOrder = 65534;
	const int	cRangeModelByWavelength = 65533;

// Unit Constants for Get-/SetResultMode, GetLinewidth, Convert... and Calibration
	const int	cReturnWavelengthVac = 0;
	const int	cReturnWavelengthAir = 1;
	const int	cReturnFrequency = 2;
	const int	cReturnWavenumber = 3;
	const int	cReturnPhotonEnergy = 4;

// Power Unit Constants
	const int	cPower_muW = 0;
	const int	cPower_mW  = 1;
	const int	cPower_dBm = 2;

// Source Type Constants for Calibration
	const int	cHeNe633 = 0;
	const int	cHeNe1152 = 0;
	const int	cNeL = 1;
	const int	cOther = 2;
	const int	cFreeHeNe = 3;
	const int	cSLR1530 = 5;

// Unit Constants for Autocalibration
	const int	cACOnceOnStart = 0;
	const int	cACMeasurements = 1;
	const int	cACDays = 2;
	const int	cACHours = 3;
	const int	cACMinutes = 4;

// Options flags for PowerCalibration
	const int	cIntSensor1     = 0x00000000;
	const int	cIntSensor2     = 0x00000001;
	const int	cTryWOStoreDark = 0x00000010;
	
// ExposureRange Constants
	const int	cGetSync = 1;
	const int	cSetSync = 2;

// Pattern- and Analysis Constants
	const int	cPatternDisable = 0;
	const int	cPatternEnable = 1;
	const int	cAnalysisDisable = cPatternDisable;
	const int	cAnalysisEnable = cPatternEnable;

	const int	cSignal1Interferometers = 0;
	const int	cSignal1WideInterferometer = 1;
	const int	cSignal1Grating = 1;
	const int	cSignal2Interferometers = 2;
	const int	cSignal2WideInterferometer = 3;
	const int	cSignalAnalysis = 4;
	const int	cSignalAnalysisX = cSignalAnalysis;
	const int	cSignalAnalysisY = cSignalAnalysis + 1;

// State constants used with AutoExposureSetting functions
	const int	cJustStepDown = 0;
	const int	cRestartAtMinimum = 1;
	const int	cJustStepUp = 0;
	const int	cDriveToLevel = 1;
	const int	cConsiderFeedback = 1;
	const int	cDontConsiderFeedback = 0;

// Options identifiers used with GetOptionInfo
	const int	cInfoSwitch = 1;
	const int	cInfoSwitchChannelsCount = 2;
	const int	cInfoIntNeonLamp = 11;
	const int	cInfo2ndExternalPort = 13;
	const int	cInfoPID = 21;
	const int	cInfoPIDPortsCount = 22;
	const int	cInfoPIDPortType = 23;
	const int	cInfoPIDPortRes = 24;
	const int	cInfoPIDPortUMin = 25;
	const int	cInfoPIDPortUMax = 26;

// PID type constants
	const int	cInfoPIDPortTypeInt = 1;
	const int	cInfoPIDPortTypeExt = 2;
	const int	cInfoPIDPortTypeDigi = 3;

// State constants used with AveragingSetting functions
	const int	cAvrgFloating = 1;
	const int	cAvrgSucceeding = 2;
	const int	cAvrgSimple = 0;
	const int	cAvrgPattern = 1;

// Return errorvalues of GetFrequency, GetWavelength, GetWLMVersion and GetOptionInfo
	const int	ErrNoValue = 0;
	const int	ErrNoSignal = -1;
	const int	ErrBadSignal = -2;
	const int	ErrLowSignal = -3;
	const int	ErrBigSignal = -4;
	const int	ErrWlmMissing = -5;
	const int	ErrNotAvailable = -6;
	const int	InfNothingChanged = -7;
	const int	ErrNoPulse = -8;
	const int	ErrChannelNotAvailable = -10;
	const int	ErrDiv0 = -13;
	const int	ErrOutOfRange = -14;
	const int	ErrUnitNotAvailable = -15;
	const int	ErrTCPErr = -26;
	const int	ErrParameterOutOfRange = -28;
	const int	ErrStringTooLong = -29;
	const int	ErrMaxErr = ErrStringTooLong;

// Return errorvalues of GetTemperature and GetPressure
	const int	ErrTemperature = -1000;
	const int	ErrTempNotMeasured = ErrTemperature + ErrNoValue;
	const int	ErrTempNotAvailable = ErrTemperature + ErrNotAvailable;
	const int	ErrTempWlmMissing = ErrTemperature + ErrWlmMissing;

// Return errorvalues of GetGain
	const int	ErrGain = -1000;
	const int	ErrGainNotAvailable        = ErrGain + ErrNotAvailable;
	const int	ErrGainWlmMissing          = ErrGain + ErrWlmMissing;
	const int	ErrGainChannelNotAvailable = ErrGain + ErrChannelNotAvailable;
	const int	ErrGainOutOfRange          = ErrGain + ErrOutOfRange;
	const int	ErrGainParameterOutOfRange = ErrGain + ErrParameterOutOfRange;

// Return errorvalues of GetMultimodeInfo
	const int	ErrMMI = -1000;
	const int	ErrMMINotAvailable        = ErrMMI + ErrNotAvailable;
	const int	ErrMMIWlmMissing          = ErrMMI + ErrWlmMissing;
	const int	ErrMMIChannelNotAvailable = ErrMMI + ErrChannelNotAvailable;
	const int	ErrMMIOutOfRange          = ErrMMI + ErrOutOfRange;
	const int	ErrMMIParameterOutOfRange = ErrMMI + ErrParameterOutOfRange;

// Return errorvalues of GetDistance
	// real errorvalues are ErrDistance combined with those of GetWavelength
	const int	ErrDistance = -1000000000;
	const int	ErrDistanceNotAvailable = ErrDistance + ErrNotAvailable;
	const int	ErrDistanceWlmMissing = ErrDistance + ErrWlmMissing;

// Return flags of ControlWLMEx in combination with Show or Hide, Wait and Res = 1
	const int	flServerStarted           = 0x00000001;
	const int	flErrDeviceNotFound       = 0x00000002;
	const int	flErrDriverError          = 0x00000004;
	const int	flErrUSBError             = 0x00000008;
	const int	flErrUnknownDeviceError   = 0x00000010;
	const int	flErrWrongSN              = 0x00000020;
	const int	flErrUnknownSN            = 0x00000040;
	const int	flErrTemperatureError     = 0x00000080;
	const int	flErrPressureError        = 0x00000100;
	const int	flErrCancelledManually    = 0x00000200;
	const int	flErrWLMBusy              = 0x00000400;
	const int	flErrUnknownError         = 0x00001000;
	const int	flNoInstalledVersionFound = 0x00002000;
	const int	flDesiredVersionNotFound  = 0x00004000;
	const int	flErrFileNotFound         = 0x00008000;
	const int	flErrParmOutOfRange       = 0x00010000;
	const int	flErrCouldNotSet          = 0x00020000;
	const int	flErrEEPROMFailed         = 0x00040000;
	const int	flErrFileFailed           = 0x00080000;
	const int	flDeviceDataNewer         = 0x00100000;
	const int	flFileDataNewer           = 0x00200000;
	const int	flErrDeviceVersionOld     = 0x00400000;
	const int	flErrFileVersionOld       = 0x00800000;
	const int	flDeviceStampNewer        = 0x01000000;
	const int	flFileStampNewer          = 0x02000000;

// Return file info flags of SetOperationFile
	const int	flFileInfoDoesntExist = 0x00000000;
	const int	flFileInfoExists      = 0x00000001;
	const int	flFileInfoCantWrite   = 0x00000002;
	const int	flFileInfoCantRead    = 0x00000004;
	const int	flFileInfoInvalidName = 0x00000008;
	const int	cFileParameterError = -1;

#endif

// *** end of wlmData.h