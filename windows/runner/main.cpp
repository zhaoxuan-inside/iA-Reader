#include <windows.h>
#include "my_application.h"
#include "utils.h"

int APIENTRY wWinMain(_In_ HINSTANCE instance, _In_opt_ HINSTANCE prev,
                      _In_ wchar_t *command_line, _In_ int show_command) {
  // Attach to console when present (e.g., 'flutter run')
  CreateAndAttachConsole();

  MyApplication app;
  return app.Run();
}
