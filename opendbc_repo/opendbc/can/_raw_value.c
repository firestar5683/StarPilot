#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

typedef struct {
  PyObject *names[4];
} ExtractState;

static PyObject *get_raw_value(PyObject *self, PyObject *args) {
  ExtractState *state = PyModule_GetState(self);
  PyObject *signal, *payload, *expected;
  PyObject *msb_obj = NULL, *lsb_obj = NULL, *size_obj = NULL, *little_obj = NULL;
  const unsigned char *data;
  Py_ssize_t length;
  long msb, lsb, size, little, first, last;
  if (!PyArg_UnpackTuple(args, "get_raw_value", 3, 3, &signal, &payload, &expected)) return NULL;
  if (state == NULL || state->names[0] == NULL || state->names[1] == NULL ||
      state->names[2] == NULL || state->names[3] == NULL) goto unsupported;
  if (!PyType_Check(expected) || Py_TYPE(signal) != (PyTypeObject *)expected) goto unsupported;
  if (!PyBytes_CheckExact(payload) && !PyByteArray_CheckExact(payload)) goto unsupported;
  msb_obj = PyObject_GetAttr(signal, state->names[0]);
  if (msb_obj == NULL) goto unsupported;
  lsb_obj = PyObject_GetAttr(signal, state->names[1]);
  if (lsb_obj == NULL) goto unsupported;
  size_obj = PyObject_GetAttr(signal, state->names[2]);
  if (size_obj == NULL) goto unsupported;
  little_obj = PyObject_GetAttr(signal, state->names[3]);
  if (little_obj == NULL) goto unsupported;
  if (!PyLong_CheckExact(msb_obj) || !PyLong_CheckExact(lsb_obj) ||
      !PyLong_CheckExact(size_obj) || !PyBool_Check(little_obj)) goto unsupported;
  msb = PyLong_AsLong(msb_obj);
  if (PyErr_Occurred()) goto unsupported;
  lsb = PyLong_AsLong(lsb_obj);
  if (PyErr_Occurred()) goto unsupported;
  size = PyLong_AsLong(size_obj);
  if (PyErr_Occurred()) goto unsupported;
  little = little_obj == Py_True;
  /* Attribute access may execute Python; acquire mutable storage only afterward. */
  if (PyBytes_CheckExact(payload)) {
    data = (const unsigned char *)PyBytes_AS_STRING(payload);
    length = PyBytes_GET_SIZE(payload);
  } else {
    data = (const unsigned char *)PyByteArray_AS_STRING(payload);
    length = PyByteArray_GET_SIZE(payload);
  }
  if (msb < 0 || msb >= 512 || lsb < 0 || lsb >= 512 || size <= 0 || size > 64) goto unsupported;
  if (little) {
    first = lsb / 8;
    last = msb / 8;
    if (size != msb - lsb + 1) goto unsupported;
  } else {
    first = msb / 8;
    last = lsb / 8;
    if (size != 8 * (last - first) + msb % 8 - lsb % 8 + 1) goto unsupported;
  }
  if (first < 0 || first > last || last >= length) goto unsupported;
  uint64_t result = 0;
  long remaining = size;
  for (long byte = msb / 8; remaining > 0; byte += little ? -1 : 1) {
    if (byte < 0 || byte >= length) goto unsupported;
    const long low = lsb / 8 == byte ? lsb : byte * 8;
    const long high = msb / 8 == byte ? msb : (byte + 1) * 8 - 1;
    const long width = high - low + 1;
    const long bit_shift = low - byte * 8;
    const long result_shift = remaining - width;
    if (width <= 0 || width > 8 || bit_shift < 0 || bit_shift > 7 ||
        result_shift < 0 || result_shift > 63) goto unsupported;
    const unsigned int fragment = (data[byte] >> bit_shift) & ((1U << width) - 1U);
    result |= (uint64_t)fragment << result_shift;
    remaining -= width;
  }
  Py_DECREF(msb_obj);
  Py_DECREF(lsb_obj);
  Py_DECREF(size_obj);
  Py_DECREF(little_obj);
  return PyLong_FromUnsignedLongLong((unsigned long long)result);

unsupported:
  Py_XDECREF(msb_obj);
  Py_XDECREF(lsb_obj);
  Py_XDECREF(size_obj);
  Py_XDECREF(little_obj);
  PyErr_Clear();
  Py_INCREF(Py_NotImplemented);
  return Py_NotImplemented;
}

static PyMethodDef methods[] = {
  {"get_raw_value", get_raw_value, METH_VARARGS, "Extract an exact complete <=64-bit CAN signal, or NotImplemented."},
  {NULL, NULL, 0, NULL},
};
static int module_traverse(PyObject *self, visitproc visit, void *arg) {
  ExtractState *state = PyModule_GetState(self);
  if (state != NULL) {
    for (int i = 0; i < 4; ++i) Py_VISIT(state->names[i]);
  }
  return 0;
}

static int module_clear(PyObject *self) {
  ExtractState *state = PyModule_GetState(self);
  if (state != NULL) {
    for (int i = 0; i < 4; ++i) Py_CLEAR(state->names[i]);
  }
  return 0;
}

static void module_free(void *self) {
  (void)module_clear((PyObject *)self);
}

static struct PyModuleDef module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "_raw_value",
  .m_doc = "Complete raw CAN signal bit extraction.",
  .m_size = sizeof(ExtractState),
  .m_methods = methods,
  .m_traverse = module_traverse,
  .m_clear = module_clear,
  .m_free = module_free,
};
PyMODINIT_FUNC PyInit__raw_value(void) {
  PyObject *created = PyModule_Create(&module);
  if (created == NULL) return NULL;
  ExtractState *state = PyModule_GetState(created);
  static const char *names[4] = {"msb", "lsb", "size", "is_little_endian"};
  for (int i = 0; i < 4; ++i) {
    state->names[i] = PyUnicode_InternFromString(names[i]);
    if (state->names[i] == NULL) {
      Py_DECREF(created);
      return NULL;
    }
  }
  return created;
}
