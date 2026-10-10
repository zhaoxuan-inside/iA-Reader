# Flutter Linux CMakeLists.txt
cmake_minimum_required(VERSION 3.10)

set(EPHEMERAL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/ephemeral")

# Configuration provided by flutter tool.
if(NOT DEFINED FLUTTER_TARGET_PLATFORM)
  set(FLUTTER_TARGET_PLATFORM "linux-x64")
endif()

# Plugin registration support.
set(FLUTTER_MANAGED_DIR "${CMAKE_CURRENT_SOURCE_DIR}")

add_library(flutter INTERFACE)
target_include_directories(flutter INTERFACE
  "${EPHEMERAL_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
