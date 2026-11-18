# SPDX-License-Identifier: GPL-2.0-or-later
"""Optional standalone Qt interface. No custom OpenRGB GUI patch is required."""

import argparse
import threading

from PySide6.QtCore import QSettings, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .control import Request, execute
from .rendering import preview_image
from .topology import PIXELS


class Worker(QThread):
    progress = Signal(object)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.stop = threading.Event()

    def run(self):
        try:
            self.completed.emit(execute(self.request, self.stop, self.progress.emit))
        except InterruptedError:
            self.completed.emit({"cancelled": True})
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class Preview(QWidget):
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.image = None
        self.setMinimumSize(320, 340)

    def set_frame(self, data, brightness):
        image = preview_image(data, self.device, brightness)
        self.image = QImage(
            image.tobytes(), image.width, image.height, image.width * 3, QImage.Format.Format_RGB888
        ).copy()
        self.update()

    def clear_frame(self):
        self.image = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#15171b"))
        if self.device == "matrix":
            pitch = min((self.width() - 32) / 7, (self.height() - 32) / 36)
            left, top = (self.width() - 7 * pitch) / 2, (self.height() - 36 * pitch) / 2
            for x, y, _ in PIXELS:
                color = self.image.pixelColor(x, y) if self.image else QColor("#383c44")
                painter.fillRect(
                    int(left + x * pitch),
                    int(top + y * pitch),
                    max(1, int(pitch * 0.75)),
                    max(1, int(pitch * 0.75)),
                    color,
                )
        else:
            diameter = min(self.width(), self.height()) - 32
            left, top = (self.width() - diameter) // 2, (self.height() - diameter) // 2
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            from PySide6.QtGui import QPainterPath

            clip = QPainterPath()
            clip.addEllipse(left, top, diameter, diameter)
            painter.setClipPath(clip)
            if self.image:
                painter.drawImage(left, top, self.image.scaled(diameter, diameter))
            else:
                painter.fillRect(self.rect(), QColor("#252830"))


class DisplayPage(QWidget):
    idle = Signal()

    def __init__(self, device, host, port, parent=None):
        super().__init__(parent)
        self.device, self.host, self.port = device, host, port
        self.worker = None
        self.pending = None
        self.touched = False
        self.settings = QSettings()
        self.settings.beginGroup(device)
        outer = QHBoxLayout(self)
        controls = QVBoxLayout()
        controls.addWidget(
            QLabel(
                "ASUS AniMe Matrix · 7 × 36 · 222 pixels"
                if device == "matrix"
                else "Corsair ELITE LCD · 480 × 480"
            )
        )
        form = QFormLayout()
        self.mode = QComboBox()
        for label, action in (
            (self.tr("Off"), "off"),
            (self.tr("Image / GIF / APNG"), "image"),
            (self.tr("Text"), "text"),
            (self.tr("Clock"), "clock"),
            (self.tr("Solid color"), "solid"),
            (self.tr("RGB synchronization"), "sync"),
        ):
            self.mode.addItem(label, action)
        form.addRow(self.tr("Content"), self.mode)
        self.file = QLineEdit(str(self.settings.value("file", "")))
        self.browse = QPushButton(self.tr("Choose file…"))
        row = QHBoxLayout()
        row.addWidget(self.file)
        row.addWidget(self.browse)
        form.addRow(self.tr("Image"), row)
        self.value = QLineEdit(str(self.settings.value("value", "OpenRGB")))
        self.value.setMaxLength(256)
        self.value_label = QLabel(self.tr("Text / color / RGB source ID"))
        form.addRow(self.value_label, self.value)
        self.repeat = QCheckBox(self.tr("Repeat animation"))
        self.repeat.setChecked(True)
        form.addRow(self.repeat)
        self.brightness = QSpinBox()
        self.brightness.setRange(0, 100)
        self.brightness.setSuffix(" %")
        self.brightness.setValue(self.saved_int("brightness", 50))
        form.addRow(self.tr("Brightness"), self.brightness)
        self.rotation = QComboBox()
        self.rotation.addItems(("0°", "90°", "180°", "270°"))
        self.rotation.setCurrentIndex(max(0, min(3, self.saved_int("rotation", 0))))
        form.addRow(self.tr("Clockwise rotation"), self.rotation)
        self.fit = QComboBox()
        for label, fit in (
            (self.tr("Contain"), "contain"),
            (self.tr("Cover"), "cover"),
            (self.tr("Stretch"), "stretch"),
        ):
            self.fit.addItem(label, fit)
        self.fit.setCurrentIndex(max(0, min(2, self.saved_int("fit", 0))))
        form.addRow(self.tr("Scale"), self.fit)
        self.fps = QSpinBox()
        self.fps.setRange(1, 60 if device == "matrix" else 30)
        self.fps.setValue(self.saved_int("fps", 30))
        form.addRow(self.tr("Maximum FPS"), self.fps)
        self.serial = QLineEdit()
        self.serial.setPlaceholderText(self.tr("Automatic if one display is connected"))
        form.addRow(self.tr("Serial (optional)"), self.serial)
        self.backend = QComboBox()
        self.backend.addItem(self.tr("OpenRGB SDK"), "sdk")
        self.backend.addItem(self.tr("Direct USB (exclusive ownership)"), "usb")
        if device == "matrix":
            form.addRow(self.tr("Matrix connection"), self.backend)
        controls.addLayout(form)
        buttons = QHBoxLayout()
        self.apply_button = QPushButton(self.tr("Apply"))
        self.off_button = QPushButton(self.tr("Turn display off"))
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.off_button)
        controls.addLayout(buttons)
        self.status = QLabel(self.tr("Not running. Saved files never start automatically."))
        self.status.setWordWrap(True)
        controls.addWidget(self.status)
        note = QLabel(
            self.tr(
                "RGB source accepts a unique device name or its numeric SDK ID. "
                "Use the CLI 'sources' command to list IDs."
            )
        )
        note.setWordWrap(True)
        controls.addWidget(note)
        controls.addStretch()
        outer.addLayout(controls, 3)
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(QLabel(self.tr("First applied frame")))
        self.preview = Preview(device)
        preview_layout.addWidget(self.preview, 1)
        outer.addLayout(preview_layout, 2)
        self.browse.clicked.connect(self.choose_file)
        self.apply_button.clicked.connect(self.apply_content)
        self.off_button.clicked.connect(self.blank)
        self.mode.currentIndexChanged.connect(self.update_inputs)
        self.update_inputs()

    def saved_int(self, key, default):
        try:
            return int(self.settings.value(key, default))
        except (TypeError, ValueError):
            return default

    def update_inputs(self):
        action = self.mode.currentData()
        for widget in (self.file, self.browse, self.repeat, self.fit):
            widget.setEnabled(action == "image")
        self.rotation.setEnabled(action in ("image", "text", "clock"))
        self.value.setEnabled(action in ("text", "solid", "sync"))
        if action == "solid":
            self.value.setPlaceholderText("#ffffff")
        elif action == "sync":
            self.value.setPlaceholderText(self.tr("Device name or numeric SDK ID"))
        else:
            self.value.setPlaceholderText(self.tr("Text"))

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Display content"),
            self.file.text(),
            self.tr("Images (*.png *.apng *.gif *.jpg *.jpeg *.bmp *.webp);;All files (*)"),
        )
        if path:
            self.file.setText(path)
            self.mode.setCurrentIndex(1)

    def request(self, action=None):
        action = action or self.mode.currentData()
        return Request(
            device=self.device,
            action=action,
            value=self.file.text() if action == "image" else self.value.text(),
            host=self.host,
            port=self.port,
            backend=self.backend.currentData(),
            serial=self.serial.text().strip() or None,
            brightness=self.brightness.value(),
            rotation=self.rotation.currentIndex() * 90,
            fit=self.fit.currentData(),
            fps=self.fps.value(),
            once=not self.repeat.isChecked(),
        )

    def apply_content(self):
        request = self.request()
        try:
            request.validate()
        except ValueError as error:
            self.status.setText(str(error))
            return
        for key, value in (
            ("file", self.file.text()),
            ("value", self.value.text()),
            ("brightness", self.brightness.value()),
            ("rotation", self.rotation.currentIndex()),
            ("fit", self.fit.currentIndex()),
            ("fps", self.fps.value()),
        ):
            self.settings.setValue(key, value)
        self.queue(request)

    def blank(self):
        self.mode.setCurrentIndex(0)
        self.queue(self.request("off"))

    def queue(self, request):
        self.pending = request
        self.touched = True
        self.status.setText(self.tr("Preparing…"))
        if self.worker is not None:
            self.worker.stop.set()
        else:
            self.launch_pending()

    def launch_pending(self):
        if self.pending is None or self.worker is not None:
            return
        request, self.pending = self.pending, None
        worker = Worker(request, self)
        self.worker = worker
        worker.progress.connect(self.on_progress)
        worker.completed.connect(self.on_result)
        worker.failed.connect(self.status.setText)
        worker.finished.connect(self.on_finished)
        worker.start()

    def on_progress(self, event):
        request = self.worker.request
        if "preview" in event:
            self.preview.set_frame(event["preview"], request.brightness)
        self.status.setText(self.tr("Content prepared · playing"))

    def on_result(self, result):
        request = self.worker.request
        if self.pending is None:
            if request.action == "off":
                self.preview.clear_frame()
                self.status.setText(self.tr("Display off"))
            else:
                self.status.setText(
                    self.tr("Stopped") if result.get("cancelled") else self.tr("Content applied")
                )

    def on_finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        if self.pending is not None:
            QTimer.singleShot(0, self.launch_pending)
        else:
            self.idle.emit()


class Window(QMainWindow):
    def __init__(self, host="127.0.0.1", port=6742):
        super().__init__()
        self.setWindowTitle("OpenRGB Display Control")
        self.resize(980, 700)
        tabs = QTabWidget()
        self.pages = [DisplayPage(device, host, port, self) for device in ("matrix", "corsair")]
        for page, label in zip(self.pages, ("ASUS Matrix", "Corsair LCD"), strict=True):
            tabs.addTab(page, label)
        self.setCentralWidget(tabs)
        self.closing = False
        self.close_timer = QTimer(self)
        self.close_timer.setInterval(100)
        self.close_timer.timeout.connect(self.finish_close)

    def closeEvent(self, event):
        if not self.closing:
            self.closing = True
            # Only displays touched by this window are blanked on exit.
            for page in self.pages:
                page.setEnabled(False)
                if page.touched:
                    page.blank()
            self.close_timer.start()
        if any(page.worker is not None or page.pending is not None for page in self.pages):
            event.ignore()
        else:
            self.close_timer.stop()
            event.accept()

    def finish_close(self):
        if all(page.worker is None and page.pending is None for page in self.pages):
            self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6742)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("Port must be in 1..65535")
    app = QApplication([])
    app.setOrganizationName("OpenRGB-Display-Control")
    app.setApplicationName("OpenRGB-Display-Control")
    window = Window(args.host, args.port)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
