#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <string.h>

static int g_py_initialized = 0;

static void ensure_python_init(void) {
    if (!g_py_initialized) {
        if (!Py_IsInitialized()) {
            Py_Initialize();
        }
        PyGILState_STATE gstate = PyGILState_Ensure();
        PyRun_SimpleString(
            "import sys, os\n"
            "for p in [os.getcwd(), '/usr/lib/ai-reader', '/usr/lib/ai-reader/backend']:\n"
            "    if os.path.exists(p) and p not in sys.path: sys.path.insert(0, p)\n"
            "try:\n"
            "    from backend.reader_engine import ai_reader_invoke as py_invoke\n"
            "except Exception:\n"
            "    try:\n"
            "        from reader_engine import ai_reader_invoke as py_invoke\n"
            "    except Exception:\n"
            "        py_invoke = None\n"
        );
        g_py_initialized = 1;
        PyGILState_Release(gstate);
    }
}

char* ai_reader_invoke(const char* action, const char* payload) {
    ensure_python_init();
    if (!action || !payload) {
        return strdup("{\"code\":40001,\"message\":\"Invalid null pointer arguments\",\"data\":{},\"metrics\":{}}");
    }

    PyGILState_STATE gstate = PyGILState_Ensure();
    PyObject* main_mod = PyImport_AddModule("__main__");
    PyObject* main_dict = PyModule_GetDict(main_mod);
    PyObject* py_invoke_fn = PyDict_GetItemString(main_dict, "py_invoke");

    char* result_cstr = NULL;
    if (py_invoke_fn && PyCallable_Check(py_invoke_fn)) {
        PyObject* args = PyTuple_Pack(2, PyUnicode_FromString(action), PyUnicode_FromString(payload));
        PyObject* py_res = PyObject_CallObject(py_invoke_fn, args);
        Py_DECREF(args);
        if (py_res && PyUnicode_Check(py_res)) {
            const char* utf8 = PyUnicode_AsUTF8(py_res);
            result_cstr = strdup(utf8);
            Py_DECREF(py_res);
        } else {
            if (PyErr_Occurred()) {
                PyErr_Print();
            }
            result_cstr = strdup("{\"code\":50001,\"message\":\"Python execution returned non-string\",\"data\":{},\"metrics\":{}}");
        }
    } else {
        result_cstr = strdup("{\"code\":50001,\"message\":\"Failed to bind backend.reader_engine.ai_reader_invoke\",\"data\":{},\"metrics\":{}}");
    }

    PyGILState_Release(gstate);
    return result_cstr ? result_cstr : strdup("{\"code\":50001,\"message\":\"Memory allocation error\",\"data\":{},\"metrics\":{}}");
}

void ai_reader_free_string(char* ptr) {
    if (ptr) {
        free(ptr);
    }
}
