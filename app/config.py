"""Configuration, API-key loading, and lightweight settings persistence.

The API key is read from (in order):
  1. the GEMINI_API_KEY / GOOGLE_API_KEY environment variable
  2. api_key.txt next to the project (already in .gitignore)
Settings and the study database live in ~/.studyhelper so they survive updates
and never end up in the repo.
"""

import json
import os
import sys

# Project root. When frozen into an .exe (PyInstaller), look next to the
# executable so api_key.txt lives alongside StudyHelper.exe; otherwise use the
# source tree.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(BASE_DIR, "api_key.txt")
_KEY_PLACEHOLDER = "PASTE-YOUR-AIzaSy-KEY-HERE"

APP_DIR = os.path.join(os.path.expanduser("~"), ".studyhelper")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
DB_FILE = os.path.join(APP_DIR, "studyhelper.db")

# Flash models are on Google's free tier; "pro" models are not.
DEFAULT_MODEL = "gemini-2.5-flash"


def ensure_app_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def load_key():
    """Return the Gemini API key, or '' if none is configured yet."""
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and line != _KEY_PLACEHOLDER:
                    return line
    except OSError:
        pass
    return ""


def save_key(key):
    """Persist the key to api_key.txt (which is git-ignored)."""
    try:
        with open(KEY_FILE, "w", encoding="utf-8") as fh:
            fh.write(key.strip() + "\n")
        return True
    except OSError:
        return False


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_settings(data):
    ensure_app_dir()
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except Exception:
        pass
