"""QThread workers so network and audio calls never block the UI."""

from PySide6.QtCore import QThread, Signal

from app import gemini_client, voice


class StreamWorker(QThread):
    chunk = Signal(str)
    done = Signal()
    failed = Signal(str)

    def __init__(self, model, parts, key=""):
        super().__init__()
        self._model = model
        self._parts = parts
        self._key = key

    def run(self):
        try:
            for text in gemini_client.stream(self._model, self._parts, self._key):
                self.chunk.emit(text)
            self.done.emit()
        except Exception as exc:  # noqa: BLE001 - surface any API error to the UI
            self.failed.emit(str(exc))


class CompleteWorker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, model, parts, key=""):
        super().__init__()
        self._model = model
        self._parts = parts
        self._key = key

    def run(self):
        try:
            self.done.emit(gemini_client.complete(self._model, self._parts, self._key))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SpeakWorker(QThread):
    done = Signal()
    failed = Signal(str)

    def __init__(self, text):
        super().__init__()
        self._text = text

    def run(self):
        try:
            voice.speak(self._text)
            self.done.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ListenWorker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def run(self):
        try:
            self.done.emit(voice.listen())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
