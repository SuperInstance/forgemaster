fn main() {
    #[cfg(feature = "cuda")]
    {
        println!("cargo:rerun-if-changed=src/cuda/production_kernel.cu");
        println!("cargo:rerun-if-changed=src/cuda/incremental_update.cu");

        let cuda_src_dir = std::path::Path::new("src/cuda");
        let out_dir = std::env::var("OUT_DIR").unwrap();

        let nvcc = std::env::var("NVCC").unwrap_or_else(|_| "nvcc".to_string());

        let common_flags = [
            "-O3",
            "--use_fast_math",
            "-gencode", "arch=compute_70,code=sm_70",  // V100
            "-gencode", "arch=compute_80,code=sm_80",  // A100
            "-gencode", "arch=compute_86,code=sm_86",  // RTX 4050
            "-Xcompiler", "-fPIC",
        ];

        // Compile production kernel → static library
        let prod_out = std::path::Path::new(&out_dir).join("libflux_production_kernel.a");
        let status = std::process::Command::new(&nvcc)
            .args(&common_flags)
            .arg("-c")
            .arg(cuda_src_dir.join("production_kernel.cu"))
            .arg("-o")
            .arg(&prod_out)
            .status()
            .expect("Failed to run nvcc — is CUDA toolkit installed?");
        assert!(status.success(), "nvcc failed compiling production_kernel.cu");

        // Compile incremental update kernel → static library
        let update_out = std::path::Path::new(&out_dir).join("libflux_update_bounds.a");
        let status = std::process::Command::new(&nvcc)
            .args(&common_flags)
            .arg("-c")
            .arg(cuda_src_dir.join("incremental_update.cu"))
            .arg("-o")
            .arg(&update_out)
            .status()
            .expect("Failed to run nvcc");
        assert!(status.success(), "nvcc failed compiling incremental_update.cu");

        // Tell cargo to link against the compiled objects and CUDA runtime
        println!("cargo:rustc-link-search=native={}", out_dir);
        println!("cargo:rustc-link-lib=static=flux_production_kernel");
        println!("cargo:rustc-link-lib=static=flux_update_bounds");
        println!("cargo:rustc-link-lib=dylib=cudart");
    }
}
