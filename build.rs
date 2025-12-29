use std::env;
use std::path::{Path, PathBuf};

fn print_rerun_if_changed(path: &str) {
    println!("cargo:rerun-if-changed={}", path);
}

fn gen_halide_runtime_bindings(halide_include_dir: &Path, out_path: &Path) {
    let header_path = halide_include_dir.join("HalideRuntime.h");

    let bindings = bindgen::Builder::default()
        .header(header_path.to_str().expect("Failed to convert path to str"))
        // .rust_target(rust_target)
        .generate()
        .expect("Unable to generate bindings");

    bindings
        .write_to_file(out_path)
        .expect("Couldn't write halide_runtime_bindings.rs.");
}

fn gen_generator_bindings(header_path: &Path, function_name: &str, out_path: &Path) {
    let bindings = bindgen::Builder::default()
        .header(header_path.to_str().expect("Failed to convert path to str"))
        // .rust_target(rust_target)
        .allowlist_function(function_name)
        .blocklist_type("halide_buffer_t")
        .blocklist_type("halide_device_interface_impl_t")
        .blocklist_type("halide_device_interface_t")
        .blocklist_type("halide_dimension_t")
        .blocklist_type("halide_filter_metadata_t")
        .blocklist_type("halide_type_t")
        .generate()
        .expect("Unable to generate bindings");

    bindings
        .write_to_file(out_path)
        .expect("Couldn't write generator bindings.");
}

fn link_library(library_path: &Path) {
    // `cargo:rustc-link-lib=static=<foo>`` requires the library to be named lib<foo>.a.
    // whereas `cargo:rustc-link-arg=` allows specifying an absolute path.
    println!(
        "cargo:rustc-link-arg={}",
        library_path
            .to_str()
            .expect("Failed to convert path to str")
    );
}

fn main() {
    for path in &[
        "halide_generated/add.h",
        "halide_generated/add.a",
        "halide_generated/demosaic.h",
        "halide_generated/demosaic.a",
        "halide_generated/host_debug_runtime.a",
    ] {
        print_rerun_if_changed(path);
    }

    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let cargo_manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());

    {
        let python_venv_dir = PathBuf::from(env::var("VIRTUAL_ENV").unwrap());
        let halide_include_dir = python_venv_dir.join("lib/python3.13/site-packages/halide/include");

        gen_halide_runtime_bindings(
            &halide_include_dir,
            &out_dir.join("halide_runtime_bindings.rs"),
        );
    }

    let halide_generated_dir = cargo_manifest_dir.join("halide_generated");

    // Add.
    {
        gen_generator_bindings(
            &halide_generated_dir.join("add.h"),
            "add",
            &out_dir.join("add_bindings.rs"),
        );

        link_library(&halide_generated_dir.join("add.a"));
    }

    // Demosaic.
    {
        gen_generator_bindings(
            &halide_generated_dir.join("demosaic.h"),
            "demosaic",
            &out_dir.join("demosaic_bindings.rs"),
        );

        link_library(&halide_generated_dir.join("demosaic.a"));
    }

    // Link the Halide runtime library separately.
    link_library(&halide_generated_dir.join("host_debug_runtime.a"));
}
