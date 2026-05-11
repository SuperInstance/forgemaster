cmake_minimum_required(VERSION 3.10)
project(flux-tensor-midi LANGUAGES Fortran)

# Fortran 2008 standard
set(CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -std=f2008 -Wall -Wextra")

# Source modules
set(MODULE_SOURCES
  src/flux_midi_flux.f90
  src/flux_midi_clock.f90
  src/flux_midi_snap.f90
  src/flux_midi_room.f90
  src/flux_midi_harmony.f90
  src/flux_midi_spectrum.f90
  src/flux_midi_batch.f90
)

# Library target
add_library(flux_midi ${MODULE_SOURCES})
target_include_directories(flux_midi PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Test executables
add_executable(test_flux tests/test_flux.f90)
target_link_libraries(test_flux flux_midi)

add_executable(test_clock tests/test_clock.f90)
target_link_libraries(test_clock flux_midi)

add_executable(test_snap tests/test_snap.f90)
target_link_libraries(test_snap flux_midi)

add_executable(test_spectrum tests/test_spectrum.f90)
target_link_libraries(test_spectrum flux_midi)

# Test runner
add_custom_target(check
  COMMAND test_flux
  COMMAND test_clock
  COMMAND test_snap
  COMMAND test_spectrum
  DEPENDS test_flux test_clock test_snap test_spectrum
  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
