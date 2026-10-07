"""Dark, translucent, indigo-accented theme applied app-wide via QSS."""

QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: #e6e8ef; }

/* The rounded, semi-transparent window body (lets the desktop show through). */
#root {
    background: rgba(18, 19, 28, 0.93);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
}

#titlebar { background: transparent; }
#appTitle { font-size: 15px; font-weight: 700; color: #ffffff; }
#appSub  { color: #8b93a7; font-size: 11px; }

QPushButton#winbtn, QPushButton#winclose {
    background: transparent; border: none; border-radius: 7px;
    min-width: 30px; max-width: 30px; min-height: 26px; color: #aab2c2; font-size: 15px;
}
QPushButton#winbtn:hover { background: rgba(255,255,255,0.08); color: #fff; }
QPushButton#winclose:hover { background: #e5484d; color: #fff; }

/* Sidebar navigation */
#sidebar { background: rgba(255,255,255,0.028); border-radius: 12px; }
QPushButton#nav {
    text-align: left; padding: 10px 14px; border: none; border-radius: 9px;
    color: #aab2c2; background: transparent; font-weight: 600;
}
QPushButton#nav:hover { background: rgba(255,255,255,0.06); color: #e6e8ef; }
QPushButton#nav:checked { background: rgba(99,102,241,0.20); color: #c7d2fe; }

/* Buttons */
QPushButton {
    background: #262a3b; border: none; border-radius: 9px;
    padding: 8px 14px; color: #e6e8ef; font-weight: 600;
}
QPushButton:hover { background: #2f3447; }
QPushButton:disabled { background: #21243200; color: #5b6276; }
QPushButton#accent { background: #6366f1; color: #ffffff; }
QPushButton#accent:hover { background: #4f46e5; }
QPushButton#accent:disabled { background: #393d63; color: #b9bdea; }

/* Inputs */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #161826; border: 1px solid #2a2d3e; border-radius: 9px;
    padding: 8px; selection-background-color: #6366f1;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #6366f1; }

QComboBox { background: #161826; border: 1px solid #2a2d3e; border-radius: 9px; padding: 6px 10px; }
QComboBox QAbstractItemView { background: #161826; border: 1px solid #2a2d3e; selection-background-color: #6366f1; }

QListWidget { background: #141622; border: 1px solid #242737; border-radius: 10px; padding: 4px; }
QListWidget::item { padding: 9px; border-radius: 7px; }
QListWidget::item:selected { background: rgba(99,102,241,0.25); color: #fff; }

QRadioButton { padding: 4px 2px; spacing: 6px; }
QCheckBox { padding: 4px 2px; spacing: 6px; }

QLabel#h1 { font-size: 19px; font-weight: 700; color: #ffffff; }
QLabel#muted { color: #8b93a7; }
QLabel#pill {
    background: rgba(99,102,241,0.15); color: #c7d2fe;
    border-radius: 10px; padding: 3px 10px; font-weight: 600;
}

QTextBrowser { background: #12131c; border: 1px solid #242737; border-radius: 10px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #333854; border-radius: 5px; min-height: 26px; }
QScrollBar::handle:vertical:hover { background: #41476a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 0; }

QProgressBar { border: none; background: transparent; max-height: 3px; }
QProgressBar::chunk { background: #6366f1; }
"""


def apply_theme(app):
    app.setStyleSheet(QSS)
