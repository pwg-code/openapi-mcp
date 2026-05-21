"""Tests for endpoint indexer."""

import pytest

from openapi_mcp_server.indexer import EndpointIndex
from openapi_mcp_server.parser import parse_spec


@pytest.fixture
def petstore_index(petstore_raw):
    spec = parse_spec(petstore_raw)
    return EndpointIndex(spec.endpoints)


def test_search_by_keyword(petstore_index):
    result = petstore_index.search(query="pet")
    assert result.total >= 3
    paths = [e.path for e in result.endpoints]
    assert "/pets" in paths
    assert "/pets/{petId}" in paths


def test_search_by_method(petstore_index):
    result = petstore_index.search(query="pet", method="GET")
    assert result.total >= 2
    assert all(e.method == "GET" for e in result.endpoints)


def test_search_by_tag(petstore_index):
    result = petstore_index.search(query="pet", tag="pets")
    assert result.total >= 3
    assert all("pets" in e.tags for e in result.endpoints)


def test_search_by_tag_store(petstore_index):
    result = petstore_index.search(query="order", tag="store")
    assert result.total >= 2


def test_search_limit(petstore_index):
    result = petstore_index.search(query="pet", limit=2)
    assert len(result.endpoints) <= 2
    assert result.total >= 3


def test_search_no_results(petstore_index):
    result = petstore_index.search(query="nonexistent")
    assert result.total == 0
    assert len(result.endpoints) == 0


def test_get_by_path_method(petstore_index):
    ep = petstore_index.get_by_path_method("/pets", "GET")
    assert ep is not None
    assert ep.summary == "List all pets"


def test_get_by_path_method_not_found(petstore_index):
    ep = petstore_index.get_by_path_method("/nonexistent", "GET")
    assert ep is None


def test_search_by_operation_id(petstore_index):
    result = petstore_index.search(query="listPets")
    assert result.total >= 1
    assert result.endpoints[0].path == "/pets"
    assert result.endpoints[0].method == "GET"