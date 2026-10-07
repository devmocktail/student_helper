"""
Quick check that your Gemini API key works.

It reads the key from the GEMINI_API_KEY environment variable (or GOOGLE_API_KEY),
sends one tiny text request, and tells you whether the key and model are good -
without touching screenshots or the GUI.

Run:  python test_key.py
"""

import os
import sys

from google import genai

try:
    from study_helper import load_key_file, DEFAULT_MODEL
except Exception:
    def load_key_file():
        return ""
    DEFAULT_MODEL = "gemini-2.5-flash"

MODEL = DEFAULT_MODEL  # uses the same default model as the app


def main():
    key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or load_key_file()
    )
    if not key:
        print("No key found. Put your AIzaSy... key in api_key.txt, or set it:")
        print('    setx GEMINI_API_KEY "AIzaSy-your-real-key-here"')
        sys.exit(1)

    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=MODEL,
            contents="Reply with exactly: OK",
        )
        print("Success! The API answered:", (resp.text or "").strip())
        print("Your key and the model '" + MODEL + "' are working.")
    except Exception as exc:
        print("The request failed. Most likely the key is wrong/revoked,")
        print("or the model name is not available to your account.\n")
        print("Error:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
