mod bindings;
pub mod error;

pub use error::{Error1, Error2, SensorError};
use pyo3::{create_exception, exceptions::PyException, prelude::*};
use std::{ffi::CString, mem::MaybeUninit};

create_exception!(Wavemeter, WavemeterError, PyException);

#[pyclass]
#[derive(Debug, PartialEq, Eq, Clone)]
pub struct Unit(i32);

#[allow(non_upper_case_globals)]
#[pymethods]
impl Unit {
    #[classattr]
    pub const WavelengthVacuum: Self = Self(bindings::cReturnWavelengthVac);
    #[classattr]
    pub const WavelengthAir: Self = Self(bindings::cReturnWavelengthAir);
    #[classattr]
    pub const Frequency: Self = Self(bindings::cReturnFrequency);
    #[classattr]
    pub const Wavenumber: Self = Self(bindings::cReturnWavenumber);
    #[classattr]
    pub const PhotonEnergy: Self = Self(bindings::cReturnPhotonEnergy);

    pub fn get_raw(&self) -> i32 {
        self.0
    }
}

#[pyclass]
#[derive(Debug, PartialEq, Eq, Clone)]
pub struct CCDArray(i32);

#[allow(non_upper_case_globals)]
#[pymethods]
impl CCDArray {
    #[classattr]
    pub const Array1: Self = Self(1);
    #[classattr]
    pub const Array2: Self = Self(2);

    pub fn get_raw(&self) -> i32 {
        self.0
    }
}

#[pyclass]
#[derive(Debug, PartialEq, Eq, Clone)]
pub struct OperationState(pub i32);

#[allow(non_upper_case_globals)]
#[pymethods]
impl OperationState {
    #[classattr]
    pub const Adjustment: Self = Self(bindings::cAdjustment);
    #[classattr]
    pub const Measurement: Self = Self(bindings::cMeasurement);
    #[classattr]
    pub const Stop: Self = Self(bindings::cStop);
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct PIDParams {
    #[pyo3(get, set)]
    pub p: f64,
    #[pyo3(get, set)]
    pub i: f64,
    #[pyo3(get, set)]
    pub d: f64,
    #[pyo3(get, set)]
    pub dt: f64,
    #[pyo3(get, set)]
    pub ta: f64,
    #[pyo3(get, set)]
    pub dev_sens_fac: f64,
}

#[pymethods]
impl PIDParams {
    #[new]
    pub fn new(p: f64, i: f64, d: f64, dt: f64, ta: f64, dev_sens_fac: f64) -> Self {
        Self {
            p,
            i,
            d,
            dt,
            ta,
            dev_sens_fac,
        }
    }
}

#[pyclass]
pub struct WaveMeter;

#[pymethods]
impl WaveMeter {
    /// Returns the Wavelength Meter or Laser Spectrum Analyser version.
    ///
    /// The version consists of:
    /// - the Wavelength Meter type (can be 5 to 8) or Laser Spectrum Analyser type (always 5)
    /// - the version number
    /// - the revision number of the software
    /// - the floating software compilation number
    ///
    /// # Errors
    /// Return [`Error1::WlmMissing`] if no Wavelength Meter or Laser Spectrum Analyser is active.
    #[staticmethod]
    pub fn get_wlm_version() -> Result<(i32, i32, i32, i32), Error1> {
        let get_version = |ver| {
            let result = unsafe { bindings::GetWLMVersion(ver) };
            if result == bindings::ErrWlmMissing {
                Err(Error1(result))
            } else {
                Ok(result)
            }
        };

        let dev_type = get_version(0)?;
        let version = get_version(1)?;
        let revision = get_version(2)?;
        let compilation = get_version(3)?;

        Ok((dev_type, version, revision, compilation))
    }

    #[staticmethod]
    pub fn get_wlm_count() -> i32 {
        unsafe { bindings::GetWLMCount(0) }
    }

    #[staticmethod]
    pub fn get_frequency(channel: i32) -> Result<f64, Error1> {
        let freq = unsafe { bindings::GetFrequencyNum(channel, 0.0) };
        Error1::check_err_f64(freq)
    }

    #[staticmethod]
    pub fn get_wavelength(channel: i32) -> Result<f64, Error1> {
        let wavelength = unsafe { bindings::GetWavelengthNum(channel, 0.0) };
        Error1::check_err_f64(wavelength)
    }

    #[staticmethod]
    pub fn get_linewidth(unit: Unit) -> Result<f64, Error1> {
        let linewidth = unsafe { bindings::GetLinewidth(unit.get_raw(), 0.0) };
        Error1::check_err_f64(linewidth)
    }

    #[staticmethod]
    pub fn get_analog_in() -> f64 {
        unsafe { bindings::GetAnalogIn(0.0) }
    }

    #[staticmethod]
    pub fn get_temperature() -> Result<f64, SensorError> {
        let temp = unsafe { bindings::GetTemperature(0.0) };
        SensorError::check_err(temp)
    }

    #[staticmethod]
    pub fn get_pressure() -> Result<f64, SensorError> {
        let pressure = unsafe { bindings::GetPressure(0.0) };
        SensorError::check_err(pressure)
    }

    #[staticmethod]
    pub fn get_exposure(channel: i32, arr: CCDArray) -> Result<i32, Error1> {
        let exposure = unsafe { bindings::GetExposureNum(channel, arr.get_raw(), 0) };
        Error1::check_err(exposure)
    }

    #[staticmethod]
    pub fn set_exposure(channel: i32, arr: CCDArray, exposure: i32) -> Result<(), Error2> {
        let code = unsafe { bindings::SetExposureNum(channel, arr.get_raw(), exposure) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_exposure_mode(channel: i32) -> bool {
        unsafe { bindings::GetExposureModeNum(channel, 0) != 0 }
    }

    #[staticmethod]
    pub fn set_exposure_mode(channel: i32, mode: bool) -> Result<(), Error2> {
        let code = unsafe { bindings::SetExposureModeNum(channel, mode as u8) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_deviation_signal(channel: i32) -> f64 {
        unsafe { bindings::GetDeviationSignalNum(channel, 0.0) }
    }

    #[staticmethod]
    pub fn set_deviation_signal(channel: i32, voltage: f64) -> Result<(), Error2> {
        let code = unsafe { bindings::SetDeviationSignalNum(channel, voltage) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_deviation_mode() -> bool {
        unsafe { bindings::GetDeviationMode(0) != 0 }
    }

    #[staticmethod]
    pub fn set_deviation_mode(enable: bool) -> Result<(), Error2> {
        let code = unsafe { bindings::SetDeviationMode(enable as u8) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_deviation_reference() -> f64 {
        unsafe { bindings::GetDeviationReference(0.0) }
    }

    #[staticmethod]
    pub fn set_deviation_reference(reference: f64) -> Result<(), Error2> {
        let code = unsafe { bindings::SetDeviationReference(reference) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_power(channel: i32) -> Result<f64, Error1> {
        let power = unsafe { bindings::GetPowerNum(channel, 0.0) };
        Error1::check_err_f64(power)
    }

    #[staticmethod]
    pub fn get_amplitude(channel: i32, array: CCDArray) -> Result<(i32, i32, i32), Error2> {
        let get_amplitude = |index| {
            let code = unsafe { bindings::GetAmplitudeNum(channel, index, 0) };
            if code < 0 {
                Err(Error2(code))
            } else {
                Ok(code)
            }
        };

        match array {
            CCDArray::Array1 => Ok((
                get_amplitude(bindings::cMin1)?,
                get_amplitude(bindings::cAvg1)?,
                get_amplitude(bindings::cMax1)?,
            )),
            CCDArray::Array2 => Ok((
                get_amplitude(bindings::cMin2)?,
                get_amplitude(bindings::cAvg2)?,
                get_amplitude(bindings::cMax2)?,
            )),
            _ => Err(Error2::NotAvailable),
        }
    }

    #[staticmethod]
    pub fn get_operation_state() -> OperationState {
        let code = unsafe { bindings::GetOperationState(0) };
        OperationState(code as i32)
    }

    #[staticmethod]
    pub fn get_background() -> bool {
        let enabled = unsafe { bindings::GetBackground(0) };
        enabled != 0
    }

    #[staticmethod]
    pub fn set_background(enable: bool) -> Result<(), Error2> {
        let code = unsafe { bindings::SetBackground(enable as i32) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_switcher_mode() -> bool {
        let enabled = unsafe { bindings::GetSwitcherMode(0) };
        enabled != 0
    }

    #[staticmethod]
    pub fn set_switcher_mode(enable: bool) -> Result<(), Error2> {
        let code = unsafe { bindings::SetSwitcherMode(enable as i32) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_switcher_channel() -> i32 {
        unsafe { bindings::GetSwitcherChannel(0) }
    }

    #[staticmethod]
    pub fn set_switcher_channel(channel: i32) -> Result<(), Error2> {
        let code = unsafe { bindings::SetSwitcherChannel(channel) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_pid_course(port: i32) -> Result<String, Error2> {
        let mut buffer = vec![0_u8; 1024];
        let code = unsafe { bindings::GetPIDCourseNum(port, buffer.as_mut_ptr() as *mut _) };

        if code < 0 {
            Err(Error2(code))
        } else {
            buffer.retain(|e| e != &0);
            CString::new(buffer)
                .expect("null bytes are removed above")
                .into_string()
                .map_err(|_| Error2::NotAvailable)
        }
    }

    #[staticmethod]
    pub fn set_pid_course(port: i32, pid_course: String) -> Result<(), Error2> {
        let pid_course = CString::new(pid_course).map_err(|_| Error2::CouldNotSet)?;
        if pid_course.as_bytes_with_nul().len() > 1024 {
            return Err(Error2::CouldNotSet);
        }

        let code = unsafe { bindings::SetPIDCourseNum(port, pid_course.as_ptr() as *mut _) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_pid_settings(port: i32) -> Result<PIDParams, Error1> {
        let pid_setting_f64 = |ps| {
            let mut dval = MaybeUninit::uninit();
            let code = unsafe {
                bindings::GetPIDSetting(ps, port, std::ptr::null_mut(), dval.as_mut_ptr())
            };
            Error1::check_err(code)?;
            Ok(unsafe { dval.assume_init() })
        };

        Ok(PIDParams {
            p: pid_setting_f64(bindings::cmiPID_P)?,
            i: pid_setting_f64(bindings::cmiPID_I)?,
            d: pid_setting_f64(bindings::cmiPID_D)?,
            dt: pid_setting_f64(bindings::cmiPID_dt)?,
            ta: pid_setting_f64(bindings::cmiPID_T)?,
            dev_sens_fac: pid_setting_f64(bindings::cmiDeviationSensitivityFactor)?,
        })
    }

    #[staticmethod]
    pub fn set_pid_settings(port: i32, pid_settings: PIDParams) -> Result<(), Error2> {
        let pid_setting_f64 = |ps, dval| {
            let code = unsafe { bindings::SetPIDSetting(ps, port, 0, dval) };
            Error2::check_err(code)
        };

        pid_setting_f64(bindings::cmiPID_P, pid_settings.p)?;
        pid_setting_f64(bindings::cmiPID_I, pid_settings.i)?;
        pid_setting_f64(bindings::cmiPID_D, pid_settings.d)?;
        pid_setting_f64(bindings::cmiPID_dt, pid_settings.dt)?;
        pid_setting_f64(bindings::cmiPID_T, pid_settings.ta)?;
        pid_setting_f64(
            bindings::cmiDeviationSensitivityFactor,
            pid_settings.dev_sens_fac,
        )?;

        Ok(())
    }

    #[staticmethod]
    pub fn clear_pid_history(port: i32) {
        unsafe { bindings::ClearPIDHistory(port) };
    }

    #[staticmethod]
    pub fn install_wait_event(timeout: i64) -> i64 {
        unsafe {
            bindings::Instantiate(
                bindings::cInstNotification,
                bindings::cNotifyInstallWaitEvent,
                timeout,
                0,
            )
        }
    }

    #[staticmethod]
    pub fn uninstall_wait_event() -> i64 {
        unsafe {
            bindings::Instantiate(
                bindings::cInstNotification,
                bindings::cNotifyRemoveWaitEvent,
                0,
                0,
            )
        }
    }
    #[staticmethod]
    pub fn wait_for_event() -> Result<(bool, i32, i32, f64), Error2> {
        let mut mode = MaybeUninit::uninit();
        let mut ival = MaybeUninit::uninit();
        let mut dval = MaybeUninit::uninit();

        let code = unsafe {
            bindings::WaitForWLMEvent(mode.as_mut_ptr(), ival.as_mut_ptr(), dval.as_mut_ptr())
        };

        match code {
            1 | 2 => unsafe {
                Ok((
                    true,
                    mode.assume_init(),
                    ival.assume_init(),
                    dval.assume_init(),
                ))
            },
            -1 | 0 => Ok((false, 0, 0, 0.0)),
            -2 => Err(Error2::WlmInternalError),
            _ => panic!("unknown return code"),
        }
    }

    #[staticmethod]
    pub fn convert_unit(val: f64, unit_from: Unit, unit_to: Unit) -> Result<f64, Error1> {
        if val < 0.0 {
            return Ok(val);
        }

        let code = unsafe { bindings::ConvertUnit(val, unit_from.get_raw(), unit_to.get_raw()) };
        Error1::check_err_f64(code)
    }

    #[staticmethod]
    pub fn start_measurement() -> Result<(), Error2> {
        let code =
            unsafe { bindings::Operation(bindings::cCtrlStartMeasurement.try_into().unwrap()) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn stop_measurement() -> Result<(), Error2> {
        let code = unsafe { bindings::Operation(bindings::cCtrlStopAll.try_into().unwrap()) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_deviation_channel(port: i32) -> Result<i32, Error1> {
        let mut ival = MaybeUninit::uninit();
        let mut dval = MaybeUninit::uninit();
        let code = unsafe {
            bindings::GetPIDSetting(
                bindings::cmiDeviationChannel,
                port,
                ival.as_mut_ptr(),
                dval.as_mut_ptr(),
            )
        };
        Error1::check_err(code)?;
        unsafe { Ok(ival.assume_init()) }
    }

    #[staticmethod]
    pub fn set_deviation_channel(port: i32, channel: i32) -> Result<(), Error2> {
        let code =
            unsafe { bindings::SetPIDSetting(bindings::cmiDeviationChannel, port, channel, 0.0) };
        Error2::check_err(code)
    }

    #[staticmethod]
    pub fn get_laser_deviation_reference(port: i32) -> Result<f64, Error1> {
        let mut ival = MaybeUninit::uninit();
        let mut dval = MaybeUninit::uninit();
        let mut sval = MaybeUninit::uninit();

        let code = unsafe {
            bindings::GetLaserControlSetting(
                bindings::cmiDeviationRefAt,
                port,
                ival.as_mut_ptr(),
                dval.as_mut_ptr(),
                sval.as_mut_ptr(),
            )
        };
        Error1::check_err(code)?;

        unsafe { Ok(dval.assume_init()) }
    }

    #[staticmethod]
    pub fn set_laser_deviation_reference(port: i32, voltage: f64) -> Result<(), Error2> {
        let code = unsafe {
            bindings::SetLaserControlSetting(
                bindings::cmiDeviationRefAt,
                port,
                0,
                voltage,
                ['a'; 0].as_mut_ptr() as *mut _,
            )
        };
        Error2::check_err(code)
    }
}

#[pymodule]
fn wavemeter(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<WaveMeter>()?;
    m.add_class::<Unit>()?;
    m.add_class::<CCDArray>()?;
    m.add_class::<OperationState>()?;
    m.add_class::<PIDParams>()?;

    m.add("WavemeterError", py.get_type::<WavemeterError>())?;

    Ok(())
}
