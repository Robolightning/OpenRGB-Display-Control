// Test-only boundary shim; production uses the real libusb header/library.
#pragma once
#include <cstddef>
#include <cstdint>
#ifdef _WIN32
typedef std::ptrdiff_t ssize_t;
#else
#include <sys/types.h>
#endif
struct libusb_context {};
struct libusb_device { int id; };
struct libusb_device_handle { int id; };
struct libusb_device_descriptor { uint16_t idVendor, idProduct; uint8_t iSerialNumber; };
int libusb_init(libusb_context**);
void libusb_exit(libusb_context*);
const char* libusb_error_name(int);
ssize_t libusb_get_device_list(libusb_context*, libusb_device***);
int libusb_get_device_descriptor(libusb_device*, libusb_device_descriptor*);
int libusb_open(libusb_device*, libusb_device_handle**);
int libusb_get_string_descriptor_ascii(libusb_device_handle*, uint8_t, unsigned char*, int);
int libusb_claim_interface(libusb_device_handle*, int);
int libusb_release_interface(libusb_device_handle*, int);
void libusb_close(libusb_device_handle*);
void libusb_free_device_list(libusb_device**, int);
int libusb_bulk_transfer(libusb_device_handle*, unsigned char, unsigned char*, int, int*, unsigned int);
