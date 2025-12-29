use super::{
    halide_type_code_t, halide_type_code_t_halide_type_float, halide_type_code_t_halide_type_int,
    halide_type_code_t_halide_type_uint, halide_type_t,
};

// Supported Halide data types.
// TODO(jiawen): Add float16 and bfloat16.
pub trait DataType {
    fn type_code() -> halide_type_code_t;
    fn bits() -> u8;
    fn lanes() -> u16 {
        1
    }
}

impl DataType for f32 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_float
    }
    fn bits() -> u8 {
        32
    }
}

impl DataType for f64 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_float
    }
    fn bits() -> u8 {
        64
    }
}

impl DataType for i8 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_int
    }
    fn bits() -> u8 {
        8
    }
}

impl DataType for i16 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_int
    }
    fn bits() -> u8 {
        16
    }
}

impl DataType for i32 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_int
    }
    fn bits() -> u8 {
        32
    }
}

impl DataType for i64 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_int
    }
    fn bits() -> u8 {
        64
    }
}

impl DataType for u8 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_uint
    }
    fn bits() -> u8 {
        8
    }
}

impl DataType for u16 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_uint
    }
    fn bits() -> u8 {
        16
    }
}

impl DataType for u32 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_uint
    }
    fn bits() -> u8 {
        32
    }
}

impl DataType for u64 {
    fn type_code() -> halide_type_code_t {
        halide_type_code_t_halide_type_uint
    }
    fn bits() -> u8 {
        64
    }
}

pub fn halide_type_for<T>() -> halide_type_t
where
    T: DataType,
{
    halide_type_t {
        code: T::type_code() as u8,
        bits: T::bits(),
        lanes: T::lanes(),
    }
}
