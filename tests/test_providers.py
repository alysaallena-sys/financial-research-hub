import json
import io
import ssl
import subprocess
import urllib.error
import unittest
from unittest.mock import Mock, patch

from finance_research_hub.providers import (ProviderError, collect_eastmoney, collect_yahoo,
                                          parse_feed, validate_request_url)
from finance_research_hub import providers


class ProviderTests(unittest.TestCase):
    def test_rss_metadata_only_and_no_http_auto_upgrade(self):
        feed = b'''<rss><channel><item><title>Synthetic &amp; title</title><link>https://example.com/a</link><guid>demo</guid><pubDate>Thu, 01 Jan 2026 12:00:00 GMT</pubDate><description>&lt;b&gt;Short synthetic summary&lt;/b&gt;</description></item><item><title>HTTP item</title><link>http://example.com/b</link></item></channel></rss>'''
        result = parse_feed(feed, "bbc")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Synthetic & title")
        self.assertEqual(result[0]["summary"], "Short synthetic summary")
        self.assertEqual(result[0]["published_at"], "2026-01-01T12:00:00+00:00")
        self.assertFalse(result[0]["is_demo"])

    def test_atom_links_and_unsafe_xml(self):
        atom = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>urn:demo</id><title>Synthetic</title><link rel="alternate" href="https://example.com/talk"/><updated>2026-01-01T00:00:00Z</updated></entry></feed>'''
        self.assertEqual(parse_feed(atom, "ted")[0]["kind"], "talk")
        with self.assertRaises(ProviderError):
            parse_feed(b'<!DOCTYPE x [<!ENTITY a "bad">]><rss/>', "bbc")

    def test_network_target_and_downgrade_boundaries(self):
        validate_request_url("https://reportapi.eastmoney.com/report/list")
        for url in ("http://reportapi.eastmoney.com/report/list", "https://127.0.0.1/", "https://reportapi.eastmoney.com.evil.test/", "https://u:p@reportapi.eastmoney.com/", "https://reportapi.eastmoney.com:444/"):
            with self.assertRaises(ProviderError):
                validate_request_url(url)

    def test_bounded_pagination_and_truncation_are_explicit(self):
        calls = []
        def transport(url, payload=None):
            calls.append((url, payload))
            return json.dumps({"TotalPage": 3, "data": [{"infoCode": "DEMO-1", "title": "Synthetic report", "orgSName": "Synthetic institution", "publishDate": "2026-01-01", "predictThisYearEps": 1.23}]}).encode()
        records, coverage = collect_eastmoney(symbol="600000", begin="2026-01-01", end="2026-01-02", transport=transport)
        self.assertEqual(len(calls), 1)
        self.assertIn("/list2", calls[0][0])
        self.assertEqual(calls[0][1]["beginTime"], "2026-01-01")
        self.assertNotIn("qType", calls[0][1])
        self.assertNotIn("industry", calls[0][1])
        self.assertEqual(set(calls[0][1]), {"pageSize", "pageNo", "p", "pageNum", "pageNumber", "beginTime", "endTime", "code", "industryCode", "rating", "ratingChange", "orgCode", "rcode"})
        self.assertTrue(coverage["truncated"])
        self.assertEqual(coverage["reported_total_pages"], 3)
        self.assertEqual(records[0]["metadata"]["direct_provider"], "Eastmoney")
        self.assertIn("forecasts", records[0]["metadata"])

    def test_unknown_total_does_not_claim_complete(self):
        def transport(url, payload=None):
            return b'{"data": []}'
        _, coverage = collect_eastmoney(report_type="macro", transport=transport)
        self.assertIsNone(coverage["truncated"])
        self.assertIsNone(coverage["reported_total_pages"])

    def test_all_five_types_have_explicit_date_range_and_expected_method(self):
        calls = []
        def transport(url, payload=None):
            calls.append((url, payload))
            return b'{"TotalPage": 1, "data": []}'
        for kind in ("stock", "industry", "strategy", "macro", "morning"):
            collect_eastmoney(report_type=kind, symbol="600000" if kind == "stock" else "", begin="2026-01-01", end="2026-01-02", transport=transport)
        self.assertIsNotNone(calls[0][1])
        self.assertIn("/list?", calls[1][0])
        self.assertIn("/jg?", calls[2][0])
        self.assertTrue(all("beginTime" in url or (payload and "beginTime" in payload) for url, payload in calls))

    def test_invalid_queries_fail_before_transport(self):
        def unexpected(*args):
            self.fail("Transport must not be called")
        with self.assertRaises(ValueError):
            collect_eastmoney(symbol="../", transport=unexpected)
        with self.assertRaises(ValueError):
            collect_eastmoney(symbol="600000", max_pages=11, transport=unexpected)
        with self.assertRaises(ValueError):
            collect_eastmoney(report_type="industry", begin="2026-02-01", end="2026-01-01", transport=unexpected)
        with self.assertRaises(ProviderError):
            collect_eastmoney(symbol="600000", transport=lambda *a: b'{"data": {}}')
        with self.assertRaises(ValueError):
            collect_yahoo("../../")


def curl_wire(content=b"synthetic data", status=200, redirect=""):
    return content + providers.CURL_STATUS_MARKER + str(status).encode() + providers.CURL_REDIRECT_MARKER + redirect.encode() + b"\n"


class CurlTransportTests(unittest.TestCase):
    def test_python_certificate_failure_has_no_automatic_transport_fallback(self):
        opener = Mock()
        opener.open.side_effect = urllib.error.URLError(ssl.SSLCertVerificationError("synthetic certificate failure"))
        with patch.object(providers.urllib.request, "build_opener", return_value=opener), patch.object(providers, "_run_curl") as curl:
            with self.assertRaises(ProviderError):
                providers.request_bytes("https://feeds.bbci.co.uk/news/business/rss.xml")
            curl.assert_not_called()

    def test_explicit_curl_keeps_tls_and_uses_stdin_json_not_shell_or_files(self):
        with patch.object(providers, "_run_curl", return_value=(0, curl_wire(b"{}"))) as run:
            result = providers.curl_request_bytes("https://reportapi.eastmoney.com/report/list2", {"test": "synthetic input"})
        self.assertEqual(result, b"{}")
        argv, body, timeout = run.call_args.args
        self.assertEqual(argv[1], "--disable")
        self.assertIn("--globoff", argv)
        self.assertIn("--no-netrc", argv)
        self.assertEqual(argv[argv.index("--proto") + 1], "=https")
        self.assertEqual(argv[argv.index("--data-binary") + 1], "@-")
        self.assertEqual(json.loads(body), {"test": "synthetic input"})
        self.assertLessEqual(timeout, providers.TIMEOUT)
        self.assertFalse(any(flag in argv for flag in ("-k", "--insecure", "--location", "-L", "--cookie", "--cookie-jar", "--netrc", "--dump-header")))
        self.assertNotIn("synthetic input", " ".join(argv))

    def test_curl_certificate_failure_stays_a_failure(self):
        with patch.object(providers, "_run_curl", return_value=(60, b"")) as run:
            with self.assertRaisesRegex(ProviderError, "validation remained enabled"):
                providers.curl_request_bytes("https://feeds.bbci.co.uk/news/business/rss.xml")
        self.assertEqual(run.call_count, 1)

    def test_redirect_to_foreign_or_http_target_is_rejected_before_following(self):
        for target in ("https://example.com/private", "http://feeds.bbci.co.uk/business", "https://127.0.0.1/", "https://user:password@feeds.bbci.co.uk/"):
            with patch.object(providers, "_run_curl", return_value=(0, curl_wire(status=302, redirect=target))) as run:
                with self.assertRaises(ProviderError):
                    providers.curl_request_bytes("https://feeds.bbci.co.uk/news/business/rss.xml")
            self.assertEqual(run.call_count, 1)

    def test_allowed_redirect_is_manual_and_preserves_307_post_body(self):
        sequence = [(0, curl_wire(status=307, redirect="https://reportapi.eastmoney.com/report/list2?moved=1")),
                    (0, curl_wire(b"{}"))]
        with patch.object(providers, "_run_curl", side_effect=sequence) as run:
            result = providers.curl_request_bytes("https://reportapi.eastmoney.com/report/list2", {"demo": True})
        self.assertEqual(result, b"{}")
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[1], run.call_args_list[1].args[1])
        self.assertTrue(run.call_args_list[1].args[0][-1].endswith("?moved=1"))

    def test_post_redirect_cannot_forward_body_to_another_allowlisted_origin(self):
        for status in (301, 302, 303, 307, 308):
            with patch.object(providers, "_run_curl", return_value=(0, curl_wire(status=status, redirect="https://feeds.bbci.co.uk/collect"))) as run:
                with self.assertRaisesRegex(ProviderError, "original origin"):
                    providers.curl_request_bytes("https://reportapi.eastmoney.com/report/list2", {"demo": True})
            self.assertEqual(run.call_count, 1)
        request = providers.urllib.request.Request("https://reportapi.eastmoney.com/report/list2", data=b"{}")
        with self.assertRaisesRegex(ProviderError, "original origin"):
            providers.SourceRedirectHandler().redirect_request(request, None, 307, "redirect", {}, "https://feeds.bbci.co.uk/collect")

    def test_official_ted_redirect_target_is_exactly_allowlisted(self):
        providers.validate_request_url("https://pa.tedcdn.com/feeds/talks.rss")
        providers.validate_request_url("https://feeds.acast.com/public/shows/67587e77c705e441797aff96")
        for target in ("https://other.tedcdn.com/feeds/talks.rss", "https://pa.tedcdn.com.evil.test/feeds/talks.rss", "http://pa.tedcdn.com/feeds/talks.rss",
                       "https://other.acast.com/public/shows/demo", "https://feeds.acast.com.evil.test/public/shows/demo", "http://feeds.acast.com/public/shows/demo"):
            with self.assertRaises(ProviderError):
                providers.validate_request_url(target)
        sequence = [(0, curl_wire(status=308, redirect="https://pa.tedcdn.com/feeds/talks.rss")),
                    (0, curl_wire(status=301, redirect="https://feeds.acast.com/public/shows/67587e77c705e441797aff96")),
                    (0, curl_wire(b"<rss/>"))]
        with patch.object(providers, "_run_curl", side_effect=sequence) as run:
            self.assertEqual(providers.curl_request_bytes("https://www.ted.com/feeds/talks.rss"), b"<rss/>")
        self.assertEqual(run.call_count, 3)
        self.assertEqual(run.call_args_list[2].args[0][-1], "https://feeds.acast.com/public/shows/67587e77c705e441797aff96")
        self.assertTrue(all(call.args[1] is None for call in run.call_args_list))

    def test_redirect_count_and_http_errors_are_bounded(self):
        with patch.object(providers, "_run_curl", return_value=(0, curl_wire(status=302, redirect="https://feeds.bbci.co.uk/moved"))) as run:
            with self.assertRaisesRegex(ProviderError, "redirect count"):
                providers.curl_request_bytes("https://feeds.bbci.co.uk/news/business/rss.xml")
        self.assertEqual(run.call_count, providers.MAX_REDIRECTS + 1)
        with patch.object(providers, "_run_curl", return_value=(0, curl_wire(status=403))):
            with self.assertRaisesRegex(ProviderError, "HTTP 403"):
                providers.curl_request_bytes("https://feeds.bbci.co.uk/news/business/rss.xml")

    def test_subprocess_stdout_is_bounded_and_only_owned_process_is_killed(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.BytesIO(b"x" * (providers.MAX_BYTES + providers.CURL_METADATA_BYTES + 1))
                self.returncode = 0
                self.kills = 0
            def wait(self, timeout):
                return self.returncode
            def poll(self):
                return self.returncode
            def kill(self):
                self.kills += 1
                self.returncode = -9
        process = FakeProcess()
        with patch.dict(providers.os.environ, {"SSLKEYLOGFILE": "synthetic-key-log", "QLOGDIR": "synthetic-quic-log"}):
            with patch.object(providers.subprocess, "Popen", return_value=process) as popen:
                with self.assertRaisesRegex(ProviderError, "5 MiB"):
                    providers._run_curl(["curl", "--disable"], None, 1)
            self.assertIn("SSLKEYLOGFILE", providers.os.environ)
            self.assertIn("QLOGDIR", providers.os.environ)
        self.assertEqual(process.kills, 1)
        self.assertIs(popen.call_args.kwargs["shell"], False)
        self.assertEqual(popen.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertNotIn("SSLKEYLOGFILE", popen.call_args.kwargs["env"])
        self.assertNotIn("QLOGDIR", popen.call_args.kwargs["env"])

    def test_subprocess_timeout_kills_owned_process_and_fails(self):
        process = Mock()
        process.stdout = io.BytesIO(b"")
        process.wait.side_effect = [subprocess.TimeoutExpired("curl", 1), 0]
        process.poll.return_value = 0
        with patch.object(providers.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(ProviderError, "timeout"):
                providers._run_curl(["curl", "--disable"], None, 0.01)
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
