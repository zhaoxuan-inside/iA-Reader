#include "my_application.h"

#include <string.h>

#include <flutter_linux/flutter_linux.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif

#include "flutter/generated_plugin_registrant.h"

struct _MyApplication {
  GtkApplication parent_instance;
  char** dart_entrypoint_arguments;
};

G_DEFINE_TYPE(MyApplication, my_application, GTK_TYPE_APPLICATION)

// 应用内顶栏为唯一标题栏（窗口去装饰）。Flutter 侧经 MethodChannel "ai.reader/window"
// 驱动最小化/最大化/关闭与拖拽；Wayland 的 begin_move_drag 需要仍处于按住状态的
// 按键 serial，故在此记录最近一次落在视图上的左键按下事件供 beginDrag 取用。
static struct {
  guint button;
  gdouble root_x;
  gdouble root_y;
  guint32 time;
} last_view_press = {0, 0.0, 0.0, 0};

static gboolean on_view_button_press(GtkWidget* view, GdkEventButton* event,
                                     gpointer user_data) {
  if (event->type == GDK_BUTTON_PRESS && event->button == 1) {
    last_view_press.button = event->button;
    last_view_press.root_x = event->x_root;
    last_view_press.root_y = event->y_root;
    last_view_press.time = event->time;
  }
  return FALSE;  // 继续传给 Flutter 自身的处理
}

static FlMethodChannel* window_channel = NULL;

static void window_method_call_handler(FlMethodChannel* channel,
                                       FlMethodCall* call, gpointer user_data) {
  GtkWindow* window = GTK_WINDOW(user_data);
  const gchar* name = fl_method_call_get_name(call);
  g_autoptr(FlMethodResponse) response = NULL;

  if (strcmp(name, "minimize") == 0) {
    gtk_window_iconify(window);
    response = FL_METHOD_RESPONSE(
        fl_method_success_response_new(fl_value_new_bool(TRUE)));
  } else if (strcmp(name, "toggleMaximize") == 0) {
    if (gtk_window_is_maximized(window)) {
      gtk_window_unmaximize(window);
    } else {
      gtk_window_maximize(window);
    }
    response = FL_METHOD_RESPONSE(
        fl_method_success_response_new(fl_value_new_bool(gtk_window_is_maximized(window))));
  } else if (strcmp(name, "close") == 0) {
    gtk_window_close(window);
    response = FL_METHOD_RESPONSE(
        fl_method_success_response_new(fl_value_new_bool(TRUE)));
  } else if (strcmp(name, "beginDrag") == 0) {
    if (last_view_press.button != 0) {
      gtk_window_begin_move_drag(window, (gint)last_view_press.button,
                                 (gint)last_view_press.root_x,
                                 (gint)last_view_press.root_y,
                                 (guint32)last_view_press.time);
    }
    response = FL_METHOD_RESPONSE(
        fl_method_success_response_new(fl_value_new_bool(TRUE)));
  } else {
    response = FL_METHOD_RESPONSE(fl_method_not_implemented_response_new());
  }

  g_autoptr(GError) error = NULL;
  if (!fl_method_call_respond(call, response, &error)) {
    g_warning("Failed to respond window method call: %s", error->message);
  }
}

// Called when first Flutter frame received.
static void first_frame_cb(MyApplication* self, FlView* view) {
  gtk_widget_show(gtk_widget_get_toplevel(GTK_WIDGET(view)));
}

// Implements GApplication::activate.
static void my_application_activate(GApplication* application) {
  MyApplication* self = MY_APPLICATION(application);
  GtkWindow* window =
      GTK_WINDOW(gtk_application_window_new(GTK_APPLICATION(application)));

  // 应用内 Flutter 顶栏即唯一标题栏：去掉 GTK 装饰，避免双标题栏；
  // 窗口最小化/最大化/关闭与拖拽由应用内顶栏经 MethodChannel 驱动。
  gtk_window_set_title(window, "AI Reader");
  gtk_window_set_default_size(window, 1280, 720);
  gtk_window_set_decorated(window, FALSE);

  g_autoptr(FlDartProject) project = fl_dart_project_new();
  // Impeller (OpenGLES) 在本机驱动栈上存在主题切换后字形/图层沿用旧颜色的渲染缺陷：
  // 暗色启动后切亮色，正文与标题仍以暗色主题颜色绘制（浅字浅底不可见），
  // 连续重建与整树重建均无法恢复（引擎全局缓存）。固定走 Skia 后端规避。
  fl_dart_project_set_enable_impeller(project, FALSE);
  fl_dart_project_set_dart_entrypoint_arguments(
      project, self->dart_entrypoint_arguments);

  FlView* view = fl_view_new(project);
  GdkRGBA background_color;
  // Background defaults to black, override it here if necessary, e.g. #00000000
  // for transparent.
  gdk_rgba_parse(&background_color, "#000000");
  fl_view_set_background_color(view, &background_color);
  gtk_widget_show(GTK_WIDGET(view));
  gtk_container_add(GTK_CONTAINER(window), GTK_WIDGET(view));

  // Show the window when Flutter renders.
  // Requires the view to be realized so we can start rendering.
  g_signal_connect_swapped(view, "first-frame", G_CALLBACK(first_frame_cb),
                           self);
  g_signal_connect(view, "button-press-event", G_CALLBACK(on_view_button_press),
                   NULL);
  gtk_widget_realize(GTK_WIDGET(view));

  // 窗口控制通道：最小化/最大化/关闭/拖拽（见文件头注释）
  g_autoptr(FlStandardMethodCodec) window_codec = fl_standard_method_codec_new();
  window_channel = fl_method_channel_new(
      fl_engine_get_binary_messenger(fl_view_get_engine(view)),
      "ai.reader/window", FL_METHOD_CODEC(window_codec));
  fl_method_channel_set_method_call_handler(window_channel,
                                            window_method_call_handler, window,
                                            NULL);

  fl_register_plugins(FL_PLUGIN_REGISTRY(view));

  gtk_widget_grab_focus(GTK_WIDGET(view));
}

// Implements GApplication::local_command_line.
static gboolean my_application_local_command_line(GApplication* application,
                                                  gchar*** arguments,
                                                  int* exit_status) {
  MyApplication* self = MY_APPLICATION(application);
  // Strip out the first argument as it is the binary name.
  self->dart_entrypoint_arguments = g_strdupv(*arguments + 1);

  g_autoptr(GError) error = nullptr;
  if (!g_application_register(application, nullptr, &error)) {
    g_warning("Failed to register: %s", error->message);
    *exit_status = 1;
    return TRUE;
  }

  g_application_activate(application);
  *exit_status = 0;

  return TRUE;
}

// Implements GApplication::startup.
static void my_application_startup(GApplication* application) {
  // MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application startup.

  G_APPLICATION_CLASS(my_application_parent_class)->startup(application);
}

// Implements GApplication::shutdown.
static void my_application_shutdown(GApplication* application) {
  // MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application shutdown.

  G_APPLICATION_CLASS(my_application_parent_class)->shutdown(application);
}

// Implements GObject::dispose.
static void my_application_dispose(GObject* object) {
  MyApplication* self = MY_APPLICATION(object);
  g_clear_pointer(&self->dart_entrypoint_arguments, g_strfreev);
  G_OBJECT_CLASS(my_application_parent_class)->dispose(object);
}

static void my_application_class_init(MyApplicationClass* klass) {
  G_APPLICATION_CLASS(klass)->activate = my_application_activate;
  G_APPLICATION_CLASS(klass)->local_command_line =
      my_application_local_command_line;
  G_APPLICATION_CLASS(klass)->startup = my_application_startup;
  G_APPLICATION_CLASS(klass)->shutdown = my_application_shutdown;
  G_OBJECT_CLASS(klass)->dispose = my_application_dispose;
}

static void my_application_init(MyApplication* self) {}

MyApplication* my_application_new() {
  // Set the program name to the application ID, which helps various systems
  // like GTK and desktop environments map this running application to its
  // corresponding .desktop file. This ensures better integration by allowing
  // the application to be recognized beyond its binary name.
  g_set_prgname(APPLICATION_ID);

  return MY_APPLICATION(g_object_new(my_application_get_type(),
                                     "application-id", APPLICATION_ID, "flags",
                                     G_APPLICATION_NON_UNIQUE, nullptr));
}
