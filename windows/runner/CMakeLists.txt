cmake_minimum_required(VERSION 3.14)
project(runner LANGUAGES CXX)

add_executable(${BINARY_NAME} WIN32
  "main.cpp"
  "my_application.cpp"
  "utils.cpp"
  "runner.exe.manifest"
)

target_compile_features(${BINARY_NAME} PRIVATE cxx_std_17)
target_link_libraries(${BINARY_NAME} PRIVATE dwmapi.lib)
