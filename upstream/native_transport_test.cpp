// SPDX-License-Identifier: GPL-2.0-or-later
// Compile this with the actual proposed AsusAnimeMatrixController.cpp and the
// test-only include shims. Does not open USB or claim physical device access.
#include "AsusAnimeMatrixController.h"
#include <cassert>
#include <cstring>
#include <cwchar>
#include <deque>
#include <iostream>
#include <vector>

int test_warnings = 0;
static std::deque<std::vector<unsigned char> > replies;
static int mode_value = 0;
static int bulk_writes = 0;
static int claims = 0;
static int releases = 0;
static bool fail_bulk = false;
static bool short_status = false;
static bool fail_write = false;
static libusb_device wrong = {0};
static libusb_device right = {1};

int hid_get_serial_number_string(hid_device*, wchar_t* value, size_t)
{
    std::wmemcpy(value, L"TEST-ONLY", 10);
    return 0;
}
int hid_write(hid_device*, const unsigned char* value, size_t size)
{
    if(fail_write) return -1;
    assert(size == 65 && value[0] == 0xEC);
    std::vector<unsigned char> reply(65, 0);
    reply[0] = 0xEC;
    reply[1] = value[1] == 0xC1 ? 0x41 : value[1];
    if(value[1] == 0x42) mode_value = value[2];
    if(value[1] == 0xC1)
    {
        reply[10] = (unsigned char)mode_value;
        if(short_status) reply.resize(3);
    }
    replies.push_back(reply);
    return 65;
}
int hid_read_timeout(hid_device*, unsigned char* value, size_t size, int)
{
    if(replies.empty()) return -1;
    std::vector<unsigned char> reply = replies.front();
    replies.pop_front();
    assert(size >= reply.size());
    std::memcpy(value, reply.data(), reply.size());
    return (int)reply.size();
}
void hid_close(hid_device*) {}
int libusb_init(libusb_context** context) { *context = new libusb_context; return 0; }
void libusb_exit(libusb_context* context) { delete context; }
const char* libusb_error_name(int) { return "mock"; }
ssize_t libusb_get_device_list(libusb_context*, libusb_device*** list)
{
    *list = new libusb_device*[3]{&wrong, &right, nullptr};
    return 2;
}
int libusb_get_device_descriptor(libusb_device*, libusb_device_descriptor* value)
{
    value->idVendor = 0x0B05; value->idProduct = 0x1A21; value->iSerialNumber = 1;
    return 0;
}
int libusb_open(libusb_device* device, libusb_device_handle** handle)
{
    *handle = new libusb_device_handle{device->id}; return 0;
}
int libusb_get_string_descriptor_ascii(libusb_device_handle* handle, uint8_t, unsigned char* value, int)
{
    const char* serial = handle->id ? "TEST-ONLY" : "WRONG";
    std::memcpy(value, serial, std::strlen(serial) + 1); return (int)std::strlen(serial);
}
int libusb_claim_interface(libusb_device_handle* handle, int interface_number)
{
    assert(handle->id == 1 && interface_number == 0); ++claims; return 0;
}
int libusb_release_interface(libusb_device_handle*, int) { ++releases; return 0; }
void libusb_close(libusb_device_handle* handle) { delete handle; }
void libusb_free_device_list(libusb_device** devices, int) { delete[] devices; }
int libusb_bulk_transfer(libusb_device_handle*, unsigned char endpoint, unsigned char*, int size,
                         int* count, unsigned int timeout)
{
    assert(endpoint == 1 && size == 768 && timeout == 500);
    ++bulk_writes; *count = fail_bulk ? 767 : 768; return 0;
}

int main()
{
    hid_device hid = {};
    unsigned char frame[768] = {};
    int active = 0;
    bool seen[226] = {};
    for(unsigned int i = 0; i < sizeof(ASUS_MATRIX_MAP); i++)
    {
        unsigned int wire = ASUS_MATRIX_MAP[i];
        if(!wire) continue;
        assert(!seen[wire]); seen[wire] = true; ++active;
        unsigned int offset = AsusMatrixRedOffset(wire);
        assert(offset + 32 < sizeof(frame)); frame[offset] = 17;
    }
    assert(active == 222 && !seen[213] && !seen[221] && !seen[225]);
    {
        AsusAnimeMatrixController controller(&hid, "test", "ALDR2-S452-TEST");
        assert(controller.GetMode() == 0);
        assert(!controller.SendFrame(frame, 767) && claims == 0);
        assert(controller.SendFrame(frame, 768));
        assert(bulk_writes == 1 && claims == 1);
        assert(controller.SendFrame(frame, 768) && bulk_writes == 1);
        assert(controller.SetMode(0) && controller.GetMode() == 0 && releases == 1);
        assert(controller.SendFrame(frame, 768) && bulk_writes == 2);
        frame[0] = 18;
        fail_bulk = true;
        assert(!controller.SendFrame(frame, 768));
        fail_bulk = false;
        assert(controller.SendFrame(frame, 768) && bulk_writes == 4);
        short_status = true;
        assert(!controller.SetMode(0) && controller.GetMode() == -1);
        short_status = false;
        fail_write = true;
        assert(!controller.SetMode(0));
        fail_write = false;
        assert(controller.SetMode(0));
    }
    assert(claims == releases && test_warnings >= 3);
    std::cout << "Native transport/topology regression checks passed\n";
}
