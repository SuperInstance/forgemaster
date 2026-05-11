cmake_minimum_required(VERSION 3.10)
project(flux_tensor_midi C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Library
add_library(flux_midi
    src/flux.c
    src/clock.c
    src/snap.c
    src/room.c
    src/midi_event.c
    src/sidechannel.c
    src/harmony.c
    src/ensemble.c
)

target_include_directories(flux_midi PUBLIC include)

# Link math library
target_link_libraries(flux_midi m)

# Tests
enable_testing()

add_executable(test_flux tests/test_flux.c)
target_link_libraries(test_flux flux_midi)
add_test(NAME test_flux COMMAND test_flux)

add_executable(test_clock tests/test_clock.c)
target_link_libraries(test_clock flux_midi)
add_test(NAME test_clock COMMAND test_clock)

add_executable(test_snap tests/test_snap.c)
target_link_libraries(test_snap flux_midi)
add_test(NAME test_snap COMMAND test_snap)

add_executable(test_room tests/test_room.c)
target_link_libraries(test_room flux_midi)
add_test(NAME test_room COMMAND test_room)
