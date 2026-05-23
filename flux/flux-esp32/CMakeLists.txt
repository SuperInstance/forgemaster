# FLUX VM for ESP32 — ESP-IDF Build Configuration
# Optimized for Xtensa LX7 dual-core constraint checking
cmake_minimum_required(VERSION 3.16)

# Must be set before include(project.cmake)
set(EXTRA_COMPONENT_DIRS "main")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(flux_esp32)

# Compiler flags for maximum throughput on Xtensa LX7
target_compile_options(${PROJECT_NAME}.elf PRIVATE
    -O2                         # Optimize for speed (not -O3, avoids code bloat)
    -ffast-math                 # Fast floating-point (we use FPU sparingly)
    -fomit-frame-pointer        # Free up A15 for general use
    -frename-registers          # Aggressive register allocation
    -finline-functions          # Inline hot opcode handlers
    -Wno-unused-function        # IRAM_ATTR functions may appear unused
)

# Custom linker script for FLUX memory layout
target_linker_script(${PROJECT_NAME}.elf
    "${CMAKE_CURRENT_SOURCE_DIR}/linker/flux_memory.ld"
)
