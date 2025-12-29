mod add;
mod demosaic;
mod halide_runtime;
use halide_runtime::BufferWrapper;
use ndarray::{Array1, Array2, Array3, array};

fn test_add() {
    let mut a2: Array1<i32> = array![1, 2, 3, 4, 5, 6];
    let mut b2: Array1<i32> = array![1, 2, 3, 4, 5, 6];

    let mut ha2_wrapper = BufferWrapper::new(a2.view_mut().into_dyn());
    let mut hb2_wrapper = BufferWrapper::new(b2.view_mut().into_dyn());

    unsafe {
        let ret = add::add(ha2_wrapper.buffer_t(), hb2_wrapper.buffer_t());
        println!("Halide add returned: {}", ret);
    }

    println!("a2 after Halide add:\n{:?}", a2);
    println!("b2 after Halide add:\n{:?}", b2);
}

fn test_demosaic() {
    let mut bayer: Array2<u16> = Array2::from_shape_fn((480, 640), |_| rand::random());
    let cfa_pattern: u8 = 1; // RGGB
    let mut rgb: Array3<i16> = Array3::zeros((3, 480, 640));

    let mut bayer_wrapper = BufferWrapper::new(bayer.view_mut().into_dyn());
    let mut rgb_wrapper = BufferWrapper::new(rgb.view_mut().into_dyn());

    unsafe {
        let ret = demosaic::demosaic(
            bayer_wrapper.buffer_t(),
            cfa_pattern,
            rgb_wrapper.buffer_t(),
        );
        println!("Halide demosaic returned: {}", ret);
    }
}

fn main() {
    println!("Hello Halide!");

    test_add();
    test_demosaic();
}
