"""Snip-style region selector.

We grab the whole primary monitor once, then let the user drag a box over that
frozen screenshot. Cropping happens on the captured image, so the selection is
pixel-accurate regardless of Windows display scaling.
"""

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog

from app import capture


def _pil_to_qpixmap(img):
    img = img.convert("RGBA")
    qimg = QImage(
        img.tobytes("raw", "RGBA"), img.width, img.height, QImage.Format_RGBA8888
    )
    return QPixmap.fromImage(qimg.copy())


class _RegionOverlay(QDialog):
    def __init__(self, pil_img, screen):
        super().__init__()
        self._pil = pil_img
        self.result_image = None
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CrossCursor)
        self._pix = _pil_to_qpixmap(pil_img)
        self._origin = None
        self._current = None

    def _src_rect(self, r):
        sx = self._pix.width() / max(1, self.width())
        sy = self._pix.height() / max(1, self.height())
        return QRect(
            int(r.x() * sx), int(r.y() * sy),
            int(r.width() * sx), int(r.height() * sy),
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self._pix)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))  # dim everything
        if self._origin and self._current:
            r = QRect(self._origin, self._current).normalized()
            # Re-draw the selected area at full brightness.
            p.drawPixmap(r, self._pix, self._src_rect(r))
            p.setPen(QPen(QColor("#6ea8ff"), 2))
            p.drawRect(r)
        p.setPen(QColor("#cfe3ff"))
        p.drawText(24, 36, "Drag a box around the problem.  Esc to cancel.")
        p.end()

    def mousePressEvent(self, event):
        self._origin = event.position().toPoint()
        self._current = self._origin
        self.update()

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._origin is not None:
            r = QRect(self._origin, event.position().toPoint()).normalized()
            if r.width() > 6 and r.height() > 6:
                s = self._src_rect(r)
                box = (s.x(), s.y(), s.x() + s.width(), s.y() + s.height())
                self.result_image = self._pil.crop(box)
            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()


def select_region():
    """Show the overlay; return a cropped PIL image, or None if cancelled."""
    screen = QGuiApplication.primaryScreen()
    pil = capture.capture_primary()
    overlay = _RegionOverlay(pil, screen)
    if overlay.exec():
        return overlay.result_image
    return None
