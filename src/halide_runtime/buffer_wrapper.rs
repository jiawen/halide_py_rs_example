use super::data_type::{DataType, halide_type_for};
use super::{halide_buffer_t, halide_dimension_t};
use ndarray::ArrayViewMutD;

// `buffer` references `_dims`.
// Dynamic number of dimensions.
// TODO(jiawen): Name this something better.
pub struct BufferWrapper {
    dims: Box<[halide_dimension_t]>,
    buffer_t: halide_buffer_t,
}

// TODO(jiawen): this only takes views. should there be versions for arrays, refs, etc too?
// how about when D is known? it's slightly faster.
// TODO(jiawen): reverse axes
impl BufferWrapper {
    // TODO: rename to "from" and implement the From trait
    pub fn new<T>(mut view: ArrayViewMutD<T>) -> Self
    where
        T: DataType,
    {
        let dimensions = view.ndim() as i32;

        let shape = view.shape();
        let strides = view.strides();

        let dims: Box<[halide_dimension_t]> = (0..dimensions)
            .map(|axis| {
                // Reverse axis order.
                let i = dimensions - axis - 1;

                halide_dimension_t {
                    min: 0,
                    extent: shape[i as usize] as i32,
                    stride: strides[i as usize] as i32, // in units of elements
                    flags: 0,
                }
            })
            .collect();

        let mut buffer_wrapper = BufferWrapper {
            dims,
            buffer_t: halide_buffer_t {
                device: 0,
                device_interface: std::ptr::null_mut(),
                host: view.as_mut_ptr() as *mut u8,
                flags: 0,
                type_: halide_type_for::<T>(),
                dimensions: dimensions,
                dim: std::ptr::null_mut(), // We will set this below.
                padding: std::ptr::null_mut(),
            },
        };

        // Set the pointer to the stable heap allocation.
        buffer_wrapper.buffer_t.dim = buffer_wrapper.dims.as_ptr() as *mut _;

        buffer_wrapper
    }

    pub fn buffer_t(&mut self) -> &mut halide_buffer_t {
        &mut self.buffer_t
    }
}
