"""OGCheck — a real, free-to-run Open Graph / social-preview validator.

Catches the silently-broken link preview (missing/404 og:image, absent tags)
before it costs you traffic. Pure standard library; deploys anywhere for free.
"""

from __future__ import annotations

from ogcheck.core import Issue, Report, validate_html, validate_url

__version__ = "1.0.0"

__all__ = ["Issue", "Report", "__version__", "validate_html", "validate_url"]
