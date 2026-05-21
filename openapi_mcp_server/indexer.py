"""Endpoint search indexer with multi-dimensional matching."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from openapi_mcp_server.models import Endpoint, EndpointSummary, SearchEndpointsResult


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return tokens


class EndpointIndex:
    def __init__(self, endpoints: list[Endpoint]):
        self.endpoints: dict[str, Endpoint] = {}
        self.path_index: dict[str, list[str]] = defaultdict(list)
        self.summary_index: dict[str, list[str]] = defaultdict(list)
        self.tag_index: dict[str, list[str]] = defaultdict(list)
        self.opid_index: dict[str, list[str]] = defaultdict(list)
        self.method_index: dict[str, list[str]] = defaultdict(list)

        for ep in endpoints:
            key = ep.key
            self.endpoints[key] = ep

            for token in _tokenize(ep.path):
                self.path_index[token].append(key)
            if ep.summary:
                for token in _tokenize(ep.summary):
                    self.summary_index[token].append(key)
            if ep.description:
                for token in _tokenize(ep.description):
                    self.summary_index[token].append(key)
            if ep.operation_id:
                for token in _tokenize(ep.operation_id):
                    self.opid_index[token].append(key)
            for tag in ep.tags:
                for token in _tokenize(tag):
                    self.tag_index[token].append(key)
            self.method_index[ep.method.upper()].append(key)

    def search(
        self,
        query: str,
        method: str | None = None,
        tag: str | None = None,
        limit: int = 10,
    ) -> SearchEndpointsResult:
        candidates: dict[str, float] = {}

        query_tokens = _tokenize(query)

        for token in query_tokens:
            for key in self.path_index.get(token, []):
                candidates[key] = candidates.get(key, 0) + 2.0
            for key in self.summary_index.get(token, []):
                candidates[key] = candidates.get(key, 0) + 1.5
            for key in self.opid_index.get(token, []):
                candidates[key] = candidates.get(key, 0) + 3.0
            for key in self.tag_index.get(token, []):
                candidates[key] = candidates.get(key, 0) + 1.0

        full_query = query.lower().replace(" ", "")
        for key, ep in self.endpoints.items():
            path_clean = ep.path.lower().replace(" ", "")
            if full_query in path_clean:
                candidates[key] = candidates.get(key, 0) + 5.0
            if ep.summary and full_query in ep.summary.lower().replace(" ", ""):
                candidates[key] = candidates.get(key, 0) + 4.0

        if method:
            method = method.upper()
            candidates = {
                k: v for k, v in candidates.items() if self.endpoints[k].method == method
            }

        if tag:
            tag_lower = tag.lower()
            candidates = {
                k: v
                for k, v in candidates.items()
                if any(t.lower() == tag_lower for t in self.endpoints[k].tags)
            }

        sorted_keys = sorted(candidates, key=lambda k: candidates[k], reverse=True)
        total = len(sorted_keys)
        top_keys = sorted_keys[:limit]

        return SearchEndpointsResult(
            total=total,
            endpoints=[
                EndpointSummary(
                    path=self.endpoints[k].path,
                    method=self.endpoints[k].method,
                    summary=self.endpoints[k].summary,
                    tags=self.endpoints[k].tags,
                    deprecated=self.endpoints[k].deprecated,
                )
                for k in top_keys
            ],
        )

    def get_by_path_method(self, path: str, method: str) -> Endpoint | None:
        key = f"{method.upper()} {path}"
        return self.endpoints.get(key)

    def get_endpoints_by_tag(self, tag: str) -> list[Endpoint]:
        tag_lower = tag.lower()
        return [
            ep
            for ep in self.endpoints.values()
            if any(t.lower() == tag_lower for t in ep.tags)
        ]
