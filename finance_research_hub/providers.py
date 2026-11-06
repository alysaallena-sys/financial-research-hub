"""Bounded read-only metadata adapters. Nothing runs until collect --live."""
from __future__ import annotations

import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

from .core import utc_now

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 15
USER_AGENT = "FinancialResearchHub/0.1 (noncommercial public metadata research)"
FEEDS = {
    "bbc": ("BBC Business", "news", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    "guardian": ("The Guardian Business", "news", "https://www.theguardian.com/business/rss"),
    "ted": ("TED Talks", "talk", "https://www.ted.com/feeds/talks.rss"),
}
ALLOWED_HOSTS = {"feeds.bbci.co.uk", "www.theguardian.com", "www.ted.com", "pa.tedcdn.com", "feeds.acast.com", "feeds.feedburner.com", "reportapi.eastmoney.com"}
REPORT_TYPES = {"stock", "industry", "strategy", "macro", "morning"}
MAX_REDIRECTS = 3
CURL_STATUS_MARKER = b"\n__FRH_HTTP_STATUS__:"
CURL_REDIRECT_MARKER = b"\n__FRH_REDIRECT_URL__:"
CURL_METADATA_BYTES = 16 * 1024


class ProviderError(RuntimeError):
    pass


def validate_request_url(url: str) -> None:
    if len(url) > 8192 or any(ord(char) < 33 for char in url):
        raise ProviderError("Network target contains unsafe whitespace or exceeds the URL limit")
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username or parsed.password or parsed.port not in {None, 443}):
        raise ProviderError("Network target is outside the fixed HTTPS source allowlist")


def _origin(url: str) -> tuple[str, str | None, int]:
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme, parsed.hostname, parsed.port or 443


class SourceRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        validate_request_url(newurl)
        if req.data is not None and _origin(req.full_url) != _origin(newurl):
            raise ProviderError("POST redirects must remain on the original origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request_bytes(url: str, payload: dict[str, Any] | None = None) -> bytes:
    validate_request_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,application/rss+xml,application/atom+xml,text/xml"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    # HTTPS uses Python's normal verified trust store. Never install permissive SSL handlers.
    opener = urllib.request.build_opener(SourceRedirectHandler())
    try:
        with opener.open(req, timeout=TIMEOUT) as response:
            validate_request_url(response.geturl())
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ProviderError("Source response exceeded 5 MiB")
            return data
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"Source request failed: {exc}") from exc


def _run_curl(argv: list[str], body: bytes | None, timeout: float) -> tuple[int, bytes]:
    """Read bounded stdout in memory; kill only this owned process on limit/timeout."""
    output = bytearray()
    too_large = threading.Event()
    read_errors: list[Exception] = []
    # Prevent inherited diagnostic settings from creating TLS-key or QUIC logs.
    # Do not alter global environment or inspect/print either variable's value.
    child_env = os.environ.copy()
    child_env.pop("SSLKEYLOGFILE", None)
    child_env.pop("QLOGDIR", None)
    process = subprocess.Popen(argv, stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=False, env=child_env)
    assert process.stdout is not None

    def read_output() -> None:
        try:
            while True:
                chunk = process.stdout.read(64 * 1024)
                if not chunk:
                    return
                if len(output) + len(chunk) > MAX_BYTES + CURL_METADATA_BYTES:
                    too_large.set()
                    process.kill()
                    return
                output.extend(chunk)
        except (OSError, ValueError) as exc:
            read_errors.append(exc)

    def write_input() -> None:
        assert process.stdin is not None
        try:
            process.stdin.write(body or b"")
        except (BrokenPipeError, OSError):
            # The exit code is authoritative if curl exits before consuming input.
            pass
        finally:
            try:
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

    reader = threading.Thread(target=read_output, daemon=True)
    writer = threading.Thread(target=write_input, daemon=True) if body is not None else None
    reader.start()
    if writer:
        writer.start()
    try:
        try:
            code = process.wait(timeout=timeout + 1)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait(timeout=2)
            raise ProviderError("System curl exceeded the request timeout; certificate validation was not disabled") from exc
        reader.join(timeout=2)
        if reader.is_alive():
            raise ProviderError("System curl output did not close after exit")
        if too_large.is_set() or code == 63:
            raise ProviderError("Source response exceeded 5 MiB")
        if read_errors:
            raise ProviderError("System curl output could not be read")
        return code, bytes(output)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        if writer:
            writer.join(timeout=2)
        reader.join(timeout=2)
        process.stdout.close()


def curl_request_bytes(url: str, payload: dict[str, Any] | None = None) -> bytes:
    """Explicit system-curl transport with verified TLS and manual allowlisted redirects.

    This is never an automatic response to a Python certificate error. It reads
    no curlrc, netrc or browser cookies. No response header/cookie file is used.
    curl's normal CA backend remains active; no trust settings are changed.
    """
    executable = "/usr/bin/curl" if Path("/usr/bin/curl").is_file() else shutil.which("curl")
    if not executable:
        raise ProviderError("System curl is unavailable; use verified urllib or install curl explicitly")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    if body is not None and len(body) > 64 * 1024:
        raise ProviderError("JSON request body exceeded 64 KiB")
    deadline = time.monotonic() + TIMEOUT
    for hop in range(MAX_REDIRECTS + 1):
        validate_request_url(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderError("System curl exceeded the total request timeout")
        # --disable must be the first option, so ~/.curlrc cannot inject options.
        # No --location: each redirect destination is checked before any request.
        argv = [executable, "--disable", "--globoff", "--silent", "--no-netrc", "--proto", "=https",
                "--max-time", f"{remaining:.3f}", "--connect-timeout", f"{min(remaining, 10):.3f}",
                "--max-filesize", str(MAX_BYTES), "--user-agent", USER_AGENT,
                "--header", "Accept: application/json,application/rss+xml,application/atom+xml,text/xml",
                "--write-out", "\n__FRH_HTTP_STATUS__:%{http_code}\n__FRH_REDIRECT_URL__:%{redirect_url}\n"]
        if body is not None:
            argv += ["--header", "Content-Type: application/json", "--data-binary", "@-"]
        argv += ["--", url]
        code, wire = _run_curl(argv, body, remaining)
        if code != 0:
            raise ProviderError(f"System curl failed with exit code {code}; TLS certificate validation remained enabled")
        try:
            content, trailer = wire.rsplit(CURL_STATUS_MARKER, 1)
            status_raw, redirect_raw = trailer.split(CURL_REDIRECT_MARKER, 1)
            status = int(status_raw.strip())
            redirect = redirect_raw.strip().decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProviderError("System curl returned invalid response metadata") from exc
        if len(content) > MAX_BYTES:
            raise ProviderError("Source response exceeded 5 MiB")
        if status in {301, 302, 303, 307, 308}:
            if hop >= MAX_REDIRECTS:
                raise ProviderError("Source exceeded the allowed redirect count")
            if not redirect:
                raise ProviderError("Source redirect did not include a destination")
            destination = urllib.parse.urljoin(url, redirect)
            validate_request_url(destination)
            if body is not None and _origin(url) != _origin(destination):
                raise ProviderError("POST redirects must remain on the original origin")
            url = destination
            if status in {301, 302, 303}:
                body = None
            continue
        if not 200 <= status < 300:
            raise ProviderError(f"Source returned HTTP {status}; no authentication or access-control bypass was attempted")
        return content
    raise ProviderError("Source redirect limit exceeded")


class TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain(value: str, limit: int = 280) -> str:
    parser = TextOnly()
    parser.feed(value)
    return " ".join(html.unescape(" ".join(parser.parts)).split())[:limit]


def iso_date(value: str) -> str:
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        return dt.isoformat() if dt.tzinfo is not None else value
    except (ValueError, TypeError, OverflowError):
        # Keep source time unchanged when its timezone is unknown.
        return value


def parse_feed(data: bytes, provider: str) -> list[dict[str, Any]]:
    if provider not in FEEDS:
        raise ProviderError("Unknown feed")
    if len(data) > MAX_BYTES or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ProviderError("Unsafe or oversized XML feed")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ProviderError("Source did not return a readable RSS/Atom feed") from exc
    name, kind, _ = FEEDS[provider]
    records = []
    nodes = root.findall(".//item")
    atom = "{http://www.w3.org/2005/Atom}"
    if not nodes:
        nodes = root.findall(f"{atom}entry")
    for node in nodes[:200]:
        title = node.findtext("title") or node.findtext(f"{atom}title") or ""
        url = node.findtext("link") or ""
        if not url:
            links = node.findall(f"{atom}link")
            url = next((x.get("href", "") for x in links if x.get("rel", "alternate") == "alternate"), "")
        # An HTTP link is not silently "upgraded" to an unverified HTTPS endpoint.
        if not title.strip() or urllib.parse.urlsplit(url).scheme != "https":
            continue
        published = node.findtext("pubDate") or node.findtext(f"{atom}published") or node.findtext(f"{atom}updated") or ""
        summary = node.findtext("description") or node.findtext(f"{atom}summary") or ""
        records.append({
            "id": node.findtext("guid") or node.findtext(f"{atom}id") or url,
            "kind": kind, "title": plain(title, 1000), "url": url,
            "source": name, "provider": provider, "published_at": iso_date(published),
            "symbol": "", "institution": "", "summary": plain(summary),
            "metadata": {"content_scope": "feed metadata and short feed summary only", "source_time_raw": published,
                         "original_publisher": name, "direct_provider": name},
            "retrieved_at": utc_now(), "is_demo": False,
        })
    return records


def collect_feed(provider: str, transport: Callable[..., bytes] = request_bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = parse_feed(transport(FEEDS[provider][2]), provider)
    return records, {"provider": provider, "observed_at": utc_now(), "returned_records": len(records),
                     "coverage": "current feed window only; not historical coverage", "truncated": None,
                     "content_scope": "public feed metadata; no full article or transcript download"}


def _source_json(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8-sig").strip()
        # Some public endpoints use JSONP. Parse the wrapper; never evaluate code.
        if not text.startswith(("{", "[")):
            match = re.fullmatch(r"[\w.]+\((.*)\);?", text, flags=re.S)
            if not match:
                raise ValueError("not JSON or JSONP")
            text = match.group(1)
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("expected object")
        return result
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProviderError("Report source did not return the expected JSON object") from exc


def _date_range(begin: str | None, end: str | None) -> tuple[str, str]:
    end = end or date.today().isoformat()
    begin = begin or (date.fromisoformat(end) - timedelta(days=7)).isoformat()
    if date.fromisoformat(begin) > date.fromisoformat(end):
        raise ValueError("begin must not be after end")
    return begin, end


def collect_eastmoney(*, report_type: str = "stock", symbol: str = "", industry: str = "",
                      begin: str | None = None, end: str | None = None,
                      max_pages: int = 1, page_size: int = 20,
                      transport: Callable[..., bytes] = request_bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if report_type not in REPORT_TYPES:
        raise ValueError("Unknown report type")
    if not 1 <= max_pages <= 10 or not 1 <= page_size <= 100:
        raise ValueError("max-pages must be 1..10 and page-size 1..100")
    if report_type == "stock" and not re.fullmatch(r"\d{6}", symbol):
        raise ValueError("stock research requires a six-digit stock symbol")
    if industry and not re.fullmatch(r"[A-Za-z0-9]{1,20}", industry):
        raise ValueError("industry must be a source industry code")
    begin, end = _date_range(begin, end)
    reports: dict[str, dict[str, Any]] = {}
    total_pages: int | None = None
    fetched_pages = 0
    endpoint = "list2" if report_type == "stock" else "list" if report_type == "industry" else "jg"
    type_codes = {"industry": 1, "stock": 1, "strategy": 2, "macro": 3, "morning": 4}
    truncated: bool | None = None
    for page in range(1, max_pages + 1):
        params = {"pageNo": page, "pageSize": page_size, "beginTime": begin, "endTime": end,
                  "qType": type_codes[report_type], "industry": "*", "rating": "*", "ratingChange": "*", "orgCode": "", "rcode": ""}
        if symbol:
            params["code"] = symbol
        if industry:
            params["industryCode"] = industry
        url = f"https://reportapi.eastmoney.com/report/{endpoint}"
        if endpoint == "list2":
            # /list2 is a distinct POST contract; do not mix /list GET fields.
            payload = {"pageSize": page_size, "pageNo": page, "p": page,
                       "pageNum": page, "pageNumber": page, "beginTime": begin,
                       "endTime": end, "code": symbol, "industryCode": "*",
                       "rating": None, "ratingChange": None, "orgCode": None, "rcode": ""}
            result = _source_json(transport(url, payload))
        else:
            result = _source_json(transport(url + "?" + urllib.parse.urlencode(params)))
        fetched_pages += 1
        rows = result.get("data")
        if not isinstance(rows, list):
            raise ProviderError("Report source schema changed: data is not a list")
        raw_total = result.get("TotalPage", result.get("totalPage", result.get("totalPages")))
        if raw_total is not None:
            try:
                total_pages = int(raw_total)
            except (ValueError, TypeError) as exc:
                raise ProviderError("Report source returned an invalid page count") from exc
            if total_pages < 0:
                raise ProviderError("Report source returned a negative page count")
        for raw in rows:
            if not isinstance(raw, dict):
                raise ProviderError("Report source schema changed: row is not an object")
            title = str(raw.get("title") or "").strip()
            code = str(raw.get("infoCode") or raw.get("id") or "")
            if not title or not code:
                continue
            detail = "zw_stock" if report_type == "stock" else "zw_industry" if report_type == "industry" else "zw_strategy" if report_type == "strategy" else "zw_macresearch"
            link = f"https://data.eastmoney.com/report/{detail}.jshtml?infocode={urllib.parse.quote(code, safe='')}"
            institution = str(raw.get("orgSName") or raw.get("orgName") or "")
            published = str(raw.get("publishDate") or "")
            metadata = {"report_type": report_type, "source_time_raw": published, "timezone": "source did not provide timezone",
                        "rating": raw.get("emRatingName") or raw.get("sRatingName") or "",
                        "original_publisher": institution or "unknown", "direct_provider": "Eastmoney",
                        "content_scope": "report list metadata only; no PDF or report full text",
                        "forecasts": {k: v for k, v in raw.items() if "predict" in k.lower()}}
            reports[code] = {"id": code, "kind": "research", "provider": "eastmoney", "title": title,
                             "url": link, "source": "东方财富研报目录", "institution": institution,
                             "symbol": str(raw.get("stockCode") or symbol), "published_at": published,
                             "summary": "", "metadata": metadata, "retrieved_at": utc_now(), "is_demo": False}
        if total_pages is not None and page >= total_pages:
            truncated = False
            break
        if not rows:
            truncated = (total_pages > page) if total_pages is not None else None
            break
    if total_pages is not None and fetched_pages < total_pages:
        truncated = True
    # Unknown totals do not become a false completeness guarantee, even on a short page.
    return list(reports.values()), {"provider": "eastmoney", "observed_at": utc_now(), "report_type": report_type,
                                    "symbol": symbol, "industry": industry, "begin": begin, "end": end,
                                    "fetched_pages": fetched_pages, "reported_total_pages": total_pages,
                                    "max_pages": max_pages, "page_size": page_size, "returned_records": len(reports),
                                    "truncated": truncated, "coverage": "bounded public report-list query; metadata only; completeness follows source pagination, not verified report universe"}


def collect_yahoo(symbol: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not re.fullmatch(r"[A-Za-z0-9.^=-]{1,24}", symbol):
        raise ValueError("A valid ticker symbol is required")
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ProviderError("Optional ratings adapter is unavailable. Install the ratings extra explicitly; no package was installed automatically.") from exc
    # The optional upstream owns its network transport; it is separately disclosed.
    try:
        frame = yf.Ticker(symbol).upgrades_downgrades
    except Exception as exc:
        raise ProviderError(f"Yahoo ratings request failed: {type(exc).__name__}: {exc}") from exc
    records = []
    if frame is None:
        raise ProviderError("Yahoo returned no ratings table")
    for when, row in frame.head(200).iterrows():
        institution = str(row.get("Firm", ""))
        published = when.isoformat() if hasattr(when, "isoformat") else str(when)
        def val(key: str) -> str:
            value = row.get(key, "")
            return "" if value is None or str(value).lower() == "nan" else str(value)
        old, new, action = val("FromGrade"), val("ToGrade"), val("Action")
        event_key = f"{symbol}|{published}|{institution}"
        records.append({"id": event_key, "kind": "rating", "title": f"{symbol} · {institution} · {old or '未提供'} → {new or '未提供'}",
                        "url": f"https://finance.yahoo.com/quote/{urllib.parse.quote(symbol, safe='')}/analysis/",
                        "provider": "yahoo", "source": "Yahoo Finance（yfinance）", "institution": institution,
                        "symbol": symbol.upper(), "published_at": published, "summary": "",
                        "metadata": {"rating_from": old, "rating_to": new, "action": action,
                                     "original_publisher": institution, "direct_provider": "Yahoo Finance",
                                     "timezone": "preserved from upstream index; may be absent",
                                     "content_scope": "aggregated rating event; not original investment-bank report text"},
                        "is_demo": False, "retrieved_at": utc_now()})
    return records, {"provider": "yahoo", "observed_at": utc_now(), "symbol": symbol.upper(),
                     "returned_records": len(records), "truncated": len(frame) > 200,
                     "coverage": "up to 200 available Yahoo aggregate rating events; institution coverage and latency unverified"}


def source_catalog(collections: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    sources = [{"id": key, "name": name, "kind": kind, "status": "available", "url": url,
                "coverage": "公开 RSS/Atom 元数据；来源窗口和时效待实际采集核对", "note": "需显式 collect --live；不抓全文"}
               for key, (name, kind, url) in FEEDS.items()]
    sources += [{"id": "eastmoney", "name": "东方财富研报目录", "kind": "research", "status": "available",
                 "url": "https://data.eastmoney.com/report/", "coverage": "个股、行业、宏观、策略、晨报列表；分页上限明确记录", "note": "元数据适配器；源码已实现，服务端和内容取用条件需实际核对"},
                {"id": "yahoo", "name": "Yahoo / yfinance 评级事件", "kind": "rating", "status": "available" if importlib.util.find_spec("yfinance") else "optional_dependency",
                 "url": "https://finance.yahoo.com/", "coverage": "机构评级事件；不含投行研报全文", "note": "需自行安装 ratings extra；上游网络行为与数据使用条款单独适用"}]
    by_id = {item["provider"]: item for item in collections or []}
    for source in sources:
        source["last_collection"] = by_id.get(source["id"])
        source["runtime_verified"] = False
    return sources
