"""OGCheck CLI — ``python -m ogcheck <url>``.

Prints a human-readable report and exits non-zero when the preview is broken, so
it doubles as a **CI check** (the "ESLint for your social preview" use case that
the demand research surfaced). This is also the basis of a free GitHub Action —
a zero-cost distribution channel.
"""

from __future__ import annotations

import sys

from ogcheck.core import validate_url

_COLORS = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
_RESET = "\033[0m"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print("usage: python -m ogcheck <url> [--no-color] [--ci]")
        print("  checks a page's Open Graph / social-preview tags and og:image.")
        return 0

    url = args[0]
    use_color = "--no-color" not in args and sys.stdout.isatty()
    report = validate_url(url)

    print(f"OGCheck — {report.url}")
    print(f"  score : {report.score}/100   {'PASS' if report.ok else 'FAIL'}")
    if report.title:
        print(f"  title : {report.title}")
    if report.image_url:
        status = report.image_status if report.image_status is not None else "unreachable"
        print(f"  image : {status}  {report.image_url}")
    if not report.issues:
        print("  ✓ no issues — your link preview looks good.")
    for issue in report.issues:
        tag = issue.severity.upper()
        if use_color:
            tag = f"{_COLORS.get(issue.severity, '')}{tag}{_RESET}"
        print(f"  [{tag}] {issue.message}")

    # In CI mode (or by default), a broken preview fails the build.
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
