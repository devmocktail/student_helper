"""
List the Gemini models your API key can use.

Run:  python list_models.py

Any model shown here can be typed into the "Model" box in the app (use the
short name, e.g. gemini-2.5-flash) to switch which model answers your questions.
"""

import sys

from google import genai

try:
    from study_helper import load_key_file, DEFAULT_MODEL
except Exception:
    def load_key_file():
        return ""
    DEFAULT_MODEL = "gemini-2.5-flash"


def main():
    key = load_key_file()
    if not key:
        print("No key found in api_key.txt. Put your key there first.")
        sys.exit(1)

    client = genai.Client(api_key=key)
    print("Models your key can use for answering (generateContent):\n")
    found = []
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" in actions:
            short = m.name.split("/")[-1]
            found.append(short)
            marker = "   <-- app default" if short == DEFAULT_MODEL else ""
            print(f"  {short:34s}{getattr(m, 'display_name', '')}{marker}")

    print("\nThe app is currently set to:", DEFAULT_MODEL)
    if DEFAULT_MODEL not in found:
        print("(Note: that default was not in the list - pick one from above.)")
    print('Type any name above into the "Model" box in the app to switch.')


if __name__ == "__main__":
    main()
