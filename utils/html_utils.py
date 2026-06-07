"""
Helpers for Telegram HTML parse mode.
"""
from html import escape


def escape_html(value) -> str:
    """Escape dynamic text before inserting it into Telegram HTML messages."""
    if value is None:
        return ""
    return escape(str(value), quote=True)


def safe_html_url(value) -> str:
    """Return an escaped http(s) URL, or an empty string for unsupported values."""
    if not value:
        return ""

    url = str(value).strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        return ""

    return escape_html(url)
