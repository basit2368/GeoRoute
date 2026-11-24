cmake_minimum_required(VERSION 3.16)
project(georoute_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(GEOROUTE_SOURCES
    src/closest_pair.cpp
    src/tsp.cpp)

add_library(georoute_engine SHARED ${GEOROUTE_SOURCES})
target_include_directories(georoute_engine PUBLIC include)
set_target_properties(georoute_engine PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON)

if(MSVC)
    target_compile_options(georoute_engine PRIVATE /W4 /O2)
else()
    target_compile_options(georoute_engine PRIVATE -Wall -Wextra -O3)
endif()

add_executable(engine_tests tests/engine_tests.cpp ${GEOROUTE_SOURCES})
target_include_directories(engine_tests PRIVATE include)

enable_testing()
add_test(NAME engine_tests COMMAND engine_tests)
