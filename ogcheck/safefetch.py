"""Outbound fetching that cannot be pointed at the machine it runs on.

OGCheck's whole job is to fetch a URL somebody hands it, which is the textbook
setup for server-side request forgery. Before this module existed, anyone could
ask the public service to fetch ``http://169.254.169.254/latest/meta-data/`` and
read the cloud instance's IAM credentials back out of the report, or sweep
``http://127.0.0.1:<port>`` and tell open ports from closed ones by whether the
error said "connection refused". Redirects were followed without a second look,
so a public-looking URL could bounce straight to a private one.

Three things matter here and each is easy to get subtly wrong:

* **Every hop is checked, not just the first.** Redirects are resolved manually
  so a 302 into a private range is refused rather than followed.
* **The check is on the resolved addresses, not the hostname.** A name like
  ``localtest.me`` resolves to 127.0.0.1 while looking perfectly ordinary, and
  every address a name resolves to has to be safe, not merely the first.
* **Failures are described, not quoted.** Handing back the raw OSError text is
  itself the leak: it is what tells an attacker whether a port is listening.

What this does not fully close is DNS rebinding — a name that answers with a
public address when it is checked and a private one microseconds later when the
socket is opened. Closing that properly means pinning the connection to the
address that was checked, which the standard library does not expose cleanly.
The window is small and the payoff is a single unauthenticated GET, but it is
real, so it is written down here rather than quietly assumed away.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

ALLOWED_SCHEMES = ("http", "https")
MAX_REDIRECTS = 5
DEFAULT_MAX_BYTES = 2_000_000


class BlockedURL(Exception):
    """The URL is not one this service is willing to fetch."""


class UnreachableURL(Exception):
    """The URL could not be looked up at all.

    Kept separate from :class:`BlockedURL` because they mean different things to
    a reader: one is "we would not", the other is "we could not". The message
    never repeats the resolver's own text, which would say whether a name exists.
    """


def _address_is_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return not (
        addr.is_private          # 10/8, 172.16/12, 192.168/16, fc00::/7
        or addr.is_loopback      # 127/8, ::1
        or addr.is_link_local    # 169.254/16 — the cloud metadata endpoint
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
        or getattr(addr, "is_site_local", False)
    )


def _resolve(host: str, port: int) -> list:
    try:
        return socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnreachableURL("that host name could not be looked up") from exc


def _as_literal_address(host: str) -> Optional[str]:
    """Return the address ``host`` literally is, or None if it is a name.

    ``ipaddress`` only accepts the four-part dotted form, but resolvers also
    accept ``127.1``, ``2130706433``, ``0177.0.0.1`` and ``0x7f.0.0.1`` — every
    one of which is loopback wearing a different hat. Leaving those to DNS meant
    the guard's behaviour depended on the platform's resolver, so they are
    decoded here instead.
    """
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass
    if ":" in host:                      # an IPv6 literal ipaddress already refused
        return None
    try:
        return socket.inet_ntoa(socket.inet_aton(host))
    except (OSError, UnicodeEncodeError):
        return None


def check_url(url: str) -> str:
    """Return ``url`` normalised, or raise :class:`BlockedURL`.

    Raised messages are safe to show a caller: they never repeat a socket error.
    """
    if not urlparse(url).scheme:
        url = "https://" + url
    parts = urlparse(url)

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise BlockedURL("only http and https addresses can be checked")
    if not parts.hostname:
        raise BlockedURL("that address has no host name")

    port = parts.port or (443 if parts.scheme.lower() == "https" else 80)

    # A literal address is judged directly; a name is judged by everything it
    # answers with, because one public answer alongside a private one is still
    # a way in.
    literal = _as_literal_address(parts.hostname)
    if literal is not None:
        if not _address_is_public(literal):
            raise BlockedURL("that address is on a private or internal network")
        return urlunparse(parts)

    for info in _resolve(parts.hostname, port):
        if not _address_is_public(info[4][0]):
            raise BlockedURL("that host name points at a private or internal network")
    return urlunparse(parts)


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Hand redirects back to the caller so each hop can be checked first."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_opener = urllib.request.build_opener(_NoRedirects)


def open_url(
    url: str,
    *,
    timeout: float,
    max_bytes: int = DEFAULT_MAX_BYTES,
    user_agent: str,
    method: str = "GET",
) -> Tuple[int, bytes, Optional[str], str]:
    """Fetch ``url``, following redirects only while they stay public.

    Returns ``(status, body, charset, final_url)``. Raises :class:`BlockedURL`
    if the URL — or any address it redirects to — is not safely public.
    """
    current = check_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        request = urllib.request.Request(
            current, headers={"User-Agent": user_agent}, method=method
        )
        try:
            with _opener.open(request, timeout=timeout) as response:
                body = response.read(max_bytes)
                charset = response.headers.get_content_charset()
                return int(response.status), body, charset, current
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                target = exc.headers.get("Location")
                if not target:
                    raise BlockedURL("that page redirected without saying where") from exc
                # Relative targets are resolved against the hop we are on.
                current = check_url(urljoin(current, target))
                continue
            # A real HTTP status is information the caller asked for.
            return int(exc.code), b"", None, current
    raise BlockedURL("that address redirected too many times")
