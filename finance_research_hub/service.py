"""One local workspace service for CLI, HTTP and read-only MCP clients."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from . import RISK_NOTICE
from .core import KINDS, Store, brief as build_brief, canonical, envelope, export_items, knowledge_chunks
from .providers import source_catalog
from .evidence import DATASET_KINDS, dataset_chunks, dataset_id, dataset_summary


def _limit(value: int, name: str = "limit") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 1000:
        raise ValueError(f"{name} must be an integer between 1 and 1000")
    return value


def _text(value: str, name: str, maximum: int) -> str:
    if not isinstance(value, str) or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError(f"{name} must be text of at most {maximum} characters without control characters")
    return value


def _provenance(item: dict[str, Any]) -> dict[str, Any]:
    meta = item.get("metadata", {})
    return {
        "record_id": item["id"], "provider": item["provider"], "source": item["source"],
        "direct_provider": meta.get("direct_provider") or item["provider"],
        "original_publisher": meta.get("original_publisher") or item["institution"] or item["source"],
        "institution": item["institution"], "source_url": item["url"],
        "upstream_id": item.get("upstream_id", ""), "published_at": item["published_at"],
        "retrieved_at": item["retrieved_at"], "first_seen_at": item.get("first_seen_at", ""),
        "content_scope": meta.get("content_scope", "saved source metadata; no full-text acceptance"),
        "is_demo": item["is_demo"], "risk_notice": item["risk_notice"], "noncommercial": True,
    }


class ResearchWorkspace:
    """Read operations share semantics; only legacy construction can create a DB.

    Set read_only=True for MCP or other consumers that must not create files,
    execute schema DDL, or ingest records. Store injection is for local tests
    and existing presentation adapters; the caller owns an injected Store.
    """

    def __init__(self, db_path: str | Path, *, read_only: bool = False,
                 store: Store | None = None, store_factory: Callable[..., Store] | None = None):
        if not isinstance(read_only, bool):
            raise ValueError("read_only must be a boolean")
        if store is not None and read_only and not store.read_only:
            raise ValueError("A read-only workspace requires a read-only injected store")
        self.db_path = str(db_path)
        self.read_only = read_only
        self._injected = store
        self._factory = store_factory or Store

    @contextmanager
    def _connection(self) -> Iterator[Store]:
        if self._injected is not None:
            yield self._injected
        else:
            # Keep the single-argument path for existing CLI/HTTP test factories.
            created = self._factory(self.db_path, read_only=True) if self.read_only else self._factory(self.db_path)
            with created as store:
                yield store

    @staticmethod
    def _search(store: Store, *, kind: str = "", provider: str = "", symbol: str = "", q: str = "", limit: int = 100) -> dict[str, Any]:
        kind = _text(kind, "kind", 20)
        filters = {"kind": kind, "provider": _text(provider, "provider", 100),
                   "symbol": _text(symbol, "symbol", 100), "q": _text(q, "q", 200)}
        details = store.query_details(**filters, limit=_limit(limit))
        return envelope(details["items"], filters=filters, empty=not details["items"],
                        **{key: value for key, value in details.items() if key != "items"},
                        completeness="Saved local matches only; source-universe completeness is not established.")

    @staticmethod
    def _history(store: Store, *, record_ids: list[str] | None = None, limit: int = 100) -> dict[str, Any]:
        details = store.history_details(record_ids=record_ids, limit=_limit(limit))
        return envelope(details["items"], empty=not details["items"],
                        **{key: value for key, value in details.items() if key != "items"})

    def status(self) -> dict[str, Any]:
        with self._connection() as store:
            result = {**store.status(), **store.dataset_counts(), "read_only": self.read_only,
                      "service": "ResearchWorkspace", "capabilities": ["search", "record", "changes", "brief", "export", "research_pack", "datasets", "dataset", "compare", "review_packet"],
                      "collection_available_through_service": False}
            total = result["record_count"] + result["dataset_count"]
            demos = result["demo_record_count"] + result["demo_dataset_count"]
            result["mode"] = "mixed" if 0 < demos < total else "demo" if demos else "local"
            return result

    def sources(self) -> dict[str, Any]:
        with self._connection() as store:
            collections = store.collections()
            try:
                from .workflow import research_catalog
                catalog = research_catalog()
                catalog_available = True
            except ModuleNotFoundError:
                catalog, catalog_available = [], False
            return envelope([], sources=source_catalog(collections), collections=collections,
                            research_catalog=catalog, research_catalog_available=catalog_available,
                            network_enabled=False, note="Adapter availability is not live-source acceptance.")

    @staticmethod
    def _references(q: str, *, limit: int = 20) -> dict[str, Any]:
        note = "Dated catalogue metadata, not active acquisition, full text or runtime acceptance."
        if not q:
            return envelope([], empty=True, total_matches=0, returned=0, limit=limit, truncated=False,
                            source_metadata_reference_only=True, query=q, note=note,
                            selection_basis="explicit_literal_query_only; no query supplied")
        try:
            from .workflow import research_catalog
            catalog = research_catalog()
        except ModuleNotFoundError:
            return envelope([], empty=True, total_matches=0, returned=0, limit=limit, truncated=False,
                            source_metadata_reference_only=True, query=q, note=note, catalogue_available=False)
        found = []
        total = 0
        for entry in catalog:
            haystack = " ".join(str(entry.get(key, "")) for key in ("id", "name", "notes", "role")).casefold()
            if q.casefold() not in haystack:
                continue
            total += 1
            if len(found) < limit:
                found.append({**entry, "risk_notice": RISK_NOTICE, "noncommercial": True,
                              "is_demo": False, "source_metadata_reference_only": True})
        return envelope(found, empty=not found, total_matches=total, returned=len(found), limit=limit,
                        truncated=total > len(found), source_metadata_reference_only=True,
                        query=q, note=note, catalogue_available=True, selection_basis="literal_catalogue_metadata")

    def search(self, *, kind: str = "", provider: str = "", symbol: str = "", q: str = "", limit: int = 100) -> dict[str, Any]:
        with self._connection() as store:
            return self._search(store, kind=kind, provider=provider, symbol=symbol, q=q, limit=limit)

    def get_record(self, record_id: str, *, history_limit: int = 50) -> dict[str, Any]:
        _limit(history_limit, "history_limit")
        with self._connection() as store:
            item = store.get_record(record_id)
            return envelope([item] if item else [], found=item is not None, empty=item is None,
                            record_id=record_id, record=item, provenance=_provenance(item) if item else None,
                            history=self._history(store, record_ids=[record_id], limit=history_limit),
                            related_selector={"symbol": item["symbol"] if item else "", "q": ""},
                            missing_reason=None if item else "No saved local record has this exact ID.")

    def changes(self, *, record_id: str = "", limit: int = 100) -> dict[str, Any]:
        record_id = _text(record_id, "record_id", 64)
        with self._connection() as store:
            if record_id:
                store.get_record(record_id)  # Validate the exact ID without scanning a result window.
            return self._history(store, record_ids=[record_id] if record_id else None, limit=limit)

    def brief(self, *, kind: str = "", provider: str = "", symbol: str = "", q: str = "", limit: int = 100) -> dict[str, Any]:
        result = self.search(kind=kind, provider=provider, symbol=symbol, q=q, limit=limit)
        summary = build_brief(result["items"])
        query = {key: result[key] for key in ("filters", "returned", "total_matches", "limit", "truncated")}
        summary["text"] += "\n\nQuery coverage: " + canonical(query)
        return {**summary, "query": query,
                "empty": result["empty"], "truncated": result["truncated"]}

    def export(self, format: str = "json", *, kind: str = "", provider: str = "", symbol: str = "", q: str = "", limit: int = 100) -> dict[str, Any]:
        result = self.search(kind=kind, provider=provider, symbol=symbol, q=q, limit=limit)
        query = {key: result[key] for key in ("filters", "returned", "total_matches", "limit", "truncated")}
        content, content_type = export_items(result["items"], format, query=query)
        return {**result, "format": format, "content": content, "content_type": content_type,
                "chunks": knowledge_chunks(result["items"]), "query": query}

    @staticmethod
    def _datasets(store: Store, *, kind: str = "", symbol: str = "", q: str = "", limit: int = 100,
                  related_record_ids: list[str] | None = None) -> dict[str, Any]:
        filters = {"kind": _text(kind, "kind", 32), "symbol": _text(symbol, "symbol", 100), "q": _text(q, "q", 200)}
        details = store.dataset_details(**filters, limit=_limit(limit), related_record_ids=related_record_ids)
        return envelope(details["items"], empty=not details["items"], filters=filters,
                        **{key: value for key, value in details.items() if key != "items"},
                        rows_scope="Directory summaries include at most 5 preview rows; use exact dataset retrieval for the saved rows.")

    def datasets(self, *, kind: str = "", symbol: str = "", q: str = "", limit: int = 100) -> dict[str, Any]:
        with self._connection() as store:
            return self._datasets(store, kind=kind, symbol=symbol, q=q, limit=limit)

    def get_dataset(self, identifier: str) -> dict[str, Any]:
        dataset_id(identifier)
        with self._connection() as store:
            item = store.get_dataset(identifier)
            return envelope([item] if item else [], found=item is not None, empty=item is None,
                            dataset_id=identifier, dataset=item, schema_available=store.dataset_schema_available(),
                            chunks=dataset_chunks(item) if item else [],
                            related_selector={"symbol": item.get("symbol") or "", "q": ""} if item else {"symbol": "", "q": ""},
                            missing_reason=None if item else "No saved local dataset has this exact ID; legacy databases may require explicit local import migration.")

    def import_dataset(self, document: dict[str, Any]) -> dict[str, Any]:
        if self.read_only:
            raise PermissionError("Read-only service does not permit local dataset import")
        with self._connection() as store:
            result = store.import_dataset(document)
            summary = dataset_summary(result["dataset"])
            return envelope([summary], status=result["status"], dataset_id=summary["id"], dataset=summary,
                            content_scope="Explicit local import only; no source network request or independent source verification.")

    @staticmethod
    def _dataset_ids(values: list[str]) -> list[str]:
        if not isinstance(values, list) or not 1 <= len(values) <= 5:
            raise ValueError("Select between 1 and 5 exact dataset IDs")
        checked = [dataset_id(value) for value in values]
        if len(set(checked)) != len(checked):
            raise ValueError("Duplicate dataset IDs are not permitted")
        return checked

    def compare(self, dataset_ids: list[str], *, alignment: str = "strict", start: str = "", end: str = "") -> dict[str, Any]:
        from .comparison import compare_datasets
        identifiers = self._dataset_ids(dataset_ids)
        if len(identifiers) < 2:
            raise ValueError("Comparison requires between 2 and 5 exact datasets")
        with self._connection() as store:
            datasets = [store.get_dataset(identifier) for identifier in identifiers]
        if any(item is None for item in datasets):
            raise LookupError("One or more exact datasets were not found")
        return compare_datasets(datasets, alignment=alignment, start=start, end=end)

    def review_packet(self, *, record_id: str = "", symbol: str = "", q: str = "", dataset_ids: list[str] | None = None,
                      question: str = "", limit: int = 20) -> dict[str, Any]:
        from .workflow import build_review_packet
        question = _text(question, "question", 1000)
        if dataset_ids is not None and not isinstance(dataset_ids, list):
            raise ValueError("dataset_ids must be a list of exact IDs")
        identifiers = self._dataset_ids(dataset_ids) if dataset_ids else []
        if not record_id and not symbol and not q and not identifiers:
            raise ValueError("review_packet requires a record selector, literal query or exact datasets")
        pack = self.research_pack(record_id=record_id, symbol=symbol, q=q, limit=limit) if record_id or symbol or q else envelope([], empty=True)
        if pack.get("missing_reason"):
            raise LookupError(pack["missing_reason"])
        with self._connection() as store:
            datasets = [store.get_dataset(identifier) for identifier in identifiers]
        if any(item is None for item in datasets):
            raise LookupError("One or more exact datasets were not found")
        return build_review_packet(pack, datasets, question=question)

    def research_pack(self, *, record_id: str = "", symbol: str = "", q: str = "", limit: int = 100, history_limit: int = 20) -> dict[str, Any]:
        record_id = _text(record_id, "record_id", 64)
        symbol, q = _text(symbol, "symbol", 100), _text(q, "q", 200)
        _limit(limit)
        if limit > 100:
            raise ValueError("research_pack supports at most 100 selected records; use search for larger result windows")
        _limit(history_limit, "history_limit")
        if not record_id and not symbol and not q:
            raise ValueError("research_pack requires an exact record_id, exact symbol or literal q")
        with self._connection() as store:
            anchor = store.get_record(record_id) if record_id else None
            if record_id and anchor is None:
                result = envelope([], found=False, empty=True, anchor=None,
                                  selection={"record_id": record_id, "symbol": symbol, "q": q, "basis": "missing_anchor", "anchor_in_selection": False},
                                  missing_reason="No saved local record has this exact anchor ID.",
                                  total_matches=0, returned=0, limit=limit, truncated=False)
            else:
                if anchor and anchor["symbol"]:
                    if symbol and symbol != anchor["symbol"]:
                        raise ValueError("Explicit symbol must match the anchor record's exact symbol")
                    # An explicit topic query can broaden beyond the anchor's symbol.
                    # Derive a symbol only when the caller supplies no selector.
                    if not symbol and not q:
                        symbol = anchor["symbol"]
                if not symbol and not q:
                    assert anchor is not None
                    result = envelope([anchor], total_matches=1, returned=1, limit=limit, truncated=False, empty=False)
                    basis = "anchor_only"
                else:
                    result = self._search(store, symbol=symbol, q=q, limit=limit)
                    basis = "exact_symbol_and_literal_query" if symbol and q else "exact_symbol" if symbol else "literal_query"
                result.update(found=bool(result["items"]), anchor=anchor,
                              selection={"record_id": record_id, "symbol": symbol, "q": q, "basis": basis,
                                         "anchor_in_selection": bool(anchor and any(i["id"] == anchor["id"] for i in result["items"]))})
            items = result["items"]
            record_ids = [item["id"] for item in items]
            if anchor and anchor["id"] not in record_ids:
                record_ids.append(anchor["id"])
            history = self._history(store, record_ids=record_ids, limit=history_limit)
            history["anchor_history_included"] = bool(anchor and anchor["id"] in record_ids)
            providers = {item["provider"] for item in items}
            collections = [c for c in store.collections() if c.get("provider") in providers]
            kinds = {item["kind"] for item in items}
            missing = sorted(KINDS - kinds)
            result.update(
                provenance=[_provenance(item) for item in items], history=history,
                chunks=knowledge_chunks(items), brief=build_brief(items), missing_kinds=missing,
                coverage={"total_matches": result["total_matches"], "returned": len(items), "limit": limit,
                          "truncated": result["truncated"], "kinds_present": sorted(kinds), "missing_kinds": missing,
                          "missing_publication_ids": [i["id"] for i in items if not i["published_at"]],
                          "provider_collections": collections,
                          "collection_scope": "Latest provider collection receipts; not a completeness guarantee for every selected record.",
                          "missing_kind_scope": "No matching saved local records of these kinds; not proof that outside sources lack material.",
                          "history_truncated": history["truncated"], "history_scope_truncated": False,
                          "history_record_count": len(record_ids)},
                relationship="Exact-symbol and/or literal-text selection only; no causal relationship or independent corroboration is established.",
                independent_corroboration="not_established", full_report_text_included=False,
            )
            related = self._datasets(store, symbol=symbol, q=q, limit=20, related_record_ids=record_ids)
            if result.get("missing_reason"):
                related = envelope([], empty=True, schema_available=related["schema_available"], limit=20,
                                   total_matches=0, returned=0, truncated=False)
            result["related_datasets"] = related
            references = self._references(q if not result.get("missing_reason") else "")
            result["reference_entries"] = references
            result["dataset_chunks"] = [chunk for item in related["items"] for chunk in dataset_chunks(item)]
            result["missing_dataset_kinds"] = sorted(DATASET_KINDS - {item["kind"] for item in related["items"]})
            result["coverage"]["datasets"] = {key: related[key] for key in ("returned", "total_matches", "limit", "truncated", "schema_available")}
            result["evidence_counts"] = {"records": len(items), "datasets": related["count"], "references": references["count"]}
            result["has_evidence"] = bool(items or related["items"] or references["items"])
            if not result.get("missing_reason"):
                result["found"], result["empty"] = result["has_evidence"], not result["has_evidence"]
            return result
