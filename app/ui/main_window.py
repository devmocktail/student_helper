"""The StudyHelper main window: a frameless, translucent PySide6 app.

Pages: Practice (capture a problem -> learn it), Mock Interview (the app
interviews you and coaches your spoken/typed answers), Flashcards (SM-2 spaced
repetition), History, and Settings.
"""

import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QRadioButton, QSizeGrip, QSlider,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    QGraphicsDropShadowEffect, QMessageBox,
)
from PySide6.QtGui import QColor

from app import capture, config, flashcards, gemini_client, resume, storage, voice
from app.prompts import (
    COACH_PROMPT, FLASHCARD_PROMPT, MOCK_QUESTION_PROMPT, PRACTICE_PROMPTS,
)
from app.ui.markdown_view import MarkdownView
from app.ui.region_selector import select_region
from app.workers import CompleteWorker, ListenWorker, SpeakWorker, StreamWorker


class TitleBar(QFrame):
    """Draggable custom title bar for the frameless window."""

    def __init__(self, window):
        super().__init__()
        self.setObjectName("titlebar")
        self._window = window
        self._drag = None
        self.setFixedHeight(52)
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(16, 8, 12, 8)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag = None


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = []
        self._settings = config.load_settings()
        self.model = self._settings.get("model", config.DEFAULT_MODEL)

        # Session state carried across pages.
        self.resume_text = ""
        self.resume_name = ""
        self._last_answer = ""
        self._current_question = ""
        self._due = []
        self._current_card = None

        self.setWindowTitle("StudyHelper")
        self.setMinimumSize(1040, 720)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)  # room for the drop shadow

        self.root = QFrame()
        self.root.setObjectName("root")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 170))
        shadow.setOffset(0, 8)
        self.root.setGraphicsEffect(shadow)
        outer.addWidget(self.root)

        root_l = QVBoxLayout(self.root)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.setSpacing(0)

        root_l.addWidget(self._build_titlebar())

        body = QHBoxLayout()
        body.setContentsMargins(14, 6, 14, 10)
        body.setSpacing(14)
        body.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._page_practice())
        self.pages.addWidget(self._page_interview())
        self.pages.addWidget(self._page_flashcards())
        self.pages.addWidget(self._page_history())
        self.pages.addWidget(self._page_settings())
        body.addWidget(self.pages, 1)
        root_l.addLayout(body, 1)

        root_l.addWidget(self._build_statusbar())
        self._select_nav(0)

    def _build_titlebar(self):
        bar = TitleBar(self)
        lay = bar.layout_

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("StudyHelper")
        t.setObjectName("appTitle")
        s = QLabel("Practice tutor & mock-interview coach")
        s.setObjectName("appSub")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        lay.addWidget(QLabel("Opacity"))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setFixedWidth(120)
        self.opacity.setRange(45, 100)
        self.opacity.setValue(100)
        self.opacity.valueChanged.connect(lambda v: self.setWindowOpacity(v / 100))
        lay.addWidget(self.opacity)

        self.on_top = QCheckBox("Stay on top")
        self.on_top.toggled.connect(self._toggle_on_top)
        lay.addWidget(self.on_top)

        mn = QPushButton("–")
        mn.setObjectName("winbtn")
        mn.clicked.connect(self.showMinimized)
        cl = QPushButton("✕")
        cl.setObjectName("winbtn")
        cl.setProperty("class", "winclose")
        cl.setObjectName("winclose")
        cl.clicked.connect(self.close)
        lay.addSpacing(6)
        lay.addWidget(mn)
        lay.addWidget(cl)
        return bar

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(190)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(4)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for i, (label, _) in enumerate([
            ("  Practice", 0), ("  Mock Interview", 1), ("  Flashcards", 2),
            ("  History", 3), ("  Settings", 4),
        ]):
            b = QPushButton(label)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, idx=i: self._select_nav(idx))
            self.nav_group.addButton(b, i)
            lay.addWidget(b)
        lay.addStretch(1)

        self.side_stats = QLabel("")
        self.side_stats.setObjectName("muted")
        self.side_stats.setWordWrap(True)
        lay.addWidget(self.side_stats)
        return side

    def _build_statusbar(self):
        bar = QFrame()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 10, 10)
        self.status = QLabel("Ready.")
        self.status.setObjectName("muted")
        lay.addWidget(self.status)
        lay.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setFixedWidth(150)
        self.progress.hide()
        lay.addWidget(self.progress)
        lay.addWidget(QSizeGrip(self))
        return bar

    # ------------------------------------------------------------- page: practice
    def _page_practice(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)

        head = QHBoxLayout()
        h = QLabel("Practice")
        h.setObjectName("h1")
        head.addWidget(h)
        head.addStretch(1)
        self.resume_pill = QLabel("No resume loaded")
        self.resume_pill.setObjectName("pill")
        head.addWidget(self.resume_pill)
        load = QPushButton("Resume (paste)…")
        load.clicked.connect(self._edit_resume)
        head.addWidget(load)
        lay.addLayout(head)

        # mode row
        modes = QHBoxLayout()
        modes.addWidget(QLabel("Mode"))
        self.mode_group = QButtonGroup(self)
        self._practice_mode = "explain"
        for label, key, checked in [
            ("Explain fully", "explain", True), ("Hints only", "hint", False),
            ("Learn this code", "learn", False), ("Fix the error", "fix", False),
        ]:
            rb = QRadioButton(label)
            rb.setChecked(checked)
            rb.toggled.connect(lambda on, k=key: self._set_mode(k) if on else None)
            self.mode_group.addButton(rb)
            modes.addWidget(rb)
        modes.addStretch(1)
        self.use_resume_practice = QCheckBox("Use my resume for context")
        modes.addWidget(self.use_resume_practice)
        lay.addLayout(modes)

        # actions
        actions = QHBoxLayout()
        self.btn_region = QPushButton("Capture a region")
        self.btn_region.setObjectName("accent")
        self.btn_region.clicked.connect(self._start_region_capture)
        self.btn_full = QPushButton("Full screen")
        self.btn_full.clicked.connect(self._start_full_capture)
        actions.addWidget(self.btn_region)
        actions.addWidget(self.btn_full)
        actions.addStretch(1)
        self.btn_cards_from = QPushButton("Make flashcards from this")
        self.btn_cards_from.clicked.connect(self._cards_from_last)
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.clicked.connect(lambda: self._copy(self.practice_output))
        actions.addWidget(self.btn_cards_from)
        actions.addWidget(self.btn_copy)
        lay.addLayout(actions)

        self.practice_output = MarkdownView()
        self.practice_output.set_markdown(
            "### Welcome\n"
            "Pick a mode, then **Capture a region** and drag a box around a "
            "practice problem. The tutor explains the solution so you learn it.\n\n"
            "_For self-study and practice - not for live graded or proctored exams._"
        )
        lay.addWidget(self.practice_output, 1)
        return page

    # ------------------------------------------------------------ page: interview
    def _page_interview(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        head = QHBoxLayout()
        h = QLabel("Mock Interview")
        h.setObjectName("h1")
        head.addWidget(h)
        head.addStretch(1)
        head.addWidget(QLabel("Focus"))
        self.iv_focus = QComboBox()
        self.iv_focus.addItems([
            "General", "Behavioral", "Technical / Coding",
            "System design", "Role-specific (from resume)",
        ])
        head.addWidget(self.iv_focus)
        lay.addLayout(head)

        sub = QLabel(
            "The app plays the interviewer: it asks you a question, you answer "
            "(type or speak), and it coaches you. Paste your resume text on the "
            "Practice page (Resume button) for tailored questions."
        )
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        qrow = QHBoxLayout()
        self.btn_new_q = QPushButton("Ask me a question")
        self.btn_new_q.setObjectName("accent")
        self.btn_new_q.clicked.connect(self._new_question)
        qrow.addWidget(self.btn_new_q)
        self.btn_speak_q = QPushButton("Speak question")
        self.btn_speak_q.clicked.connect(self._speak_question)
        self.btn_speak_q.setEnabled(voice.tts_available())
        qrow.addWidget(self.btn_speak_q)
        qrow.addStretch(1)
        lay.addLayout(qrow)

        self.iv_question = MarkdownView()
        self.iv_question.setMaximumHeight(130)
        self.iv_question.set_markdown("_Click **Ask me a question** to begin._")
        lay.addWidget(self.iv_question)

        lay.addWidget(QLabel("Your answer"))
        self.iv_answer = QTextEdit()
        self.iv_answer.setPlaceholderText("Type your answer here, or use 'Answer by voice'.")
        self.iv_answer.setMaximumHeight(130)
        lay.addWidget(self.iv_answer)

        arow = QHBoxLayout()
        self.btn_voice_ans = QPushButton("Answer by voice")
        self.btn_voice_ans.clicked.connect(self._answer_by_voice)
        self.btn_voice_ans.setEnabled(voice.stt_available())
        if not voice.stt_available():
            self.btn_voice_ans.setToolTip(
                "Install voice support: pip install SpeechRecognition pyttsx3 PyAudio"
            )
        arow.addWidget(self.btn_voice_ans)
        arow.addStretch(1)
        self.btn_feedback = QPushButton("Get feedback")
        self.btn_feedback.setObjectName("accent")
        self.btn_feedback.clicked.connect(self._get_feedback)
        arow.addWidget(self.btn_feedback)
        lay.addLayout(arow)

        self.iv_feedback = MarkdownView()
        lay.addWidget(self.iv_feedback, 1)
        return page

    # ----------------------------------------------------------- page: flashcards
    def _page_flashcards(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        head = QHBoxLayout()
        h = QLabel("Flashcards")
        h.setObjectName("h1")
        head.addWidget(h)
        head.addStretch(1)
        self.fc_due_lbl = QLabel("")
        self.fc_due_lbl.setObjectName("pill")
        head.addWidget(self.fc_due_lbl)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._refresh_due)
        head.addWidget(refresh)
        lay.addLayout(head)

        self.fc_front = MarkdownView()
        self.fc_front.setMaximumHeight(150)
        lay.addWidget(self.fc_front)
        self.fc_back = MarkdownView()
        lay.addWidget(self.fc_back, 1)

        grade = QHBoxLayout()
        self.btn_reveal = QPushButton("Show answer")
        self.btn_reveal.setObjectName("accent")
        self.btn_reveal.clicked.connect(self._reveal_card)
        grade.addWidget(self.btn_reveal)
        grade.addStretch(1)
        self._grade_btns = []
        for label in ("Again", "Hard", "Good", "Easy"):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, lb=label: self._grade_card(lb))
            b.setEnabled(False)
            self._grade_btns.append(b)
            grade.addWidget(b)
        lay.addLayout(grade)

        # all cards
        lay.addWidget(QLabel("All cards"))
        self.fc_list = QListWidget()
        self.fc_list.setMaximumHeight(140)
        lay.addWidget(self.fc_list)
        crow = QHBoxLayout()
        crow.addStretch(1)
        delb = QPushButton("Delete selected")
        delb.clicked.connect(self._delete_card)
        crow.addWidget(delb)
        lay.addLayout(crow)
        return page

    # ------------------------------------------------------------- page: history
    def _page_history(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        head = QHBoxLayout()
        h = QLabel("History")
        h.setObjectName("h1")
        head.addWidget(h)
        head.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._refresh_history)
        head.addWidget(refresh)
        lay.addLayout(head)

        split = QHBoxLayout()
        self.hist_list = QListWidget()
        self.hist_list.setFixedWidth(300)
        self.hist_list.currentItemChanged.connect(self._show_history_item)
        split.addWidget(self.hist_list)
        self.hist_view = MarkdownView()
        split.addWidget(self.hist_view, 1)
        lay.addLayout(split, 1)
        return page

    # ------------------------------------------------------------ page: settings
    def _page_settings(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)
        h = QLabel("Settings")
        h.setObjectName("h1")
        lay.addWidget(h)

        lay.addWidget(QLabel("Gemini API key"))
        krow = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setText(config.load_key())
        krow.addWidget(self.key_edit, 1)
        save_key = QPushButton("Save key")
        save_key.clicked.connect(self._save_key)
        krow.addWidget(save_key)
        lay.addLayout(krow)
        hint = QLabel("Saved to api_key.txt (already in .gitignore). Flash models are free; pro models are not.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        lay.addWidget(QLabel("Model"))
        self.model_edit = QLineEdit(self.model)
        self.model_edit.editingFinished.connect(self._save_model)
        lay.addWidget(self.model_edit)

        info = QLabel(
            "Data is stored in ~/.studyhelper (history + flashcards).\n\n"
            "Voice: " + ("available" if (voice.tts_available() and voice.stt_available())
                          else "not installed - run: pip install SpeechRecognition pyttsx3 PyAudio") + "\n\n"
            "Note: window transparency is cosmetic only. This window is still fully "
            "visible in a screen share - it is a study tool, not a hidden overlay."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addStretch(1)
        return page

    # ------------------------------------------------------------------- helpers
    def _select_nav(self, idx):
        self.pages.setCurrentIndex(idx)
        btn = self.nav_group.button(idx)
        if btn:
            btn.setChecked(True)
        if idx == 2:
            self._refresh_due()
            self._refresh_card_list()
        elif idx == 3:
            self._refresh_history()
        self._update_stats()

    def _set_mode(self, key):
        self._practice_mode = key

    def _toggle_on_top(self, on):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()

    def _update_stats(self):
        s = storage.stats()
        self.side_stats.setText(
            f"{s['cards']} cards · {s['due']} due\n{s['history']} saved answers"
        )

    def _set_busy(self, busy, buttons=()):
        self.progress.setVisible(busy)
        for b in buttons:
            b.setEnabled(not busy)
        self.status.setText("Working…" if busy else "Ready.")

    def _cleanup(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    def _copy(self, view):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(view.toPlainText())
        self.status.setText("Copied to clipboard.")

    def _stream(self, parts, view, buttons=(), on_text=None):
        view.clear_markdown()
        acc = {"text": ""}
        worker = StreamWorker(self.model, parts, config.load_key())

        def on_chunk(t):
            acc["text"] += t
            view.append_chunk(t)

        def on_done():
            self._set_busy(False, buttons)
            if on_text:
                on_text(acc["text"])
            self._cleanup(worker)

        def on_fail(msg):
            self._set_busy(False, buttons)
            view.set_markdown("**Error:** " + msg)
            self._cleanup(worker)

        worker.chunk.connect(on_chunk)
        worker.done.connect(on_done)
        worker.failed.connect(on_fail)
        self._workers.append(worker)
        self._set_busy(True, buttons)
        worker.start()

    # ---------------------------------------------------------------- resume
    def _edit_resume(self):
        """Paste resume text directly - no file reading."""
        from PySide6.QtWidgets import QDialog

        dlg = QDialog(self)
        dlg.setWindowTitle("Resume context")
        dlg.setMinimumSize(560, 460)
        v = QVBoxLayout(dlg)
        info = QLabel(
            "Paste your resume / background text here. It stays loaded for this "
            "session and personalises practice help and mock-interview questions."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        v.addWidget(info)

        box = QTextEdit()
        box.setPlaceholderText("Paste your resume text here…")
        box.setPlainText(self.resume_text)
        v.addWidget(box, 1)

        row = QHBoxLayout()
        clear = QPushButton("Clear")
        clear.clicked.connect(box.clear)
        row.addWidget(clear)
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dlg.reject)
        save = QPushButton("Save")
        save.setObjectName("accent")
        save.clicked.connect(dlg.accept)
        row.addWidget(cancel)
        row.addWidget(save)
        v.addLayout(row)

        if dlg.exec():
            self.resume_text = box.toPlainText().strip()
            self._update_resume_pill()
            if self.resume_text:
                self.use_resume_practice.setChecked(True)
                self.status.setText(f"Resume saved ({len(self.resume_text)} chars).")
            else:
                self.status.setText("Resume cleared.")

    def _update_resume_pill(self):
        if self.resume_text:
            self.resume_pill.setText(f"Resume: {len(self.resume_text)} chars")
        else:
            self.resume_pill.setText("No resume")

    # --------------------------------------------------------------- practice
    def _start_region_capture(self):
        self.hide()
        QTimer.singleShot(180, self._region_then_ask)

    def _region_then_ask(self):
        img = None
        try:
            img = select_region()
        finally:
            self.show()
            self.raise_()
            self.activateWindow()
        if img is not None:
            self._run_practice(img)
        else:
            self.status.setText("Capture cancelled.")

    def _start_full_capture(self):
        self.hide()
        QTimer.singleShot(180, self._full_then_ask)

    def _full_then_ask(self):
        try:
            img = capture.capture_primary()
        finally:
            self.show()
        self._run_practice(img)

    def _run_practice(self, img):
        png = capture.to_png_bytes(img)
        prompt = PRACTICE_PROMPTS[self._practice_mode]
        ctx = (resume.condense(self.resume_text)
               if self.use_resume_practice.isChecked() and self.resume_text else None)
        parts = gemini_client.build_parts(prompt, image_png=png, resume_text=ctx)

        def done(text):
            self._last_answer = text
            title = text.strip().splitlines()[0][:70] if text.strip() else "Practice answer"
            storage.add_history(self._practice_mode, title, text)
            self._update_stats()
            self.status.setText("Done.")

        self._stream(parts, self.practice_output,
                     buttons=(self.btn_region, self.btn_full), on_text=done)

    def _cards_from_last(self):
        if not self._last_answer.strip():
            self.status.setText("Capture and get an answer first.")
            return
        parts = gemini_client.build_parts(
            FLASHCARD_PROMPT.format(material=self._last_answer[:6000])
        )
        worker = CompleteWorker(self.model, parts, config.load_key())

        def done(text):
            self._set_busy(False, (self.btn_cards_from,))
            n = self._ingest_cards(text)
            self.status.setText(f"Added {n} flashcard(s).")
            self._update_stats()
            self._cleanup(worker)

        def fail(msg):
            self._set_busy(False, (self.btn_cards_from,))
            self.status.setText("Card generation failed: " + msg)
            self._cleanup(worker)

        worker.done.connect(done)
        worker.failed.connect(fail)
        self._workers.append(worker)
        self._set_busy(True, (self.btn_cards_from,))
        worker.start()

    def _ingest_cards(self, text):
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1] if "```" in raw else raw
            raw = raw.lstrip("json").strip()
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return 0
        try:
            items = json.loads(raw[start:end + 1])
        except Exception:
            return 0
        n = 0
        for it in items:
            front = (it.get("front") or "").strip()
            back = (it.get("back") or "").strip()
            if front and back:
                storage.add_card(front, back)
                n += 1
        return n

    # -------------------------------------------------------------- interview
    def _new_question(self):
        focus = self.iv_focus.currentText()
        prompt = MOCK_QUESTION_PROMPT.format(focus=focus)
        ctx = resume.condense(self.resume_text) if self.resume_text else None
        parts = gemini_client.build_parts(prompt, resume_text=ctx)
        self.iv_answer.clear()
        self.iv_feedback.clear_markdown()

        def done(text):
            self._current_question = text.strip()
            self.status.setText("Your turn - type or speak your answer.")

        self._stream(parts, self.iv_question, buttons=(self.btn_new_q,), on_text=done)

    def _speak_question(self):
        if not self._current_question:
            self.status.setText("Ask a question first.")
            return
        worker = SpeakWorker(self._current_question)
        worker.failed.connect(lambda m: self.status.setText("TTS error: " + m))
        worker.done.connect(lambda: self._cleanup(worker))
        self._workers.append(worker)
        self.status.setText("Speaking…")
        worker.start()

    def _answer_by_voice(self):
        worker = ListenWorker()
        self.btn_voice_ans.setEnabled(False)
        self.status.setText("Listening… speak your answer.")

        def done(text):
            cur = self.iv_answer.toPlainText()
            self.iv_answer.setPlainText((cur + " " + text).strip())
            self.btn_voice_ans.setEnabled(True)
            self.status.setText("Transcribed.")
            self._cleanup(worker)

        def fail(msg):
            self.btn_voice_ans.setEnabled(True)
            self.status.setText("Voice error: " + msg)
            self._cleanup(worker)

        worker.done.connect(done)
        worker.failed.connect(fail)
        self._workers.append(worker)
        worker.start()

    def _get_feedback(self):
        q = self._current_question.strip()
        a = self.iv_answer.toPlainText().strip()
        if not q:
            self.status.setText("Ask a question first.")
            return
        if not a:
            self.status.setText("Write or speak an answer first.")
            return
        ctx = resume.condense(self.resume_text) if self.resume_text else None
        extra = f"INTERVIEW QUESTION:\n{q}\n\nCANDIDATE'S ANSWER:\n{a}"
        parts = gemini_client.build_parts(COACH_PROMPT, resume_text=ctx, extra=extra)

        def done(text):
            storage.add_history("interview", q[:70], text)
            self._update_stats()
            self.status.setText("Feedback ready.")

        self._stream(parts, self.iv_feedback, buttons=(self.btn_feedback,), on_text=done)

    # -------------------------------------------------------------- flashcards
    def _refresh_due(self):
        self._due = list(storage.due_cards())
        self.fc_due_lbl.setText(f"{len(self._due)} due")
        self._next_card()

    def _next_card(self):
        for b in self._grade_btns:
            b.setEnabled(False)
        self.btn_reveal.setEnabled(bool(self._due))
        if not self._due:
            self._current_card = None
            self.fc_front.set_markdown("### All caught up \U0001F389\nNo cards due right now.")
            self.fc_back.set_markdown("")
            return
        self._current_card = self._due[0]
        self.fc_front.set_markdown("**Q.** " + self._current_card["front"])
        self.fc_back.set_markdown("_Answer hidden - click **Show answer**._")

    def _reveal_card(self):
        if not self._current_card:
            return
        self.fc_back.set_markdown("**A.** " + self._current_card["back"])
        for b in self._grade_btns:
            b.setEnabled(True)

    def _grade_card(self, label):
        if not self._current_card:
            return
        q = flashcards.GRADES[label]
        upd = flashcards.review(self._current_card, q)
        storage.update_card(
            self._current_card["id"], upd["interval"], upd["reps"],
            upd["ef"], upd["due"], upd["lapses"],
        )
        if self._due:
            self._due.pop(0)
        self.fc_due_lbl.setText(f"{len(self._due)} due")
        self._update_stats()
        self._refresh_card_list()
        self._next_card()

    def _refresh_card_list(self):
        self.fc_list.clear()
        for row in storage.all_cards():
            item = QListWidgetItem(f"{row['front'][:60]}")
            item.setData(Qt.UserRole, row["id"])
            self.fc_list.addItem(item)

    def _delete_card(self):
        item = self.fc_list.currentItem()
        if not item:
            return
        storage.delete_card(item.data(Qt.UserRole))
        self._refresh_card_list()
        self._refresh_due()
        self._update_stats()

    # ----------------------------------------------------------------- history
    def _refresh_history(self):
        self.hist_list.clear()
        import datetime
        for row in storage.list_history():
            when = datetime.datetime.fromtimestamp(row["created"]).strftime("%b %d %H:%M")
            item = QListWidgetItem(f"[{row['mode']}] {row['title']}\n{when}")
            item.setData(Qt.UserRole, row["answer"])
            self.hist_list.addItem(item)

    def _show_history_item(self, current, _previous):
        if current:
            self.hist_view.set_markdown(current.data(Qt.UserRole) or "")

    # ----------------------------------------------------------------- settings
    def _save_key(self):
        if config.save_key(self.key_edit.text()):
            self.status.setText("API key saved.")
        else:
            self.status.setText("Could not save key.")

    def _save_model(self):
        self.model = self.model_edit.text().strip() or config.DEFAULT_MODEL
        self._settings["model"] = self.model
        config.save_settings(self._settings)
