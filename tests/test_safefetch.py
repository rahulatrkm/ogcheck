"""What OGCheck refuses to fetch.

The service takes a URL from anyone and fetches it, which is the exact shape of
a server-side request forgery hole. Before the guard existed, this worked
against the live deployment:

    /check?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/

That address is the cloud metadata endpoint. It is not firewalled from the
instance itself, and the fetched body came back inside the report. The same
trick against http://127.0.0.1:<port> turned the service into a port scanner,
because "connection refused" and "timed out" are different error strings and
both were quoted back to the caller.

So these tests are adversarial rather than illustrative: each one is an attempt,
and passing means the attempt failed.
"""

from __future__ import annotations

import socket
import unittest
from unittest import mock

from ogcheck import core
from ogcheck.safefetch import BlockedURL, check_url


def _resolves_to(*addresses):
    """Pretend DNS returns exactly these addresses, so no test touches a network."""
    return lambda host, port, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
        for a in addresses
    ]


class BlocksTheHostItRunsOn(unittest.TestCase):
    def test_cloud_metadata_endpoint_is_refused(self):
        # The one that hands over IAM credentials on AWS, GCP and Azure alike.
        with self.assertRaises(BlockedURL):
            check_url("http://169.254.169.254/latest/meta-data/")

    def test_loopback_is_refused(self):
        for url in (
            "http://127.0.0.1:8000/",
            "https://[::1]/",
            "http://0.0.0.0:5000/",
        ):
            with self.subTest(url=url), self.assertRaises(BlockedURL):
                check_url(url)

    def test_loopback_spelled_the_awkward_ways_is_refused(self):
        # Every one of these is 127.0.0.1 to a resolver, and none of them is a
        # valid address to Python's ipaddress module. Relying on DNS to catch
        # them made the guard depend on which platform it ran on.
        for url in (
            "http://127.1/",
            "http://2130706433/",
            "http://0177.0.0.1/",
            "http://0x7f.0.0.1/",
        ):
            with self.subTest(url=url), self.assertRaises(BlockedURL):
                check_url(url)

    def test_a_private_range_spelled_short_is_refused(self):
        with self.assertRaises(BlockedURL):
            check_url("http://10.1/")

    def test_private_ranges_are_refused(self):
        for url in (
            "http://10.0.0.5/",
            "http://172.16.4.4/",
            "http://192.168.1.1/admin",
            "http://[fc00::1]/",
        ):
            with self.subTest(url=url), self.assertRaises(BlockedURL):
                check_url(url)

    def test_an_ipv6_mapped_ipv4_loopback_is_refused(self):
        # ::ffff:127.0.0.1 is loopback wearing an IPv6 costume.
        with self.assertRaises(BlockedURL):
            check_url("http://[::ffff:127.0.0.1]/")

    def test_a_public_address_is_allowed(self):
        self.assertEqual(check_url("http://93.184.216.34/"), "http://93.184.216.34/")


class BlocksNamesThatPointInward(unittest.TestCase):
    def test_a_name_resolving_to_loopback_is_refused(self):
        # Names like this really exist and resolve to 127.0.0.1 on purpose.
        with mock.patch("socket.getaddrinfo", _resolves_to("127.0.0.1")):
            with self.assertRaises(BlockedURL):
                check_url("https://localtest.me/")

    def test_one_bad_answer_among_good_ones_is_still_refused(self):
        # Checking only the first address returned is a way through.
        with mock.patch("socket.getaddrinfo", _resolves_to("93.184.216.34", "10.0.0.1")):
            with self.assertRaises(BlockedURL):
                check_url("https://mixed.example/")

    def test_an_ordinary_name_is_allowed(self):
        with mock.patch("socket.getaddrinfo", _resolves_to("93.184.216.34")):
            self.assertEqual(check_url("https://example.com/x"), "https://example.com/x")

    def test_a_name_that_does_not_resolve_is_refused_without_the_dns_error(self):
        from ogcheck.safefetch import UnreachableURL

        def boom(*a, **kw):
            raise socket.gaierror(-2, "Name or service not known")

        with mock.patch("socket.getaddrinfo", boom):
            with self.assertRaises(UnreachableURL) as caught:
                check_url("https://nope.example/")
        self.assertNotIn("gaierror", str(caught.exception))


class BlocksOtherWaysIn(unittest.TestCase):
    def test_non_http_schemes_are_refused(self):
        for url in (
            "file:///etc/passwd",
            "ftp://internal/secrets",
            "gopher://127.0.0.1:6379/_INFO",   # the classic Redis SSRF gadget
            "data:text/html,<h1>x",
        ):
            with self.subTest(url=url), self.assertRaises(BlockedURL):
                check_url(url)

    def test_a_bare_host_still_defaults_to_https(self):
        with mock.patch("socket.getaddrinfo", _resolves_to("93.184.216.34")):
            self.assertTrue(check_url("example.com").startswith("https://"))


class DoesNotDescribeWhatItFound(unittest.TestCase):
    """A fetch failure must read the same whatever actually happened."""

    def test_a_refused_port_and_a_timeout_are_indistinguishable(self):
        messages = set()
        for failure in (
            ConnectionRefusedError(111, "Connection refused"),
            TimeoutError("timed out"),
            OSError(113, "No route to host"),
        ):
            with mock.patch.object(core, "_fetch_text", side_effect=failure):
                with mock.patch("socket.getaddrinfo", _resolves_to("93.184.216.34")):
                    report = core.validate_url("https://example.com/", check_image=False)
            messages.add(report.fetch_error)
        self.assertEqual(len(messages), 1, f"leaks which failure occurred: {messages}")

    def test_the_error_does_not_quote_the_socket(self):
        with mock.patch.object(core, "_fetch_text",
                               side_effect=ConnectionRefusedError(111, "Connection refused")):
            report = core.validate_url("https://example.com/", check_image=False)
        self.assertNotIn("refused", report.fetch_error.lower())
        self.assertNotIn("111", report.fetch_error)

    def test_a_blocked_url_says_so_and_stops(self):
        report = core.validate_url("http://169.254.169.254/", check_image=False)
        self.assertTrue(report.issues)
        self.assertEqual(report.issues[0].code, "fetch_blocked")
        # It must not fall through and try to parse a page it never fetched.
        self.assertIn("private", report.fetch_error.lower())


class FollowsRedirectsOnlyWhileTheyStayPublic(unittest.TestCase):
    def test_a_redirect_into_the_private_network_is_refused(self):
        import urllib.error

        from ogcheck import safefetch

        hops = []

        class FakeOpener:
            def open(self, request, timeout=None):
                hops.append(request.full_url)
                raise urllib.error.HTTPError(
                    request.full_url, 302, "Found",
                    {"Location": "http://169.254.169.254/latest/meta-data/"}, None,
                )

        with mock.patch("socket.getaddrinfo", _resolves_to("93.184.216.34")):
            with mock.patch.object(safefetch, "_opener", FakeOpener()):
                with self.assertRaises(BlockedURL):
                    safefetch.open_url("https://attacker.example/", timeout=1,
                                       user_agent="test")
        self.assertEqual(hops, ["https://attacker.example/"],
                         "it must not have opened the redirect target")

    def test_endless_redirects_stop(self):
        import urllib.error

        from ogcheck import safefetch

        class Loop:
            def open(self, request, timeout=None):
                raise urllib.error.HTTPError(
                    request.full_url, 302, "Found",
                    {"Location": "https://example.com/next"}, None,
                )

        with mock.patch("socket.getaddrinfo", _resolves_to("93.184.216.34")):
            with mock.patch.object(safefetch, "_opener", Loop()):
                with self.assertRaises(BlockedURL):
                    safefetch.open_url("https://example.com/", timeout=1, user_agent="test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
