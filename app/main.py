"""Entry point.  Run from the project root with:  python -m app.main"""

import sys

from PySide6.QtWidgets import QApplication

from app import storage
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("StudyHelper")
    storage.init()
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
