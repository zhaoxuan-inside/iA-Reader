cmake_minimum_required(VERSION 3.10)
project(runner LANGUAGES CXX)

set(BINARY_NAME "ai_reader")
set(APPLICATION_ID "com.example.ai_reader")

cmake_policy(SET CMP0063 NEW)

set(CMAKE_INSTALL_RPATH "$ORIGIN/lib")

# Root filesystem for cross-building.
if(SYSROOT_PATH)
  set(CMAKE_SYSROOT ${SYSROOT_PATH})
  if(CMAKE_C_COMPILER_TARGET)
    set(CMAKE_CXX_COMPILER_TARGET ${CMAKE_C_COMPILER_TARGET})
  else()
    set(CMAKE_CXX_COMPILER_TARGET ${CMAKE_C_COMPILER_TARGET})
  endif()
endif()

# Build configuration
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Configure build type.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE "Debug" CACHE STRING "Choose the type of build." FORCE)
endif()

# Compilation flags
add_definitions(-DAPPLICATION_ID="${APPLICATION_ID}")

# Add dependency libraries
find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK REQUIRED IMPORTED_TARGET gtk+-3.0)

add_subdirectory(flutter)

add_executable(${BINARY_NAME}
  "main.cc"
  "my_application.cc"
  "${FLUTTER_MANAGED_DIR}/generated_plugin_registrant.cc"
)

target_link_libraries(${BINARY_NAME} PRIVATE flutter)
target_link_libraries(${BINARY_NAME} PRIVATE PkgConfig::GTK)

# Target properties
set_target_properties(${BINARY_NAME} PROPERTIES
  OUTPUT_NAME "${BINARY_NAME}"
)
