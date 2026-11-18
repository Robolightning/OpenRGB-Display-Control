import struct
from unittest.mock import Mock

import pytest
from PIL import Image

from openrgb_display_control.hardware import DisplayError, corsair_packets, matrix_packet
from openrgb_display_control.hardware import MatrixUSB as Matrix
from openrgb_display_control.rendering import fit_image, jpeg_frame, matrix_frame
from openrgb_display_control.topology import ACTIVE, MATRIX_MAP, MATRIX_SIZE


@pytest.mark.parametrize("size", [1, 1015, 1016, 1017, 2032, 2033, 65536])
def test_corsair_packet_boundaries(size):
    data = bytes(i % 251 for i in range(size))
    packets = list(corsair_packets(data))
    decoded = b""
    for i, packet in enumerate(packets):
        assert len(packet) == 1024
        op, a, b, end, index, n = struct.unpack("<BBBBHH", packet[:8])
        assert (op, a, b, index) == (2, 5, 0x40, i)
        assert end == int(i == len(packets) - 1)
        decoded += packet[8 : 8 + n]
        assert not any(packet[8 + n :])
    assert decoded == data


def test_matrix_topology_and_padding():
    assert MATRIX_SIZE == (7, 36)
    assert len(MATRIX_MAP) == 7 * 36
    assert len(ACTIVE) == 222
    frame = matrix_frame(Image.new("RGB", MATRIX_SIZE, (10, 20, 30)))
    assert len(frame) == 768
    assert frame.count(10) == frame.count(20) == frame.count(30) == 222
    assert frame.count(0) == 102


def test_portrait_landmarks_keep_physical_wire_slots():
    # Top-left and the irregular last rows must not rotate or mirror, and
    # block 15's padding must remain intact after changing the coordinate map.
    image = Image.new("RGB", MATRIX_SIZE)
    markers = {
        (0, 0): (0, (11, 12, 13)),
        (1, 0): (1, (21, 22, 23)),
        (4, 31): (720, (31, 32, 33)),
        (0, 32): (722, (41, 42, 43)),
        (0, 35): (732, (51, 52, 53)),
    }
    for xy, (_, color) in markers.items():
        image.putpixel(xy, color)
    frame = matrix_frame(image)
    for offset, color in markers.values():
        assert tuple(frame[offset + channel * 16] for channel in range(3)) == color
    assert [sum(bool(wire) for wire in MATRIX_MAP[y * 7 : (y + 1) * 7]) for y in range(36)] == [
        2,
        4,
        6,
    ] + [7] * 26 + [7, 6, 5, 4, 3, 2, 1]
    assert not any(frame[offset] for offset in (721, 729, 733, 734, 735))


def test_rotation_is_clockwise_like_qt_preview():
    image = Image.new("RGB", (2, 3))
    image.putpixel((0, 0), (255, 0, 0))
    rotated = fit_image(image, (3, 2), "stretch", rotation=90)
    assert rotated.getpixel((2, 0)) == (255, 0, 0)
    assert rotated.getpixel((0, 0)) == (0, 0, 0)


def test_matrix_off_does_not_reenable_hardware_animation():
    panel = object.__new__(Matrix)
    panel.command = Mock(return_value=bytes([0xEC, 0x42, 0]) + bytes(62))
    panel.status = Mock(return_value={"mode": 0})
    panel.off()
    panel.command.assert_called_once_with(0x42, bytes([0, 0, 0]))


def test_matrix_checks_off_readback():
    panel = object.__new__(Matrix)
    panel.command = Mock()
    panel.status = Mock(return_value={"mode": 2})
    with pytest.raises(DisplayError):
        panel.off()


def test_matrix_invalid_size_never_opens_usb():
    panel = object.__new__(Matrix)
    panel._open_bulk = Mock()
    with pytest.raises(ValueError):
        panel.send(bytes(767))
    panel._open_bulk.assert_not_called()


def test_black_jpeg_is_decodable_at_native_resolution():
    import io

    image = Image.open(io.BytesIO(jpeg_frame(Image.new("RGB", (480, 480)))))
    assert image.size == (480, 480)
    assert image.getextrema() == ((0, 0), (0, 0), (0, 0))


def test_matrix_oversize_command_rejected():
    with pytest.raises(ValueError):
        matrix_packet(0x42, bytes(64))


def test_apng_animation_excludes_default_poster(tmp_path):
    from openrgb_display_control.rendering import image_frames

    poster = Image.new("RGB", MATRIX_SIZE, "black")
    red = Image.new("RGB", MATRIX_SIZE, "red")
    green = Image.new("RGB", MATRIX_SIZE, "lime")
    path = tmp_path / "sample.apng"
    poster.save(
        path,
        format="PNG",
        save_all=True,
        append_images=[red, green],
        default_image=True,
        duration=[100, 200],
    )
    frames = image_frames(path, "matrix", brightness=100)
    assert len(frames) == 2
    assert frames[0].data.count(255) == 222
    assert frames[0].data != frames[1].data
    assert frames[0].duration == 0.1 and frames[1].duration == 0.2
