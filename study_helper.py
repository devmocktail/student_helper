"""
Study Helper - a practice-time tutor.

Capture a coding problem or multiple-choice question from your screen while
you are PRACTICING, and Gemini will explain the concepts and walk through the
solution so you learn how to solve it yourself.

This is a normal, visible desktop window. It is meant for self-study with
practice problems - not for use during live graded or proctored exams.
"""

import io
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ---------------------------------------------------------------------------
# Dependencies (installed via requirements.txt). We import them inside a guard
# so the window can still open and show a helpful message if something is
# missing, instead of crashing on launch.
# ---------------------------------------------------------------------------
try:
    import mss
    from PIL import Image
    from google import genai
    from google.genai import types
    _DEPS_OK = True
    _DEPS_ERR = ""
except Exception as exc:  # pragma: no cover - only hit when deps are missing
    _DEPS_OK = False
    _DEPS_ERR = repr(exc)

# Change this if you want a different Gemini model. You can also change it live
# in the "Model" box in the app, or run list_models.py to see every model your
# key can use. NOTE: the "pro" models (gemini-pro-latest / gemini-3.x-pro) are
# NOT in Google's free tier, so a free key gets a 429 "quota" error on them.
# Flash models ARE free. Good free choices: gemini-2.5-flash, gemini-flash-latest.
DEFAULT_MODEL = "gemini-2.5-flash"

# The app reads your API key automatically from api_key.txt (next to this
# script) so you never have to type it in the window. Paste your key into that
# file once. Keeping it in its own file - instead of inside the code - means you
# can share or back up the script without leaking the key, and swap keys easily.
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_key.txt")
_KEY_PLACEHOLDER = "PASTE-YOUR-AIzaSy-KEY-HERE"


def load_key_file():
    """Return the API key stored in api_key.txt, or '' if it is not set yet."""
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and line != _KEY_PLACEHOLDER:
                    return line
    except OSError:
        pass
    return ""


# ---------------------------------------------------------------------------
# Prompts - the whole tool is framed around teaching, not just answering.
# ---------------------------------------------------------------------------
TUTOR_PROMPT = """You are a patient, encouraging computer science tutor helping a student who is PRACTICING. \
The attached screenshot contains a coding problem or a multiple-choice question.

Respond in Markdown with this structure:

1. **Problem** - Restate the problem in your own words in 1-2 sentences so I know you read it correctly. If the image is unclear or contains no question, say so instead of guessing.
2. **Key ideas** - The concepts and the general approach needed, explained simply.
3. **Step by step** - Walk through the reasoning used to reach the solution.
4. **Solution** - If it is code: a clean, well-commented solution, followed by its time and space complexity. If it is a multiple-choice question: state the correct option, explain why it is right, and briefly why each other option is wrong.
5. **Remember this** - One takeaway that helps with similar problems in the future.

Teach the reasoning so I could solve the next one on my own."""

HINT_PROMPT = """You are a patient computer science tutor helping a student who is PRACTICING. \
The attached screenshot contains a coding problem or a multiple-choice question.

Do NOT give the final answer or the full code. Instead respond in Markdown with:

1. **Problem** - Restate it briefly so I know you read it correctly.
2. **Where to start** - The first thing I should think about.
3. **Hints** - 2 to 4 progressively stronger hints toward the approach, but stop before revealing the actual answer.
4. **Check yourself** - A question I should be able to answer once I am on the right track.

Your goal is to help me figure it out myself, not to hand me the solution."""

CODE_ONLY_PROMPT = """The attached screenshot contains a coding problem or a multiple-choice question.

Give ONLY the answer - no explanation, no restating the problem, no headings:
- Coding problem: output just the complete solution inside a single code block. Keep comments minimal. Use the same programming language shown in the image; if none is shown, use Python.
- Multiple-choice question: output just the correct option (its letter and text). If several are correct, list them.

Do not add reasoning or any extra commentary."""

FIX_PROMPT = """The attached screenshot shows code that is failing - it may contain an error message, a compiler error, a runtime exception, and/or failing test cases, usually along with the code and the problem.

Work out what is wrong and give a corrected, complete, working solution.

Output ONLY the corrected solution inside a single code block, in the same programming language shown. Put one short comment at the very top of the code naming what was wrong and what you changed. Do not add any other explanation, headings, or commentary."""


# ---------------------------------------------------------------------------
# Screen capture helpers
# ---------------------------------------------------------------------------
def capture_fullscreen():
    """Grab the whole primary monitor as a PIL image."""
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def capture_region(bbox):
    """Grab a (left, top, right, bottom) region as a PIL image."""
    left, top, right, bottom = bbox
    region = {
        "left": int(left),
        "top": int(top),
        "width": int(right - left),
        "height": int(bottom - top),
    }
    with mss.mss() as sct:
        raw = sct.grab(region)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def img_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------
def ask_gemini(api_key, model, mode, png_bytes):
    if not _DEPS_OK:
        raise RuntimeError(
            "Required packages are not installed.\n\n"
            "Run:  pip install -r requirements.txt\n\n"
            "Details: " + _DEPS_ERR
        )
    key = (
        api_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or load_key_file()
    )
    if not key:
        raise RuntimeError(
            "No Gemini API key found. Paste your key into api_key.txt "
            "(next to this script), or into the API key box, or set the "
            "GEMINI_API_KEY environment variable."
        )
    client = genai.Client(api_key=key)
    prompt = {
        "hint": HINT_PROMPT,
        "code": CODE_ONLY_PROMPT,
        "fix": FIX_PROMPT,
    }.get(mode, TUTOR_PROMPT)
    part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
    resp = client.models.generate_content(
        model=model or DEFAULT_MODEL,
        contents=[prompt, part],
    )
    return (resp.text or "").strip()


# ---------------------------------------------------------------------------
# Drag-to-select a screen region (a translucent fullscreen overlay)
# ---------------------------------------------------------------------------
class RegionSelector:
    def __init__(self, root):
        self.root = root
        self.bbox = None

    def select(self):
        """Show the overlay and return (left, top, right, bottom) or None."""
        self.bbox = None
        top = tk.Toplevel(self.root)
        top.attributes("-fullscreen", True)
        top.attributes("-alpha", 0.25)
        top.attributes("-topmost", True)
        top.configure(cursor="cross", bg="black")

        canvas = tk.Canvas(top, highlightthickness=0, bg="black")
        canvas.pack(fill="both", expand=True)
        canvas.create_text(
            canvas.winfo_screenwidth() // 2, 40,
            text="Drag a box around the problem.  Press Esc to cancel.",
            fill="#cfe3ff", font=("Segoe UI", 14),
        )

        state = {"sx": 0, "sy": 0, "cx": 0, "cy": 0, "rect": None}

        def on_down(e):
            state["sx"], state["sy"] = e.x_root, e.y_root
            state["cx"], state["cy"] = e.x, e.y
            state["rect"] = canvas.create_rectangle(
                e.x, e.y, e.x, e.y, outline="#4ea1ff", width=2
            )

        def on_move(e):
            if state["rect"] is not None:
                canvas.coords(state["rect"], state["cx"], state["cy"], e.x, e.y)

        def on_up(e):
            left, right = sorted((state["sx"], e.x_root))
            top_, bottom = sorted((state["sy"], e.y_root))
            if right - left > 5 and bottom - top_ > 5:
                self.bbox = (left, top_, right, bottom)
            top.destroy()

        canvas.bind("<ButtonPress-1>", on_down)
        canvas.bind("<B1-Motion>", on_move)
        canvas.bind("<ButtonRelease-1>", on_up)
        top.bind("<Escape>", lambda e: top.destroy())
        top.focus_force()
        self.root.wait_window(top)
        return self.bbox


# ---------------------------------------------------------------------------
# Look and feel
# ---------------------------------------------------------------------------
BG = "#eef1f6"          # window background
CARD = "#ffffff"        # panel background
INK = "#1b1f27"         # primary text
MUTED = "#5b6472"       # secondary text
ACCENT = "#4f46e5"      # indigo accent
ACCENT_DK = "#4338ca"   # accent, pressed
BORDER = "#d7dce4"
CODE_BG = "#f3f4f8"

FONT = ("Segoe UI", 10)
FONT_SEMI = ("Segoe UI Semibold", 10)

_INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_NUMBER_RE = re.compile(r"^(\s*)(\d+[.)])\s+(.*)$")


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.selector = RegionSelector(root)
        self.api_key = tk.StringVar(
            value=os.environ.get("GEMINI_API_KEY", "") or load_key_file()
        )
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.mode = tk.StringVar(value="explain")
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg=BG)
        style.configure(".", background=BG, foreground=INK, font=FONT)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=INK, font=FONT)
        style.configure("Card.TLabel", background=CARD, foreground=INK, font=FONT)
        style.configure("CardHint.TLabel", background=CARD, foreground=MUTED, font=FONT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT)

        style.configure(
            "TEntry", fieldbackground=CARD, foreground=INK, padding=6,
            bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", ACCENT)],
            lightcolor=[("focus", ACCENT)],
            darkcolor=[("focus", ACCENT)],
        )

        style.configure("TButton", background="#e3e7ef", foreground=INK,
                        font=FONT_SEMI, padding=(12, 7), borderwidth=0)
        style.map("TButton", background=[("active", "#d4dae4")])

        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                        font=FONT_SEMI, padding=(16, 8), borderwidth=0)
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_DK), ("disabled", "#bdbbe8")],
            foreground=[("disabled", "#f0eefc")],
        )

        style.configure("TRadiobutton", background=BG, foreground=INK, font=FONT)
        style.map("TRadiobutton", foreground=[("selected", ACCENT)],
                  background=[("active", BG)])

        style.configure("Accent.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor="#dde2ea",
                        bordercolor="#dde2ea", lightcolor=ACCENT, darkcolor=ACCENT)

    def _build_ui(self):
        self.root.title("Study Helper")
        self.root.geometry("920x700")
        self.root.minsize(720, 540)
        self._setup_styles()

        # --- header ---
        header = tk.Frame(self.root, bg=ACCENT)
        header.pack(fill="x")
        tk.Label(header, text="Study Helper", bg=ACCENT, fg="#ffffff",
                 font=("Segoe UI Semibold", 17)).pack(anchor="w", padx=20, pady=(14, 0))
        tk.Label(header, text="Practice tutor - capture a problem, learn the solution",
                 bg=ACCENT, fg="#d8d6fb", font=("Segoe UI", 10)).pack(
                     anchor="w", padx=20, pady=(1, 14))

        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=18, pady=16)

        # --- settings card ---
        card = ttk.Frame(body, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        ttk.Label(card, text="Gemini API key", style="Card.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.api_key, show="•").grid(
            row=1, column=0, sticky="we", padx=(0, 14), pady=(3, 0))
        ttk.Label(card, text="Model", style="Card.TLabel").grid(
            row=0, column=1, sticky="w")
        ttk.Entry(card, textvariable=self.model, width=22).grid(
            row=1, column=1, sticky="we", pady=(3, 0))
        hint = ("Key loaded from api_key.txt"
                if self.api_key.get() else
                "Paste your key here, or save it in api_key.txt")
        ttk.Label(card, text=hint, style="CardHint.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        card.columnconfigure(0, weight=3)
        card.columnconfigure(1, weight=2)

        # --- mode row ---
        mode_row = ttk.Frame(body)
        mode_row.pack(fill="x", pady=(16, 8))
        ttk.Label(mode_row, text="Mode").pack(side="left", padx=(0, 10))
        for label, value in (
            ("Explain fully", "explain"),
            ("Hints only", "hint"),
            ("Just the code", "code"),
            ("Fix the error", "fix"),
        ):
            ttk.Radiobutton(
                mode_row, text=label, variable=self.mode, value=value
            ).pack(side="left", padx=(0, 12))

        # --- action buttons ---
        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(0, 12))
        self.btn_region = ttk.Button(
            btns, text="Capture a region", style="Accent.TButton",
            command=lambda: self.capture(full=False))
        self.btn_region.pack(side="left")
        self.btn_full = ttk.Button(
            btns, text="Full screen", command=lambda: self.capture(full=True))
        self.btn_full.pack(side="left", padx=8)
        self.btn_copy = ttk.Button(btns, text="Copy answer", command=self.copy_output)
        self.btn_copy.pack(side="right")

        # --- output (thin border via a 1px wrapper frame) ---
        out_wrap = tk.Frame(body, bg=BORDER)
        out_wrap.pack(fill="both", expand=True)
        self.output = scrolledtext.ScrolledText(
            out_wrap, wrap="word", state="disabled",
            font=("Segoe UI", 11), fg=INK, bg=CARD,
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=16, pady=14, insertbackground=INK,
        )
        self.output.pack(fill="both", expand=True, padx=1, pady=1)
        self._configure_text_tags()
        self._set_output(
            "Modes\n"
            "    Explain fully / Hints only / Just the code\n"
            "    Fix the error - capture a failing run (your code + the error) "
            "to get a corrected solution\n\n"
            "How to use\n"
            "    1. Pick a mode above.\n"
            "    2. Click \"Capture a region\" and drag a box around the problem "
            "(or the error).\n"
            "    3. Read the result here.  \"Copy answer\" copies it.\n\n"
            "Meant for practicing on your own - not for live graded or proctored exams."
        )

        # --- status bar ---
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", side="bottom", padx=18, pady=(0, 14))
        self.status = ttk.Label(bar, text="Ready.", style="Muted.TLabel")
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(
            bar, mode="indeterminate", length=170,
            style="Accent.Horizontal.TProgressbar")
        self.progress.pack(side="right")

    # --- output rendering -------------------------------------------------
    def _configure_text_tags(self):
        o = self.output
        o.tag_configure("body", font=("Segoe UI", 11), foreground=INK,
                        spacing1=2, spacing3=3)
        o.tag_configure("h1", font=("Segoe UI Semibold", 16), foreground=INK,
                        spacing1=10, spacing3=6)
        o.tag_configure("h2", font=("Segoe UI Semibold", 13), foreground=INK,
                        spacing1=9, spacing3=4)
        o.tag_configure("h3", font=("Segoe UI Semibold", 11), foreground=ACCENT,
                        spacing1=7, spacing3=3)
        # List items: one tag per indent level so nested lists keep their own
        # hanging indent (wrapped lines line up under the text, not the marker).
        # Created before "bold"/"icode" so those still win on inline **bold** /
        # `code` inside a list item.
        for _lvl in range(4):
            o.tag_configure(
                "list%d" % _lvl, font=("Segoe UI", 11), foreground=INK,
                lmargin1=16 + _lvl * 22, lmargin2=16 + _lvl * 22 + 20,
                spacing1=2, spacing3=2,
            )
        o.tag_configure("bold", font=("Segoe UI", 11, "bold"))
        o.tag_configure("icode", font=("Consolas", 10), background="#e9ecf3")
        o.tag_configure("codeblock", font=("Consolas", 10), background=CODE_BG,
                        lmargin1=14, lmargin2=14, spacing1=1, spacing3=1)

    def _insert_inline(self, text, base):
        for part in _INLINE_RE.split(text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                self.output.insert("end", part[2:-2], (base, "bold"))
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                self.output.insert("end", part[1:-1], (base, "icode"))
            else:
                self.output.insert("end", part, base)

    def _render_markdown(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        try:
            in_code = False
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    self.output.insert("end", line + "\n", "codeblock")
                elif stripped.startswith("### "):
                    self._insert_inline(stripped[4:], "h3")
                    self.output.insert("end", "\n")
                elif stripped.startswith("## "):
                    self._insert_inline(stripped[3:], "h2")
                    self.output.insert("end", "\n")
                elif stripped.startswith("# "):
                    self._insert_inline(stripped[2:], "h1")
                    self.output.insert("end", "\n")
                elif (m := _BULLET_RE.match(line)):
                    tag = "list%d" % min(len(m.group(1)) // 2, 3)
                    self.output.insert("end", "•  ", tag)
                    self._insert_inline(m.group(2), tag)
                    self.output.insert("end", "\n")
                elif (m := _NUMBER_RE.match(line)):
                    tag = "list%d" % min(len(m.group(1)) // 2, 3)
                    self.output.insert("end", m.group(2) + "  ", tag)
                    self._insert_inline(m.group(3), tag)
                    self.output.insert("end", "\n")
                else:
                    self._insert_inline(line, "body")
                    self.output.insert("end", "\n")
        except Exception:
            self.output.delete("1.0", "end")
            self.output.insert("1.0", text, "body")
        self.output.configure(state="disabled")

    # --- capture flow -----------------------------------------------------
    def capture(self, full=False):
        if not _DEPS_OK:
            messagebox.showerror(
                "Missing packages",
                "Required packages are not installed.\n\n"
                "Run:  pip install -r requirements.txt\n\nDetails: " + _DEPS_ERR,
            )
            return

        if full:
            self.root.iconify()
            self.root.after(250, lambda: self._grab_and_send(None))
        else:
            bbox = self.selector.select()
            if not bbox:
                self.set_status("Selection cancelled.")
                return
            self.root.iconify()
            self.root.after(250, lambda: self._grab_and_send(bbox))

    def _grab_and_send(self, bbox):
        try:
            img = capture_fullscreen() if bbox is None else capture_region(bbox)
        except Exception as exc:
            self.root.deiconify()
            self.set_status("Capture failed.")
            messagebox.showerror("Capture failed", str(exc))
            return
        self.root.deiconify()

        png = img_to_png_bytes(img)
        self.set_status("Asking Gemini...")
        self.set_busy(True)
        threading.Thread(target=self._worker, args=(png,), daemon=True).start()

    def _worker(self, png):
        try:
            text = ask_gemini(
                self.api_key.get().strip(),
                self.model.get().strip(),
                self.mode.get(),
                png,
            )
            self.root.after(0, lambda: self._done(text, None))
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda: self._done(None, msg))

    def _done(self, text, err):
        self.set_busy(False)
        if err:
            self.set_status("Error.")
            messagebox.showerror("Gemini error", err)
            return
        self._render_markdown(text or "(empty response)")
        self.set_status("Done.")

    # --- small helpers ----------------------------------------------------
    def copy_output(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output.get("1.0", "end").strip())
        self.set_status("Copied to clipboard.")

    def _set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def set_status(self, text):
        self.status.configure(text=text)

    def set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_region.configure(state=state)
        self.btn_full.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()


def main():
    # On Windows, tell the OS we handle our own scaling so the region we draw
    # lines up with the pixels the screenshot grabs under display scaling.
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
