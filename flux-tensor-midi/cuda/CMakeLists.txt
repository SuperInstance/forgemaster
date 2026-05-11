cmake_minimum_required(VERSION 3.18)
project(flux_tensor_midi_cuda CUDA CXX)

set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CXX_STANDARD 17)

# Target sm_86 (Ampere — Jetson Orin, RTX 3000 series)
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -arch=sm_86")

# Also generate code for sm_75 (Turing — Jetson Xavier, RTX 2000)
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -gencode arch=compute_75,code=sm_75")

# Library
add_library(flux_midi_cuda
    src/flux.cu
    src/snap.cu
    src/clock.cu
    src/harmony.cu
    src/ensemble.cu
)

target_include_directories(flux_midi_cuda PUBLIC include)

# Test
enable_testing()

add_executable(test_batch tests/test_batch.cu)
target_link_libraries(test_batch flux_midi_cuda)
add_test(NAME test_batch COMMAND test_batch)
