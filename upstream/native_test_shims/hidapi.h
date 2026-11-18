// Test-only boundary shim; production uses the real hidapi header/library.
#pragma once
#include <cstddef>
struct hid_device { int unused; };
int hid_get_serial_number_string(hid_device*, wchar_t*, size_t);
int hid_write(hid_device*, const unsigned char*, size_t);
int hid_read_timeout(hid_device*, unsigned char*, size_t, int);
void hid_close(hid_device*);
