# StudyHelper (PySide6)

A practice-time study tutor and mock-interview coach. Capture a practice
problem and learn the solution, let the app interview you and coach your
answers, and review everything with spaced-repetition flashcards.

> For self-study and practice — **not** for use during live graded or proctored
> exams or interviews. The window is a normal, visible window.

## Install

```bash
pip install -r requirements.txt
```

Optional voice (spoken questions / spoken answers in Mock Interview):

```bash
pip install SpeechRecognition pyttsx3 PyAudio
```

## Run

```bash
python -m app.main
```

or double-click `run_studyhelper.bat`.

## Setup

1. Put your Gemini API key in **Settings** (saved to `api_key.txt`, which is
   git-ignored), or set the `GEMINI_API_KEY` environment variable.
2. On the **Practice** page, click *Load resume…* to personalise questions and
   feedback (PDF / DOCX / TXT). The resume stays loaded for the whole session.

## Pages

- **Practice** — Capture a region (or full screen) of a practice problem; get a
  full explanation, hints only, a code walk-through, or a debug fix. Turn any
  answer into flashcards with one click.
- **Mock Interview** — The app asks you an interview question (tailored to your
  resume and a chosen focus), you answer by typing or voice, and it scores and
  coaches you with a model answer and a follow-up.
- **Flashcards** — SM-2 spaced repetition. Grade each card Again / Hard / Good /
  Easy and it schedules the next review.
- **History** — Every answer and feedback session, saved and searchable.
- **Settings** — API key, model, and where your data lives (`~/.studyhelper`).

## Notes

- Data (history + flashcards) is stored in `~/.studyhelper/studyhelper.db`.
- Window transparency/opacity is cosmetic only; the window is fully visible in a
  screen share.
- The original single-file `study_helper.py` (tkinter) is unchanged and still
  works.
