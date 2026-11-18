import math
from contextlib import nullcontext
from dataclasses import replace
from threading import Event
from unittest.mock import Mock

import pytest
from PIL import Image

from openrgb_display_control import control, rendering, sdk
from openrgb_display_control.cli import main
from openrgb_display_control.control import Request, execute, open_display
from openrgb_display_control.hardware import CorsairLCD, DisplayError
from openrgb_display_control.locking import single_writer
from openrgb_display_control.playback import play
from openrgb_display_control.rendering import Frame, image_frames
from openrgb_display_control.topology import MATRIX_SIZE


class FakeTime:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def wait(self, seconds):
        self.now += seconds

    def is_set(self):
        return False


def test_fps_limit_skips_frames_without_slowing_animation():
    clock, display = FakeTime(), Mock()
    display.send.return_value = True
    frames = [Frame(bytes([i]), 0.01) for i in range(10)]
    result = play(display, frames, once=True, fps=20, stop=clock, clock=clock)
    assert [call.args[0] for call in display.send.call_args_list] == [b"\x00", b"\x05"]
    assert result["elapsed_seconds"] == pytest.approx(0.1)
    assert result["source_frames_skipped"] == 4


def test_long_stall_jumps_to_current_frame_without_a_catchup_queue():
    clock, display = FakeTime(), Mock()

    def send(data):
        clock.now += 2.001 if display.send.call_count == 1 else 0
        return True

    display.send.side_effect = send
    result = play(
        display, [Frame(b"a", 0.1), Frame(b"b", 0.1)], seconds=2.15, fps=30, stop=clock, clock=clock
    )
    assert display.send.call_count <= 3
    assert result["source_frames_skipped"] >= 19


@pytest.mark.parametrize(
    "seconds,fps", [(math.nan, 30), (math.inf, 30), (-1, 30), (1, math.nan), (1, math.inf), (1, 0)]
)
def test_nonfinite_timing_rejected_before_hardware(seconds, fps):
    with pytest.raises(ValueError):
        Request("matrix", "clock", seconds=seconds, fps=fps).validate()


def test_sdk_failure_never_falls_back_to_usb(monkeypatch):
    monkeypatch.setattr(sdk.SDKMatrix, "open", Mock(side_effect=TimeoutError("SDK timeout")))
    raw = Mock()
    monkeypatch.setattr(control, "MatrixUSB", raw)
    with pytest.raises(TimeoutError):
        open_display(Request("matrix", "off"))
    raw.assert_not_called()


def test_sdk_validation_failure_disconnects(monkeypatch):
    client = Mock(devices=[])
    monkeypatch.setattr(sdk, "connect", lambda *args: client)
    with pytest.raises(DisplayError):
        sdk.SDKMatrix.open()
    client.disconnect.assert_called_once()


def test_sdk_off_invalidates_frame_cache():
    client, device = Mock(), Mock()
    panel = sdk.SDKMatrix(client, device)
    panel._last = bytes(768)
    panel.off()
    assert panel._last is None
    device.set_mode.assert_called_once_with("Off", save=False)


def test_invalid_file_does_not_open_display_or_change_brightness(monkeypatch, tmp_path):
    opener = Mock()
    monkeypatch.setattr(control, "open_display", opener)
    with pytest.raises(FileNotFoundError):
        execute(Request("corsair", "image", str(tmp_path / "missing.png")))
    opener.assert_not_called()


def test_cancelled_preparation_does_not_open_hardware(monkeypatch):
    stop = Event()
    stop.set()
    opener = Mock()
    monkeypatch.setattr(control, "open_display", opener)
    execute(Request("matrix", "off"), stop)
    opener.assert_not_called()


def test_corsair_attempts_backlight_off_if_black_upload_fails():
    panel = object.__new__(CorsairLCD)
    panel.send = Mock(side_effect=DisplayError("write failed"))
    panel.brightness = Mock()
    with pytest.raises(DisplayError):
        panel.off()
    panel.brightness.assert_called_once_with(0)


def test_off_on_exit_runs_after_send_failure(monkeypatch):
    panel = Mock()
    panel.send.side_effect = DisplayError("write failed")
    monkeypatch.setattr(control, "open_display", lambda request: nullcontext(panel))
    with pytest.raises(DisplayError):
        execute(Request("corsair", "solid", "red", off_on_exit=True))
    panel.off.assert_called_once()


def test_animation_cache_limit(monkeypatch, tmp_path):
    path = tmp_path / "small.png"
    Image.new("RGB", MATRIX_SIZE, "red").save(path)
    monkeypatch.setattr(rendering, "MAX_CACHE", 767)
    with pytest.raises(ValueError, match="cache"):
        image_frames(path, "matrix")


def test_animation_frame_limit(monkeypatch, tmp_path):
    path = tmp_path / "animation.gif"
    a = Image.new("RGB", MATRIX_SIZE, "red")
    a.save(path, save_all=True, append_images=[Image.new("RGB", MATRIX_SIZE, "blue")], duration=100)
    monkeypatch.setattr(rendering, "MAX_FRAMES", 1)
    with pytest.raises(ValueError, match="frames"):
        image_frames(path, "matrix")


def test_alpha_composites_on_black():
    image = Image.new("RGBA", (1, 1), (255, 0, 0, 0))
    assert rendering.fit_image(image, (1, 1)).getpixel((0, 0)) == (0, 0, 0)


def test_exif_orientation_is_used_by_both_preview_and_output():
    image = Image.new("RGB", (2, 3))
    image.putpixel((0, 0), (255, 0, 0))
    image.getexif()[274] = 6
    result = rendering.fit_image(image, (3, 2), fit="stretch")
    assert result.getpixel((2, 0)) == (255, 0, 0)


def test_preview_decodes_the_exact_encoded_matrix_frame():
    image = Image.new("RGB", MATRIX_SIZE, (13, 24, 35))
    frame = rendering.encode_image(image, "matrix", brightness=50)
    preview = rendering.preview_image(frame, "matrix", brightness=50)
    assert preview.getpixel((0, 0)) == (6, 12, 18)
    assert preview.getpixel((6, 0)) == (0, 0, 0)


@pytest.mark.parametrize("text", ["OpenRGB", "05\n35", "A", "Привет"])
def test_text_fits_portrait_without_windows_font_paths(text):
    image = rendering.text_image(text, MATRIX_SIZE)
    assert image.getbbox() is not None
    assert image.size == MATRIX_SIZE


def test_process_lock_rejects_a_second_writer():
    with single_writer("matrix"), pytest.raises(DisplayError):
        with single_writer("matrix"):
            pass


def test_cli_rejects_invalid_timing_without_opening_hardware(monkeypatch, capsys):
    executor = Mock()
    monkeypatch.setattr("openrgb_display_control.cli.execute", executor)
    assert main(["--device", "matrix", "clock", "--seconds", "nan"]) == 1
    executor.assert_not_called()
    assert "finite" in capsys.readouterr().out


def test_request_validation_does_not_mutate_options():
    request = Request("matrix", "image", "a.png")
    assert replace(request, rotation=90).rotation == 90
    assert request.rotation == 0


def test_solid_color_ignores_previous_image_rotation_and_fit():
    frames = control.prepare(
        Request("matrix", "solid", "red", brightness=100, rotation=90), Event()
    )
    assert frames[0].data.count(255) == 222


def test_rotated_text_uses_the_rotated_canvas_before_encoding():
    frames = control.prepare(Request("matrix", "text", "OpenRGB", rotation=90), Event())
    preview = rendering.matrix_image(frames[0].data)
    assert preview.getbbox() is not None


def test_sdk_reused_device_id_is_rejected_before_any_write():
    client, device = Mock(), Mock()
    device.name = "Matrix"
    device.data.metadata.serial = "test-serial"
    device.data.metadata.location = "test-location"
    panel = sdk.SDKMatrix(client, device)
    device.update.side_effect = lambda: setattr(device, "name", "Different device")
    with pytest.raises(DisplayError, match="identity"):
        panel.send(bytes(768))
    device.set_mode.assert_not_called()
    device.set_colors.assert_not_called()
    with pytest.raises(DisplayError, match="identity"):
        panel.off()
    device.set_mode.assert_not_called()
