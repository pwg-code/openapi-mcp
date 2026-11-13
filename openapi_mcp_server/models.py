"""Data models for OpenAPI MCP Server."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


# --- Config Models ---


class ProjectConfig(BaseModel):
    name: str
    source: Literal["local", "remote"]
    path: str | None = None
    url: str | None = None
    refresh_interval: int | None = None
    request_timeout: int | None = None
    headers: dict[str, str] = {}

    @model_validator(mode="after")
    def validate_source_fields(self) -> "ProjectConfig":
        if self.source == "local" and not self.path:
            raise ValueError(f"Project '{self.name}': 'path' is required when source is 'local'")
        if self.source == "remote" and not self.url:
            raise ValueError(f"Project '{self.name}': 'url' is required when source is 'remote'")
        return self


class Settings(BaseModel):
    refresh_interval: int = 15
    request_timeout: int = 30


class AppConfig(BaseModel):
    settings: Settings = Settings()
    projects: dict[str, ProjectConfig]


# --- OpenAPI Parsed Models ---


class ServerInfo(BaseModel):
    url: str
    description: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)


class ParameterDetail(BaseModel):
    name: str
    location: str = Field(alias="in")
    required: bool = False
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    description: str | None = None

    model_config = {"populate_by_name": True}


class RequestBodyDetail(BaseModel):
    content_type: str = "application/json"
    required: bool = False
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    example: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class ResponseDetail(BaseModel):
    status_code: str
    description: str = ""
    content_type: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    example: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class Endpoint(BaseModel):
    path: str
    method: str
    summary: str | None = None
    description: str | None = None
    operation_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    deprecated: bool = False
    parameters: list[ParameterDetail] = Field(default_factory=list)
    request_body: RequestBodyDetail | None = None
    responses: list[ResponseDetail] = Field(default_factory=list)
    servers: list[ServerInfo] = Field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.method.upper()} {self.path}"


class TagInfo(BaseModel):
    name: str
    description: str | None = None
    endpoint_count: int = 0


class ParsedSpec(BaseModel):
    title: str
    version: str
    description: str | None = None
    servers: list[ServerInfo] = Field(default_factory=list)
    endpoints: list[Endpoint] = Field(default_factory=list)
    tags: list[TagInfo] = Field(default_factory=list)
    schemas: dict[str, dict[str, Any]] = Field(default_factory=dict)
    raw_spec: dict[str, Any] = Field(default_factory=dict)


# --- Registry Models ---


class ProjectStatus(str, Enum):
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


class ProjectEntry(BaseModel):
    config: ProjectConfig
    spec: ParsedSpec | None = None
    status: ProjectStatus = ProjectStatus.LOADING
    last_updated: datetime | None = None
    last_checked: datetime | None = None
    error_message: str | None = None
    content_hash: str | None = None
    failure_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


# --- Tool Input/Output Models ---


class EndpointSummary(BaseModel):
    path: str
    method: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    deprecated: bool = False


class SearchEndpointsResult(BaseModel):
    total: int
    endpoints: list[EndpointSummary]


class ProjectInfo(BaseModel):
    name: str
    source: str
    location: str
    title: str | None = None
    version: str | None = None
    endpoint_count: int = 0
    last_updated: str | None = None
    status: str
    error_message: str | None = None


class ListProjectsResult(BaseModel):
    projects: list[ProjectInfo]


class ProjectNotReadyStatus(BaseModel):
    """Structured response returned when a project exists but its spec is not usable yet."""

    project: str
    status: str
    message: str | None = None
    suggestion: str


class ListTagsResult(BaseModel):
    tags: list[TagInfo]


class ProjectRefreshResult(BaseModel):
    project: str
    updated: bool = False
    previous_version: str | None = None
    current_version: str | None = None
    error: str | None = None


class RefreshResult(BaseModel):
    results: list[ProjectRefreshResult]
