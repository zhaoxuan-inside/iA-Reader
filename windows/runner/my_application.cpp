#include "my_application.h"
#include <windows.h>

MyApplication::MyApplication() {}
MyApplication::~MyApplication() {}

int MyApplication::Run() {
  HWND hwnd = CreateWindowEx(
      0, L"STATIC", L"AI Reader - 极简跨平台阅读器",
      WS_OVERLAPPEDWINDOW | WS_VISIBLE,
      CW_USEDEFAULT, CW_USEDEFAULT, 1280, 800,
      nullptr, nullptr, GetModuleHandle(nullptr), nullptr);

  MSG msg;
  while (GetMessage(&msg, nullptr, 0, 0)) {
    TranslateMessage(&msg);
    DispatchMessage(&msg);
  }
  return static_cast<int>(msg.wParam);
}
