"""Test get_endpoint_detail tool — verify schema definitions are fully returned."""

import json
import re
from pathlib import Path

import pytest

from openapi_mcp_server.models import AppConfig, ProjectConfig, Settings
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.tools.detail import handle

REAL_SPEC = Path(r"D:\project\private\openapi-mcp\openapi.json")


@pytest.fixture
async def real_registry(tmp_path):
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(REAL_SPEC.read_text(encoding="utf-8"), encoding="utf-8")

    config = AppConfig(
        settings=Settings(),
        projects={
            "myapp": ProjectConfig(
                name="myapp",
                source="local",
                path=str(spec_path),
            ),
        },
    )
    registry = ProjectRegistry(config)
    await registry.load_all()
    return registry


def _pretty(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---- Test 1: GET endpoint — parameters have schema, response $ref resolved ----


@pytest.mark.asyncio
async def test_get_endpoint_ref_response(real_registry):
    """GET /api/v1/admin/users — response schema should have $ref resolved inline."""
    result = await handle(real_registry, {
        "project": "myapp",
        "path": "/api/v1/admin/users",
        "method": "get",
    })
    data = json.loads(result)

    print("\n========== GET /api/v1/admin/users ==========")
    print(_pretty(data))

    # parameters should exist and have 'schema' (alias, not 'schema_')
    assert len(data["parameters"]) > 0
    for p in data["parameters"]:
        assert "schema" in p, f"Parameter {p['name']} missing 'schema' field"
        assert "in" in p, f"Parameter {p['name']} missing 'in' field (alias for location)"

    # 200 response should have resolved schema (not a bare $ref)
    resp_200 = [r for r in data["responses"] if r["status_code"] == "200"]
    assert len(resp_200) == 1
    schema = resp_200[0]["schema"]
    assert schema is not None, "200 response schema is None"

    # Top-level $ref should be resolved
    assert "$ref" not in schema, f"200 response top-level schema still contains $ref: {schema}"


# ---- Test 2: PUT endpoint with $ref in request body ----


@pytest.mark.asyncio
async def test_put_endpoint_ref_request_body(real_registry):
    """PUT /api/v1/admin/users/{user_id}/status — request body schema should be resolved."""
    result = await handle(real_registry, {
        "project": "myapp",
        "path": "/api/v1/admin/users/{user_id}/status",
        "method": "put",
    })
    data = json.loads(result)

    print("\n========== PUT /api/v1/admin/users/{user_id}/status ==========")
    print(_pretty(data))

    assert data["request_body"] is not None
    rb_schema = data["request_body"]["schema"]
    assert rb_schema is not None, "request_body schema is None"
    assert "$ref" not in rb_schema, f"request_body schema still contains $ref: {rb_schema}"
    assert "type" in rb_schema or "properties" in rb_schema or "allOf" in rb_schema, \
        f"request_body schema looks unresolved: {rb_schema}"


# ---- Test 3: POST endpoint — request body + response schemas ----


@pytest.mark.asyncio
async def test_post_endpoint_full_schema(real_registry):
    """POST /api/v1/admin/dishes — both request body and response schemas should be resolved."""
    result = await handle(real_registry, {
        "project": "myapp",
        "path": "/api/v1/admin/dishes",
        "method": "post",
    })
    data = json.loads(result)

    print("\n========== POST /api/v1/admin/dishes ==========")
    print(_pretty(data))

    # request body
    assert data["request_body"] is not None
    rb_schema = data["request_body"]["schema"]
    assert rb_schema is not None
    assert "$ref" not in rb_schema, f"request_body schema still contains $ref: {rb_schema}"


# ---- Test 4: No $ref should remain anywhere — nested anyOf/allOf/oneOf resolved ----


@pytest.mark.asyncio
async def test_no_unresolved_refs_anywhere(real_registry):
    """$ref inside anyOf/allOf/oneOf/items should also be recursively resolved."""
    result = await handle(real_registry, {
        "project": "myapp",
        "path": "/api/v1/admin/dishes",
        "method": "post",
    })

    refs = re.findall(r'"\$ref"\s*:\s*"([^"]+)"', result)
    if refs:
        print(f"\n========== Found unresolved $ref references: {refs} ==========")
    else:
        print("\n========== No unresolved $ref found — all resolved ==========")

    assert len(refs) == 0, f"Found {len(refs)} unresolved $ref: {refs}"


# ---- Test 5: Parameter schemas are complete ----


@pytest.mark.asyncio
async def test_parameter_schemas_complete(real_registry):
    """All parameters should have their schema field populated (alias key)."""
    result = await handle(real_registry, {
        "project": "myapp",
        "path": "/api/v1/admin/dishes",
        "method": "get",
    })
    data = json.loads(result)

    print("\n========== GET /api/v1/admin/dishes (parameter focus) ==========")
    for p in data["parameters"]:
        schema_str = json.dumps(p.get("schema", {}), ensure_ascii=False)
        print(f"  param={p['name']}, in={p['in']}, schema={schema_str}")

    for p in data["parameters"]:
        schema = p.get("schema")
        assert schema is not None, f"Parameter '{p['name']}' has no schema"
        assert isinstance(schema, dict), f"Parameter '{p['name']}' schema is not a dict"


# ---- Test 6: Error case — nonexistent endpoint ----


@pytest.mark.asyncio
async def test_nonexistent_endpoint(real_registry):
    result = await handle(real_registry, {
        "project": "myapp",
        "path": "/api/v1/nonexistent",
        "method": "get",
    })
    assert "Error" in result
    print(f"\n========== Nonexistent endpoint: {result} ==========")
