// build.rs — compile CUDA kernel with nvcc; fall back to cc-compiled CPU stub.
//
// Primary path: invoke nvcc 12.6 directly to produce a static archive.
// Fallback  : use the `cc` crate to compile cuda_stub.c, which exports the
//             same C symbols with no-op / error-return implementations.
//
// Why not use `cc::Build::cuda(true)` for the primary path?
// The cc crate's CUDA support selects the nvcc that is first on PATH
// (/usr/bin/nvcc here — CUDA 11.5).  We specifically need 12.6 to match the
// installed libcudart.so.12 from /usr/local/cuda-12.6.  Using Command gives
// us precise control over the binary path.

use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=cuda_kernel.cu");
    println!("cargo:rerun-if-changed=cuda_stub.c");
    println!("cargo:rerun-if-changed=build.rs");

    let out_dir    = PathBuf::from(env::var("OUT_DIR").unwrap());
    let nvcc       = "/usr/local/cuda-12.6/bin/nvcc";
    let cuda_lib   = "/usr/local/cuda-12.6/lib64";
    let obj_path   = out_dir.join("cuda_kernel.o");
    let lib_path   = out_dir.join("libcuda_kernel.a");

    // ── Step 1: try to compile the CUDA kernel ────────────────────────────
    let nvcc_ok = Command::new(nvcc)
        .args([
            "-O2",
            "-arch=sm_50",          // Maxwell+, covers most post-2014 GPUs
            "-Xcompiler", "-fPIC",  // position-independent code for the .a
            "-c", "cuda_kernel.cu",
            "-o", obj_path.to_str().unwrap(),
        ])
        .status()
        .map(|s| s.success())
        .unwrap_or(false);

    // ── Step 2: archive and emit link directives, or fall back ────────────
    if nvcc_ok {
        let ar_ok = Command::new("ar")
            .args(["crs", lib_path.to_str().unwrap(), obj_path.to_str().unwrap()])
            .status()
            .map(|s| s.success())
            .unwrap_or(false);

        if ar_ok {
            // Tell Cargo where to find libcuda_kernel.a
            println!("cargo:rustc-link-search=native={}", out_dir.display());
            println!("cargo:rustc-link-lib=static=cuda_kernel");

            // CUDA runtime (dynamic) — linked after the static archive so the
            // linker can resolve cudaMalloc, cudaMemcpy, etc.
            println!("cargo:rustc-link-search=native={}", cuda_lib);
            println!("cargo:rustc-link-lib=dylib=cudart");
            // nvcc-compiled objects pull in libstdc++ symbols
            println!("cargo:rustc-link-lib=dylib=stdc++");

            // Embed the runtime library path so `cargo run` works without
            // LD_LIBRARY_PATH being set manually.
            println!("cargo:rustc-link-arg=-Wl,-rpath,{}", cuda_lib);
            return;
        }
    }

    // ── Fallback: cc crate compiles the C stub ────────────────────────────
    println!("cargo:warning=nvcc not found or failed — building CPU stub (no GPU support)");
    cc::Build::new()
        .file("cuda_stub.c")
        .compile("cuda_kernel");
}
