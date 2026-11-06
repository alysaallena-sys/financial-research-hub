"""Source-aware records, immutable change history and portable risk notices."""
from __future__ import annotations

import csv
import hashlib
import html
import heapq
import io
import json
import sqlite3
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import LICENSE_ID, RISK_NOTICE, RISK_NOTICE_EN

KINDS = {"news", "talk", "research", "rating"}
READ_DEADLINE_SECONDS = 5.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def safe_url(value: str) -> str:
    """Keep only ordinary HTTPS source links; never render script/file URLs."""
    if any(ord(char) < 33 for char in value) or any(char in value for char in '<>"'):
        raise ValueError("Source URL contains unsafe whitespace or markup")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Source links must use HTTPS without embedded credentials")
    return value


def normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
    kind = str(raw.get("kind", ""))
    if kind not in KINDS:
        raise ValueError("Unknown record kind")
    provider = str(raw.get("provider") or "").strip()
    title = str(raw.get("title") or "").strip()
    if not provider or not title:
        raise ValueError("provider and title are required")
    if len(provider) > 100:
        raise ValueError("provider must have at most 100 characters")
    url = safe_url(str(raw.get("url", "")))
    upstream_id = str(raw.get("upstream_id") or raw.get("id") or url)
    identity = hashlib.sha256(f"{provider}\0{kind}\0{upstream_id}".encode()).hexdigest()
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    if not isinstance(raw.get("is_demo", False), bool):
        raise ValueError("is_demo must be a boolean")
    # Rebuild the envelope. Imported material cannot disable/replace this notice.
    return {
        "id": identity,
        "upstream_id": upstream_id,
        "kind": kind,
        "title": title[:1000],
        "url": url,
        "source": str(raw.get("source") or provider)[:200],
        "provider": provider,
        "published_at": str(raw.get("published_at") or ""),
        "symbol": str(raw.get("symbol") or "")[:100],
        "institution": str(raw.get("institution") or "")[:200],
        "summary": str(raw.get("summary") or "")[:1000],
        "metadata": metadata,
        "retrieved_at": str(raw.get("retrieved_at") or utc_now()),
        "risk_notice": RISK_NOTICE,
        "noncommercial": True,
        "is_demo": bool(raw.get("is_demo", False)),
    }


def fingerprint(record: dict[str, Any]) -> str:
    # Retrieval time does not create a false "updated report" on every poll.
    content = {k: v for k, v in record.items() if k not in {"retrieved_at", "first_seen_at", "last_seen_at"}}
    return hashlib.sha256(canonical(content).encode()).hexdigest()


def envelope(items: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    flags = {bool(item.get("is_demo")) for item in items}
    mode = "mixed" if len(flags) > 1 else "demo" if flags == {True} else "local"
    return {
        **extra,
        "risk_notice": RISK_NOTICE,
        "risk_notice_en": RISK_NOTICE_EN,
        "noncommercial": True,
        "license": LICENSE_ID,
        "editor_notice_required": True,
        "mode": mode,
        "count": len(items),
        "items": items,
    }


class Store:
    """All acquired state stays in the explicitly chosen local SQLite file."""

    def __init__(self, path: str | Path, *, read_only: bool = False):
        self.path = str(path)
        self.read_only = read_only
        self._deadline = time.monotonic() + READ_DEADLINE_SECONDS if read_only else None
        if read_only:
            if self.path == ":memory:":
                raise ValueError("Read-only mode requires an existing SQLite file")
            resolved = Path(self.path).resolve()
            if not resolved.is_file():
                raise FileNotFoundError("Read-only workspace database does not exist")
            self.db = sqlite3.connect(resolved.as_uri() + "?mode=ro", uri=True)
            self.db.row_factory = sqlite3.Row
            self.db.set_progress_handler(self._progress, 1000)
            return
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS items (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, provider TEXT NOT NULL,
              symbol TEXT NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
              first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS items_kind_provider ON items(kind, provider);
            CREATE INDEX IF NOT EXISTS items_symbol ON items(symbol);
            CREATE TABLE IF NOT EXISTS changes (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL,
              change_type TEXT NOT NULL, observed_at TEXT NOT NULL,
              before_payload TEXT, after_payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS collections (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL,
              observed_at TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS changes_item_sequence ON changes(item_id,sequence DESC);
            CREATE TABLE IF NOT EXISTS datasets (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, symbol TEXT NOT NULL,
              provider TEXT NOT NULL, source_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
              payload TEXT NOT NULL, first_seen_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS datasets_kind_symbol ON datasets(kind,symbol);
            CREATE INDEX IF NOT EXISTS datasets_symbol ON datasets(symbol);
        """)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def _progress(self) -> int:
        return int(self._deadline is not None and time.monotonic() >= self._deadline)

    def _read_tick(self) -> None:
        if self._progress():
            raise sqlite3.OperationalError("Read-only workspace query deadline exceeded")

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def ingest(self, records: list[dict[str, Any]], collection: dict[str, Any] | None = None) -> dict[str, int]:
        if self.read_only:
            raise PermissionError("Read-only workspace does not permit ingestion")
        # Validate the complete batch before changing durable state.
        prepared = [normalize_record(raw) for raw in records]
        totals = {"new": 0, "updated": 0, "unchanged": 0}
        observed = utc_now()
        with self.db:
            for item in prepared:
                digest = fingerprint(item)
                row = self.db.execute("SELECT * FROM items WHERE id=?", (item["id"],)).fetchone()
                if row and row["fingerprint"] == digest:
                    self.db.execute("UPDATE items SET last_seen_at=? WHERE id=?", (observed, item["id"]))
                    totals["unchanged"] += 1
                    continue
                change = "updated" if row else "new"
                first_seen = row["first_seen_at"] if row else observed
                self.db.execute(
                    "INSERT INTO items VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                    "kind=excluded.kind,provider=excluded.provider,symbol=excluded.symbol,"
                    "fingerprint=excluded.fingerprint,payload=excluded.payload,last_seen_at=excluded.last_seen_at",
                    (item["id"], item["kind"], item["provider"], item["symbol"], digest, canonical(item), first_seen, observed),
                )
                self.db.execute(
                    "INSERT INTO changes(item_id,change_type,observed_at,before_payload,after_payload) VALUES(?,?,?,?,?)",
                    (item["id"], change, observed, row["payload"] if row else None, canonical(item)),
                )
                totals[change] += 1
            if collection:
                self.db.execute("INSERT INTO collections(provider,observed_at,payload) VALUES(?,?,?)", (
                    str(collection.get("provider", "unknown")), observed, canonical(collection)))
        return totals

    @staticmethod
    def _item(row: sqlite3.Row) -> dict[str, Any]:
        item = json.loads(row["payload"])
        item["id"] = row["id"]
        item["first_seen_at"] = row["first_seen_at"]
        item["last_seen_at"] = row["last_seen_at"]
        item["risk_notice"], item["noncommercial"] = RISK_NOTICE, True
        return item

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        if not isinstance(record_id, str) or not re.fullmatch(r"[0-9a-f]{64}", record_id):
            raise ValueError("record_id must be a 64-character lowercase hexadecimal ID")
        self._read_tick()
        row = self.db.execute("SELECT * FROM items WHERE id=?", (record_id,)).fetchone()
        return self._item(row) if row else None

    def query_details(self, *, kind: str = "", provider: str = "", symbol: str = "", q: str = "", limit: int = 100) -> dict[str, Any]:
        if kind and kind not in KINDS:
            raise ValueError("Unknown record kind")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        for name, value, maximum in (("provider", provider, 100), ("symbol", symbol, 100), ("q", q, 200)):
            if not isinstance(value, str) or len(value) > maximum:
                raise ValueError(f"{name} must be text with at most {maximum} characters")
        conditions, params = [], []
        for column, value in (("kind", kind), ("provider", provider), ("symbol", symbol)):
            if value:
                conditions.append(f"{column}=?")
                params.append(value)
        sql = "SELECT * FROM items" + (" WHERE " + " AND ".join(conditions) if conditions else "")
        # Search in Python so SQL wildcards in a query remain ordinary characters.
        self._read_tick()
        rows = self.db.execute(sql, params)
        total = 0
        def matches():
            nonlocal total
            for row in rows:
                self._read_tick()
                item = self._item(row)
                if q and q.casefold() not in " ".join(str(item.get(k, "")) for k in ("title", "summary", "symbol", "institution", "source")).casefold():
                    continue
                total += 1
                yield item
        results = heapq.nlargest(limit, matches(), key=lambda i: (i["published_at"], i["id"]))
        return {"items": results, "total_matches": total, "returned": len(results),
                "limit": limit, "truncated": total > limit}

    def query(self, **filters: Any) -> list[dict[str, Any]]:
        return self.query_details(**filters)["items"]

    def history_details(self, *, record_ids: list[str] | None = None, limit: int = 100) -> dict[str, Any]:
        self._read_tick()
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        params: list[Any] = []
        where = ""
        if record_ids is not None:
            if len(record_ids) > 101:
                raise ValueError("History scope supports at most 101 record IDs")
            for record_id in record_ids:
                if not isinstance(record_id, str) or not re.fullmatch(r"[0-9a-f]{64}", record_id):
                    raise ValueError("record_id must be a 64-character lowercase hexadecimal ID")
            if not record_ids:
                return {"items": [], "returned": 0, "total_matches": 0, "limit": limit,
                        "truncated": False, "record_ids": []}
            params.extend(record_ids)
            where = " WHERE item_id IN (" + ",".join("?" for _ in record_ids) + ")"
        total = self.db.execute("SELECT COUNT(*) FROM changes" + where, params).fetchone()[0]
        rows = self.db.execute("SELECT * FROM changes" + where + " ORDER BY sequence DESC LIMIT ?", [*params, limit]).fetchall()
        items = [{
            "sequence": row["sequence"], "item_id": row["item_id"],
            "change_type": row["change_type"], "observed_at": row["observed_at"],
            "before": json.loads(row["before_payload"]) if row["before_payload"] else None,
            "after": json.loads(row["after_payload"]),
            "item": json.loads(row["after_payload"]),
            "risk_notice": RISK_NOTICE, "noncommercial": True,
            "is_demo": json.loads(row["after_payload"]).get("is_demo", False),
        } for row in rows]
        return {"items": items, "returned": len(items), "total_matches": total, "limit": limit,
                "truncated": total > len(items), "record_ids": record_ids}

    def changes(self, limit: int = 100, *, record_id: str = "") -> list[dict[str, Any]]:
        return self.history_details(record_ids=[record_id] if record_id else None, limit=limit)["items"]

    def collections(self) -> list[dict[str, Any]]:
        self._read_tick()
        rows = self.db.execute("SELECT provider, MAX(sequence) AS n FROM collections GROUP BY provider").fetchall()
        return [json.loads(self.db.execute("SELECT payload FROM collections WHERE sequence=?", (r["n"],)).fetchone()[0]) for r in rows]

    def dataset_schema_available(self) -> bool:
        self._read_tick()
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='datasets'").fetchone() is not None

    def import_dataset(self, raw: dict[str, Any]) -> dict[str, Any]:
        from .evidence import CONTENT_HASH_BASIS, normalize_dataset
        if self.read_only:
            raise PermissionError("Read-only workspace does not permit dataset import")
        dataset = normalize_dataset(raw)
        serialized = canonical(dataset)
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        with self.db:
            old = self.db.execute("SELECT fingerprint,first_seen_at FROM datasets WHERE id=?", (dataset["id"],)).fetchone()
            if old and old["fingerprint"] != digest:
                raise ValueError("Dataset ID is immutable; use a new versioned source_id for changed evidence")
            first_seen = old["first_seen_at"] if old else utc_now()
            if not old:
                self.db.execute("INSERT INTO datasets VALUES(?,?,?,?,?,?,?,?)", (
                    dataset["id"], dataset["kind"], dataset["symbol"] or "", dataset["provenance"]["provider"],
                    dataset["source_id"], digest, serialized, first_seen))
        return {"status": "unchanged" if old else "new", "dataset": {**dataset, "first_seen_at": first_seen,
                "content_hash": digest, "hash_basis": CONTENT_HASH_BASIS}}

    def get_dataset(self, identifier: str) -> dict[str, Any] | None:
        from .evidence import CONTENT_HASH_BASIS, dataset_id
        dataset_id(identifier)
        if not self.dataset_schema_available():
            return None
        row = self.db.execute("SELECT payload,first_seen_at,fingerprint FROM datasets WHERE id=?", (identifier,)).fetchone()
        if not row:
            return None
        item = json.loads(row["payload"])
        item["first_seen_at"] = row["first_seen_at"]
        item.update(content_hash=row["fingerprint"], hash_basis=CONTENT_HASH_BASIS)
        item.update(risk_notice=RISK_NOTICE, noncommercial=True)
        for value in item["rows"]:
            value.update(risk_notice=RISK_NOTICE, noncommercial=True, is_demo=item["is_demo"])
        return item

    def dataset_counts(self) -> dict[str, Any]:
        from .evidence import DATASET_KINDS
        counts = {kind: 0 for kind in sorted(DATASET_KINDS)}
        if not self.dataset_schema_available():
            return {"counts_by_dataset_kind": counts, "dataset_count": 0, "demo_dataset_count": 0,
                    "dataset_schema_available": False}
        counts.update({row["kind"]: row["n"] for row in self.db.execute("SELECT kind,COUNT(*) AS n FROM datasets GROUP BY kind")})
        demos = 0
        for row in self.db.execute("SELECT payload FROM datasets"):
            self._read_tick()
            demos += json.loads(row[0]).get("is_demo") is True
        return {"counts_by_dataset_kind": counts, "dataset_count": sum(counts.values()),
                "demo_dataset_count": demos, "dataset_schema_available": True}

    def dataset_details(self, *, kind: str = "", symbol: str = "", q: str = "", limit: int = 100,
                        related_record_ids: list[str] | None = None) -> dict[str, Any]:
        from .evidence import CONTENT_HASH_BASIS, DATASET_KINDS, dataset_id, dataset_summary
        if kind and kind not in DATASET_KINDS:
            raise ValueError("Unknown numeric dataset kind")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise ValueError("Dataset limit must be between 1 and 1000")
        if related_record_ids is not None:
            if len(related_record_ids) > 101:
                raise ValueError("Related dataset selection supports at most 101 record IDs")
            for identifier in related_record_ids:
                dataset_id(identifier)
        if not self.dataset_schema_available():
            return {"items": [], "returned": 0, "total_matches": 0, "limit": limit,
                    "truncated": False, "schema_available": False}
        conditions, params = [], []
        if related_record_ids is None:
            for column, value in (("kind", kind), ("symbol", symbol)):
                if value:
                    conditions.append(column + "=?")
                    params.append(value)
        sql = "SELECT payload,first_seen_at,fingerprint FROM datasets" + (" WHERE " + " AND ".join(conditions) if conditions else "")
        rows = self.db.execute(sql, params)
        total = 0
        wanted_links = set(related_record_ids or [])
        def matching():
            nonlocal total
            for row in rows:
                self._read_tick()
                item = json.loads(row["payload"])
                item["first_seen_at"] = row["first_seen_at"]
                item.update(content_hash=row["fingerprint"], hash_basis=CONTENT_HASH_BASIS)
                haystack = " ".join((item["title"], item.get("symbol") or "", " ".join(item.get("topics", [])), canonical(item["provenance"]))).casefold()
                matched = (not kind or item["kind"] == kind) and (not symbol or item.get("symbol") == symbol) and (not q or q.casefold() in haystack)
                linked = bool(wanted_links.intersection(item.get("related_record_ids", [])))
                if related_record_ids is not None:
                    matched = linked or (bool(symbol or q) and matched)
                if not matched:
                    continue
                total += 1
                summary = dataset_summary(item)
                if related_record_ids is not None:
                    summary["relationship_basis"] = "explicit_record_link" if linked else "exact_symbol_and_literal_query" if symbol and q else "exact_symbol" if symbol else "literal_query"
                yield summary
        selected = heapq.nlargest(limit, matching(), key=lambda item: (item.get("as_of") or "", item["id"]))
        return {"items": selected, "returned": len(selected), "total_matches": total, "limit": limit,
                "truncated": total > len(selected), "schema_available": True}

    def status(self) -> dict[str, Any]:
        self._read_tick()
        groups = self.db.execute("SELECT kind,COUNT(*) AS n FROM items GROUP BY kind").fetchall()
        counts = {kind: 0 for kind in sorted(KINDS)}
        counts.update({r["kind"]: r["n"] for r in groups})
        total = sum(counts.values())
        demo_count = 0
        for row in self.db.execute("SELECT payload FROM items"):
            self._read_tick()
            demo_count += json.loads(row[0]).get("is_demo") is True
        result = envelope([], counts_by_kind=counts, record_count=total, demo_record_count=demo_count,
                          changes_count=self.db.execute("SELECT COUNT(*) FROM changes").fetchone()[0],
                          network_enabled=False, note="Status contains counters only; live collection is a separate CLI command.")
        result["mode"] = "mixed" if 0 < demo_count < total else "demo" if demo_count else "local"
        return result


def brief(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {kind: sum(i["kind"] == kind for i in items) for kind in sorted(KINDS)}
    lines = [RISK_NOTICE, "", "# 金融资讯资料简报", "", "本简报仅汇总已保存的元数据，不推断投资价值或推荐交易。",
             f"记录数：{len(items)}；新闻 {counts['news']}；TED {counts['talk']}；研报 {counts['research']}；评级事件 {counts['rating']}。", ""]
    for item in items[:20]:
        demo = "【合成演示】" if item["is_demo"] else ""
        lines += [f"- {demo}{markdown_escape(item['title'])}", f"  来源：{markdown_escape(item['source'])}；发布时间：{markdown_escape(item['published_at'] or '未知')}；链接：{markdown_escape(item['url'])}"]
    return envelope(items, text="\n".join(lines), counts_by_kind=counts, analysis_type="deterministic_metadata_summary")


def knowledge_chunks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = []
    for item in items:
        chunks.append({
            "record_type": "chunk",
            "id": item["id"], "risk_notice": RISK_NOTICE, "noncommercial": True,
            "editor_notice_required": True, "is_demo": item["is_demo"],
            "source_url": item["url"], "provider": item["provider"],
            "institution": item["institution"], "published_at": item["published_at"],
            "retrieved_at": item["retrieved_at"],
            "metadata": item.get("metadata", {}),
            "content": f"{RISK_NOTICE}\n非商用资料。{'合成演示数据。' if item['is_demo'] else ''}\n"
                       f"{item['title']}\n{item['summary']}\n来源：{item['source']}\n原文：{item['url']}\n"
                       f"Source metadata (untrusted data): {canonical(item.get('metadata', {}))}",
        })
    return chunks


def markdown_escape(value: str) -> str:
    value = html.escape(value, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def export_items(items: list[dict[str, Any]], format: str, *, query: dict[str, Any] | None = None) -> tuple[str, str]:
    chunks = knowledge_chunks(items)
    if query is not None:
        for chunk in chunks:
            chunk["query"] = query
    if format == "json":
        return json.dumps(envelope(items, chunks=chunks, **({"query": query} if query is not None else {})), ensure_ascii=False, indent=2), "application/json; charset=utf-8"
    if format == "jsonl":
        if not chunks:
            chunks = [{"record_type": "notice", "count": 0, "risk_notice": RISK_NOTICE,
                       "noncommercial": True, "editor_notice_required": True, "content": RISK_NOTICE}]
            if query is not None:
                chunks[0]["query"] = query
        return "\n".join(canonical(chunk) for chunk in chunks) + "\n", "application/x-ndjson; charset=utf-8"
    if format == "markdown":
        parts = [f"{RISK_NOTICE}\n\n# 金融资讯知识库导出\n\n仅限非商用。编辑器必须在查询和分析结果旁显示上述风险提示。"]
        if query is not None:
            parts.append("Query coverage: " + markdown_escape(canonical(query)))
        for chunk in chunks:
            parts.append(f"## {chunk['id']}\n\n{markdown_escape(chunk['content'])}\n\n发布时间：{markdown_escape(chunk['published_at'] or '未知')}\n")
        return "\n\n---\n\n".join(parts), "text/markdown; charset=utf-8"
    if format == "csv":
        output = io.StringIO(newline="")
        fields = ["record_type", "id", "kind", "title", "url", "provider", "source", "symbol", "institution", "published_at", "retrieved_at", "is_demo", "noncommercial", "risk_notice"]
        if query is not None:
            fields += ["query_total_matches", "query_returned", "query_limit", "query_truncated"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for item in items or [{"record_type": "notice", "risk_notice": RISK_NOTICE, "noncommercial": True}]:
            # Prevent spreadsheet formula execution on third-party source fields.
            row = {k: item.get(k, "") for k in fields}
            row["record_type"] = item.get("record_type", "record")
            if query is not None:
                row.update({"query_" + key: query.get(key, "") for key in ("total_matches", "returned", "limit", "truncated")})
            for key, value in row.items():
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    row[key] = "'" + value
            row["risk_notice"], row["noncommercial"] = RISK_NOTICE, True
            writer.writerow(row)
        return output.getvalue(), "text/csv; charset=utf-8"
    raise ValueError("format must be json, jsonl, csv or markdown")


def demo_records() -> list[dict[str, Any]]:
    """Entirely synthetic fixtures: no actual bank statement or price claim."""
    examples = [
        ("news", "demo-news", "示例：公开财经新闻进入资料库", "", "示例新闻来源", "标题与来源元数据演示，不代表真实新闻。"),
        ("talk", "demo-ted", "示例：TED 观点与研究主题关联", "", "示例演讲来源", "演讲信息演示。未抓取真实演讲或字幕。"),
        ("research", "demo-research", "示例：合成公司行业研究目录", "DEMO-CN", "示例机构 A（合成）", "演示新增研报记录与来源追溯。未获取研报正文。"),
        ("rating", "demo-rating", "示例：评级事件记录", "DEMO-US", "示例机构 B（合成）", "合成评级变化，仅用于检验界面和变更记录。"),
    ]
    return [{"id": ident, "kind": kind, "title": title, "url": f"https://example.com/{ident}",
             "source": source, "provider": provider, "published_at": "2026-01-01T12:00:00+00:00",
             "symbol": symbol, "institution": source if kind in {"research", "rating"} else "",
             "summary": summary, "metadata": {"synthetic": True, "rating_from": "示例旧评级", "rating_to": "示例新评级"} if kind == "rating" else {"synthetic": True},
             "is_demo": True, "retrieved_at": "2026-01-01T12:01:00+00:00"}
            for kind, ident, title, symbol, source, summary in examples
            for provider in ["demo"]]
