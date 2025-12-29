#[allow(dead_code)]
#[allow(non_camel_case_types)] // Fixes the "upper camel case" warnings
#[allow(non_snake_case)] // Fixes function names like MyFunction()
#[allow(non_upper_case_globals)] // Fixes constants like my_constant
mod include_bindings;
pub use include_bindings::halide_buffer_t;
pub use include_bindings::halide_dimension_t;
pub use include_bindings::halide_type_code_t;
pub use include_bindings::halide_type_code_t_halide_type_float;
pub use include_bindings::halide_type_code_t_halide_type_int;
pub use include_bindings::halide_type_code_t_halide_type_uint;
pub use include_bindings::halide_type_t;

mod buffer_wrapper;
mod data_type;

pub use buffer_wrapper::BufferWrapper;
pub use data_type::DataType;
