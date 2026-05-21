"""Tests for OpenAPI parser."""

import pytest

from openapi_mcp_server.parser import ParseError, parse_spec


def test_parse_petstore(petstore_raw):
    spec = parse_spec(petstore_raw)

    assert spec.title == "Petstore API"
    assert spec.version == "1.0.0"
    assert len(spec.endpoints) == 6

    ep_get_pets = [e for e in spec.endpoints if e.path == "/pets" and e.method == "GET"][0]
    assert ep_get_pets.summary == "List all pets"
    assert ep_get_pets.operation_id == "listPets"
    assert ep_get_pets.tags == ["pets"]
    assert len(ep_get_pets.parameters) == 1
    assert ep_get_pets.parameters[0].name == "limit"
    assert ep_get_pets.parameters[0].location == "query"

    ep_post_pets = [e for e in spec.endpoints if e.path == "/pets" and e.method == "POST"][0]
    assert ep_post_pets.request_body is not None
    assert ep_post_pets.request_body.required
    assert ep_post_pets.request_body.schema_["type"] == "object"

    ep_get_pet = [e for e in spec.endpoints if e.path == "/pets/{petId}" and e.method == "GET"][0]
    assert ep_get_pet.parameters[0].name == "petId"
    assert ep_get_pet.parameters[0].location == "path"
    assert ep_get_pet.parameters[0].required

    ep_delete_pet = [e for e in spec.endpoints if e.path == "/pets/{petId}" and e.method == "DELETE"][0]
    assert ep_delete_pet.deprecated


def test_deref_schema(petstore_raw):
    spec = parse_spec(petstore_raw)

    # GET /pets response should have Pets schema dereferenced
    ep = [e for e in spec.endpoints if e.path == "/pets" and e.method == "GET"][0]
    resp_200 = [r for r in ep.responses if r.status_code == "200"][0]
    assert resp_200.schema_ is not None
    assert resp_200.schema_["type"] == "array"
    assert "properties" in resp_200.schema_["items"]

    # GET /pets/{petId} response should have Pet schema dereferenced
    ep = [e for e in spec.endpoints if e.path == "/pets/{petId}" and e.method == "GET"][0]
    resp_200 = [r for r in ep.responses if r.status_code == "200"][0]
    assert resp_200.schema_ is not None
    assert resp_200.schema_["type"] == "object"
    assert "id" in resp_200.schema_["properties"]


def test_parse_tags(petstore_raw):
    spec = parse_spec(petstore_raw)

    tag_names = [t.name for t in spec.tags]
    assert "pets" in tag_names
    assert "store" in tag_names

    pets_tag = [t for t in spec.tags if t.name == "pets"][0]
    assert pets_tag.endpoint_count == 4

    store_tag = [t for t in spec.tags if t.name == "store"][0]
    assert store_tag.endpoint_count == 2


def test_reject_swagger_2():
    with pytest.raises(ParseError, match="Unsupported OpenAPI version"):
        parse_spec({"swagger": "2.0", "info": {"title": "test", "version": "1.0"}})


def test_reject_openapi_2():
    with pytest.raises(ParseError, match="Unsupported OpenAPI version"):
        parse_spec({"openapi": "2.0.0", "info": {"title": "test", "version": "1.0"}})