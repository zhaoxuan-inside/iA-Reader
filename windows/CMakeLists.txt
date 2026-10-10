cmake_minimum_required(VERSION 3.14)
project(ai_reader LANGUAGES CXX)

set(BINARY_NAME "ai_reader")

cmake_policy(SET CMP0091 NEW)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")

# Enable Per-Monitor V2 DPI awareness
add_subdirectory("runner")
