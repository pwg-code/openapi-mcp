"""OpenAPI 3.x parser with $ref dereferencing."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from openapi_mcp_server.models import (
    Endpoint,
    ParameterDetail,
    ParsedSpec,
    RequestBodyDetail,
    ResponseDetail,
    ServerInfo,
    TagInfo,
)

MAX_DEREF_DEPTH = 10


class ParseError(Exception):
    pass


def parse_spec(raw: dict[str, Any]) -> ParsedSpec:
    version = raw.get("openapi", "")
    if not version.startswith("3."):
        raise ParseError(f"Unsupported OpenAPI version: {version!r}. Only 3.x is supported.")

    info = raw.get("info", {})
    components = raw.get("components", {})
    schemas = components.get("schemas", {})

    servers = _parse_servers(raw.get("servers", []))
    tags = _parse_tags(raw.get("tags", []))

    endpoints = _parse_paths(raw.get("paths", {}), components)

    tag_endpoint_counts: dict[str, int] = {}
    for ep in endpoints:
        for t in ep.tags:
            tag_endpoint_counts[t] = tag_endpoint_counts.get(t, 0) + 1

    enriched_tags = []
    for t in tags:
        t.endpoint_count = tag_endpoint_counts.get(t.name, 0)
        enriched_tags.append(t)
    for t_name, count in tag_endpoint_counts.items():
        if not any(t.name == t_name for t in enriched_tags):
            enriched_tags.append(TagInfo(name=t_name, endpoint_count=count))

    return ParsedSpec(
        title=info.get("title", "Untitled"),
        version=info.get("version", "0.0.0"),
        description=info.get("description"),
        servers=servers,
        endpoints=endpoints,
        tags=enriched_tags,
        schemas={k: _deref(v, components, set()) for k, v in schemas.items()},
        raw_spec=raw,
    )


def _parse_servers(raw_servers: list[dict[str, Any]]) -> list[ServerInfo]:
    return [
        ServerInfo(
            url=s.get("url", ""),
            description=s.get("description"),
            variables=s.get("variables", {}),
        )
        for s in raw_servers
    ]


def _parse_tags(raw_tags: list[dict[str, Any]]) -> list[TagInfo]:
    return [
        TagInfo(name=t.get("name", ""), description=t.get("description"))
        for t in raw_tags
        if t.get("name")
    ]


def _parse_paths(
    paths: dict[str, Any],
    components: dict[str, Any],
) -> list[Endpoint]:
    endpoints = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        path_params = [_parse_param(p, components) for p in path_item.get("parameters", [])]

        for method in ("get", "post", "put", "delete", "patch", "head", "options", "trace"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            op_params = [_parse_param(p, components) for p in operation.get("parameters", [])]
            merged_params = _merge_params(path_params, op_params)

            request_body = _parse_request_body(operation.get("requestBody"), components)
            responses = _parse_responses(operation.get("responses", {}), components)
            servers = _parse_servers(operation.get("servers", []))

            endpoints.append(
                Endpoint(
                    path=path,
                    method=method.upper(),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    operation_id=operation.get("operationId"),
                    tags=operation.get("tags", []),
                    deprecated=operation.get("deprecated", False),
                    parameters=merged_params,
                    request_body=request_body,
                    responses=responses,
                    servers=servers,
                )
            )

    return endpoints


def _merge_params(
    path_params: list[ParameterDetail],
    op_params: list[ParameterDetail],
) -> list[ParameterDetail]:
    op_keys = {(p.name, p.location) for p in op_params}
    merged = list(op_params)
    for p in path_params:
        if (p.name, p.location) not in op_keys:
            merged.append(p)
    return merged


def _parse_param(param: dict[str, Any], components: dict[str, Any]) -> ParameterDetail:
    param = _deref(param, components, set())
    schema = param.get("schema", {})
    schema = _deref(schema, components, set()) if schema else {}
    return ParameterDetail(
        name=param.get("name", ""),
        **{"in": param.get("in", "query")},
        required=param.get("required", False),
        **{"schema": schema},
        description=param.get("description"),
    )


def _parse_request_body(
    rb: dict[str, Any] | None,
    components: dict[str, Any],
) -> RequestBodyDetail | None:
    if not rb:
        return None

    rb = _deref(rb, components, set())
    content = rb.get("content", {})

    for content_type, media in content.items():
        schema = media.get("schema", {})
        schema = _deref(schema, components, set()) if schema else {}
        example = media.get("example")
        if not example:
            examples = media.get("examples", {})
            if examples:
                first = next(iter(examples.values()), {})
                example = first.get("value") if isinstance(first, dict) else None
        return RequestBodyDetail(
            content_type=content_type,
            required=rb.get("required", False),
            **{"schema": schema},
            example=example,
        )

    return RequestBodyDetail(required=rb.get("required", False))


def _parse_responses(
    responses: dict[str, Any],
    components: dict[str, Any],
) -> list[ResponseDetail]:
    result = []
    for status_code, resp in responses.items():
        resp = _deref(resp, components, set())
        content = resp.get("content", {})

        if content:
            for ct, media in content.items():
                schema = media.get("schema", {})
                schema = _deref(schema, components, set()) if schema else None
                example = media.get("example")
                if not example:
                    examples = media.get("examples", {})
                    if examples:
                        first = next(iter(examples.values()), {})
                        example = first.get("value") if isinstance(first, dict) else None
                result.append(
                    ResponseDetail(
                        status_code=status_code,
                        description=resp.get("description", ""),
                        content_type=ct,
                        **{"schema": schema},
                        example=example,
                    )
                )
        else:
            result.append(
                ResponseDetail(
                    status_code=status_code,
                    description=resp.get("description", ""),
                )
            )

    return result


def _deref(
    node: Any,
    components: dict[str, Any],
    visited: set[str],
    depth: int = 0,
) -> Any:
    if depth > MAX_DEREF_DEPTH:
        return node

    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if ref and isinstance(ref, str):
        if ref in visited:
            return {"$ref": ref, "_circular": True}

        if not ref.startswith("#/components/"):
            return node

        parts = ref.lstrip("#/").split("/")
        resolved = components
        for part in parts[1:]:
            if isinstance(resolved, dict):
                resolved = resolved.get(part)
            else:
                return node
            if resolved is None:
                return node

        return _deref(deepcopy(resolved), components, visited | {ref}, depth + 1)

    result = {}
    for key, value in node.items():
        if isinstance(value, dict):
            result[key] = _deref(value, components, visited, depth + 1)
        elif isinstance(value, list):
            result[key] = [
                _deref(item, components, visited, depth + 1)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result
