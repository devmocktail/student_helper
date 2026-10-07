"""A QTextBrowser that renders Markdown with syntax-highlighted code.

Code blocks are highlighted with Pygments (inline styles via noclasses=True so
Qt's limited rich-text CSS renders colors reliably). Supports live streaming:
append chunks and the view re-renders and auto-scrolls.
"""

from PySide6.QtWidgets import QTextBrowser

try:
    import markdown
    _MD = markdown.Markdown(
        extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
        extension_configs={
            "codehilite": {
                "noclasses": True,
                "pygments_style": "monokai",
                "guess_lang": False,
            }
        },
    )
    _MD_OK = True
except Exception:
    _MD = None
    _MD_OK = False

_BASE_CSS = """
body, p, li, td, th { font-family: 'Segoe UI', sans-serif; font-size: 14px; color: #e6e8ef; }
h1 { font-size: 20px; color: #ffffff; }
h2 { font-size: 17px; color: #c7d2fe; }
h3 { font-size: 15px; color: #a5b4fc; }
a  { color: #8ab4ff; }
code { font-family: 'Consolas', 'Cascadia Code', monospace; background: #1f2233;
       padding: 1px 4px; border-radius: 4px; }
pre { background: #15171f; padding: 10px; border-radius: 8px; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; }
th, td { border: 1px solid #2a2d3e; padding: 4px 8px; }
blockquote { color: #9aa3b2; border-left: 3px solid #6366f1; padding-left: 10px; }
"""


class MarkdownView(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.document().setDefaultStyleSheet(_BASE_CSS)
        self._buffer = ""

    def set_markdown(self, text):
        self._buffer = text or ""
        self._render()

    def append_chunk(self, chunk):
        self._buffer += chunk
        self._render(scroll=True)

    def clear_markdown(self):
        self._buffer = ""
        self.setHtml("")

    def _render(self, scroll=False):
        if _MD_OK:
            _MD.reset()
            try:
                html = _MD.convert(self._buffer)
            except Exception:
                html = "<pre>%s</pre>" % _escape(self._buffer)
        else:
            html = "<pre>%s</pre>" % _escape(self._buffer)
        self.setHtml(html)
        if scroll:
            bar = self.verticalScrollBar()
            bar.setValue(bar.maximum())


def _escape(text):
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
