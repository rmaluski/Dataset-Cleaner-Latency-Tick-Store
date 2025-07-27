cmake_minimum_required(VERSION 3.16)
project(dataset_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(Arrow REQUIRED)
find_package(OpenMP)
find_package(Prometheus REQUIRED)

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# Source files
set(SOURCES
    src/simd_parser.cpp
    src/arrow_loader.cpp
    src/parallel_processor.cpp
    src/prometheus_exporter.cpp
    src/csv_tokenizer.cpp
)

# Create shared library
add_library(dataset_core SHARED ${SOURCES})

# Link libraries
target_link_libraries(dataset_core
    Arrow::arrow
    Arrow::arrow_python
    prometheus::prometheus
)

if(OpenMP_CXX_FOUND)
    target_link_libraries(dataset_core OpenMP::OpenMP_CXX)
endif()

# Compiler flags for optimization
target_compile_options(dataset_core PRIVATE
    -O3
    -march=native
    -mtune=native
    -ffast-math
    -funroll-loops
)

# Python extension
pybind11_add_module(dataset_core_python src/python_binding.cpp)
target_link_libraries(dataset_core_python dataset_core) 