#include "utils.h"
#include <windows.h>
#include <stdio.h>

void CreateAndAttachConsole() {
  if (::AttachConsole(ATTACH_PARENT_PROCESS)) {
    FILE *unused;
    if (freopen_s(&unused, "CONOUT$", "w", stdout)) {}
    if (freopen_s(&unused, "CONOUT$", "w", stderr)) {}
  }
}
