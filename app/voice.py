"""Optional voice support for the mock-interview page.

Everything here degrades gracefully: if the optional packages aren't installed,
the UI falls back to typing. Install with:
    pip install SpeechRecognition pyttsx3 PyAudio
"""


def tts_available():
    try:
        import pyttsx3  # noqa: F401
        return True
    except Exception:
        return False


def stt_available():
    try:
        import speech_recognition  # noqa: F401
        return True
    except Exception:
        return False


def speak(text):
    """Speak text aloud (blocking). Call from a worker thread."""
    import pyttsx3

    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    try:
        engine.stop()
    except Exception:
        pass


def listen(timeout=15, phrase_time_limit=120):
    """Record from the mic and return the transcribed text. Worker thread only."""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(
            source, timeout=timeout, phrase_time_limit=phrase_time_limit
        )
    # Uses Google's free web speech API (no key needed, needs internet).
    return recognizer.recognize_google(audio)
