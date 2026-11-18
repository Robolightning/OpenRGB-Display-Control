import os
import time
from threading import Event

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from openrgb_display_control import gui


@pytest.fixture
def app(tmp_path):
    application = QApplication.instance() or QApplication([])
    application.setOrganizationName("DisplayControlTests")
    application.setApplicationName("IsolatedTests")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    return application


def pump(app, condition, timeout=3):
    end = time.monotonic() + timeout
    while not condition() and time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)
    assert condition()


def test_opening_and_closing_gui_never_touches_hardware(app, monkeypatch):
    calls = []
    monkeypatch.setattr(gui, "execute", lambda *args: calls.append(args))
    window = gui.Window()
    assert not any(page.touched for page in window.pages)
    window.close()
    app.processEvents()
    assert calls == []


def test_latest_request_waits_for_old_worker_and_off_releases_it(app, monkeypatch):
    calls = []
    started = Event()
    released = Event()

    def execute(request, stop, emit):
        calls.append(request.action)
        if request.action == "clock":
            started.set()
            assert stop.wait(2)
            released.set()
        elif request.action == "off":
            assert released.is_set()
        return {"cancelled": stop.is_set()}

    monkeypatch.setattr(gui, "execute", execute)
    page = gui.DisplayPage("matrix", "127.0.0.1", 6742)
    page.mode.setCurrentIndex(3)
    page.apply_content()
    pump(app, started.is_set)
    page.blank()
    pump(app, lambda: page.worker is None and page.pending is None)
    assert calls == ["clock", "off"]
    assert page.preview.image is None


def test_preview_has_no_pixels_in_staircase_holes(app):
    from PIL import Image

    from openrgb_display_control.rendering import matrix_frame

    widget = gui.Preview("matrix")
    widget.set_frame(matrix_frame(Image.new("RGB", (7, 36), "red")), 100)
    assert widget.image.pixelColor(0, 0).red() == 255
    assert widget.image.pixelColor(6, 0).red() == 0


def test_settings_do_not_autoplay_saved_file(app, monkeypatch):
    settings = QSettings()
    settings.setValue("matrix/file", "animation.gif")
    calls = []
    monkeypatch.setattr(gui, "execute", lambda *args: calls.append(args))
    window = gui.Window()
    assert window.pages[0].file.text() == "animation.gif"
    assert window.pages[0].mode.currentData() == "off"
    assert calls == []
    window.close()
