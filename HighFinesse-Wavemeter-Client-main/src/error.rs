use crate::bindings;
use pyo3::prelude::*;

#[derive(Debug, PartialEq, Eq)]
pub struct Error1(pub i32);

#[allow(non_upper_case_globals)]
impl Error1 {
    pub const NoValue: Self = Self(bindings::ErrNoValue);
    pub const NoSignal: Self = Self(bindings::ErrNoSignal);
    pub const BadSignal: Self = Self(bindings::ErrBadSignal);
    pub const LowSignal: Self = Self(bindings::ErrLowSignal);
    pub const BigSignal: Self = Self(bindings::ErrBigSignal);
    pub const WlmMissing: Self = Self(bindings::ErrWlmMissing);
    pub const NotAvailable: Self = Self(bindings::ErrNotAvailable);
    pub const InfNothingChanged: Self = Self(bindings::InfNothingChanged);
    pub const NoPulse: Self = Self(bindings::ErrNoPulse);
    pub const ChannelNotAvailable: Self = Self(bindings::ErrChannelNotAvailable);
    pub const Div0: Self = Self(bindings::ErrDiv0);
    pub const OutOfRange: Self = Self(bindings::ErrOutOfRange);
    pub const UnitNotAvailable: Self = Self(bindings::ErrUnitNotAvailable);
    pub const TCPErr: Self = Self(bindings::ErrTCPErr);
    pub const ParameterOutOfRange: Self = Self(bindings::ErrParameterOutOfRange);
    pub const StringTooLong: Self = Self(bindings::ErrStringTooLong);

    pub fn check_err_f64(val: f64) -> Result<f64, Self> {
        if val <= 0.0 {
            Err(Self(val as i32))
        } else {
            Ok(val)
        }
    }

    pub fn check_err(val: i32) -> Result<i32, Self> {
        if val <= 0 {
            Err(Self(val))
        } else {
            Ok(val)
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub struct Error2(pub i32);

#[allow(non_upper_case_globals)]
impl Error2 {
    pub const WlmMissing: Self = Self(bindings::ResERR_WlmMissing);
    pub const CouldNotSet: Self = Self(bindings::ResERR_CouldNotSet);
    pub const ParameterOutOfRange: Self = Self(bindings::ResERR_ParmOutOfRange);
    pub const WlmOutOfResources: Self = Self(bindings::ResERR_WlmOutOfResources);
    pub const WlmInternalError: Self = Self(bindings::ResERR_WlmInternalError);
    pub const NotAvailable: Self = Self(bindings::ResERR_NotAvailable);
    pub const WlmBusy: Self = Self(bindings::ResERR_WlmBusy);
    pub const NotInMeasurementMode: Self = Self(bindings::ResERR_NotInMeasurementMode);
    pub const OnlyInMeasurementMode: Self = Self(bindings::ResERR_OnlyInMeasurementMode);
    pub const ChannelNotAvailable: Self = Self(bindings::ResERR_ChannelNotAvailable);
    pub const ChannelTemporarilyNotAvailable: Self =
        Self(bindings::ResERR_ChannelTemporarilyNotAvailable);
    pub const CalibrationOptionNotAvailable: Self = Self(bindings::ResERR_CalOptionNotAvailable);
    pub const CalibrationWavelengthOutOfRange: Self =
        Self(bindings::ResERR_CalWavelengthOutOfRange);
    pub const BadCalibrationSignal: Self = Self(bindings::ResERR_BadCalibrationSignal);
    pub const UnitNotAvailable: Self = Self(bindings::ResERR_UnitNotAvailable);

    pub fn check_err(val: i32) -> Result<(), Self> {
        if val < 0 {
            Err(Self(val))
        } else {
            Ok(())
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub struct SensorError(pub i32);

#[allow(non_upper_case_globals)]
impl SensorError {
    pub const NotMeasured: Self = Self(bindings::ErrTempNotMeasured);
    pub const NotAvailable: Self = Self(bindings::ErrTempNotAvailable);
    pub const WlmMissing: Self = Self(bindings::ErrTempWlmMissing);

    pub fn check_err(val: f64) -> Result<f64, Self> {
        if val < 0.0 {
            Err(Self(val as i32))
        } else {
            Ok(val)
        }
    }
}

impl From<Error1> for PyErr {
    fn from(err: Error1) -> Self {
        super::WavemeterError::new_err(format!("{:?}", err))
    }
}

impl From<Error2> for PyErr {
    fn from(err: Error2) -> Self {
        super::WavemeterError::new_err(format!("{:?}", err))
    }
}

impl From<SensorError> for PyErr {
    fn from(err: SensorError) -> Self {
        super::WavemeterError::new_err(format!("{:?}", err))
    }
}
