cmake_minimum_required(VERSION 3.10)
project(snapkit C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(snapkit STATIC src/snapkit.c)
target_include_directories(snapkit PUBLIC include)
target_link_libraries(snapkit PUBLIC m)

add_library(snapkit_shared SHARED src/snapkit.c)
target_include_directories(snapkit_shared PUBLIC include)
target_link_libraries(snapkit_shared PUBLIC m)
set_target_properties(snapkit_shared PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Tests
enable_testing()

add_executable(test_eisenstein tests/test_eisenstein.c)
target_link_libraries(test_eisenstein snapkit)
add_test(NAME test_eisenstein COMMAND test_eisenstein)

add_executable(test_temporal tests/test_temporal.c)
target_link_libraries(test_temporal snapkit)
add_test(NAME test_temporal COMMAND test_temporal)

add_executable(test_spectral tests/test_spectral.c)
target_link_libraries(test_spectral snapkit)
add_test(NAME test_spectral COMMAND test_spectral)
